"""
VISION DIGEST — AI "xem" khung hình KHẮP video 1 LẦN, cache lại, rồi nhét
vào prompt chọn đoạn (cả CẮT THƯỜNG m1 lẫn REUP m2).

Kết quả: list[{"t": giây, "desc": mô tả 1 dòng (EN, ngắn), "act": 0-10}]
  - t    : mốc giây của khung hình (ưu tiên GIỮA mỗi cảnh từ scene cut_points;
           không có scenes -> rải đều ~mỗi _STEP giây; CAP _CAP frame/video).
  - desc : 1 câu <=15 từ mô tả cảnh (tiếng Anh cho gọn token).
  - act  : độ hấp dẫn THỊ GIÁC 0-10 (hành động/bất ngờ/hút mắt) — đoạn ít
           thoại nhưng nhiều hành động nhờ điểm này mà được AI chọn.

CACHE: bảng analysis kind="vision_digest" (UNIQUE(video_id, kind)) — lần cắt
lại đọc cache, KHÔNG gọi vision lần 2. FAIL-SAFE: không vision / LIGHT_MODE /
USE_VISION=0 / lỗi -> trả [] và MỌI THỨ chạy y như cũ (prompt không đổi).
"""
from __future__ import annotations

import os
import tempfile

from config import settings

from app.ai import llm
from app.core.analysis import _set as _save_analysis
from app.core.analysis import get_analysis
from app.core.ffmpeg_utils import extract_frame

VD_KIND = "vision_digest"   # kind trong bảng analysis (cache)
_CAP = 24                   # trần số frame / video (video dài lấy thưa hơn)
_BATCH = 6                  # số ảnh / 1 lời gọi vision (đỡ tốn request)
_STEP = 20.0                # fallback không có scenes: ~mỗi 20s 1 frame
_FRAME_W = 480              # ảnh nhỏ (jpg) — đỡ tốn token vision
_DESC_MAX = 90              # cắt desc dài (model lắm lời) — giữ prompt gọn

_VISION_PROMPT = (
    "You are analyzing frames sampled from ONE video (in order). For EACH "
    "image, return a JSON array item: {\"i\": image index starting at 0, "
    "\"desc\": ONE short English sentence (<=15 words) describing what is "
    "happening on screen, \"act\": 0-10 integer = how visually exciting "
    "(action, motion, surprise, emotion, eye-catching) the frame is; "
    "static/black/text-only screens score 0-2, calm talking 3-5, strong "
    "action/impact/emotion 7-10}. Return ONLY the JSON array, no prose.")


def vision_digest_enabled() -> bool:
    """Có nên xây digest không: USE_VISION bật + KHÔNG LIGHT_MODE (máy yếu
    bỏ qua như cũ) + provider hiện tại nhìn được hình. Hàm rẻ, gọi trước để
    quyết định có hiện progress 'AI đang xem khung hình' hay không."""
    if not getattr(settings, "USE_VISION", False):
        return False
    if getattr(settings, "LIGHT_MODE", True):
        return False
    return llm.vision_available()


def pick_frame_times(duration: float, cut_points=None,
                     cap: int = _CAP, step: float = _STEP) -> list:
    """Chọn mốc giây để trích frame. ƯU TIÊN scene cut_points: lấy ĐIỂM GIỮA
    mỗi cảnh (frame đại diện, né mờ chuyển cảnh); quá cap -> tỉa đều. Không
    có scenes -> rải đều ~mỗi `step` giây (video dài -> giãn ra giữ <=cap).
    Hàm thuần — unit test được."""
    dur = float(duration or 0)
    if dur <= 1.0:
        return []
    cuts = []
    for c in (cut_points or []):
        try:
            v = float(c)
        except (TypeError, ValueError):
            continue
        if 0.0 < v < dur:
            cuts.append(v)
    times: list = []
    if cuts:
        bounds = [0.0] + sorted(cuts) + [dur]
        for a, b in zip(bounds, bounds[1:]):
            if b - a >= 1.0:                    # cảnh teo < 1s -> bỏ
                times.append(round((a + b) / 2.0, 2))
    if not times:                               # fallback: rải đều
        n = max(1, min(int(cap), int(dur // step) + 1))
        times = [round(dur * (k + 0.5) / n, 2) for k in range(n)]
    if len(times) > cap:                        # tỉa ĐỀU giữ đúng cap mốc
        idx = [round(i * (len(times) - 1) / (cap - 1)) for i in range(cap)]
        times = [times[i] for i in sorted(set(idx))]
    return times


def format_digest_block(digest: list, t0: float = None, t1: float = None,
                        max_chars: int = 1500) -> str:
    """Đổi digest -> khối chữ nhét vào prompt (lọc theo khoảng [t0,t1] nếu
    truyền). digest rỗng/không dòng nào lọt khoảng -> "" (prompt Y HỆT cũ).
    Mỗi dòng: 't | desc | act N'. Cắt trần max_chars. Hàm thuần."""
    rows = []
    for d in digest or []:
        try:
            t = float(d["t"])
            desc = str(d.get("desc") or "").strip()
            act = int(d.get("act", 0))
        except (KeyError, TypeError, ValueError):
            continue
        if not desc:
            continue
        if t0 is not None and t < float(t0):
            continue
        if t1 is not None and t > float(t1):
            continue
        rows.append(f"{t:.0f} | {desc[:_DESC_MAX]} | act {max(0, min(10, act))}")
    if not rows:
        return ""
    head = "HÌNH ẢNH THEO MỐC (giây | cảnh trên màn hình | điểm hành động 0-10):"
    out = head
    for r in rows:
        if len(out) + len(r) + 1 > max_chars:
            break
        out += "\n" + r
    return out if out != head else ""


def _describe_batch(paths: list) -> list:
    """Gọi vision 1 batch ảnh -> [{'i','desc','act'}] (i là index TRONG batch).
    Ném lỗi cho caller quyết (caller bỏ batch lỗi, giữ batch khác)."""
    data = llm.complete_vision_json(_VISION_PROMPT, paths)
    if isinstance(data, dict):          # model bọc {"frames":[...]} / {"items":...}
        for k in ("frames", "items", "results", "images"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    return data if isinstance(data, list) else []


def build_vision_digest(video_id: int, src_path: str, duration: float,
                        ctx=None) -> list:
    """Xây (hoặc đọc cache) VISION DIGEST cho 1 video.

    - Gate: vision_digest_enabled() (USE_VISION + không LIGHT_MODE + provider
      vision) — không đạt -> [] (mọi thứ chạy như cũ).
    - CACHE: analysis kind='vision_digest' — có rồi trả luôn, KHÔNG gọi vision.
    - Trích <=_CAP frame (ưu tiên giữa cảnh theo scenes, fallback đều ~20s),
      jpg nhỏ ~480px vào thư mục TẠM (tự dọn), gọi vision BATCH _BATCH ảnh/lần.
    - Lỗi từng batch -> bỏ batch đó (digest thiếu vẫn hơn không); TOÀN BỘ lỗi
      -> trả [] và KHÔNG cache (lần sau thử lại). ctx: progress + check hủy.
    """
    if not vision_digest_enabled():
        return []
    cached = get_analysis(video_id, VD_KIND)
    if isinstance(cached, list):
        return cached
    if not src_path or not os.path.exists(str(src_path)) \
            or float(duration or 0) <= 1.0:
        return []
    scenes = get_analysis(video_id, "scenes") or {}
    times = pick_frame_times(duration, scenes.get("cut_points"))
    if not times:
        return []
    from app.queue.worker import CanceledError
    digest: list = []
    try:
        with tempfile.TemporaryDirectory(prefix="vdg_") as td:
            frames = []                     # [(t, path)]
            for k, t in enumerate(times):
                if ctx is not None and hasattr(ctx, "check_canceled"):
                    ctx.check_canceled()
                fp = os.path.join(td, f"f{k:03d}.jpg")
                if extract_frame(src_path, t, fp, width=_FRAME_W):
                    frames.append((t, fp))
            n_batch = (len(frames) + _BATCH - 1) // _BATCH
            for bi in range(0, len(frames), _BATCH):
                if ctx is not None and hasattr(ctx, "check_canceled"):
                    ctx.check_canceled()
                if ctx is not None and hasattr(ctx, "progress"):
                    ctx.progress(0.22 + 0.06 * (bi // _BATCH) / max(1, n_batch),
                                 f"AI xem khung hình khắp video "
                                 f"({bi // _BATCH + 1}/{n_batch})...")
                batch = frames[bi:bi + _BATCH]
                try:
                    rows = _describe_batch([p for _, p in batch])
                except Exception:  # noqa: BLE001 - batch lỗi -> bỏ riêng batch
                    continue
                for r in rows or []:
                    try:
                        i = int(r.get("i", r.get("index")))
                        desc = str(r.get("desc") or "").strip()
                        act = int(round(float(r.get("act", 0))))
                    except (TypeError, ValueError):
                        continue
                    if 0 <= i < len(batch) and desc:
                        digest.append({"t": batch[i][0],
                                       "desc": desc[:_DESC_MAX],
                                       "act": max(0, min(10, act))})
    except CanceledError:               # user bấm Hủy -> nổi lên cho worker
        raise
    except Exception:  # noqa: BLE001 - lỗi khác (ffmpeg/IO...) -> êm, chạy như cũ
        return []
    digest.sort(key=lambda d: d["t"])
    if digest:                    # chỉ cache khi CÓ dữ liệu (lỗi tạm -> thử lại)
        try:
            _save_analysis(video_id, VD_KIND, "done", data=digest,
                           engine=f"vision:{llm.active_provider()}")
        except Exception:  # noqa: BLE001 - cache hỏng không chặn kết quả
            pass
    return digest
