# -*- coding: utf-8 -*-
"""TÁCH cho ra NGUYÊN NHÂN THẬT: `fps=` sau hwdownload, hay `-r` ở đầu ra?

Kết luận trước đó ("xfade_opencl cần >= 30 khung") là SAI — chỉ trùng hợp. Ca
d=0,25 s (8 khung) chạy tốt khi có thêm bộ lọc `fps=30` SAU `hwdownload`. Bảng
này kiểm 4 tổ hợp trên CÙNG 1 cặp đoạn để chốt nguyên nhân.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi5_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="goroi5_")
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


def thu(a: str, b: str, d: float, co_fps: bool, co_r: bool,
        ten: str) -> tuple[int, int, str]:
    out = os.path.join(td, f"o_{ten}.mp4")
    n = GPU.CHUAN_HOA
    sau = ",fps=30" if co_fps else ""
    graph = (f"[0:v]{n},hwupload[x];[1:v]{n},hwupload[y];"
             f"[x][y]xfade_opencl=transition=custom:"
             f"source='{GPU.duong_filter(GPU.duong_kernel())}':kernel=gl_gio:"
             f"duration={d:.3f}:offset=0[o];"
             f"[o]hwdownload,format=yuv420p{sau}[v]")
    cmd = [FF, "-y", "-hide_banner", "-v", "warning",
           "-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
           "-i", a, "-i", b, "-filter_complex", graph, "-map", "[v]"]
    if co_r:
        cmd += ["-r", "30"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", out]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       creationflags=CNW)
    ghi = ""
    for dg in (p.stderr or "").splitlines():
        if "drop=" in dg or "empty" in dg.lower():
            ghi = dg.strip()[:70]
    return p.returncode, (dem(out) if os.path.exists(out) else 0), ghi


print(f"[nguồn] {os.path.basename(src)}")
for d in (0.30, 0.40, 1.00):
    a, b = seg(100.0, d, f"a{d}"), seg(300.0, d, f"b{d}")
    kv = dem(a)
    print(f"\n=== vùng chồng {d}s = {kv} khung (30 fps) · kỳ vọng ra {kv} khung ===")
    print(f"  {'tổ hợp':<34}{'rc':>5}{'khung ra':>10}   ghi chú")
    for co_fps, co_r, ten in ((False, False, "TRẦN (không fps, không -r)"),
                              (False, True, "chỉ `-r 30` ở đầu ra"),
                              (True, False, "chỉ `fps=30` sau hwdownload"),
                              (True, True, "cả `fps=30` và `-r 30`")):
        rc, nr, ghi = thu(a, b, d, co_fps, co_r, f"{d}_{co_fps}_{co_r}")
        kq = "OK" if (rc == 0 and nr == kv) else "** SAI **"
        print(f"  {ten:<34}{rc if rc < 1000 else 'lỗi':>5}{nr:>10}   {kq} {ghi}")
