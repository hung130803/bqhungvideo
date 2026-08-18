"""CHẤM ĐIỂM trên BỘ ĐỐI CHỨNG GHI BẰNG TAY.

BỘ ĐỐI CHỨNG dưới đây do TÔI SOI KHUNG HÌNH mà ghi, không do thước nào sinh.
Mỏ neo: 4 video Douyin "giải thích phim" đều ĐỐT phụ đề lời NGƯỜI KỂ vào
khung, nên dải phụ đề TRỐNG = người kể không nói. Mỗi khoảng dưới đây đều có
ít nhất một khung tôi đã mở ra xem (ảnh giữ ở `_kq_nn/soi/`).

Đã soi và XÁC NHẬN KHÔNG có phụ đề:
  v1 t=1.50 (áo khoác)                      -> _kq_nn/soi/soi_0.png hàng 1
  v1 t=362.70 (cảnh tối, thoại tiếng Anh)   -> soi_0.png hàng 4
  v2 t=1.50 (tối)                           -> mo_dau_dai.png hàng 4
  v4 t=1.00 / 2.50 / 3.60 (bãi đá, tường)   -> mo_dau_dai.png hàng 1-3
  v4 t=4.75 / 6.20                          -> soi_1.png hàng 3-4
Đã soi và XÁC NHẬN CÓ phụ đề người kể (đối chứng chiều ngược):
  v1 t=30.00 «他们还定了一个规矩» · v1 t=108.75 «另一边» (dòng NGẮN)
  v2 t=4.00 «从来没有...» · v2 t=7.00 «由安娜贝尔...»
  v3 t=163.00 «可一抬头» · v3 t=200.00 «一想到...» · v3 t=218.75 «如此一来»
  v4 t=40.00 «已经彻底沦为感染者的乐园»
Đã soi 6 đoạn NGHI đối thoại giữa video (v3#133 «那东西是我的», v3#86, v2#36,
v2#80, v2#133, v1#36) -> phụ đề KHỚP bản chép lời -> đều là NGƯỜI KỂ thuật
lại. Ảnh: `_kq_nn/soi/dang_ngo.png`.

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_cham.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
SAN = GOC / "_kq_nn"

#: SỰ THẬT GHI BẰNG TAY — các khoảng TIẾNG GỐC CỦA PHIM (giây, thang nguồn).
SU_THAT = {
    "v1_dutu": [(0.00, 3.50), (362.14, 363.21)],
    "v2_nieu": [(0.00, 3.00)],
    "v3_8daodien": [],
    "v4_khuyendung": [(0.00, 6.36)],
}

#: đoạn có >= mức này thời lượng nằm trong vùng tiếng gốc thì nhãn = GIỮ GỐC
TY_LE_GIU = 0.50
#: 0,20..0,50 = PHA (nửa nọ nửa kia) — báo riêng, không gộp vào hai cột chính
TY_LE_PHA = 0.20

#: ngưỡng giọng lấy từ TỰ KIỂM edge-tts (khác giọng 0,224-0,297), KHÔNG lấy từ
#: chính bộ đối chứng — lấy từ bộ đối chứng là tự chọn số cho mình thắng.
NGUONG_GIONG = 0.30


def phu(a: float, b: float, vung) -> float:
    """Tỉ lệ thời lượng [a,b] nằm trong `vung`."""
    d = max(1e-9, b - a)
    s = 0.0
    for x, y in vung:
        s += max(0.0, min(b, y) - max(a, x))
    return s / d


def main() -> None:
    from app.ai import ai_nguoi_noi as nn

    L2 = json.loads((SAN / "llm2.json").read_text(encoding="utf-8"))
    EC = json.loads((SAN / "ecapa.json").read_text(encoding="utf-8"))

    BANG = {}
    for ten, vung in SU_THAT.items():
        d = json.loads((SAN / f"chep_{ten}.json").read_text(encoding="utf-8"))
        doan = nn.doan_tu_cau(d["cau"])
        llm = {int(k): v["ai"] for k, v in L2[ten].items()}
        giong = {int(k): v for k, v in EC[ten]["diem"].items()} if ten in EC \
            else {}
        that = {}
        for x in doan:
            p = phu(x.start, x.end, vung)
            that[x.i] = ("giu" if p >= TY_LE_GIU
                         else "pha" if p >= TY_LE_PHA else "long")
        BANG[ten] = {"doan": doan, "llm": llm, "giong": giong, "that": that}

    ARM = (("chi LLM", True, False),
           ("chi GIONG", False, True),
           ("LLM hoac GIONG", True, True))

    for nhan, dung_llm, dung_giong in ARM:
        print(f"\n{'='*74}\nARM: {nhan}\n{'='*74}")
        T = {"giu_dung": 0, "giu_tong": 0, "long_oan": 0,
             "bo_sot": 0, "long_tong": 0, "pha_bat": 0, "pha_tong": 0}
        for ten, v in BANG.items():
            doan, that = v["doan"], v["that"]
            kq, tt = nn.quyet_dinh(
                doan,
                llm=v["llm"] if dung_llm else None,
                giong=v["giong"] if dung_giong else None,
                nguong_giong=NGUONG_GIONG if dung_giong else None,
                can_so_dau=1)
            theo_i = {k.i: k for k in kq}
            gd = go = bs = lt = pb = pt = 0
            sai_bs = []
            for x in doan:
                k = theo_i[x.i]
                if that[x.i] == "giu":
                    if k.giu:
                        gd += 1
                    else:
                        go += 1
                elif that[x.i] == "pha":
                    pt += 1
                    pb += 1 if k.giu else 0
                else:
                    lt += 1
                    if k.giu:
                        bs += 1
                        sai_bs.append(x)
            T["giu_dung"] += gd
            T["giu_tong"] += gd + go
            T["long_oan"] += go
            T["bo_sot"] += bs
            T["long_tong"] += lt
            T["pha_bat"] += pb
            T["pha_tong"] += pt
            print(f"  {ten:16s} that-giu {gd + go} | BAT DUNG {gd} | "
                  f"LONG OAN {go} | pha {pb}/{pt} | "
                  f"bo sot nguoi ke {bs}/{lt} | huy_tran={tt.huy_vi_vuot_tran}")
            for x in sai_bs:
                print(f"       (bo sot) #{x.i:3d} [{x.start:7.2f}] "
                      f"{x.text[:40]}")
        gt = max(1, T["giu_tong"])
        lt = max(1, T["long_tong"])
        print(f"  {'-'*70}")
        print(f"  TONG: doan that-la-goc {T['giu_tong']} "
              f"| BAT DUNG {T['giu_dung']}/{T['giu_tong']} = "
              f"{T['giu_dung']/gt*100:.1f}%")
        print(f"        LONG OAN {T['long_oan']}/{T['giu_tong']} = "
              f"{T['long_oan']/gt*100:.1f}%")
        print(f"        BO SOT nguoi ke {T['bo_sot']}/{T['long_tong']} = "
              f"{T['bo_sot']/lt*100:.2f}%")
        print(f"        doan PHA (nua no nua kia) bat duoc "
              f"{T['pha_bat']}/{T['pha_tong']}")

    # khoảng giữ gốc của arm tốt nhất, để nơi gọi dùng
    print(f"\n{'='*74}\nKHOANG GIU GOC (arm 'LLM hoac GIONG')\n{'='*74}")
    for ten, v in BANG.items():
        kq, tt = nn.quyet_dinh(v["doan"], llm=v["llm"], giong=v["giong"],
                               nguong_giong=NGUONG_GIONG, can_so_dau=1)
        kh = nn.khoang_giu_goc(kq, v["doan"])
        print(f"  {ten:16s} {kh}  (su that: {SU_THAT[ten]})")
        print("  " + nn.bao_cao(kq, tt, v["doan"]).replace("\n", "\n  "))


if __name__ == "__main__":
    main()
