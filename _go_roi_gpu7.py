# -*- coding: utf-8 -*-
r"""CHỐT CÁCH CHỮA PTS rác của `xfade_opencl` + đo file RA THẬT (không phải null).

Gốc bệnh (đo ở `_go_roi_gpu6.py`): `xfade_opencl` gắn **AV_NOPTS_VALUE** lên
khung ra -> `showinfo` in `pts_time:-600479950316066` (≈ -6,0e14 giây).
  · muxer bỏ hết khung  -> file ra **0 khung**;
  · `fps=` cố lấp từ -6e14 giây tới 0 -> **sinh khung vô tận** -> 19,1 GB RSS.

Bảng này so 3 cách đánh lại mốc, trên FILE THẬT (đếm bằng ffprobe), có trần
`-frames:v` + timeout để không bao giờ phình lại.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi7_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="goroi7_")
src = _nguon_nhat.mot("JP")
FPS, TRAN = 30, 150


def seg(moc: float, dai: float, ten: str) -> str:
    p = os.path.join(td, f"{ten}.mp4")
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", f"{dai:.3f}", "-i", src, "-an",
                    "-vf", "scale=480:854:force_original_aspect_ratio=increase,"
                           f"crop=480:854,setsar=1,fps={FPS}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", p],
                   capture_output=True, timeout=180, creationflags=CNW)
    return p


def dem(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", p],
                       capture_output=True, text=True, creationflags=CNW)
    s = (r.stdout or "").strip()
    return int(s) if s.isdigit() else 0


def thu(nhan: str, duoi: str, a: str, b: str, d: float, ky: int) -> None:
    out = os.path.join(td, f"o_{abs(hash(nhan + str(d)))}.mp4")
    n = GPU.CHUAN_HOA
    ker = GPU.duong_filter(GPU.duong_kernel())
    graph = (f"[0:v]{n},hwupload[x];[1:v]{n},hwupload[y];"
             f"[x][y]xfade_opencl=transition=custom:source='{ker}':"
             f"kernel=gl_gio:duration={d:.3f}:offset=0[o];"
             f"[o]hwdownload,format=yuv420p{duoi}[v]")
    cmd = [FF, "-y", "-hide_banner", "-v", "error",
           "-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
           "-i", a, "-i", b, "-filter_complex", graph, "-map", "[v]",
           "-frames:v", str(TRAN),          # TRẦN CỨNG — chống phình 19 GB
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", out]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           errors="replace", timeout=75, creationflags=CNW)
    except subprocess.TimeoutExpired:
        print(f"  {nhan:<34} ** TREO > 75s (sinh khung vô tận) **")
        return
    k = dem(out) if os.path.exists(out) else 0
    kq = "OK" if k == ky else ("** CHẠM TRẦN, VÔ TẬN **" if k >= TRAN
                               else f"** SAI, kỳ vọng {ky} **")
    print(f"  {nhan:<34} rc={p.returncode:<3} khung={k:<5} {kq}"
          + (f"   {(p.stderr or '').strip().splitlines()[-1][:60]}"
             if p.returncode else ""))


print(f"[nguồn] {os.path.basename(src)}  ·  OpenCL={GPU.co_opencl()}")
for d in (0.25, 0.30, 0.50):
    a, b = seg(100.0, d, f"a{d}"), seg(300.0, d, f"b{d}")
    ky = dem(a)
    print(f"\n=== vùng chồng {d}s = {ky} khung ===")
    thu("KHÔNG đánh lại mốc", "", a, b, d, ky)
    thu("fps=30 (ca phình RAM)", f",fps={FPS}", a, b, d, ky)
    thu("setpts=N/FR/TB", ",setpts=N/FR/TB", a, b, d, ky)
    thu(f"setpts=N/{FPS}/TB", f",setpts=N/{FPS}/TB", a, b, d, ky)
    thu("setpts=PTS-STARTPTS", ",setpts=PTS-STARTPTS", a, b, d, ky)

print(f"\nthư mục: {td}")
