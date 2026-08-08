# -*- coding: utf-8 -*-
r"""TÌM CÁCH CHO `progress` CHẠY ĐÚNG — nghi LỆCH TIMEBASE.

Bằng chứng dẫn tới nghi vấn (`_go_roi_gpu8.py`):
  · `xfade` CPU: 'khác A' 0->39, 'khác B' 37->3 = đường cong ĐÚNG.
  · `xfade_opencl` (CẢ kiểu dựng sẵn `fade` LẪN kernel tự viết): 'khác B' = 0 ở
    MỌI khung -> `progress` kẹt ở đầu "đã xong", chuyển cảnh xảy ra trong < 1
    khung. Kiểu dựng sẵn cũng hỏng -> **lỗi của filter, không phải kernel**.
  · Chèn `setpts=PTS-STARTPTS` trước `hwupload` làm đường cong ĐỘNG trở lại
    (nhưng xong quá sớm: hết ở khung 9/15) -> filter NHẠY với mốc/timebase.
Số `-600479950316066` = AV_NOPTS_VALUE ở timebase **1/15360** (mp4 hay dùng),
trong khi `duration` có vẻ được quy đổi ở timebase khác -> hết `duration` chỉ
sau 1-2 khung.

Bảng này thử ép timebase/mốc bằng `settb`, `fps`, `setpts` và tìm tổ hợp cho
đường cong TRÙNG bản CPU. AN TOÀN: `-frames:v` + timeout ở mọi lệnh.
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
_SB = tempfile.mkdtemp(prefix="goroi9_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="goroi9_")
src = _nguon_nhat.mot("JP")
D, FPS, W, H = 0.5, 30, 480, 854
KY = int(round(D * FPS))
N, M = GPU.CHUAN_HOA, GPU.VE_LAI_MOC
KER = GPU.duong_filter(GPU.duong_kernel())


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


def diem(ks: list) -> tuple:
    """(sai số so đường cong CPU, mô tả). Càng nhỏ càng giống bản CPU."""
    if len(ks) < KY:
        return 9e9, f"chỉ {len(ks)} khung"
    a = [pct(k, KA[min(i, len(KA) - 1)]) for i, k in enumerate(ks[:KY])]
    b = [pct(k, KB[min(i, len(KB) - 1)]) for i, k in enumerate(ks[:KY])]
    e = float(np.mean([abs(x - y) for x, y in zip(a, CPU_A)])
              + np.mean([abs(x - y) for x, y in zip(b, CPU_B)]))
    return e, ("A:" + "".join(f"{v:4.0f}" for v in a) + " | B:"
               + "".join(f"{v:4.0f}" for v in b))


def chay(nhan: str, graph: str, hw: bool = True) -> list:
    out = os.path.join(td, f"o_{abs(hash(nhan))}.mp4")
    cmd = [FF, "-y", "-hide_banner", "-v", "error"]
    if hw:
        cmd += ["-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl"]
    cmd += ["-i", A, "-i", B, "-filter_complex", graph, "-map", "[v]",
            "-frames:v", str(KY + 5), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "18", "-pix_fmt", "yuv420p", out]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           errors="replace", timeout=90, creationflags=CNW)
    except subprocess.TimeoutExpired:
        print(f"  {nhan:<40} ** TREO > 90s **")
        return []
    if p.returncode:
        print(f"  {nhan:<40} rc={p.returncode} "
              f"{(p.stderr or '').strip().splitlines()[-1][:70]}")
        return []
    return moi_khung(out)


A, B = seg(100.0, "a"), seg(300.0, "b")
KA, KB = moi_khung(A), moi_khung(B)
r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=time_base,avg_frame_rate",
                    "-of", "csv=p=0", A], capture_output=True, text=True,
                   creationflags=CNW)
print(f"[nguồn] {os.path.basename(src)} · đoạn thử timebase/fps = "
      f"{(r.stdout or '').strip()}")

ks = chay("xfade CPU (CHUẨN)",
          f"[0:v][1:v]xfade=transition=fade:duration={D:.3f}:offset=0[v]", False)
CPU_A = [pct(k, KA[min(i, len(KA) - 1)]) for i, k in enumerate(ks[:KY])]
CPU_B = [pct(k, KB[min(i, len(KB) - 1)]) for i, k in enumerate(ks[:KY])]
print("  CHUẨN  A:" + "".join(f"{v:4.0f}" for v in CPU_A)
      + " | B:" + "".join(f"{v:4.0f}" for v in CPU_B))


def kern(dau: str, dur: float = D) -> str:
    return (f"[0:v]{N}{dau},hwupload[x];[1:v]{N}{dau},hwupload[y];"
            f"[x][y]xfade_opencl=transition=custom:source='{KER}':"
            f"kernel=gl_gat_trai:duration={dur:.4f}:offset=0[o];[o]{M}[v]")


print("\n--- ép TIMEBASE / mốc ở ĐẦU VÀO ---")
CA = [
    ("trần (như hiện tại)", kern("")),
    ("settb=1/30", kern(",settb=1/30")),
    ("settb=AVTB", kern(",settb=AVTB")),
    ("setpts=PTS-STARTPTS", kern(",setpts=PTS-STARTPTS")),
    ("setpts=N,settb=1/30", kern(",setpts=N,settb=1/30")),
    ("settb=1/15360", kern(",settb=1/15360")),
    ("fps=30,setpts=N,settb=1/30", kern(",fps=30,setpts=N,settb=1/30")),
]
ket = []
for nhan, g in CA:
    k = chay(nhan, g)
    if k:
        e, mo = diem(k)
        ket.append((e, nhan))
        print(f"  {nhan:<28} lệch {e:6.1f}  {mo}")

print("\n--- bù bằng cách NHÂN `duration` (nếu timebase lệch đúng 1 hệ số) ---")
for he in (512.0, 16.0, 1.0 / 512):
    nhan = f"duration x{he:g}"
    k = chay(nhan, kern("", D * he))
    if k:
        e, mo = diem(k)
        ket.append((e, nhan))
        print(f"  {nhan:<28} lệch {e:6.1f}  {mo}")

if ket:
    ket.sort()
    print(f"\nTỐT NHẤT: {ket[0][1]}  (lệch {ket[0][0]:.1f} so đường cong CPU)")
print(f"\nthư mục: {td}")
