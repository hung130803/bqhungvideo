# -*- coding: utf-8 -*-
"""ĐO: bảo edge-tts ĐỌC NHANH (rate=+N%) có thay được `atempo` không?

VÌ SAO HỎI: `atempo` là WSOLA — cắt-dán cửa sổ sóng, đo được **5,4-8,1 dB méo
phổ** (vòng tròn ép nhanh k rồi chậm 1/k). Còn `rate` của edge-tts là giọng
đọc nhanh THẬT do chính mô hình sinh ra: **KHÔNG có phép cắt-dán nào**, méo
do co giãn = 0 theo cấu tạo.

CẦN ĐO 3 điều trước khi dám dùng:
  1. `rate=+N%` có ra ĐÚNG tỉ lệ nhanh N% không (để tính ngược được)?
  2. Đọc nhanh có làm SAI CHỮ không (WER, Groq thật)?
  3. Lề im lặng có đổi không (bản vá cắt lề phải còn ăn)?

    .venv\\Scripts\\python _do_rate_tts.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
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

from app.core import dubbing, thay_giong as tg  # noqa: E402
import _do_nguong_tempo as ng  # noqa: E402

LAM = REPO / "_do_rate_tam"
RATE = [0, 5, 10, 15, 20, 25, 30, 40, 50]


def main() -> int:
    ng._nap()
    if LAM.exists():
        shutil.rmtree(LAM, ignore_errors=True)
    LAM.mkdir(parents=True, exist_ok=True)
    cau = ng.CAU
    voice = tg.giong_theo_ngon_ngu("en")
    print(f"Giọng: {voice} · {len(cau)} câu · rate {RATE}")

    d0: list[float] = []
    bang = {}
    for r in RATE:
        rs = f"+{r}%" if r >= 0 else f"{r}%"
        ps = [str(LAM / f"r{r}_{i}.mp3") for i in range(len(cau))]
        ok = asyncio.run(dubbing._synth_all(cau, voice, ps, rate=rs))
        ty, wers, les = [], [], []
        for i, t in enumerate(cau):
            if not ok[i]:
                print(f"  ! TTS hỏng #{i} rate {rs}")
                continue
            sach = LAM / f"r{r}_{i}.wav"
            dau, cuoi, tho = tg.do_le_im(ps[i])
            d = tg.cat_le_im(ps[i], sach)
            if r == 0:
                d0.append(d)
            les.append((dau, cuoi))
            ty.append(d0[i] / max(0.01, d))
            wers.append(ng.wer(t, ng.chep(sach, f"R|{r}|{i}")))
        n = max(1, len(ty))
        bang[r] = {
            "nhanh_thuc": sum(ty) / n,
            "nhanh_thuc_min": min(ty or [0]),
            "nhanh_thuc_max": max(ty or [0]),
            "wer": 100.0 * sum(wers) / n,
            "le_dau": sum(x for x, _ in les) / n,
            "le_cuoi": sum(y for _, y in les) / n,
        }
        b = bang[r]
        print(f"  rate {rs:>5}: NHANH THẬT {b['nhanh_thuc']:.3f}x "
              f"({b['nhanh_thuc_min']:.3f}-{b['nhanh_thuc_max']:.3f}) · "
              f"WER {b['wer']:.2f}% · lề {b['le_dau']:.3f}/{b['le_cuoi']:.3f}s")

    print("\n=== BẢNG rate edge-tts ===")
    print(f"{'rate %':>7} {'nhanh thật':>11} {'sai lệch':>9} {'WER %':>7} "
          f"{'lề đầu s':>9} {'lề cuối s':>10}")
    for r in RATE:
        b = bang[r]
        mong = 1.0 + r / 100.0
        print(f"{r:>7} {b['nhanh_thuc']:>11.3f} "
              f"{100 * (b['nhanh_thuc'] / mong - 1):>8.1f}% "
              f"{b['wer']:>7.2f} {b['le_dau']:>9.3f} {b['le_cuoi']:>10.3f}")
    print("\nĐối chiếu MÉO: atempo cùng mức ép đo được 5,357-8,071 dB méo phổ; "
          "rate edge-tts = 0 (không có phép co giãn nào).")
    (REPO / "_do_rate_ketqua.json").write_text(
        json.dumps({str(k): v for k, v in bang.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(LAM, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
