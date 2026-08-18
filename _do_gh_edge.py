# -*- coding: utf-8 -*-
r"""GIÓNG HÀNG vs `WordBoundary` — TRÊN CÙNG MỘT FILE TIẾNG edge-tts.

**ĐO ĐỂ BÁO SỐ, KHÔNG ĐỂ ĐỔI GÌ.** Mốc của edge-tts đang chạy sản xuất cho
200-300 kênh của anh Hùng; đổi cách lấy mốc của nó là đụng phụ đề của toàn bộ
số kênh đó. File này chỉ trả lời một câu: *nếu đổi thì số sẽ ra sao* — quyết
định là của anh Hùng.

VÌ SAO PHẢI ĐO RIÊNG. `_do_gn_gh.py` so gióng hàng (trên tiếng OmniVoice) với
edge-tts (trên tiếng edge-tts) — **hai file tiếng khác nhau**, nên chênh lệch
lẫn cả "model nào đọc rõ hơn". Ở đây cả hai bộ mốc lấy trên **ĐÚNG MỘT FILE**,
khác nhau đúng ở phép lấy mốc:

  WB   `WordBoundary` — mốc THẬT do chính máy đọc trả về (đang dùng).
  GH   gióng hàng cưỡng bức chạy trên chính file WAV đó.

Thước: `silencedetect` (không máy nghe nào) — mốc chữ ĐẦU so với lúc file
thật sự phát ra tiếng.

    .venv\Scripts\python -u _do_gh_edge.py
"""
from __future__ import annotations

import asyncio
import importlib.util as _u
import json
import os
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass

_s1 = _u.spec_from_file_location("_m_gn_moc", REPO / "_do_gn_moc.py")
M = _u.module_from_spec(_s1)
_s1.loader.exec_module(M)
_s2 = _u.spec_from_file_location("_m_gn_gh", REPO / "_do_gn_gh.py")
G = _u.module_from_spec(_s2)
_s2.loader.exec_module(G)

SO_LUOT = int(os.environ.get("BQ_LUOT", "2"))
NN = [x for x in os.environ.get("BQ_NN", "vi,en,zh,ja").split(",") if x]
RA = REPO / os.environ.get("BQ_RA", "_do_gh_edge.json")


def main() -> int:
    from app.core import dubbing
    from app.core import giong_hang as gh
    if not gh.co_giong_hang():
        print("KHÔNG có bộ gióng hàng -> đo vô nghĩa. Dừng.")
        return 2

    kho = {nn: {a: {"phu": [], "n_moc": 0, "n_tu": 0, "cau": 0,
                    "dau_dung": 0, "tho": [], "sach": []}
                for a in ("WB", "GH")} for nn in NN}
    san = Path(tempfile.mkdtemp(prefix="bq_ghedge_"))
    try:
        for luot in range(SO_LUOT):
            for nn in NN:
                texts = M.nap_cau(nn)
                d = san / f"l{luot}_{nn}"
                d.mkdir(parents=True, exist_ok=True)
                paths = [str(d / f"c{i:03d}.wav") for i in range(len(texts))]
                print(f"  lượt {luot + 1} · {M.NHAN_NN.get(nn, nn)} "
                      f"({len(texts)} câu)…")
                ok, wb = asyncio.run(dubbing._synth_all_words(
                    texts, M.GIONG_EDGE[nn], paths, lang=nn, el_lui=False))
                ok = list(ok)
                if not any(ok):
                    print("      ! edge-tts không đọc được -> bỏ")
                    continue
                moc = {"WB": list(wb),
                       "GH": gh.giong_hang_loat(paths, texts, nn)}
                for a in ("WB", "GH"):
                    r = G.cham(texts, paths, ok, moc[a])
                    for k in ("phu", "tho", "sach"):
                        kho[nn][a][k] += r[k]
                    for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                        kho[nn][a][k] += r[k]
    finally:
        shutil.rmtree(san, ignore_errors=True)

    print("\n" + "=" * 78)
    print("CÙNG MỘT FILE TIẾNG edge-tts · thước `silencedetect` · ms")
    print("DƯƠNG = mốc MUỘN hơn tiếng · ÂM = mốc SỚM hơn tiếng")
    print("=" * 78)
    gop = {a: {"phu": [], "n_moc": 0, "n_tu": 0, "cau": 0, "dau_dung": 0,
               "tho": [], "sach": []} for a in ("WB", "GH")}
    for nn in NN:
        print(f"\n### {M.NHAN_NN.get(nn, nn).upper()}")
        print(f"    {'arm':<5}{'PHỦ %':>8}{'mốc/chữ':>12}{'lệch HỆ THỐNG':>15}"
              f"{'RUNG':>8}{'rung p90':>10}")
        for a in ("WB", "GH"):
            dd = kho[nn][a]
            if not dd["cau"]:
                continue
            t = G.tk(dd["tho"])
            p = statistics.mean(dd["phu"]) if dd["phu"] else 0.0
            print(f"    {a:<5}{p:>8.1f}{dd['n_moc']:>6}/{dd['n_tu']:<5}"
                  f"{t.get('he_thong', 0):>15.1f}{t.get('rung', 0):>8.1f}"
                  f"{t.get('rung_p90', 0):>10.1f}")
            for k in ("phu", "tho", "sach"):
                gop[a][k] += dd[k]
            for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                gop[a][k] += dd[k]

    print("\n### GỘP 4 THỨ TIẾNG")
    for a in ("WB", "GH"):
        t = G.tk(gop[a]["tho"])
        p = statistics.mean(gop[a]["phu"]) if gop[a]["phu"] else 0.0
        print(f"    {a:<5} PHỦ {p:>5.1f}%  ·  lệch hệ thống "
              f"{t.get('he_thong', 0):>7.1f} ms  ·  RUNG {t.get('rung', 0):>6.1f} ms"
              f"  ·  n={t.get('n', 0)}")
    print("\nĐỌC CHO ĐÚNG: `lệch HỆ THỐNG` trừ được bằng một hằng số, `RUNG` "
          "thì không —\nRUNG mới là chất lượng thật của bộ mốc.")
    print("KHÔNG TỰ ĐỔI GÌ. Mốc edge-tts đang chạy sản xuất 200-300 kênh.")

    RA.write_text(json.dumps(
        {"so_luot": SO_LUOT, "nn": NN,
         "tk": {nn: {a: {"phu_tb": (round(statistics.mean(d["phu"]), 1)
                                    if d["phu"] else None),
                         "n_moc": d["n_moc"], "n_tu": d["n_tu"],
                         "cau": d["cau"], "dau_dung": d["dau_dung"],
                         "tho": G.tk(d["tho"]), "sach": G.tk(d["sach"])}
                     for a, d in kho[nn].items()} for nn in NN},
         "gop": {a: {"phu_tb": (round(statistics.mean(d["phu"]), 1)
                                if d["phu"] else None),
                     "tho": G.tk(d["tho"])} for a, d in gop.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
