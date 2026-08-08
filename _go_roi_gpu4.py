# -*- coding: utf-8 -*-
"""Cách NÉ ngưỡng 30 khung: nâng fps ở vùng chồng rồi hạ về lại.

`xfade_opencl` cần >= 30 KHUNG trong vùng chồng (đo ở `_go_roi_gpu3.py`), mà app
đặt chuyển cảnh 0,25-0,40 s = 8-12 khung ở 30 fps -> ra 0 khung TRONG IM LẶNG.
Ý tưởng: nhân đôi/ba khung TRƯỚC khi upload (`fps=90`) cho đủ 30 khung, chuyển
cảnh trên GPU, rồi `fps=30` sau khi tải về. Nội dung không đổi, chỉ đủ khung.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi4_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="goroi4_")
src = _nguon_nhat.mot("JP")


def seg(moc: float, dai: float, ten: str) -> str:
    p = os.path.join(td, ten + ".mp4")
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", f"{dai:.3f}", "-i", src, "-an",
                    "-vf", "scale=720:1280:force_original_aspect_ratio=increase,"
                           "crop=720:1280,setsar=1,fps=30",
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


def thu(a: str, b: str, d: float, fps_gpu: int, fps_ra: int) -> tuple[int, int]:
    out = os.path.join(td, f"o_{d}_{fps_gpu}.mp4")
    n = GPU.CHUAN_HOA
    graph = (f"[0:v]{n},fps={fps_gpu},hwupload[x];"
             f"[1:v]{n},fps={fps_gpu},hwupload[y];"
             f"[x][y]xfade_opencl=transition=custom:"
             f"source='{GPU.duong_filter(GPU.duong_kernel())}':kernel=gl_gio:"
             f"duration={d:.3f}:offset=0[o];"
             f"[o]hwdownload,format=yuv420p,fps={fps_ra}[v]")
    p = subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                        "-init_hw_device", "opencl=ocl", "-filter_hw_device",
                        "ocl", "-i", a, "-i", b, "-filter_complex", graph,
                        "-map", "[v]", "-r", str(fps_ra),
                        "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "18", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True, creationflags=CNW)
    return p.returncode, (dem(out) if os.path.exists(out) else 0)


print(f"[nguồn] {os.path.basename(src)}")
print("\nMọi ca: 2 đoạn 30 fps dài ĐÚNG d · ra 30 fps")
print(f"{'d (giây)':>9}{'khung 30fps':>12}{'fps GPU':>9}{'khung GPU':>11}"
      f"{'rc':>5}{'khung ra':>10}   kết luận")
for d in (0.25, 0.30, 0.35, 0.40, 0.50):
    a, b = seg(100.0, d, f"a{d}"), seg(300.0, d, f"b{d}")
    goc = dem(a)
    ky_vong = max(1, int(round(d * 30)))
    for fps_gpu in (30, 90, 120):
        n_gpu = int(round(d * fps_gpu))
        rc, nr = thu(a, b, d, fps_gpu, 30)
        ok = (rc == 0 and abs(nr - ky_vong) <= 1 and nr > 0)
        print(f"{d:>9.2f}{goc:>12}{fps_gpu:>9}{n_gpu:>11}"
              f"{rc if rc < 1000 else 'lỗi':>5}{nr:>10}   "
              + ("OK" if ok else "** CỤT/0 KHUNG **")
              + (f" (kỳ vọng {ky_vong})" if not ok else ""))
