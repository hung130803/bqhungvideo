# -*- coding: utf-8 -*-
r"""SOI ĐƯỜNG CONG `progress` từng khung — vì sao MỌI kernel ra y hệt đoạn B.

Sau khi chữa PTS rác bằng `setpts=N/FR/TB`, số khung ra đã ĐÚNG (15/15) nhưng
khung GIỮA đo được **khác A 38,0% · khác B 0,0%** ở CẢ 24 kernel, với cùng một
bộ số -> nghi `progress` bị kẹt ở một đầu chứ không phải kernel sai.

Bảng này in **% khác A và % khác B của TỪNG khung**, cho 3 ca:
  1. `xfade` CPU        — cái ĐÚNG, để biết đường cong phải trông thế nào
  2. `xfade_opencl` kiểu DỰNG SẴN (`fade`) — mã của chính ffmpeg, loại trừ kernel
  3. `xfade_opencl` kernel gl-transitions
Thêm ca chuẩn hoá PTS đầu vào (`setpts=PTS-STARTPTS` TRƯỚC `hwupload`) để xem
`progress` có sống lại không.

AN TOÀN: mọi lệnh có `-frames:v` + timeout (bài học 19,1 GB RSS).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi8_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF = settings.FFMPEG_PATH
td = tempfile.mkdtemp(prefix="goroi8_")
src = _nguon_nhat.mot("JP")
D, FPS, W, H = 0.5, 30, 480, 854
KY = int(round(D * FPS))


def seg(moc: float, ten: str) -> str:
    p = os.path.join(td, f"{ten}.mp4")
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", f"{D:.3f}", "-i", src, "-an",
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                           f"crop={W}:{H},setsar=1,fps={FPS}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", p],
                   capture_output=True, timeout=180, creationflags=CNW)
    return p


def moi_khung(p: str) -> list:
    """TẤT CẢ khung xám của file (đọc tuần tự — clip ngắn seek không nổi)."""
    cap = cv2.VideoCapture(p)
    ra = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        ra.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.int16))
    cap.release()
    return ra


def pct(x, y) -> float:
    return float((np.abs(x - y) > 12).mean() * 100.0)


def chay(nhan: str, graph: str, hw: bool) -> None:
    out = os.path.join(td, f"o_{abs(hash(nhan))}.mp4")
    cmd = [FF, "-y", "-hide_banner", "-v", "error"]
    if hw:
        cmd += ["-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl"]
    cmd += ["-i", A, "-i", B, "-filter_complex", graph, "-map", "[v]",
            "-frames:v", str(KY + 5),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", out]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           errors="replace", timeout=90, creationflags=CNW)
    except subprocess.TimeoutExpired:
        print(f"{nhan}: ** TREO > 90s **")
        return
    if p.returncode:
        print(f"{nhan}: rc={p.returncode} {(p.stderr or '')[-120:]}")
        return
    ks = moi_khung(out)
    print(f"\n{nhan}  ({len(ks)} khung)")
    print("   khung |" + "".join(f"{i:5d}" for i in range(len(ks))))
    print("  khác A |" + "".join(f"{pct(k, KA[min(i, len(KA) - 1)]):5.0f}"
                                 for i, k in enumerate(ks)))
    print("  khác B |" + "".join(f"{pct(k, KB[min(i, len(KB) - 1)]):5.0f}"
                                 for i, k in enumerate(ks)))


A, B = seg(100.0, "a"), seg(300.0, "b")
KA, KB = moi_khung(A), moi_khung(B)
print(f"[nguồn] {os.path.basename(src)} · 2 đoạn {D}s = {len(KA)}/{len(KB)} khung"
      f" · A khác B {pct(KA[len(KA) // 2], KB[len(KB) // 2]):.0f}%")
print("Đọc bảng: chuyển cảnh ĐÚNG = 'khác A' tăng dần 0->cao, 'khác B' giảm dần"
      " cao->0. Cột phẳng = progress KẸT.")

N = GPU.CHUAN_HOA
KER = GPU.duong_filter(GPU.duong_kernel())
M = GPU.VE_LAI_MOC

chay("1. xfade CPU (ĐỐI CHỨNG ĐÚNG)",
     f"[0:v][1:v]xfade=transition=fade:duration={D:.3f}:offset=0[v]", False)
chay("2. xfade_opencl=fade (kiểu DỰNG SẴN của ffmpeg)",
     f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
     f"[x][y]xfade_opencl=transition=fade:duration={D:.3f}:offset=0[o];"
     f"[o]{M}[v]", True)
chay("3. xfade_opencl custom gl_gat_trai",
     f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
     f"[x][y]xfade_opencl=transition=custom:source='{KER}':kernel=gl_gat_trai:"
     f"duration={D:.3f}:offset=0[o];[o]{M}[v]", True)
chay("4. như (3) + setpts=PTS-STARTPTS TRƯỚC hwupload",
     f"[0:v]{N},setpts=PTS-STARTPTS,hwupload[x];"
     f"[1:v]{N},setpts=PTS-STARTPTS,hwupload[y];"
     f"[x][y]xfade_opencl=transition=custom:source='{KER}':kernel=gl_gat_trai:"
     f"duration={D:.3f}:offset=0[o];[o]{M}[v]", True)
chay("5. như (3) nhưng đoạn A DÀI GẤP ĐÔI, offset=D",
     f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
     f"[x][y]xfade_opencl=transition=custom:source='{KER}':kernel=gl_gat_trai:"
     f"duration={D:.3f}:offset=0.001[o];[o]{M}[v]", True)
print(f"\nthư mục: {td}")
