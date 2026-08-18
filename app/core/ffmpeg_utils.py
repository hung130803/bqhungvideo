"""
Bọc ffmpeg/ffprobe qua CLI (ổn định hơn binding trên Windows).

Nguyên tắc tối ưu I/O (theo spec): ghép filter graph trong 1 lệnh, tránh
xuất file tạm thừa. Hàm export_vertical_clip cắt + crop bám mặt + scale 9:16
+ encode trong DUY NHẤT 1 lệnh ffmpeg.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from config import settings

# Cờ giấu cửa sổ console đen trên Windows khi gọi subprocess
_CREATE_NO_WINDOW = 0x08000000 if hasattr(subprocess, "STARTUPINFO") else 0
# Ưu tiên IDLE cho tác vụ NẶNG (encode/phân tích dài): Windows LUÔN nhường mọi
# app khác trước -> máy KHÔNG đơ khi đang xuất; máy rảnh thì encode vẫn full tốc.
# (Tác vụ ngắn probe/demo giữ nguyên ưu tiên thường — xong trong vài giây.)
_IDLE_PRIORITY = 0x00000040 if hasattr(subprocess, "STARTUPINFO") else 0


# Theo dõi tiến trình con đang chạy để DỪNG khi tắt app (tránh ffmpeg mồ côi
# ngốn CPU sau khi đóng app -> lần mở sau bị nghẽn).
import threading as _threading
_ACTIVE_PROCS: set = set()
_PROC_LOCK = _threading.Lock()
# Bật khi app đang đóng -> cấm spawn ffmpeg mới (vd fallback NVENC->libx264)
_SHUTDOWN = _threading.Event()


def register_proc(p) -> None:
    with _PROC_LOCK:
        _ACTIVE_PROCS.add(p)
    # GẮN thêm vào job đang chạy trên thread này (nếu là thread worker) để nút
    # Hủy job kill được tiến trình NGAY (không đợi lệnh chạy xong). Import trễ
    # tránh vòng import; gọi từ thread thường (UI) thì không gắn gì.
    try:
        from app.queue import worker as _w
        _w.register_job_proc(p)
    except Exception:  # noqa: BLE001 - không được làm hỏng spawn vì registry
        pass


def unregister_proc(p) -> None:
    with _PROC_LOCK:
        _ACTIVE_PROCS.discard(p)
    try:
        from app.queue import worker as _w
        _w.unregister_job_proc(p)
    except Exception:  # noqa: BLE001
        pass


def _job_canceled() -> bool:
    """Job (worker) sở hữu thread hiện tại đã bị bấm Hủy? Thread thường -> False."""
    try:
        from app.queue import worker as _w
        return _w.current_job_canceled()
    except Exception:  # noqa: BLE001
        return False


def _raise_if_job_canceled() -> None:
    if _job_canceled():
        from app.queue.worker import CanceledError
        raise CanceledError()


def terminate_all_children() -> None:
    """Dừng mọi tiến trình con (ffmpeg/phân tích) đang chạy (gọi khi đóng app)."""
    _SHUTDOWN.set()      # chặn spawn ffmpeg mới (fallback encoder...) sau lúc này
    with _PROC_LOCK:
        procs = list(_ACTIVE_PROCS)
    for p in procs:
        try:
            p.kill()
        except OSError:
            pass


# ================= CỬA CHỜ: SỐ LỆNH ffmpeg CHẠY CÙNG LÚC =================
# VÌ SAO PHẢI CÓ (đo thật 07/08/2026, máy 24 nhân + RTX 3060, máy rảnh 6-14%):
#   1 lượt xuất  ->  7,04s ·  22,33 CPU-giây ·  61 luồng ( 2,54x số nhân)
#   10 lượt      -> 49,07s · 263,85 CPU-giây · 592 luồng (24,70x số nhân!)
# 10 lượt tốn 263,85 CPU-giây, song song hoàn hảo chỉ cần 223,3 -> +18% CPU
# ĐỐT VÔ ÍCH vì giành luồng. Máy "đơ khi xuất hàng loạt" là vì đây.
#
# VÌ SAO SIẾT NÚM LUỒNG KHÔNG ĐỦ (đo sau khi đã bịt hết núm ở bản này): 10 lượt
# còn 397 luồng = 16,5x số nhân. 1 tiến trình ffmpeg + NVENC có SÀN ~36-40 luồng,
# siết `-threads`/`-filter_threads` hết cỡ cũng không xuống dưới.
# **Chỉ giảm SỐ TIẾN TRÌNH mới đạt mốc "tổng luồng <= 2x số nhân".**
#
# Cửa này ĐỘC LẬP với "số làn" user đặt: user đặt 10 làn thì hàng chờ vẫn nhận
# 10 việc song song (tải/chép lời/AI vẫn chạy bình thường), nhưng chỉ N lệnh
# ffmpeg được chạy cùng lúc, số còn lại ĐỢI TỚI LƯỢT tại đây.
_GATE_COND = _threading.Condition()
_GATE_DANG = 0                  # số lệnh ffmpeg ĐANG chạy (đang giữ chỗ)
# SÀN LUỒNG đo được của 1 tiến trình ffmpeg — dùng để chia ngân sách "tổng
# luồng <= 2x số nhân" thành SỐ TIẾN TRÌNH. nvenc nặng hơn vì kéo pool CUDA.
# SÀN luồng đo được của 1 tiến trình ffmpeg (tư liệu — công thức CŨ chia ngân
# sách luồng cho 2 số này; nay chia theo SỐ NHÂN, xem `so_ffmpeg_song_song`).
_SAN_LUONG_NVENC = 40           # đo: 36 (pha 2 siết hết) .. 49 (pha 1)
_SAN_LUONG_CPU = 30             # đo: 27 (libx264 giải mã 4 + encode 4)
# SỐ NHÂN dành cho MỖI lệnh ffmpeg — công thức chia chỗ từ 08/08/2026.
# Đo thật ở N=1 trên 24 nhân: 1 lệnh xuất chỉ ăn ~1,37 nhân CPU thật (NVENC gánh
# phần nặng), nên chia 8 nhân/lệnh là còn RẤT rộng tay; mức đó cho đúng N=3 trên
# máy anh Hùng. Đường CPU (libx264) tự ăn hết nhân nên phải chia thưa hơn.
_NHAN_MOI_LENH_NVENC = 8
_NHAN_MOI_LENH_CPU = 12


def so_ffmpeg_song_song() -> int:
    """SỐ LỆNH ffmpeg được phép chạy CÙNG LÚC — TỰ ĐO THEO MÁY.

    ĐỔI CÁCH CHIA 08/08/2026 — anh Hùng chốt "ƯU TIÊN THÔNG LƯỢNG, chịu máy hơi
    nặng". Công thức CŨ chia theo NGÂN SÁCH LUỒNG (tổng luồng <= 2x số nhân,
    chia cho SÀN ~40 luồng/tiến trình) ra N=1 trên máy 24 nhân. Số đo ở N=1
    (50 kênh / 10 làn, 08/08/2026):
      - luồng ffmpeg đỉnh 35 = 1,46x nhân · trễ UI 13,7 ms  -> RẤT êm
      - NHƯNG CPU cả máy chỉ dùng **14,3%** (1,37/24 nhân, bỏ không 85%) và
        job thứ 50 đợi **15,4 phút** -> vượt mốc "nghẽn > 10 phút" của chính anh.
    Mốc "<= 2x nhân" và "dùng hết máy" LOẠI TRỪ NHAU vì 1 tiến trình ffmpeg +
    NVENC có SÀN ~36-40 luồng: 48 luồng ngân sách / 40 = 1 tiến trình. Anh Hùng
    chọn thông lượng -> nay chia theo SỐ NHÂN, không theo ngân sách luồng:
      - 24 nhân + NVENC -> 24//8  = **3**   (máy anh Hùng)
      - 16 nhân + NVENC -> 2 ·  8 nhân -> 1 ·  4 nhân -> 1  (máy nhân viên)
      - 24 nhân, CPU    -> 24//12 = 2      (libx264 tự ăn hết nhân, chia thưa)
    Trần vẫn 4: ĐO ĐƯỢC N=4 KHÔNG nhanh hơn N=3 (37,85 vs 37,71 s) mà +32%
    luồng, +12% CPU-giây -> nút cổ chai là GPU. ĐỪNG nới trần.
    `ECO_MODE` ("Tiết kiệm máy") vẫn kéo về 1.

    `BQ_FFMPEG_SLOTS` (biến môi trường) ép cứng con số — dùng để ĐO từng mức và
    gỡ rối trên máy user mà không phải phát hành bản mới.
    """
    ep = os.environ.get("BQ_FFMPEG_SLOTS", "").strip()
    if ep:
        try:
            return max(1, min(16, int(ep)))
        except ValueError:
            pass
    if settings.ECO_MODE:
        return 1               # "Tiết kiệm máy" = 1 lệnh ffmpeg, không hơn
    cores = os.cpu_count() or 4
    # KHÔNG gọi detect_encoder() ở đây: nó có thể spawn ffmpeg thử NVENC, mà hàm
    # này chạy TRONG cửa chờ -> tự khoá mình. Chỉ đọc cache / ý user.
    dung_gpu = (_ENCODER_CACHE == "h264_nvenc"
                or settings.VIDEO_ENCODER == "nvenc")
    moi = _NHAN_MOI_LENH_NVENC if dung_gpu else _NHAN_MOI_LENH_CPU
    return max(1, min(4, cores // moi))


# ================= ĐANG ĐỢI LƯỢT THÌ PHẢI NÓI =================
# ANH HÙNG BÁO 08/08/2026: *"xuất đến 1 ngưỡng r đứng im k báo gì cả, phải 3 4
# phút k hiện 1%"*. ĐO RA GỐC: `_run` xin chỗ ở cửa chờ TRƯỚC khi spawn ffmpeg.
# Lúc đang đợi thì CHƯA CÓ tiến trình nào in dòng `time=`, mà `_run_with_fallback`
# chỉ nhích % khi thấy `time=` -> thanh đứng nguyên VÀ không một chữ nào đổi.
# Máy 24 nhân + NVENC chỉ có 3 chỗ, mà đường PHÂN TÍCH (`extract_audio_wav_why`)
# cũng qua đúng cửa này -> 3 làn AI + 3 làn cắt = 6 việc tranh 3 chỗ.
#
# Cách nối: THEO THREAD (worker chạy mỗi job 1 thread). Job gắn hàm báo bằng
# `dat_bao_cho()`, cửa chờ gọi nó mỗi ~0,5s với câu "đang đợi lượt (N việc
# trước)". Không truyền tham số xuyên 8 tầng hàm, không đụng chữ ký cũ.
_TLS = _threading.local()


def dat_bao_cho(cb: Optional[Callable[[str], None]]) -> None:
    """Gắn hàm BÁO TRẠNG THÁI cho thread hiện tại (None = gỡ). Gọi trong
    `finally` để gỡ, nếu không thread worker dùng lại sẽ báo nhầm việc cũ."""
    _TLS.bao = cb


def _bao_cho(msg: str) -> None:
    cb = getattr(_TLS, "bao", None)
    if cb is None:
        return
    try:
        cb(msg)
    except Exception as e:      # noqa: BLE001 - hàm báo hỏng KHÔNG được làm
        # chết lượt xuất. NHƯNG Huỷ thì PHẢI nổi lên (ctx.progress tự kiểm huỷ).
        if type(e).__name__ == "CanceledError":
            raise


# ---- ƯU TIÊN trong cửa chờ ----
# XUẤT được ưu tiên hơn PHÂN TÍCH vì XUẤT là việc anh Hùng ĐANG NHÌN thanh %,
# còn tách audio chạy nền. NHƯNG ưu tiên trần trụi = bỏ đói chiều ngược lại
# (đúng lỗi "làn cắt chết đói vì LIMIT 50" đã sập một lần), nên có VAN CHỐNG
# ĐÓI: chờ quá `_DOI_TOI_DA` giây thì việc phân tích được NÂNG ngang hàng xuất,
# và trong cùng hàng thì FIFO theo số thứ tự -> nó chắc chắn tới lượt.
UT_XUAT = 0
UT_PHAN_TICH = 1
_DOI_TOI_DA = 20.0          # giây; test hạ xuống để đo nhanh
_GATE_STT = 0               # số thứ tự vào hàng (FIFO trong cùng mức ưu tiên)
_GATE_HANG: dict = {}       # stt -> [ưu_tiên, lúc_vào_hàng]


def _khoa_xep(stt: int, bay_gio: float) -> tuple:
    ut, luc = _GATE_HANG[stt]
    if bay_gio - luc >= _DOI_TOI_DA:
        ut = UT_XUAT        # chờ quá lâu -> nâng hạng, KHÔNG BAO GIỜ chết đói
    return (ut, stt)


def _so_truoc(stt: int, bay_gio: float) -> int:
    """Số việc đứng TRƯỚC mình = đang chạy + đang đợi mà xếp trên mình."""
    ta = _khoa_xep(stt, bay_gio)
    return _GATE_DANG + sum(1 for k in _GATE_HANG
                            if _khoa_xep(k, bay_gio) < ta)


def _xin_cho_ffmpeg(uu_tien: int = UT_XUAT) -> bool:
    """Giữ 1 chỗ trong cửa chờ. True = đã giữ (caller PHẢI trả chỗ ở finally).

    Đợi theo NHỊP 0,25s chứ không chặn vô hạn, vì mỗi nhịp phải kiểm lại:
      - job bị bấm Hủy -> ném CanceledError NGAY (đừng để user bấm Hủy mà việc
        vẫn xếp hàng đợi tới lượt rồi mới chạy);
      - đang đóng app -> trả False và ĐI LUÔN (treo ở đây là treo bước thoát
        app; caller đã tự chặn spawn bằng _SHUTDOWN);
      - trần đã đổi (user bật "Tiết kiệm máy" giữa lượt) -> đọc lại mỗi nhịp;
      - BÁO CHO USER còn mấy việc đứng trước (xem `dat_bao_cho`).
    """
    global _GATE_DANG, _GATE_STT
    with _GATE_COND:
        _GATE_STT += 1
        stt = _GATE_STT
        _GATE_HANG[stt] = [int(uu_tien), time.time()]
    da_bao = False
    lan_bao = 0.0
    try:
        while True:
            if _SHUTDOWN.is_set():
                return False
            with _GATE_COND:
                bay_gio = time.time()
                # tới lượt = còn chỗ VÀ mình đang xếp đầu hàng
                if (_GATE_DANG < so_ffmpeg_song_song()
                        and _khoa_xep(stt, bay_gio) == min(
                            _khoa_xep(k, bay_gio) for k in _GATE_HANG)):
                    _GATE_DANG += 1
                    _GATE_HANG.pop(stt, None)
                    _GATE_COND.notify_all()
                    if da_bao:
                        _bao_cho("đã tới lượt — đang chạy ffmpeg...")
                    return True
                truoc = _so_truoc(stt, bay_gio)
                _GATE_COND.wait(0.25)
            _raise_if_job_canceled()
            # BÁO mỗi ~0,5s (đủ để thanh trạng thái sống, không nghẽn DB)
            if time.time() - lan_bao >= 0.5:
                lan_bao = time.time()
                da_bao = True
                _bao_cho(f"đang đợi lượt ffmpeg ({truoc} việc trước)"
                         if truoc > 0 else "đang đợi lượt ffmpeg...")
    finally:
        with _GATE_COND:
            _GATE_HANG.pop(stt, None)
            _GATE_COND.notify_all()


def _tra_cho_ffmpeg() -> None:
    global _GATE_DANG
    with _GATE_COND:
        _GATE_DANG = max(0, _GATE_DANG - 1)
        # notify_all (không phải notify): có ƯU TIÊN nên người được đánh thức
        # ngẫu nhiên có thể KHÔNG phải người xếp đầu hàng -> chỗ trống nằm không.
        _GATE_COND.notify_all()


def dang_chay_ffmpeg() -> int:
    """Số lệnh ffmpeg đang giữ chỗ (cho test/đo)."""
    with _GATE_COND:
        return _GATE_DANG


def dang_doi_ffmpeg() -> int:
    """Số việc đang XẾP HÀNG chờ chỗ (cho test/đo)."""
    with _GATE_COND:
        return len(_GATE_HANG)


def _run(cmd: list[str], on_line: Optional[Callable[[str], None]] = None,
         uu_tien: int = UT_XUAT) -> int:
    """Chạy 1 lệnh ffmpeg QUA CỬA CHỜ (xem `so_ffmpeg_song_song`).

    ĐỪNG spawn ffmpeg bằng subprocess trực tiếp ở chỗ khác: đi vòng qua cửa này
    là quay lại đúng cảnh 592 luồng / 24,7x số nhân.
    """
    _raise_if_job_canceled()   # job đã bị Hủy -> KHÔNG spawn thêm ffmpeg
    co_cho = _xin_cho_ffmpeg(uu_tien)
    try:
        return _run_khong_cho(cmd, on_line)
    finally:
        if co_cho:
            _tra_cho_ffmpeg()


def _run_khong_cho(cmd: list[str],
                   on_line: Optional[Callable[[str], None]] = None) -> int:
    """Thân cũ của `_run` — KHÔNG qua cửa chờ. Đừng gọi trực tiếp."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_CREATE_NO_WINDOW | _IDLE_PRIORITY,
    )
    # register_proc: vào _ACTIVE_PROCS (dọn khi tắt app) + gắn vào JOB đang chạy
    # (nút Hủy job kill NGAY tiến trình này thay vì đợi nó chạy xong).
    register_proc(proc)
    try:
        # đóng race: bấm Hủy đúng lúc vừa spawn (trước khi register xong)
        _raise_if_job_canceled()
        for line in proc.stdout:  # type: ignore[union-attr]
            if on_line:
                on_line(line.rstrip())
        proc.wait()
        # Bị Hủy (cancel đã kill proc) -> ném CanceledError thay vì trả mã lỗi:
        # nếu trả mã lỗi, _run_with_fallback sẽ tưởng NVENC hỏng (ghi cache sai)
        # rồi spawn libx264 encode LẠI từ đầu -> hủy còn lâu hơn.
        _raise_if_job_canceled()
        return proc.returncode
    finally:
        # Thoát bất thường (on_line ném CanceledError khi bấm Hủy, lỗi khác...)
        # -> PHẢI giết ffmpeg, nếu không nó chạy hết clip ăn CPU/GPU và giữ file
        # output; đã unregister thì đóng app cũng không dọn được nữa.
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        unregister_proc(proc)


@dataclass
class MediaInfo:
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    has_audio: bool = False


def probe(path: str | Path) -> MediaInfo:
    """Đọc metadata video bằng ffprobe."""
    cmd = [
        settings.FFPROBE_PATH, "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    info = MediaInfo()
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", creationflags=_CREATE_NO_WINDOW, timeout=60,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return info        # thiếu ffprobe / file hỏng -> trả rỗng, không crash
    try:
        data = json.loads(out.stdout or "{}")
    except ValueError:
        return info
    info.duration = float(data.get("format", {}).get("duration", 0) or 0)
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and info.width == 0:
            info.width = int(s.get("width", 0) or 0)
            info.height = int(s.get("height", 0) or 0)
            fr = s.get("avg_frame_rate", "0/1")
            try:
                num, den = fr.split("/")
                info.fps = round(float(num) / float(den), 3) if float(den) else 0.0
            except (ValueError, ZeroDivisionError):
                info.fps = 0.0
        elif s.get("codec_type") == "audio":
            info.has_audio = True
    return info


def detect_encoder() -> str:
    """
    Trả về tên video encoder ffmpeg dùng được.
    settings.VIDEO_ENCODER: auto|nvenc|libx264.
    'auto' => thử NVENC, không có thì libx264.
    """
    want = settings.VIDEO_ENCODER
    if want == "libx264":
        return "libx264"
    if want == "nvenc":
        return "h264_nvenc"  # user ép dùng, không test
    # auto: TEST NVENC chạy thật (nhiều máy liệt kê có nhưng encode lỗi)
    global _ENCODER_CACHE
    if _ENCODER_CACHE is None:
        _ENCODER_CACHE = "h264_nvenc" if _nvenc_works_cached() else "libx264"
    return _ENCODER_CACHE


_ENCODER_CACHE: Optional[str] = None
_NVENC_CACHE_DAYS = 7
# LÝ DO NVENC không dùng được (chuỗi tiếng Việt cho UI); '' = dùng được/chưa rõ.
# Quan trọng nhất: driver NVIDIA CŨ hơn bản ffmpeg yêu cầu (vd ffmpeg 2025 đòi
# driver >=570) — máy CÓ GPU tốt mà xuất vẫn chậm bằng CPU, user không hề biết.
_NVENC_NOTE: str = ""


def nvenc_note() -> str:
    """Lý do NVENC không dùng được (cho UI hiện gợi ý). Chỉ có nghĩa SAU khi
    detect_encoder() đã chạy (app gọi lúc khởi động qua resource_manager)."""
    return _NVENC_NOTE


def _classify_nvenc_error(log: str) -> str:
    """Đọc stderr ffmpeg khi test/encode NVENC lỗi -> câu giải thích + cách sửa."""
    low = (log or "").lower()
    if ("minimum required nvidia driver" in low
            or "required nvenc api version" in low):
        # bắt kèm số driver yêu cầu nếu có (vd "570.0 or newer")
        import re as _re
        m = _re.search(r"driver for nvenc is\s*([0-9.]+)", low)
        need = m.group(1) if m else "570"
        return (f"Driver NVIDIA đang cũ — cần bản ≥ {need} để encode GPU. "
                "Cập nhật driver (NVIDIA App/GeForce) rồi mở lại app: xuất "
                "video sẽ nhanh gấp nhiều lần và máy không còn nặng.")
    if "cannot load nvcuda" in low or "no nvidia" in low:
        return ""      # không có GPU NVIDIA -> không cần note (CPU là đúng)
    if low.strip():
        return ("GPU NVIDIA có nhưng NVENC lỗi khi encode — app tự dùng CPU. "
                "Thử cập nhật driver NVIDIA nếu muốn xuất nhanh bằng GPU.")
    return ""


# Chữ ký lỗi TẦM MÔI TRƯỜNG (driver/thư viện NVIDIA) — mọi input đều hỏng,
# đáng ghi cache file. Khác lỗi encoder MỨC INPUT (1 video dị) và khác hẳn
# lỗi KHÔNG liên quan NVENC (filter graph, file nguồn...).
_NVENC_ENV_SIGNS = (
    "minimum required nvidia driver", "required nvenc api version",
    "cannot load nvcuda", "failed loading nvenc",
    "no nvenc capable devices", "no capable devices",
    "cuda_error", "cuda error", "no nvidia devices",
)


def _looks_nvenc_env_failure(log: str) -> bool:
    """Lỗi driver/thư viện NVIDIA (dính cả máy) -> đáng ghi cache file."""
    low = (log or "").lower()
    return any(s in low for s in _NVENC_ENV_SIGNS)


def _looks_nvenc_failure(log: str) -> bool:
    """Log ffmpeg có THẬT SỰ chỉ ra lỗi từ NVENC không?

    Nhận diện bằng dòng log CỦA CHÍNH component encoder `[h264_nvenc @ 0x..]`
    (bracket đứng NGAY trước tên — dòng `[vost#0:0/h264_nvenc @..]` là task
    wrapper, báo lỗi CHUNG cho cả lỗi filter phía trước, KHÔNG tính) hoặc các
    chữ ký driver/thư viện. Lỗi filter graph/input ('Error reinitializing
    filters', 'Invalid argument' từ [fc#/[Parsed_...) -> False."""
    low = (log or "").lower()
    return "[h264_nvenc @" in low or _looks_nvenc_env_failure(low)


_DRIVER_VER_CACHE: str | None = None


def _gpu_driver_version() -> str:
    """Phiên bản driver NVIDIA (vd '610.62') qua nvidia-smi; '' nếu không có
    GPU/nvidia-smi. Cache theo tiến trình (gọi 1 lần lúc mở app)."""
    global _DRIVER_VER_CACHE
    if _DRIVER_VER_CACHE is not None:
        return _DRIVER_VER_CACHE
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8,
            creationflags=(0x0800_0000 if os.name == "nt" else 0))
        _DRIVER_VER_CACHE = (r.stdout or "").strip().splitlines()[0].strip() \
            if r.returncode == 0 and (r.stdout or "").strip() else ""
    except Exception:  # noqa: BLE001 - không có nvidia-smi/treo -> coi như ''
        _DRIVER_VER_CACHE = ""
    return _DRIVER_VER_CACHE


def _nvenc_cache_key() -> str:
    """Nhận diện MÔI TRƯỜNG encode: binary ffmpeg (path+mtime+size) + PHIÊN
    BẢN DRIVER NVIDIA + PHIÊN BẢN APP. User cập nhật driver (ffmpeg không
    đổi) -> key đổi -> test lại NVENC NGAY, không phải chờ hết hạn cache 7
    ngày (lỗi thật: user lên driver 610 nhưng app vẫn nhớ 'NVENC hỏng' từ
    thời driver 560). Phiên bản app trong key: máy từng bị ghi OAN 'NVENC
    hỏng' (bug đổ lỗi nhầm bản cũ) được test lại NGAY lần đầu mở bản mới."""
    import shutil
    p = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH
    drv = _gpu_driver_version()
    try:
        from app.version import __version__ as _appv
    except Exception:  # noqa: BLE001
        _appv = ""
    try:
        st = os.stat(p)
        return f"{p}|{int(st.st_mtime)}|{st.st_size}|drv={drv}|app={_appv}"
    except OSError:
        return f"{p}|drv={drv}|app={_appv}"


def _nvenc_works_cached() -> bool:
    """_nvenc_works() nhưng CACHE kết quả ra file 7 ngày.

    Test NVENC (encode thử 1 frame) chạy ĐỒNG BỘ lúc mở app (import
    resource_manager) — máy có GPU thường tốn ~0.5-2s, treo tới 20s nếu driver
    lỗi -> app lâu hiện. Cache theo binary ffmpeg; hết 7 ngày (driver có thể
    đã đổi) thì test lại. VIDEO_ENCODER=nvenc/libx264 (ép tay) KHÔNG đi qua
    đây (detect_encoder trả thẳng) nên đổi setting không cần xóa cache."""
    import time
    from config import DATA_DIR
    global _NVENC_NOTE
    cf = Path(DATA_DIR) / "_cache" / "nvenc_check.json"
    key = _nvenc_cache_key()
    try:
        d = json.loads(cf.read_text(encoding="utf-8"))
        # ok=True tin 7 ngày; ok=False CHỈ TIN 1 NGÀY — bản cũ từng ghi oan
        # 'NVENC hỏng' khi export lỗi vì lý do khác -> máy dính cache đó bị
        # CPU-encode cả tuần. Giờ hôm sau mở app là test lại, GPU tự hồi.
        ttl_days = _NVENC_CACHE_DAYS if d.get("ok") else 1
        if (d.get("ffmpeg") == key and isinstance(d.get("ok"), bool)
                and 0 <= time.time() - float(d.get("ts", 0))
                < ttl_days * 86400):
            _NVENC_NOTE = str(d.get("note") or "")
            return d["ok"]
    except (OSError, ValueError, TypeError):
        pass
    ok, note = _nvenc_works()
    _NVENC_NOTE = note
    _save_nvenc_cache(ok, note)
    return ok


def _save_nvenc_cache(ok: bool, note: str = "") -> None:
    import time
    from config import DATA_DIR
    cf = Path(DATA_DIR) / "_cache" / "nvenc_check.json"
    try:
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps({"ok": ok, "ts": time.time(),
                                  "ffmpeg": _nvenc_cache_key(),
                                  "note": note}),
                      encoding="utf-8")
    except OSError:
        pass


def _nvenc_works() -> tuple[bool, str]:
    """Encode thử 1 frame bằng h264_nvenc. Trả (ok, note): ok=True nếu chạy
    được thật; note = lý do dễ hiểu khi KHÔNG chạy được (driver cũ...)."""
    cmd = [
        settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error",
        # 256x256: NVENC có KÍCH THƯỚC TỐI THIỂU (~145px tùy đời card/driver)
        # — 128x128 từng FAIL OAN "Frame Dimension less than minimum" trên
        # driver 610 + RTX 3060 dù NVENC hoàn toàn khỏe ở cỡ thật.
        "-f", "lavfi", "-i", "testsrc=size=256x256:rate=1",
        # testsrc mặc định rgb24 -> vài bản ffmpeg từ chối đưa thẳng vào NVENC;
        # ép yuv420p để test không FAIL OAN (false negative) vì pixel format.
        "-frames:v", "1", "-pix_fmt", "yuv420p",
        "-c:v", "h264_nvenc", "-f", "null", "-",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=20)
        if r.returncode == 0:
            return True, ""
        return False, _classify_nvenc_error(r.stderr or r.stdout or "")
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False, ""


def ffmpeg_available() -> bool:
    try:
        subprocess.run(
            [settings.FFMPEG_PATH, "-version"],
            capture_output=True, creationflags=_CREATE_NO_WINDOW, timeout=15,
        )
        return True
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def extract_frame(src: str | Path, t: float, dst: str | Path,
                  width: int = 360) -> bool:
    """Trích 1 khung hình tại giây t -> ảnh (cho khung xem trước). True nếu OK.

    Hay được gọi từ UI thread (mở editor) -> PHẢI có timeout: file trên ổ
    mạng/OneDrive đơ có thể làm ffmpeg treo -> treo cả app.
    """
    cmd = [
        settings.FFMPEG_PATH, "-y", "-ss", f"{max(0, t):.3f}", "-i", str(src),
        "-frames:v", "1", "-vf", f"scale={width}:-1", "-q:v", "3", str(dst),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30,
                           creationflags=_CREATE_NO_WINDOW,
                           stdin=subprocess.DEVNULL)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def extract_audio_wav(src: str | Path, dst: str | Path, sr: int = 16000) -> bool:
    """Tách audio mono 16k cho whisper/librosa. Trả về True nếu thành công."""
    return extract_audio_wav_why(src, dst, sr)[0]


def extract_audio_wav_why(src: str | Path, dst: str | Path,
                          sr: int = 16000) -> tuple[bool, str]:
    """Như `extract_audio_wav` nhưng TRẢ KÈM LÝ DO khi thất bại.

    VÌ SAO CẦN (lỗi thật anh Hùng gặp 2026-07-25): app chỉ báo "Tách audio thất
    bại (ffmpeg?)" — đổ lỗi cho ffmpeg — trong khi nguyên nhân thật là video gốc
    đã bị chuyển vào `_Loi` sau lần cắt lỗi trước nên KHÔNG CÒN ở đường dẫn cũ.
    Anh đi tìm sai hướng (tưởng video hỏng / quá dài), mất cả buổi. Kèm được
    dòng cuối của ffmpeg là biết ngay hỏng ở đâu.
    """
    p = Path(src)
    if not p.exists():
        return (False, f"KHÔNG TÌM THẤY video gốc: {src}")
    try:
        if p.stat().st_size == 0:
            return (False, f"video gốc RỖNG 0 byte: {src}")
    except OSError:
        pass
    tail: list[str] = []

    def keep(line: str) -> None:
        s = (line or "").strip()
        if s:
            tail.append(s)
            if len(tail) > 6:          # giữ vài dòng cuối là đủ chẩn đoán
                tail.pop(0)
    # SIẾT LUỒNG GIẢI MÃ (`-threads` PHẢI đứng TRƯỚC `-i`, sau `-i` là ENCODE).
    # LỖI THẬT đo được khi TỔNG RÀ SOÁT 08/08/2026 (`_ra_luong_toan_may.py` soi
    # MỌI ffmpeg trên máy trong lúc dây chuyền chạy): lệnh NÀY **một mình ăn
    # 132 luồng = 5,50× số nhân** — nhiều hơn cả lệnh XUẤT (81) — và tạo đỉnh
    # lớn nhất của cả lượt (156 luồng khi chạy cùng lệnh đo). Nó đứng NGOÀI cửa
    # chờ ffmpeg và KHÔNG dùng `_global_enc_opts()` nên chưa từng bị siết.
    # Việc thật của nó rất nhẹ (giải mã rồi ghi PCM 16 kHz MỘT kênh — không
    # encode, không filter) nên mức 4 là quá đủ. Cùng công thức với
    # `chon_doan._num_luong()` để chỉ có một quy tắc về luồng lệnh-ngoài-cửa-chờ.
    _dt = str(min(4, max(1, (os.cpu_count() or 4) // 2)))
    cmd = [
        settings.FFMPEG_PATH, "-y", "-threads", _dt, "-i", str(src),
        "-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(dst),
    ]
    # ƯU TIÊN THẤP: tách audio chạy NỀN, còn XUẤT là việc anh Hùng đang nhìn
    # thanh %. Có van chống đói (`_DOI_TOI_DA`) nên lệnh này không bao giờ bị
    # bỏ quên — quá 20s chờ là được nâng ngang hàng với xuất.
    rc = _run(cmd, keep, uu_tien=UT_PHAN_TICH)
    if rc == 0:
        return (True, "")
    why = " | ".join(tail[-3:]) or f"ffmpeg trả mã {rc}"
    low = why.lower()
    if "no space" in low or "disk full" in low:
        why = "Ổ ĐĨA HẾT CHỖ khi ghi audio tạm — dọn ổ đĩa rồi cắt lại."
    elif "does not contain any stream" in low:
        why = f"Video KHÔNG CÓ TIẾNG nên không tách được audio. ({why})"
    return (False, why)


# ---- NGÂN SÁCH CPU TOÀN CỤC cho encode ----
# Tổng luồng encode của TẤT CẢ ffmpeg đang chạy <= ~60% số nhân logic và LUÔN
# chừa >=2 nhân cho hệ thống -> khi app xuất video, máy vẫn dùng bình thường.

def _encode_budget() -> int:
    """Tổng số luồng encode cho phép (mọi job cộng lại)."""
    cores = os.cpu_count() or 4
    return max(1, min(cores - 2, (cores * 3) // 5))


def _max_encode_jobs() -> int:
    """Số job encode có thể chạy SONG SONG lúc này (để chia ngân sách luồng).
    Tiết kiệm máy -> luôn 1. Hiệu năng tối đa -> theo 'Luồng cắt' của pool."""
    if settings.ECO_MODE:
        return 1
    try:
        from app.queue.worker import active_pool
        pool = active_pool()
        if pool is not None:
            return max(1, int(pool.max_cpu))
    except Exception:  # noqa: BLE001 - không có pool (subprocess/test) -> mặc định
        pass
    return 2


def encode_threads() -> int:
    """Số luồng -threads cho MỖI ffmpeg encode = ngân_sách // số job song song.
    Tiết kiệm máy: chỉ 1 job nhưng cũng chỉ dùng ~1/2 ngân sách -> nhẹ hẳn."""
    budget = _encode_budget()
    if settings.ECO_MODE:
        return max(1, budget // 2)
    return max(1, budget // _max_encode_jobs())


def decode_threads() -> int:
    """Số luồng GIẢI MÃ — `-threads N` đặt **TRƯỚC `-i`** (đặt SAU `-i` thì
    ffmpeg hiểu là luồng ENCODE; sai chỗ là im lặng, không báo lỗi).

    CHỖ HỞ ĐÃ BỊT: trước đây KHÔNG chỗ nào trong app đặt `-threads` trước `-i`
    -> giải mã ăn mặc định `-threads 0` ≈ 17 luồng/lệnh, dư 12-14 luồng/lệnh.

    VÌ SAO CHỌN 4 (đo thật pha 1 `_build_seg` — bước DUY NHẤT không có filter
    nên GIẢI-MÃ-BOUND, tức chỗ duy nhất siết luồng CÓ THỂ làm chậm thật, và
    đúng là chỗ lần thử trước thất bại; video Nhật thật, lặp 3 lấy trung vị,
    máy 24 nhân rảnh 6,6%):
        nvenc  không giới hạn : 0,76s · 1,89 CPU-giây · 61 luồng
        nvenc  + giải mã 4    : 0,75s · 1,67 CPU-giây · 49 luồng  (wall 0,99x)
        nvenc  + giải mã 2    : 0,78s · 1,50 CPU-giây · 47 luồng  (wall 1,03x)
        nvenc  + giải mã 1    : 0,99s · 1,17 CPU-giây · 45 luồng  (wall 1,30x)
        libx264 hiện tại      : 0,78s · 4,97 CPU-giây · 48 luồng
        libx264 giải mã+enc 4 : 0,84s · 4,34 CPU-giây · 27 luồng  (wall 1,08x)
        libx264 giải mã+enc 2 : 1,16s · 3,23 CPU-giây · 19 luồng  (wall 1,49x)
        libx264 giải mã+enc 1 : 1,99s · 2,64 CPU-giây · 12 luồng  (wall 2,55x)
    -> 4 là mức cuối cùng còn MIỄN PHÍ về thời gian. **1 thì chậm THẬT** (nvenc
    +30%, libx264 +155%) — đừng hạ xuống 1 dù thấy cột luồng đẹp hơn.

    ĐÍNH CHÍNH kết luận cũ *"chặn luồng làm chậm 3,4 lần (61,2s -> 208,3s)"*:
    NHIỄU, KHÔNG THẬT. Mốc 61,2s đo lúc app chạy 96,7% CPU; đo lại đúng cấu
    hình đó trên máy rảnh ra 7,04s (phồng ~9 lần).
    """
    cores = os.cpu_count() or 4
    return max(1, min(2 if settings.ECO_MODE else 4, cores))


def _enc_args(encoder: str, quality: str = "high") -> list[str]:
    """Tham số encode theo encoder + mức chất lượng."""
    if encoder == "h264_nvenc":
        cq = "19" if quality == "high" else "23"
        # -pix_fmt yuv420p: nguồn 10-bit/4:4:4 (video tải chất lượng cao) sẽ làm
        # NVENC từ chối -> rơi oan về libx264 encode LẠI từ đầu; ép 420p (chuẩn
        # phát hành shorts) để NVENC ăn được mọi nguồn.
        # `-threads` trên nhánh nvenc: TRƯỚC ĐÂY KHÔNG CÓ NÚM NÀO. Đo pha 2
        # (concat+blur+overlay+đốt .ass): thêm `-threads 4` hạ 58 -> 46 luồng,
        # wall 1,00x, và log ffmpeg VẪN ghi `h264_nvenc` -> KHÔNG rớt về CPU
        # (đúng điều lần thử trước nghi mà không ai ghi log lại để biết).
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", cq,
                "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-threads", str(encode_threads())]
    # 'veryfast' nhanh hơn 'medium' nhiều lần, chất lượng vẫn tốt cho clip ngắn
    # -> máy yếu (không GPU) xuất nhanh. crf 20 = nét, file gọn.
    crf = "20" if quality == "high" else "23"
    # ★ `-pix_fmt yuv420p` + `-profile:v high` LÀ BẮT BUỘC Ở CẢ HAI NHÁNH.
    #
    # LỖI THẬT (anh Hùng 18/08/2026, ảnh trình phát Windows): *"khi phân tích
    # cắt các part cứ báo lỗi, video bị trắng"* — `We can't open ... It uses
    # unsupported encoding settings. 0x80004005`.
    #
    # Nhánh này TRƯỚC ĐÂY KHÔNG CÓ `-pix_fmt`, nên x264 lấy pix_fmt THEO ĐẦU RA
    # CỦA FILTER GRAPH, mà graph lại lấy theo NGUỒN:
    #   nguồn yuv420p 8-bit  -> ra yuv420p       -> High      -> mở được
    #   nguồn 10-bit (VP9 P2 / AV1 HDR, yt-dlp tải bestvideo là gặp)
    #                        -> ra yuv420p10le   -> **High 10**
    #   nguồn 4:4:4          -> ra yuv444p       -> **High 4:4:4 Predictive**
    # Trình phát dựng sẵn của Windows KHÔNG giải mã được High 10 / High 4:4:4
    # -> đúng lời lỗi 0x80004005 **và** đúng triệu chứng KHUNG TRẮNG (nó dựng
    # được khung nhưng không giải nổi dữ liệu màu). ffmpeg vẫn **mã thoát 0**,
    # đủ khung, đủ `moov` — nên KHÔNG một cổng nào cũ bắt được.
    #
    # VÌ SAO CHỈ HỎNG THỈNH THOẢNG: nhánh nvenc CÓ `-pix_fmt` sẵn, nên chỉ
    # những lượt **LÙI VỀ libx264** mới ra file hỏng (`_run_with_fallback` lùi
    # khi NVENC lỗi — hết session NVENC, driver, hoặc máy nhân viên không GPU).
    # Cùng một video, Part này mở được Part kia không = đúng ảnh anh Hùng gửi.
    #
    # Đây là ANH EM của lỗi đã vá ở `_enc_mezz` (cổng 42) — hôm đó vá đúng MỘT
    # hàm, còn `_enc_args` (hàm sinh ra FILE THÀNH PHẨM) thì bị bỏ sót.
    # GIỚI HẠN thread mỗi ffmpeg theo NGÂN SÁCH TOÀN CỤC (xem encode_threads):
    # mặc định libx264 ăn HẾT luồng CPU -> 2-3 job song song là máy đơ 100%.
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
            "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-threads", str(encode_threads())]


def khung_chan(out_w: int, out_h: int) -> tuple[int, int]:
    """Ép KÍCH THƯỚC KHUNG về SỐ CHẴN (h264 4:2:0 đòi chẵn cả hai chiều).

    Chiều LẺ thì libx264 ném *"width not divisible by 2"* và NVENC ra khung
    méo/hỏng — cả hai đều là mất clip. Phép nội suy bên trong (`reframe_chain`,
    `scale=...:-2`) đã chẵn sẵn, nhưng `out_w`/`out_h` đi từ **payload job**
    (`m1._export_clip_impl` đọc `payload.get("out_w")`) nên một mẫu cũ / một
    lối gọi mới truyền số lẻ là xuống thẳng ffmpeg không ai chặn.

    Làm TRÒN XUỐNG (không lên) để khung không bao giờ vượt kích thước user đặt;
    sàn 2 để không ra 0.
    """
    return (max(2, int(out_w) // 2 * 2), max(2, int(out_h) // 2 * 2))


def _global_enc_opts() -> list[str]:
    """Tùy chọn TOÀN CỤC đặt ngay sau 'ffmpeg -y' và **TRƯỚC MỌI `-i`**.

    3 núm, mỗi núm bịt 1 chỗ hở khác nhau:
      - `-filter_complex_threads`: luồng của filter graph (đã có từ trước).
      - `-filter_threads`: luồng của filter graph ĐƠN (`-vf`/`-af`). CHỖ HỞ:
        trước đây thiếu hẳn núm này.
      - `-threads` (vì nằm TRƯỚC `-i` nên ffmpeg hiểu là luồng GIẢI MÃ):
        CHỖ HỞ NẶNG NHẤT — không chỗ nào trong app đặt nó, giải mã ăn mặc định
        `-threads 0` ≈ 17 luồng/lệnh. Xem `decode_threads()` để biết vì sao 4.

    THỨ TỰ QUAN TRỌNG: hàm này PHẢI được nối vào cmd TRƯỚC các `-i`. Ai đổi chỗ
    thành sau `-i` là biến `-threads` thành núm ENCODE (im lặng, không lỗi).
    """
    return ["-filter_complex_threads", str(encode_threads()),
            "-filter_threads", str(encode_threads()),
            "-threads", str(decode_threads())]


# Font hỗ trợ (tên hiển thị -> file trong thư mục Fonts của Windows)
FONTS = {
    "Arial": "arial.ttf", "Arial đậm": "arialbd.ttf", "Tahoma": "tahoma.ttf",
    "Times": "times.ttf", "Impact": "impact.ttf", "Verdana": "verdana.ttf",
}


def _font_file(name: str = "Arial") -> str:
    """Trả đường dẫn font đã escape cho ffmpeg (fallback arial).
    Dùng %WINDIR%\\Fonts (không cứng ổ C:) để chạy trên mọi máy Windows."""
    import os
    win = os.environ.get("WINDIR", r"C:\Windows")
    fonts_dir = os.path.join(win, "Fonts")
    fname = FONTS.get(name, "arial.ttf")
    for f in (fname, "arial.ttf", "segoeui.ttf", "tahoma.ttf"):
        p = os.path.join(fonts_dir, f)
        if os.path.exists(p):
            return p.replace("\\", "/").replace(":", r"\:")
    return "arial.ttf"


_TEXT_Y = {"top": "h*0.07", "center": "(h-text_h)/2", "bottom": "h*0.84"}


def _esc_drawtext(text: str) -> str:
    """Escape text cho drawtext (tránh vỡ filtergraph)."""
    text = text.replace("\\", r"\\").replace(":", r"\:").replace("%", r"\%")
    text = text.replace("'", "’").replace("\n", " ")  # né dấu nháy
    return text


def _hex_to_ff(color: str) -> str:
    """#RRGGBB -> 0xRRGGBB cho drawtext; tên màu giữ nguyên."""
    c = (color or "white").strip()
    if c.startswith("#") and len(c) == 7:
        return "0x" + c[1:].upper()
    return c


def _drawtext_filter(o: dict, out_h: int) -> str:
    """
    Vẽ 1 lớp chữ. o nhận:
      text (bắt buộc), nx/ny (tâm chữ 0..1) HOẶC position(top/center/bottom),
      size (cỡ theo % chiều cao, vd 0.07), color (#RRGGBB), font (tên).
    """
    fontsize = max(18, int(out_h * float(o.get("size", 0.06))))
    border = max(2, fontsize // 16)
    if "nx" in o and "ny" in o:
        x = f"w*{float(o['nx']):.4f}-text_w/2"
        y = f"h*{float(o['ny']):.4f}-text_h/2"
    else:
        x = "(w-text_w)/2"
        y = _TEXT_Y.get(o.get("position", "bottom"), _TEXT_Y["bottom"])
    return (
        f"drawtext=fontfile='{_font_file(o.get('font', 'Arial'))}':"
        f"text='{_esc_drawtext(o['text'])}':"
        f"fontcolor={_hex_to_ff(o.get('color', 'white'))}:fontsize={fontsize}:"
        f"borderw={border}:bordercolor=black@0.9:x={x}:y={y}"
    )


def _text_chain(text_overlays: list, out_h: int, lin: str, lout: str) -> str:
    """Nối nhiều lớp drawtext: [lin]drawtext,drawtext...[lout]."""
    valid = [o for o in (text_overlays or []) if o.get("text")]
    if not valid:
        return f"[{lin}]null[{lout}]"
    chain = ",".join(_drawtext_filter(o, out_h) for o in valid)
    return f"[{lin}]{chain}[{lout}]"


# Các kiểu đặt khung 9:16 (CapCut-style)
REFRAME_MODES = ("face", "center", "fit_blur")
REFRAME_LABELS = {
    "face": "Bám mặt (auto)",
    "center": "Cắt giữa",
    "fit_blur": "Vừa khung + nền mờ",
}


def reframe_chain(mode: str, cx: float, out_w: int, out_h: int,
                  zoom: float, lin: str, lout: str, p: str,
                  crop_rect: Optional[tuple] = None) -> str:
    """
    Trả về 1 đoạn filtergraph biến [lin] -> [lout] theo kiểu khung 9:16.

    mode:
      manual   -> dùng crop_rect (nx,ny,nw,nh) chuẩn hoá 0..1 do user kéo-thả.
      face/center -> CROP đầy khung (zoom cắt sát chủ thể). zoom>=1 cắt sát hơn.
      fit_blur -> giữ NGUYÊN khung gốc (không cắt mất gì), nền phóng to làm mờ.
    p = hậu tố nhãn (để dùng nhiều lần trong 1 filter_complex không trùng tên).
    """
    if mode == "manual" and crop_rect:
        nx, ny, nw, nh = crop_rect
        return (
            f"[{lin}]crop=w='iw*{nw:.5f}':h='ih*{nh:.5f}':"
            f"x='iw*{nx:.5f}':y='ih*{ny:.5f}',"
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h},unsharp=5:5:0.8:5:5:0.0,setsar=1[{lout}]"
        )
    if mode == "fit_blur":
        return (
            f"[{lin}]split=2[bg{p}][fg{p}];"
            f"[bg{p}]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},boxblur=20:2[bgb{p}];"
            f"[fg{p}]scale={out_w}:-2:flags=lanczos[fgf{p}];"
            f"[bgb{p}][fgf{p}]overlay=(W-w)/2:(H-h)/2,setsar=1[{lout}]"
        )
    cxv = 0.5 if mode == "center" else min(0.85, max(0.15, cx))
    z = max(1.0, float(zoom))
    return (
        f"[{lin}]crop=w='min(ih*9/16,iw)/{z:.4f}':h='ih/{z:.4f}':"
        f"x='(iw-min(ih*9/16,iw)/{z:.4f})*{cxv:.4f}':y='(ih-ih/{z:.4f})/2',"
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={out_w}:{out_h},unsharp=5:5:0.8:5:5:0.0,setsar=1[{lout}]"
    )


# 🎙 RECAP: mức tiếng gốc TRONG khoảng duck (lúc giọng AI đang nói). 0.12 =
# tiếng gốc còn văng vẳng ~12% làm NỀN SỐNG dưới giọng AI (như kênh recap
# thật — video không chết sóng), thay vì câm tuyệt đối (volume=0 cũ). Giọng
# AI vẫn áp đảo rõ: đã loudnorm to hơn gốc +1.5dB, còn nền 0.12 ≈ -18.4dB
# so mức gốc -> chênh ~20dB (>12dB yêu cầu tách bạch lời nói).
_DUCK_LEVEL = 0.12


def _atempo_chain(tempo: float) -> str:
    """Chuỗi atempo cho hệ số bất kỳ, CHIA TẦNG để luôn nằm trong [0.5, 2.0]
    (khoảng an toàn atempo trên MỌI bản ffmpeg, kể cả cũ trên máy khách).
    tempo<1 = chậm lại (giãn), >1 = nhanh lên. Trả 1 filter atempo=... hoặc
    nhiều cái nối bằng dấu phẩy."""
    tempo = max(0.01, float(tempo))
    parts = []
    while tempo < 0.5 - 1e-9:
        parts.append("atempo=0.5")
        tempo /= 0.5
    while tempo > 2.0 + 1e-9:
        parts.append("atempo=2.0")
        tempo /= 2.0
    parts.append(f"atempo={tempo:.4f}")
    return ",".join(parts)


# ---- HIỆU ỨNG TINH TẾ ----
# Bộ tiếng chuyển đoạn TỔNG HỢP thuần bằng ffmpeg (anoisesrc/sine/aevalsrc +
# bandpass/lowpass/highpass + afade + volume + atempo) — KHÔNG cần file kèm nên
# chạy trên MỌI máy khách (bản .exe nhẹ). ~9 LOẠI khác hẳn nhau (không chỉ đổi
# tần số) -> mỗi điểm ghép chọn NGẪU NHIÊN 1 loại, tránh lặp liên tiếp cùng loại
# nên nghe ĐA DẠNG, không nhàm. TẤT CẢ đều NGẮN (~0.15-0.3s) + âm lượng NHỎ
# (~0.2-0.28) -> tinh tế, không lố.
#
# Mỗi loại là 1 hàm build(delay_ms, vol) -> (input_args, filter_branch):
#   input_args = phần "-f lavfi -t <dur> -i <src>" đưa vào lệnh ffmpeg (mỗi loại
#     tự chọn nguồn: nhiễu trắng / sine / xung aevalsrc).
#   filter_branch = chuỗi filter "[{IDX}:a]...[{OUT}]" — IDX/OUT được nơi gọi
#     thay bằng chỉ số input thật + nhãn output. adelay đặt đúng mốc ghép.
# Đặt {IDX}/{OUT} làm placeholder để nơi gọi (export_canvas_clip) không phải
# biết chi tiết từng loại.

def _fx_lavfi(dur: float, src: str) -> str:
    """1 input lavfi ngắn: '-f lavfi -t <dur> -i <src>' (dạng đã nối chuỗi)."""
    return f"-f|lavfi|-t|{dur:.3f}|-i|{src}"


def _fx_whoosh_up(delay_ms: int, vol: float):
    """Whoosh vút LÊN: nhiễu quét bandpass tần số TĂNG (afreqshift giả bằng
    bandpass cố định + fade) — dùng nguồn nhiễu, highpass tăng dần cảm giác lên."""
    dur = 0.26
    return (_fx_lavfi(dur, "anoisesrc=color=white:r=48000"),
            f"[{{IDX}}:a]highpass=f=600,bandpass=f=1500:width_type=h:w=1200,"
            f"afade=t=in:st=0:d={dur*0.7:.3f}:curve=ipar,"
            f"afade=t=out:st={dur*0.8:.3f}:d={dur*0.2:.3f}:curve=tri,"
            f"volume={vol:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_whoosh_down(delay_ms: int, vol: float):
    """Whoosh vút XUỐNG: nhiễu quét cảm giác GIẢM — fade vào nhanh, tắt dài,
    lowpass để nghe trầm dần."""
    dur = 0.28
    return (_fx_lavfi(dur, "anoisesrc=color=white:r=48000"),
            f"[{{IDX}}:a]bandpass=f=1300:width_type=h:w=1000,lowpass=f=2200,"
            f"afade=t=in:st=0:d={dur*0.15:.3f}:curve=exp,"
            f"afade=t=out:st={dur*0.35:.3f}:d={dur*0.65:.3f}:curve=qsin,"
            f"volume={vol:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_swoosh_air(delay_ms: int, vol: float):
    """Swoosh gió nhẹ: nhiễu + bandpass RỘNG (dải rộng nghe như luồng gió)."""
    dur = 0.30
    return (_fx_lavfi(dur, "anoisesrc=color=pink:r=48000"),
            f"[{{IDX}}:a]bandpass=f=1100:width_type=h:w=2000,"
            f"afade=t=in:st=0:d={dur*0.4:.3f}:curve=tri,"
            f"afade=t=out:st={dur*0.5:.3f}:d={dur*0.5:.3f}:curve=tri,"
            f"volume={vol*0.95:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_pop(delay_ms: int, vol: float):
    """Pop: sine ngắn tắt CỰC nhanh (cú 'bụp' gọn)."""
    dur = 0.12
    return (_fx_lavfi(dur, "sine=frequency=440:r=48000"),
            f"[{{IDX}}:a]afade=t=in:st=0:d=0.005:curve=exp,"
            f"afade=t=out:st=0.02:d={dur-0.02:.3f}:curve=exp,"
            f"volume={vol*0.9:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_tick(delay_ms: int, vol: float):
    """Tick/click: xung CỰC ngắn (aevalsrc 1 nhịp) qua highpass -> 'tít' sắc."""
    dur = 0.05
    return (_fx_lavfi(dur, "sine=frequency=2200:r=48000"),
            f"[{{IDX}}:a]highpass=f=1500,"
            f"afade=t=out:st=0.008:d={dur-0.008:.3f}:curve=exp,"
            f"volume={vol*0.8:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_riser(delay_ms: int, vol: float):
    """Riser ngắn: sine sweep LÊN nhẹ (tạo hồi hộp) — aevalsrc quét tần số tăng."""
    dur = 0.30
    # aevalsrc: tần số tăng tuyến tính 300 -> 1500 Hz trong dur giây.
    expr = f"sin(2*PI*t*(300+{1200/dur:.1f}*t))"
    return (_fx_lavfi(dur, f"aevalsrc={expr}:s=48000"),
            f"[{{IDX}}:a]afade=t=in:st=0:d={dur*0.6:.3f}:curve=ipar,"
            f"afade=t=out:st={dur*0.85:.3f}:d={dur*0.15:.3f}:curve=tri,"
            f"volume={vol*0.85:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_boom(delay_ms: int, vol: float):
    """Soft boom/impact: sine THẤP tắt nhanh — RẤT nhẹ (không dội)."""
    dur = 0.22
    return (_fx_lavfi(dur, "sine=frequency=90:r=48000"),
            f"[{{IDX}}:a]lowpass=f=180,"
            f"afade=t=in:st=0:d=0.01:curve=exp,"
            f"afade=t=out:st=0.04:d={dur-0.04:.3f}:curve=qsin,"
            f"volume={vol*0.9:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_ding(delay_ms: int, vol: float):
    """Ding nhẹ: sine CAO tắt dần — âm lượng nhỏ để không lố."""
    dur = 0.28
    return (_fx_lavfi(dur, "sine=frequency=1760:r=48000"),
            f"[{{IDX}}:a]afade=t=in:st=0:d=0.006:curve=exp,"
            f"afade=t=out:st=0.03:d={dur-0.03:.3f}:curve=qsin,"
            f"volume={vol*0.7:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


def _fx_whoosh_mid(delay_ms: int, vol: float):
    """Whoosh trung tính: nhiễu bandpass dải giữa, bán chuông mượt (gốc kinh điển)."""
    dur = 0.24
    return (_fx_lavfi(dur, "anoisesrc=color=white:r=48000"),
            f"[{{IDX}}:a]bandpass=f=1400:width_type=h:w=900,"
            f"afade=t=in:st=0:d={dur*0.3:.3f}:curve=exp,"
            f"afade=t=out:st={dur*0.35:.3f}:d={dur*0.65:.3f}:curve=tri,"
            f"volume={vol:.3f},aresample=48000,adelay={delay_ms}|{delay_ms}[{{OUT}}]")


# Danh sách LOẠI tiếng tổng hợp (mỗi phần tử là 1 hàm build). ~9 loại khác hẳn.
_FX_TYPES = (
    _fx_whoosh_mid, _fx_whoosh_up, _fx_whoosh_down, _fx_swoosh_air,
    _fx_pop, _fx_tick, _fx_riser, _fx_boom, _fx_ding,
)


# Ánh xạ NGỮ CẢNH -> các loại tiếng TỔNG HỢP dùng khi THIẾU thư viện đóng gói
# (bản cũ chưa có app/assets/sfx). Giữ đúng "tính cách" mỗi loại: transition ->
# whoosh/gió; impact -> boom; riser -> riser; reveal -> ding; pop -> pop/tick.
_CAT_SYNTH_IDX = {
    "transition": (0, 1, 2, 3),   # whoosh_mid/up/down/swoosh_air
    "impact": (7,),               # boom
    "riser": (6,),                # riser
    "reveal": (8,),               # ding
    "pop": (4, 5),                # pop / tick
    # Loại CẢM XÚC MỚI (chỉ dùng khi THIẾU thư viện đóng gói — bản .exe cũ):
    # ánh xạ về loại tổng hợp GẦN nhất (không có tiếng tổng hợp riêng cho
    # suspense/comedy/scratch/sad/drumroll -> mượn boom/riser/whoosh/ding).
    "suspense": (7, 6),           # boom trầm / riser -> căng
    "comedy": (4, 8),             # pop / ding -> vui
    "scratch": (1, 2),            # whoosh up/down -> quét nhanh
    "sad": (8,),                  # ding trầm -> buồn
    "drumroll": (6, 7),           # riser / boom -> dồn trước cao trào
}


def _pick_synth_for_category(cat: str, avoid: Optional[int],
                             rng) -> int:
    """Chọn index _FX_TYPES cho category (fallback khi thiếu thư viện), tránh
    lặp `avoid` nếu có lựa chọn khác. Hàm thuần — test được."""
    opts = list(_CAT_SYNTH_IDX.get(cat, _CAT_SYNTH_IDX["transition"]))
    choices = [i for i in opts if i != avoid] or opts
    return rng.choice(choices)


def _fx_synth_branch(type_idx: int, at_sec: float, vol: float, in_idx: int,
                     out_label: str):
    """Sinh (input_args_list, filter_branch) cho 1 loại tiếng tổng hợp tại at_sec.

    input_args_list = list token '-f','lavfi','-t',...,'-i','<src>' để nối vào
    lệnh ffmpeg. filter_branch đã thay {IDX}->in_idx, {OUT}->out_label."""
    delay_ms = max(0, int(round(at_sec * 1000)))
    build = _FX_TYPES[type_idx % len(_FX_TYPES)]
    in_args, branch = build(delay_ms, vol)
    return (in_args.split("|"),
            branch.replace("{IDX}", str(in_idx)).replace("{OUT}", out_label))


# ---- THƯ VIỆN TIẾNG ĐỘNG ĐÓNG GÓI SẴN (app/assets/sfx/<category>/*.wav) ----
# Sinh SẴN bằng tools/gen_sfx.py (thuần ffmpeg, không bản quyền) rồi COMMIT vào
# repo -> máy khách chỉ cập nhật là có, KHÔNG cài/tải gì. Chọn theo NGỮ CẢNH
# điểm nối (transition/impact/riser/reveal/pop) thay vì random bừa. Nếu thư
# viện thiếu (bản cũ chưa có) -> tự lùi về bộ tiếng TỔNG HỢP (_FX_TYPES).

# Danh sách category hợp lệ (khớp thư mục con dưới app/assets/sfx/). 5 loại
# GỐC (transition/impact/riser/reveal/pop) + 5 loại CẢM XÚC (suspense/comedy/
# scratch/sad/drumroll) — AI đạo diễn tự gắn nhãn theo cảm xúc từng đoạn.
SFX_CATEGORIES = ("transition", "impact", "riser", "reveal", "pop",
                  "suspense", "comedy", "scratch", "sad", "drumroll")

# ĐÃ BỎ DÙNG 08/08/2026 — GIỮ LẠI LÀM MỐC ĐỐI CHỨNG, ĐỪNG DÙNG LẠI.
# Âm lượng trộn theo LOẠI: hệ số TUYỆT ĐỐI nhân thẳng vào file. Sai ở chỗ nó
# không biết file to hay nhỏ, mà 184 file trong kho trải **26,5 dB** mức nghe
# được (-3,3 .. -29,8 dB). Đo trên clip thật: tiếng ở điểm nối chỉ nhô hơn nền
# **+0,7 dB** = anh Hùng "không nghe được gì cả". Thay bằng `tinh_gain_sfx`
# (chuẩn hoá theo mean của CHÍNH file + nền của CHÍNH clip) + `_SFX_CAT_DB`.
_SFX_CAT_VOL_CU = {
    "transition": 0.28, "impact": 0.42, "riser": 0.38,
    "reveal": 0.24, "pop": 0.30,
    "suspense": 0.20, "comedy": 0.34, "scratch": 0.40,
    "sad": 0.22, "drumroll": 0.40,
}


def _assets_sfx_dir() -> Path:
    """Thư mục thư viện SFX đóng gói. Dùng ROOT_DIR (config): bản dev trỏ vào
    mã nguồn, bản .exe trỏ vào sys._MEIPASS -> load được cả 2 môi trường."""
    from config import ROOT_DIR
    return Path(ROOT_DIR) / "app" / "assets" / "sfx"


_SFX_LIB_CACHE: Optional[dict] = None
# Loại + file SFX ĐÃ chọn tại mỗi điểm nối trong lần export_canvas_clip gần nhất
# (đường thư viện/tổng hợp — KHÔNG gồm đường thư mục user). Dùng cho test/log
# kiểm ngữ cảnh chọn đúng. list[(category, filename_or_synth)].
_SFX_LAST_PICK: list = []
#: Tiếng động đã dùng GẦN ĐÂY (xuyên các lượt xuất). LỖI THẬT từ log máy anh
#: Hùng 06/08/2026: Part 1 và Part 2 của CÙNG video đều ra
#: `reveal/k_interfacesounds_confirmation_003.opus` — vì chống-lặp cũ chỉ nhớ
#: TRONG MỘT lượt gọi, mỗi Part là 1 lượt riêng nên bốc lại từ đầu. Kho 184 file
#: mà nghe mãi 1 tiếng. Nay nhớ N file gần nhất theo TỪNG NHÓM.
_SFX_GAN_DAY: dict = {}
_SFX_NHO = 6


def _sfx_library() -> dict:
    """{category: [đường_dẫn_wav,...]} từ thư viện đóng gói, CACHE 1 lần.
    Thiếu thư mục/category -> danh sách rỗng cho category đó (caller tự lùi
    tổng hợp). KHÔNG probe từng file ở đây (thư viện tự sinh -> tin cậy; probe
    27 file mỗi lần export sẽ chậm)."""
    global _SFX_LIB_CACHE
    if _SFX_LIB_CACHE is not None:
        return _SFX_LIB_CACHE
    base = _assets_sfx_dir()
    lib: dict = {}
    for cat in SFX_CATEGORIES:
        d = base / cat
        try:
            # NHẬN CẢ ĐỊNH DẠNG NÉN: kho tải về (CC0) lưu Opus 32k mono —
            # đo 05/08/2026: 1,7 KB/file so với 37,2 KB/file của WAV (nhẹ 21
            # lần) nên mở kho 4-5 lần mà bản cài vẫn NHỎ HƠN. Chỉ tìm .wav là
            # tải kho về xong app KHÔNG THẤY file nào (lỗi im lặng).
            files = sorted(str(p) for p in d.iterdir()
                           if p.is_file() and p.suffix.lower() in
                           (".wav", ".opus", ".ogg", ".mp3", ".m4a"))
        except OSError:
            files = []
        lib[cat] = files
    _SFX_LIB_CACHE = lib
    return lib


def _hop_muc(path: str, dich_db: float, tran_db: float) -> bool:
    """File này có KÊU ĐƯỢC tới mức `dich_db` mà không bị gọt nát không?

    2 điều kiện, cả hai lấy từ bảng đo sẵn nên tra 0 ms:
      * kéo nổi tới đích: `đích − rms50 <= _SFX_GAIN_MAX` (file quá nhỏ thì
        gain bị kẹp -> ra tiếng lí nhí = đúng cái nhấp nháy phải diệt);
      * hệ số đỉnh ngắn hạn vừa chỗ trống tới trần (+ `_SFX_CREST_DU` dB còn
        gọt được): file crest 20 dB chơi ở đích -11 dBFS thì `alimiter` phải
        gọt 11 dB -> mất ~8 dB độ to, nghe hụt hẳn so với file bên cạnh.
    Hàm thuần (chỉ đọc bảng) — test được."""
    _m, mx, st = _muc_sfx3(path)
    if dich_db - st > _SFX_GAIN_MAX:
        return False
    if _moc_dinh_sfx(path) > _SFX_DICH_TOI_DA:
        return False            # vào quá chậm -> không đánh dấu được điểm nhấn
    return (mx - st) <= (tran_db - dich_db) + _SFX_CREST_DU


def _pick_sfx_by_category(cats: list, seed: Optional[int] = None,
                          muc: Optional[tuple] = None,
                          loi_mocs: Optional[list] = None,
                          noi_mocs: Optional[list] = None) -> list:
    """Với MỖI category trong `cats` (theo thứ tự điểm nối), chọn NGẪU NHIÊN 1
    file .wav trong category đó từ thư viện đóng gói, KHÔNG lặp file 2 lần LIÊN
    TIẾP CÙNG loại (đa dạng). Category không có file (thiếu thư viện) -> trả
    None ở vị trí đó (caller lùi bộ tổng hợp). Trả list cùng độ dài `cats`:
    mỗi phần tử là (category, path) hoặc (category, None). Hàm thuần (chỉ đọc
    thư viện đã cache) — test được.

    `muc = (nền, mức_lời, trần_lớp)` (dBFS) -> LỌC TRƯỚC những file không kêu
    nổi tới mức cần cho CHÍNH clip này (`_hop_muc`). Đây là chỗ chữa "nhấp
    nháy": trước đây bốc trúng file quá nhỏ / hệ số đỉnh quá lớn là mốc đó câm,
    chạy 5 lượt cổng 44 thì hỏng 1. VẪN NGẪU NHIÊN trong số file hợp mức (kho
    184 file, lọc xong còn hàng chục) — anh Hùng cần 3 Part không kêu giống
    hệt nhau. Lọc mà rỗng -> lùi về danh sách đầy đủ (thà kêu nhỏ còn hơn câm).

    `loi_mocs` = MỨC LỜI CỤC BỘ tại từng mốc (cùng độ dài `cats`, phần tử None
    = không đo được). Mốc rơi vào lúc ĐANG NÓI có đích CAO HƠN nên bộ lọc phải
    dùng đúng đích của MỐC ĐÓ; lọc theo đích chung của cả clip là nhận cả file
    không thể kêu nổi tới mức mốc đó cần (đúng lỗi "nói át rồi").
    """
    import random as _r
    rng = _r.Random(seed) if seed is not None else _r
    lib = _sfx_library()
    out: list = []
    last_by_cat: dict = {}
    for _i, cat in enumerate(cats):
        cat = cat if cat in SFX_CATEGORIES else "transition"
        files = lib.get(cat) or []
        # ---- LỌC 1: LOA ĐIỆN THOẠI (09/08/2026) — PHẢI ĐI TRƯỚC ----
        # Ưu tiên file KHÔNG mất độ to khi cắt dưới 300 Hz. Nhóm nào cũng trầm
        # (đo: `suspense` 0/12, `sad` 0/10, `drumroll` 0/10 đạt −6 dB) thì
        # KHÔNG lùi về cả danh sách — lấy NỬA ÍT TRẦM NHẤT, vẫn ngẫu nhiên
        # nhưng trong số nghe được nhất hiện có.
        # VÌ SAO TRƯỚC chứ không sau: lọc mức (`_hop_muc`) đòi hệ số đỉnh NHỎ,
        # mà file hệ số đỉnh nhỏ chính là file ĐẶC/TRẦM (boom, drone). Chạy nó
        # trước là **tự lọc RA đúng những file điện thoại không phát được**: đo
        # ngày 09/08 với thứ tự ngược, mốc ĐANG NÓI vẫn còn 3/9 chỉ nhô ở dải
        # <300 Hz (+21,2 và +39,2 dB) mà mọi dải nghe được thì KHÔNG đổi.
        if files:
            _tot = [f for f in files if hut_qua_loa(f) >= _SFX_LOA_HUT_MAX]
            if not _tot and len(files) > 2:
                _tot = sorted(files, key=hut_qua_loa,
                              reverse=True)[:max(2, len(files) // 2)]
            files = _tot or files
        # ---- LỌC 2: MỨC (kêu nổi tới đích, không bị `alimiter` gọt nát) ----
        if files and muc:
            _lm = (loi_mocs[_i] if loi_mocs and _i < len(loi_mocs) else None)
            _d = dich_sfx_dB(cat, muc[0], muc[1], _lm)
            # trần lớp cũng nhích theo đích của MỐC NÀY (khớp `_tran_moc`)
            _tt = (muc[3] if len(muc) > 3 else _SFX_DINH_TRAN_DB)
            _dk = (_SFX_DUCK_DB_NOI
                   if (noi_mocs and _i < len(noi_mocs) and noi_mocs[_i])
                   else 0.0)
            _tr = (muc[2] if _lm is None else
                   max(-20.0, min(_SFX_DINH_TRAN_DB,
                                  _tt - _SFX_LOP_DUOI_TRON + _dk,
                                  dich_sfx_dB("impact", muc[0], muc[1], _lm)
                                  + _SFX_CREST_CHO)))
            _hop = [f for f in files if _hop_muc(f, _d, _tr)]
            # Lọc mức mà rỗng -> KHÔNG lùi về cả kho (lùi là nhận lại file trầm
            # vừa loại). Giữ đúng một ràng buộc BẮT BUỘC: tiếng VÀO CHẬM không
            # đánh dấu được điểm nhấn nào (xem `_moc_dinh_sfx`).
            files = _hop or [f for f in files
                             if _moc_dinh_sfx(f) <= _SFX_DICH_TOI_DA] or files
        # ---- LỌC 3: LỆCH DẢI TẦN, **chỉ ở mốc rơi vào lúc ĐANG NÓI** ----
        # Chỗ có giọng nói thì chỉ lấy những file SÁNG NHẤT NHÓM (nhiều năng
        # lượng trên 4 kHz — xem `do_sang_sfx`): dải đó giọng nói gần như trống
        # nên tiếng động nghe rõ mà KHÔNG phải to thêm. Ưu tiên TƯƠNG ĐỐI (cách
        # file sáng nhất NHÓM `_SFX_SANG_DU` dB) chứ không ngưỡng cứng: nhóm
        # `impact` (hay dùng nhất) không có file nào thật sáng, đặt ngưỡng cứng
        # là nhóm đó rỗng rồi lùi về cả kho = mất trắng bộ lọc.
        # Mốc rơi vào khoảng lặng KHÔNG lọc: không có gì che thì tiếng trầm hay
        # sáng đều nghe rõ, giữ nguyên độ đa dạng của kho.
        if (noi_mocs and _i < len(noi_mocs) and noi_mocs[_i]
                and len(files) > 3):
            _sx = sorted(files, key=do_sang_sfx, reverse=True)
            _nguong = do_sang_sfx(_sx[0]) - _SFX_SANG_DU
            _sang = [f for f in _sx if do_sang_sfx(f) >= _nguong]
            # ÍT NHẤT 3 file để còn ngẫu nhiên được (anh Hùng cần 3 Part không
            # kêu giống hệt nhau) — nhóm nào sáng đều thì lấy đúng 3 sáng nhất.
            files = _sang if len(_sang) >= 3 else _sx[:3]
        if not files:
            out.append((cat, None))
            continue
        prev = last_by_cat.get(cat)
        # loại cả file vừa dùng trong lượt này VÀ N file gần đây của các lượt
        # TRƯỚC (chống trùng tiếng giữa các Part — xem _SFX_GAN_DAY).
        _gd = _SFX_GAN_DAY.get(cat) or []
        choices = [f for f in files if f != prev and f not in _gd]
        if not choices:
            choices = [f for f in files if f != prev] or files
        pick = rng.choice(choices)
        last_by_cat[cat] = pick
        _q = _SFX_GAN_DAY.setdefault(cat, [])
        _q.append(pick)
        del _q[:-_SFX_NHO]
        out.append((cat, pick))
    return out


# ================= TIẾNG ĐỘNG PHẢI **NGHE ĐƯỢC** — ĐO BẰNG dB ===============
# Anh Hùng xem clip thật 08/08/2026: *"âm thanh hiệu ứng hay gì ấy thậm chí còn
# không nghe được gì cả luôn"* · *"có hiệu ứng mà không có âm thanh cứ sao sao"*.
# ĐO RA ĐÚNG 2 LỖI (`_do_tieng.py`, clip THẬT 10 s, 2 đoạn, 2 điểm nhấn):
#
#  (1) ĐIỂM NHẤN HÌNH **KHÔNG HỀ CÓ TIẾNG**. Bật/tắt tiếng động, đỉnh RMS quanh
#      giây 1,20 và 7,20 lệch **0,0 dB / -0,2 dB** = không một mẫu âm nào được
#      trộn. Đúng vậy: bản cũ chỉ chèn tiếng ở ĐIỂM NỐI đoạn (`whoosh_offsets`),
#      mà điểm nối do CẮT GHÉP quyết định, chẳng liên quan gì tới điểm nhấn hình.
#      Clip 1 đoạn thì KHÔNG có tiếng nào, dù có 3 hiệu ứng.
#
#  (2) TIẾNG Ở ĐIỂM NỐI **QUÁ NHỎ**: bật lên chỉ nhô hơn bản tắt **+0,7 dB**
#      (nền clip -23,6 dB, đỉnh -19,3 -> -18,6 dB). Tai người coi ~1 dB là
#      "không đổi gì". Vì sao: bản cũ nhân CỨNG `volume` theo NHÓM (0,24-0,42)
#      trong khi mức NGHE ĐƯỢC (mean_volume) của 184 file trong kho trải
#      **26,5 dB** (-3,3 .. -29,8 dB — xem `tools/do_muc_sfx.py`). Cùng một
#      nhóm, file này nghe rõ, file kia mất hút; và không hệ số cố định nào
#      đúng cho mọi clip vì tiếng GỐC mỗi clip mỗi khác.
#
# CÁCH CHỮA (đo được, không chỉnh mò): tính hệ số theo SỐ ĐO của cả hai đầu —
#   gain_dB = (nền_clip + CHENH + bù_theo_nhóm) - mean_của_file
# rồi kẹp lại để không vỡ tiếng (đỉnh file + gain <= -1 dBFS). CHENH = 8 dB nằm
# giữa dải anh Hùng yêu cầu (6-10 dB). Kèm DUCKING: hạ tiếng gốc ~5 dB đúng lúc
# tiếng động kêu (cửa sổ 0,45 s, vào/ra êm) -> nghe rõ mà KHÔNG đè giọng nói.
# ---------------------------------------------------------------------------
# SỬA 08/08/2026 — LƯỢT KIỂM ĐỘC LẬP ĐO TRÊN CLIP THẬT THÌ BẢN v2.18.0 HỎNG.
# Đo 5 mốc trên clip 16 s (bật tiếng động so bản tắt): **+0,6 / −1,1 / −0,0 /
# −1,6 / +2,4 dB** -> 2/5 mốc còn NHỎ ĐI. Ba nguyên nhân, đều đã đo:
#
#  (1) **NỀN đo bằng `mean_volume` CẢ CLIP.** Với clip ồn (xe tải nổ máy) thì
#      `mean_volume` CHÍNH LÀ mức lời, không phải nền: đo được -15,7 dBFS trong
#      khi nền thật (bpv20 đường bao RMS) là -26 .. -36. "Đích = nền + 8 dB"
#      lấy trên số đó ra một cái đích cao vô lý (-7,7 dBFS mean) mà không lớp
#      tiếng nào với tới -> vế kẹp đỉnh luôn thắng. Nay đo bằng BÁCH PHÂN VỊ
#      của đường bao RMS 50 ms (`_do_muc_clip`): bpv20 = nền · bpv90 = MỨC LỜI.
#
#  (2) **CHUẨN HOÁ THEO `mean_volume` CỦA FILE.** Kho là tiếng NGẮN có đuôi
#      ngân: mean cả file bị đuôi và khoảng lặng kéo xuống, nên cùng một hệ số
#      mà file này kêu to file kia mất hút (= "nhấp nháy", cổng 44 chạy 5 lượt
#      FAIL 1). Nay chuẩn hoá theo **ĐỈNH RMS 50 ms** (mục thứ 3 của
#      `muc_do.json`) — đúng thước tai người nghe và đúng thước cổng đo.
#      Đo lại 8 file trải crest 1,5..16,6 dB: lệch so đích **-0,4..+0,7 dB**
#      (trước: trải hàng chục dB).
#
#  (3) **KẸP ĐỈNH RIÊNG TỪNG LỚP.** "Đỉnh lớp <= -1 dBFS" khoá độ to của mọi
#      file có hệ số đỉnh lớn: kho có crest ngắn hạn trung vị **11,2 dB** nên
#      kẹp đỉnh giữ RMS lớp mãi ở -12 dBFS trở xuống. Nay KHÔNG kẹp gain nữa
#      mà HẠN ĐỈNH bằng `alimiter` (giữ nguyên độ to, chỉ gọt đỉnh) và đặt
#      thêm một `alimiter` **SAU KHI TRỘN** để bảo đảm đỉnh cuối <= -1 dBFS —
#      cần thiết vì nguồn thật đo được đỉnh **0,0 dBFS** (video "Parker and
#      Chester"), tức không kẹp lớp nào cứu được, phải gọt ở chỗ trộn.
#      `alimiter` đặt `latency=1` -> TRỄ ĐÚNG 0,0 ms (đo: không có thì 0,98 ms).
#      Cả hai `alimiter` CHỈ có mặt khi thật sự chèn tiếng động, nên mức "tat"
#      ra lệnh ffmpeg không khác một ký tự nào (bất biến sống còn).
#
#: Tiếng động phải cao hơn NỀN (bpv20) của chính clip bao nhiêu dB.
SFX_TREN_NEN_DB = 8.0
#: SÀN theo MỨC LỜI (bpv90): clip ồn thì "nền + 8" vẫn chìm dưới lời, nên tiếng
#: động phải được kéo lên ít nhất ngang lời + ngần này dB mới nghe thấy.
_SFX_TREN_LOI_DB = 1.0
#: TRẦN theo MỨC LỜI: anh Hùng chốt "đỉnh SFX không quá ~1,5x mức lời" =
#: +3,5 dB. Đây là vế CHỐNG ÁT LỜI, đứng sau cả bù nhóm.
_SFX_TRAN_LOI_DB = 3.5
#: ===================== BỊ **LỜI NÓI** CHE (09/08/2026) =====================
#: Anh Hùng nghe clip v2.19.0: *"hiệu ứng âm thanh nhỏ quá, nó dùng mà không
#: nghe thấy luôn, NÓI ÁT RỒI hay sao"* — và anh ấy ĐOÁN ĐÚNG.
#: v2.19.0 đặt MỘT đích cho CẢ CLIP, tính từ `nen`/`loi` là bách phân vị của
#: TOÀN clip. Tai người không nghe "so với cả clip", tai nghe **so với thứ đang
#: phát NGAY LÚC ĐÓ**. Đo 13 mốc trên 3 video thật (`_do_che_loi.py`):
#:   * mốc rơi vào KHOẢNG LẶNG: tiếng động cao hơn thứ đang phát **+7,0 dB**
#:     (trung vị) -> dải to thêm tới +11..+38 dB, nghe rất rõ;
#:   * mốc rơi vào lúc ĐANG NÓI: **−1,6 dB** (trung vị), tức tiếng động NHỎ HƠN
#:     giọng nói -> 4/9 mốc chỉ còn nhô ở dải <300 Hz (loa điện thoại KHÔNG tái
#:     tạo), 1/9 mốc dải nào cũng +0,1 dB = KHÔNG NGHE RA GÌ.
#: Nguyên nhân số học: mức lời cục bộ tại mốc cao hơn bpv90 CẢ CLIP tới
#: **+5,2 dB** (đo: YEN lời −19,6 nhưng tại mốc −14,4), trong khi đích bị trần
#: `bpv90 + 3,5` khoá. Đích thua mức lời cục bộ ngay từ công thức.
#: CHỮA: đo MỨC LỜI CỤC BỘ tại CHÍNH mốc đó (`muc_tai_moc`) rồi
#:   * SÀN mới: `lời_cục_bộ + _SFX_TREN_LOI_MOC_DB`;
#:   * TRẦN vẫn "1,5x mức lời" nhưng lấy theo `max(lời_clip, lời_cục_bộ)` —
#:     bất biến CHỐNG ÁT LỜI giữ nguyên ý nghĩa, chỉ thôi tự khoá mình.
#: Vì sao +1,5 chứ không cao hơn: cộng 2 nguồn không tương quan, tỉ lệ SFX/lời
#: = S dB làm dải đó to thêm `10log10(1+10^(S/10))` dB. S=−6 -> +1,0 dB (đúng
#: ngưỡng vừa phân biệt được); S=0 -> +3,0 dB. Ở mốc đang nói còn CỘNG THÊM
#: 6 dB ducking (`_SFX_DUCK_DB_NOI`, đỉnh bướu rơi đúng vào mốc) nên tỉ lệ thực
#: là **+7,5 dB** — ngang đúng ca khoảng lặng đang nghe rõ (+7,5 dB đo được).
#: KHÔNG đẩy `_SFX_TREN_LOI_MOC_DB` lên +3: nguồn của anh Hùng có bản đỉnh
#: −2,45 dBFS, đích cao hơn nữa thì `alimiter` sau khi trộn gọt đúng vào cú va
#: (đo: lớp SFX bị gọt mất 7 dB, tỉ lệ tụt về −6,3 dB = tệ hơn lúc chưa sửa).
#: Dọn chỗ bằng ducking RẺ hơn kéo to: nó cho đúng ngần ấy dB mà không thêm
#: một chút năng lượng nào vào bản trộn.
_SFX_TREN_LOI_MOC_DB = 1.5
#: Bề rộng cửa sổ đo "thứ đang phát tại mốc" (giây). Bằng đúng cửa sổ tai nghe
#: một cú va mà cổng 44 dùng (±0,175 s) — đo rộng hơn là lấy phải cả câu nói
#: bên cạnh, đo hẹp hơn là trượt khỏi âm tiết đang che.
_SFX_MOC_RONG = 0.35
#: Mốc bị coi là "ĐANG NÓI" khi mức cục bộ cao hơn NỀN cục bộ ngần này dB.
#: Đo trên 3 video thật: ca khoảng lặng ra +0,6..+6,2 dB, ca đang nói ra
#: +7,6..+26,0 dB -> 7 dB tách sạch 2 nhóm.
_SFX_DANG_NOI_DB = 7.0
#: Suy ra khi thiếu số đo: đỉnh RMS 50 ms ~ mean + 6 dB · mức lời ~ nền + 12 dB.
#: (chỉ dùng cho lối gọi cũ 4 tham số / bảng `muc_do.json` bản 2 cột.)
_SFX_ST_SUY_RA, _SFX_LOI_SUY_RA = 6.0, 12.0
#: LỖI THẦM LẶNG ĐO ĐƯỢC 08/08/2026 — **MẤT ĐÚNG 3,0 dB Ở MỌI TIẾNG ĐỘNG**.
#: Kho là file MONO; `amix` ra stereo nên ffmpeg tự chèn phép đổi bố cục kênh,
#: mà luật đổi mono->stereo của ffmpeg nhân 1/căn2 cho mỗi bên (-3,01 dB). App
#: tính hệ số theo mức đo được của file rồi bị lấy mất 3 dB không một dòng báo:
#: đo trên clip thật, lớp tiếng động luôn thấp hơn đích **-2,7 .. -3,1 dB**.
#: `pan` với toán tử `<` (KHÔNG chuẩn hoá lại) đưa mono ra cả 2 bên ở nguyên
#: mức, và để nguyên file stereo (đo: mono +3,0 dB · stereo 0,0 dB).
_SFX_PAN_GIU_MUC = "pan=stereo|FL<FL+FC|FR<FR+FC"
#: Bù theo NHÓM (dB, cộng vào mốc trên). Thay cho bảng `_SFX_CAT_VOL` cũ: bảng
#: cũ là hệ số TUYỆT ĐỐI nên không biết file to hay nhỏ; bảng này là ĐỘ LỆCH
#: TƯƠNG ĐỐI nên giữ đúng "tính cách" từng nhóm mà vẫn chuẩn hoá được.
_SFX_CAT_DB = {
    "impact": +2.0, "riser": +1.0, "drumroll": +1.0, "scratch": +1.5,
    "transition": 0.0, "pop": 0.0, "comedy": +0.5,
    "reveal": -1.5, "suspense": -3.0, "sad": -2.5,
}
#: Trần ĐỈNH của MỘT lớp tiếng động (dBFS) — nay do `alimiter` giữ, KHÔNG kẹp
#: gain nữa. Chừa chỗ để cộng với tiếng gốc mà lớp hạn cuối không phải gọt sâu.
_SFX_DINH_TRAN_DB = -2.0
#: Trần ĐỈNH SAU KHI TRỘN (dBFS) — bảo đảm không méo dù nguồn đã sát 0 dBFS.
#: -1,6 chứ không phải -1,0: AAC là mã hoá CÓ MẤT, sóng giải mã ra VỌT LÊN trên
#: mức đã mã hoá (đo: hạn -1,0 -> file .mp4 giải ra **-0,45 dBFS**). Chừa 0,6 dB
#: cho phần vọt đó thì đỉnh ĐỌC ĐƯỢC TỪ FILE mới thật sự <= -1 dBFS.
#: SỬA 09/08/2026 -2,0 -> -3,0: nâng đích theo MỨC LỜI CỤC BỘ làm lớp tiếng
#: động to hơn hẳn, nên `alimiter` phải gọt sâu hơn trong 1 ms và phần VỌT của
#: AAC nở ra theo. Đo ngay: clip YÊN xuất ra **+0,41 dBFS / 1 mẫu chạm trần**
#: trong khi bản TẮT là -4,84 / 0 mẫu — tức bản BẬT MÉO HƠN bản TẮT, phá đúng
#: luật đã chốt. Chừa thêm 1 dB thì hết, mà độ to không đổi (limiter chỉ chạm
#: vào đúng mấy cú va cao nhất).
_SFX_TRAN_TRON_DB = -3.0
#: Kẹp hệ số (dB) để một file lỗi/quá nhỏ không bị kéo lên thành tiếng ồn.
_SFX_GAIN_MIN, _SFX_GAIN_MAX = -30.0, 15.0
#: Hệ số đỉnh ngắn hạn (max − rms50) tối đa còn "gọt được": file vượt mức này
#: mà bị nén cho vừa trần thì mất quá nhiều độ to -> lúc bốc file thì TRÁNH nó
#: (vẫn ngẫu nhiên trong số còn lại — anh Hùng cần 3 Part không kêu giống nhau).
#: Đo: để 6,0 dB thì clip ỒN vẫn bốc trúng file crest 11 dB, `alimiter` gọt mất
#: ~5 dB -> lớp tiếng động thấp hơn đích 6,4 dB. Để 3,0 thì clip ồn chỉ dùng
#: tiếng ĐẶC (whoosh/drone), clip yên vẫn dùng được cả kho — đúng nghề trộn
#: tiếng: mix dày thì phải chọn tiếng dày, không chọn cú click nhọn.
_SFX_CREST_DU = 3.0
#: HỤT QUA LOA ĐIỆN THOẠI còn CHẤP NHẬN được (dB, xem `hut_qua_loa`). Đo kho
#: 184 file: trung vị **−0,5 dB** (đại đa số không hụt gì) nhưng bpv10 là
#: **−18,5 dB** và tệ nhất **−44,7 dB**. Đặt −6,0: loại 51 file, còn 133 để bốc
#: ngẫu nhiên. −6 chứ không phải −3 vì −3 chỉ còn 120 file mà chẳng thêm gì —
#: hụt 6 dB vẫn nghe rõ, hụt 18 dB thì không.
_SFX_LOA_HUT_MAX = -6.0
#: CÁCH FILE SÁNG NHẤT NHÓM bao nhiêu dB thì còn được bốc **ở mốc ĐANG NÓI**
#: (xem `do_sang_sfx`). A/B SẠCH (`_do_che_loi.py BQ_SO_FILE=...`): cùng clip
#: ỒN, cùng mốc đang nói 4,40 s, cùng hệ số — chỉ ép khác đúng 1 file, đo
#: D_CHE = dải nghe được nổi lên khỏi THỨ ĐANG CHE bao nhiêu dB:
#:   `impactGlass_light_001`  sáng −23,2 -> **+9,6 dB**
#:   `impactGlass_medium_003` sáng −32,6 -> **+4,2 dB**
#:   `impactGlass_medium_000` sáng −35,7 -> **+4,3 dB**
#:   `boom_deep_05`           sáng −56,3 -> **−0,5 dB = KHÔNG NGHE RA**
#: Tức trong CÙNG một nhóm, file sáng hơn 12 dB nghe rõ hơn **5,4 dB** mà
#: không tốn thêm một dB độ to nào — đúng hướng "chọn tiếng LỆCH DẢI TẦN với
#: giọng nói". Sáng nhất nhóm `impact` (sau bộ lọc loa) là −23,2 nên cửa 10 dB
#: giữ 7/20 file: đủ để 3 Part không kêu giống hệt nhau, mà đã kéo kỳ vọng lên
#: phía +9,6. Cửa 8 dB còn 5 file (bắt đầu lặp tiếng), cửa 15 dB nhận lại
#: 16/20 = gần như không lọc.
_SFX_SANG_DU = 10.0
#: DÓNG CÚ VA VÀO ĐÚNG MỐC: đẩy tiếng động sớm lên đúng bằng "giây xảy ra
#: đỉnh" để chỗ TO NHẤT của nó rơi vào đúng giây điểm nhấn. Kho có 18/184 file
#: vào chậm hơn mức này (trung vị 0,10 s · bpv90 0,35 s · max 0,60 s) — số đó
#: bị loại khỏi điểm nhấn vì đẩy sớm hơn 0,35 s là nghe thành "tiếng của cảnh
#: trước", không còn đánh dấu gì.
_SFX_DICH_TOI_DA = 0.35
#: DUCKING: hạ tiếng gốc bao nhiêu dB lúc tiếng động kêu, trong bao lâu, và
#: bắt đầu sớm hơn tiếng động bao nhiêu.
#: SỬA 08/08/2026 — **DUCKING LÀ THỦ PHẠM CHÍNH của "mốc còn NHỎ ĐI"**. Bản cũ
#: 5,0 dB / 0,45 s / sớm 0,06 s: bướu nửa hình sin SÂU NHẤT ở GIỮA bướu, tức
#: **0,225 s SAU mốc** — nhưng cửa sổ tai/máy đo nghe cú va là ±0,175 s QUANH
#: mốc, nên trong đúng cửa sổ đó tiếng gốc bị hạ 5 dB mà cú va chưa kịp bù
#: (đo YÊN@1,20s: **-2,5 dB**, tức bật tiếng động lên thì chỗ đó NHỎ ĐI).
#: Nay `_SFX_DUCK_SOM` ÂM = bắt đầu **SAU** mốc 0,15 s: **cú va tự nó phải
#: xuyên qua**, ducking chỉ dọn chỗ cho phần NGÂN phía sau. Nhờ vậy cửa sổ đo
#: gần như không dính ducking mà tiếng động vẫn có chỗ thở.
#: -0,22 chứ không phải -0,15: cửa sổ tai nghe cú va là ±0,175 s quanh mốc, để
#: ducking chạm vào rìa cửa sổ đó là mốc lại tụt (đo YÊN@1,20s: -0,6 dB, hỏng
#: 1/5 lượt). Bướu phải nằm HẲN ngoài cửa sổ.
_SFX_DUCK_DB, _SFX_DUCK_DAI, _SFX_DUCK_SOM = 3.0, 0.35, -0.22
#: DUCK SÂU HƠN **CHỈ Ở MỐC RƠI VÀO LÚC ĐANG NÓI** (09/08/2026). Mốc rơi vào
#: khoảng lặng đã nghe rất rõ (+7,0 dB so thứ đang phát) nên không cần đụng;
#: mốc rơi vào lúc đang nói mới là chỗ bị che. Hạ giọng thêm 3 dB ở phần NGÂN
#: (bướu vẫn bắt đầu SAU mốc 0,15 s như cũ, không trùm lên chính cú va) là dọn
#: chỗ mà KHÔNG phải kéo tiếng động to thêm 3 dB — cách này không làm clip chói
#: và không đẩy thêm việc cho lớp hạn đỉnh cuối.
#: 6 dB là mức ducking lời-dưới-nhạc thông dụng của phát thanh (6-12 dB), lại
#: chỉ kéo dài 0,35 s nên không nghe thành "hụt tiếng".
_SFX_DUCK_DB_NOI = 6.0
#: ...VÀ BƯỚU PHẢI MỞ RA **TRƯỚC** MỐC ở ca đang nói (0,10 s), dài 0,45 s.
#: ĐÂY LÀ CHỖ v2.19.0 ĐÁNH ĐỔI NHẦM. Bản đó đẩy bướu ra SAU mốc để cổng 44 hết
#: báo "mốc nhỏ đi" — nhưng làm thế thì ĐÚNG LÚC cú va đánh xuống, tiếng gốc
#: vẫn đang to hết cỡ: (1) tai không tách được cú va ra khỏi giọng nói, (2)
#: nguồn của anh Hùng đã sát trần nên `alimiter` sau khi trộn phải gọt, và nó
#: gọt đúng cú va. Đo được: nguồn nóng (bản TẮT -2,45 dBFS) thì lớp tiếng động
#: bị gọt mất tới **7 dB** (SFX -9,2 -> -16,6 dBFS), SMR tụt về **-6,3 dB**.
#: SỚM 0,225 s trên bướu dài 0,45 s = ĐỈNH BƯỚU RƠI ĐÚNG VÀO MỐC, tức đúng lúc
#: cú va đánh xuống thì giọng nói đã hạ TRỌN `_SFX_DUCK_DB_NOI` = 6 dB. Thử
#: sớm 0,10 s trước (hạ 3,8 dB tại mốc) thì nguồn NÓNG vẫn hỏng 3/4 mốc — chưa
#: đủ chỗ. Ramp vào 0,225 s là quá êm để nghe thành "hụt tiếng".
#: DỌN CHỖ RẺ HƠN KÉO TO: 6 dB ducking cho 6 dB tỉ lệ tín hiệu/che mà KHÔNG
#: thêm một chút năng lượng nào vào file -> không chói, không đẩy việc cho lớp
#: hạn đỉnh cuối. Vì thế `_SFX_TREN_LOI_MOC_DB` chỉ cần +1,5 dB.
#: Ca KHOẢNG LẶNG GIỮ NGUYÊN bướu-sau-mốc của v2.19.0 (đo: đang chạy tốt,
#: +7,5 dB so thứ đang phát) — không có gì che thì không cần dọn chỗ.
_SFX_DUCK_SOM_NOI, _SFX_DUCK_DAI_NOI = 0.225, 0.45
#: Lớp tiếng động được phép có ĐỈNH cao hơn mức RMS đích bao nhiêu dB. Đây là
#: cái quyết định lớp hạn đỉnh CUỐI phải gọt nhiều hay ít: clip YÊN có đích
#: -16,6 dBFS mà vẫn cho lớp đội đỉnh tới -2 dBFS thì cộng với tiếng gốc
#: (-4,9) ra +2,4 dBFS -> limiter phải gọt 4,4 dB, gọt đúng vào mốc điểm nhấn.
#: Cho 10 dB là vừa: kho có crest ngắn hạn trung vị 11,2 dB nên gần như không
#: mất độ to, mà đỉnh lớp hạ theo đích -> clip yên thì limiter gần như im.
_SFX_CREST_CHO = 10.0
#: LỚP TIẾNG ĐỘNG phải nằm THẤP HƠN trần bản trộn ít nhất ngần này dB (09/08).
#: Lý do: `alimiter` **gọt đỉnh mà GIỮ độ to**, nên gọt SỚM ở nhánh SFX là rẻ;
#: còn để lớp hạn đỉnh CUỐI gọt thì nó hạ CẢ BẢN TRỘN (kể cả giọng nói) và hạ
#: đúng vào giây điểm nhấn. Đo trên nguồn nóng: không có vế này thì lớp SFX bị
#: gọt từ -9,2 xuống -16,6 dBFS (mất 7 dB) và mốc thành KHÔNG NGHE RA.
_SFX_LOP_DUOI_TRON = 3.0
#: 2 tiếng động gần nhau hơn mức này -> BỎ cái sau (tránh "rào rào").
_SFX_CACH_MIN = 0.80
#: Mức nền GIẢ ĐỊNH (dBFS) khi clip không có tiếng gốc để đo.
_SFX_NEN_MAC_DINH = -26.0

#: LOẠI TIẾNG THEO **KIỂU HIỆU ỨNG HÌNH** (anh Hùng: *"zoom/rung -> impact; loé
#: sáng -> reveal/riser; glitch -> scratch; chuyển đoạn -> transition; cảnh hài
#: -> comedy"*). Khoá là khoá trong `hieu_ung.KHO`.
_SFX_THEO_HIEU_UNG = {
    # dời chỗ / va đập
    "zoom_nhoi": "impact", "rung_lac": "impact", "meo_kinh": "impact",
    "zoom_day": "riser", "song_meo": "suspense",
    # sáng / lộ ra
    "loe_sang": "reveal", "quang_sang": "reveal", "nhay_sang": "riser",
    "tuong_phan": "impact", "sh_tuong_phan": "impact",
    # tối / nén
    "sup_toi": "suspense", "toi_vien": "suspense", "sh_toi_vien": "suspense",
    "vien_phim": "suspense",
    # vỡ hình / nhiễu
    "o_vuong": "scratch", "xao_dong": "scratch", "glitch_khoi": "scratch",
    "lech_bang": "scratch", "dong_quet": "scratch", "nhieu_analog": "scratch",
    "vien_net": "scratch",
    # phim / hạt / mờ
    "hat_phim": "transition", "hat_nhieu": "transition",
    "sh_hat_phim": "transition", "mo_net": "pop", "mo_vuong": "pop",
    # chữ
    "dem_nguoc": "drumroll",
}


def _la_hook_first(segs: list) -> bool:
    """Clip này có phải kiểu HOOK-FIRST (đoạn cao trào được BÊ LÊN ĐẦU)?

    Dấu hiệu chắc chắn, không phải đoán: đoạn đầu bắt đầu MUỘN HƠN đoạn sau
    trên timeline GỐC — tức app đã nhảy NGƯỢC thời gian. Cùng dấu hiệu mà
    `m1._loai_theo_khoang_nhay` dùng để chọn tiếng cho chỗ nối. Hàm thuần."""
    try:
        return (len(segs) >= 2
                and float(segs[0][0]) > float(segs[1][0]) + 0.05)
    except (TypeError, ValueError, IndexError):
        return False


def loai_sfx_theo_hieu_ung(khoa: str) -> str:
    """Kiểu hiệu ứng HÌNH -> nhóm tiếng động đi kèm. Kiểu lạ -> 'impact'
    (điểm nhấn thì phải có cú nhấn, không được im). Hàm thuần."""
    return _SFX_THEO_HIEU_UNG.get(str(khoa or ""), "impact")


_SFX_MUC_BANG: Optional[dict] = None
_SFX_MUC_DO: dict = {}          # cache mức đo SỐNG (file ngoài kho / bảng thiếu)


def _sfx_bang_muc() -> dict:
    """Bảng mức âm kho tiếng động (`app/assets/sfx/muc_do.json`), cache 1 lần.
    Thiếu file -> {} và `_muc_sfx` tự đo sống (chậm hơn nhưng vẫn đúng)."""
    global _SFX_MUC_BANG
    if _SFX_MUC_BANG is not None:
        return _SFX_MUC_BANG
    try:
        import json
        p = _assets_sfx_dir() / "muc_do.json"
        _SFX_MUC_BANG = json.loads(p.read_text(encoding="utf-8"))
    except Exception:      # noqa: BLE001 — thiếu bảng KHÔNG được làm chết xuất
        _SFX_MUC_BANG = {}
    return _SFX_MUC_BANG


def _muc_sfx3(path: str) -> tuple[float, float, float]:
    """(mean_dB, max_dB, **đỉnh RMS 50 ms**) của 1 file tiếng động.

    Mục thứ 3 là cái QUYẾT ĐỊNH độ to nghe được và là cái app chuẩn hoá theo
    (xem khối `SFX_TREN_NEN_DB`). Bảng `muc_do.json` bản CŨ chỉ có 2 cột ->
    suy ra `mean + _SFX_ST_SUY_RA` để bản cài cũ vẫn chạy được, không nổ.
    Ưu tiên BẢNG đóng gói (0 ms); không có thì đo sống 1 lần rồi nhớ."""
    p = str(path)
    if p in _SFX_MUC_DO:
        return _SFX_MUC_DO[p]
    try:
        key = Path(p).resolve().relative_to(
            _assets_sfx_dir().resolve()).as_posix()
    except (ValueError, OSError):
        key = ""
    v = _sfx_bang_muc().get(key)
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        st = (float(v[2]) if len(v) >= 3
              else float(v[0]) + _SFX_ST_SUY_RA)
        kq = (float(v[0]), float(v[1]), st)
    else:
        d = _do_muc_file(p) or (-12.0, -3.0)
        kq = (d[0], d[1], d[0] + _SFX_ST_SUY_RA)
    _SFX_MUC_DO[p] = kq
    return kq


def _muc_sfx(path: str) -> tuple[float, float]:
    """(mean_dB, max_dB) — giữ cho lối gọi cũ."""
    m, x, _s = _muc_sfx3(path)
    return (m, x)


def _moc_dinh_sfx(path: str) -> float:
    """GIÂY xảy ra đỉnh RMS 50 ms của file (0,0 nếu bảng chưa có cột 4).

    VÌ SAO PHẢI BIẾT: kho có tiếng **VÀO CHẬM** — `ding_soft_04_v2.opus` đỉnh
    rơi **0,60 s SAU** lúc bắt đầu. Chèn nó đúng giây điểm nhấn thì trong cửa
    sổ tai nghe cú va (±0,175 s) nó chỉ có **-28,3 dBFS** thay vì -20,1 = hụt
    **8,2 dB**, tức điểm nhấn coi như KHÔNG có tiếng dù nhật ký ghi là có.
    Đây là 1 trong 2 nguồn làm cổng 44 nhấp nháy (chạy 5 lượt hỏng 2)."""
    try:
        key = Path(str(path)).resolve().relative_to(
            _assets_sfx_dir().resolve()).as_posix()
    except (ValueError, OSError):
        return 0.0
    v = _sfx_bang_muc().get(key)
    if isinstance(v, (list, tuple)) and len(v) >= 4:
        try:
            return max(0.0, float(v[3]))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def do_sang_sfx(path: str) -> float:
    """ĐỘ SÁNG (cột 6, dB <= 0): năng lượng trên 4 kHz so với toàn dải.

    VÌ SAO DÙNG: giọng người dồn 300-3400 Hz. Tiếng động có nhiều năng lượng
    TRÊN 4 kHz thì ở dải đó nó gần như KHÔNG có gì che -> nghe rõ mà không
    phải to thêm một dB nào (không chói, không phải hạ giọng sâu, không đẩy
    việc cho lớp hạn đỉnh). Đây là hướng "chọn tiếng động LỆCH DẢI TẦN với
    giọng nói".
    Đo kho 184 file: trung vị **-32,3 dB** · bpv75 **-14,4** · sáng nhất
    **-1,1**. Sáng tập trung ở `pop` (16 file >= -12 dB), `scratch` (9),
    `riser` (5); nhóm `impact` KHÔNG có file nào >= -12 dB — nên app dùng ưu
    tiên TƯƠNG ĐỐI (lấy nửa sáng nhất của nhóm) chứ không đặt ngưỡng cứng, để
    nhóm nào cũng còn file mà bốc. Bảng thiếu cột 6 -> -99 = không ưu tiên
    được, đường cũ y nguyên."""
    try:
        key = Path(str(path)).resolve().relative_to(
            _assets_sfx_dir().resolve()).as_posix()
    except (ValueError, OSError):
        return -99.0
    v = _sfx_bang_muc().get(key)
    if isinstance(v, (list, tuple)) and len(v) >= 6:
        try:
            return float(v[5])
        except (TypeError, ValueError):
            return -99.0
    return -99.0


def hut_qua_loa(path: str) -> float:
    """CÒN LẠI BAO NHIÊU dB khi phát qua LOA ĐIỆN THOẠI (cột 5, <= 0 dB).

    = đỉnh RMS 50 ms sau khi cắt dưới 300 Hz (bậc 4) TRỪ đỉnh RMS 50 ms cả dải.
    Bảng chưa có cột 5 -> 0,0 = coi như không hụt (đường cũ y nguyên).

    VÌ SAO PHẢI BIẾT — **NGUYÊN NHÂN THỨ HAI của "không nghe thấy"**, đo
    09/08/2026: khán giả Shorts nghe bằng loa điện thoại, thứ gần như không
    phát được dưới 300 Hz. Kho 184 file có **51 file hụt quá 6 dB**, tệ nhất
    `impact/boom_deep_05.opus` hụt **44,7 dB** — trên máy đo nó "to đúng đích",
    trên điện thoại nó CÂM. Đo trên clip thật: mốc bốc trúng file trầm thì dải
    <300 Hz vọt **+22..+38 dB** còn mọi dải từ 300 Hz trở lên KHÔNG đổi (còn
    tụt vì ducking) -> khán giả nghe thấy đúng một thứ: giọng nói bị hụt đi."""
    try:
        key = Path(str(path)).resolve().relative_to(
            _assets_sfx_dir().resolve()).as_posix()
    except (ValueError, OSError):
        return 0.0
    v = _sfx_bang_muc().get(key)
    if isinstance(v, (list, tuple)) and len(v) >= 5:
        try:
            return min(0.0, float(v[4]))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _doc_volumedetect(txt: str) -> Optional[tuple[float, float]]:
    """Bóc (mean_dB, max_dB) từ log `volumedetect`. Hàm thuần — test được."""
    mean = mx = None
    for ln in (txt or "").splitlines():
        if "mean_volume:" in ln:
            try:
                mean = float(ln.split("mean_volume:")[1].split("dB")[0])
            except (ValueError, IndexError):
                pass
        elif "max_volume:" in ln:
            try:
                mx = float(ln.split("max_volume:")[1].split("dB")[0])
            except (ValueError, IndexError):
                pass
    if mean is None or mx is None:
        return None
    return (mean, mx)


def _do_muc_file(path: str) -> Optional[tuple[float, float]]:
    """Đo (mean, max) dB của 1 file âm bằng ffmpeg. None nếu không đo được."""
    try:
        r = subprocess.run(
            [settings.FFMPEG_PATH, "-hide_banner", "-v", "info", "-nostdin",
             "-threads", "1", "-i", str(path), "-vn", "-af", "volumedetect",
             "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", creationflags=_CREATE_NO_WINDOW, timeout=60)
        return _doc_volumedetect(r.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return None


def _muc_nen_dB(dau_vao: list) -> Optional[float]:
    """Mức NỀN (mean_volume dBFS) của tiếng nguồn trên ĐÚNG timeline sắp xuất.

    `dau_vao` = danh sách token input của caller (`-f concat -i list` hoặc
    `-ss/-t -i src`) — cùng khuôn `hieu_ung.do_nhip` dùng, nên đo đúng phần
    phim được giữ lại chứ không phải cả file gốc.

    CỐ Ý KHÔNG qua cửa chờ ffmpeg (như `do_nhip`): lệnh này chỉ giải mã ÂM
    THANH, `-threads 1`, đo 60 s clip hết ~0,2 s. Bắt nó xếp hàng sau các lệnh
    encode nặng thì mỗi lượt xuất đội thêm hàng chục giây vô ích.
    """
    kq = _do_muc_clip(dau_vao)
    return None if kq is None else kq["mean"]


def _bpv(xs: list, q: float) -> float:
    y = sorted(xs)
    return y[min(len(y) - 1, int(len(y) * q))] if y else 0.0


def _do_muc_clip(dau_vao: list) -> Optional[dict]:
    """MỌI số đo mức của tiếng nguồn trên ĐÚNG timeline sắp xuất — MỘT lượt.

    Trả `{"nen", "giua", "loi", "dinh", "mean"}` (dBFS):
      * `nen`  = bpv20 đường bao RMS 50 ms — **NỀN THẬT**. `mean_volume` (bản
        cũ) KHÔNG phải nền: clip ồn đo mean -15,7 dBFS trong khi nền là -26 ..
        -36 và -15,7 chính là mức LỜI. Lấy mean làm nền là tự đặt cho tiếng
        động một cái đích cao vô lý rồi vế kẹp đỉnh nuốt sạch.
      * `loi`  = bpv90 — MỨC LỜI NÓI, cái mà tiếng động phải "đấu" và không
        được vượt quá ~1,5 lần.
      * `dinh` = `max_volume` — để tính còn bao nhiêu chỗ trống tới trần.

    Đường bao lấy bằng `asetnsamples` + `astats` chạy TRONG ffmpeg (C), Python
    chỉ sắp xếp ~1.200 số cho clip 60 s. `volumedetect` đặt TRƯỚC `aresample`
    nên `dinh` là đỉnh thật ở 48 kHz, không phải đỉnh sau khi hạ tần số.

    CỐ Ý KHÔNG qua cửa chờ ffmpeg (như `do_nhip`): chỉ giải mã ÂM THANH,
    `-threads 1`, đo 60 s clip hết ~0,2 s. Bắt nó xếp hàng sau các lệnh encode
    nặng thì mỗi lượt xuất đội thêm hàng chục giây vô ích.
    """
    try:
        r = subprocess.run(
            [settings.FFMPEG_PATH, "-hide_banner", "-v", "info", "-nostdin",
             "-threads", "1", *[str(x) for x in dau_vao], "-vn",
             "-af", "volumedetect,aresample=8000,"
                    "aformat=channel_layouts=mono,asetnsamples=n=400,"
                    "astats=metadata=1:reset=1,ametadata=print:"
                    "key=lavfi.astats.Overall.RMS_level:file=-",
             "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", creationflags=_CREATE_NO_WINDOW, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return None
    vd = _doc_volumedetect(r.stderr or "")
    bao = []
    for ln in (r.stdout or "").splitlines():
        if "RMS_level=" in ln:
            try:
                v = float(ln.split("=", 1)[1])
            except (ValueError, IndexError):
                continue
            if v > -200.0:              # -inf = cửa sổ im lặng tuyệt đối
                bao.append(v)
    if not bao and vd is None:
        return None
    if not bao:
        # không dựng được đường bao -> lùi về mean cho cả 3 mốc (bản cũ)
        return {"nen": vd[0], "giua": vd[0], "loi": vd[0],
                "dinh": vd[1], "mean": vd[0]}
    return {"nen": _bpv(bao, 0.20), "giua": _bpv(bao, 0.50),
            "loi": _bpv(bao, 0.90),
            "dinh": (vd[1] if vd else max(bao)),
            "mean": (vd[0] if vd else _bpv(bao, 0.50)),
            # ĐƯỜNG BAO THÔ — để tính MỨC LỜI CỤC BỘ tại từng mốc (`muc_tai_moc`).
            # `asetnsamples=n=400` sau `aresample=8000` = đúng 50 ms/cửa sổ,
            # cùng thước với cổng đo. Không tốn thêm một lượt ffmpeg nào: số này
            # vốn đã dựng xong ở trên, bản cũ chỉ vứt đi sau khi lấy bách phân vị.
            "bao": bao, "buoc": 400.0 / 8000.0}


def muc_tai_moc(bao: list, buoc: float, giay: float,
                rong: float = _SFX_MOC_RONG) -> Optional[float]:
    """MỨC LỜI CỤC BỘ (dBFS) của tiếng nguồn NGAY TẠI mốc — hàm thuần.

    = giá trị LỚN NHẤT của đường bao RMS 50 ms trong cửa sổ `±rong/2` quanh mốc.

    VÌ SAO PHẢI CÓ HÀM NÀY (lỗi v2.19.0): bản cũ chỉ có MỘT đích cho cả clip,
    tính từ bpv90 TOÀN clip. Nhưng mốc điểm nhấn không rơi vào "clip trung
    bình" — nó rơi vào một chỗ CỤ THỂ, và chỗ đó thường là lúc đang nói. Đo 3
    video thật: mức tại mốc cao hơn bpv90 cả clip tới **+5,2 dB**, trong khi
    đích lại bị trần `bpv90 + 3,5` khoá -> tiếng động thua giọng nói ngay từ
    công thức, dù cổng 44 vẫn báo "nổi +26 dB trên nền".

    LẤY MAX chứ không lấy trung bình: cái che cú va là âm tiết TO NHẤT trong
    cửa sổ, không phải mức trung bình của cửa sổ."""
    if not bao or buoc <= 0:
        return None
    i0 = max(0, int(round((float(giay) - rong / 2.0) / buoc)))
    i1 = min(len(bao), int(round((float(giay) + rong / 2.0) / buoc)) + 1)
    if i1 <= i0:
        return None
    return max(bao[i0:i1])


def nen_tai_moc(bao: list, buoc: float, giay: float,
                rong: float = 3.0) -> Optional[float]:
    """NỀN CỤC BỘ (bpv20 trong ±rong/2 quanh mốc) — để phân biệt mốc rơi vào
    lúc ĐANG NÓI với mốc rơi vào KHOẢNG LẶNG. Hàm thuần."""
    if not bao or buoc <= 0:
        return None
    i0 = max(0, int(round((float(giay) - rong / 2.0) / buoc)))
    i1 = min(len(bao), int(round((float(giay) + rong / 2.0) / buoc)) + 1)
    if i1 <= i0:
        return None
    return _bpv(list(bao[i0:i1]), 0.20)


def la_moc_dang_noi(bao: list, buoc: float, giay: float) -> bool:
    """Mốc này có rơi đúng lúc ĐANG NÓI không? (mức cục bộ vượt nền cục bộ
    `_SFX_DANG_NOI_DB` dB). Đo 3 video thật: khoảng lặng +0,6..+6,2 dB · đang
    nói +7,6..+26,0 dB. Hàm thuần."""
    m = muc_tai_moc(bao, buoc, giay)
    n = nen_tai_moc(bao, buoc, giay)
    if m is None or n is None:
        return False
    return (m - n) >= _SFX_DANG_NOI_DB


def dich_sfx_dB(cat: str, nen_db: float, loi_db: Optional[float] = None,
                loi_moc: Optional[float] = None) -> float:
    """ĐỈNH RMS 50 ms mà lớp tiếng động PHẢI đạt (dBFS) — hàm thuần.

    Ba vế SÀN, lấy vế CAO nhất rồi mới chặn trần:
      * `nền + SFX_TREN_NEN_DB`  — clip yên: nổi hẳn lên khỏi nền.
      * `lời + _SFX_TREN_LOI_DB` — clip ỒN: nền thấp nhưng LỜI to, bám theo nền
        thì tiếng động chìm nghỉm dưới lời (đúng lỗi anh Hùng nghe thấy).
      * `lời_CỤC_BỘ + _SFX_TREN_LOI_MOC_DB` — **MỚI 09/08/2026**: cái tai nghe
        không phải "cả clip" mà là thứ đang phát ĐÚNG LÚC ĐÓ. Thiếu vế này thì
        mốc rơi vào lúc đang nói có tiếng động THẤP HƠN giọng nói (đo 3 video:
        trung vị −1,6 dB) = bị che, dù cổng 44 vẫn xanh.
      * trần `max(lời, lời_cục_bộ) + _SFX_TRAN_LOI_DB` (~1,5x mức lời) — vế
        CHỐNG ÁT LỜI, đứng SAU bù nhóm nên nhóm "impact" cũng không được vượt.
        Lấy `max` chứ không thay hẳn bằng `lời_cục_bộ`: mốc rơi vào KHOẢNG LẶNG
        có `lời_cục_bộ` rất thấp, thay hẳn là tự bóp chết đúng cái ca đang chạy
        tốt (đo: ca khoảng lặng hiện +7,0 dB so thứ đang phát).

    `loi_moc=None` -> KẾT QUẢ Y HỆT bản cũ (mọi lối gọi cũ không đổi 1 số)."""
    if loi_db is None:
        loi_db = float(nen_db) + _SFX_LOI_SUY_RA
    bu = _SFX_CAT_DB.get(str(cat), 0.0)
    san = [float(nen_db) + SFX_TREN_NEN_DB, float(loi_db) + _SFX_TREN_LOI_DB]
    tran_goc = float(loi_db)
    if loi_moc is not None:
        san.append(float(loi_moc) + _SFX_TREN_LOI_MOC_DB)
        tran_goc = max(tran_goc, float(loi_moc))
    return min(max(san) + bu, tran_goc + _SFX_TRAN_LOI_DB)


def tinh_gain_sfx(cat: str, mean_db: float, max_db: float, nen_db: float,
                  st_db: Optional[float] = None,
                  loi_db: Optional[float] = None,
                  loi_moc: Optional[float] = None) -> float:
    """HỆ SỐ NHÂN (tuyến tính) cho 1 lớp tiếng động — HÀM THUẦN, test được.

    `gain = đích − ĐỈNH RMS 50 ms của file`, kẹp trong [`_SFX_GAIN_MIN`,
    `_SFX_GAIN_MAX`] để file hỏng/quá nhỏ không bị kéo thành tiếng ồn.

    KHÔNG còn vế "kẹp đỉnh <= -1 dBFS" — chính vế đó khoá độ to của 74% kho
    khi clip ồn (đo: thiếu trung vị 8,9 dB, tối đa 21,8 dB so với đích). Việc
    giữ đỉnh nay là của `alimiter` ở nhánh SFX + `alimiter` sau khi trộn:
    limiter GỌT ĐỈNH mà GIỮ độ to, còn kẹp gain thì hạ cả hai.

    `st_db`/`loi_db` thiếu -> suy ra từ `mean_db`/`nen_db` (lối gọi 4 tham số
    cũ vẫn chạy, chỉ kém chính xác hơn).
    """
    if st_db is None:
        st_db = float(mean_db) + _SFX_ST_SUY_RA
    g = dich_sfx_dB(cat, nen_db, loi_db, loi_moc) - float(st_db)
    g = max(_SFX_GAIN_MIN, min(_SFX_GAIN_MAX, g))
    return 10.0 ** (g / 20.0)


def _lin(db_: float) -> float:
    return 10.0 ** (float(db_) / 20.0)


def _han_dinh(tran_db: float, nha: int = 40) -> str:
    """Chuỗi `alimiter` GỌT ĐỈNH về `tran_db` dBFS mà KHÔNG đổi độ to.

    3 tuỳ chọn bắt buộc, mỗi cái bịt một cái bẫy ĐO ĐƯỢC:
      * `level=0`  — mặc định `level=true` là TỰ NÂNG mức lên sát trần (đo:
        +3,1 dB cho tín hiệu đang ở -44 dB). Bật nó là app tự ý làm to clip.
      * `latency=1` — bù đúng phần trễ nhìn trước. Đo: không có thì lệch
        **0,98 ms**, có thì **0,0 ms**. Tiếng lệch hình là lỗi loại v1.87.
      * `attack=1` — cú va ngắn 0,17 s, tấn công 5 ms mặc định là gọt hụt.

    `nha` (release) NGẮN ở lớp trộn cuối: cửa sổ đo/nghe là 50 ms, nhả 40 ms
    nghĩa là gọt xong còn ghì gần trọn cửa sổ đó -> chính mốc điểm nhấn bị kéo
    xuống. Nhả 10 ms thì gọt đúng cái đỉnh rồi buông ngay.
    """
    return (f"alimiter=limit={min(1.0, max(0.0625, _lin(tran_db))):.4f}"
            f":level=0:latency=1:attack=1:release={int(nha)}")


def _bieu_thuc_duck(mocs: list, sau_db: Optional[list] = None,
                    dang_noi: Optional[list] = None) -> str:
    """Biểu thức `volume` hạ tiếng gốc quanh MỖI mốc tiếng động — VÀO/RA ÊM.

    Mỗi mốc là một bướu nửa hình sin dài `_SFX_DUCK_DAI` (bắt đầu sớm
    `_SFX_DUCK_SOM`): ở 2 mép bướu = 0 nên âm lượng đúng bằng 1,0 -> KHÔNG có
    cú "cụp" (bậc thang trong `volume` nghe thành tiếng bụp). Hàm thuần.

    `sau_db` = ĐỘ SÂU RIÊNG cho từng mốc (dB, cùng độ dài `mocs`) và
    `dang_noi` = mốc nào rơi đúng lúc ĐANG NÓI — MỚI 09/08/2026. Mốc đang nói
    cần dọn chỗ SÂU HƠN (`_SFX_DUCK_DB_NOI`) và bướu phải mở ra **TRƯỚC** mốc
    (`_SFX_DUCK_SOM_NOI`) để đúng lúc cú va đánh xuống đã có chỗ trống — cả về
    phổ (tai tách được) lẫn về biên độ (`alimiter` sau khi trộn không phải gọt
    vào chính cú va). Mốc rơi vào khoảng lặng GIỮ NGUYÊN cách của v2.19.0: bướu
    nằm sau mốc, 3 dB — nó đã nghe rõ, dọn thêm chỉ làm clip hụt tiếng vô cớ.
    Thiếu cả hai -> mọi mốc dùng đường cũ, RA CHUỖI TƯƠNG ĐƯƠNG bản cũ.

    Bướu SÂU/DÀI KHÁC NHAU thì KHÔNG gộp chung một hệ số được nữa: viết thành
    TỔNG các bướu đã nhân sẵn hệ số riêng, rồi `min(1,...)` chặn chỗ 2 bướu
    chồng nhau (chồng nhau vẫn không bao giờ hạ quá 100% = câm)."""
    if not mocs:
        return ""
    ds = list(sau_db) if sau_db else [_SFX_DUCK_DB] * len(mocs)
    if len(ds) != len(mocs):
        ds = [_SFX_DUCK_DB] * len(mocs)
    ns = list(dang_noi) if dang_noi else [False] * len(mocs)
    if len(ns) != len(mocs):
        ns = [False] * len(mocs)
    bu = []
    for g, sdb, noi in zip(mocs, ds, ns):
        som = _SFX_DUCK_SOM_NOI if noi else _SFX_DUCK_SOM
        dai = _SFX_DUCK_DAI_NOI if noi else _SFX_DUCK_DAI
        a = max(0.0, float(g) - som)
        b = a + dai
        d = 1.0 - 10.0 ** (-float(sdb) / 20.0)
        bu.append(f"{d:.3f}*between(t,{a:.3f},{b:.3f})*"
                  f"sin(3.14159*(t-{a:.3f})/{dai:.3f})")
    return f"volume='1-min(1,{'+'.join(bu)})':eval=frame"


def _sfx_file_ok(path: str) -> bool:
    """File tiếng động ĐỌC ĐƯỢC + có luồng audio? (ffprobe nhanh). File hỏng/
    rỗng/không phải audio -> False để BỎ QUA an toàn (fallback tổng hợp), tránh
    làm ffmpeg export FAIL."""
    try:
        r = subprocess.run(
            [settings.FFPROBE_PATH, "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=_CREATE_NO_WINDOW, timeout=15)
        return r.returncode == 0 and "audio" in (r.stdout or "")
    except (OSError, subprocess.TimeoutExpired):
        return False


def _list_sfx_files(sfx_dir: Optional[str]) -> list[str]:
    """Liệt kê file tiếng động HỢP LỆ (đọc được, có audio) trong thư mục user.
    An toàn: thư mục/file lỗi -> rỗng -> nơi gọi tự fallback sang tiếng tổng hợp."""
    if not sfx_dir:
        return []
    exts = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
    try:
        cands = [str(p) for p in Path(sfx_dir).iterdir()
                 if p.is_file() and p.suffix.lower() in exts]
    except OSError:
        return []
    return [p for p in cands if _sfx_file_ok(p)]


# ================= DỌN FILE TẠM: PHẢI XOÁ ĐƯỢC, KHÔNG "BEST-EFFORT" =========
# ĐO THẬT 08/08/2026 (`_do_ro_seg.py`, ffmpeg thật): xuất LỖI trong lúc mảnh còn
# bị Windows khoá 2 giây (đúng cảnh ffmpeg vừa bị kill) để lại **6 file `_seg_*`
# / 8,9 MB** nằm vĩnh viễn trong %TEMP% — bản cũ `unlink` 1 phát rồi `except
# OSError: pass`, PermissionError bị nuốt IM LẶNG. Đây là đúng loại rác đã làm
# ổ C đầy 100% hôm 31/07 (1,71 GB `_seg_*` phải dọn tay).
#
# 3 LỚP, phải có ĐỦ CẢ 3 (thiếu lớp nào là rác vẫn tồn):
#   1. THỬ LẠI có chờ: Windows nhả handle sau vài trăm ms, tổng ~2,1 s là đủ.
#   2. SỔ NỢ `_RAC_TON`: xoá vẫn không được -> GHI SỔ, lượt xuất sau dọn hộ
#      (đừng để mất dấu — mất dấu là không ai dọn nữa).
#   3. QUÉT MỒ CÔI lúc mở app: app thoát bằng `os._exit` nên `finally` KHÔNG
#      chạy -> mảnh của lần chạy trước phải có người nhặt (xem `don_seg_mo_coi`).
_XOA_CHO = (0.0, 0.15, 0.35, 0.6, 1.0)      # tổng chờ ~2,1 s
_RAC_TON: set = set()                        # file chưa xoá được -> dọn lại sau
_RAC_LOCK = _threading.Lock()


def _thu_xoa(p: str) -> bool:
    """Xoá 1 file, THỬ LẠI theo `_XOA_CHO` khi bị KHOÁ. True = không còn file."""
    q = Path(p)
    for i, cho in enumerate(_XOA_CHO):
        if cho:
            time.sleep(cho)
        try:
            q.unlink(missing_ok=True)
            return True
        except PermissionError:
            # ffmpeg vừa bị kill -> handle chưa nhả. Chờ nhịp sau rồi thử lại.
            if not q.exists():
                return True
            continue
        except OSError:
            # lỗi KHÁC (đường dẫn hỏng, là thư mục...) -> thử lại vô ích
            return not q.exists()
    return not q.exists()


def _cleanup_dst(dst) -> bool:
    """Xoá file output dở dang / mảnh tạm. True = đã sạch.

    KHÔNG còn "best-effort im lặng": xoá không được thì GHI SỔ `_RAC_TON` để
    `don_rac_ton()` (đầu mỗi lượt xuất) và `don_seg_mo_coi()` (lúc mở app) còn
    đường nhặt lại. Chỉ chờ khi file THẬT SỰ còn đó -> đường xuất bình thường
    (file không tồn tại) vẫn trả về tức thì, không chậm đi một ms nào.
    """
    if not dst:
        return True
    p = str(dst)
    try:
        if not Path(p).exists():
            return True
    except OSError:
        return True
    if _thu_xoa(p):
        with _RAC_LOCK:
            _RAC_TON.discard(p)
        return True
    with _RAC_LOCK:
        _RAC_TON.add(p)
    return False


def _cleanup_paths(paths) -> list:
    """Xoá NHIỀU file tạm. TRẢ VỀ danh sách CHƯA xoá được (rỗng = sạch).

    Giá trị trả về là bắt buộc phải dùng ở chỗ nào có `del temps[:]`: bản cũ
    xoá sổ vô điều kiện nên file khoá được coi như đã dọn -> mất dấu vĩnh viễn.
    """
    con: list = []
    for p in paths or []:
        if p and not _cleanup_dst(p):
            con.append(p)
    return con


def don_rac_ton() -> int:
    """Dọn lại các file tạm lần trước xoá không được. Trả số file đã sạch."""
    with _RAC_LOCK:
        ds = list(_RAC_TON)
    n = 0
    for p in ds:
        try:
            if not Path(p).exists():
                with _RAC_LOCK:
                    _RAC_TON.discard(p)
                n += 1
                continue
            Path(p).unlink(missing_ok=True)
        except OSError:
            continue
        with _RAC_LOCK:
            _RAC_TON.discard(p)
        n += 1
    return n


def rac_ton() -> list:
    """Sổ nợ hiện tại (cho test/đo)."""
    with _RAC_LOCK:
        return sorted(_RAC_TON)


# --- TÊN MẢNH TẠM CÓ ĐÓNG DẤU PID: `_seg_p<pid>h<6 hex>_...` -----------------
# Nhờ dấu PID mà lúc mở app phân biệt được "mảnh của lượt xuất ĐANG chạy" (phải
# để yên) với "mảnh của lần chạy trước đã chết" (dọn ngay), thay vì phải đoán
# theo tuổi file 2 giờ như `tempsweep`. Máy anh Hùng tự cập nhật + tắt app giữa
# chừng liên tục nên "đợi 2 giờ" là để rác nằm lại cả buổi.
import re as _re
_MAU_TAG = _re.compile(r"^_seg_p(\d+)h[0-9a-f]{6}_")


def _tag_moi() -> str:
    import uuid
    return f"p{os.getpid()}h{uuid.uuid4().hex[:6]}"


def _pid_con_song(pid: int) -> bool:
    """PID còn sống? Không chắc chắn -> trả True (quy tắc repo: nghi ngờ thì GIỮ)."""
    if pid == os.getpid():
        return True
    try:
        import psutil
        return bool(psutil.pid_exists(pid))
    except Exception:  # noqa: BLE001 - thiếu psutil -> không dám phán
        return True


def don_seg_mo_coi(thu_muc: Optional[str] = None) -> tuple[int, int]:
    """Dọn mảnh `_seg_*` MỒ CÔI của các lần chạy TRƯỚC. Trả (số file, số byte).

    AN TOÀN (đừng nới lỏng — %TEMP% có thể có file của user):
      * CHỈ trong thư mục tạm, CHỈ tên khớp `_seg_p<pid>h<6 hex>_` (mẫu do
        chính app đặt) — file `_seg_*` tên khác (bản app cũ) để `tempsweep`
        dọn theo tuổi 2 giờ, không đụng ở đây.
      * PID còn sống (kể cả CHÍNH MÌNH) -> BỎ QUA: đó là lượt xuất đang chạy.
      * Không đọc được PID / thiếu psutil -> BỎ QUA.
      * Bị khoá -> im lặng bỏ qua, KHÔNG BAO GIỜ ném lỗi ra ngoài.
    """
    import tempfile
    goc = Path(thu_muc or tempfile.gettempdir())
    n = byte = 0
    try:
        ds = list(goc.glob("_seg_*"))
    except OSError:
        return (0, 0)
    for p in ds:
        m = _MAU_TAG.match(p.name)
        if not m:
            continue
        try:
            pid = int(m.group(1))
        except ValueError:
            continue
        if _pid_con_song(pid):
            continue
        try:
            if not p.is_file():
                continue
            sz = p.stat().st_size
            p.unlink()
        except OSError:
            continue
        n += 1
        byte += sz
    return (n, byte)


# Dấu hiệu NGUYÊN NHÂN trong log ffmpeg. ffmpeg in nguyên nhân ở ĐẦU rồi mới in
# một tràng HỆ QUẢ, nên chỉ giữ "6 dòng cuối" là che mất đúng dòng cần đọc — hộp
# lỗi anh Hùng gửi 07/08/2026 toàn hệ quả ("Could not open encoder before EOF",
# "Conversion failed!"), không một chữ nào nói vì sao.
_TU_LOI = ("Error", "error", "Invalid", "invalid", "No such file", "Impossible",
           "Output file is empty", "not found", "moov atom", "Permission denied",
           "Unable to", "Unrecognized", "does not contain", "Cannot")


def _cat_theo_do_dai_that(segs: list, dur: float, src) -> list:
    """KẸP mọi mốc cắt vào [0, độ_dài_THẬT_của_file] trước khi gọi ffmpeg.

    VÌ SAO: độ dài trong DB lấy lúc NHẬP video; nếu file tải thiếu (mạng đứt)
    hoặc bị thay bằng bản ngắn hơn thì Part cuối có mốc vượt phim -> ffmpeg ra
    0 khung. Kẹp lại thì clip vẫn xuất được (ngắn hơn) thay vì mất cả Part.
    Quy tắc chung của repo: KHÔNG đọc được độ dài thì GIỮ NGUYÊN, đừng phán.
    """
    if not dur or dur <= 0:
        return segs
    ra: list = []
    for s, e in segs:
        s2, e2 = max(0.0, min(float(s), dur)), max(0.0, min(float(e), dur))
        if e2 - s2 >= 0.30:          # dưới 0,3s thì không còn là đoạn phim
            ra.append((s2, e2))
    if not ra:
        raise RuntimeError(
            f"Mọi mốc cắt đều nằm ngoài phim: video gốc chỉ dài {dur:.1f}s "
            f"nhưng đoạn cần cắt bắt đầu ở {min(s for s, _ in segs):.1f}s. "
            "Video gốc tải thiếu hoặc đã bị thay — tải lại rồi phân tích lại.")
    return ra


def _gom_log(loi: list, tail: list) -> str:
    """Ghép DÒNG NGUYÊN NHÂN (đầu log) + vài dòng cuối, bỏ trùng, giữ thứ tự."""
    ra: list = []
    for ln in list(loi) + list(tail[-4:]):
        ln = (ln or "").rstrip()
        if ln and ln not in ra:
            ra.append(ln)
    return "\n".join(ra[:10])


def _run_with_fallback(build_cmd, encoder: str, total: float,
                       on_progress, what: str, dst=None) -> None:
    """Chạy ffmpeg với encoder; nếu NVENC lỗi -> thử libx264. Ném lỗi kèm log.

    dst (nếu truyền): file output — sẽ bị XÓA khi thất bại/hủy để không để lại
    .mp4 hỏng mang tên thành phẩm trong thư mục người dùng.
    """
    encoders_to_try = [encoder] if encoder == "libx264" else [encoder, "libx264"]
    last_log = ""
    for enc in encoders_to_try:
        # Đang đóng app (terminate_all_children đã giết ffmpeg NVENC) -> KHÔNG
        # được spawn ffmpeg libx264 mới chạy mồ côi sau khi app tắt.
        if _SHUTDOWN.is_set():
            break
        tail: list[str] = []
        dau: dict = {"rong": False, "loi": []}

        def _line(line: str) -> None:
            tail.append(line)
            if len(tail) > 40:
                tail.pop(0)
            # ĐO 07/08/2026: `-ss` vượt độ dài THẬT của file -> ffmpeg TRẢ MÃ 0
            # kèm output 0 KiB. Không bắt ở đây thì app tưởng XUẤT XONG, ghi
            # clip rỗng vào thư mục thành phẩm rồi XOÁ VIDEO GỐC = mất trắng.
            if "Output file is empty" in line:
                dau["rong"] = True
            if len(dau["loi"]) < 6 and any(k in line for k in _TU_LOI):
                dau["loi"].append(line)
            if on_progress and "time=" in line:
                try:
                    t = line.split("time=")[1].split(" ")[0]
                    h, m, s = t.split(":")
                    cur = int(h) * 3600 + int(m) * 60 + float(s)
                    on_progress(min(1.0, cur / max(0.1, total)))
                except (ValueError, IndexError):
                    pass

        try:
            code = _run(build_cmd(enc), _line)
        except Exception:          # CanceledError (bấm Hủy) hoặc lỗi khác
            _cleanup_dst(dst)
            raise
        if code == 0 and not dau["rong"]:
            return
        if dau["rong"]:
            # Đổi encoder KHÔNG chữa được: rỗng là vì mốc cắt nằm ngoài phim.
            _cleanup_dst(dst)
            raise RuntimeError(
                f"ffmpeg không {what}: file ra RỖNG (0 khung hình). Mốc cắt "
                "nằm NGOÀI độ dài thật của video gốc — video gốc tải thiếu "
                "hoặc đã bị thay. Hãy tải lại video rồi phân tích lại.")
        last_log = _gom_log(dau["loi"], tail)
        if enc == "h264_nvenc":
            # CHỈ đổ lỗi NVENC khi log THẬT SỰ chỉ ra lỗi NVENC/driver.
            # LỖI THẬT (máy user): export hỏng vì lý do KHÁC (filter graph,
            # file nguồn hỏng, đường dẫn...) nhưng nhánh này vẫn ghi
            # ok=false vào cache -> MỌI export sau rơi về CPU libx264 suốt
            # 7 ngày -> "xuất chậm hẳn + máy đơ dù bật tiết kiệm" trong khi
            # GPU hoàn toàn khỏe. (vẫn THỬ libx264 cho lượt này — vô hại.)
            full = "\n".join(tail)
            if _looks_nvenc_failure(full):
                global _ENCODER_CACHE, _NVENC_NOTE
                _ENCODER_CACHE = "libx264"     # phiên này khỏi thử NVENC nữa
                _NVENC_NOTE = _classify_nvenc_error(full)
                # Chỉ GHI CACHE FILE (dính qua các lần mở app) khi lỗi tầm
                # DRIVER/THƯ VIỆN (mọi input đều sẽ hỏng). Lỗi encoder mức
                # input (1 video dị) -> chỉ hạ trong phiên, mở app lại thử lại.
                if _looks_nvenc_env_failure(full):
                    _save_nvenc_cache(False, _NVENC_NOTE)
    _cleanup_dst(dst)
    raise RuntimeError(f"ffmpeg không {what}. Log cuối:\n" + (last_log or "(trống)"))


def export_vertical_clip(
    src: str | Path,
    dst: str | Path,
    start: float,
    end: float,
    crop_keyframes: Optional[list[dict]] = None,
    out_w: int = 1080,
    out_h: int = 1920,
    encoder: Optional[str] = None,
    quality: str = "high",
    mode: str = "face",
    zoom: float = 1.0,
    crop_rect: Optional[tuple] = None,
    text_overlays: Optional[list] = None,
    overlay_png: Optional[str] = None,
    flip_h: bool = False,
    on_progress: Optional[Callable[[float], None]] = None,
) -> bool:
    """
    Cắt [start,end] -> đặt khung 9:16 (mode face/center/fit_blur/manual + zoom hoặc
    crop_rect) -> chèn lớp chữ -> encode, 1 lệnh ffmpeg.

    flip_h: lật gương ngang (hflip) KHỐI video TRƯỚC reframe/overlay -> chỉ hình
            soi gương, chữ overlay KHÔNG ngược.

    overlay_png: ảnh PNG trong suốt (đúng cỡ out_w×out_h) chứa toàn bộ chữ/nền —
                 ưu tiên dùng (render từ UI nên xem trước == xuất). Nếu không có,
                 fallback text_overlays (drawtext).
    """
    encoder = encoder or detect_encoder()
    out_w, out_h = khung_chan(out_w, out_h)
    dur = max(0.1, end - start)

    cx = 0.5
    if crop_keyframes:
        xs = [float(k.get("cx", 0.5)) for k in crop_keyframes if "cx" in k]
        if xs:
            cx = sum(xs) / len(xs)

    use_png = bool(overlay_png and os.path.exists(overlay_png))
    has_text = (not use_png) and any(o.get("text") for o in (text_overlays or []))
    base_out = "vr" if (use_png or has_text) else "v"
    # LẬT GƯƠNG: hflip lên video gốc TRƯỚC reframe (và trước overlay/chữ) -> chỉ
    # hình soi gương, chữ overlay chồng sau nên KHÔNG ngược.
    vin = "0:v"
    pre = ""
    if flip_h:
        pre = "[0:v]hflip[vflip];"
        vin = "vflip"
    base = reframe_chain(mode, cx, out_w, out_h, zoom, vin, base_out, "0",
                         crop_rect=crop_rect)
    base = pre + base
    if use_png:
        fc = base + ";[vr][1:v]overlay=0:0[v]"
    elif has_text:
        fc = base + ";" + _text_chain(text_overlays, out_h, "vr", "v")
    else:
        fc = base

    def build(enc: str) -> list[str]:
        # -ss và -t ĐỀU là input-option của video gốc (trước -i) để cắt đúng
        # thời lượng kể cả khi có thêm input PNG.
        cmd = [settings.FFMPEG_PATH, "-y", *_global_enc_opts(),
               "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src)]
        if use_png:
            cmd += ["-i", str(overlay_png)]
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                *_enc_args(enc, quality),
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)]
        return cmd

    _run_with_fallback(build, encoder, dur, on_progress, "xuất được clip",
                       dst=dst)
    return True


def export_stitched_clip(
    src: str | Path,
    dst: str | Path,
    moments: list[dict],
    out_w: int = 1080,
    out_h: int = 1920,
    encoder: Optional[str] = None,
    quality: str = "high",
    mode: str = "face",
    zoom: float = 1.0,
    text_overlays: Optional[list] = None,
    overlay_png: Optional[str] = None,
    flip_h: bool = False,
    on_progress: Optional[Callable[[float], None]] = None,
) -> bool:
    """
    GHÉP nhiều đoạn rời rạc thành 1 video dọc 9:16, trong DUY NHẤT 1 lệnh ffmpeg
    (filter_complex concat — không file tạm). overlay_png (nếu có) chèn lên toàn clip.

    flip_h: lật gương ngang (hflip) từng đoạn video TRƯỚC reframe/concat/overlay
            -> chỉ hình soi gương, chữ overlay KHÔNG ngược.
    """
    moments = [m for m in (moments or []) if m["end"] > m["start"]]
    if not moments:
        raise RuntimeError("Mixed-Cut không có đoạn nào để ghép.")
    encoder = encoder or detect_encoder()
    out_w, out_h = khung_chan(out_w, out_h)
    total = sum(m["end"] - m["start"] for m in moments)
    # Video KHÔNG có luồng tiếng (screen-record...) -> atrim/concat a=1 sẽ fail;
    # ghép chỉ hình.
    has_audio = probe(src).has_audio

    # MỖI ĐOẠN = 1 INPUT seek riêng (như export_canvas_clip): 1 input + trim
    # fan-out làm frame các đoạn SAU xếp hàng chờ ở concat -> RAM ffmpeg phình
    # không giới hạn (đo 19.6GB) khi encoder chậm hơn decoder.
    parts, labels, seg_in = [], [], []
    for i, m in enumerate(moments):
        s, e = m["start"], m["end"]
        cx = float(m.get("cx", 0.5))
        # `-threads` phải LẶP trước TỪNG `-i` (ffmpeg "tiêu" nó cho đúng đầu
        # vào ngay sau đó) — xem chú thích dài ở `_build_xf` của pha 1.5, nơi
        # lỗi này đo được **133 luồng = 5,54× nhân**. Ở đây n đầu vào đều là
        # CÙNG một file nguồn nên chia đều ngân sách giải mã.
        seg_in += ["-threads", str(max(1, decode_threads() // max(1, len(moments)))),
                   "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src)]
        # LẬT GƯƠNG: hflip TRƯỚC reframe/concat/overlay -> chỉ hình soi
        # gương, overlay chữ + phụ đề chồng sau nên KHÔNG ngược.
        flip_f = "hflip," if flip_h else ""
        parts.append(f"[{i}:v]{flip_f}setpts=PTS-STARTPTS[pv{i}]")
        parts.append(reframe_chain(mode, cx, out_w, out_h, zoom,
                                   f"pv{i}", f"v{i}", str(i)))
        if has_audio:
            parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
            labels.append(f"[v{i}][a{i}]")
        else:
            labels.append(f"[v{i}]")
    n = len(moments)
    use_png = bool(overlay_png and os.path.exists(overlay_png))
    has_text = (not use_png) and any(o.get("text") for o in (text_overlays or []))
    vout = "[vcat]" if (use_png or has_text) else "[v]"
    a_flag = 1 if has_audio else 0
    parts.append("".join(labels) + f"concat=n={n}:v=1:a={a_flag}{vout}"
                 + ("[a]" if has_audio else ""))
    if use_png:
        parts.append(f"[vcat][{n}:v]overlay=0:0[v]")
    elif has_text:
        parts.append(_text_chain(text_overlays, out_h, "vcat", "v"))
    fc = ";".join(parts)

    def build(enc: str) -> list[str]:
        cmd = [settings.FFMPEG_PATH, "-y", *_global_enc_opts(), *seg_in]
        if use_png:
            cmd += ["-i", str(overlay_png)]
        cmd += ["-filter_complex", fc, "-map", "[v]"]
        if has_audio:
            cmd += ["-map", "[a]"]
        cmd += [*_enc_args(enc, quality),
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)]
        return cmd

    _run_with_fallback(build, encoder, total, on_progress, "ghép được Mixed-Cut",
                       dst=dst)
    return True


def detect_black_crop(src: str | Path, t: float = 0.0,
                      dur: float = 2.0) -> Optional[str]:
    """Dò viền đen bằng cropdetect -> 'W:H:X:Y' hoặc None nếu không cần cắt."""
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-ss", f"{max(0, t):.3f}",
           "-i", str(src), "-t", f"{dur:.3f}",
           "-vf", "cropdetect=24:2:0", "-f", "null", "-"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", creationflags=_CREATE_NO_WINDOW,
                             timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    crop = None
    for line in (out.stderr or "").splitlines():
        i = line.find("crop=")
        if i != -1:
            crop = line[i + 5:].strip().split()[0]
    # Cảnh mở đầu TỐI/ĐEN hoàn toàn -> cropdetect trả giá trị 0/ÂM (vd
    # "0:0:-1:-1") — đưa vào filter crop sẽ làm ffmpeg fail 100%. Validate kỹ.
    if crop:
        try:
            w, h, x, y = (int(float(v)) for v in crop.split(":")[:4])
        except (ValueError, IndexError):
            return None
        if w < 16 or h < 16 or x < 0 or y < 0:
            return None
    return crop


def fit_src_video_rect(video_rect: tuple, src_w: int, src_h: int,
                       out_w: int, out_h: int) -> tuple:
    """KHUNG TỰ KHỚP TỈ LỆ VIDEO GỐC (không mất hình).

    Mẫu lưu video_rect=(cx, cy, scale_w) theo tỉ lệ video LÚC TẠO MẪU; nguồn
    reup tỉ lệ khác (1:1, 16:9...) scale theo bề ngang đó sẽ TRÀN canvas
    1080x1920 -> bị cắt mất 2 bên/trên dưới. Hàm này tính lại khung theo tỉ lệ
    NGUỒN: giữ TÂM (cx,cy) + BỀ NGANG mẫu, chiều cao = w_px*(src_h/src_w);
    nếu khung tràn canvas (cao/rộng quá) -> THU CẢ KHUNG lại vừa canvas (giữ
    tỉ lệ nguồn); cuối cùng nắn tâm tối thiểu để khung nằm TRỌN trong canvas
    -> video hiện đủ 100%, nền (blur/đen/trắng) lấp phần thừa.

    GIỮ THU PHÓNG CỦA USER: scale_w > 1 nghĩa là user CHỦ ĐỘNG phóng to khối
    video vượt bề ngang canvas (chấp nhận cắt 2 bên) — bề ngang KHÔNG phụ
    thuộc tỉ lệ nguồn nên sw>1 chỉ có thể là ý user. Trường hợp này KHÔNG
    thu nhỏ lại (trước đây k=min(...) kéo về 1.0 -> 'xuất không theo thu
    phóng'). Chỉ khi sw<=1 (mẫu bình thường) mới thu khung cho nguồn quá
    cao/rộng nằm trọn canvas như cũ. Nắn tâm chỉ áp theo TRỤC mà khung còn
    lọt trong canvas (khung to hơn canvas thì giữ tâm user).

    Trả (cx, cy, scale_w) mới. src_w/src_h <= 0 -> trả nguyên (không đoán mò).
    """
    cx, cy, sw = (float(video_rect[0]), float(video_rect[1]),
                  float(video_rect[2]))
    if src_w <= 0 or src_h <= 0 or sw <= 0:
        return video_rect
    w_px = sw * out_w                      # bề ngang khung mẫu (pixel canvas)
    h_px = w_px * src_h / src_w            # cao theo TỈ LỆ NGUỒN (scale=vw:-2)
    if sw <= 1.0:                          # mẫu thường -> giữ trọn hình như cũ
        k = min(1.0, out_w / w_px, out_h / h_px)   # tràn -> thu cả khung
        w_px *= k
        h_px *= k
    # Nắn tâm TỐI THIỂU để khung nằm trọn trong canvas — CHỈ theo trục khung
    # còn lọt (nửa khung <= nửa canvas); khung phóng to quá canvas -> giữ tâm.
    hw, hh = w_px / (2 * out_w), h_px / (2 * out_h)
    if hw <= 0.5:
        cx = min(max(cx, hw), 1.0 - hw)
    if hh <= 0.5:
        cy = min(max(cy, hh), 1.0 - hh)
    return (round(cx, 4), round(cy, 4), round(w_px / out_w, 4))


# ==================== CHUYỂN CẢNH Ở CHỖ GHÉP ĐOẠN (xfade) ====================
# VÌ SAO CHỌN xfade chứ không phải hiệu ứng filter (flicker/zoom/glitch/film):
# 0 file tải về, 0 rủi ro bản quyền, **KHÔNG sửa màu nên không thể loè**, và nó
# chữa đúng chỗ đang **cắt cụt khô khốc** giữa 2 đoạn.
#
# 58 kiểu của filter `xfade` (bỏ 'custom' vì cần biểu thức riêng). Giữ danh sách
# ở đây để cổng test đối chiếu được với `ffmpeg -h filter=xfade` của bản đang
# đóng gói — máy khách dùng ĐÚNG ffmpeg trong `bin/`, nhưng ai đổi bản ffmpeg mà
# kiểu bị gỡ thì phải FAIL to, KHÔNG được im lặng ra clip cắt khô.
XFADE_KIEU: tuple = (
    "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circlecrop", "rectcrop", "distance", "fadeblack", "fadewhite", "radial",
    "smoothleft", "smoothright", "smoothup", "smoothdown",
    "circleopen", "circleclose", "vertopen", "vertclose",
    "horzopen", "horzclose", "dissolve", "pixelize",
    "diagtl", "diagtr", "diagbl", "diagbr",
    "hlslice", "hrslice", "vuslice", "vdslice",
    "hblur", "fadegrays", "wipetl", "wipetr", "wipebl", "wipebr",
    "squeezeh", "squeezev", "zoomin", "fadefast", "fadeslow",
    "hlwind", "hrwind", "vuwind", "vdwind",
    "coverleft", "coverright", "coverup", "coverdown",
    "revealleft", "revealright", "revealup", "revealdown",
)

# 4 MỨC cho ô chọn trong Chỉnh mẫu. "tat" = đường cũ Y NGUYÊN (bất biến sống
# còn: preset cũ phải ra file giống hệt `main`).
CHUYEN_CANH_MUC: tuple = ("tat", "nhe", "vua", "manh")
CHUYEN_CANH_NHAN: dict = {
    "tat": "Tắt (cắt thẳng như cũ)",
    "nhe": "Nhẹ (mờ dần — khuyên dùng)",
    "vua": "Vừa (mờ + trượt nhẹ)",
    "manh": "Mạnh (trượt / mở khép rõ)",
}

# LUẬT CHỌN KIỂU — KHÔNG RANDOM. Dùng lại ĐÚNG khuôn đã chạy tốt cho TIẾNG ĐỘNG
# (`m1_highlight._loai_theo_khoang_nhay`): suy theo **NỘI DUNG chỗ nối**, không
# bốc thăm. Lý do phải thế: luật cũ của tiếng động làm MỌI Part một tiếng "ding"
# — đúng cái anh Hùng sợ ("thêm ngẫu nhiên k hợp cảnh k hợp logic gì cả").
#   nguoc  : nhảy NGƯỢC thời gian (hook-first đưa cao trào lên đầu) -> cắt phũ
#            giữa 2 mạch, cần chuyển DỨT KHOÁT.
#   lien   : gần liền mạch (<= 1,2s, chỉ bỏ mấy giây thừa) -> hình gần như
#            không đổi, phải MỀM, hiệu ứng rõ ở đây là lố.
#   chot   : đoạn KẾ rất ngắn (< 2,5s = câu chốt/punchline) -> nhấn.
#   xa     : nhảy xa = đổi bối cảnh -> chuyển trung tính.
# Mỗi (mức, loại) cho 2 kiểu; chọn theo CHỈ SỐ điểm nối (i % 2) -> cùng 1 video
# KHÔNG lặp một kiểu ở mọi chỗ nối, mà vẫn TIỀN ĐỊNH (test lại được, không phụ
# thuộc seed).
_XF_LUAT: dict = {
    "nhe": {"nguoc": ("fadeblack", "fade"), "lien": ("dissolve", "fade"),
            "chot": ("fadewhite", "fade"), "xa": ("fade", "dissolve")},
    "vua": {"nguoc": ("fadeblack", "wipeleft"), "lien": ("dissolve", "smoothleft"),
            "chot": ("fadewhite", "circleclose"), "xa": ("fade", "smoothright")},
    "manh": {"nguoc": ("slideleft", "wipeleft"), "lien": ("smoothleft", "smoothright"),
             "chot": ("circleclose", "squeezev"), "xa": ("slideup", "horzclose")},
}
# Thời lượng (giây) theo loại chỗ nối × mức. Khoảng cho phép 0,25-0,4s như đã
# chốt; ngắn hơn 0,2s thì mắt không kịp thấy, dài hơn 0,4s là "chậm như slide".
_XF_DAI: dict = {
    "nhe": {"nguoc": 0.25, "lien": 0.30, "chot": 0.30, "xa": 0.25},
    "vua": {"nguoc": 0.25, "lien": 0.30, "chot": 0.35, "xa": 0.30},
    "manh": {"nguoc": 0.30, "lien": 0.35, "chot": 0.40, "xa": 0.35},
}


def _loai_cho_noi(segs: list, i: int) -> str:
    """Loại chỗ nối thứ i suy từ NỘI DUNG (y khuôn `_loai_theo_khoang_nhay`).
    Hàm thuần — test được, không đọc settings."""
    try:
        het = float(segs[i][1])
        bat, het_ke = float(segs[i + 1][0]), float(segs[i + 1][1])
    except (IndexError, TypeError, ValueError):
        return "xa"
    nhay = bat - het
    if nhay < -0.05:
        return "nguoc"
    if nhay <= 1.2:
        return "lien"
    if (het_ke - bat) < 2.5:
        return "chot"
    return "xa"


def chon_chuyen_canh(segs: list, muc: str = "nhe") -> list:
    """[(kiểu_xfade, thời_lượng_giây)] cho TỪNG chỗ nối, suy theo nội dung.

    Trả [] khi: mức 'tat'/rỗng/lạ, hoặc clip chỉ 1 đoạn (không có chỗ nối).
    Hàm THUẦN (không đọc settings, không gọi ffmpeg) -> unit test được.
    """
    m = str(muc or "").strip().lower()
    if m not in _XF_LUAT or len(segs or []) < 2:
        return []
    # Mức 'manh' + máy CÓ OpenCL -> dùng kho kernel GPU (21 kiểu gl-transitions,
    # MIT). Máy nhân viên thiếu OpenCL -> `gpu` rỗng -> đường CPU y như cũ,
    # KHÔNG một dòng lỗi (fallback ÊM, cổng 37 có ca này).
    gpu = set(co_chuyen_canh_gpu()) if m == "manh" else set()
    ra: list = []
    for i in range(len(segs) - 1):
        loai = _loai_cho_noi(segs, i)
        cap = _XF_LUAT[m][loai]
        kieu = cap[i % len(cap)]
        if gpu:
            cap_g = [k for k in _XF_GPU[loai] if k in gpu]
            if cap_g:
                kieu = cap_g[i % len(cap_g)]
        ra.append((kieu, float(_XF_DAI[m][loai])))
    return ra


def _bu_xfade(segs: list, chuyen: list, dur_nguon: float) -> list:
    """Số giây PHẢI LẤY THÊM ở CUỐI mỗi đoạn để xfade KHÔNG làm clip ngắn đi.

    ĐÂY LÀ CHỖ DỄ SẬP NHẤT CỦA VIỆC NÀY. `xfade` ĂN BỚT `d` giây ở mỗi chỗ nối:
    output = dài(A) + dài(B) - d. Không bù thì clip NGẮN đi (n-1)*d giây, mà
    phụ đề `.ass` và mốc tiếng động đã dựng theo timeline "các đoạn nối thẳng"
    -> **LỆCH HẾT** từ chỗ nối đầu tiên trở đi (0,3s × 3 chỗ nối = lệch 0,9s).

    CÁCH BÙ (giữ timeline BẤT BIẾN, không phải sửa .ass): lấy THÊM đúng `d` giây
    phim ở SAU đoạn A, rồi đặt `offset = dài_gốc(A)`. Khi đó:
      - t < a          : khung của A (y như nối thẳng)
      - a <= t < a+d   : A (phần lấy thêm) hoà với B[0..d] — chỗ chuyển cảnh
      - t >= a+d       : B[t-a]  (y như nối thẳng)
    Tổng = a + b, và MỌI khung của B rơi ĐÚNG mốc cũ -> lệch phụ đề = 0 về mặt
    toán học (đo thật vẫn phải làm, xem cổng `_test_chuyen_canh.py`).

    Hết phim thì không có gì mà lấy thêm: THU NGẮN d còn đúng phần còn lại;
    dưới 0,08s thì trả 0 = chỗ nối đó CẮT THẲNG như cũ (thà cụt 1 chỗ còn hơn
    lệch tiếng-hình cả clip). KHÔNG lùi đầu đoạn B để bù — làm thế là dịch nội
    dung B sớm lên, đúng kiểu lỗi "hình một đằng tiếng một đằng" của v1.87.

    **KẸP THEO ĐỘ DÀI ĐOẠN KẾ — LỖI THẬT ĐÃ ĐO 08/08/2026, đừng gỡ.** `xfade`
    (hình) và `acrossfade` (tiếng) xử lý "đoạn B NGẮN HƠN d" **KHÁC NHAU**: hình
    ra đúng `a+b`, còn tiếng ra `a+d`. Đo thật (A gốc 2,0s, đã bù):

    | B dài | d    | hình ra | tiếng ra | lệch |
    |-------|------|---------|----------|------|
    | 0,20  | 0,40 | 2,200   | 2,400    | **200 ms** |
    | 0,20  | 0,30 | 2,200   | 2,300    | **100 ms** |
    | 0,30  | 0,40 | 2,300   | 2,400    | **100 ms** |
    | 0,30  | 0,30 | 2,300   | 2,300    | 0 ms |

    Mốc cho phép là **80 ms**. Ca này app TỰ ĐẨY MÌNH VÀO: `_loai_cho_noi` gọi
    một chỗ nối là `'chot'` **đúng khi đoạn kế < 2,5s**, mà `_XF_DAI` cho
    `'chot'` thời lượng DÀI NHẤT (vua 0,35s · manh 0,40s); còn
    `_cat_theo_do_dai_that` cho đoạn ngắn tới **0,30s** (Part cuối bị kẹp vào mép
    phim). Mức mặc định `'nhe'` vừa đúng 0,30 nên thoát, `'vua'`/`'manh'` thì
    KHÔNG. Vì vậy `d` phải <= độ dài ĐOẠN KẾ.
    """
    ra: list = []
    segs = list(segs or [])
    for i, (_k, d) in enumerate(chuyen or []):
        try:
            het = float(segs[i][1])
            dai_ke = float(segs[i + 1][1]) - float(segs[i + 1][0])
        except (IndexError, TypeError, ValueError):
            ra.append(0.0)
            continue
        con = max(0.0, float(dur_nguon or 0.0) - het)
        d2 = min(float(d), con) if dur_nguon else float(d)
        d2 = min(d2, max(0.0, dai_ke))          # <= độ dài ĐOẠN KẾ
        ra.append(round(d2, 3) if d2 >= 0.08 else 0.0)
    return ra


def _graph_xfade(n: int, chuyen: list, bu: list, dai_goc: list,
                 co_tieng: bool) -> tuple[str, str, str]:
    """Filter graph nối n đoạn bằng xfade (+ acrossfade cho tiếng).

    Trả (graph, nhãn_video, nhãn_tiếng|""). offset TÍCH LUỸ theo ĐỘ DÀI GỐC
    (không cộng phần bù) — xem `_bu_xfade` để biết vì sao đúng.
    Chỗ nối có bù = 0 -> dùng `concat` (cắt thẳng) để không ăn bớt thời lượng.
    settb/setpts: mọi đoạn phải cùng timebase và bắt đầu từ 0, nếu không xfade
    tính offset trên PTS gốc -> chuyển cảnh nổ ra sai chỗ (hoặc mất hẳn).
    """
    p: list = []
    for i in range(n):
        p.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
        if co_tieng:
            p.append(f"[{i}:a]asetpts=N/SR/TB[a{i}]")
    vcur, acur = "[v0]", "[a0]"
    moc = 0.0
    for i in range(n - 1):
        moc += float(dai_goc[i])
        d = float(bu[i]) if i < len(bu) else 0.0
        vo, ao = f"[xv{i}]", f"[xa{i}]"
        if d >= 0.08:
            kieu = str(chuyen[i][0])
            p.append(f"{vcur}[v{i + 1}]xfade=transition={kieu}:"
                     f"duration={d:.3f}:offset={moc:.3f}{vo}")
            if co_tieng:
                p.append(f"{acur}[a{i + 1}]acrossfade=d={d:.3f}:"
                         f"c1=tri:c2=tri{ao}")
        else:
            p.append(f"{vcur}[v{i + 1}]concat=n=2:v=1:a=0{vo}")
            if co_tieng:
                p.append(f"{acur}[a{i + 1}]concat=n=2:v=0:a=1{ao}")
        vcur, acur = vo, ao
    return ";".join(p), vcur, (acur if co_tieng else "")


#: Kiểu chuyển cảnh GPU thay cho kiểu CPU nào (dùng khi máy KHÔNG có OpenCL ->
#: LÙI ÊM về `xfade` CPU, KHÔNG một dòng lỗi). Ánh xạ theo CÁI MẮT THẤY, không
#: theo tên: `gl_gon_song` (gợn sóng lan) gần `dissolve` nhất, `gl_gat_trai`
#: (gạt mềm) gần `slideleft`…
GPU_LUI_VE: dict = {
    "gl_crosswarp": "dissolve", "gl_gat_trai": "slideleft",
    "gl_gat_len": "slideup", "gl_gat_cheo_meo": "smoothleft",
    "gl_gio": "hlwind", "gl_gon_song": "dissolve",
    "gl_vo_o": "pixelize", "gl_luoi_vuong": "diagtl",
    "gl_quat_quay": "radial", "gl_gach_cheo": "diagtl",
    "gl_nhoe_mo": "hblur", "gl_xoay_tron": "circleclose",
    "gl_bien_hinh": "dissolve", "gl_soc_doc": "vertopen",
    "gl_o_ngau": "pixelize", "gl_giot_nuoc": "circleopen",
    "gl_kim_dong_ho": "radial", "gl_vong_mo": "hblur",
    "gl_chong_chong": "radial", "gl_troi_mem": "smoothright",
    "gl_giat_khoi": "pixelize",
}
#: Ở mức 'manh' — và CHỈ mức đó — mỗi loại chỗ nối được phép dùng 2 kernel GPU.
#: Vì sao chỉ 'manh': đây là mức anh Hùng chọn khi muốn "thấy rõ nhất", và nhóm
#: GPU tốn **2n lệnh ffmpeg/clip** thay vì n+1 (đo: GPU KHÔNG rẻ hơn CPU,
#: 1,03x CPU-giây) nên không đáng ép lên mức mặc định của 200-300 kênh.
_XF_GPU: dict = {
    "nguoc": ("gl_giat_khoi", "gl_gat_trai"),
    "lien": ("gl_crosswarp", "gl_gon_song"),
    "chot": ("gl_xoay_tron", "gl_giot_nuoc"),
    "xa": ("gl_troi_mem", "gl_quat_quay"),
}


def co_chuyen_canh_gpu() -> list:
    """Khoá chuyển cảnh GPU dùng được trên máy này (rỗng = tự lùi về CPU)."""
    try:
        from app.core import hieu_ung_gpu as _HG
        return _HG.dung_duoc()
    except Exception:      # noqa: BLE001 — thiếu module không được làm chết xuất
        return []


def _enc_mezz(enc: str) -> list:
    """Tham số encoder của mảnh mezzanine — DÙNG CHUNG cho mọi mảnh.

    `concat` demuxer đòi mọi mảnh CÙNG thông số; mảnh thân và mảnh chuyển cảnh
    GPU phải ra từ đúng một bộ tham số này, lệch một cái là ffmpeg im lặng bỏ
    mảnh hoặc ra clip giật.

    **LỖI THẬT ĐO ĐƯỢC 08/08/2026 (có từ bản `main`, KHÔNG phải hồi quy):**
    nhánh `libx264` THIẾU `-pix_fmt yuv420p` trong khi nhánh nvenc có. Mảnh
    THÂN vào từ file nên ra `yuv420p`, còn mảnh CHUYỂN CẢNH đi qua
    `filter_complex` (`xfade`) thì x264 tự chọn **`yuv444p`**:
        pix_fmt các mảnh = [yuv420p, **yuv444p**, yuv420p, **yuv444p**, yuv420p]
    Lệch pix_fmt giữa các file làm ffmpeg **DỰNG LẠI filter graph** ở mỗi mảnh,
    mà `metadata=print:file=` MỞ LẠI FILE Ở CHẾ ĐỘ GHI ĐÈ mỗi lần dựng lại ->
    `hieu_ung.do_nhip` chỉ còn số đo của MẢNH CUỐI: **4 giây trên 16** -> dải
    động phẳng -> `chon_hieu_ung` trả **0 ĐIỂM NHẤN**. Đo cùng clip, cùng máy:
        libx264      -> đo được  4s/16s -> **0** điểm nhấn
        h264_nvenc   -> đo được 16s/16s -> **3** điểm nhấn
    Nghĩa là MÁY NHÂN VIÊN (không NVENC) và mọi lượt NVENC lùi về CPU đều
    **mất sạch hiệu ứng điểm nhấn mà không một dòng báo** — đúng câu anh Hùng
    hỏi *"làm sao để biết có thêm hiệu ứng hay âm thanh gì k"*.
    """
    if enc == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p1", "-rc", "vbr",
                "-cq", "16", "-pix_fmt", "yuv420p",
                "-threads", str(encode_threads())]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
            "-pix_fmt", "yuv420p",       # BẮT BUỘC: xem docstring
            "-threads", str(encode_threads())]


def _tach_va_noi_manh(src, segs: list, xf: list, bu: list, encoder: str,
                      fps: float, co_tieng: bool, tdir: str, tag: str,
                      temps: list, on_progress=None,
                      dung_gpu: bool = True) -> list:
    """PHA 1 + 1.5 KIỂU "2n−1 MẢNH" — trả danh sách mảnh theo ĐÚNG thứ tự nối.

    KHÁC đường "nối cả clip" ở CHỖ NÀO: đường cũ tách n mezzanine rồi nối bằng
    1 lệnh `xfade` -> **encode LẠI TOÀN CLIP thêm một lượt nữa**. Ở đây chỉ
    encode lại **đúng cửa sổ chuyển cảnh** (0,25-0,4 giây/chỗ nối):

        thân_0 · chuyển_0 · thân_1 · chuyển_1 · thân_2 …

    trong đó (dùng lại đúng phép bù của `_bu_xfade`, timeline BẤT BIẾN):
      thân_j    = src[ s_j + bu[j-1] .. e_j ]      (bỏ `bu[j-1]` giây đã bị
                                                    chuyển cảnh trước ăn mất)
      chuyển_i  = hoà( src[e_i .. e_i+bu[i]] , src[s_{i+1} .. s_{i+1}+bu[i]] )
    Tổng = Σ(e_j − s_j) — **đúng bằng đường cắt thẳng**, nên `.ass` và mốc
    tiếng động KHÔNG phải sửa một dòng nào.

    `dung_gpu=True`  -> `xfade_opencl` + kernel gl-transitions (mức 'manh').
      Đường này BẮT BUỘC phải cắt mảnh: `xfade_opencl` **không nối cả clip
      được** (bẫy #1 trong docstring `hieu_ung_gpu`: 2 `hwupload` = 2 ngữ cảnh
      khung -> ffmpeg chết ngay khi hết chuyển cảnh, ra clip CỤT TRONG IM LẶNG).
    `dung_gpu=False` -> `xfade` CPU thường (mức 'nhe'/'vua').
      Đường này KHÔNG bắt buộc, nhưng RẺ HƠN HẲN — xem `_extract_segments_to_temp`.

    SỐ LỆNH ffmpeg = **2n−1** (đường nối-cả-clip là n+1): 2 đoạn 3 vs 3,
    3 đoạn 5 vs 4. Ném lỗi -> caller LÙI ÊM (GPU về CPU; CPU về nối-cả-clip).
    """
    if dung_gpu:
        from app.core import hieu_ung_gpu as _HG
        ker = _HG.duong_kernel()
        if not ker:
            raise RuntimeError("thiếu gl_transitions.cl")
        dv = _HG.dau_vao(fps)
    else:
        _HG = ker = None                    # noqa: F841 - chỉ dùng ở nhánh GPU
        # Cùng công thức chuẩn hoá đầu vào như đường GPU (trừ `hwupload`):
        # `settb` + `fps` cố định để `xfade` tính offset trên timebase ổn định.
        dv = f"format=yuv420p,fps={max(1.0, float(fps)):g},setpts=PTS-STARTPTS"
    n = len(segs)
    ra: list = []
    # ĐẾM BẰNG SỐ KHUNG, KHÔNG bằng giây. Mỗi mảnh riêng lẻ bị làm tròn LÊN
    # trọn khung, mà `concat` demuxer thì CỘNG DỒN: đo thật clip 3 đoạn ra
    # **17,067s thay vì 17,000s** (+4 khung). 4 đoạn sẽ là +7 khung = 0,117s,
    # VƯỢT mốc lệch tiếng-hình 80 ms. Chốt số khung từng mảnh thì tổng khung =
    # tổng khung của đường cắt thẳng -> lệch 0.
    nd = [int(round(float(b) * fps)) for b in bu]
    for j, (s, e) in enumerate(segs):
        n_truoc = nd[j - 1] if j > 0 else 0
        ss = s + n_truoc / fps
        nb = int(round((float(e) - float(s)) * fps)) - n_truoc
        if nb < 1:
            raise RuntimeError(f"thân đoạn {j + 1} còn {nb} khung")
        than = os.path.join(tdir, f"_seg_{tag}_b{j}.mkv")
        temps.append(than)

        def _b(enc: str, _s=ss, _n=nb, _p=than) -> list:
            c = [settings.FFMPEG_PATH, "-y", "-threads", str(decode_threads()),
                 "-ss", f"{_s:.3f}", "-t", f"{_n / fps + 1.0 / fps:.6f}",
                 "-i", str(src)]
            c += _enc_mezz(enc) + ["-r", f"{fps:g}", "-fps_mode:v", "cfr",
                                   "-frames:v", str(_n),
                                   "-t", f"{_n / fps:.6f}"]
            if co_tieng:
                c += ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
            return c + [_p]

        if on_progress:
            on_progress((j / max(1, n)) * 0.999)
        _run_with_fallback(_b, encoder, nb / fps, None,
                           f"tách thân đoạn {j + 1}/{n} (GPU)", dst=than)
        ra.append(than)
        if j >= n - 1:
            break
        d = nd[j] / fps                 # đúng số khung, không phải giây tròn
        kieu = str(xf[j][0])
        cv = os.path.join(tdir, f"_seg_{tag}_g{j}.mkv")
        temps.append(cv)
        if dung_gpu:
            graph = (f"[0:v]{dv},hwupload[a];[1:v]{dv},hwupload[b];"
                     f"[a][b]xfade_opencl=transition=custom:"
                     f"source='{_HG.duong_filter(ker)}':kernel={kieu}:"
                     f"duration={d:.3f}:offset=0[o];[o]{_HG.VE_LAI_MOC}[v]")
        else:
            graph = (f"[0:v]{dv}[a];[1:v]{dv}[b];"
                     f"[a][b]xfade=transition={kieu}:"
                     f"duration={d:.3f}:offset=0[v]")
        if co_tieng:
            graph += f";[0:a][1:a]acrossfade=d={d:.3f}:c1=tri:c2=tri[ao]"

        def _g(enc: str, _a=e, _b=segs[j + 1][0], _d=d, _n=nd[j], _g=graph,
               _p=cv, _gpu=dung_gpu) -> list:
            # 2 đầu vào -> chia đôi ngân sách giải mã (xem `_build_xf`)
            c = [settings.FFMPEG_PATH, "-y"]
            if _gpu:
                c += ["-init_hw_device", "opencl=ocl",
                      "-filter_hw_device", "ocl"]
            c += ["-threads", str(max(1, decode_threads() // 2)),
                  "-filter_complex_threads", str(min(4, encode_threads())),
                  "-ss", f"{_a:.3f}", "-t", f"{_d + 1.0 / fps:.6f}",
                  "-i", str(src),
                  "-ss", f"{_b:.3f}", "-t", f"{_d + 1.0 / fps:.6f}",
                  "-i", str(src),
                  "-filter_complex", _g, "-map", "[v]"]
            if co_tieng:
                c += ["-map", "[ao]"]
            # `-frames:v` + `-t` ở ĐẦU RA chốt mảnh ĐÚNG SỐ KHUNG. Trước đây
            # chỉ có `-frames:v int(d*fps)+3` thì 3 khung dư thành ĐỘ DÀI THẬT
            # (đo: clip 3 đoạn 17,067s thay vì 17,000s). `-frames:v` vẫn là
            # PHANH CUỐI cho tai nạn "sinh khung vô tận, 19 GB RAM".
            c += ["-frames:v", str(_n), "-t", f"{_d:.6f}"]
            c += _enc_mezz(enc) + ["-r", f"{fps:g}", "-fps_mode:v", "cfr"]
            if co_tieng:
                c += ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
            return c + [_p]

        _run_with_fallback(
            _g, encoder, d, None,
            f"chuyển cảnh {'GPU' if dung_gpu else 'CPU'} {kieu} "
            f"({j + 1}/{n - 1})", dst=cv)
        # `co_opencl()` đã đếm khung lúc dò máy, nhưng mảnh THẬT vẫn phải kiểm:
        # `xfade_opencl` từng ra file CÓ KÍCH THƯỚC mà **0 KHUNG** (rc=0, im
        # lặng). 0 khung ở đây = clip mất hẳn chỗ nối -> thà lùi về đường cũ.
        # Đường CPU cũng kiểm: rẻ (đọc 1 lần) và bắt được mọi ca "rc=0 mà rỗng".
        from app.core import hieu_ung_gpu as _HG2
        if _HG2._dem_khung(cv) < 1:
            raise RuntimeError(f"mảnh chuyển cảnh {kieu} ra 0 khung")
        ra.append(cv)
    return ra


def _extract_segments_to_temp(src, segs: list, encoder: str,
                              on_progress=None,
                              chuyen_canh: Optional[list] = None,
                              temps_out: Optional[list] = None
                              ) -> tuple[str, list]:
    """PHA 1 của ghép nhiều đoạn: TÁCH từng đoạn ra FILE TẠM (.mkv, mezzanine
    chất lượng cao) rồi trả (đường_dẫn_file_danh_sách_concat, [file_tạm]).

    VÌ SAO 2 PHA (bài học 2 lỗi thật):
    - 1 lệnh trim+concat: decoder chạy trước encoder -> frame các đoạn sau
      xếp hàng ở concat, RAM phình 19.6GB (máy đơ cứng, RAM 97%).
    - 1 nhánh select (bản vá RAM v1.87): frame LUÔN ra theo dòng thời gian
      GỐC, nhưng hook-first xếp đoạn KHÔNG theo thứ tự thời gian + audio đi
      atrim theo THỨ TỰ DANH SÁCH -> hình một đằng tiếng một đằng, caption
      lệch hết (lỗi user báo).
    2 pha: mỗi đoạn 1 lệnh -ss/-t riêng (RAM phẳng, tiếng-hình cắt CÙNG NHAU
    nên khớp tuyệt đối), concat demuxer nối THEO THỨ TỰ DANH SÁCH (hook-first
    đúng), ép CFR đều nhau (nguồn VFR YouTube không còn trôi lệch).
    Mezzanine cq/crf 16 + pha cuối crf 20 -> mất chất không nhận ra được.
    Caller PHẢI dọn các file trả về (kể cả khi lỗi/hủy).

    chuyen_canh (MỚI — CHUYỂN CẢNH xfade): [(kiểu, giây)] cho từng chỗ nối.
    Rỗng/None -> đường CŨ Y NGUYÊN (bất biến sống còn: preset cũ ra file giống
    hệt `main`). Có -> thêm PHA 1.5: lấy THÊM `d` giây ở cuối mỗi đoạn (xem
    `_bu_xfade`) rồi nối n đoạn thành 1 file mezzanine DUY NHẤT bằng
    xfade + acrossfade; danh sách concat trả về chỉ còn 1 dòng nên PHA 2 (graph
    khủng: nền mờ + overlay + đốt .ass + fade + tiếng động) KHÔNG PHẢI SỬA GÌ.
    Đổi lấy 1 lượt encode mezzanine nữa — chấp nhận, vì gộp xfade vào graph pha
    2 phải đánh số lại toàn bộ input (nền màu/overlay/nhạc/dub) trong hàm 400
    dòng đang gánh cả sản xuất 200-300 kênh.

    temps_out: LIST CỦA CALLER — hàm append từng file tạm vào đó NGAY khi tạo.
    RÒ RÁC THẬT (có từ bản `main`; đo 07/08/2026 còn **0,53 GB `_seg_*`** trong
    `%TEMP%`): caller bọc `try/except` rồi gọi `_cleanup_paths(_seg_temps)`,
    nhưng khi hàm này NÉM LỖI thì phép gán `_seg_list, _seg_temps = ...` CHƯA
    CHẠY nên `_seg_temps` vẫn RỖNG -> mọi mảnh đã tách nằm lại VĨNH VIỄN. Chuyển
    cảnh làm nó nặng thêm vì pha 1.5 là một chỗ ném lỗi MỚI. Đúng loại rác
    1,71 GB phải dọn tay hôm 31/07 khi ổ C đầy 100%."""
    import tempfile
    info = probe(src)
    fps = info.fps if 10.0 <= (info.fps or 0) <= 120.0 else 30.0
    tdir = tempfile.gettempdir()
    # TÊN CÓ ĐÓNG DẤU PID (`_tag_moi`) -> lúc mở app phân biệt được mảnh của lượt
    # ĐANG chạy với mảnh mồ côi của lần chạy trước (`don_seg_mo_coi`).
    tag = _tag_moi()
    temps: list = temps_out if temps_out is not None else []
    n = len(segs)
    dai_goc = [float(e) - float(s) for s, e in segs]
    xf = list(chuyen_canh or [])[:max(0, n - 1)]
    bu = _bu_xfade(segs, xf, float(info.duration or 0.0)) if xf else []
    # ---- NHÓM GPU (21 kernel gl-transitions, MIT). Máy nhân viên thiếu OpenCL
    # -> `co_chuyen_canh_gpu()` rỗng -> ĐỔI kiểu GPU sang kiểu CPU tương đương
    # và đi đường cũ. KHÔNG một dòng lỗi, KHÔNG mất chuyển cảnh.
    co_gpu = any(str(k).startswith("gl_") for k, _d in xf)
    if co_gpu and not co_chuyen_canh_gpu():
        xf = [(GPU_LUI_VE.get(str(k), str(k)), d) for k, d in xf]
        co_gpu = False
    # ---- KIẾN TRÚC "2n−1 MẢNH" cho MỌI mức chuyển cảnh (không chỉ GPU).
    # Đường CŨ nối n mezzanine bằng 1 lệnh `xfade` = ENCODE LẠI TOÀN CLIP thêm
    # một lượt ở pha 1.5. Đường này chỉ encode lại **cửa sổ chuyển cảnh
    # 0,25-0,4 giây** rồi để `concat` demuxer nối — đúng kiến trúc đã dùng cho
    # nhóm GPU, nay áp cho cả `nhe`/`vua` (xfade CPU).
    #
    # ĐO A/B CÙNG MÁY, CÙNG SCRIPT, MÁY RẢNH 10-11% (3 đoạn 24s, 1080x1920,
    # nvenc, lặp 3 lấy trung vị) — `BQ_XFADE_NOI_CA_CLIP=1` ép về đường CŨ:
    #   | ca                 | CŨ            | MỚI           |
    #   | TẮT hết (đối chứng)| 5,70s / 20,06 | 5,64s / 20,39 |
    #   | chỉ chuyển cảnh nhe| 9,43s (1,65×) | 7,43s (1,32×) | wall −21% CPU −34%
    #   | MẶC ĐỊNH nhe+nhe   |13,13s (2,30×) |11,20s (1,98×) | wall −15% CPU −26%
    #   | manh+manh (GPU)    |12,71s (2,23×) |10,38s (1,84×) | wall −18% CPU −29%
    # Đo đan xen bằng script riêng ra cùng kết luận: wall 0,85× · CPU 0,72×.
    # **CHƯA ĐẠT mốc ≤ 1,4×** cho mặc định — phần dư là HIỆU ỨNG ĐIỂM NHẤN ở
    # pha 2 (một mình đã 1,61×), không phải chuyển cảnh.
    # Hỏng thì LÙI ÊM về đường nối-cả-clip cũ (khối `for` bên dưới) — đường cũ
    # vẫn nguyên vẹn, không xoá.
    # `BQ_XFADE_NOI_CA_CLIP=1` ép về đường CŨ (nối cả clip) — để ĐO A/B đan xen
    # trong CÙNG một lượt (quy tắc sắt: đo 2 phiên khác nhau ra kết luận sai 2
    # lần) và để gỡ rối trên máy user mà không phải phát hành bản mới.
    _cu = os.environ.get("BQ_XFADE_NOI_CA_CLIP", "").strip() == "1"
    if xf and not _cu and any(d >= 0.08 for d in bu):
        try:
            manh = _tach_va_noi_manh(src, segs, xf, bu, encoder, fps,
                                     bool(info.has_audio), tdir, tag, temps,
                                     on_progress, dung_gpu=co_gpu)
            lst = os.path.join(tdir, f"_seg_{tag}_list.txt")
            with open(lst, "w", encoding="utf-8") as f:
                f.write("ffconcat version 1.0\n")
                for p in manh:
                    f.write("file '" + p.replace("\\", "/") + "'\n")
            temps.append(lst)     # vào SỔ luôn: caller dọn 1 chỗ, không sót
            return lst, temps
        except Exception as e:      # noqa: BLE001 — hỏng KHÔNG được làm chết
            # lượt xuất: dọn mảnh rồi làm lại bằng đường nối-cả-clip. Mảnh đã
            # tạo nằm trong `temps` (list của caller) nên vẫn được dọn dù có gì.
            # HUỶ (`CanceledError`) thì PHẢI ném tiếp — lùi đường khác lúc user
            # vừa bấm Huỷ là chạy thêm cả một lượt xuất nữa (cổng 37 ca "huỷ
            # giữa lúc xuất"). So theo TÊN LỚP vì worker import vòng.
            if type(e).__name__ == "CanceledError":
                raise
            print(f"[hieu-ung] chuyển cảnh 2n-1 hỏng ({e}) -> lùi nối cả clip")
            # GIỮ LẠI trong sổ những mảnh CHƯA xoá được (đang bị Windows khoá
            # vì ffmpeg vừa chết). Bản cũ `del temps[:]` vô điều kiện -> mảnh
            # khoá bị xoá khỏi sổ nên caller KHÔNG CÒN ĐƯỜNG NÀO dọn, rác nằm
            # lại vĩnh viễn (đo `_do_ro_seg.py`: 6 file / 8,9 MB một lượt).
            con = _cleanup_paths(list(temps))
            del temps[:]
            temps.extend(con)
    # Đường "nối cả clip" chạy bằng filter `xfade` THƯỜNG -> kiểu GPU (`gl_*`)
    # PHẢI đổi sang kiểu CPU tương đương trước khi vào. BỎ SÓT chỗ này là ffmpeg
    # báo `Not yet implemented in FFmpeg, patches welcome` rồi CHẾT cả lượt xuất
    # (đã sập đúng 1 lần khi thêm cờ `BQ_XFADE_NOI_CA_CLIP` để đo A/B).
    if co_gpu:
        xf = [(GPU_LUI_VE.get(str(k), str(k)), d) for k, d in xf]
        co_gpu = False
    for i, (s, e) in enumerate(segs):
        seg_path = os.path.join(tdir, f"_seg_{tag}_{i}.mkv")
        temps.append(seg_path)
        # LẤY THÊM `bu[i]` giây ở CUỐI đoạn i để xfade có cái mà hoà mà KHÔNG
        # ăn bớt thời lượng clip -> phụ đề/tiếng động không lệch. Đoạn cuối
        # không có chỗ nối sau nó nên bu = 0.
        e = e + (bu[i] if i < len(bu) else 0.0)

        def _build_seg(enc: str, _s=s, _e=e, _p=seg_path) -> list[str]:
            # `-threads` TRƯỚC `-i` = luồng GIẢI MÃ. Pha 1 không có filter nên
            # nó GIẢI-MÃ-BOUND: đây là chỗ DUY NHẤT siết luồng có thể làm chậm
            # thật, và đúng là chỗ lần thử trước thất bại. Đã đo riêng (xem
            # `decode_threads`): mức 4 giữ nguyên wall (0,99x) mà hạ 61 -> 49
            # luồng; mức 1 mới chậm thật (nvenc +30%, libx264 +155%).
            c = [settings.FFMPEG_PATH, "-y", "-threads", str(decode_threads()),
                 "-ss", f"{_s:.3f}", "-t", f"{_e - _s:.3f}", "-i", str(src)]
            if enc == "h264_nvenc":
                c += ["-c:v", "h264_nvenc", "-preset", "p1", "-rc", "vbr",
                      "-cq", "16", "-pix_fmt", "yuv420p",
                      # nhánh nvenc trước đây TRẮNG TRƠN, không núm nào. Đo:
                      # `-threads 4` sau `-i` hạ 61 -> 37 luồng, wall 1,00x,
                      # log vẫn `h264_nvenc` (KHÔNG rớt về CPU).
                      "-threads", str(encode_threads())]
            else:
                # `-pix_fmt yuv420p` BẮT BUỘC: mảnh lệch pix_fmt làm ffmpeg
                # DỰNG LẠI filter graph mỗi mảnh -> `metadata=print:file=` ghi
                # đè -> `do_nhip` chỉ còn số của mảnh CUỐI -> MẤT ĐIỂM NHẤN
                # (cổng 45a đo: lệch 420->444 ra nl=8/cd=8 thay vì 16/16).
                c += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                      "-pix_fmt", "yuv420p",
                      "-threads", str(encode_threads())]
            # CFR đồng nhất mọi đoạn (concat demuxer cần cùng thông số) + PCM
            # 48k stereo (không mất chất tiếng qua 2 pha, đồng nhất layout).
            c += ["-r", f"{fps:g}", "-fps_mode:v", "cfr"]
            if info.has_audio:
                c += ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
            c += [_p]
            return c

        if on_progress:
            on_progress((i / max(1, n)) * 0.999)
        _run_with_fallback(_build_seg, encoder, e - s, None,
                           f"tách được đoạn {i + 1}/{n}", dst=seg_path)
    # BẢN SAO, KHÔNG phải tham chiếu. LỖI THẬT (cổng 36 bắt được ngay lượt đầu):
    # để `noi = temps` thì `temps.append(gop)` ở dưới sửa LUÔN `noi` -> file GỘP
    # (chưa tồn tại) bị đưa vào làm INPUT thứ n+1 -> ffmpeg:
    # "Error opening input file _seg_xxx_xf.mkv: No such file or directory".
    noi = list(temps)
    if xf and any(d >= 0.08 for d in bu):
        # ---- PHA 1.5: CHUYỂN CẢNH. Nối n mezzanine thành 1 mezzanine.
        gop = os.path.join(tdir, f"_seg_{tag}_xf.mkv")
        temps.append(gop)
        graph, vlab, alab = _graph_xfade(n, xf, bu, dai_goc, info.has_audio)

        # `_in=list(noi)` CHỐT ngay danh sách input vào tham số mặc định: dưới
        # đây `noi` bị gán lại thành [gop], mà `_run_with_fallback` có thể gọi
        # build LẦN 2 (lùi nvenc -> libx264). Đọc biến ngoài là lần 2 dựng lệnh
        # với input = chính file output.
        def _build_xf(enc: str, _g=graph, _v=vlab, _a=alab, _o=gop,
                      _in=list(noi)) -> list[str]:
            # `-threads` là tuỳ chọn THEO TỪNG ĐẦU VÀO: ffmpeg chỉ áp nó cho
            # `-i` NGAY SAU nó rồi "tiêu" mất. Bản trước đặt **một lần** trước
            # cả cụm `-i` và ghi chú là "áp cho TỪNG đầu vào" — **SAI**, chỉ
            # đầu vào ĐẦU TIÊN bị siết, n-1 đầu vào còn lại vẫn `-threads 0`.
            #
            # ĐO THẬT khi TỔNG RÀ SOÁT 08/08/2026 (`_ra_luong_toan_may.py` soi
            # MỌI ffmpeg trên máy): đúng lệnh này với **6 đầu vào** ăn **133
            # luồng = 5,54× số nhân** dù dòng lệnh có `-threads 1` — khớp y
            # phép tính 5 đầu vào × ~25 luồng mặc định + filter + encode.
            # Đây là ĐỈNH LỚN NHẤT của cả lượt dây chuyền.
            #
            # Chữa: LẶP `-threads` trước TỪNG `-i`. Ngân sách vẫn chia đều nên
            # tổng luồng giải mã không đổi so với lệnh 1 đầu vào.
            _dt = max(1, decode_threads() // max(1, len(_in)))
            c = [settings.FFMPEG_PATH, "-y",
                 "-filter_complex_threads", str(min(4, encode_threads()))]
            for p in _in:
                c += ["-threads", str(_dt), "-i", p]
            c += ["-filter_complex", _g, "-map", _v]
            if _a:
                c += ["-map", _a]
            if enc == "h264_nvenc":
                c += ["-c:v", "h264_nvenc", "-preset", "p1", "-rc", "vbr",
                      "-cq", "16", "-pix_fmt", "yuv420p",
                      "-threads", str(encode_threads())]
            else:
                # cùng lý do như `_build_seg`: mảnh CHUYỂN CẢNH đi qua
                # `filter_complex` nên rất dễ ra 444 nếu không ép.
                c += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                      "-pix_fmt", "yuv420p",
                      "-threads", str(encode_threads())]
            c += ["-r", f"{fps:g}", "-fps_mode:v", "cfr"]
            if info.has_audio:
                c += ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
            c += [_o]
            return c

        _run_with_fallback(_build_xf, encoder, sum(dai_goc), None,
                           f"nối {n} đoạn có chuyển cảnh", dst=gop)
        noi = [gop]
    lst = os.path.join(tdir, f"_seg_{tag}_list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for p in noi:
            f.write("file '" + p.replace("\\", "/") + "'\n")
    temps.append(lst)             # vào SỔ luôn: caller dọn 1 chỗ, không sót
    return lst, temps


def _cc_cach_ten(cach: str) -> str:
    """Nhãn TIẾNG VIỆT của cách che (cho nhật ký). KHÔNG emoji."""
    return "phủ khối" if str(cach or "").strip().lower() == "khoi" else "làm mờ"


def export_canvas_clip(
    src: str | Path,
    dst: str | Path,
    segments: list,          # [(s,e), ...] — các khúc giữ lại; >1 = ghép, bỏ đoạn thừa
    video_rect: tuple,       # (cx, cy, scale_w)
    bg: str = "blur",        # blur | black | white | fill (crop cắt 2 bên đầy khung)
    out_w: int = 1080,
    out_h: int = 1920,
    encoder: Optional[str] = None,
    overlay_png: Optional[str] = None,
    pre_crop: Optional[str] = None,
    ass_path: Optional[str] = None,     # phụ đề chạy chữ (.ass) -> đốt vào video
    fonts_dir: Optional[str] = None,    # thư mục font cho phụ đề (libass)
    blur_amt: int = 22,                 # độ mờ nền blur
    speed: float = 1.0,                 # tăng tốc clip (1.0-1.3...)
    pitch: float = 1.0,                 # đổi giọng (1=gốc, >1 cao/nữ, <1 trầm/nam)
    bgm_path: Optional[str] = None,     # NHẠC NỀN: file nhạc trộn dưới tiếng gốc
    bgm_vol: float = 0.15,              # âm lượng nhạc nền (0..1)
    orig_vol: float = 1.0,              # ÂM LƯỢNG TIẾNG GỐC (0..1); có lồng tiếng
                                        # + để 1.0 -> tự hạ ~0.12 làm nền
    dub_path: Optional[str] = None,     # LỒNG TIẾNG AI: wav 48k dài đúng bằng clip
    duck_ranges: Optional[list] = None, # 🎙 RECAP: các khoảng (a,b) trên timeline
                                        # ĐẦU RA (sau speed) mà ÂM GỐC bị HẠ
                                        # xuống _DUCK_LEVEL (~12%, nền văng
                                        # vẳng) — lúc giọng AI nói. Chỉ áp
                                        # lên tiếng gốc, KHÔNG đụng nhạc nền/
                                        # narration. Có duck_ranges -> KHÔNG tự
                                        # hạ nền tiếng gốc kiểu dub (orig_vol
                                        # giữ nguyên ở các đoạn giữ tiếng gốc).
    dub_mute_original: bool = False,    # True = tắt hẳn tiếng gốc khi có lồng tiếng
    dub_stretch: float = 1.0,           # CHẾ ĐỘ "Khớp video": làm CHẬM ĐỀU clip
                                        # theo hệ số này (>1) để giọng đọc lọt
                                        # khung tự nhiên (dub đã dựng theo timeline
                                        # đã giãn). 1.0 = không giãn.
    fx_fade: bool = True,               # HIỆU ỨNG: fade hình NHẸ đầu/cuối clip
                                        # (~0.35s) — tinh tế, chuyên nghiệp.
    fx_whoosh: bool = True,             # HIỆU ỨNG: tiếng chuyển đoạn NHỎ tại
                                        # điểm ghép các đoạn (chỉ khi >1 segment).
    fx_sfx_dir: Optional[str] = None,   # THƯ MỤC tiếng động RIÊNG của user (tùy
                                        # chọn): nếu có + có file -> mỗi điểm ghép
                                        # lấy NGẪU NHIÊN 1 file trong đó; để trống
                                        # -> dùng thư viện SFX ĐÓNG GÓI theo ngữ
                                        # cảnh (fallback tổng hợp).
    join_categories: Optional[list] = None,  # NGỮ CẢNH mỗi điểm nối: list category
                                        # ("transition"/"impact"/"riser"/"reveal"/
                                        # "pop") DÀI BẰNG số điểm nối (len(segs)-1).
                                        # Caller (m1/m2) biết cấu trúc đoạn -> chọn
                                        # đúng loại (recap climax -> impact, kết ->
                                        # reveal, thường -> transition). None/thiếu
                                        # -> transition cho mọi điểm nối (như cũ).
    flip_h: bool = False,               # LẬT GƯƠNG ngang (né content-ID khi
                                        # reup). Áp hflip lên KHỐI video content
                                        # TRƯỚC overlay chữ/phụ đề -> hình soi
                                        # gương nhưng CHỮ vẫn đọc bình thường.
    fit_src: bool = False,              # KHUNG TỰ KHỚP TỈ LỆ VIDEO GỐC: tính
                                        # lại video_rect theo tỉ lệ NGUỒN (giữ
                                        # tâm + bề ngang mẫu, clamp vừa canvas)
                                        # -> nguồn 1:1/16:9 hiện TRỌN không bị
                                        # cắt, nền lấp phần thừa. bg='fill'
                                        # (crop đầy khung) mâu thuẫn "không mất
                                        # hình" -> tự chuyển sang nền mờ.
    dim_ranges: Optional[list] = None,  # 🔦 RECAP SPOTLIGHT: các khoảng (a,b)
                                        # trên timeline ĐẦU RA (sau speed) —
                                        # CÙNG hệ quy chiếu duck_ranges — mà
                                        # KHỐI video content bị LÀM TỐI NHẸ
                                        # (eq=brightness=-dim_amount) lúc AI
                                        # đang KỂ. Áp TRƯỚC khi đốt phụ đề/
                                        # overlay -> CHỮ vẫn sáng rõ. Đoạn giữ
                                        # tiếng gốc (ngoài khoảng) sáng bình
                                        # thường -> cảm giác "spotlight" khi AI
                                        # nói. None/rỗng -> KHÔNG dim (bất biến
                                        # clip thường + reup cũ).
    dim_amount: float = 0.14,           # MỨC TỐI (0..0.5); brightness eq =
                                        # -dim_amount. <=0 -> KHÔNG dim.
    hieu_ung: object = "",               # HIỆU ỨNG THẤY ĐƯỢC ở ĐIỂM NHẤN:
                                        # "" / "tat" -> đường CŨ Y NGUYÊN;
                                        # "nhe"/"vua"/"manh" -> AI tự chọn theo
                                        # CẢNH (`hieu_ung.chon_hieu_ung`, đo
                                        # tiếng + chuyển động của chính clip);
                                        # hoặc truyền thẳng list
                                        # [{bat,het,khoa,dam}] (dùng cho test/demo)
    hieu_ung_log: Optional[list] = None,  # LIST CỦA CALLER: hàm ghi vào đây các
                                        # hiệu ứng ĐÃ CHỌN (để log/ghi chú
                                        # "giây thứ mấy -> hiệu ứng gì -> vì sao")
    noi_dung: Optional[dict] = None,     # NỘI DUNG CẢNH cho nhóm LỚP PHỦ HẠT:
                                        # {"digest": [{'t','desc','act'}] mốc
                                        # AI XEM HÌNH trên timeline NGUỒN (đọc
                                        # CACHE, KHÔNG gọi LLM), "loi": chép
                                        # lời của chính đoạn này, "transcript":
                                        # bản chép lời ĐẦY ĐỦ (có mốc từng câu)
                                        # để dựng đường ĐOÁN CẢNH BẰNG LỜI khi
                                        # KHÔNG có digest}. Thiếu cả hai ->
                                        # nhóm lớp phủ TỰ BỎ QUA (xem
                                        # `lop_phu.chon_lop_phu`) và mọi thứ
                                        # chạy y hệt bản cũ.
    tieng_dong_log: Optional[list] = None,  # LIST CỦA CALLER: TIẾNG ĐỘNG đã chèn
                                        # ở từng điểm nối [{giay, loai, ten,
                                        # nguon}]. Cùng dữ liệu với biến toàn
                                        # cục `_SFX_LAST_PICK` nhưng TRẢ RIÊNG
                                        # cho từng lượt — 3 làn xuất chạy song
                                        # song thì biến toàn cục là của lượt
                                        # nào xong sau cùng, đọc ra là số của
                                        # clip KHÁC.
    chuyen_canh: object = "",            # CHUYỂN CẢNH ở chỗ ghép đoạn (xfade):
                                        # "" / "tat" -> đường CŨ Y NGUYÊN;
                                        # "nhe"/"vua"/"manh" -> tự chọn kiểu
                                        # theo NỘI DUNG chỗ nối
                                        # (`chon_chuyen_canh`); hoặc truyền
                                        # thẳng [(kiểu, giây)] (dùng cho test).
    che_chu: bool = False,               # CHE CHỮ CHÁY SẴN TRONG HÌNH
                                        # (`app/core/che_chu.py`). MẶC ĐỊNH
                                        # TẮT: có ca che nhầm nên anh Hùng phải
                                        # tự bật. False -> KHÔNG dò, KHÔNG một
                                        # dòng filter nào => lệnh ffmpeg giống
                                        # HỆT bản trước khi có tính năng này
                                        # (bất biến của 200-300 kênh đang chạy).
    che_chu_cach: str = "mo",            # "mo" (làm mờ) | "khoi" (phủ khối)
    che_chu_muc: float = 1.0,            # mức mờ — SÀN CỨNG 0,60
                                        # (`che_chu.chuan_muc_mo`; mức 0,40 đo
                                        # ra "sạch" mà mắt vẫn đọc được chữ).
    che_chu_dai: object = None,          # DaiChu đã dò sẵn (test/đo). None ->
                                        # tự dò 1 lần rồi NHỚ theo video.
    che_chu_toan_khung: Optional[bool] = None,  # QUÉT CẢ KHUNG (chữ ở TRÊN/
                                        # GÓC) thay vì chỉ dải ĐÁY. BA trạng
                                        # thái: None = theo env
                                        # `BQ_CHE_TOAN_KHUNG` (mặc định TẮT) ·
                                        # True/False = user đã chọn trong mẫu.
                                        # Ép về bool là mất đường đổi mặc định
                                        # toàn cục (bài học `projects.xem_hinh`
                                        # cổng 51).
    che_chu_log: Optional[list] = None,  # LIST CỦA CALLER: hàm ghi vào đây
                                        # {che, ly_do, dai} — nhật ký dây
                                        # chuyền in ra cho anh Hùng đọc. Che
                                        # nhầm/không che đều phải NÓI RA, đừng
                                        # im lặng (bài học "lớp chữ MẤT").
    on_progress: Optional[Callable[[float], None]] = None,
) -> bool:
    """
    Mô hình CapCut: khung 9:16 = NỀN (đen/trắng/mờ) + KHỐI video; hoặc 'fill' = crop
    cắt 2 bên cho video đầy khung. Nhiều khúc -> GHÉP. Tùy chọn tăng tốc + đổi giọng.

    dub_stretch (>1): "Khớp video (mượt)" — làm CHẬM ĐỀU cả clip video (setpts)
    để khớp giọng lồng tiếng đọc ở tốc độ TỰ NHIÊN, thay vì tăng tốc giọng gắt.
    Track lồng tiếng (dub_path) đã được dựng trên timeline ĐÃ GIÃN (dài
    total*dub_stretch) nên KHÔNG bị atempo theo dub_stretch — chỉ video + tiếng
    gốc + nhạc nền chậm lại. Phụ đề .ass cũng đã build theo timeline giãn -> đốt
    trước setpts nên tự khớp. Kết hợp với `speed` (user tua nhanh) qua 1 hệ số
    video hiệu dụng = speed/dub_stretch (vẫn DUY NHẤT 1 lệnh ffmpeg).
    """
    # SỔ NỢ: mảnh của lượt trước xoá không được (file còn khoá lúc đó) — nhặt
    # lại ở đây, chỗ rẻ nhất và chắc chắn có người đi qua. Sổ rỗng -> 0 ms.
    don_rac_ton()
    segs = [(float(s), float(e)) for s, e in (segments or []) if e > s]
    if not segs:
        raise RuntimeError("Không có đoạn nào để xuất.")
    encoder = encoder or detect_encoder()
    out_w, out_h = khung_chan(out_w, out_h)
    # Video KHÔNG có tiếng -> mọi filter [0:a] sẽ fail; xuất chỉ hình.
    _info = probe(src)
    has_audio = _info.has_audio
    # KẸP mốc vào độ dài THẬT trước khi tính total/multi (xem hàm để biết vì sao)
    segs = _cat_theo_do_dai_that(segs, float(_info.duration or 0.0), src)
    multi = len(segs) > 1
    total = sum(e - s for s, e in segs)
    dub_on = bool(dub_path and os.path.exists(str(dub_path)))
    # Tắt hẳn tiếng gốc khi lồng tiếng -> KHÔNG concat/lọc audio gốc luôn
    # (concat ra [caud] mà không dùng sẽ làm ffmpeg fail "unconnected output").
    use_voice = has_audio and not (dub_on and dub_mute_original)
    if fit_src:
        # KHUNG TỰ KHỚP TỈ LỆ VIDEO GỐC (dùng probe ĐÃ CÓ SẴN, không probe
        # thêm). Kích thước hiệu dụng = sau pre_crop (cắt viền đen 'w:h:x:y'
        # đổi tỉ lệ content thật). fill = crop đầy khung -> mâu thuẫn "không
        # mất hình": đổi sang nền mờ để video vẫn hiện trọn.
        if bg == "fill":
            bg = "blur"
        _ew, _eh = _info.width, _info.height
        if pre_crop:
            try:
                _pw, _ph = (int(float(v))
                            for v in str(pre_crop).split(":")[:2])
                if _pw > 0 and _ph > 0:
                    _ew, _eh = _pw, _ph
            except (ValueError, IndexError):
                pass
        video_rect = fit_src_video_rect(video_rect, _ew, _eh, out_w, out_h)
    cx, cy, sw = video_rect
    vw = max(2, int(round(sw * out_w)) // 2 * 2)
    use_png = bool(overlay_png and os.path.exists(overlay_png))
    blur_amt = max(1, int(blur_amt))
    speed = max(0.5, min(3.0, float(speed or 1.0)))
    pitch = max(0.5, min(2.0, float(pitch or 1.0)))
    # "Khớp video (mượt)": chỉ áp khi THẬT có lồng tiếng (dub track dựng theo
    # timeline đã giãn). Không có dub -> bỏ qua để không làm chậm oan clip.
    dub_stretch = max(1.0, min(2.0, float(dub_stretch or 1.0))) if dub_on else 1.0
    # TỐC ĐỘ VIDEO HIỆU DỤNG: user tua nhanh (speed) rồi giãn để khớp giọng
    # (chia dub_stretch). vspeed<1 = video chậm lại. Dùng cho setpts video +
    # atempo tiếng gốc/nhạc nền; RIÊNG dub giữ `speed` (đã dài sẵn theo stretch).
    vspeed = speed / dub_stretch
    # MỐC GHÉP (giây) ở timeline ĐẦU RA cho whoosh: cộng dồn độ dài các đoạn
    # (trừ đoạn cuối — không có ghép sau nó) rồi chia vspeed (video đã tăng/giãn
    # tốc). Chỉ có khi >1 đoạn. Lệch mốc nhẹ vài chục ms không đáng kể với whoosh.
    whoosh_offsets: list[float] = []
    if multi:
        acc = 0.0
        for s, e in segs[:-1]:
            acc += (e - s)
            whoosh_offsets.append(acc / vspeed)
    # NGỮ CẢNH mỗi điểm nối (10 loại SFX_CATEGORIES + "none"). Chuẩn hoá về
    # đúng len(whoosh_offsets): thiếu -> "transition" (như cũ); loại lạ ->
    # "transition"; "none" -> GIỮ NGUYÊN (điểm nối KHÔNG chèn tiếng — nhãn AI
    # "none" hoặc lạ khác); dư -> cắt bớt. Không có join_categories -> toàn
    # transition.
    join_cats: list[str] = []
    for i in range(len(whoosh_offsets)):
        c = "transition"
        if join_categories and i < len(join_categories):
            cand = str(join_categories[i] or "").strip().lower()
            if cand in SFX_CATEGORIES:
                c = cand
            elif cand == "none":
                c = "none"          # AI gắn "none" -> bỏ chèn ở điểm này
        join_cats.append(c)
    orig_vol = max(0.0, min(1.0, float(orig_vol if orig_vol is not None else 1.0)))
    # ÂM LƯỢNG TIẾNG GỐC áp vào luồng tiếng gốc TRƯỚC khi amix. Khi có lồng
    # tiếng và user để mặc định 1.0 (thanh kéo chưa động) -> tự hạ nền ~0.12
    # để lời lồng tiếng nổi lên; user kéo mức khác thì tôn trọng đúng mức đó.
    # Các khoảng TẮT ÂM GỐC (recap thuyết minh) — hợp lệ khi (a,b) đúng thứ tự
    ducks: list[tuple[float, float]] = []
    for pair in (duck_ranges or []):
        try:
            a, b = float(pair[0]), float(pair[1])
        except (TypeError, ValueError, IndexError):
            continue
        if b - a > 0.05:
            ducks.append((max(0.0, a), b))
    voice_vol = orig_vol
    if dub_on and not dub_mute_original and orig_vol >= 0.999 and not ducks:
        voice_vol = 0.12
    # 🔦 SPOTLIGHT: mức tối (clamp 0..0.5) + các khoảng LÀM TỐI (đầu ra, sau
    # speed — như duck). dim_amount<=0 hoặc không có khoảng hợp lệ -> tắt hẳn.
    dim_amt = max(0.0, min(0.5, float(dim_amount if dim_amount is not None else 0.0)))
    dims: list[tuple[float, float]] = []
    for pair in (dim_ranges or []):
        try:
            a, b = float(pair[0]), float(pair[1])
        except (TypeError, ValueError, IndexError):
            continue
        if b - a > 0.05:
            dims.append((max(0.0, a), b))

    # ---- CHE CHỮ CHÁY SẴN TRONG HÌNH (`app/core/che_chu.py`) ----------------
    # Nguồn Douyin/reup đốt phụ đề VÀO KHUNG, gỡ ra không được. Đây là chỗ che
    # nó đi. GỘP VÀO LƯỢT MÃ HOÁ NÀY, KHÔNG thêm lệnh ffmpeg thứ hai — chạy
    # riêng một lượt tốn **35-76 giây cho video 10 phút**. Với 200-300 kênh thì
    # khoảng cách đó là khoản thật.
    # CHI PHÍ CỦA CHÍNH CHUỖI CHE (đo đan xen, xem docstring `che_chu.py`):
    # "làm mờ" **+1,30 s/phút** · "phủ khối" **−0,01 s/phút**. Số +0,1-0,2
    # từng ghi ở đây CHỈ đúng với "phủ khối" — phần đắt là `boxblur` tranh CPU
    # với libx264, không phải kiến trúc filter (split/overlay chỉ +0,05).
    #
    # `che_chu=False` -> KHÔNG dò, `_cc_loc` rỗng, KHÔNG một `parts.append` nào
    # => lệnh ffmpeg KHÔNG khác một ký tự nào so với bản trước tính năng này
    # (cùng cách giữ bất biến mà nhóm shader/chuyển cảnh đang dùng).
    #
    # DÒ nằm NGOÀI `build`: `build` được gọi LẠI khi lùi nvenc -> libx264, dò
    # trong đó là đọc 16 khung HAI LẦN.
    # CỐ Ý KHÔNG qua cửa chờ ffmpeg (y như `_do_muc_clip`/`do_nhip`): 16 lượt
    # `-ss ... -frames:v 1` ở 640px, không encode. Bắt nó xếp hàng sau các lệnh
    # encode nặng thì mỗi lượt xuất đội thêm hàng chục giây vô ích. Kết quả được
    # NHỚ theo video nên 3 Part của một video chỉ dò MỘT lượt.
    _cc_loc, _cc_dai, _cc_ly = "", None, ""
    if che_chu:
        _raise_if_job_canceled()   # bấm Huỷ -> đừng đọc 16 khung rồi mới chết
        try:
            from app.core import che_chu as _CC
            # `segs` = các đoạn nguồn sẽ ghép, ĐÚNG THỨ TỰ (hook-first thì
            # NGƯỢC thời gian). Nhờ nó `che_chu` đổi HỘP CHE theo từng mốc thay
            # vì che một DẢI NGANG suốt clip (anh Hùng 14/08/2026: *"che mờ
            # ĐÚNG VỊ TRÍ chữ xuất hiện thôi"*). Trục thời gian của `enable=`
            # là trục ĐẦU RA — đúng trục `.ass` đang dùng, và `_bu_xfade` viết
            # ra chính là để giữ trục đó. Không truyền `segs` thì
            # `loc_cho_xuat` tự lùi về MỘT hộp cho cả clip: vẫn đúng, chỉ che
            # thừa hơn.
            _cc_loc, _cc_dai, _cc_ly = _CC.loc_cho_xuat(
                src, cach=che_chu_cach, muc=che_chu_muc, dai=che_chu_dai,
                segs=segs, toan_khung=che_chu_toan_khung)
        except Exception as _e:    # noqa: BLE001 — che chữ KHÔNG được làm chết
            _cc_loc, _cc_dai = "", None            # lượt xuất; nói ra lý do
            _cc_ly = f"dò/che chữ lỗi ({_e}) -> KHÔNG che"
    if che_chu_log is not None:
        che_chu_log.append({
            "bat": bool(che_chu), "che": bool(_cc_loc),
            "cach": _cc_cach_ten(che_chu_cach), "muc": float(che_chu_muc or 0),
            "ly_do": _cc_ly,
            "dai": (_cc_dai.dict() if _cc_dai is not None else None)})

    # ---- GHÉP NHIỀU ĐOẠN = 2 PHA (xem _extract_segments_to_temp): pha 1
    # tách từng đoạn ra file tạm (RAM phẳng, tiếng-hình cắt CÙNG NHAU, giữ
    # ĐÚNG THỨ TỰ danh sách kể cả hook-first, ép CFR chống nguồn VFR trôi);
    # pha 2 nối bằng concat demuxer -> vào graph như 1 input LIỀN MẠCH.
    _seg_list = ""
    _seg_temps: list = []
    # CHUYỂN CẢNH: nhận MỨC (chuỗi) -> tự suy kiểu theo nội dung chỗ nối, hoặc
    # nhận thẳng danh sách [(kiểu, giây)] (test). Sai kiểu/mức lạ -> [] = TẮT.
    _xf: list = []
    if multi:
        if isinstance(chuyen_canh, str):
            _xf = chon_chuyen_canh(segs, chuyen_canh)
        elif isinstance(chuyen_canh, (list, tuple)):
            _xf = [(str(k), float(d)) for k, d in chuyen_canh]
    if multi:
        if on_progress:
            on_progress(0.01)
        try:
            # temps_out=_seg_temps: hàm append MẢNH VÀO ĐÂY ngay khi tạo. Trước
            # đây chỉ nhận qua giá trị TRẢ VỀ, mà lỗi giữa đường thì phép gán
            # chưa chạy -> `_seg_temps` rỗng -> dọn 0 file, rác nằm lại vĩnh
            # viễn (đo: 0,53 GB `_seg_*` trong %TEMP%).
            _seg_list, _seg_temps = _extract_segments_to_temp(
                src, segs,
                encoder, lambda p: on_progress and on_progress(p * 0.35),
                chuyen_canh=_xf, temps_out=_seg_temps)
        except Exception:
            _cleanup_paths(_seg_temps)
            raise

    # ---- HIỆU ỨNG THẤY ĐƯỢC ở ĐIỂM NHẤN (kho `app/core/hieu_ung.py`) ----
    # "" / "tat" -> KHÔNG một dòng filter nào thêm vào => đường CŨ Y NGUYÊN
    # (bất biến sống còn: bật-tắt phải ra file GIỐNG HỆT `main`).
    # Mức ("nhe"/"vua"/"manh") -> ĐO nhịp của CHÍNH clip sắp xuất (mức âm + mức
    # chuyển động từng giây, 1 lệnh ffmpeg 160px) rồi `chon_hieu_ung` suy ra
    # điểm nhấn — TIỀN ĐỊNH, KHÔNG bốc thăm. Đo trên ĐÚNG timeline đầu ra:
    # nhiều đoạn thì đo file danh sách concat (đã ghép, đã hook-first), một
    # đoạn thì đo đúng khoảng [s,e] của nguồn.
    _hu: list = []
    # `fps` cho `zoompan` phải là fps của LUỒNG ĐI VÀO NÓ, KHÔNG phải fps NGUỒN.
    # LỖI 1 (đo thật 08/08/2026): nền Đen/Trắng dựng bằng `color=…:r=30` và nó
    # là input CHÍNH của `overlay` -> luồng ra 30 fps. Truyền fps nguồn 25 thì
    # `zoompan` đóng dấu lại mốc thời gian theo 25 -> 30 khung/giây bị kéo dài
    # thành 1,2 giây => **clip DÀI HƠN 20%** (đo: 2,000s -> 2,400s), hình dài
    # hơn tiếng. Nền mờ/fill thì luồng vẫn là hình gốc nên giữ fps nguồn (mọi
    # mezzanine pha 1 đã ép CFR bằng đúng fps này).
    _hu_fps = _info.fps if 10.0 <= (_info.fps or 0) <= 120.0 else 30.0
    if bg not in ("blur", "fill"):
        _hu_fps = 30.0
    # Timeline ĐẦU RA (sau speed) — CÙNG hệ quy chiếu duck_ranges/dim_ranges/
    # whoosh_offsets. LỖI 3: trước đây mốc được sinh trên timeline NỘI BỘ (chưa
    # speed) rồi lại NHÂN vspeed lúc dựng filter như thể nó là mốc đầu ra ->
    # điểm rơi ra NGOÀI clip. Đo thật: clip nội bộ 10s, speed 1,25 -> ra 8,03s
    # mà điểm thứ 3 nằm ở giây 9,00-9,70 = KHÔNG BAO GIỜ CHẠY.
    _out_dur = total / vspeed if abs(vspeed - 1.0) > 0.001 else total
    try:
        from app.core import hieu_ung as _HU
        # ffmpeg con thừa hưởng os.environ -> đặt FREI0R_PATH ở đây là đủ cho cả
        # đường list-truyền-thẳng (test/demo) lẫn đường tự chọn theo mức.
        _HU.dat_frei0r_path()
        # LỖI 5: font phải biết TRƯỚC khi chọn. `chuoi_filter` tự bỏ hiệu ứng
        # cần font khi máy thiếu font -> nếu để nó chọn rồi mới bỏ thì nhật ký
        # khoe hiệu ứng KHÔNG có trong file, và điểm nhấn đó mất trắng 1 suất.
        _font = _HU.font_mac_dinh(str(fonts_dir or ""))
        if isinstance(hieu_ung, (list, tuple)):
            _hu = [dict(x) for x in hieu_ung]
        elif str(hieu_ung or "").strip().lower() in ("nhe", "vua", "manh"):
            if multi and _seg_list:
                _vao = ["-f", "concat", "-safe", "0", "-i", _seg_list]
            else:
                _s0, _e0 = segs[0]
                _vao = ["-ss", f"{_s0:.3f}", "-t", f"{_e0 - _s0:.3f}",
                        "-i", str(src)]
            _nl, _cd = _HU.do_nhip("", ffmpeg=settings.FFMPEG_PATH,
                                   dau_vao=_vao)
            # ĐO CỤT = ĐO SAI — VỨT, ĐI ĐƯỜNG CẤU TRÚC (xem `hieu_ung.do_du`).
            # `do_nhip` có thể trả về một danh sách NGẮN mà không hề báo lỗi
            # (file `metadata=print` bị GHI ĐÈ khi ffmpeg dựng lại filter graph
            # giữa các mảnh concat — đúng lỗi 08/08/2026 làm máy KHÔNG NVENC ra
            # 0 điểm nhấn). Đo thật trên `chon_hieu_ung`: đo cụt 4/16 giây ->
            # **0 điểm nhấn**, trong khi KHÔNG đo được -> vẫn **3 điểm**. Tức
            # thà không đo còn hơn đo cụt.
            if not _HU.do_du(_nl, _cd, _out_dur * vspeed):
                _nl, _cd = [], []
            # `do_nhip` đo trên timeline NỘI BỘ (1 giá trị / giây). Đổi sang
            # timeline ĐẦU RA: giây thứ i của clip ra = giây i*vspeed của trong.
            if abs(vspeed - 1.0) > 0.001:
                _n = max(1, int(_out_dur))
                _nl = [_nl[min(len(_nl) - 1, int(i * vspeed))]
                       for i in range(_n)] if _nl else []
                _cd = [_cd[min(len(_cd) - 1, int(i * vspeed))]
                       for i in range(_n)] if _cd else []
            # mốc chỗ nối trên timeline ĐẦU RA (xfade đã bù nên mốc KHÔNG đổi)
            _moc = [sum(e - s for s, e in segs[:i + 1]) / vspeed
                    for i in range(len(segs) - 1)]
            _dung_kieu = _HU.dung_duoc(co_font=bool(_font))
            # ---- LỚP PHỦ HẠT CHỌN THEO NỘI DUNG (`app/core/lop_phu.py`) ----
            # Chạy TRƯỚC `chon_hieu_ung` rồi đưa vào bằng `dat_truoc`: bằng
            # chứng NỘI DUNG mạnh hơn số đo tiếng/hình, nên nó được đặt chỗ
            # trước, phần còn lại của ngân sách 10% mới chia cho điểm nhấn.
            # Không digest / không khớp / nội dung pha tạp -> `[]` + một dòng lý
            # do vào `logs/lop_phu_<ngày>.log`. KHÔNG gọi LLM ở đây, chỉ đọc.
            _lp_chon: list = []
            try:
                from app.core import lop_phu as _LP
                _lp_moc = _LP.loc_digest_theo_doan(
                    (noi_dung or {}).get("digest") or [], segs, vspeed)
                _lp_loi = str((noi_dung or {}).get("loi") or "")
                if not _lp_moc:
                    # ---- ĐƯỜNG THỨ HAI: ĐOÁN CẢNH BẰNG **LỜI THOẠI** ----
                    # `VISION_CUT` mặc định TẮT (đo 219 giây/video) nên hầu hết
                    # clip KHÔNG có digest -> trước v2.21.0 nhóm lớp phủ gần như
                    # không bao giờ chạy ("không thấy tuyết/trái tim nào").
                    # Chép lời thì clip nào cũng có sẵn, 0 giây thêm, 0 lượt LLM.
                    # XEM HÌNH VẪN ƯU TIÊN: chỉ vào đây khi digest RỖNG.
                    _lp_moc = _LP.digest_tu_loi(
                        (noi_dung or {}).get("transcript") or {}, segs, vspeed)
                    # và KHÔNG đưa `loi` vào nữa: mốc đã DỰNG TỪ chính lời đó,
                    # tính cả hai là ĐẾM MỘT BẰNG CHỨNG HAI LẦN -> một câu nhắc
                    # "trời mưa" tự nó qua ngưỡng. Để rỗng thì bậc thang giữ
                    # nguyên ý nghĩa: phải **2 CÂU** nói tới cảnh đó.
                    _lp_loi = ""
                # NGÔN NGỮ của bản chép lời -> chọn ĐÚNG bảng từ khoá lời
                # thoại. Bắt buộc truyền cả ở đường XEM HÌNH (mốc là mô tả
                # tiếng Anh nhưng `_lp_loi` là lời THẬT của video): thiếu là
                # câu tiếng Trung nói "料理" (= xử lý) bị bảng Nhật cấm oan
                # 5 cảnh. Nhãn lạ/rỗng -> bảng mặc định, hành vi y cũ.
                _lp_lang = str(((noi_dung or {}).get("transcript") or {})
                               .get("language") or "")
                _lp_chon, _lp_ly = _LP.chon_lop_phu(
                    _lp_moc, _lp_loi, _out_dur,
                    str(hieu_ung).strip().lower(), co_the_dung=_dung_kieu,
                    ngon_ngu=_lp_lang)
                _LP.ghi_nhat_ky(_lp_ly, os.path.basename(str(dst)))
            except Exception:  # noqa: BLE001 — lớp phủ KHÔNG được chặn lượt xuất
                _lp_chon = []
            _hu = _HU.chon_hieu_ung(_out_dur, str(hieu_ung).strip().lower(),
                                    nl=_nl, cd=_cd, moc_noi=_moc,
                                    co_the_dung=_dung_kieu,
                                    hook=_la_hook_first(segs),
                                    dat_truoc=_lp_chon)
        _hu = _HU.loc_theo_font(_hu, bool(_font))
        if _hu and hieu_ung_log is not None:
            hieu_ung_log.extend(_hu)
    except Exception:      # noqa: BLE001 — hiệu ứng KHÔNG được làm chết lượt xuất
        _hu = []

    # Có hiệu ứng nhóm SHADER trong bộ đã chọn không -> quyết định việc mở
    # thiết bị Vulkan trong `build`. Để NGOÀI `build` vì `build` chạy lại cho
    # từng encoder (nvenc -> libx264) và nhánh LÙI ÊM bên dưới sửa `_hu`.
    def _can_vk_now() -> bool:
        try:
            from app.core import hieu_ung as _HU3
            return bool(_HU3.can_vulkan(_hu))
        except Exception:  # noqa: BLE001
            return False

    _can_vk = _can_vk_now()

    # ---- MỖI ĐIỂM NHẤN HÌNH PHẢI CÓ TIẾNG ĐI KÈM (xem khối `SFX_TREN_NEN_DB`)
    # Gộp 2 nguồn mốc thành MỘT danh sách rồi mới dựng lớp tiếng:
    #   * ĐIỂM NỐI đoạn — như cũ, loại theo `join_cats` (kể cả "none" = bỏ).
    #   * ĐIỂM NHẤN hiệu ứng — MỚI: loại suy từ KIỂU hiệu ứng
    #     (`loai_sfx_theo_hieu_ung`). Đây là chỗ bịt lỗi anh Hùng nêu: đo bản cũ
    #     ra ĐÚNG 0,0 dB chênh lệch ở mốc điểm nhấn = không có tiếng nào.
    # Mốc nào cách mốc đã nhận < `_SFX_CACH_MIN` thì BỎ (điểm nối thường trùng
    # điểm nhấn — 2 tiếng chồng nhau nghe thành "rào rào", đúng loại loè).
    _sfx_diem: list = []            # [(giây, nhóm, "nối"|"điểm nhấn")]
    if fx_whoosh:
        for _i, _off in enumerate(whoosh_offsets):
            if join_cats[_i] != "none":
                _sfx_diem.append((float(_off), join_cats[_i], "nối"))
        for _c in (_hu or []):
            _g = float(_c.get("bat", 0.0))
            if any(abs(_g - x[0]) < _SFX_CACH_MIN for x in _sfx_diem):
                continue
            _sfx_diem.append(
                (_g, loai_sfx_theo_hieu_ung(_c.get("khoa", "")), "điểm nhấn"))
        _sfx_diem = [x for x in sorted(_sfx_diem) if 0.0 <= x[0] < _out_dur]

    # MỨC NỀN của chính clip này — để tính hệ số cho tiếng động (xem
    # `tinh_gain_sfx`). Chỉ đo khi THẬT SỰ sắp chèn tiếng: clip không có điểm
    # nào thì không tốn một ms nào.
    # NGHE THẤY CÁI GÌ thì lấy CÁI ĐÓ làm nền: lồng tiếng AI đè tiếng gốc
    # (`dub_mute_original`, hoặc user kéo tiếng gốc gần 0) -> đo tiếng GỐC là
    # đo thứ khán giả KHÔNG nghe, ra hệ số sai hẳn. Lúc đó đo chính file dub.
    _nen_db = _SFX_NEN_MAC_DINH
    _loi_db = _SFX_NEN_MAC_DINH + _SFX_LOI_SUY_RA
    _dinh_goc = -6.0
    _con_goc = bool(has_audio and use_voice and voice_vol > 0.05)
    _vao_a: list = []
    if _sfx_diem and _con_goc:
        if multi and _seg_list:
            _vao_a = ["-f", "concat", "-safe", "0", "-i", _seg_list]
        else:
            _s0, _e0 = segs[0]
            _vao_a = ["-ss", f"{_s0:.3f}", "-t", f"{_e0 - _s0:.3f}",
                      "-i", str(src)]
    elif _sfx_diem and dub_on:
        _vao_a = ["-i", str(dub_path)]
    _bao_goc: list = []          # đường bao RMS 50 ms của tiếng nguồn (dBFS)
    _bao_buoc = 0.05
    if _vao_a:
        _mc = _do_muc_clip(_vao_a)
        if _mc is not None and -70.0 < _mc["nen"] < 0.0:
            # tiếng gốc còn bị nhân `voice_vol` trong graph -> nền THẬT ở đầu ra
            # thấp hơn chỗ đo đúng bấy nhiêu dB. Không tính bù là tiếng động
            # thành nhỏ so với lời khi user kéo thanh "âm lượng tiếng gốc".
            # (đường DUB thì file dub vào mix ở mức 1,0 -> không bù.)
            _bu = (20.0 * math.log10(max(voice_vol, 0.001))
                   if _con_goc else 0.0)
            _nen_db = _mc["nen"] + _bu
            _loi_db = _mc["loi"] + _bu
            _dinh_goc = _mc["dinh"] + _bu
            # ĐƯỜNG BAO (đã bù `voice_vol` như 3 mốc trên) -> mức lời CỤC BỘ
            # tại TỪNG mốc. Đây là số chữa lỗi "nói át rồi": bản cũ chỉ có mức
            # lời CẢ CLIP nên mốc rơi vào lúc đang nói bị tính hụt tới 5,2 dB.
            _bao_goc = [float(v) + _bu for v in (_mc.get("bao") or [])]
            _bao_buoc = float(_mc.get("buoc") or 0.05)
    # TRẦN CỦA LỚP HẠN ĐỈNH CUỐI phải tính TRƯỚC trần lớp (xem `_tran_lop`).
    _tran_tron = max(_SFX_TRAN_TRON_DB, min(-0.2, _dinh_goc - 1.2))
    # TRẦN ĐỈNH CỦA MỘT LỚP tiếng động — bám theo ĐÍCH của chính clip này chứ
    # không cố định. Clip yên có đích thấp; nếu vẫn cho lớp đội đỉnh tới
    # -2 dBFS thì cộng với tiếng gốc là vượt trần, và lớp hạn đỉnh cuối gọt
    # đúng vào giây điểm nhấn (đo: mốc tụt -0,6 dB). Hạ trần lớp theo đích thì
    # limiter gần như không phải làm gì mà độ to KHÔNG đổi.
    # THÊM 09/08/2026 — vế `_tran_tron - _SFX_LOP_DUOI_TRON`: lớp tiếng động
    # KHÔNG được phép một mình chiếm gần hết trần của bản trộn. Nguồn NÓNG
    # (đỉnh -2,45 dBFS) mà lớp cũng đội tới -2,0 thì tổng vượt xa trần, và lớp
    # hạn đỉnh CUỐI phải gọt 5-8 dB — nó gọt vào đúng cú va (đo: SFX -9,2 ->
    # -16,6 dBFS). Gọt SỚM ở nhánh SFX thì `alimiter` chỉ hạ ĐỈNH mà GIỮ độ to,
    # nên tiếng động vẫn đủ to trong khi bản trộn không còn phải gọt gì.
    _tran_lop = max(-20.0, min(_SFX_DINH_TRAN_DB,
                               _tran_tron - _SFX_LOP_DUOI_TRON,
                               dich_sfx_dB("impact", _nen_db, _loi_db)
                               + _SFX_CREST_CHO))
    #: (nền, mức lời, trần lớp, trần bản trộn) — truyền cho
    #: `_pick_sfx_by_category` để nó chỉ bốc file KÊU NỔI tới mức clip này cần.
    _muc_ba = (_nen_db, _loi_db, _tran_lop, _tran_tron)
    # ---- MỨC LỜI **CỤC BỘ** TẠI TỪNG MỐC (chữa "nói át rồi", 09/08/2026) ----
    # Mỗi mốc một con số riêng: `_loi_moc[i]` = đỉnh RMS 50 ms của tiếng NGUỒN
    # trong ±0,175 s quanh chính mốc đó, `_noi_moc[i]` = mốc đó có rơi vào lúc
    # ĐANG NÓI không. Thiếu đường bao (nguồn câm / đo hỏng) -> None + False =
    # rơi đúng về đường cũ, không mốc nào đổi.
    _loi_moc: list = []
    _noi_moc: list = []
    for _g, _c2, _v2 in _sfx_diem:
        _lm = (muc_tai_moc(_bao_goc, _bao_buoc, _g) if _bao_goc else None)
        _loi_moc.append(_lm)
        _noi_moc.append(bool(_bao_goc)
                        and la_moc_dang_noi(_bao_goc, _bao_buoc, _g))
    # TRẦN LỚP theo TỪNG mốc: mốc đang nói có đích cao hơn nên trần lớp phải
    # nhích theo, không thì `alimiter` nhánh SFX gọt mất đúng phần vừa nâng.
    # DUCKING TRẢ LẠI CHỖ TRỐNG — phải cộng vào, không thì bóp chết chính cú va.
    # Ở mốc ĐANG NÓI, tiếng gốc đã bị hạ TRỌN `_SFX_DUCK_DB_NOI` đúng tại mốc
    # (đỉnh bướu rơi vào mốc), tức bản trộn có thêm ngần ấy dB chỗ trống. Không
    # cộng lại thì `_tran_tron - _SFX_LOP_DUOI_TRON` chỉ cho lớp SFX đội đỉnh
    # hơn đích đúng **1,0 dB** trên nguồn nóng -> `alimiter` nhánh SFX ép hệ số
    # đỉnh 11 dB xuống 1 dB và lấy mất luôn độ to (đo: lớp ra -14,3 dBFS trong
    # khi đích -8,7 = hụt 5,6 dB, mốc thành KHÔNG NGHE RA).
    _tran_moc = [max(-20.0, min(_SFX_DINH_TRAN_DB,
                                _tran_tron - _SFX_LOP_DUOI_TRON
                                + (_SFX_DUCK_DB_NOI if _n3 else 0.0),
                                dich_sfx_dB("impact", _nen_db, _loi_db, _lm)
                                + _SFX_CREST_CHO))
                 for _lm, _n3 in zip(_loi_moc, _noi_moc)]
    # TRẦN CỦA LỚP HẠN ĐỈNH CUỐI — **BÁM THEO ĐỈNH CỦA CHÍNH NGUỒN**.
    # Nguồn của anh Hùng có bản master VƯỢT 0 dBFS (đo "Parker and Chester":
    # bản TẮT tiếng động xuất ra đỉnh **+0,51 dBFS**, tức app đang ra file MÉO
    # SẴN). Nếu cứ hạ cứng về -2 dBFS thì lớp hạn đỉnh gọt luôn cả TIẾNG GỐC ở
    # những chỗ nguồn đang to — nên đúng mốc điểm nhấn, bản BẬT lại THẤP HƠN
    # bản TẮT (đo: -0,9 dB, cổng 44 hỏng 2/5 lượt). Quy tắc:
    #   * bình thường (nguồn <= -1,5 dBFS): trần = `_SFX_TRAN_TRON_DB` (-2),
    #     file xuất ra đỉnh <= -1 dBFS đúng yêu cầu;
    #   * nguồn ĐÃ nóng hơn thế: trần bám đỉnh nguồn, LUÔN thấp hơn nó 1,2 dB
    #     -> bản có tiếng động **không bao giờ méo hơn bản không có**, mà cũng
    #     không bị làm nhỏ đi vô cớ.
    # 1,2 dB chứ không phải 0,6: AAC là mã hoá CÓ MẤT nên sóng giải ra VỌT LÊN
    # trên mức đã mã hoá ~0,5-0,9 dB. Để 0,6 thì đo được bản BẬT **+0,54 và
    # +0,74 dBFS** so với bản TẮT +0,51 — tức nhỉnh HƠN bản gốc, hỏng 2/5 lượt.
    # (`_tran_tron` tính ở TRÊN vì `_tran_lop`/`_tran_moc` phải bám theo nó.)

    def build(enc: str) -> list[str]:
        cmd = [settings.FFMPEG_PATH, "-y", *_global_enc_opts()]
        # THIẾT BỊ VULKAN cho nhóm hiệu ứng SHADER (`libplacebo`). CHỈ thêm khi
        # bộ hiệu ứng đã chọn THẬT SỰ có shader — đó là cách giữ BẤT BIẾN SỐNG
        # CÒN: mức "tat" (và mọi bộ không shader) ra lệnh ffmpeg KHÔNG khác một
        # ký tự nào so với bản `main`, nên file xuất giống hệt (đo PSNR 99 dB ở
        # cổng 36). Máy không có Vulkan thì `hieu_ung.dung_duoc()` đã loại hết
        # shader từ bước CHỌN nên nhánh này không bao giờ chạy tới.
        if _can_vk:
            cmd += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
        parts = []
        # Các input phụ (màu nền/overlay/nhạc/dub) đánh số sau input video.
        vin = 1
        if multi:
            cmd += ["-f", "concat", "-safe", "0", "-i", _seg_list]
        else:
            s, e = segs[0]
            cmd += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src)]
        content, aud, aud_map = "[0:v]", "[0:a]", "0:a?"
        # CHE CHỮ CHÁY SẴN: áp TRƯỚC MỌI THỨ, kể cả `hflip`. Toạ độ dải do
        # `do_dai_chu` trả về là PIXEL CỦA KHUNG NGUỒN — mà `[0:v]` ở đây đúng
        # là khung nguồn ở CẢ HAI đường (một đoạn = `-ss/-t` trên nguồn; nhiều
        # đoạn = concat các mezzanine pha 1, mà `_build_seg` KHÔNG có filter
        # scale nào nên mảnh giữ nguyên cỡ nguồn). Đặt SAU `hflip` thì x0/x1 bị
        # soi gương -> che lệch sang mép đối diện với dải chữ trên video không
        # đối xứng ngang.
        if _cc_loc:
            parts.append(f"{content}{_cc_loc}[cche]")
            content = "[cche]"
        # LẬT GƯƠNG: hflip áp lên KHỐI video content SỚM NHẤT (ngay sau khi lấy
        # content, TRƯỚC pre_crop/reframe/overlay PNG/phụ đề/fade). Nhờ vậy chỉ
        # HÌNH bị soi gương; overlay chữ + phụ đề .ass chồng SAU nên KHÔNG ngược.
        if flip_h:
            parts.append(f"{content}hflip[cflip]")
            content = "[cflip]"
        vsrc = content
        if pre_crop:
            parts.append(f"{content}crop={pre_crop}[cc]")
            vsrc = "[cc]"
        if bg == "fill":            # CROP cắt 2 bên cho video ĐẦY khung 9:16
            parts.append(f"{vsrc}scale={out_w}:{out_h}:"
                         f"force_original_aspect_ratio=increase,"
                         f"crop={out_w}:{out_h},setsar=1[vv]")
            nextidx = vin
        elif bg == "blur":
            # NHẸ: blur trên ảnh THU NHỎ 1/4 rồi phóng to -> rẻ ~16 lần, nhìn y hệt.
            bw, bh = max(2, out_w // 4), max(2, out_h // 4)
            br = max(2, blur_amt // 4)
            parts.append(f"{vsrc}split=2[bv][fv]")
            parts.append(f"[bv]scale={bw}:{bh}:force_original_aspect_ratio=increase,"
                         f"crop={bw}:{bh},boxblur={br}:1,"
                         f"scale={out_w}:{out_h},setsar=1[base]")
            parts.append(f"[fv]scale={vw}:-2:flags=lanczos,setsar=1[fg]")
            parts.append(f"[base][fg]overlay=x='{cx:.4f}*W-w/2':"
                         f"y='{cy:.4f}*H-h/2'[vv]")
            nextidx = vin
        else:
            col = "white" if bg == "white" else "black"
            cmd += ["-f", "lavfi", "-t", f"{total:.3f}",
                    "-i", f"color=c={col}:s={out_w}x{out_h}:r=30"]
            parts.append(f"[{vin}:v]setsar=1[base]")
            parts.append(f"{vsrc}scale={vw}:-2:flags=lanczos,setsar=1[fg]")
            parts.append(f"[base][fg]overlay=x='{cx:.4f}*W-w/2':"
                         f"y='{cy:.4f}*H-h/2'[vv]")
            nextidx = vin + 1
        final = "[vv]"
        if use_png:
            cmd += ["-i", str(overlay_png)]
            parts.append(f"[vv][{nextidx}:v]overlay=0:0[v]")
            final = "[v]"
        # NHẠC NỀN: thêm input (loop vô hạn, cắt theo độ dài clip ở dưới)
        bgm_idx = None
        aidx = nextidx + (1 if use_png else 0)
        if bgm_path and os.path.exists(str(bgm_path)):
            bgm_idx = aidx
            aidx += 1
            cmd += ["-stream_loop", "-1", "-i", str(bgm_path)]
        # LỒNG TIẾNG AI: wav đã dựng sẵn dài đúng bằng clip (timeline gốc)
        dub_idx = None
        if dub_on:
            dub_idx = aidx
            aidx += 1
            cmd += ["-i", str(dub_path)]
        # 🔦 SPOTLIGHT: LÀM TỐI NHẸ khối frame trong các khoảng AI KỂ — áp
        # TRƯỚC khi đốt phụ đề (.ass)/overlay chữ nên CHỮ vẫn SÁNG rõ, chỉ
        # HÌNH dịu xuống. dim_ranges dùng hệ quy chiếu timeline ĐẦU RA (sau
        # speed) — CÙNG duck_ranges — nhưng eq đặt TRƯỚC setpts nên `t` ở
        # đây là timeline TRƯỚC speed => nhân vspeed để đổi mốc đầu ra ->
        # mốc nội bộ (khớp ĐÚNG khoảng duck âm thanh). eq=brightness nhận
        # -1..1; dim_amt<=0.5 -> tối nhẹ, KHÔNG về đen (vẫn nhìn rõ).
        if dims and dim_amt > 0.0005:
            expr = "+".join(
                f"between(t,{a * vspeed:.3f},{b * vspeed:.3f})"
                for a, b in dims)
            parts.append(f"{final}eq=brightness=-{dim_amt:.4f}:"
                         f"enable='{expr}'[vdim]")
            final = "[vdim]"
        # HIỆU ỨNG ĐIỂM NHẤN — đặt TRƯỚC khi đốt .ass/overlay chữ nên hình có
        # hiệu ứng mà CHỮ vẫn nét (y như spotlight ở trên). Mốc `_hu` ở timeline
        # ĐẦU RA (xem chỗ chọn ở trên), còn `t` ở đây là timeline TRƯỚC setpts
        # => nhân vspeed (cùng cách quy đổi với dim_ranges/duck_ranges).
        # `fps` truyền vào là fps của LUỒNG ĐI VÀO zoompan (`_hu_fps`, đã tính ở
        # trên theo `bg`) — đặt sai là clip dài/ngắn hơn tiếng, xem LỖI 1.
        if _hu:
            _hu_t = [dict(c, bat=float(c["bat"]) * vspeed,
                          het=float(c["het"]) * vspeed) for c in _hu]
            try:
                from app.core import hieu_ung as _HU2
                # truyền FONT ĐÃ TRA (`_font`), KHÔNG truyền `fonts_dir` thô:
                # `chuoi_filter("")` bỏ luôn bước tự tìm font nên hiệu ứng cần
                # font bị VỨT trong khi chỗ chọn ở trên lại thấy có font ->
                # nhật ký một đằng, file một nẻo (đúng LỖI 5 vừa bịt).
                _ch = _HU2.chuoi_filter(_hu_t, out_w, out_h, _hu_fps, _font)
            except Exception:  # noqa: BLE001
                _ch = ""
            if _ch:
                parts.append(f"{final}{_ch}[vhu]")
                final = "[vhu]"
        if ass_path and os.path.exists(ass_path):
            ap = str(ass_path).replace("\\", "/").replace(":", "\\:")
            sub = f"subtitles='{ap}'"
            if fonts_dir:
                fd = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
                sub += f":fontsdir='{fd}'"
            parts.append(f"{final}{sub}[vsub]")
            final = "[vsub]"
        # TĂNG TỐC/GIÃN VIDEO: setpts SAU phụ đề -> chữ đốt sẵn nên vẫn KHỚP.
        # vspeed = speed/dub_stretch: user tua nhanh + giãn khớp giọng gộp làm 1.
        if abs(vspeed - 1.0) > 0.001:
            parts.append(f"{final}setpts=PTS/{vspeed:.5f}[vsp]")
            final = "[vsp]"
        # Độ dài OUTPUT (sau setpts) — dùng cho fade cuối + cắt audio.
        out_dur = total / vspeed if abs(vspeed - 1.0) > 0.001 else total
        # HIỆU ỨNG FADE hình NHẸ đầu/cuối (~0.35s) — TINH TẾ, chuyên nghiệp,
        # KHÔNG lố. Áp SAU cùng (sau overlay/phụ đề/setpts) trên khung ĐẦU RA
        # nên khớp thời lượng thật; fade nhẹ nên phần chữ chớm mờ 0.35s đầu/cuối
        # là chấp nhận được (yêu cầu). Bỏ qua nếu clip quá ngắn.
        _fd = 0.35
        if fx_fade and out_dur > _fd * 2 + 0.05:
            fout_st = max(0.0, out_dur - _fd)
            parts.append(f"{final}fade=t=in:st=0:d={_fd:.3f},"
                         f"fade=t=out:st={fout_st:.3f}:d={_fd:.3f}[vfx]")
            final = "[vfx]"
        # ĐỔI GIỌNG + tốc độ cho AUDIO GỐC (chỉ khi video CÓ tiếng)
        af = []
        if abs(pitch - 1.0) > 0.01:     # đổi cao độ giọng (giữ tốc độ)
            af += [f"asetrate=48000*{pitch:.4f}", "aresample=48000",
                   f"atempo={1.0/pitch:.4f}"]
        if abs(vspeed - 1.0) > 0.001:   # tiếng gốc theo tốc độ video hiệu dụng
            af.append(_atempo_chain(vspeed))
        # ---- TRỘN AUDIO: tiếng gốc (+lọc) / lồng tiếng AI / nhạc nền ----
        # Tiếng gốc áp voice_vol (thanh kéo "Âm lượng tiếng gốc"); có lồng tiếng
        # + để mặc định thì tự hạ nền (đã tính ở voice_vol trên), hoặc bỏ hẳn
        # (dub_mute_original). amix normalize=0 để giữ nguyên âm lượng từng lớp.
        mix: list[str] = []
        amap = None
        # Whoosh chuyển đoạn -> cũng là 1 lớp cần TRỘN vào tiếng gốc (nếu có)
        # nên phải tính vào need_mix để tiếng gốc đi qua [vce] chứ không map thẳng
        # (map thẳng sẽ để [caud] treo + whoosh nuốt mất tiếng gốc).
        # `_sfx_diem` GỘP điểm nối + điểm nhấn hiệu ứng (tính ngoài `build`).
        whoosh_on = bool(fx_whoosh and _sfx_diem)
        # voice_vol==0 -> tiếng gốc câm hẳn: BỎ khỏi mix (như dub_mute) để amix
        # không thừa 1 nhánh im lặng làm loãng các lớp khác.
        include_voice = use_voice and voice_vol > 0.0005
        if include_voice:
            vf = ["aresample=48000"] + af
            apply_vol = abs(voice_vol - 1.0) > 0.001
            if apply_vol:
                vf.append(f"volume={voice_vol:.3f}")   # âm lượng tiếng gốc
            # DUCKING theo TIẾNG ĐỘNG: hạ tiếng gốc ~5 dB đúng lúc tiếng động
            # kêu (vào/ra êm — xem `_bieu_thuc_duck`). Nhờ nó tiếng động nghe
            # RÕ mà không phải kéo to lên đè giọng nói. Không có điểm nào ->
            # KHÔNG thêm filter nào (đường cũ y nguyên).
            if whoosh_on:
                # SÂU HƠN chỉ ở mốc rơi vào lúc ĐANG NÓI — xem `_SFX_DUCK_DB_NOI`.
                _dk = _bieu_thuc_duck(
                    [g for g, _c, _n in _sfx_diem],
                    sau_db=[(_SFX_DUCK_DB_NOI if _n2 else _SFX_DUCK_DB)
                            for _n2 in _noi_moc],
                    dang_noi=_noi_moc)
                if _dk:
                    vf.append(_dk)
            if ducks:
                # 🎙 RECAP: HẠ tiếng gốc xuống _DUCK_LEVEL (nền văng vẳng ~12%
                # — video 'sống' như kênh recap thật, KHÔNG câm tuyệt đối)
                # trong các khoảng AI đang nói. Đặt SAU atempo (af) nên t =
                # timeline ĐẦU RA (sau speed) — caller đã chia mốc cho speed.
                # Chỉ nhánh tiếng gốc, không đụng lớp khác. (dub_mute_original
                # đi đường khác — use_voice=False, không qua đây.)
                expr = "+".join(f"between(t,{a:.3f},{b:.3f})"
                                for a, b in ducks)
                vf.append(f"volume={_DUCK_LEVEL}:enable='{expr}'")
            need_mix = ((dub_idx is not None) or (bgm_idx is not None)
                        or whoosh_on or bool(ducks))
            if need_mix or af or apply_vol:
                parts.append(f"{aud}{','.join(vf)}[vce]")
                mix.append("[vce]")
            else:
                amap = aud_map  # KHÔNG lọc/trộn -> map thẳng (giữ hành vi cũ)
        if dub_idx is not None:
            dch = ["aresample=48000"]
            # Dub track đã dài = total*dub_stretch (timeline đã giãn để khớp
            # video setpts). Chỉ cần theo `speed` (user tua nhanh) -> ra out_dur
            # = total*dub_stretch/speed = total/vspeed, KHỚP video. KHÔNG atempo
            # theo dub_stretch (nếu không dub sẽ nhanh gấp đôi so với hình).
            if abs(speed - 1.0) > 0.01:
                dch.append(_atempo_chain(speed))
            parts.append(f"[{dub_idx}:a]{','.join(dch)},atrim=0:{out_dur:.3f},"
                         f"asetpts=PTS-STARTPTS[dub]")
            mix.append("[dub]")
        if bgm_idx is not None:
            # nhạc nền: chỉnh âm lượng + cắt đúng độ dài clip (sau tăng tốc)
            parts.append(f"[{bgm_idx}:a]volume={max(0.0, min(1.0, bgm_vol)):.3f},"
                         f"atrim=0:{out_dur:.3f},asetpts=PTS-STARTPTS[bgm]")
            mix.append("[bgm]")
        # HIỆU ỨNG TIẾNG CHUYỂN ĐOẠN: cú NHỎ tại MỖI điểm ghép (chỉ khi >1 đoạn).
        # Ưu tiên THƯ MỤC tiếng động của user (fx_sfx_dir) nếu có file -> mỗi
        # điểm ghép lấy NGẪU NHIÊN 1 file (adelay + volume ~0.3, cắt out_dur,
        # KHÔNG lặp). Không có -> dùng bộ tiếng TỔNG HỢP đa dạng (thuần ffmpeg,
        # chạy mọi máy khách). Mốc ghép tính ở timeline ĐẦU RA (chia vspeed vì
        # video/tiếng đã tăng/giãn tốc). Nếu tiếng chuyển đoạn là NGUỒN audio
        # DUY NHẤT (video câm) -> thêm 1 nền im lặng dài đủ clip trước để amix
        # duration=first không cắt cụt output.
        if whoosh_on:
            # `_sfx_diem` đã lọc "none" (AI chỉ định KHÔNG chèn) và đã gộp
            # ĐIỂM NỐI + ĐIỂM NHẤN HÌNH ở ngoài `build`.
            n_joint = len(_sfx_diem)
            # reset log MỖI lần export (mọi điểm "none" -> danh sách rỗng).
            # `build()` có thể chạy LẦN 2 (lùi nvenc -> libx264) nên phải gán
            # lại từ đầu, không được cộng dồn.
            global _SFX_LAST_PICK
            _SFX_LAST_PICK = []
            if tieng_dong_log is not None:
                del tieng_dong_log[:]
            base_had_audio = len(mix) > 0 or (amap is not None)
            if not base_had_audio and n_joint:
                # nền im lặng đủ dài để giữ độ dài + làm nhánh 'first' của amix
                sil_idx = aidx
                aidx += 1
                cmd += ["-f", "lavfi", "-t", f"{out_dur:.3f}",
                        "-i", "anullsrc=r=48000:cl=stereo"]
                parts.append(f"[{sil_idx}:a]asetpts=PTS-STARTPTS[wbed]")
                mix.append("[wbed]")
            import random as _rnd
            active_cats = [c for _g, c, _n in _sfx_diem]
            active_offs = [g for g, _c, _n in _sfx_diem]
            active_vais = [n for _g, _c, n in _sfx_diem]
            # ƯU TIÊN 1 — THƯ MỤC tiếng động của USER (giữ tính năng cũ): có file
            # hợp lệ -> mỗi mốc lấy NGẪU NHIÊN 1 file (không phân loại ngữ cảnh
            # vì file user tùy ý). random.sample tránh trùng khi đủ.
            sfx_files = _list_sfx_files(fx_sfx_dir) if n_joint else []
            if sfx_files:
                if len(sfx_files) >= n_joint:
                    picked = _rnd.sample(sfx_files, n_joint)
                else:
                    picked = [_rnd.choice(sfx_files) for _ in range(n_joint)]
                picks = list(zip(active_cats, picked))
            else:
                # ƯU TIÊN 2 — THƯ VIỆN ĐÓNG GÓI theo NGỮ CẢNH. Mỗi mốc chọn 1
                # file trong đúng nhóm (không lặp liên tiếp cùng nhóm). Nhóm
                # THIẾU file (bản cũ chưa có thư viện) -> ƯU TIÊN 3: lùi bộ
                # tiếng TỔNG HỢP hợp loại (cũng tránh lặp liên tiếp).
                # `loi_mocs` = mức lời CỤC BỘ từng mốc -> mốc đang nói lọc theo
                # đích CAO hơn, chỉ nhận file thật sự kêu nổi tới mức đó.
                picks = (_pick_sfx_by_category(active_cats, muc=_muc_ba,
                                               loi_mocs=_loi_moc,
                                               noi_mocs=_noi_moc)
                         if n_joint else [])
            _tu_user = bool(sfx_files)
            last_synth: dict = {}
            chosen_log: list = []
            for wi, ((cat, fpath), off, vai) in enumerate(
                    zip(picks, active_offs, active_vais)):
                w_idx = aidx
                aidx += 1
                if fpath:
                    # === CHUẨN HOÁ THEO SỐ ĐO (thay hệ số cứng `_SFX_CAT_VOL`)
                    # Bản cũ nhân cứng 0,24-0,42 cho mọi file trong khi kho trải
                    # 26,5 dB -> tiếng động chỉ nhô +0,7 dB trên nền = KHÔNG
                    # NGHE THẤY. Bản v2.18.0 chuẩn hoá theo `mean` của file rồi
                    # KẸP GAIN cho đỉnh <= -1 dBFS -> clip ồn thì vế kẹp thắng
                    # 74% số file (thiếu trung vị 8,9 dB). NAY: chuẩn hoá theo
                    # **đỉnh RMS 50 ms** và gọt đỉnh bằng `alimiter` (giữ độ to).
                    _mean, _max, _st = _muc_sfx3(str(fpath))
                    # `loi_moc` = MỨC LỜI CỤC BỘ tại chính mốc này — chữa "nói
                    # át rồi": bản cũ đưa MỘT mức lời của CẢ CLIP cho mọi mốc
                    # nên mốc rơi vào lúc đang nói bị tính hụt (đo: tiếng động
                    # thấp hơn giọng nói 1,6 dB trung vị = bị che).
                    vol = tinh_gain_sfx(cat, _mean, _max, _nen_db,
                                        st_db=_st, loi_db=_loi_db,
                                        loi_moc=_loi_moc[wi])
                    # DÓNG CHỖ TO NHẤT của tiếng vào ĐÚNG giây điểm nhấn: đẩy
                    # sớm lên bằng "giây xảy ra đỉnh" của chính file đó. Không
                    # dóng thì tiếng vào chậm (ding/sparkle) kêu SAU cú va nên
                    # không đánh dấu gì — xem `_moc_dinh_sfx`.
                    _dich = min(_SFX_DICH_TOI_DA, _moc_dinh_sfx(str(fpath)))
                    d_ms = max(0, int(round((off - _dich) * 1000)))
                    cmd += ["-i", str(fpath)]
                    parts.append(
                        f"[{w_idx}:a]aresample=48000,{_SFX_PAN_GIU_MUC},"
                        f"volume={vol:.4f},"
                        f"{_han_dinh(_tran_moc[wi])},"
                        f"adelay={d_ms}|{d_ms},atrim=0:{out_dur:.3f},"
                        f"asetpts=PTS-STARTPTS[wh{wi}]")
                    chosen_log.append((cat, os.path.basename(str(fpath))))
                    if tieng_dong_log is not None:
                        tieng_dong_log.append(
                            {"giay": round(float(off), 2), "loai": cat,
                             "ten": os.path.basename(str(fpath)),
                             "vai": vai,
                             # MỐC NÀY CÓ RƠI VÀO LÚC ĐANG NÓI KHÔNG — quyết
                             # định CẢ đích độ to LẪN kiểu ducking (nông/sau
                             # mốc vs sâu/trùm mốc). Không ghi ra thì cổng đo
                             # ducking phải ĐOÁN cửa sổ, và nó đã đoán sai một
                             # lần (đo bằng cửa sổ của ca khoảng lặng trên mốc
                             # đang nói -> ra −0,1 dB rồi kết luận "không có
                             # ducking" trong khi ducking đang hạ 5,9 dB).
                             "noi": bool(_noi_moc[wi]),
                             "db": round(20.0 * math.log10(max(vol, 1e-6)), 1),
                             "nguon": ("thư mục của bạn" if _tu_user
                                       else "kho tiếng động của app")})
                else:
                    # thiếu thư viện -> tiếng tổng hợp hợp loại. Bộ tổng hợp
                    # sinh bằng lavfi nên biên độ đã biết (~ -6 dBFS đỉnh):
                    # quy về cùng đích bằng cách coi mean ~ -14 dB.
                    tidx = _pick_synth_for_category(
                        cat, last_synth.get(cat), _rnd)
                    last_synth[cat] = tidx
                    vol = tinh_gain_sfx(cat, -14.0, -6.0, _nen_db,
                                        st_db=-10.0, loi_db=_loi_db,
                                        loi_moc=_loi_moc[wi])
                    in_args, branch = _fx_synth_branch(
                        tidx, off, vol, w_idx, f"wh{wi}")
                    cmd += in_args
                    parts.append(branch)
                    chosen_log.append((cat, f"synth#{tidx}"))
                    if tieng_dong_log is not None:
                        tieng_dong_log.append(
                            {"giay": round(float(off), 2), "loai": cat,
                             "ten": f"tự sinh #{tidx}", "vai": vai,
                             "noi": bool(_noi_moc[wi]),
                             "db": round(20.0 * math.log10(max(vol, 1e-6)), 1),
                             "nguon": "ffmpeg tự sinh"})
                mix.append(f"[wh{wi}]")
            # cho test/log biết ĐÃ chọn loại+file gì tại mỗi mốc
            _SFX_LAST_PICK = chosen_log
        if len(mix) == 1:
            amap = mix[0]
        elif len(mix) >= 2:
            parts.append("".join(mix) + f"amix=inputs={len(mix)}:"
                         f"duration=first:normalize=0[aout]")
            amap = "[aout]"
        # ---- HẠN ĐỈNH SAU KHI TRỘN — chỗ DUY NHẤT bảo đảm KHÔNG MÉO ----
        # `amix normalize=0` là phép CỘNG: nguồn thật đo được đỉnh **0,0 dBFS**
        # (video "Parker and Chester"), cộng thêm bất kỳ lớp nào cũng vượt trần
        # -> không một cách kẹp lớp riêng nào cứu được, phải gọt ở đây.
        # CHỈ thêm khi thật sự có tiếng động: mọi đường khác (kể cả mức "tat")
        # giữ nguyên `[aout]` -> chuỗi filter KHÔNG khác một ký tự nào so với
        # bản cũ (bất biến sống còn, cổng 36 đo PSNR).
        if whoosh_on and amap and amap.startswith("["):
            parts.append(f"{amap}{_han_dinh(_tran_tron, nha=10)}[alim]")
            amap = "[alim]"
        # amap còn None + không voice -> video câm, chỉ xuất hình
        cmd += ["-filter_complex", ";".join(parts), "-map", final]
        if amap:
            cmd += ["-map", amap]
        cmd += [*_enc_args(enc, "high"), "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart", str(dst)]
        return cmd

    # ffmpeg log 'time=' là thời gian OUTPUT -> tổng thời lượng ra = total/vspeed
    # (vspeed=speed/dub_stretch); dùng total gốc sẽ làm thanh % kẹt rồi nhảy vọt.
    out_total = total / vspeed if abs(vspeed - 1.0) > 0.001 else total
    # multi: pha tách đã chiếm 0..0.35 thanh % -> pha cuối chạy 0.35..1.0
    _prog = (None if on_progress is None else
             ((lambda p: on_progress(0.35 + 0.65 * p)) if multi
              else on_progress))
    try:
        try:
            from app.queue.worker import CanceledError as _Huy
        except Exception:                # noqa: BLE001
            _Huy = ()                    # không nạp được -> không bắt nhầm ai
        try:
            _run_with_fallback(build, encoder, out_total, _prog,
                               "xuất được clip", dst=dst)
        except _Huy:
            raise                        # HUỶ là HUỶ — không được "lùi êm"
        except Exception:                # noqa: BLE001
            # LÙI ÊM KHI GPU HỎNG GIỮA CHỪNG. `hieu_ung.dung_duoc()` đã dò
            # Vulkan bằng một lượt render THẬT lúc chọn hiệu ứng, nhưng giữa
            # lúc xuất thì driver vẫn có thể chết / GPU bị lượt khác chiếm /
            # máy ảo mất thiết bị. Khi ấy thà xuất clip KHÔNG có 1-2 điểm nhấn
            # còn hơn để cả clip FAIL — đúng cách `_tach_va_noi_manh` lùi từ
            # GPU về CPU. Chỉ thử LẠI ĐÚNG 1 LẦN và chỉ khi lượt vừa rồi CÓ
            # shader, nên lỗi thật (hết đĩa, mốc cắt ngoài phim…) vẫn nổ TO
            # ngay lần đầu chứ không bị nuốt.
            if not _can_vk:
                raise
            try:
                from app.core import hieu_ung as _HU4
                _hu = _HU4.bo_shader(_hu)
            except Exception:            # noqa: BLE001
                _hu = []
            _can_vk = False
            if hieu_ung_log is not None:
                del hieu_ung_log[:]
                hieu_ung_log.extend(_hu)
            # bỏ luôn TIẾNG của những điểm nhấn vừa bị gỡ — nhật ký khoe tiếng
            # cho một hiệu ứng KHÔNG có trong file là đúng kiểu "một đằng một
            # nẻo" đã sập ở LỖI 5. Điểm NỐI thì giữ nguyên (không liên quan GPU).
            _con = {round(float(c.get("bat", 0.0)), 3) for c in (_hu or [])}
            _sfx_diem = [x for x in _sfx_diem
                         if x[2] == "nối" or round(x[0], 3) in _con]
            _run_with_fallback(build, encoder, out_total, _prog,
                               "xuất được clip", dst=dst)
    finally:
        # dọn file đoạn tạm + file danh sách MỌI trường hợp (xong/lỗi/hủy).
        # `_cleanup_paths` nay THỬ LẠI ~2,1s khi file còn bị khoá (ffmpeg vừa bị
        # kill) và ghi SỔ NỢ cái nào vẫn không xoá được -> `don_rac_ton()` ở
        # lượt xuất sau nhặt nốt. Trước đây nuốt PermissionError im lặng.
        _cleanup_paths(_seg_temps + ([_seg_list] if _seg_list else []))
    return True


# ======================================================================
# CHUẨN HOÁ ĐỘ TO CHO **FILE CLIP ĐÃ XUẤT** (mọi đường xuất)
# ======================================================================
#
# Anh Hùng 16/08/2026: *"tool cắt sao phần giọng nói ít tiếng quá"*. Đường THAY
# TIẾNG đã chữa (`thay_giong.chuan_do_to`). Đo tiếp đường CẮT ra một lỗ hổng
# KHÁC, và nó nặng hơn (`_kq_lufs_duong.json`, ffmpeg thật trên 4 video thật):
#
#   * ĐỘ TO TRẢI **15,75 LU** giữa các clip (−6,65 .. −22,40) — đường cắt
#     KHÔNG có một bước chuẩn hoá nào, clip to hay nhỏ hoàn toàn tuỳ đoạn phim
#     cắt trúng. Clip −22,40 thấp hơn đích **8,4 LU**.
#   * **ĐỈNH THẬT VƯỢT 0 dBTP ở 3/8 bản xuất** (+3,94 · +0,94 · +0,66) = VỠ
#     TIẾNG thật. `alimiter` sau khi trộn CHỈ được thêm khi có tiếng động
#     (`whoosh_on`), nên đường cắt trần không ai chặn đỉnh.
#
# Lệch so với nguồn KHÔNG một chiều (+3,47 / −7,23) -> **không "chép mức nguồn"
# được, phải ĐO TỪNG CLIP**.
#
# ---------------------------------------------------------------------------
# THƯỚC: `ebur128`, **KHÔNG** phải `loudnorm` — ĐÃ TRUY RA BẰNG THƯỚC THỨ BA
# ---------------------------------------------------------------------------
# Luật của repo: hai thước lệch quá 0,5 LU thì DỪNG. Lượt hiệu chuẩn DỪNG thật
# (`cat_7963.mp4`: loudnorm −10,78 · ebur128 −10,20 = lệch 0,58 LU). Truy tiếp
# bằng **thước THỨ BA tự viết** (ITU-R BS.1770-4 bằng numpy, KHÔNG qua ffmpeg —
# xem `_do_hai_thuoc.py`):
#
#   thước 3 = −10,21 -> cách `ebur128` **0,008 LU** · cách `loudnorm` **0,572 LU**
#
# Cả 8 bản xuất đều lệch CÙNG CHIỀU ÂM (−0,12 .. −0,58 LU): **`loudnorm` pha đo
# ĐỌC THẤP**. Cả hai thước vẫn TUYẾN TÍNH (nhân −6/−3/0/+3 dB thì cả hai dịch
# đúng ±0,00-0,01 dB), nên đây KHÔNG phải phép đo hỏng — chỉ là hai bộ cổng
# (gating) chia khối khác nhau. Nhưng YouTube/TikTok đo theo BS.1770, nên lấy
# `loudnorm` làm đích là **đẩy clip TO HƠN đích thật tới 0,6 LU**.
#
# ---------------------------------------------------------------------------
# CÁCH ÁP: NÂNG THUẦN + HẠN ĐỈNH — *KHÔNG* dùng `loudnorm` để áp
# ---------------------------------------------------------------------------
# `loudnorm linear=true` **TỰ TỤT VỀ CHẾ ĐỘ ĐỘNG mà rc vẫn 0** khi không đủ chỗ
# trống tới trần đỉnh (đo trên đường thay tiếng: LRA 2,10 -> 1,90 = NÉN DẬP).
# Hệ số TĨNH thì giữ nguyên mọi cân bằng theo TOÁN HỌC: nhân cả bản trộn với
# cùng một số thì hiệu (giọng − nhạc − tiếng động) ở MỌI cửa sổ không đổi.

#: Đích độ to tích hợp. −14 LUFS cho mobile có cơ sở (AES 10268, 4,2 triệu
#: album); và mạng xã hội chỉ chuẩn hoá XUỐNG chứ KHÔNG nâng lên, nên clip
#: −22 LUFS phát ra nhỏ hơn hẳn mọi clip khác trong cùng luồng.
DICH_LUFS_CLIP = -14.0

#: Trần ĐỈNH THẬT (dBTP) của clip đã chuẩn hoá.
TRAN_DINH_THAT_CLIP = -1.0

#: Biên trừ hao đặt cho `alimiter`. Với QUÁ MẪU (dưới) `alimiter` giữ đúng
#: trần nên phần vọt còn lại chỉ là của **nén AAC (~+0,2 dB)**. Chọn 0,5 dB ->
#: bản AAC cuối ra ~−1,3 dBTP, còn dư ~0,3 dB cho lượt re-encode của TikTok
#: (AES TD1004: coder bit rate thấp vọt đỉnh nhiều hơn) — cùng cách tính đã
#: dùng cho đường thay tiếng.
BIEN_DINH_CLIP = 0.5

#: **QUÁ MẪU 4× QUANH `alimiter` — BẮT BUỘC, và đây là chỗ đã suýt sập.**
#:
#: `alimiter` chặn đỉnh **MẪU**, không chặn đỉnh **THẬT** (giữa hai mẫu), nên
#: nó không giữ nổi trần trên nguồn có cú va nhọn. Đo trên clip hệ số đỉnh
#: 22,8 dB (nâng +3,10 dB, trần `alimiter` −2,0):
#:
#: | chuỗi | ffmpeg `bin/` (N-125998) | ffmpeg trên PATH (N-121186) |
#: |---|---|---|
#: | `alimiter` trần trụi | −1,4 dBTP | **−0,0 dBTP (VƯỢT trần −1,0)** |
#: | **`aresample=192k` -> `alimiter` -> `aresample=48k`** | **−1,8** | **−1,8** |
#:
#: Hai điều rút ra:
#:  (1) không quá mẫu thì **kết quả PHỤ THUỘC BẢN ffmpeg** — lệch tới 1,4 dB.
#:      Bản `.exe` giao cho nhân viên dùng `bin/` (config trỏ thẳng), còn chạy
#:      TỪ NGUỒN thì `settings.FFMPEG_PATH = "ffmpeg"` lấy bản trên PATH. Tức
#:      **máy dev và máy thật chạy hai bản ffmpeg khác nhau** (bẫy "dev xanh,
#:      máy thật đỏ" của cổng 58, lần này ở tầng binary).
#:  (2) có quá mẫu thì hai bản ra **ĐÚNG MỘT SỐ**, và phần vọt còn lại đúng
#:      bằng phần của AAC (0,2 dB).
#: Giá: đo được **+0,05 giây/clip** (0,32 -> 0,37 s) — gần như cho không, vì
#: chỉ luồng TIẾNG đi qua. I và LRA **không đổi một ly** (−19,0 / 7,0 cả hai).
QUA_MAU_HAN_DINH = 192000

#: SÀN: clip đo dưới mức này thì **BỎ QUA**. Clip gần câm (video không tiếng,
#: đoạn phim im) đo ra −60..−70 LUFS; nâng về −14 là +46..+56 dB, và thứ được
#: nâng lúc đó là NỀN NHIỄU chứ không phải nội dung.
SAN_LUFS_CLIP = -45.0

#: Trần chỉnh độ to MỘT LƯỢT (dB, cả hai chiều) — chặn một lượt đo lỗi không
#: đẻ ra clip vỡ tiếng.
TRAN_CHINH_DO_TO_CLIP = 24.0

#: **CLIP ĐÃ ĐÚNG ĐỘ TO RỒI THÌ ĐỪNG ĐỤNG.** Lệch dưới mức này (và đỉnh đã
#: dưới trần) -> KHÔNG mã hoá lại audio: tránh một đời nén AAC thừa + tiết
#: kiệm ~1 giây/clip trên 200-300 kênh. 0,5 LU nằm dưới ngưỡng tai nghe ra
#: (~1 LU).
NGUONG_BO_QUA_LU = 0.5

#: NGÂN SÁCH GỌT (dB) — phần `alimiter` được phép cắt khỏi đỉnh.
#:
#: Đây là chỗ **BẤT KHẢ THI** phải nói thẳng: clip đo I −21,90 LUFS mà đỉnh
#: thật +0,90 dBTP có hệ số đỉnh **22,8 dB**; muốn vừa −14 LUFS vừa ≤ −1 dBTP
#: thì hệ số đỉnh phải còn 13 dB — tức PHẢI nén 10 dB. Không có cách nào vừa
#: đủ to vừa không đụng dải động. Quét ngân sách trên chính clip đó
#: (`_do_got_lra.py`, thước `ebur128`):
#:
#: | ngân sách gọt | 0 | 2 | 4 | **6** | 8 | 10,3 (đủ đích) |
#: |---|---|---|---|---|---|---|
#: | ΔLRA | +0,10 | 0,00 | +0,10 | **0,00** | −0,20 | **−0,80** |
#: | đỉnh thật sau | −1,50 | −0,90 | −1,10 | **−1,20** | −1,00 | **−0,50 (VƯỢT)** |
#:
#: Gọt hết cỡ vừa NÉN DẬP (ΔLRA −0,80) vừa **phá luôn trần đỉnh** (−0,50).
#: Chốt 6,0 dB: ΔLRA 0,00 và còn cách mốc hỏng (8 dB) một khoảng, đúng cách
#: đặt trần của cổng 56 CA17 (đừng siết sát số đo).
NGAN_SACH_GOT_DB = 6.0

#: LRA được phép TỤT bao nhiêu thì vẫn coi là "không nén dập".
#:
#: Ngân sách gọt MỘT MÌNH KHÔNG ĐỦ — đo ra hai clip cùng bị gọt mà phản ứng
#: ngược nhau: gọt 6,00 dB -> ΔLRA **0,00** (đỉnh là một cú va lẻ, ngắn hơn
#: khối 3 giây nên không đụng LRA) · gọt 4,70 dB -> ΔLRA **−0,60** (đoạn to
#: KÉO DÀI, gọt là đổi hẳn độ to khối). Vì vậy phải ĐO LẠI SAU KHI ÁP rồi mới
#: kết luận, và có đường LÙI ở dưới.
LRA_TUT_TOI_DA = 0.2

#: Lệch độ dài tối đa cho phép giữa file vào và file ra (giây). `-c:v copy`
#: nên độ dài phải giữ nguyên; lệch là dấu hiệu ffmpeg cắt cụt.
LECH_DO_DAI_CLIP = 0.05


def _lop_huy():
    """Lớp `CanceledError` (nạp MUỘN — `worker` import ngược lại module này)."""
    try:
        from app.queue.worker import CanceledError
        return (CanceledError,)
    except Exception:           # noqa: BLE001
        return ()


def do_do_to_clip(path: str | Path, han: int = 900) -> dict:
    """ĐỘ TO TÍCH HỢP + ĐỈNH THẬT + DẢI ĐỘNG của một file, bằng `ebur128`.

    Trả `{"I": LUFS, "TP": dBTP, "LRA": LU}`.

    `-vn` để KHÔNG giải mã hình (chỉ cần tiếng) — đây là chỗ tiết kiệm chính:
    file 1080x1920 mà giải mã cả hình thì phép ĐO đắt hơn cả phép ÁP.

    ffmpeg lỗi / không in được Summary thì **NÉM**, tuyệt đối không trả `None`
    hay số mặc định: đó đúng là bẫy `astats` cổng 53 và `startswith` cổng 44 —
    *phép đo hỏng nguy hiểm hơn không đo, vì nó phát chứng nhận*.
    """
    import re as _re

    p = Path(path)
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-nostdin", "-i", str(p),
           "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=han,
                       stdin=subprocess.DEVNULL,
                       creationflags=_CREATE_NO_WINDOW)
    err = (r.stderr or b"").decode("utf-8", "replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi khi đo độ to {p.name} "
                           f"(mã thoát {r.returncode}): {err[-400:]}")
    if "Summary:" not in err:
        raise RuntimeError(f"ebur128 KHÔNG in Summary cho {p.name} "
                           f"(file không có tiếng?): {err[-400:]}")
    duoi = err[err.rfind("Summary:"):]

    def _lay(nhan: str) -> float:
        m = _re.search(nhan + r":\s*\n?\s*(-?\d+\.?\d*)", duoi)
        if not m:
            raise RuntimeError(f"ebur128 thiếu '{nhan}' cho {p.name}")
        return float(m.group(1))

    return {"I": _lay("I"), "LRA": _lay("LRA"), "TP": _lay("Peak")}


def _chuoi_do_to(nang_db: float, tran_lim_db: float) -> str:
    """Chuỗi filter TIẾNG: nâng thuần -> **quá mẫu** -> hạn đỉnh -> về 48k.

    Quá mẫu là phần bắt buộc, xem `QUA_MAU_HAN_DINH`. Tỉ lệ 4× nguyên nên
    vòng 48k -> 192k -> 48k không đổi số mẫu (đã kiểm độ dài + I + LRA).
    """
    return (f"volume={nang_db:.3f}dB,"
            f"aresample={QUA_MAU_HAN_DINH},"
            + _han_dinh(tran_lim_db, nha=10)
            + ",aresample=48000")


def _ap_do_to(src: Path, dst: Path, nang_db: float, tran_lim_db: float) -> None:
    """NÂNG THUẦN + HẠN ĐỈNH trên FILE VIDEO, giữ nguyên hình (`-c:v copy`).

    Chỉ luồng TIẾNG được mã hoá lại (~1 giây/clip); luồng hình chép nguyên
    byte nên KHÔNG có đời nén hình nào thêm. Đi qua `_run` = qua CỬA CHỜ
    ffmpeg (và nút Huỷ giết được tiến trình này).
    """
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-nostdin",
           "-i", str(src), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
           "-af", _chuoi_do_to(nang_db, tran_lim_db),
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)]
    rc = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"ffmpeg mã {rc} khi chuẩn hoá độ to {src.name}")
    # ffmpeg TRẢ MÃ 0 MÀ FILE 0 KiB là chuyện ĐÃ XẢY RA THẬT trên repo này.
    co = dst.stat().st_size if dst.exists() else 0
    if co < 1024:
        raise RuntimeError(f"chuẩn hoá độ to: ffmpeg mã 0 mà file ra rỗng "
                           f"({co} byte)")


def chuan_do_to_clip(path: str | Path,
                     dich: float = DICH_LUFS_CLIP,
                     tran_tp: float = TRAN_DINH_THAT_CLIP) -> dict:
    """Đưa clip ĐÃ XUẤT về `dich` LUFS, đỉnh thật <= `tran_tp` dBTP.

    Ghi ĐÈ chính file đó (qua file tạm + `os.replace`, nên hỏng giữa chừng thì
    bản cũ còn nguyên). Trả một `dict` NHẬT KÝ — mọi đường ra đều có
    `bo_qua`/`ly_do` để nơi gọi ghi lại được, KHÔNG bao giờ im lặng.

    **BẬC THANG HỆ SỐ, TO NHẤT TRƯỚC — ÁP RỒI ĐO, ĐẠT THÌ LẤY.** Không tính
    trước rồi tin, vì đã đo được hai clip cùng bị gọt mà LRA phản ứng ngược
    nhau (gọt 6,00 dB -> ΔLRA 0,00 · gọt 4,70 dB -> ΔLRA −0,60):

      1. đủ đích (`−14 LUFS`)
      2. gọt đúng `NGAN_SACH_GOT_DB`
      3. gọt NỬA ngân sách
      4. **KHÔNG gọt một dB nào** (`nâng = trần_alimiter − đỉnh`)

    Bậc 4 đạt **THEO CẤU TẠO**: không chạm đỉnh nào thì `alimiter` không có gì
    để làm -> LRA không thể đổi, đỉnh ra đúng trần. Nên vòng lặp LUÔN dừng.
    Bậc nào cũng bị kẹp `<= đích` — chuẩn hoá KHÔNG BAO GIỜ đẩy clip vượt −14.

    Ca thường (6/8 clip đo được) đạt ngay bậc 1 = **một lượt ffmpeg**.

    Hỏng ở bất kỳ đâu -> **GIỮ NGUYÊN file cũ** + `bo_qua=True`. Thà giao clip
    chưa chuẩn hoá còn hơn mất clip. HUỶ thì NỔI LÊN (huỷ là huỷ).
    """
    p = Path(path)
    tran_lim = tran_tp - BIEN_DINH_CLIP
    kq: dict = {"file": p.name, "bo_qua": True, "ly_do": "", "nang_db": 0.0,
                "buoc": 0, "dat_dich": False, "qua_tran_dinh": False}

    truoc = do_do_to_clip(p)
    dai_truoc = probe(p).duration
    kq["truoc"] = {k: round(v, 2) for k, v in truoc.items()}

    # CHẶN NÂNG ĐIÊN: clip gần câm -> thứ được nâng là NỀN NHIỄU chứ không
    # phải nội dung. Thà giao clip nhỏ tiếng còn hơn giao clip rít.
    if truoc["I"] < SAN_LUFS_CLIP:
        kq["ly_do"] = (f"clip chỉ {truoc['I']:.2f} LUFS, dưới sàn "
                       f"{SAN_LUFS_CLIP:.0f} — nâng lên là nâng nền nhiễu")
        kq["sau"] = kq["truoc"]
        return kq

    can = max(-TRAN_CHINH_DO_TO_CLIP,
              min(TRAN_CHINH_DO_TO_CLIP, dich - truoc["I"]))

    # ĐÃ ĐÚNG ĐỘ TO RỒI THÌ ĐỪNG ĐỤNG (và đỉnh cũng đã dưới trần).
    if abs(can) <= NGUONG_BO_QUA_LU and truoc["TP"] <= tran_tp:
        kq["ly_do"] = (f"đã đúng độ to sẵn ({truoc['I']:.2f} LUFS, lệch đích "
                       f"{can:+.2f} LU) và đỉnh {truoc['TP']:.2f} dBTP dưới "
                       f"trần — không mã hoá lại")
        kq["sau"] = kq["truoc"]
        kq["dat_dich"] = True
        return kq

    # BẬC THANG hệ số, TO NHẤT trước; mọi bậc kẹp `<= can` (không vượt đích).
    bac: list[float] = []
    for x in (can,
              (tran_lim + NGAN_SACH_GOT_DB) - truoc["TP"],
              (tran_lim + NGAN_SACH_GOT_DB / 2.0) - truoc["TP"],
              tran_lim - truoc["TP"]):
        x = min(can, x)
        if not bac or x < bac[-1] - 1e-6:
            bac.append(x)
    kq["bac_thang"] = [round(x, 2) for x in bac]
    kq["da_thu"] = []

    tam = p.with_name(f"_dt_{os.getpid()}_{p.name}")
    try:
        for buoc, nang in enumerate(bac, start=1):
            _ap_do_to(p, tam, nang, tran_lim)

            sau = do_do_to_clip(tam)
            dai_sau = probe(tam).duration
            lech_dai = abs(dai_sau - dai_truoc)
            if lech_dai > LECH_DO_DAI_CLIP:
                raise RuntimeError(
                    f"độ dài đổi {lech_dai:.3f}s ({dai_truoc:.3f} -> "
                    f"{dai_sau:.3f}) — KHÔNG nhận")
            tut = truoc["LRA"] - sau["LRA"]
            qua = sau["TP"] > tran_tp + 1e-9
            # BIÊN 1e-6 KHÔNG PHẢI CHO ĐẸP — ĐÃ CẮN THẬT: `ebur128` in LRA một
            # chữ số thập phân, `10.9 - 10.7` trong dấu phẩy động ra
            # **0,20000000000000107** > 0,2 -> bậc ĐANG ĐẠT bị loại, clip tụt
            # từ −15,4 xuống −18,3 = **mất 2,9 LU vì một hạt bụi số học**.
            if (qua or tut > LRA_TUT_TOI_DA + 1e-6) and buoc < len(bac):
                kq["da_thu"].append(
                    {"nang_db": round(nang, 2),
                     "sau": {k: round(v, 2) for k, v in sau.items()},
                     "lra_tut": round(tut, 2), "qua_tran_dinh": bool(qua)})
                continue        # -> BẬC THẤP HƠN
            kq.update({
                "bo_qua": False, "buoc": buoc, "nang_db": round(nang, 2),
                "tran_alimiter_db": round(tran_lim, 2),
                "sau": {k: round(v, 2) for k, v in sau.items()},
                "lra_tut": round(tut, 2),
                "dat_dich": abs(sau["I"] - dich) <= NGUONG_BO_QUA_LU + 1e-6,
                "qua_tran_dinh": bool(qua),
                "lech_do_dai": round(lech_dai, 3),
                "ly_do": ("" if buoc == 1 else
                          f"bậc {buoc}/{len(bac)}: {buoc - 1} hệ số to hơn bị "
                          f"loại vì tụt dải động / vượt trần đỉnh"),
            })
            if not kq["dat_dich"]:
                kq["thieu_lu"] = round(dich - sau["I"], 2)
                kq["ly_do"] = (
                    (kq["ly_do"] + " · " if kq["ly_do"] else "")
                    + f"CHƯA tới đích: còn thiếu {kq['thieu_lu']:.2f} LU — "
                      f"clip có hệ số đỉnh {truoc['TP'] - truoc['I']:.1f} dB, "
                      f"muốn đủ to phải nén dải động")
            os.replace(tam, p)
            return kq
        # Không tới đây được: bậc cuối luôn được NHẬN (điều kiện lùi có
        # `buoc < len(bac)`). Giữ nhánh cho chắc, KHÔNG im lặng.
        kq["ly_do"] = "không bậc nào nhận được — giữ nguyên bản cũ"
        return kq
    except Exception as e:      # noqa: BLE001 — HỎNG thì GIỮ bản cũ
        if _lop_huy() and isinstance(e, _lop_huy()):
            raise               # HUỶ LÀ HUỶ, không nuốt
        kq["ly_do"] = f"lỗi khi chuẩn hoá độ to -> giữ nguyên bản cũ ({e})"
        kq["sau"] = kq["truoc"]
        return kq
    finally:
        _cleanup_paths([tam])
