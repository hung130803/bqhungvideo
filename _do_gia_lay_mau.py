# -*- coding: utf-8 -*-
"""ĐO GIÁ LẤY MẪU: muốn dò HỘP THEO ĐOẠN thì phải đọc DÀY khung — bao nhiêu tiền?

Ba đường, đo ĐAN XEN (máy anh Hùng luôn có việc nền — đo liền mạch ra kết luận
sai 2 lần, xem ghi chú CLAUDE.md):
  A. `-ss` trước `-i`, N lượt   (cách `che_chu` đang dùng)
  B. MỘT lượt giải mã, `-vf fps=k`
  C. MỘT lượt `-skip_frame nokey` (chỉ giải mã khung khoá)
"""
from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
_SB = Path(r"D:\claude\_do_che_chu\_sandbox")
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                              # noqa: BLE001
    pass

from app.core import che_chu as C                              # noqa: E402

KHO = Path(r"D:\claude\_do_che_chu\nguon")


def _chay(cmd) -> tuple:
    t = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW,
                       stdin=subprocess.DEVNULL)
    return time.perf_counter() - t, len(r.stdout), r.returncode


def A(p: Path, n: int, w: int, h: int) -> tuple:
    tt = C.thong_tin(p)
    moc = C._moc_lay_mau(0.0, tt["do_dai"], n)
    t = time.perf_counter()
    so = 0
    for m in moc:
        cmd = [C._bin("ffmpeg"), "-v", "error", "-ss", f"{m:.3f}", "-i",
               str(p), "-frames:v", "1", "-vf", f"scale={w}:{h}",
               "-f", "rawvideo", "-pix_fmt", "gray", "-"]
        _, nb, rc = _chay(cmd)
        so += 1 if nb == w * h else 0
    return time.perf_counter() - t, so


def B(p: Path, k: float, w: int, h: int) -> tuple:
    cmd = [C._bin("ffmpeg"), "-v", "error", "-i", str(p), "-vf",
           f"fps={k},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    dt, nb, rc = _chay(cmd)
    return dt, nb // (w * h)


def Cc(p: Path, w: int, h: int) -> tuple:
    cmd = [C._bin("ffmpeg"), "-v", "error", "-skip_frame", "nokey",
           "-i", str(p), "-vsync", "0", "-vf", f"scale={w}:{h}",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    dt, nb, rc = _chay(cmd)
    return dt, nb // (w * h)


def main():
    w, h = 640, 360
    for ten in ("zh_ep12.mp4", "zh_dongho.mp4"):
        p = KHO / ten
        if not p.exists():
            continue
        tt = C.thong_tin(p)
        ph = tt["do_dai"] / 60.0
        print(f"\n=== {ten}  {tt['do_dai']:.0f}s ({ph:.2f} phút)")
        ket = {}
        for vong in range(3):                       # ĐAN XEN 3 vòng
            for ten_c, fn in (("A16", lambda: A(p, 16, w, h)),
                              ("A48", lambda: A(p, 48, w, h)),
                              ("A96", lambda: A(p, 96, w, h)),
                              ("B1fps", lambda: B(p, 1.0, w, h)),
                              ("Ckhoá", lambda: Cc(p, w, h))):
                dt, so = fn()
                ket.setdefault(ten_c, []).append((dt, so))
        for k, v in ket.items():
            dts = [x[0] for x in v]
            print(f"  {k:6s} trung vị {statistics.median(dts):7.2f}s "
                  f"({statistics.median(dts)/ph:6.2f} s/phút phim) · "
                  f"{v[0][1]} khung")


if __name__ == "__main__":
    main()
