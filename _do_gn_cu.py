# -*- coding: utf-8 -*-
r"""PHÉP THỬ QUYẾT ĐỊNH: hai đường lấy mốc trên **ĐÚNG MỘT BỘ FILE TIẾNG**.

VÌ SAO PHẢI CÓ FILE NÀY. `_do_gn_gh.py` đã so hai đường trên cùng audio,
nhưng audio đó do lượt chạy HÔM NAY sinh ra và OmniVoice **KHÔNG TIỀN ĐỊNH**:
cùng câu, cùng mã, lượt này đọc rõ lượt kia đọc ngọng. Đo được ngay trong
lượt này: PHỦ của đường Groq trên tiếng Việt ra **41,8% · 61,4%** với bộ WAV
cũ (`_do_gn_san`, lượt trước sinh) nhưng **99,4%** với bộ WAV mới — cùng một
hàm `_lay_moc_groq`, cùng một corpus.

Tức con số PHỦ 34-56% đã ghi trong nhãn KHÔNG phải hằng số của đường Groq:
nó là hằng số của **một mẻ tiếng đọc kém**. Muốn biết gióng hàng có chữa được
bệnh không thì phải cho nó ĐÚNG mẻ tiếng đó, chứ không phải một mẻ mới may
mắn hơn. Đây cũng là cách duy nhất bỏ hẳn nhiễu "lượt này model đọc rõ hơn".

    .venv\Scripts\python -u _do_gn_cu.py
    BQ_SAN=_do_gn_san BQ_LUOT_SAN=l0,l1 .venv\Scripts\python -u _do_gn_cu.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import os
import statistics
import sys
import time
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

SAN = REPO / os.environ.get("BQ_SAN", "_do_gn_san")
LUOTS = [x for x in os.environ.get("BQ_LUOT_SAN", "l0,l1").split(",") if x]
NN = [x for x in os.environ.get("BQ_NN", "vi,en,zh,ja").split(",") if x]
RA = REPO / os.environ.get("BQ_RA", "_do_gn_cu.json")


def main() -> int:
    from app.core import giong_hang as gh
    if not gh.co_giong_hang():
        print("KHÔNG có bộ gióng hàng -> đo vô nghĩa. Dừng.")
        return 2
    if not SAN.is_dir():
        print(f"Chưa có hộp cát {SAN.name}. Dừng.")
        return 2

    kho: dict = {}
    giay: dict = {}
    for luot in LUOTS:
        for nn in NN:
            d = SAN / f"{luot}_{nn}_OV"
            if not d.is_dir():
                continue
            texts = M.nap_cau(nn)
            paths = [str(d / f"c{i:03d}.wav") for i in range(len(texts))]
            ok = [Path(p).exists() for p in paths]
            if not any(ok):
                continue
            print(f"  {luot} · {M.NHAN_NN.get(nn, nn)} "
                  f"({sum(1 for x in ok if x)}/{len(texts)} wav)…")
            # XOAY THỨ TỰ hai đường theo lượt (cột GIÂY mới công bằng)
            doi = (["GROQ", "GH"] if (LUOTS.index(luot) + NN.index(nn)) % 2 == 0
                   else ["GH", "GROQ"])
            m: dict = {}
            for x in doi:
                t0 = time.time()
                if x == "GROQ":
                    m["OV_GROQ"] = G.moc_groq(texts, paths, ok)
                else:
                    m["OV_GH"] = G.moc_gh(texts, paths, ok, nn)
                giay.setdefault("OV_" + x, []).append(round(time.time() - t0, 2))
            for a in ("OV_GROQ", "OV_GH"):
                r = G.cham(texts, paths, ok, m[a])
                d0 = kho.setdefault(nn, {}).setdefault(
                    a, {"phu": [], "n_moc": 0, "n_tu": 0, "cau": 0,
                        "dau_dung": 0, "tho": [], "sach": []})
                for k in ("phu", "tho", "sach"):
                    d0[k] += r[k]
                for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                    d0[k] += r[k]

    print("\n" + "=" * 80)
    print("HAI ĐƯỜNG LẤY MỐC TRÊN CÙNG MỘT BỘ FILE TIẾNG (thước: "
          "silencedetect)")
    print("=" * 80)
    gop = {a: {"phu": [], "n_moc": 0, "n_tu": 0, "cau": 0, "dau_dung": 0,
               "tho": [], "sach": []} for a in ("OV_GROQ", "OV_GH")}
    for nn in NN:
        if nn not in kho:
            continue
        print(f"\n### {M.NHAN_NN.get(nn, nn).upper()}")
        print(f"    {'arm':<8}{'PHỦ %':>8}{'mốc/chữ':>12}{'đầu đúng':>10}"
              f"{'RUNG thô':>10}{'RUNG sạch':>11}{'muộn>50ms':>11}"
              f"{'hệ thống':>10}")
        for a in ("OV_GROQ", "OV_GH"):
            d = kho[nn][a]
            t, s = G.tk(d["tho"]), G.tk(d["sach"])
            p = statistics.mean(d["phu"]) if d["phu"] else 0.0
            print(f"    {a:<8}{p:>8.1f}{d['n_moc']:>6}/{d['n_tu']:<5}"
                  f"{d['dau_dung']:>6}/{d['cau']:<3}"
                  f"{t.get('rung', 0):>10.1f}{s.get('rung', 0):>11.1f}"
                  f"{t.get('ty_muon', 0):>10.1f}%{t.get('he_thong', 0):>10.1f}")
            for k in ("phu", "tho", "sach"):
                gop[a][k] += d[k]
            for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                gop[a][k] += d[k]

    print("\n### GỘP")
    for a in ("OV_GROQ", "OV_GH"):
        d = gop[a]
        if not d["cau"]:
            continue
        t = G.tk(d["tho"])
        print(f"    {a:<8}PHỦ {statistics.mean(d['phu']):>5.1f}%  "
              f"{d['n_moc']}/{d['n_tu']} mốc  ·  đầu đúng "
              f"{d['dau_dung']}/{d['cau']}  ·  RUNG thô {t.get('rung', 0)} ms")
    print("\n  GIÂY:")
    for k, v in giay.items():
        if v:
            print(f"    {k:<9} TB {sum(v) / len(v):>7.2f}s  ({len(v)} lượt)")

    RA.write_text(json.dumps(
        {"san": str(SAN), "luot": LUOTS, "nn": NN, "giay": giay,
         "tk": {nn: {a: {"phu_tb": (round(statistics.mean(d["phu"]), 1)
                                    if d["phu"] else None),
                         "n_moc": d["n_moc"], "n_tu": d["n_tu"],
                         "cau": d["cau"], "dau_dung": d["dau_dung"],
                         "tho": G.tk(d["tho"]), "sach": G.tk(d["sach"])}
                     for a, d in kho[nn].items()} for nn in kho},
         "gop": {a: {"phu_tb": (round(statistics.mean(d["phu"]), 1)
                                if d["phu"] else None),
                     "n_moc": d["n_moc"], "n_tu": d["n_tu"], "cau": d["cau"],
                     "dau_dung": d["dau_dung"], "tho": G.tk(d["tho"])}
                 for a, d in gop.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
