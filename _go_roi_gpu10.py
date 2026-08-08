# -*- coding: utf-8 -*-
r"""CHỐT: `xfade_opencl` có chạy ĐÚNG đường cong không — so `fade` với `fade`.

**LỖI ĐO của chính tôi ở `_go_roi_gpu9.py`:** tôi chấm kernel `gl_gat_trai`
(kiểu TRƯỢT) bằng đường cong tham chiếu `xfade=fade` (kiểu MỜ DẦN). Hai kiểu
chuyển cảnh khác nhau thì đường cong % pixel khác nhau là ĐƯƠNG NHIÊN -> mọi ca
đều "lệch" và tôi suýt kết luận hớ. Cùng bài học "so sai đối chứng" của cổng 36.

Ở đây chấm **`xfade_opencl=fade` với `xfade=fade` CPU** — CÙNG một phép chuyển
cảnh, nên lệch còn lại đúng là lỗi của `xfade_opencl`.

Thêm: đo `pha_tron` = mức TRỘN thật của khung giữa. Chuyển cảnh mờ dần ĐÚNG thì
khung giữa phải là TRUNG BÌNH của A và B (lệch nhỏ với `(A+B)/2`), còn khi
`progress` kẹt thì nó trùng khít A hoặc B.
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
_SB = tempfile.mkdtemp(prefix="goroiA_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF = settings.FFMPEG_PATH
td = tempfile.mkdtemp(prefix="goroiA_")
src = _nguon_nhat.mot("JP")
D, FPS, W, H = 0.5, 30, 480, 854
KY = int(round(D * FPS))
M = GPU.VE_LAI_MOC


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
    cap, ra = cv2.VideoCapture(p), []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        ra.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32))
    cap.release()
    return ra


def pct(x, y) -> float:
    return float((np.abs(x - y) > 12).mean() * 100.0)


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
        print(f"  {nhan:<34} ** TREO **")
        return []
    if p.returncode:
        print(f"  {nhan:<34} rc={p.returncode} "
              f"{(p.stderr or '').strip().splitlines()[-1][:70]}")
        return []
    return moi_khung(out)


def bang(nhan: str, ks: list) -> None:
    if not ks:
        return
    a = [pct(k, KA[min(i, len(KA) - 1)]) for i, k in enumerate(ks[:KY])]
    b = [pct(k, KB[min(i, len(KB) - 1)]) for i, k in enumerate(ks[:KY])]
    # mức TRỘN ở khung giữa: |khung - (A+B)/2| trung bình. Trộn thật -> NHỎ.
    i = min(KY // 2, len(ks) - 1)
    tron = float(np.abs(ks[i] - (KA[min(i, len(KA) - 1)]
                                 + KB[min(i, len(KB) - 1)]) / 2.0).mean())
    e = (float(np.mean([abs(x - y) for x, y in zip(a, CA_)]))
         + float(np.mean([abs(x - y) for x, y in zip(b, CB_)]))) if CA_ else -1
    print(f"  {nhan:<34} lệch{e:6.1f}  trộn giữa {tron:5.1f}\n"
          f"        A:" + "".join(f"{v:4.0f}" for v in a)
          + "\n        B:" + "".join(f"{v:4.0f}" for v in b))


A, B = seg(100.0, "a"), seg(300.0, "b")
KA, KB = moi_khung(A), moi_khung(B)
CA_: list = []
CB_: list = []
print(f"[nguồn] {os.path.basename(src)} · {len(KA)}/{len(KB)} khung")
print("Đọc bảng: 'lệch' = sai khác đường cong so `xfade=fade` CPU (0 = trùng"
      " khít). 'trộn giữa' = |khung giữa − (A+B)/2|; MỜ DẦN đúng thì NHỎ (~5-10),"
      " progress kẹt thì LỚN (~20+).")

ks = chay("xfade=fade CPU (CHUẨN)",
          f"[0:v][1:v]xfade=transition=fade:duration={D:.3f}:offset=0[v]", False)
CA_ = [pct(k, KA[min(i, len(KA) - 1)]) for i, k in enumerate(ks[:KY])]
CB_ = [pct(k, KB[min(i, len(KB) - 1)]) for i, k in enumerate(ks[:KY])]
bang("xfade=fade CPU (CHUẨN)", ks)

print("\n--- xfade_opencl=fade, đổi chuỗi ĐẦU VÀO ---")
DAU = [
    ("CHUAN_HOA (như hiện tại)", GPU.CHUAN_HOA),
    ("CHUAN_HOA + settb=1/30", GPU.CHUAN_HOA + ",settb=1/30"),
    ("không setparams", "format=yuv420p,setsar=1"),
    ("không setparams + settb=1/30", "format=yuv420p,setsar=1,settb=1/30"),
    ("chỉ format", "format=yuv420p"),
]
for nhan, dau in DAU:
    bang(nhan, chay("f_" + nhan,
                    f"[0:v]{dau},hwupload[x];[1:v]{dau},hwupload[y];"
                    f"[x][y]xfade_opencl=transition=fade:"
                    f"duration={D:.3f}:offset=0[o];[o]{M}[v]"))
print(f"\nthư mục: {td}")
