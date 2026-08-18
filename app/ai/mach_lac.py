# -*- coding: utf-8 -*-
"""HẬU KIỂM **BẢN GHÉP** — 3 đoạn hay riêng lẻ chưa chắc ghép lại đã mạch lạc.

VÌ SAO CÓ FILE NÀY (anh Hùng 09/08/2026): app chọn 3 đoạn hay rồi ghép, và
**chưa bao giờ xem lại bản ghép**. Ba đoạn đều hay mà đặt cạnh nhau vẫn có thể
rời rạc — trong nhà -> ngoài đường -> lại trong nhà, hoặc đoạn 2 trả lời một
câu hỏi mà đoạn 3 mới đặt ra.

Khâu CHỌN chấm TỪNG đoạn (`chon_doan.cham_hoi_dong` — hội đồng 3 trọng tài).
Khâu này hỏi câu KHÁC HẲN: **"xâu chúng lại theo thứ tự này thì có xuôi
không"**. Rẻ: chỉ đọc LỜI THOẠI của chính các đoạn đã chọn (đã có sẵn), 1 lượt
LLM cho cả clip, và chỉ dùng `vision_digest` khi CACHE đã có (không bao giờ tự
bật AI xem hình — đo thật 219 giây/video).

=== FAIL-SAFE LÀ ĐIỀU KIỆN TIÊN QUYẾT (không phải tính năng phụ) ===
Hậu kiểm lỗi · hết lượt · LLM trả rác · trả thứ tự vô lý -> **GIỮ NGUYÊN lựa
chọn ban đầu**. Không bao giờ được làm hỏng clip. Cụ thể `hau_kiem` chỉ đổi khi
CẢ BA điều sau đúng:
  1. đọc được JSON;
  2. `thu_tu` là HOÁN VỊ đầy đủ của 0..n-1 (thiếu/thừa/lặp -> bỏ);
  3. bỏ đoạn thì phần còn lại vẫn >= 2 đoạn VÀ >= `min_giay` giây.
`LLMTooLarge` (413) được ném LÊN NGUYÊN VẸN, KHÔNG phạt key — xem cổng 28
CLAUDE.md: 1 yêu cầu quá to từng khoá cả 38 key 120 giây.
"""
from __future__ import annotations

import json
import re
from typing import Optional

#: Điểm mạch lạc (0-10) từ mức này trở lên thì **KHÔNG ĐỘNG VÀO**. Cố ý đặt
#: thấp: mặc định của khâu này phải là IM LẶNG. Chỉ bản ghép thật sự lủng củng
#: mới đáng để đổi, vì mọi thay đổi đều là rủi ro với clip đang tốt.
NGUONG_MACH_LAC = 6.0
#: Số đoạn tối thiểu còn lại sau khi bỏ. 1 đoạn thì hết chuyện "ghép" nên cũng
#: hết lý do hậu kiểm.
DOAN_TOI_THIEU = 2
#: Trần chữ lời thoại mỗi đoạn nhét vào prompt. Prompt chọn đoạn đã sát mức
#: 413 (xem cổng 26/28) nên khâu này phải gọn.
CHU_MOI_DOAN = 420

_HD = ("Bạn là DỰNG PHIM của kênh video ngắn. Dưới đây là các ĐOẠN đã được cắt "
       "ra từ MỘT video và sẽ được GHÉP LIỀN NHAU theo đúng thứ tự đánh số. "
       "Hãy xem BẢN GHÉP có MẠCH LẠC không: người xem lần đầu có hiểu được "
       "mạch chuyện không, có đoạn nào lạc lõng/thừa/nhắc tới thứ chưa hề "
       "giới thiệu không, đảo thứ tự có xuôi hơn không.\n"
       "Trả về DUY NHẤT JSON, không markdown, không thêm chữ nào:\n"
       '{"mach_lac": 0-10, "thu_tu": [chỉ số theo thứ tự MỚI] hoặc null, '
       '"bo": chỉ số đoạn nên BỎ hoặc null, "vi_sao": "1 câu ngắn tiếng Việt"}\n'
       # THANG ĐIỂM PHẢI NÓI RÕ CHIỀU — nếu không, model tự hiểu ngược.
       # ĐO THẬT 09/08/2026 (cổng 49 CA 5) với bản ghi CHỈ "mach_lac: 0-10":
       #   bản XUÔI (1-2-3)     -> 0/10, lý do "Mạch chuyện rõ ràng và logic"
       #   bản ĐẢO LỘN (3-1-2)  -> 8/10, lý do "thứ tự thời gian không logic"
       # tức model chấm ĐỘ LỦNG CỦNG chứ không phải độ mạch lạc — ngược hoàn
       # toàn, và vì 8 >= ngưỡng nên đề nghị SỬA ĐÚNG của nó lại bị bỏ đi.
       'THANG "mach_lac": **10 = RẤT MẠCH LẠC** (xem một mạch, hiểu ngay, các '
       'đoạn nối nhau tự nhiên) · **0 = RỜI RẠC** (các đoạn không ăn nhập, '
       "người xem lần đầu không hiểu). Điểm CÀNG CAO là CÀNG TỐT.\n"
       "QUY TẮC: chỉ đề nghị đổi khi thật sự lủng củng; giữ nguyên thì "
       '"thu_tu": null và "bo": null. KHÔNG bao giờ bỏ quá 1 đoạn.')


def loi_doan(transcript: dict, a: float, b: float,
             tran: int = CHU_MOI_DOAN) -> str:
    """Lời thoại GIAO với [a,b]. Cùng luật `lop_phu.loi_theo_doan`: lấy cả
    video là lấy bằng chứng của chỗ khác."""
    ra = []
    for c in (transcript or {}).get("segments") or []:
        try:
            s, e = float(c.get("start")), float(c.get("end"))
        except (TypeError, ValueError):
            continue
        if e > a and s < b:
            t = " ".join(str(c.get("text") or "").split())
            if t:
                ra.append(t)
        if sum(len(x) for x in ra) > tran:
            break
    return " ".join(ra)[:tran]


def _hinh_doan(digest: list, a: float, b: float, toi_da: int = 2) -> str:
    """Mô tả hình của đoạn — CHỈ khi `vision_digest` đã có sẵn trong cache.

    KHÔNG BAO GIỜ gọi thêm vision ở đây (219 giây/video). Rỗng -> prompt không
    có dòng hình, đúng như trước.
    """
    ra = []
    for d in digest or []:
        try:
            t = float(d.get("t"))
        except (TypeError, ValueError):
            continue
        if a <= t <= b:
            s = str(d.get("desc") or "").strip()
            if s:
                ra.append(s[:70])
        if len(ra) >= toi_da:
            break
    return " / ".join(ra)


def khoi_prompt(segs: list, transcript: dict,
                digest: Optional[list] = None) -> str:
    """Prompt hậu kiểm. Hàm THUẦN (không mạng, không DB) -> test được."""
    dong = []
    for i, (s, e) in enumerate(segs):
        s, e = float(s), float(e)
        lo = loi_doan(transcript, s, e)
        hi = _hinh_doan(digest, s, e)
        dong.append(f"[{i}] dài {e - s:.0f}s"
                    + (f" · hình: {hi}" if hi else "")
                    + f"\nlời: {lo or '(không có thoại)'}")
    return _HD + "\n\n" + "\n\n".join(dong)


def doc_ket(raw: str, n: int) -> Optional[dict]:
    """Bóc JSON của lượt hậu kiểm. Trả None = KHÔNG ĐỌC ĐƯỢC -> giữ nguyên.

    Mọi kiểm tra tính hợp lệ nằm ở ĐÂY, không tin LLM: `thu_tu` phải là HOÁN VỊ
    đủ 0..n-1 (model rất hay trả thiếu một số hoặc lặp), `bo` phải là chỉ số có
    thật. Sai một điều là bỏ HẲN đề nghị đó chứ không "sửa hộ" — sửa hộ là đang
    đoán thay model.
    """
    if not raw:
        return None
    try:
        from app.ai.llm import bo_khoi_suy_nghi as _bks
        raw = _bks(raw)
    except Exception:  # noqa: BLE001 — không có hàm thì cứ parse như cũ
        pass
    d = None
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
        except (ValueError, TypeError):
            d = None
    if d is None:
        # BỘ BÓC BAO DUNG (v2.35.0): khối markdown · chữ dẫn thừa · dấu phẩy
        # thừa · JSON ĐỨT CUỐI. Regex trên đòi có `}` ĐÓNG nên câu trả lời bị
        # cắt vì hết token là không khớp gì -> lượt hậu kiểm im lặng bỏ qua.
        # Đặt SAU đường cũ nên JSON hợp lệ vẫn ra kết quả y hệt.
        try:
            from app.ai.llm import boc_json as _bj
            d = _bj(raw)
        except Exception:  # noqa: BLE001
            return None
    if not isinstance(d, dict):
        return None
    ra: dict = {"mach_lac": None, "thu_tu": None, "bo": None,
                "vi_sao": str(d.get("vi_sao") or "")[:160]}
    try:
        ra["mach_lac"] = max(0.0, min(10.0, float(d.get("mach_lac"))))
    except (TypeError, ValueError):
        ra["mach_lac"] = None
    tt = d.get("thu_tu")
    if isinstance(tt, list) and len(tt) == n:
        try:
            tt = [int(x) for x in tt]
        except (TypeError, ValueError):
            tt = None
        if tt is not None and sorted(tt) == list(range(n)):
            ra["thu_tu"] = tt
    bo = d.get("bo")
    if bo is not None:
        try:
            bo = int(bo)
        except (TypeError, ValueError):
            bo = None
        if bo is not None and 0 <= bo < n:
            ra["bo"] = bo
    return ra


def hau_kiem(segs: list, transcript: dict, complete_text,
             digest: Optional[list] = None, min_giay: float = 0.0,
             model: str = "") -> tuple:
    """XEM LẠI BẢN GHÉP -> `(segs_mới, lý_do)`. `segs_mới` là `segs` nếu giữ.

    `complete_text(prompt) -> str` truyền từ ngoài (dùng đúng bộ xoay key +
    vòng đợi-hết-lượt của app). **KHÔNG BAO GIỜ NÉM LỖI** trừ `LLMTooLarge`
    (413 phải nổi lên nguyên vẹn để caller thu nhỏ; phạt key ở đây là đốt sạch
    38 key — cổng 28).

    `min_giay`: tổng thời lượng tối thiểu được phép còn lại nếu BỎ một đoạn.
    0 = không kiểm (caller đã có `_enforce_len` nói lời cuối).
    """
    n = len(segs or [])
    if n < DOAN_TOI_THIEU:
        return segs, f"clip chỉ {n} đoạn -> không có gì để xem lại"
    from app.ai import llm
    try:
        pr = khoi_prompt(segs, transcript, digest)
        raw = (complete_text(pr, model=model) if model else complete_text(pr))
    except llm.LLMTooLarge:
        raise                      # 413: caller thu nhỏ. TUYỆT ĐỐI không phạt key
    except Exception as e:  # noqa: BLE001 — hậu kiểm hỏng KHÔNG được hỏng clip
        return segs, (f"hậu kiểm lỗi ({type(e).__name__}: {str(e)[:70]}) -> "
                      "GIỮ NGUYÊN lựa chọn ban đầu")
    d = doc_ket(raw or "", n)
    if d is None:
        return segs, "hậu kiểm trả về không đọc được -> GIỮ NGUYÊN lựa chọn ban đầu"
    ml = d["mach_lac"]
    if ml is None:
        return segs, "hậu kiểm không chấm được điểm -> GIỮ NGUYÊN"
    if ml >= NGUONG_MACH_LAC and not d["thu_tu"] and d["bo"] is None:
        return segs, (f"bản ghép mạch lạc {ml:.0f}/10 -> giữ nguyên "
                      f"{n} đoạn" + (f" ({d['vi_sao']})" if d["vi_sao"] else ""))
    if ml >= NGUONG_MACH_LAC:
        # điểm cao mà vẫn đòi đổi = model tự mâu thuẫn -> tin CON SỐ, không tin
        # đề nghị. Đây là lối an toàn: mặc định của khâu này là im lặng.
        return segs, (f"bản ghép mạch lạc {ml:.0f}/10 (>= {NGUONG_MACH_LAC:.0f}) "
                      "nhưng vẫn đề nghị đổi -> KHÔNG đổi, giữ nguyên")
    moi = list(segs)
    viec = []
    if d["thu_tu"] and d["thu_tu"] != list(range(n)):
        moi = [moi[i] for i in d["thu_tu"]]
        viec.append("đổi thứ tự -> " + "→".join(str(i) for i in d["thu_tu"]))
    if d["bo"] is not None:
        con = [x for j, x in enumerate(segs) if j != d["bo"]]
        tong = sum(float(e) - float(s) for s, e in con)
        if len(con) < DOAN_TOI_THIEU:
            viec.append(f"đề nghị bỏ đoạn {d['bo']} nhưng còn < "
                        f"{DOAN_TOI_THIEU} đoạn -> KHÔNG bỏ")
        elif min_giay and tong < float(min_giay):
            viec.append(f"đề nghị bỏ đoạn {d['bo']} nhưng còn {tong:.0f}s < "
                        f"Min {float(min_giay):.0f}s -> KHÔNG bỏ")
        else:
            # bỏ TRÊN DANH SÁCH ĐÃ ĐỔI THỨ TỰ: chỉ số của model là của bản GỐC
            _bo = segs[d["bo"]]
            moi = [x for x in moi if x is not _bo]
            viec.append(f"bỏ đoạn {d['bo']}")
    if not viec:
        return segs, (f"bản ghép chỉ {ml:.0f}/10 nhưng hậu kiểm không nêu được "
                      "cách sửa hợp lệ -> GIỮ NGUYÊN")
    return moi, (f"bản ghép {ml:.0f}/10 < {NGUONG_MACH_LAC:.0f} -> "
                 + " · ".join(viec)
                 + (f" ({d['vi_sao']})" if d["vi_sao"] else ""))


def ghi_nhat_ky(ly_do: str, ten: str = "") -> None:
    """1 dòng vào `logs/mach_lac_<ngày>.log`. KHÔNG BAO GIỜ ném lỗi.

    Phải ghi CẢ lúc giữ nguyên: khâu này im lặng theo thiết kế, không ghi thì
    "sao Part này lủng củng thế" là câu không tra được — đúng bẫy đã che chuyện
    model vision bị Groq gỡ.
    """
    try:
        from datetime import datetime

        from config import DATA_DIR
        d = DATA_DIR / "logs"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"mach_lac_{datetime.now():%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] {ten} — {ly_do}\n")
    except Exception:  # noqa: BLE001
        pass
