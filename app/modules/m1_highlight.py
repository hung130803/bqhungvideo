"""
MODULE 1 — AUTO CẮT HIGHLIGHT + FACE-TRACK CROP.

Chọn đoạn bằng 3 tín hiệu (đọc lại từ lõi phân tích đã cache, KHÔNG phân tích lại):
  1. audio peak (librosa)         -> đoạn năng lượng cao
  2. scene detection (PySceneDetect) -> mốc chuyển cảnh để cắt gọn
  3. transcript -> LLM chấm điểm "viral nhất" (JSON: điểm + lý do + tiêu đề)

Xuất: cắt + crop dọc 9:16 BÁM mặt người nói (face-track) trong 1 lệnh ffmpeg.

Hai handler đăng ký vào worker:
  - "m1_highlights"   : sinh danh sách clip đề xuất, lưu bảng clips.
  - "m1_export_clip"  : xuất 1 clip ra file 9:16.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from app.ai import llm
from app.core import face_track
from app.core.analysis import get_analysis
from app.core.ffmpeg_utils import (
    detect_black_crop, export_canvas_clip, export_stitched_clip,
    export_vertical_clip, extract_frame,
)
from app.database import db
from app.queue.worker import JobContext, register_handler

# ---- tham số mặc định (preset có thể override) ----
DEFAULTS = {
    "min_len": 60.0,     # clip tối thiểu trên 1 phút (theo yêu cầu)
    "max_len": 90.0,
    "target_len": 75.0,
    "max_candidates": 25,     # giới hạn số ứng viên gửi LLM (kiểm soát chi phí)
    "out_w": 1080,
    "out_h": 1920,
    "w_llm": 0.5,
    "w_audio": 0.3,
    "w_scene": 0.2,
    # Mixed-Cut: ghép nhiều khoảnh khắc ngắn thành 1 clip dài
    "moment_min": 6.0,
    "moment_max": 16.0,
    "mix_target_len": 75.0,   # tổng độ dài clip ghép (>1 phút)
    "mix_max_len": 120.0,
}

_SENTENCE_END = (".", "?", "!", "…", ".\"", "?\"", "!\"")


def _safe_name(s: str, limit: int = 70) -> str:
    """Bỏ ký tự cấm trong tên file/thư mục Windows, gọn khoảng trắng."""
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', "", s or "")
    return re.sub(r"\s+", " ", s).strip()[:limit].strip()


# ============================================================
# Sinh ứng viên highlight
# ============================================================
def _build_candidates(transcript: dict, scenes: dict, duration: float,
                      cfg: dict) -> list[dict]:
    """Tạo các cửa sổ [start,end] dài min..max giây, ưu tiên kết thúc trọn câu."""
    segs = (transcript or {}).get("segments", [])
    min_len, max_len = cfg["min_len"], cfg["max_len"]

    if not segs:
        # Không có transcript: chia đều theo target_len
        out, t = [], 0.0
        step = cfg["target_len"]
        while t + min_len <= duration:
            out.append({"start": round(t, 2),
                        "end": round(min(t + step, duration), 2), "text": ""})
            t += step
        return out

    cut_points = set((scenes or {}).get("cut_points", []))

    candidates: list[dict] = []
    for a_idx, anchor in enumerate(segs):
        a = anchor["start"]
        end, text_parts = a, []
        for s in segs:
            if s["end"] <= a:
                continue
            end = s["end"]
            text_parts.append(s["text"])
            length = end - a
            if length >= min_len:
                ends_sentence = s["text"].rstrip().endswith(_SENTENCE_END)
                near_cut = any(abs(end - c) < 0.6 for c in cut_points)
                if ends_sentence or near_cut or length >= max_len * 0.9:
                    break
            if length >= max_len:
                break
        length = end - a
        if min_len * 0.8 <= length <= max_len:
            candidates.append({"start": round(a, 2), "end": round(end, 2),
                               "text": " ".join(text_parts).strip()})

    # Khử trùng lặp: bỏ cửa sổ chồng > 55% lên cửa sổ đã nhận
    candidates.sort(key=lambda c: c["start"])
    deduped: list[dict] = []
    for c in candidates:
        keep = True
        for d in deduped:
            overlap = min(c["end"], d["end"]) - max(c["start"], d["start"])
            shorter = min(c["end"] - c["start"], d["end"] - d["start"])
            if overlap > 0.55 * shorter:
                keep = False
                break
        if keep:
            deduped.append(c)
    return deduped


def _audio_score(audio: dict, start: float, end: float) -> float:
    """Điểm 0..100 theo năng lượng RMS trung bình + đỉnh trong cửa sổ."""
    if not audio:
        return 50.0
    env = audio.get("rms_envelope", {})
    hop = env.get("hop_sec", 0) or 0
    vals = env.get("values", [])
    if hop and vals:
        i0, i1 = int(start / hop), int(end / hop)
        seg = vals[i0:i1] or [0]
        mean_e = sum(seg) / len(seg)
        max_e = max(seg)
        base = 100 * (0.6 * mean_e + 0.4 * max_e)
    else:
        base = 50.0
    # cộng thưởng nếu có đỉnh năng lượng mạnh trong cửa sổ
    peaks = [p for p in audio.get("peaks", []) if start <= p["t"] <= end]
    if peaks:
        base += 10 * max(p["energy"] for p in peaks)
    return float(min(100.0, base))


def _scene_score(scenes: dict, start: float, end: float) -> float:
    """Điểm 0..100: có chuyển cảnh trong đoạn = sinh động hơn (vừa phải)."""
    if not scenes:
        return 50.0
    cuts = [c for c in scenes.get("cut_points", []) if start < c < end]
    # 1-3 chuyển cảnh là lý tưởng; quá nhiều thì loạn
    n = len(cuts)
    if n == 0:
        return 45.0
    if n <= 3:
        return 70.0 + n * 5
    return max(50.0, 85.0 - (n - 3) * 5)


def _llm_scores(candidates: list[dict], language: str) -> dict[int, dict]:
    """Gửi toàn bộ ứng viên trong 1 lần gọi LLM -> {index: {score,reason,title}}."""
    if not llm.is_configured():
        return {}
    items = []
    for i, c in enumerate(candidates):
        txt = (c["text"] or "").replace("\n", " ")[:600]
        items.append(f'#{i} ({c["start"]:.0f}-{c["end"]:.0f}s): "{txt}"')
    listing = "\n".join(items)

    system = (
        "Bạn là chuyên gia viral short-form (TikTok/Reels/Shorts). "
        "Chấm điểm tiềm năng viral của từng đoạn dựa trên hook, cảm xúc, "
        "tính trọn vẹn và khả năng giữ chân người xem. Trả về JSON THUẦN."
    )
    prompt = (
        f"Ngôn ngữ nội dung: {language or 'không rõ'}.\n"
        f"Dưới đây là các đoạn ứng viên cắt từ 1 video dài:\n{listing}\n\n"
        "Với MỖI đoạn, trả về một object trong mảng JSON:\n"
        '[{"index": số, "score": 0-100, "reason": "lý do ngắn gọn tiếng Việt", '
        '"title": "tiêu đề giật tít gợi ý"}]\n'
        "Chỉ trả JSON, không thêm chữ nào khác."
    )
    try:
        data = llm.complete_json(prompt, system=system)
    except Exception:  # noqa: BLE001 - lỗi LLM KHÔNG được làm sập M1; lùi heuristic
        return {}
    out: dict[int, dict] = {}
    rows = data if isinstance(data, list) else data.get("clips", [])
    for r in rows or []:
        try:
            idx = int(r["index"])
            out[idx] = {
                "score": float(r.get("score", 50)),
                "reason": str(r.get("reason", "")).strip(),
                "title": str(r.get("title", "")).strip(),
            }
        except (KeyError, ValueError, TypeError):
            continue
    return out


def _ensure_min_duration(segments: list, duration: float,
                         min_total: float = 60.0) -> list:
    """Đảm bảo tổng độ dài clip >= min_total bằng cách nới đoạn cuối/đầu."""
    segs = [list(s) for s in segments]
    if not segs:                                 # không có đoạn -> khỏi nới
        return segs
    total = sum(e - s for s, e in segs)
    if total >= min_total or duration <= 0:
        return segs
    deficit = min_total - total
    add = min(duration - segs[-1][1], deficit)  # nới đoạn CUỐI về sau
    segs[-1][1] = round(segs[-1][1] + add, 2)
    deficit -= add
    if deficit > 0:                              # còn thiếu -> nới đoạn ĐẦU về trước
        add2 = min(segs[0][0], deficit)
        segs[0][0] = round(segs[0][0] - add2, 2)
    return segs


# Ngân sách ký tự MỖI lần gọi LLM. Model local 7B nhả tốt khi prompt ~5-8k ký tự;
# prompt quá dài (>9k) khiến nó loạn -> chỉ ra 1 token. Nên CHIA transcript thành
# nhiều khúc nhỏ, gọi từng khúc rồi gộp kết quả (tin cậy + miễn phí + không giới hạn).
_CHUNK_CHARS = 5500

_SEL_SYSTEM = (
    "Bạn là chuyên gia dựng clip viral cho TikTok/Reels/Shorts. Từ transcript có mốc "
    "thời gian, chọn các KHOẢNH KHẮC ĐỈNH NHẤT (cao trào, bất ngờ, cảm xúc mạnh, câu "
    "chốt đắt) và lấy ĐỦ TRỌN VẸN câu chuyện đó — từ lúc dẫn dắt tới lúc chốt. GHÉP "
    "các đoạn liên quan thành 1 clip mạch lạc và BỎ phần nhàm/lạc đề ở giữa. "
    "Trường title LUÔN viết bằng TIẾNG VIỆT CÓ DẤU (để người dựng hiểu); "
    "title_pub = tiêu đề giật tít viết bằng ĐÚNG NGÔN NGỮ GỐC của video (để gắn lên "
    "video). CHỈ trả JSON, không thêm bất kỳ chữ nào khác.")


_LANG_NAMES = {
    "vi": "tiếng Việt", "vietnamese": "tiếng Việt",
    "en": "tiếng Anh", "english": "tiếng Anh",
    "ja": "tiếng Nhật", "japanese": "tiếng Nhật",
    "ko": "tiếng Hàn", "korean": "tiếng Hàn",
    "zh": "tiếng Trung", "chinese": "tiếng Trung",
    "th": "tiếng Thái", "thai": "tiếng Thái",
    "fr": "tiếng Pháp", "es": "tiếng Tây Ban Nha", "de": "tiếng Đức",
    "ru": "tiếng Nga", "id": "tiếng Indonesia",
}


def _lang_name(code: str) -> str:
    return _LANG_NAMES.get((code or "").strip().lower(), code or "ngôn ngữ gốc của video")


def _chunk_transcript(segs: list) -> list[str]:
    """Chia transcript thành các khúc ~_CHUNK_CHARS ký tự; mỗi dòng 'bd kt | lời'."""
    chunks, cur, n = [], [], 0
    for s in segs:
        line = f'{s["start"]:.0f} {s["end"]:.0f} | {s["text"].strip()}'
        if n + len(line) > _CHUNK_CHARS and cur:
            chunks.append("\n".join(cur))
            cur, n = [], 0
        cur.append(line)
        n += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


_PURPOSE_HINT = {
    "compilation": "Cắt kiểu COMPILATION: gom nhiều khoảnh khắc hay trong video.",
    "peak": "Chỉ lấy KHOẢNH KHẮC ĐỈNH NHẤT (cao trào, sốc, bùng nổ).",
    "teaser": "Cắt kiểu TEASER: ngắn, gây tò mò, nhử người xem.",
    "story": "Cắt theo ARC CÂU CHUYỆN: có mở đầu - cao trào - kết, trọn vẹn.",
    "highlight": "Cắt HIGHLIGHTS REEL: các điểm nhấn hấp dẫn nhất.",
}
_STYLE_HINT = {
    "funny": "Ưu tiên đoạn HÀI HƯỚC, vui, gây cười.",
    "drama": "Ưu tiên đoạn KỊCH TÍNH, căng thẳng, cảm xúc mạnh.",
    "info": "Ưu tiên đoạn THÔNG TIN/TIPS hữu ích, đáng học.",
    "calm": "Ưu tiên đoạn NHẸ NHÀNG, thư giãn.",
    "review": "Ưu tiên đoạn ĐÁNH GIÁ/nhận xét.",
    "story": "Ưu tiên đoạn có TÌNH TIẾT/câu chuyện cuốn.",
}


def _select_prompt(listing: str, lang_name: str = "ngôn ngữ gốc của video",
                   purpose: str = "", style: str = "",
                   min_len: float = 60.0, max_len: float = 0.0,
                   count: int = 0) -> str:
    extra = ""
    if _PURPOSE_HINT.get(purpose):
        extra += "- " + _PURPOSE_HINT[purpose] + "\n"
    if _STYLE_HINT.get(style):
        extra += "- " + _STYLE_HINT[style] + "\n"
    how_many = (f"Chọn ĐÚNG {count} clip hay nhất" if count > 0
                else "Chọn 3-6 clip hay nhất")
    if min_len and min_len > 0:                 # có Min -> ép tối thiểu
        mx = f", tối đa ~{int(max_len)} giây" if max_len else ""
        len_rule = (f"- ĐỘ DÀI: TỐI THIỂU {int(min_len)} giây{mx}. Đoạn hay kéo "
                    "dài thì để dài hơn, miễn hấp dẫn. ĐỪNG gò về đúng 1 phút.\n")
    else:                                       # Min=0 -> độ dài TỰ DO / ngẫu nhiên
        mxx = f" (không quá ~{int(max_len)} giây)" if max_len else ""
        len_rule = ("- ĐỘ DÀI: TỰ DO theo nội dung" + mxx + " — khoảnh khắc nào "
                    "hay thì lấy trọn, ngắn dài tuỳ nội dung, KHÔNG ép độ dài.\n")
    return (
        "Transcript (mỗi dòng: GIÂY_BẮT_ĐẦU GIÂY_KẾT_THÚC | lời nói):\n"
        f"{listing}\n\n"
        f"Video này nói bằng {lang_name.upper()}.\n"
        f"{how_many} trong đoạn này. QUY TẮC:\n"
        + extra +
        "- Ưu tiên cảnh ĐỈNH ĐIỂM/cao trào, có hook ở đầu, giữ chân người xem.\n"
        "- Mỗi clip là MỘT câu chuyện/cao trào TRỌN VẸN: lấy đủ phần dẫn dắt + cao "
        "trào + chốt, KHÔNG cắt cụt giữa chừng.\n"
        + len_rule +
        "- Có thể chia 1 clip thành NHIỀU đoạn nhỏ (tối đa ~6 khúc) để bỏ phần "
        "thừa/lặp/ngắt quãng, MIỄN ghép lại liền mạch, đúng mạch nội dung video.\n"
        "- Cắt vào RANH GIỚI CÂU trọn vẹn (đầu/cuối câu nói), ĐỪNG cắt giữa câu.\n"
        "- segments là CÁC MỐC THỜI GIAN (số giây), KHÔNG phải lời nói.\n"
        "- title: BẮT BUỘC TIẾNG VIỆT CÓ DẤU (để người dựng đọc hiểu nội dung).\n"
        f"- title_pub = tiêu đề giật tít, viết BẰNG {lang_name.upper()} (ĐÚNG ngôn "
        f"ngữ video) để GẮN LÊN video. Ví dụ video {lang_name} thì title_pub phải là "
        f"{lang_name}, KHÔNG dịch sang tiếng Anh/Việt.\n"
        f"- hook = MỘT câu cực ngắn (3-7 từ) GÂY TÒ MÒ/SỐC nhất của clip (câu hỏi gây "
        f"thắc mắc, câu giật gân) viết BẰNG {lang_name.upper()} — để hiện TO ở đầu "
        f"clip giữ chân người xem. Lấy từ chính lời thoại hay nhất.\n"
        "Trả về ĐÚNG định dạng JSON này (mảng), không thêm chữ:\n"
        '[{"title":"tiêu đề tiếng Việt","title_pub":"tiêu đề giật tít bằng đúng ngôn '
        'ngữ video","hook":"câu hook ngắn giật tít","score":85,'
        '"reason":"lý do ngắn","segments":[[30,95],[140,210]]}]')


def _natural_boundaries(transcript: dict, scenes: dict) -> list:
    """Tập mốc 'cắt sạch' của VIDEO GỐC: ranh giới câu nói + ranh giới cảnh."""
    bset = set()
    for s in (transcript or {}).get("segments", []):
        try:
            bset.add(round(float(s["start"]), 2))
            bset.add(round(float(s["end"]), 2))
        except (KeyError, ValueError, TypeError):
            continue
    for c in (scenes or {}).get("cut_points", []):
        try:
            bset.add(round(float(c), 2))
        except (ValueError, TypeError):
            continue
    return sorted(bset)


def _snap(boundaries: list, t: float, tol: float) -> float:
    """Đẩy mốc t về ranh giới gần nhất trong khoảng tol giây; không có -> giữ nguyên."""
    best, bd = t, tol + 1.0
    for b in boundaries:
        d = abs(b - t)
        if d < bd:
            bd, best = d, b
    return best if bd <= tol else t


def _snap_segments(segments: list, boundaries: list, tol: float = 1.5) -> list:
    """Snap đầu/cuối mỗi đoạn vào ranh giới câu/cảnh để cắt không lẹm giữa câu/cảnh."""
    if not boundaries:
        return segments
    out = []
    for s, e in segments:
        s2, e2 = _snap(boundaries, s, tol), _snap(boundaries, e, tol)
        out.append([round(s2, 2), round(e2, 2)] if e2 - s2 >= 1.0 else [s, e])
    return out


_REFINE_SYSTEM = (
    "Bạn là biên tập viên video giỏi, chuyên cắt clip CÔ ĐỌNG và HẤP DẪN LIÊN TỤC. "
    "Bạn ĐỌC HIỂU nội dung để biết đoạn nào đáng giữ, đoạn nào thừa. CHỈ trả JSON.")


def _clip_sentences(segments: list, segs: list) -> list:
    """Các câu transcript NẰM TRONG segments của clip (kèm mốc giây)."""
    out = []
    for s in segs:
        st, en = float(s["start"]), float(s["end"])
        if any(en > a and st < b for a, b in segments):  # giao với khúc nào đó
            out.append((st, en, (s.get("text") or "").strip()))
    return out


def _refine_clip(clip: dict, segs: list, duration: float, boundaries=None,
                 min_len: float = 0.0) -> dict:
    """
    PASS 2 — AI ĐỌC KỸ transcript của 1 clip rồi CẮT GỌN: bỏ câu lan man/lặp/lạc đề,
    giữ phần hay (hook/cao trào/chốt) — ĐƯỢC giữ khoảng lặng nếu tạo kịch tính.
    Lỗi/cắt quá tay -> giữ nguyên clip gốc (an toàn).
    """
    sents = _clip_sentences(clip["segments"], segs)
    if len(sents) < 4:           # đã ngắn/ít câu -> khỏi tinh chỉnh
        return clip
    lines = "\n".join(f'{a:.0f} {b:.0f} | {t}' for a, b, t in sents)[:5000]
    prompt = (
        "Đây là transcript của MỘT clip (mỗi dòng: bắt_đầu kết_thúc | lời nói):\n"
        f"{lines}\n\n"
        "Hãy CẮT GỌN clip này cho cô đọng, hấp dẫn LIÊN TỤC:\n"
        "- GIỮ phần hay: mở đầu hút (hook), cao trào, câu chốt, cảm xúc mạnh. "
        "ĐƯỢC giữ khoảng lặng nếu nó tạo kịch tính/hồi hộp.\n"
        "- BỎ: câu lan man, lặp lại, dài dòng, lạc đề, mở đầu/kết thúc thừa.\n"
        "- Cố giữ tổng >= 60 giây nếu còn đủ phần hay; nội dung ít hay thì ngắn hơn.\n"
        '- Cắt vào ranh giới câu trọn vẹn.\n'
        'Trả JSON các mốc GIỮ LẠI (số giây): {"segments":[[s,e],...]}')
    try:
        data = llm.complete_json(prompt, system=_REFINE_SYSTEM)
    except Exception:  # noqa: BLE001 - tinh chỉnh lỗi -> giữ clip gốc
        return clip
    raw = data.get("segments") if isinstance(data, dict) else data
    span0, span1 = clip["segments"][0][0], clip["segments"][-1][1]
    new = []
    for pair in (raw or []):
        try:
            s, e = float(pair[0]), float(pair[1])
        except (ValueError, TypeError, IndexError):
            continue
        s = max(span0, min(span1, s))
        e = max(span0, min(span1, e))
        if e - s >= 1.5:
            new.append([round(s, 2), round(e, 2)])
    if not new:
        return clip
    new.sort(key=lambda x: x[0])
    if boundaries:
        new = _snap_segments(new, boundaries)
    merged = [list(new[0])]              # gộp khúc sát nhau (<0.4s)
    for s, e in new[1:]:
        if s - merged[-1][1] <= 0.4:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    total = sum(e - s for s, e in merged)
    orig = sum(e - s for s, e in clip["segments"])
    # cắt quá tay -> giữ gốc. QUAN TRỌNG: nếu user đặt Min mà tỉa xuống dưới Min
    # thì GIỮ CLIP GỐC (đã >= Min từ PASS 1) -> không bao giờ ra clip < Min.
    if (total < 40 or total < 0.3 * orig
            or (min_len and total < min_len - 0.5)):
        return clip
    out = dict(clip)
    out["segments"] = merged
    return out


def _smooth_segments(segments: list, min_gap: float = 1.2,
                     min_seg: float = 2.0) -> list:
    """Làm MƯỢT: gộp 2 khúc cách nhau quá gần (<min_gap, cắt nhỏ vô nghĩa) + bỏ
    khúc quá ngắn (<min_seg) gây giật. Tránh clip ghép vụn 10 mảnh."""
    if not segments:
        return segments
    segs = sorted([list(s) for s in segments], key=lambda x: x[0])
    merged = [segs[0]]
    for s, e in segs[1:]:
        if s - merged[-1][1] < min_gap:          # khe hở nhỏ -> nối liền
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    kept = [m for m in merged if m[1] - m[0] >= min_seg]
    return kept or merged                        # nếu lỡ bỏ hết -> giữ merged


def _cap_max_duration(segments: list, max_len: float) -> list:
    """ÉP tổng độ dài clip <= max_len (cắt bớt khúc cuối). 0 = không giới hạn."""
    if not max_len or max_len <= 0:
        return segments
    out, total = [], 0.0
    for s, e in segments:
        if total >= max_len:
            break
        dur = e - s
        if total + dur <= max_len:
            out.append([s, e]); total += dur
        else:                                       # cắt ngắn khúc cuối cho vừa
            out.append([round(s, 2), round(s + (max_len - total), 2)])
            break
    return out or segments[:1]


def _normalize_clip(r, duration: float, boundaries=None,
                    min_len: float = 60.0, max_len: float = 0.0) -> Optional[dict]:
    """Kiểm tra & chuẩn hoá 1 clip từ JSON LLM. Trả None nếu không hợp lệ."""
    if not isinstance(r, dict):
        return None
    try:
        segments = []
        for pair in (r.get("segments") or []):
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            s, e = float(pair[0]), float(pair[1])  # ném ValueError nếu là chuỗi lời nói
            s = max(0.0, min(duration, s))
            e = max(0.0, min(duration, e))
            if e - s >= 1.0:
                segments.append([round(s, 2), round(e, 2)])
        if not segments:
            return None
        segments.sort(key=lambda x: x[0])
        if boundaries:  # bám ranh giới câu/cảnh của video gốc -> cắt sạch
            segments = _snap_segments(segments, boundaries)
        segments = _smooth_segments(segments)      # gộp khúc vụn cho mượt, đỡ giật
        segments = _ensure_min_duration(segments, duration, min_len)  # >= Min user đặt
        segments = _cap_max_duration(segments, max_len)               # <= Max user đặt
        return {
            "title": str(r.get("title", "")).strip() or "Clip",
            # title_en = TIÊU ĐỀ GẮN LÊN VIDEO (theo NGÔN NGỮ video); ưu tiên
            # title_pub (mới), lùi title_en (mẫu cũ) -> giữ tương thích.
            "title_en": str(r.get("title_pub") or r.get("title_en") or "").strip(),
            "hook": str(r.get("hook", "")).strip(),
            "score": float(r.get("score", 60)),
            "reason": str(r.get("reason", "")).strip(),
            "segments": segments,
        }
    except (KeyError, ValueError, TypeError, IndexError):
        return None


def _llm_select_clips(transcript: dict, duration: float, ctx=None,
                      scenes: dict = None, cfg: dict = None) -> list:
    """
    AI tự chọn các clip hay: CHIA transcript thành nhiều khúc, gọi LLM từng khúc
    (prompt gọn -> model local trả ổn định), rồi GỘP. Mỗi clip có thể gồm nhiều
    'segments' (ghép đoạn hay, bỏ đoạn thừa); đầu/cuối được SNAP vào ranh giới
    câu nói + cảnh thật của video gốc để cắt sạch. Trả list theo thứ tự thời gian.
    """
    if not llm.is_configured():
        return []
    segs = (transcript or {}).get("segments", [])
    if not segs:
        return []
    cfg = cfg or {}
    min_len = float(cfg.get("min_len", 60.0))
    max_len = float(cfg.get("max_len", 0.0) or 0.0)
    count = int(cfg.get("count", 0) or 0)          # số clip muốn cắt (0 = tự động)
    purpose = cfg.get("purpose", "")
    style = cfg.get("style", "")
    boundaries = _natural_boundaries(transcript, scenes)
    lang_name = _lang_name((transcript or {}).get("language", ""))
    chunks = _chunk_transcript(segs)
    all_clips: list = []
    errors: list[str] = []
    for ci, listing in enumerate(chunks):
        if ctx is not None:
            frac = ci / max(1, len(chunks))
            ctx.progress(0.30 + 0.25 * frac,
                         f"AI đọc & chọn đoạn hay (phần {ci + 1}/{len(chunks)})...")
        try:
            data = llm.complete_json(
                _select_prompt(listing, lang_name, purpose, style, min_len,
                               max_len, count),
                system=_SEL_SYSTEM)
        except Exception as e:  # noqa: BLE001 - gom lỗi, không làm sập job
            errors.append(str(e))
            continue
        rows = data if isinstance(data, list) else (data.get("clips") or [data])
        for r in rows or []:
            clip = _normalize_clip(r, duration, boundaries, min_len, max_len)
            if clip:
                all_clips.append(clip)

    if not all_clips:
        if errors:  # LLM có cấu hình nhưng gọi lỗi -> để generate_highlights báo rõ
            raise llm.LLMError(errors[0])
        return []

    # Khử trùng lặp: các clip có điểm bắt đầu gần nhau (<8s) -> giữ điểm cao hơn
    all_clips.sort(key=lambda c: c["score"], reverse=True)
    kept: list = []
    for c in all_clips:
        s0 = c["segments"][0][0]
        if any(abs(s0 - k["segments"][0][0]) < 8.0 for k in kept):
            continue
        kept.append(c)
        if len(kept) >= (count if count > 0 else 12):  # đúng số user đặt (hoặc 12)
            break
    kept.sort(key=lambda c: c["segments"][0][0])  # theo thứ tự thời gian (Part 1,2,3)

    # PASS 2 — AI ĐỌC KỸ từng clip, cắt gọn bỏ phần thừa (hiểu nội dung, giữ đoạn đắt)
    refined = []
    for i, c in enumerate(kept):
        if ctx is not None:
            ctx.progress(0.55 + 0.05 * (i / max(1, len(kept))),
                         f"AI đọc kỹ & cắt gọn clip {i + 1}/{len(kept)}...")
        refined.append(_refine_clip(c, segs, duration, boundaries, min_len))
    return refined


def _vision_rescore(video_id: int, clips: list, ctx) -> list:
    """
    Chấm điểm bằng HÌNH ẢNH: trích 1 khung hình đại diện mỗi clip, cho model vision
    (Qwen2.5-VL) xem rồi chấm 0-100, TRỘN với điểm chữ. Lỗi -> giữ nguyên điểm chữ.
    """
    if not llm.vision_available() or not clips:
        return clips
    vrow = db.query_one(
        "SELECT v.src_path, p.assets_dir FROM videos v "
        "JOIN projects p ON p.id=v.project_id WHERE v.id=?", (video_id,))
    if not vrow:
        return clips
    from pathlib import Path as _P
    tmp = _P(vrow["assets_dir"])
    # chỉ XEM hình các clip điểm cao nhất (đỡ tốn) — tối đa 10
    order = sorted(range(len(clips)), key=lambda i: clips[i]["score"], reverse=True)
    pick = set(order[:10])
    frames = []
    for i, c in enumerate(clips):
        if i not in pick:
            continue
        s, e = c["segments"][0]
        fp = tmp / f"_vlf_{i}.jpg"
        if extract_frame(vrow["src_path"], (s + e) / 2, fp, width=384):
            frames.append((i, str(fp)))

    prompt_tpl = (
        "Mỗi ảnh là khung hình đại diện của một đoạn video ngắn (theo thứ tự "
        "#0, #1, ...). Chấm điểm tiềm năng VIRAL 0-100 dựa trên HÌNH ẢNH: hành "
        "động/cao trào, biểu cảm, độ hút mắt, bố cục. Trả JSON THUẦN: "
        '[{"index":0,"vscore":0-100}]')
    for b in range(0, len(frames), 4):  # batch 4 ảnh/lần
        batch = frames[b:b + 4]
        try:
            data = llm.complete_vision_json(prompt_tpl, [fp for _, fp in batch])
        except Exception:  # noqa: BLE001 - lỗi vision không làm sập; giữ điểm chữ
            continue
        rows = data if isinstance(data, list) else data.get("clips", [])
        for r in rows or []:
            try:
                local = int(r["index"])
                if 0 <= local < len(batch):
                    gi = batch[local][0]
                    vs = float(r.get("vscore", r.get("score", 50)))
                    clips[gi]["vscore"] = vs
            except (KeyError, ValueError, TypeError):
                continue

    for c in clips:
        if "vscore" in c:
            c["score"] = round(0.5 * c["score"] + 0.5 * c["vscore"], 1)
    for _, fp in frames:
        try:
            os.remove(fp)
        except OSError:
            pass
    return clips


def generate_highlights(payload: dict, ctx: JobContext) -> dict:
    """
    Handler job 'm1_highlights'.
    AI tự chọn clip (độ dài linh hoạt, bỏ đoạn thừa, ghép khúc hay). Nếu bật vision,
    chấm thêm bằng HÌNH ẢNH. Không có LLM -> heuristic (audio + cảnh).
    """
    video_id = int(payload["video_id"])
    cfg = {**DEFAULTS, **(payload.get("preset") or {})}

    ctx.progress(0.05, "Đọc kết quả phân tích...")
    transcript = get_analysis(video_id, "transcript") or {}
    audio = get_analysis(video_id, "audio") or {}
    scenes = get_analysis(video_id, "scenes") or {}
    vrow = db.query_one("SELECT duration FROM videos WHERE id=?", (video_id,))
    duration = float(vrow["duration"] or 0) if vrow else 0.0

    # ---- Ưu tiên: AI tự chọn clip + segments ----
    llm.reset_usage()                 # đếm token Gemini riêng cho video này
    prov = llm.active_provider()
    prov_name = {"gemini": "Gemini", "ollama": "Ollama (máy)", "groq": "Groq (mây)",
                 "openai": "OpenAI", "deepseek": "DeepSeek"}.get(prov, prov)
    ctx.progress(0.30, f"AI [{prov_name}] đang đọc nội dung & chọn đoạn hay...")
    llm_error = ""
    try:
        ai_clips = _llm_select_clips(transcript, duration, ctx, scenes, cfg)
    except llm.LLMError as e:  # gọi LLM lỗi thật -> báo rõ, vẫn lùi heuristic
        ai_clips = []
        llm_error = str(e)
    if ai_clips:
        from config import settings as _st
        # máy yếu: KHÔNG chấm điểm bằng hình (ngốn CPU + tốn lượt) -> chỉ dựa transcript
        used_vision = llm.vision_available() and not getattr(_st, "LIGHT_MODE", True)
        if used_vision:
            ctx.progress(0.6, f"AI [{prov_name}] đang XEM hình ảnh từng đoạn...")
            ai_clips = _vision_rescore(video_id, ai_clips, ctx)
            ai_clips.sort(key=lambda c: c["segments"][0][0])  # giữ thứ tự thời gian
        db.execute("DELETE FROM clips WHERE video_id=? AND status='suggested'",
                   (video_id,))
        clip_ids = []
        for c in ai_clips:
            segs = c["segments"]
            total = sum(e - s for s, e in segs)
            signals = {"segments": segs, "n_seg": len(segs), "llm_used": True,
                       "ai": prov, "ai_name": prov_name,
                       "vision": used_vision, "vscore": c.get("vscore"),
                       "title_en": c.get("title_en", ""), "hook": c.get("hook", ""),
                       "dur": round(total, 1)}
            cid = db.insert(
                """INSERT INTO clips (video_id, start_sec, end_sec, score, reason,
                                      title, transcript, signals, status)
                   VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
                (video_id, segs[0][0], segs[-1][1], round(c["score"], 1),
                 c["reason"], c["title"], "", db.dumps(signals)),
            )
            clip_ids.append(cid)
        msg = (f"AI [{prov_name}] chọn {len(clip_ids)} clip"
               + (" (có xem hình)" if used_vision else ""))
        cost = {}
        if prov == "gemini":            # CHI PHÍ ước tính cho video này
            u = llm.get_usage()
            vnd = llm.estimate_cost_vnd(u)
            tok = u["in"] + u["out"]
            msg += f" · tốn ~{tok:,} token ≈ {vnd:,}₫"
            cost = {"tokens": tok, "cost_vnd": vnd}
        ctx.progress(1.0, msg)
        return {"count": len(clip_ids), "clip_ids": clip_ids,
                "llm_used": True, "ai": prov, "vision": used_vision, **cost}

    # ---- Fallback heuristic (LLM chưa cấu hình HOẶC gọi lỗi) ----
    if llm_error:
        note = ("AI chọn clip gặp lỗi nên tạm dùng cắt cơ bản. Hãy kiểm tra Ollama "
                f"đang chạy rồi thử lại. (Chi tiết: {llm_error[:160]})")
    elif not llm.is_configured():
        note = "Chưa bật AI (Ollama). Đang dùng cắt cơ bản theo âm thanh/cảnh."
    else:
        note = ""
    return _generate_heuristic(video_id, cfg, transcript, audio, scenes,
                               duration, ctx, note=note)


def _generate_heuristic(video_id, cfg, transcript, audio, scenes, duration, ctx,
                        note: str = ""):
    """Bản dự phòng khi không có LLM: cửa sổ + chấm audio/cảnh (1 đoạn liền/clip)."""
    ctx.progress(0.5, "Tạo đoạn ứng viên (không có AI)...")
    candidates = _build_candidates(transcript, scenes, duration, cfg)
    if not candidates:
        return {"count": 0, "clip_ids": [], "note": "Không tạo được ứng viên."}
    candidates.sort(key=lambda c: _audio_score(audio, c["start"], c["end"]),
                    reverse=True)
    candidates = candidates[: cfg["max_candidates"]]
    candidates.sort(key=lambda c: c["start"])  # theo thứ tự thời gian

    db.execute("DELETE FROM clips WHERE video_id=? AND status='suggested'",
               (video_id,))
    clip_ids = []
    for c in candidates:
        a_s = _audio_score(audio, c["start"], c["end"])
        s_s = _scene_score(scenes, c["start"], c["end"])
        final = 0.6 * a_s + 0.4 * s_s
        signals = {"segments": [[c["start"], c["end"]]], "n_seg": 1,
                   "llm_used": False, "ai": "", "audio": round(a_s, 1),
                   "scene": round(s_s, 1)}
        cid = db.insert(
            """INSERT INTO clips (video_id, start_sec, end_sec, score, reason,
                                  title, transcript, signals, status)
               VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
            (video_id, c["start"], c["end"], round(final, 1),
             "Năng lượng/chuyển cảnh nổi bật.", "Clip", c["text"], db.dumps(signals)),
        )
        clip_ids.append(cid)
    msg = note or f"Đề xuất {len(clip_ids)} clip (cắt cơ bản)"
    ctx.progress(1.0, msg)
    return {"count": len(clip_ids), "clip_ids": clip_ids, "llm_used": False,
            "note": note}


# ============================================================
# MIXED-CUT — ghép nhiều khoảnh khắc hay nhất thành 1 clip dài
# ============================================================
def _moment_cx(faces: dict, start: float, end: float) -> float:
    """Tâm crop ngang trung bình (0..1) cho 1 đoạn, từ face-track."""
    kfs = face_track.crop_keyframes_for_range(faces or {}, start, end)
    xs = [k["cx"] for k in kfs if "cx" in k]
    return sum(xs) / len(xs) if xs else 0.5


def generate_mixed_cut(payload: dict, ctx: JobContext) -> dict:
    """
    Handler job 'm1_mixed_cut'.
    Chọn nhiều khoảnh khắc NGẮN điểm cao nhất khắp video, ghép theo thứ tự thời
    gian thành 1 clip dài (>1 phút). Lưu 1 dòng clip với signals.mode='mixed'.
    """
    video_id = int(payload["video_id"])
    cfg = {**DEFAULTS, **(payload.get("preset") or {})}

    ctx.progress(0.05, "Đọc kết quả phân tích...")
    transcript = get_analysis(video_id, "transcript") or {}
    audio = get_analysis(video_id, "audio") or {}
    scenes = get_analysis(video_id, "scenes") or {}
    faces = get_analysis(video_id, "faces") or {}

    vrow = db.query_one("SELECT duration FROM videos WHERE id=?", (video_id,))
    duration = float(vrow["duration"] or 0) if vrow else 0.0

    ctx.progress(0.15, "Tạo các khoảnh khắc ứng viên...")
    moment_cfg = {**cfg, "min_len": cfg["moment_min"], "max_len": cfg["moment_max"]}
    moments = _build_candidates(transcript, scenes, duration, moment_cfg)
    if len(moments) < 2:
        return {"count": 0, "note": "Video quá ngắn/ít nội dung để ghép."}

    # chấm điểm từng khoảnh khắc
    moments.sort(key=lambda c: _audio_score(audio, c["start"], c["end"]), reverse=True)
    moments = moments[: cfg["max_candidates"]]
    ctx.progress(0.4, f"AI chấm điểm {len(moments)} khoảnh khắc...")
    llm_map = _llm_scores(moments, transcript.get("language", ""))
    use_llm = bool(llm_map)

    scored = []
    for i, m in enumerate(moments):
        a_s = _audio_score(audio, m["start"], m["end"])
        s_s = _scene_score(scenes, m["start"], m["end"])
        l = llm_map.get(i, {})
        l_s = l.get("score", 50.0)
        final = (cfg["w_llm"] * l_s + cfg["w_audio"] * a_s + cfg["w_scene"] * s_s
                 if use_llm else 0.6 * a_s + 0.4 * s_s)
        scored.append({**m, "score": final, "title": l.get("title", "")})

    # chọn tham lam theo điểm, không chồng nhau, tới khi đủ độ dài
    ctx.progress(0.7, "Chọn & sắp xếp các đoạn hay nhất...")
    scored.sort(key=lambda x: x["score"], reverse=True)
    chosen, total = [], 0.0
    for m in scored:
        if any(not (m["end"] <= c["start"] or m["start"] >= c["end"]) for c in chosen):
            continue  # chồng lấn -> bỏ
        chosen.append(m)
        total += m["end"] - m["start"]
        if total >= cfg["mix_target_len"]:
            break
    if total > cfg["mix_max_len"]:
        chosen = chosen[:-1]

    if len(chosen) < 2:
        return {"count": 0, "note": "Không đủ đoạn hay để ghép."}

    chosen.sort(key=lambda x: x["start"])  # theo thứ tự thời gian

    moments_out = [{"start": round(m["start"], 2), "end": round(m["end"], 2),
                    "cx": round(_moment_cx(faces, m["start"], m["end"]), 4)}
                   for m in chosen]
    dur_total = sum(m["end"] - m["start"] for m in moments_out)
    best_title = max(chosen, key=lambda x: x["score"]).get("title", "")
    title = best_title or f"Mix {len(chosen)} khoảnh khắc hay"
    avg = round(sum(m["score"] for m in chosen) / len(chosen), 1)

    signals = {"mode": "mixed", "llm_used": use_llm,
               "moments": moments_out, "n": len(moments_out)}

    cid = db.insert(
        """INSERT INTO clips (video_id, start_sec, end_sec, score, reason, title,
                              transcript, signals, status)
           VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
        (video_id, moments_out[0]["start"], moments_out[-1]["end"], avg,
         f"Ghép {len(chosen)} đoạn điểm cao (~{dur_total:.0f}s).", title,
         " ".join(m.get("text", "") for m in chosen), db.dumps(signals)),
    )
    ctx.progress(1.0, f"Đã tạo Mixed-Cut ({len(chosen)} đoạn, {dur_total:.0f}s)")
    return {"count": 1, "clip_id": cid, "moments": len(chosen),
            "duration": round(dur_total, 1), "llm_used": use_llm}


# ============================================================
# Xuất clip 9:16 face-track
# ============================================================
def export_clip(payload: dict, ctx: JobContext) -> dict:
    """
    Handler job 'm1_export_clip'.
    payload: {clip_id, out_w?, out_h?}
    Đọc face-track đã cache -> crop bám mặt -> xuất 9:16.
    """
    clip_id = int(payload["clip_id"])
    clip = db.query_one("SELECT * FROM clips WHERE id=?", (clip_id,))
    if not clip:
        raise ValueError(f"Không tìm thấy clip id={clip_id}")

    video_id = clip["video_id"]
    vrow = db.query_one(
        """SELECT v.src_path, p.assets_dir, p.export_dir FROM videos v
           JOIN projects p ON p.id=v.project_id WHERE v.id=?""",
        (video_id,),
    )
    if not vrow:
        raise ValueError("Không tìm thấy video nguồn của clip.")

    src = vrow["src_path"]
    # MỖI VIDEO 1 FOLDER RIÊNG (tên theo video) trong KHO 'Đã xuất' chung -> gọn,
    # không lẫn. <kho>/Đã xuất/<tên video>/Part N <tiêu đề>.mp4
    # Ưu tiên out_dir (kho chung) > export_dir của kênh (cũ) > assets/clips.
    base = Path(payload.get("out_dir") or vrow["export_dir"]
                or (Path(vrow["assets_dir"]) / "clips"))
    vid_folder = _safe_name(Path(src).stem) or f"video_{video_id}"
    out_dir = base / vid_folder
    out_dir.mkdir(parents=True, exist_ok=True)
    part_no = int(payload.get("part_no", 0) or 0)
    safe = _safe_name(payload.get("out_name", "") or "")   # = "Part N <tiêu đề>"
    stem = safe or (f"Part {part_no}" if part_no > 0 else f"clip_{clip_id}")
    out_path = out_dir / f"{stem}.mp4"
    # CHỐNG TRÙNG TÊN: nếu đã có file KHÁC (video khác cùng tên Part+tiêu đề) -> thêm
    # số để KHÔNG ghi đè/lẫn sang video khác. Re-export chính clip này thì ghi đè.
    prev = clip["export_path"] or ""
    if out_path.exists() and str(out_path) != prev:
        k = 2
        while (out_dir / f"{stem} ({k}).mp4").exists():
            k += 1
        out_path = out_dir / f"{stem} ({k}).mp4"

    encoder = ctx.profile.get("encoder", "libx264")
    out_w = int(payload.get("out_w", DEFAULTS["out_w"]))
    out_h = int(payload.get("out_h", DEFAULTS["out_h"]))
    mode = payload.get("mode", "face")          # face|center|fit_blur|manual
    zoom = float(payload.get("zoom", 1.0))
    crop_rect = payload.get("crop_rect")        # (nx,ny,nw,nh) khi mode='manual'
    video_rect = payload.get("video_rect")      # (cx,cy,scale) khi mode='canvas'
    bg = payload.get("bg", "blur")              # blur|black|white
    text_overlays = payload.get("text_overlays") or []  # fallback drawtext
    overlay_png = payload.get("overlay_png")    # ảnh lớp chữ render từ UI
    signals = db.loads(clip["signals"], {}) or {}

    pfx = f"Part {part_no} — " if part_no > 0 else ""   # cho user biết đang xuất Part nào

    def on_prog(p: float):
        ctx.progress(0.15 + 0.8 * p, f"{pfx}đang cắt + chèn chữ + xuất 9:16...")

    if signals.get("mode") != "mixed" and video_rect:
        # ---- Mô hình CapCut: nền + khối video (ghép các khúc hay) ----
        segs = signals.get("segments") or [[clip["start_sec"], clip["end_sec"]]]
        pre_crop = None
        if payload.get("trim_black"):
            ctx.progress(0.08, f"{pfx}đang dò viền đen...")
            pre_crop = detect_black_crop(src, segs[0][0])
        # PHỤ ĐỀ CHẠY CHỮ khớp lời (từ mốc từng-từ của whisper, ánh xạ theo đoạn ghép)
        ass_path = fonts_dir = None
        if payload.get("captions"):
            from app.core import captions
            from config import ROOT_DIR
            tr = get_analysis(video_id, "transcript") or {}
            words = tr.get("words") or []
            if words:
                cdir = Path(vrow["assets_dir"]) / "_cache"
                cdir.mkdir(parents=True, exist_ok=True)
                ap = str(cdir / f"_cap_{clip_id}.ass")
                cs = payload.get("cap_style") or {}
                csize = float(cs.get("size") or 0)
                if captions.build_ass(
                        words, segs, ap, out_w, out_h,
                        font=cs.get("font") or "Montserrat",
                        size=int(csize * out_h) if csize < 1 else int(csize),
                        color=cs.get("color") or "",
                        ny=float(cs.get("ny", 0.78)),
                        preset=cs.get("preset") or "Trắng đơn giản",
                        delay=float(cs.get("delay", 0.12)),
                        hook=(signals.get("hook", "")
                              if cs.get("hook_on", True) else ""),
                        hook_dur=float(cs.get("hook_dur", 6.0))):
                    ass_path = ap
                    fonts_dir = str(ROOT_DIR / "app" / "assets" / "fonts")
        ctx.progress(0.15, f"{pfx}đang dựng khung (nền + video + phụ đề)...")
        export_canvas_clip(
            src, out_path, [(s, e) for s, e in segs],
            tuple(video_rect), bg=bg, out_w=out_w, out_h=out_h,
            encoder=encoder, overlay_png=overlay_png, pre_crop=pre_crop,
            ass_path=ass_path, fonts_dir=fonts_dir,
            blur_amt=int(payload.get("blur_amt", 22)),
            speed=float(payload.get("speed", 1.0)),
            pitch=float(payload.get("pitch", 1.0)),
            on_progress=on_prog,
        )
        result_extra = {"canvas": True, "bg": bg, "n_seg": len(segs),
                        "captions": bool(ass_path)}
    elif signals.get("mode") == "mixed":
        # ---- Mixed-Cut: ghép nhiều đoạn (crop thủ công không áp dụng) ----
        ctx.progress(0.1, f"{pfx}đang ghép các đoạn (Mixed-Cut)...")
        export_stitched_clip(
            src, out_path, signals.get("moments", []),
            out_w=out_w, out_h=out_h, encoder=encoder,
            mode=(mode if mode != "manual" else "face"), zoom=zoom,
            text_overlays=text_overlays, overlay_png=overlay_png,
            on_progress=on_prog,
        )
        result_extra = {"mixed": True, "moments": len(signals.get("moments", []))}
    else:
        # ---- clip đơn ----
        keyframes: Optional[list[dict]] = None
        if mode == "face":  # chỉ cần face-track khi bám mặt
            ctx.progress(0.05, "Đọc dữ liệu bám mặt...")
            faces = get_analysis(video_id, "faces")
            if faces:
                keyframes = face_track.crop_keyframes_for_range(
                    faces, clip["start_sec"], clip["end_sec"])
        ctx.progress(0.15, "Đang cắt + đặt khung 9:16 + encode...")
        export_vertical_clip(
            src, out_path, clip["start_sec"], clip["end_sec"],
            crop_keyframes=keyframes, out_w=out_w, out_h=out_h,
            encoder=encoder, mode=mode, zoom=zoom,
            crop_rect=tuple(crop_rect) if crop_rect else None,
            text_overlays=text_overlays, overlay_png=overlay_png,
            on_progress=on_prog,
        )
        result_extra = {"mode": mode}

    db.execute(
        "UPDATE clips SET status='exported', export_path=? WHERE id=?",
        (str(out_path), clip_id),
    )
    # dọn PNG lớp chữ tạm
    if overlay_png and os.path.basename(str(overlay_png)).startswith("_ovl_"):
        try:
            os.remove(overlay_png)
        except OSError:
            pass
    ctx.progress(1.0, "Đã xuất clip")
    return {"clip_id": clip_id, "export_path": str(out_path), **result_extra}


# ---- đăng ký handler với worker ----
register_handler("m1_highlights", generate_highlights)
register_handler("m1_mixed_cut", generate_mixed_cut)
register_handler("m1_export_clip", export_clip)
