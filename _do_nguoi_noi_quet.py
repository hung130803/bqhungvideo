"""QUÉT dải phụ đề mỗi `BUOC` giây trên cả 4 video -> tìm KHOẢNG TRỐNG phụ đề.

Khoảng trống phụ đề = chỗ người kể KHÔNG nói = tiếng của chính bộ phim.
Đây là mỏ neo sự thật; tôi soi bằng mắt từng khoảng tìm ra trước khi ghi nhãn.

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_quet.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = GOC / "_kq_nn"
FF = str(GOC / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0
BUOC = 0.5
TEN = ("v1_dutu", "v2_nieu", "v3_8daodien", "v4_khuyendung")


def quet(video: str, y0: int, y1: int, W: int, dai: float):
    """Đọc CẢ video 1 lượt ở nhịp 1/BUOC fps, chỉ giữ dải phụ đề."""
    import numpy as np
    from app.core import che_chu as cc
    h = y1 - y0
    fps = 1.0 / BUOC
    r = subprocess.run(
        [FF, "-v", "error", "-i", video, "-vf",
         f"fps={fps},crop={W}:{h}:0:{y0},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True, creationflags=_NO_WIN, timeout=1200)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b"")[:300].decode("utf8", "replace"))
    step = W * h
    n = len(r.stdout) // step
    out = []
    for k in range(n):
        g = np.frombuffer(r.stdout[k * step:(k + 1) * step],
                          dtype=np.uint8).reshape(h, W)
        m = cc._mat_na(g)
        colsum = m.mean(axis=0)
        # CHỮ PHỤ ĐỀ nằm giữa khung: đo phần mực trong 80% giữa, và đo
        # xem cột có mực có tạo thành MỘT KHỐI liền ở giữa hay không
        out.append({"t": round(k * BUOC, 2),
                    "md": round(float(m.mean()), 5),
                    "rong": round(float((colsum > 0.02).mean()), 4)})
    return out


def khoang_trong(rows, nguong_md: float, nguong_rong: float):
    """Gộp các mốc KHÔNG có chữ thành khoảng liên tiếp."""
    ra = []
    dau = None
    for r in rows:
        trong = r["md"] < nguong_md or r["rong"] < nguong_rong
        if trong and dau is None:
            dau = r["t"]
        elif not trong and dau is not None:
            ra.append((dau, r["t"]))
            dau = None
    if dau is not None:
        ra.append((dau, rows[-1]["t"] + BUOC))
    return ra


def main() -> None:
    pd = json.loads((SAN / "phude.json").read_text(encoding="utf-8"))
    ket = {}
    for ten in TEN:
        v = pd[ten]
        video = str(SAN / "video" / f"{ten}.mp4")
        d = json.loads((SAN / f"chep_{ten}.json").read_text(encoding="utf-8"))
        rows = quet(video, v["y0"], v["y1"], v["W"], d["dai"])
        mds = sorted(r["md"] for r in rows)
        rgs = sorted(r["rong"] for r in rows)
        n = len(mds)
        print(f"== {ten}: {n} moc (buoc {BUOC}s)")
        print(f"   md   : 1% {mds[n//100]:.4f} | 5% {mds[n//20]:.4f} "
              f"| 25% {mds[n//4]:.4f} | trung vi {mds[n//2]:.4f}")
        print(f"   rong : 1% {rgs[n//100]:.4f} | 5% {rgs[n//20]:.4f} "
              f"| 25% {rgs[n//4]:.4f} | trung vi {rgs[n//2]:.4f}")
        kt = khoang_trong(rows, 0.05, 0.10)
        tong = sum(b - a for a, b in kt)
        print(f"   khoang KHONG chu (md<0.05 hoac rong<0.10): {len(kt)} khoang,"
              f" tong {tong:.1f}s / {d['dai']:.0f}s")
        for a, b in kt:
            if b - a >= 1.0:
                print(f"      {a:7.2f} - {b:7.2f}  ({b - a:.1f}s)")
        ket[ten] = {"rows": rows, "trong": kt}
    (SAN / "quet.json").write_text(json.dumps(ket, ensure_ascii=False),
                                   encoding="utf-8")
    print("GHI: _kq_nn/quet.json")


if __name__ == "__main__":
    main()
