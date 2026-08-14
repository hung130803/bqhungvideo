# -*- coding: utf-8 -*-
"""GIÁ của từng MẢNH trong chuỗi che chữ — để biết tiền đi đâu.

Câu hỏi: `+0,81 giây/phút` (đo được) so với `+0,1-0,2` (con số hứa) — phần dư
nằm ở `boxblur` hay ở `split`/`overlay`? Và cách "phủ khối" (một `drawbox`,
KHÔNG split/overlay) rẻ hơn bao nhiêu?

ĐAN XEN + TRUNG VỊ (máy anh Hùng luôn có việc nền).
Chạy: .venv\\Scripts\\python _do_che_chu_gia.py [so_vong]
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_DATA_DIR", r"D:\claude\_do_che_chu\_sandbox")
os.environ.setdefault("BQ_DB_PATH", r"D:\claude\_do_che_chu\_sandbox\studio.db")

import _test_guard  # noqa: E402,F401  chặn cửa sổ ngoài
from app.core import che_chu as C                 # noqa: E402
from app.core import ffmpeg_utils as FU           # noqa: E402

SAN = Path(r"D:\claude\_do_che_chu\_do")
SAN.mkdir(parents=True, exist_ok=True)
SRC = Path(r"D:\claude\_do_che_chu\nguon\zh_ep12.mp4")
RECT = (0.5, 0.5, 1.0)
SEGS = [(30.0, 90.0)]                              # ĐÚNG 60 giây = 1 phút


def xuat(dst: Path, dai, cach="mo", muc=1.0) -> float:
    t = time.perf_counter()
    FU.export_canvas_clip(str(SRC), str(dst), SEGS, RECT, bg="blur",
                          out_w=1080, out_h=1920, fx_fade=False,
                          fx_whoosh=False, hieu_ung="tat", chuyen_canh="tat",
                          che_chu=dai is not None, che_chu_cach=cach,
                          che_chu_muc=muc, che_chu_dai=dai)
    return time.perf_counter() - t


def main() -> int:
    vong = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    d = C.dai_theo_video(SRC)
    print(f"dải: {d.ly_do}")
    # DẢI GIẢ, cao 2 px: giữ nguyên kiến trúc split/crop/boxblur/overlay nhưng
    # phần việc THẬT gần bằng 0 -> tách "giá của KIẾN TRÚC" khỏi "giá của mờ".
    nho = C.DaiChu(co_chu=True, y0=d.y0, y1=d.y0 + 2, x0=d.x0, x1=d.x0 + 2,
                   rong=d.rong, cao=d.cao)
    bo = [("TẮT (đối chứng)", None, "mo", 1.0),
          ("kiến trúc RỖNG (dải 2x2 px)", nho, "mo", 1.0),
          ("phủ KHỐI (drawbox, không split)", d, "khoi", 1.0),
          ("làm mờ mức 0,60 (sàn)", d, "mo", 0.60),
          ("làm mờ mức 1,00 (mặc định)", d, "mo", 1.00),
          ("làm mờ mức 2,00 (trần)", d, "mo", 2.00)]
    so = {ten: [] for ten, *_ in bo}
    for i in range(vong):
        for j, (ten, dd, ca, mu) in enumerate(bo):
            so[ten].append(xuat(SAN / f"g{j}.mp4", dd, ca, mu))
        print(f"  vòng {i+1} xong")
    goc = sorted(so["TẮT (đối chứng)"])[vong // 2]
    print(f"\n{'cách':38s} {'trung vị':>9s} {'thêm/phút':>11s}  thô")
    for ten, *_ in bo:
        tv = sorted(so[ten])[vong // 2]
        print(f"{ten:38s} {tv:8.2f}s {tv-goc:+10.2f}s  "
              f"{[round(x,2) for x in so[ten]]}")
    print(f"\ncửa sổ ngoài bị chặn: {len(_test_guard.DA_CHAN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
