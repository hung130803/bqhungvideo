# -*- coding: utf-8 -*-
"""SOI KỸ 2 ĐIỀU BẤT THƯỜNG của `_do_rubberband.py` — TRƯỚC KHI TIN BẢNG.

(A) `atempo=1.0` ra 3,617 dB. Đó là MÉO THẬT hay chỉ là TRỄ (dịch thời gian)?
    Trễ cũng là vấn đề nhưng là vấn đề KHÁC (lệch mốc), và nếu sau khi căn
    thẳng hàng mà lệch về ~0 thì con số 3,617 dB đang nói quá.
    -> căn bằng tương quan chéo rồi ĐO LẠI.

(B) `rubberband=tempo=1.0` ra file NGẮN HƠN 1,28%. Mất ở ĐẦU hay ở ĐUÔI?
    Mất ở ĐẦU = lệch mốc mọi câu (nguy hiểm). Mất ở ĐUÔI = ăn vào lề im
    0,08 s mà `cat_le_im` chừa lại (chấp nhận được) — HOẶC cụt phụ âm cuối
    (không chấp nhận được). Phải phân biệt bằng số, đừng đoán.

  .venv\\Scripts\\python -u _do_rb_soi.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import numpy as np  # noqa: E402

from config import settings  # noqa: E402
import _do_rubberband as R  # noqa: E402

LAM = R.LAM


def tre_mau(x: np.ndarray, y: np.ndarray, toi_da: int = 4000) -> int:
    """Trễ (mẫu) của y so với x, bằng tương quan chéo trên 2 giây đầu."""
    n = min(len(x), len(y), 32000)
    a = x[:n] - x[:n].mean()
    b = y[:n] - y[:n].mean()
    c = np.correlate(a, b, mode="full")
    mid = len(c) // 2
    lo, hi = max(0, mid - toi_da), min(len(c), mid + toi_da)
    return int(np.argmax(c[lo:hi]) + lo - mid)


def nang_luong_duoi(p: Path, giay: float) -> float:
    """RMS dBFS của `giay` giây CUỐI file."""
    x = R.pcm(p)
    n = int(giay * 16000)
    seg = x[-n:] if len(x) > n else x
    if len(seg) == 0:
        return -99.0
    r = float(np.sqrt(np.mean(seg ** 2)))
    return 20.0 * np.log10(max(r, 1e-9))


def main() -> int:
    print("=" * 74)
    print("SOI KỸ — trước khi tin bảng của `_do_rubberband.py`")
    print("=" * 74)

    goc = sorted(LAM.glob("goc_*.wav"))
    if not goc:
        print("Chưa có file — chạy `_do_rubberband.py nhanh` trước.")
        return 1

    # ══════════════ (A) atempo=1.0 — méo hay trễ? ══════════════
    print("\n(A) `atempo=1.0`: MÉO THẬT hay chỉ TRỄ?")
    print("-" * 74)
    print(f"{'câu':>4} | {'trễ mẫu':>8} | {'trễ ms':>7} | "
          f"{'dB thô':>8} | {'dB sau khi CĂN':>15}")
    print("-" * 74)
    tho_l, can_l = [], []
    for i, g in enumerate(goc):
        a = LAM / f"a1_{i}_100.wav"
        if not a.exists():
            continue
        x, y = R.pcm(g), R.pcm(a)
        d = tre_mau(x, y)
        # thô
        n = min(len(x), len(y))
        mx, my = R.logmel(x[:n]), R.logmel(y[:n])
        m = min(len(mx), len(my))
        tho = float(np.mean(np.abs(mx[:m] - my[:m]))) * 10.0
        # căn thẳng hàng rồi đo lại
        if d > 0:
            xa, ya = x[d:], y
        else:
            xa, ya = x, y[-d:]
        n2 = min(len(xa), len(ya))
        mx2, my2 = R.logmel(xa[:n2]), R.logmel(ya[:n2])
        m2 = min(len(mx2), len(my2))
        can = float(np.mean(np.abs(mx2[:m2] - my2[:m2]))) * 10.0
        tho_l.append(tho)
        can_l.append(can)
        print(f"{i:4d} | {d:8d} | {d/16.0:7.1f} | {tho:8.3f} | {can:15.3f}")
    print("-" * 74)
    print(f"{'TB':>4} | {'':>8} | {'':>7} | {np.mean(tho_l):8.3f} | "
          f"{np.mean(can_l):15.3f}")
    if np.mean(can_l) < 0.5:
        print("\n  => CHỦ YẾU LÀ TRỄ, không phải méo phổ. Con số 3,6 dB ở bảng")
        print("     (1) đang NÓI QUÁ. Nhưng TRỄ cũng là lỗi thật: nó dịch")
        print("     toàn bộ câu đi, tức lệch mốc tiếng so với hình.")
    else:
        print("\n  => MÉO THẬT (căn thẳng hàng rồi vẫn lệch).")

    # ══════════════ (B) rubberband mất độ dài ở đâu? ══════════════
    print("\n\n(B) `rubberband=tempo=1.0` NGẮN HƠN 1,28% — mất ở ĐẦU hay ĐUÔI?")
    print("-" * 74)
    print(f"{'câu':>4} | {'trễ mẫu':>8} | {'dài gốc':>8} | {'dài rb':>8} | "
          f"{'mất ms':>7} | {'dBFS đuôi gốc':>14}")
    print("-" * 74)
    for i, g in enumerate(goc):
        b = LAM / f"r1_{i}_100.wav"
        if not b.exists():
            continue
        x, y = R.pcm(g), R.pcm(b)
        d = tre_mau(x, y)
        dg, db = R.do_dai(g), R.do_dai(b)
        mat = (dg - db) * 1000.0
        # đuôi gốc đúng bằng phần bị mất: có tiếng hay là im?
        duoi = nang_luong_duoi(g, max(0.01, (dg - db)))
        print(f"{i:4d} | {d:8d} | {dg:8.3f} | {db:8.3f} | {mat:7.1f} | "
              f"{duoi:14.1f}")
    print("-" * 74)
    print("  trễ 0 mẫu = KHÔNG mất ở đầu (mốc giữ nguyên) -> mất ở ĐUÔI.")
    print("  dBFS đuôi rất thấp (< -50) = phần mất là IM LẶNG, không cụt chữ.")

    # ══════════════ (C) rubberband=1.0 có phải bit-perfect? ══════════════
    print("\n\n(C) `rubberband=tempo=1.0` có trả lại ĐÚNG mẫu gốc không?")
    print("-" * 74)
    for i, g in enumerate(goc[:3]):
        b = LAM / f"r1_{i}_100.wav"
        if not b.exists():
            continue
        x, y = R.pcm(g), R.pcm(b)
        n = min(len(x), len(y))
        lech = np.abs(x[:n] - y[:n])
        print(f"  câu {i}: lệch mẫu lớn nhất {lech.max():.6f} · "
              f"TB {lech.mean():.8f} · giống hệt: "
              f"{'CÓ' if lech.max() < 1e-4 else 'KHÔNG'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
