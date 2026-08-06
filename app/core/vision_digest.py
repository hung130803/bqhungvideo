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
#: trần số frame/video. 24 -> 12 sau khi ĐO 06/08/2026: model vision Groq chỉ
#: nhận 3 ảnh/lượt và giới hạn 8.000 token/phút, nên 24 khung = 8 lượt gọi =
#: gần 3 phút ngân sách token cho 1 video. 12 khung vẫn phủ khắp video.
_CAP = 12
#: số ảnh/lượt. ĐO THẬT 06/08/2026 với qwen3.6-27b, ảnh 384px (~796 token/ảnh
#: theo hoá đơn, nhưng hạn mức token/phút tính ~2.410/ảnh):
#:    1 ảnh -> ĐẠT (1,6s) · 2 ảnh -> ĐẠT (1,2s) · 3 ảnh -> 413 "Requested 8632
#:    > Limit 8000". Model cũng chỉ nhận tối đa 3 ảnh (400). Nên chốt 2.
_BATCH = 2
_STEP = 20.0                # fallback không có scenes: ~mỗi 20s 1 frame
_FRAME_W = 384              # ảnh nhỏ (jpg) — đỡ tốn token vision
#: lý do lượt xây digest gần nhất trả rỗng (để nhật ký/bộ đo nói được SỰ THẬT
#: thay vì im lặng ra 0 mốc — đúng bẫy đã sập: model 404 mà app không hé nửa
#: lời). Chỉ để đọc, không ai được dựa vào nó để quyết định.
LOI_CUOI = ""
_DESC_MAX = 90              # cắt desc dài (model lắm lời) — giữ prompt gọn

_VISION_PROMPT = (
    "You are analyzing frames sampled from ONE video (in order). For EACH "
    "image, return a JSON array item: {\"i\": image index starting at 0, "
    "\"desc\": ONE short English sentence (<=15 words) describing what is "
    "happening on screen, \"act\": 0-10 integer = how visually exciting "
    "(action, motion, surprise, emotion, eye-catching) the frame is; "
    "static/black/text-only screens score 0-2, calm talking 3-5, strong "
    "action/impact/emotion 7-10}. Return ONLY the JSON array, no prose.")


def vision_digest_enabled(bat_buoc: bool = False) -> bool:
    """Có nên xây digest không: USE_VISION bật + KHÔNG LIGHT_MODE (máy yếu
    bỏ qua như cũ) + provider hiện tại nhìn được hình. Hàm rẻ, gọi trước để
    quyết định có hiện progress 'AI đang xem khung hình' hay không."""
    if not getattr(settings, "USE_VISION", False):
        return False
    # bat_buoc: gọi từ ca KHÔNG CÒN CĂN CỨ NÀO KHÁC (video không lời nói) —
    # lúc đó hình là tất cả những gì AI có, nên bật kể cả khi VISION_CUT tắt.
    if bat_buoc:
        return llm.vision_available()
    # VISION_CUT: bật AI XEM HÌNH cho khâu CHỌN ĐOẠN mà KHÔNG phải tắt
    # LIGHT_MODE. Vì sao tách (anh Hùng 06/08/2026 muốn "AI xem hình để hiểu
    # video ASMR/hành động"): LIGHT_MODE là cờ MÁY YẾU, tắt nó sẽ bật LUÔN
    # faces/scenes/audio (mediapipe rất nặng, và luồng của anh Hùng dùng mẫu
    # khung nên faces vô dụng). Nay xem-hình có công tắc RIÊNG.
    if getattr(settings, "VISION_CUT", False):
        return llm.vision_available()
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


def _sua_i(rows: list, batch: list, path: str) -> list:
    """Gửi LẺ 1 ảnh thì model trả i=0; đổi lại thành chỉ số THẬT của ảnh đó
    trong batch, nếu không mô tả sẽ bị gán cho sai mốc giây."""
    idx = next((k for k, (_t, p) in enumerate(batch) if p == path), None)
    if idx is None:
        return []
    ra = []
    for r in rows or []:
        if isinstance(r, dict):
            r = dict(r)
            r["i"] = idx
            ra.append(r)
    return ra


def _ghi_loi(video_id, ly_do: str) -> None:
    """Ghi 1 dòng vào `logs/vision_<ngày>.log` khi AI XEM HÌNH ra 0 mốc.

    Vì sao phải có: khâu này fail-safe tuyệt đối (lỗi -> [] -> chọn đoạn chạy
    như cũ) nên KHÔNG có gì hiện ra ngoài. Đúng cái đã che mất chuyện model
    vision bị Groq gỡ suốt (404 mọi lượt). Ghi nhật ký = lần sau tra 10 giây."""
    try:
        from datetime import datetime

        from config import DATA_DIR
        d = DATA_DIR / "logs"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"vision_{datetime.now():%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] video {video_id} — AI xem "
                    f"hình KHÔNG ra mốc nào · model="
                    f"{getattr(settings, 'GROQ_VISION_MODEL', '?')} · {ly_do}\n")
    except Exception:  # noqa: BLE001 - ghi nhật ký không bao giờ được chặn việc
        pass


def build_vision_digest(video_id: int, src_path: str, duration: float,
                        ctx=None, bat_buoc: bool = False) -> list:
    """Xây (hoặc đọc cache) VISION DIGEST cho 1 video.

    - Gate: vision_digest_enabled() (USE_VISION + không LIGHT_MODE + provider
      vision) — không đạt -> [] (mọi thứ chạy như cũ).
    - CACHE: analysis kind='vision_digest' — có rồi trả luôn, KHÔNG gọi vision.
    - Trích <=_CAP frame (ưu tiên giữa cảnh theo scenes, fallback đều ~20s),
      jpg nhỏ ~480px vào thư mục TẠM (tự dọn), gọi vision BATCH _BATCH ảnh/lần.
    - Lỗi từng batch -> bỏ batch đó (digest thiếu vẫn hơn không); TOÀN BỘ lỗi
      -> trả [] và KHÔNG cache (lần sau thử lại). ctx: progress + check hủy.
    """
    global LOI_CUOI
    LOI_CUOI = ""
    if not vision_digest_enabled(bat_buoc):
        LOI_CUOI = "tắt (USE_VISION/VISION_CUT/không có key vision)"
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
                    try:
                        rows = _describe_batch([p for _, p in batch])
                    except llm.LLMTooLarge:
                        # HẠN MỨC token/phút của tài khoản Groq có thể siết bất
                        # cứ lúc nào (đo 8.000/phút hôm nay, mai Groq đổi là
                        # chuyện của họ). Thay vì mất cả batch -> gửi TỪNG ẢNH.
                        # Không phạt key nào (xem llm.is_too_large_error).
                        rows = []
                        for _t1, _p1 in batch:
                            try:
                                rows += _sua_i(_describe_batch([_p1]),
                                               batch, _p1)
                            except Exception as e2:  # noqa: BLE001
                                LOI_CUOI = f"{type(e2).__name__}: {str(e2)[:200]}"
                except Exception as e:  # noqa: BLE001 - batch lỗi -> bỏ batch đó
                    # GHI LẠI lý do. BẪY ĐÃ SẬP 06/08/2026: model vision cấu
                    # hình sẵn (llama-4-scout) bị Groq gỡ -> 404 mọi batch ->
                    # digest rỗng, mà app không báo gì nên tưởng "AI có xem
                    # hình rồi, chỉ là không thấy gì đáng kể".
                    LOI_CUOI = f"{type(e).__name__}: {str(e)[:200]}"
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
    except Exception as e:  # noqa: BLE001 - lỗi khác (ffmpeg/IO...) -> êm như cũ
        LOI_CUOI = f"{type(e).__name__}: {str(e)[:200]}"
        _ghi_loi(video_id, LOI_CUOI)
        return []
    if not digest and LOI_CUOI:
        _ghi_loi(video_id, LOI_CUOI)
    digest.sort(key=lambda d: d["t"])
    if digest:                    # chỉ cache khi CÓ dữ liệu (lỗi tạm -> thử lại)
        try:
            _save_analysis(video_id, VD_KIND, "done", data=digest,
                           engine=f"vision:{llm.active_provider()}")
        except Exception:  # noqa: BLE001 - cache hỏng không chặn kết quả
            pass
    return digest
