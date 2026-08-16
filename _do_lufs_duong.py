# -*- coding: utf-8 -*-
"""ĐO ĐỘ TO **TỪNG ĐƯỜNG XUẤT** — không chỉ đường thay tiếng.

Anh Hùng nói *"tool cắt sao phần giọng nói ít tiếng quá"*. Đường thay tiếng đã
chữa (xem `chuan_do_to`), nhưng phải rà CẢ các đường còn lại rồi mới được nói
là xong: **cắt thường · ghép nhiều đoạn (mixed-cut) · recap (có lồng tiếng +
nhạc nền)**.

Chạy ffmpeg THẬT trên video THẬT của anh Hùng, đo bằng đúng thước của
`_do_lufs.py` (hai phép đo độc lập).

**KHÔNG kết luận từ mã nguồn** — `grep loudnorm` ra 0 dòng chỉ nói lên "không
có bước chuẩn hoá", nó KHÔNG nói lên clip ra to hay nhỏ: đường cắt chép tiếng
GỐC nên độ to của nó là độ to của NGUỒN, mà nguồn thì mỗi kênh một kiểu.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_lufs import do_ebur128, do_loudnorm  # noqa: E402

DICH = -14.0


def _nguon() -> list[tuple[str, Path]]:
    """Video THẬT trên máy — mỗi cái một kiểu master khác nhau."""
    dl = Path.home() / "Downloads"
    ra = []
    lt = dl / "longtieng" / "近期热播的7部新片推荐。 #电影推荐 #新片速递.mp4"
    if lt.exists():
        ra.append(("Douyin (nguồn anh Hùng đang làm)", lt))
    vd = dl / "Video"
    for ten in ("GOING BACK TO OUR OLD HOUSE.mp4",
                "DaddyOFive.mp4",
                "Kid BREAKS his leg prank.mp4"):
        p = vd / ten
        if p.exists():
            ra.append((ten[:38], p))
    return ra


def main() -> int:
    from app.core import ffmpeg_utils as fu

    tam = REPO / "_do_duong"
    tam.mkdir(exist_ok=True)
    ra: list[dict] = []

    for nhan, src in _nguon():
        print(f"\n=== NGUỒN: {nhan} ===", flush=True)
        g = do_loudnorm(src)
        print(f"  nguồn        I {g['input_i']:+7.2f} · TP {g['input_tp']:+6.2f}"
              f" · LRA {g['input_lra']:5.2f}")
        ra.append({"duong": "NGUỒN", "nhan": nhan, **{
            k: round(v, 2) for k, v in g.items()}})

        # ---- ĐƯỜNG 1: CẮT THƯỜNG (export_canvas_clip, 1 đoạn, không nhạc) ----
        d1 = tam / f"cat_{abs(hash(nhan)) % 9999}.mp4"
        try:
            fu.export_canvas_clip(src, d1, [(10.0, 25.0)], (0.5, 0.5, 1.0),
                                  out_w=540, out_h=960)
            if d1.exists() and d1.stat().st_size > 1024:
                d = do_loudnorm(d1)
                e = do_ebur128(d1)
                print(f"  cắt thường   I {d['input_i']:+7.2f} · "
                      f"TP {d['input_tp']:+6.2f} · LRA {d['input_lra']:5.2f}"
                      f"   (lệch nguồn {d['input_i'] - g['input_i']:+.2f} LU)")
                ra.append({"duong": "cắt thường", "nhan": nhan,
                           **{k: round(v, 2) for k, v in d.items()},
                           "eb_I": e["I"]})
        except Exception as ex:  # noqa: BLE001
            print(f"  cắt thường   LỖI: {ex}")

        # ---- ĐƯỜNG 2: GHÉP NHIỀU ĐOẠN (mixed-cut) ----
        d2 = tam / f"ghep_{abs(hash(nhan)) % 9999}.mp4"
        try:
            fu.export_canvas_clip(src, d2, [(10.0, 18.0), (30.0, 38.0)],
                                  (0.5, 0.5, 1.0), out_w=540, out_h=960)
            if d2.exists() and d2.stat().st_size > 1024:
                d = do_loudnorm(d2)
                print(f"  ghép 2 đoạn  I {d['input_i']:+7.2f} · "
                      f"TP {d['input_tp']:+6.2f} · LRA {d['input_lra']:5.2f}"
                      f"   (lệch nguồn {d['input_i'] - g['input_i']:+.2f} LU)")
                ra.append({"duong": "ghép 2 đoạn", "nhan": nhan,
                           **{k: round(v, 2) for k, v in d.items()}})
        except Exception as ex:  # noqa: BLE001
            print(f"  ghép 2 đoạn  LỖI: {ex}")

    print("\n" + "=" * 78)
    print(f"{'đường':14} {'nguồn':40} {'I':>8} {'TP':>7} {'LRA':>6}")
    print("=" * 78)
    for r in ra:
        co = "" if r["input_i"] >= -16.0 else "  <-- NHỎ"
        print(f"{r['duong']:14} {r['nhan'][:40]:40} {r['input_i']:8.2f} "
              f"{r['input_tp']:7.2f} {r['input_lra']:6.2f}{co}")
    print(f"\nĐÍCH mạng xã hội: I {DICH:.1f} LUFS · TP -1,0 dBTP")

    (REPO / "_kq_lufs_duong.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Ghi: {REPO / '_kq_lufs_duong.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
