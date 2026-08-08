# -*- coding: utf-8 -*-
"""Gỡ rối 1 ca chuyển cảnh GPU: in NGUYÊN log ffmpeg + probe từng bước."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
W, H, FPS, D = 720, 1280, 30, 0.5
td = tempfile.mkdtemp(prefix="goroi_gpu_")
src = _nguon_nhat.mot("JP")
print("[nguồn]", os.path.basename(src))

segs = []
for i, moc in enumerate((100.0, 300.0)):
    p = os.path.join(td, f"s{i}.mp4")
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner", "-v",
                        "error", "-ss", f"{moc:.3f}", "-t", f"{D:.3f}",
                        "-i", src, "-an", "-vf",
                        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                        f"crop={W}:{H},setsar=1,fps={FPS}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                        "-pix_fmt", "yuv420p", p],
                       capture_output=True, text=True, errors="replace",
                       creationflags=CNW)
    segs.append(p)
    pr = subprocess.run([settings.FFPROBE_PATH, "-v", "error", "-select_streams",
                         "v:0", "-count_frames", "-show_entries",
                         "stream=nb_read_frames,duration,pix_fmt,color_range,"
                         "color_space", "-of", "default=nw=1", p],
                        capture_output=True, text=True, creationflags=CNW)
    print(f"  seg{i}: rc={r.returncode} size={os.path.getsize(p)}")
    print("   ", pr.stdout.replace("\n", " · ").strip())

out = os.path.join(td, "g.mp4")
args = GPU.lenh_vung_chong(segs[0], segs[1], out, "gl_gio", D,
                           enc=["-c:v", "libx264", "-preset", "veryfast",
                                "-crf", "18", "-pix_fmt", "yuv420p"])
print("\n[LỆNH]")
print(" ", " ".join(str(x) for x in args)[:600])
p = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                    *[str(x) for x in args]],
                   capture_output=True, text=True, errors="replace",
                   creationflags=CNW)
print(f"\n[rc] {p.returncode}")
print("[stderr 2500 ký tự cuối]")
print((p.stderr or "")[-2500:])
if os.path.exists(out):
    print(f"\n[file ra] {os.path.getsize(out)} byte")
    pr = subprocess.run([settings.FFPROBE_PATH, "-v", "error", "-select_streams",
                         "v:0", "-count_frames", "-show_entries",
                         "stream=nb_read_frames,duration,nb_frames", "-of",
                         "default=nw=1", out],
                        capture_output=True, text=True, creationflags=CNW)
    print("[probe]", (pr.stdout or "").replace("\n", " · "), "ERR:", pr.stderr[:200])
else:
    print("\n[file ra] KHÔNG CÓ")
