"""
Đăng ký các job handler vào worker pool.

  - "analyze" : chạy lõi phân tích (tiến trình con) cho 1 video.
  - "auto"    : phân tích (nếu chưa) + tìm highlight trong 1 job — nút chính của UI.
  - "auto_mixed" : phân tích (nếu chưa) + ghép khoảnh khắc hay nhất (Mixed-Cut).
  - "m1_export_clip": đăng ký trong m1_highlight.
"""
from __future__ import annotations

import os
import subprocess
import sys

from app.core.analysis import analysis_status
from config import ROOT_DIR
from .worker import CanceledError, JobContext, register_handler

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
# Ưu tiên THẤP cho tiến trình phân tích -> lỡ chạy nặng cũng KHÔNG đơ máy yếu.
_BELOW_NORMAL = 0x00004000 if sys.platform == "win32" else 0


def _run_analyze(video_id: int, ctx: JobContext, force: bool,
                 base: float = 0.0, span: float = 1.0) -> None:
    """Chạy lõi phân tích trong tiến trình con; tiến độ trong khoảng base..base+span."""
    # Bản .exe (PyInstaller) KHÔNG chạy được "-m module" -> dùng cờ --analyze mà
    # main.py nhận diện. Bản dev (python) thì chạy module như cũ.
    if getattr(sys, "frozen", False):
        args = [sys.executable, "--analyze", str(video_id)]
    else:
        args = [sys.executable, "-m", "app.core.analysis_runner", str(video_id)]
    if force:
        args.append("force")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        args, cwd=str(ROOT_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        creationflags=_CREATE_NO_WINDOW | _BELOW_NORMAL,
    )
    from app.core.ffmpeg_utils import register_proc, unregister_proc
    register_proc(proc)
    last_error = ""

    # Đọc stdout bằng THREAD RIÊNG + poll hủy mỗi 0.5s: nếu đọc trực tiếp,
    # lúc tiến trình con im lặng lâu (nạp model whisper, transcribe đoạn dài)
    # sẽ không có dòng nào -> nút Hủy bị lờ tới dòng PROGRESS kế tiếp.
    import queue as _q
    import threading
    lines: _q.Queue = _q.Queue()

    def _reader():
        try:
            for raw in proc.stdout:  # type: ignore[union-attr]
                lines.put(raw.rstrip("\n"))
        except Exception:  # noqa: BLE001
            pass
        finally:
            lines.put(None)          # hết stdout (tiến trình thoát)

    threading.Thread(target=_reader, daemon=True).start()
    try:
        while True:
            ctx.check_canceled()     # nhạy với nút Hủy kể cả pha im lặng
            try:
                line = lines.get(timeout=0.5)
            except _q.Empty:
                continue
            if line is None:
                break
            if line.startswith("PROGRESS\t"):
                parts = line.split("\t", 2)
                try:
                    p = float(parts[1])
                except (ValueError, IndexError):
                    p = 0.0
                ctx.progress(base + span * p, parts[2] if len(parts) > 2 else "")
            elif line.startswith("ERROR\t"):
                last_error = line.split("\t", 1)[1]
    except CanceledError:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise
    finally:
        unregister_proc(proc)
    code = proc.wait()
    if code != 0:
        if last_error:
            raise RuntimeError(f"Phân tích lỗi: {last_error}")
        raise RuntimeError(
            f"Tiến trình phân tích dừng đột ngột (mã {code}). Thường do whisper GPU "
            "thiếu cuDNN — bỏ trống WHISPER_DEVICE trong .env (chạy CPU) rồi thử lại.")


def _analyze(payload: dict, ctx: JobContext) -> dict:
    video_id = int(payload["video_id"])
    _run_analyze(video_id, ctx, payload.get("force", False))
    return {"video_id": video_id, "status": analysis_status(video_id)}


def _auto(payload: dict, ctx: JobContext) -> dict:
    """Tạo clip tự động: phân tích (nếu chưa) -> tìm highlight, 1 thanh tiến trình."""
    from app.modules.m1_highlight import generate_highlights
    video_id = int(payload["video_id"])

    done = all(analysis_status(video_id).get(k) in ("done", "skipped")
               for k in ("transcript", "scenes", "audio", "faces"))
    if not done:
        _run_analyze(video_id, ctx, force=False, base=0.0, span=0.8)

    parent = ctx

    class _Sub:
        profile = parent.profile
        def progress(self, p, m=""):
            parent.progress(0.8 + 0.2 * p, m)
        def check_canceled(self):
            parent.check_canceled()

    res = generate_highlights(
        {"video_id": video_id, "preset": payload.get("preset")}, _Sub())
    return {"video_id": video_id, **res}


def _auto_mixed(payload: dict, ctx: JobContext) -> dict:
    """Mixed-Cut 1 nút: phân tích (nếu chưa) -> ghép khoảnh khắc hay nhất."""
    from app.modules.m1_highlight import generate_mixed_cut
    video_id = int(payload["video_id"])

    done = all(analysis_status(video_id).get(k) in ("done", "skipped")
               for k in ("transcript", "scenes", "audio", "faces"))
    if not done:
        _run_analyze(video_id, ctx, force=False, base=0.0, span=0.8)

    parent = ctx

    class _Sub:
        profile = parent.profile
        def progress(self, p, m=""):
            parent.progress(0.8 + 0.2 * p, m)
        def check_canceled(self):
            parent.check_canceled()

    res = generate_mixed_cut(
        {"video_id": video_id, "preset": payload.get("preset")}, _Sub())
    return {"video_id": video_id, **res}


register_handler("analyze", _analyze)
register_handler("auto", _auto)
register_handler("auto_mixed", _auto_mixed)

# Nạp handler của Module 1 (tự register khi import)
from app.modules import m1_highlight  # noqa: E402,F401
