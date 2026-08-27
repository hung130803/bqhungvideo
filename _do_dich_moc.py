# -*- coding: utf-8 -*-
"""ARM MỐC — chạy ĐÚNG đường dịch app đang đi (`thay_giong._dich_loat`) trên
bộ câu THẬT, ghi sổ TỪNG LƯỢT GỌI + bắt mã E/F ngay tại chỗ.

Ghi kết quả ra file NGAY SAU MỖI LƯỢT (lượt này dài, đừng để mất).
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _dich_do_chung as C                                    # noqa: E402


def mot_luot(ma_video: str, dich_sang: str, lan: int) -> dict:
    from app.core import thay_giong as TG
    cau, meta = C.doc_cau(ma_video)
    goc = [c["text"] for c in cau]
    so = C.SoGoi()
    so.bat()
    t0 = time.time()
    loi = ""
    try:
        bd = TG._dich_loat(cau, dich_sang, (meta.get("language") or "")[:2].lower())
    except Exception as e:                                    # noqa: BLE001
        loi = f"{type(e).__name__}: {e}"
        bd = list(goc)
    finally:
        so.tat()
    giay = round(time.time() - t0, 2)

    # ---- mã F: câu TRẢ NGUYÊN VĂN GỐC / RỖNG ------------------------------
    f_goc = [i for i in range(len(goc)) if bd[i].strip() == goc[i].strip()]
    f_rong = [i for i in range(len(goc)) if not bd[i].strip()]
    # ---- mã E: hệ chữ LẠ trong bản dịch ------------------------------------
    e_he = {}
    for i, t in enumerate(bd):
        h = C.he_chu(t)
        if h:
            e_he.setdefault(h, []).append(i)
    e_khong_dau = ([i for i, t in enumerate(bd)
                    if not C.co_dau_viet(t) and not C.he_chu(t)]
                   if C.__dict__ and dich_sang == "vi" else [])

    kq = {
        "video": ma_video, "dich_sang": dich_sang, "lan": lan,
        "so_cau": len(goc), "giay": giay, "loi": loi,
        "goi": so.tom_tat(), "goi_chi_tiet": so.muc,
        "F_tra_nguyen_goc": f_goc, "F_rong": f_rong,
        "E_he_chu_la": {k: v for k, v in e_he.items()},
        "E_khong_dau_viet": e_khong_dau,
        "ban_dich": bd, "goc": goc,
    }
    C.ghi(f"moc_{ma_video}_{dich_sang}_l{lan}.json", kq)
    g = so.tom_tat()
    print(f"[MỐC {ma_video} -> {dich_sang} lượt {lan}] {giay}s · "
          f"{g['so_luot']} lượt gọi (cắt {g['so_bi_cat']} · lỗi {g['so_loi']}) · "
          f"model {g['model']} · prompt max {g['prompt_token_max']} tok · "
          f"max_tokens min {g['max_tokens_min']}")
    print(f"   F: trả nguyên gốc {len(f_goc)} · rỗng {len(f_rong)} | "
          f"E: hệ chữ lạ {[(k, len(v)) for k, v in e_he.items()]} · "
          f"không dấu Việt {len(e_khong_dau)}")
    if loi:
        print("   LỖI:", loi)
    return kq


if __name__ == "__main__":
    viec = sys.argv[1:] or ["v396:vi:1", "v396:vi:2", "v396:en:1", "v148:vi:1"]
    for v in viec:
        mv, ds, ln = v.split(":")
        mot_luot(mv, ds, int(ln))
