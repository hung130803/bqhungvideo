# -*- coding: utf-8 -*-
r"""HIỆU CHUẨN TRẦN CHI PHÍ CỦA CỔNG 56 CA 17 (che chữ) — ĐO, KHÔNG ĐOÁN.

VÌ SAO CÓ FILE NÀY: trần CA17 (DẢI 2,0 · HỘP 4,5 s/phút) đặt theo MỘT lượt đo
duy nhất (`+0,84` / `+3,31`), rồi cùng một dòng mã mà số cứ trôi:

  | lượt          | DẢI   | HỘP    |
  |---------------|-------|--------|
  | mốc (14/08)   | +0,84 | +3,31  |
  | 15/08         | +2,57 | +5,46  |
  | 16/08         | —     | +4,60  |
  | lúc máy bận   | —     | +10,66 |

`git diff v2.27.0..HEAD -- app/core/che_chu.py app/core/ffmpeg_utils.py` RỖNG
-> KHÔNG phải hồi quy. Tức trần đặt sai từ đầu: nó là số của MỘT lượt, không
phải số có biên.

CÁCH ĐO (khác CA17 ở đúng 2 điểm, và đó là lý do file này tồn tại):
  · **≥5 VÒNG** thay vì 3 — 3 vòng không đủ để thấy biên độ.
  · **THỨ TỰ XOAY VÒNG mỗi vòng** — CA17 luôn chạy TẮT trước rồi DẢI rồi HỘP,
    nên arm chạy sau luôn gánh phần máy đã nóng. Đây đúng bài học "đo A/B phải
    đan xen" đã cho kết luận NGƯỢC 3 lần trong repo này.
Cùng clip, cùng `segs`, cùng `_RECT` như CA17 để số so được với mốc cũ.

TỰ CANH MÁY RẢNH: CPU nền > `BQ_CPU_MAX` (mặc định 15%) thì **DỪNG**, không đo.
Số đo lúc máy bận đã cho `+10,66` — vô dụng mà trông vẫn như số thật.

  .venv\Scripts\python -u _do_ca17.py
  BQ_VONG=7 .venv\Scripts\python -u _do_ca17.py
"""
from __future__ import annotations

import json
import os
import shutil
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

os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

KHO = Path(r"D:\claude\_do_che_chu\nguon")
SAN = REPO / f"bq_ca17_{os.getpid()}"
RA = REPO / "_do_ca17.json"

SO_VONG = int(os.environ.get("BQ_VONG", "5"))
CPU_MAX = float(os.environ.get("BQ_CPU_MAX", "15"))

_RECT = (0.5, 0.5, 1.0)            # y hệt CA17
_OUT_W, _OUT_H = 1080, 1920
GIAY = 60.0
SEGS = [(30.0, 30.0 + GIAY)]


def cpu_nen() -> float:
    import psutil
    return max(psutil.cpu_percent(interval=1.0) for _ in range(3))


def _xuat(src: Path, dst: Path, che: bool, cach: str = "mo") -> float:
    """Gọi ĐÚNG `export_canvas_clip` của app — y hệt `_xuat` của cổng 56."""
    from app.core import ffmpeg_utils as fu
    k = {}
    if che:
        k = dict(che_chu=True, che_chu_cach=cach, che_chu_muc=1.0,
                 che_chu_log=None)
    t0 = time.perf_counter()
    fu.export_canvas_clip(
        str(src), str(dst), SEGS, _RECT, bg="blur",
        out_w=_OUT_W, out_h=_OUT_H, fx_fade=False, fx_whoosh=False,
        hieu_ung="tat", chuyen_canh="tat", **k)
    t = time.perf_counter() - t0
    try:
        dst.unlink()
    except OSError:
        pass
    return t


def do_mot(ten: str, src: Path, i: int) -> float:
    from app.core import che_chu as C
    if ten == "TẮT":
        return _xuat(src, SAN / f"tat{i}.mp4", False)
    # PHẢI xoá sổ nhớ khi ĐỔI CHẾ ĐỘ: lượt sau đọc lại bản dò của lượt trước
    # là đo nhầm (bẫy CA17 đã ghi). Rồi HÂM NÓNG để chỉ đo CHUỖI FILTER.
    C._DAI_NHO.clear()
    C._DAI_KHOA.clear()
    C._BAT_HOP = (ten == "HỘP")
    C.dai_theo_video(src)
    return _xuat(src, SAN / f"{ten[:1]}{i}.mp4", True)


def main() -> int:
    src = None
    for ten in ("zh_ep12.mp4", "zh_dongho.mp4"):
        if (KHO / ten).exists():
            src = KHO / ten
            break
    if src is None:
        print("KHÔNG có video nguồn — bỏ qua.")
        return 2

    c = cpu_nen()
    print("=" * 74)
    print(f"HIỆU CHUẨN CA17 — {src.name} · clip {GIAY:.0f}s · {SO_VONG} vòng "
          f"ĐAN XEN (thứ tự XOAY)")
    print(f"CPU nền trước khi đo: {c:.1f}%  (trần {CPU_MAX:.0f}%)")
    print("=" * 74)
    if c > CPU_MAX:
        print(f"MÁY BẬN ({c:.1f}% > {CPU_MAX:.0f}%) -> DỪNG, không đo.")
        print("Số đo lúc máy bận đã cho +10,66 s/phút — vô dụng mà trông như thật.")
        return 3

    SAN.mkdir(parents=True, exist_ok=True)
    from app.core import che_chu as C
    cu_hop = C._BAT_HOP
    ARM = ["TẮT", "DẢI", "HỘP"]
    tho: dict[str, list[float]] = {a: [] for a in ARM}
    try:
        for v in range(SO_VONG):
            thu_tu = ARM[v % 3:] + ARM[:v % 3]          # XOAY thứ tự mỗi vòng
            dong = []
            for ten in thu_tu:
                t = do_mot(ten, src, v)
                tho[ten].append(t)
                dong.append(f"{ten} {t:.2f}s")
            print(f"  vòng {v + 1}  ({' -> '.join(thu_tu)}):  "
                  + " · ".join(dong))
            sys.stdout.flush()
    finally:
        C._BAT_HOP = cu_hop
        shutil.rmtree(SAN, ignore_errors=True)

    c2 = cpu_nen()
    tv = lambda xs: sorted(xs)[len(xs) // 2]             # noqa: E731
    ph = GIAY / 60.0
    m = {a: tv(tho[a]) for a in ARM}
    them = {a: (m[a] - m["TẮT"]) / ph for a in ("DẢI", "HỘP")}

    print()
    print("=" * 74)
    print(f"KẾT QUẢ — trung vị {SO_VONG} vòng · CPU nền sau khi đo {c2:.1f}%")
    print("=" * 74)
    print(f"{'arm':<6}|{'trung vị':>10} |{'nhỏ nhất':>10} |{'lớn nhất':>10} "
          f"|{'biên độ':>9}")
    print("-" * 54)
    for a in ARM:
        xs = tho[a]
        print(f"{a:<6}|{tv(xs):>9.2f}s |{min(xs):>9.2f}s |{max(xs):>9.2f}s "
              f"|{max(xs) - min(xs):>8.2f}s")
    print()
    print(f"  DẢI thêm : {them['DẢI']:+.2f} giây/phút phim")
    print(f"  HỘP thêm : {them['HỘP']:+.2f} giây/phút phim")
    print(f"  HỘP − DẢI: {them['HỘP'] - them['DẢI']:+.2f} giây/phút phim")
    print()
    # Biên an toàn: lấy trần theo LỚN NHẤT (không phải trung vị) rồi cộng 25%.
    # Trần cũ đặt theo TRUNG VỊ CỦA MỘT LƯỢT nên hết biên ngay lượt sau.
    for a in ("DẢI", "HỘP"):
        xau = (max(tho[a]) - m["TẮT"]) / ph
        print(f"  gợi ý trần {a}: max({xau:+.2f}) × 1,25 = "
              f"**{xau * 1.25:.2f}** s/phút")
    d_max = (max(tho["HỘP"]) - m["TẮT"]) / ph - (min(tho["DẢI"]) - m["TẮT"]) / ph
    print(f"  gợi ý trần HỘP−DẢI: {d_max:+.2f} × 1,25 = **{d_max * 1.25:.2f}**")

    RA.write_text(json.dumps(
        {"nguon": src.name, "so_vong": SO_VONG, "cpu_truoc": c, "cpu_sau": c2,
         "tho": tho, "trung_vi": m, "them": them}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nGhi: {RA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
