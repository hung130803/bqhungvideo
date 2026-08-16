# -*- coding: utf-8 -*-
"""CHE OAN TRÊN NGUỒN CAMERA CỐ ĐỊNH — dò được "nguồn tĩnh" hay không?

VẤN ĐỀ (đã đo, ghi ở `che_chu.py`): cửa tách CHỮ khỏi NỀN mạnh nhất của bước
quét CẢ KHUNG là **GIAO NHAU THEO THỜI GIAN** (`_loc_thoi_gian`): giữ điểm ảnh
còn BẬT ở khung liền trước HOẶC liền sau. Nó dựa trên một giả định:
*"phụ đề đứng yên, còn NỀN thì TRÔI"*.

Camera đứng yên thì giả định đó **SAI HOÀN TOÀN** — nền cũng đứng yên từng
điểm ảnh, nên nó sống sót y như chữ. Hậu quả đo được trên `jp_tuyet`: 4 vùng
dò ra thì 2 sai, bôi gần hết khung. Hiện chữa bằng cách để quét-cả-khung
**mặc định TẮT**.

Ý TƯỞNG ĐO Ở ĐÂY — **TỰ CHẤM ĐIỂM CHÍNH CÁI CỬA ĐÓ**: nếu `_loc_thoi_gian`
gần như KHÔNG BỎ ĐI GÌ thì nó đang không lọc được gì cả, và mọi kết luận sau
nó đều không đáng tin. Thước:

    ty_giu = (số điểm ảnh mặt nạ CÒN LẠI sau lọc) / (số điểm ảnh mặt nạ TRƯỚC lọc)

  · nền TRÔI  -> nền bị giết nhiều  -> `ty_giu` THẤP
  · nền TĨNH  -> gần như giữ nguyên -> `ty_giu` ~ 1,0

**GIÁ BẰNG 0**: cả `mns` (trước lọc) lẫn `gia` (sau lọc) đều đã được
`do_vung_chu` tính sẵn — chỉ thêm hai phép `.sum()`. KHÔNG thêm một lượt giải
mã hay một lệnh ffmpeg nào.

Đo thêm `dong_khung` = mức đổi TRUNG BÌNH giữa hai khung liền nhau (trên chính
mặt nạ đã có) để đối chiếu — hai thước độc lập nói cùng một chuyện thì mới tin.

CÁCH ĐỌC KẾT QUẢ: chỉ khi nhóm video CHE OAN tách RỜI khỏi nhóm video tốt thì
mới có ngưỡng để dùng. Chồng lấn -> **GHI NỢ, KHÔNG ĐẶT NGƯỠNG MÒ**.

  .venv\\Scripts\\python -u _do_nguon_tinh.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

import numpy as np                                        # noqa: E402
from app.core import che_chu as C                         # noqa: E402

NHIN = Path(r"D:\claude\_che_toan_khung")
NGUON = Path(r"D:\claude\_do_che_chu\nguon")

#: (nhãn, đường dẫn, số VÙNG CHỮ THẬT — ghi bằng mắt, lấy từ `_do_toan_khung.py`)
BO = [
    ("jp_taxi", NHIN / "nguon/jp_taxi.mp4", 2),
    ("jp_tuyet", NHIN / "nguon/jp_tuyet.mp4", 2),
    ("jp_art", NHIN / "nguon/jp_art.mp4", 2),
    ("zh_phim", NHIN / "nguon/zh_phim.mp4", 1),
    ("zh_ep12", NGUON / "zh_ep12.mp4", 1),
    ("zh_dongho", NGUON / "zh_dongho.mp4", 1),
    ("dy1", NGUON / "dy1.mp4", 1),
    ("dy2", NGUON / "dy2.mp4", 1),
    ("dy3", NGUON / "dy3.mp4", 1),
    ("en_bus", NGUON / "en_bus.mp4", 0),
    ("en_d5", NGUON / "en_d5.mp4", 0),
]


def do_mot(p: Path) -> dict:
    """`ty_giu` + `dong_khung` — dùng ĐÚNG các hàm `do_vung_chu` đang dùng."""
    goi, w, h = C._doc_dong(p, C.VUNG_FPS, C.VUNG_RONG)
    if goi is None:
        return {}
    n = goi.shape[0]
    mns = C._mo_goi(goi, 0, n, h, w)
    truoc = float(mns.sum())
    gia = C._loc_thoi_gian(mns)
    sau = float(gia.sum())
    # mức đổi giữa 2 khung liền nhau, trên CHÍNH mặt nạ (thước thứ hai, độc lập)
    dong = float(np.abs(mns[1:].astype(np.int8)
                        - mns[:-1].astype(np.int8)).mean())
    return {
        "khung": n,
        "ty_giu": round(sau / max(1.0, truoc), 4),
        "dong_khung": round(dong, 4),
        "md_truoc": round(truoc / max(1.0, mns.size), 4),
    }


def main() -> int:
    print("=" * 78)
    print("DÒ NGUỒN TĨNH — cửa GIAO NHAU THEO THỜI GIAN có còn tác dụng không?")
    print("  ty_giu ~ 1,0  = lọc KHÔNG bỏ đi gì  = nền cũng đứng yên = NGUỒN TĨNH")
    print("=" * 78)
    print(f"  {'video':12s} {'thật':>4s} {'dò':>3s} {'oan':>4s} | "
          f"{'ty_giu':>7s} {'dong_khung':>11s} {'md_truoc':>9s} | {'giây':>5s}")
    ra = []
    for nhan, p, that in BO:
        if not Path(p).exists():
            print(f"  {nhan:12s} THIẾU FILE")
            continue
        t0 = time.perf_counter()
        d = do_mot(Path(p))
        if not d:
            print(f"  {nhan:12s} KHÔNG đọc được")
            continue
        vs = C.do_vung_chu(p)
        gi = time.perf_counter() - t0
        oan = max(0, len(vs) - that)
        d.update({"nhan": nhan, "that": that, "do": len(vs), "oan": oan})
        ra.append(d)
        print(f"  {nhan:12s} {that:4d} {len(vs):3d} {oan:4d} | "
              f"{d['ty_giu']:7.4f} {d['dong_khung']:11.4f} "
              f"{d['md_truoc']:9.4f} | {gi:5.1f}")

    xau = [d for d in ra if d["oan"] > 0]
    tot = [d for d in ra if d["oan"] == 0]
    print()
    print("=" * 78)
    print(f"  NHÓM CHE OAN ({len(xau)} video): "
          + ", ".join(f"{d['nhan']}({d['oan']})" for d in xau))
    print(f"  NHÓM SẠCH    ({len(tot)} video): "
          + ", ".join(d["nhan"] for d in tot))
    if xau and tot:
        for khoa in ("ty_giu", "dong_khung"):
            a = [d[khoa] for d in xau]
            b = [d[khoa] for d in tot]
            print(f"\n  {khoa}:")
            print(f"    che oan : {min(a):.4f} .. {max(a):.4f}")
            print(f"    sạch    : {min(b):.4f} .. {max(b):.4f}")
            tach = (min(a) > max(b)) or (max(a) < min(b))
            print(f"    -> {'TÁCH RỜI (có ngưỡng dùng được)' if tach else 'CHỒNG LẤN — KHÔNG có ngưỡng, GHI NỢ'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
