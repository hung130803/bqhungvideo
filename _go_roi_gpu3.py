# -*- coding: utf-8 -*-
"""Tìm CHÍNH XÁC ngưỡng `xfade_opencl` bắt đầu ra 0 khung — theo GIÂY hay KHUNG?

Quan trọng với việc này: app đặt chuyển cảnh **0,25-0,40 giây**. Nếu ngưỡng nằm
trên mức đó thì nhóm GPU KHÔNG dùng được cho đường xuất thật, phải nói thẳng.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi3_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="goroi3_")
src = _nguon_nhat.mot("JP")


def seg(moc: float, dai: float, fps: int, ten: str) -> str:
    p = os.path.join(td, ten + ".mp4")
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", f"{dai:.3f}", "-i", src, "-an",
                    "-vf", "scale=720:1280:force_original_aspect_ratio=increase,"
                           f"crop=720:1280,setsar=1,fps={fps}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", p],
                   capture_output=True, creationflags=CNW)
    return p


def dem(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", p],
                       capture_output=True, text=True, creationflags=CNW)
    s = (r.stdout or "").strip()
    return int(s) if s.isdigit() else 0


def thu(a: str, b: str, d: float) -> tuple[int, int]:
    out = os.path.join(td, "o.mp4")
    graph = (f"[0:v]{GPU.CHUAN_HOA},hwupload[x];[1:v]{GPU.CHUAN_HOA},hwupload[y];"
             f"[x][y]xfade_opencl=transition=custom:"
             f"source='{GPU.duong_filter(GPU.duong_kernel())}':kernel=gl_gio:"
             f"duration={d:.3f}:offset=0[o];[o]hwdownload,format=yuv420p[v]")
    p = subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                        "-init_hw_device", "opencl=ocl", "-filter_hw_device",
                        "ocl", "-i", a, "-i", b, "-filter_complex", graph,
                        "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "18", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True, creationflags=CNW)
    return p.returncode, (dem(out) if os.path.exists(out) else 0)


print(f"[nguồn] {os.path.basename(src)}")
print("\n=== 30 fps: quét độ dài vùng chồng ===")
print(f"{'d (giây)':>10}{'khung vào':>11}{'rc':>5}{'khung ra':>10}   kết luận")
for d in (0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10):
    a, b = seg(100.0, d, 30, f"a{d}"), seg(300.0, d, 30, f"b{d}")
    nv = dem(a)
    rc, nr = thu(a, b, d)
    print(f"{d:>10.2f}{nv:>11}{rc if rc < 1000 else 'lỗi':>5}{nr:>10}   "
          + ("OK" if nr == nv and nv > 0 else "** 0 KHUNG / CỤT (im lặng) **"))

print("\n=== ĐỔI fps để phân biệt 'theo GIÂY' hay 'theo SỐ KHUNG' ===")
print(f"{'d':>6}{'fps':>6}{'khung vào':>11}{'rc':>5}{'khung ra':>10}   kết luận")
for d, fps in ((0.5, 30), (0.5, 60), (0.5, 120), (1.0, 15), (1.0, 30)):
    a, b = seg(100.0, d, fps, f"x{d}_{fps}"), seg(300.0, d, fps, f"y{d}_{fps}")
    nv = dem(a)
    rc, nr = thu(a, b, d)
    print(f"{d:>6.2f}{fps:>6}{nv:>11}{rc if rc < 1000 else 'lỗi':>5}{nr:>10}   "
          + ("OK" if nr == nv and nv > 0 else "** 0 KHUNG / CỤT **"))
