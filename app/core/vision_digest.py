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

#: ---- SỐ MỐC HÌNH TỐI THIỂU ĐỂ XEM HÌNH CÓ NGHĨA ----
#: ĐO A/B 60 lượt thật 09/08/2026 (6 video × 5 vòng × 2 bên, cùng máy, đan xen):
#:   video 728 s (12 mốc) -> lựa chọn chồng lấn chỉ **6,8%**  (p=0,024)
#:   video 150 s ( 8 mốc) -> chồng lấn **23,4%**              (p=0,008)
#:   video  53 s ( 3 mốc) -> chồng lấn **100%** = chọn Y HỆT bản không xem hình
#: Tức dấu hiệu KHÔNG phải "video nói nhiều/ít" (hiệu ứng mạnh NHẤT lại ở video
#: mật độ lời cao nhất 4,25 từ/giây) mà là **SỐ MỐC HÌNH**: dưới ngưỡng này thì
#: digest quá thưa để đổi được lựa chọn, tiền và giây bỏ ra là bỏ không.
#: Nguồn ~53 s chỉ được 3 mốc vì app rải ~20 s/khung (xem `_STEP`, `_CAP`).
MOC_TOI_THIEU = 8

#: ---- CHỐT CHẶN GROQ QUÁ TẢI (503 'over capacity') ----
#: ĐO 09/08/2026: 1 video trong bộ A/B dính 503 CẢ 5/5 vòng -> **+244 giây**,
#: trong khi 5 video còn lại chỉ +1,6 .. +10,6 giây. 503 KHÔNG khớp
#: `is_rate_limit_error` nên không đốt key (đúng) — nhưng cũng vì thế app cứ
#: thử tiếp hết batch này tới batch khác và mất hàng phút cho thứ chắc chắn
#: hỏng. Quá ngần này giây HOẶC quá ngần này lượt 503 -> BỎ XEM HÌNH cho video
#: đó, đi tiếp bằng chép lời (fail-safe đã có sẵn), ghi lý do vào nhật ký.
VISION_HAN_GIAY = 28.0
VISION_503_TOI_DA = 2

_VISION_PROMPT = (
    "You are analyzing frames sampled from ONE video (in order). For EACH "
    "image, return a JSON array item: {\"i\": image index starting at 0, "
    "\"desc\": ONE short English sentence (<=15 words) describing what is "
    "happening on screen, \"act\": 0-10 integer = how visually exciting "
    "(action, motion, surprise, emotion, eye-catching) the frame is; "
    "static/black/text-only screens score 0-2, calm talking 3-5, strong "
    "action/impact/emotion 7-10}. Return ONLY the JSON array, no prose.")


def xem_hinh_kenh(video_id) -> "bool | None":
    """AI XEM HÌNH của KÊNH chứa video này: True/False/**None = chưa đặt**.

    Vì sao tra ở ĐÂY chứ không bắt mỗi nơi gọi tự truyền xuống: cổng 19 đã ghi
    lỗi thật (a) — mẫu-riêng-theo-kênh chỉ được áp ở đường DÂY CHUYỀN tự động
    vì caller phải tự đổi biến, nên "Xuất video này"/"Xuất cả kênh" bấm tay vẫn
    ăn cấu hình trang chính. Đặt việc tra cứu vào CỬA DUY NHẤT mà mọi đường
    phân tích đều đi qua thì không đường nào bỏ sót được.

    KHÔNG BAO GIỜ NÉM: DB cũ chưa có cột / DB vỡ / video mồ côi -> None (y hệt
    hành vi v2.21.0)."""
    try:
        from app.database.db import db as _db
        r = _db.query_one("SELECT project_id FROM videos WHERE id=?",
                          (int(video_id),))
        if not r:
            return None
        from app import services as _sv
        return _sv.project_vision(r["project_id"])
    except Exception:  # noqa: BLE001 - tra không ra -> theo mặc định app
        return None


def vision_digest_enabled(bat_buoc: bool = False, kenh=None) -> bool:
    """Có nên xây digest không: USE_VISION bật + KHÔNG LIGHT_MODE (máy yếu
    bỏ qua như cũ) + provider hiện tại nhìn được hình. Hàm rẻ, gọi trước để
    quyết định có hiện progress 'AI đang xem khung hình' hay không.

    `kenh`: lựa chọn RIÊNG của kênh (`projects.xem_hinh`) — True = bật ·
    False = tắt · **None = kênh chưa đụng tới -> đi đúng đường v2.21.0**.
    """
    if not getattr(settings, "USE_VISION", False):
        return False
    # bat_buoc: gọi từ ca KHÔNG CÒN CĂN CỨ NÀO KHÁC (video không lời nói) —
    # lúc đó hình là tất cả những gì AI có, nên bật kể cả khi VISION_CUT tắt.
    # Đứng TRƯỚC ô của kênh: anh Hùng chốt "video KHÔNG có lời vẫn tự bật như
    # hiện nay, không phụ thuộc ô này".
    if bat_buoc:
        return llm.vision_available()
    # Ô BẬT RIÊNG THEO KÊNH (anh Hùng 09/08/2026: "cứ thêm phần bật tuỳ chỉnh
    # từng kênh đã, tôi test xem sao"). Kênh đã chọn thì tiếng nói của kênh là
    # cuối cùng — đè cả VISION_CUT lẫn LIGHT_MODE.
    if kenh is True:
        return llm.vision_available()
    if kenh is False:
        return False
    # kenh None (gần 300 kênh chưa đụng tới) -> TỪ ĐÂY XUỐNG Y HỆT v2.21.0.
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


def nen_xem_hinh(video_id, bat_buoc: bool = False) -> bool:
    """`vision_digest_enabled` CÓ tính ô bật riêng của kênh chứa video này.
    Dùng ở nơi cần biết TRƯỚC (để hiện dòng tiến trình) — `build_vision_digest`
    tự tra lại nên nơi gọi quên hàm này cũng không lọt."""
    return vision_digest_enabled(bat_buoc, xem_hinh_kenh(video_id))


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


def _describe_batch(paths: list, key_dau: int = 0) -> list:
    """Gọi vision 1 batch ảnh -> [{'i','desc','act'}] (i là index TRONG batch).
    Ném lỗi cho caller quyết (caller bỏ batch lỗi, giữ batch khác).

    `key_dau`: mốc xuất phát trong vòng xoay key — để các lượt chạy SONG SONG
    không chen vào cùng một hàng đợi (xem `llm.complete_vision_json`)."""
    data = llm.complete_vision_json(_VISION_PROMPT, paths, key_dau=key_dau)
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


def la_loi_qua_tai(msg: str) -> bool:
    """Lỗi Groq **QUÁ TẢI** (503 'over capacity' / 'service unavailable').

    Phân biệt rạch ròi với 3 loại đã có: 429 = key hết lượt (phạt key, đợi) ·
    413 = yêu cầu quá to (thu nhỏ, KHÔNG phạt key) · 503 = **máy chủ họ đang
    quá tải** — không phải lỗi của key, không phải lỗi của yêu cầu, và đợi
    trong cùng một lượt cắt cũng chẳng giúp gì. Hàm thuần."""
    m = (msg or "").lower()
    if "413" in m or "too large" in m:
        return False            # 413 có đường xử lý RIÊNG (thu nhỏ), đừng lẫn
    return any(s in m for s in ("503", "over capacity", "overloaded",
                               "service unavailable", "service_unavailable",
                               "temporarily unavailable"))


class _ChotQuaTai:
    """Sổ theo dõi 'video này có đáng xem hình tiếp không'.

    Giữ mốc bắt đầu + số lượt 503. Quá `VISION_HAN_GIAY` giây HOẶC quá
    `VISION_503_TOI_DA` lượt 503 -> `nen_dung()` = True, mọi batch còn lại bị
    BỎ QUA (không gọi mạng thêm một lượt nào) và caller ghi nhật ký."""

    def __init__(self, han_giay: float = None, so_503: int = None):
        import time as _t
        self._t = _t
        self.moc = _t.monotonic()
        self.han = float(VISION_HAN_GIAY if han_giay is None else han_giay)
        self.tran_503 = int(VISION_503_TOI_DA if so_503 is None else so_503)
        self.n_503 = 0
        self.ly_do = ""

    def da_ton(self) -> float:
        return self._t.monotonic() - self.moc

    def ghi_loi(self, err: str) -> None:
        if err and la_loi_qua_tai(err):
            self.n_503 += 1

    def nen_dung(self) -> bool:
        if self.n_503 >= self.tran_503:
            self.ly_do = (f"Groq QUÁ TẢI (503) {self.n_503} lượt >= "
                          f"{self.tran_503} — bỏ xem hình cho video này, đi "
                          f"tiếp bằng chép lời")
            return True
        d = self.da_ton()
        if d > self.han:
            self.ly_do = (f"xem hình quá {self.han:.0f}s (đã {d:.1f}s) — bỏ "
                          f"phần còn lại, đi tiếp bằng chép lời")
            return True
        return False


def _mot_batch(batch: list, key_dau: int = 0, chot=None) -> tuple:
    """MỘT lượt vision -> `(rows, lời_lỗi)`. **KHÔNG BAO GIỜ NÉM** (trừ Huỷ).

    Tách ra khỏi vòng lặp để chạy được cả TUẦN TỰ lẫn SONG SONG bằng đúng một
    đoạn mã — hai nhánh khác nhau là hai chỗ để lệch nhau âm thầm.
    Lỗi -> `([], lý do)`: mất 1 batch vẫn hơn mất cả digest.
    `chot`: sổ quá tải — đã chốt rồi thì KHÔNG gọi mạng nữa (nhánh song song
    submit cả loạt một lượt, chặn ở đây mới thật sự cắt được).
    """
    from app.queue.worker import CanceledError
    if chot is not None and chot.nen_dung():
        return [], ""
    try:
        try:
            return _describe_batch([p for _, p in batch], key_dau), ""
        except llm.LLMTooLarge:
            # HẠN MỨC token/phút của tài khoản Groq có thể siết bất cứ lúc nào
            # (đo 8.000/phút hôm nay, mai Groq đổi là chuyện của họ). Thay vì
            # mất cả batch -> gửi TỪNG ẢNH. Không phạt key nào (xem
            # llm.is_too_large_error).
            rows, loi = [], ""
            for _t1, _p1 in batch:
                try:
                    rows += _sua_i(_describe_batch([_p1], key_dau), batch, _p1)
                except Exception as e2:  # noqa: BLE001
                    loi = f"{type(e2).__name__}: {str(e2)[:200]}"
            return rows, loi
    except CanceledError:
        raise
    except Exception as e:  # noqa: BLE001 - batch lỗi -> bỏ batch đó
        # GHI LẠI lý do. BẪY ĐÃ SẬP 06/08/2026: model vision cấu hình sẵn
        # (llama-4-scout) bị Groq gỡ -> 404 mọi batch -> digest rỗng, mà app
        # không báo gì nên tưởng "AI có xem hình rồi, chỉ là không thấy gì".
        return [], f"{type(e).__name__}: {str(e)[:200]}"


def _gom(digest: list, batch: list, rows) -> None:
    """Nhặt mô tả hợp lệ của 1 batch vào `digest` (gán ĐÚNG mốc giây)."""
    for r in rows or []:
        try:
            i = int(r.get("i", r.get("index")))
            desc = str(r.get("desc") or "").strip()
            act = int(round(float(r.get("act", 0))))
        except (TypeError, ValueError, AttributeError):
            continue
        if 0 <= i < len(batch) and desc:
            digest.append({"t": batch[i][0], "desc": desc[:_DESC_MAX],
                           "act": max(0, min(10, act))})


def _ghi_loi(video_id, ly_do: str, dau: str = "KHÔNG ra mốc nào") -> None:
    """Ghi 1 dòng vào `logs/vision_<ngày>.log` khi AI XEM HÌNH ra 0 mốc **hoặc
    bị BỎ QUA có chủ đích** (nguồn quá ngắn / Groq quá tải).

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
                    f"hình {dau} · model="
                    f"{getattr(settings, 'GROQ_VISION_MODEL', '?')} · {ly_do}\n")
    except Exception:  # noqa: BLE001 - ghi nhật ký không bao giờ được chặn việc
        pass


_TU_TRA = object()      # sentinel: 'chưa biết ô của kênh -> tự tra từ video_id'


def build_vision_digest(video_id: int, src_path: str, duration: float,
                        ctx=None, bat_buoc: bool = False, kenh=_TU_TRA) -> list:
    """Xây (hoặc đọc cache) VISION DIGEST cho 1 video.

    - Gate: vision_digest_enabled() (USE_VISION + Ô CỦA KÊNH + không LIGHT_MODE
      + provider vision) — không đạt -> [] (mọi thứ chạy như cũ). `kenh` bỏ
      trống = TỰ TRA từ `video_id` (cửa duy nhất, không đường nào lọt).
    - CACHE: analysis kind='vision_digest' — có rồi trả luôn, KHÔNG gọi vision.
    - Trích <=_CAP frame (ưu tiên giữa cảnh theo scenes, fallback đều ~20s),
      jpg nhỏ ~480px vào thư mục TẠM (tự dọn), gọi vision BATCH _BATCH ảnh/lần.
    - Dưới `MOC_TOI_THIEU` mốc -> BỎ QUA (đo: chọn Y HỆT bản không xem hình).
    - Groq 503 quá tải / quá `VISION_HAN_GIAY` giây -> bỏ phần còn lại.
    - Lỗi từng batch -> bỏ batch đó (digest thiếu vẫn hơn không); TOÀN BỘ lỗi
      -> trả [] và KHÔNG cache (lần sau thử lại). ctx: progress + check hủy.
    """
    global LOI_CUOI
    LOI_CUOI = ""
    if kenh is _TU_TRA:
        # bat_buoc thắng mọi ô -> khỏi tốn 1 lượt tra DB.
        kenh = None if bat_buoc else xem_hinh_kenh(video_id)
    if not vision_digest_enabled(bat_buoc, kenh):
        LOI_CUOI = "tắt (USE_VISION/ô của kênh/VISION_CUT/không có key vision)"
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
    # ---- BỎ QUA KHI VÔ ÍCH: nguồn quá ngắn -> quá ít mốc hình ----
    # Đo A/B 60 lượt: dưới MOC_TOI_THIEU mốc thì lựa chọn TRÙNG 100% với bản
    # không xem hình. Bỏ ở đây = tiết kiệm mà KHÔNG mất gì. `bat_buoc` (video
    # KHÔNG có lời nói) được đi tiếp: lúc đó hình là căn cứ DUY NHẤT còn lại,
    # 3 mốc vẫn hơn không có gì.
    if not bat_buoc and len(times) < MOC_TOI_THIEU:
        LOI_CUOI = (f"BỎ QUA: nguồn {float(duration or 0):.0f}s chỉ ước lượng "
                    f"{len(times)} mốc hình < {MOC_TOI_THIEU} — đo A/B cho "
                    f"thấy dưới ngưỡng này AI chọn Y HỆT bản không xem hình")
        _ghi_loi(video_id, LOI_CUOI, dau="BỊ BỎ QUA (không tốn lượt nào)")
        return []
    from app.queue.worker import CanceledError
    chot = _ChotQuaTai()
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
            lo = [frames[i:i + _BATCH] for i in range(0, len(frames), _BATCH)]
            n_batch = len(lo)
            # SỐ LƯỢT CHẠY CÙNG LÚC. ĐO 09/08/2026 (`_do_vision_219.py`):
            # **98,7% của 219 giây là ĐỢI MẠNG TUẦN TỰ**, trích khung chỉ 1,3%
            # -> đây đúng là chỗ để song song, và nó KHÔNG tốn thêm CPU máy anh
            # Hùng (chỉ là ổ cắm mạng). `VISION_SONG_SONG=1` -> đường cũ.
            try:
                _ss = int(getattr(settings, "VISION_SONG_SONG", 6) or 1)
            except (TypeError, ValueError):
                _ss = 1
            _ss = max(1, min(_ss, n_batch))
            if _ss <= 1:
                for bi, batch in enumerate(lo):
                    if ctx is not None and hasattr(ctx, "check_canceled"):
                        ctx.check_canceled()
                    # CHỐT QUÁ TẢI/QUÁ GIỜ: kiểm TRƯỚC khi bỏ tiền cho batch
                    # kế. Đo thật: 1 video dính 503 cả 5/5 vòng tốn +244 giây.
                    if chot.nen_dung():
                        break
                    if ctx is not None and hasattr(ctx, "progress"):
                        ctx.progress(0.22 + 0.06 * bi / max(1, n_batch),
                                     f"AI xem khung hình khắp video "
                                     f"({bi + 1}/{n_batch})...")
                    rows, err = _mot_batch(batch, bi, chot)
                    if err:
                        LOI_CUOI = err
                        chot.ghi_loi(err)
                    _gom(digest, batch, rows)
            else:
                if ctx is not None and hasattr(ctx, "check_canceled"):
                    ctx.check_canceled()   # HUỶ: kiểm TRƯỚC khi thả luồng
                if ctx is not None and hasattr(ctx, "progress"):
                    ctx.progress(0.22, f"AI xem khung hình khắp video "
                                       f"({n_batch} lượt song song, mỗi lượt "
                                       f"một key)...")
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=_ss,
                                        thread_name_prefix="vdg") as ex:
                    # `bi` vừa là thứ tự lượt vừa là MỐC XUẤT PHÁT trong vòng
                    # xoay key -> mỗi lượt bắt đầu ở một key khác nhau, không
                    # chen vào cùng một hàng đợi (đo: 40-45s -> 0,9s cho 3/4).
                    ket = list(ex.map(lambda t: _mot_batch(t[1], t[0], chot),
                                      list(enumerate(lo))))
                for (rows, err), batch in zip(ket, lo):
                    if err:
                        LOI_CUOI = err
                        chot.ghi_loi(err)
                    _gom(digest, batch, rows)
                chot.nen_dung()          # để `ly_do` có chữ cho nhật ký
                if ctx is not None and hasattr(ctx, "check_canceled"):
                    ctx.check_canceled()   # bấm Huỷ lúc đang đợi -> nổi lên đây
    except CanceledError:               # user bấm Hủy -> nổi lên cho worker
        raise
    except Exception as e:  # noqa: BLE001 - lỗi khác (ffmpeg/IO...) -> êm như cũ
        LOI_CUOI = f"{type(e).__name__}: {str(e)[:200]}"
        _ghi_loi(video_id, LOI_CUOI)
        return []
    if chot.ly_do:
        # CẮT NGANG có chủ đích -> phải ghi sổ dù có nhặt được vài mốc, nếu
        # không thì "digest thiếu một nửa" lại là một chuyện im lặng nữa.
        LOI_CUOI = chot.ly_do
        _ghi_loi(video_id, chot.ly_do,
                 dau=f"BỊ CẮT NGANG ({len(digest)} mốc nhặt được)")
    elif not digest and LOI_CUOI:
        _ghi_loi(video_id, LOI_CUOI)
    digest.sort(key=lambda d: d["t"])
    if digest and chot.ly_do:
        # BỊ CẮT NGANG -> DÙNG cho lượt này nhưng KHÔNG ĐÓNG DẤU vào cache:
        # Groq quá tải là chuyện của 5 phút, đóng dấu digest cụt là video đó
        # mang bản cụt VĨNH VIỄN (cache theo video, không hết hạn).
        return digest
    if digest:                    # chỉ cache khi CÓ dữ liệu (lỗi tạm -> thử lại)
        try:
            _save_analysis(video_id, VD_KIND, "done", data=digest,
                           engine=f"vision:{llm.active_provider()}")
        except Exception:  # noqa: BLE001 - cache hỏng không chặn kết quả
            pass
    return digest
