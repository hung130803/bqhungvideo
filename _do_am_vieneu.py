# -*- coding: utf-8 -*-
"""VIENEU CÓ **PHIÊN ÂM ĐƯỢC** TIẾNG NÀY KHÔNG — đo ở tầng G2P, không cần GPU.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CẦN PHÉP ĐO NÀY (nó trả lời câu mà `_do_lan_nn.py` KHÔNG trả lời được)
═══════════════════════════════════════════════════════════════════════════
`_do_lan_nn.py` đo *"đọc ra có đúng chữ không"* trên 4 tiếng và ra ba kiểu số
KHÔNG so được với nhau:

  · **Việt** — đọc được thật, `vnb:` trả 59/59, số có nghĩa.
  · **Trung · Nhật** — `vnb:` trả **24/58**, arm bị đóng dấu KHÔNG HỢP LỆ:
    đúng 24 mục đó là **token rời chữ Latin** (Netflix · TikTok · iPhone…),
    còn 34 CÂU thì máy nhân bản không ra gì và `dubbing._synth_all` **lùi êm
    về edge-tts**. Bảng ghi "0/34 câu" chứ không ghi được bệnh.
  · **Hàn** — `vnb:` trả **58/58 HỢP LỆ** (không lùi!) nhưng WER **308-351%**
    và Groq dán nhãn tiếng **0-1/34** câu là tiếng Hàn. Tức máy CÓ đọc, và
    thứ nó đọc ra không phải tiếng Hàn.

Ba kiểu số ấy chỉ có một cách giải thích chung, và nó nằm ở tầng **PHIÊN ÂM**
chứ không phải tầng model âm — đo được bằng vài giây CPU, không cần GPU,
không tốn lượt Groq. Đó là việc của file này.

═══════════════════════════════════════════════════════════════════════════
ĐO CÁI GÌ
═══════════════════════════════════════════════════════════════════════════
Chạy `vieneu_utils.phonemize_text.phonemize_text` (CHÍNH bộ phiên âm mà
`_MA_DOC` gọi, trong CHÍNH venv của VieNeu) trên **cùng bộ câu**
`_bo_cau_thu_doc.CORPUS` mà `_do_lan_nn.py` dùng — không đẻ corpus thứ hai.

Đầu ra rỗng (hoặc chỉ còn dấu câu) = **model không nhận được chữ nào**. Lúc đó
cái nó phát ra là tiếng bịa từ đầu đến cuối, và bộ dò `doc_lan` **không cứu
được**: `lan_vuot` đo `giây / (a + b*n)` với `n` = số ký tự của chữ GỐC, mà
chữ gốc thì model có bao giờ thấy đâu.

Chạy:  _giong_vieneu\\venv\\Scripts\\python -u _do_am_vieneu.py
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

RA_TXT = GOC / "_kq_am_vieneu.txt"
RA_JSON = GOC / "_kq_am_vieneu.json"

#: Còn lại NGẦN NÀY ký tự âm trở xuống thì coi như model **không nhận được
#: chữ nào**. Không phải 0: bộ phiên âm giữ lại dấu câu (tiếng Hàn ra đúng
#: một dấu chấm), mà dấu chấm thì không phải chữ để đọc.
SAN_AM = 2

TEN = {"vi": "Việt", "en": "Anh", "zh": "Trung", "ja": "Nhật", "ko": "Hàn"}


def _co_latin(s: str) -> bool:
    """Chuỗi có chữ cái Latin không (a-z, kể cả có dấu tiếng Việt)."""
    return bool(re.search(r"[A-Za-zÀ-ỹ]", str(s or "")))


def do_mot_tieng(nn: str, muc: list[tuple[str, str]], ph) -> dict:
    """Phiên âm từng mục -> đếm mục ra RỖNG. Trả số thô + vài ví dụ."""
    hang = []
    for loai, chu in muc:
        try:
            am = ph(chu)
            am = am if isinstance(am, str) else str(am)
            loi = ""
        except Exception as e:  # noqa: BLE001
            am, loi = "", f"{type(e).__name__}: {e}"
        # Chỉ tính ký tự ÂM, bỏ dấu câu/khoảng trắng: bộ phiên âm giữ nguyên
        # dấu câu nên "." dài 1 mà chẳng có chữ nào để đọc.
        loi_am = re.sub(r"[\s.,!?;:…、。！？]", "", am)
        hang.append({
            "loai": loi, "kieu": loai, "chu": chu, "am": am,
            "n_chu": len(chu.strip()), "n_am": len(loi_am),
            "latin": _co_latin(chu),
            "rong": len(loi_am) <= SAN_AM,
        })
    rong = [h for h in hang if h["rong"]]
    return {
        "nn": nn, "n": len(hang), "rong": len(rong),
        "rong_khong_latin": sum(1 for h in rong if not h["latin"]),
        "n_khong_latin": sum(1 for h in hang if not h["latin"]),
        "hang": hang,
    }


def main() -> int:
    import _bo_cau_thu_doc as B
    from vieneu_utils.phonemize_text import phonemize_text as ph

    ra: dict[str, dict] = {}
    for nn in ("vi", "en", "zh", "ja", "ko"):
        muc: list[tuple[str, str]] = []
        toks: list[str] = []
        for _l, cau, tk in B.CORPUS[nn]:
            muc.append(("cau", cau))
            for t in tk:
                if t not in toks:
                    toks.append(t)
        muc += [("tok", t) for t in toks]
        ra[nn] = do_mot_tieng(nn, muc, ph)
        print(f"  [{nn}] xong {ra[nn]['rong']}/{ra[nn]['n']} mục ra RỖNG")
        # GHI NGAY sau mỗi tiếng — lượt trước mất sạch vì gom tới cuối.
        RA_JSON.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    b = io.StringIO()
    w = b.write
    w("=" * 78 + "\n")
    w("VIENEU PHIÊN ÂM ĐƯỢC TIẾNG NÀO — đo ở tầng G2P (không GPU, không Groq)\n")
    w("=" * 78 + "\n")
    w("`phonemize_text` là CHÍNH bộ phiên âm `_MA_DOC` gọi. Ra RỖNG nghĩa là\n")
    w(f"model không nhận được chữ nào (<= {SAN_AM} ký tự âm, bỏ dấu câu).\n\n")
    w(f"{'tiếng':<8}{'mục':>6}{'RỖNG':>8}{'%':>8}   "
      f"{'mục KHÔNG có chữ Latin':>24}{'RỖNG':>8}{'%':>8}\n")
    for nn, d in ra.items():
        p = 100.0 * d["rong"] / max(1, d["n"])
        nk = d["n_khong_latin"]
        pk = 100.0 * d["rong_khong_latin"] / max(1, nk)
        w(f"{TEN[nn]:<8}{d['n']:>6}{d['rong']:>8}{p:>7.1f}%   "
          f"{nk:>24}{d['rong_khong_latin']:>8}{pk:>7.1f}%\n")

    w("\n" + "=" * 78 + "\n")
    w("VÍ DỤ — chữ vào, âm ra\n")
    w("=" * 78 + "\n")
    for nn, d in ra.items():
        w(f"\n  ### {TEN[nn]}\n")
        cau = [h for h in d["hang"] if h["kieu"] == "cau"]
        for h in cau[:3]:
            w(f"    {'RỖNG' if h['rong'] else 'ĐỌC'}  "
              f"{h['n_chu']:>3} chữ -> {h['n_am']:>3} âm · "
              f"«{h['chu'][:34]}» -> «{h['am'][:44]}»\n")
    txt = b.getvalue()
    RA_TXT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"Số thô: {RA_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
