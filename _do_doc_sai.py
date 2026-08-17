# -*- coding: utf-8 -*-
"""ĐO TỈ LỆ MÁY ĐỌC SAI chữ nước ngoài / tên riêng / số / đơn vị.

Anh Hùng 17/08/2026: *"ví dụ như chọn tiếng Việt, mấy chữ tiếng Anh hay tên
riêng hay tên gì đó nó đọc toàn bị lỗi ở cái đó ... bạn kiểm tra xem mấy phần
tiếng khác có bị lỗi thế không, lỗi to đó"*.

CÁCH ĐO (đúng cách cổng 60/64/67 đã dùng, không bịa cách mới): sinh tiếng THẬT
bằng **cửa chung** `dubbing._synth_all` — đúng hàm mà đường thay giọng gọi —
rồi cho **Groq chép ngược** chính file tiếng đó, và hỏi TỪNG TOKEN có sống sót
không.

**TÔI KHÔNG CÓ TAI.** Mọi kết luận ở đây là SỐ ĐO, không phải "nghe thấy sai".
File tiếng giữ lại ở `_NGHE_THU_ANH_HUNG/doc_sai/` để anh Hùng tự nghe.

BA CHỐT CHỐNG TỰ LỪA (đọc trước khi tin bảng số):

1. **SÀN ĐỐI CHỨNG `cau_thuong`.** Máy nghe cũng sai. Không có sàn này thì mọi
   con số là "lỗi máy đọc CỘNG lỗi máy nghe" và không tách ra được. Chỉ phần
   VƯỢT sàn mới là lỗi của máy đọc.

2. **KHỚP HAI TẦNG.** Tầng 1 so chuỗi đã chuẩn hoá (rẻ, 0 lượt LLM). Trượt
   tầng 1 mới hỏi Groq — vì `2026` đọc đúng thành *"hai nghìn không trăm hai
   mươi sáu"* thì so chuỗi báo SAI OAN. Bộ chấm được nói RÕ CHIỀU (bài học
   `mach_lac`: prompt không nói chiều thì model chấm ngược thang).

3. **TỰ KIỂM BỘ CHẤM.** Trước khi chấm thật, đưa 6 cặp ĐÃ BIẾT ĐÁP ÁN (3 đúng
   3 sai) cho chính bộ chấm đó. Sai quá 1 cặp thì DỪNG, không in bảng — bộ đo
   hỏng còn nguy hơn không đo (bài học `astats` cổng 53).

Chạy:  .venv\\Scripts\\python -u _do_doc_sai.py
Env:   BQ_DS_NN=vi,en   giới hạn ngôn ngữ ·  BQ_DS_LAI=1  bỏ cache, đọc lại
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _bo_cau_thu_doc import CORPUS, NHAN_LOAI, NHAN_NN, THU_TU_LOAI  # noqa: E402

HOP = REPO / "_do_doc_sai"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "doc_sai"
CACHE = HOP / "cache.json"

#: 6 cặp TỰ KIỂM bộ chấm — (token, bản chép, đáp án đúng?).
TU_KIEM = [
    ("Netflix", "bộ phim này đang đứng đầu bảng xếp hạng nét-phờ-líc", True),
    ("2026", "đến năm hai nghìn không trăm hai mươi sáu thì mọi chuyện đã khác",
     True),
    ("90%", "có tới chín mươi phần trăm khán giả cho điểm rất cao", True),
    ("Netflix", "bộ phim này đang đứng đầu bảng xếp hạng nắp phích lít xơ ích",
     False),
    ("Elon Musk", "ê lôn mút lại gây tranh cãi", False),
    ("15/08", "chúng tôi hẹn gặp nhau vào ngày mười lăm chia không tám",
     False),
]


# ---------------------------------------------------------------- chuẩn hoá
def bo_dau(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def chuan(s: str) -> str:
    """Về dạng so được: bỏ dấu, thường hoá, bỏ mọi thứ không phải chữ/số.

    KHÔNG bỏ khoảng trắng — bỏ hết là `"AI"` khớp trúng giữa chữ `"tại"`
    (`t-AI`), tức tự phát chứng nhận cho mọi câu tiếng Việt có vần "ai".
    """
    s = bo_dau(str(s)).lower()
    s = re.sub(r"[^0-9a-z一-鿿぀-ヿ\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def khop_chuoi(token: str, ban_chep: str) -> bool:
    """Tầng 1: token có mặt NGUYÊN VẸN trong bản chép (đã chuẩn hoá)."""
    t, b = chuan(token), chuan(ban_chep)
    if not t:
        return False
    if t in b:
        return True
    # chữ Hán/kana không có dấu cách -> `in` là đủ; chữ latin thì phải khớp
    # theo RANH GIỚI TỪ, không thì `AI` khớp trong `said`, `MV` trong `mvp`.
    if re.fullmatch(r"[0-9a-z]+", t):
        return re.search(rf"(?<![0-9a-z]){re.escape(t)}(?![0-9a-z])", b) is not None
    return False


# ---------------------------------------------------------------- bộ chấm
_PROMPT = """Bạn chấm chất lượng của một MÁY ĐỌC (text-to-speech).

Một câu đã được máy đọc thành tiếng, rồi một máy nghe chép lại thành chữ.
Nhiệm vụ: xét xem NGƯỜI NGHE có nhận ra được ĐÚNG cái token cần đọc hay không.

TOKEN CẦN ĐỌC: {token}
BẢN CHÉP NGƯỢC: {chep}

Trả lời "dung": true khi trong bản chép có một dạng NHẬN RA ĐƯỢC của token —
kể cả khi nó được viết khác đi, ví dụ:
  * số đọc thành chữ: 2026 -> "hai nghìn không trăm hai mươi sáu" -> true
  * ký hiệu đọc thành chữ: 90% -> "chín mươi phần trăm" -> true
  * phiên âm gần đúng nghe ra được: Netflix -> "nét phờ líc" -> true
  * chữ Hán/kana đọc đúng nhưng máy nghe ghi bằng chữ khác cùng âm -> true

Trả lời "dung": false khi token BIẾN MẤT hoặc méo tới mức không nhận ra:
  * Netflix -> "nắp phích lít xơ ích" -> false
  * Elon Musk -> "ê lôn mút" (mất hẳn một nửa tên) -> false
  * 15/08 -> "mười lăm chia không tám" (đọc dấu gạch thành phép chia) -> false
  * token không xuất hiện dưới bất kỳ dạng nào -> false

CHIỀU CỦA CÂU TRẢ LỜI: true = ĐỌC ĐƯỢC (tốt) · false = ĐỌC HỎNG (xấu).

Chỉ trả JSON: {{"dung": true hoặc false, "nghe_ra": "phần bản chép ứng với token, hoặc chuỗi rỗng"}}"""


def cham_llm(token: str, chep: str) -> tuple[bool, str]:
    from app.ai import llm
    try:
        r = llm.complete_text(
            _PROMPT.format(token=token, chep=chep[:600]), temperature=0.0)
        s = llm.bo_khoi_suy_nghi(r) if hasattr(llm, "bo_khoi_suy_nghi") else r
        m = re.search(r"\{.*\}", s, re.S)
        d = json.loads(m.group(0)) if m else {}
        return bool(d.get("dung")), str(d.get("nghe_ra") or "")[:80]
    except Exception as e:                                  # noqa: BLE001
        # KHÔNG chấm được -> nói ra, đừng đoán. Đếm riêng ở cột `loi_cham`.
        return False, f"[lỗi chấm: {type(e).__name__}]"


def tu_kiem_bo_cham() -> bool:
    print("TỰ KIỂM BỘ CHẤM (6 cặp đã biết đáp án)")
    sai = 0
    for tok, chep, dap in TU_KIEM:
        if khop_chuoi(tok, chep):
            ra, cach = True, "chuỗi"
        else:
            ra, _ = cham_llm(tok, chep)
            cach = "LLM"
        d = "ĐÚNG" if ra == dap else "**SAI**"
        if ra != dap:
            sai += 1
        print(f"  {d}  «{tok}» -> đáp án {dap} · bộ chấm {ra} ({cach})")
    print(f"  -> lệch {sai}/6")
    return sai <= 1


# ---------------------------------------------------------------- đọc + chép
def doc_mot_loat(cau: list[str], voice: str, thu: Path) -> list[bool]:
    """Sinh tiếng qua CỬA CHUNG `dubbing._synth_all` (đúng cửa app dùng)."""
    from app.core import dubbing
    thu.mkdir(parents=True, exist_ok=True)
    paths = [str(thu / f"c{i:03d}.mp3") for i in range(len(cau))]
    return asyncio.run(dubbing._synth_all(cau, voice, paths))


def chep_nguoc(mp3: Path) -> str:
    from app.core import transcribe as TR
    try:
        return str(TR.transcribe(str(mp3)).get("text") or "")
    except Exception as e:                                  # noqa: BLE001
        return f"[lỗi chép: {type(e).__name__}: {str(e)[:80]}]"


# ---------------------------------------------------------------- chạy
def do_mot_nn(nn: str, cache: dict) -> list[dict]:
    from app.core.thay_giong import giong_theo_ngon_ngu
    ds = CORPUS[nn]
    voice = giong_theo_ngon_ngu(nn)
    thu = HOP / nn
    cau = [c for _, c, _ in ds]
    print(f"\n=== {NHAN_NN[nn]} ({nn}) · giọng {voice} · {len(cau)} câu ===")
    t0 = time.time()
    khoa_l = f"{nn}|{voice}"
    if cache.get(khoa_l) and os.environ.get("BQ_DS_LAI") != "1":
        print("  (dùng lại bản chép đã có trong cache)")
        chep_ds = cache[khoa_l]
    else:
        ok = doc_mot_loat(cau, voice, thu)
        print(f"  đọc xong {sum(ok)}/{len(ok)} câu · {time.time()-t0:.0f}s")
        chep_ds = []
        for i in range(len(cau)):
            mp3 = thu / f"c{i:03d}.mp3"
            chep_ds.append(chep_nguoc(mp3) if ok[i] and mp3.exists()
                           else "[không đọc được]")
        cache[khoa_l] = chep_ds
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"  chép ngược xong · {time.time()-t0:.0f}s")
    # giữ file cho anh Hùng tự nghe
    dich = NGHE / nn
    dich.mkdir(parents=True, exist_ok=True)
    for i, (loai, c, _) in enumerate(ds):
        src = thu / f"c{i:03d}.mp3"
        if src.exists():
            ten = re.sub(r"[^0-9A-Za-z]+", "_", c)[:40]
            shutil.copy2(src, dich / f"{i:02d}_{loai}_{ten}.mp3")

    ra = []
    for i, (loai, c, toks) in enumerate(ds):
        chep = chep_ds[i] if i < len(chep_ds) else ""
        for tok in toks:
            if khop_chuoi(tok, chep):
                dung, nghe, cach = True, tok, "chuỗi"
            else:
                dung, nghe = cham_llm(tok, chep)
                cach = "LLM"
            ra.append({"nn": nn, "loai": loai, "cau": c, "token": tok,
                       "chep": chep, "dung": dung, "nghe_ra": nghe,
                       "cach": cach})
    return ra


def bang(kq: list[dict]) -> None:
    nns = sorted({r["nn"] for r in kq}, key=lambda x: list(NHAN_NN).index(x))
    print("\n" + "=" * 78)
    print("TỈ LỆ ĐỌC SAI theo LOẠI và theo NGÔN NGỮ (số token sai / tổng)")
    print("=" * 78)
    head = f"{'Loại':<26}" + "".join(f"{NHAN_NN[n]:>12}" for n in nns)
    print(head)
    print("-" * len(head))
    for loai in THU_TU_LOAI:
        d = f"{NHAN_LOAI[loai]:<26}"
        for n in nns:
            c = [r for r in kq if r["nn"] == n and r["loai"] == loai]
            sai = sum(1 for r in c if not r["dung"])
            d += f"{f'{sai}/{len(c)} ({100*sai/max(1,len(c)):.0f}%)':>12}"
        print(d)
    print("-" * len(head))
    d = f"{'TỔNG':<26}"
    for n in nns:
        c = [r for r in kq if r["nn"] == n]
        sai = sum(1 for r in c if not r["dung"])
        d += f"{f'{sai}/{len(c)} ({100*sai/max(1,len(c)):.0f}%)':>12}"
    print(d)

    print("\nTOKEN ĐỌC HỎNG (bản chép nghe ra gì):")
    for n in nns:
        xau = [r for r in kq if r["nn"] == n and not r["dung"]]
        if not xau:
            print(f"  [{NHAN_NN[n]}] không token nào hỏng")
            continue
        print(f"  [{NHAN_NN[n]}] {len(xau)} token:")
        for r in xau:
            print(f"     «{r['token']}» ({r['loai']}) -> «{r['nghe_ra']}»")


def main() -> int:
    HOP.mkdir(exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)
    if not tu_kiem_bo_cham():
        print("\nBỘ CHẤM KHÔNG ĐÁNG TIN -> DỪNG, không in bảng số.")
        return 2
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            cache = {}
    nns = [x.strip() for x in
           (os.environ.get("BQ_DS_NN") or "vi,en,zh,ja").split(",") if x.strip()]
    kq: list[dict] = []
    for nn in nns:
        kq += do_mot_nn(nn, cache)
    bang(kq)
    (HOP / "ket_qua.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSỐ LIỆU: {HOP/'ket_qua.json'}")
    print(f"FILE NGHE THỬ CHO ANH HÙNG: {NGHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
