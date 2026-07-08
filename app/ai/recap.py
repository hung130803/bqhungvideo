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
tiếp. KHUÔN CẤU TRÚC kênh recap thật (v7 — _structure_rules): người kể nói
CHỦ ĐẠO thành KHỐI DÀI 8-25s (2-5 câu liền mạch, hook đầu 3-6s), tiếng gốc
chỉ BUNG 3-12s ở khoảnh khắc đắt (~2-4 lần/clip), CẤM ping-pong đổi vai vụn;
mạch: HOOK -> DỰNG CHUYỆN -> BUNG GỐC -> KỂ TIẾP -> BUNG GỐC -> CHỐT.
Nếu có ẢNH khung hình (vision), AI nhìn cảnh để hiểu bối cảnh rồi kể.

Output JSON: {"title": "...", "parts": [{"start": s, "end": e,
              "mode": "orig"|"narrate", "text": "..."}]}
Các part PHỦ KÍN [clip_start, clip_end] theo thứ tự thời gian.

validate_parts() là hàm THUẦN (không LLM) tự sửa output hỏng: clamp vào phạm
vi clip, bỏ part rác, mode lạ -> orig, chồng lấn -> cắt, khoảng hở -> chèn
part orig, narrate rỗng/COPY transcript (kể cả FUZZY: trùng >60% từ với
transcript trong đúng khoảng thời gian đó) -> orig; SỬA CẤU TRÚC chống
ping-pong (_fix_structure + _limit_role_changes): narrate vụn kẹp giữa 2
orig -> gộp vào orig, orig <3s -> gộp vào narrate kề, quá 2 cú bung/window
-> giữ cú dài nhất, quá 8 lần đổi vai/clip -> gộp cặp ngắn nhất.
Có unit-test riêng.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Optional

from app.ai import llm

# 4 phong cách thuyết minh (key lưu QSettings/preset -> hint đưa vào prompt).
# Mỗi phong cách có MÔ TẢ CÁCH VIẾT; VÍ DỤ chuẩn vibe (few-shot) tách riêng
# _STYLE_EX THEO NGÔN NGỮ VIDEO — model hay bắt chước NGÔN NGỮ của ví dụ nên
# video EN chỉ được thấy ví dụ EN, video VI chỉ thấy ví dụ VI (KHÔNG trộn).
STYLES = {
    "story": (
        "Kể chuyện",
        "PHONG CÁCH KỂ CHUYỆN — kể cho ĐỨA BẠN THÂN nghe về gã trong video:\n"
        "  + Câu NGẮN, dồn dập, có khựng \"...\" nhá tò mò.\n"
        "  + Gọi nhân vật bằng biệt danh đời thường (gã này, bà chị, ông chú, "
        "cậu nhóc) — KHÔNG gọi trung tính kiểu 'người đàn ông'.\n"
        "  + Cuối mỗi đoạn narrate cài 1 móc tò mò: chuyện gì xảy ra tiếp?"),
    "clickbait": (
        "Giật gân câu view",
        "PHONG CÁCH GIẬT GÂN — cường điệu + câu hỏi treo LIÊN TỤC:\n"
        "  + Mở bằng cú sốc, liên tục treo: \"Nhưng khoan... bạn chưa thấy "
        "gì đâu.\"\n"
        "  + Phóng đại có kiểm soát: nhất/chưa từng/không tưởng — nhưng KHÔNG "
        "bịa chi tiết sai với video."),
    "funny": (
        "Hài hước",
        "PHONG CÁCH HÀI HƯỚC — mỉa nhẹ + nhân cách hóa, KHÔNG giải thích joke:\n"
        "  + Cà khịa như nói xấu bạn mình: chọc vào cái ngớ ngẩn, tương phản, "
        "sự tự tin lố của nhân vật.\n"
        "  + Nhân cách hóa đồ vật/con vật; thả joke rồi ĐI TIẾP luôn."),
    "analysis": (
        "Phân tích sâu",
        "PHONG CÁCH PHÂN TÍCH — mổ xẻ 'VÌ SAO' với giọng tự tin, sắc lạnh:\n"
        "  + Chỉ ra cái người xem KHÔNG tự nhận ra; khẳng định chắc nịch rồi "
        "chứng minh, không vòng vo 'có lẽ/hình như'.\n"
        "  + Chốt mỗi ý bằng 1 câu đắt: bài học/ý nghĩa đằng sau."),
}
DEFAULT_STYLE = "story"

# Few-shot VÍ DỤ chuẩn vibe theo phong cách, TÁCH THEO NGÔN NGỮ video:
# "vi" cho video tiếng Việt, "en" cho MỌI ngôn ngữ khác (ví dụ tiếng Anh
# trung tính — quan trọng là KHÔNG cho model thấy tiếng Việt khi video
# không phải tiếng Việt, tránh model trả lời theo ngôn ngữ của ví dụ).
_STYLE_EX = {
    "story": {
        "vi": "\"Gã này tưởng hôm nay là ngày may mắn nhất đời mình. Sai. "
              "Sai khủng khiếp...\" — \"Và cái cách bà chị phản ứng... tôi "
              "kể bạn nghe, không ai đỡ nổi.\"",
        "en": "\"This guy thought today was the luckiest day of his life. "
              "Wrong. Horribly wrong...\" — \"And the way she reacted... "
              "let me tell you, nobody saw that coming.\"",
    },
    "clickbait": {
        "vi": "\"Đây có thể là quyết định tệ nhất đời anh ta. Và điên nhất "
              "là... anh ta còn chưa biết điều đó.\" — \"99% người xem đoán "
              "sai đoạn tiếp theo. Bạn thì sao?\"",
        "en": "\"This might be the worst decision of his life. And the "
              "craziest part... he doesn't even know it yet.\" — \"99% of "
              "viewers guess the next part wrong. Will you?\"",
    },
    "funny": {
        "vi": "\"Sự tự tin của ông chú này... đóng thuế được luôn đấy.\" — "
              "\"Con mèo nhìn chủ kiểu: rồi, lại nữa rồi.\"",
        "en": "\"The confidence on this man... you could tax it.\" — \"The "
              "cat looks at its owner like: here we go again.\"",
    },
    "analysis": {
        "vi": "\"Để ý tay trái gã... đó không phải ngẫu nhiên. Đó là tính "
              "toán.\" — \"Ai cũng nghĩ cô ấy thua từ giây thứ ba. Nhưng "
              "không. Chính lúc đó cô ấy đang thắng.\"",
        "en": "\"Watch his left hand... that's not luck. That's "
              "calculation.\" — \"Everyone thinks she lost by second three. "
              "But no. That's exactly when she started winning.\"",
    },
}

_SYSTEM = (
    "Bạn là NGƯỜI KỂ CHUYỆN (narrator) của một kênh video triệu view. Bạn "
    "đứng NGOÀI video, kể về nhân vật và sự việc trong video cho khán giả "
    "của bạn nghe — như một người dẫn chuyện lôi cuốn, KHÔNG phải người "
    "thuật lại lời thoại. Bạn tự hiểu bối cảnh + nội dung + lời thoại rồi "
    "TỰ SÁNG TÁC lời kể hấp dẫn của riêng mình. GIỌNG BẠN LÀ CHỦ ĐẠO: bạn "
    "kể thành KHỐI DÀI liền mạch trên nền hình (video tắt tiếng); tiếng "
    "gốc chỉ được BUNG ngắn ở đúng khoảnh khắc đắt nhất (để nhân vật tự "
    "nói) — KHÔNG nói vụn 1-2 câu rồi nhả về tiếng gốc kiểu ping-pong. "
    "2-3 giây đầu quyết định người xem ở lại hay lướt — câu mở phải gây "
    "sốc/tò mò tức thì. CHỈ trả JSON thuần, không thêm chữ nào khác.")

# Tốc độ đọc TTS để AI canh độ dài lời thuyết minh (ghi thẳng vào prompt)
_RATE_HINT = ("Tốc độ giọng đọc AI: tiếng Anh ~2.3 từ/giây, tiếng Việt ~3.5 "
              "âm tiết/giây (ngôn ngữ khác tương đương ~2.5 từ/giây).")

# ------------------------------------------------------------------
# KHUÔN CẤU TRÚC KÊNH RECAP THẬT (v7): người kể nói CHỦ ĐẠO thành KHỐI DÀI
# (8-25s = 2-5 câu liền mạch), tiếng gốc chỉ BUNG ngắn (3-12s) ở khoảnh
# khắc đắt (~2-4 lần/clip) — hết kiểu ping-pong nói vụn 1-2 câu rồi nhả về
# gốc. Ngưỡng dùng CHUNG cho prompt + validate (đổi 1 chỗ, 2 nơi cùng theo).
# ------------------------------------------------------------------
_NARR_MIN_S = 8            # khối kể thường 8-25 giây (2-5 câu liền mạch)
_NARR_MAX_S = 25
_HOOK_MIN_S = 3            # hook đầu clip 3-6 giây
_HOOK_MAX_S = 6
_ORIG_MIN_S = 3            # cú bung tiếng gốc 3-12 giây
_ORIG_MAX_S = 12
# Ngưỡng SỬA CẤU TRÚC trong validate (chống ping-pong):
_STRUCT_NARR_MIN = 6.0     # narrate < 6s kẹp giữa 2 orig (không phải hook) -> gộp vào orig
_STRUCT_ORIG_MIN = 3.0     # orig < 3s -> gộp vào narrate kề
_MAX_ORIG_BREAKS = 2       # tối đa số lần bung tiếng gốc MỖI window
_MAX_ROLE_CHANGES = 8      # tối đa TỔNG số lần đổi vai narrate<->orig cả clip


def _structure_rules(per_window: bool = False) -> str:
    """KHUÔN CẤU TRÚC kênh recap thật — dùng CHUNG cho prompt 1-span
    (build_prompt) và prompt đạo diễn (build_director_prompt): người kể nói
    chủ đạo khối dài, tiếng gốc chỉ bung ở khoảnh khắc đắt, cấm ping-pong.
    per_window=True -> thêm trần số lần bung TỪNG KHUNG CẢNH (đạo diễn)."""
    return (
        "KHUÔN CẤU TRÚC CLIP (bắt buộc — dựng kịch bản theo ĐÚNG từng "
        "bước):\n"
        f"  B1. HOOK — narrate {_HOOK_MIN_S}-{_HOOK_MAX_S} giây: 1 câu mở "
        "gây SỐC/TÒ MÒ tức thì.\n"
        f"  B2. DỰNG CHUYỆN — narrate KHỐI DÀI {_NARR_MIN_S}-{_NARR_MAX_S} "
        "giây (2-5 câu LIỀN MẠCH): bạn kể trên nền hình (video câm) — ai, "
        "chuyện gì, vì sao đáng xem; CUỐI khối DẪN MỒI vào tiếng gốc "
        "(kiểu: \"Và nghe gã nói câu này...\").\n"
        f"  B3. BUNG TIẾNG GỐC lần 1 — orig {_ORIG_MIN_S}-{_ORIG_MAX_S} "
        "giây: khoảnh khắc đắt (câu nói hay nhất / tiếng động / cao trào) "
        "— để nhân vật TỰ nói.\n"
        f"  B4. KỂ TIẾP ĐẨY CĂNG — narrate khối dài {_NARR_MIN_S}-"
        f"{_NARR_MAX_S} giây: bình luận + đẩy căng thẳng, dẫn mồi cú bung "
        "kế tiếp.\n"
        f"  B5. BUNG TIẾNG GỐC lần 2 — orig {_ORIG_MIN_S}-{_ORIG_MAX_S} "
        "giây: khoảnh khắc ĐỈNH NHẤT clip.\n"
        f"  B6. CHỐT — narrate {_NARR_MIN_S}-{_NARR_MAX_S} giây: câu chốt "
        "đắt + KÊU GỌI tương tác.\n"
        "  (Clip DÀI -> chèn thêm cặp KỂ DÀI -> BUNG GỐC ở giữa; clip NGẮN "
        "-> bỏ B4+B5 — nhưng THỨ TỰ các bước KHÔNG đổi.)\n"
        "ĐỘ DÀI PART (bắt buộc):\n"
        f"- Part narrate (trừ hook) dài {_NARR_MIN_S}-{_NARR_MAX_S} giây = "
        "2-5 câu LIỀN MẠCH có nhịp — chỗ nhiều chỗ ít LINH HOẠT theo "
        "chuyện, CẤM chia đều tăm tắp.\n"
        f"- Part orig dài {_ORIG_MIN_S}-{_ORIG_MAX_S} giây; CẢ CLIP chỉ "
        "BUNG tiếng gốc 2-4 lần"
        + (" — MỖI khung cảnh TỐI ĐA 1-2 lần bung" if per_window else "")
        + "; trước MỖI lần bung phải có lời DẪN MỒI.\n"
        "CẤM PING-PONG (nói vụn 1-2 câu rồi nhả về tiếng gốc — nghe như "
        "người chen ngang lúc nhân vật đang nói, nghiệp dư):\n"
        f"- CẤM part narrate < {_STRUCT_NARR_MIN:.0f} giây kẹp giữa 2 part "
        "orig (trừ HOOK đầu clip).\n"
        f"- CẤM part orig < {_STRUCT_ORIG_MIN:.0f} giây.\n"
        "- CẤM quá 2 lần đổi vai narrate<->orig trong bất kỳ 20 giây nào.\n")


def style_label(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[0]


# ------------------------------------------------------------------
# AUDIO TAG CẢM XÚC (ElevenLabs v3): AI đạo diễn chèn [excited]/[whispers]/
# [dramatic pause]... + nhấn CAPS vào LỜI narrate để giọng lên xuống, nhấn
# nhá như người thật. Các tag CHỈ để TTS v3 đọc — TUYỆT ĐỐI KHÔNG được lọt
# vào PHỤ ĐỀ. _strip_audio_tags dọn tag + hạ CAPS về thường cho bản làm sub.
# ------------------------------------------------------------------
# [tag] cảm xúc: 1-3 từ chữ-thường trong ngoặc vuông (["excited"], [dramatic
# pause], [whispers]...). KHÔNG bắt [123]/[..] tránh nuốt số/dấu người dùng gõ.
_AUDIO_TAG_RE = re.compile(r"\[[a-zA-Z][a-zA-Z '\-]{0,28}\]")
# TÁCH theo "từ" (chuỗi ký tự chữ liền nhau, giữ dấu Việt) để dò từ nhấn CAPS.
# CỐ Ý dùng .isupper() thay vì regex range [A-ZÀ-Ỹ]: range unicode đó lồng cả
# ký tự Việt THƯỜNG (ã, đ...) -> bắt oan chữ hoa đầu câu ("Gã" -> "gã"). Dùng
# .isupper() (một từ chỉ True khi MỌI chữ cái đều hoa) mới đúng "từ nhấn CAPS".
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _lower_caps_word(m: "re.Match") -> str:
    """Hạ 1 TỪ NHẤN CAPS (>=2 chữ, TOÀN HOA: "SAI"/"GONE"/"THẮNG") về chữ
    thường. Từ thường/viết-hoa-đầu ("Gã", "Poker") GIỮ NGUYÊN — chỉ từ nhấn
    mạnh toàn hoa mới hạ (chuẩn cho phụ đề)."""
    w = m.group(0)
    return w.lower() if len(w) >= 2 and w.isupper() else w


def _strip_audio_tags(text: str) -> str:
    """Bỏ audio tag cảm xúc ([excited]/[whispers]/[dramatic pause]...) và HẠ
    các từ nhấn CAPS về chữ thường -> bản SẠCH dùng cho PHỤ ĐỀ + word timing
    (giọng edge/gemini cũng nhận bản này vì KHÔNG hiểu tag v3). CHỈ đường TTS
    ElevenLabs v3 nhận bản CÓ tag. Chuẩn hoá khoảng trắng thừa do bỏ tag.
    Hàm thuần — unit test được.

    Ví dụ: '[excited]Không thể TIN nổi... [whispers]hắn đã thua.' ->
           'Không thể tin nổi... hắn đã thua.'"""
    t = str(text or "")
    if not t:
        return ""
    t = _AUDIO_TAG_RE.sub(" ", t)          # bỏ mọi [tag]
    t = _WORD_RE.sub(_lower_caps_word, t)  # HẠ từ nhấn CAPS (toàn hoa) về thường
    # gọn khoảng trắng + khoảng trắng thừa trước dấu câu do bỏ tag
    t = re.sub(r"\s+([,.!?…;:])", r"\1", t)
    return re.sub(r"\s{2,}", " ", t).strip()


# Khối chỉ dẫn AI CHÈN audio tag cảm xúc (chỉ đưa vào prompt khi emotion BẬT).
# Tag hợp lệ v3 + cách nhấn CAPS — AI tự chọn hợp NGỮ CẢNH từng câu.
def _emotion_rule(ln: str) -> str:
    """Chỉ dẫn CHÈN audio tag cảm xúc kiểu ElevenLabs v3 vào lời narrate
    (chỉ khi user BẬT 'Giọng cảm xúc'). Tag nằm TRONG text narrate, hệ thống
    tự tách khỏi phụ đề (chỉ giọng đọc)."""
    return (
        "🎭 GIỌNG CẢM XÚC (bắt buộc — kiểu ElevenLabs v3): CHÈN audio tag "
        "cảm xúc NGAY TRONG lời narrate để giọng đọc lên xuống, nhấn nhá, "
        "cảm xúc mạnh NHƯ NGƯỜI THẬT:\n"
        "- Đặt tag trong ngoặc vuông NGAY TRƯỚC cụm cần cảm xúc, hợp NGỮ "
        "CẢNH từng câu: [excited] (hào hứng), [whispers] (thì thầm gây tò "
        "mò), [sighs] (thở dài), [laughs] (cười), [sarcastic] (mỉa mai), "
        "[curious] (tò mò), [dramatic pause] (ngừng kịch tính trước cú "
        "twist).\n"
        "- NHẤN từ khoá GÂY SỐC bằng CHỮ IN HOA (vd: \"và rồi... tất cả "
        "BIẾN MẤT\") + dùng dấu \"...\" để ngắt nhá.\n"
        "- TIẾT CHẾ BẮT BUỘC (audio tag cũng TÍNH KÝ TỰ TTS trả phí): mỗi "
        "part CHỈ 1-2 tag, đặt ĐÚNG chỗ đắt nhất (hook/twist/đỉnh điểm); "
        "câu thường KHÔNG tag. Tag phải khớp nội dung (cảnh vui -> "
        "[excited]/[laughs]; cảnh căng -> [whispers]/[dramatic pause]).\n"
        "- Tag CHỈ để giọng đọc, hệ thống TỰ BỎ khỏi phụ đề — cứ chèn thoải "
        "mái, phụ đề vẫn sạch.\n"
        + ("  VÍ DỤ: \"[whispers]Không ai ngờ... [excited]hắn đã THẮNG tất "
           "cả!\"\n" if _is_vi_lang(ln) else
           "  EXAMPLE: \"[whispers]Nobody saw it coming... [excited]he "
           "WON it all!\"\n"))


# ------------------------------------------------------------------
# NGÔN NGỮ ĐẦU RA: tên tiếng Anh chuẩn + hậu kiểm "viết sai ngôn ngữ"
# ------------------------------------------------------------------
# Tên ngôn ngữ CHUẨN TIẾNG ANH cho prompt: model tuân lệnh "write in
# English" tốt hơn hẳn "viết bằng tiếng Anh" (tên Việt dễ kéo model trả
# lời tiếng Việt). Key = code whisper HOẶC alias tên dài/tên Việt cũ.
_LANG_EN = {
    "vi": "Vietnamese", "en": "English", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "th": "Thai", "fr": "French", "es": "Spanish",
    "de": "German", "ru": "Russian", "id": "Indonesian", "pt": "Portuguese",
    "hi": "Hindi", "ar": "Arabic", "it": "Italian", "nl": "Dutch",
    "tr": "Turkish", "pl": "Polish", "uk": "Ukrainian", "ms": "Malay",
    "tl": "Filipino",
}
_LANG_ALIAS = {
    "vietnamese": "vi", "tiếng việt": "vi", "tieng viet": "vi",
    "english": "en", "tiếng anh": "en", "japanese": "ja", "tiếng nhật": "ja",
    "korean": "ko", "tiếng hàn": "ko", "chinese": "zh", "tiếng trung": "zh",
    "thai": "th", "tiếng thái": "th", "french": "fr", "tiếng pháp": "fr",
    "spanish": "es", "tiếng tây ban nha": "es", "german": "de",
    "tiếng đức": "de", "russian": "ru", "tiếng nga": "ru",
    "indonesian": "id", "tiếng indonesia": "id", "portuguese": "pt",
}


def lang_en_name(code: str) -> str:
    """Code/tên ngôn ngữ -> tên CHUẨN TIẾNG ANH ("English", "Vietnamese"...)
    để ÉP ngôn ngữ đầu ra trong prompt recap. Không nhận diện được -> trả
    nguyên chuỗi (vẫn ép được nếu whisper trả tên lạ); rỗng -> cụm mô tả.
    Hàm thuần — unit test được."""
    s = str(code or "").strip().lower()
    s = _LANG_ALIAS.get(s, s)
    if s in _LANG_EN:
        return _LANG_EN[s]
    return (str(code).strip() if str(code or "").strip()
            else "the original spoken language of the video")


def _is_vi_lang(lang_name: str) -> bool:
    """lang_name (code/tên Anh/tên Việt) có phải TIẾNG VIỆT không."""
    s = str(lang_name or "").strip().lower()
    return _LANG_ALIAS.get(s, s) == "vi"


# Ký tự ĐẶC TRƯNG tiếng Việt: ă đ ơ ư + nguyên âm mang dấu hỏi/ngã/nặng +
# nguyên âm mũ/móc kèm thanh (ấ ề ộ ớ ữ...). CỐ TÌNH KHÔNG tính â ê ô á à
# é è í ó ú ý ã õ trần — có trong Pháp/Bồ/Tây Ban Nha ("café", "hôtel",
# "São") -> không bắt oan từ mượn trong lời kể tiếng Anh.
_VI_CHAR_SET = frozenset(
    "ăằắẳẵặầấẩẫậđềếểễệồốổỗộơờớởỡợưừứửữựạảẹẻẽịỉĩọỏụủũỹỵỷỳ")


def looks_vietnamese(text: str) -> bool:
    """Text có phải tiếng Việt không: >= 2 ký tự đặc trưng Việt VÀ mật độ
    > 10% số ký tự chữ (câu Việt thật dày dấu; "café"/tên riêng lác đác
    không đủ). Hàm thuần — unit test được."""
    t = unicodedata.normalize("NFC", str(text or "")).lower()
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return False
    hits = sum(1 for c in letters if c in _VI_CHAR_SET)
    return hits >= 2 and hits / len(letters) > 0.10


def _looks_wrong_lang(text: str, lang_name: str) -> bool:
    """HẬU KIỂM ngôn ngữ: video KHÔNG phải tiếng Việt mà text (lời narrate/
    title) là tiếng Việt -> SAI (LLM trả lời theo ngôn ngữ prompt thay vì
    ngôn ngữ video). Hàm thuần — unit test được."""
    return not _is_vi_lang(lang_name) and looks_vietnamese(text)


def script_lang_issues(title: str, parts: list, lang_name: str):
    """-> (list index part narrate SAI ngôn ngữ, title_sai: bool).
    Chỉ bắt chiều 'video KHÔNG Việt mà viết Việt' (chiều chặn cứng);
    chiều ngược lại chỉ cảnh báo (_vi_ascii_warn). Hàm thuần."""
    bad = [i for i, p in enumerate(parts or [])
           if str(p.get("mode") or "") == "narrate"
           and _looks_wrong_lang(str(p.get("text") or ""), lang_name)]
    return bad, _looks_wrong_lang(str(title or ""), lang_name)


def _vi_ascii_warn(parts, lang_name: str) -> str:
    """Video TIẾNG VIỆT mà TOÀN BỘ lời narrate không dấu (ASCII thuần) ->
    NGHI sai ngôn ngữ — chỉ CẢNH BÁO, không chặn (tên riêng/không dấu vẫn
    có thể hợp lệ). Hàm thuần."""
    if not _is_vi_lang(lang_name):
        return ""
    texts = [str(p.get("text") or "") for p in (parts or [])
             if str(p.get("mode") or "") == "narrate"]
    joined = "".join(texts)
    if texts and joined.strip() and all(ord(c) < 128 for c in joined):
        return ("nghi kịch bản sai ngôn ngữ: video tiếng Việt nhưng lời kể "
                "toàn chữ không dấu")
    return ""


# Chỉ trích gửi kèm khi RETRY vì viết sai ngôn ngữ (dùng cho cả 2 đường).
_WRONG_LANG_NOTE = (
    "LẦN TRƯỚC bạn VIẾT SAI NGÔN NGỮ: video này nói {ln} nhưng bạn viết "
    "tiêu đề/lời kể bằng tiếng Việt. Bạn PHẢI viết lại TOÀN BỘ title, "
    "context_summary và MỌI text narrate 100% bằng {ln} — KHÔNG một từ "
    "tiếng Việt nào (giọng đọc {ln} sẽ đọc lời của bạn).")


def _lang_rule(ln: str) -> str:
    """Khối ÉP NGÔN NGỮ ĐẦU RA — đặt NGAY ĐẦU prompt (trước mọi luật) và
    nhắc lại ở cuối sát chỗ yêu cầu JSON (model chú ý 2 đầu prompt)."""
    out = (f"NGÔN NGỮ ĐẦU RA BẮT BUỘC: {ln}.\n"
           f"TOÀN BỘ \"title\", \"context_summary\" và MỌI \"text\" trong "
           f"parts PHẢI viết 100% bằng {ln}.\n")
    if not _is_vi_lang(ln):
        out += (f"CẤM viết tiếng Việt — video KHÔNG nói tiếng Việt; giọng "
                f"đọc {ln} sẽ đọc lời bạn viết, chữ sai ngôn ngữ sẽ đọc lơ "
                "lớ hỏng clip. (Chỉ dẫn dưới đây viết bằng tiếng Việt CHỈ "
                f"để mô tả luật — đầu ra vẫn phải 100% {ln}.)\n")
    return out


def _lang_remind(ln: str) -> str:
    """Nhắc lại luật ngôn ngữ NGAY TRƯỚC yêu cầu trả JSON."""
    return (f"NHẮC LẠI — QUAN TRỌNG NHẤT: title, context_summary và mọi "
            f"text narrate PHẢI viết 100% bằng {ln}"
            + ("" if _is_vi_lang(ln) else ", TUYỆT ĐỐI KHÔNG tiếng Việt")
            + ".\n")


def _style_hint(key: str, ln: str = "") -> str:
    """Mô tả phong cách + VÍ DỤ chuẩn vibe ĐÚNG NGÔN NGỮ video (vi -> ví dụ
    Việt; mọi ngôn ngữ khác -> ví dụ tiếng Anh, không trộn 2 thứ tiếng)."""
    k = key if key in STYLES else DEFAULT_STYLE
    ex = _STYLE_EX[k]["vi" if _is_vi_lang(ln) else "en"]
    return (STYLES[k][1]
            + "\n  VÍ DỤ chuẩn vibe (bắt chước VIBE, đừng chép): " + ex)


def _narrator_rules(ln: str, style: str, emotion: bool = False) -> str:
    """Khối luật NGƯỜI KỂ CHUYỆN dùng chung cho prompt 1-clip (build_prompt)
    và prompt đạo diễn multi-window (build_director_prompt) — giữ 1 nguồn
    để 2 đường không lệch luật (anti-copy, văn nói, vibe phong cách).
    emotion=True -> chèn thêm khối _emotion_rule (AI tự chèn audio tag v3)."""
    return (
        "QUY TRÌNH 2 BƯỚC (bắt buộc — nghĩ theo 2 vai TÁCH BẠCH):\n"
        "• BƯỚC 1 (VAI HIỂU CHUYỆN): đọc transcript, tự viết trong đầu 1 câu "
        "TÓM TẮT BỐI CẢNH ngắn — chuyện gì, ai, diễn biến. Câu này CHỈ để bạn "
        "HIỂU, TUYỆT ĐỐI KHÔNG dùng làm lời đọc (điền vào trường "
        "\"context_summary\").\n"
        "• BƯỚC 2 (VAI NGƯỜI KỂ NGOÀI): dựa trên bối cảnh đó, viết lời "
        "narrate — BÌNH LUẬN / CẢM XÚC / DỰ ĐOÁN / ĐẶT CÂU HỎI về chuyện. "
        "Đoạn tiếng gốc (orig) để NHÂN VẬT TỰ NÓI — lời narrate chỉ DẪN MỒI "
        "vào, KHÔNG nói hộ, KHÔNG thuật lại câu nhân vật.\n\n"
        "CẤM TUYỆT ĐỐI trong lời narrate:\n"
        "- CẤM lặp lại, diễn giải lại, PARAPHRASE hay tóm tắt lại câu nhân "
        "vật VỪA nói hoặc SẮP nói trong transcript — người xem sắp nghe/vừa "
        "nghe câu đó rồi, kể lại là thừa và chán. Đổi vài từ/đảo trật tự VẪN "
        "là thuật lại -> CẤM.\n"
        "- CẤM dùng lại NGUYÊN CỤM 3 từ trở lên có trong transcript (nhại "
        "cụm lời thoại).\n"
        "- CẤM kiểu tường thuật gián tiếp: \"anh ấy nói rằng...\", \"cô ấy "
        "bảo là...\", \"anh ta giải thích rằng...\".\n"
        # VÍ DỤ ✅/❌ theo ĐÚNG ngôn ngữ video (video Việt -> ví dụ Việt;
        # ngôn ngữ khác -> ví dụ tiếng Anh) — KHÔNG trộn 2 thứ tiếng để
        # model không bắt chước nhầm ngôn ngữ của ví dụ.
        + ("VÍ DỤ ĐÚNG/SAI (bám vào transcript, KHÔNG chép):\n"
           "  Transcript nhân vật: \"tôi bấm nhầm nút bán hết cổ phiếu\".\n"
           "  ✅ ĐÚNG (bình luận góc ngoài): \"Gã này vừa mất cả gia tài "
           "chỉ vì một cú click...\"\n"
           "  ❌ SAI (thuật lại): \"Anh ấy nói anh ấy bấm nhầm nút bán hết "
           "cổ phiếu.\"\n\n"
           if _is_vi_lang(ln) else
           "VÍ DỤ ĐÚNG/SAI (bám vào transcript, KHÔNG chép):\n"
           "  Transcript: \"i accidentally sold all my shares\".\n"
           "  ✅ RIGHT (outsider comment): \"One wrong click. His entire "
           "fortune — gone.\"\n"
           "  ❌ WRONG (retelling): \"He says he accidentally sold all his "
           "shares.\"\n\n") +
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
        # DRAMA/VIRAL nhưng BÁM SÁT nội dung (không bịa/không lệch) — few-shot
        # cặp ĐÚNG (drama + dính chi tiết cảnh) vs SAI (bịa/chung chung/lệch).
        "DRAMA & CUỐN (bắt buộc — nhưng BÁM SÁT nội dung, KHÔNG bịa):\n"
        "- Mỗi câu kể phải NHẮC 1 chi tiết CỤ THỂ của cảnh (tên/hành động/"
        "con số/đồ vật CÓ trong transcript) RỒI thêm cảm xúc/twist/stakes: "
        "\"điều hắn không ngờ là...\", \"và đây là lúc mọi thứ sụp đổ...\", "
        "\"cái giá phải trả lớn hơn hắn tưởng...\".\n"
        "- CẤM bịa chi tiết KHÔNG có trong video; CẤM lệch chủ đề; CẤM câu "
        "sáo rỗng chung chung lắp cảnh nào cũng được (\"thật không thể tin "
        "được\", \"quá đỉnh luôn\").\n"
        + ("  VÍ DỤ ✅ (drama + BÁM cảnh 'đặt cược 500 đô'): \"500 đô... đặt "
           "hết vào một ván bài. Điều gã không ngờ là ván này sẽ đổi cả đời "
           "gã.\"\n"
           "  VÍ DỤ ❌ (bịa/lệch): \"Gã rút súng ra bắn\" (video KHÔNG có "
           "súng) — BỊA.\n"
           "  VÍ DỤ ❌ (chung chung): \"Thật không thể tin nổi các bạn ạ!\" "
           "— không dính chi tiết nào, lắp đâu cũng được.\n"
           if _is_vi_lang(ln) else
           "  ✅ EXAMPLE (drama + on-scene 'bet 500 dollars'): \"500 "
           "dollars... all on one hand. What he didn't expect was that this "
           "hand would change everything.\"\n"
           "  ❌ WRONG (fabricated): \"He pulls out a gun\" (video has NO "
           "gun) — MADE UP.\n"
           "  ❌ WRONG (generic): \"This is absolutely unbelievable guys!\" "
           "— sticks to no detail, fits any clip.\n")
        + (_emotion_rule(ln) if emotion else "")
        + f"{_style_hint(style, ln)}\n"
        + ("(Lời narrate viết bằng TIẾNG VIỆT — đúng ngôn ngữ video.)\n"
           if _is_vi_lang(ln) else
           "(Chỉ dẫn/luật viết bằng tiếng Việt CHỈ để bạn hiểu — lời "
           f"narrate, title, context_summary THẬT phải viết 100% bằng {ln}, "
           "KHÔNG được viết tiếng Việt.)\n"))


def build_prompt(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float, title: str = "",
                 frames: Optional[list] = None, ratio: float = 55,
                 emotion: bool = False) -> str:
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
        # KHỐI ÉP NGÔN NGỮ đặt TRƯỚC MỌI LUẬT (lỗi thật: video EN nhưng AI
        # viết kịch bản tiếng Việt vì toàn bộ prompt là tiếng Việt).
        _lang_rule(ln) + "\n"
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
        + _narrator_rules(ln, style, emotion=emotion) + "\n"
        "CÔNG THỨC VIRAL (bắt buộc):\n"
        + _structure_rules() +
        "- HOOK: part ĐẦU TIÊN BẮT BUỘC là narrate, câu mở phải gây SỐC "
        "hoặc TÒ MÒ tức thì (kiểu: \"Bạn sẽ không tin điều gã này sắp "
        "làm...\"). CẤM mở đầu nhạt kiểu \"Trong video này...\", \"Hôm nay "
        "chúng ta...\", \"Xin chào...\".\n"
        "- MẠCH CHUYỆN theo ĐÚNG TRÌNH TỰ THỜI GIAN video. Người LẠ chưa "
        "xem video gốc phải hiểu TRỌN câu chuyện (có mở-thân-kết), CẤM "
        "nhảy cóc.\n"
        "- ĐOẠN GIỮ TIẾNG GỐC (orig) = ĐỒNG ĐẮT: đọc transcript và chọn "
        "đúng câu nói/tiếng động/cảm xúc MẠNH NHẤT (câu chốt, tiếng hét, "
        "khoảnh khắc vỡ òa) làm twist/đỉnh điểm — KHÔNG chọn đoạn nói "
        "chuyện thường.\n"
        "- Mỗi khối narrate phải THÊM thông tin, cảm xúc hoặc góc nhìn mới "
        "— CẤM tả lại y nguyên cái người xem tự thấy trên hình.\n\n"
        "QUY TẮC KỸ THUẬT:\n"
        f"- Chia CLIP thành các part PHỦ KÍN từ {clip_start:.1f}s đến "
        f"{clip_end:.1f}s, theo ĐÚNG thứ tự thời gian, KHÔNG chồng lấn, "
        "KHÔNG hở, KHÔNG đảo đoạn.\n"
        f"- Độ dài part theo KHUÔN CẤU TRÚC ở trên: narrate {_NARR_MIN_S}-"
        f"{_NARR_MAX_S} giây (hook {_HOOK_MIN_S}-{_HOOK_MAX_S} giây), orig "
        f"{_ORIG_MIN_S}-{_ORIG_MAX_S} giây. mode = \"orig\" hoặc "
        "\"narrate\".\n"
        "- start/end của MỖI part phải trùng mép câu transcript (không cắt "
        "ngang giữa câu nói).\n"
        f"- Tổng thời lượng narrate chiếm ~{pct}% clip (chấp nhận "
        f"{max(20, pct - 10)}-{min(90, pct + 10)}%) — người kể nói CHỦ "
        "ĐẠO, tiếng gốc chỉ bung đúng chỗ đắt.\n"
        f"- text của part narrate: viết BẰNG {ln} (ĐÚNG ngôn ngữ video), "
        "văn NÓI tự nhiên — khối dài = 2-5 câu NGẮN nối nhau LIỀN MẠCH "
        "cùng 1 mạch ý.\n"
        f"- {_RATE_HINT} HÃY ĐẾM CHỮ: lời narrate phải đọc VỪA KHÍT độ dài "
        "part (part 10 giây tiếng Anh ~20 từ, part 20 giây ~41-46 từ). "
        "ĐỪNG viết dài quá — sẽ bị cắt.\n"
        "- TRẦN CỨNG SỐ CHỮ (hệ số an toàn 0.9): TUYỆT ĐỐI KHÔNG viết quá "
        "(số_giây_part × 2.3 × 0.9) từ tiếng Anh cho part đó — hook 6 giây "
        "tối đa 12 từ, part 10 giây tối đa 20 từ, part 20 giây tối đa 41 "
        "từ (tiếng Việt: số_giây × 3.5 × 0.9 ≈ 3 âm tiết/giây). ĐẾM LẠI "
        "từng part trước khi trả — lời vượt trần SẼ BỊ CẮT CỤT giữa câu "
        "khi đọc.\n"
        "- SÀN CỨNG SỐ CHỮ: lời narrate phải LẤP ĐẦY ~85-95% thời lượng "
        "part — TỐI THIỂU (số_giây_part × 2.3 × 0.75) từ tiếng Anh (part "
        "20 giây >= 34 từ; tiếng Việt: số_giây × 3.5 × 0.75 âm tiết). "
        "KHÔNG ĐỦ Ý để lấp thì VIẾT PART NGẮN LẠI (rút end xuống), ĐỪNG "
        "để giọng đọc xong mà hình còn trống dài không ai nói gì.\n"
        "- part orig KHÔNG cần text (để chuỗi rỗng).\n"
        f"- title: tiêu đề giật tít cho clip, viết bằng {ln}.\n"
        "- context_summary: 1 câu TÓM TẮT BỐI CẢNH (bước 1) — CHỈ để bạn "
        "hiểu, KHÔNG phải lời đọc.\n"
        + _lang_remind(ln) +
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"context_summary": "...", "title": "...", "parts": '
        '[{"start": giây, "end": giây, "mode": "orig"|"narrate", '
        '"text": "lời thuyết minh nếu narrate"}]}')


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
# SIẾT 0.60 -> 0.45: diễn giải SÁT NGHĨA (đổi vài từ, đảo trật tự) vẫn trùng
# ~45-55% từ với transcript -> nghe như "đọc lại lời người kia". Lời KỂ sáng
# tác thật (thêm cảm xúc/bình luận/góc ngoài) dùng từ vựng khác hẳn -> trùng
# thấp (thường <30%), nên hạ ngưỡng vẫn KHÔNG loại nhầm câu sáng tác.
_FUZZY_COPY_MAX = 0.45
# n-gram CHẶN THEO Ý: narrate trùng >= số TỪ-NỘI-DUNG LIÊN TIẾP này với 1 cụm
# trong transcript window -> coi là THUẬT LẠI lời nhân vật (dù tỉ lệ tổng thấp).
# Bắt kiểu "anh ấy nói anh ấy bấm nhầm nút bán hết cổ phiếu" nhại nguyên cụm.
_RETELL_NGRAM = 3


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


def _window_text(sentences: list, start: float, end: float) -> str:
    """Chuỗi transcript (đã chuẩn hoá, giữ THỨ TỰ) của các câu GIAO [start,end]
    — dùng dò n-gram LIÊN TIẾP (chặn thuật lại nguyên cụm)."""
    parts = []
    for a, b, t in sentences or []:
        try:
            if float(b) > start and float(a) < end and t:
                parts.append(_norm_for_copy(t))
        except (TypeError, ValueError):
            continue
    return " ".join(parts)


def _content_seq(text: str) -> list:
    """Dãy TỪ-NỘI-DUNG (bỏ stopword vi+en, bỏ từ 1 ký tự) theo ĐÚNG thứ tự
    xuất hiện — để dò n-gram liên tiếp trùng transcript."""
    return [w for w in _norm_for_copy(text).split()
            if len(w) > 1 and w not in _STOPWORDS]


def _is_retelling(text: str, window_text: str, n: int = _RETELL_NGRAM) -> bool:
    """narrate text có >= `n` TỪ-NỘI-DUNG LIÊN TIẾP trùng 1 cụm trong
    transcript window không -> THUẬT LẠI (nhại nguyên cụm lời nhân vật).

    Bắt kiểu (b) sai: transcript "tôi bấm nhầm nút bán hết cổ phiếu" ->
    narrate "anh ấy nói anh ấy bấm nhầm nút bán hết cổ phiếu" (cụm nội dung
    'bấm nhầm nút bán hết cổ phiếu' trùng liên tiếp) -> LOẠI. Câu (a) sáng
    tác "gã này vừa mất cả gia tài chỉ vì một cú click" KHÔNG có n-gram nội
    dung liên tiếp nào trùng -> QUA. Hàm thuần — unit test được.

    Dùng _STOPWORDS (bỏ từ nối) trước khi ghép n-gram nên "anh ấy nói" (toàn
    stopword/đại từ) không tính — chỉ cụm NỘI DUNG thật mới bị bắt."""
    if n < 1:
        return False
    seq = _content_seq(text)
    if len(seq) < n:
        return False
    win = _content_seq(window_text)
    if len(win) < n:
        return False
    win_grams = {" ".join(win[i:i + n]) for i in range(len(win) - n + 1)}
    for i in range(len(seq) - n + 1):
        if " ".join(seq[i:i + n]) in win_grams:
            return True
    return False


# ------------------------------------------------------------------
# STOPWORD vi+en (ngắn, tự nhúng) — dùng cho RELEVANCE CHECK: lời narrate
# phải có >=1 TỪ-NỘI-DUNG (không tính stopword) trùng với transcript của
# khung cảnh đó (hoặc khung kề) — 0 trùng = nghi "cắt 1 đằng nói 1 đằng".
# ------------------------------------------------------------------
_STOP_VI = set(
    "và hay hoặc nhưng mà thì là của ở trong trên dưới tại cho với từ được "
    "bị này kia đó những các một hai ba không có làm rồi đã đang sẽ cũng rất "
    "quá lắm luôn nhé nha ạ ơi à ừ anh chị em ông bà cô chú nó họ tôi ta bạn "
    "mình chúng gì sao khi nào đây đấy ai để vì nên còn lại ra vào lên xuống "
    "cái con người việc chuyện lúc bây giờ nữa thôi đi đến về như vậy thế "
    "nếu thật sự ấy hắn cả chỉ mới vừa ngay sau trước".split())
_STOP_EN = set(
    "the a an and or but so of to in on at for with from by as is are was "
    "were be been being it its this that these those he she they them we "
    "you i me his her their our my your not no nor do does did done will "
    "would shall should can could may might must have has had having just "
    "very really then than there here what when where which who whom whose "
    "why how all any some more most other another into over under after "
    "before again once out up down off only own same too also about because "
    "while if else even still yet going go get got one two".split())
_STOPWORDS = _STOP_VI | _STOP_EN


def _content_words(text: str) -> set:
    """Tập TỪ-NỘI-DUNG của text (đã chuẩn hoá, bỏ stopword vi+en, bỏ từ 1 ký
    tự) — dùng so RELEVANCE lời narrate với transcript khung cảnh."""
    return {w for w in _norm_for_copy(text).split()
            if len(w) > 1 and w not in _STOPWORDS}


# Độ dài PREFIX tối thiểu để coi 2 từ-nội-dung là LIÊN QUAN (cùng gốc/biến
# thể) trong relevance check: "bet"~"betting", "cược"~"đặt cược". Nới relevance
# để câu drama sáng tạo (dùng từ đồng nghĩa/biến thể thay vì trùng literal)
# KHÔNG bị loại oan, vẫn CHẶN câu 0 liên quan (bịa hẳn).
_RELEVANCE_PREFIX = 4


def _is_relevant(text: str, near: set) -> bool:
    """Lời narrate có LIÊN QUAN transcript khung (tập từ-nội-dung `near`) không.

    NỚI so với 'trùng literal': câu QUA nếu có >= 1 từ-nội-dung
      (a) trùng CHÍNH XÁC 1 từ trong near, HOẶC
      (b) chia sẻ PREFIX >= _RELEVANCE_PREFIX ký tự với 1 từ near (bắt biến
          thể/đồng nghĩa cùng gốc: 'bet'/'betting', 'cược'/'đặt cược').
    0 từ liên quan (kể cả nới prefix) = câu chung chung/bịa hẳn -> LOẠI.
    Hàm thuần — unit test được."""
    words = _content_words(text)
    if not words or not near:
        return False
    if words & near:                       # (a) trùng chính xác
        return True
    # (b) cùng prefix >= _RELEVANCE_PREFIX (chỉ khi CẢ 2 đủ dài — tránh khớp
    # oan 2 từ ngắn 4 ký tự khác nghĩa: yêu cầu prefix dài hơn nếu từ dài).
    npfx = {n[:_RELEVANCE_PREFIX] for n in near
            if len(n) >= _RELEVANCE_PREFIX}
    return any(len(w) >= _RELEVANCE_PREFIX and w[:_RELEVANCE_PREFIX] in npfx
               for w in words)


# ------------------------------------------------------------------
# HARD-FILTER khung cảnh RÁC: intro/outro/kêu subscribe/màn hình chữ.
#  - _CTA_PATTERNS: lời chào/cảm ơn/kêu gọi (EN + VI) — window mà >30% từ
#    thuộc câu dạng này -> loại (outro/intro kênh).
#  - _MIN_DENSITY: mật độ lời thoại tối thiểu (từ/giây) — đoạn màn hình chữ
#    /nhạc không lời rất thưa lời -> loại (trừ khi là window duy nhất).
# Regex chạy trên text đã _norm_for_copy (chữ thường, bỏ dấu câu).
# ------------------------------------------------------------------
_CTA_PATTERNS = [re.compile(p, re.UNICODE) for p in (
    # --- EN ---
    r"thanks?\s+(?:you\s+)?(?:so\s+much\s+)?(?:all\s+)?for\s+watching",
    r"\bsubscribe\b", r"\bunsubscribe\b",
    r"hit\s+the\s+(?:like|bell|subscribe)",
    r"smash\s+th(?:at|e)\s+like",
    r"like\s+and\s+(?:share|subscribe)", r"like\s+comment",
    r"see\s+you\s+(?:in\s+the\s+|guys\s+)?next",
    r"link\s+in\s+(?:the\s+)?(?:bio|description)",
    r"\bsponsored?\b", r"\bsponsors?\b",
    r"welcome\s+back\s+to\s+(?:the\s+|my\s+)?channel",
    r"don\s?t\s+forget\s+to\s+(?:like|subscribe)",
    # --- VI ---
    r"đăng\s+ký\s+kênh", r"(?:nhấn|bấm|ấn)\s+(?:nút\s+)?đăng\s+ký",
    r"(?:nhấn|bật|bấm)\s+(?:cái\s+)?chuông",
    r"like\s+(?:và\s+|va\s+)?share", r"like\s+share",
    r"cảm\s+ơn\s+(?:\S+\s+){0,4}?đã\s+(?:xem|theo\s+dõi|đồng\s+hành|ủng\s+hộ)",
    r"hẹn\s+gặp\s+lại", r"ủng\s+hộ\s+kênh",
    r"chào\s+mừng\s+(?:\S+\s+){0,4}?(?:quay\s+trở\s+lại|đến\s+với\s+kênh)",
    r"video\s+(?:lần\s+)?(?:sau|tiếp\s+theo|kế\s+tiếp)",
    r"tài\s+trợ", r"quảng\s+cáo",
)]
_MIN_DENSITY = 1.2     # từ/giây trung bình tối thiểu của 1 window
_CTA_MAX = 0.30        # >30% từ trong window là lời chào/kêu gọi -> loại


def _is_cta_text(text: str) -> bool:
    """Câu transcript có phải lời chào/cảm ơn/kêu subscribe/sponsor không."""
    t = _norm_for_copy(text)
    return bool(t) and any(p.search(t) for p in _CTA_PATTERNS)


def _win_density(sentences: list, start: float, end: float) -> float:
    """Mật độ lời thoại (từ/giây) của [start,end] theo transcript — câu giao
    1 phần chỉ tính số từ THEO TỈ LỆ phần giao (không phồng mật độ ảo)."""
    dur = max(0.001, float(end) - float(start))
    words = 0.0
    for a, b, t in sentences or []:
        try:
            a, b = float(a), float(b)
        except (TypeError, ValueError):
            continue
        ov = min(b, end) - max(a, start)
        if ov <= 0 or not t:
            continue
        n = len(_norm_for_copy(t).split())
        words += n * min(1.0, ov / max(0.001, b - a))
    return words / dur


def _cta_ratio(sentences: list, start: float, end: float) -> float:
    """Tỉ lệ (0..1) số TỪ trong [start,end] thuộc câu CHÀO/KÊU GỌI
    (thanks for watching / đăng ký kênh / sponsor...) — outro/intro kênh."""
    tot = cta = 0
    for a, b, t in sentences or []:
        try:
            if float(b) <= start or float(a) >= end or not t:
                continue
        except (TypeError, ValueError):
            continue
        n = len(_norm_for_copy(t).split())
        tot += n
        if _is_cta_text(t):
            cta += n
    return (cta / tot) if tot else 0.0


# ------------------------------------------------------------------
# PARSER BAO DUNG: LLM hay trả windows/parts sai DẠNG (nhưng đúng Ý) —
# chấp nhận mọi biến thể phổ biến thay vì vứt cả kịch bản rồi rơi fallback.
# ------------------------------------------------------------------
def _coerce_windows(raw) -> list:
    """Ép mọi dạng 'windows' LLM hay trả -> list [s, e] THÔ (validate_windows
    lọc số/độ dài sau — float() bên đó đã nhận cả chuỗi số "12.5"):
      - [[s, e], ...] chuẩn.
      - [{"start": s, "end": e}, ...] / {"s","e"} / {"from","to"} /
        {"begin","end"} (LLM quen schema part).
      - dict bọc thêm 1 lớp: {"windows": [...]} / {"list": [...]} hoặc
        dict index {"0": [s, e], ...}.
      - phần tử rác (số trần, chuỗi chữ, thiếu mốc) -> bỏ êm.
    Hàm thuần — unit test được."""
    if isinstance(raw, dict):
        for k in ("windows", "list", "items", "data", "segments"):
            v = raw.get(k)
            if isinstance(v, (list, tuple, dict)):
                return _coerce_windows(v)
        raw = list(raw.values())
    out = []
    for w in (raw or []):
        if isinstance(w, dict):
            s = next((w[k] for k in ("start", "s", "from", "begin")
                      if k in w), None)
            e = next((w[k] for k in ("end", "e", "to", "finish", "stop")
                      if k in w), None)
            if s is not None and e is not None:
                out.append([s, e])
        elif isinstance(w, (list, tuple)) and len(w) >= 2:
            out.append([w[0], w[1]])
    return out


def _coerce_parts(raw) -> list:
    """Ép mọi dạng 'parts' LLM hay trả -> list dict THÔ có start/end/mode/
    text (validate_parts lọc tiếp): nhận dict bọc ({"parts": [...]}) + key
    thay thế (s/e, from/to, begin). Phần tử không phải dict -> bỏ êm."""
    if isinstance(raw, dict):
        for k in ("parts", "list", "items", "data", "script"):
            v = raw.get(k)
            if isinstance(v, (list, tuple, dict)):
                return _coerce_parts(v)
        raw = list(raw.values())
    out = []
    for p in (raw or []):
        if not isinstance(p, dict):
            continue
        q = dict(p)
        if "start" not in q:
            for k in ("s", "from", "begin"):
                if k in q:
                    q["start"] = q[k]
                    break
        if "end" not in q:
            for k in ("e", "to", "finish", "stop"):
                if k in q:
                    q["end"] = q[k]
                    break
        out.append(q)
    return out


def _part_dur(p: dict) -> float:
    return float(p["end"]) - float(p["start"])


def _merge_orig_adjacent(parts: list[dict], gap: float = 0.3) -> list[dict]:
    """Gộp các part orig liền kề (đỡ vụn). Hàm thuần."""
    if not parts:
        return []
    merged: list[dict] = [dict(parts[0])]
    for p in parts[1:]:
        if (p["mode"] == "orig" and merged[-1]["mode"] == "orig"
                and abs(p["start"] - merged[-1]["end"]) < gap):
            merged[-1]["end"] = p["end"]
        else:
            merged.append(dict(p))
    return merged


def _fix_structure(parts: list[dict],
                   max_orig_breaks: int = _MAX_ORIG_BREAKS) -> list[dict]:
    """SỬA CẤU TRÚC chống PING-PONG trong 1 window/clip (hàm thuần —
    unit test được). parts đã SẠCH (sorted, phủ kín, orig kề đã gộp):

      (a) part narrate < _STRUCT_NARR_MIN kẹp giữa 2 part orig (không phải
          part ĐẦU = hook) -> GỘP cả 3 thành 1 orig (bỏ lời vụn — người
          xem nghe tiếng gốc liền mạch thay vì bị chen ngang 1-2 câu).
      (b) part orig < _STRUCT_ORIG_MIN -> gộp vào part narrate KỀ (ưu tiên
          narrate dài hơn) — cú bung tiếng gốc ngắn hơn 3s nghe như hụt.
      (c) quá max_orig_breaks lần BUNG tiếng gốc -> giữ các orig DÀI NHẤT,
          phần còn lại: có lời gốc hợp lệ (_otext — orig LLM trả kèm text
          đã qua anti-copy) -> chuyển narrate; không -> gộp vào narrate kề.

    Ranh giới part sau sửa vẫn PHỦ KÍN đúng khoảng cũ (chỉ gộp, không tạo
    hở/chồng lấn). Trả list part mới (đã gộp orig kề lần cuối)."""
    out = [dict(p) for p in parts]

    # ---- (b) orig quá ngắn -> gộp vào narrate kề (ưu tiên narrate dài hơn).
    # GIỮ TỐI THIỂU 1 part orig: nếu script CÓ orig, TUYỆT ĐỐI không nuốt hết
    # (lỗi thật: LLM trả ping-pong toàn orig <3s -> gộp sạch -> clip 100% AI
    # nói, tiếng gốc không còn window nào). Khi chỉ còn 1 orig, THA cú DÀI
    # NHẤT (dù < ngưỡng) — thà bung gốc hơi ngắn còn hơn mất hẳn tiếng gốc.
    n_orig0 = sum(1 for p in out if p["mode"] == "orig")
    changed = True
    while changed:
        changed = False
        origs = [i for i, p in enumerate(out) if p["mode"] == "orig"]
        if len(origs) <= 1:             # chỉ còn 1 orig -> giữ, không nuốt tiếp
            break
        # xử lý orig NGẮN NHẤT trước -> orig dài hơn có cơ hội sống sót
        shorts = sorted((i for i in origs
                         if _part_dur(out[i]) < _STRUCT_ORIG_MIN),
                        key=lambda i: _part_dur(out[i]))
        for i in shorts:
            prv = (out[i - 1] if i > 0
                   and out[i - 1]["mode"] == "narrate" else None)
            nxt = (out[i + 1] if i + 1 < len(out)
                   and out[i + 1]["mode"] == "narrate" else None)
            if prv is None and nxt is None:
                continue                # không có narrate kề -> đành giữ
            if nxt is None or (prv is not None
                               and _part_dur(prv) >= _part_dur(nxt)):
                prv["end"] = out[i]["end"]
            else:
                nxt["start"] = out[i]["start"]
            del out[i]
            changed = True
            break

    # ---- (a) narrate vụn kẹp giữa 2 orig (trừ hook đầu) -> gộp 3 thành 1 orig
    changed = True
    while changed:
        changed = False
        for i in range(1, len(out) - 1):
            p = out[i]
            if (p["mode"] == "narrate"
                    and _part_dur(p) < _STRUCT_NARR_MIN
                    and out[i - 1]["mode"] == "orig"
                    and out[i + 1]["mode"] == "orig"):
                out[i - 1]["end"] = out[i + 1]["end"]
                del out[i:i + 2]
                changed = True
                break

    # ---- (c) quá số lần bung tiếng gốc cho phép -> giữ các orig DÀI nhất
    origs = [i for i, p in enumerate(out) if p["mode"] == "orig"]
    if len(origs) > max_orig_breaks:
        keep = set(sorted(origs, key=lambda i: _part_dur(out[i]),
                          reverse=True)[:max_orig_breaks])
        for i in [j for j in origs if j not in keep][::-1]:
            p = out[i]
            otext = str(p.get("_otext") or "").strip()
            if otext:                   # orig có lời hợp lệ -> thành narrate
                out[i] = dict(p, mode="narrate", text=otext)
                continue
            prv = (out[i - 1] if i > 0
                   and out[i - 1]["mode"] == "narrate" else None)
            nxt = (out[i + 1] if i + 1 < len(out)
                   and out[i + 1]["mode"] == "narrate" else None)
            if prv is None and nxt is None:
                continue                # không có narrate kề -> đành giữ
            if nxt is None or (prv is not None
                               and _part_dur(prv) >= _part_dur(nxt)):
                prv["end"] = p["end"]
            else:
                nxt["start"] = p["start"]
            del out[i]
    return _merge_orig_adjacent(out)


def _limit_role_changes(parts: list[dict],
                        max_changes: int = _MAX_ROLE_CHANGES,
                        barriers=()) -> list[dict]:
    """(d) TỔNG số lần đổi vai narrate<->orig cả clip > max_changes -> gộp
    bớt từ các CẶP KỀ NGẮN NHẤT: part ngắn hơn bị NUỐT vào mode của part
    dài hơn (narrate bị nuốt thì bỏ lời; orig bị nuốt thì narrate kề giãn
    thời gian — TTS fit tự bù). KHÔNG gộp vắt qua `barriers` (mốc ghép
    window — cú nhảy cảnh là cắt cứng, part không được vắt qua 2 khung);
    KHÔNG nuốt part ĐẦU clip (hook); KHÔNG nuốt part ORIG CUỐI CÙNG (script
    có orig thì phải còn >=1 orig — tránh clip 100% AI nói). Hàm thuần —
    unit test được."""
    out = [dict(p) for p in parts]
    bset = {round(float(b), 2) for b in (barriers or ())}

    def n_changes() -> int:
        return sum(1 for i in range(len(out) - 1)
                   if out[i]["mode"] != out[i + 1]["mode"])

    while n_changes() > max_changes:
        n_orig = sum(1 for p in out if p["mode"] == "orig")
        best, bi = None, -1
        for i in range(len(out) - 1):
            if out[i]["mode"] == out[i + 1]["mode"]:
                continue
            if round(float(out[i]["end"]), 2) in bset:
                continue                # mối ghép window -> không gộp qua
            d0, d1 = _part_dur(out[i]), _part_dur(out[i + 1])
            victim = i if d0 <= d1 else i + 1
            if victim == 0:
                continue                # nạn nhân là hook -> tha
            if out[victim]["mode"] == "orig" and n_orig <= 1:
                continue                # orig CUỐI CÙNG -> tha (giữ tiếng gốc)
            key = min(d0, d1)
            if best is None or key < best:
                best, bi = key, i
        if bi < 0:
            break                       # hết cặp gộp được -> chịu
        if _part_dur(out[bi]) <= _part_dur(out[bi + 1]):
            out[bi + 1]["start"] = out[bi]["start"]   # part trước bị nuốt
            del out[bi]
        else:
            out[bi]["end"] = out[bi + 1]["end"]       # part sau bị nuốt
            del out[bi + 1]
    return out


def validate_parts(parts, clip_start: float, clip_end: float,
                   min_part: float = 1.5,
                   sentences: Optional[list] = None,
                   limit_changes: bool = True) -> list[dict]:
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
      - SỬA CẤU TRÚC chống ping-pong (_fix_structure): narrate vụn (<6s)
        kẹp giữa 2 orig (trừ hook đầu) -> gộp vào orig; orig <3s -> gộp
        vào narrate kề; quá _MAX_ORIG_BREAKS lần bung tiếng gốc -> giữ các
        cú DÀI nhất. limit_changes=True (mặc định, đường 1-span) -> giới
        hạn thêm TỔNG số lần đổi vai <= _MAX_ROLE_CHANGES (đường window:
        validate_parts_windows tự làm ở mức CẢ CLIP với mối ghép window).
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
        was_narrate = mode == "narrate"
        if mode != "narrate":          # mode lạ/thiếu -> orig
            mode = "orig"
        if mode == "narrate" and not text:
            mode = "orig"              # narrate mà không có lời -> giữ tiếng gốc
        if mode == "narrate" and _is_transcript_copy(text, transcript_norm):
            mode, text = "orig", ""    # AI chép transcript -> giữ tiếng gốc
        if (mode == "narrate" and sentences
                and _fuzzy_copy_ratio(
                    text, _window_words(sentences, s, e)) > _FUZZY_COPY_MAX):
            mode, text = "orig", ""    # trùng FUZZY quá nhiều từ -> tiếng gốc
        if (mode == "narrate" and sentences
                and _is_retelling(text, _window_text(sentences, s, e))):
            mode, text = "orig", ""    # nhại nguyên cụm (n-gram) -> tiếng gốc
        # LƯU LỜI GỐC HỢP LỆ của part orig LLM trả kèm text (_otext): nếu
        # _fix_structure phải hạ bớt cú bung tiếng gốc thừa, part có lời
        # sạch (qua ĐỦ 3 lưới anti-copy) được chuyển narrate thay vì gộp.
        # Narrate bị anti-copy hạ orig thì KHÔNG được phục hồi (text bẩn).
        otext = ""
        orig_text = str(p.get("text") or "").strip()
        if (mode == "orig" and not was_narrate and orig_text
                and not _is_transcript_copy(orig_text, transcript_norm)
                and not (sentences and _fuzzy_copy_ratio(
                    orig_text,
                    _window_words(sentences, s, e)) > _FUZZY_COPY_MAX)
                and not (sentences and _is_retelling(
                    orig_text, _window_text(sentences, s, e)))):
            otext = orig_text
        clean.append({"start": round(s, 2), "end": round(e, 2),
                      "mode": mode, "text": text if mode == "narrate" else "",
                      "_otext": otext})

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

    # Gộp part orig liền kề (đỡ vụn) rồi SỬA CẤU TRÚC chống ping-pong
    merged = _merge_orig_adjacent(out)
    merged = _fix_structure(merged)
    if limit_changes:
        merged = _limit_role_changes(merged)
    for p in merged:                    # _otext chỉ dùng nội bộ -> bỏ
        p.pop("_otext", None)
    return merged


def narrate_ratio(parts: list[dict]) -> float:
    """Tỉ lệ thời lượng narrate / tổng (0..1) — để log/kiểm tra."""
    total = sum(p["end"] - p["start"] for p in parts) or 1.0
    nar = sum(p["end"] - p["start"] for p in parts if p["mode"] == "narrate")
    return nar / total


# Nếu anti-copy SIẾT làm rụng quá nhiều narrate (còn < tỉ lệ này số part
# narrate mà LLM ĐỊNH viết) -> lời kể đang thuật lại lời nhân vật -> RETRY 1
# lần với chỉ trích cụ thể (thà retry còn hơn xuất clip gần như toàn orig).
_ANTICOPY_RETRY_KEEP = 0.5
# Chỉ trích gửi kèm khi retry vì thuật lại (dùng cho cả 2 đường prompt).
_RETELL_RETRY_NOTE = (
    "LẦN TRƯỚC lời kể của bạn ĐANG THUẬT LẠI / diễn giải lại lời nhân vật "
    "(lặp cụm từ trong transcript) nên bị hệ thống LOẠI gần hết. Hãy viết "
    "LẠI: đứng NGOÀI video mà BÌNH LUẬN / cảm xúc / dự đoán / đặt câu hỏi về "
    "chuyện — TUYỆT ĐỐI KHÔNG nhắc lại nội dung câu nhân vật đang/ sắp nói "
    "(để họ TỰ nói ở đoạn orig), KHÔNG dùng lại cụm từ nào của transcript.")


def _narrate_count(raw_parts) -> int:
    """Số part LLM ĐỊNH viết narrate (trước khi validate/anti-copy hạ orig) —
    để đo anti-copy có rụng quá nhiều không. raw = list dict thô."""
    n = 0
    for p in _coerce_parts(raw_parts):
        if str(p.get("mode") or "").strip().lower() == "narrate" \
                and str(p.get("text") or "").strip():
            n += 1
    return n


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
                          max_total: float, ratio: float = 55,
                          win_min: int = 3, win_max: int = 6,
                          emotion: bool = False) -> str:
    """Prompt ĐẠO DIỄN: từ TOÀN BỘ transcript (đã rút gọn nếu dài), chọn
    win_min-win_max khung cảnh rời nhau + viết kịch bản parts có CẦU NỐI
    giữa các khung (min/max user chỉnh trong ⚙ Cài đặt Reup, mặc định 3-6)."""
    ln = lang_name.upper()
    try:
        pct = int(round(max(30.0, min(80.0, float(ratio)))))
    except (TypeError, ValueError):
        pct = 55
    try:
        w_lo = max(2, int(win_min))
    except (TypeError, ValueError):
        w_lo = 3
    try:
        w_hi = max(w_lo, int(win_max))
    except (TypeError, ValueError):
        w_hi = max(w_lo, 6)
    return (
        # KHỐI ÉP NGÔN NGỮ đặt TRƯỚC MỌI LUẬT (lỗi thật: video EN nhưng AI
        # viết kịch bản + tiêu đề tiếng Việt vì prompt toàn tiếng Việt).
        _lang_rule(ln) + "\n"
        f"Đây là TOÀN BỘ transcript của một video dài {duration:.0f} giây, "
        f"nói bằng {ln} (mỗi dòng: GIÂY_BẮT_ĐẦU GIÂY_KẾT_THÚC | lời nói):\n"
        f"{listing}\n\n"
        "VAI CỦA BẠN: ĐẠO DIỄN kiêm NGƯỜI KỂ CHUYỆN của kênh recap triệu "
        "view. Nhiệm vụ: CẮT GHÉP video thành 1 clip recap gồm NHIỀU KHUNG "
        "CẢNH rời nhau kể TRỌN câu chuyện (như recap phim), rồi viết lời kể "
        "của bạn phủ lên.\n\n"
        "BƯỚC 1 — CHỌN KHUNG CẢNH (windows):\n"
        f"- Chọn {w_lo}-{w_hi} khung cảnh RỜI NHAU bám mạch chuyện: mở đầu "
        "-> diễn biến -> twist/cao trào -> kết. ĐÚNG thứ tự thời gian, KHÔNG "
        "chồng lấn, KHÔNG đảo đoạn.\n"
        f"- Mỗi khung dài 8-40 giây; TỔNG các khung trong khoảng "
        f"{min_total:.0f}-{max_total:.0f} giây.\n"
        "- Mép khung phải trùng mép câu transcript (không cắt ngang câu "
        "nói).\n"
        "- Chỉ lấy khoảnh khắc ĐẮT (kịch tính, twist, cảm xúc mạnh, câu "
        "chốt) — mạnh dạn BỎ hẳn đoạn nhàm/lặp ở giữa; người xem sẽ được "
        "lời kể của bạn nối mạch.\n"
        "- NÉ RÁC ĐẦU/CUỐI: CẤM lấy ~15 giây ĐẦU video (intro kênh/màn "
        "hình chữ/nhạc hiệu) và ~20 giây CUỐI (outro/credits/kêu gọi đăng "
        "ký) — trừ khi transcript cho thấy ở đó có nội dung chuyện THẬT SỰ "
        "đắt.\n"
        "- CẤM chọn khung mà lời thoại chủ yếu là chào/cảm ơn/kêu gọi/"
        "quảng cáo — các kiểu: \"thanks for watching\", \"subscribe\", "
        "\"like and share\", \"see you in the next video\", \"link in "
        "description\", \"đăng ký kênh\", \"nhấn chuông\", \"like và "
        "share\", \"cảm ơn các bạn đã xem\", \"hẹn gặp lại\", \"ủng hộ "
        "kênh\", sponsor/tài trợ... Khung như vậy (hoặc khung gần như "
        "KHÔNG có lời thoại — nhạc nền, chữ trên màn hình) sẽ bị hệ thống "
        "LOẠI BỎ.\n\n"
        "BƯỚC 2 — VIẾT KỊCH BẢN parts phủ lên các khung đó (orig = giữ "
        "tiếng gốc / narrate = bạn kể, video tắt tiếng):\n"
        + _structure_rules(per_window=True) +
        "- KHUÔN trên áp cho CẢ CLIP xuyên các khung: HOOK ở đầu khung 1; "
        "các cú BUNG GỐC rơi vào đúng khoảnh khắc đắt của từng khung.\n"
        "- Mốc part nằm TRONG khung, KHÔNG vắt qua 2 khung; các part PHỦ "
        "KÍN từng khung; start/end trùng mép câu.\n"
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
        "- BÁM CẢNH (bắt buộc): MỖI part narrate phải nhắc ÍT NHẤT 1 CHI "
        "TIẾT CỤ THỂ có trong transcript của ĐÚNG khung đó (tên riêng / "
        "hành động / con số / đồ vật) — CẤM câu chung chung lắp vào cảnh "
        "nào cũng được; lời lạc cảnh sẽ bị hệ thống LOẠI.\n"
        "  VÍ DỤ ĐÚNG (transcript khung có \"đặt cược 500 đô\"): \"500 "
        "đô... cho một ván bài gã chưa từng thắng.\" — dính chi tiết "
        "'500 đô', 'ván bài' của đúng cảnh đó.\n"
        "  VÍ DỤ SAI (bị loại): \"Thật không thể tin được!\", \"Quá đỉnh "
        "luôn các bạn ạ.\" — không dính chi tiết nào của cảnh, lắp đâu "
        "cũng được.\n"
        f"- Part narrate CUỐI: câu chốt đắt + KÊU GỌI tương tác (hỏi ý "
        f"kiến, kêu theo dõi) viết bằng {ln}.\n"
        f"- Tổng thời lượng narrate ~{pct}% clip (chấp nhận "
        f"{max(20, pct - 10)}-{min(90, pct + 10)}%) — người kể nói CHỦ "
        "ĐẠO, tiếng gốc chỉ bung đúng chỗ đắt.\n"
        "- Đoạn orig = ĐỒNG ĐẮT: chọn đúng câu nói/tiếng động/cảm xúc MẠNH "
        "NHẤT trong khung làm twist/đỉnh điểm.\n"
        "- CẤM SPOILER: không nhắc trước nội dung khung CHƯA chiếu tới — "
        "chỉ được GỢI tò mò.\n\n"
        + _narrator_rules(ln, style, emotion=emotion) +
        f"\n- {_RATE_HINT} HÃY ĐẾM CHỮ: lời narrate đọc VỪA KHÍT độ dài "
        "part (part 10 giây tiếng Anh ~20 từ, part 20 giây ~41-46 từ). "
        "ĐỪNG viết dài — sẽ bị cắt.\n"
        "- TRẦN CỨNG SỐ CHỮ (hệ số an toàn 0.9): TUYỆT ĐỐI KHÔNG viết quá "
        "(số_giây_part × 2.3 × 0.9) từ tiếng Anh cho part đó — hook 6 giây "
        "tối đa 12 từ, part 10 giây tối đa 20 từ, part 20 giây tối đa 41 "
        "từ (tiếng Việt: số_giây × 3.5 × 0.9 ≈ 3 âm tiết/giây). ĐẾM LẠI "
        "từng part trước khi trả — lời vượt trần SẼ BỊ CẮT CỤT giữa câu "
        "khi đọc.\n"
        "- SÀN CỨNG SỐ CHỮ: lời narrate phải LẤP ĐẦY ~85-95% thời lượng "
        "part — TỐI THIỂU (số_giây_part × 2.3 × 0.75) từ tiếng Anh (part "
        "20 giây >= 34 từ; tiếng Việt: số_giây × 3.5 × 0.75 âm tiết). "
        "KHÔNG ĐỦ Ý để lấp thì VIẾT PART NGẮN LẠI (rút end xuống), ĐỪNG "
        "để giọng đọc xong mà hình còn trống dài không ai nói gì.\n"
        "- part orig KHÔNG cần text (chuỗi rỗng).\n"
        f"- title: tiêu đề giật tít cho clip, viết bằng {ln}.\n"
        "- context_summary: 1 câu TÓM TẮT BỐI CẢNH (bước 1) — CHỈ để bạn "
        "hiểu, KHÔNG phải lời đọc.\n"
        + _lang_remind(ln) +
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"context_summary": "...", "title": "...", '
        '"windows": [[giây_bắt_đầu, giây_kết_thúc], ...], '
        '"parts": [{"start": giây, "end": giây, "mode": "orig"|"narrate", '
        '"text": "lời thuyết minh nếu narrate"}]}\n'
        '("windows" BẮT BUỘC là MẢNG CÁC CẶP SỐ [[s, e], ...] — ÍT NHẤT 2 '
        "khung — KHÔNG dùng object {\"start\": ...} cho windows.)")


def validate_windows(windows, duration: float,
                     min_total: float = 0.0, max_total: float = 0.0,
                     min_w: float = _WIN_MIN, max_w: float = _WIN_MAX,
                     max_n: int = _WIN_MAX_N,
                     sentences: Optional[list] = None) -> list:
    """Chuẩn hoá danh sách khung LLM trả -> [[s,e],...] SẠCH hoặc [] (hỏng).

    - CHẤP NHẬN mọi dạng LLM hay trả (_coerce_windows): [[s,e]], list dict
      start/end (hoặc s/e, from/to), dict bọc {"windows": [...]}, chuỗi số.
    - phần tử không ép được cặp số / dài < min_w -> BỎ; dài > max_w -> cắt đuôi.
    - clamp vào [0, duration]; sort; CHỒNG LẤN -> đẩy start khung sau về end
      khung trước (teo dưới min_w thì bỏ khung đó).
    - sentences != None: HARD-FILTER khung RÁC —
        + khung mà >30% từ là lời chào/kêu subscribe/sponsor (EN+VI) -> loại
          (outro/intro kênh);
        + khung thưa lời (< ~1.2 từ/giây — màn hình chữ/nhạc không lời) ->
          loại, TRỪ khi là khung duy nhất.
    - quá max_n khung -> giữ max_n khung đầu (đúng mạch thời gian).
    - max_total > 0: tổng vượt trần -> cắt bớt khung cuối (khúc cuối teo
      dưới min_w thì bỏ hẳn).
    - CÒN 1 KHUNG: nếu DÀI ĐỦ (>= max(20s, 60% min_total)) vẫn CHẤP NHẬN —
      coi như 1-span hợp lệ (2 khung LLM trả sát nhau bị khử chồng lấn gộp
      còn 1 không đáng vứt cả kịch bản); ngắn quá -> [].
    - HỎNG -> []: không còn khung, hoặc min_total > 0 mà tổng < 60% min_total.
    Hàm thuần — unit test được."""
    dur = float(duration or 0)
    out = []
    for w in _coerce_windows(windows):
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
    if sentences:
        # HARD-FILTER khung rác theo transcript: outro/kêu sub + thưa lời
        n_before = len(fixed)
        kept = []
        for s, e in fixed:
            if _cta_ratio(sentences, s, e) > _CTA_MAX:
                continue               # toàn lời chào/kêu gọi -> outro/intro
            if (_win_density(sentences, s, e) < _MIN_DENSITY
                    and n_before > 1):
                continue               # thưa lời (chữ màn hình/nhạc) -> loại
            kept.append([s, e])
        fixed = kept
    if len(fixed) > max_n:
        # QUÁ max_n khung (user đặt Max cảnh) -> GIỮ các khung DÀI hơn
        # (nhiều nội dung/điểm cao hơn), vẫn xếp theo thứ tự thời gian.
        keep = sorted(sorted(range(len(fixed)),
                             key=lambda i: fixed[i][1] - fixed[i][0],
                             reverse=True)[:max_n])
        fixed = [fixed[i] for i in keep]
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
    if not fixed:
        return []
    if len(fixed) == 1:
        # 1 khung dài đủ = 1-span hợp lệ (đừng vứt oan cả kịch bản)
        need = max(20.0, 0.6 * float(min_total or 0.0))
        return fixed if fixed[0][1] - fixed[0][0] >= need else []
    if min_total and min_total > 0:
        if sum(e - s for s, e in fixed) < 0.6 * min_total:
            return []
    return fixed


def validate_parts_windows(parts, windows: list, sentences=None,
                           min_part: float = 1.5) -> list[dict]:
    """Validate kịch bản MULTI-WINDOW: chia parts về từng khung (theo TÂM
    part), rồi validate_parts TỪNG khung (clamp vào khung, lấp hở bằng orig,
    anti-copy...) -> part KHÔNG BAO GIỜ vắt qua 2 khung (mốc luôn map được
    qua _map_to_output của dubbing). Trả list part phủ kín MỌI khung.

    RELEVANCE CHECK (ngược chiều anti-copy, cần sentences): lời narrate phải
    có >= 1 TỪ-NỘI-DUNG (bỏ stopword vi+en) trùng transcript của khung đó
    HOẶC khung KỀ (cầu nối được nhắc cảnh trước/sau) — 0 trùng = câu chung
    chung lắp đâu cũng được ("cắt 1 đằng nói 1 đằng") -> hạ orig. THA part
    CẦU NỐI tại điểm ghép (part đầu của khung thứ 2 trở đi). Khoảng hợp lệ
    của narrate: >=1 từ trùng (liên quan) nhưng <=60% (không chép lại —
    _fuzzy_copy_ratio trong validate_parts vẫn chặn).

    SỬA CẤU TRÚC: validate_parts từng khung tự sửa ping-pong (narrate vụn
    kẹp giữa 2 orig -> gộp; orig <3s -> gộp; > _MAX_ORIG_BREAKS cú bung
    mỗi khung -> giữ cú dài nhất); sau khi ghép đủ các khung, giới hạn
    TỔNG số lần đổi vai cả clip <= _MAX_ROLE_CHANGES (_limit_role_changes,
    KHÔNG gộp part vắt qua mối ghép window)."""
    parts = _coerce_parts(parts)
    wlist = list(windows or [])
    # tập từ-nội-dung từng khung (cho relevance; tính 1 lần)
    wwords: list[set] = []
    if sentences:
        for ws, we in wlist:
            wwords.append({w for w in _window_words(sentences, ws, we)
                           if len(w) > 1 and w not in _STOPWORDS})
    out: list[dict] = []
    for wi, (ws, we) in enumerate(wlist):
        sub = []
        for p in parts:
            try:
                mid = (float(p.get("start")) + float(p.get("end"))) / 2
            except (TypeError, ValueError):
                continue
            if ws - 0.01 <= mid <= we + 0.01:
                sub.append(p)
        sub.sort(key=lambda p: float(p.get("start")))
        if sentences and wwords:
            near = set(wwords[wi])
            if wi > 0:
                near |= wwords[wi - 1]
            if wi + 1 < len(wwords):
                near |= wwords[wi + 1]
            checked = []
            for j, p in enumerate(sub):
                mode = str(p.get("mode") or "").strip().lower()
                text = str(p.get("text") or "")
                if (mode == "narrate" and text.strip()
                        and not _is_relevant(text, near)
                        and not (wi > 0 and j == 0)):
                    # 0 từ-nội-dung LIÊN QUAN transcript khung (và khung kề;
                    # NỚI: chấp nhận biến thể/đồng nghĩa cùng gốc qua prefix)
                    # -> nghi LẠC ĐỀ/bịa -> hạ orig. Tha CẦU NỐI (part đầu
                    # khung thứ 2 trở đi — lời bắc cầu được phép thoát cảnh).
                    p = dict(p, mode="orig", text="")
                checked.append(p)
            sub = checked
        out.extend(validate_parts(sub, ws, we, min_part=min_part,
                                  sentences=sentences, limit_changes=False))
    # (d) TỔNG đổi vai cả clip: gộp bớt từ cặp ngắn nhất; mốc cuối mỗi
    # window (trừ window chót) là mối ghép — cấm gộp part vắt qua.
    return _limit_role_changes(out, barriers=[we for _ws, we in wlist[:-1]])


def _director_from_data(data, sentences: list, duration: float,
                        min_total: float, max_total: float,
                        win_max: int = _WIN_MAX_N):
    """Ép + validate output đạo diễn -> ({'title','windows','parts'} | None,
    thông_điệp_lỗi_cụ_thể) — thông điệp dùng cho lượt RETRY SỬA LỖI.
    Chấp nhận data là chuỗi JSON / list bọc / dict; windows-parts mọi dạng
    phổ biến (_coerce_windows/_coerce_parts). win_max = TRẦN số khung (user
    đặt trong ⚙ Cài đặt Reup — thừa thì validate_windows giữ khung dài hơn;
    DƯỚI Min user thì vẫn chấp nhận nếu >=2 khung/1 khung dài — Min chỉ là
    mong muốn, không giết kịch bản). Hàm thuần — unit test được."""
    if isinstance(data, str):           # model trả JSON-trong-chuỗi
        try:
            data = json.loads(data)
        except ValueError:
            return None, ("kết quả không phải JSON object — trả JSON THUẦN "
                          "đúng schema, không bọc trong chuỗi/chữ")
    if isinstance(data, list):          # model bọc object trong mảng
        data = next((x for x in data if isinstance(x, dict)), None)
    if not isinstance(data, dict):
        return None, ('kết quả không phải JSON object dạng {"title", '
                      '"windows", "parts"}')
    windows = validate_windows(data.get("windows"), duration,
                               min_total=min_total, max_total=max_total,
                               max_n=max(2, int(win_max or _WIN_MAX_N)),
                               sentences=sentences)
    if not windows:
        return None, (
            '"windows" hỏng: phải là MẢNG CÁC CẶP SỐ [[giây_bắt_đầu, '
            "giây_kết_thúc], ...] (KHÔNG dùng object), ít nhất 2 khung rời "
            "nhau đúng thứ tự thời gian, mỗi khung 8-40 giây, tổng "
            f"{min_total:.0f}-{max_total:.0f} giây; khung phải nằm ở đoạn "
            "CÓ LỜI THOẠI DÀY và KHÔNG phải intro/outro/kêu subscribe")
    parts = validate_parts_windows(data.get("parts"), windows,
                                   sentences=sentences)
    if not any(p["mode"] == "narrate" for p in parts):
        return None, (
            '"parts" hỏng: cần ít nhất 1 part {"start", "end", "mode": '
            '"narrate", "text"} nằm TRONG các windows đã chọn, lời kể phải '
            "nhắc chi tiết cụ thể từ transcript của đúng khung đó (không "
            "chép nguyên văn, không câu chung chung lắp đâu cũng được)")
    return {"title": str(data.get("title") or "").strip(),
            "windows": windows, "parts": parts}, ""


def _enforce_script_lang(result: Optional[dict], lang_name: str,
                         retry_fn) -> Optional[dict]:
    """HẬU KIỂM NGÔN NGỮ kịch bản đã validate (dùng chung 2 đường).

    Video KHÔNG phải tiếng Việt mà title/lời narrate dính tiếng Việt ->
    RETRY 1 lần qua retry_fn() (gọi LLM kèm chỉ trích _WRONG_LANG_NOTE,
    trả script ĐÃ validate hoặc None). Retry vẫn sai -> LOẠI part sai
    (hạ orig, giữ tiếng gốc) + xóa title sai (caller dùng title fallback)
    + gắn result["lang_warn"] để caller log cảnh báo progress.
    Video TIẾNG VIỆT mà lời toàn không dấu -> chỉ cảnh báo lang_warn."""
    if not result:
        return result
    bad, tbad = script_lang_issues(result.get("title", ""),
                                   result.get("parts") or [], lang_name)
    if not bad and not tbad:
        w = _vi_ascii_warn(result.get("parts"), lang_name)
        if w:
            result["lang_warn"] = w
        return result
    r2 = retry_fn()
    if r2:
        b2, tb2 = script_lang_issues(r2.get("title", ""),
                                     r2.get("parts") or [], lang_name)
        if not b2 and not tb2 and any(
                p["mode"] == "narrate" for p in r2.get("parts") or []):
            return r2                   # bản retry đúng ngôn ngữ -> dùng
    # vẫn sai -> loại part sai (giữ tiếng gốc) + bỏ tiêu đề sai ngôn ngữ
    for i in bad:
        result["parts"][i] = dict(result["parts"][i], mode="orig", text="")
    if tbad:
        result["title"] = ""
    result["lang_warn"] = (
        f"AI viết sai ngôn ngữ (video nói {lang_name}) — đã giữ tiếng gốc "
        f"cho {len(bad)} đoạn"
        + (", dùng tiêu đề dự phòng" if tbad else ""))
    return result


def write_director_script(sentences: list, lang_name: str, style: str,
                          duration: float, min_total: float,
                          max_total: float, ratio: float = 55,
                          listing: str = "", win_min: int = 3,
                          win_max: int = 6,
                          emotion: bool = False) -> Optional[dict]:
    """Gọi LLM đạo diễn trên TOÀN BỘ transcript -> {"title", "windows",
    "parts"} ĐÃ validate; None nếu windows/parts hỏng cả sau khi RETRY
    (caller fallback đường 1-span cũ).

    RETRY SỬA LỖI: lần 1 trả JSON hỏng/không qua validate -> gọi LẠI đúng
    1 lần, đính kèm THÔNG ĐIỆP LỖI CỤ THỂ (windows phải là [[s,e],...]...)
    để model tự sửa — đỡ rơi fallback oan chỉ vì sai dạng JSON.
    HẬU KIỂM NGÔN NGỮ: kịch bản/tiêu đề sai ngôn ngữ video -> retry 1 lần
    kèm chỉ trích; vẫn sai -> loại part sai + "lang_warn" (caller log).

    sentences = [(start, end, text)] TOÀN transcript (anti-copy + relevance
    + lọc mật độ lời). listing = transcript RÚT GỌN cho prompt (caller gộp
    câu nếu video dài); rỗng -> tự build từ sentences.
    win_min/win_max = khoảng SỐ KHUNG CẢNH mong muốn (⚙ Cài đặt Reup).
    Ném llm.LLMError nếu gọi LLM thất bại vì mạng/key (caller quyết
    fallback); lỗi PARSE JSON thì tự retry chứ không ném."""
    if not listing:
        listing = "\n".join(f"{a:.1f} {b:.1f} | {t}"
                            for a, b, t in sentences)[:11000]
    prompt = build_director_prompt(listing, lang_name, style, duration,
                                   min_total, max_total, ratio=ratio,
                                   win_min=win_min, win_max=win_max,
                                   emotion=emotion)

    def _lang_retry():
        """Gọi lại LLM kèm chỉ trích SAI NGÔN NGỮ -> script validate/None."""
        try:
            d3 = llm.complete_json(
                prompt + "\n\n" + _WRONG_LANG_NOTE.format(
                    ln=lang_name.upper()), system=_SYSTEM)
            r3, _e3 = _director_from_data(d3, sentences, duration,
                                          min_total, max_total, win_max)
        except llm.LLMError:
            r3 = None
        return r3

    result, err = None, ""
    try:
        data = llm.complete_json(prompt, system=_SYSTEM)
        result, err = _director_from_data(data, sentences, duration,
                                          min_total, max_total, win_max)
    except llm.LLMError as e:
        if "không phải JSON" not in str(e):
            raise                       # lỗi mạng/key/quota -> caller quyết
        err = ("kết quả không phải JSON hợp lệ — trả DUY NHẤT 1 JSON object "
               "đúng schema, không thêm chữ/markdown")
    # ---- ANTI-COPY SIẾT rụng quá nửa narrate (thuật lại) -> RETRY chỉ trích ----
    # (chỉ khi ĐÃ có result hợp lệ nhưng phần narrate bị hạ orig gần hết)
    if result and isinstance(data, dict):
        want = _narrate_count(data.get("parts"))
        kept = sum(1 for p in result["parts"] if p["mode"] == "narrate")
        if want >= 2 and kept < max(1, _ANTICOPY_RETRY_KEEP * want):
            try:
                d2 = llm.complete_json(prompt + "\n\n" + _RETELL_RETRY_NOTE,
                                       system=_SYSTEM)
                r2, _e2 = _director_from_data(d2, sentences, duration,
                                              min_total, max_total, win_max)
            except llm.LLMError:
                r2 = None
            if r2 and sum(1 for p in r2["parts"]
                          if p["mode"] == "narrate") > kept:
                return _enforce_script_lang(r2, lang_name, _lang_retry)
        return _enforce_script_lang(result, lang_name, _lang_retry)
    # ---- RETRY SỬA LỖI (1 lần): nói rõ lỗi để model tự sửa ----
    retry_prompt = (
        prompt + "\n\nLẦN TRƯỚC bạn đã trả kết quả KHÔNG DÙNG ĐƯỢC — lỗi: "
        + err + ".\nHãy SỬA ĐÚNG lỗi đó và trả lại DUY NHẤT 1 JSON object "
        "đúng schema yêu cầu ở trên, không thêm chữ nào khác.")
    try:
        data = llm.complete_json(retry_prompt, system=_SYSTEM)
    except llm.LLMError:
        return None                     # retry vẫn hỏng -> caller fallback
    result, _err = _director_from_data(data, sentences, duration,
                                       min_total, max_total, win_max)
    return _enforce_script_lang(result, lang_name, _lang_retry)


def write_script(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float,
                 title: str = "",
                 frames: Optional[list] = None,
                 ratio: float = 55,
                 emotion: bool = False) -> Optional[dict]:
    """Gọi LLM viết kịch bản 1 clip -> {"title","parts"} ĐÃ VALIDATE.

    sentences = [(start, end, text)] câu transcript trong phạm vi clip.
    frames = [(giây, đường_dẫn_ảnh)] khung hình gửi kèm (chỉ khi caller đã
    kiểm llm.vision_available()) — AI NHÌN cảnh để hiểu bối cảnh rồi kể; lỗi
    vision -> tự lùi về prompt chữ thuần (không vỡ luồng).
    ratio = % thời lượng AI kể user chọn (30-80, mặc định 55).
    Ném llm.LLMError nếu gọi LLM thất bại (caller quyết fail/skip).
    Trả None nếu LLM trả JSON không dùng được (không có part narrate nào).
    """
    base_prompt = build_prompt(sentences, lang_name, style, clip_start,
                               clip_end, title, frames=frames, ratio=ratio,
                               emotion=emotion)

    def _call(prompt: str):
        data = None
        if frames:
            try:
                data = llm.complete_vision_json(
                    prompt, [p for _t, p in frames], system=_SYSTEM)
            except Exception:  # noqa: BLE001 — vision lỗi -> lùi prompt chữ
                data = None
        if data is None:
            p2 = prompt
            if frames:                  # vision fail -> prompt KHÔNG nhắc ảnh
                p2 = build_prompt(sentences, lang_name, style, clip_start,
                                  clip_end, title, ratio=ratio,
                                  emotion=emotion)
                if prompt != base_prompt:   # giữ chỉ trích retry ở cuối
                    p2 += prompt[len(base_prompt):]
            data = llm.complete_json(p2, system=_SYSTEM)
        if isinstance(data, list):      # model trả thẳng mảng parts
            data = {"parts": data}
        return data if isinstance(data, dict) else None

    data = _call(base_prompt)
    if data is None:
        return None
    raw = data.get("parts")
    if not isinstance(raw, list):
        return None
    parts = validate_parts(raw, clip_start, clip_end, sentences=sentences)
    kept = sum(1 for p in parts if p["mode"] == "narrate")
    want = _narrate_count(raw)
    # ANTI-COPY SIẾT rụng quá nửa narrate (thuật lại) -> RETRY 1 lần với chỉ
    # trích cụ thể. Vẫn tệ -> GIỮ kết quả tốt hơn (thà orig còn hơn đọc lại).
    if want >= 2 and kept < max(1, _ANTICOPY_RETRY_KEEP * want):
        data2 = _call(base_prompt + "\n\n" + _RETELL_RETRY_NOTE)
        if isinstance(data2, dict) and isinstance(data2.get("parts"), list):
            parts2 = validate_parts(data2["parts"], clip_start, clip_end,
                                    sentences=sentences)
            if sum(1 for p in parts2 if p["mode"] == "narrate") > kept:
                parts, data = parts2, data2
    if not any(p["mode"] == "narrate" for p in parts):
        return None                     # không có thuyết minh -> vô nghĩa

    # ---- HẬU KIỂM NGÔN NGỮ (đường 1-span cũng phải đúng ngôn ngữ video):
    # sai -> retry 1 lần kèm chỉ trích; vẫn sai -> loại part sai + title
    # fallback heuristic cũ (title tham số) + lang_warn cho caller log.
    def _lang_retry():
        try:
            d3 = _call(base_prompt + "\n\n"
                       + _WRONG_LANG_NOTE.format(ln=lang_name.upper()))
        except llm.LLMError:
            return None
        if not (isinstance(d3, dict) and isinstance(d3.get("parts"), list)):
            return None
        p3 = validate_parts(d3["parts"], clip_start, clip_end,
                            sentences=sentences)
        return {"title": str(d3.get("title") or "").strip(), "parts": p3}

    out = _enforce_script_lang(
        {"title": str(data.get("title") or "").strip(), "parts": parts},
        lang_name, _lang_retry)
    if not out.get("title") and title:
        out["title"] = title            # title sai ngôn ngữ -> heuristic cũ
    if not any(p["mode"] == "narrate" for p in out["parts"]):
        return None                     # part sai bị loại sạch -> bỏ kịch bản
    return out
