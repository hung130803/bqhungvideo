"""
LLM "ĐẠO DIỄN" cho tính năng 🎙 Reup thuyết minh (recap).

Nhiệm vụ: từ transcript CỦA 1 CLIP (các câu start/end/text trong phạm vi clip),
viết KỊCH BẢN chia clip thành các PART xen kẽ:
  - mode "orig"    : GIỮ TIẾNG GỐC (khoảnh khắc đắt — thoại hay, cao trào).
  - mode "narrate" : TẮT TIẾNG GỐC, giọng AI THUYẾT MINH (kể/dẫn/bình) về nội
                     dung đang diễn ra — viết bằng ĐÚNG NGÔN NGỮ video.

Output JSON: {"title": "...", "parts": [{"start": s, "end": e,
              "mode": "orig"|"narrate", "text": "..."}]}
Các part PHỦ KÍN [clip_start, clip_end] theo thứ tự thời gian.

validate_parts() là hàm THUẦN (không LLM) tự sửa output hỏng: clamp vào phạm
vi clip, bỏ part rác, mode lạ -> orig, chồng lấn -> cắt, khoảng hở -> chèn
part orig. Có unit-test riêng.
"""
from __future__ import annotations

from typing import Optional

from app.ai import llm

# 4 phong cách thuyết minh (key lưu QSettings/preset -> hint đưa vào prompt)
STYLES = {
    "story": ("Kể chuyện",
              "Giọng KỂ CHUYỆN cuốn hút như kênh recap phim: dẫn dắt mạch "
              "truyện, gợi tò mò chuyện gì xảy ra tiếp theo."),
    "clickbait": ("Giật gân câu view",
                  "Giọng GIẬT GÂN câu view: cường điệu, đặt câu hỏi sốc, "
                  "nhấn mạnh chi tiết khó tin để giữ chân người xem."),
    "funny": ("Hài hước",
              "Giọng HÀI HƯỚC: bình luận dí dỏm, chọc vui nhân vật/tình "
              "huống, ví von bất ngờ."),
    "analysis": ("Phân tích sâu",
                 "Giọng PHÂN TÍCH SÂU: mổ xẻ vì sao nhân vật làm vậy, ý "
                 "nghĩa/bài học đằng sau, bình tĩnh và sắc sảo."),
}
DEFAULT_STYLE = "story"

_SYSTEM = (
    "Bạn là ĐẠO DIỄN kịch bản cho kênh reup-thuyết-minh (recap) video ngắn. "
    "Bạn chia clip thành các đoạn XEN KẼ: đoạn GIỮ TIẾNG GỐC (khoảnh khắc "
    "đắt nhất) và đoạn AI THUYẾT MINH (video tắt tiếng, giọng AI kể/dẫn/bình "
    "về nội dung đang diễn ra). CHỈ trả JSON thuần, không thêm chữ nào khác.")

# Tốc độ đọc TTS để AI canh độ dài lời thuyết minh (ghi thẳng vào prompt)
_RATE_HINT = ("Tốc độ giọng đọc AI: tiếng Anh ~2.3 từ/giây, tiếng Việt ~3.5 "
              "âm tiết/giây (ngôn ngữ khác tương đương ~2.5 từ/giây).")


def style_label(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[0]


def _style_hint(key: str) -> str:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])[1]


def build_prompt(sentences: list, lang_name: str, style: str,
                 clip_start: float, clip_end: float, title: str = "") -> str:
    """sentences = [(start, end, text)] các câu transcript TRONG clip."""
    lines = "\n".join(f"{a:.1f} {b:.1f} | {t}" for a, b, t in sentences)[:6000]
    dur = clip_end - clip_start
    return (
        f"CLIP từ giây {clip_start:.1f} đến {clip_end:.1f} (dài {dur:.0f}s) "
        f"của một video nói bằng {lang_name.upper()}."
        + (f' Tiêu đề gợi ý: "{title}".' if title else "") + "\n"
        "Transcript trong clip (mỗi dòng: bắt_đầu kết_thúc | lời nói):\n"
        f"{lines}\n\n"
        f"Hãy viết KỊCH BẢN THUYẾT MINH kiểu kênh recap. Phong cách: "
        f"{_style_hint(style)}\n"
        "QUY TẮC:\n"
        f"- Chia CLIP thành các part PHỦ KÍN từ {clip_start:.1f}s đến "
        f"{clip_end:.1f}s, theo thứ tự thời gian, KHÔNG chồng lấn, KHÔNG hở.\n"
        "- Mỗi part dài 3-15 giây. mode = \"orig\" (giữ tiếng gốc — chọn "
        "khoảnh khắc thoại ĐẮT nhất, cao trào, câu chốt) hoặc \"narrate\" "
        "(giọng AI thuyết minh, video tắt tiếng).\n"
        "- Tổng thời lượng các part narrate chiếm 40-70% clip; XEN KẼ với "
        "orig cho nhịp nhàng (mở đầu nên là narrate dẫn dắt).\n"
        f"- text của part narrate: viết BẰNG {lang_name.upper()} (ĐÚNG ngôn "
        "ngữ video), văn NÓI tự nhiên; kể/dẫn/bình về những gì đang diễn ra "
        "trong khoảng thời gian đó.\n"
        f"- {_RATE_HINT} HÃY ĐẾM CHỮ: lời narrate phải đọc VỪA KHÍT độ dài "
        "part (part 6 giây tiếng Anh ~13-14 từ). ĐỪNG viết dài quá — sẽ bị "
        "cắt.\n"
        "- part orig KHÔNG cần text (để chuỗi rỗng).\n"
        f"- title: tiêu đề giật tít cho clip, viết bằng {lang_name.upper()}.\n"
        "Trả về ĐÚNG JSON này, không thêm chữ:\n"
        '{"title": "...", "parts": [{"start": giây, "end": giây, '
        '"mode": "orig"|"narrate", "text": "lời thuyết minh nếu narrate"}]}')


# ------------------------------------------------------------------
# VALIDATE + TỰ SỬA kịch bản (hàm thuần — unit test được)
# ------------------------------------------------------------------
def validate_parts(parts, clip_start: float, clip_end: float,
                   min_part: float = 1.5) -> list[dict]:
    """Chuẩn hoá kịch bản LLM trả về -> list part SẠCH phủ kín clip.

    Tự sửa mọi lỗi thường gặp:
      - part không phải dict / start-end không phải số / dài < min_part -> BỎ.
      - mode lạ -> "orig"; narrate mà không có text -> "orig".
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
                 title: str = "") -> Optional[dict]:
    """Gọi LLM viết kịch bản 1 clip -> {"title","parts"} ĐÃ VALIDATE.

    sentences = [(start, end, text)] câu transcript trong phạm vi clip.
    Ném llm.LLMError nếu gọi LLM thất bại (caller quyết fail/skip).
    Trả None nếu LLM trả JSON không dùng được (không có part narrate nào).
    """
    data = llm.complete_json(
        build_prompt(sentences, lang_name, style, clip_start, clip_end, title),
        system=_SYSTEM)
    if isinstance(data, list):          # model trả thẳng mảng parts
        data = {"parts": data}
    if not isinstance(data, dict):
        return None
    raw = data.get("parts")
    if not isinstance(raw, list):
        return None
    parts = validate_parts(raw, clip_start, clip_end)
    if not any(p["mode"] == "narrate" for p in parts):
        return None                     # không có thuyết minh -> vô nghĩa
    return {"title": str(data.get("title") or "").strip(), "parts": parts}
