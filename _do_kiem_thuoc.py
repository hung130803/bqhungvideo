"""KIỂM THƯỚC NHẤN NHÁ DỰNG LẠI — có tái lập được bảng 82 giọng đang chạy không?

``_do_nhan_nha.py`` là bản DỰNG LẠI (bản gốc chưa bao giờ được commit). Trước
khi dùng nó đo thêm một giọng nào, phải chứng minh nó cho ra **đúng những con
số đã nằm trong ``app/core/nhan_nha.BANG``** — nếu không thì mọi giọng mới sẽ
mang số của một cái thước KHÁC, nằm chung một cột với số cũ, và không ai nhìn
ra được.

Chọn 8 giọng TRẢI KHẮP THANG (đáy 2,26 -> đỉnh 5,86) chứ không lấy 8 giọng
sát nhau: thước lệch tuyến tính (nhân/cộng một hằng số) chỉ lộ ra khi so hai
đầu thang.

NGƯỠNG: ``nhan_nha.__doc__`` đã ghi số đo lại của chính lượt gốc —
*"5 giọng đủ 4 câu lệch 0,00 · 0,00 · 0,00 · +0,01 · +0,09"*, giọng lệch nhiều
nhất +0,12 là giọng thiếu câu. Nên lấy **0,15** làm trần cho từng giọng: rộng
hơn nhiễu đã biết một chút, nhưng hẹp hơn nhiều so với bậc thang mức
(RAT_CAO 4,1 · CAO 3,6 · VUA 3,1 — cách nhau 0,5).

Chạy: PYTHONPATH=_lib_giong .venv\\Scripts\\python -u _do_kiem_thuoc.py
"""
from __future__ import annotations

import os
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "_lib_giong"))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

#: Trần lệch cho TỪNG giọng (nửa cung) — xem docstring.
TRAN = 0.15

#: 8 giọng trải khắp thang của bảng đang chạy.
MAU = [
    "ar-SA-HamedNeural",        # 5,86 — đỉnh bảng
    "en-GB-RyanNeural",         # 5,38
    "en-US-AndrewNeural",       # 4,49
    "vi-VN-NamMinhNeural",      # 4,04
    "en-US-AriaNeural",         # 3,33
    "vi-VN-HoaiMyNeural",       # 3,18
    "en-US-JennyNeural",        # 3,06
    "es-ES-ElviraNeural",       # 2,26 — đáy bảng
]


def main() -> int:
    from _do_nhan_nha_bang import SAN, do_mot
    from app.core import nhan_nha

    SAN.mkdir(exist_ok=True)
    print("KIỂM THƯỚC DỰNG LẠI — so với app/core/nhan_nha.BANG")
    print("-" * 74)
    print(f"{'giọng':30s} {'bảng':>7s} {'đo lại':>8s} {'lệch':>7s} "
          f"{'khung':>7s} {'câu':>4s}")
    lech: list[float] = []
    hong: list[str] = []
    for v in MAU:
        cu = nhan_nha.BANG.get(v)
        d = do_mot(v)
        if d.get("loi"):
            print(f"{v:30s} {cu:7.2f}  LỖI: {d['loi']}")
            hong.append(f"{v}: {d['loi']}")
            continue
        moi = d["nhan_nha"]
        dl = moi - cu
        lech.append(abs(dl))
        dau = "  " if abs(dl) <= TRAN else "<<"
        print(f"{v:30s} {cu:7.2f} {moi:8.2f} {dl:+7.2f} {d['so_khung']:7d} "
              f"{d['so_cau']:4d} {dau}")
        if abs(dl) > TRAN:
            hong.append(f"{v}: lệch {dl:+.2f} > {TRAN}")
    print("-" * 74)
    if lech:
        print(f"lệch tuyệt đối: TB {st.mean(lech):.3f} · "
              f"trung vị {st.median(lech):.3f} · max {max(lech):.3f} "
              f"(trần {TRAN})")
    if hong:
        print(f"\nTHƯỚC KHÔNG TÁI LẬP ĐƯỢC BẢNG CŨ — {len(hong)} giọng lệch:")
        for h in hong:
            print("  " + h)
        print("=> KHÔNG được dùng thước này để thêm giọng vào BANG.")
        return 1
    print("\nTHƯỚC TÁI LẬP ĐƯỢC BẢNG CŨ -> dùng được để mở rộng bảng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
