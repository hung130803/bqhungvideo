# -*- coding: utf-8 -*-
"""B2 — THỬ CÁCH SỬA *TRƯỚC KHI* VIẾT VÀO APP: chuyển tự sang âm Việt.

`_do_ssml.py` đã đóng đường SSML (edge-tts escape thẻ, đọc thành tiếng).
`_do_doc_roi.py` đã khoanh vùng bệnh: **chỉ tiếng Việt** mới vượt trần, và chỉ
ở 2 loại **tên riêng** + **viết tắt**; số/ngày/đơn vị đã 0% ở cả 4 ngôn ngữ.

Còn đúng một câu hỏi: **chuyển tự có ăn không?** Nối vào app rồi mới đo là
cách làm ngược — `dich_va_soat` và `dich_theo_gio` đều bị bác BẰNG SỐ ở đúng
chỗ này, sau khi đã đo. Làm y như thế.

CÁCH ĐO: đúng bộ token của `_do_doc_roi.py`, đúng cửa chung `dubbing._synth_all`,
giọng Việt, **2 arm ĐAN XEN** trong cùng một lượt:
  * arm THÔ   — token nguyên văn (đường app đang chạy)
  * arm PHIÊN ÂM — token đã chuyển tự sang âm Việt

**PHẢI ĐO CẢ CHIỀU XẤU ĐI.** Bảng in đủ 3 cột: tốt lên · TỆ ĐI · y nguyên. Chỉ
khoe cột "tốt lên" là đúng cái bẫy `_do_co_gian_ab` đã bắt (27 tốt lên nhưng
32 TỆ ĐI, tổng lại là hoà).

Chạy:  .venv\\Scripts\\python -u _do_phien_am.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_doc_roi import token_theo_nn  # noqa: E402
from _do_doc_sai import cham_llm, chep_nguoc, khop_chuoi  # noqa: E402

HOP = REPO / "_do_phien_am"
GIONG_VI = "vi-VN-HoaiMyNeural"

#: TÊN CHỮ CÁI kiểu ANH, viết bằng âm Việt.
#: GỐC BỆNH ĐO ĐƯỢC: giọng Việt đánh vần bằng TÊN CHỮ CÁI VIỆT (G = "dê",
#: D = "đê", P = "pê") nên `GDP` ra "dê-dê-pê" -> máy nghe chép thành **DDP**.
#: Người Việt thì đọc viết tắt bằng tên chữ cái ANH ("gi-đi-pi").
CHU_ANH = {
    "A": "ây", "B": "bi", "C": "xi", "D": "đi", "E": "i", "F": "ép",
    "G": "gi", "H": "ếch", "I": "ai", "J": "giay", "K": "kây", "L": "eo",
    "M": "em", "N": "en", "O": "âu", "P": "pi", "Q": "kiu", "R": "a",
    "S": "ét", "T": "ti", "U": "diu", "V": "vi", "W": "đắp liu", "X": "ích",
    "Y": "quai", "Z": "dét",
}

#: TÊN RIÊNG — chỉ chép âm cho mấy cái ĐO RA HỎNG, không làm bảng bao la.
#: Bảng càng to càng nhiều cơ hội làm HỎNG cái đang chạy tốt (`Netflix`,
#: `iPhone`, `YouTube` hiện ĐANG ĐÚNG — đụng vào là lỗ).
TEN_RIENG = {
    "marvel": "Ma-veo",
    "tiktok": "Tíc-tóc",
    "view": "viu",
    "netflix": "Nét-phờ-lích",       # đang ĐÚNG — đưa vào để ĐO xem có tệ đi
    "youtube": "Diu-túp",            # đang ĐÚNG — đo chiều xấu
    "iphone": "Ai-phôn",             # đang ĐÚNG — đo chiều xấu
    "elon musk": "I-lon Mátx",
}


def phien_am(tok: str) -> str:
    """Đổi token sang âm Việt. Trả NGUYÊN VĂN nếu không biết cách đọc."""
    t = tok.strip()
    if t.lower() in TEN_RIENG:
        return TEN_RIENG[t.lower()]
    # VIẾT TẮT = chuỗi 2-5 chữ cái HOA liền nhau, không có nguyên âm thành từ.
    if re.fullmatch(r"[A-Z]{2,5}", t):
        return " ".join(CHU_ANH.get(c, c) for c in t)
    return t


def doc_loat(texts: list[str], thu: Path) -> list[bool]:
    from app.core import dubbing
    thu.mkdir(parents=True, exist_ok=True)
    paths = [str(thu / f"t{i:03d}.mp3") for i in range(len(texts))]
    return asyncio.run(dubbing._synth_all(texts, GIONG_VI, paths))


def cham(toks, chep_ds) -> list[bool]:
    ra = []
    for (_loai, tok), chep in zip(toks, chep_ds):
        if khop_chuoi(tok, chep):
            ra.append(True)
        else:
            d, _ = cham_llm(tok, chep)
            ra.append(d)
    return ra


def main() -> int:
    HOP.mkdir(exist_ok=True)
    toks = token_theo_nn("vi")
    tho = [t for _l, t in toks]
    pa = [phien_am(t) for t in tho]
    doi = [(a, b) for a, b in zip(tho, pa) if a != b]
    print(f"{len(toks)} token · {len(doi)} token có phiên âm khác bản thô")
    for a, b in doi:
        print(f"   «{a}» -> «{b}»")

    t0 = time.time()
    ok_a = doc_loat(tho, HOP / "tho")
    ok_b = doc_loat(pa, HOP / "pa")
    print(f"\nđọc xong · thô {sum(ok_a)}/{len(ok_a)} · phiên âm "
          f"{sum(ok_b)}/{len(ok_b)} · {time.time()-t0:.0f}s")

    chep_a, chep_b = [], []
    for i in range(len(toks)):
        pa_ = HOP / "tho" / f"t{i:03d}.mp3"
        pb_ = HOP / "pa" / f"t{i:03d}.mp3"
        chep_a.append(chep_nguoc(pa_) if ok_a[i] and pa_.exists() else "[hỏng]")
        chep_b.append(chep_nguoc(pb_) if ok_b[i] and pb_.exists() else "[hỏng]")
    print(f"chép ngược xong · {time.time()-t0:.0f}s")

    da, db = cham(toks, chep_a), cham(toks, chep_b)
    tot = sum(1 for x, y in zip(da, db) if not x and y)
    te = sum(1 for x, y in zip(da, db) if x and not y)
    nguyen = sum(1 for x, y in zip(da, db) if x == y)

    print("\n" + "=" * 74)
    print("CHUYỂN TỰ SANG ÂM VIỆT — GHÉP CẶP TỪNG TOKEN (cùng giọng, cùng lượt)")
    print("=" * 74)
    print(f"{'':<20}{'THÔ':>10}{'PHIÊN ÂM':>12}")
    print(f"{'token đọc HỎNG':<20}{f'{len(da)-sum(da)}/{len(da)}':>10}"
          f"{f'{len(db)-sum(db)}/{len(db)}':>12}")
    print(f"{'tỉ lệ hỏng':<20}{f'{100*(1-sum(da)/len(da)):.0f}%':>10}"
          f"{f'{100*(1-sum(db)/len(db)):.0f}%':>12}")
    print(f"\nGHÉP CẶP:  TỐT LÊN {tot} · **TỆ ĐI {te}** · y nguyên {nguyen}")

    print("\nCHI TIẾT từng token đổi trạng thái:")
    for (loai, tok), x, y, ca, cb in zip(toks, da, db, chep_a, chep_b):
        if x != y:
            m = "TỐT LÊN " if y else "TỆ ĐI   "
            print(f"  {m} «{tok}» ({loai})")
            print(f"      thô     -> «{ca.strip()[:60]}»")
            print(f"      phiên âm-> «{cb.strip()[:60]}»")

    json.dump({"toks": [t for _l, t in toks], "pa": pa,
               "chep_tho": chep_a, "chep_pa": chep_b,
               "dung_tho": da, "dung_pa": db},
              open(HOP / "ket_qua.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nSỐ LIỆU: {HOP/'ket_qua.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
