# -*- coding: utf-8 -*-
"""LỆCH BẬC — bộ dò TIỀN ĐỊNH cho lỗi "bản dịch câu #i thật ra là câu #i+k".

VÌ SAO PHẢI CÓ: đây là lỗi DUY NHẤT trong 6 mã bệnh mà app **không có một
phép kiểm nào** với tới. `_theo_nhan` chỉ hỏi *"nhãn #i có về không"*; nhãn
VỀ ĐỦ mà mang chữ của câu KHÁC thì mọi cổng đều xanh, đếm câu vào = câu ra,
không sót chữ gốc, không rỗng — và người xem nghe lời của cảnh sau đặt lên
cảnh trước. Đúng chữ anh Hùng dùng: *"không hiểu ngữ nghĩa gì cả, linh tinh"*.

CÁCH DÒ: dịch NGƯỢC bản dịch về tiếng gốc (lượt gọi ĐỘC LẬP, model KHÁC) rồi
với mỗi câu tìm câu gốc KHỚP NHẤT trong cửa sổ ±`CUA_SO`. Khớp nhất rơi vào
`i+k` với `k != 0` -> LỆCH BẬC `k`.

BẤT BIẾN CỦA PHÉP ĐO: phải dịch ngược theo LÔ NHỎ (`CO_LO_NGUOC`) — chính bộ
dịch ngược cũng RỚT ĐUÔI khi lô to, và lúc đó bảng lệch bậc sẽ đọc thành
"không dò được" thay vì "có lệch".
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _dich_do_chung as C                                    # noqa: E402
import _dich_cham as CH                                       # noqa: E402

CUA_SO = 4
#: Lô dịch ngược phải NHỎ — lô to thì chính bộ đo rớt đuôi (đã sập 1 lần).
CO_LO_NGUOC = 8
#: Khớp với hàng xóm phải hơn khớp với chính nó ngần này điểm chrF mới kết
#: luận là LỆCH — dưới mức đó là nhiễu của phép dịch ngược.
BIEN_CHAC = 3.0


def dich_nguoc_nho(dich, goc_ma, dich_ma):
    cu = CH.CO_LO_CHAM
    CH.CO_LO_CHAM = CO_LO_NGUOC
    try:
        return CH.dich_nguoc(dich, goc_ma, dich_ma)
    finally:
        CH.CO_LO_CHAM = cu


def do_lech(goc, nguoc):
    """Trả list {k, tu_khop, tot_nhat, chac} cho từng câu."""
    n = len(goc)
    ra = []
    for i in range(n):
        if not (nguoc[i] or "").strip():
            ra.append({"k": None, "tu": None, "tot": None, "chac": False})
            continue
        diem = {}
        for k in range(-CUA_SO, CUA_SO + 1):
            j = i + k
            if 0 <= j < n:
                diem[k] = CH.chrf(goc[j], nguoc[i])
        k_tot = max(diem, key=lambda k: diem[k])
        tu = diem.get(0, 0.0)
        ra.append({"k": k_tot, "tu": round(tu, 2),
                   "tot": round(diem[k_tot], 2),
                   "chac": bool(k_tot != 0 and diem[k_tot] - tu >= BIEN_CHAC)})
    return ra


def chay(ten_kq: str) -> dict:
    kq = json.loads((C.HOP / (ten_kq + ".json")).read_text(encoding="utf-8"))
    _cau, meta = C.doc_cau(kq["video"])
    goc_ma = (meta.get("language") or "")[:2].lower()
    CH.kiem_thuoc()
    nguoc = dich_nguoc_nho(kq["ban_dich"], goc_ma, kq["dich_sang"])
    lech = do_lech(kq["goc"], nguoc)
    co = [x for x in lech if x["k"] is not None]
    xau = [i for i, x in enumerate(lech) if x["chac"]]
    dem_k = {}
    for x in co:
        if x["chac"]:
            dem_k[str(x["k"])] = dem_k.get(str(x["k"]), 0) + 1
    ra = {"ten_kq": ten_kq, "so_cau": kq["so_cau"],
          "do_duoc": len(co), "khong_do_duoc": kq["so_cau"] - len(co),
          "so_lech": len(xau), "ty_le_lech": round(100.0 * len(xau)
                                                   / max(1, kq["so_cau"]), 1),
          "phan_bo_k": dict(sorted(dem_k.items(), key=lambda kv: -kv[1])),
          "cau_lech": xau, "chi_tiet": lech, "dich_nguoc": nguoc}
    C.ghi("lech_" + ten_kq + ".json", ra)
    print("[%s] %d câu · dò được %d · LỆCH BẬC %d câu (%.1f%%) · phân bố k=%s"
          % (ten_kq, ra["so_cau"], ra["do_duoc"], ra["so_lech"],
             ra["ty_le_lech"], ra["phan_bo_k"]))
    if xau:
        print("   câu lệch:", xau[:40])
    return ra


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["moc_v396_vi_l1"]):
        chay(t)
