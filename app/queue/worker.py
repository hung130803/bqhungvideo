"""
Worker pool + job queue bền vững (SQLite).

Đặc điểm theo spec:
- Hàng đợi GPU RIÊNG: job needs_gpu chạy trong pool GPU giới hạn (mặc định 1)
  để 2 job không tranh GPU; job CPU chạy trong pool CPU.
- Persistent: trạng thái lưu DB. Khởi động lại -> job 'running' dở được đưa về
  'pending' và chạy tiếp.
- Smart-skip: enqueue trùng dedup_key (đã done) -> bỏ qua.
- Retry: lỗi -> tăng attempts, còn lượt thì về 'pending', hết lượt -> 'failed'.
- Hủy: cancel(job_id) -> handler nhận CanceledError ở checkpoint gần nhất.

Handler đăng ký trong jobs.py qua register_handler(type, fn).
fn(payload: dict, ctx: JobContext) -> dict (result) hoặc None.
"""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from app.database import db

# ---- registry handler ----
_HANDLERS: dict[str, Callable] = {}

# ---- LÀN THỨ BA: THAY GIỌNG NÓI ----
# Vì sao phải có làn RIÊNG (không dùng lại làn CPU/GPU):
#   · Job thay giọng chạy HÀNG PHÚT mỗi video (Demucs 0,4× thời lượng + Groq
#     + edge-tts) và ăn ~1,3 GB RAM. Nhét vào làn CPU là job xuất clip của
#     anh Hùng phải xếp hàng sau nó.
#   · `_lane_limit` khoá mỗi làn về 1 khi ECO_MODE bật (mặc định BẬT), nên
#     dùng làn cũ thì SỐ LUỒNG user đặt ở hộp Thay giọng không bao giờ có
#     tác dụng — đa luồng chỉ là cái nhãn.
# Điều phối vẫn lấy job theo TỪNG LÀN, cửa sổ 50 dòng RIÊNG cho mỗi làn —
# đúng cách đã chữa lỗi "làn cắt chết đói vì LIMIT 50" (cổng 5).
LAN_GPU = "gpu"
LAN_CPU = "cpu"
LAN_TG = "tg"
LOAI_LAN_TG = ("thay_giong",)
_TG_PLACE = ",".join("?" * len(LOAI_LAN_TG))

#: Trần luồng của làn thay giọng khi giọng đọc chạy QUA MẠNG (edge-tts,
#: ElevenLabs). Demucs ăn ~1,3 GB RAM/video; quá số này là máy đảo trang ->
#: CHẬM HƠN chứ không nhanh hơn.
#:
#: **ĐỪNG HẠ SỐ NÀY** — 200-300 kênh đang chạy sản xuất bằng edge-tts, và cổng
#: 55 CA 2 đo trên chính đường đó: 2 luồng nhanh hơn chạy lần lượt **1,82 lần**
#: (13,80s so với 25,06s). Cái phải hạ là trần của GIỌNG CHẠY TRÊN MÁY, và nó
#: là một con số KHÁC — xem `tran_luong_tg`.
TG_TRAN = 4

# ---------------------------------------------------------------------------
# TRẦN LUỒNG PHỤ THUỘC LOẠI GIỌNG
# ---------------------------------------------------------------------------
# SỐ ĐO 21/08/2026 trên máy anh Hùng (24 nhân · 31,8 GB), CÙNG 4 video, đường
# giọng NHÂN BẢN (chạy trên máy):
#   · **4 luồng: hơn 1,5 TIẾNG -> ra 0 VIDEO**
#   · **1 luồng: khoảng 45 PHÚT -> ra 4 VIDEO**
# Lúc chạy 4 luồng đo được **23,5 trong 24 nhân bận, máy 100% CPU**, mỗi video
# chậm đi ~4 lần. Tức ô "Số luồng" đang MỜI người dùng chọn con số làm chậm
# chính mình.
#
# VÌ SAO `TG_TRAN = 4` KHÔNG SAI Ở CHỖ NÓ RA ĐỜI MÀ VẪN HỎNG Ở ĐÂY: nó được
# đặt theo bước TÁCH NHẠC Demucs (~1,3 GB RAM/video) — đúng với đường edge-tts,
# vì edge-tts đọc QUA MẠNG nên không đốt một nhân CPU nào. Đường giọng chạy
# TRÊN MÁY có thêm một bước nặng THỨ HAI mà **chưa ai đo lúc đặt con số đó**:
# VieNeu ăn ~3 GB RAM và **6,6-8,3 NHÂN CPU mỗi tiến trình**. Bốn tiến trình
# như thế đòi 26-33 nhân trên một máy 24 nhân -> tranh nhau -> chậm hơn CHÍNH
# NÓ chạy 1 luồng. Nên đây **KHÔNG phải "hạ trần xuống 1"**, mà là **trần phải
# PHỤ THUỘC GIỌNG**.
#
# SUY RA TỪ MÁY, KHÔNG GHI CỨNG MỘT SỐ: máy 8 nhân và máy 24 nhân không thể
# dùng chung một con số, và máy nhân viên thì khác hẳn máy anh Hùng.
#: Nhân CPU cho 1 luồng giọng-trên-máy (đo 6,6-8,3 -> lấy đầu trên).
NHAN_MOI_LUONG_MAY = 8.0
#: RAM cho 1 luồng giọng-trên-máy: VieNeu ~3 GB + Demucs ~1,3 GB.
RAM_MOI_LUONG_MAY_GB = 4.3
#: Chừa lại cho phần còn lại của app (ffmpeg xuất clip · phân tích · giao diện)
#: + hệ điều hành. Không chừa thì đúng lúc thay giọng chạy là mọi việc khác
#: đứng — mà máy anh Hùng LUÔN có prodown tải nền ("Đo A/B phải đan xen").
NHAN_CHUA = 4.0
RAM_CHUA_GB = 6.0


def phan_cung() -> tuple[int, float]:
    """(số nhân CPU, RAM GB). Không đọc được RAM -> **0,0 = "không biết"**.

    Đọc thẳng `os`/`psutil` chứ KHÔNG mượn `resource_manager.HARDWARE`: module
    đó gọi `nvidia-smi` ngay lúc import, mà bộ điều phối phải nạp được cả ở
    cổng test lẫn máy không GPU.
    """
    nhan = os.cpu_count() or 4
    ram = 0.0
    try:
        import psutil
        nhan = psutil.cpu_count(logical=True) or nhan
        ram = float(psutil.virtual_memory().total) / (1024 ** 3)
    except Exception:  # noqa: BLE001 - thiếu psutil -> chỉ mất cột RAM
        pass
    return max(1, int(nhan)), ram


def tran_luong_tg(tren_may: bool = False, nhan: Optional[int] = None,
                  ram_gb: Optional[float] = None) -> int:
    """Trần luồng KHUYẾN NGHỊ của làn thay giọng, THEO LOẠI GIỌNG.

    `tren_may=False` (edge-tts · ElevenLabs — đọc QUA MẠNG) -> trả nguyên
    `TG_TRAN`, **không đổi một ly hành vi đang chạy sản xuất**.

    `tren_may=True` (nhân bản `vnb:` · VieNeu `vn:` · Kokoro `kk:` · Piper ·
    giọng ngoài) -> suy từ SỐ NHÂN và RAM của chính máy này.

    Bộ điều phối **KHÔNG tự phân loại giọng** — bảng tiền tố chỉ có một nguồn
    duy nhất là `giong_bang.tren_may`, hộp Thay giọng hỏi rồi truyền vào. Chép
    một bảng tiền tố thứ hai vào đây là đẻ chỗ để lệch nhau (đúng ca `ov:` ·
    `vn:` · `cb:` · `kk:` đã sập bốn lần ở `giong_bang._TIEN_TO`).

    Hàm THUẦN khi truyền `nhan`/`ram_gb` — cổng test chấm được máy 8 nhân mà
    không cần một cái máy 8 nhân.

    `ram_gb=0` = không đọc được -> **KHÔNG kẹp theo RAM** (luật chung của repo:
    không xác định được thì GIỮ, đừng đoán rồi hạ oan).
    """
    if not tren_may:
        return TG_TRAN
    n, r = phan_cung()
    if nhan is not None:
        n = max(1, int(nhan))
    if ram_gb is not None:
        r = float(ram_gb)
    tran = min(TG_TRAN, int((n - NHAN_CHUA) // NHAN_MOI_LUONG_MAY))
    if r > 0:
        tran = min(tran, int((r - RAM_CHUA_GB) // RAM_MOI_LUONG_MAY_GB))
    return max(1, tran)


def register_handler(job_type: str, fn: Callable) -> None:
    _HANDLERS[job_type] = fn


# ---- theo dõi TIẾN TRÌNH CON theo JOB (để Hủy có tác dụng NGAY) ----
# Trước đây Hủy chỉ đặt cờ; worker chỉ kiểm cờ ở checkpoint (progress) -> nếu
# đang kẹt trong 1 lệnh ffmpeg/phân tích dài thì phải đợi lệnh đó XONG (1-2
# phút). Giờ: mỗi tiến trình con spawn từ thread job được GẮN vào job_id đang
# chạy trên thread đó; cancel(job_id) -> kill NGAY các tiến trình này -> lệnh
# đang chạy chết trong ~1s -> handler thấy cờ hủy -> CanceledError.
_CURRENT = threading.local()            # .pool / .job_id của thread worker
_JOB_PROCS: dict[int, set] = {}
_JOB_PROCS_LOCK = threading.Lock()

# Pool đang chạy của app (chỉ có 1). ffmpeg_utils đọc để chia NGÂN SÁCH luồng
# encode (-threads = ngân_sách // max_cpu) mà không phải import UI.
_ACTIVE_POOL: Optional["WorkerPool"] = None


def active_pool() -> Optional["WorkerPool"]:
    return _ACTIVE_POOL


def _set_current_job(pool: "WorkerPool", job_id: int) -> None:
    _CURRENT.pool = pool
    _CURRENT.job_id = job_id


def _clear_current_job() -> None:
    _CURRENT.pool = None
    _CURRENT.job_id = None


def current_job_id() -> Optional[int]:
    """job_id đang chạy trên thread hiện tại (None nếu không phải thread job)."""
    return getattr(_CURRENT, "job_id", None)


def current_job_canceled() -> bool:
    """Job sở hữu thread hiện tại đã bị bấm Hủy? Gọi từ thread thường -> False."""
    pool = getattr(_CURRENT, "pool", None)
    jid = getattr(_CURRENT, "job_id", None)
    return bool(pool is not None and jid is not None and jid in pool._canceled)


def register_job_proc(p) -> None:
    """Gắn tiến trình con vào job đang chạy trên thread này (nếu có).
    cancel(job_id) sẽ kill NGAY các tiến trình đã gắn."""
    jid = current_job_id()
    if jid is None:
        return
    with _JOB_PROCS_LOCK:
        _JOB_PROCS.setdefault(jid, set()).add(p)


def unregister_job_proc(p) -> None:
    jid = current_job_id()
    if jid is None:
        return
    with _JOB_PROCS_LOCK:
        procs = _JOB_PROCS.get(jid)
        if procs:
            procs.discard(p)


def kill_job_procs(job_id: int) -> None:
    """Giết NGAY mọi tiến trình con (ffmpeg/phân tích) của 1 job — gọi khi Hủy.
    kill() không chờ tiến trình thoát -> KHÔNG block UI thread. Tiến trình đã
    kết thúc (poll() không None) thì bỏ qua."""
    with _JOB_PROCS_LOCK:
        procs = list(_JOB_PROCS.get(job_id, ()))
    for p in procs:
        try:
            if p.poll() is None:
                p.kill()
        except OSError:
            pass


class CanceledError(Exception):
    """Ném ra khi job bị hủy giữa chừng."""


class JobContext:
    """Truyền vào handler: báo tiến độ, kiểm tra hủy, lấy profile phần cứng."""

    def __init__(self, pool: "WorkerPool", job_id: int, profile: dict):
        self.pool = pool
        self.job_id = job_id
        self.profile = profile
        self._last = 0.0
        self._last_msg = None

    def progress(self, p: float, msg: str = "") -> None:
        self.check_canceled()
        now = time.time()
        # GHI THƯA để đỡ nghẽn DB (UI + nút Hủy mượt): chỉ ghi mỗi ~0.3s khi cùng
        # 1 bước; mốc đầu/cuối hoặc đổi bước thì ghi ngay.
        if 0.0 < p < 1.0 and msg == self._last_msg and (now - self._last) < 0.3:
            return
        self._last = now
        self._last_msg = msg
        db.execute(
            "UPDATE jobs SET progress=?, message=? WHERE id=?",
            (max(0.0, min(1.0, p)), msg, self.job_id),
        )
        self.pool._notify()

    def check_canceled(self) -> None:
        if self.job_id in self.pool._canceled:
            raise CanceledError()


class WorkerPool:
    def __init__(self, profile: dict, max_cpu: int = 2, max_gpu: int = 1,
                 poll_interval: float = 0.5, max_tg: int = 2):
        self.profile = profile
        self.max_cpu = max(1, max_cpu)
        self.max_gpu = max(0, max_gpu)
        self.max_tg = max(1, max_tg)
        # Giọng đang chọn có chạy TRÊN MÁY không, và người dùng đã CỐ Ý ép số
        # cao hơn khuyến nghị chưa. Hộp Thay giọng đặt hai cờ này qua
        # `set_limits`; không ai đặt -> giữ đúng hành vi cũ (trần `TG_TRAN`).
        self.tg_tren_may = False
        self.tg_ep = False
        self.poll_interval = poll_interval

        # Executor để DƯ sức (cap 16) — số luồng thực tế do self.max_cpu/max_gpu
        # KIỂM SOÁT khi điều phối, nên ĐỔI SỐ LUỒNG LÚC ĐANG CHẠY được (set_limits).
        self._cpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="cpu")
        self._gpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="gpu")
        # Executor RIÊNG cho làn thay giọng: job ở đây chạy HÀNG PHÚT, dùng
        # chung executor với làn CPU là job xuất clip không còn chỗ chạy.
        self._tg_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="tg")
        self._inflight: set[int] = set()
        self._inflight_gpu: dict[int, bool] = {}   # nhớ job nào dùng GPU (khỏi hỏi DB)
        self._inflight_tg: set[int] = set()        # job đang chạy ở làn THAY GIỌNG
        self._canceled: set[int] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._dispatcher: Optional[threading.Thread] = None
        self._listeners: list[Callable[[], None]] = []
        global _ACTIVE_POOL
        _ACTIVE_POOL = self       # cho ffmpeg_utils chia ngân sách luồng encode

    # ---- vòng đời ----
    def start(self) -> None:
        self._recover_crashed()
        self._stop.clear()
        # cho phép start LẠI sau stop(): executor đã shutdown thì tạo mới
        if self._cpu_pool._shutdown:
            self._cpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="cpu")
        if self._gpu_pool._shutdown:
            self._gpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="gpu")
        if getattr(self._tg_pool, "_shutdown", False):
            self._tg_pool = ThreadPoolExecutor(max_workers=8,
                                               thread_name_prefix="tg")
        self._dispatcher = threading.Thread(target=self._loop, daemon=True,
                                            name="dispatcher")
        self._dispatcher.start()

    def stop(self, wait: bool = False) -> None:
        self._stop.set()
        if self._dispatcher and self._dispatcher.is_alive():
            self._dispatcher.join(timeout=2)  # dừng điều phối trước khi đóng pool
        # Báo hủy cho job ĐANG chạy in-process (auto/LLM): thread sẽ thoát ở
        # checkpoint gần nhất thay vì giữ .exe sống ngầm tới khi job xong
        # (ThreadPoolExecutor join thread non-daemon lúc interpreter shutdown).
        with self._lock:
            self._canceled.update(self._inflight)
        # Job đang 'Đang hủy...' (cancel_req=1) phải CHỐT 'canceled' trước —
        # đưa nó về 'pending' như job thường là mở app lại nó TỰ CHẠY LẠI
        # dù user đã bấm Huỷ (bug anh Hùng 30/07: huỷ xong tắt app/cập nhật,
        # vào lại thấy job huỷ tự chạy).
        db.execute(
            "UPDATE jobs SET status='canceled', message='Đã hủy', "
            "finished_at=datetime('now') "
            "WHERE status='running' AND cancel_req=1"
        )
        db.execute(
            "UPDATE jobs SET status='pending', progress=0, "
            "message='Tạm dừng do tắt app' WHERE status='running'"
        )
        self._cpu_pool.shutdown(wait=wait, cancel_futures=True)
        if self._gpu_pool:
            self._gpu_pool.shutdown(wait=wait, cancel_futures=True)
        if getattr(self, "_tg_pool", None):
            self._tg_pool.shutdown(wait=wait, cancel_futures=True)

    def add_listener(self, fn: Callable[[], None]) -> None:
        """UI đăng ký để được báo khi có thay đổi (cập nhật bảng job)."""
        self._listeners.append(fn)

    def _notify(self) -> None:
        for fn in list(self._listeners):
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass

    def set_limits(self, max_cpu: Optional[int] = None,
                   max_gpu: Optional[int] = None,
                   max_tg: Optional[int] = None,
                   tg_tren_may: Optional[bool] = None,
                   tg_ep: Optional[bool] = None) -> None:
        """Đổi SỐ LUỒNG lúc đang chạy (cắt = cpu, AI = gpu, thay giọng = tg).
        Có hiệu lực ngay.

        `tg_tren_may` = giọng đang chọn có chạy TRÊN MÁY không (hộp Thay giọng
        hỏi `giong_bang.tren_may` rồi truyền vào — xem `tran_luong_tg`).
        `tg_ep` = người dùng ĐÃ ĐỌC cảnh báo mà vẫn chọn số cao hơn khuyến
        nghị -> tôn trọng, chỉ còn trần cứng `TG_TRAN`. **Không ai truyền hai
        cờ này thì hành vi giống HỆT bản trước** (đường edge-tts của 200-300
        kênh không đổi một ly).
        """
        if max_cpu is not None:
            self.max_cpu = max(1, min(16, int(max_cpu)))
        if max_gpu is not None:
            self.max_gpu = max(1, min(16, int(max_gpu)))
        if tg_tren_may is not None:
            self.tg_tren_may = bool(tg_tren_may)
        if tg_ep is not None:
            self.tg_ep = bool(tg_ep)
        if max_tg is not None:
            self.max_tg = max(1, min(TG_TRAN, int(max_tg)))
        self._notify()   # đánh thức điều phối để áp số mới ngay

    # ---- crash recovery ----
    def _recover_crashed(self) -> None:
        # Job user ĐÃ BẤM HUỶ (cancel_req=1) mà app tắt/crash trước khi kịp
        # chốt -> 'canceled', TUYỆT ĐỐI không đưa lại hàng đợi (huỷ là huỷ).
        db.execute(
            "UPDATE jobs SET status='canceled', message='Đã hủy', "
            "finished_at=datetime('now') "
            "WHERE status='running' AND cancel_req=1"
        )
        # Job dở mà CHƯA hết lượt -> đưa lại hàng đợi chạy tiếp.
        db.execute(
            "UPDATE jobs SET status='pending', progress=0, "
            "message='Khôi phục sau khi tắt app' "
            "WHERE status='running' AND attempts < max_attempts"
        )
        # Job dở đã hết lượt (có thể đã làm sập app nhiều lần) -> đánh dấu thất bại,
        # KHÔNG chạy lại để tránh vòng lặp crash khi mở app.
        db.execute(
            "UPDATE jobs SET status='failed', "
            "error='Dừng đột ngột nhiều lần (có thể lỗi thư viện native). "
            "Đã ngừng tự chạy lại — bấm Thử lại nếu muốn.', "
            "message='Thất bại (đã ngừng tự lặp)', finished_at=datetime('now') "
            "WHERE status='running' AND attempts >= max_attempts"
        )

    # ---- enqueue (smart-skip) ----
    def enqueue(self, job_type: str, payload: dict, *, project_id=None,
                video_id=None, needs_gpu: bool = False, priority: int = 0,
                dedup_key: Optional[str] = None, max_attempts: int = 3,
                skip_if_done: bool = True) -> Optional[int]:
        if dedup_key:
            done = skip_if_done and db.query_one(
                "SELECT id FROM jobs WHERE dedup_key=? AND status='done'",
                (dedup_key,),
            )
            if done:
                return None  # đã làm rồi -> bỏ qua
            # đang chờ/đang chạy cùng key -> trả id cũ, không tạo trùng
            pend = db.query_one(
                "SELECT id, status FROM jobs WHERE dedup_key=? AND status IN "
                "('pending','running')", (dedup_key,),
            )
            if pend:
                # Job trùng còn XẾP HÀNG -> cập nhật payload MỚI NHẤT (user vừa
                # đổi cài đặt rồi bấm lại thì phải áp cài đặt mới). Điều kiện
                # status='pending' trong UPDATE tránh race với dispatcher.
                if pend["status"] == "pending":
                    db.execute(
                        "UPDATE jobs SET payload=? WHERE id=? AND status='pending'",
                        (db.dumps(payload), pend["id"]),
                    )
                return int(pend["id"])

        job_id = db.insert(
            """INSERT INTO jobs (type, project_id, video_id, payload, needs_gpu,
                                 priority, dedup_key, max_attempts, status)
               VALUES (?,?,?,?,?,?,?,?, 'pending')""",
            (job_type, project_id, video_id, db.dumps(payload),
             1 if needs_gpu else 0, priority, dedup_key, max_attempts),
        )
        self._notify()
        return job_id

    def cancel(self, job_id: int) -> None:
        self._canceled.add(job_id)
        # KILL NGAY tiến trình con của job (ffmpeg encode/tiến trình phân tích):
        # lệnh đang chạy chết trong ~1s -> _run thấy cờ hủy -> CanceledError
        # -> job kết thúc 'canceled' ngay thay vì đợi lệnh chạy hết (1-2 phút).
        kill_job_procs(job_id)
        # nếu còn pending (chưa chạy) -> đánh dấu canceled luôn
        db.execute(
            "UPDATE jobs SET status='canceled', message='Đã hủy' "
            "WHERE id=? AND status='pending'", (job_id,),
        )
        # đang chạy -> báo 'Đang hủy...' + GHI Ý ĐỊNH HUỶ BỀN vào DB.
        # cancel_req=1 để stop()/khôi phục sau restart biết job này ĐÃ bị huỷ
        # — cờ RAM (_canceled) chết theo app, chỉ mình nó thì tắt app/cập nhật
        # đúng lúc 'Đang hủy...' là job hồi sinh chạy lại (bug anh Hùng 30/07).
        db.execute(
            "UPDATE jobs SET message='Đang hủy...', cancel_req=1 "
            "WHERE id=? AND status='running'", (job_id,),
        )
        self._notify()

    def cancel_all(self) -> None:
        """Hủy MỌI việc: job pending -> 'canceled' NGAY (1 lệnh SQL); job đang
        chạy -> đặt cờ + kill tiến trình con từng job. Không chờ gì cả (an toàn
        gọi từ UI thread)."""
        with self._lock:
            running = list(self._inflight)
        self._canceled.update(running)
        for jid in running:
            kill_job_procs(jid)
        db.execute(
            "UPDATE jobs SET status='canceled', message='Đã hủy' "
            "WHERE status='pending'"
        )
        db.execute(
            "UPDATE jobs SET message='Đang hủy...', cancel_req=1 "
            "WHERE status='running'"
        )
        self._notify()

    def retry(self, job_id: int) -> None:
        self._canceled.discard(job_id)
        # cancel_req=0: user CHỦ ĐỘNG chạy lại — xoá ý định huỷ cũ, nếu không
        # lần tắt app kế tiếp lại chuyển nó thành 'canceled' oan.
        db.execute(
            "UPDATE jobs SET status='pending', attempts=0, error=NULL, "
            "progress=0, cancel_req=0, message='Đưa lại hàng đợi' "
            "WHERE id=? AND status IN ('failed','canceled')", (job_id,),
        )
        self._notify()

    # ---- vòng lặp dispatcher ----
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._dispatch_once()
            except Exception:  # noqa: BLE001 - dispatcher không bao giờ chết
                pass
            time.sleep(self.poll_interval)

    def _lane_limit(self, needs_gpu: bool) -> int:
        """Số job tối đa của lane. TIẾT KIỆM MÁY (settings.ECO_MODE, mặc định
        BẬT): mỗi lane chỉ 1 job (1 xuất + 1 phân tích) -> máy vẫn dùng bình
        thường khi app chạy. Đọc settings mỗi lần nên bật/tắt có hiệu lực NGAY."""
        limit = self.max_gpu if needs_gpu else self.max_cpu
        try:
            from config import settings
            if settings.ECO_MODE:
                return min(limit, 1)
        except Exception:  # noqa: BLE001 - thiếu config (test) -> giữ nguyên
            pass
        return limit

    def _lane_limit_tg(self) -> int:
        """Số video THAY GIỌNG chạy song song.

        CỐ Ý KHÔNG bị `ECO_MODE` khoá về 1: đây là việc người dùng vừa bấm và
        đang NGỒI XEM bảng tiến độ, còn số luồng thì chính họ đặt trong hộp
        Thay giọng. Khoá về 1 là biến ô "Số luồng" thành cái nhãn vô nghĩa.
        Trần `TG_TRAN` vì Demucs ăn ~1,3 GB RAM/video — quá số này là máy đảo
        trang, chậm hơn chứ không nhanh hơn.

        **TRẦN PHỤ THUỘC GIỌNG (21/08/2026).** `TG_TRAN` đo theo bước Demucs,
        đúng cho giọng đọc QUA MẠNG. Giọng chạy TRÊN MÁY còn ăn 6,6-8,3 nhân
        CPU mỗi tiến trình nữa, nên `tg_tren_may` -> kẹp thêm bằng
        `tran_luong_tg(True)` (suy từ nhân + RAM của máy này).

        **VẪN CHO ÉP:** `tg_ep` = người dùng đã đọc cảnh báo trên hộp Thay
        giọng và vẫn chọn số cao hơn -> bỏ kẹp khuyến nghị, chỉ giữ trần cứng.
        Cùng tinh thần với việc hàm này cố ý không nghe `ECO_MODE`: khoá cứng
        là biến ô "Số luồng" thành cái nhãn.
        """
        tran = TG_TRAN
        if self.tg_tren_may and not self.tg_ep:
            tran = min(tran, tran_luong_tg(True))
        return max(1, min(tran, int(self.max_tg)))

    def _dem_lan(self) -> tuple[int, int, int]:
        """(đang chạy GPU, đang chạy CPU, đang chạy THAY GIỌNG).

        Đọc bộ nhớ, KHÔNG truy vấn DB -> nhanh, không nghẽn, đếm đúng.
        """
        with self._lock:
            tg = len(self._inflight_tg)
            gpu = sum(1 for j, v in self._inflight_gpu.items()
                      if v and j not in self._inflight_tg)
            cpu = len(self._inflight) - gpu - tg
        return gpu, cpu, tg

    def _capacity_lan(self, lan: str) -> int:
        gpu, cpu, tg = self._dem_lan()
        if lan == LAN_TG:
            return self._lane_limit_tg() - tg
        la_gpu = lan == LAN_GPU
        return self._lane_limit(la_gpu) - (gpu if la_gpu else cpu)

    def _capacity(self, needs_gpu: bool) -> int:
        """Giữ nguyên chữ ký CŨ (script đo/test ngoài đang gọi)."""
        return self._capacity_lan(LAN_GPU if needs_gpu else LAN_CPU)

    def _dispatch_once(self) -> None:
        """Xếp job chờ vào 3 LÀN RIÊNG: GPU (phân tích) · CPU (cắt/xuất) ·
        TG (thay giọng nói).

        LỖI THẬT (anh Hùng 2026-07-26 — màn Tiến trình hiện "1 phân tích ·
        0 đang cắt · 72 đợi" dù Luồng cắt = 2): trước đây chỉ MỘT query
        `ORDER BY priority DESC ... LIMIT 50` cho CẢ HAI làn. Job phân tích có
        priority=10, job xuất priority=3 — nên khi ≥50 job phân tích đang chờ
        thì 50 dòng lấy về TOÀN LÀ phân tích, job xuất KHÔNG BAO GIỜ lọt vào
        cửa sổ → làn CPU đứng im, video phân tích xong mà không ai cắt. Chạy
        2 nhóm cùng lúc là chạm ngưỡng này ngay (72 > 50).

        Nay MỖI LÀN có cửa sổ 50 dòng RIÊNG nên một làn bị ngập không thể làm
        làn kia chết đói. Trong từng làn vẫn giữ đúng thứ tự ưu tiên như cũ.
        Làn TG lọc theo `type`, hai làn cũ LOẠI TRỪ đúng các type đó — nếu
        không thì job thay giọng lại nằm chung cửa sổ 50 dòng của làn CPU và
        lỗi chết đói tái diễn y hệt, chỉ đổi tên thủ phạm.
        """
        for lan in (LAN_GPU, LAN_CPU, LAN_TG):
            if self._capacity_lan(lan) <= 0:
                continue                    # làn đang đầy -> khỏi truy vấn
            if lan == LAN_TG:
                rows = db.query(
                    "SELECT id, type, payload, needs_gpu FROM jobs "
                    f"WHERE status='pending' AND type IN ({_TG_PLACE}) "
                    "ORDER BY priority DESC, created_at ASC LIMIT 50",
                    tuple(LOAI_LAN_TG))
            else:
                rows = db.query(
                    "SELECT id, type, payload, needs_gpu FROM jobs "
                    "WHERE status='pending' AND needs_gpu=? "
                    f"AND type NOT IN ({_TG_PLACE}) "
                    "ORDER BY priority DESC, created_at ASC LIMIT 50",
                    (1 if lan == LAN_GPU else 0, *LOAI_LAN_TG))
            self._dispatch_rows(rows, lan)

    def _dispatch_rows(self, rows, lan) -> None:
        # `lan` nhận CẢ bool (bản cũ: True = GPU) lẫn chuỗi làn — script đo cũ
        # gọi thẳng hàm này thì vẫn chạy đúng thay vì xếp nhầm làn im lặng.
        if isinstance(lan, bool):
            lan = LAN_GPU if lan else LAN_CPU
        for r in rows:
            jid = int(r["id"])
            with self._lock:
                if jid in self._inflight:
                    continue
            needs_gpu = bool(r["needs_gpu"])
            if self._capacity_lan(lan) <= 0:
                break                       # làn vừa đầy -> dừng, sang làn kia
            with self._lock:
                self._inflight.add(jid)
                self._inflight_gpu[jid] = needs_gpu
                if lan == LAN_TG:
                    self._inflight_tg.add(jid)
            if lan == LAN_TG:
                pool = self._tg_pool
            else:
                pool = self._gpu_pool if needs_gpu else self._cpu_pool
            pool.submit(self._run_job, jid, r["type"], r["payload"])

    # ---- chạy 1 job ----
    def _run_job(self, job_id: int, job_type: str, payload_json: str) -> None:
        payload = db.loads(payload_json, {})
        ctx = JobContext(self, job_id, self.profile)
        handler = _HANDLERS.get(job_type)
        _set_current_job(self, job_id)   # để register_job_proc gắn đúng job
        try:
            if handler is None:
                raise RuntimeError(f"Không có handler cho job type '{job_type}'")
            # Đóng race Hủy-tất-cả ↔ dispatcher: job vừa bị đánh dấu canceled
            # (khi còn pending) nhưng dispatcher đã kịp submit -> không chạy.
            if job_id in self._canceled:
                raise CanceledError()
            row = db.query_one("SELECT status FROM jobs WHERE id=?", (job_id,))
            if row and row["status"] == "canceled":
                raise CanceledError()
            db.execute(
                "UPDATE jobs SET status='running', progress=0, "
                "started_at=datetime('now'), "
                "attempts=attempts+1, message='Bắt đầu...' WHERE id=?", (job_id,),
            )
            self._notify()
            result = handler(payload, ctx)
            db.execute(
                "UPDATE jobs SET status='done', progress=1.0, result=?, "
                "error=NULL, message='Hoàn tất', finished_at=datetime('now') "
                "WHERE id=?",
                (db.dumps(result) if result is not None else None, job_id),
            )
            # GHI HOẠT ĐỘNG GẦN NHẤT thẳng vào kênh/video (bền vững, không mất
            # khi 'Xóa lịch sử' xoá job done). Nhãn dùng chính type job.
            jr = db.query_one(
                "SELECT project_id, video_id FROM jobs WHERE id=?", (job_id,))
            if jr and jr["video_id"] is not None:
                db.execute(
                    "UPDATE videos SET last_done_at=datetime('now'), "
                    "last_done_type=? WHERE id=?", (job_type, jr["video_id"]))
            if jr and jr["project_id"] is not None:
                db.execute(
                    "UPDATE projects SET last_done_at=datetime('now'), "
                    "last_done_type=? WHERE id=?", (job_type, jr["project_id"]))
        except CanceledError:
            db.execute(
                "UPDATE jobs SET status='canceled', message='Đã hủy', "
                "finished_at=datetime('now') WHERE id=?", (job_id,),
            )
        except Exception as e:  # noqa: BLE001
            row = db.query_one("SELECT attempts, max_attempts FROM jobs WHERE id=?",
                               (job_id,))
            attempts = row["attempts"] if row else 99
            max_att = row["max_attempts"] if row else 3
            if attempts < max_att:
                db.execute(
                    "UPDATE jobs SET status='pending', progress=0, error=?, "
                    "message=? WHERE id=?",
                    (str(e), f"Lỗi, thử lại ({attempts}/{max_att})", job_id),
                )
            else:
                db.execute(
                    "UPDATE jobs SET status='failed', error=?, "
                    "message='Thất bại', finished_at=datetime('now') WHERE id=?",
                    (str(e), job_id),
                )
        finally:
            _clear_current_job()
            with _JOB_PROCS_LOCK:
                _JOB_PROCS.pop(job_id, None)
            with self._lock:
                self._inflight.discard(job_id)
                self._inflight_gpu.pop(job_id, None)
                self._inflight_tg.discard(job_id)
            self._canceled.discard(job_id)
            self._notify()
