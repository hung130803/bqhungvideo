"""
Bọc ffmpeg/ffprobe qua CLI (ổn định hơn binding trên Windows).

Nguyên tắc tối ưu I/O (theo spec): ghép filter graph trong 1 lệnh, tránh
xuất file tạm thừa. Hàm export_vertical_clip cắt + crop bám mặt + scale 9:16
+ encode trong DUY NHẤT 1 lệnh ffmpeg.
"""
from __future__ import annotations

import json
import os
import subprocess
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
_SAN_LUONG_NVENC = 40           # đo: 36 (pha 2 siết hết) .. 49 (pha 1)
_SAN_LUONG_CPU = 30             # đo: 27 (libx264 giải mã 4 + encode 4)


def so_ffmpeg_song_song() -> int:
    """SỐ LỆNH ffmpeg được phép chạy CÙNG LÚC — TỰ ĐO THEO MÁY.

    Ngân sách: tổng luồng ffmpeg <= 2x số nhân logic (mốc chốt 07/08/2026, thay
    mốc 1,5x cũ vì SÀN luồng mỗi tiến trình làm nó bất khả thi). Chia ngân sách
    đó cho SÀN luồng mỗi tiến trình -> ra số tiến trình:
      - 24 nhân + NVENC -> (2*24)//40 = 1
      - 64 nhân + NVENC -> 3
      -  8 nhân, CPU    -> 1   (máy nhân viên yếu)
    Trần 4: hơn nữa thì GPU/đĩa thành nút cổ chai chứ không nhanh thêm.

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
    san = _SAN_LUONG_NVENC if dung_gpu else _SAN_LUONG_CPU
    return max(1, min(4, (2 * cores) // san))


def _xin_cho_ffmpeg() -> bool:
    """Giữ 1 chỗ trong cửa chờ. True = đã giữ (caller PHẢI trả chỗ ở finally).

    Đợi theo NHỊP 0,25s chứ không chặn vô hạn, vì mỗi nhịp phải kiểm lại:
      - job bị bấm Hủy -> ném CanceledError NGAY (đừng để user bấm Hủy mà việc
        vẫn xếp hàng đợi tới lượt rồi mới chạy);
      - đang đóng app -> trả False và ĐI LUÔN (treo ở đây là treo bước thoát
        app; caller đã tự chặn spawn bằng _SHUTDOWN);
      - trần đã đổi (user bật "Tiết kiệm máy" giữa lượt) -> đọc lại mỗi nhịp.
    """
    global _GATE_DANG
    while True:
        if _SHUTDOWN.is_set():
            return False
        with _GATE_COND:
            if _GATE_DANG < so_ffmpeg_song_song():
                _GATE_DANG += 1
                return True
            _GATE_COND.wait(0.25)
        _raise_if_job_canceled()


def _tra_cho_ffmpeg() -> None:
    global _GATE_DANG
    with _GATE_COND:
        _GATE_DANG = max(0, _GATE_DANG - 1)
        _GATE_COND.notify()


def dang_chay_ffmpeg() -> int:
    """Số lệnh ffmpeg đang giữ chỗ (cho test/đo)."""
    with _GATE_COND:
        return _GATE_DANG


def _run(cmd: list[str], on_line: Optional[Callable[[str], None]] = None) -> int:
    """Chạy 1 lệnh ffmpeg QUA CỬA CHỜ (xem `so_ffmpeg_song_song`).

    ĐỪNG spawn ffmpeg bằng subprocess trực tiếp ở chỗ khác: đi vòng qua cửa này
    là quay lại đúng cảnh 592 luồng / 24,7x số nhân.
    """
    _raise_if_job_canceled()   # job đã bị Hủy -> KHÔNG spawn thêm ffmpeg
    co_cho = _xin_cho_ffmpeg()
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
            capture_output=True, text=True, timeout=8,
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
    cmd = [
        settings.FFMPEG_PATH, "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(dst),
    ]
    rc = _run(cmd, keep)
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
                "-pix_fmt", "yuv420p", "-threads", str(encode_threads())]
    # 'veryfast' nhanh hơn 'medium' nhiều lần, chất lượng vẫn tốt cho clip ngắn
    # -> máy yếu (không GPU) xuất nhanh. crf 20 = nét, file gọn.
    crf = "20" if quality == "high" else "23"
    # GIỚI HẠN thread mỗi ffmpeg theo NGÂN SÁCH TOÀN CỤC (xem encode_threads):
    # mặc định libx264 ăn HẾT luồng CPU -> 2-3 job song song là máy đơ 100%.
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
            "-threads", str(encode_threads())]


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

# Âm lượng trộn theo LOẠI (áp lên file .wav lúc mix trong export). impact/riser
# to hơn transition chút (khoảnh khắc mạnh); reveal/ding nhẹ — không lố.
# suspense/sad NHỎ (làm nền dưới giọng, không lấn); comedy VỪA (phải nghe rõ
# cái vui); scratch RÕ (cú "khựng" bất ngờ phải nổi bật); drumroll VỪA-to (dồn
# trước cao trào). Loại lạ -> 0.28 (an toàn như transition).
_SFX_CAT_VOL = {
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


def _pick_sfx_by_category(cats: list, seed: Optional[int] = None) -> list:
    """Với MỖI category trong `cats` (theo thứ tự điểm nối), chọn NGẪU NHIÊN 1
    file .wav trong category đó từ thư viện đóng gói, KHÔNG lặp file 2 lần LIÊN
    TIẾP CÙNG loại (đa dạng). Category không có file (thiếu thư viện) -> trả
    None ở vị trí đó (caller lùi bộ tổng hợp). Trả list cùng độ dài `cats`:
    mỗi phần tử là (category, path) hoặc (category, None). Hàm thuần (chỉ đọc
    thư viện đã cache) — test được."""
    import random as _r
    rng = _r.Random(seed) if seed is not None else _r
    lib = _sfx_library()
    out: list = []
    last_by_cat: dict = {}
    for cat in cats:
        cat = cat if cat in SFX_CATEGORIES else "transition"
        files = lib.get(cat) or []
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


def _cleanup_dst(dst) -> None:
    """Xóa file output dở dang (mp4 hỏng) khi xuất lỗi/hủy — best-effort."""
    if not dst:
        return
    try:
        Path(dst).unlink(missing_ok=True)
    except OSError:
        pass


def _cleanup_paths(paths) -> None:
    """Xóa NHIỀU file tạm best-effort (file đoạn mezzanine, list concat...)."""
    for p in paths or []:
        _cleanup_dst(p)


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
        seg_in += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src)]
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
    ra: list = []
    for i in range(len(segs) - 1):
        loai = _loai_cho_noi(segs, i)
        cap = _XF_LUAT[m][loai]
        ra.append((cap[i % len(cap)], float(_XF_DAI[m][loai])))
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
    """
    ra: list = []
    for i, (_k, d) in enumerate(chuyen or []):
        try:
            het = float(segs[i][1])
        except (IndexError, TypeError, ValueError):
            ra.append(0.0)
            continue
        con = max(0.0, float(dur_nguon or 0.0) - het)
        d2 = min(float(d), con) if dur_nguon else float(d)
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
    import uuid
    info = probe(src)
    fps = info.fps if 10.0 <= (info.fps or 0) <= 120.0 else 30.0
    tdir = tempfile.gettempdir()
    tag = uuid.uuid4().hex[:8]
    temps: list = temps_out if temps_out is not None else []
    n = len(segs)
    dai_goc = [float(e) - float(s) for s, e in segs]
    xf = list(chuyen_canh or [])[:max(0, n - 1)]
    bu = _bu_xfade(segs, xf, float(info.duration or 0.0)) if xf else []
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
                c += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
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
            c = [settings.FFMPEG_PATH, "-y",
                 "-filter_complex_threads", str(encode_threads()),
                 "-threads", str(decode_threads())]
            for p in _in:
                c += ["-i", p]
            c += ["-filter_complex", _g, "-map", _v]
            if _a:
                c += ["-map", _a]
            if enc == "h264_nvenc":
                c += ["-c:v", "h264_nvenc", "-preset", "p1", "-rc", "vbr",
                      "-cq", "16", "-pix_fmt", "yuv420p",
                      "-threads", str(encode_threads())]
            else:
                c += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
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
    return lst, temps


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
    chuyen_canh: object = "",            # CHUYỂN CẢNH ở chỗ ghép đoạn (xfade):
                                        # "" / "tat" -> đường CŨ Y NGUYÊN;
                                        # "nhe"/"vua"/"manh" -> tự chọn kiểu
                                        # theo NỘI DUNG chỗ nối
                                        # (`chon_chuyen_canh`); hoặc truyền
                                        # thẳng [(kiểu, giây)] (dùng cho test).
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
    segs = [(float(s), float(e)) for s, e in (segments or []) if e > s]
    if not segs:
        raise RuntimeError("Không có đoạn nào để xuất.")
    encoder = encoder or detect_encoder()
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
    _hu_fps = _info.fps if 10.0 <= (_info.fps or 0) <= 120.0 else 30.0
    try:
        from app.core import hieu_ung as _HU
        # ffmpeg con thừa hưởng os.environ -> đặt FREI0R_PATH ở đây là đủ cho cả
        # đường list-truyền-thẳng (test/demo) lẫn đường tự chọn theo mức.
        _HU.dat_frei0r_path()
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
            # mốc chỗ nối trên timeline ĐẦU RA (xfade đã bù nên mốc KHÔNG đổi)
            _moc = [sum(e - s for s, e in segs[:i + 1])
                    for i in range(len(segs) - 1)]
            _hu = _HU.chon_hieu_ung(total, str(hieu_ung).strip().lower(),
                                    nl=_nl, cd=_cd, moc_noi=_moc)
        if _hu and hieu_ung_log is not None:
            hieu_ung_log.extend(_hu)
    except Exception:      # noqa: BLE001 — hiệu ứng KHÔNG được làm chết lượt xuất
        _hu = []

    def build(enc: str) -> list[str]:
        cmd = [settings.FFMPEG_PATH, "-y", *_global_enc_opts()]
        parts = []
        # Các input phụ (màu nền/overlay/nhạc/dub) đánh số sau input video.
        vin = 1
        if multi:
            cmd += ["-f", "concat", "-safe", "0", "-i", _seg_list]
        else:
            s, e = segs[0]
            cmd += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src)]
        content, aud, aud_map = "[0:v]", "[0:a]", "0:a?"
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
        # hiệu ứng mà CHỮ vẫn nét (y như spotlight ở trên). Mốc chọn ở timeline
        # ĐẦU RA, còn `t` ở đây là timeline TRƯỚC setpts => nhân vspeed (cùng
        # cách quy đổi với dim_ranges/duck_ranges).
        # `fps` truyền vào phải là fps THẬT của nguồn: `zoompan` sinh lại mốc
        # thời gian theo `fps`, đặt 30 cho nguồn 29,97 là clip tự co 0,1% ->
        # lệch tiếng-hình. Mezzanine pha 1 cũng ép CFR bằng đúng fps này.
        if _hu:
            _hu_t = [dict(c, bat=float(c["bat"]) * vspeed,
                          het=float(c["het"]) * vspeed) for c in _hu]
            try:
                from app.core import hieu_ung as _HU2
                _ch = _HU2.chuoi_filter(_hu_t, out_w, out_h, _hu_fps,
                                        str(fonts_dir or ""))
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
        whoosh_on = bool(fx_whoosh and multi and whoosh_offsets)
        # voice_vol==0 -> tiếng gốc câm hẳn: BỎ khỏi mix (như dub_mute) để amix
        # không thừa 1 nhánh im lặng làm loãng các lớp khác.
        include_voice = use_voice and voice_vol > 0.0005
        if include_voice:
            vf = ["aresample=48000"] + af
            apply_vol = abs(voice_vol - 1.0) > 0.001
            if apply_vol:
                vf.append(f"volume={voice_vol:.3f}")   # âm lượng tiếng gốc
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
            # ĐIỂM NỐI có nhãn "none" (AI chỉ định KHÔNG chèn) -> BỎ QUA hẳn ở
            # MỌI đường (user dir + thư viện) để tôn trọng ý đồ AI: index các
            # điểm nối THỰC SỰ chèn tiếng. Tính TRƯỚC nền im lặng để KHÔNG thêm
            # nền thừa khi MỌI điểm nối đều "none" (video câm -> vẫn câm).
            active_ji = [i for i in range(len(whoosh_offsets))
                         if join_cats[i] != "none"]
            n_joint = len(active_ji)
            # reset log điểm-nối MỖI lần export (mọi "none" -> danh sách rỗng)
            global _SFX_LAST_PICK
            _SFX_LAST_PICK = []
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
            # ƯU TIÊN 1 — THƯ MỤC tiếng động của USER (giữ tính năng cũ): có file
            # hợp lệ -> mỗi điểm nối lấy NGẪU NHIÊN 1 file (không phân loại ngữ
            # cảnh vì file user tùy ý). random.sample tránh trùng khi đủ.
            sfx_files = _list_sfx_files(fx_sfx_dir) if n_joint else []
            if sfx_files:
                if len(sfx_files) >= n_joint:
                    picked = _rnd.sample(sfx_files, n_joint)
                else:
                    picked = [_rnd.choice(sfx_files) for _ in range(n_joint)]
                for wi, (ji, fpath) in enumerate(zip(active_ji, picked)):
                    off = whoosh_offsets[ji]
                    s_idx = aidx
                    aidx += 1
                    cmd += ["-i", str(fpath)]
                    d_ms = max(0, int(round(off * 1000)))
                    # cắt về out_dur SAU adelay để không kéo dài clip; volume nhỏ.
                    parts.append(
                        f"[{s_idx}:a]aresample=48000,volume=0.3,"
                        f"adelay={d_ms}|{d_ms},atrim=0:{out_dur:.3f},"
                        f"asetpts=PTS-STARTPTS[wh{wi}]")
                    mix.append(f"[wh{wi}]")
            elif n_joint:
                # ƯU TIÊN 2 — THƯ VIỆN ĐÓNG GÓI theo NGỮ CẢNH (join_cats). Mỗi
                # điểm nối chọn 1 file trong đúng category (không lặp liên tiếp
                # cùng loại). Category THIẾU file (bản cũ chưa có thư viện) ->
                # ƯU TIÊN 3: lùi bộ tiếng TỔNG HỢP hợp loại (_pick_synth_for_
                # category, cũng tránh lặp liên tiếp). Ghi lại loại đã chọn để
                # caller/log kiểm được (SFX_LAST_PICK).
                active_cats = [join_cats[i] for i in active_ji]
                active_offs = [whoosh_offsets[i] for i in active_ji]
                picks = _pick_sfx_by_category(active_cats)
                last_synth: dict = {}
                chosen_log: list = []
                for wi, ((cat, fpath), off) in enumerate(
                        zip(picks, active_offs)):
                    w_idx = aidx
                    aidx += 1
                    vol = _SFX_CAT_VOL.get(cat, 0.28)
                    if fpath:
                        d_ms = max(0, int(round(off * 1000)))
                        cmd += ["-i", str(fpath)]
                        parts.append(
                            f"[{w_idx}:a]aresample=48000,volume={vol:.3f},"
                            f"adelay={d_ms}|{d_ms},atrim=0:{out_dur:.3f},"
                            f"asetpts=PTS-STARTPTS[wh{wi}]")
                        chosen_log.append((cat, os.path.basename(fpath)))
                    else:
                        # thiếu thư viện -> tiếng tổng hợp hợp loại
                        tidx = _pick_synth_for_category(
                            cat, last_synth.get(cat), _rnd)
                        last_synth[cat] = tidx
                        in_args, branch = _fx_synth_branch(
                            tidx, off, vol, w_idx, f"wh{wi}")
                        cmd += in_args
                        parts.append(branch)
                        chosen_log.append((cat, f"synth#{tidx}"))
                    mix.append(f"[wh{wi}]")
                # cho test/log biết ĐÃ chọn loại+file gì tại mỗi điểm nối
                _SFX_LAST_PICK = chosen_log
        if len(mix) == 1:
            amap = mix[0]
        elif len(mix) >= 2:
            parts.append("".join(mix) + f"amix=inputs={len(mix)}:"
                         f"duration=first:normalize=0[aout]")
            amap = "[aout]"
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
        _run_with_fallback(build, encoder, out_total, _prog,
                           "xuất được clip", dst=dst)
    finally:
        # dọn file đoạn tạm + file danh sách MỌI trường hợp (xong/lỗi/hủy)
        _cleanup_paths(_seg_temps + ([_seg_list] if _seg_list else []))
    return True
