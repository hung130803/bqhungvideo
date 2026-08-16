# -*- coding: utf-8 -*-
"""TỰ KIỂM THƯỚC CHẤM DỊCH — đo TỈ LỆ BẮT ĐÚNG CỦA CHÍNH THƯỚC.

**SỐ NÀY QUAN TRỌNG HƠN ĐIỂM DỊCH.** Repo vừa dính đúng bẫy "phép đo phát
chứng chỉ cho thứ vẫn hỏng": thước cũ cho **7,85-7,97/10** cho bản dịch có
`新片 -> "phim về chip"`. Nên trước khi tin một con số nào của
`app/ai/cham_dich.py`, phải bắt nó chứng minh nó bắt được lỗi.

HAI CHIỀU, thiếu chiều nào cũng vô dụng:
  · 30 bản dịch HỎNG CÓ CHỦ Ý (`_do_bo_hong.HONG`) -> thước phải TRƯỢT chúng
  · 20 bản dịch TỐT (`_do_bo_hong.TOT`)            -> thước phải CHO ĐẠT

BA QUYẾT ĐỊNH ĐO, đừng "dọn gọn" mất:
1. **TRỘN LẪN hỏng với tốt rồi mới gửi**, xáo TIỀN ĐỊNH (`random.Random(20260816)`).
   Hội đồng chấm CẢ LOẠT trong một prompt; đưa nguyên một khối toàn-hỏng là
   mồi cho model chấm gắt, đưa khối toàn-tốt là mồi cho nó chấm hiền — con số
   ra sẽ đẹp/xấu vì cách xếp bài chứ không vì thước.
2. **NHIỀU LƯỢT.** LLM không tiền định (CLAUDE.md đã đo 0% vs 39,1% trên cùng
   một mã). Chạy 1 lượt rồi báo số là tự lừa mình. Mặc định 2 lượt, `BQ_LUOT=n`.
3. **TÁCH THEO CỬA BẮT** (luật máy · hội đồng · thuật ngữ). Nếu gần như chỉ
   luật máy bắt thì phần LLM đắt tiền kia không kéo được gì, phải nói ra.

  .venv\\Scripts\\python -u _do_thuoc_dich.py
"""
from __future__ import annotations

import os
import random
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

from _do_bo_hong import HONG, LOAI, TOT           # noqa: E402
from app.ai import cham_dich as CD                # noqa: E402

SEED = 20260816
SO_LUOT = int(os.environ.get("BQ_LUOT", "2"))


def dung_bo() -> tuple[list, list, list]:
    """Trả (goc, dich, nhan) đã TRỘN LẪN và xáo tiền định.

    `nhan[i]` = mã lỗi (bản hỏng) hoặc `"TOT"`.
    """
    bo = [(g, d, ma) for ma, g, d in HONG] + [(g, d, "TOT") for g, d in TOT]
    random.Random(SEED).shuffle(bo)
    return [x[0] for x in bo], [x[1] for x in bo], [x[2] for x in bo]


def cua_bat(c: dict) -> str:
    """Cửa nào đã bắt câu này (để biết phần LLM có kéo được gì không).

    Từ v2 thước dùng NGƯỠNG RIÊNG TỪNG TRỤC, không còn MIN 4 trục >= 7,0 —
    nên phải kể ĐÍCH DANH trục nào tụt, chứ in một con số `diem` chung thì
    người đọc không biết câu bị bắt vì nghĩa hay vì văn phong.
    """
    ra = []
    if c.get("loi"):
        ra.append("máy:" + ",".join(c["loi"]))
    if c.get("thuat_ngu"):
        ra.append("thuật-ngữ")
    tut = [f"{k}={c[k]}" for k, v in CD.NGUONG_TRUC.items()
           if c.get(k) is not None and c[k] < v]
    if tut:
        ra.append("trục:" + ",".join(tut))
    return " + ".join(ra) or "(không cửa nào)"


def mot_luot(so: int) -> dict:
    goc, dich, nhan = dung_bo()
    t0 = time.time()
    kq = CD.cham_ban_dich(goc, dich, goc_ma="zh", dich_ma="vi")
    giay = time.time() - t0

    cau = kq["cau"]
    bat_theo_loai = {k: [0, 0] for k in LOAI}        # [bắt, tổng]
    oan: list[tuple[str, str, dict]] = []
    sot: list[tuple[str, str, str, dict]] = []
    tot_dat = tot_tong = 0

    for i, c in enumerate(cau):
        la_hong = nhan[i] != "TOT"
        truot = not c["dat"]
        if la_hong:
            bat_theo_loai[nhan[i]][1] += 1
            if truot:
                bat_theo_loai[nhan[i]][0] += 1
            else:
                sot.append((nhan[i], goc[i], dich[i], c))
        else:
            tot_tong += 1
            if not truot:
                tot_dat += 1
            else:
                oan.append((goc[i], dich[i], c))

    n_bat = sum(v[0] for v in bat_theo_loai.values())
    n_hong = sum(v[1] for v in bat_theo_loai.values())

    print(f"\n{'=' * 72}\nLƯỢT {so} — {giay:.1f}s "
          f"(hội đồng {len(CD.MODEL_HOI_DONG)} model + soát thuật ngữ)\n{'=' * 72}")
    print(f"BẮT ĐÚNG (bản HỎNG bị trượt): {n_bat}/{n_hong} = "
          f"{100.0 * n_bat / max(1, n_hong):.1f}%")
    print(f"KHÔNG KÊU OAN (bản TỐT được đạt): {tot_dat}/{tot_tong} = "
          f"{100.0 * tot_dat / max(1, tot_tong):.1f}%")
    print(f"không chấm được (không model nào trả lời): "
          f"{kq['khong_cham_duoc']}/{kq['tong']}")

    print("\nBẮT ĐÚNG THEO TỪNG LOẠI LỖI:")
    for k in LOAI:
        b, t = bat_theo_loai[k]
        print(f"  {k:<11} {b}/{t}" + ("" if b == t else "   <-- CÒN SÓT"))

    # Cửa nào đang gánh việc
    dem_cua = {"máy": 0, "thuật-ngữ": 0, "hội-đồng": 0}
    for i, c in enumerate(cau):
        if nhan[i] == "TOT" or c["dat"]:
            continue
        if c.get("loi"):
            dem_cua["máy"] += 1
        if c.get("thuat_ngu"):
            dem_cua["thuật-ngữ"] += 1
        if c.get("diem") is not None and c["diem"] < CD.NGUONG_DAT:
            dem_cua["hội-đồng"] += 1
    print(f"\nCỬA NÀO BẮT (một câu có thể bị nhiều cửa bắt): {dem_cua}")

    if sot:
        print(f"\n--- CÒN SÓT {len(sot)} bản HỎNG (thước cho ĐẠT) ---")
        for ma, g, d, c in sot:
            print(f"  [{ma}] {g[:34]}\n      -> {d[:64]}\n      điểm {c.get('diem')} "
                  f"· 4 trục {[c.get(k) for k in CD.TIEU_CHI]} · phiếu {c['so_phieu']}")
    if oan:
        print(f"\n--- KÊU OAN {len(oan)} bản TỐT (thước cho TRƯỢT) ---")
        for g, d, c in oan:
            print(f"  {g[:34]}\n      -> {d[:64]}\n      {cua_bat(c)} "
                  f"· 4 trục {[c.get(k) for k in CD.TIEU_CHI]}")

    # ---- PHÂN BỐ ĐIỂM, để HIỆU CHUẨN NGƯỠNG BẰNG SỐ chứ không chỉnh mò ----
    # Cách làm giống `_do_cjk_calib.py`: đo cả 2 nhóm rồi tìm xem có KHOẢNG
    # TRỐNG nào giữa chúng không. Không có khoảng trống thì đổi ngưỡng chỉ là
    # đổi chỗ bị đau, phải sửa CÔNG THỨC chứ không phải con số.
    pb = {"HONG": [], "TOT": []}
    pb_tb = {"HONG": [], "TOT": []}
    tn_oan: list[tuple[str, list]] = []
    for i, c in enumerate(cau):
        k = "TOT" if nhan[i] == "TOT" else "HONG"
        if c.get("diem") is not None:
            pb[k].append(c["diem"])
            pb_tb[k].append(c["diem_tb"])
        if nhan[i] == "TOT" and c.get("thuat_ngu"):
            tn_oan.append((dich[i][:50], c["thuat_ngu"]))

    for k in ("HONG", "TOT"):
        v = sorted(pb[k])
        if v:
            print(f"\nPHÂN BỐ `diem` (=MIN 4 trục) nhóm {k}: n={len(v)} "
                  f"· thấp {v[0]} · 25% {v[len(v) // 4]} · giữa {v[len(v) // 2]} "
                  f"· 75% {v[3 * len(v) // 4]} · cao {v[-1]}")
            print(f"    {v}")
    if tn_oan:
        print(f"\n  soát-thuật-ngữ KÊU OAN {len(tn_oan)} câu tốt:")
        for d, t in tn_oan:
            print(f"    {d} <- {t}")

    return {"bat": n_bat, "hong": n_hong, "tot_dat": tot_dat,
            "tot_tong": tot_tong, "theo_loai": bat_theo_loai,
            "cua": dem_cua, "giay": giay, "pb": pb, "pb_tb": pb_tb,
            "cau": cau, "nhan": nhan}


def main() -> int:
    print("=" * 72)
    print("TỰ KIỂM THƯỚC CHẤM DỊCH — 30 bản HỎNG + 20 bản TỐT, TRỘN LẪN")
    print(f"ngưỡng đạt {CD.NGUONG_DAT} · hội đồng {CD.MODEL_HOI_DONG}")
    print("=" * 72)

    luot = [mot_luot(i + 1) for i in range(SO_LUOT)]

    print(f"\n{'=' * 72}\nTỔNG {SO_LUOT} LƯỢT\n{'=' * 72}")
    tb_bat = sum(100.0 * l["bat"] / max(1, l["hong"]) for l in luot) / len(luot)
    tb_oan = sum(100.0 * l["tot_dat"] / max(1, l["tot_tong"])
                 for l in luot) / len(luot)
    print("  lượt | bắt đúng (hỏng) | không kêu oan (tốt) | giây")
    for i, l in enumerate(luot):
        print(f"  {i + 1:<4} | {l['bat']}/{l['hong']} = "
              f"{100.0 * l['bat'] / max(1, l['hong']):5.1f}%     | "
              f"{l['tot_dat']}/{l['tot_tong']} = "
              f"{100.0 * l['tot_dat'] / max(1, l['tot_tong']):5.1f}%       | "
              f"{l['giay']:.0f}")
    print(f"\n  TỈ LỆ BẮT ĐÚNG TRUNG BÌNH:  {tb_bat:.1f}%")
    print(f"  TỈ LỆ KHÔNG KÊU OAN TB:     {tb_oan:.1f}%")

    print("\n  bắt đúng theo loại (cộng mọi lượt):")
    for k in LOAI:
        b = sum(l["theo_loai"][k][0] for l in luot)
        t = sum(l["theo_loai"][k][1] for l in luot)
        print(f"    {k:<11} {b}/{t} = {100.0 * b / max(1, t):5.1f}%")

    # ---- QUÉT NGƯỠNG: ngưỡng nào cho tổng lỗi thấp nhất? ----
    # Chỉ xét cửa HỘI ĐỒNG (luật máy + thuật ngữ là chốt riêng, không có
    # ngưỡng để chỉnh). Bảng này trả lời câu "hạ ngưỡng thì mất bao nhiêu
    # khả năng bắt" — không có bảng thì mọi lời bàn về ngưỡng chỉ là ý kiến.
    print("\n  QUÉT NGƯỠNG (chỉ cửa hội đồng, bỏ qua luật máy/thuật ngữ):")
    print("    ngưỡng | hỏng bị bắt | tốt bị kêu oan")
    gom_h = [x for l in luot for x in l["pb"]["HONG"]]
    gom_t = [x for l in luot for x in l["pb"]["TOT"]]
    for ng in [4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5]:
        bh = sum(1 for x in gom_h if x < ng)
        ot = sum(1 for x in gom_t if x < ng)
        print(f"    {ng:>5.1f}  | {bh:>3}/{len(gom_h)} = "
              f"{100.0 * bh / max(1, len(gom_h)):5.1f}% | "
              f"{ot:>3}/{len(gom_t)} = {100.0 * ot / max(1, len(gom_t)):5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
