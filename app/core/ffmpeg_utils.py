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
# Ưu tiên THẤP cho ffmpeg nặng (encode) -> máy KHÔNG đơ, UI vẫn mượt khi đang xuất.
_BELOW_NORMAL = 0x00004000 if hasattr(subprocess, "STARTUPINFO") else 0


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


def unregister_proc(p) -> None:
    with _PROC_LOCK:
        _ACTIVE_PROCS.discard(p)


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
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_CREATE_NO_WINDOW | _BELOW_NORMAL,
    )
    with _PROC_LOCK:
        _ACTIVE_PROCS.add(proc)
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            if on_line:
                on_line(line.rstrip())
        proc.wait()
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
        with _PROC_LOCK:
            _ACTIVE_PROCS.discard(proc)


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
        _ENCODER_CACHE = "h264_nvenc" if _nvenc_works() else "libx264"
    return _ENCODER_CACHE


_ENCODER_CACHE: Optional[str] = None


def _nvenc_works() -> bool:
    """Encode thử 1 frame bằng h264_nvenc. True nếu chạy được thật."""
    cmd = [
        settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=128x128:rate=1",
        # testsrc mặc định rgb24 -> vài bản ffmpeg từ chối đưa thẳng vào NVENC;
        # ép yuv420p để test không FAIL OAN (false negative) vì pixel format.
        "-frames:v", "1", "-pix_fmt", "yuv420p",
        "-c:v", "h264_nvenc", "-f", "null", "-",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True,
                           creationflags=_CREATE_NO_WINDOW, timeout=20)
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


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


def _enc_args(encoder: str, quality: str = "high") -> list[str]:
    """Tham số encode theo encoder + mức chất lượng."""
    if encoder == "h264_nvenc":
        cq = "19" if quality == "high" else "23"
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", cq]
    # 'veryfast' nhanh hơn 'medium' nhiều lần, chất lượng vẫn tốt cho clip ngắn
    # -> máy yếu (không GPU) xuất nhanh. crf 20 = nét, file gọn.
    crf = "20" if quality == "high" else "23"
    # GIỚI HẠN thread mỗi ffmpeg: mặc định libx264 ăn HẾT luồng CPU -> 2-3 job
    # song song là máy đơ 100% CPU. Chia ~1/3 số luồng cho mỗi job (2..8).
    threads = max(2, min(8, (os.cpu_count() or 4) // 3))
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
            "-threads", str(threads)]


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
            global _ENCODER_CACHE
            _ENCODER_CACHE = "libx264"
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
    on_progress: Optional[Callable[[float], None]] = None,
) -> bool:
    """
    Cắt [start,end] -> đặt khung 9:16 (mode face/center/fit_blur/manual + zoom hoặc
    crop_rect) -> chèn lớp chữ -> encode, 1 lệnh ffmpeg.

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
    base = reframe_chain(mode, cx, out_w, out_h, zoom, "0:v", base_out, "0",
                         crop_rect=crop_rect)
    if use_png:
        fc = base + ";[vr][1:v]overlay=0:0[v]"
    elif has_text:
        fc = base + ";" + _text_chain(text_overlays, out_h, "vr", "v")
    else:
        fc = base

    def build(enc: str) -> list[str]:
        # -ss và -t ĐỀU là input-option của video gốc (trước -i) để cắt đúng
        # thời lượng kể cả khi có thêm input PNG.
        cmd = [settings.FFMPEG_PATH, "-y",
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
    on_progress: Optional[Callable[[float], None]] = None,
) -> bool:
    """
    GHÉP nhiều đoạn rời rạc thành 1 video dọc 9:16, trong DUY NHẤT 1 lệnh ffmpeg
    (filter_complex concat — không file tạm). overlay_png (nếu có) chèn lên toàn clip.
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
        parts.append(
            f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[pv{i}]")
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
        cmd = [settings.FFMPEG_PATH, "-y", "-i", str(src)]
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
    dub_path: Optional[str] = None,     # LỒNG TIẾNG AI: wav 48k dài đúng bằng clip
    dub_mute_original: bool = False,    # True = tắt hẳn tiếng gốc khi có lồng tiếng
    on_progress: Optional[Callable[[float], None]] = None,
) -> bool:
    """
    Mô hình CapCut: khung 9:16 = NỀN (đen/trắng/mờ) + KHỐI video; hoặc 'fill' = crop
    cắt 2 bên cho video đầy khung. Nhiều khúc -> GHÉP. Tùy chọn tăng tốc + đổi giọng.
    """
    segs = [(float(s), float(e)) for s, e in (segments or []) if e > s]
    if not segs:
        raise RuntimeError("Không có đoạn nào để xuất.")
    encoder = encoder or detect_encoder()
    multi = len(segs) > 1
    total = sum(e - s for s, e in segs)
    # Video KHÔNG có tiếng -> mọi filter [0:a] sẽ fail; xuất chỉ hình.
    has_audio = probe(src).has_audio
    dub_on = bool(dub_path and os.path.exists(str(dub_path)))
    # Tắt hẳn tiếng gốc khi lồng tiếng -> KHÔNG concat/lọc audio gốc luôn
    # (concat ra [caud] mà không dùng sẽ làm ffmpeg fail "unconnected output").
    use_voice = has_audio and not (dub_on and dub_mute_original)
    cx, cy, sw = video_rect
    vw = max(2, int(round(sw * out_w)) // 2 * 2)
    use_png = bool(overlay_png and os.path.exists(overlay_png))
    blur_amt = max(1, int(blur_amt))
    speed = max(0.5, min(3.0, float(speed or 1.0)))
    pitch = max(0.5, min(2.0, float(pitch or 1.0)))

    def build(enc: str) -> list[str]:
        cmd = [settings.FFMPEG_PATH, "-y"]
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
        if ass_path and os.path.exists(ass_path):
            ap = str(ass_path).replace("\\", "/").replace(":", "\\:")
            sub = f"subtitles='{ap}'"
            if fonts_dir:
                fd = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
                sub += f":fontsdir='{fd}'"
            parts.append(f"{final}{sub}[vsub]")
            final = "[vsub]"
        # TĂNG TỐC: setpts SAU phụ đề -> chữ đốt sẵn nên vẫn KHỚP khi tua nhanh
        if abs(speed - 1.0) > 0.01:
            parts.append(f"{final}setpts=PTS/{speed:.4f}[vsp]")
            final = "[vsp]"
        # ĐỔI GIỌNG + tốc độ cho AUDIO (chỉ khi video CÓ tiếng)
        af = []
        if abs(pitch - 1.0) > 0.01:     # đổi cao độ giọng (giữ tốc độ)
            af += [f"asetrate=48000*{pitch:.4f}", "aresample=48000",
                   f"atempo={1.0/pitch:.4f}"]
        if abs(speed - 1.0) > 0.01:
            af.append(f"atempo={speed:.4f}")
        out_dur = total / speed if abs(speed - 1.0) > 0.01 else total
        # ---- TRỘN AUDIO: tiếng gốc (+lọc) / lồng tiếng AI / nhạc nền ----
        # Có lồng tiếng: tiếng GỐC hạ còn 0.15 (giữ "không khí" nền) hoặc bỏ hẳn
        # (dub_mute_original). amix normalize=0 để giữ nguyên âm lượng từng lớp.
        mix: list[str] = []
        amap = None
        if use_voice:
            vf = ["aresample=48000"] + af
            if dub_idx is not None:
                vf.append("volume=0.150")   # né tiếng gốc dưới lồng tiếng
            need_mix = (dub_idx is not None) or (bgm_idx is not None)
            if need_mix or af:
                parts.append(f"{aud}{','.join(vf)}[vce]")
                mix.append("[vce]")
            else:
                amap = aud_map  # KHÔNG lọc/trộn -> map thẳng (giữ hành vi cũ)
        if dub_idx is not None:
            dch = ["aresample=48000"]
            if abs(speed - 1.0) > 0.01:     # dub dựng theo timeline gốc -> tua theo
                dch.append(f"atempo={speed:.4f}")
            parts.append(f"[{dub_idx}:a]{','.join(dch)},atrim=0:{out_dur:.3f},"
                         f"asetpts=PTS-STARTPTS[dub]")
            mix.append("[dub]")
        if bgm_idx is not None:
            # nhạc nền: chỉnh âm lượng + cắt đúng độ dài clip (sau tăng tốc)
            parts.append(f"[{bgm_idx}:a]volume={max(0.0, min(1.0, bgm_vol)):.3f},"
                         f"atrim=0:{out_dur:.3f},asetpts=PTS-STARTPTS[bgm]")
            mix.append("[bgm]")
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

    # ffmpeg log 'time=' là thời gian OUTPUT -> khi tăng tốc, tổng thời lượng
    # ra = total/speed; dùng total gốc sẽ làm thanh % kẹt ở ~1/speed rồi nhảy vọt.
    out_total = total / speed if abs(speed - 1.0) > 0.01 else total
    _run_with_fallback(build, encoder, out_total, on_progress, "xuất được clip",
                       dst=dst)
    return True
