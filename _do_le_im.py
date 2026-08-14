# -*- coding: utf-8 -*-
"""ĐO LỀ IM LẶNG edge-tts thêm vào đầu/cuối MỖI CÂU.

MANH MỐI: trong lượt đo thật, câu dịch 12 ký tự đọc mất 1,87 giây còn câu 28
ký tự chỉ 2,42 giây. Khớp tuyến tính ra ~1,4 giây CHI PHÍ CỐ ĐỊNH — tức phần
lớn thời lượng câu NGẮN không phải là tiếng nói. Nếu đúng thì app đang **ép
nhanh giọng để nén KHOẢNG IM LẶNG**, méo tiếng mà chẳng được gì.

Đo bằng `silencedetect` của ffmpeg trên chính file edge-tts trả về.

    .venv\\Scripts\\python _do_le_im.py
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
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

from config import settings  # noqa: E402
from app.core import dubbing, thay_giong as tg  # noqa: E402

LAM = REPO / "_do_le_tam"

CAU = {
    "en": ["Yes.", "He ran away.", "Nobody said a word.",
           "The doctor came up with a clever idea.",
           "What happened next changed the way the whole family lived for years.",
           "She looked at the photograph one more time and finally understood "
           "everything that had been hidden from her since childhood."],
    "vi": ["Rồi.", "Anh ta bỏ chạy.", "Không ai nói một lời.",
           "Bác sĩ nghĩ ra một cách rất thông minh.",
           "Chuyện xảy ra sau đó đã thay đổi cả gia đình suốt nhiều năm liền.",
           "Cô nhìn tấm ảnh thêm một lần nữa và cuối cùng đã hiểu ra tất cả "
           "những gì bị giấu kín từ khi còn nhỏ."],
}


def im_hai_dau(path: Path, nguong_db: float = -45.0) -> tuple[float, float, float]:
    """(im đầu, im cuối, tổng) giây — đo bằng silencedetect THẬT."""
    tong = tg.probe_duration(path)
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-i", str(path),
         "-af", f"silencedetect=n={nguong_db}dB:d=0.03", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = r.stderr or ""
    khoang = []
    st = None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", txt):
        if m.group(1) == "start":
            st = float(m.group(2))
        elif st is not None:
            khoang.append((st, float(m.group(2))))
            st = None
    if st is not None:
        khoang.append((st, tong))
    dau = khoang[0][1] if khoang and khoang[0][0] <= 0.02 else 0.0
    cuoi = (tong - khoang[-1][0]) if khoang and khoang[-1][1] >= tong - 0.02 \
        else 0.0
    return dau, cuoi, tong


def main() -> int:
    if LAM.exists():
        shutil.rmtree(LAM, ignore_errors=True)
    LAM.mkdir(parents=True, exist_ok=True)
    for ma, texts in CAU.items():
        voice = tg.giong_theo_ngon_ngu(ma)
        paths = [str(LAM / f"{ma}_{i}.mp3") for i in range(len(texts))]
        ok = asyncio.run(dubbing._synth_all(texts, voice, paths))
        print(f"\n=== {ma} · {voice} ===")
        print(f"{'ký tự':>6} {'tổng s':>7} {'im đầu':>7} {'im cuối':>8} "
              f"{'TIẾNG s':>8} {'ký tự/giây tiếng':>17}")
        tong_kt = tong_tieng = 0.0
        for i, t in enumerate(texts):
            if not ok[i]:
                print(f"  ! TTS hỏng câu #{i}")
                continue
            d, c, tg_ = im_hai_dau(Path(paths[i]))
            tieng = max(0.01, tg_ - d - c)
            tong_kt += len(t)
            tong_tieng += tieng
            print(f"{len(t):>6} {tg_:>7.3f} {d:>7.3f} {c:>8.3f} {tieng:>8.3f} "
                  f"{len(t) / tieng:>17.2f}")
        print(f"  => TỐC ĐỘ ĐỌC (bỏ lề im): {tong_kt / max(0.01, tong_tieng):.2f}"
              f" ký tự/giây")
    shutil.rmtree(LAM, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
