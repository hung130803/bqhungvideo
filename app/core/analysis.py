"""
Orchestrator của LÕI PHÂN TÍCH DÙNG CHUNG.

Chạy MỘT LẦN khi import video, lưu kết quả từng 'kind' vào bảng `analysis`.
Mọi module sau ĐỌC LẠI qua get_analysis() — TUYỆT ĐỐI không phân tích lại
cùng 1 video (smart-skip nếu kind đã 'done').

kind: transcript | diarization | scenes | audio | faces
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from app.database import db
from config import PROJECTS_DIR
from . import audio_analysis, diarization, face_track, scene_detect, transcribe
from .ffmpeg_utils import extract_audio_wav

ProgressFn = Optional[Callable[[float, str], None]]

# Thứ tự + nhãn hiển thị
STEPS = [
    ("transcript", "Chép lời (word-level)"),
    ("diarization", "Tách người nói"),
    ("scenes", "Dò chuyển cảnh"),
    ("audio", "Phân tích nhạc/beat"),
    ("faces", "Bám khuôn mặt"),
]


def _set(video_id: int, kind: str, status: str, data=None, engine="", error=""):
    db.execute(
        """INSERT INTO analysis (video_id, kind, status, data, engine, error, updated_at)
           VALUES (?,?,?,?,?,?,datetime('now'))
           ON CONFLICT(video_id, kind) DO UPDATE SET
             status=excluded.status, data=excluded.data, engine=excluded.engine,
             error=excluded.error, updated_at=datetime('now')""",
        (video_id, kind, status, db.dumps(data) if data is not None else None,
         engine, error),
    )


def get_analysis(video_id: int, kind: str):
    """Đọc lại kết quả phân tích đã cache (dict) hoặc None nếu chưa có/chưa xong."""
    row = db.query_one(
        "SELECT status, data FROM analysis WHERE video_id=? AND kind=?",
        (video_id, kind),
    )
    if not row or row["status"] != "done":
        return None
    return db.loads(row["data"])


def analysis_status(video_id: int) -> dict:
    """Trả {kind: status} cho UI hiển thị tiến độ lõi phân tích."""
    rows = db.query("SELECT kind, status FROM analysis WHERE video_id=?", (video_id,))
    return {r["kind"]: r["status"] for r in rows}


def _project_audio_path(video_id: int) -> Path:
    row = db.query_one(
        """SELECT p.assets_dir FROM videos v
           JOIN projects p ON p.id=v.project_id WHERE v.id=?""",
        (video_id,),
    )
    base = Path(row["assets_dir"]) if row else (PROJECTS_DIR / "tmp")
    base = base / "_cache"          # file audio tạm -> _cache, không lẫn folder người dùng
    base.mkdir(parents=True, exist_ok=True)
    return base / f"audio_{video_id}.wav"


def run_analysis(
    video_id: int,
    profile: dict,
    on_progress: ProgressFn = None,
    force: bool = False,
) -> dict:
    """
    Chạy toàn bộ lõi phân tích cho 1 video.
    `profile`: cấu hình từ resource_manager (whisper_model, device, compute_type...).
    Smart-skip: kind đã 'done' thì bỏ qua (trừ khi force=True).
    Trả về {kind: status}.
    """
    row = db.query_one("SELECT src_path FROM videos WHERE id=?", (video_id,))
    if not row:
        raise ValueError(f"Không tìm thấy video id={video_id}")
    src = row["src_path"]

    existing = analysis_status(video_id)

    # CHẾ ĐỘ MÁY YẾU: chỉ chép lời (mây); bỏ dò cảnh/âm thanh/khuôn mặt (ngốn CPU).
    from config import settings as _st
    steps = STEPS
    if getattr(_st, "LIGHT_MODE", True):
        steps = [s for s in STEPS if s[0] == "transcript"]
        for k, _lbl in STEPS:                    # đánh dấu bước nặng = bỏ qua
            if k != "transcript" and existing.get(k) != "done":
                _set(video_id, k, "skipped")

    n = len(steps)
    for i, (kind, label) in enumerate(steps):
        base, span = i / n, 1 / n
        if not force and existing.get(kind) == "done":
            if on_progress:
                on_progress(base + span, f"{label}: đã có (bỏ qua)")
            continue

        _set(video_id, kind, "running")
        # BƯỚC nào / trên TỔNG mấy bước — user thấy rõ "Phân tích 1/5" ở đầu
        # message (khu tiến trình lớn hiện nguyên câu này).
        _pfx = f"Phân tích {i + 1}/{n} · {label} — "

        def _step_fn(base=base, span=span, pfx=_pfx):
            def fn(p: float, msg: str):
                if on_progress:
                    on_progress(base + span * p, f"{pfx}{msg}" if msg else pfx)
            return fn

        try:
            data, engine = _run_one(video_id, kind, src, profile, _step_fn())
            if data is None:  # bỏ qua êm (vd diarization không cấu hình)
                _set(video_id, kind, "skipped")
            else:
                _set(video_id, kind, "done", data=data, engine=engine)
        except Exception as e:  # noqa: BLE001 - ghi lỗi, không làm sập cả pipeline
            _set(video_id, kind, "failed", error=str(e))
            if on_progress:
                on_progress(base + span, f"{label}: lỗi ({e})")
        finally:
            if kind == "transcript":
                # Trả RAM model whisper NGAY khi chép lời xong: các pha sau
                # (scenes/faces) không cần model, để nó nằm chờ tốn 0.5-3GB.
                transcribe.release_models()

    # Dọn file audio tạm: kết quả đã cache trong DB, không cần giữ .wav (~8MB/video).
    # Nếu sau này phân tích lại, ensure_audio() sẽ tự tách lại.
    try:
        wav = _project_audio_path(video_id)
        if wav.exists():
            wav.unlink()
    except OSError:
        pass

    return analysis_status(video_id)


def _run_one(video_id: int, kind: str, src: str, profile: dict, prog: ProgressFn):
    """Chạy 1 kind, trả (data, engine). data=None nghĩa là skip êm."""
    # Audio dùng chung cho transcript/diarization/audio — tách 1 lần.
    def ensure_audio() -> str:
        wav = _project_audio_path(video_id)
        if not wav.exists():
            from app.core import ffmpeg_utils as _fu
            from app.core.ffmpeg_utils import extract_audio_wav_why
            # ĐANG ĐỢI LƯỢT THÌ PHẢI NÓI: tách audio đi qua CỬA CHỜ ffmpeg
            # (3 chỗ trên máy 24 nhân) nên có lúc đứng im vài phút. Gắn hàm báo
            # theo THREAD; gỡ trong finally kẻo thread worker dùng lại báo nhầm.
            _fu.dat_bao_cho(lambda m: prog(0.02, m) if prog else None)
            try:
                ok, why = extract_audio_wav_why(src, wav)
            finally:
                _fu.dat_bao_cho(None)
            if not ok:
                # NÓI ĐÚNG NGUYÊN NHÂN, đừng đổ cho ffmpeg. Thường gặp nhất là
                # video gốc đã bị chuyển vào `_Loi` sau lần cắt lỗi trước, nên
                # bấm "Cắt lại" là tìm ở đường dẫn cũ → không thấy file.
                if "KHÔNG TÌM THẤY" in why:
                    raise RuntimeError(
                        f"{why}\n\nVideo gốc có thể đã bị chuyển vào thư mục "
                        "_Loi (sau lần cắt lỗi trước) hoặc vào Thùng rác. "
                        "Chuyển video về lại thư mục kênh rồi bấm Cắt lại.")
                raise RuntimeError(f"Tách audio thất bại: {why}")
        return str(wav)

    if kind == "transcript":
        if not transcribe.provider_ready():
            # KHÔNG skip êm: thiếu transcript thì AI không chọn được đoạn hay,
            # job vẫn báo "Hoàn tất" nhưng clip cắt mò -> khách tưởng app dở.
            raise RuntimeError(
                "Chưa có cách chép lời — vào 'Cài đặt AI' dán key Groq "
                "(miễn phí, console.groq.com/keys) rồi bấm Tạo clip lại. "
                "(Hoặc cài faster-whisper nếu muốn chạy trên máy.)")
        wav = ensure_audio()
        model = profile.get("whisper_model", "small")
        data = transcribe.transcribe(
            wav, model_name=model,
            device=profile.get("device", "cpu"),
            compute_type=profile.get("compute_type", "int8"),
            on_progress=prog,
        )
        # GHI ĐÚNG NƠI ĐÃ CHÉP LỜI. Trước đây dòng này đóng cứng
        # `f"faster-whisper:{model}"` cho MỌI lượt — kể cả lượt đi Groq (mây).
        # Đó là lời nói dối tai hại: `transcribe()` **tự lùi về whisper MÁY khi
        # Groq lỗi, KHÔNG báo một dòng nào** (CLAUDE.md cổng 22, "chậm hơn hàng
        # chục lần"), và cột `analysis.engine` là chỗ DUY NHẤT nhìn ra được
        # chuyện đó. Cột nói sai thì lời khuyên "nghi dây chuyền chậm thì kiểm
        # key TRƯỚC" không làm được. Đo thật 08/08/2026: cả 7 video của lượt
        # tổng rà soát ghi 'faster-whisper:large-v3' trong khi THỰC TẾ chép
        # bằng Groq — suýt kết luận sai là "app đang tụt về whisper máy".
        return data, (data.get("engine") or f"faster-whisper:{model}")

    if kind == "diarization":
        if not diarization.is_available():
            return None, ""  # skip êm nếu thiếu token/lib
        wav = ensure_audio()
        return diarization.diarize(wav, on_progress=prog), "pyannote-3.1"

    if kind == "scenes":
        if not scene_detect.is_available():
            return None, ""
        return scene_detect.detect_scenes(src, on_progress=prog), "pyscenedetect"

    if kind == "audio":
        if not audio_analysis.is_available():
            return None, ""
        wav = ensure_audio()
        return audio_analysis.analyze_audio(wav, on_progress=prog), "librosa"

    if kind == "faces":
        if not face_track.is_available():
            return None, ""
        return face_track.track_faces(src, on_progress=prog), "mediapipe"

    raise ValueError(f"kind không hợp lệ: {kind}")
