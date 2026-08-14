# -*- coding: utf-8 -*-
"""ĐO LỖI (1) "KHÔNG KHỚP" — THƯỚC CŨ ĐANG ĐO NHẦM THỨ.

v2.27.0 đo ra: câu vượt tempo 1,30 = **0,0%** cả 3 lượt · chồng lấn **0 ms** ·
`tempo_max` 1,017-1,027. Theo số thì hết lỗi. Nhưng anh Hùng NGHE vẫn sai.

**VÌ SAO SỐ CŨ MÙ** (đọc `khop_thoi_gian`, dòng 1996):

    lech_dau.append(0.0)                  # đặt ĐÚNG mốc gốc

`lech_dau_ms` KHÔNG PHẢI SỐ ĐO — nó là hằng số 0,0 gán cứng. Cả `chong_lan`
cũng chỉ nhìn MỘT CHIỀU: câu có liếm sang câu KẾ không. Cả hai đều không hỏi
được câu mà tai người hỏi: **"trong lúc miệng người ta đang mấp máy, có tiếng
mới nào phát ra không?"**

Đường v2.27.0 cắt lề im (~0,20s đầu + ~0,87s cuối MỖI CÂU) rồi rút gọn chữ rồi
đọc nhanh — cả 3 đều làm câu NGẮN LẠI. Câu ngắn đặt ở mốc `start` gốc thì phần
đuôi khung thành KHOẢNG LẶNG trong khi trên hình miệng vẫn đang nói. Không một
thước nào của v2.27.0 nhìn thấy chuyện đó.

**THƯỚC MỚI — PHỦ MIỆNG:** với mỗi câu, `phủ = d_fin / khung` (khung = end −
start của người nói GỐC). `hụt = khung − d_fin` = số giây miệng mấp máy mà
không có tiếng. Đây là thứ tai bắt được.

    .venv\\Scripts\\python _do_khop_mieng.py [zh|zh2|en] [số lượt]
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

import _do_kho_tg as KHO                       # noqa: E402
from app.core import thay_giong as tg          # noqa: E402

SAN = REPO / "_do_khop_san"


def _d(p) -> float:
    try:
        return tg.probe_duration(p)
    except Exception:  # noqa: BLE001
        return 0.0


def _tv(xs: list[float]) -> float:
    """Trung vị — chống 1 câu dị làm lệch cả bảng."""
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mot_luot(k: dict, lan: int, dich_sang: str) -> dict:
    """Chạy ĐÚNG các bước 3-5 của `thay_giong_video`, đo phủ miệng từng câu."""
    tam = SAN / f"{k['ten']}_l{lan}"
    if tam.exists():
        shutil.rmtree(tam, ignore_errors=True)
    tam.mkdir(parents=True, exist_ok=True)

    cau, tong = k["cau"], k["tong"]
    goc_ma = k["ngon_ngu"]
    t0 = time.time()

    dd = tg.dich_hau_kiem(cau, dich_sang, goc_ma)
    tts = tg.doc_ban_dich(dd["ban_dich"], tam / "tts", "", dich_sang)
    rg = tg.rut_gon_vua_khung(cau, dd["ban_dich"], tts, tong,
                              tam / "rutgon", dich_sang, tts["voice"])
    dn = tg.doc_nhanh_vua_khung(cau, rg["texts"], rg["files"], rg["ok"],
                                tong, tam / "docnhanh", dich_sang, tts["voice"])
    kh = tg.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, tam / "khop")

    # ---- ĐO PHỦ MIỆNG: mốc nào có tiếng, mốc nào miệng mấp máy mà câm
    theo_moc = {round(a, 3): f for a, f in kh["manh"]}
    dong: list[dict] = []
    for i, c in enumerate(cau):
        a, b = float(c["start"]), float(c["end"])
        khung = max(0.05, b - a)
        f = theo_moc.get(round(a, 3))
        d_fin = _d(f) if f else 0.0
        dong.append({
            "i": i, "a": a, "b": b, "khung": khung,
            "d_tho": _d(tts["files_tho"][i]) if i < len(tts["files_tho"]) else 0,
            "d_sach": _d(tts["files"][i]) if i < len(tts["files"]) else 0,
            "d_dn": _d(dn["files"][i]) if i < len(dn["files"]) else 0,
            "d_fin": d_fin,
            "phu": d_fin / khung if khung > 0 else 0.0,
            "hut_ms": (khung - d_fin) * 1000.0,
            "goc": c["text"], "dich": dd["ban_dich"][i],
            "cuoi": rg["texts"][i] if i < len(rg["texts"]) else "",
        })

    phu = [r["phu"] for r in dong]
    hut = [r["hut_ms"] for r in dong]
    tong_khung = sum(r["khung"] for r in dong)
    tong_tieng = sum(r["d_fin"] for r in dong)
    doi_chu = [r for r in dong if r["cuoi"].strip() != r["dich"].strip()]

    return {
        "lan": lan, "giay": round(time.time() - t0, 1),
        "so_cau": len(dong),
        "phu_tb": round(sum(phu) / len(phu), 3) if phu else 0,
        "phu_tv": round(_tv(phu), 3),
        "phu_min": round(min(phu or [0]), 3),
        # Câu phủ dưới 70% = hơn 30% thời gian miệng mấp máy mà câm tiếng.
        "cau_phu_duoi_70": sum(1 for x in phu if x < 0.70),
        "cau_phu_duoi_50": sum(1 for x in phu if x < 0.50),
        "hut_ms_tv": round(_tv(hut), 1),
        "hut_ms_max": round(max(hut or [0]), 1),
        "tong_khung": round(tong_khung, 2),
        "tong_tieng": round(tong_tieng, 2),
        "phu_tong": round(tong_tieng / tong_khung, 3) if tong_khung else 0,
        # số cũ, giữ lại để thấy nó VẪN ĐẸP trong khi phủ miệng đã hỏng
        "tempo_max": kh["tempo_max"],
        "vuot_130_pc": round(100.0 * kh["so_cau_vuot_canh_bao"]
                             / max(1, kh["so_cau"]), 1),
        "chong_lan_ms": kh["chong_lan_ms_max"],
        "so_cau_cat": kh["so_cau_cat"],
        # rút gọn
        "so_doi_chu": len(doi_chu),
        "pc_doi_chu": round(100.0 * len(doi_chu) / max(1, len(dong)), 1),
        "_dong": dong, "_tam": str(tam), "_manh": kh["manh"],
        "_dich": dd["ban_dich"], "_cuoi": rg["texts"],
    }


def main() -> int:
    SAN.mkdir(parents=True, exist_ok=True)
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh"
    so_luot = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    dich_sang = "vi" if ten == "en" else "en"

    print(f"chuẩn bị nguồn [{ten}] (dùng cache chép lời)...")
    k = KHO.chuan_bi(ten, can_nhac=False)
    print(f"  {k['tong']:.2f}s · {len(k['cau'])} câu · nhãn "
          f"{k['chep'].get('language')} · dịch sang {dich_sang}")

    # Số CỐ ĐỊNH, không phụ thuộc LLM: khung gốc nói bao nhiêu giây trên tổng.
    tk = sum(max(0.05, float(c["end"]) - float(c["start"])) for c in k["cau"])
    print(f"  người gốc nói {tk:.2f}s / {k['tong']:.2f}s "
          f"= {100 * tk / k['tong']:.1f}% thời lượng\n")

    kqs = []
    for lan in range(1, so_luot + 1):
        print(f"--- LƯỢT {lan}/{so_luot} ---")
        r = mot_luot(k, lan, dich_sang)
        kqs.append(r)
        print(f"  {r['giay']}s · {r['so_cau']} câu")
        print(f"  PHỦ MIỆNG   tb {r['phu_tb']:.3f} · trung vị {r['phu_tv']:.3f}"
              f" · thấp nhất {r['phu_min']:.3f}")
        print(f"  câu phủ <70% : {r['cau_phu_duoi_70']}/{r['so_cau']}"
              f"  ·  <50% : {r['cau_phu_duoi_50']}/{r['so_cau']}")
        print(f"  HỤT trung vị {r['hut_ms_tv']:.0f} ms · lớn nhất "
              f"{r['hut_ms_max']:.0f} ms")
        print(f"  tổng tiếng mới {r['tong_tieng']:.2f}s / khung gốc "
              f"{r['tong_khung']:.2f}s = {r['phu_tong']:.3f}")
        print(f"  [số CŨ vẫn đẹp] tempo_max {r['tempo_max']} · vượt 1,30 "
              f"{r['vuot_130_pc']}% · chồng lấn {r['chong_lan_ms']} ms")
        print(f"  rút gọn đổi chữ {r['so_doi_chu']}/{r['so_cau']} câu "
              f"({r['pc_doi_chu']}%) · cắt đuôi {r['so_cau_cat']} câu")
        # 5 câu hụt nhất — để đọc bằng mắt
        xau = sorted(r["_dong"], key=lambda x: x["phu"])[:5]
        for x in xau:
            print(f"    #{x['i']:>3} @{x['a']:6.2f}s khung {x['khung']:5.2f}s "
                  f"-> tiếng {x['d_fin']:5.2f}s (phủ {x['phu']:.2f}) "
                  f"| {x['cuoi'][:52]}")
        print()

    print("===== TỔNG HỢP 3 LƯỢT =====")
    print(f"{'lượt':>5} {'phủ tb':>7} {'phủ tv':>7} {'<70%':>6} {'<50%':>6} "
          f"{'hụt tv':>8} {'phủ tổng':>9} {'tempo_max':>10} {'vượt1,30':>9}")
    for r in kqs:
        print(f"{r['lan']:>5} {r['phu_tb']:>7.3f} {r['phu_tv']:>7.3f} "
              f"{r['cau_phu_duoi_70']:>3}/{r['so_cau']:<2} "
              f"{r['cau_phu_duoi_50']:>3}/{r['so_cau']:<2} "
              f"{r['hut_ms_tv']:>7.0f}ms {r['phu_tong']:>9.3f} "
              f"{r['tempo_max']:>10} {r['vuot_130_pc']:>8}%")

    (SAN / f"kq_{ten}.json").write_text(
        json.dumps([{a: b for a, b in r.items() if not a.startswith("_")}
                    for r in kqs], ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nchi tiết: {SAN / f'kq_{ten}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
