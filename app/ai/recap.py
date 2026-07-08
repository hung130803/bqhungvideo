"""
LLM "NGƯỜI KỂ CHUYỆN" cho tính năng 🎙 Reup thuyết minh (recap).

Nhiệm vụ: từ transcript CỦA 1 CLIP (các câu start/end/text trong phạm vi clip),
viết KỊCH BẢN chia clip thành các PART xen kẽ:
  - mode "orig"    : GIỮ TIẾNG GỐC (khoảnh khắc đắt — thoại hay, cao trào).
  - mode "narrate" : TẮT TIẾNG GỐC, giọng AI KỂ CHUYỆN — người kể đứng NGOÀI
                     video, TỰ SÁNG TÁC lời kể của riêng mình (transcript chỉ
                     để HIỂU chuyện, KHÔNG phải nguồn kể lại) — viết bằng
                     ĐÚNG NGÔN NGỮ video.

Prompt viết theo vai NGƯỜI KỂ CHUYỆN kênh triệu view: cấm lặp lại/diễn giải
lại lời nhân vật, phải THÊM cái transcript không có (cảm xúc, phán đoán, bình
luận, câu hỏi khán giả, thông tin nền), lời kể DẪN MỒI vào đoạn tiếng gốc kế
tiếp. Giữ công thức viral: part ĐẦU TIÊN là narrate HOOK (2-3 giây đầu quyết
định giữ chân), tuần tự thời gian, câu ngắn văn nói, đếm chữ khít khung.
Nếu có ẢNH khung hình (vision), AI nhìn cảnh để hiểu bối cảnh rồi kể.

Output JSON: {"title": "...", "parts": [{"start": s, "end": e,
              "mode": "orig"|"narrate", "text": "..."}]}
Các part PHỦ KÍN [clip_start, clip_end] theo thứ tự thời gian.

validate_parts() là hàm THUẦN (không LLM) tự sửa output hỏng: clamp vào phạm
vi clip, bỏ part rác, mode lạ -> orig, chồng lấn -> cắt, khoảng hở -> chèn
part orig, narrate rỗng/COPY transcript (kể cả FUZZY: trùng >60% từ với
transcript trong đúng khoảng thời gian đó) -> orig. Có unit-test riêng.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from app.ai import llm

# 4 phong cách thuyết minh (key lưu QSettings/preset -> hint đưa vào prompt).
# Mỗi phong cách có MÔ TẢ CÁCH VIẾT + 1-2 câu VÍ DỤ chuẩn vibe (few-shot —
# ví dụ tiếng Việt, prompt dặn AI bắt chước VIBE bằng đúng ngôn ngữ video).
STYLES = {
    "story": (
        "Kể chuyện",
        "PHONG CÁCH KỂ CHUYỆN — kể cho ĐỨA BẠN THÂN nghe về gã trong video:\n"
        "  + Câu NGẮN, dồn dập, có khựng \"...\" nhá tò mò.\n"
        "  + Gọi nhân vật bằng biệt danh đời thường (gã này, bà chị, ông chú, "
        "cậu nhóc) — KHÔNG gọi trung tính kiểu 'người đàn ông'.\n"
        "  + Cuối mỗi đoạn narrate cài 1 móc tò mò: chuyện gì xảy ra tiếp?\n"
        "  VÍ DỤ chuẩn vibe (bắt chước VIBE, đừng chép): \"Gã này tưởng hôm "
        "nay là ngày may mắn nhất đời mình. Sai. Sai khủng khiếp...\" — "
        "\"Và cái cách bà chị phản ứng... tôi kể bạn nghe, không ai đỡ nổi.\""),
    "clickbait": (
        "Giật gân câu view",
        "PHONG CÁCH GIẬT GÂN — cường điệu + câu hỏi treo LIÊN TỤC:\n"
        "  + Mở bằng cú sốc, liên tục treo: \"Nhưng khoan... bạn chưa thấy "
        "gì đâu.\"\n"
        "  + Phóng đại có kiểm soát: nhất/chưa từng/không tưởng — nhưng KHÔNG "
        "bịa chi tiết sai với video.\n"
        "  VÍ DỤ chuẩn vibe: \"Đây có thể là quyết định tệ nhất đời anh ta. "
        "Và điên nhất là... anh ta còn chưa biết điều đó.\" — \"99% người xem "
        "đoán sai đoạn tiếp theo. Bạn thì sao?\""),
    "funny": (
        "Hài hước",
        "PHONG CÁCH HÀI HƯỚC — mỉa nhẹ + nhân cách hóa, KHÔNG giải thích joke:\n"
        "  + Cà khịa như nói xấu bạn mình: chọc vào cái ngớ ngẩn, tương phản, "
        "sự tự tin lố của nhân vật.\n"
        "  + Nhân cách hóa đồ vật/con vật; thả joke rồi ĐI TIẾP luôn.\n"
        "  VÍ DỤ chuẩn vibe: \"Sự tự tin của ông chú này... đóng thuế được "
        "luôn đấy.\" — \"Con mèo nhìn chủ kiểu: rồi, lại nữa rồi.\""),
    "analysis": (
        "Phân tích sâu",
        "PHONG CÁCH PHÂN TÍCH — mổ xẻ 'VÌ SAO' với giọng tự tin, sắc lạnh:\n"
        "  + Chỉ ra cái người xem KHÔNG tự nhận ra; khẳng định chắc nịch rồi "
        "chứng minh, không vòng vo 'có lẽ/hình như'.\n"
        "  + Chốt mỗi ý bằng 1 câu đắt: bài học/ý nghĩa đằng sau.\n"
        "  VÍ DỤ chuẩn vibe: \"Để ý tay trái gã... đó không phải ngẫu nhiên. "
        "Đó là tính toán.\" — \"Ai cũng nghĩ cô ấy thua từ giây thứ ba. "
        "Nhưng không. Chính lúc đó cô ấy đang thắng.\""),
}
DEFAULT_STYLE = "story"

_SYSTEM = (
    "Bạn là NGƯỜI KỂ CHUYỆN (narrator) của một kênh video triệu view. Bạn "
    "đứng NGOÀI video, kể về nhân vật và sự việc trong video cho khán giả "
    "của bạn nghe — như một người dẫn chuyện lôi cuốn, KHÔNG phải người "
    "thuật lại lời thoại. Bạn tự hiểu bối cảnh + nội dung + lời thoại rồi "
    "TỰ SÁNG TÁC lời kể hấp dẫn của riêng mình, chia clip thành các đoạn "
    "XEN KẼ: đoạn GIỮ TIẾNG GỐC (khoảnh khắc đắt nhất — để nhân vật tự nói) "
    "và đoạn BẠN KỂ (video tắt tiếng, chỉ còn giọng bạn). 2-3 giây đầu quyết "
    "định người xem ở lại hay lướt — câu mở phải gây sốc/tò mò tức thì. "
    "CHỈ trả JSON thuần, không thêm chữ nào khác.")

# Tốc độ đọc TTS để AI canh độ dài lời thuyết minh (ghi thẳng vào prompt)
_RATE_HINT = ("Tốc độ giọng đọc AI: tiếng Anh ~2.3 từ/giây, tiếng Việt ~3.5 "
              "âm tiết/giây (ngôn ngữ khác tương đương ~2.5 từ/giây).")


def style_label(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[0]


def _style_hint(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[1]


def _narrator_rules(ln: str, style: str) -> str:
    """Khối luật NGƯỜI KỂ CHUYỆN dùng chung cho prompt 1-clip (build_prompt)
    và prompt đạo diễn multi-window (build_director_prompt) — giữ 1 nguồn
    để 2 đường không lệch luật (anti-copy, văn nói, vibe phong cách)."""
    return (
        "CẤM TUYỆT ĐỐI trong lời narrate:\n"
        "- CẤM lặp lại, diễn giải lại hay tóm tắt lại câu nhân vật VỪA nói "
        "hoặc SẮP nói trong transcript — người xem sắp nghe/vừa nghe câu đó "
        "rồi, kể lại là thừa và chán.\n"
        "- CẤM kiểu tường thuật gián tiếp: \"anh ấy nói rằng...\", \"cô ấy "
        "bảo là...\", \"anh ta giải thích rằng...\".\n\n"
        "LỜI KỂ CỦA BẠN PHẢI:\n"
        "- Gọi nhân vật theo góc nhìn NGƯỜI NGOÀI: \"gã này\", \"cô gái "
        "ấy\", \"ông chú\", \"the guy\"... — bạn KHÔNG phải người trong "
        "video.\n"
        "- THÊM cái transcript KHÔNG có: cảm xúc, phán đoán, bình luận, câu "
        "hỏi ném cho khán giả, thông tin nền. Kiểu: \"Điều điên rồ là hắn "
        "còn không biết...\", \"Ai cũng nghĩ X. Nhưng không.\"\n"
        "- DẪN MỒI vào đoạn tiếng gốc kế tiếp như thả câu: lời kể ngay "
        "TRƯỚC 1 part orig phải khiến người xem HÓNG câu nhân vật sắp nói "
        "(kiểu: \"Và nghe hắn nói câu này...\") — đừng nói nội dung câu đó "
        "ra.\n\n"
        "VĂN NÓI kể miệng (bắt buộc):\n"
        f"- Khẩu ngữ tự nhiên đúng {ln} — như nói vo, không phải đọc văn "
        "bản.\n"
        "- Dùng dấu \"...\" tạo khựng nhá tò mò; câu hỏi tu từ; câu NGẮN "
        "dồn dập (tối đa 12 từ/câu).\n"
        "- CẤM văn viết/thuyết trình/liệt kê: \"đầu tiên\", \"tiếp theo\", "
        "\"như các bạn thấy\", \"trong video này\", \"chúng ta có thể "
        "thấy\"...\n"
        f"{_style_hint(style)}\n"
        "(Ví dụ trên là tiếng Việt để bạn bắt VIBE — lời narrate thật phải "
        f"viết bằng {ln}.)\n")


def build_prompt(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float, title: str = "",
                 frames: Optional[list] = None, ratio: float = 55) -> str:
    """sentences = [(start, end, text)] các câu transcript TRONG clip.
    frames = [(giây, đường_dẫn_ảnh)] khung hình gửi kèm (vision) — ảnh #k
    chụp tại mốc giây tương ứng; None/rỗng = không có vision.
    ratio = tỉ lệ % thời lượng AI kể (user chỉnh 30-80, mặc định 55) —
    đưa vào prompt dạng ~X% ±10%."""
    lines = "\n".join(f"{a:.1f} {b:.1f} | {t}" for a, b, t in sentences)[:6000]
    dur = clip_end - clip_start
    ln = lang_name.upper()
    try:
        pct = int(round(max(30.0, min(80.0, float(ratio)))))
    except (TypeError, ValueError):
        pct = 55

    # ---- NGỮ CẢNH THỊ GIÁC: có ảnh -> nhìn cảnh để HIỂU; không -> chỉ transcript ----
    if frames:
        vis = (
            "NGỮ CẢNH HÌNH ẢNH: kèm theo là "
            f"{len(frames)} ẢNH khung hình chụp từ chính clip, theo thứ tự: "
            + "; ".join(f"ảnh #{i} tại giây {t:.0f}"
                        for i, (t, _p) in enumerate(frames)) + ".\n"
            "- HÃY NHÌN KỸ từng ảnh để HIỂU cảnh gì đang diễn ra tại mốc đó "
            "(ai, làm gì, bối cảnh, biểu cảm) — rồi KỂ bằng góc nhìn của "
            "bạn về đúng diễn biến đang chiếu trong khoảng part đó.\n")
    else:
        vis = (
            "KHÔNG có ảnh kèm theo — dùng transcript có mốc thời gian ở trên "
            "để HIỂU chuyện gì đang diễn ra trong từng khoảng:\n"
            "- Lời kể của part [start-end] phải khớp DIỄN BIẾN đang xảy ra "
            "trong khoảng [start-end] đó (đừng kể lệch sang chuyện đoạn "
            "khác) — nhưng KỂ theo cách của bạn, KHÔNG thuật lại lời thoại.\n")
    vis += ("- CẤM SPOILER: không nhắc trước nội dung của đoạn CHƯA chiếu tới "
            "(twist chỉ được hé khi video chiếu tới nó) — chỉ được GỢI tò mò.\n")

    return (
        f"CLIP từ giây {clip_start:.1f} đến {clip_end:.1f} (dài {dur:.0f}s) "
        f"của một video nói bằng {ln}."
        + (f' Tiêu đề gợi ý: "{title}".' if title else "") + "\n"
        "Transcript trong clip (mỗi dòng: bắt_đầu kết_thúc | lời nói) — "
        "transcript CHỈ ĐỂ BẠN HIỂU chuyện, KHÔNG phải nguồn để kể lại:\n"
        f"{lines}\n\n"
        f"{vis}\n"
        "VAI CỦA BẠN: người kể chuyện (narrator) của kênh video triệu view. "
        "Bạn đứng NGOÀI video, kể về nhân vật/sự việc cho khán giả của bạn "
        "nghe. Hãy viết KỊCH BẢN gồm các part xen kẽ: orig (nhân vật tự "
        "nói) / narrate (lời KỂ của bạn).\n\n"
        + _narrator_rules(ln, style) + "\n"
        "CÔNG THỨC VIRAL (bắt buộc):\n"
        "1) HOOK 2-3 GIÂY ĐẦU: part ĐẦU TIÊN BẮT BUỘC là narrate, câu mở "
        "phải gây SỐC hoặc TÒ MÒ tức thì (kiểu: \"Bạn sẽ không tin điều gã "
        "này sắp làm...\"). CẤM mở đầu nhạt kiểu \"Trong video này...\", "
        "\"Hôm nay chúng ta...\", \"Xin chào...\".\n"
        "2) MẠCH CHUYỆN mini story-arc theo ĐÚNG TRÌNH TỰ THỜI GIAN video: "
        "hook -> dựng bối cảnh THẬT NHANH -> đẩy căng thẳng -> twist/đỉnh "
        "điểm -> kết mở hoặc câu hỏi tương tác cho người xem. Người LẠ chưa "
        "xem video gốc phải hiểu TRỌN câu chuyện (có mở-thân-kết), CẤM nhảy "
        "cóc.\n"
        "3) ĐOẠN GIỮ TIẾNG GỐC (orig) = ĐỒNG ĐẮT: đọc transcript và chọn "
        "đúng câu nói/tiếng động/cảm xúc MẠNH NHẤT (câu chốt, tiếng hét, "
        "khoảnh khắc vỡ òa) làm twist/đỉnh điểm — KHÔNG chọn đoạn nói "
        "chuyện thường.\n"
        "4) Mỗi câu narrate phải THÊM thông tin, cảm xúc hoặc góc nhìn mới "
        "— CẤM tả lại y nguyên cái người xem tự thấy trên hình.\n\n"
        "QUY TẮC KỸ THUẬT:\n"
        f"- Chia CLIP thành các part PHỦ KÍN từ {clip_start:.1f}s đến "
        f"{clip_end:.1f}s, theo ĐÚNG thứ tự thời gian, KHÔNG chồng lấn, "
        "KHÔNG hở, KHÔNG đảo đoạn.\n"
        "- Mỗi part dài 3-15 giây. mode = \"orig\" hoặc \"narrate\".\n"
        "- start/end của MỖI part phải trùng mép câu transcript (không cắt "
        "ngang giữa câu nói).\n"
        f"- Tổng thời lượng narrate chiếm ~{pct}% clip (chấp nhận "
        f"{max(20, pct - 10)}-{min(90, pct + 10)}%); XEN KẼ với orig cho "
        "nhịp nhàng.\n"
        f"- text của part narrate: viết BẰNG {ln} (ĐÚNG ngôn ngữ video), "
        "văn NÓI tự nhiên.\n"
        f"- {_RATE_HINT} HÃY ĐẾM CHỮ: lời narrate phải đọc VỪA KHÍT độ dài "
        "part (part 6 giây tiếng Anh ~13-14 từ). ĐỪNG viết dài quá — sẽ bị "
        "cắt.\n"
        "- part orig KHÔNG cần text (để chuỗi rỗng).\n"
        f"- title: tiêu đề giật tít cho clip, viết bằng {ln}.\n"
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"title": "...", "parts": [{"start": giây, "end": giây, '
        '"mode": "orig"|"narrate", "text": "lời thuyết minh nếu narrate"}]}')


# ------------------------------------------------------------------
# VALIDATE + TỰ SỬA kịch bản (hàm thuần — unit test được)
# ------------------------------------------------------------------
def _norm_for_copy(text: str) -> str:
    """Chuẩn hoá text để so 'copy nguyên văn': bỏ dấu câu/khoảng trắng thừa,
    hạ chữ thường, chuẩn unicode (đủ bắt AI chép transcript đổi vài dấu phẩy)."""
    t = unicodedata.normalize("NFC", str(text or "")).lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def _is_transcript_copy(text: str, transcript_norm: str) -> bool:
    """Narrate text có phải CHÉP NGUYÊN VĂN transcript không (AI lười).
    Chỉ tính khi câu đủ dài (>= 4 từ và >= 15 ký tự sau chuẩn hoá) — câu quá
    ngắn ('what?', 'không thể nào') trùng ngẫu nhiên là bình thường."""
    if not transcript_norm:
        return False
    t = _norm_for_copy(text)
    if len(t) < 15 or len(t.split()) < 4:
        return False
    return t in transcript_norm


# Ngưỡng FUZZY anti-copy: lời narrate trùng > tỉ lệ từ này với transcript
# TRONG ĐÚNG KHOẢNG THỜI GIAN của part -> coi như AI kể lại lời nhân vật.
_FUZZY_COPY_MAX = 0.60


def _fuzzy_copy_ratio(text: str, window_words: set) -> float:
    """Tỉ lệ (0..1) từ của lời narrate XUẤT HIỆN trong tập từ transcript
    của cửa sổ thời gian tương ứng (đã chuẩn hoá _norm_for_copy). Lời quá
    ngắn (< 4 từ) -> 0.0 (trùng ngẫu nhiên là bình thường).

    Đây là lưới FUZZY bắt kiểu 'diễn giải lại lời nhân vật' (đổi vài từ,
    đảo trật tự) mà _is_transcript_copy (so nguyên văn) lọt: lời KỂ sáng
    tác thật sự (thêm cảm xúc/bình luận/góc nhìn ngoài) dùng từ vựng khác
    hẳn transcript nên tỉ lệ trùng thấp."""
    words = _norm_for_copy(text).split()
    if len(words) < 4 or not window_words:
        return 0.0
    hit = sum(1 for w in words if w in window_words)
    return hit / len(words)


def _window_words(sentences: list, start: float, end: float) -> set:
    """Tập từ (đã chuẩn hoá) của các câu transcript GIAO với [start, end]."""
    out: set = set()
    for a, b, t in sentences or []:
        try:
            if float(b) > start and float(a) < end and t:
                out.update(_norm_for_copy(t).split())
        except (TypeError, ValueError):
            continue
    return out


def validate_parts(parts, clip_start: float, clip_end: float,
                   min_part: float = 1.5,
                   sentences: Optional[list] = None) -> list[dict]:
    """Chuẩn hoá kịch bản LLM trả về -> list part SẠCH phủ kín clip.

    Tự sửa mọi lỗi thường gặp:
      - part không phải dict / start-end không phải số / dài < min_part -> BỎ.
      - mode lạ -> "orig"; narrate mà không có text (rỗng) -> "orig".
      - narrate mà text CHÉP NGUYÊN VĂN transcript (AI lười copy) HOẶC trùng
        FUZZY > 60% từ với transcript trong ĐÚNG khoảng thời gian part đó
        (AI diễn giải lại lời nhân vật) -> "orig" (giữ tiếng gốc còn hơn AI
        đọc lại). Cần `sentences` = [(start, end, text)] transcript để so.
      - clamp start/end vào [clip_start, clip_end].
      - chồng lấn -> cắt start part sau về end part trước (hết chỗ -> bỏ).
      - khoảng hở / đầu / cuối thiếu -> chèn part "orig" lấp kín.
      - gộp các part orig liền kề.
    Luôn trả >= 1 part (parts rỗng/hỏng hết -> 1 part orig cả clip).
    """
    clip_start, clip_end = float(clip_start), float(clip_end)
    if clip_end - clip_start < 0.5:
        return [{"start": clip_start, "end": clip_end, "mode": "orig",
                 "text": ""}]
    transcript_norm = " ".join(
        _norm_for_copy(t) for _a, _b, t in (sentences or []) if t)
    clean: list[dict] = []
    for p in (parts or []):
        if not isinstance(p, dict):
            continue
        try:
            s, e = float(p.get("start")), float(p.get("end"))
        except (TypeError, ValueError):
            continue
        s = max(clip_start, min(clip_end, s))
        e = max(clip_start, min(clip_end, e))
        if e - s < min_part:
            continue
        mode = str(p.get("mode") or "").strip().lower()
        text = str(p.get("text") or "").strip()
        if mode != "narrate":          # mode lạ/thiếu -> orig
            mode = "orig"
        if mode == "narrate" and not text:
            mode = "orig"              # narrate mà không có lời -> giữ tiếng gốc
        if mode == "narrate" and _is_transcript_copy(text, transcript_norm):
            mode, text = "orig", ""    # AI chép transcript -> giữ tiếng gốc
        if (mode == "narrate" and sentences
                and _fuzzy_copy_ratio(
                    text, _window_words(sentences, s, e)) > _FUZZY_COPY_MAX):
            mode, text = "orig", ""    # AI kể lại lời nhân vật -> tiếng gốc
        clean.append({"start": round(s, 2), "end": round(e, 2),
                      "mode": mode, "text": text if mode == "narrate" else ""})

    clean.sort(key=lambda x: (x["start"], x["end"]))

    # Khử chồng lấn: part sau bắt đầu từ end part trước
    fixed: list[dict] = []
    for p in clean:
        if fixed and p["start"] < fixed[-1]["end"]:
            p = dict(p, start=fixed[-1]["end"])
        if p["end"] - p["start"] >= min_part:
            fixed.append(p)

    # Lấp hở + đầu/cuối bằng part orig
    out: list[dict] = []
    cur = clip_start
    for p in fixed:
        if p["start"] - cur > 0.25:
            out.append({"start": round(cur, 2), "end": p["start"],
                        "mode": "orig", "text": ""})
        elif p["start"] > cur:         # hở tí xíu -> kéo part ra lấp luôn
            p = dict(p, start=round(cur, 2))
        out.append(p)
        cur = p["end"]
    if clip_end - cur > 0.25:
        out.append({"start": round(cur, 2), "end": round(clip_end, 2),
                    "mode": "orig", "text": ""})
    elif out and clip_end > cur:
        out[-1] = dict(out[-1], end=round(clip_end, 2))

    if not out:
        return [{"start": round(clip_start, 2), "end": round(clip_end, 2),
                 "mode": "orig", "text": ""}]

    # Gộp part orig liền kề (đỡ vụn)
    merged: list[dict] = [dict(out[0])]
    for p in out[1:]:
        if (p["mode"] == "orig" and merged[-1]["mode"] == "orig"
                and abs(p["start"] - merged[-1]["end"]) < 0.3):
            merged[-1]["end"] = p["end"]
        else:
            merged.append(dict(p))
    return merged


def narrate_ratio(parts: list[dict]) -> float:
    """Tỉ lệ thời lượng narrate / tổng (0..1) — để log/kiểm tra."""
    total = sum(p["end"] - p["start"] for p in parts) or 1.0
    nar = sum(p["end"] - p["start"] for p in parts if p["mode"] == "narrate")
    return nar / total


# ------------------------------------------------------------------
# 🎬 ĐẠO DIỄN MULTI-WINDOW (v4): LLM nhận TOÀN BỘ transcript, TỰ CHỌN
# 3-6 KHUNG CẢNH rời nhau theo mạch chuyện + viết kịch bản CẦU NỐI
# (kiểu recap phim). Windows hỏng -> caller fallback đường 1-span cũ.
# ------------------------------------------------------------------
_WIN_MIN = 6.0        # khung tối thiểu (prompt xin 8s; nhận từ 6s khỏi vứt oan)
_WIN_MAX = 45.0       # khung tối đa (prompt xin 40s; nhận tới 45s)
_WIN_MAX_N = 6


def build_director_prompt(listing: str, lang_name: str, style: str,
                          duration: float, min_total: float,
                          max_total: float, ratio: float = 55) -> str:
    """Prompt ĐẠO DIỄN: từ TOÀN BỘ transcript (đã rút gọn nếu dài), chọn
    3-6 khung cảnh rời nhau + viết kịch bản parts có CẦU NỐI giữa các khung."""
    ln = lang_name.upper()
    try:
        pct = int(round(max(30.0, min(80.0, float(ratio)))))
    except (TypeError, ValueError):
        pct = 55
    return (
        f"Đây là TOÀN BỘ transcript của một video dài {duration:.0f} giây, "
        f"nói bằng {ln} (mỗi dòng: GIÂY_BẮT_ĐẦU GIÂY_KẾT_THÚC | lời nói):\n"
        f"{listing}\n\n"
        "VAI CỦA BẠN: ĐẠO DIỄN kiêm NGƯỜI KỂ CHUYỆN của kênh recap triệu "
        "view. Nhiệm vụ: CẮT GHÉP video thành 1 clip recap gồm NHIỀU KHUNG "
        "CẢNH rời nhau kể TRỌN câu chuyện (như recap phim), rồi viết lời kể "
        "của bạn phủ lên.\n\n"
        "BƯỚC 1 — CHỌN KHUNG CẢNH (windows):\n"
        "- Chọn 3-6 khung cảnh RỜI NHAU bám mạch chuyện: mở đầu -> diễn "
        "biến -> twist/cao trào -> kết. ĐÚNG thứ tự thời gian, KHÔNG chồng "
        "lấn, KHÔNG đảo đoạn.\n"
        f"- Mỗi khung dài 8-40 giây; TỔNG các khung trong khoảng "
        f"{min_total:.0f}-{max_total:.0f} giây.\n"
        "- Mép khung phải trùng mép câu transcript (không cắt ngang câu "
        "nói).\n"
        "- Chỉ lấy khoảnh khắc ĐẮT (kịch tính, twist, cảm xúc mạnh, câu "
        "chốt) — mạnh dạn BỎ hẳn đoạn nhàm/lặp ở giữa; người xem sẽ được "
        "lời kể của bạn nối mạch.\n\n"
        "BƯỚC 2 — VIẾT KỊCH BẢN parts phủ lên các khung đó (xen kẽ orig = "
        "giữ tiếng gốc / narrate = bạn kể, video tắt tiếng):\n"
        "- Mỗi part dài 3-15 giây; mốc part nằm TRONG khung, KHÔNG vắt qua "
        "2 khung; các part PHỦ KÍN từng khung; start/end trùng mép câu.\n"
        "- Part ĐẦU TIÊN của khung 1 BẮT BUỘC là narrate HOOK: câu mở gây "
        "SỐC/TÒ MÒ tức thì. CẤM mở nhạt kiểu \"Trong video này...\".\n"
        "- CẦU NỐI khi nhảy cảnh: part ĐẦU của mỗi khung từ khung thứ 2 "
        "trở đi NÊN là narrate làm CẦU cho cú nhảy thời gian (kiểu: \"Và "
        "ngay sau đó...\", \"Nhưng 5 phút sau, mọi thứ đổi khác...\") — "
        "người xem không bị hụt khi cảnh nhảy. Chỉ bỏ cầu nếu 2 khung liền "
        "mạch tự nhiên.\n"
        "- CẤM KỂ ĐỀU ĐỀU: MỖI part narrate phải có ÍT NHẤT 1 trong: câu "
        "hỏi ném cho khán giả / câu cảm thán / nhá twist (\"nhưng bạn chưa "
        "thấy gì đâu...\") / con số gây sốc.\n"
        f"- Part narrate CUỐI: câu chốt đắt + KÊU GỌI tương tác (hỏi ý "
        f"kiến, kêu theo dõi) viết bằng {ln}.\n"
        f"- Tổng thời lượng narrate ~{pct}% clip (chấp nhận "
        f"{max(20, pct - 10)}-{min(90, pct + 10)}%); XEN KẼ với orig.\n"
        "- Đoạn orig = ĐỒNG ĐẮT: chọn đúng câu nói/tiếng động/cảm xúc MẠNH "
        "NHẤT trong khung làm twist/đỉnh điểm.\n"
        "- CẤM SPOILER: không nhắc trước nội dung khung CHƯA chiếu tới — "
        "chỉ được GỢI tò mò.\n\n"
        + _narrator_rules(ln, style) +
        f"\n- {_RATE_HINT} HÃY ĐẾM CHỮ: lời narrate đọc VỪA KHÍT độ dài "
        "part (part 6 giây tiếng Anh ~13-14 từ). ĐỪNG viết dài — sẽ bị "
        "cắt.\n"
        "- part orig KHÔNG cần text (chuỗi rỗng).\n"
        f"- title: tiêu đề giật tít cho clip, viết bằng {ln}.\n"
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"title": "...", "windows": [[giây_bắt_đầu, giây_kết_thúc], ...], '
        '"parts": [{"start": giây, "end": giây, "mode": "orig"|"narrate", '
        '"text": "lời thuyết minh nếu narrate"}]}')


def validate_windows(windows, duration: float,
                     min_total: float = 0.0, max_total: float = 0.0,
                     min_w: float = _WIN_MIN, max_w: float = _WIN_MAX,
                     max_n: int = _WIN_MAX_N) -> list:
    """Chuẩn hoá danh sách khung LLM trả -> [[s,e],...] SẠCH hoặc [] (hỏng).

    - phần tử không phải cặp số / dài < min_w -> BỎ; dài > max_w -> cắt đuôi.
    - clamp vào [0, duration]; sort; CHỒNG LẤN -> đẩy start khung sau về end
      khung trước (teo dưới min_w thì bỏ khung đó).
    - quá max_n khung -> giữ max_n khung đầu (đúng mạch thời gian).
    - max_total > 0: tổng vượt trần -> cắt bớt khung cuối (khúc cuối teo
      dưới min_w thì bỏ hẳn).
    - HỎNG -> []: còn < 2 khung (1 khung = chẳng phải cắt ghép, caller nên
      dùng đường 1-span cũ) hoặc min_total > 0 mà tổng < 60% min_total.
    Hàm thuần — unit test được."""
    dur = float(duration or 0)
    out = []
    for w in (windows or []):
        if not isinstance(w, (list, tuple)) or len(w) < 2:
            continue
        try:
            s, e = float(w[0]), float(w[1])
        except (TypeError, ValueError):
            continue
        s = max(0.0, s)
        if dur > 0:
            s, e = min(s, dur), min(e, dur)
        if e - s > max_w:
            e = s + max_w
        if e - s >= min_w:
            out.append([round(s, 2), round(e, 2)])
    out.sort(key=lambda w: (w[0], w[1]))
    fixed: list = []
    for s, e in out:
        if fixed and s < fixed[-1][1]:
            s = fixed[-1][1]
        if e - s >= min_w:
            fixed.append([round(s, 2), round(e, 2)])
    fixed = fixed[:max_n]
    if max_total and max_total > 0:
        total, cut = 0.0, []
        for s, e in fixed:
            if total >= max_total - 0.01:
                break
            if total + (e - s) > max_total:
                e = round(s + (max_total - total), 2)
                if e - s < min_w:
                    break
            cut.append([s, e])
            total += e - s
        fixed = cut
    if len(fixed) < 2:
        return []
    if min_total and min_total > 0:
        if sum(e - s for s, e in fixed) < 0.6 * min_total:
            return []
    return fixed


def validate_parts_windows(parts, windows: list, sentences=None,
                           min_part: float = 1.5) -> list[dict]:
    """Validate kịch bản MULTI-WINDOW: chia parts về từng khung (theo TÂM
    part), rồi validate_parts TỪNG khung (clamp vào khung, lấp hở bằng orig,
    anti-copy...) -> part KHÔNG BAO GIỜ vắt qua 2 khung (mốc luôn map được
    qua _map_to_output của dubbing). Trả list part phủ kín MỌI khung."""
    out: list[dict] = []
    for ws, we in windows or []:
        sub = []
        for p in parts or []:
            if not isinstance(p, dict):
                continue
            try:
                mid = (float(p.get("start")) + float(p.get("end"))) / 2
            except (TypeError, ValueError):
                continue
            if ws - 0.01 <= mid <= we + 0.01:
                sub.append(p)
        out.extend(validate_parts(sub, ws, we, min_part=min_part,
                                  sentences=sentences))
    return out


def write_director_script(sentences: list, lang_name: str, style: str,
                          duration: float, min_total: float,
                          max_total: float, ratio: float = 55,
                          listing: str = "") -> Optional[dict]:
    """Gọi LLM đạo diễn 1 LẦN trên TOÀN BỘ transcript -> {"title",
    "windows", "parts"} ĐÃ validate; None nếu windows/parts hỏng (caller
    fallback đường 1-span cũ).

    sentences = [(start, end, text)] TOÀN transcript (để anti-copy).
    listing = transcript RÚT GỌN cho prompt (caller gộp câu nếu video dài);
    rỗng -> tự build từ sentences.
    Ném llm.LLMError nếu gọi LLM thất bại (caller quyết fallback)."""
    if not listing:
        listing = "\n".join(f"{a:.1f} {b:.1f} | {t}"
                            for a, b, t in sentences)[:11000]
    prompt = build_director_prompt(listing, lang_name, style, duration,
                                   min_total, max_total, ratio=ratio)
    data = llm.complete_json(prompt, system=_SYSTEM)
    if not isinstance(data, dict):
        return None
    windows = validate_windows(data.get("windows"), duration,
                               min_total=min_total, max_total=max_total)
    if not windows:
        return None
    parts = validate_parts_windows(data.get("parts"), windows,
                                   sentences=sentences)
    if not any(p["mode"] == "narrate" for p in parts):
        return None
    return {"title": str(data.get("title") or "").strip(),
            "windows": windows, "parts": parts}


def write_script(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float,
                 title: str = "",
                 frames: Optional[list] = None,
                 ratio: float = 55) -> Optional[dict]:
    """Gọi LLM viết kịch bản 1 clip -> {"title","parts"} ĐÃ VALIDATE.

    sentences = [(start, end, text)] câu transcript trong phạm vi clip.
    frames = [(giây, đường_dẫn_ảnh)] khung hình gửi kèm (chỉ khi caller đã
    kiểm llm.vision_available()) — AI NHÌN cảnh để hiểu bối cảnh rồi kể; lỗi
    vision -> tự lùi về prompt chữ thuần (không vỡ luồng).
    ratio = % thời lượng AI kể user chọn (30-80, mặc định 55).
    Ném llm.LLMError nếu gọi LLM thất bại (caller quyết fail/skip).
    Trả None nếu LLM trả JSON không dùng được (không có part narrate nào).
    """
    prompt = build_prompt(sentences, lang_name, style, clip_start, clip_end,
                          title, frames=frames, ratio=ratio)
    data = None
    if frames:
        try:
            data = llm.complete_vision_json(
                prompt, [p for _t, p in frames], system=_SYSTEM)
        except Exception:  # noqa: BLE001 — vision lỗi -> lùi prompt chữ
            data = None
    if data is None:
        if frames:                      # vision fail -> prompt KHÔNG nhắc ảnh
            prompt = build_prompt(sentences, lang_name, style,
                                  clip_start, clip_end, title, ratio=ratio)
        data = llm.complete_json(prompt, system=_SYSTEM)
    if isinstance(data, list):          # model trả thẳng mảng parts
        data = {"parts": data}
    if not isinstance(data, dict):
        return None
    raw = data.get("parts")
    if not isinstance(raw, list):
        return None
    parts = validate_parts(raw, clip_start, clip_end, sentences=sentences)
    if not any(p["mode"] == "narrate" for p in parts):
        return None                     # không có thuyết minh -> vô nghĩa
    return {"title": str(data.get("title") or "").strip(), "parts": parts}
