"""
MODULE 2 — 🎙 REUP THUYẾT MINH (recap).

Đưa video vào -> AI đọc nội dung -> chọn các đoạn hay (TÁI DÙNG đường chọn
clip của M1) -> với MỖI clip, LLM "đạo diễn" (app/ai/recap.py) viết KỊCH BẢN
chia đoạn xen kẽ: GIỮ TIẾNG GỐC (khoảnh khắc đắt) / AI THUYẾT MINH (video tắt
tiếng, giọng AI kể — đúng NGÔN NGỮ video, theo PHONG CÁCH user chọn).

Kịch bản lưu vào clips.signals["recap"] (JSON sẵn có — không cần migration):
  {"style": "story", "lang": "en", "parts": [{"start","end","mode","text"}]}
Mốc part theo TIMELINE VIDEO GỐC (giây tuyệt đối, nằm trong segments của clip).

Xuất dùng lại job m1_export_clip: clip CÓ signals.recap -> m1 dựng track
thuyết minh (TTS) + tắt tiếng gốc trong các khoảng narrate (duck_ranges).
Clip KHÔNG có recap -> xuất y hệt cũ.

generate_recap KHÔNG đăng ký trực tiếp — được job "auto_recap"
(app/queue/jobs.py) gọi sau bước phân tích (như auto/auto_mixed).
"""
from __future__ import annotations

from app.ai import llm, recap
from app.core.analysis import get_analysis
from app.database import db
from app.modules.m1_highlight import (
    DEFAULTS, _delete_suggested, _lang_name, _llm_select_clips,
)
from app.queue.worker import JobContext

# Trần độ dài 1 clip recap khi user KHÔNG đặt Max (span liền mạch nên phải có
# trần cứng — thuyết minh clip 5 phút không phải mục tiêu short 9:16).
_HARD_MAX = 150.0


def _clip_sentences(segs: list, start: float, end: float) -> list:
    """Các câu transcript GIAO với [start,end] -> [(s, e, text)]."""
    out = []
    for s in segs or []:
        try:
            a, b = float(s["start"]), float(s["end"])
        except (KeyError, TypeError, ValueError):
            continue
        txt = (s.get("text") or "").strip()
        if txt and b > start and a < end:
            out.append((max(a, start), min(b, end), txt))
    return out


def generate_recap(payload: dict, ctx: JobContext) -> dict:
    """Bước 'reup thuyết minh' — job 'auto_recap' gọi sau khi phân tích.

    payload: {video_id, preset: {..., recap_style}}. Kết quả: các dòng clips
    status='suggested' kèm signals.recap (kịch bản). Lỗi LLM -> ném lỗi rõ.
    """
    video_id = int(payload["video_id"])
    preset = payload.get("preset") or {}
    cfg = {**DEFAULTS, **preset}
    style = str(preset.get("recap_style") or recap.DEFAULT_STYLE)

    if not llm.is_configured():
        raise RuntimeError(
            "Reup thuyết minh cần AI viết kịch bản — hãy dán key Groq/Gemini "
            "trong 'Cài đặt AI' rồi thử lại.")

    ctx.progress(0.02, "Đọc kết quả phân tích...")
    transcript = get_analysis(video_id, "transcript") or {}
    scenes = get_analysis(video_id, "scenes") or {}
    segs = transcript.get("segments") or []
    if not segs:
        raise RuntimeError(
            "Video chưa có lời thoại (transcript) — không viết được kịch bản "
            "thuyết minh. Hãy chạy phân tích trước.")
    vrow = db.query_one("SELECT duration FROM videos WHERE id=?", (video_id,))
    duration = float(vrow["duration"] or 0) if vrow else 0.0
    lang_name = _lang_name(transcript.get("language", ""))

    # ---- 1) Chọn các đoạn hay (tái dùng đường chọn clip của auto) ----
    prov = llm.active_provider()
    ctx.progress(0.05, f"AI [{prov}] đang đọc nội dung & chọn đoạn hay...")

    class _Sel:                       # map tiến độ chọn clip về 0.05..0.45
        profile = ctx.profile
        def progress(self, p, m=""):
            ctx.progress(0.05 + 0.40 * max(0.0, min(1.0, (p - 0.3) / 0.3)), m)
        def check_canceled(self):
            ctx.check_canceled()

    clips, warns = _llm_select_clips(transcript, duration, _Sel(), scenes, cfg)
    if not clips:
        return {"count": 0, "clip_ids": [],
                "note": "AI không chọn được đoạn nào đủ hay để thuyết minh."}

    # Recap dùng SPAN LIỀN MẠCH (thuyết minh phủ cả đoạn, không cắt khúc giữa)
    max_len = float(cfg.get("max_len") or 0) or _HARD_MAX
    spans = []
    for c in clips:
        s0 = float(c["segments"][0][0])
        e1 = float(c["segments"][-1][1])
        e1 = min(e1, s0 + max_len, duration or e1)
        if e1 - s0 >= 10.0:
            spans.append((s0, round(e1, 2), c))

    # ---- 2) LLM đạo diễn viết kịch bản từng clip ----
    scripts = []
    errors: list[str] = []
    for i, (s0, e1, c) in enumerate(spans):
        ctx.progress(0.45 + 0.5 * i / max(1, len(spans)),
                     f"Viết kịch bản {i + 1}/{len(spans)}...")
        sents = _clip_sentences(segs, s0, e1)
        try:
            sc = recap.write_script(sents, lang_name, style, s0, e1,
                                    title=c.get("title", ""))
        except llm.LLMError as e:
            errors.append(str(e))
            sc = None
        scripts.append(sc)
    if spans and not any(scripts):
        raise RuntimeError(
            "AI không viết được kịch bản thuyết minh cho clip nào"
            + (f" — lỗi: {errors[0][:200]}" if errors else
               " (kịch bản trả về không hợp lệ)."))

    # ---- 3) Lưu clip + kịch bản (signals.recap) ----
    _delete_suggested(video_id)
    lang = (transcript.get("language") or "").strip()
    clip_ids = []
    n_script = 0
    for (s0, e1, c), sc in zip(spans, scripts):
        signals = {
            "segments": [[s0, e1]], "n_seg": 1, "llm_used": True,
            "ai": prov, "dur": round(e1 - s0, 1),
            "title_en": (sc or {}).get("title") or c.get("title_en", ""),
            "hook": c.get("hook", ""),
        }
        if sc:
            n_script += 1
            signals["recap"] = {"style": style, "lang": lang,
                                "parts": sc["parts"]}
        cid = db.insert(
            """INSERT INTO clips (video_id, start_sec, end_sec, score, reason,
                                  title, transcript, signals, status)
               VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
            (video_id, s0, e1, round(float(c.get("score", 60)), 1),
             ("Thuyết minh " + recap.style_label(style) + ". "
              + (c.get("reason") or "")).strip(),
             c.get("title") or "Clip thuyết minh", "", db.dumps(signals)))
        clip_ids.append(cid)

    msg = (f"AI [{prov}] tạo {len(clip_ids)} clip thuyết minh "
           f"({n_script} có kịch bản, phong cách {recap.style_label(style)})")
    if errors:
        msg += f" — {len(errors)} clip viết kịch bản lỗi (giữ tiếng gốc)"
    if warns:
        msg += " — CẢNH BÁO: " + "; ".join(warns)
    ctx.progress(1.0, msg)
    return {"count": len(clip_ids), "clip_ids": clip_ids,
            "scripts": n_script, "style": style, "llm_used": True}
