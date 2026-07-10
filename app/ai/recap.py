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
part orig, narrate rỗng/COPY transcript (kể cả KỂ LẠI: trùng cao TẬP từ với
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

# ---- KHUÔN LOW-RATIO (user kéo "Tỉ lệ AI kể" <= 40%): AI nói ÍT, NHANH
# GỌN, nhường video gốc — hook ngắn + 1-2 cầu nối + chốt, còn lại tiếng
# gốc chạy dài. Ngưỡng + độ dài dùng chung prompt (2 đường) 1 chỗ. ----
_LOW_RATIO_MAX = 40.0      # ratio <= 40 -> khuôn low-ratio
_LR_HOOK_MIN, _LR_HOOK_MAX = 3, 6        # hook mở đầu (giây)
_LR_BRIDGE_MIN, _LR_BRIDGE_MAX = 4, 8    # cầu nối kể ngắn (giây)
_LR_OUTRO_MIN, _LR_OUTRO_MAX = 3, 5      # chốt kể cuối (giây)


def _is_low_ratio(ratio) -> bool:
    """Tỉ lệ AI kể có thuộc chế độ LOW-RATIO (<= 40%) không. Hàm thuần."""
    try:
        return float(ratio) <= _LOW_RATIO_MAX
    except (TypeError, ValueError):
        return False


def _structure_rules(per_window: bool = False, ratio: float = 55.0) -> str:
    """KHUÔN CẤU TRÚC kênh recap thật — dùng CHUNG cho prompt 1-span
    (build_prompt) và prompt đạo diễn (build_director_prompt).
    per_window=True -> thêm trần số lần bung TỪNG KHUNG CẢNH (đạo diễn).

    2 KHUÔN THEO `ratio` (Tỉ lệ AI kể user chọn):
      - ratio <= 40 (LOW-RATIO): AI nói ÍT + NHANH GỌN — HOOK ngắn 3-6s ->
        VIDEO GỐC CHẠY DÀI -> 1 cầu nối kể NGẮN 4-8s -> GỐC DÀI -> chốt kể
        3-5s. Video gốc là CHỦ ĐẠO (sửa lỗi user 'AI nói quá nhiều ~80%').
      - ratio > 40: khuôn cũ — người kể nói chủ đạo khối dài, tiếng gốc chỉ
        bung ở khoảnh khắc đắt, cấm ping-pong."""
    if _is_low_ratio(ratio):
        return (
            "KHUÔN CẤU TRÚC CLIP (bắt buộc — chế độ AI NÓI ÍT, VIDEO GỐC "
            "LÀ CHÍNH — dựng kịch bản theo ĐÚNG từng bước):\n"
            f"  B1. HOOK — narrate NGẮN {_LR_HOOK_MIN}-{_LR_HOOK_MAX} giây: "
            "1 câu mở gây SỐC/TÒ MÒ tức thì, NHANH GỌN rồi nhường ngay.\n"
            "  B2. VIDEO GỐC CHẠY DÀI — orig 15-40 giây: để video TỰ KỂ, "
            "KHÔNG chen lời.\n"
            f"  B3. CẦU NỐI — narrate NGẮN {_LR_BRIDGE_MIN}-{_LR_BRIDGE_MAX} "
            "giây: 1-2 câu ngắn nối cảnh/đẩy căng rồi NHƯỜNG lại ngay.\n"
            "  B4. GỐC DÀI tiếp — orig 15-40 giây: khoảnh khắc đỉnh, nhân "
            "vật tự nói.\n"
            f"  B5. CHỐT — narrate {_LR_OUTRO_MIN}-{_LR_OUTRO_MAX} giây: 1 "
            "câu chốt đắt + kêu gọi NGẮN.\n"
            "  (Clip NGẮN -> bỏ B3+B4; clip DÀI -> chèn thêm cặp GỐC DÀI -> "
            "cầu nối ngắn, nhưng CẢ CLIP tối đa 1-2 cầu nối.)\n"
            "ĐỘ DÀI PART (bắt buộc — AI nói NHANH GỌN, KHÔNG lan man):\n"
            f"- Part narrate NGẮN: hook {_LR_HOOK_MIN}-{_LR_HOOK_MAX} giây, "
            f"cầu nối {_LR_BRIDGE_MIN}-{_LR_BRIDGE_MAX} giây, chốt "
            f"{_LR_OUTRO_MIN}-{_LR_OUTRO_MAX} giây — câu NGẮN dồn dập, "
            "CẤM viết khối kể dài.\n"
            "- Part orig DÀI là CHỦ ĐẠO (video gốc tự kể chuyện)"
            + (" — MỖI khung cảnh TỐI ĐA 1 cầu nối kể" if per_window else "")
            + ".\n"
            "- CẤM chen narrate giữa lúc nhân vật đang nói cao trào; lời kể "
            "vượt tỉ lệ sẽ bị hệ thống CẮT BỚT.\n")
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


def _part_len_rule(pct: int) -> str:
    """Dòng 'Độ dài part' trong QUY TẮC KỸ THUẬT — theo khuôn của ratio."""
    if _is_low_ratio(pct):
        return (f"- Độ dài part theo KHUÔN Ở TRÊN: narrate NGẮN (hook "
                f"{_LR_HOOK_MIN}-{_LR_HOOK_MAX} giây, cầu nối "
                f"{_LR_BRIDGE_MIN}-{_LR_BRIDGE_MAX} giây, chốt "
                f"{_LR_OUTRO_MIN}-{_LR_OUTRO_MAX} giây); orig DÀI thoải "
                "mái (video gốc là chính). mode = \"orig\" hoặc "
                "\"narrate\".\n")
    return (f"- Độ dài part theo KHUÔN CẤU TRÚC ở trên: narrate "
            f"{_NARR_MIN_S}-{_NARR_MAX_S} giây (hook {_HOOK_MIN_S}-"
            f"{_HOOK_MAX_S} giây), orig {_ORIG_MIN_S}-{_ORIG_MAX_S} giây. "
            "mode = \"orig\" hoặc \"narrate\".\n")


def _ratio_rule(pct: int) -> str:
    """Dòng ÉP TỈ LỆ narrate trong prompt — vai chủ đạo đổi theo ratio."""
    lo, hi = max(10, pct - 10), min(90, pct + 10)
    if _is_low_ratio(pct):
        return (f"- Tổng thời lượng narrate CHỈ ~{pct}% clip (chấp nhận "
                f"{lo}-{hi}%) — TIẾNG GỐC là CHỦ ĐẠO, AI chỉ chen hook + "
                "cầu nối + chốt NGẮN GỌN; kể vượt tỉ lệ sẽ bị hệ thống CẮT "
                "bớt phần kể.\n")
    return (f"- Tổng thời lượng narrate chiếm ~{pct}% clip (chấp nhận "
            f"{lo}-{hi}%) — người kể nói CHỦ ĐẠO, tiếng gốc chỉ bung đúng "
            "chỗ đắt.\n")


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
# 🔊 NHÃN TIẾNG ĐỘNG (SFX) THEO CẢM XÚC — AI đạo diễn gắn cho MỖI part
# ------------------------------------------------------------------
# TẬP NHÃN CỐ ĐỊNH: khớp SFX_CATEGORIES của ffmpeg_utils + "none" (không chèn).
# App (m1_highlight._join_categories -> ffmpeg_utils) đọc part["sfx"] và chèn
# đúng loại tiếng tại ĐIỂM VÀO part đó. Nhãn lạ / thiếu -> "none".
SFX_LABELS = ("none", "transition", "impact", "riser", "reveal", "pop",
              "suspense", "comedy", "scratch", "sad", "drumroll")
_SFX_LABEL_SET = frozenset(SFX_LABELS)
# TRẦN mật độ: tối đa 1 tiếng / khoảng giây này (tránh dày đặc/lố nhạc nhọt).
_SFX_MIN_GAP_S = 7.0


def _sfx_rule() -> str:
    """Khối chỉ dẫn AI GẮN NHÃN tiếng động theo CẢM XÚC cho mỗi part. Dùng
    chung 2 đường prompt (1-span + đạo diễn). Nhấn: PHẦN LỚN để none, chỉ gắn
    2-4 điểm/clip ở CHỖ THỰC SỰ HỢP — tránh lố."""
    return (
        "🔊 TIẾNG ĐỘNG THEO CẢM XÚC (bắt buộc — thêm field \"sfx\" cho MỖI "
        "part): chọn ĐÚNG 1 nhãn trong tập cố định để app tự chèn tiếng động "
        "ngắn ngay ĐẦU part đó, khớp cảm xúc/nhịp cảnh:\n"
        "  • none — KHÔNG chèn tiếng (MẶC ĐỊNH cho ĐA SỐ part).\n"
        "  • scratch — cú \"khựng\" BẤT NGỜ / plot-twist quay ngoắt (record "
        "scratch).\n"
        "  • comedy — khoảnh khắc HÀI / lầy / ngớ ngẩn (boing vui).\n"
        "  • sad — đoạn BUỒN / hụt hẫng / tiếc nuối (nốt trầm buồn).\n"
        "  • suspense — đoạn GÂY CẤN / hồi hộp / căng thẳng (drone trầm nền).\n"
        "  • drumroll — NGAY TRƯỚC cao trào / màn hé lộ (trống dồn).\n"
        "  • riser — build-up căng dần trước cú twist (khác drumroll: mượt "
        "hơn).\n"
        "  • impact — CÚ SỐC MẠNH / va chạm / con số gây choáng (boom).\n"
        "  • reveal — lúc LỘ DIỆN kết quả / câu chốt cuối (ding).\n"
        "  • pop — điểm nhấn nhẹ, vui tươi nhanh (pop/blip).\n"
        "  • transition — CHUYỂN CẢNH thường, nhảy thời gian (whoosh nhẹ).\n"
        "QUY TẮC GẮN (bắt buộc — vừa đủ, KHÔNG lạm dụng):\n"
        "- GẮN CHÍNH XÁC 2-4 part có tiếng (KHÁC \"none\") trong cả clip — tại "
        "ĐÚNG 2-4 khoảnh khắc ĐẮT NHẤT (twist bất ngờ, cú sốc, cao trào, câu "
        "chốt, hoặc nhịp buồn/hài rõ rệt). ÍT hơn 2 -> clip chán; NHIỀU hơn 4 "
        "-> nghe LỐ, rẻ tiền như nhạc chế.\n"
        "- MỌI part còn lại BẮT BUỘC để \"sfx\": \"none\".\n"
        "- Gắn ĐÚNG cảm xúc: cảnh buồn KHÔNG dùng comedy; cảnh hài KHÔNG dùng "
        "sad; cú bất ngờ dùng scratch; trước cao trào dùng drumroll/riser; cú "
        "sốc mạnh dùng impact; câu chốt cuối dùng reveal. Đừng gắn bừa cho có.\n"
        "- 2 part LIỀN NHAU KHÔNG cùng gắn tiếng (để tai được thở); tiếng nên "
        "rơi vào ĐẦU part quan trọng, cách nhau vài giây.\n")


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
    "tl": "Filipino", "lo": "Lao", "km": "Khmer", "my": "Burmese",
}
_LANG_ALIAS = {
    "vietnamese": "vi", "tiếng việt": "vi", "tieng viet": "vi",
    "english": "en", "tiếng anh": "en", "japanese": "ja", "tiếng nhật": "ja",
    "korean": "ko", "tiếng hàn": "ko", "chinese": "zh", "tiếng trung": "zh",
    "thai": "th", "tiếng thái": "th", "french": "fr", "tiếng pháp": "fr",
    "spanish": "es", "tiếng tây ban nha": "es", "german": "de",
    "tiếng đức": "de", "russian": "ru", "tiếng nga": "ru",
    "indonesian": "id", "tiếng indonesia": "id", "portuguese": "pt",
    "italian": "it", "tiếng ý": "it", "arabic": "ar", "tiếng ả rập": "ar",
    "hindi": "hi", "dutch": "nl", "tiếng hà lan": "nl",
    "turkish": "tr", "tiếng thổ nhĩ kỳ": "tr", "polish": "pl",
    "tiếng ba lan": "pl", "lao": "lo", "tiếng lào": "lo",
    "khmer": "km", "tiếng khmer": "km", "burmese": "my", "myanmar": "my",
    "tiếng miến điện": "my",
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


def detect_lang_by_script(text: str) -> str:
    """NHẬN DIỆN ngôn ngữ theo CHỮ VIẾT trong text -> mã ("ja"/"ko"/"zh"/"th"/
    "ru"/"ar"/"hi"/"he") hoặc "" nếu là chữ Latin/không rõ. Dùng làm LƯỚI AN
    TOÀN: nếu nhãn ngôn ngữ lưu bị SAI (vd whisper bị ép "en" nhưng chữ ra là
    tiếng Nhật) thì cứ nhìn CHỮ mà ép đúng. Chữ Latin (en/vi/fr/de/es...) trả ""
    vì không phân biệt được qua ký tự -> giữ nhãn gốc. Hàm thuần.

    ja vs zh: có kana (hiragana/katakana) -> ja; chỉ có Hán tự -> zh."""
    t = str(text or "")
    if not t:
        return ""
    kana = hangul = han = thai = cyr = arab = deva = hebr = 0
    letters = 0
    for ch in t:
        o = ord(ch)
        if ch.isspace() or not ch.isalpha():
            continue
        letters += 1
        if 0x3040 <= o <= 0x30FF or 0xFF66 <= o <= 0xFF9F:
            kana += 1
        elif 0xAC00 <= o <= 0xD7A3:
            hangul += 1
        elif (0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF
              or 0xF900 <= o <= 0xFAFF):
            han += 1
        elif 0x0E00 <= o <= 0x0E7F:
            thai += 1
        elif 0x0400 <= o <= 0x04FF:
            cyr += 1
        elif 0x0600 <= o <= 0x06FF:
            arab += 1
        elif 0x0900 <= o <= 0x097F:
            deva += 1
        elif 0x0590 <= o <= 0x05FF:
            hebr += 1
    if letters <= 0:
        return ""
    # script phi-Latin CHIẾM ĐA SỐ đáng kể -> ép theo script đó
    nonlatin = kana + hangul + han + thai + cyr + arab + deva + hebr
    if nonlatin < 0.15 * letters:
        return ""                       # chủ yếu Latin -> giữ nhãn gốc
    if kana > 0:
        return "ja"
    for cnt, code in ((hangul, "ko"), (thai, "th"), (cyr, "ru"),
                      (arab, "ar"), (deva, "hi"), (hebr, "he"), (han, "zh")):
        if cnt and cnt == max(hangul, thai, cyr, arab, deva, hebr, han):
            return code
    return ""


def resolve_lang(stored: str, text: str = "") -> str:
    """Ngôn ngữ ĐÁNG TIN NHẤT cho recap/phụ đề: ưu tiên nhãn `stored` của
    whisper; NHƯNG nếu CHỮ trong `text` là script phi-Latin (Nhật/Hàn/Thái/
    Nga/Ả Rập...) mà nhãn lại rỗng HOẶC trỏ ngôn ngữ Latin (en/vi/fr...) thì
    nhãn đó SAI -> ép theo CHỮ. (Sửa lỗi transcript cũ bị dán nhãn 'en' cho
    video Nhật.) Hàm thuần."""
    by_text = detect_lang_by_script(text)
    if not by_text:
        return stored or ""
    s = str(stored or "").strip().lower()
    s = _LANG_ALIAS.get(s, s)
    # nhãn gốc CŨNG là script phi-Latin và khớp -> giữ; ngược lại (rỗng/Latin/
    # khác script) -> tin CHỮ
    if s in ("ja", "ko", "zh", "th", "ru", "ar", "hi", "he") and s == by_text:
        return stored
    if s in ("ja", "ko", "zh", "th", "ru", "ar", "hi", "he") and s != by_text:
        return by_text            # nhãn phi-Latin nhưng khác chữ -> tin chữ
    return by_text                # nhãn rỗng/Latin nhưng chữ phi-Latin -> ép chữ


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
        "NGUYÊN TẮC VÀNG — BẠN LÀ NGƯỜI BÌNH LUẬN ĐỨNG NGOÀI:\n"
        "- Bạn KHÔNG thuật lại việc đang xảy ra trên màn hình — khán giả TỰ "
        "THẤY hình + TỰ NGHE nhân vật nói ở đoạn tiếng gốc. Mô tả lại diễn "
        "biến = THỪA và CHÁN.\n"
        "- Thay vào đó, lời bạn phải THÊM tầng NGOÀI hình: CẢM XÚC / ĐÁNH GIÁ "
        "/ DỰ ĐOÁN / CÂU HỎI ném khán giả / thông tin nền / HẬU QUẢ / cái giá "
        "phải trả — thứ transcript KHÔNG nói ra.\n"
        "- Đoạn tiếng GỐC để nhân vật + hình TỰ kể diễn biến; lời bạn chỉ "
        "THÊM GÓC NHÌN, KHÔNG lặp lại diễn biến đó.\n\n"
        "CẤM TUYỆT ĐỐI trong lời narrate:\n"
        "- CẤM MÔ TẢ LẠI hành động/sự việc đang diễn ra trên hình (khán giả "
        "tự thấy) — kiểu \"anh ấy mở van và nghe tiếng xì\", \"cô ấy cầm dao "
        "lên cắt\". Đó là THUYẾT MINH LẠI, không phải BÌNH LUẬN.\n"
        "- CẤM lặp lại, diễn giải lại, PARAPHRASE hay tóm tắt lại câu nhân "
        "vật VỪA nói hoặc SẮP nói trong transcript — người xem sắp nghe/vừa "
        "nghe câu đó rồi. Đổi ĐẠI TỪ (tôi->anh ấy / I->he), đổi THÌ "
        "(cắt->đã cắt / touched->touches), hay ĐẢO TRẬT TỰ VẪN là thuật lại "
        "-> CẤM.\n"
        "- CẤM dùng lại NGUYÊN CỤM 3 từ trở lên có trong transcript (nhại "
        "cụm lời thoại).\n"
        "- CẤM kiểu tường thuật gián tiếp: \"anh ấy nói rằng...\", \"cô ấy "
        "bảo là...\", \"anh ta giải thích rằng...\".\n"
        # VÍ DỤ ✅/❌ theo ĐÚNG ngôn ngữ video (video Việt -> ví dụ Việt;
        # ngôn ngữ khác -> ví dụ tiếng Anh) — KHÔNG trộn 2 thứ tiếng để
        # model không bắt chước nhầm ngôn ngữ của ví dụ. THÊM cặp EXPLAINER
        # (nhân vật TỰ THUYẾT MINH) — lỗi thật: AI mô tả lại hành động họ nói.
        + ("VÍ DỤ ĐÚNG/SAI (bám vào transcript, KHÔNG chép):\n"
           "  ① Transcript nhân vật: \"tôi bấm nhầm nút bán hết cổ phiếu\".\n"
           "    ✅ ĐÚNG (bình luận góc ngoài): \"Gã này vừa mất cả gia tài "
           "chỉ vì một cú click...\"\n"
           "    ❌ SAI (thuật lại): \"Anh ấy nói anh ấy bấm nhầm nút bán hết "
           "cổ phiếu.\"\n"
           "  ② (EXPLAINER — nhân vật tự thuyết minh) Transcript: \"vừa chạm "
           "vào cái van là tôi nghe tiếng xì rất to\".\n"
           "    ❌ SAI (mô tả lại việc trên hình): \"Anh ấy chạm vào van và "
           "nghe tiếng xì lớn.\"\n"
           "    ✅ ĐÚNG (bình luận từ ngoài): \"Và đây là khoảnh khắc mọi "
           "thứ suýt nổ tung — thứ mà 9/10 người sẽ không dám thử.\"\n\n"
           if _is_vi_lang(ln) else
           "VÍ DỤ ĐÚNG/SAI (bám vào transcript, KHÔNG chép):\n"
           "  (1) Transcript: \"i accidentally sold all my shares\".\n"
           "    ✅ RIGHT (outsider comment): \"One wrong click. His entire "
           "fortune — gone.\"\n"
           "    ❌ WRONG (retelling): \"He says he accidentally sold all his "
           "shares.\"\n"
           "  (2) (EXPLAINER — the person narrates their own action) "
           "Transcript: \"the moment I touched the valve I heard a really "
           "loud hiss\".\n"
           "    ❌ WRONG (re-describing on-screen action): \"He touches the "
           "valve and a loud hiss is heard.\"\n"
           "    ✅ RIGHT (commentary from outside): \"This is the moment it "
           "nearly blew up — something 9 out of 10 people would never dare "
           "to try.\"\n\n") +
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
    ratio = tỉ lệ % thời lượng AI kể (user chỉnh 15-80, mặc định 30) —
    đưa vào prompt dạng ~X% ±10%; ratio <= 40 -> KHUÔN LOW-RATIO (AI nói
    ít, nhanh gọn, nhường video gốc — xem _structure_rules)."""
    lines = "\n".join(f"{a:.1f} {b:.1f} | {t}" for a, b, t in sentences)[:6000]
    dur = clip_end - clip_start
    ln = lang_name.upper()
    try:
        pct = int(round(max(15.0, min(80.0, float(ratio)))))
    except (TypeError, ValueError):
        pct = 30

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
        + _structure_rules(ratio=pct) +
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
        + _part_len_rule(pct) +
        "- start/end của MỖI part phải trùng mép câu transcript (không cắt "
        "ngang giữa câu nói).\n"
        + _ratio_rule(pct) +
        f"- text của part narrate: viết BẰNG {ln} (ĐÚNG ngôn ngữ video), "
        "văn NÓI tự nhiên — "
        + ("mỗi part chỉ 1-2 câu NGẮN, vào thẳng ý, không lan man.\n"
           if _is_low_ratio(pct) else
           "khối dài = 2-5 câu NGẮN nối nhau LIỀN MẠCH cùng 1 mạch ý.\n")
        + f"- {_RATE_HINT} HÃY ĐẾM CHỮ: lời narrate phải đọc VỪA KHÍT độ dài "
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
        + _sfx_rule()
        + _lang_remind(ln) +
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"context_summary": "...", "title": "...", "parts": '
        '[{"start": giây, "end": giây, "mode": "orig"|"narrate", '
        '"text": "lời thuyết minh nếu narrate", "sfx": "none"|"transition"|'
        '"impact"|"riser"|"reveal"|"pop"|"suspense"|"comedy"|"scratch"|'
        '"sad"|"drumroll"}]}')


# ------------------------------------------------------------------
# VALIDATE + TỰ SỬA kịch bản (hàm thuần — unit test được)
# ------------------------------------------------------------------
def _norm_for_copy(text: str) -> str:
    """Chuẩn hoá text để so 'copy nguyên văn': bỏ dấu câu/khoảng trắng thừa,
    hạ chữ thường, chuẩn unicode (đủ bắt AI chép transcript đổi vài dấu phẩy).

    GIỮ DẤU KẾT HỢP (unicode Mn/Mc — virama/matra Devanagari, sara Thái,
    dấu Khmer/Miến/Ả Rập): lưới cũ `[^\\w\\s]` coi chúng là "dấu câu" và
    thay bằng KHOẢNG TRẮNG -> từ Hindi/Thái bị BĂM VỤN ("क्या" -> "क या")
    -> stopword không khớp + mọi lời trùng mọi lời -> anti-copy gut oan
    (lỗi thật với tiếng Hindi). Ký tự EN/VI/JA/latin đều isalnum -> đường
    cũ GIỮ NGUYÊN từng byte (bất biến test khẳng định)."""
    t = unicodedata.normalize("NFC", str(text or "")).lower()
    t = "".join(c if (c.isalnum() or c.isspace() or c == "_"
                      or unicodedata.category(c) in ("Mn", "Mc"))
                else " " for c in t)
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------
# TÁCH TỪ CJK-AWARE. Ngôn ngữ KHÔNG DÙNG DẤU CÁCH (Nhật/Trung/Thái/Hàn) ->
# `.split()` coi CẢ CÂU là 1 "từ" -> _win_density tính ~0.3 token/giây <
# _MIN_DENSITY (1.2) -> validate_windows loại SẠCH khung -> None -> fallback.
# _word_tokens tách MỖI ký tự CJK thành 1 token riêng (mật độ Nhật ~2-3
# token/giây, qua ngưỡng), NHƯNG giữ NGUYÊN phần latin/số theo khoảng trắng.
# BẤT BIẾN: với text KHÔNG có ký tự CJK, _word_tokens(x) == x.split()
# (test khẳng định) — đường EN/VI KHÔNG đổi hành vi.
# ------------------------------------------------------------------
# Dải ký tự CHỮ VIẾT KHÔNG DÙNG DẤU CÁCH giữa các từ (tên biến giữ
# "_CJK_*" để không phá chỗ gọi — khái niệm đúng là "chữ viết không dấu
# cách"): hiragana+katakana (U+3040-30FF), kanji/CJK ext-A (U+3400-4DBF)
# + CJK Unified (U+4E00-9FFF) + compat (U+F900-FAFF), katakana nửa
# (U+FF66-FF9F), hangul (U+AC00-D7A3 — tiếng Hàn CÓ dùng dấu cách nhưng
# per-char chỉ làm density cao hơn, vô hại), Thái (U+0E00-0E7F), Lào
# (U+0E80-0EFF), Miến Điện (U+1000-109F), Khmer (U+1780-17FF).
# KHÔNG gồm latin/cyrillic/ả rập/devanagari — các tiếng đó dùng dấu
# cách, giữ nguyên đường .split() (bất biến test khẳng định).
_CJK_CHARS = (
    "぀-ヿ"        # hiragana + katakana
    "㐀-䶿"        # CJK Unified ext-A
    "一-鿿"        # CJK Unified
    "豈-﫿"        # CJK compat ideographs
    "ｦ-ﾟ"        # halfwidth katakana
    "가-힣"        # hangul syllables
    "฀-๿"        # Thái
    "຀-໿"        # Lào
    "က-႟"        # Miến Điện
    "ក-៿"        # Khmer
)
_CJK_RE = re.compile("[" + _CJK_CHARS + "]")
# Token: 1 KÝ TỰ CJK riêng lẻ, HOẶC 1 cụm không-phải-CJK-không-khoảng-trắng
# (latin/số giữ nguyên như split theo dấu cách). Chuỗi con non-CJK giữa các
# ký tự CJK cũng thành token riêng theo cụm — đúng ý "latin giữ theo cách".
_CJK_TOKEN_RE = re.compile("[" + _CJK_CHARS + "]|[^\\s" + _CJK_CHARS + "]+")


def _has_cjk(text: str) -> bool:
    """Text có chứa ký tự CJK (Nhật/Trung/Hàn) không. Hàm thuần."""
    return bool(_CJK_RE.search(str(text or "")))


def _word_tokens(norm_text: str) -> list:
    """Tách `norm_text` (đã qua _norm_for_copy) thành danh sách token cho
    ĐẾM MẬT ĐỘ / SO-KHỚP TẬP-TỪ CJK-aware:
      - ký tự CJK -> mỗi ký tự 1 token riêng (câu Nhật/Trung không có dấu
        cách vẫn cho nhiều token -> mật độ đúng);
      - phần latin/số giữ NGUYÊN theo khoảng trắng (như .split()).
    BẤT BIẾN: nếu norm_text KHÔNG có ký tự CJK, trả về Y HỆT
    `norm_text.split()`. Hàm thuần — unit test được."""
    s = str(norm_text or "")
    if not _CJK_RE.search(s):
        return s.split()          # bất biến: đường non-CJK y hệt .split()
    return _CJK_TOKEN_RE.findall(s)


def _is_transcript_copy(text: str, transcript_norm: str) -> bool:
    """Narrate text có phải CHÉP NGUYÊN VĂN transcript không (AI lười).
    Chỉ tính khi câu đủ dài (>= 4 từ và >= 15 ký tự sau chuẩn hoá) — câu quá
    ngắn ('what?', 'không thể nào') trùng ngẫu nhiên là bình thường."""
    if not transcript_norm:
        return False
    t = _norm_for_copy(text)
    # Guard độ dài: >= 4 TOKEN (CJK-aware — câu Nhật không dấu cách vẫn đếm
    # đúng qua _word_tokens) VÀ >= 15 ký tự. Non-CJK: _word_tokens == split()
    # nên hành vi Y CŨ.
    if len(t) < 15 or len(_word_tokens(t)) < 4:
        return False
    return t in transcript_norm


# Ngưỡng FUZZY anti-copy: lời narrate trùng > tỉ lệ từ này với transcript
# TRONG ĐÚNG KHOẢNG THỜI GIAN của part -> coi như AI kể lại lời nhân vật.
# SIẾT 0.60 -> 0.45: diễn giải SÁT NGHĨA (đổi vài từ, đảo trật tự) vẫn trùng
# ~45-55% từ với transcript -> nghe như "đọc lại lời người kia". Lời KỂ sáng
# tác thật (thêm cảm xúc/bình luận/góc ngoài) dùng từ vựng khác hẳn -> trùng
# thấp (thường <30%), nên hạ ngưỡng vẫn KHÔNG loại nhầm câu sáng tác.
# SIẾT LẠI (v8): 0.45 -> chuyển sang so TẬP TỪ-NỘI-DUNG (order-independent,
# chuẩn hoá đại từ ngôi + biến thể thì/số) với ngưỡng 0.55 — lỗi thật: LLM
# "kể lại" lời nhân vật chỉ đổi đại từ (I->he) + thì (touched->touches) +
# đảo trật tự thì lưới CŨ (đếm TỪ THÔ có thứ tự, không bỏ stopword) tính ~73%
# nhưng CHỈ soi ĐÚNG window part -> khi LLM đặt narrate ở window KHÁC với câu
# nó kể lại thì trượt (xem _copy_overlap_windows áp cả window KỀ).
_FUZZY_COPY_MAX = 0.45          # (giữ cho tương thích test cũ — lưới thô)
# Ngưỡng TẬP TỪ-NỘI-DUNG (bỏ stopword, chuẩn đại từ/thì): narrate trùng >=
# tỉ lệ này TẬP từ-nội-dung với transcript window (VÀ window kề) -> KỂ LẠI.
_CONTENT_OVERLAP_MAX = 0.55
# n-gram CHẶN THEO Ý: narrate trùng >= số TỪ-NỘI-DUNG LIÊN TIẾP này với 1 cụm
# trong transcript window -> coi là THUẬT LẠI lời nhân vật (dù tỉ lệ tổng thấp).
# Bắt kiểu "anh ấy nói anh ấy bấm nhầm nút bán hết cổ phiếu" nhại nguyên cụm.
_RETELL_NGRAM = 3

# ------------------------------------------------------------------
# CHUẨN HOÁ ĐẠI TỪ NGÔI + biến thể thì/số cho anti-copy ORDER-INDEPENDENT.
# Lỗi thật: nhân vật TỰ THUYẾT MINH ("tôi/I" làm), AI kể lại đổi ngôi
# (I->he, tôi->gã) + thì (touched->touches) + đảo trật tự -> lưới cũ trượt.
# Gộp MỌI đại từ ngôi về 1 token chung "§p" (chủ ngữ/tân ngữ/sở hữu đều gộp
# — chỉ cần biết "có 1 người" chứ không phân biệt ai) rồi so TẬP từ-nội-dung.
# ------------------------------------------------------------------
_PRON_CANON = "§p"
_PRON_WORDS = frozenset((
    # --- EN: chủ ngữ / tân ngữ / sở hữu / phản thân ---
    "i", "me", "my", "mine", "myself",
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "we", "us", "our", "ours", "ourselves",
    "they", "them", "their", "theirs", "themselves",
    "you", "your", "yours", "yourself", "yourselves",
    "it", "its", "itself",
    # --- VI: các đại từ ngôi thường gặp (có/không dấu) ---
    "tôi", "toi", "tao", "ta", "tớ", "to", "mình", "minh",
    "anh", "chị", "chi", "em", "hắn", "han", "cô", "co",
    "chú", "chu", "bác", "bac", "ông", "ong", "bà", "ba",
    "nó", "no", "họ", "ho", "cậu", "cau", "gã", "ga", "y", "thị", "thi",
))


def _canon_word(w: str) -> str:
    """Chuẩn hoá 1 từ cho so-TẬP anti-copy: đại từ ngôi -> token chung "§p";
    cắt hậu tố thì/số EN thường (-ing/-ed/-es/-s) để "touches"~"touched"
    ~"touch" khớp nhau (chặn AI đổi thì né lưới). Hàm thuần."""
    if w in _PRON_WORDS:
        return _PRON_CANON
    for suf in ("ing", "ed", "es", "s"):
        if len(w) - len(suf) >= 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _content_pron_set(text: str) -> set:
    """TẬP TỪ-NỘI-DUNG của text sau khi (a) chuẩn hoá đại từ ngôi -> "§p",
    (b) cắt hậu tố thì/số EN, (c) BỎ các stopword còn lại. Đại từ ngôi được
    GIỮ (dạng "§p") vì "một người làm X" là nội dung khớp giữa narrate kể lại
    và transcript. Dùng cho so-TẬP ORDER-INDEPENDENT (đảo trật tự vẫn khớp)."""
    out: set = set()
    for w in _norm_for_copy(text).split():
        c = _canon_word(w)
        if c == _PRON_CANON:
            out.add(c)
        elif len(c) > 1 and c not in _STOPWORDS:
            out.add(c)
    return out


def _fuzzy_copy_ratio(text: str, window_words: set) -> float:
    """Tỉ lệ (0..1) từ của lời narrate XUẤT HIỆN trong tập từ transcript
    của cửa sổ thời gian tương ứng (đã chuẩn hoá _norm_for_copy). Lời quá
    ngắn (< 4 từ) -> 0.0 (trùng ngẫu nhiên là bình thường).

    Đây là lưới FUZZY bắt kiểu 'diễn giải lại lời nhân vật' (đổi vài từ,
    đảo trật tự) mà _is_transcript_copy (so nguyên văn) lọt: lời KỂ sáng
    tác thật sự (thêm cảm xúc/bình luận/góc nhìn ngoài) dùng từ vựng khác
    hẳn transcript nên tỉ lệ trùng thấp.

    HINDI: bỏ hư từ Devanagari (_STOP_HI) trước khi đếm — câu Hindi ngắn
    gần như toàn hư từ (का की में है...) nên đếm TỪ THÔ làm lời sáng tác
    trùng ~100% -> gut oan (lỗi thật). Token Devanagari không đụng vi/en
    -> đường EN/VI giữ Y CŨ (lưới thô cố tình đếm cả stopword vi/en)."""
    words = [w for w in _norm_for_copy(text).split() if w not in _STOP_HI]
    if len(words) < 4 or not window_words:
        return 0.0
    hit = sum(1 for w in words if w in window_words)
    return hit / len(words)


def _content_overlap_ratio(text: str, window_text: str) -> float:
    """Tỉ lệ (0..1) TẬP TỪ-NỘI-DUNG của narrate trùng tập từ-nội-dung của
    transcript window — ORDER-INDEPENDENT + chuẩn hoá đại từ ngôi + thì/số
    (_content_pron_set). Đây là lưới CHÍNH bắt "kể lại" kiểu explainer: câu
    narrate "The moment he touches the valve, a loud hiss is heard" vs
    transcript "The moment I touched the valve I heard a really loud hiss"
    -> tập nội dung {§p, moment, touch, valve, loud, hiss, hear} trùng ~100%.
    Lời BÌNH LUẬN sáng tác (từ vựng ngoài: exploded, dare, people...) trùng
    thấp. narrate < 4 từ-nội-dung -> 0.0 (trùng ngẫu nhiên). Hàm thuần."""
    a = _content_pron_set(text)
    if len(a) < 4 or not window_text:
        return 0.0
    b = _content_pron_set(window_text)
    if not b:
        return 0.0
    return len(a & b) / len(a)


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
    """Dãy TỪ-NỘI-DUNG (đã CHUẨN HOÁ đại từ ngôi -> "§p" + cắt hậu tố thì/số,
    bỏ stopword còn lại, bỏ từ 1 ký tự) theo ĐÚNG thứ tự xuất hiện — để dò
    n-gram liên tiếp trùng transcript. Chuẩn hoá (_canon_word) giúp n-gram
    khớp dù AI đổi thì (touched/touches) hoặc ngôi (I/he)."""
    out = []
    for w in _norm_for_copy(text).split():
        c = _canon_word(w)
        if c == _PRON_CANON or (len(c) > 1 and c not in _STOPWORDS):
            out.append(c)
    return out


def _is_retelling(text: str, window_text: str, n: int = _RETELL_NGRAM) -> bool:
    """narrate có KỂ LẠI lời nhân vật không — 2 lưới (OR):
      (1) TẬP TỪ-NỘI-DUNG (order-independent, chuẩn đại từ/thì) trùng
          transcript window >= _CONTENT_OVERLAP_MAX (55%) -> KỂ LẠI. Bắt
          kiểu explainer đổi ngôi + thì + đảo trật tự: "The moment he
          touches the valve, a loud hiss is heard" vs transcript "The
          moment I touched the valve I heard a really loud hiss".
      (2) >= `n` TỪ-NỘI-DUNG LIÊN TIẾP trùng 1 cụm trong window (nhại nguyên
          cụm) — cả sau chuẩn hoá đại từ/thì.

    Câu (a) sáng tác "gã này vừa mất cả gia tài chỉ vì một cú click" trùng
    tập THẤP + KHÔNG có n-gram liên tiếp -> QUA. Hàm thuần — unit test được.

    Dùng _canon_word + _STOPWORDS: "anh ấy nói" (toàn đại từ/stopword) thành
    ["§p", "nói"] — chỉ cụm NỘI DUNG thật mới bị bắt."""
    if not window_text:
        return False
    # (1) TẬP TỪ-NỘI-DUNG order-independent
    if _content_overlap_ratio(text, window_text) >= _CONTENT_OVERLAP_MAX:
        return True
    # (2) n-gram TỪ-NỘI-DUNG liên tiếp (đã chuẩn hoá đại từ/thì)
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


# Nới CỬA SỔ anti-copy ra 2 bên part `_COPY_WIN_PAD` giây — LỖI THẬT: video
# nhân vật TỰ THUYẾT MINH (explainer), AI đặt narrate ở part [12-16] nhưng
# lại KỂ LẠI câu transcript nói ở [8-12] (part KHÁC). Lưới cũ chỉ soi ĐÚNG
# [12,16] nên trượt. Soi cả câu transcript KỀ (±pad, phủ câu ngay trước/sau)
# thì bắt được. pad ~6s = ~1 câu explainer 2 bên.
_COPY_WIN_PAD = 6.0


def _is_copy_narrate(text: str, sentences: list, start: float,
                     end: float, pad: float = _COPY_WIN_PAD) -> bool:
    """narrate `text` có KỂ LẠI / TRÙNG CAO transcript quanh [start,end]
    không (soi CẢ câu KỀ ±pad — nhân vật explainer tự thuyết minh, AI kể lại
    câu ở part sát bên) -> True = giữ tiếng gốc. Gộp 3 lưới:
      - _fuzzy_copy_ratio (đếm từ THÔ) > _FUZZY_COPY_MAX (giữ lưới cũ);
      - _is_retelling: TẬP từ-nội-dung order-independent (chuẩn đại từ/thì)
        >= _CONTENT_OVERLAP_MAX HOẶC n-gram nội dung liên tiếp trùng.
    Soi window HẸP (đúng [start,end]) TRƯỚC rồi window RỘNG (±pad) — window
    rộng bắt câu kề, hẹp tránh phồng oan khi part dài. Hàm thuần — test được.

    CJK (Nhật/Trung/Hàn): các lưới FUZZY (_fuzzy_copy_ratio) + N-GRAM nội dung
    (_is_retelling) được HIỆU CHUẨN cho ngôn ngữ có dấu cách. Áp token-KÝ-TỰ
    cho CJK sẽ BÁO NHẦM (kanji chung như 会社/気持ち trùng 3-gram) -> gut oan
    thoại tốt. Nên với text CJK ta BỎ QUA 2 lưới này (coi như KHÔNG copy) —
    lưới CHÉP NGUYÊN VĂN _is_transcript_copy (so chuỗi con, char-based, đúng
    cho CJK) vẫn chạy RIÊNG ở validate_parts nên chép y nguyên vẫn bị bắt."""
    if _has_cjk(text):
        return False
    for ws, we in ((start, end), (start - pad, end + pad)):
        wtext = _window_text(sentences, ws, we)
        if not wtext:
            continue
        if _fuzzy_copy_ratio(text, _window_words(sentences, ws, we)) \
                > _FUZZY_COPY_MAX:
            return True
        if _is_retelling(text, wtext):
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
# HINDI: hư từ Devanagari (hậu tố cách/trợ động từ/đại từ) — LỖI THẬT: câu
# Hindi ngắn gần như toàn hư từ (का की के में है...), _STOPWORDS chỉ có
# vi+en nên hư từ Hindi bị đếm là TỪ-NỘI-DUNG -> lời BÌNH LUẬN sáng tác
# tiếng Hindi trùng >=55% "nội dung" với transcript -> _is_retelling gut
# oan SẠCH narrate. Token Devanagari không đụng vi/en/ja -> thêm an toàn.
_STOP_HI = set(
    "का की के को से में ने पर और भी ही तो या है हैं था थी थे हो होगा होगी "
    "होंगे हुआ हुई हुए कर करके रहा रही रहे गया गई गए यह वह इस उस ये वो जो "
    "कि अब जब तब क्या कौन क्यों कैसे कहाँ नहीं मैं हम तुम आप वे मेरा मेरी "
    "मेरे उसका उसकी उसके उनका उनकी उनके अपना अपनी अपने इसका इसकी इसके एक "
    "दो कुछ सब बहुत लिए साथ बाद पहले फिर ओर तरह बात वाला वाली वाले".split())
_STOPWORDS = _STOP_VI | _STOP_EN | _STOP_HI


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
    Hàm thuần — unit test được.

    CJK (Nhật/Trung/Hàn): lưới prefix/trùng-token được hiệu chuẩn cho ngôn
    ngữ CÓ dấu cách; token-ký-tự CJK trùng/không-trùng ngẫu nhiên nên dễ LOẠI
    OAN lời kể tốt. Với text CJK -> coi như LIÊN QUAN (relevance đã có ràng
    buộc GIAO THỜI GIAN ở tầng gọi: `near` là tập từ transcript đúng khung +
    khung kề). Non-CJK: hành vi Y CŨ."""
    if _has_cjk(text):
        return True
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
        n = len(_word_tokens(_norm_for_copy(t)))   # CJK-aware (non-CJK y cũ)
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
        n = len(_word_tokens(_norm_for_copy(t)))   # CJK-aware (non-CJK y cũ)
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


def _raw_sfx_labels(raw_parts) -> list[tuple[float, str]]:
    """Rút (start, nhãn_sfx_hợp_lệ) từ parts THÔ của LLM — CHỈ nhãn KHÁC
    "none" (nhãn thật AI muốn chèn). Dùng để tái gắn nhãn cho part sau khi
    validate reshape (gộp/tách/đổi mode làm rớt key sfx). Hàm thuần."""
    out: list[tuple[float, str]] = []
    for p in _coerce_parts(raw_parts):
        if not isinstance(p, dict):
            continue
        try:
            s = float(p.get("start"))
        except (TypeError, ValueError):
            continue
        lab = str(p.get("sfx") or "").strip().lower()
        if lab in _SFX_LABEL_SET and lab != "none":
            out.append((round(s, 2), lab))
    return out


def _apply_sfx_labels(parts: list[dict], raw_labels: list,
                      min_gap: float = _SFX_MIN_GAP_S) -> list[dict]:
    """Gắn nhãn "sfx" vào các part ĐÃ validate từ raw_labels (start, nhãn):
    part nhận nhãn của raw-label có start GẦN start part đó nhất (trong 2.5s).
    Sau đó ÉP MẬT ĐỘ: quét theo thời gian, chỉ GIỮ nhãn nếu cách nhãn được
    giữ TRƯỚC đó >= min_gap giây (tránh dày đặc/lố). Part không nhận nhãn ->
    "none". KHÔNG sửa list vào. Hàm thuần — unit test được."""
    out = [dict(p) for p in parts]
    used = [False] * len(raw_labels)
    for p in out:
        try:
            ps = float(p["start"])
        except (KeyError, TypeError, ValueError):
            p["sfx"] = "none"
            continue
        best_j, best_d = -1, 2.5
        for j, (rs, _lab) in enumerate(raw_labels):
            if used[j]:
                continue
            d = abs(rs - ps)
            if d < best_d:
                best_j, best_d = j, d
        if best_j >= 0:
            used[best_j] = True
            p["sfx"] = raw_labels[best_j][1]
        else:
            p["sfx"] = "none"
    # ÉP MẬT ĐỘ: theo thứ tự thời gian, khử nhãn quá gần nhãn trước đã giữ.
    last_kept = None
    for p in sorted(out, key=lambda x: float(x.get("start", 0))):
        if p.get("sfx", "none") == "none":
            continue
        try:
            ps = float(p["start"])
        except (KeyError, TypeError, ValueError):
            p["sfx"] = "none"
            continue
        if last_kept is not None and ps - last_kept < min_gap:
            p["sfx"] = "none"           # quá dày -> bỏ
        else:
            last_kept = ps
    return out


def validate_parts(parts, clip_start: float, clip_end: float,
                   min_part: float = 1.5,
                   sentences: Optional[list] = None,
                   limit_changes: bool = True,
                   raw_parts=None) -> list[dict]:
    """Chuẩn hoá kịch bản LLM trả về -> list part SẠCH phủ kín clip.

    Tự sửa mọi lỗi thường gặp:
      - part không phải dict / start-end không phải số / dài < min_part -> BỎ.
      - mode lạ -> "orig"; narrate mà không có text (rỗng) -> "orig".
      - narrate mà text CHÉP NGUYÊN VĂN transcript (AI lười copy) HOẶC trùng
        transcript trong khoảng part ĐÓ + câu KỀ (±_COPY_WIN_PAD) — bắt cả
        kiểu KỂ LẠI đổi đại từ/thì/đảo trật tự (order-independent, chuẩn hoá
        đại từ ngôi) qua _is_copy_narrate -> "orig" (giữ tiếng gốc còn hơn AI
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
                and _is_copy_narrate(text, sentences, s, e)):
            mode, text = "orig", ""    # kể lại / trùng cao -> giữ tiếng gốc
        # LƯU LỜI GỐC HỢP LỆ của part orig LLM trả kèm text (_otext): nếu
        # _fix_structure phải hạ bớt cú bung tiếng gốc thừa, part có lời
        # sạch (qua ĐỦ 3 lưới anti-copy) được chuyển narrate thay vì gộp.
        # Narrate bị anti-copy hạ orig thì KHÔNG được phục hồi (text bẩn).
        otext = ""
        orig_text = str(p.get("text") or "").strip()
        if (mode == "orig" and not was_narrate and orig_text
                and not _is_transcript_copy(orig_text, transcript_norm)
                and not (sentences and _is_copy_narrate(
                    orig_text, sentences, s, e))):
            otext = orig_text
        # NHÃN TIẾNG ĐỘNG (sfx) AI gắn cho part -> giữ qua validate (sanitize +
        # ép mật độ ở cuối). Nhãn lạ/thiếu -> "none".
        raw_sfx = str(p.get("sfx") or "").strip().lower()
        sfx = raw_sfx if raw_sfx in _SFX_LABEL_SET else "none"
        clean.append({"start": round(s, 2), "end": round(e, 2),
                      "mode": mode, "text": text if mode == "narrate" else "",
                      "_otext": otext, "sfx": sfx})

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
    # 🔊 TÁI GẮN NHÃN SFX: sau reshape (gộp/tách/đổi mode) key sfx dễ rớt/lệch
    # mốc -> gắn lại từ nhãn THÔ của LLM theo start GẦN NHẤT + ÉP MẬT ĐỘ (tối
    # đa 1 tiếng / _SFX_MIN_GAP_S giây). raw_parts=None -> dùng chính parts vào.
    merged = _apply_sfx_labels(
        merged, _raw_sfx_labels(raw_parts if raw_parts is not None else parts))
    return merged


def narrate_ratio(parts: list[dict]) -> float:
    """Tỉ lệ thời lượng narrate / tổng (0..1) — để log/kiểm tra."""
    total = sum(p["end"] - p["start"] for p in parts) or 1.0
    nar = sum(p["end"] - p["start"] for p in parts if p["mode"] == "narrate")
    return nar / total


# Dung sai ÉP CỨNG tỉ lệ AI kể: tổng narrate được vượt ratio user chọn tối
# đa chừng này ĐIỂM % (LLM canh giây không bao giờ khít tuyệt đối); vượt
# hơn -> enforce_narrate_ratio CẮT bớt part kể (sửa lỗi user 'AI nói ~80%
# dù chọn ít' — prompt xin thôi chưa đủ, phải ép sau validate).
_RATIO_TOL_PCT = 12.0
# Sau khi cắt vẫn giữ TỐI THIỂU chừng này part narrate (hook + 1) — clip
# thuyết minh mà 0-1 part kể thì mất chất recap.
_RATIO_MIN_NARR = 2


def enforce_narrate_ratio(parts: list[dict], ratio: float,
                          tol: float = _RATIO_TOL_PCT,
                          min_keep: int = _RATIO_MIN_NARR) -> list[dict]:
    """ÉP CỨNG tỉ lệ AI kể SAU validate: tổng thời lượng narrate vượt
    `ratio` + `tol` (điểm %) -> CHUYỂN dần các part narrate ÍT QUAN TRỌNG
    NHẤT thành orig (trả tiếng gốc về) đến khi lọt trần:

      - LUÔN GIỮ part narrate ĐẦU (hook) + part narrate CUỐI (chốt).
      - Ưu tiên bỏ part narrate Ở GIỮA DÀI NHẤT trước (part dài = chiếm
        nhiều thời lượng nhất, bỏ 1 phát hạ ratio nhanh nhất).
      - Dừng khi <= trần HOẶC chỉ còn `min_keep` part narrate (mặc định 2:
        hook + 1) — thà hơi vượt trần còn hơn clip mất hết lời kể.

    Trả list part mới (orig kề nhau đã gộp), KHÔNG sửa list vào. Parts có
    <= min_keep part narrate -> trả nguyên (chỉ copy). Hàm thuần — unit
    test được."""
    out = [dict(p) for p in parts or []]
    total = sum(_part_dur(p) for p in out)
    if total <= 0:
        return out
    try:
        limit = (max(0.0, min(100.0, float(ratio))) + float(tol)) / 100.0
    except (TypeError, ValueError):
        limit = (30.0 + _RATIO_TOL_PCT) / 100.0

    try:
        target = max(0.0, min(100.0, float(ratio))) / 100.0
    except (TypeError, ValueError):
        target = 0.45

    def _narr_idx() -> list:
        return [i for i, p in enumerate(out) if p["mode"] == "narrate"]

    # CHỌN HÀNH ĐỘNG đưa tỉ lệ GẦN mục tiêu (`target`) NHẤT — KHÔNG bỏ đoạn
    # nếu bỏ xong lệch target XA HƠN giữ nguyên (tránh "cắt trụi": clip chỉ
    # có hook + 1 đoạn giữa + chốt, bỏ đoạn giữa hụt sâu dưới target thì thà
    # giữ hơi vượt trần). Chỉ bỏ ĐOẠN GIỮA, giữ hook + chốt, >= min_keep.
    while True:
        idx = _narr_idx()
        cur = sum(_part_dur(out[i]) for i in idx) / total
        if cur <= limit or len(idx) <= max(1, int(min_keep)):
            break
        middle = idx[1:-1]              # giữ hook (đầu) + chốt (cuối)
        if not middle:
            break
        # thử bỏ TỪNG đoạn giữa -> tỉ lệ còn lại; chọn cái đưa về gần target
        # nhất; nếu không cái nào tốt hơn hiện tại -> dừng (giữ nguyên).
        cur_dur = sum(_part_dur(out[j]) for j in idx)
        best, best_gap = None, abs(cur - target)
        for i in middle:
            after = (cur_dur - _part_dur(out[i])) / total
            gap = abs(after - target)
            if gap < best_gap - 1e-9:
                best, best_gap = i, gap
        if best is None:
            break
        out[best] = dict(out[best], mode="orig", text="")
    return _merge_orig_adjacent(out)


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
# 🔇 CỨU KỊCH BẢN "CÂM" — LỖI THẬT (thấy với TIẾNG HÀN trên llama-3.3/groq):
# prompt đạo diễn ĐẦY ĐỦ làm model trả CẤU TRÚC đúng (windows/parts chuẩn
# schema) nhưng bỏ TRỐNG MỌI chuỗi ("title": "", mọi "text": "") — retry
# kèm chỉ trích / đổi cách ép ngôn ngữ đều KHÔNG chữa được (đã đo A/B).
# Trong khi đó prompt NGẮN GỌN xin lời kể thì model viết tiếng Hàn bình
# thường. => Khi phát hiện kịch bản câm: gọi 1 PASS PHỤ prompt TỐI GIẢN
# chỉ xin lời kể cho TỪNG slot narrate rỗng, điền vào rồi validate lại
# (anti-copy/relevance/ngôn ngữ vẫn soi đủ ở tầng validate — KHÔNG nới).
# Bounded: đúng 1 lệnh gọi LLM mỗi lần cứu; lỗi -> trả None (fallback cũ).
# ------------------------------------------------------------------
def _bad_narrate_slots(parts_list: list, sentences: list) -> list:
    """[(index, part)] các part narrate CẦN VIẾT LẠI: text RỖNG (kịch bản
    câm) HOẶC text CHÉP/KỂ LẠI transcript (sẽ bị anti-copy hạ orig — lỗi
    thật với TIẾNG Ả RẬP: llama lười, dán nguyên câu transcript làm lời
    kể). Hàm thuần — dùng đúng các lưới anti-copy của validate."""
    tn = " ".join(_norm_for_copy(t) for _a, _b, t in (sentences or []) if t)
    out = []
    for i, p in enumerate(parts_list):
        if str(p.get("mode") or "").strip().lower() != "narrate":
            continue
        t = str(p.get("text") or "").strip()
        if not t:
            out.append((i, p))
            continue
        try:
            s, e = float(p.get("start")), float(p.get("end"))
        except (TypeError, ValueError):
            continue
        if _is_transcript_copy(t, tn) or (
                sentences and _is_copy_narrate(t, sentences, s, e)):
            out.append((i, p))
    return out


def _fill_mute_narrates(data, sentences: list, lang_name: str,
                        listing: str = ""):
    """PASS PHỤ viết lời cho các part narrate HỎNG (text rỗng — kịch bản
    câm; hoặc text chép/kể lại transcript — sẽ bị anti-copy gut): prompt
    TỐI GIẢN (không khối ép ngôn ngữ dài — chính prompt dài làm model câm)
    xin lời kể đúng ngôn ngữ cho từng slot. Lời mới vẫn qua ĐỦ các lưới
    anti-copy/relevance ở validate sau đó — KHÔNG nới lỏng. Trả data MỚI
    (copy, parts đã điền + title nếu thiếu); None nếu gọi LLM lỗi / không
    điền được slot nào."""
    if not isinstance(data, dict):
        return None
    ps = _coerce_parts(data.get("parts"))
    slots = _bad_narrate_slots(ps, sentences)
    if not slots:
        return None
    if not listing:
        listing = "\n".join(f"{a:.1f} {b:.1f} | {t}"
                            for a, b, t in (sentences or []))[:11000]
    ln = str(lang_name or "").strip() \
        or "the original spoken language of the video"
    lines = []
    for i, p in slots:
        try:
            s, e = float(p.get("start")), float(p.get("end"))
        except (TypeError, ValueError):
            continue
        lines.append(f"- slot {i}: giây {s:.1f} -> {e:.1f} "
                     f"(~{max(4, int((e - s) * 2.1))} từ)")
    if not lines:
        return None
    prompt = (
        f"Transcript video nói bằng {ln} (mỗi dòng: BẮT_ĐẦU KẾT_THÚC | lời "
        f"nói):\n{listing}\n\n"
        f"Bạn là người kể chuyện đứng NGOÀI video. Viết lời kể bằng {ln} "
        "cho từng slot dưới đây (slot = khoảng thời gian trên video): 1-2 "
        "câu NGẮN, bình luận/cảm xúc/câu hỏi về chuyện quanh mốc đó, KHÔNG "
        "chép nguyên văn transcript, KHÔNG thuật lại lời nhân vật.\n"
        + "\n".join(lines) + "\n\n"
        f'Trả về DUY NHẤT JSON: {{"title": "tiêu đề {ln} giật tít", '
        f'"texts": {{"<số slot>": "lời kể {ln}"}}}} — đủ MỌI slot, '
        "text KHÔNG rỗng.")
    try:
        d2 = llm.complete_json(prompt, system=_SYSTEM)
    except llm.LLMError:
        return None
    texts = d2.get("texts") if isinstance(d2, dict) else None
    if not isinstance(texts, dict):
        return None
    filled = 0
    for i, p in slots:
        t = str(texts.get(str(i)) or texts.get(i) or "").strip()
        if t:
            p["text"] = t
            filled += 1
    if not filled:
        return None
    out = dict(data, parts=ps)
    if not str(out.get("title") or "").strip() and isinstance(d2, dict):
        out["title"] = str(d2.get("title") or "").strip()
    return out


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
                          emotion: bool = False,
                          win_auto: bool = False) -> str:
    """Prompt ĐẠO DIỄN: từ TOÀN BỘ transcript (đã rút gọn nếu dài), chọn
    các khung cảnh rời nhau + viết kịch bản parts có CẦU NỐI giữa các khung.
    ratio 15-80 (mặc định 30); <= 40 -> KHUÔN LOW-RATIO (AI nói ít, nhanh
    gọn, video gốc là chính — _structure_rules).

    win_auto=True (m2_recap GIỜ LUÔN dùng — số cảnh do AI tự quyết, đã bỏ
    hẳn phần "Cắt ghép" trong ⚙ Cài đặt Reup): bỏ khung gò cứng win_min-
    win_max, thay bằng chỉ dẫn TỰ chọn số cảnh hợp lý theo nội dung (thường
    2-6), ưu tiên mạch chuyện hay. win_auto=False (giữ cho tương thích/test):
    ép chọn win_min-win_max khung."""
    ln = lang_name.upper()
    try:
        pct = int(round(max(15.0, min(80.0, float(ratio)))))
    except (TypeError, ValueError):
        pct = 30
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
        + ("- TỰ CHỌN số khung cảnh hợp lý theo nội dung (thường 2-6 khung) "
           "— ưu tiên MẠCH CHUYỆN hay, KHÔNG gò cứng số lượng: chuyện cần "
           "ít cảnh thì ít, cần nhiều thì nhiều. Các khung RỜI NHAU bám "
           "mạch: mở đầu -> diễn biến -> twist/cao trào -> kết. ĐÚNG thứ tự "
           "thời gian, KHÔNG chồng lấn, KHÔNG đảo đoạn.\n"
           if win_auto else
           f"- Chọn {w_lo}-{w_hi} khung cảnh RỜI NHAU bám mạch chuyện: mở "
           "đầu -> diễn biến -> twist/cao trào -> kết. ĐÚNG thứ tự thời "
           "gian, KHÔNG chồng lấn, KHÔNG đảo đoạn.\n")
        + f"- Mỗi khung dài 8-40 giây; TỔNG các khung trong khoảng "
        f"{min_total:.0f}-{max_total:.0f} giây.\n"
        "- RẢI ĐỀU + ĐA DẠNG: các khung phủ ĐẦU / GIỮA / CUỐI mạch chuyện, "
        "nội dung KHÁC NHAU — ĐỪNG dồn nhiều khung vào cùng 1 cảnh/1 chỗ hay "
        "lặp lại cùng chủ đề.\n"
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
        + _structure_rules(per_window=True, ratio=pct) +
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
        + _ratio_rule(pct) +
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
        + _sfx_rule()
        + _lang_remind(ln) +
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"context_summary": "...", "title": "...", '
        '"windows": [[giây_bắt_đầu, giây_kết_thúc], ...], '
        '"parts": [{"start": giây, "end": giây, "mode": "orig"|"narrate", '
        '"text": "lời thuyết minh nếu narrate", "sfx": "none"|"transition"|'
        '"impact"|"riser"|"reveal"|"pop"|"suspense"|"comedy"|"scratch"|'
        '"sad"|"drumroll"}]}\n'
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
                # THA part ĐẦU của MỖI khung (j == 0): khung 1 -> HOOK, các
                # khung sau -> CẦU NỐI. Cả hai theo THIẾT KẾ là BÌNH LUẬN từ
                # ngoài (cảm xúc/twist/câu hỏi) nên có thể KHÔNG nhắc chi tiết
                # cảnh — relevance 0 là BÌNH THƯỜNG, KHÔNG phải lạc đề. Lỗi
                # thật: fix "bình luận đừng mô tả" làm hook sáng tác (vd "gã
                # này tưởng mình cẩn thận, nhưng...") bị relevance hạ orig ->
                # rụng hết narrate -> None -> fallback. Chỉ ép relevance các
                # part narrate GIỮA khung (không phải hook/cầu nối).
                if (mode == "narrate" and text.strip()
                        and not _is_relevant(text, near)
                        and j != 0):
                    # 0 từ-nội-dung LIÊN QUAN transcript khung (và khung kề;
                    # NỚI: chấp nhận biến thể/đồng nghĩa cùng gốc qua prefix)
                    # -> nghi LẠC ĐỀ/bịa -> hạ orig.
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


# ------------------------------------------------------------------
# 🔁 NHIỀU-PASS (v8): sau khi có kịch bản hợp lệ, AI TỰ CHẤM (critic) rồi
# VIẾT LẠI (refine) 1 bản tốt hơn. FAIL-SAFE tuyệt đối: pass mới lỗi / không
# validate / bị gut narrate -> QUAY VỀ bản nháp. Tối đa 1 critic + 1 refine
# (bounded, KHÔNG lặp). Bật/tắt bằng settings.AI_MULTIPASS.
# ------------------------------------------------------------------
_CRITIC_SYSTEM = (
    "Bạn là BIÊN TẬP VIÊN khó tính của kênh recap triệu view. Chấm kịch bản "
    "thuyết minh NGHIÊM KHẮC, chỉ ra điểm yếu CỤ THỂ. Trả DUY NHẤT 1 JSON "
    "object, không thêm chữ.")


def _script_draft_digest(result: dict) -> str:
    """Tóm tắt BẢN NHÁP cho critic đọc: title + từng part (mode, thời lượng,
    lời narrate). Ngắn gọn, không phá schema."""
    lines = [f"TIÊU ĐỀ: {result.get('title') or '(chưa có)'}"]
    for i, p in enumerate(result.get("parts") or []):
        try:
            dur = float(p.get("end", 0)) - float(p.get("start", 0))
        except (TypeError, ValueError):
            dur = 0.0
        mode = str(p.get("mode") or "orig")
        if mode == "narrate":
            lines.append(f"  [{i}] narrate {dur:.0f}s: {p.get('text') or ''}")
        else:
            lines.append(f"  [{i}] orig {dur:.0f}s (giữ tiếng gốc)")
    return "\n".join(lines)


# Ngưỡng độ dài listing (ký tự) tối đa còn bật nhiều-pass. Vượt -> 1-pass để
# tiết kiệm TOKEN/NGÀY Groq (critic+refine gửi lại prompt ~gấp 2-3 lần token).
_MULTIPASS_MAX_LISTING = 4000


def _refine_script(result: dict, sentences: list, lang_name: str, style: str,
                   min_total: float, max_total: float, duration: float,
                   win_max: int, emotion: bool, ratio: float,
                   listing: str = "", win_min: int = 3,
                   win_auto: bool = False) -> dict:
    """NHIỀU-PASS: 1 critic + 1 refine trên bản `result` ĐÃ validate. Trả bản
    REFINE chỉ khi nó validate OK VÀ giữ >= số narrate bản nháp; ngược lại
    (kể cả LLM lỗi / JSON hỏng / critic hỏng) -> trả NGUYÊN bản nháp. Bounded:
    tối đa 1 critic + 1 refine, KHÔNG lặp. Không bao giờ ném."""
    try:
        base_narr = sum(1 for p in result.get("parts") or []
                        if p.get("mode") == "narrate")
        if base_narr <= 0:
            return result              # nháp không có narrate -> khỏi refine
        if not listing:
            listing = "\n".join(f"{a:.1f} {b:.1f} | {t}"
                                for a, b, t in sentences)[:11000]
        base_prompt = build_director_prompt(
            listing, lang_name, style, duration, min_total, max_total,
            ratio=ratio, win_min=win_min, win_max=win_max, emotion=emotion,
            win_auto=win_auto)
        digest = _script_draft_digest(result)

        # ---- PASS 1: CHẤM (critic) ----
        fix, weak = "", []
        try:
            critic_prompt = (
                "BẢN NHÁP kịch bản thuyết minh (recap) cần chấm:\n"
                f"{digest}\n\n"
                "TÓM TẮT transcript video (mỗi dòng: giây | lời):\n"
                f"{listing[:4000]}\n\n"
                "CHẤM theo các tiêu chí (0-10 mỗi mục):\n"
                "- hook: câu narrate ĐẦU có giữ chân người xem ngay không.\n"
                "- emotion: sức nặng CẢM XÚC của lời kể.\n"
                "- originality: TÍNH NGUYÊN BẢN — người kể BÌNH LUẬN từ NGOÀI, "
                "KHÔNG thuật/chép lại lời nhân vật.\n"
                "- pacing: nhịp lời kể có KHỚP thời lượng từng part không.\n"
                f"- language: có viết ĐÚNG ngôn ngữ video ({lang_name}) không.\n"
                "- coherence: mạch truyện mở-thân-kết có mạch lạc không; SFX "
                "(nếu có) gắn hợp lý không.\n"
                'Trả DUY NHẤT 1 JSON: {"scores":{"hook":0-10,"emotion":0-10,'
                '"originality":0-10,"pacing":0-10,"language":0-10,'
                '"coherence":0-10},"total":0-60,"weak":["..."],'
                '"fix":"chỉ dẫn sửa cụ thể, ngắn gọn"}')
            crit = llm.complete_json(critic_prompt, system=_CRITIC_SYSTEM,
                                     provider=None)
            if isinstance(crit, dict):
                fix = str(crit.get("fix") or "").strip()
                w = crit.get("weak")
                if isinstance(w, list):
                    weak = [str(x).strip() for x in w if str(x).strip()]
        except (llm.LLMError, Exception):  # noqa: BLE001 - critic hỏng -> fix rỗng
            fix, weak = "", []

        # ---- PASS 2: VIẾT LẠI (refine) ----
        note = ""
        if fix or weak:
            note = "\n\nMỘT BIÊN TẬP VIÊN ĐÃ CHẤM VÀ CHỈ RA ĐIỂM YẾU:\n"
            if fix:
                note += fix + "\n"
            if weak:
                note += "Điểm yếu: " + "; ".join(weak[:6]) + "\n"
        import json as _json
        draft_json = _json.dumps(
            {"title": result.get("title", ""),
             "windows": result.get("windows") or [],
             "parts": result.get("parts") or []},
            ensure_ascii=False)
        refine_prompt = (
            base_prompt
            + "\n\nĐÂY LÀ BẢN NHÁP CỦA BẠN:\n" + draft_json
            + note
            + "\n\nHãy VIẾT LẠI 1 BẢN TỐT HƠN, sửa đúng các điểm yếu đó. "
            "GIỮ NGUYÊN schema, GIỮ cùng windows (cùng các cặp [start,end]), "
            f"GIỮ đúng ngôn ngữ ({lang_name.upper()}). Trả DUY NHẤT 1 JSON "
            "object.")
        try:
            d2 = llm.complete_json(refine_prompt, system=_SYSTEM)
        except (llm.LLMError, Exception):  # noqa: BLE001
            return result
        r2, _e2 = _director_from_data(d2, sentences, duration,
                                      min_total, max_total, win_max)
        r2 = _enforce_script_lang(r2, lang_name, lambda: None)
        if not r2:
            return result              # refine không validate -> giữ nháp
        new_narr = sum(1 for p in r2.get("parts") or []
                       if p.get("mode") == "narrate")
        if new_narr < base_narr:
            return result              # refine bị gut narrate -> giữ nháp
        return r2
    except Exception:  # noqa: BLE001 - bất kỳ lỗi nào -> fail-safe giữ nháp
        return result


def write_director_script(sentences: list, lang_name: str, style: str,
                          duration: float, min_total: float,
                          max_total: float, ratio: float = 55,
                          listing: str = "", win_min: int = 3,
                          win_max: int = 6,
                          emotion: bool = False,
                          win_auto: bool = False) -> Optional[dict]:
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
    win_auto=True (mặc định ⚙): AI TỰ chọn số cảnh — prompt bỏ khung gò
    cứng, validate dùng bound rộng (caller truyền max_n rộng).
    Ném llm.LLMError nếu gọi LLM thất bại vì mạng/key (caller quyết
    fallback); lỗi PARSE JSON thì tự retry chứ không ném."""
    if not listing:
        listing = "\n".join(f"{a:.1f} {b:.1f} | {t}"
                            for a, b, t in sentences)[:11000]
    prompt = build_director_prompt(listing, lang_name, style, duration,
                                   min_total, max_total, ratio=ratio,
                                   win_min=win_min, win_max=win_max,
                                   emotion=emotion, win_auto=win_auto)

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

    def _maybe_refine(res):
        """NHIỀU-PASS trên kịch bản HỢP LỆ (res != None). Tắt cờ / None ->
        trả nguyên (caller fallback như cũ). Fail-safe: _refine_script tự
        quay về bản nháp nếu pass mới lỗi/tệ hơn."""
        if not res:
            return res
        try:
            from config import settings as _st
            if not getattr(_st, "AI_MULTIPASS", True):
                return res
        except Exception:  # noqa: BLE001 - config lỗi -> giữ bản cũ, khỏi refine
            return res
        # 💸 TIẾT KIỆM TOKEN/NGÀY: nhiều-pass (critic+refine) gửi lại prompt +
        # transcript -> gấp ~2-3 lần token. Với transcript DÀI (video dài/chương
        # lớn) dễ chạm HẠN MỨC TOKEN/NGÀY của Groq (per-day). Chỉ bật nhiều-pass
        # khi listing đủ NGẮN; video dài -> 1-pass (chất lượng vẫn tốt) để reup
        # CHẠY XONG thay vì hết lượt ngày giữa chừng.
        if len(listing or "") > _MULTIPASS_MAX_LISTING:
            return res
        return _refine_script(res, sentences, lang_name, style, min_total,
                              max_total, duration, win_max, emotion, ratio,
                              listing=listing, win_min=win_min,
                              win_auto=win_auto)

    result, err, data = None, "", None
    try:
        data = llm.complete_json(prompt, system=_SYSTEM)
        result, err = _director_from_data(data, sentences, duration,
                                          min_total, max_total, win_max)
    except llm.LLMError as e:
        if "không phải JSON" not in str(e):
            raise                       # lỗi mạng/key/quota -> caller quyết
        err = ("kết quả không phải JSON hợp lệ — trả DUY NHẤT 1 JSON object "
               "đúng schema, không thêm chữ/markdown")
    # ---- CỨU KỊCH BẢN parts HỎNG vì narrate CÂM (mọi text rỗng — lỗi thật
    # llama+tiếng Hàn) hoặc narrate CHÉP transcript bị anti-copy gut SẠCH
    # (lỗi thật llama+tiếng Ả Rập) -> 1 pass phụ viết lời rồi validate lại
    # (lưới anti-copy vẫn soi đủ trên lời mới — không nới) ----
    if result is None and '"parts"' in (err or "") and isinstance(data, dict):
        d_fill = _fill_mute_narrates(data, sentences, lang_name,
                                     listing=listing)
        if d_fill:
            result, err = _director_from_data(d_fill, sentences, duration,
                                              min_total, max_total, win_max)
            if result:
                data = d_fill
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
                return _maybe_refine(
                    _enforce_script_lang(r2, lang_name, _lang_retry))
            # retry vẫn lười chép -> PASS PHỤ viết lại các narrate bị bắt
            # chép (prompt tối giản, lời mới vẫn qua đủ lưới anti-copy)
            d_rw = _fill_mute_narrates(data, sentences, lang_name,
                                       listing=listing)
            if d_rw:
                r3, _e3 = _director_from_data(d_rw, sentences, duration,
                                              min_total, max_total, win_max)
                if r3 and sum(1 for p in r3["parts"]
                              if p["mode"] == "narrate") > kept:
                    return _maybe_refine(
                        _enforce_script_lang(r3, lang_name, _lang_retry))
        return _maybe_refine(
            _enforce_script_lang(result, lang_name, _lang_retry))
    # ---- RETRY SỬA LỖI (1 lần): nói rõ lỗi để model tự sửa ----
    # LỖI THẬT (explainer): LLM viết narrate KỂ LẠI lời nhân vật -> anti-copy
    # hạ HẾT về orig -> _director_from_data trả None (err "parts hỏng"). Retry
    # generic không đủ mạnh; đính THÊM _RETELL_RETRY_NOTE (bảo BÌNH LUẬN từ
    # ngoài, đừng mô tả lại việc trên màn hình) để model sửa đúng gốc.
    retell_hint = ("\n\n" + _RETELL_RETRY_NOTE) if "parts" in (err or "") else ""
    retry_prompt = (
        prompt + "\n\nLẦN TRƯỚC bạn đã trả kết quả KHÔNG DÙNG ĐƯỢC — lỗi: "
        + err + ".\nHãy SỬA ĐÚNG lỗi đó và trả lại DUY NHẤT 1 JSON object "
        "đúng schema yêu cầu ở trên, không thêm chữ nào khác." + retell_hint)
    try:
        data = llm.complete_json(retry_prompt, system=_SYSTEM)
    except llm.LLMError:
        return None                     # retry vẫn hỏng -> caller fallback
    result, _err = _director_from_data(data, sentences, duration,
                                       min_total, max_total, win_max)
    # retry vẫn hỏng parts (câm/chép bị gut) -> cứu bằng pass phụ viết lời
    if result is None and '"parts"' in (_err or "") and isinstance(data, dict):
        d_fill = _fill_mute_narrates(data, sentences, lang_name,
                                     listing=listing)
        if d_fill:
            result, _err = _director_from_data(d_fill, sentences, duration,
                                               min_total, max_total, win_max)
    return _maybe_refine(_enforce_script_lang(result, lang_name, _lang_retry))


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
    ratio = % thời lượng AI kể user chọn (15-80, mặc định 30; <= 40 ->
    prompt dùng khuôn LOW-RATIO — AI nói ít, nhanh gọn).
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
