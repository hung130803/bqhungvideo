"""ĐO NHẤN NHÁ **MỌI GIỌNG edge-tts CÓ BỘ CÂU ĐÚNG TIẾNG**.

``_do_nhan_nha_bang.py`` đo "danh sách gọn" (giọng ⭐ hot + toàn bộ ``en-``).
File này đi tiếp phần còn lại: **109 giọng của 14 thứ tiếng khác** mà app đang
giấu khỏi danh sách gọn, và giấu **không vì lý do nào ngoài việc chưa ai đo**.

**CHỈ ĐO NGÔN NGỮ CÓ BỘ CÂU RIÊNG trong ``_do_nhan_nha_bang.CAU``.** edge-tts
có 322 giọng / 75 thứ tiếng; 60 thứ tiếng còn lại (137 giọng) **KHÔNG đo** vì
``cau_cho()`` sẽ cho chúng đọc câu TIẾNG ANH — đúng cái bẫy docstring của
``_do_nhan_nha_bang`` đã dặn ("bắt giọng Nhật đọc câu tiếng Việt là đo một thứ
khác hẳn"). Số đo được trong ca đó trông y hệt một kết luận thật; thà để trống.

**DÙNG LẠI NGUYÊN XI ``do_mot``** của ``_do_nhan_nha_bang`` -> cùng cửa
(``dubbing._synth_all``), cùng thước (``_do_nhan_nha.f0_nua_cung``), cùng bộ
câu. Không có thước thứ hai nào trong file này.

Kết quả ghi dồn vào **CÙNG một ``ket_qua.json``** với lượt trước nên chạy lại
không đo lại từ đầu, và bảng in ra là bảng của cả hai lượt.

Chạy: .venv\\Scripts\\python -u _do_nhan_nha_het.py [--in-bang]
      --in-bang: in ra đúng dạng dòng để dán vào ``nhan_nha.BANG``.
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "_lib_giong"))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

KHO = REPO / "_kq_edge_voices.json"


def danh_sach() -> list[str]:
    """Giọng CHƯA có trong bảng, thuộc ngôn ngữ CÓ bộ câu riêng."""
    from _do_nhan_nha_bang import CAU
    from app.core import nhan_nha

    v = json.loads(KHO.read_text(encoding="utf-8"))
    ra = [x["ShortName"] for x in v
          if x["Locale"].split("-")[0] in CAU
          and x["ShortName"] not in nhan_nha.BANG]
    return sorted(set(ra))


def main() -> int:
    from _do_nhan_nha_bang import SAN, do_mot

    SAN.mkdir(exist_ok=True)
    ds = danh_sach()
    kq = SAN / "ket_qua.json"
    ra: dict = {}
    if kq.exists():
        try:
            ra = json.loads(kq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra = {}
    print(f"ĐO NHẤN NHÁ {len(ds)} GIỌNG CÒN LẠI (cửa dubbing._synth_all)")
    print("-" * 74)
    t0 = time.monotonic()
    for i, v in enumerate(ds, 1):
        if v in ra and not ra[v].get("loi"):
            d = ra[v]
        else:
            d = do_mot(v)
            ra[v] = d
            kq.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        if d.get("loi"):
            print(f"{i:3d}/{len(ds)} {v:34s} LỖI: {d['loi']}", flush=True)
        else:
            print(f"{i:3d}/{len(ds)} {v:34s} {d['nhan_nha']:6.2f} "
                  f"{d['f0_giua_hz']:7.1f}Hz {d['so_khung']:5d} khung",
                  flush=True)
    tot = {k: x["nhan_nha"] for k, x in ra.items()
           if k in set(ds) and not x.get("loi")}
    print("-" * 74)
    print(f"ĐO ĐƯỢC {len(tot)}/{len(ds)} · {time.monotonic()-t0:.0f} giây")
    if tot:
        xs = sorted(tot.values())
        print(f"thấp nhất {xs[0]:.2f} · cao nhất {xs[-1]:.2f} · "
              f"TRẢI {xs[-1]-xs[0]:.2f} · trung vị {st.median(xs):.2f}")
        top = sorted(tot.items(), key=lambda kv: -kv[1])[:10]
        print("CAO NHẤT: " + " · ".join(f"{k} {x:.2f}" for k, x in top))
    if "--in-bang" in sys.argv:
        print("\n--- dán vào nhan_nha.BANG ---")
        for k, x in sorted(tot.items(), key=lambda kv: -kv[1]):
            print(f'    "{k}": {x:.2f},')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
