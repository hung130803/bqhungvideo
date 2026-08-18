# -*- coding: utf-8 -*-
r"""ĐO GIÓNG HÀNG CÓ CHỮA ĐƯỢC BỆNH MỐC CỦA OmniVoice KHÔNG — 4 THỨ TIẾNG.

═══════════════════════════════════════════════════════════════════════════
CHỈ MỘT THƯỚC: `silencedetect`. KHÔNG MÁY NGHE NÀO.
═══════════════════════════════════════════════════════════════════════════
Hai bẫy đã sập, ghi lại để đừng sập lần thứ ba:

  · **Đo OmniVoice bằng Groq = so nó với chính nó.** Mốc của nó LẤY TỪ Groq,
    mà Groq tiền định trong hai cú gọi liền nhau -> ra đúng **0,0 ms trên
    1.587 mốc**, một bảng điểm hoàn hảo cho thứ chưa hề được kiểm.
  · **Mọi thước là máy nghe đều thiên vị.** faster-whisper `medium` nói
    OmniVoice (50,6 ms) tốt hơn edge-tts (56,5 ms) — nhưng cột số mốc khớp
    tố giác: **1.466 vs 1.043**. Mốc do máy nghe sinh ra thì khớp với một
    máy nghe khác dễ hơn hẳn mốc lấy từ CHỮ GỐC.

`silencedetect` không nghe chữ, nó chỉ trả lời "giây nào file này thật sự
bắt đầu phát ra tiếng". So mốc chữ ĐẦU với giây đó là phép đo duy nhất mà cả
ba arm đều không có lợi thế sân nhà. Đúng thước thứ ba đã chặn phép trừ sai
94 ms ở cổng 67.

═══════════════════════════════════════════════════════════════════════════
BA ARM — HAI ARM OmniVoice DÙNG **CHUNG MỘT FILE TIẾNG**
═══════════════════════════════════════════════════════════════════════════
  EDGE      edge-tts, mốc `WordBoundary` của chính máy đọc. PHỦ 100% do cấu
            tạo. Arm đối chứng **CHẠY LẠI trên CÙNG corpus** — cổng 67 đã
            chứng minh độ trễ của thước đổi theo GIỌNG và theo NGÔN NGỮ nên
            chép số cũ sang là so hai thứ khác nhau.
  OV_GROQ   OmniVoice + `giong_ngoai._lay_moc_groq` (đường đang chạy).
  OV_GH     **CÙNG file WAV đó** + `dubbing._moc_giong_hang` (cửa chung).

Sinh tiếng MỘT LƯỢT rồi lấy mốc hai đường là chỗ mạnh nhất của phép đo này:
hai arm khác nhau ĐÚNG một thứ là phép lấy mốc, không lẫn nhiễu của model
sinh tiếng (OmniVoice không tiền định).

═══════════════════════════════════════════════════════════════════════════
PHỦ LÀ CỘT QUYẾT ĐỊNH
═══════════════════════════════════════════════════════════════════════════
`_lay_moc_groq` BỎ mọi từ Groq nghe không khớp (cố ý — mốc bịa tệ hơn thiếu
mốc), nên chữ Groq nghe sai là chữ đó KHÔNG CÓ MỐC NÀO. Gióng hàng thì
**không đoán chữ, nó ĐÃ BIẾT chữ** -> phải phủ ~100% do cấu tạo. Không lên
gần 100% thì gióng hàng KHÔNG chữa được bệnh, và phải nói thẳng.

RUNG in ra **HAI CỘT, cố ý**:
  THÔ    mọi câu có mốc, `moc[0]` là gì thì lấy nấy — **so được với 236,0 ms
         đã ghi** (`_do_gn_moc.py` T3 tính đúng kiểu này).
  SẠCH   chỉ câu mà `moc[0]` ĐÚNG LÀ từ đầu câu. Cột THÔ trừng phạt arm nào
         PHỦ thấp hai lần (mất mốc đầu -> `moc[0]` là từ thứ ba -> lệch
         dương rất to), nên cột SẠCH mới là chất lượng thuần của mốc.

    .venv\Scripts\python -u _do_gn_gh.py
    BQ_SO_CAU=12 BQ_LUOT=2 BQ_NN=vi,en,zh,ja .venv\Scripts\python -u _do_gn_gh.py
"""
from __future__ import annotations

import asyncio
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

_sp = _u.spec_from_file_location("_m_gn_moc", REPO / "_do_gn_moc.py")
M = _u.module_from_spec(_sp)
_sp.loader.exec_module(M)                    # nap_cau · _chuan · NHAN_NN …

SO_CAU = int(os.environ.get("BQ_SO_CAU", "12"))
SO_LUOT = int(os.environ.get("BQ_LUOT", "2"))
NN = [x for x in os.environ.get("BQ_NN", "vi,en,zh,ja").split(",") if x]
RA = REPO / os.environ.get("BQ_RA", "_do_gn_gh.json")
GIONG_OV = os.environ.get("BQ_GIONG_OV", "ov:nu_tre")

ARMS = ("EDGE", "OV_GROQ", "OV_GH")
MUON_MS = 50.0                                # "hiện muộn" theo mốc cũ


# ---------------------------------------------------------------------------
# THƯỚC — silencedetect, có nhớ (cùng file WAV thì đo một lần)
# ---------------------------------------------------------------------------
_IM: dict[str, float] = {}


def im_dau(wav: str) -> float:
    """Giây file thật sự bắt đầu phát tiếng. KHÔNG dùng máy nghe nào."""
    if wav not in _IM:
        from app.core import thay_giong as tg
        dau, _cuoi, _t = tg.do_le_im(wav)
        _IM[wav] = float(dau)
    return _IM[wav]


def _tokens(text: str) -> list[str]:
    """Mẫu số của PHỦ. Dùng CHUNG cho cả 3 arm — mỗi arm một cách đếm là
    bảng số vô nghĩa. `recap._word_tokens` là bộ CJK-aware app đang dùng."""
    from app.ai import recap
    return [t for t in recap._word_tokens(text) if M._chuan(t)]


def cham(texts: list[str], paths: list[str], ok: list, moc: list) -> dict:
    """Chấm một arm trên một thứ tiếng. Trả SỐ THÔ để gộp sau."""
    phu: list[float] = []
    n_moc = n_tu = 0
    lech_tho: list[float] = []
    lech_sach: list[float] = []
    dau_dung = cau = 0
    for i, t in enumerate(texts):
        if i >= len(ok) or not ok[i] or not Path(paths[i]).exists():
            continue
        tu = _tokens(t)
        if not tu:
            continue
        m = moc[i] if i < len(moc) else []
        cau += 1
        n_tu += len(tu)
        n_moc += len(m)
        phu.append(100.0 * len(m) / len(tu))
        if not m:
            continue
        try:
            d = im_dau(paths[i])
        except Exception as e:                               # noqa: BLE001
            print(f"      ! silencedetect hỏng câu {i}: {type(e).__name__}: {e}")
            continue
        x = (float(m[0][0]) - d) * 1000.0
        lech_tho.append(x)
        if M._chuan(m[0][2]) == M._chuan(tu[0]):
            dau_dung += 1
            lech_sach.append(x)
    return {"phu": phu, "n_moc": n_moc, "n_tu": n_tu, "cau": cau,
            "dau_dung": dau_dung, "tho": lech_tho, "sach": lech_sach}


def tk(lech: list[float]) -> dict:
    """TÁCH LỆCH HỆ THỐNG KHỎI RUNG — số thô là số lừa (đã sập 3 lần)."""
    if not lech:
        return {"n": 0}
    goc = statistics.median(lech)
    rung = [abs(x - goc) for x in lech]
    return {"n": len(lech),
            "he_thong": round(goc, 1),
            "rung": round(sum(rung) / len(rung), 1),
            "rung_p90": round(sorted(rung)[min(len(rung) - 1,
                                               int(len(rung) * 0.9))], 1),
            "muon": sum(1 for x in lech if x > MUON_MS),
            "ty_muon": round(100.0 * sum(1 for x in lech if x > MUON_MS)
                             / len(lech), 1)}


# ---------------------------------------------------------------------------
# SINH TIẾNG
# ---------------------------------------------------------------------------
def doc_edge(texts: list[str], nn: str, san: Path) -> tuple[list, list, list]:
    """Đi CHÍNH cửa `dubbing._synth_all_words` của app."""
    from app.core import dubbing
    san.mkdir(parents=True, exist_ok=True)
    paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
    ok, words = asyncio.run(dubbing._synth_all_words(
        texts, M.GIONG_EDGE[nn], paths, lang=nn, el_lui=False))
    return list(ok), paths, list(words)


def doc_ov(texts: list[str], nn: str, san: Path) -> tuple[list, list]:
    """Sinh tiếng OmniVoice, **KHÔNG lấy mốc** (`lay_moc=False`).

    Hai arm mốc sẽ dùng chung đúng những file này.
    """
    from app.core import giong_ngoai as gn
    san.mkdir(parents=True, exist_ok=True)
    paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
    ok, _w = gn.doc_loat(texts, paths, GIONG_OV, lang=nn, lay_moc=False)
    return list(ok), paths


def moc_groq(texts: list[str], paths: list[str], ok: list) -> list:
    """Đường ĐANG CHẠY: mỗi câu một lượt Groq chép ngược."""
    from app.core import giong_ngoai as gn
    ra: list[list] = [[] for _ in texts]
    for i, t in enumerate(texts):
        if i >= len(ok) or not ok[i] or not Path(paths[i]).exists():
            continue
        try:
            ra[i] = gn._lay_moc_groq(t, paths[i])
        except Exception as e:                               # noqa: BLE001
            print(f"      ! groq hỏng câu {i}: {type(e).__name__}: {e}")
    return ra


def moc_gh(texts: list[str], paths: list[str], ok: list, nn: str) -> list:
    """Đường MỚI: gọi ĐÚNG cửa chung `dubbing._moc_giong_hang`.

    Không dựng đường riêng cho phép đo — nếu cửa chung có bệnh thì phép đo
    phải nhìn thấy bệnh đó.
    """
    from app.core import dubbing
    return asyncio.run(dubbing._moc_giong_hang(
        texts, paths, ok, [[] for _ in texts], nn, GIONG_OV))


# ---------------------------------------------------------------------------
def in_bang(tieu_de: str, kho: dict) -> None:
    print(f"\n  {tieu_de}")
    print(f"    {'arm':<8}{'PHỦ %':>8}{'mốc/chữ':>12}{'đầu đúng':>10}"
          f"{'RUNG thô':>10}{'RUNG sạch':>11}{'muộn>50ms':>11}{'hệ thống':>10}")
    for a in ARMS:
        d = kho.get(a)
        if not d or not d["cau"]:
            print(f"    {a:<8}   -  (không đo được)")
            continue
        t, s = tk(d["tho"]), tk(d["sach"])
        p = statistics.mean(d["phu"]) if d["phu"] else 0.0
        print(f"    {a:<8}{p:>8.1f}{d['n_moc']:>6}/{d['n_tu']:<5}"
              f"{d['dau_dung']:>6}/{d['cau']:<3}"
              f"{t.get('rung', 0):>10.1f}{s.get('rung', 0):>11.1f}"
              f"{t.get('ty_muon', 0):>10.1f}%{t.get('he_thong', 0):>10.1f}")


def main() -> int:
    from config import settings
    if not settings.groq_keys():
        print("KHÔNG có key Groq -> arm OV_GROQ không đo được. Dừng.")
        return 2
    from app.core import giong_hang as gh
    from app.core import giong_ngoai as gn
    if not gn.co_omnivoice():
        print(f"KHÔNG dùng được OmniVoice: {gn.tinh_trang_omnivoice()['thieu']}")
        return 2
    if not gh.co_giong_hang():
        print(f"KHÔNG có bộ gióng hàng: {gh.tinh_trang_giong_hang()['thieu']}"
              f" -> arm OV_GH sẽ trả mốc rỗng, đo vô nghĩa. Dừng.")
        return 2

    try:
        import psutil
        psutil.cpu_percent()
        time.sleep(1.0)
        cpu = psutil.cpu_percent()
        print(f"CPU nền lúc bắt đầu: {cpu:.1f}%"
              + ("  ** MÁY ĐANG BẬN, số thời gian không dùng được **"
                 if cpu > 15 else ""))
    except Exception:                                        # noqa: BLE001
        cpu = -1.0

    san_goc = REPO / "_do_gn_gh_san"
    kho: dict = {nn: {a: {"phu": [], "n_moc": 0, "n_tu": 0, "cau": 0,
                          "dau_dung": 0, "tho": [], "sach": []}
                      for a in ARMS} for nn in NN}
    giay: dict = {}

    for luot in range(SO_LUOT):
        for nn in NN:
            texts = M.nap_cau(nn)
            # ĐAN XEN + XOAY THỨ TỰ (nhớ mục "Đo A/B phải đan xen" — đã sai
            # 3 lần trên máy này vì đo liền mạch).
            thu_tu = (["EDGE", "OV"] if luot % 2 == 0 else ["OV", "EDGE"])
            for buoc in thu_tu:
                nhan = M.NHAN_NN.get(nn, nn)
                if buoc == "EDGE":
                    print(f"  lượt {luot + 1} · {nhan} · EDGE ({len(texts)} câu)…")
                    t0 = time.time()
                    ok, paths, w = doc_edge(
                        texts, nn, san_goc / f"l{luot}_{nn}_edge")
                    giay.setdefault("EDGE", []).append(round(time.time() - t0, 2))
                    r = cham(texts, paths, ok, w)
                    for k in ("phu", "tho", "sach"):
                        kho[nn]["EDGE"][k] += r[k]
                    for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                        kho[nn]["EDGE"][k] += r[k]
                    continue

                print(f"  lượt {luot + 1} · {nhan} · OmniVoice sinh tiếng "
                      f"({len(texts)} câu)…")
                t0 = time.time()
                ok, paths = doc_ov(texts, nn, san_goc / f"l{luot}_{nn}_ov")
                giay.setdefault("OV_SINH", []).append(round(time.time() - t0, 2))
                if not any(ok):
                    print("      ! OmniVoice trả ok toàn False (chốt "
                          "ALL-OR-NOTHING) -> bỏ lượt này")
                    continue
                # Xoay cả thứ tự lấy mốc: cột GIÂY của hai đường mới công bằng
                doi = ["GROQ", "GH"] if (luot + NN.index(nn)) % 2 == 0 \
                    else ["GH", "GROQ"]
                m: dict = {}
                for d in doi:
                    t0 = time.time()
                    if d == "GROQ":
                        m["OV_GROQ"] = moc_groq(texts, paths, ok)
                    else:
                        m["OV_GH"] = moc_gh(texts, paths, ok, nn)
                    giay.setdefault("OV_" + d, []).append(
                        round(time.time() - t0, 2))
                for a in ("OV_GROQ", "OV_GH"):
                    r = cham(texts, paths, ok, m[a])
                    for k in ("phu", "tho", "sach"):
                        kho[nn][a][k] += r[k]
                    for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                        kho[nn][a][k] += r[k]

    print("\n" + "=" * 80)
    print("KẾT QUẢ — thước DUY NHẤT: silencedetect · ms · DƯƠNG = mốc MUỘN "
          "hơn tiếng")
    print("=" * 80)
    gop = {a: {"phu": [], "n_moc": 0, "n_tu": 0, "cau": 0, "dau_dung": 0,
               "tho": [], "sach": []} for a in ARMS}
    for nn in NN:
        print(f"\n### {M.NHAN_NN.get(nn, nn).upper()}")
        in_bang(f"{len(M.nap_cau(nn))} câu × {SO_LUOT} lượt", kho[nn])
        for a in ARMS:
            for k in ("phu", "tho", "sach"):
                gop[a][k] += kho[nn][a][k]
            for k in ("n_moc", "n_tu", "cau", "dau_dung"):
                gop[a][k] += kho[nn][a][k]

    print("\n" + "=" * 80)
    print("GỘP 4 THỨ TIẾNG")
    print("=" * 80)
    in_bang("tổng", gop)
    print("\n  GIÂY (một lượt gọi cho cả loạt câu):")
    for k, v in giay.items():
        if v:
            print(f"    {k:<9} TB {sum(v) / len(v):>7.2f}s  ({len(v)} lượt, "
                  f"thô {v})")

    RA.write_text(json.dumps(
        {"so_cau": SO_CAU, "so_luot": SO_LUOT, "nn": NN, "giong_ov": GIONG_OV,
         "cpu_nen": cpu, "giay": giay,
         "tk": {nn: {a: {"phu_tb": (round(statistics.mean(d["phu"]), 1)
                                    if d["phu"] else None),
                         "n_moc": d["n_moc"], "n_tu": d["n_tu"],
                         "cau": d["cau"], "dau_dung": d["dau_dung"],
                         "tho": tk(d["tho"]), "sach": tk(d["sach"])}
                     for a, d in kho[nn].items()} for nn in NN},
         "gop": {a: {"phu_tb": (round(statistics.mean(d["phu"]), 1)
                                if d["phu"] else None),
                     "n_moc": d["n_moc"], "n_tu": d["n_tu"],
                     "cau": d["cau"], "dau_dung": d["dau_dung"],
                     "tho": tk(d["tho"]), "sach": tk(d["sach"])}
                 for a, d in gop.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
