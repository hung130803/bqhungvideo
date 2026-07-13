"""
MODULE 1 — AUTO CẮT HIGHLIGHT + FACE-TRACK CROP.

Chọn đoạn bằng 3 tín hiệu (đọc lại từ lõi phân tích đã cache, KHÔNG phân tích lại):
  1. audio peak (librosa)         -> đoạn năng lượng cao
  2. scene detection (PySceneDetect) -> mốc chuyển cảnh để cắt gọn
  3. transcript -> LLM chấm điểm "viral nhất" (JSON: điểm + lý do + tiêu đề)

Xuất: cắt + crop dọc 9:16 BÁM mặt người nói (face-track) trong 1 lệnh ffmpeg.

Handler đăng ký vào worker:
  - "m1_export_clip"  : xuất 1 clip ra file 9:16.
generate_highlights / generate_mixed_cut KHÔNG đăng ký trực tiếp — được job
"auto" / "auto_mixed" (app/queue/jobs.py) gọi sau bước phân tích.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from app.ai import llm
from app.ai import recap as _recap   # dùng chung pattern CTA/chào đa ngôn ngữ
from app.core import face_track
from app.core import vision_digest as _vd
from app.core.analysis import get_analysis
from app.core.ffmpeg_utils import (
    detect_black_crop, export_canvas_clip, export_stitched_clip,
    export_vertical_clip, extract_frame,
)
from app.database import db
from app.queue.worker import CanceledError, JobContext, register_handler

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
    return re.sub(r"\s+", " ", s).strip()[:limit].strip().strip(". ")  # bỏ chấm/cách cuối


# ============================================================
# Sinh ứng viên highlight
# ============================================================
def _build_candidates(transcript: dict, scenes: dict, duration: float,
                      cfg: dict) -> list[dict]:
    """Tạo các cửa sổ [start,end] có độ dài ĐA DẠNG trong [min,max] giây.

    MỖI ứng viên nhắm 1 độ dài NGẪU NHIÊN riêng (_target_len) trong [min,max]:
    gom câu tới khi ĐẠT ~target đó rồi mới cắt ở ranh giới câu/cảnh gần nhất.
    KHÔNG break ở min (đó là lỗi cũ làm mọi clip dồn về ~60s). Không tạo clip
    < min (trừ đoạn CUỐI video không đủ nội dung). Giữ dedup chồng lấn.
    """
    segs = (transcript or {}).get("segments", [])
    min_len, max_len = cfg["min_len"], cfg["max_len"]

    if not segs:
        # Không có transcript: chia theo độ dài NGẪU NHIÊN mỗi bước (đa dạng)
        out, t = [], 0.0
        while t + min_len <= duration:
            step = _target_len(min_len, max_len) or cfg["target_len"]
            out.append({"start": round(t, 2),
                        "end": round(min(t + step, duration), 2), "text": ""})
            t += step
        return out

    cut_points = set((scenes or {}).get("cut_points", []))

    candidates: list[dict] = []
    for a_idx, anchor in enumerate(segs):
        a = anchor["start"]
        # MỖI ứng viên có target NGẪU NHIÊN riêng -> độ dài trải đều [min,max].
        target = _target_len(min_len, max_len) or max_len or (min_len + 30.0)
        end, text_parts = a, []
        for s in segs:
            if s["end"] <= a:
                continue
            end = s["end"]
            text_parts.append(s["text"])
            length = end - a
            # CHỈ dừng khi đã đạt target riêng của ứng viên (KHÔNG dừng ở min).
            if length >= target:
                ends_sentence = s["text"].rstrip().endswith(_SENTENCE_END)
                near_cut = any(abs(end - c) < 0.6 for c in cut_points)
                # đã đủ dài + ở ranh giới sạch -> cắt; hoặc lố target đáng kể
                if ends_sentence or near_cut or length >= target + 8.0:
                    break
            if length >= max_len:              # chạm trần cứng -> dừng
                break
        length = end - a
        if length > max_len:                   # câu cuối lố trần -> ép về max
            end = round(a + max_len, 2)
            length = max_len
        # KHÔNG nhận clip < min (trừ đoạn cuối video: hết câu mà chưa đủ min).
        is_tail = end >= (segs[-1]["end"] - 0.5)
        if length >= min_len - 0.5 or (is_tail and length >= min_len * 0.5):
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
    lang_name = _lang_name(language)
    prompt = (
        f"Ngôn ngữ nội dung: {lang_name}.\n"
        f"Dưới đây là các đoạn ứng viên cắt từ 1 video dài:\n{listing}\n\n"
        "Chấm điểm sao cho khi lấy các đoạn điểm CAO sẽ RẢI ĐỀU toàn video "
        "(đầu/giữa/cuối) và nội dung ĐA DẠNG — ưu tiên khoảnh khắc KHÁC nhau, "
        "TRÁNH nhiều đoạn cùng 1 cảnh/chủ đề.\n"
        "Với MỖI đoạn, trả về một object trong mảng JSON:\n"
        '[{"index": số, "score": 0-100, "reason": "lý do ngắn gọn tiếng Việt", '
        '"title": "tiêu đề giật tít tiếng Việt (cho người dựng đọc)", '
        '"title_pub": "tiêu đề giật tít viết BẰNG ĐÚNG NGÔN NGỮ VIDEO"}]\n'
        f"QUY TẮC title_pub: viết bằng {lang_name.upper()} — ĐÚNG ngôn ngữ của "
        "lời thoại trong ngoặc kép ở trên (dùng để GẮN LÊN video), TUYỆT ĐỐI "
        "không dịch sang ngôn ngữ khác.\n"
        "Chỉ trả JSON, không thêm chữ nào khác."
    )
    try:
        data = llm.complete_json(prompt, system=system)
    except Exception:  # noqa: BLE001 - lỗi LLM KHÔNG được làm sập M1; lùi heuristic
        return {}
    out: dict[int, dict] = {}
    # LLM có thể trả JSON hợp lệ nhưng KHÔNG phải list/dict (chuỗi, số, null)
    # -> .get sẽ nổ AttributeError làm sập job thay vì lùi heuristic
    rows = (data if isinstance(data, list)
            else (data.get("clips", []) if isinstance(data, dict) else []))
    for r in rows or []:
        try:
            idx = int(r["index"])
            out[idx] = {
                "score": float(r.get("score", 50)),
                "reason": str(r.get("reason", "")).strip(),
                "title": str(r.get("title", "")).strip(),
                # tiêu đề GẮN LÊN video — đúng ngôn ngữ video (không phải Việt)
                "title_pub": str(r.get("title_pub", "")).strip(),
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


# Nhãn TIẾNG VIỆT của ngôn ngữ video cho prompt (đồng bộ danh sách code với
# recap._LANG_EN/_LANG_ALIAS — đủ pt/ar/hi/it/nl/tr/pl/uk/ms/tl/lo/km/my).
# Không nhận diện được -> _lang_name giữ fallback trả raw code như cũ.
_LANG_NAMES = {
    "vi": "tiếng Việt", "vietnamese": "tiếng Việt",
    "en": "tiếng Anh", "english": "tiếng Anh",
    "ja": "tiếng Nhật", "japanese": "tiếng Nhật",
    "ko": "tiếng Hàn", "korean": "tiếng Hàn",
    "zh": "tiếng Trung", "chinese": "tiếng Trung",
    "th": "tiếng Thái", "thai": "tiếng Thái",
    "fr": "tiếng Pháp", "french": "tiếng Pháp",
    "es": "tiếng Tây Ban Nha", "spanish": "tiếng Tây Ban Nha",
    "de": "tiếng Đức", "german": "tiếng Đức",
    "ru": "tiếng Nga", "russian": "tiếng Nga",
    "id": "tiếng Indonesia", "indonesian": "tiếng Indonesia",
    "pt": "tiếng Bồ Đào Nha", "portuguese": "tiếng Bồ Đào Nha",
    "ar": "tiếng Ả Rập", "arabic": "tiếng Ả Rập",
    "hi": "tiếng Hindi", "hindi": "tiếng Hindi",
    "it": "tiếng Ý", "italian": "tiếng Ý",
    "nl": "tiếng Hà Lan", "dutch": "tiếng Hà Lan",
    "tr": "tiếng Thổ Nhĩ Kỳ", "turkish": "tiếng Thổ Nhĩ Kỳ",
    "pl": "tiếng Ba Lan", "polish": "tiếng Ba Lan",
    "uk": "tiếng Ukraina", "ukrainian": "tiếng Ukraina",
    "ms": "tiếng Mã Lai", "malay": "tiếng Mã Lai",
    "tl": "tiếng Philippines (Tagalog)", "tagalog": "tiếng Philippines (Tagalog)",
    "filipino": "tiếng Philippines (Tagalog)",
    "lo": "tiếng Lào", "lao": "tiếng Lào",
    "km": "tiếng Khmer", "khmer": "tiếng Khmer",
    "my": "tiếng Miến Điện", "burmese": "tiếng Miến Điện",
    "myanmar": "tiếng Miến Điện",
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


def _target_len(min_len: float, max_len: float) -> float:
    """Độ dài MỤC TIÊU NGẪU NHIÊN cho MỖI clip trong khoảng [Min, Max] — để clip
    ĐA DẠNG (cái ngắn cái dài) thay vì dồn đều 1 con số. Nghiêng nhẹ về giữa-trên
    khoảng cho clip đủ 'đầy đặn' (dùng trung bình 2 lần random -> ít ra sát Min).
    Chỉ có Min -> [min, min*1.8]. Không có Min -> 0 (tự do)."""
    import random
    if min_len and min_len > 0 and max_len and max_len > min_len:
        lo, hi = min_len, max_len
        t = (random.uniform(lo, hi) + random.uniform(lo, hi)) / 2  # dồn về giữa
        return round(t, 1)
    if min_len and min_len > 0:
        hi = max_len if max_len else min_len * 1.8
        return round(random.uniform(min_len, max(min_len, hi)), 1)
    return 0.0


def _select_prompt(listing: str, lang_name: str = "ngôn ngữ gốc của video",
                   purpose: str = "", style: str = "",
                   min_len: float = 60.0, max_len: float = 0.0,
                   count: int = 0, visual_block: str = "") -> str:
    extra = ""
    if _PURPOSE_HINT.get(purpose):
        extra += "- " + _PURPOSE_HINT[purpose] + "\n"
    if _STYLE_HINT.get(style):
        extra += "- " + _STYLE_HINT[style] + "\n"
    # 👁 VISION DIGEST: AI đã "xem" khung hình khắp video -> chèn khối mô tả
    # cảnh + điểm hành động để chọn đoạn bằng CẢ MẮT (video ít thoại/nhiều
    # hành động không bị bỏ sót). visual_block rỗng -> prompt Y HỆT cũ.
    vis_part, vis_rule = "", ""
    if visual_block:
        vis_part = f"{visual_block}\n\n"
        vis_rule = (
            "- KẾT HỢP LỜI THOẠI + HÌNH ẢNH: khối 'HÌNH ẢNH THEO MỐC' mô tả "
            "cảnh trên màn hình tại từng giây kèm điểm hành động 0-10. Đoạn "
            "HÀNH ĐỘNG CAO (act>=7: rượt đuổi, va chạm, cao trào thị giác, "
            "khoảnh khắc sốc) RẤT ĐÁNG CHỌN kể cả khi ÍT LỜI THOẠI — đừng "
            "chỉ dựa vào lời nói.\n")
    how_many = (f"Chọn ĐÚNG {count} clip hay nhất" if count > 0
                else "Chọn 3-6 clip hay nhất")
    if min_len and min_len > 0:                 # có Min/Max -> độ dài ĐA DẠNG
        mx = f"{int(max_len)}" if max_len else "180"
        len_rule = (
            f"- ĐỘ DÀI: mỗi clip dài TỰ DO trong khoảng {int(min_len)}-{mx}s, "
            f"và NÊN KHÁC NHAU giữa các clip (cái ngắn ~{int(min_len)}s, cái dài "
            f"gần {mx}s) tùy nội dung — ĐỪNG làm đều tăm tắp cùng 1 độ dài. "
            f"{int(min_len)}s là SÀN CỨNG (không được ngắn hơn), {mx}s là TRẦN.\n"
            f"- LẤY TRỌN câu chuyện: phần dẫn dắt + diễn biến + cao trào + câu "
            f"chốt. ĐƯỢC GHÉP nhiều đoạn liên quan (nhiều khúc trong 'segments'). "
            f"Câu chuyện dài thì lấy dài (gần {mx}s), ngắn gọn thì thôi — miễn "
            f"trọn vẹn và hấp dẫn, ĐỪNG cắt cụt ở {int(min_len)}s.\n")
    else:                                       # Min=0 -> độ dài TỰ DO / ngẫu nhiên
        mxx = f" (không quá ~{int(max_len)} giây)" if max_len else ""
        len_rule = ("- ĐỘ DÀI: TỰ DO theo nội dung" + mxx + " — khoảnh khắc nào "
                    "hay thì lấy trọn, ngắn dài tuỳ nội dung, KHÔNG ép độ dài.\n")
    return (
        "Transcript (mỗi dòng: GIÂY_BẮT_ĐẦU GIÂY_KẾT_THÚC | lời nói):\n"
        f"{listing}\n\n"
        + vis_part +
        f"Video này nói bằng {lang_name.upper()}.\n"
        f"{how_many} trong đoạn này. QUY TẮC:\n"
        + extra + vis_rule +
        "- ĐA DẠNG + RẢI ĐỀU: chọn các đoạn RẢI ĐỀU toàn video (đầu / giữa / "
        "cuối), nội dung KHÁC NHAU — ĐỪNG chọn nhiều đoạn cùng 1 cảnh/chủ đề "
        "hay dồn cụm 1 chỗ; ưu tiên các khoảnh khắc KHÁC nhau cho phong phú.\n"
        "- Ưu tiên cảnh ĐỈNH ĐIỂM/cao trào, có hook ở đầu, giữ chân người xem.\n"
        "- TUYỆT ĐỐI TRÁNH RÁC KÊNH (bất kể ngôn ngữ): intro chào kênh/trailer "
        "nhá hàng mở đầu video, đoạn kêu gọi subscribe/like/bấm chuông/link mô "
        "tả/sponsor/quảng cáo, lời chào tạm biệt cuối video (\"thanks for "
        "watching\", \"see you in the next video\", \"チャンネル登録\", \"ご視聴"
        "ありがとう\", \"đăng ký kênh\"...). KHÔNG lấy các câu đó vào clip, càng "
        "KHÔNG đặt chúng ở ĐẦU hoặc CUỐI clip — clip phải mở bằng nội dung "
        "chuyện thật và kết ở câu chốt chuyện; hệ thống sẽ tự cắt bỏ đoạn rác.\n"
        "- CŨNG TRÁNH RÁC MỀM: đoạn đọc quảng cáo sponsor (\"this video is "
        "sponsored by...\", \"案件\"), khoe mốc subscriber/milestone, nhắc "
        "video trước/kênh phụ, giveaway, cảm ơn patron, mid-roll \"before we "
        "continue, make sure...\", nói lan man không có nội dung — đều là "
        "rác, KHÔNG lấy vào clip.\n"
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
        "- hook_time = MỐC GIÂY [bắt_đầu, kết_thúc] của khoảnh khắc CAO TRÀO/SỐC "
        "NHẤT trong clip (2-4 giây, phải nằm TRONG segments của clip) — dùng để "
        "chiếu 'nhá hàng' lên ĐẦU clip giữ chân người xem.\n"
        "Trả về ĐÚNG định dạng JSON này (mảng), không thêm chữ:\n"
        '[{"title":"tiêu đề tiếng Việt","title_pub":"tiêu đề giật tít bằng đúng ngôn '
        'ngữ video","hook":"câu hook ngắn giật tít","hook_time":[52,55],"score":85,'
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


# ------------------------------------------------------------------
# 🚮 NÉ RÁC KÊNH cho đường CẮT THƯỜNG (m1): intro chào kênh / trailer /
# outro kêu subscribe / sponsor / RÁC MỀM (đọc quảng cáo sponsor, khoe mốc
# subscriber, nhắc video trước, giveaway, cảm ơn patron). Dùng CHUNG pattern
# đa ngôn ngữ với recap (_is_cta_text + _is_greeting_text + _is_promo_text).
# NGUYÊN TẮC FAIL-SAFE: mọi lọc chỉ chạy khi vẫn còn clip hợp lệ; clip duy
# nhất / video toàn CTA -> giữ như cũ (không phá pipeline đang chạy).
# ------------------------------------------------------------------
_EDGE_TRIM_MAX_SENT = 3     # tối đa số câu rác được snap bỏ ở MỖI mép clip


def _is_junk_sentence(text: str) -> bool:
    """Câu là RÁC KÊNH: kêu gọi subscribe/like/sponsor (CTA), lời chào mở
    kênh (greeting), hoặc RÁC MỀM promo/housekeeping (đọc quảng cáo sponsor,
    khoe mốc subscriber, nhắc video trước/kênh phụ, giveaway, cảm ơn patron)
    — đa ngôn ngữ. Hàm thuần."""
    return (_recap._is_cta_text(text) or _recap._is_greeting_text(text)
            or _recap._is_promo_text(text))


def _junk_ratio(segments: list, segs: list) -> float:
    """Tỉ lệ (0..1) số TỪ thuộc câu CTA/chào kênh/promo trong các câu
    transcript giao với `segments` của clip (CJK-aware). Hàm thuần."""
    tot = junk = 0
    for _st, _en, t in _clip_sentences(segments, segs):
        if not t:
            continue
        n = len(_recap._word_tokens(_recap._norm_for_copy(t)))
        tot += n
        if _is_junk_sentence(t):
            junk += n
    return (junk / tot) if tot else 0.0


def _trim_junk_edges(segments: list, segs: list, min_len: float = 0.0) -> list:
    """SNAP mép clip bỏ câu CTA/chào kênh ở ĐẦU/CUỐI clip: câu ĐẦU là rác
    -> dịch start qua hết câu đó; câu CUỐI là rác -> rút end về trước câu
    đó (tối đa _EDGE_TRIM_MAX_SENT câu mỗi mép). CHỈ cắt khi tổng còn lại
    >= min_len - 2s (min_len=0 -> sàn 15s); không đủ -> GIỮ NGUYÊN mép đó
    (đừng phá clip — fail-safe). Luôn trả list KHÔNG rỗng. Hàm thuần."""
    if not segments or not segs:
        return segments
    floor = (min_len - 2.0) if (min_len and min_len > 0) else 15.0
    cur = [[float(s), float(e)] for s, e in segments]
    cur.sort(key=lambda x: x[0])

    def _total(ss):
        return sum(e - s for s, e in ss)

    def _clean(ss):                     # bỏ khúc teo (<1s) sau khi dịch mép
        return [[round(s, 2), round(e, 2)] for s, e in ss if e - s >= 1.0]

    for _ in range(_EDGE_TRIM_MAX_SENT):            # ---- mép ĐẦU ----
        sents = _clip_sentences(cur, segs)
        if not sents:
            break
        st, en, txt = sents[0]
        # câu rác phải GIAO khúc ĐẦU của clip (không phải khúc sau)
        if (not txt or not _is_junk_sentence(txt)
                or st >= cur[0][1] - 0.01 or en <= cur[0][0] + 0.01):
            break
        cand = [list(s) for s in cur]
        cand[0][0] = max(cand[0][0], en)            # dịch start qua câu rác
        cand = _clean(cand)
        if not cand or _total(cand) < floor:
            break                                   # cắt nữa là phá -> thôi
        cur = cand
    for _ in range(_EDGE_TRIM_MAX_SENT):            # ---- mép CUỐI ----
        sents = _clip_sentences(cur, segs)
        if not sents:
            break
        st, en, txt = sents[-1]
        if (not txt or not _is_junk_sentence(txt)
                or st >= cur[-1][1] - 0.01 or en <= cur[-1][0] + 0.01):
            break
        cand = [list(s) for s in cur]
        cand[-1][1] = min(cand[-1][1], st)          # rút end về trước câu rác
        cand = _clean(cand)
        if not cand or _total(cand) < floor:
            break
        cur = cand
    return [[round(s, 2), round(e, 2)] for s, e in cur]


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
        "- BỎ: câu lan man, lặp lại, dài dòng, lạc đề, mở đầu/kết thúc thừa; "
        "lời chào kênh/kêu gọi subscribe/like/link mô tả/sponsor (mọi ngôn "
        "ngữ); đoạn đọc quảng cáo sponsor, khoe mốc subscriber, nhắc video "
        "trước, giveaway, cảm ơn patron — nhất là khi nó nằm ở đầu/cuối clip.\n"
        "- CHỈ bỏ câu THẬT SỰ thừa — GIỮ độ dài gần như hiện tại, ĐỪNG cắt "
        "ngắn clip đi nhiều (không rút xuống dưới ~85% độ dài đang có).\n"
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
        except (ValueError, TypeError, IndexError, KeyError):
            # KeyError: LLM trả list DICT ({"start":...}) thay vì cặp số —
            # bỏ phần tử đó, đừng sập cả job vì 1 câu trả lời lệch dạng.
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
    # PASS 2 CHỈ được DỌN NHẸ (bỏ câu thừa), KHÔNG được gọt mất độ dài đã nới ở
    # PASS 1. Trước đây cho tỉa tới 30% -> clip 126s bị gọt về ~65s (hủy công
    # nới, clip toàn ~1p). Giờ chỉ cho tỉa tối đa ~15%; rút nhiều hơn -> giữ gốc.
    if (total < 40 or total < 0.85 * orig
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


def _extend_to_target(segments: list, segs: list, target: float,
                      max_len: float = 0.0, gap_stop: float = 6.0,
                      hard_gap: float = 8.0) -> list:
    """NỚI THÔNG MINH đoạn CUỐI bằng các CÂU transcript KẾ TIẾP (câu thật) cho tới
    khi tổng độ dài đạt ~target. Clip là multi-segment nên khoảng lặng KHÔNG phải
    rào cản chính: BẮC QUA khoảng lặng vừa (tới gap_stop~6s) bằng cách MỞ đoạn mới
    (không chèn im lặng — chỉ tính từ câu tiếp). Dừng khi: đạt target, chạm max_len,
    hết câu, hoặc gặp gap CỰC lớn (>hard_gap = đổi cảnh hẳn)."""
    if not target or target <= 0 or not segments or not segs:
        return segments
    out = [list(s) for s in segments]
    total = sum(e - s for s, e in out)
    if total >= target:
        return out
    ordered = sorted(segs, key=lambda s: float(s["start"]))
    cur_end = out[-1][1]
    for s in ordered:
        st, en = float(s["start"]), float(s["end"])
        if en <= cur_end + 0.05:            # câu đã nằm trong/trước đoạn cuối
            continue
        gap = st - cur_end
        if gap > hard_gap:                  # gap CỰC lớn -> dừng (đổi cảnh hẳn)
            break
        # 🚮 câu chạm tới là CTA/chào kênh (outro "subscribe...") -> DỪNG nới,
        # đừng nuốt đoạn rác vào clip (thiếu độ dài đã có _enforce_len lo).
        if _is_junk_sentence(str(s.get("text") or "")):
            break
        if gap <= gap_stop:
            add = en - cur_end              # gap nhỏ/vừa -> kéo dài đoạn hiện tại
            if max_len and total + add > max_len + 0.5:
                break                       # sẽ vượt trần -> dừng (giữ trọn câu)
            out[-1][1] = round(en, 2)
            total += add
        else:
            # gap vừa-lớn (gap_stop..hard_gap): bắc qua bằng đoạn MỚI (không tính
            # phần im lặng vào tổng, chỉ tính lời nói thật -> không phình max).
            add = en - st
            if max_len and total + add > max_len + 0.5:
                break
            out.append([round(st, 2), round(en, 2)])
            total += add
        cur_end = en
        if total >= target:
            break
    return out


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


def _enforce_len(segments: list, min_len: float, max_len: float,
                 duration: float, boundaries=None) -> tuple[list, str]:
    """RÀO CHẮN CUỐI CÙNG — ép TỔNG độ dài clip vào [min_len, max_len].

    Chạy SAU MỌI bước (LLM chọn / heuristic / refine / dedup / extend) ngay
    trước khi lưu clip. Bảo đảm TUYỆT ĐỐI (biên độ ±2s cho mép câu):
      - Tổng > max_len -> CẮT khúc cuối về <= max_len (bám mép câu nếu có).
      - Tổng < min_len -> NỚI: kéo dài khúc CUỐI về sau tới hết video, còn
        thiếu thì kéo khúc ĐẦU về trước. Ưu tiên dừng ở ranh giới câu/cảnh
        (boundaries) trong ±2s; hết chỗ (đầu/cuối video) -> nới tối đa có
        thể, trả note để caller log 'không đủ dài'.

    Trả (segments_moi, note). note != "" khi KHÔNG nới nổi tới min_len (video
    ngắn hơn min). Hàm thuần (chỉ dùng duration/boundaries) — unit test được.
    """
    if not segments:
        return segments, ""
    segs = [[float(s), float(e)] for s, e in segments]
    segs.sort(key=lambda x: x[0])
    note = ""

    def _total(ss):
        return sum(e - s for s, e in ss)

    # ---- 1) CẮT nếu quá max ----
    if max_len and max_len > 0 and _total(segs) > max_len + 2.0:
        segs = [[round(s, 2), round(e, 2)]
                for s, e in _cap_max_duration(segs, max_len)]

    # ---- 2) NỚI nếu dưới min ----
    def _snap_up(t):
        """Đẩy mốc CUỐI lên ranh giới câu GẦN NHẤT trong [t, t+2]."""
        if not boundaries:
            return t
        cands = [b for b in boundaries if t - 0.05 <= b <= t + 2.0]
        return max(cands) if cands else t

    def _snap_down(t):
        """Đẩy mốc ĐẦU xuống ranh giới câu GẦN NHẤT trong [t-2, t]."""
        if not boundaries:
            return t
        cands = [b for b in boundaries if t - 2.0 <= b <= t + 0.05]
        return min(cands) if cands else t

    if min_len and min_len > 0 and _total(segs) < min_len - 2.0:
        deficit = min_len - _total(segs)
        # 2a) nới khúc CUỐI về sau (tới hết video)
        last_end = segs[-1][1]
        room_fwd = max(0.0, duration - last_end)
        add = min(room_fwd, deficit)
        if add > 0.01:
            new_end = _snap_up(last_end + add)
            new_end = min(new_end, duration)
            if new_end - last_end < add - 0.5:   # snap kéo NGẮN lại -> bỏ snap
                new_end = min(last_end + add, duration)
            segs[-1][1] = round(new_end, 2)
            deficit = min_len - _total(segs)
        # 2b) còn thiếu -> nới khúc ĐẦU về trước
        if deficit > 0.5:
            first_start = segs[0][0]
            room_bwd = max(0.0, first_start)
            add2 = min(room_bwd, deficit)
            if add2 > 0.01:
                new_start = _snap_down(first_start - add2)
                new_start = max(0.0, new_start)
                if first_start - new_start < add2 - 0.5:
                    new_start = max(0.0, first_start - add2)
                segs[0][0] = round(new_start, 2)
                deficit = min_len - _total(segs)
        if deficit > 2.0:                        # vẫn thiếu -> video quá ngắn
            note = (f"clip chỉ dài {_total(segs):.0f}s (< {min_len:.0f}s yêu "
                    f"cầu) — video/đoạn không đủ dài để nới")
    return [[round(s, 2), round(e, 2)] for s, e in segs], note


def _normalize_clip(r, duration: float, boundaries=None,
                    min_len: float = 60.0, max_len: float = 0.0,
                    segs: list = None) -> Optional[dict]:
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
        # NỚI THÔNG MINH: LLM hay chọn đoạn ngắn ~min -> nếu còn ngắn hơn TARGET
        # đáng kể (<target*0.8), mở rộng đoạn cuối bằng các CÂU transcript kế tiếp
        # (câu thật) tới ~target/max. Không phụ thuộc LLM nghe lời.
        target = _target_len(min_len, max_len)
        if target and segs:
            cur = sum(e - s for s, e in segments)
            if cur < target * 0.8:
                segments = _extend_to_target(segments, segs, target, max_len)
                if boundaries:                     # snap lại ranh giới sau khi nới
                    segments = _snap_segments(segments, boundaries)
                    segments = _smooth_segments(segments)
        segments = _ensure_min_duration(segments, duration, min_len)  # >= Min user đặt
        segments = _cap_max_duration(segments, max_len)               # <= Max user đặt
        # hook_time: mốc cao trào 2-4s NẰM TRONG segments -> dùng cho hook-first
        hook_seg = None
        ht = r.get("hook_time")
        if isinstance(ht, (list, tuple)) and len(ht) >= 2:
            try:
                hs, he = float(ht[0]), float(ht[1])
                if he - hs >= 1.0:
                    he = min(he, hs + 4.0)          # tối đa 4s
                    inside = any(s - 0.5 <= hs and he <= e + 0.5
                                 for s, e in segments)
                    if inside:
                        hook_seg = [round(hs, 2), round(he, 2)]
            except (ValueError, TypeError):
                pass
        return {
            "title": str(r.get("title", "")).strip() or "Clip",
            # title_en = TIÊU ĐỀ GẮN LÊN VIDEO (theo NGÔN NGỮ video); ưu tiên
            # title_pub (mới), lùi title_en (mẫu cũ) -> giữ tương thích.
            "title_en": str(r.get("title_pub") or r.get("title_en") or "").strip(),
            "hook": str(r.get("hook", "")).strip(),
            "hook_seg": hook_seg,
            "score": float(r.get("score", 60)),
            "reason": str(r.get("reason", "")).strip(),
            "segments": segments,
        }
    except (KeyError, ValueError, TypeError, IndexError):
        return None


def _chunk_span(listing: str) -> tuple:
    """(t0, t1) của 1 chunk transcript ('bd kt | lời' mỗi dòng) — để lọc
    digest đúng khoảng thời gian chunk. Không parse được -> (None, None)
    (format_digest_block sẽ lấy toàn bộ). Hàm thuần."""
    t0 = t1 = None
    for ln in (listing or "").splitlines():
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*\|", ln)
        if not m:
            continue
        a, b = float(m.group(1)), float(m.group(2))
        t0 = a if t0 is None else min(t0, a)
        t1 = b if t1 is None else max(t1, b)
    return t0, t1


def _llm_select_clips(transcript: dict, duration: float, ctx=None,
                      scenes: dict = None, cfg: dict = None,
                      digest: list = None) -> list:
    """
    AI tự chọn các clip hay: CHIA transcript thành nhiều khúc, gọi LLM từng khúc
    (prompt gọn -> model local trả ổn định), rồi GỘP. Mỗi clip có thể gồm nhiều
    'segments' (ghép đoạn hay, bỏ đoạn thừa); đầu/cuối được SNAP vào ranh giới
    câu nói + cảnh thật của video gốc để cắt sạch. Trả list theo thứ tự thời gian.
    digest: VISION DIGEST (app/core/vision_digest) — có thì chèn khối 'HÌNH ẢNH
    THEO MỐC' của đúng khoảng chunk vào prompt; rỗng/None -> prompt Y HỆT cũ.
    """
    if not llm.is_configured():
        return [], []
    segs = (transcript or {}).get("segments", [])
    if not segs:
        return [], []
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
        vis_block = ""
        if digest:                      # 👁 khối hình ảnh ĐÚNG khoảng chunk này
            _t0, _t1 = _chunk_span(listing)
            pad = 10.0                  # nới nhẹ 2 mép (frame giữa cảnh sát mép)
            vis_block = _vd.format_digest_block(
                digest,
                None if _t0 is None else _t0 - pad,
                None if _t1 is None else _t1 + pad)
        try:
            data = llm.complete_json(
                _select_prompt(listing, lang_name, purpose, style, min_len,
                               max_len, count, visual_block=vis_block),
                system=_SEL_SYSTEM)
        except Exception as e:  # noqa: BLE001 - gom lỗi, không làm sập job
            errors.append(str(e))
            continue
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("clips") or [data]
        else:               # JSON scalar (chuỗi/số/null) -> chunk này không có clip
            rows = []
        for r in rows or []:
            clip = _normalize_clip(r, duration, boundaries, min_len, max_len,
                                   segs)
            if clip:
                # 🚮 SNAP mép: câu đầu/cuối clip là CTA/chào kênh -> dịch mép
                # bỏ câu đó (giữ >= min_len; không đủ thì giữ nguyên mép).
                clip["segments"] = _trim_junk_edges(clip["segments"], segs,
                                                    min_len)
                all_clips.append(clip)

    if not all_clips:
        if errors:  # LLM có cấu hình nhưng gọi lỗi -> để generate_highlights báo rõ
            raise llm.LLMError(errors[0])
        return [], []

    # 🚮 LOẠI clip TOÀN rác kênh (>30% từ là CTA/chào — như validate_windows
    # bên reup). FAIL-SAFE: lọc mà hết sạch (clip duy nhất toàn CTA / video
    # toàn CTA) -> giữ như cũ, không phá pipeline.
    _clean = [c for c in all_clips
              if _junk_ratio(c["segments"], segs) <= _recap._CTA_MAX]
    if _clean:
        all_clips = _clean

    # Khử TRÙNG NỘI DUNG: giữ clip điểm cao trước, BỎ clip nào ĐÈ LÊN clip đã
    # giữ. So theo TOÀN KHOẢNG [đầu..cuối] chứ không chỉ điểm bắt đầu — vì clip
    # đã được nới dài (tới ~target) nên 2 clip bắt đầu cách xa vẫn có thể chồng
    # 40-50s -> Part 1 & Part 2 bị trùng đoạn. Bỏ nếu chồng > 25% clip ngắn hơn.
    def _span(c):
        return c["segments"][0][0], c["segments"][-1][1]

    all_clips.sort(key=lambda c: c["score"], reverse=True)
    kept: list = []
    for c in all_clips:
        cs, ce = _span(c)
        clash = False
        for k in kept:
            ks, ke = _span(k)
            ov = min(ce, ke) - max(cs, ks)          # độ chồng lấn (giây)
            if ov > 0 and ov > 0.25 * min(ce - cs, ke - ks):
                clash = True
                break
        if clash:
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
    # Trả kèm lỗi từng chunk: video dài hết quota giữa chừng -> nửa sau video
    # KHÔNG được AI đọc; phải cảnh báo chứ không được im lặng báo thành công.
    warns = ([f"{len(errors)}/{len(chunks)} phần transcript gọi AI lỗi "
              f"(phần sau video có thể chưa được phân tích)"]
             if errors else [])
    return refined, warns


# ------------------------------------------------------------------
# 🔁 NHIỀU-PASS CẮT CLIP (v8): sau khi có danh sách clip ứng viên, AI ĐỌC
# LẠI toàn cảnh + CHẤM/CHỌN top viral, loại clip trùng/lê thê. FAIL-SAFE:
# chỉ LỌC + SẮP XẾP LẠI (KHÔNG đổi start/end), keo rỗng/hỏng -> giữ nguyên;
# lỗi bất kỳ -> giữ nguyên. Bù đủ want_n từ danh sách gốc nếu thiếu.
# ------------------------------------------------------------------
_REFINE_SEL_SYSTEM = (
    "Bạn là giám khảo chọn clip viral cho TikTok/Reels/Shorts. Từ danh sách "
    "clip ứng viên, chọn ra các clip TỐT NHẤT (hook mạnh, tự đủ, tiềm năng "
    "viral, không trùng nhau). CHỈ trả JSON, không thêm chữ.")


def _clip_digest(clips: list, segs: list, vdigest: list = None) -> str:
    """Tóm tắt từng clip cho critic đọc: index, mốc đầu-cuối, 1-2 câu mở đầu +
    1 câu ở giữa/cao trào (lấy từ transcript segs theo thời gian). vdigest
    (vision) có -> thêm tối đa 2 dòng 'hình: desc(act)' của khung trong clip."""
    def _sent_at(t0: float, t1: float, n: int = 1) -> str:
        picked = []
        for s in segs:
            try:
                a = float(s.get("start", 0))
            except (TypeError, ValueError):
                continue
            if t0 - 0.5 <= a <= t1 + 0.5:
                txt = str(s.get("text") or "").strip()
                if txt:
                    picked.append(txt)
                if len(picked) >= n:
                    break
        return " ".join(picked)[:180]

    lines = []
    for i, c in enumerate(clips):
        try:
            cs = c["segments"][0][0]
            ce = c["segments"][-1][1]
        except (KeyError, IndexError, TypeError):
            cs = ce = 0.0
        mid = (cs + ce) / 2.0
        opener = _sent_at(cs, cs + 12.0, 2)
        climax = _sent_at(mid, ce, 1)
        vis = ""
        if vdigest:                     # 👁 vài dòng hình ảnh của đúng clip này
            ent = [d for d in vdigest
                   if cs <= float(d.get("t", -1)) <= ce][:2]
            if ent:
                vis = " | hình: " + "; ".join(
                    f"{str(d.get('desc', ''))[:60]} (act {d.get('act', 0)})"
                    for d in ent)
        lines.append(
            f"[{i}] {cs:.0f}-{ce:.0f}s | mở đầu: {opener} | cao trào: {climax}"
            + vis)
    return "\n".join(lines)


def _parse_unusable(data, n: int) -> set:
    """Đọc trường 'usable' từ JSON critic -> tập index KHÔNG đáng đăng
    (usable=false). FAIL-SAFE: dạng lạ / index sai -> bỏ qua; TẤT CẢ clip
    đều false -> trả set rỗng (giữ như cũ, đừng trắng tay). Hàm thuần."""
    raw = data.get("usable") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return set()
    bad: set = set()
    for k, v in raw.items():
        try:
            idx = int(k)
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < n):
            continue
        if v is False or (isinstance(v, str)
                          and v.strip().lower() in ("false", "no", "0")):
            bad.add(idx)
    if len(bad) >= n:                  # tất cả false -> fail-safe giữ như cũ
        return set()
    return bad


def _refine_clip_selection(clips: list, transcript: dict, language: str,
                           want_n: int, min_len: float, max_len: float,
                           vdigest: list = None) -> list:
    """NHIỀU-PASS: AI chấm + chọn top clip. Trả list ĐÃ LỌC + SẮP XẾP theo độ
    hay (KHÔNG đổi start/end). Fail-safe: keep rỗng/không hợp lệ / lỗi -> trả
    NGUYÊN `clips`. Bù đủ want_n từ danh sách gốc (thứ tự cũ) nếu thiếu.
    Bounded: đúng 1 lần gọi LLM, KHÔNG lặp."""
    try:
        if not clips or len(clips) <= 1:
            return clips
        segs = (transcript or {}).get("segments", []) or []
        lang_name = _lang_name(language)
        auto = not (want_n and want_n > 0)   # want_n<=0 = AI tự quyết số clip
        target_n = len(clips) if auto else want_n
        digest = _clip_digest(clips, segs, vdigest)
        prompt = (
            f"Video nói bằng {lang_name.upper()}. Dưới đây là {len(clips)} "
            "clip ỨNG VIÊN (đã có mốc thời gian cố định, KHÔNG đổi được):\n"
            f"{digest}\n\n"
            "Hãy CHẤM & CHỌN theo tiêu chí:\n"
            "- HOOK 3 giây đầu phải mạnh (gây tò mò/sốc ngay).\n"
            "- Câu chuyện TỰ ĐỦ: xem KHÔNG cần biết bối cảnh trước đó.\n"
            "- Tiềm năng VIRAL cao (cảm xúc, twist, cao trào, câu chốt đắt).\n"
            "- KHÔNG lê thê/khoảng chết.\n"
            "- KHÔNG dính RÁC KÊNH: intro chào kênh/trailer mở đầu, kêu gọi "
            "subscribe/like/link mô tả/sponsor, lời tạm biệt cuối video — "
            "clip mở đầu hay kết thúc bằng mấy đoạn đó phải xếp KÉM/drop.\n"
            "- KHÔNG dính RÁC MỀM: đoạn đọc quảng cáo sponsor, khoe mốc "
            "subscriber, nhắc video trước, giveaway, cảm ơn patron, nói lan "
            "man không có nội dung — clip dính mấy đoạn đó đánh usable=false.\n"
            "- 2 clip KHÔNG trùng nội dung (tránh nhàm + ăn bản quyền).\n"
            f"Chọn tối đa {target_n} clip TỐT NHẤT. Trả DUY NHẤT 1 JSON: "
            '{"keep":[index theo thứ tự TỐT->kém], "drop":[index yếu/trùng], '
            '"usable":{"index":true/false — clip có ĐÁNG ĐĂNG không (false '
            'nếu dính quảng cáo/rác/lan man không dùng được)}, '
            '"reason":{"index":"lý do ngắn"}}')
        data = llm.complete_json(prompt, system=_REFINE_SEL_SYSTEM)
        keep_raw = None
        if isinstance(data, dict):
            keep_raw = data.get("keep")
        if not isinstance(keep_raw, list):
            return clips               # JSON không có keep hợp lệ -> giữ nguyên
        # chỉ nhận index HỢP LỆ, dedup giữ thứ tự (thứ tự tốt->kém của AI)
        seen: set = set()
        order: list = []
        for x in keep_raw:
            try:
                idx = int(x)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(clips) and idx not in seen:
                seen.add(idx)
                order.append(idx)
        if not order:
            return clips               # keep rỗng/không hợp lệ -> giữ nguyên
        # 🚮 usable=false (clip dính quảng cáo/rác/lan man) -> DROP khi còn
        # clip khác thay; tất cả false / drop hết -> giữ order như cũ.
        unusable = _parse_unusable(data, len(clips))
        if unusable:
            filt = [i for i in order if i not in unusable]
            if filt:                   # còn clip thay thế -> mới dám drop
                order = filt
        picked = [clips[i] for i in order]
        if auto:
            return picked              # AI tự quyết số clip -> không bù/không cắt
        # BÙ đủ want_n từ gốc (thứ tự cũ) nếu AI chọn thiếu — ưu tiên clip
        # KHÔNG bị đánh usable=false; vẫn thiếu mới đụng tới clip unusable.
        if len(picked) < target_n:
            for skip_bad in (True, False):
                for i, c in enumerate(clips):
                    if i in seen or (skip_bad and i in unusable):
                        continue
                    if not skip_bad and i not in unusable:
                        continue       # vòng 2 chỉ bù clip unusable còn lại
                    picked.append(c)
                    seen.add(i)
                    if len(picked) >= target_n:
                        break
                if len(picked) >= target_n:
                    break
        return picked[:target_n]
    except Exception:  # noqa: BLE001 - bất kỳ lỗi nào -> fail-safe giữ nguyên
        return clips


def _apply_quality_floor(clips: list, floor: float) -> tuple[list, int]:
    """SÀN CHẤT LƯỢNG: bỏ clip score < floor — "mọi đoạn thừa phải bỏ, CHỈ
    lấy đoạn hay dùng được". FAIL-SAFE: <2 clip hoặc floor<=0 -> giữ nguyên;
    tất cả dưới sàn -> vẫn GIỮ 1 clip điểm cao nhất (đừng trắng tay).
    Trả (clips_giữ, số_clip_bị_bỏ). Hàm thuần — unit test được."""
    if not clips or len(clips) < 2 or not floor or floor <= 0:
        return clips, 0
    kept = [c for c in clips if float(c.get("score", 0)) >= floor]
    if not kept:
        kept = [max(clips, key=lambda c: float(c.get("score", 0)))]
    return kept, len(clips) - len(kept)


def _digest_rescore(clips: list, vdigest: list) -> list:
    """Chấm điểm hình ảnh TỪ VISION DIGEST (không gọi vision lần 2 — digest đã
    xem cả video, KHÔNG chỉ 1 frame/clip như _vision_rescore cũ): vscore =
    trung bình act (0-10) của các khung trong khoảng clip × 10, trộn 50/50
    với điểm chữ (cùng công thức _vision_rescore). Clip không có khung nào
    trong khoảng -> giữ nguyên điểm chữ. Hàm thuần — unit test được."""
    for c in clips or []:
        try:
            cs, ce = c["segments"][0][0], c["segments"][-1][1]
        except (KeyError, IndexError, TypeError):
            continue
        acts = [float(d.get("act", 0)) for d in vdigest or []
                if cs <= float(d.get("t", -1)) <= ce]
        if not acts:
            continue
        c["vscore"] = round(10.0 * sum(acts) / len(acts), 1)
        c["score"] = round(0.5 * c["score"] + 0.5 * c["vscore"], 1)
    return clips


def _vision_rescore(video_id: int, clips: list, ctx) -> list:
    """
    Chấm điểm bằng HÌNH ẢNH: trích 1 khung hình đại diện mỗi clip, cho model vision
    (Qwen2.5-VL) xem rồi chấm 0-100, TRỘN với điểm chữ. Lỗi -> giữ nguyên điểm chữ.
    CHỈ còn dùng khi KHÔNG có vision digest (đường cũ) — có digest thì
    _digest_rescore thay thế, đỡ gọi vision trùng.
    """
    if not llm.vision_available() or not clips:
        return clips
    vrow = db.query_one(
        "SELECT v.src_path, p.assets_dir FROM videos v "
        "JOIN projects p ON p.id=v.project_id WHERE v.id=?", (video_id,))
    if not vrow:
        return clips
    from pathlib import Path as _P
    # ảnh tạm vào _cache (không lẫn folder người dùng) + tên theo video_id
    # (2 job song song 2 video cùng project sẽ không ghi đè ảnh của nhau)
    tmp = _P(vrow["assets_dir"]) / "_cache"
    tmp.mkdir(parents=True, exist_ok=True)
    # chỉ XEM hình các clip điểm cao nhất (đỡ tốn) — tối đa 10
    order = sorted(range(len(clips)), key=lambda i: clips[i]["score"], reverse=True)
    pick = set(order[:10])
    frames = []
    for i, c in enumerate(clips):
        if i not in pick:
            continue
        s, e = c["segments"][0]
        fp = tmp / f"_vlf_{video_id}_{i}.jpg"
        if extract_frame(vrow["src_path"], (s + e) / 2, fp, width=384):
            frames.append((i, str(fp)))

    prompt_tpl = (
        "Mỗi ảnh là khung hình đại diện của một đoạn video ngắn (theo thứ tự "
        "#0, #1, ...). Chấm điểm tiềm năng VIRAL 0-100 dựa trên HÌNH ẢNH: hành "
        "động/cao trào, biểu cảm, độ hút mắt, bố cục. Trả JSON THUẦN: "
        '[{"index":0,"vscore":0-100}]')
    for b in range(0, len(frames), 4):  # batch 4 ảnh/lần
        if ctx is not None:             # nhạy nút Hủy giữa các lượt gọi vision
            ctx.check_canceled()
        batch = frames[b:b + 4]
        try:
            data = llm.complete_vision_json(prompt_tpl, [fp for _, fp in batch])
        except Exception:  # noqa: BLE001 - lỗi vision không làm sập; giữ điểm chữ
            continue
        rows = (data if isinstance(data, list)
                else (data.get("clips", []) if isinstance(data, dict) else []))
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


def _delete_suggested(video_id: int) -> None:
    """Xóa clip gợi ý cũ TRỪ clip đang có job xuất chờ/chạy — nếu xóa, job xuất
    sẽ 'Không tìm thấy clip' và fail khó hiểu (race khi user bấm Tạo clip lại
    ngay lúc đang xuất)."""
    keep: set = set()
    for j in db.query(
            "SELECT payload FROM jobs WHERE type='m1_export_clip' "
            "AND status IN ('pending','running') AND video_id=?", (video_id,)):
        try:
            keep.add(int(db.loads(j["payload"], {}).get("clip_id")))
        except (TypeError, ValueError):
            pass
    if keep:
        ph = ",".join("?" * len(keep))
        db.execute(
            f"DELETE FROM clips WHERE video_id=? AND status='suggested' "
            f"AND id NOT IN ({ph})", (video_id, *keep))
    else:
        db.execute("DELETE FROM clips WHERE video_id=? AND status='suggested'",
                   (video_id,))


# ============================================================
# 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO (cross-run dedup)
# ============================================================
# Ngưỡng: ứng viên trùng > _USED_OVERLAP (30%) với 1 khoảng ĐÃ DÙNG -> loại
# (đường heuristic) / phạt nặng điểm (đường LLM). "Đã dùng" = mọi clip của
# video này đang ở trạng thái suggested/exported/done (kể cả lần bấm trước còn
# treo suggested) -> bấm Tạo clip / Reup lần sau ra đoạn KHÁC.
_USED_OVERLAP = 0.30
_USED_STATUSES = ("suggested", "exported", "done")


def _clip_used_ranges(signals: dict, start: float, end: float) -> list:
    """Rút CÁC KHOẢNG [s,e] mà 1 clip THẬT SỰ dùng từ signals (clip ghép nhiều
    đoạn: recap.windows / segments / moments) — lùi start_sec..end_sec nếu
    signals thiếu. Hàm thuần — test được."""
    out: list = []
    sig = signals if isinstance(signals, dict) else {}
    rec = sig.get("recap") if isinstance(sig.get("recap"), dict) else {}
    # ưu tiên windows recap (span thật của clip thuyết minh) -> segments -> moments
    for key, src in (("windows", rec), ("segments", sig)):
        for pair in (src.get(key) or []):
            try:
                s, e = float(pair[0]), float(pair[1])
            except (TypeError, ValueError, IndexError):
                continue
            if e > s:
                out.append([s, e])
        if out:
            return out
    for m in (sig.get("moments") or []):
        try:
            s, e = float(m["start"]), float(m["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if e > s:
            out.append([s, e])
    if out:
        return out
    # không có signals chi tiết -> dùng span thô của clip
    if end > start:
        return [[float(start), float(end)]]
    return []


def load_used_ranges(video_id: int, statuses=_USED_STATUSES) -> list:
    """Tập các khoảng [s,e] video này ĐÃ dùng ở các clip trước (mọi trạng thái
    trong `statuses`). Đọc từ clips.signals (segments/recap.windows/moments) —
    lùi start_sec/end_sec. Trả list đã sort tăng (chưa gộp). Gọi TRƯỚC khi
    _delete_suggested để giữ được các đoạn của lần bấm trước còn treo suggested.
    """
    if not statuses:
        return []
    ph = ",".join("?" * len(statuses))
    rows = db.query(
        f"SELECT start_sec, end_sec, signals FROM clips "
        f"WHERE video_id=? AND status IN ({ph})",
        (video_id, *statuses))
    used: list = []
    for r in rows or []:
        sig = db.loads(r["signals"], {}) or {}
        used.extend(_clip_used_ranges(sig, r["start_sec"], r["end_sec"]))
    used.sort(key=lambda x: x[0])
    return used


def _overlap_frac(s: float, e: float, used: list) -> float:
    """Tỉ lệ đoạn [s,e] bị các khoảng `used` phủ (0..1). Hàm thuần — test được."""
    span = e - s
    if span <= 0 or not used:
        return 0.0
    # gộp phần giao (used có thể chồng nhau) rồi cộng độ dài giao
    hits = sorted(([max(s, float(a)), min(e, float(b))] for a, b in used
                   if min(e, float(b)) > max(s, float(a))), key=lambda x: x[0])
    covered, cur_e = 0.0, -1e9
    for a, b in hits:
        if a > cur_e:
            covered += b - a
            cur_e = b
        elif b > cur_e:
            covered += b - cur_e
            cur_e = b
    return min(1.0, covered / span)


def _filter_used_candidates(cands: list, used: list, keyfn=None,
                            thr: float = _USED_OVERLAP) -> tuple[list, bool]:
    """Loại ứng viên trùng > thr với `used`. keyfn(c) -> (start, end).
    Nếu LOẠI HẾT (video đã dùng gần hết) -> trả lại DANH SÁCH GỐC sắp theo độ
    trùng TĂNG DẦN (ít trùng nhất trước) + cờ exhausted=True để caller log.
    Hàm thuần — test được."""
    if not used or not cands:
        return list(cands), False
    keyfn = keyfn or (lambda c: (c["start"], c["end"]))
    kept = []
    for c in cands:
        s, e = keyfn(c)
        if _overlap_frac(float(s), float(e), used) <= thr:
            kept.append(c)
    if kept:
        return kept, False
    # đã dùng gần hết -> ưu tiên phần ÍT TRÙNG NHẤT (không bỏ trắng tay)
    ranked = sorted(cands, key=lambda c: _overlap_frac(
        float(keyfn(c)[0]), float(keyfn(c)[1]), used))
    return ranked, True


def generate_highlights(payload: dict, ctx: JobContext) -> dict:
    """
    Bước "tìm highlight" — được job 'auto' (jobs.py) gọi sau khi phân tích.
    AI tự chọn clip (độ dài linh hoạt, bỏ đoạn thừa, ghép khúc hay). Nếu bật vision,
    chấm thêm bằng HÌNH ẢNH. Không có LLM -> heuristic (audio + cảnh).
    """
    video_id = int(payload["video_id"])
    cfg = {**DEFAULTS, **(payload.get("preset") or {})}

    ctx.progress(0.05, "Đọc kết quả phân tích...")
    transcript = get_analysis(video_id, "transcript") or {}
    audio = get_analysis(video_id, "audio") or {}
    scenes = get_analysis(video_id, "scenes") or {}
    vrow = db.query_one("SELECT duration, src_path FROM videos WHERE id=?",
                        (video_id,))
    duration = float(vrow["duration"] or 0) if vrow else 0.0

    # 👁 VISION DIGEST: AI xem khung hình KHẮP video 1 lần (cache theo video)
    # -> prompt chọn đoạn có cả HÌNH ẢNH, không chỉ lời thoại. Gate USE_VISION
    # + không LIGHT_MODE + provider vision; lỗi/tắt -> [] (chạy y như cũ).
    digest: list = []
    if _vd.vision_digest_enabled():
        ctx.progress(0.20, "AI đang xem khung hình khắp video...")
        digest = _vd.build_vision_digest(
            video_id, (vrow["src_path"] or "") if vrow else "", duration,
            ctx=ctx)

    # 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO: đọc các đoạn ĐÃ dùng của video này TRƯỚC
    # khi _delete_suggested (giữ được cả lần bấm trước còn treo suggested) ->
    # loại/phạt ứng viên trùng để lần này ra đoạn KHÁC.
    used_ranges = load_used_ranges(video_id)

    # ---- Ưu tiên: AI tự chọn clip + segments ----
    llm.reset_usage()                 # đếm token Gemini riêng cho video này
    prov = llm.active_provider()
    prov_name = {"gemini": "Gemini", "ollama": "Ollama (máy)", "groq": "Groq (mây)",
                 "openai": "OpenAI", "deepseek": "DeepSeek"}.get(prov, prov)
    ctx.progress(0.30, f"AI [{prov_name}] đang đọc nội dung & chọn đoạn hay...")
    llm_error = ""
    ai_warns: list = []
    try:
        ai_clips, ai_warns = _llm_select_clips(transcript, duration, ctx,
                                               scenes, cfg, digest=digest)
    except llm.LLMError as e:  # gọi LLM lỗi thật -> báo rõ, vẫn lùi heuristic
        ai_clips = []
        llm_error = str(e)
    # 🔁 NHIỀU-PASS: AI đọc lại toàn cảnh, chấm + chọn top viral, loại clip
    # trùng/lê thê. FAIL-SAFE (chỉ lọc/sắp xếp, không đổi boundary; lỗi/keo
    # rỗng -> giữ nguyên). Chạy TRƯỚC dedup cross-run (used_ranges) như cũ.
    if ai_clips:
        from config import settings as _st0
        if getattr(_st0, "AI_MULTIPASS", True):
            _want = int(cfg.get("count", 0) or 0)
            ctx.progress(0.58, f"AI [{prov_name}] chấm & chọn clip tốt nhất...")
            ai_clips = _refine_clip_selection(
                ai_clips, transcript, (transcript or {}).get("language", ""),
                _want, float(cfg.get("min_len", 60.0)),
                float(cfg.get("max_len", 0.0) or 0.0), vdigest=digest)
    if ai_clips:
        from config import settings as _st
        # máy yếu: KHÔNG chấm điểm bằng hình (ngốn CPU + tốn lượt) -> chỉ dựa transcript
        used_vision = llm.vision_available() and not getattr(_st, "LIGHT_MODE", True)
        if used_vision:
            if digest:
                # 👁 ĐÃ có vision digest (xem cả video) -> chấm bằng act của
                # digest, KHÔNG gọi vision lần 2 (đỡ tốn lượt, không trùng).
                ai_clips = _digest_rescore(ai_clips, digest)
            else:
                ctx.progress(0.6, f"AI [{prov_name}] đang XEM hình ảnh từng đoạn...")
                ai_clips = _vision_rescore(video_id, ai_clips, ctx)
            ai_clips.sort(key=lambda c: c["segments"][0][0])  # giữ thứ tự thời gian
        # 🚪 SÀN CHẤT LƯỢNG (QUALITY_FLOOR, mặc định 55; 0=tắt): sau chọn +
        # chấm (điểm đã trộn vision nếu có), bỏ clip điểm thấp — chỉ giữ
        # đoạn đáng dùng. Fail-safe trong helper: luôn giữ >=1 clip cao nhất.
        _floor = 0.0
        try:
            _floor = float(getattr(_st, "QUALITY_FLOOR", 55) or 0)
        except (TypeError, ValueError):
            _floor = 55.0
        ai_clips, _n_low = _apply_quality_floor(ai_clips, _floor)
        if _n_low:
            ctx.progress(0.62, f"bỏ {_n_low} clip điểm thấp (<{int(_floor)}) "
                               "— chỉ giữ đoạn đáng dùng")
        # 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO: loại clip trùng >30% với đoạn đã dùng
        # ở lần trước. Dùng span [đầu..cuối] của clip (clip đã nới dài). Hết
        # sạch (video đã dùng gần hết) -> giữ clip ít trùng nhất + log.
        exhausted_note = ""
        if used_ranges:
            ai_clips, exhausted = _filter_used_candidates(
                ai_clips, used_ranges,
                keyfn=lambda c: (c["segments"][0][0], c["segments"][-1][1]))
            ai_clips.sort(key=lambda c: c["segments"][0][0])
            if exhausted:
                exhausted_note = ("video này đã tạo nhiều clip, các đoạn mới có "
                                  "thể trùng phần đã dùng")
        _delete_suggested(video_id)
        # 🔒 RÀO CHẮN CUỐI: MỌI clip PHẢI lọt [min_len, max_len]. Chạy SAU tất
        # cả bước AI (chọn + refine + dedup) — sửa lỗi 'đặt min 60 mà ra 46s'
        # (extend_to_target bị gap chặn, refine cắt gọn...). Không nới nổi ->
        # gom cảnh báo cho user.
        _bnd = _natural_boundaries(transcript, scenes)
        _min = float(cfg.get("min_len", 60.0))
        _max = float(cfg.get("max_len", 0.0) or 0.0)
        _tsegs = (transcript or {}).get("segments", []) or []
        _len_notes: list = []
        clip_ids = []
        for c in ai_clips:
            segs, _note = _enforce_len(c["segments"], _min, _max, duration,
                                       _bnd)
            # 🚮 nới min (_enforce_len) có thể nuốt lại outro/intro theo THỜI
            # GIAN -> snap mép bỏ câu CTA/chào lần CUỐI (chỉ cắt khi vẫn giữ
            # được >= min_len - 2s, không thì giữ nguyên — fail-safe).
            segs = _trim_junk_edges(segs, _tsegs, _min)
            c["segments"] = segs
            if _note:
                _len_notes.append(_note)
            total = sum(e - s for s, e in segs)
            signals = {"segments": segs, "n_seg": len(segs), "llm_used": True,
                       "ai": prov, "ai_name": prov_name,
                       "vision": used_vision, "vscore": c.get("vscore"),
                       "title_en": c.get("title_en", ""), "hook": c.get("hook", ""),
                       "hook_seg": c.get("hook_seg"),
                       "dur": round(total, 1)}
            # 🌐 TÊN CLIP THEO NGÔN NGỮ VIDEO: video KHÔNG phải tiếng Việt ->
            # tên hiển thị = title_pub (đúng ngôn ngữ video); tiêu đề Việt chỉ
            # dùng cho video tiếng Việt (user muốn tiêu đề Nhật cho video Nhật
            # ở MỌI chỗ, kể cả danh sách clip trong app).
            _t_show = c["title"]
            _t_pub = str(c.get("title_en") or "").strip()
            if _t_pub:
                from app.ai import recap as _rec
                _lg = _rec.resolve_lang(transcript.get("language", ""),
                                        transcript.get("text", "") or "")
                if not _rec._is_vi_lang(_lg):
                    _t_show = _t_pub
            cid = db.insert(
                """INSERT INTO clips (video_id, start_sec, end_sec, score, reason,
                                      title, transcript, signals, status)
                   VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
                (video_id, segs[0][0], segs[-1][1], round(c["score"], 1),
                 c["reason"], _t_show, "", db.dumps(signals)),
            )
            clip_ids.append(cid)
        msg = (f"AI [{prov_name}] chọn {len(clip_ids)} clip"
               + (" (có xem hình)" if used_vision else ""))
        if ai_warns:
            msg += " — CẢNH BÁO: " + "; ".join(ai_warns)
        if _len_notes:                  # có clip không nới đủ min (video ngắn)
            msg += f" — LƯU Ý: {len(_len_notes)} clip ngắn hơn Min (đoạn không đủ dài)"
        if exhausted_note:              # video đã dùng gần hết -> cảnh báo trùng
            msg += f" — ⚠ {exhausted_note}"
        cost = {}
        if prov == "gemini":            # CHI PHÍ ước tính cho video này
            u = llm.get_usage()
            vnd = llm.estimate_cost_vnd(u)
            tok = u["in"] + u["out"]
            msg += f" · tốn ~{tok:,} token ≈ {vnd:,}₫"
            cost = {"tokens": tok, "cost_vnd": vnd}
        ctx.progress(1.0, msg)
        return {"count": len(clip_ids), "clip_ids": clip_ids,
                "llm_used": True, "ai_used": True, "ai": prov,
                "vision": used_vision, **cost}

    # ---- Fallback heuristic (LLM chưa cấu hình HOẶC gọi lỗi) ----
    # ⚠ MINH BẠCH: nói RÕ đây là cắt kiểu CƠ BẢN (kém thông minh hơn AI) +
    # gợi ý dán key để AI chọn đoạn hay + đa dạng hơn. Trả cờ ai_used=False.
    if llm_error:
        note = ("⚠ AI chọn đoạn gặp lỗi nên đang chọn đoạn kiểu CƠ BẢN (kém "
                "thông minh hơn). Kiểm tra key/Ollama trong Cài đặt AI rồi thử "
                f"lại để AI chọn đoạn hay + đa dạng hơn. (Chi tiết: {llm_error[:120]})")
    elif not llm.is_configured():
        note = ("⚠ Chưa có key AI -> đang chọn đoạn kiểu CƠ BẢN (kém thông minh "
                "hơn). Dán key Groq trong Cài đặt AI để AI chọn đoạn hay + đa "
                "dạng hơn.")
    else:
        note = ""
    return _generate_heuristic(video_id, cfg, transcript, audio, scenes,
                               duration, ctx, note=note, used_ranges=used_ranges)


def _spread_pick(candidates: list, audio: dict, limit: int, duration: float,
                 min_gap: float) -> list:
    """ĐA DẠNG: chọn tối đa `limit` ứng viên RẢI ĐỀU toàn video thay vì lấy
    top-N đỉnh năng lượng LIỀN NHAU (dồn cụm 1 chỗ). Chia [0,duration] thành
    `limit` khoảng, MỖI khoảng lấy ứng viên điểm audio cao nhất; ép mọi cặp
    đoạn chọn cách nhau >= min_gap (tính theo mốc bắt đầu). Thiếu (khoảng
    trống) -> bù thêm đỉnh cao nhất còn lại vẫn thoả min_gap. Hàm thuần —
    test được.
    """
    if not candidates:
        return []
    scored = sorted(candidates,
                    key=lambda c: _audio_score(audio, c["start"], c["end"]),
                    reverse=True)
    if limit <= 0:
        return scored
    span = duration if duration and duration > 0 else (
        max(c["end"] for c in candidates) or 1.0)

    def _far_enough(c, chosen):
        return all(abs(c["start"] - k["start"]) >= min_gap for k in chosen)

    chosen: list = []
    # 1) rải theo khoảng: mỗi khoảng lấy đỉnh cao nhất thoả min_gap
    for b in range(limit):
        lo, hi = span * b / limit, span * (b + 1) / limit
        best = None
        for c in scored:
            mid = (c["start"] + c["end"]) / 2
            if lo <= mid < hi and c not in chosen and _far_enough(c, chosen):
                best = c
                break                        # scored đã sort giảm -> đỉnh đầu
        if best is not None:
            chosen.append(best)
    # 2) chưa đủ (nhiều khoảng trống) -> bù đỉnh cao nhất còn lại thoả min_gap
    if len(chosen) < limit:
        for c in scored:
            if len(chosen) >= limit:
                break
            if c not in chosen and _far_enough(c, chosen):
                chosen.append(c)
    # 3) vẫn thiếu (video quá ngắn, min_gap chặn hết) -> nới: lấy đỉnh còn lại
    if len(chosen) < limit:
        for c in scored:
            if len(chosen) >= limit:
                break
            if c not in chosen:
                chosen.append(c)
    return chosen


def _generate_heuristic(video_id, cfg, transcript, audio, scenes, duration, ctx,
                        note: str = "", used_ranges: list = None):
    """Bản dự phòng khi không có LLM: cửa sổ + chấm audio/cảnh (1 đoạn liền/clip).

    ĐA DẠNG (VIỆC 2): thay vì lấy top-N đỉnh năng lượng LIỀN NHAU (dễ cụm 1
    chỗ), chia video thành N khoảng RỜI rồi mỗi khoảng lấy đỉnh -> đoạn RẢI
    ĐỀU đầu/giữa/cuối. Ép KHOẢNG CÁCH tối thiểu giữa các đoạn (>=8% thời lượng
    hoặc 30s). CHỐNG TRÙNG (VIỆC 1): loại ứng viên trùng >30% với used_ranges.
    """
    ctx.progress(0.5, "Tạo đoạn ứng viên (không có AI)...")
    candidates = _build_candidates(transcript, scenes, duration, cfg)
    if not candidates:
        return {"count": 0, "clip_ids": [], "note": "Không tạo được ứng viên.",
                "llm_used": False, "ai_used": False}

    # 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO: loại ứng viên trùng >30% với đoạn đã dùng
    exhausted_note = ""
    if used_ranges:
        candidates, exhausted = _filter_used_candidates(candidates, used_ranges)
        if exhausted:
            exhausted_note = ("video này đã tạo nhiều clip, các đoạn mới có thể "
                              "trùng phần đã dùng")

    # 🚮 NÉ RÁC ĐẦU/CUỐI VIDEO: ứng viên CHẠM 3% đầu (intro) / 3% cuối (outro)
    # mà >30% từ là câu CTA/chào kênh -> loại. KHÔNG loại theo vị trí đơn
    # thuần (nội dung hay ở đầu video vẫn giữ). FAIL-SAFE: lọc hết -> giữ cũ.
    tsegs = (transcript or {}).get("segments", []) or []
    if duration > 0 and tsegs:
        _head, _tail = 0.03 * duration, 0.97 * duration
        _no_junk = [
            c for c in candidates
            if not ((c["start"] <= _head or c["end"] >= _tail)
                    and _junk_ratio([[c["start"], c["end"]]], tsegs)
                    > _recap._CTA_MAX)]
        if _no_junk:
            candidates = _no_junk

    count = int(cfg.get("count", 0) or 0)
    limit = count if count > 0 else 12
    limit = min(limit, cfg["max_candidates"])

    # ĐA DẠNG: chọn đỉnh năng lượng RẢI theo các phần video (spread) + ép
    # khoảng cách tối thiểu — không cụm 1 chỗ.
    min_gap = max(30.0, 0.08 * duration) if duration > 0 else 30.0
    candidates = _spread_pick(candidates, audio, limit, duration, min_gap)
    candidates.sort(key=lambda c: c["start"])  # theo thứ tự thời gian

    min_len = float(cfg.get("min_len", 60.0))
    max_len = float(cfg.get("max_len", 0.0) or 0.0)
    _bnd = _natural_boundaries(transcript, scenes)
    _delete_suggested(video_id)
    clip_ids = []
    for c in candidates:
        # 🔒 RÀO CHẮN CUỐI: clip PHẢI lọt [min_len, max_len] (nới nếu < min,
        # cắt nếu > max). Thay _ensure_min_duration cũ (chỉ lo min, không cắt
        # max, không bám mép câu). Sửa lỗi 'đặt min 60 ra 46'.
        seg, _ = _enforce_len([[c["start"], c["end"]]], min_len, max_len,
                              duration, _bnd)
        # 🚮 snap mép bỏ câu CTA/chào kênh dính ở đầu/cuối (fail-safe giữ min)
        seg = _trim_junk_edges(seg, tsegs, min_len)
        c_start, c_end = seg[0][0], seg[-1][1]
        a_s = _audio_score(audio, c_start, c_end)
        s_s = _scene_score(scenes, c_start, c_end)
        final = 0.6 * a_s + 0.4 * s_s
        signals = {"segments": [[c_start, c_end]], "n_seg": 1,
                   "llm_used": False, "ai": "", "audio": round(a_s, 1),
                   "scene": round(s_s, 1)}
        cid = db.insert(
            """INSERT INTO clips (video_id, start_sec, end_sec, score, reason,
                                  title, transcript, signals, status)
               VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
            (video_id, c_start, c_end, round(final, 1),
             "Năng lượng/chuyển cảnh nổi bật.", "Clip", c["text"], db.dumps(signals)),
        )
        clip_ids.append(cid)
    msg = note or f"Đề xuất {len(clip_ids)} clip (cắt cơ bản)"
    if exhausted_note:
        msg += f" — ⚠ {exhausted_note}"
    ctx.progress(1.0, msg)
    # ai_used=False -> UI/card biết đây là cắt CƠ BẢN (không phải AI chọn)
    return {"count": len(clip_ids), "clip_ids": clip_ids, "llm_used": False,
            "ai_used": False, "note": note}


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
    Bước "Mixed-Cut" — được job 'auto_mixed' (jobs.py) gọi sau khi phân tích.
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

    # 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO (đọc TRƯỚC khi ghi clip mới)
    used_ranges = load_used_ranges(video_id)

    ctx.progress(0.15, "Tạo các khoảnh khắc ứng viên...")
    moment_cfg = {**cfg, "min_len": cfg["moment_min"], "max_len": cfg["moment_max"]}
    moments = _build_candidates(transcript, scenes, duration, moment_cfg)
    if len(moments) < 2:
        return {"count": 0, "note": "Video quá ngắn/ít nội dung để ghép."}

    # 🚫 loại khoảnh khắc trùng >30% với đoạn đã dùng ở clip trước (né bản
    # quyền: Mixed-Cut lần sau né các khúc đã ghép lần trước). Hết sạch ->
    # giữ khúc ít trùng nhất.
    mix_exhausted = False
    if used_ranges:
        moments, mix_exhausted = _filter_used_candidates(moments, used_ranges)

    # chấm điểm từng khoảnh khắc
    moments.sort(key=lambda c: _audio_score(audio, c["start"], c["end"]), reverse=True)
    moments = moments[: cfg["max_candidates"]]
    ctx.progress(0.4, f"AI chấm điểm {len(moments)} khoảnh khắc...")
    llm_map = _llm_scores(moments, transcript.get("language", ""))
    use_llm = bool(llm_map)

    # KHÔNG AI + KHÔNG phân tích âm thanh (LIGHT_MODE) -> _audio_score trả hằng
    # 50 cho mọi đoạn = chọn moment BỪA. Thà báo rõ còn hơn ghép lung tung.
    has_audio = bool(((audio or {}).get("rms_envelope") or {}).get("values"))
    if not use_llm and not has_audio:
        return {"count": 0,
                "note": "Mixed-Cut cần AI (dán key Groq trong Cài đặt AI) "
                        "để chọn khoảnh khắc"}

    scored = []
    for i, m in enumerate(moments):
        a_s = _audio_score(audio, m["start"], m["end"])
        s_s = _scene_score(scenes, m["start"], m["end"])
        l = llm_map.get(i, {})
        l_s = l.get("score", 50.0)
        final = (cfg["w_llm"] * l_s + cfg["w_audio"] * a_s + cfg["w_scene"] * s_s
                 if use_llm else 0.6 * a_s + 0.4 * s_s)
        scored.append({**m, "score": final, "title": l.get("title", ""),
                       "title_pub": l.get("title_pub", "")})

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

    # SNAP đầu/cuối mỗi khoảnh khắc vào ranh giới CÂU NÓI + CẢNH của video gốc
    # -> không cắt lẹm giữa câu (như highlights). Snap xong khử chồng lấn nhẹ.
    boundaries = _natural_boundaries(transcript, scenes)
    if boundaries:
        snapped = _snap_segments([[m["start"], m["end"]] for m in chosen],
                                 boundaries)
        prev_end = 0.0
        for m, (s, e) in zip(chosen, snapped):
            s = max(s, prev_end)             # snap có thể làm 2 đoạn đè nhau
            if e - s >= 1.0:
                m["start"], m["end"] = round(s, 2), round(e, 2)
            prev_end = m["end"]

    # LƯU KÈM "score" mỗi moment -> lúc xuất, _join_categories biết moment nào
    # điểm CAO NHẤT để đặt 'impact' tại điểm nối VÀO đoạn đó (ngữ cảnh cấu trúc,
    # không cần AI). score đã tính ở scored (LLM/audio+scene).
    moments_out = [{"start": round(m["start"], 2), "end": round(m["end"], 2),
                    "cx": round(_moment_cx(faces, m["start"], m["end"]), 4),
                    "score": round(float(m.get("score", 0.0)), 1)}
                   for m in chosen]
    dur_total = sum(m["end"] - m["start"] for m in moments_out)
    best = max(chosen, key=lambda x: x["score"])
    title = best.get("title", "") or f"Mix {len(chosen)} khoảnh khắc hay"
    # 🌐 video KHÔNG phải tiếng Việt -> tên clip = title_pub (đúng ngôn ngữ)
    _t_pub = (best.get("title_pub", "") or "").strip()
    if _t_pub:
        from app.ai import recap as _rec
        _lg = _rec.resolve_lang(transcript.get("language", ""),
                                transcript.get("text", "") or "")
        if not _rec._is_vi_lang(_lg):
            title = _t_pub
    avg = round(sum(m["score"] for m in chosen) / len(chosen), 1)

    signals = {"mode": "mixed", "llm_used": use_llm,
               "moments": moments_out, "n": len(moments_out),
               # tiêu đề GẮN LÊN video (đúng ngôn ngữ video) của moment đỉnh nhất
               "title_en": (best.get("title_pub", "") or "").strip()}

    cid = db.insert(
        """INSERT INTO clips (video_id, start_sec, end_sec, score, reason, title,
                              transcript, signals, status)
           VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
        (video_id, moments_out[0]["start"], moments_out[-1]["end"], avg,
         f"Ghép {len(chosen)} đoạn điểm cao (~{dur_total:.0f}s).", title,
         " ".join(m.get("text", "") for m in chosen), db.dumps(signals)),
    )
    mmsg = f"Đã tạo Mixed-Cut ({len(chosen)} đoạn, {dur_total:.0f}s)"
    if mix_exhausted:
        mmsg += " — ⚠ video này đã tạo nhiều clip, các đoạn mới có thể trùng"
    ctx.progress(1.0, mmsg)
    return {"count": 1, "clip_id": cid, "moments": len(chosen),
            "duration": round(dur_total, 1), "llm_used": use_llm}


# ============================================================
# Xuất clip 9:16 face-track
# ============================================================
def _caption_tokens(text: str) -> list:
    """Tách text thành token làm words GIẢ cho phụ đề chạy chữ, CJK-AWARE.

    Câu Nhật/Trung/Thái/Lào/Khmer/Miến KHÔNG có dấu cách -> `.split()` trả CẢ
    CÂU 1 token -> phụ đề hiện nguyên câu 1 lúc (lỗi đa ngôn ngữ). Dùng
    recap._word_tokens (per-char CJK) rồi GHÉP CỤM 2-4 KÝ TỰ HIỂN THỊ/token
    cho phụ đề đọc được (từng ký tự đơn quá vụn); dấu câu dính vào cụm kề,
    không đứng riêng; cụm đuôi 1-2 ký tự gộp vào cụm trước nếu không vượt 4.
    KHÔNG cắt cụm ngay TRƯỚC dấu kết hợp (Mn — nguyên âm/thanh điệu Thái/Lào/
    Miến bám ký tự trước; cắt rời sẽ render vòng tròn chấm ◌) -> đếm độ dài
    cụm theo KÝ TỰ HIỂN THỊ (bỏ Mn).
    BẤT BIẾN: text KHÔNG có ký tự CJK -> trả Y HỆT text.split() (đường EN/VI
    không đổi). Hàm thuần — unit test được."""
    import unicodedata
    from app.ai.recap import _has_cjk, _word_tokens
    s = str(text or "").strip()
    if not s:
        return []
    if not _has_cjk(s):
        return s.split()                 # bất biến: non-CJK y hệt .split()

    def _vis(chunk: str) -> int:         # số ký tự HIỂN THỊ (bỏ dấu kết hợp)
        return sum(1 for ch in chunk
                   if unicodedata.category(ch) != "Mn")

    out, buf = [], ""
    for t in _word_tokens(s):
        if _has_cjk(t) and len(t) == 1:  # ký tự CJK đơn -> gom cụm 3 (2-4)
            # đầy 3 ký tự hiển thị -> chốt cụm TRƯỚC khi thêm, trừ khi t là
            # dấu kết hợp (phải bám ký tự trước, không được mở cụm mới)
            if buf and _vis(buf) >= 3 and unicodedata.category(t) != "Mn":
                out.append(buf)
                buf = ""
            buf += t
        elif not any(ch.isalnum() for ch in t):
            # token TOÀN dấu câu (、。!? "…") -> dính vào cụm đang gom/cụm
            # trước, KHÔNG thành token riêng (phụ đề nháy 1 dấu câu rất xấu)
            if buf:
                buf += t
            elif out:
                out[-1] += t
            else:
                buf = t
        else:                            # cụm latin/số -> giữ nguyên như split
            if buf:
                out.append(buf)
                buf = ""
            out.append(t)
    if buf:
        # đuôi 1-2 ký tự: gộp vào cụm CJK trước nếu tổng <= 4 (đỡ token vụn)
        if out and _has_cjk(out[-1]) and _vis(out[-1]) + _vis(buf) <= 4:
            out[-1] += buf
        else:
            out.append(buf)
    return out


def _fake_words_from_segments(segments: list) -> list:
    """Transcript KHÔNG có mốc từng-từ (vd Groq không trả words) -> tạo words
    GIẢ: chia đều thời gian mỗi segment cho từng từ (giống cách làm cho lồng
    tiếng). Phụ đề vẫn chạy chữ, chỉ kém khớp lời hơn whisper word-level.
    Token CJK-aware qua _caption_tokens (câu Nhật/Thái không dấu cách vẫn ra
    cụm 2-4 ký tự thay vì nguyên câu); non-CJK y hệt .split() cũ."""
    out = []
    for d in segments or []:
        try:
            s, e = float(d["start"]), float(d["end"])
            toks = _caption_tokens(d.get("text") or "")
        except (KeyError, TypeError, ValueError):
            continue
        if not toks or e <= s:
            continue
        step = max(0.05, (e - s) / len(toks))
        for k, tk in enumerate(toks):
            out.append({"start": round(s + k * step, 3),
                        "end": round(s + (k + 1) * step, 3),
                        "word": tk})
    return out


def _group_recap_cues(cues: list, out_kind: str) -> list:
    """Gom cue phụ đề recap TỪNG TỪ (kind word/orig_word) thành CỤM 2-3 từ
    khi user chọn kiểu 'cụm' (group). Cue đã là CẢ CÂU (kind sent/orig_sent)
    -> giữ nguyên (fallback không có word boundary). out_kind = kind cụm mới
    ('sent' cho narrate / 'orig_sent' cho gốc) -> build_ass render 1
    Dialogue/cụm. Giữ đúng thứ tự thời gian. Hàm thuần."""
    from app.core import captions as _cap
    word_cues = [(c[0], c[1], c[2]) for c in cues
                 if len(c) > 3 and str(c[3]) in ("word", "orig_word")]
    other = [c for c in cues
             if not (len(c) > 3 and str(c[3]) in ("word", "orig_word"))]
    grouped = [(a, b, txt, out_kind)
               for a, b, txt in _cap.group_word_cues(word_cues)]
    out = list(other) + grouped
    out.sort(key=lambda c: c[0])
    return out


def _recap_caption_cues(narr_events: list) -> list:
    """Cue phụ đề cho ĐOẠN THUYẾT MINH (recap).

    narr_events = [{"start","end","text"[,"words"]}] trên timeline ĐẦU RA
    (chưa speed) — dubbing.build_recap_track trả về.

    - Event CÓ "words" (edge-tts WordBoundary — mốc từng từ THẬT của giọng
      đọc, đã scale theo atempo): phụ đề WORD-LEVEL y hệt đoạn gốc (mỗi từ
      1 cue, giữ tới từ kế như captions._word_cues) -> đồng nhất trải nghiệm.
    - Event KHÔNG có "words" (giọng Gemini không trả word boundary, hoặc
      TTS lỗi event): FALLBACK chia câu theo SỐ KÝ TỰ như cũ.
    - Event có cờ "clamped" (build_recap_track ĐÃ hậu kiểm cứng cue theo
      tiếng THẬT): words có thì KHÔNG nới đuôi (+0.15s) / không giữ chữ
      qua khoảng lặng >=0.18s — mép cue đã là mép tiếng đo thật.
    - clamped + words RỖNG (hậu kiểm xóa hết / không dựng được cue) NHƯNG
      part CÓ text + CÓ khoảng nói: KHÔNG bỏ chữ nữa (lỗi 'mất phụ đề') —
      DỰNG cue câu-cụm phân bố ĐỀU trên KHOẢNG CÓ TIẾNG của part
      ([speech_a, speech_b] build_recap_track đo được, lưu ở event; thiếu ->
      [start, end]). Thà căn xấp xỉ còn hơn mất chữ.

    Trả [(start, end, text, kind)] đưa vào build_ass qua extra_cues;
    kind = "word" (chạy từng từ) | "sent" (hiện cả câu)."""
    cues = []
    for n in narr_events or []:
        text = (n.get("text") or "").strip()
        if not text:
            continue
        n_end = float(n["end"])
        words = n.get("words") or []
        clamped = bool(n.get("clamped"))
        if words:
            # WORD-LEVEL: từ hiện đúng lúc đọc, giữ tới từ kế (liền mạch,
            # không nhấp nháy); từ cuối/trước khoảng lặng tắt sớm (+0.15s).
            # Cue ĐÃ CLAMP: mép cuối = mép hết tiếng đo thật (+0.12s pad có
            # sẵn) -> KHÔNG cộng đuôi; chỉ giữ tới cue kế khi hở < 0.18s
            # (dưới ngưỡng silencedetect — không phủ chữ lên khoảng im).
            hold_gap = 0.18 if clamped else 0.45
            tail = 0.0 if clamped else 0.15
            for i, (a, b, wtxt) in enumerate(words):
                wtxt = str(wtxt).strip()
                if not wtxt:
                    continue
                if i + 1 < len(words) and words[i + 1][0] - b < hold_gap:
                    end = words[i + 1][0]
                else:
                    end = b + tail
                end = min(end, n_end) if not clamped else end
                a = max(float(n["start"]), float(a))
                cues.append((round(a, 3), round(max(a + 0.05, end), 3),
                             wtxt, "word"))
            continue
        # FALLBACK theo câu (Gemini/không word boundary HOẶC clamped mà cue bị
        # xóa hết): chia câu-cụm theo SỐ KÝ TỰ, phân bố ĐỀU trên KHOẢNG CÓ
        # TIẾNG THẬT của part. Ưu tiên [speech_a, speech_b] build_recap_track
        # đo được (bỏ lặng đầu/cuối -> lệch nhỏ); thiếu -> [start, end] (end
        # đã co về mép hết tiếng). Bảo đảm part CÓ text LUÔN có phụ đề.
        sp = n.get("speech")
        if isinstance(sp, (list, tuple)) and len(sp) >= 2:
            t0, t1 = float(sp[0]), float(sp[1])
        else:
            t0, t1 = float(n["start"]), n_end
        sents = [s.strip() for s in re.split(r"(?<=[.!?…;])\s+", text)
                 if s.strip()]
        if not sents:
            sents = [text]
        total_chars = sum(len(s) for s in sents)
        t = t0
        dur = t1 - t0
        if dur <= 0.1:
            continue
        for s in sents:
            d = dur * len(s) / max(1, total_chars)
            cues.append((round(t, 3), round(min(t + d, t1), 3), s, "sent"))
            t += d
    return cues


def _part_mode_at(recap_parts: list, t: float) -> str:
    """mode ("orig"/"narrate") của part recap chứa mốc t (timeline GỐC); mốc
    rơi ranh giới -> part BẮT ĐẦU tại t. Không tìm thấy -> "". Hàm thuần."""
    best = ""
    for p in recap_parts or []:
        try:
            a, b = float(p["start"]), float(p["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if a <= t < b or abs(a - t) < 0.05:
            return str(p.get("mode") or "")
        if a <= t <= b:
            best = str(p.get("mode") or "")
    return best


# Tập NHÃN "sfx" cố định mà AI (recap.build_director_prompt) được phép gắn cho
# MỖI part; khớp SFX_CATEGORIES của ffmpeg_utils + "none" (không chèn). Dùng để
# NHẬN nhãn AI trong _join_categories (ưu tiên hơn suy luận cấu trúc cũ).
_AI_SFX_LABELS = frozenset((
    "none", "transition", "impact", "riser", "reveal", "pop",
    "suspense", "comedy", "scratch", "sad", "drumroll"))


def _part_sfx_at(recap_parts: list, t: float):
    """NHÃN "sfx" do AI gắn cho part recap CHỨA mốc t (timeline GỐC), nếu part
    ĐÓ có field "sfx" hợp lệ (trong _AI_SFX_LABELS). Trả:
      - tên nhãn ("impact"/"scratch"/.../"none") nếu part có nhãn AI hợp lệ,
      - None nếu part KHÔNG có nhãn (kịch bản cũ/heuristic) hoặc nhãn lạ
        -> caller tự lùi về suy luận cấu trúc.
    Ưu tiên part BẮT ĐẦU tại t (điểm nối rơi đúng mép part). Hàm thuần."""
    best = None
    for p in recap_parts or []:
        try:
            a, b = float(p["start"]), float(p["end"])
        except (KeyError, TypeError, ValueError):
            continue
        raw = str(p.get("sfx") or "").strip().lower()
        lab = raw if raw in _AI_SFX_LABELS else None
        if a <= t < b or abs(a - t) < 0.05:
            return lab
        if a <= t <= b and best is None:
            best = lab
    return best


def _seg_index_containing(segs: list, a: float, b: float) -> int:
    """Chỉ số đoạn trong segs GIAO NHIỀU NHẤT với khoảng [a,b] (timeline GỐC).
    Không giao đoạn nào -> -1. Hàm thuần — test được."""
    best_i, best_ov = -1, 0.0
    for i, seg in enumerate(segs):
        try:
            s, e = float(seg[0]), float(seg[1])
        except (IndexError, TypeError, ValueError):
            continue
        ov = min(b, e) - max(a, s)
        if ov > best_ov:
            best_ov, best_i = ov, i
    return best_i


def _context_join_categories(segs: list, signals: dict, seed=None) -> list:
    """NGỮ CẢNH CẤU TRÚC cho clip THƯỜNG / Mixed (KHÔNG có nhãn cảm xúc của AI).
    Suy loại tiếng theo VỊ TRÍ điểm nối so với khoảnh khắc cao trào ĐÃ BIẾT
    (không cần key AI):

      - Điểm nối NGAY TRƯỚC / VÀO đoạn chứa hook_time (cao trào clip) -> 'impact'
        HOẶC 'riser' (chọn ngẫu nhiên -> tạo nhấn/hồi hộp).
      - Mixed-Cut: điểm nối VÀO đoạn (moment) điểm CAO NHẤT -> 'impact'.
      - Điểm nối CUỐI (vào đoạn kết clip) -> 'reveal' (ding chốt nhẹ).
      - Còn lại -> 'transition' (whoosh/gió) như cũ.

    Ưu tiên: nếu 1 điểm nối vừa là cao trào vừa là điểm cuối -> giữ cao trào
    (impact/riser) vì nhấn mạnh hơn chốt. hook_time đọc từ signals["hook_seg"]
    (mốc TIMELINE GỐC do AI chọn ở _normalize_clip); moment điểm cao nhất đọc
    từ signals["moments"][*]["score"]. Không có ngữ cảnh -> toàn 'transition'
    (+ reveal cuối). Hàm thuần (chỉ đọc segs/signals) — unit test được."""
    import random as _r
    rng = _r.Random(seed) if seed is not None else _r
    n_join = max(0, len(segs) - 1)
    if n_join == 0:
        return []
    cats = ["transition"] * n_join
    # (a) điểm nối CUỐI -> reveal (chốt nhẹ) — đặt trước, cao trào ghi đè sau.
    cats[-1] = "reveal"

    # (b) đoạn CAO TRÀO cần được nhấn ở điểm nối VÀO nó (join index = seg_idx-1).
    climax_seg = -1
    sig = signals if isinstance(signals, dict) else {}
    moments = sig.get("moments") or []
    if moments:                       # Mixed-Cut: moment điểm cao nhất
        try:
            climax_seg = max(range(len(moments)),
                             key=lambda i: float(moments[i].get("score", 0.0)))
        except (ValueError, TypeError):
            climax_seg = -1
    else:                             # Clip thường: đoạn chứa hook_time
        hs = sig.get("hook_seg")
        if isinstance(hs, (list, tuple)) and len(hs) >= 2:
            try:
                climax_seg = _seg_index_containing(
                    segs, float(hs[0]), float(hs[1]))
            except (ValueError, TypeError):
                climax_seg = -1

    # điểm nối VÀO đoạn cao trào = join index (climax_seg - 1). climax_seg==0
    # (cao trào NẰM Ở ĐOẠN ĐẦU, vd hook-first đã đưa lên đầu) -> KHÔNG có điểm
    # nối trước nó để nhấn; bỏ qua (đầu clip không ghép).
    if climax_seg >= 1 and (climax_seg - 1) < n_join:
        # hook: ngẫu nhiên impact HOẶC riser (nhấn/hồi hộp); mixed: impact.
        if moments:
            cats[climax_seg - 1] = "impact"
        else:
            cats[climax_seg - 1] = rng.choice(("impact", "riser"))
    return cats


def _join_categories(segs: list, recap_parts: list | None,
                     is_recap: bool, signals: dict | None = None) -> list:
    """NGỮ CẢNH cho MỖI điểm nối giữa các đoạn segs (len = len(segs)-1) ->
    list category cho export_canvas_clip.

    - Clip THƯỜNG / Mixed (không recap): chọn tiếng THEO NGỮ CẢNH CẤU TRÚC
      (_context_join_categories) — cao trào (hook_time / moment điểm cao nhất)
      -> impact/riser; đoạn kết -> reveal; còn lại -> transition. KHÔNG cần AI.
    - RECAP:
        * ƯU TIÊN NHÃN AI: nếu part chứa điểm nối có field "sfx" hợp lệ do AI
          gắn (recap.build_director_prompt) -> DÙNG NHÃN ĐÓ (kể cả "none" =
          KHÔNG chèn tại điểm đó). Nhãn cảm xúc (scratch/comedy/sad/suspense/
          drumroll...) chỉ đi đường này.
        * FALLBACK suy luận cấu trúc (kịch bản cũ/heuristic KHÔNG có nhãn):
          - Điểm nối CUỐI (vào đoạn KẾT clip) -> 'reveal' (ding chốt nhẹ).
          - Vào đoạn mà part ĐẦU là 'orig' (bung tiếng gốc đắt/cao trào) ->
            'impact' (boom mạnh đầu đoạn).
          - Vào đoạn mà part đầu là 'narrate' (mở mạch kể mới) -> 'riser' cho
            điểm nối ĐẦU TIÊN (hồi hộp trước cao trào), còn lại -> 'transition'.
          - Còn lại -> 'transition'.
    Trả list category DÀI = số điểm nối; phần tử "none" -> ffmpeg_utils BỎ QUA
    (không chèn tiếng ở điểm đó). Hàm thuần — unit test được."""
    n_join = max(0, len(segs) - 1)
    if n_join == 0:
        return []
    if not is_recap or not recap_parts:
        # Clip thường / Mixed: KHÔNG có nhãn cảm xúc AI -> dùng ngữ cảnh cấu trúc.
        return _context_join_categories(segs, signals or {})
    cats: list = []
    used_riser = False
    for i in range(n_join):
        # mốc BẮT ĐẦU đoạn kế (đoạn i+1) trên timeline GỐC
        try:
            nxt_start = float(segs[i + 1][0])
        except (IndexError, TypeError, ValueError):
            cats.append("transition")
            continue
        # (1) NHÃN AI có ưu tiên tuyệt đối (kể cả "none" = không chèn)
        ai = _part_sfx_at(recap_parts, nxt_start)
        if ai is not None:
            cats.append(ai)
            continue
        # (2) FALLBACK: suy luận theo cấu trúc như v1.35 (part không nhãn)
        if i == n_join - 1:
            cats.append("reveal")           # vào đoạn KẾT -> chốt nhẹ
            continue
        mode = _part_mode_at(recap_parts, nxt_start)
        if mode == "orig":
            cats.append("impact")           # bung tiếng gốc đắt -> boom
        elif mode == "narrate" and not used_riser:
            cats.append("riser")            # mở mạch kể mới đầu tiên -> hồi hộp
            used_riser = True
        else:
            cats.append("transition")
    return cats


def _recap_orig_caption_cues(recap_parts: list, segs: list,
                             tr_words: list, segments_transcript: list) -> list:
    """Cue phụ đề cho ĐOẠN GỐC (mode="orig") của clip recap — phụ đề LỜI
    GỐC nhân vật đang nói, WORD-LEVEL, trên TIMELINE ĐẦU RA (đã map + trừ
    offset segment). Trả [(start, end, text, "orig_word"|"orig_sent")].

    LỖI ĐÃ SỬA: trước đây đoạn orig lấy transcript words rồi để build_ass
    tự _remap_words — nhưng words đó chia CHUNG style/đường với clip thường,
    dễ rơi rớt khi mốc part (gốc) lệch mốc segment ghép. Giờ build TƯỜNG
    MINH: với MỖI part orig, lấy words gốc rơi trong [part.start, part.end),
    MAP về timeline đầu ra bằng dubbing._map_to_output (trừ tổng thời lượng
    segment trước + offset trong segment — GIỐNG narrate), tạo cue word-level.

    tr_words = [{"start","end","word"}] mốc VIDEO GỐC (whisper word-level
    hoặc _fake_words_from_segments). Không có words phủ 1 part orig -> FALLBACK
    chia đều theo KÝ TỰ các câu transcript giao part đó (kiểu phụ đề thường).
    Mốc đầu ra CHƯA chia speed (giống narrate extra_cues — burn trước setpts).
    Kind "orig_*" -> build_ass render Style Default (khác Narrate italic vàng).
    """
    from app.core import dubbing
    orig_rngs = [(float(p["start"]), float(p["end"]))
                 for p in (recap_parts or []) if p.get("mode") == "orig"]
    if not orig_rngs:
        return []
    cues: list = []
    for a, b in orig_rngs:
        # words gốc BẮT ĐẦU trong part này -> map về đầu ra
        win_words = []
        for w in tr_words or []:
            try:
                ws, we = float(w["start"]), float(w["end"])
                wtxt = str(w.get("word") or "").strip()
            except (KeyError, TypeError, ValueError):
                continue
            if not wtxt or not (a <= ws < b):
                continue
            oa = dubbing._map_to_output(ws, segs)
            ob = dubbing._map_to_output(min(we, b), segs)
            if oa is None:
                continue
            if ob is None or ob <= oa:
                ob = oa + 0.2
            win_words.append([round(oa, 3), round(ob, 3), wtxt])
        if win_words:
            win_words.sort(key=lambda x: x[0])
            n = len(win_words)
            for i, (oa, ob, wtxt) in enumerate(win_words):
                # giữ tới từ kế (liền mạch) như captions._word_cues
                if i + 1 < n and win_words[i + 1][0] - ob < 0.45:
                    end = win_words[i + 1][0]
                else:
                    end = ob + 0.15
                cues.append((round(oa, 3), round(max(oa + 0.05, end), 3),
                             wtxt, "orig_word"))
            continue
        # FALLBACK: không có word-level -> chia đều theo KÝ TỰ các câu giao part
        sents = []
        for s in (segments_transcript or []):
            try:
                s0, e0 = float(s["start"]), float(s["end"])
            except (KeyError, TypeError, ValueError):
                continue
            txt = (s.get("text") or "").strip()
            if txt and e0 > a and s0 < b:
                sents.append((s0, e0, txt))
        for s0, e0, txt in sents:
            oa = dubbing._map_to_output(max(s0, a), segs)
            ob = dubbing._map_to_output(min(e0, b), segs)
            if oa is None or ob is None or ob <= oa or not txt.strip():
                continue
            # chia câu theo dấu câu, phân bổ thời gian theo số ký tự
            import re as _re
            pieces = [p.strip() for p in _re.split(r"(?<=[.!?…;,])\s+", txt)
                      if p.strip()] or [txt.strip()]
            tot = sum(len(p) for p in pieces) or 1
            t = oa
            for p in pieces:
                d = (ob - oa) * len(p) / tot
                cues.append((round(t, 3), round(min(t + d, ob), 3),
                             p, "orig_sent"))
                t += d
    cues.sort(key=lambda c: c[0])
    return cues


def _pick_hook_seg(video_id: int, signals: dict, segs: list):
    """Chọn 2-4s CAO TRÀO nhất để 'nhá hàng' lên đầu clip (hook-first).
    Ưu tiên mốc AI đã chọn (hook_seg); không có thì dò cửa sổ âm thanh to nhất.
    Trả None nếu không tìm được / hook đã nằm ngay đầu clip (tránh lặp)."""
    hs = signals.get("hook_seg")
    try:
        if isinstance(hs, (list, tuple)) and len(hs) >= 2:
            a, b = float(hs[0]), float(hs[1])
            if b - a >= 1.0 and abs(a - float(segs[0][0])) > 3.0:
                return [round(a, 2), round(min(b, a + 4.0), 2)]
            return None
    except (ValueError, TypeError):
        pass
    audio = get_analysis(video_id, "audio")   # fallback: cửa sổ 2.5s to nhất
    if not audio:
        return None
    best, best_sc = None, -1.0
    for s0, e0 in segs:
        t = float(s0)
        while t + 2.5 <= float(e0):
            sc = _audio_score(audio, t, t + 2.5)
            if sc > best_sc:
                best_sc, best = sc, [round(t, 2), round(t + 2.5, 2)]
            t += 1.0
    if best and abs(best[0] - float(segs[0][0])) > 3.0:
        return best
    return None


def _cleanup_files(paths) -> None:
    """Xóa best-effort danh sách file tạm (bỏ qua đường dẫn rỗng/lỗi)."""
    for f in paths:
        if not f:
            continue
        try:
            os.remove(f)
        except OSError:
            pass


def export_clip(payload: dict, ctx: JobContext) -> dict:
    """Handler job 'm1_export_clip' — bọc dọn FILE TẠM quanh _export_clip_impl.

    Đo thật cho thấy _cache tích tụ file tạm khi export LỖI/HỦY (mỗi clip:
    _dub_*.wav ~30-50MB, _ovl_*.png, _cap_*.ass) — trước đây chỉ dọn khi
    THÀNH CÔNG. Quy tắc dọn:
      - _dub_/_cap_ (dựng lại được mỗi lượt chạy): dọn MỌI trường hợp
        (xong/hủy/lỗi — lượt thử lại tự dựng lại).
      - _ovl_ (UI render sẵn, handler KHÔNG dựng lại được): dọn khi xong/hủy;
        khi lỗi chỉ dọn nếu job đã HẾT lượt thử lại (giữ cho retry ra đúng chữ).
    """
    temps: list = []                       # impl append: _dub_*.wav, _cap_*.ass
    ovl = str(payload.get("overlay_png") or "")
    ovl_tmp = ovl if os.path.basename(ovl).startswith("_ovl_") else ""
    try:
        result = _export_clip_impl(payload, ctx, temps)
    except CanceledError:
        _cleanup_files(temps + [ovl_tmp])
        raise
    except Exception:
        _cleanup_files(temps)
        row = db.query_one("SELECT attempts, max_attempts FROM jobs WHERE id=?",
                           (ctx.job_id,))
        if ovl_tmp and (not row or row["attempts"] >= row["max_attempts"]):
            _cleanup_files([ovl_tmp])      # lỗi HẲN (không retry nữa) -> dọn nốt
        raise
    _cleanup_files(temps + [ovl_tmp])
    return result


def _export_clip_impl(payload: dict, ctx: JobContext, temps: list) -> dict:
    """
    Thân job 'm1_export_clip'.
    payload: {clip_id, out_w?, out_h?}
    Đọc face-track đã cache -> crop bám mặt -> xuất 9:16.
    temps: danh sách file tạm tạo ra trong lúc chạy (_dub_/_cap_) — caller
    (export_clip) dọn khi job kết thúc, KỂ CẢ lỗi/hủy.
    """
    clip_id = int(payload["clip_id"])
    clip = db.query_one("SELECT * FROM clips WHERE id=?", (clip_id,))
    if not clip:
        raise ValueError(
            "Clip không còn tồn tại (đã bị xóa hoặc danh sách gợi ý đã được "
            "tạo lại) — hãy xuất lại từ danh sách clip hiện tại.")

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
    # Ưu tiên out_dir (kho chung/thư mục riêng của kênh) > export_dir DB (cũ)
    # > assets/clips.
    base = Path(payload.get("out_dir") or vrow["export_dir"]
                or (Path(vrow["assets_dir"]) / "clips"))
    # flat=True (kênh có THƯ MỤC LƯU RIÊNG): Part vào THẲNG base, KHÔNG tạo
    # folder con theo tên video (nhiều video chung 1 folder — chống trùng tên
    # file bên dưới lo). flat=False: giữ như cũ (1 folder/video).
    flat = bool(payload.get("flat"))
    vid_folder = _safe_name(Path(src).stem) or f"video_{video_id}"
    out_dir = base if flat else (base / vid_folder)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # ổ rút / đường dẫn không truy cập được -> báo rõ để user biết
        raise RuntimeError(
            f"Thư mục lưu của kênh không truy cập được: {out_dir} ({e})")
    part_no = int(payload.get("part_no", 0) or 0)
    # limit rộng hơn (120): out_name = "Part N <tiêu đề ~70> #tag #tag #tag" -> để
    # 70 sẽ cắt cụt hashtag. _safe_name vẫn bỏ ký tự cấm, GIỮ '#' + chữ có dấu/nhật.
    safe = _safe_name(payload.get("out_name", "") or "", limit=120)  # "Part N <tiêu đề> #tags"
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
    flip_h = bool(payload.get("flip_h"))        # LẬT GƯƠNG ngang (né content-ID)
    signals = db.loads(clip["signals"], {}) or {}

    pfx = f"Part {part_no} — " if part_no > 0 else ""   # cho user biết đang xuất Part nào

    def on_prog(p: float):
        ctx.progress(0.15 + 0.8 * p, f"{pfx}đang cắt + chèn chữ + xuất 9:16...")

    if video_rect:
        # ---- Mô hình CapCut: nền + khối video (ghép các khúc hay) ----
        # Mixed-Cut CŨNG đi nhánh này khi có mẫu (video_rect): các moments trở
        # thành segments -> ăn ĐỦ mẫu (nền/chữ/phụ đề/tốc độ/giọng/nhạc/logo)
        # thay vì export_stitched_clip bỏ qua toàn bộ mẫu.
        if signals.get("mode") == "mixed":
            segs = ([[m["start"], m["end"]]
                     for m in signals.get("moments", [])]
                    or [[clip["start_sec"], clip["end_sec"]]])
        else:
            segs = signals.get("segments") or [[clip["start_sec"], clip["end_sec"]]]
        # 🎙 RECAP: clip có KỊCH BẢN thuyết minh (m2_recap) -> dựng track giọng
        # AI + tắt tiếng gốc trong các khoảng narrate. Mốc part theo timeline
        # video gốc nên hook-first (chèn đoạn lên đầu) sẽ làm LỆCH — bỏ qua.
        recap_meta = signals.get("recap") or {}
        recap_parts = recap_meta.get("parts") or []
        is_recap = bool(recap_parts)
        # HOOK-FIRST: chiếu 2-4s cao trào nhất lên ĐẦU clip giữ chân người xem
        if payload.get("hook_first") and not is_recap:
            hseg = _pick_hook_seg(video_id, signals, segs)
            if hseg:
                segs = [hseg] + [list(p) for p in segs]
        pre_crop = None
        if payload.get("trim_black"):
            ctx.progress(0.08, f"{pfx}đang dò viền đen...")
            pre_crop = detect_black_crop(src, segs[0][0])
        # LỒNG TIẾNG AI: dựng track thuyết minh (dịch + TTS) TRƯỚC khi export.
        # Dựng theo segs SAU hook-first -> mốc khớp đúng timeline đầu ra.
        dub_path = None
        dub_segs = None
        dub_stretch = 1.0            # >1 ở chế độ "Khớp video": làm chậm đều clip
        duck_ranges = None           # 🎙 recap: các khoảng TẮT tiếng gốc (đầu ra)
        narr_events = None           # 🎙 recap: [{"start","end","text"}] thuyết minh
        dim_ranges = None            # 🔦 recap: các đoạn AI KỂ -> làm tối nhẹ hình
        # 🔦 Mức làm tối video khi AI kể (spotlight). Mặc định 0.14 (BẬT).
        # payload["recap_dim"] (%/ratio từ ⚙ Cài đặt Reup) override; <=0 -> tắt.
        try:
            dim_amount = float(payload.get("recap_dim", 0.14))
            if dim_amount > 1.0:     # nhận cả dạng phần trăm (vd 14 -> 0.14)
                dim_amount = dim_amount / 100.0
        except (TypeError, ValueError):
            dim_amount = 0.14
        dim_amount = max(0.0, min(0.5, dim_amount))
        if is_recap:
            # ---- 🎙 REUP THUYẾT MINH: TTS kịch bản -> track narration ----
            # (thay cho lồng tiếng dub thường; dub_lang của mẫu bị bỏ qua)
            # GIỌNG KỂ: recap_voice từ "Cài đặt Reup thuyết minh" (toàn cục);
            # rỗng -> dub_voice của payload (mẫu cũ, tương thích ngược) ->
            # rỗng nốt thì build_recap_track tự chọn theo ngôn ngữ video.
            from app.core import dubbing
            tr_rec = get_analysis(video_id, "transcript") or {}
            lang = (recap_meta.get("lang") or tr_rec.get("language") or "")
            cdir = Path(vrow["assets_dir"]) / "_cache"
            cdir.mkdir(parents=True, exist_ok=True)
            dw = str(cdir / f"_dub_{clip_id}.wav")
            temps.append(dw)          # dọn khi job kết thúc (kể cả lỗi/hủy)
            ctx.progress(0.05, f"{pfx}đang thu giọng thuyết minh AI...")
            try:                      # "Âm lượng giọng kể" (⚙ Cài đặt Reup)
                _rvol = float(payload.get("recap_volume", 1.15) or 1.15)
            except (TypeError, ValueError):
                _rvol = 1.15
            dub_path, narr_events = dubbing.build_recap_track(
                recap_parts, segs,
                payload.get("recap_voice") or payload.get("dub_voice") or "",
                lang, dw,
                pace=payload.get("recap_pace") or "normal",
                # "Tông giọng" (⚙ Cài đặt Reup) -> pitch edge-tts
                pitch=payload.get("recap_pitch") or "normal",
                # src: đo loudness tiếng gốc -> auto-match âm lượng giọng kể
                src_path=src, volume=_rvol,
                # 🎭 Giọng cảm xúc (audio tag v3) — BẬT + giọng ElevenLabs ->
                # model eleven_v3 đọc [excited]/CAPS; giọng khác strip tag.
                emotion=bool(payload.get("recap_emotion", True)),
                on_progress=lambda p, m="": ctx.progress(
                    0.05 + 0.10 * p, f"{pfx}thuyết minh: {m}"))
            # Khoảng HẠ tiếng gốc ở timeline ĐẦU RA SAU speed (chia speed
            # như dub — filter duck đặt sau atempo trong export_canvas_clip).
            # Dùng n["duck"] = khoảng AI NÓI THẬT (speech±pad, kẹp trong
            # part) — KHÔNG duck cả part: lời ngắn hơn part thì phần còn lại
            # tiếng gốc TRỞ LẠI bình thường (hết 'khoảng chết' câm lặng).
            spd = max(0.5, min(3.0, float(payload.get("speed", 1.0) or 1.0)))
            duck_ranges = []
            for n in narr_events:
                da, de = n.get("duck") or (n["start"], n["end"])
                duck_ranges.append((float(da) / spd, float(de) / spd))
            # 🔦 SPOTLIGHT: LÀM TỐI NHẸ hình đúng các ĐOẠN AI KỂ. Dùng
            # start/end của part narrate (KHÔNG dùng "duck") -> khoảng ỔN
            # ĐỊNH thị giác, không nhấp nháy theo từng câu nói. Cùng hệ quy
            # chiếu timeline đầu ra (chia speed) như duck_ranges.
            if dim_amount > 0.0005:
                dim_ranges = [(float(n["start"]) / spd, float(n["end"]) / spd)
                              for n in narr_events]
        elif payload.get("dub_lang") and payload.get("dub_enable"):
            from app.core import dubbing
            tr_dub = get_analysis(video_id, "transcript") or {}
            # 🛡 CLIP THƯỜNG KHÔNG BỊ LỒNG TIẾNG OAN: lồng tiếng chỉ có nghĩa khi
            # DỊCH sang ngôn ngữ KHÁC. Nếu ngôn ngữ đích TRÙNG ngôn ngữ gốc của
            # video (vd video Nhật + mẫu lỡ để dub_lang=ja) -> KHÔNG dịch gì,
            # chỉ tạo giọng AI đè + (nếu dub_mute) tắt hẳn tiếng gốc -> đúng
            # triệu chứng "clip thường mất tiếng gốc, đọc giọng AI". Bỏ qua dub
            # trong trường hợp này -> GIỮ NGUYÊN tiếng gốc. Dịch chéo ngôn ngữ
            # (user CHỦ Ý) vẫn chạy bình thường.
            # CHUẨN HÓA về TÊN ANH ("Japanese"/"English") trước khi so: Groq
            # trả language dạng TÊN ("Japanese") còn dub_lang là MÃ ISO ("ja")
            # -> so chuỗi thô sẽ HỤT (Japanese != ja). recap.lang_en_name map
            # cả tên lẫn mã về cùng 1 chuẩn.
            from app.ai import recap as _recap
            _src_raw = (tr_dub.get("language") or "").strip()
            _dub_raw = str(payload.get("dub_lang") or "").strip()
            _src_lang = _recap.lang_en_name(_src_raw).strip().lower()
            _dub_lang = _recap.lang_en_name(_dub_raw).strip().lower()
            _same_lang = bool(_src_raw) and _src_lang == _dub_lang
            if _same_lang:
                ctx.progress(0.05, f"{pfx}bỏ lồng tiếng (đích trùng ngôn ngữ "
                             "gốc) — giữ nguyên tiếng gốc")
            if tr_dub.get("segments") and not _same_lang:
                cdir = Path(vrow["assets_dir"]) / "_cache"
                cdir.mkdir(parents=True, exist_ok=True)
                dw = str(cdir / f"_dub_{clip_id}.wav")
                temps.append(dw)          # dọn khi job kết thúc (kể cả lỗi/hủy)
                ctx.progress(0.05, f"{pfx}đang tạo lồng tiếng AI...")
                dub_path, dub_segs, dub_stretch = dubbing.build_dub_track(
                    tr_dub, segs, payload["dub_lang"],
                    payload.get("dub_voice") or "", dw,
                    dub_mode=payload.get("dub_mode", "natural") or "natural",
                    on_progress=lambda p, m="": ctx.progress(
                        0.05 + 0.10 * p, f"{pfx}lồng tiếng: {m}"))
        # PHỤ ĐỀ CHẠY CHỮ + HOOK giật tít. HOOK render ĐỘC LẬP với phụ đề: bật
        # hook mà tắt phụ đề vẫn hiện hook; chữ hook = hook AI -> title_pub ->
        # tiêu đề clip. 🌐 CHỮ TRÊN VIDEO PHẢI ĐÚNG NGÔN NGỮ VIDEO: tiêu đề
        # clip ("title") là TIẾNG VIỆT cho người dựng đọc — video KHÔNG phải
        # tiếng Việt thì TUYỆT ĐỐI không đốt nó lên video (user báo video Nhật
        # bị gắn tiêu đề Việt). Ứng viên trông-tiếng-Việt bị loại; hết ứng viên
        # -> lùi về CÂU THOẠI ĐẦU của clip (đúng ngôn ngữ gốc), vẫn không có
        # -> bỏ trống hook (thà không chữ còn hơn sai ngôn ngữ).
        ass_path = fonts_dir = None
        _cs0 = payload.get("cap_style") or {}
        _hook_txt0 = ""
        if _cs0.get("hook_on", True):
            from app.ai import recap as _rec
            _tr0 = get_analysis(video_id, "transcript") or {}
            _lang0 = _rec.resolve_lang(
                _tr0.get("language", ""), _tr0.get("text", "") or "")
            _vi_video = _rec._is_vi_lang(_lang0)
            for _cand in (signals.get("hook"), signals.get("title_en"),
                          clip["title"]):
                _cand = str(_cand or "").strip()
                if not _cand:
                    continue
                if not _vi_video and _rec.looks_vietnamese(_cand):
                    continue           # video không phải Việt -> loại chữ Việt
                _hook_txt0 = _cand
                break
            if not _hook_txt0:
                # câu thoại ĐẦU trong phạm vi clip = hook đúng ngôn ngữ gốc
                _c0, _c1 = float(clip["start_sec"]), float(clip["end_sec"])
                for _sg in (_tr0.get("segments") or []):
                    try:
                        _a = float(_sg.get("start", 0))
                    except (TypeError, ValueError):
                        continue
                    _t = str(_sg.get("text") or "").strip()
                    if _t and _c0 - 0.5 <= _a <= _c1:
                        _hook_txt0 = _t[:60]
                        break
        if payload.get("captions") or _hook_txt0:
            from app.core import captions
            from config import ROOT_DIR
            tr = get_analysis(video_id, "transcript") or {}
            words = (tr.get("words") or []) if payload.get("captions") else []
            if payload.get("captions") and not words and tr.get("segments"):
                # Groq transcribe có thể KHÔNG trả mốc từng-từ -> nếu bỏ qua
                # thì mất cả PHỤ ĐỀ lẫn HOOK. Tạo words giả từ segments.
                words = _fake_words_from_segments(tr["segments"])
            cap_segs = segs
            extra_cues = None
            if is_recap and payload.get("captions"):
                # 🎙 RECAP: MỌI phụ đề đi qua extra_cues (nhất quán timeline
                # đầu ra — burn trước setpts) -> KHÔNG dùng đường words/
                # _remap_words nữa (dễ rớt khi mốc part gốc lệch mốc segment
                # ghép). 2 loại cue render đồng thời, KHÔNG đè (part rời nhau):
                #   - NARRATE: phụ đề lời KỂ AI (Style Narrate).
                #   - ORIG: phụ đề LỜI GỐC nhân vật word-level (Style Default,
                #     như clip thường) — sửa lỗi 'đoạn gốc không có phụ đề'.
                orig_cues = _recap_orig_caption_cues(
                    recap_parts, segs, words, tr.get("segments") or [])
                narr_cues = _recap_caption_cues(narr_events or [])
                # 🔤 KIỂU 'CỤM' (group): trước đây recap LUÔN tách TỪNG TỪ dù
                # user chọn cụm (lỗi 'chọn chạy chữ theo cụm nhưng hiện 1
                # chữ'). Preset gốc là group -> GOM cue orig thành cụm 2-3 từ;
                # preset chữ AI (narr_preset, '' -> giống gốc) là group -> gom
                # cue narrate. Gom xong đổi kind word->sent (build_ass render
                # 1 Dialogue/cụm) — KHÁC kiểu word (1 Dialogue/từ).
                from app.core import captions as _cap
                _cs_pre = str(_cs0.get("preset") or "") or "Trắng đơn giản"
                _np = str(_cs0.get("narr_preset") or "")
                if _cap.preset_mode(_cs_pre) == "group":
                    orig_cues = _group_recap_cues(orig_cues, "orig_sent")
                _narr_eff = (_cs_pre if (not _np
                             or _np == _cap.NARR_SAME_LABEL) else _np)
                if _cap.preset_mode(_narr_eff) == "group":
                    narr_cues = _group_recap_cues(narr_cues, "sent")
                extra_cues = list(orig_cues) + list(narr_cues)
                words = []          # recap: không dùng đường words trực tiếp
            if dub_segs and payload.get("captions"):
                # CÓ LỒNG TIẾNG -> phụ đề dùng CHỮ ĐÃ DỊCH. Bản dịch không có
                # mốc từng-từ -> tạo words GIẢ chia đều thời gian cụm cho từng
                # từ; mốc đã ở timeline ĐẦU RA nên segments = [[0, tổng]].
                words = []
                for d in dub_segs:
                    # CJK-aware: bản dịch Nhật/Trung/Thái không có dấu cách
                    # vẫn ra cụm 2-4 ký tự (non-CJK y hệt .split() cũ)
                    toks = _caption_tokens(d["text"] or "")
                    if not toks:
                        continue
                    step = max(0.05, (d["end"] - d["start"]) / len(toks))
                    for k, tk in enumerate(toks):
                        words.append({"start": d["start"] + k * step,
                                      "end": d["start"] + (k + 1) * step,
                                      "word": tk})
                # dub_segs ở timeline GỐC (chưa giãn): phụ đề đốt trước setpts
                # nên khung = tổng gốc; setpts sẽ giãn chữ cùng video khi có
                # dub_stretch (như cơ chế `speed`).
                cap_segs = [[0.0, sum(float(e) - float(s) for s, e in segs)]]
            cs = _cs0
            hook_txt = _hook_txt0
            # HOOK không cần words -> vẫn vẽ khi transcript trống/lỗi/tắt phụ đề
            if words or hook_txt.strip() or extra_cues:
                cdir = Path(vrow["assets_dir"]) / "_cache"
                cdir.mkdir(parents=True, exist_ok=True)
                ap = str(cdir / f"_cap_{clip_id}.ass")
                temps.append(ap)          # dọn khi job kết thúc (kể cả lỗi/hủy)
                csize = float(cs.get("size") or 0)
                if captions.build_ass(
                        words, cap_segs, ap, out_w, out_h,
                        font=cs.get("font") or "Montserrat",
                        size=int(csize * out_h) if csize < 1 else int(csize),
                        color=cs.get("color") or "",
                        # màu viền / độ dày viền TÙY CHỌN cho Style Default
                        cap_outline=str(cs.get("cap_outline") or ""),
                        cap_ow=float(cs.get("cap_ow", 0.0) or 0.0),
                        ny=float(cs.get("ny", 0.78)),
                        preset=cs.get("preset") or "Trắng đơn giản",
                        delay=float(cs.get("delay", 0.12)),
                        hook=hook_txt,
                        hook_dur=float(cs.get("hook_dur", 6.0)),
                        hook_nx=float(cs.get("hook_nx", 0.5)),
                        hook_ny=float(cs.get("hook_ny", 0.10)),
                        hook_size=float(cs.get("hook_size", 0) or 0),
                        extra_cues=extra_cues,
                        # 🎙 CHỮ AI ĐỌC (Chỉnh mẫu) — chỉ ảnh hưởng cue narrate
                        # (Style Narrate); clip thường/đoạn gốc bỏ qua. Lấy TỪ
                        # MẪU (cap_style), KHÔNG từ ⚙ Cài đặt Reup nữa.
                        narr_color=str(cs.get("narr_color") or ""),
                        narr_outline=str(cs.get("narr_outline") or ""),
                        narr_ow=float(cs.get("narr_ow", 0.0) or 0.0),
                        # KIỂU chạy chữ riêng cho chữ AI ('(giống phụ đề gốc)'
                        # -> Style Default). narr_same giữ cho tương thích.
                        narr_preset=str(cs.get("narr_preset") or ""),
                        narr_font=str(cs.get("narr_font") or ""),
                        narr_italic=(
                            None if cs.get("narr_italic") is None
                            else bool(cs.get("narr_italic"))),
                        narr_same=bool(cs.get("narr_same", False)),
                        narr_ny=float(cs.get("narr_ny", 0.0) or 0.0),
                        narr_size=float(cs.get("narr_size", 0.0) or 0.0),
                        # KIỂU CHỮ HOA từng phần (Chỉnh mẫu): áp lên CHỮ HIỂN
                        # THỊ, KHÔNG đổi mốc/timing.
                        cap_case=str(cs.get("cap_case") or ""),
                        narr_case=str(cs.get("narr_case") or ""),
                        hook_case=str(cs.get("hook_case") or "")):
                    ass_path = ap
                    fonts_dir = str(ROOT_DIR / "app" / "assets" / "fonts")
        ctx.progress(0.15, f"{pfx}đang dựng khung (nền + video + phụ đề)...")
        # NGỮ CẢNH tiếng chuyển đoạn theo cấu trúc đoạn: recap biết vai part
        # (orig climax -> impact, kết -> reveal, mở mạch kể -> riser); clip
        # thường/Mixed -> transition. Thư viện SFX đóng gói chọn đúng loại.
        join_cats = _join_categories(segs, recap_parts, is_recap, signals)
        export_canvas_clip(
            src, out_path, [(s, e) for s, e in segs],
            tuple(video_rect), bg=bg, out_w=out_w, out_h=out_h,
            encoder=encoder, overlay_png=overlay_png, pre_crop=pre_crop,
            ass_path=ass_path, fonts_dir=fonts_dir,
            blur_amt=int(payload.get("blur_amt", 22)),
            speed=float(payload.get("speed", 1.0)),
            pitch=float(payload.get("pitch", 1.0)),
            bgm_path=payload.get("bgm_path") or None,
            bgm_vol=float(payload.get("bgm_vol", 0.15)),
            orig_vol=float(payload.get("orig_vol", 1.0)),
            dub_path=dub_path,
            duck_ranges=duck_ranges,
            # 🔦 SPOTLIGHT: làm tối nhẹ hình lúc AI kể (chỉ recap; clip
            # thường dim_ranges=None -> KHÔNG dim). dim_amount đã gate ở trên.
            dim_ranges=dim_ranges,
            dim_amount=dim_amount,
            # recap: KHÔNG tắt hẳn tiếng gốc theo cờ dub_mute của mẫu — đoạn
            # orig phải giữ tiếng; duck_ranges đã HẠ nền đúng lúc AI nói.
            dub_mute_original=bool(payload.get("dub_mute")) and not is_recap,
            dub_stretch=dub_stretch,
            fx_fade=bool(payload.get("fx_fade", True)),
            fx_whoosh=bool(payload.get("fx_whoosh", True)),
            fx_sfx_dir=payload.get("fx_sfx_dir") or None,
            join_categories=join_cats,
            flip_h=flip_h,
            # KHUNG TỰ KHỚP TỈ LỆ VIDEO GỐC (không mất hình): export_canvas_clip
            # tự tính lại video_rect theo tỉ lệ nguồn (đã có probe sẵn ở đó).
            fit_src=bool(payload.get("fit_src")),
            on_progress=on_prog,
        )
        # (wav lồng tiếng + .ass tạm được caller export_clip dọn qua `temps`)
        result_extra = {"canvas": True, "bg": bg, "n_seg": len(segs),
                        "captions": bool(ass_path),
                        "dub": (payload.get("dub_lang", "") if dub_path
                                and not is_recap else ""),
                        "recap": is_recap,
                        "mixed": signals.get("mode") == "mixed"}
    elif signals.get("mode") == "mixed":
        # ---- Mixed-Cut KHÔNG có mẫu (video_rect): ghép kiểu cũ (crop bám mặt),
        # crop thủ công không áp dụng ----
        ctx.progress(0.1, f"{pfx}đang ghép các đoạn (Mixed-Cut)...")
        export_stitched_clip(
            src, out_path, signals.get("moments", []),
            out_w=out_w, out_h=out_h, encoder=encoder,
            mode=(mode if mode != "manual" else "face"), zoom=zoom,
            text_overlays=text_overlays, overlay_png=overlay_png,
            flip_h=flip_h,
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
            flip_h=flip_h,
            on_progress=on_prog,
        )
        result_extra = {"mode": mode}

    db.execute(
        "UPDATE clips SET status='exported', export_path=? WHERE id=?",
        (str(out_path), clip_id),
    )
    # (PNG lớp chữ tạm _ovl_ được caller export_clip dọn — kể cả lỗi/hủy)
    ctx.progress(1.0, "Đã xuất clip")
    return {"clip_id": clip_id, "export_path": str(out_path), **result_extra}


# ---- đăng ký handler với worker ----
register_handler("m1_export_clip", export_clip)
