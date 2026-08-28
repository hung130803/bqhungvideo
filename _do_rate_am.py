# -*- coding: utf-8 -*-
"""ĐƯỜNG CONG `rate` ÂM — đọc CHẬM lại bằng CHÍNH máy đọc, 0 phép xử lý tín hiệu.

`_do_doc_cham.py` đo được hướng "kéo dài câu cho đầy khung" chữa được lời kêu
*"được đoạn rồi nghỉ"* với **lệch tiếng-hình ~7 ms**, nhưng nó kéo bằng
`rubberband` -> **méo phổ 3,1-3,5 dB**. Bước 4c của app đã có sẵn đường KHÔNG
méo: `rate` của máy đọc (`doc_nhanh_vua_khung` dùng `+N%`). Câu hỏi còn lại là
**`-N%` có kéo dài được đúng chừng đó không**, và tới đâu thì bão hoà.

CLAUDE.md đã có nửa dương: `+5% -> 1,046x · +20% -> 1,190 · +50% -> 1,455`.
Nửa ÂM thì **chưa ai đo**. Đo bằng CHÍNH cửa app dùng (`dubbing._synth_all`),
trên câu tiếng Việt THẬT, đo độ dài NÓI THẬT (`do_le_im`) chứ không phải độ dài
file (edge-tts chèn ~0,2 s đầu / ~0,87 s cuối — bẫy v2.27.0).

    .venv\\Scripts\\python -u _do_rate_am.py
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

from app.core import dubbing                          # noqa: E402
from app.core import thay_giong as tg                 # noqa: E402

LAM = REPO / "_do_rate_am_tam"
KQ = REPO / "_kq_rate_am.json"
GIONG = "vi-VN-HoaiMyNeural"
RATES = ["-40%", "-30%", "-25%", "-20%", "-15%", "-10%", "-5%", "+0%"]

CAU = [
    "Bộ phim này được tám đạo diễn Hollywood cùng nhau thực hiện.",
    "Anh ta lo rằng sau khi chôn cất, mọi thứ sẽ không còn nguyên vẹn.",
    "Lúc này, người khám nghiệm tử thi tình cờ dẫn gia đình tới.",
    "Xác vừa mới chôn xong thì hắn đã bắt đầu đào lên rồi.",
]


def doc(rate: str, lam: Path) -> list[float]:
    """Trả GIÂY NÓI THẬT của từng câu ở mức `rate` đó."""
    lam.mkdir(parents=True, exist_ok=True)
    paths = [str(lam / f"c{i}.mp3") for i in range(len(CAU))]
    ok = asyncio.run(dubbing._synth_all(CAU, GIONG, paths, rate=rate))
    ra = []
    for p, o in zip(paths, ok):
        if not o or not Path(p).exists():
            ra.append(0.0)
            continue
        d = tg.probe_duration(p)
        a, b, _ = tg.do_le_im(p, nguong_db=tg.NGUONG_IM_MOC_DB)
        ra.append(max(0.0, d - a - b))       # GIÂY NÓI THẬT
    return ra


def main() -> int:
    goc = doc("+0%", LAM / "r0")
    if not all(goc):
        print("KHÔNG đọc được câu mốc -> dừng (mạng edge-tts?)")
        return 2
    print(f"MỐC (+0%): {[round(x, 3) for x in goc]}  "
          f"tổng {sum(goc):.3f}s\n")
    print(f"| {'rate':>6} | {'hệ số kéo dài':>13} | {'từng câu':>34} |")
    print(f"|{'-' * 8}|{'-' * 15}|{'-' * 36}|")
    bang = []
    for r in RATES:
        d = doc(r, LAM / ("r" + r.replace("%", "").replace("+", "p")
                          .replace("-", "m")))
        he = [(x / g) for x, g in zip(d, goc) if g > 0 and x > 0]
        tb = statistics.fmean(he) if he else 0.0
        bang.append({"rate": r, "he_so_tb": round(tb, 4),
                     "he_so_cau": [round(x, 4) for x in he],
                     "giay": [round(x, 3) for x in d]})
        print(f"| {r:>6} | {tb:>13.4f} | "
              f"{' '.join(f'{x:.3f}' for x in he):>34} |")
    KQ.write_text(json.dumps(bang, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi: {KQ.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
