# -*- coding: utf-8 -*-
"""ĐO PHÂN BỐ TEMPO TỪNG CÂU — vì sao lồng tiếng "nói không mượt".

Anh Hùng NGHE THẬT và báo: *"phần sub thoại giọng lồng tiếng cảm giác KHÔNG
KHỚP, KHÔNG MƯỢT, nói còn nhiều lỗi"*. Số đo cũ chỉ có `tempo_max` (lượt nào
cũng chạm trần 1,5) — MỘT con số không nói được bao nhiêu câu bị ép.

File này đo PHÂN BỐ: bao nhiêu % câu vượt 1,2 · 1,3 · 1,4 · chạm trần; và với
câu vượt thì bản dịch DÀI HƠN câu gốc bao nhiêu (ký tự/giây khung).

Thành phần THẬT: Groq (dịch + hậu kiểm), edge-tts, ffmpeg. Chép lời lấy từ
cache `_do_kho_tg.py` (tiền định) để 3 lượt so được với nhau.

    .venv\\Scripts\\python _do_tempo_cau.py [zh|zh2|en|tatca] [số lượt]
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
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _do_kho_tg as kho  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

BAC = (1.05, 1.20, 1.30, 1.40, 1.49)


def _pb(xs: list[float]) -> str:
    n = max(1, len(xs))
    return " · ".join(f">{b:.2f}: {100.0 * sum(1 for t in xs if t > b) / n:4.1f}%"
                      for b in BAC)


def mot_luot(k: dict, dich_sang: str, vong: int, lam: Path) -> dict:
    cau, tong = k["cau"], k["tong"]
    goc_ma = (k["chep"].get("language") or "")
    t0 = time.time()
    dd = tg.dich_hau_kiem(cau, dich_sang, goc_ma)
    tts = tg.doc_ban_dich(dd["ban_dich"], lam / "tts", "", dich_sang)
    rg = tg.rut_gon_vua_khung(cau, dd["ban_dich"], tts, tong,
                              lam / "rutgon", dich_sang, tts["voice"])
    dn = tg.doc_nhanh_vua_khung(cau, rg["texts"], rg["files"], rg["ok"], tong,
                                lam / "docnhanh", dich_sang, tts["voice"])
    rg["files"], rg["ok"] = dn["files"], dn["ok"]
    kh = tg.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, lam / "khop")

    # NGHĨA CÓ MẤT KHÔNG: `dich_hau_kiem` chỉ chấm bản dịch ĐẦU. Bước rút gọn
    # sửa chữ SAU đó và KHÔNG được chấm lần nào — nên phải chấm lại bản CUỐI
    # bằng đúng phép dịch-ngược có sẵn, rồi so với điểm bản đầu.
    goc_txt = [c["text"] for c in cau]
    diem_cuoi = tg._dich_nguoc_cham(goc_txt, rg["texts"], goc_ma, dich_sang)
    doi = [i for i in range(len(cau))
           if i < len(rg["texts"]) and rg["texts"][i] != dd["ban_dich"][i]]
    nghia = {
        "so_cau_doi_chu": len(doi),
        "diem_dau_tb": round(sum(dd["diem"]) / max(1, len(dd["diem"])), 2),
        "diem_cuoi_tb": round(sum(diem_cuoi) / max(1, len(diem_cuoi)), 2),
        "diem_cuoi_min": round(min(diem_cuoi), 2) if diem_cuoi else 0.0,
        "duoi_nguong_cuoi": sum(1 for d in diem_cuoi
                                if d < tg.NGUONG_GIONG_NGHIA),
    }
    # ĐỐI CHỨNG BẮT BUỘC: câu KHÔNG bị đổi chữ phải được chấm GẦN NHƯ CŨ.
    # Không có cột này thì không phân biệt được "rút gọn làm mất nghĩa" với
    # "chính bộ chấm nhấp nháy" — và bộ chấm là LLM, nó chấm cả LOẠT nên đổi
    # 16 câu là đổi luôn ngữ cảnh của 27 câu còn lại.
    giu = [i for i in range(len(cau)) if i < len(diem_cuoi) and i not in doi]
    if giu:
        nghia["doi_chung_giu_dau"] = round(
            sum(dd["diem"][i] for i in giu) / len(giu), 2)
        nghia["doi_chung_giu_cuoi"] = round(
            sum(diem_cuoi[i] for i in giu) / len(giu), 2)
        nghia["doi_chung_troi"] = round(
            nghia["doi_chung_giu_cuoi"] - nghia["doi_chung_giu_dau"], 2)
    if doi:
        nghia["diem_dau_cau_doi"] = round(
            sum(dd["diem"][i] for i in doi) / len(doi), 2)
        nghia["diem_cuoi_cau_doi"] = round(
            sum(diem_cuoi[i] for i in doi) / len(doi), 2)
        # TỤT THẬT = tụt của câu bị đổi TRỪ ĐI trôi của câu giữ nguyên
        nghia["tut_that"] = round(
            (nghia["diem_cuoi_cau_doi"] - nghia["diem_dau_cau_doi"])
            - nghia.get("doi_chung_troi", 0.0), 2)
        xau = sorted(doi, key=lambda i: diem_cuoi[i])[:3]
        nghia["vi_du_xau"] = [{
            "i": i, "diem": round(diem_cuoi[i], 1),
            "goc": goc_txt[i][:90],
            "dich_dau": dd["ban_dich"][i][:110],
            "sau_rut_gon": rg["texts"][i][:110],
        } for i in xau]

    # câu nào bị ép -> bản dịch dài hơn câu gốc bao nhiêu?
    dai = []
    for i, t in enumerate(kh["tempo_cau"]):
        if t > 1.001 and i < len(rg["texts"]):
            khung = tg.khung_cho_phep(cau, i, tong)
            dai.append({
                "i": i, "tempo": t,
                "kytu_goc": len(cau[i]["text"]),
                "kytu_dich": len(rg["texts"][i]),
                "khung": round(khung, 2),
                "doc_mat": round(tg.probe_duration(rg["files"][i]), 2),
            })
    return {
        "vong": vong, "giay": round(time.time() - t0, 1),
        "so_cau": len(cau),
        "cat_le": tts.get("cat_le", {}),
        "nghia": nghia,
        "dich": {kk: vv for kk, vv in dd.items() if kk != "ban_dich"},
        "rut_gon": {kk: vv for kk, vv in rg.items()
                    if kk not in ("texts", "files", "ok")},
        "doc_nhanh": {kk: vv for kk, vv in dn.items()
                      if kk not in ("files", "ok", "can_truoc", "can_sau")},
        "khop": {kk: vv for kk, vv in kh.items() if kk != "manh"},
        "dai": dai,
        "texts": rg["texts"],
    }


def main() -> int:
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh"
    so_luot = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    tens = [t for t, _ in kho.NGUON] if ten == "tatca" else [ten]
    lam = REPO / "_do_tempo_tam"
    tat: dict = {}
    for tn in tens:
        k = kho.chuan_bi(tn)
        dich_sang = "en" if tn.startswith("zh") else "vi"
        print(f"\n########## {tn} · {k['tong']:.1f}s · {len(k['cau'])} câu · "
              f"{k['chep'].get('language')} -> {dich_sang} ##########")
        luots = []
        for v in range(so_luot):
            if lam.exists():
                shutil.rmtree(lam, ignore_errors=True)
            lam.mkdir(parents=True, exist_ok=True)
            r = mot_luot(k, dich_sang, v + 1, lam)
            luots.append(r)
            kh, rg = r["khop"], r["rut_gon"]
            print(f"\n--- LƯỢT {v + 1} ({r['giay']}s) ---")
            cl = r.get("cat_le") or {}
            if cl:
                print(f"  cắt lề im: {cl.get('giay_truoc')}s -> "
                      f"{cl.get('giay_sau')}s (bỏ {cl.get('giay_cat_tong')}s "
                      f"= {cl.get('giay_cat_tb')}s/câu)")
            print(f"  dịch lại {r['dich']['ty_le_dich_lai']}% · "
                  f"điểm nghĩa TB {r['dich']['diem_tb']} · "
                  f"min {r['dich']['diem_min']}")
            print(f"  rút gọn: sửa {rg['so_sua']} câu · "
                  f"tempo CẦN max {rg['tempo_can_max_truoc']} -> "
                  f"{rg['tempo_can_max_sau']} · "
                  f"vượt {rg['so_cau_vuot_truoc']} -> {rg['so_cau_vuot_sau']}")
            dn = r.get("doc_nhanh") or {}
            if dn:
                print(f"  đọc nhanh lại: {dn.get('so_doc_lai')} câu · "
                      f"rate max +{dn.get('rate_max')}% · "
                      f"tempo CẦN max {dn.get('can_max_truoc')} -> "
                      f"{dn.get('can_max_sau')}")
            print(f"  PHÂN BỐ tempo ÁP THẬT ({kh['so_cau']} câu): "
                  f"{_pb(kh['tempo_cau'])}")
            print(f"  tempo max {kh['tempo_max']} · TB {kh['tempo_tb']} · "
                  f"ép {kh['so_cau_ep']} · mượn {kh['so_cau_muon']}")
            print(f"  CHỒNG LẤN max {kh['chong_lan_ms_max']} ms · "
                  f"{kh['so_cau_chong_lan']} câu · "
                  f"lệch đầu max {kh['lech_dau_ms_max']} ms · "
                  f"cắt đuôi {kh.get('so_cau_cat', '?')} câu")
            ng = r["nghia"]
            print(f"  NGHĨA (dịch-ngược chấm lại bản CUỐI): "
                  f"{ng['so_cau_doi_chu']} câu bị đổi chữ · "
                  f"điểm TB {ng['diem_dau_tb']} -> {ng['diem_cuoi_tb']} · "
                  f"min cuối {ng['diem_cuoi_min']} · "
                  f"dưới ngưỡng {ng['duoi_nguong_cuoi']} câu")
            if "doi_chung_troi" in ng:
                print(f"    ĐỐI CHỨNG câu GIỮ NGUYÊN: {ng['doi_chung_giu_dau']}"
                      f" -> {ng['doi_chung_giu_cuoi']} "
                      f"(trôi {ng['doi_chung_troi']:+.2f} = nhiễu bộ chấm)")
            if "diem_dau_cau_doi" in ng:
                print(f"    riêng câu BỊ ĐỔI: {ng['diem_dau_cau_doi']} -> "
                      f"{ng['diem_cuoi_cau_doi']} · TỤT THẬT "
                      f"{ng.get('tut_that'):+.2f} (đã trừ nhiễu)")
                for e in ng.get("vi_du_xau", []):
                    print(f"      #{e['i']} ({e['diem']}) gốc: {e['goc']}")
                    print(f"           dịch : {e['dich_dau']}")
                    print(f"           rút  : {e['sau_rut_gon']}")
            if r["dai"]:
                x = sorted(r["dai"], key=lambda d: -d["tempo"])[:5]
                print("  5 câu ép mạnh nhất (gốc -> dịch, ký tự):")
                for d in x:
                    print(f"    #{d['i']:3d} tempo {d['tempo']:.3f} · "
                          f"{d['kytu_goc']:3d} -> {d['kytu_dich']:3d} ký tự · "
                          f"khung {d['khung']:.2f}s · đọc mất {d['doc_mat']:.2f}s")
        tat[tn] = luots

        print(f"\n===== TỔNG {tn}: {so_luot} lượt =====")
        for v, r in enumerate(luots):
            kh = r["khop"]
            print(f"  lượt {v + 1}: max {kh['tempo_max']:.3f} · "
                  f"TB {kh['tempo_tb']:.3f} · {_pb(kh['tempo_cau'])} · "
                  f"chồng {kh['chong_lan_ms_max']:.0f} ms/"
                  f"{kh['so_cau_chong_lan']} câu")

    out = REPO / f"_do_tempo_kq_{ten}.json"
    out.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nGhi: {out.name}")
    shutil.rmtree(lam, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
