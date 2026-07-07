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

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from app.database import db

# ---- registry handler ----
_HANDLERS: dict[str, Callable] = {}


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
                 poll_interval: float = 0.5):
        self.profile = profile
        self.max_cpu = max(1, max_cpu)
        self.max_gpu = max(0, max_gpu)
        self.poll_interval = poll_interval

        # Executor để DƯ sức (cap 16) — số luồng thực tế do self.max_cpu/max_gpu
        # KIỂM SOÁT khi điều phối, nên ĐỔI SỐ LUỒNG LÚC ĐANG CHẠY được (set_limits).
        self._cpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="cpu")
        self._gpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="gpu")
        self._inflight: set[int] = set()
        self._inflight_gpu: dict[int, bool] = {}   # nhớ job nào dùng GPU (khỏi hỏi DB)
        self._canceled: set[int] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._dispatcher: Optional[threading.Thread] = None
        self._listeners: list[Callable[[], None]] = []

    # ---- vòng đời ----
    def start(self) -> None:
        self._recover_crashed()
        self._stop.clear()
        # cho phép start LẠI sau stop(): executor đã shutdown thì tạo mới
        if self._cpu_pool._shutdown:
            self._cpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="cpu")
        if self._gpu_pool._shutdown:
            self._gpu_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="gpu")
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
        db.execute(
            "UPDATE jobs SET status='pending', progress=0, "
            "message='Tạm dừng do tắt app' WHERE status='running'"
        )
        self._cpu_pool.shutdown(wait=wait, cancel_futures=True)
        if self._gpu_pool:
            self._gpu_pool.shutdown(wait=wait, cancel_futures=True)

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
                   max_gpu: Optional[int] = None) -> None:
        """Đổi SỐ LUỒNG lúc đang chạy (cắt = cpu, AI = gpu). Có hiệu lực ngay."""
        if max_cpu is not None:
            self.max_cpu = max(1, min(16, int(max_cpu)))
        if max_gpu is not None:
            self.max_gpu = max(1, min(16, int(max_gpu)))
        self._notify()   # đánh thức điều phối để áp số mới ngay

    # ---- crash recovery ----
    def _recover_crashed(self) -> None:
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
        # đang chạy -> báo 'Đang hủy...' để UI phản hồi tức thì
        db.execute(
            "UPDATE jobs SET message='Đang hủy...' "
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
            "UPDATE jobs SET message='Đang hủy...' WHERE status='running'"
        )
        self._notify()

    def retry(self, job_id: int) -> None:
        self._canceled.discard(job_id)
        db.execute(
            "UPDATE jobs SET status='pending', attempts=0, error=NULL, "
            "progress=0, message='Đưa lại hàng đợi' "
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

    def _capacity(self, needs_gpu: bool) -> int:
        # dùng bộ nhớ (không truy vấn DB) -> nhanh, không nghẽn, đếm đúng
        with self._lock:
            running_gpu = sum(1 for v in self._inflight_gpu.values() if v)
            running_cpu = len(self._inflight) - running_gpu
        return (self.max_gpu - running_gpu) if needs_gpu else (self.max_cpu - running_cpu)

    def _dispatch_once(self) -> None:
        rows = db.query(
            "SELECT id, type, payload, needs_gpu FROM jobs WHERE status='pending' "
            "ORDER BY priority DESC, created_at ASC LIMIT 50"
        )
        for r in rows:
            jid = int(r["id"])
            with self._lock:
                if jid in self._inflight:
                    continue
            needs_gpu = bool(r["needs_gpu"])
            if self._capacity(needs_gpu) <= 0:
                continue
            with self._lock:
                self._inflight.add(jid)
                self._inflight_gpu[jid] = needs_gpu
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
            self._canceled.discard(job_id)
            self._notify()
