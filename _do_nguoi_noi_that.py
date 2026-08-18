"""BỘ ĐỐI CHỨNG SỰ THẬT — "đoạn này có phụ đề người kể hay không".

Bộ dò đầu tiên (mật độ nét cả dải) BÁO GIẢ ở dòng phụ đề NGẮN: `另一边`
(3 chữ) ra md 0,027 / rộng 0,097, tụt xuống dưới cùng bảng y như chỗ KHÔNG
có chữ. Đã soi mắt và bắt được (`_kq_nn/soi/soi_0.png` hàng 3).

THƯỚC MỚI: chữ phụ đề là nét **SÁNG GẦN TRẮNG** có viền tối, nằm **GIỮA
khung**, và **NẰM TRÊN MỘT HÀNG** — vân cảnh (đá, lá, tường) thì tối hơn và
rải khắp. Đo `diem` = tỉ lệ điểm ảnh vừa nằm trong mặt nạ nét vừa sáng >=
`NGUONG_SANG`, tính trong 84% GIỮA bề ngang.

Nhãn cuối cùng KHÔNG do ngưỡng quyết — tôi soi mắt từng đoạn ở vùng ranh giới
và ghi nhãn tay (xem `_kq_nn/nhan_tay.json`).

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_that.py
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
TEN = ("v1_dutu", "v2_nieu", "v3_8daodien", "v4_khuyendung")

NGUONG_SANG = 190       # chữ phụ đề gần trắng
GIUA = 0.84             # chỉ tính 84% giữa bề ngang
BUOC = 0.25             # nhịp lấy mẫu (giây)


def quet(video: str, y0: int, y1: int, W: int):
    import numpy as np
    from app.core import che_chu as cc
    h = y1 - y0
    r = subprocess.run(
        [FF, "-v", "error", "-i", video, "-vf",
         f"fps={1.0 / BUOC},crop={W}:{h}:0:{y0},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True, creationflags=_NO_WIN, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b"")[:300].decode("utf8", "replace"))
    step = W * h
    x0 = int(W * (1 - GIUA) / 2)
    x1 = W - x0
    out = []
    for k in range(len(r.stdout) // step):
        g = np.frombuffer(r.stdout[k * step:(k + 1) * step],
                          dtype=np.uint8).reshape(h, W)[:, x0:x1]
        m = cc._mat_na(g).astype(bool) & (g >= NGUONG_SANG)
        # hàng đậm nhất: chữ nằm gọn trên 1-2 hàng chữ
        hang = m.mean(axis=1)
        out.append({"t": round(k * BUOC, 2),
                    "diem": round(float(m.mean()), 5),
                    "hang": round(float(hang.max()), 5)})
    return out


def main() -> None:
    pd = json.loads((SAN / "phude.json").read_text(encoding="utf-8"))
    ket = {}
    for ten in TEN:
        v = pd[ten]
        rows = quet(str(SAN / "video" / f"{ten}.mp4"),
                    v["y0"], v["y1"], v["W"])
        ds = sorted(r["diem"] for r in rows)
        n = len(ds)
        print(f"== {ten}: {n} moc, buoc {BUOC}s")
        print(f"   diem: min {ds[0]:.5f} | 1% {ds[n//100]:.5f} "
              f"| 5% {ds[n//20]:.5f} | 25% {ds[n//4]:.5f} "
              f"| trung vi {ds[n//2]:.5f} | max {ds[-1]:.5f}")
        ket[ten] = rows

        # gộp mốc THẤP thành khoảng, để soi mắt
        for ng in (0.004, 0.008):
            kt, dau = [], None
            for r in rows:
                if r["diem"] < ng and dau is None:
                    dau = r["t"]
                elif r["diem"] >= ng and dau is not None:
                    kt.append((dau, r["t"]))
                    dau = None
            if dau is not None:
                kt.append((dau, rows[-1]["t"] + BUOC))
            dai = [(a, b) for a, b in kt if b - a >= 0.75]
            print(f"   nguong {ng}: {len(kt)} khoang "
                  f"(tong {sum(b-a for a,b in kt):.2f}s), "
                  f">=0.75s: {len(dai)} -> "
                  f"{' '.join(f'{a:.2f}-{b:.2f}' for a, b in dai[:14])}")
    (SAN / "diem.json").write_text(json.dumps(ket, ensure_ascii=False),
                                   encoding="utf-8")
    print("GHI: _kq_nn/diem.json")


if __name__ == "__main__":
    main()
