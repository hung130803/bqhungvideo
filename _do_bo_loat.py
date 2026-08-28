# -*- coding: utf-8 -*-
"""NỢ 1 — VÌ SAO **MỘT** CÂU HỎNG LÀM BỎ CẢ LOẠT, VÀ CÂU NÀO HỎNG.

Nhật ký máy anh Hùng (`giong_vieneu_2026*.log`) — 7 lần "ghi ra file 0 giây",
**6/7 lần rơi đúng câu CUỐI CÙNG của loạt**:

    câu 64/65 · câu 67/68 (2 lần) · câu 142/143 (2 lần) · câu 167/168

Đó KHÔNG phải nhiễu ngẫu nhiên — nó là một hình dạng. Script này đi tìm hình
dạng ấy bằng cách gọi **thẳng tiến trình con** `_chay_vieneu` (tức ĐẦU RA THÔ
của model, trước mọi lớp logic của app) trên chữ THẬT.

BA PHÉP, chạy riêng bằng tham số dòng lệnh:
  · `nho`   — loạt NGẮN lặp nhiều lượt: câu cuối có hỏng nhiều hơn câu giữa
              không (đây là phép có ĐỐI CHỨNG, vì cùng bộ chữ đảo vị trí).
  · `that`  — đọc CẢ 167 câu tiếng Việt THẬT của video v396 một lượt.
  · `bien`  — chỉ đọc các câu NGẮN/kỳ dị (1-2 chữ, dấu câu) để xem chữ nào
              làm model trả mảng RỖNG.

KHÔNG đụng máy anh Hùng: mẫu giọng CHÉP sang hộp cát, hộp cát nằm trong repo
và dọn bằng `giong_vieneu._don` (chốt "chỉ xoá thứ nằm trong thư mục VieNeu").
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from app.core import giong_vieneu as gv                       # noqa: E402

HOP = REPO / "_kq_bo_loat"
HOP.mkdir(exist_ok=True)


def _mau() -> str:
    """Mẫu giọng nhân bản — CHÉP sang hộp cát, không đọc thẳng máy anh Hùng."""
    goc = Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo" / "_mau_giong" / "test.wav"
    if not goc.is_file():
        goc = REPO / "_mau_giong" / "giong_cua_toi.wav"
    dich = HOP / "mau.wav"
    if not dich.is_file():
        shutil.copy2(goc, dich)
    return str(dich)


def _doc_that() -> list[str]:
    d = json.loads((REPO / "_kq_dich" / "app_v396_vi_l1.json").read_text(
        encoding="utf-8"))
    return [str(t) for t in d["ban_dich"]]


def _chay(texts: list[str], ref: str, nhan: str) -> list[dict]:
    """Gọi tiến trình con THẬT, trả [{i, chu, giay}] — `giay` do CHÍNH app đo
    lại từ file (không tin số tiến trình con báo)."""
    sb = gv.thu_muc_vieneu() / f"_tam_dobo_{os.getpid()}_{int(time.time()) % 100000}"
    (sb / "raw").mkdir(parents=True, exist_ok=True)
    items = [{"i": i, "text": t, "raw": str(sb / "raw" / f"c{i:04d}.wav")}
             for i, t in enumerate(texts)]
    tt = gv.tinh_trang_vieneu()
    t0 = time.time()
    ket = gv._chay_vieneu(items, tt["python"], "", ref, 3600, None)
    giay = round(time.time() - t0, 1)
    ra = []
    if ket.get("ok"):
        theo = {int(r["i"]): r for r in ket.get("ra") or []}
        for i, t in enumerate(texts):
            r = theo.get(i)
            d = gv.dai_wav(Path(r["p"])) if r else -1.0
            ra.append({"i": i, "chu": t, "ky_tu": len(t),
                       "giay": round(d, 3), "co_ban_ghi": bool(r),
                       "giay_con_bao": (r or {}).get("giay")})
    else:
        print(f"  [{nhan}] tiến trình con HỎNG: {ket.get('loi')}")
    gv._don(sb)
    gv._don(Path(ket.get("_sandbox") or ""))
    hong = [x for x in ra if x["giay"] <= 0.02]
    print(f"  [{nhan}] {len(ra) - len(hong)}/{len(ra)} câu ra tiếng · "
          f"{giay}s · HỎNG: {[x['i'] for x in hong]}")
    return ra


def phep_nho(so_luot: int = 3) -> dict:
    """Loạt NGẮN, lặp nhiều lượt, MỖI LƯỢT ĐẢO THỨ TỰ.

    Đối chứng nằm ở chỗ đảo: nếu hỏng bám theo VỊ TRÍ CUỐI thì mỗi lượt một câu
    khác nhau hỏng; nếu bám theo CHỮ thì luôn cùng một câu hỏng dù nó đứng đâu.
    """
    goc = _doc_that()
    bo = goc[:11] + ["rằng"]          # 12 câu, câu cuối là câu ngắn thật (#86)
    ref = _mau()
    luot = []
    for k in range(so_luot):
        # lượt chẵn: giữ nguyên · lượt lẻ: ĐẢO NGƯỢC (câu cuối thành câu đầu)
        xs = list(bo) if k % 2 == 0 else list(reversed(bo))
        ra = _chay(xs, ref, f"nho l{k + 1}{'' if k % 2 == 0 else ' (đảo)'}")
        luot.append({"luot": k + 1, "dao": bool(k % 2), "ra": ra,
                     "hong_vi_tri": [x["i"] for x in ra if x["giay"] <= 0.02],
                     "hong_chu": [x["chu"] for x in ra if x["giay"] <= 0.02]})
    return {"phep": "nho", "so_cau": len(bo), "luot": luot}


def phep_that() -> dict:
    """167 câu tiếng Việt THẬT — đúng cỡ loạt anh Hùng chạy."""
    xs = _doc_that()
    ref = _mau()
    ra = _chay(xs, ref, f"that {len(xs)} câu")
    return {"phep": "that", "so_cau": len(xs), "ra": ra,
            "hong": [x["i"] for x in ra if x["giay"] <= 0.02]}


def phep_bien() -> dict:
    """Chữ ở BIÊN — 1-2 ký tự, chỉ dấu câu, chỉ số. Câu 1 ký tự có thật trong
    transcript anh Hùng (`现` — xem NỢ 3)."""
    xs = ["rằng", "Ừ", "A", ".", "...", "?", "1", "M", "Ê", "Vâng",
          "hả", "-", "Ô kê", "现", "Đó"]
    ref = _mau()
    ra = _chay(xs, ref, "biên")
    return {"phep": "bien", "so_cau": len(xs), "ra": ra,
            "hong": [(x["i"], x["chu"]) for x in ra if x["giay"] <= 0.02]}


if __name__ == "__main__":
    ten = sys.argv[1] if len(sys.argv) > 1 else "nho"
    print(f"== PHÉP {ten} ==")
    kq = {"nho": phep_nho, "that": phep_that, "bien": phep_bien}[ten]()
    p = HOP / f"{ten}.json"
    p.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print("ghi:", p)
