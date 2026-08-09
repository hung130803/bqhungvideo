"""HOOK CHỌN THEO TÒ MÒ — không theo TIẾNG TO.

VÌ SAO CÓ FILE NÀY
------------------
`hook-first` (v2.20.0 trở về trước) lấy 2-4 giây **cao trào ÂM THANH** đưa lên
đầu clip: `m1_highlight._pick_hook_seg` dò cửa sổ 2,5 s có `_audio_score` lớn
nhất. Nhưng chỗ ỒN NHẤT không phải chỗ giữ chân người xem — tiếng hét, tiếng
nhạc nổi, tiếng va chạm đều ăn điểm mà **không hứa hẹn gì**. Hook giỏi là chỗ
**để lại câu hỏi / thông tin dở dang** ("và rồi anh ta phát hiện ra…").

Nguồn dữ liệu là **chép lời ĐÃ CÓ SẴN** (`analysis['transcript']`, mọi video đi
qua bước này rồi) nên đường này tốn **0 giây mạng, 0 lượt LLM, 0 lượt vision**.

BẤT BIẾN SỐNG CÒN
-----------------
* Video **KHÔNG có lời** (hoặc chép lời không có mốc câu) -> trả None -> caller
  đi **Y NGUYÊN đường cũ** (hook_seg của AI, rồi cao trào tiếng). Không được vỡ.
* Hàm chấm là hàm **THUẦN** (`cham_cau`) — unit test được, không đụng DB/mạng.
* **ĐA NGÔN NGỮ bắt buộc**: Nhật · Hàn · Anh · Việt (+ Trung/Thái đi kèm bảng
  CJK). Đếm từ dùng `recap._word_tokens` — **CẤM `.split()`**: câu Nhật/Trung
  không có dấu cách thì `.split()` ra ĐÚNG 1 token và mọi ngưỡng độ dài sai
  hết (đúng lỗi đã làm hỏng 183 video Nhật, xem cổng 40 trong CLAUDE.md).
* Chữ viết KHÔNG dấu cách (CJK/Thái) dò từ khoá bằng **chuỗi con**; chữ viết CÓ
  dấu cách (Anh/Việt/Hàn...) dò theo **ranh giới từ** — "and" không được khớp
  trong "island", "ra" không được khớp trong "trai".
* Tiếng Việt **GIỮ NGUYÊN DẤU** khi so khớp. Bỏ dấu là `phát hiện` -> `phat
  hien` đụng hàng loạt chữ khác; bài học này đã ghi ở nhóm lớp phủ.
"""
from __future__ import annotations

import re

from app.ai.recap import _CJK_CHARS, _has_cjk, _word_tokens

# ---------------------------------------------------------------------------
# BẢNG TỪ KHOÁ.
# Mỗi nhóm: (trọng số, tập từ khoá). Từ khoá viết THƯỜNG, tiếng Việt CÓ DẤU.
# Nguyên tắc chọn từ: chỉ nhận từ nào tự nó đã mang nghĩa "còn nữa / chưa xong /
# hoá ra là", KHÔNG nhận từ chỉ mang nghĩa "mạnh" (hét, nổ, chạy) — mạnh là
# việc của đường cao trào tiếng, và chính nó là cái đang chọn sai.
# ---------------------------------------------------------------------------

# (1) DỞ DANG / CÒN TIẾP — dấu hiệu MẠNH NHẤT: câu chưa nói hết ý.
_DO_DANG = (
    # Anh
    "and then", "but then", "until", "before i", "before he", "before she",
    "that's when", "thats when", "turns out", "turned out", "little did",
    "next thing", "the moment", "right before", "just as", "as soon as",
    "what happened next", "and suddenly", "and that's when",
    # Việt (CÓ DẤU)
    "và rồi", "rồi thì", "cho đến khi", "đến khi", "hoá ra", "hóa ra",
    "thì ra là", "ngay lúc đó", "ngay khi", "trước khi", "sau đó thì",
    "chuyện gì xảy ra", "và bất ngờ", "nhưng rồi",
    # Nhật
    "そしたら", "そして", "ところが", "その時", "その瞬間", "実は",
    "すると", "しかし", "だが", "その後", "ついに", "とうとう",
    # Hàn
    "그런데", "그러다", "그때", "그 순간", "알고 보니", "사실은",
    "결국", "그리고 나서", "하지만",
    # Trung (đi kèm, không phải nhóm bắt buộc)
    "然后", "结果", "没想到", "突然间", "直到",
)

# (2) PHÁT HIỆN / TIẾT LỘ — "anh ta phát hiện ra…"
_PHAT_HIEN = (
    "discovered", "discover", "found out", "find out", "realized", "realised",
    "realize", "figured out", "revealed", "reveal", "secret", "the truth",
    "turns out", "nobody knows", "no one knows", "hidden", "actually",
    "phát hiện", "nhận ra", "mới biết", "biết được", "bí mật", "sự thật",
    "tiết lộ", "không ai biết", "thì ra", "giấu", "ẩn giấu",
    "気づいた", "気づく", "発見", "わかった", "秘密", "真実", "実は",
    "誰も知らない", "隠れ", "判明",
    "발견", "알게 됐", "알게 되", "깨달", "비밀", "진실", "밝혀",
    "아무도 모르", "숨겨",
    "发现", "秘密", "真相", "原来",
)

# (3) CÂU HỎI TRỰC TIẾP — bỏ ngỏ theo đúng nghĩa đen.
_CAU_HOI = (
    "why", "how did", "how do", "how can", "what if", "what happens",
    "what would", "guess what", "can you", "do you know", "ever wonder",
    "tại sao", "vì sao", "làm sao", "làm thế nào", "chuyện gì", "điều gì",
    "bạn có biết", "đố bạn", "liệu",
    "なぜ", "どうして", "どうやって", "何が", "知ってる", "だろうか",
    "왜", "어떻게", "무슨 일", "아세요", "알아요",
    "为什么", "怎么", "什么",
)

# (4) BẤT NGỜ / CỰC ĐOAN — "chưa bao giờ", "bỗng nhiên".
_BAT_NGO = (
    "suddenly", "never", "nobody", "no one", "everyone", "the first time",
    "for the first time", "the last thing", "worst", "best", "craziest",
    "unbelievable", "shocked", "shocking", "i couldn't believe",
    "bỗng nhiên", "đột nhiên", "bất ngờ", "chưa bao giờ", "không ai",
    "lần đầu tiên", "lần cuối", "tệ nhất", "tuyệt nhất", "điên rồ",
    "không thể tin", "sốc", "kinh khủng",
    "突然", "いきなり", "初めて", "まさか", "信じられない", "衝撃",
    "誰も", "一番",
    "갑자기", "처음", "설마", "믿을 수 없", "충격", "아무도", "제일",
    "居然", "竟然", "第一次", "震惊",
)

# (5) HỨA HẸN CÓ CẤU TRÚC — "3 điều", "bước cuối cùng".
_HUA_HEN = (
    "the first", "number one", "step one", "here's how", "heres how",
    "let me show", "watch this", "wait for it", "keep watching",
    "điều đầu tiên", "thứ nhất", "bước đầu", "đây là cách", "để tôi cho",
    "xem này", "chờ chút", "xem tiếp",
    "まず", "一つ目", "こうやって", "見て", "最後まで",
    "첫 번째", "이렇게", "보세요", "끝까지",
)

# (6) XẤU — chào hỏi / kêu gọi / câu rỗng. Có mặt là TRỪ điểm nặng: mở clip
# bằng "xin chào các bạn, hôm nay mình sẽ..." là cách chắc chắn mất người xem.
_XAU = (
    "hello", "hi guys", "hey guys", "welcome to", "welcome back",
    "subscribe", "like and", "my channel", "thanks for watching",
    "don't forget to", "dont forget to", "as always", "in this video",
    "xin chào", "chào các bạn", "chào mọi người", "hôm nay mình",
    "đăng ký kênh", "like và", "kênh của mình", "cảm ơn các bạn",
    "đừng quên", "trong video này", "video hôm nay",
    "こんにちは", "みなさん", "チャンネル登録", "今日は", "この動画",
    "안녕하세요", "여러분", "구독", "오늘은", "이 영상",
    "大家好", "订阅", "今天",
)

# Tiếng đệm thuần — câu chỉ gồm mấy thứ này thì KHÔNG bao giờ làm hook.
_DEM = {
    "um", "uh", "uhh", "hmm", "mm", "ah", "oh", "yeah", "yep", "ok", "okay",
    "so", "well", "right", "you know", "like", "à", "ừ", "ờ", "vâng", "dạ",
    "え", "えー", "あの", "うん", "はい", "네", "어", "음",
}

_NHOM = (
    (_DO_DANG, 1.00, "dở dang/còn tiếp"),
    (_PHAT_HIEN, 0.92, "phát hiện/tiết lộ"),
    (_CAU_HOI, 0.80, "câu hỏi bỏ ngỏ"),
    (_BAT_NGO, 0.62, "bất ngờ/cực đoan"),
    (_HUA_HEN, 0.48, "hứa hẹn có cấu trúc"),
)

# Ngưỡng NHẬN hook theo tò mò. Dưới mức này -> trả None -> caller đi đường CŨ.
# Chọn 0.34: đủ để MỘT nhóm mạnh (dở dang 1,00 x 0,35 hệ số đầu = 0,35) qua
# cửa, còn câu chỉ có 1 từ "hứa hẹn" mờ nhạt thì không.
NGUONG = 0.34
# Cửa sổ hook: giống đường cũ (2-4 s), tối thiểu 1,2 s mới đáng chiếu.
DAI_MIN, DAI_MAX = 1.2, 4.0
# Hook phải cách mốc mở đầu clip ít nhất ngần này, không thì chiếu lại chính nó.
CACH_DAU_MIN = 3.0

_KHOANG_TRANG = re.compile(r"\s+")
# Ký tự "kết câu" của các hệ chữ — câu KHÔNG kết thúc bằng chúng = còn dở.
_KET_CAU = "。．.!?！？…‥~〜"
_CJK_SET_RE = re.compile("[" + _CJK_CHARS + "]")


def _chuan(text: str) -> str:
    """Chuẩn hoá NHẸ: thường hoá + gộp khoảng trắng. **GIỮ NGUYÊN DẤU tiếng
    Việt** (bỏ dấu là mở cửa cho nhận nhầm) và giữ nguyên chữ CJK."""
    return _KHOANG_TRANG.sub(" ", str(text or "").strip().lower())


def _khop(hay: str, kim: str) -> bool:
    """`kim` có nằm trong `hay` không, ĐÚNG kiểu chữ viết của `kim`.

    * `kim` chứa ký tự CJK/Thái (không dùng dấu cách) -> so **chuỗi con**.
    * `kim` toàn chữ có dấu cách -> so theo **RANH GIỚI TỪ**, nếu không thì
      "and" khớp trong "island", "ra" khớp trong "trai" -> điểm rác.
    """
    if not kim:
        return False
    if _CJK_SET_RE.search(kim):
        return kim in hay
    # \b của Python làm việc trên [A-Za-z0-9_] nên chữ Việt có dấu (ngoài ASCII)
    # KHÔNG được coi là ký tự từ -> tự dựng ranh giới bằng lookaround.
    mau = r"(?<![^\W\d_])" + re.escape(kim) + r"(?![^\W\d_])"
    try:
        return re.search(mau, hay) is not None
    except re.error:                       # pragma: no cover - từ khoá đều sạch
        return kim in hay


def cham_cau(text: str, giay: float = 0.0) -> tuple:
    """Chấm mức GÂY TÒ MÒ của một câu. **HÀM THUẦN** -> (điểm 0..1, lý do).

    `giay` = độ dài câu tính bằng giây (0 = không biết) chỉ dùng để phạt câu
    quá ngắn/quá dài, không ảnh hưởng phần ngữ nghĩa.
    """
    t = _chuan(text)
    if not t:
        return 0.0, "câu rỗng"
    toks = _word_tokens(t)                 # CJK-aware — CẤM .split()
    n = len(toks)
    if n < 2:
        return 0.0, "câu quá ngắn (< 2 token)"
    if not _has_cjk(t) and all(w.strip(".,!?…") in _DEM for w in toks):
        return 0.0, "toàn tiếng đệm"

    diem, ly = 0.0, []
    for tap, w, ten in _NHOM:
        trung = [k for k in tap if _khop(t, k)]
        if trung:
            # Một nhóm chỉ ăn điểm MỘT LẦN (câu nhắc 3 lần "why" không tò mò
            # gấp 3); nhóm thứ hai trở đi cộng dồn với hệ số giảm dần.
            diem += w * (0.35 if not ly else 0.18)
            ly.append(f"{ten} «{trung[0]}»")

    # Câu KHÔNG kết thúc bằng dấu kết -> đang nói dở, đúng thứ ta cần.
    if t[-1] not in _KET_CAU:
        diem += 0.10
        ly.append("kết câu bỏ lửng")
    # Câu hỏi có dấu ? -> luôn để lại một câu hỏi theo nghĩa đen.
    if t[-1] in "?？":
        diem += 0.12
        ly.append("kết bằng dấu hỏi")

    # PHẠT: chào hỏi / kêu gọi đăng ký. Đây là điểm ÂM thật sự, không phải
    # "không cộng" — mở clip bằng câu chào là cách chắc chắn mất người xem.
    xau = [k for k in _XAU if _khop(t, k)]
    if xau:
        diem -= 0.55
        ly.append(f"XẤU: chào hỏi/kêu gọi «{xau[0]}»")

    # PHẠT độ dài: câu 2-3 token thì dù có từ khoá cũng không kể được gì;
    # câu quá dài (> 45 token) là cả đoạn văn, cắt 4 giây không trọn ý.
    if n < 4:
        diem -= 0.16
        ly.append(f"ngắn ({n} token)")
    elif n > 45:
        diem -= 0.10
        ly.append(f"dài ({n} token)")
    if 0 < giay < 0.8:
        diem -= 0.12
        ly.append(f"chỉ {giay:.1f}s")

    diem = max(0.0, min(1.0, diem))
    return round(diem, 4), ("; ".join(ly) or "không có dấu hiệu tò mò")


def _cau_trong_doan(transcript: dict, segs: list) -> list:
    """Các câu chép lời GIAO với đoạn đã chọn -> [(bd, kt, lời)]. Hàm thuần.

    Vì sao chỉ lấy câu trong đoạn: hook phải là phim CÓ TRONG clip. Lấy câu ở
    phút 12 rồi chiếu lên đầu clip cắt ở phút 2 là ghép hai cảnh không liên
    quan — đúng loại lỗi mà `loc_digest_theo_doan` đã phải chữa cho lớp phủ.
    """
    ss = []
    for p in segs or []:
        try:
            a, b = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        if b > a:
            ss.append((a, b))
    if not ss:
        return []
    ra = []
    for c in (transcript or {}).get("segments") or []:
        try:
            a, b = float(c.get("start")), float(c.get("end"))
        except (TypeError, ValueError):
            continue
        if b <= a:
            continue
        txt = str(c.get("text") or "").strip()
        if txt and any(b > s and a < e for s, e in ss):
            ra.append((a, b, txt))
    ra.sort(key=lambda x: x[0])
    return ra


def chon_hook_to_mo(transcript: dict, segs: list, top: int = 0):
    """Chọn cửa sổ hook theo TÒ MÒ. Trả dict hoặc **None**.

    None = không dùng được đường này (không lời / không mốc câu / không câu nào
    đủ tò mò) -> caller PHẢI đi đường cũ. Đây là bất biến sống còn.

    dict: {"seg": [bd, kt], "diem": float, "cau": str, "vi_sao": str}
    `top` > 0 -> kèm khoá "bang" = danh sách `top` câu điểm cao nhất (để nhật
    ký / cổng in ra cho người đọc tự đánh giá).
    """
    cau = _cau_trong_doan(transcript, segs)
    if not cau:
        return None
    try:
        moc_dau = float(segs[0][0])
    except (TypeError, ValueError, IndexError):
        moc_dau = 0.0

    cham = []
    for a, b, txt in cau:
        d, ly = cham_cau(txt, b - a)
        cham.append((d, a, b, txt, ly))
    cham.sort(key=lambda x: (-x[0], x[1]))

    bang = [{"diem": d, "bd": a, "kt": b, "cau": txt, "ly_do": ly}
            for d, a, b, txt, ly in cham[:top]] if top else []

    for d, a, b, txt, ly in cham:
        if d < NGUONG:
            break                                    # đã sắp giảm dần -> hết
        if abs(a - moc_dau) <= CACH_DAU_MIN:
            continue                                 # trùng ngay đầu clip
        dai = max(DAI_MIN, min(DAI_MAX, b - a))
        ra = {"seg": [round(a, 2), round(a + dai, 2)], "diem": d,
              "cau": txt.strip(),
              "vi_sao": (f"tò mò {d:.2f}/1,00 (ngưỡng {NGUONG:.2f}): {ly}")}
        if bang:
            ra["bang"] = bang
        return ra
    return None
