# -*- coding: utf-8 -*-
"""GỘP BẢNG MẤT TIẾNG — TRƯỚC / SAU, giây-theo-giây (19/08/2026).

Đọc kết quả của `_do_mat_giong.py` (đo lại chính file anh Hùng đang có) và
của `_do_bang_sau.py` (ghép cặp TẮT/BẬT trong một lượt) rồi in ra MỘT bảng.

**BA CỘT, BA CÂU HỎI KHÁC NHAU — đọc gộp là kết luận sai:**
  · `HÙNG`  = file đang nằm trong `Downloads\\longtieng\\xuất`. Chú ý: mấy
    file này đã bị GHI ĐÈ lúc 12:52-12:59 ngày 19/08 bằng bản `.exe` v2.38.0
    (dựng 10:58 cùng ngày) — **v2.38.0 ĐÃ CHỨA bản vá** (`git merge-base
    --is-ancestor 4d738e8 460a896` -> đúng). Nên cột này KHÔNG còn là "bảng
    TRƯỚC"; bảng TRƯỚC 82,35 s đo trên bản xuất CŨ, nay không còn trên đĩa.
  · `TẮT`   = ĐỐI CHỨNG THẬT của bảng TRƯỚC: cùng lượt chạy, chỉ bỏ mảnh bù.
  · `BẬT`   = đường thật hôm nay.
Chỉ `TẮT -> BẬT` là phép so có ý nghĩa; `HÙNG` để đối chiếu thực địa.

Chạy: .venv\\Scripts\\python -u _ra_bang_mat_tieng.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass


def doc(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                       # noqa: BLE001
        return None


def bac(L: float) -> str:
    return ("<0,5s" if L < 0.5 else "0,5-1s" if L < 1.0
            else "1-2s" if L < 2.0 else ">=2s")


def main() -> int:
    l1 = doc(REPO / "_kq_mat_giong_L1.json") or []
    l2 = doc(REPO / "_kq_mat_giong_L2.json") or []
    sau: dict = {}
    for hau in ("", "_v2", "_v3", "_v4"):
        d = doc(REPO / f"_kq_bang_sau{hau}.json") or {}
        for k, v in d.items():
            if v.get("ok"):
                sau[k] = v

    print("=" * 78)
    print("LẶP LẠI CỦA CHÍNH THƯỚC (cùng file, hai lượt Demucs độc lập)")
    print("=" * 78)
    ta = tb = tv = 0.0
    for x, y in zip(l1, l2):
        ta += x["giay_mat"]
        tb += y["giay_mat"]
        tv += x["dai_goc"]
        print(f"  {x['ten'][:24]:<26}{x['giay_mat']:>8.2f}s{y['giay_mat']:>9.2f}s"
              f"{y['giay_mat'] - x['giay_mat']:>+8.2f}s")
    if tv:
        print(f"  {'TỔNG':<26}{ta:>8.2f}s{tb:>9.2f}s{tb - ta:>+8.2f}s"
              f"   ({100 * ta / tv:.2f}% vs {100 * tb / tv:.2f}%)")
        print(f"  => thước lệch {abs(tb - ta):.2f}s trên {tv:.0f}s "
              f"= {100 * abs(tb - ta) / tv:.2f}% — KHÔNG phải nguồn của "
              f"chênh lệch 82,35 -> 45,6")

    print()
    print("=" * 78)
    print("BẢNG MẤT TIẾNG — GHÉP CẶP TRONG MỘT LƯỢT CHẠY")
    print("=" * 78)
    print(f"  {'video':<26}{'dài':>8}{'HÙNG':>9}{'TẮT':>9}{'BẬT':>9}"
          f"{'bù':>6}{'giây bù':>9}")
    t = {"HUNG": 0.0, "TAT": 0.0, "BAT": 0.0}
    tvs = 0.0
    for k in sorted(sau, key=int):
        v = sau[k]
        tvs += v["dai"]
        c = []
        for n in ("HUNG", "TAT", "BAT"):
            g = (v["do"].get(n) or {}).get("giay_mat")
            c.append(f"{g:>8.2f}s" if g is not None else f"{'—':>9}")
            if g is not None:
                t[n] += g
        bg = v.get("bu_goc") or {}
        print(f"  {v['ten'][:24]:<26}{v['dai']:>7.1f}s{''.join(c)}"
              f"{bg.get('so_bu', 0):>6}{bg.get('giay_bu', 0):>8.2f}s")
    if tvs:
        print(f"  {'TỔNG':<26}{tvs:>7.1f}s{t['HUNG']:>8.2f}s{t['TAT']:>8.2f}s"
              f"{t['BAT']:>8.2f}s")
        print(f"  {'% thời lượng':<26}{'':>8}{100 * t['HUNG'] / tvs:>8.2f}%"
              f"{100 * t['TAT'] / tvs:>8.2f}%{100 * t['BAT'] / tvs:>8.2f}%")
        gi = t["TAT"] - t["BAT"]
        print(f"\n  GHÉP CẶP: TẮT {t['TAT']:.2f}s -> BẬT {t['BAT']:.2f}s  "
              f"= giảm {gi:.2f}s ({100 * gi / max(1e-9, t['TAT']):.1f}%)")

    print()
    print("=" * 78)
    print("GIÂY-THEO-GIÂY — mốc nào mất tiếng, dài bao nhiêu")
    print("=" * 78)
    for k in sorted(sau, key=int):
        v = sau[k]
        print(f"\n  ── {v['ten'][:56]}  ({v['dai']:.1f}s) ──")
        for n, nhan in (("TAT", "TẮT (đối chứng: bản vá bị gỡ)"),
                        ("BAT", "BẬT (đường thật hôm nay)"),
                        ("HUNG", "file anh Hùng đang có")):
            d = v["do"].get(n) or {}
            kh = d.get("khoang") or []
            print(f"    {nhan:<34} {d.get('giay_mat', 0):>6.2f}s / "
                  f"{len(kh)} khoảng")
            for a, b in kh[:40]:
                print(f"       {a:8.2f} -> {b:8.2f}   ({b - a:5.2f}s)")
            if len(kh) > 40:
                print(f"       … còn {len(kh) - 40} khoảng")

    # phân bố độ dài khoảng — trả lời "mất TỪNG MẢNH NHỎ hay MẤT CẢ CÂU"
    print()
    print("=" * 78)
    print("PHÂN BỐ ĐỘ DÀI KHOẢNG MẤT (giây)")
    print("=" * 78)
    print(f"  {'nguồn':<28}{'<0,5s':>9}{'0,5-1s':>9}{'1-2s':>9}{'>=2s':>9}"
          f"{'tổng':>9}")
    nguon: list[tuple[str, list]] = [
        ("file anh Hùng đang có (L1)",
         [kh for x in l1 for kh in x["khoang"]]),
    ]
    for n, nhan in (("TAT", "ghép cặp — TẮT"), ("BAT", "ghép cặp — BẬT")):
        nguon.append((nhan, [kh for v in sau.values()
                             for kh in ((v["do"].get(n) or {}).get("khoang")
                                        or [])]))
    for nhan, khs in nguon:
        b = {"<0,5s": 0.0, "0,5-1s": 0.0, "1-2s": 0.0, ">=2s": 0.0}
        for a, z in khs:
            b[bac(z - a)] += z - a
        print(f"  {nhan:<28}{b['<0,5s']:>8.2f}s{b['0,5-1s']:>8.2f}s"
              f"{b['1-2s']:>8.2f}s{b['>=2s']:>8.2f}s{sum(b.values()):>8.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
