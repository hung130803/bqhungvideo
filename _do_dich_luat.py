# -*- coding: utf-8 -*-
"""QUÉT LUẬT GỘP trên phiếu thô đã dump — tìm luật hạ KÊU OAN mà giữ BẮT ĐÚNG.

Đích của việc này (CLAUDE.md, VIỆC 1): **bắt đúng >= 90% · kêu oan <= 10%.**
Thước v1 đạt bắt 100% nhưng kêu oan 30% — nối vào đường dịch ở mức đó là cứ 3
câu dịch TỐT thì 1 câu bị đem đi dịch lại, mà bước dịch lại đã đo được là CÓ
CƠ LÀM XẤU ĐI (−0,58 .. −1,24 điểm).

MỌI LUẬT ĐƯỢC CHẤM TRÊN CÙNG MỘT BỘ PHIẾU nên hiệu số giữa chúng là hiệu số
của LUẬT, không lẫn nhiễu LLM (xem `_do_dich_calib.py`).

**CHỐNG TỰ LỪA — bắt buộc đọc trước khi tin bảng ở cuối:** quét vài nghìn luật
trên 50 câu thì luật thắng có thể chỉ đang HỌC THUỘC 50 câu đó. Vì vậy script
nhận HAI bộ file: bộ HIỆU CHUẨN (`BQ_CALIB`) để chọn luật, bộ KIỂM
(`BQ_KIEM`, lượt chạy KHÁC, seed khác) chỉ để BÁO SỐ. Số đáng tin là số trên
bộ KIỂM. Không có bộ kiểm thì script NÓI RÕ là chưa kiểm chéo.

  .venv\\Scripts\\python -u _do_dich_luat.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

from _do_bo_hong import LOAI                             # noqa: E402
from app.ai import cham_dich as CD                       # noqa: E402

TRUC = CD.TIEU_CHI                                       # nghia xuoi noi tron


# --------------------------------------------------------------------------
def nap(paths: list[Path]) -> list[dict]:
    """Trả list CÂU đã tính trung vị từng trục. Mỗi câu là một QUAN SÁT
    (cùng một cặp câu ở 2 lượt = 2 quan sát — đúng, vì LLM chấm khác nhau)."""
    ra: list[dict] = []
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        for lt in d["luot"]:
            for c in lt["cau"]:
                tv = {}
                for k in TRUC:
                    v = [c["cham"][m][k] for m in c["cham"]
                         if isinstance(c["cham"][m], dict) and k in c["cham"][m]]
                    tv[k] = statistics.median(v) if v else None
                ra.append({
                    "goc": c["goc"], "dich": c["dich"], "nhan": c["nhan"],
                    "loi_may": c["loi_may"], "tv": tv,
                    "tn": c["tn"], "luot": lt["so"], "file": p.name,
                    "so_phieu": sum(1 for m in c["cham"] if c["cham"][m]),
                })
    return ra


def tn_khoa(c: dict, can: int) -> list[str]:
    """Khoá lỗi thuật ngữ được >= `can` model cùng kêu. `can` >= 99 = TẮT cửa."""
    if can >= 99:
        return []
    dem: dict[str, int] = {}
    for m in c["tn"]:
        for k in c["tn"][m]:
            dem[k] = dem.get(k, 0) + 1
    return sorted(k for k, v in dem.items() if v >= can)


# --------------------------------------------------------------------------
# LUẬT — mỗi luật là (tên, hàm(câu) -> ĐẠT?)
# --------------------------------------------------------------------------
def luat_moc(c: dict) -> bool:
    """v1 đang chạy: luật máy + thuật ngữ(2/2 model) + MIN 4 trục >= 7,0."""
    if c["loi_may"] or tn_khoa(c, 2):
        return False
    tv = [c["tv"][k] for k in TRUC if c["tv"][k] is not None]
    return bool(tv) and min(tv) >= 7.0


def lam_luat(ng: dict, tn_can: int, tn_theo_nghia: float | None = None):
    """Sinh luật 'ngưỡng RIÊNG từng trục'.

    `ng` = {trục: ngưỡng}. `tn_theo_nghia` != None nghĩa là cửa thuật ngữ chỉ
    còn quyền phủ quyết khi `nghia` cũng dưới mức đó (thuật ngữ một mình là
    nguồn kêu oan chính — nhưng bỏ hẳn nó thì mất ca `新片 -> phim về chip`).
    """
    def f(c: dict) -> bool:
        if c["loi_may"]:
            return False
        if tn_khoa(c, tn_can):
            if tn_theo_nghia is None:
                return False
            n = c["tv"].get("nghia")
            if n is None or n < tn_theo_nghia:
                return False
        for k, v in ng.items():
            x = c["tv"].get(k)
            if x is None:
                continue                 # không ai chấm trục đó -> không kết tội
            if x < v:
                return False
        if all(c["tv"].get(k) is None for k in TRUC):
            return False                 # không một phiếu nào -> không có căn cứ
        return True
    return f


def cham_luat(cau: list[dict], f) -> dict:
    bat = hong = oan = tot = 0
    theo_loai = {k: [0, 0] for k in LOAI}
    ds_oan: list[dict] = []
    ds_sot: list[dict] = []
    for c in cau:
        dat = f(c)
        if c["nhan"] == "TOT":
            tot += 1
            if dat:
                pass
            else:
                oan += 1
                ds_oan.append(c)
        else:
            hong += 1
            theo_loai[c["nhan"]][1] += 1
            if not dat:
                bat += 1
                theo_loai[c["nhan"]][0] += 1
            else:
                ds_sot.append(c)
    return {"bat": bat, "hong": hong, "ty_bat": 100.0 * bat / max(1, hong),
            "oan": oan, "tot": tot, "ty_oan": 100.0 * oan / max(1, tot),
            "theo_loai": theo_loai, "ds_oan": ds_oan, "ds_sot": ds_sot}


# --------------------------------------------------------------------------
def in_phan_bo(cau: list[dict]) -> None:
    print("\nPHÂN BỐ TỪNG TRỤC (trung vị hội đồng) — tìm trục nào TÁCH được "
          "2 nhóm:")
    print("  trục   | HỎNG: thấp/25%/giữa/75%/cao | TỐT: thấp/25%/giữa/75%/cao "
          "| trùng nhau")
    for k in TRUC:
        h = sorted(c["tv"][k] for c in cau
                   if c["nhan"] != "TOT" and c["tv"][k] is not None)
        t = sorted(c["tv"][k] for c in cau
                   if c["nhan"] == "TOT" and c["tv"][k] is not None)
        if not h or not t:
            continue
        # AUC = xác suất một câu TỐT được chấm cao hơn một câu HỎNG
        n = 0
        for a in t:
            for b in h:
                n += 1 if a > b else (0.5 if a == b else 0)
        auc = n / (len(t) * len(h))

        def q(v):
            return (f"{v[0]:.0f}/{v[len(v)//4]:.0f}/{v[len(v)//2]:.0f}/"
                    f"{v[3*len(v)//4]:.0f}/{v[-1]:.0f}")
        print(f"  {k:<6} | {q(h):<27} | {q(t):<26} | AUC {auc:.3f}")
    print("  (AUC 1,000 = tách hoàn toàn · 0,500 = trục vô dụng)")


def in_cua(cau: list[dict]) -> None:
    print("\nTỪNG CỬA MỘT MÌNH (bắt bao nhiêu bản HỎNG · kêu oan bao nhiêu "
          "bản TỐT):")
    cua = {
        "luật máy": lambda c: not c["loi_may"],
        "thuật ngữ 1/3": lambda c: not tn_khoa(c, 1),
        "thuật ngữ 2/3": lambda c: not tn_khoa(c, 2),
        "thuật ngữ 3/3": lambda c: not tn_khoa(c, 3),
    }
    for k in TRUC:
        for ng in (5.0, 6.0, 7.0):
            cua[f"{k} >= {ng:.0f}"] = (
                lambda c, k=k, ng=ng: c["tv"][k] is None or c["tv"][k] >= ng)
    for ten, f in cua.items():
        r = cham_luat(cau, f)
        print(f"  {ten:<16} bắt {r['bat']:>3}/{r['hong']} = {r['ty_bat']:5.1f}%"
              f"  · kêu oan {r['oan']:>3}/{r['tot']} = {r['ty_oan']:5.1f}%")


def quet(cau: list[dict]) -> list[tuple]:
    """Quét lưới luật 'ngưỡng riêng từng trục'. Trả list (điểm, mô tả, tham số)."""
    ra = []
    buoc = [0.0, 3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 7.5, 8.0]
    for tn_can in (2, 3, 99):
        for tn_ng in (None, 6.0, 7.0):
            if tn_can >= 99 and tn_ng is not None:
                continue
            for a in buoc:                       # nghia
                for b in buoc:                   # xuoi
                    for cc in buoc:              # noi
                        for d in buoc:           # tron
                            ng = {"nghia": a, "xuoi": b, "noi": cc, "tron": d}
                            r = cham_luat(cau, lam_luat(ng, tn_can, tn_ng))
                            ra.append((r["ty_bat"], r["ty_oan"], ng, tn_can,
                                       tn_ng))
    return ra


#: DANH SÁCH NGẮN — luật SỐ TRÒN, chọn bằng ĐẦU chứ không bằng argmax của
#: lưới. Lưới quét ~46.000 luật trên 200 quan sát nên luật thắng lưới có thể
#: chỉ đang học thuộc bộ này; bảng dưới đây để so xem luật thắng có hơn hẳn
#: một luật đơn giản hay không, và luật nào ĐỨNG VỮNG sang bộ kiểm.
NGAN: list[tuple[str, dict, int, float | None]] = [
    ("v1 MIN>=7 · tn2/2", {}, 2, None),                       # xử lý riêng
    ("A nghia3 xuoi6 noi5 tron6 · tn3 · tn<6",
     {"nghia": 3.0, "xuoi": 6.0, "noi": 5.0, "tron": 6.0}, 3, 6.0),
    ("B nghia5 xuoi6 noi5 tron6 · tn3 · tn<6",
     {"nghia": 5.0, "xuoi": 6.0, "noi": 5.0, "tron": 6.0}, 3, 6.0),
    ("C nghia5 xuoi6 noi6 tron6 · tn3 · tn<6",
     {"nghia": 5.0, "xuoi": 6.0, "noi": 6.0, "tron": 6.0}, 3, 6.0),
    ("D nghia6 xuoi6 noi6 tron6 · tn3 · tn<6",
     {"nghia": 6.0, "xuoi": 6.0, "noi": 6.0, "tron": 6.0}, 3, 6.0),
    ("E nghia5 xuoi6 noi5 tron6 · tn3 · KHÔNG điều kiện",
     {"nghia": 5.0, "xuoi": 6.0, "noi": 5.0, "tron": 6.0}, 3, None),
    ("F nghia5 xuoi6 noi5 tron6 · TẮT cửa thuật ngữ",
     {"nghia": 5.0, "xuoi": 6.0, "noi": 5.0, "tron": 6.0}, 99, None),
    ("G nghia5 xuoi5 noi5 tron5 · tn3 · tn<6",
     {"nghia": 5.0, "xuoi": 5.0, "noi": 5.0, "tron": 5.0}, 3, 6.0),
    ("H MIN>=6 (chỉ hạ ngưỡng v1) · tn2/2", {}, 2, None),      # xử lý riêng
]


def _luat_min(nguong: float, tn_can: int):
    def f(c: dict) -> bool:
        if c["loi_may"] or tn_khoa(c, tn_can):
            return False
        tv = [c["tv"][k] for k in TRUC if c["tv"][k] is not None]
        return bool(tv) and min(tv) >= nguong
    return f


def in_ngan(c_cal: list[dict], c_kiem: list[dict]) -> None:
    print("\n" + "=" * 74)
    print("DANH SÁCH NGẮN — luật SỐ TRÒN, chấm trên CẢ HAI bộ")
    print("=" * 74)
    print(f"  {'luật':<44} | HIỆU CHUẨN bắt/oan | KIỂM CHÉO bắt/oan")
    for ten, ng, tn_can, tn_ng in NGAN:
        if ten.startswith("v1"):
            f = _luat_min(7.0, 2)
        elif ten.startswith("H "):
            f = _luat_min(6.0, 2)
        else:
            f = lam_luat(ng, tn_can, tn_ng)
        a = cham_luat(c_cal, f)
        b = cham_luat(c_kiem, f) if c_kiem else None
        s = (f"{b['ty_bat']:5.1f}% / {b['ty_oan']:5.1f}%" if b
             else "     (chưa có)     ")
        print(f"  {ten:<44} | {a['ty_bat']:5.1f}% / {a['ty_oan']:5.1f}%   "
              f"| {s}")
    print("\n  BẮT ĐÚNG THEO LOẠI LỖI (bộ KIỂM nếu có, không thì HIỆU CHUẨN):")
    bo = c_kiem or c_cal
    print(f"  {'luật':<44} | " + " | ".join(f"{k:<9}" for k in LOAI))
    for ten, ng, tn_can, tn_ng in NGAN:
        if ten.startswith("v1"):
            f = _luat_min(7.0, 2)
        elif ten.startswith("H "):
            f = _luat_min(6.0, 2)
        else:
            f = lam_luat(ng, tn_can, tn_ng)
        r = cham_luat(bo, f)
        o = []
        for k in LOAI:
            b_, t_ = r["theo_loai"][k]
            o.append(f"{b_:>3}/{t_:<3}  ")
        print(f"  {ten:<44} | " + " | ".join(o))


def main() -> int:
    calib = [REPO / x for x in
             os.environ.get("BQ_CALIB", "_do_dich_calib.json").split(";") if x]
    kiem = [REPO / x for x in os.environ.get("BQ_KIEM", "").split(";") if x]
    calib = [p for p in calib if p.exists()]
    kiem = [p for p in kiem if p.exists()]
    if not calib:
        print("Chưa có file dump. Chạy `_do_dich_calib.py` trước.")
        return 2

    c_cal = nap(calib)
    print("=" * 74)
    print(f"BỘ HIỆU CHUẨN: {[p.name for p in calib]} — {len(c_cal)} quan sát "
          f"({sum(1 for c in c_cal if c['nhan'] != 'TOT')} hỏng / "
          f"{sum(1 for c in c_cal if c['nhan'] == 'TOT')} tốt)")
    if kiem:
        c_kiem = nap(kiem)
        print(f"BỘ KIỂM CHÉO : {[p.name for p in kiem]} — {len(c_kiem)} quan sát")
    else:
        c_kiem = []
        print("BỘ KIỂM CHÉO : (CHƯA CÓ — mọi số dưới đây là số TRÊN CHÍNH BỘ "
              "ĐÃ DÙNG ĐỂ CHỌN LUẬT, đừng báo cáo như kết quả)")
    print("=" * 74)

    r0 = cham_luat(c_cal, luat_moc)
    print("\nMỐC (thước v1: MIN 4 trục >= 7,0 + thuật ngữ 2/2):")
    print(f"  bắt đúng {r0['bat']}/{r0['hong']} = {r0['ty_bat']:.1f}%  ·  "
          f"KÊU OAN {r0['oan']}/{r0['tot']} = {r0['ty_oan']:.1f}%")

    in_phan_bo(c_cal)
    in_cua(c_cal)
    in_ngan(c_cal, c_kiem)

    print("\n" + "=" * 74)
    print("QUÉT LƯỚI LUẬT 'NGƯỠNG RIÊNG TỪNG TRỤC'")
    print("=" * 74)
    ds = quet(c_cal)

    # --- Pareto: với mỗi mức kêu oan, luật nào bắt được nhiều nhất ---
    print("\nBIÊN ĐÁNH ĐỔI (mỗi mức KÊU OAN -> luật BẮT ĐƯỢC NHIỀU NHẤT):")
    print("  kêu oan <= | bắt đúng | nghia xuoi  noi tron | tn_can tn_theo_nghia")
    tot_nhat = None
    for tran in (0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 30.0):
        hop = [x for x in ds if x[1] <= tran]
        if not hop:
            continue
        # ưu tiên bắt cao; hoà thì lấy kêu oan thấp; hoà nữa lấy ngưỡng CAO
        # (ngưỡng cao = luật chặt hơn = ít phụ thuộc may mắn của bộ này)
        b = max(hop, key=lambda x: (x[0], -x[1], sum(x[2].values())))
        ng = b[2]
        print(f"  {tran:>9.1f}% | {b[0]:7.1f}% | "
              f"{ng['nghia']:5.1f}{ng['xuoi']:5.1f}{ng['noi']:5.1f}"
              f"{ng['tron']:5.1f} | {b[3]:>6} {str(b[4]):>13}")
        if tran <= 10.0 and b[0] >= 90.0:
            tot_nhat = b
    if tot_nhat is None:
        # không luật nào đạt đích -> lấy luật tốt nhất ở mức oan <= 10%
        hop = [x for x in ds if x[1] <= 10.0]
        if hop:
            tot_nhat = max(hop, key=lambda x: (x[0], -x[1]))

    if tot_nhat:
        ng, tn_can, tn_ng = tot_nhat[2], tot_nhat[3], tot_nhat[4]
        print("\nLUẬT CHỌN (đích: bắt >= 90% · oan <= 10%):")
        print(f"  ngưỡng {ng} · thuật ngữ cần {tn_can} model"
              f" · thuật ngữ chỉ phủ quyết khi nghia < {tn_ng}")
        f = lam_luat(ng, tn_can, tn_ng)
        for ten, bo in (("HIỆU CHUẨN", c_cal), ("KIỂM CHÉO", c_kiem)):
            if not bo:
                continue
            r = cham_luat(bo, f)
            rm = cham_luat(bo, luat_moc)
            print(f"\n  --- {ten} ({len(bo)} quan sát) ---")
            print(f"    MỐC v1 : bắt {rm['ty_bat']:5.1f}% · kêu oan "
                  f"{rm['ty_oan']:5.1f}%")
            print(f"    LUẬT MỚI: bắt {r['ty_bat']:5.1f}% ({r['bat']}/{r['hong']})"
                  f" · kêu oan {r['ty_oan']:5.1f}% ({r['oan']}/{r['tot']})")
            print("    bắt đúng theo loại lỗi:")
            for k in LOAI:
                b, t = r["theo_loai"][k]
                print(f"      {k:<11} {b:>3}/{t:<3} = {100.0*b/max(1,t):5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
