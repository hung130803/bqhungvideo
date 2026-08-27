# -*- coding: utf-8 -*-
"""PHÂN LOẠI BỆNH A-F cho MỘT bản dịch — ra TỈ LỆ %, không gộp thành "dịch sai".

| mã | bệnh                                   | cách xác nhận ở đây                |
|----|----------------------------------------|------------------------------------|
| A  | NGUỒN đã sai (ASR nghe nhầm)           | `cham_nguon.nghe <= 2`             |
| B  | CẮT CÂU sai (mẩu giữa ý)               | `cham_nguon.tron <= 2`             |
| C  | MẤT NGỮ CẢNH                           | câu nằm ở lượt gọi ĐÒI LẠI (lô nhỏ)|
| D  | MODEL yếu / prompt tệ                  | chấm <= 2 mà nguồn LÀNH (A,B loại) |
| E  | LẪN NGÔN NGỮ                           | hệ chữ lạ / còn chữ gốc            |
| F  | RỚT / RỖNG / TRẢ NGUYÊN VĂN            | so bản dịch với câu gốc            |

THỨ TỰ XẾP LÀ CỐ Ý: một câu hỏng chỉ được đếm vào ĐÚNG MỘT mã, theo thứ tự
F -> E -> A -> B -> C -> D. Nguồn sai (A) hoặc câu cụt (B) thì dịch không cứu
được, nên chúng phải được TRỪ RA trước khi kết tội model (D).
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _dich_do_chung as C                                    # noqa: E402
import _dich_cham as CH                                       # noqa: E402

#: Chấm <= mức này là câu HỎNG (thang 1-5 của `cham_trung_thanh`).
NGUONG_HONG = 2.0
#: `nghe` <= mức này -> nguồn đã sai (mã A).
NGUONG_NGHE = 2.0
#: `tron` <= mức này -> câu bị chặt giữa ý (mã B).
NGUONG_TRON = 2.0


def cham_nguon_cache(ma_video: str, goc_ma: str) -> list:
    """Chấm NGUỒN một lần rồi cất — mọi arm dùng CHUNG, vì nguồn không đổi."""
    p = C.HOP / ("nguon_%s.json" % ma_video)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))["cham"]
    cau, _meta = C.doc_cau(ma_video)
    t0 = time.time()
    cham = CH.cham_nguon(cau, goc_ma)
    C.ghi("nguon_%s.json" % ma_video,
          {"video": ma_video, "goc_ma": goc_ma, "model_cham": CH.MODEL_CHAM,
           "giay": round(time.time() - t0, 1), "cham": cham})
    return cham


def phan_loai(kq: dict, cham_ng: list, cham_dich: list, bt_chrf: list) -> dict:
    """Xếp từng câu vào ĐÚNG MỘT mã bệnh (hoặc 'lanh')."""
    n = kq["so_cau"]
    goc, bd = kq["goc"], kq["ban_dich"]
    f_set = set(kq["F_tra_nguyen_goc"]) | set(kq["F_rong"])
    e_set = set()
    for v in (kq.get("E_he_chu_la") or {}).values():
        e_set |= set(v)
    e_set |= set(kq.get("E_khong_dau_viet") or [])
    e_set -= f_set

    # câu nào nằm ở lượt gọi ĐÒI LẠI (lượt 2 trở đi) -> mất ngữ cảnh cả bài
    doi_lai = set()
    for k, m in enumerate(kq.get("goi_chi_tiet") or []):
        if k >= 1:
            doi_lai |= set(m.get("nhan") or [])

    ma = {}
    for i in range(n):
        if i in f_set:
            ma[i] = "F"
            continue
        if i in e_set:
            ma[i] = "E"
            continue
        d = cham_dich[i].get("diem")
        if d is None or d > NGUONG_HONG:
            ma[i] = "lanh"
            continue
        ng = (cham_ng[i] or {}).get("nghe")
        tr = (cham_ng[i] or {}).get("tron")
        if ng is not None and ng <= NGUONG_NGHE:
            ma[i] = "A"
        elif tr is not None and tr <= NGUONG_TRON:
            ma[i] = "B"
        elif i in doi_lai:
            ma[i] = "C"
        else:
            ma[i] = "D"
    dem = {}
    for k in ("A", "B", "C", "D", "E", "F", "lanh"):
        dem[k] = sum(1 for v in ma.values() if v == k)
    ty = {k: round(100.0 * v / max(1, n), 1) for k, v in dem.items()}
    diem = [c["diem"] for c in cham_dich if c.get("diem") is not None]
    cf = [x for x in bt_chrf if x is not None]
    return {
        "so_cau": n, "ma": ma, "dem": dem, "ty_le": ty,
        "so_luot_goi": (kq.get("goi") or {}).get("so_luot"),
        "cau_o_luot_doi_lai": len(doi_lai),
        "diem_tb": round(sum(diem) / max(1, len(diem)), 3),
        "diem_1_2": sum(1 for d in diem if d <= 2),
        "diem_5": sum(1 for d in diem if d >= 5),
        "chrf_tb": round(sum(cf) / max(1, len(cf)), 2),
        "chrf_trung_vi": round(sorted(cf)[len(cf) // 2], 2) if cf else 0.0,
        "loi_theo_ma": _dem_loi(cham_dich),
        "goc": goc, "ban_dich": bd,
    }


def _dem_loi(cham_dich: list) -> dict:
    d = {}
    for c in cham_dich:
        m = c.get("loi") or ""
        if m:
            d[m] = d.get(m, 0) + 1
    return dict(sorted(d.items(), key=lambda x: -x[1]))


def chay(ten_kq: str) -> dict:
    kq = json.loads((C.HOP / (ten_kq + ".json")).read_text(encoding="utf-8"))
    ma_video, ds = kq["video"], kq["dich_sang"]
    cau, meta = C.doc_cau(ma_video)
    goc_ma = (meta.get("language") or "")[:2].lower()
    CH.kiem_thuoc()

    cham_ng = cham_nguon_cache(ma_video, goc_ma)
    t0 = time.time()
    nguoc = CH.dich_nguoc(kq["ban_dich"], goc_ma, ds)
    cf = [CH.chrf(kq["goc"][i], nguoc[i]) if nguoc[i] else None
          for i in range(kq["so_cau"])]
    cham_d = CH.cham_trung_thanh(kq["goc"], kq["ban_dich"], goc_ma, ds)
    ra = phan_loai(kq, cham_ng, cham_d, cf)
    ra.update({"ten_kq": ten_kq, "video": ma_video, "dich_sang": ds,
               "lan": kq.get("lan"), "giay_cham": round(time.time() - t0, 1),
               "model_cham": CH.MODEL_CHAM,
               "dich_nguoc": nguoc, "chrf": cf, "cham_dich": cham_d})
    C.ghi("benh_" + ten_kq + ".json", ra)
    t = ra["ty_le"]
    print("[%s] %d câu · %d lượt gọi · chấm %.0fs" %
          (ten_kq, ra["so_cau"], ra["so_luot_goi"] or 0, ra["giay_cham"]))
    print("   A %s%% · B %s%% · C %s%% · D %s%% · E %s%% · F %s%% | LÀNH %s%%"
          % (t["A"], t["B"], t["C"], t["D"], t["E"], t["F"], t["lanh"]))
    print("   điểm TB %.2f/5 · câu <=2 điểm: %d · câu 5 điểm: %d · "
          "chrF dịch-ngược TB %.1f (trung vị %.1f)"
          % (ra["diem_tb"], ra["diem_1_2"], ra["diem_5"],
             ra["chrf_tb"], ra["chrf_trung_vi"]))
    print("   mã lỗi LLM chấm:", ra["loi_theo_ma"])
    return ra


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["moc_v396_vi_l1"]):
        chay(t)
