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


def _run(cmd: list[str], on_line: Optional[Callable[[str], None]] = None) -> int:
    """Chạy lệnh, đẩy stderr (ffmpeg log) qua callback nếu cần."""
    _raise_if_job_canceled()   # job đã bị Hủy -> KHÔNG spawn thêm ffmpeg
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
    cmd = [
        settings.FFMPEG_PATH, "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(dst),
    ]
    return _run(cmd) == 0


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


def _enc_args(encoder: str, quality: str = "high") -> list[str]:
    """Tham số encode theo encoder + mức chất lượng."""
    if encoder == "h264_nvenc":
        cq = "19" if quality == "high" else "23"
        # -pix_fmt yuv420p: nguồn 10-bit/4:4:4 (video tải chất lượng cao) sẽ làm
        # NVENC từ chối -> rơi oan về libx264 encode LẠI từ đầu; ép 420p (chuẩn
        # phát hành shorts) để NVENC ăn được mọi nguồn.
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", cq,
                "-pix_fmt", "yuv420p"]
    # 'veryfast' nhanh hơn 'medium' nhiều lần, chất lượng vẫn tốt cho clip ngắn
    # -> máy yếu (không GPU) xuất nhanh. crf 20 = nét, file gọn.
    crf = "20" if quality == "high" else "23"
    # GIỚI HẠN thread mỗi ffmpeg theo NGÂN SÁCH TOÀN CỤC (xem encode_threads):
    # mặc định libx264 ăn HẾT luồng CPU -> 2-3 job song song là máy đơ 100%.
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
            "-threads", str(encode_threads())]


def _global_enc_opts() -> list[str]:
    """Tùy chọn TOÀN CỤC đặt ngay sau 'ffmpeg -y' cho lệnh export dùng
    -filter_complex: giới hạn luồng của filter graph (mặc định ffmpeg lấy HẾT
    số nhân cho MỖI graph -> nhiều job song song đẻ hàng trăm thread)."""
    return ["-filter_complex_threads", str(encode_threads())]


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
            files = sorted(str(p) for p in d.iterdir()
                           if p.is_file() and p.suffix.lower() == ".wav")
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
        choices = [f for f in files if f != prev] or files
        pick = rng.choice(choices)
        last_by_cat[cat] = pick
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

        def _line(line: str) -> None:
            tail.append(line)
            if len(tail) > 14:
                tail.pop(0)
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
        if code == 0:
            return
        last_log = "\n".join(tail[-6:])
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

    parts, labels = [], []
    for i, m in enumerate(moments):
        s, e = m["start"], m["end"]
        cx = float(m.get("cx", 0.5))
        # LẬT GƯƠNG: hflip ngay sau trim (TRƯỚC reframe/concat/overlay) -> chỉ
        # hình soi gương, overlay chữ + phụ đề chồng sau nên KHÔNG ngược.
        flip_f = "hflip," if flip_h else ""
        parts.append(
            f"[0:v]trim=start={s:.3f}:end={e:.3f},{flip_f}"
            f"setpts=PTS-STARTPTS[pv{i}]")
        parts.append(reframe_chain(mode, cx, out_w, out_h, zoom,
                                   f"pv{i}", f"v{i}", str(i)))
        if has_audio:
            parts.append(
                f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}]")
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
        parts.append("[vcat][1:v]overlay=0:0[v]")
    elif has_text:
        parts.append(_text_chain(text_overlays, out_h, "vcat", "v"))
    fc = ";".join(parts)

    def build(enc: str) -> list[str]:
        cmd = [settings.FFMPEG_PATH, "-y", *_global_enc_opts(), "-i", str(src)]
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
    multi = len(segs) > 1
    total = sum(e - s for s, e in segs)
    # Video KHÔNG có tiếng -> mọi filter [0:a] sẽ fail; xuất chỉ hình.
    _info = probe(src)
    has_audio = _info.has_audio
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

    def build(enc: str) -> list[str]:
        cmd = [settings.FFMPEG_PATH, "-y", *_global_enc_opts()]
        parts = []
        if multi:
            cmd += ["-i", str(src)]
            labs = ""
            for i, (s, e) in enumerate(segs):
                parts.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[sv{i}]")
                if use_voice:
                    parts.append(f"[0:a]atrim={s:.3f}:{e:.3f},"
                                 f"asetpts=PTS-STARTPTS[sa{i}]")
                    labs += f"[sv{i}][sa{i}]"
                else:
                    labs += f"[sv{i}]"
            a_flag = 1 if use_voice else 0
            parts.append(f"{labs}concat=n={len(segs)}:v=1:a={a_flag}[cvid]"
                         + ("[caud]" if use_voice else ""))
            content, aud, aud_map = "[cvid]", "[caud]", "[caud]"
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
            nextidx = 1
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
            nextidx = 1
        else:
            col = "white" if bg == "white" else "black"
            cmd += ["-f", "lavfi", "-t", f"{total:.3f}",
                    "-i", f"color=c={col}:s={out_w}x{out_h}:r=30"]
            parts.append("[1:v]setsar=1[base]")
            parts.append(f"{vsrc}scale={vw}:-2:flags=lanczos,setsar=1[fg]")
            parts.append(f"[base][fg]overlay=x='{cx:.4f}*W-w/2':"
                         f"y='{cy:.4f}*H-h/2'[vv]")
            nextidx = 2
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
    _run_with_fallback(build, encoder, out_total, on_progress, "xuất được clip",
                       dst=dst)
    return True
