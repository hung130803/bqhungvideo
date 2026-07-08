"""
LLM "ĐẠO DIỄN" cho tính năng 🎙 Reup thuyết minh (recap).

Nhiệm vụ: từ transcript CỦA 1 CLIP (các câu start/end/text trong phạm vi clip),
viết KỊCH BẢN chia clip thành các PART xen kẽ:
  - mode "orig"    : GIỮ TIẾNG GỐC (khoảnh khắc đắt — thoại hay, cao trào).
  - mode "narrate" : TẮT TIẾNG GỐC, giọng AI THUYẾT MINH (kể/dẫn/bình) về nội
                     dung đang diễn ra — viết bằng ĐÚNG NGÔN NGỮ video.

Prompt viết theo CÔNG THỨC VIRAL: part ĐẦU TIÊN bắt buộc là narrate HOOK
gây sốc/tò mò (2-3 giây đầu quyết định giữ chân), mạch chuyện mini story-arc
(hook -> bối cảnh -> căng thẳng -> twist -> kết mở), câu ngắn dồn dập, cấm
kể lại y nguyên cái người xem tự thấy. Nếu có ẢNH khung hình (vision), AI
phải viết lời BÁM đúng cảnh đang chiếu.

Output JSON: {"title": "...", "parts": [{"start": s, "end": e,
              "mode": "orig"|"narrate", "text": "..."}]}
Các part PHỦ KÍN [clip_start, clip_end] theo thứ tự thời gian.

validate_parts() là hàm THUẦN (không LLM) tự sửa output hỏng: clamp vào phạm
vi clip, bỏ part rác, mode lạ -> orig, chồng lấn -> cắt, khoảng hở -> chèn
part orig, narrate rỗng/COPY nguyên văn transcript -> orig. Có unit-test riêng.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from app.ai import llm

# 4 phong cách thuyết minh (key lưu QSettings/preset -> hint đưa vào prompt).
# Mỗi phong cách có MÔ TẢ CÁCH VIẾT riêng rõ rệt (đưa nguyên văn vào prompt).
STYLES = {
    "story": (
        "Kể chuyện",
        "PHONG CÁCH KỂ CHUYỆN — viết như đang kể cho ĐỨA BẠN THÂN nghe:\n"
        "  + Câu NGẮN, dồn dập, nhịp nhanh. Kiểu: \"Gã này tưởng ngon ăn. "
        "Sai lầm. Sai lầm lớn nhất đời gã.\"\n"
        "  + Gọi nhân vật bằng biệt danh đời thường (gã này, bà chị, ông chú, "
        "cậu nhóc) — KHÔNG gọi trung tính kiểu 'người đàn ông'.\n"
        "  + Cuối mỗi đoạn narrate cài 1 móc tò mò: chuyện gì xảy ra tiếp?"),
    "clickbait": (
        "Giật gân câu view",
        "PHONG CÁCH GIẬT GÂN — cường điệu + câu hỏi treo LIÊN TỤC:\n"
        "  + Mở bằng cú sốc: \"Đây có thể là quyết định tệ nhất đời anh ta.\"\n"
        "  + Liên tục đặt câu hỏi treo: \"Nhưng khoan. Bạn chưa thấy gì đâu.\" "
        "\"Điều xảy ra tiếp theo không ai ngờ.\"\n"
        "  + Phóng đại có kiểm soát: nhất/chưa từng/không tưởng — nhưng KHÔNG "
        "bịa chi tiết sai với video."),
    "funny": (
        "Hài hước",
        "PHONG CÁCH HÀI HƯỚC — mỉa nhẹ + nhân cách hóa, KHÔNG giải thích joke:\n"
        "  + Bình luận như đang cà khịa bạn mình: chọc vào cái ngớ ngẩn, "
        "tương phản, sự tự tin lố của nhân vật.\n"
        "  + Nhân cách hóa đồ vật/con vật (con mèo khinh thường ra mặt, "
        "cái ghế quyết định phản chủ).\n"
        "  + Thả joke rồi ĐI TIẾP luôn — tuyệt đối không giải thích vì sao "
        "nó buồn cười."),
    "analysis": (
        "Phân tích sâu",
        "PHONG CÁCH PHÂN TÍCH — mổ xẻ 'VÌ SAO' với giọng tự tin, sắc lạnh:\n"
        "  + Chỉ ra cái người xem KHÔNG tự nhận ra: \"Để ý tay trái anh ta. "
        "Đó không phải ngẫu nhiên.\"\n"
        "  + Khẳng định chắc nịch rồi chứng minh bằng chi tiết trong video, "
        "không vòng vo 'có lẽ/hình như'.\n"
        "  + Chốt mỗi ý bằng 1 câu đắt: bài học/ý nghĩa đằng sau."),
}
DEFAULT_STYLE = "story"

_SYSTEM = (
    "Bạn là ĐẠO DIỄN kịch bản viral cho kênh reup-thuyết-minh (recap) video "
    "ngắn TikTok/Reels. Bạn chia clip thành các đoạn XEN KẼ: đoạn GIỮ TIẾNG "
    "GỐC (khoảnh khắc đắt nhất) và đoạn AI THUYẾT MINH (video tắt tiếng, "
    "giọng AI kể/dẫn/bình về CẢNH ĐANG CHIẾU). 2-3 giây đầu quyết định người "
    "xem ở lại hay lướt — câu mở phải gây sốc/tò mò tức thì. "
    "CHỈ trả JSON thuần, không thêm chữ nào khác.")

# Tốc độ đọc TTS để AI canh độ dài lời thuyết minh (ghi thẳng vào prompt)
_RATE_HINT = ("Tốc độ giọng đọc AI: tiếng Anh ~2.3 từ/giây, tiếng Việt ~3.5 "
              "âm tiết/giây (ngôn ngữ khác tương đương ~2.5 từ/giây).")


def style_label(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[0]


def _style_hint(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[1]


def build_prompt(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float, title: str = "",
                 frames: Optional[list] = None) -> str:
    """sentences = [(start, end, text)] các câu transcript TRONG clip.
    frames = [(giây, đường_dẫn_ảnh)] khung hình gửi kèm (vision) — ảnh #k
    chụp tại mốc giây tương ứng; None/rỗng = không có vision."""
    lines = "\n".join(f"{a:.1f} {b:.1f} | {t}" for a, b, t in sentences)[:6000]
    dur = clip_end - clip_start
    ln = lang_name.upper()

    # ---- NGỮ CẢNH THỊ GIÁC: có ảnh -> dặn bám cảnh; không -> bám transcript ----
    if frames:
        vis = (
            "NGỮ CẢNH HÌNH ẢNH: kèm theo là "
            f"{len(frames)} ẢNH khung hình chụp từ chính clip, theo thứ tự: "
            + "; ".join(f"ảnh #{i} tại giây {t:.0f}"
                        for i, (t, _p) in enumerate(frames)) + ".\n"
            "- HÃY NHÌN KỸ từng ảnh để hiểu cảnh gì đang chiếu tại mốc đó "
            "(ai, làm gì, bối cảnh, biểu cảm).\n"
            "- Lời narrate của part nào phải BÁM VÀO cảnh đang chiếu trong "
            "khoảng thời gian part đó (đối chiếu ảnh gần mốc nhất + "
            "transcript).\n")
    else:
        vis = (
            "KHÔNG có ảnh kèm theo — ngữ cảnh duy nhất là transcript có mốc "
            "thời gian ở trên:\n"
            "- Lời narrate của part [start-end] phải nói về ĐÚNG nội dung các "
            "câu transcript trong khoảng [start-end] ĐÓ.\n")
    vis += ("- CẤM SPOILER: không nhắc trước nội dung của đoạn CHƯA chiếu tới "
            "(twist chỉ được hé khi video chiếu tới nó) — chỉ được GỢI tò mò.\n")

    return (
        f"CLIP từ giây {clip_start:.1f} đến {clip_end:.1f} (dài {dur:.0f}s) "
        f"của một video nói bằng {ln}."
        + (f' Tiêu đề gợi ý: "{title}".' if title else "") + "\n"
        "Transcript trong clip (mỗi dòng: bắt_đầu kết_thúc | lời nói):\n"
        f"{lines}\n\n"
        f"{vis}\n"
        f"Hãy viết KỊCH BẢN THUYẾT MINH VIRAL kiểu kênh recap.\n"
        f"{_style_hint(style)}\n\n"
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
        "4) VĂN PHONG: câu NGẮN (tối đa 12 từ/câu), chủ động, cấm từ thừa "
        "(rằng, thì, là, việc, một cách...). CẤM tả lại y nguyên cái người "
        "xem tự thấy trên hình — mỗi câu phải THÊM thông tin, cảm xúc hoặc "
        "góc nhìn mới. CẤM chép lại nguyên văn lời thoại transcript vào "
        "narrate (đoạn đó hãy để orig).\n\n"
        "QUY TẮC KỸ THUẬT:\n"
        f"- Chia CLIP thành các part PHỦ KÍN từ {clip_start:.1f}s đến "
        f"{clip_end:.1f}s, theo ĐÚNG thứ tự thời gian, KHÔNG chồng lấn, "
        "KHÔNG hở, KHÔNG đảo đoạn.\n"
        "- Mỗi part dài 3-15 giây. mode = \"orig\" hoặc \"narrate\".\n"
        "- start/end của MỖI part phải trùng mép câu transcript (không cắt "
        "ngang giữa câu nói).\n"
        "- Tổng thời lượng narrate chiếm 40-70% clip; XEN KẼ với orig cho "
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


def validate_parts(parts, clip_start: float, clip_end: float,
                   min_part: float = 1.5,
                   sentences: Optional[list] = None) -> list[dict]:
    """Chuẩn hoá kịch bản LLM trả về -> list part SẠCH phủ kín clip.

    Tự sửa mọi lỗi thường gặp:
      - part không phải dict / start-end không phải số / dài < min_part -> BỎ.
      - mode lạ -> "orig"; narrate mà không có text (rỗng) -> "orig".
      - narrate mà text CHÉP NGUYÊN VĂN transcript (AI lười copy) -> "orig"
        (đoạn đó giữ tiếng gốc còn hơn AI đọc lại y hệt). Cần `sentences`
        = [(start, end, text)] transcript trong clip để so.
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


def write_script(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float,
                 title: str = "",
                 frames: Optional[list] = None) -> Optional[dict]:
    """Gọi LLM viết kịch bản 1 clip -> {"title","parts"} ĐÃ VALIDATE.

    sentences = [(start, end, text)] câu transcript trong phạm vi clip.
    frames = [(giây, đường_dẫn_ảnh)] khung hình gửi kèm (chỉ khi caller đã
    kiểm llm.vision_available()) — AI NHÌN cảnh để viết lời bám hình; lỗi
    vision -> tự lùi về prompt chữ thuần (không vỡ luồng).
    Ném llm.LLMError nếu gọi LLM thất bại (caller quyết fail/skip).
    Trả None nếu LLM trả JSON không dùng được (không có part narrate nào).
    """
    prompt = build_prompt(sentences, lang_name, style, clip_start, clip_end,
                          title, frames=frames)
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
                                  clip_start, clip_end, title)
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
