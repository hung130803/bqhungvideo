# -*- coding: utf-8 -*-
"""LỖI 2 — GIỌNG MỚI CÓ BỊ NHẠC NỀN NHẤN CHÌM KHÔNG?

Đọc lại `_ket.json` do `_do_tach_mat.py` ghi (đường bao RMS của gốc/nhạc/giọng
theo cửa sổ 0,25 s) rồi trả lời đúng MỘT câu hỏi:

  Ở những lúc ĐANG NÓI, giọng cao hơn hay thấp hơn nhạc nền bao nhiêu dB?

So bản GỐC (người xem Trung Quốc nghe được) với bản THAY TIẾNG của anh Hùng.
Chênh lệch giữa hai cột đó chính là mức "nghe không được".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from _do_mat_tieng import BUOC, gom_khoang       # noqa: E402

#: Cửa sổ được coi là "ĐANG NÓI": lớp giọng nằm trong khoảng bấy nhiêu dB so
#: với đỉnh của chính lớp giọng đó. Lấy tương đối vì hai file có mức khác nhau.
DANG_NOI_DUOI_DINH_DB = 12.0

#: Giọng thấp hơn nhạc quá mức này thì tai thường KHÔNG tách ra được.
CHIM_DB = 3.0


def phan_tich(ten: str, kj: dict) -> dict:
    nhac = kj["bao_nhac"]
    giong = kj["bao_giong"]
    n = min(len(nhac), len(giong))
    dinh = max(giong[:n])
    noi = [i for i in range(n) if giong[i] >= dinh - DANG_NOI_DUOI_DINH_DB]
    if not noi:
        return {"ten": ten, "loi": "không tìm được cửa sổ đang nói"}
    d = [giong[i] - nhac[i] for i in noi]
    d_sap = sorted(d)
    chim = [i for i in noi if giong[i] - nhac[i] < -CHIM_DB]
    return {
        "ten": ten,
        "so_cua_so_noi": len(noi),
        "giay_noi": round(len(noi) * BUOC, 2),
        "giong_dinh_db": round(dinh, 1),
        "nhac_tb_luc_noi_db": round(sum(nhac[i] for i in noi) / len(noi), 1),
        "giong_tb_luc_noi_db": round(sum(giong[i] for i in noi) / len(noi), 1),
        "giong_tren_nhac_tb": round(sum(d) / len(d), 2),
        "giong_tren_nhac_trung_vi": round(d_sap[len(d_sap) // 2], 2),
        "giong_tren_nhac_min": round(min(d), 2),
        "giong_tren_nhac_max": round(max(d), 2),
        "so_cua_so_chim": len(chim),
        "ty_le_chim": round(100.0 * len(chim) / len(noi), 1),
        "giay_chim": round(len(chim) * BUOC, 2),
        "_chim_khoang": gom_khoang(chim),
    }


def main() -> int:
    cap = [("GỐC (tiếng Trung)", REPO / "_do_lt" / "tam" / "_ket.json"),
           ("BẢN THAY TIẾNG anh Hùng xuất",
            REPO / "_do_lt" / "tam_xuat" / "_ket.json")]
    ra = []
    for ten, p in cap:
        if not p.exists():
            print(f"THIẾU {p}")
            return 1
        ra.append(phan_tich(ten, json.loads(p.read_text(encoding="utf-8"))))

    print("== GIỌNG SO VỚI NHẠC NỀN, ĐO LÚC ĐANG NÓI ==")
    print(f"{'':38} {'gốc':>12} {'thay tiếng':>12}")
    hang = [
        ("số giây đang nói", "giay_noi"),
        ("nhạc lúc đang nói (dB)", "nhac_tb_luc_noi_db"),
        ("giọng lúc đang nói (dB)", "giong_tb_luc_noi_db"),
        ("GIỌNG TRÊN NHẠC — trung bình (dB)", "giong_tren_nhac_tb"),
        ("GIỌNG TRÊN NHẠC — trung vị (dB)", "giong_tren_nhac_trung_vi"),
        ("GIỌNG TRÊN NHẠC — thấp nhất (dB)", "giong_tren_nhac_min"),
        (f"cửa sổ giọng CHÌM dưới nhạc >{CHIM_DB:.0f}dB", "so_cua_so_chim"),
        ("  = % thời lượng đang nói", "ty_le_chim"),
        ("  = số giây", "giay_chim"),
    ]
    for nhan, khoa in hang:
        print(f"{nhan:38} {ra[0].get(khoa, '-'):>12} {ra[1].get(khoa, '-'):>12}")

    print("\n== KHOẢNG GIỌNG BỊ NHẠC NHẤN CHÌM (bản thay tiếng) ==")
    kh = ra[1].get("_chim_khoang") or []
    if not kh:
        print("  (không có)")
    for a, b in kh:
        if b - a < 0.4:
            continue
        print(f"    {a:7.2f}s -> {b:7.2f}s   ({b - a:5.2f}s)")
    print(f"  tổng {len(kh)} khoảng")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
