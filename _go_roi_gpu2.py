# -*- coding: utf-8 -*-
"""Quét biến thể để tìm VÌ SAO `xfade_opencl` ra 0 khung (rc=0, file rỗng)."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi2_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="goroi2_")
src = _nguon_nhat.mot("JP")


def seg(moc: float, dai: float, w: int, h: int, fps: int, ten: str) -> str:
    p = os.path.join(td, ten + ".mp4")
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", f"{dai:.3f}", "-i", src, "-an",
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                           f"crop={w}:{h},setsar=1,fps={fps}",
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
    return int(s) if s.isdigit() else -1


def thu(ten: str, a: str, b: str, d: float, off: float, them: list,
        kieu: str = "gl_gio") -> None:
    out = os.path.join(td, "o_" + ten + ".mp4")
    graph = (f"[0:v]{GPU.CHUAN_HOA},hwupload[x];[1:v]{GPU.CHUAN_HOA},hwupload[y];"
             f"[x][y]xfade_opencl=transition=custom:"
             f"source='{GPU.duong_filter(GPU.duong_kernel())}':kernel={kieu}:"
             f"duration={d:.3f}:offset={off:.3f}[o];"
             f"[o]hwdownload,format=yuv420p[v]")
    cmd = [FF, "-y", "-hide_banner", "-v", "error",
           "-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
           "-i", a, "-i", b, "-filter_complex", graph, "-map", "[v]", *them,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", out]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       creationflags=CNW)
    n = dem(out) if os.path.exists(out) else -1
    kb = os.path.getsize(out) // 1024 if os.path.exists(out) else 0
    print(f"  {ten:<40} rc={p.returncode}  khung={n:>4}  {kb:>5} KB   "
          + ((p.stderr or "").strip().splitlines() or [""])[-1][:60])


print(f"[nguồn] {os.path.basename(src)}")
print("\n=== A) đổi ĐỘ DÀI vùng chồng (2 đoạn dài ĐÚNG d, offset=0) ===")
for d in (0.5, 1.0, 2.0):
    a = seg(100.0, d, 720, 1280, 30, f"a{d}")
    b = seg(300.0, d, 720, 1280, 30, f"b{d}")
    print(f"  [2 đoạn mỗi đoạn {d}s = {dem(a)}/{dem(b)} khung]")
    thu(f"d={d} off=0", a, b, d, 0.0, [])

print("\n=== B) đoạn DÀI HƠN vùng chồng + offset > 0 ===")
a2 = seg(100.0, 2.0, 720, 1280, 30, "a2")
b2 = seg(300.0, 2.0, 720, 1280, 30, "b2")
print(f"  [2 đoạn 2,0s = {dem(a2)}/{dem(b2)} khung]")
for d, off in ((0.5, 1.5), (0.5, 1.0), (0.5, 0.5)):
    thu(f"doan 2s · d={d} off={off}", a2, b2, d, off, [])

print("\n=== C) 720x1280 vs 640x360 (nghi cỡ khung) ===")
a3 = seg(100.0, 1.0, 640, 360, 30, "a3")
b3 = seg(300.0, 1.0, 640, 360, 30, "b3")
thu("640x360 d=1.0 off=0", a3, b3, 1.0, 0.0, [])

print("\n=== D) thêm núm thời gian ===")
a4 = seg(100.0, 0.5, 720, 1280, 30, "a4")
b4 = seg(300.0, 0.5, 720, 1280, 30, "b4")
for ten, them in (("-r 30", ["-r", "30"]),
                  ("-fps_mode passthrough", ["-fps_mode:v", "passthrough"]),
                  ("-fps_mode cfr -r 30", ["-fps_mode:v", "cfr", "-r", "30"]),
                  ("-vsync 0", ["-vsync", "0"])):
    thu(f"d=0.5 off=0 {ten}", a4, b4, 0.5, 0.0, them)

print("\n=== E) xfade CPU CÙNG tham số (đối chứng) ===")
out = os.path.join(td, "cpu.mp4")
p = subprocess.run([FF, "-y", "-hide_banner", "-v", "error", "-i", a4,
                    "-i", b4, "-filter_complex",
                    "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=0[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "18", "-pix_fmt", "yuv420p", out],
                   capture_output=True, text=True, creationflags=CNW)
print(f"  xfade CPU d=0.5 off=0                    rc={p.returncode}  "
      f"khung={dem(out):>4}")
