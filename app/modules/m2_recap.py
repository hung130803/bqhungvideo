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

import os
import tempfile

from config import settings

from app.ai import llm, recap
from app.core.analysis import get_analysis
from app.core.ffmpeg_utils import extract_frame
from app.database import db
from app.modules.m1_highlight import (
    DEFAULTS, _delete_suggested, _lang_name, _llm_select_clips,
)
from app.queue.worker import JobContext

# Trần độ dài 1 clip recap khi user KHÔNG đặt Max (span liền mạch nên phải có
# trần cứng — thuyết minh clip 5 phút không phải mục tiêu short 9:16).
_HARD_MAX = 150.0
# Snap mốc part vào mép câu transcript trong phạm vi ±_SNAP_TOL giây
_SNAP_TOL = 1.5
# Tối đa số khung hình gửi model vision cho MỖI clip (tiết kiệm quota/băng thông)
_MAX_FRAMES = 6


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


# ------------------------------------------------------------------
# SNAP mốc cắt vào RANH GIỚI CÂU transcript (không cắt ngang câu nói)
# ------------------------------------------------------------------
def _sentence_edges(segs: list) -> list:
    """Tập mốc mép câu (start + end mỗi segment transcript), đã sort."""
    edges = set()
    for s in segs or []:
        try:
            edges.add(round(float(s["start"]), 2))
            edges.add(round(float(s["end"]), 2))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(edges)


def _snap_time(t: float, edges: list, tol: float = _SNAP_TOL) -> float:
    """Dịch mốc t tới mép câu GẦN NHẤT trong ±tol giây; không có -> giữ nguyên."""
    best, bd = float(t), tol + 1e-9
    for b in edges:
        d = abs(b - t)
        if d < bd:
            bd, best = d, b
    return best


def _unsplit_word(t: float, words: list) -> float:
    """Nếu mốc t rơi vào GIỮA 1 từ (word-level transcript) -> đẩy ra mép từ
    gần hơn (không cắt ngang từ). words = [(ws, we)]. Không words -> giữ t."""
    for ws, we in words or []:
        if ws + 0.01 < t < we - 0.01:
            return ws if (t - ws) <= (we - t) else we
    return t


def _snap_parts(parts: list, edges: list, tol: float = _SNAP_TOL,
                words: list | None = None, min_part: float = 1.5) -> list:
    """Snap ranh giới GIỮA các part vào mép câu transcript (±tol giây).

    Ranh giới chung của part i và i+1 được dịch CÙNG NHAU (giữ phủ kín,
    không tạo hở/chồng lấn). Mốc MỞ ĐẦU part đầu + KẾT THÚC part cuối cũng
    snap (LLM hay lệch vài trăm ms so với mép câu -> validate sẽ chèn part
    orig vụn lên TRƯỚC hook, phá luật "part đầu là narrate"). Sau khi snap
    theo câu, nếu mốc vẫn nằm GIỮA 1 từ (transcript có words) -> đẩy ra mép
    từ. Snap nào làm 1 trong 2 part kề ngắn hơn min_part -> BỎ snap đó (giữ
    mốc cũ). Hàm thuần — test được."""
    if not parts:
        return []
    out = [dict(p) for p in parts]
    # đầu part ĐẦU + cuối part CUỐI (validate_parts sẽ clamp vào span clip)
    s0 = _unsplit_word(_snap_time(float(out[0]["start"]), edges, tol), words)
    if (abs(s0 - float(out[0]["start"])) >= 0.01
            and float(out[0]["end"]) - s0 >= min_part):
        out[0]["start"] = round(s0, 2)
    e9 = _unsplit_word(_snap_time(float(out[-1]["end"]), edges, tol), words)
    if (abs(e9 - float(out[-1]["end"])) >= 0.01
            and e9 - float(out[-1]["start"]) >= min_part):
        out[-1]["end"] = round(e9, 2)
    for i in range(len(out) - 1):
        b0 = float(out[i]["end"])
        b1 = _snap_time(b0, edges, tol)
        b1 = _unsplit_word(b1, words)
        if abs(b1 - b0) < 0.01:
            continue
        # không được làm part kề teo dưới min_part
        if (b1 - float(out[i]["start"]) < min_part
                or float(out[i + 1]["end"]) - b1 < min_part):
            continue
        out[i]["end"] = round(b1, 2)
        out[i + 1]["start"] = round(b1, 2)
    return out


# ------------------------------------------------------------------
# NGỮ CẢNH THỊ GIÁC: trích khung hình cho model vision "nhìn" clip
# ------------------------------------------------------------------
def _clip_frames(src: str, start: float, end: float, tmp_dir: str,
                 tag: str) -> list:
    """Trích tối đa _MAX_FRAMES khung hình RẢI ĐỀU clip (1 frame giữa mỗi
    cửa sổ con ~12-15s — cỡ 1 part ứng viên) -> [(giây, đường_dẫn_jpg)].
    Ảnh nhỏ ~360px (tiết kiệm token vision). Frame trích lỗi -> bỏ riêng."""
    dur = end - start
    if dur <= 1.0 or not src or not os.path.exists(src):
        return []
    n = max(2, min(_MAX_FRAMES, int(round(dur / 12.0))))
    out = []
    for k in range(n):
        t = start + (k + 0.5) * dur / n        # giữa mỗi cửa sổ con
        fp = os.path.join(tmp_dir, f"_recapf_{tag}_{k}.jpg")
        if extract_frame(src, t, fp, width=360):
            out.append((round(t, 1), fp))
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
    vrow = db.query_one("SELECT duration, src_path FROM videos WHERE id=?",
                        (video_id,))
    duration = float(vrow["duration"] or 0) if vrow else 0.0
    src_path = (vrow["src_path"] or "") if vrow else ""
    lang_name = _lang_name(transcript.get("language", ""))
    edges = _sentence_edges(segs)          # mép câu -> snap mốc cắt
    tr_words = []                          # (ws, we) word-level nếu whisper trả
    for w in (transcript.get("words") or []):
        try:
            tr_words.append((float(w["start"]), float(w["end"])))
        except (KeyError, TypeError, ValueError):
            continue

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

    # Recap dùng SPAN LIỀN MẠCH (thuyết minh phủ cả đoạn, không cắt khúc giữa).
    # Đầu/cuối span SNAP vào mép câu transcript (±_SNAP_TOL) -> không mở/đóng
    # clip giữa chừng 1 câu nói.
    max_len = float(cfg.get("max_len") or 0) or _HARD_MAX
    spans = []
    for c in clips:
        s0 = float(c["segments"][0][0])
        e1 = float(c["segments"][-1][1])
        s0 = max(0.0, _snap_time(s0, edges))
        e1 = _snap_time(e1, edges)
        e1 = min(e1, s0 + max_len, duration or e1)
        if e1 - s0 >= 10.0:
            spans.append((round(s0, 2), round(e1, 2), c))

    # ---- 2) LLM đạo diễn viết kịch bản từng clip ----
    # NGỮ CẢNH THỊ GIÁC: nếu bật USE_VISION + model vision sẵn sàng -> trích
    # tối đa _MAX_FRAMES khung hình/clip cho AI NHÌN cảnh rồi viết lời bám
    # hình. Không vision -> prompt tự dặn bám transcript theo mốc thời gian.
    use_vision = bool(getattr(settings, "USE_VISION", False)
                      and llm.vision_available())
    scripts = []
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="recapf_") as ftd:
        for i, (s0, e1, c) in enumerate(spans):
            ctx.progress(0.45 + 0.5 * i / max(1, len(spans)),
                         f"Viết kịch bản {i + 1}/{len(spans)}"
                         + (" (AI xem hình)" if use_vision else "") + "...")
            sents = _clip_sentences(segs, s0, e1)
            frames = (_clip_frames(src_path, s0, e1, ftd, str(i))
                      if use_vision else None)
            try:
                sc = recap.write_script(sents, lang_name, style, s0, e1,
                                        title=c.get("title", ""),
                                        frames=frames)
            except llm.LLMError as e:
                errors.append(str(e))
                sc = None
            if sc:
                # SNAP mốc part vào mép câu (±_SNAP_TOL, không cắt ngang
                # câu/từ) rồi validate lại cho phủ kín sạch sẽ.
                snapped = _snap_parts(sc["parts"], edges, words=tr_words)
                sc["parts"] = recap.validate_parts(snapped, s0, e1,
                                                   sentences=sents)
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
