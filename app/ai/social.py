"""AI viết CAPTION + HASHTAG đăng bài cho 1 clip (TikTok/Reels/Shorts).

Dùng LLM đang cấu hình (Groq/Gemini/...). Trả dict chuẩn hóa:
  {"title": "...", "caption": "...", "hashtags": ["#a", "#b", ...]}
"""
from __future__ import annotations

from app.ai import llm

_SYSTEM = (
    "Bạn là chuyên gia content ngắn (TikTok/Reels/Shorts) chuyên viết caption "
    "triệu view. Trả về JSON THUẦN, không thêm chữ nào khác."
)


def write_post(title: str, transcript: str, language: str = "",
               channel: str = "") -> dict:
    """Sinh caption đăng bài từ tiêu đề + lời thoại của clip. Ném LLMError nếu lỗi."""
    lang = (language or "").strip()
    tx = (transcript or "").strip().replace("\n", " ")[:2500]
    # QUY TẮC NGÔN NGỮ: có language -> dùng nó; rỗng -> AI tự nhận diện từ CHÍNH
    # lời thoại. TUYỆT ĐỐI không đưa tên kênh lên đầu prompt như ngữ cảnh chung
    # (kênh tên 'hàn quốc' từng làm AI viết caption tiếng Hàn cho video Anh).
    if lang:
        lang_rule = (f"- NGÔN NGỮ: viết title + caption + hashtag bằng "
                     f"{lang.upper()} (ngôn ngữ của lời thoại).\n")
    else:
        lang_rule = ("- NGÔN NGỮ: tự nhận diện ngôn ngữ từ chính đoạn lời "
                     "thoại trong ngoặc kép ở trên và viết ĐÚNG ngôn ngữ đó.\n")
    brand = (f" 1-2 tag thương hiệu lấy từ tên kênh \"{channel}\" (LƯU Ý: đây "
             "chỉ là TÊN KÊNH để tạo hashtag, KHÔNG phải ngôn ngữ/chủ đề — "
             "không suy ra ngôn ngữ từ tên kênh)." if channel.strip() else "")
    prompt = (
        f"Tiêu đề clip: {title or '(chưa có)'}\n"
        f"Lời thoại trong clip:\n\"{tx}\"\n\n"
        "Viết bài đăng cho clip này:\n"
        + lang_rule +
        "- TUYỆT ĐỐI không dùng ngôn ngữ khác với lời thoại.\n"
        "- title: tiêu đề giật tít <70 ký tự, gây tò mò, KHÔNG bịa nội dung "
        "không có trong lời thoại.\n"
        "- caption: 1-3 câu dẫn dắt + 1 câu hỏi/kêu gọi tương tác (comment, "
        "follow). Tự nhiên, có thể chèn 1-2 emoji hợp ngữ cảnh.\n"
        "- hashtags: 8-12 hashtag XẾP THEO THỨ TỰ: 3-4 tag đúng chủ đề nội "
        "dung, 2-3 tag ngách nội dung, 2-3 tag phổ biến (fyp/viral/xu hướng "
        "theo đúng ngôn ngữ lời thoại)." + brand + "\n"
        "Trả về ĐÚNG JSON: {\"title\":\"...\",\"caption\":\"...\","
        "\"hashtags\":[\"#...\",\"#...\"]}"
    )
    data = llm.complete_json(prompt, system=_SYSTEM)
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}
    if not isinstance(data, dict):
        raise llm.LLMError("AI trả về định dạng lạ, bấm thử lại.")
    tags = []
    for t in (data.get("hashtags") or []):
        t = str(t).strip().replace(" ", "")
        if t and not t.startswith("#"):
            t = "#" + t
        if t and t not in tags:
            tags.append(t)
    return {
        "title": str(data.get("title", "")).strip() or (title or "").strip(),
        "caption": str(data.get("caption", "")).strip(),
        "hashtags": tags,
    }


def format_post(post: dict) -> str:
    """Ghép thành văn bản dán thẳng vào ô đăng bài."""
    parts = []
    if post.get("title"):
        parts.append(post["title"])
    if post.get("caption"):
        parts.append(post["caption"])
    if post.get("hashtags"):
        parts.append(" ".join(post["hashtags"]))
    return "\n\n".join(parts).strip()
