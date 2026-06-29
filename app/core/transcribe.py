"""
Transcribe word-level bằng faster-whisper (local, free).
Trả về danh sách segment + danh sách từ kèm timestamp.

Lib nặng được import lười (lazy) để app khởi động được dù chưa cài.
"""
from __future__ import annotations

from typing import Callable, Optional

from config import settings

_model_cache: dict = {}  # (model_name, device, compute) -> WhisperModel
_cuda_libs_done = False


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_cuda_libs() -> bool:
    """Đưa cuDNN/cuBLAS (cài qua pip nvidia-*) vào đường tìm DLL để whisper chạy
    GPU. Trả True nếu thấy thư viện. Gọi trước khi nạp model cuda."""
    global _cuda_libs_done
    if _cuda_libs_done:
        return True
    import os
    try:
        import nvidia
        import pathlib
        nv = pathlib.Path(list(nvidia.__path__)[0])
        dirs = [str(nv / s) for s in ("cublas/bin", "cudnn/bin", "cuda_nvrtc/bin")
                if (nv / s).is_dir()]
        if not dirs:
            return False
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ["PATH"]
        for d in dirs:
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
        _cuda_libs_done = True
        return True
    except Exception:  # noqa: BLE001
        return False


def _get_model(model_name: str, device: str, compute_type: str):
    key = (model_name, device, compute_type)
    if key not in _model_cache:
        from faster_whisper import WhisperModel
        from config import MODELS_DIR
        if device == "cuda":
            _ensure_cuda_libs()
        try:
            _model_cache[key] = WhisperModel(
                model_name, device=device, compute_type=compute_type,
                download_root=str(MODELS_DIR),
            )
        except Exception:  # noqa: BLE001 - GPU lỗi/thiếu cuDNN -> lùi CPU cho chạy được
            if device == "cuda":
                _model_cache[key] = WhisperModel(
                    model_name, device="cpu", compute_type="int8",
                    download_root=str(MODELS_DIR),
                )
            else:
                raise
    return _model_cache[key]


def _stable_available() -> bool:
    try:
        import stable_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _get_stable_model(model_name: str, device: str, compute_type: str):
    key = ("stable", model_name, device, compute_type)
    if key not in _model_cache:
        import stable_whisper
        from config import MODELS_DIR
        if device == "cuda":
            _ensure_cuda_libs()
        try:
            _model_cache[key] = stable_whisper.load_faster_whisper(
                model_name, device=device, compute_type=compute_type,
                download_root=str(MODELS_DIR))
        except Exception:  # noqa: BLE001 - GPU lỗi -> lùi CPU
            if device == "cuda":
                _model_cache[key] = stable_whisper.load_faster_whisper(
                    model_name, device="cpu", compute_type="int8",
                    download_root=str(MODELS_DIR))
            else:
                raise
    return _model_cache[key]


def _transcribe_stable(audio_path, model_name, device, compute_type, language,
                       on_progress) -> dict:
    """Dùng stable-ts: căn mốc TỪNG TỪ chính xác hơn (snap theo khoảng lặng)."""
    if on_progress:
        on_progress(0.1, "Đang chép lời (căn chuẩn)...")
    model = _get_stable_model(model_name, device, compute_type)
    # (Đã GỠ vad=True: torch CPU + tải model silero làm TREO bước chép lời.)
    r = model.transcribe(audio_path, language=language, word_timestamps=True,
                         verbose=False)
    segments, words, full = [], [], []
    for seg in r.segments:
        segments.append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                         "text": (seg.text or "").strip()})
        full.append((seg.text or "").strip())
        for w in (seg.words or []):
            words.append({"start": round(w.start, 3), "end": round(w.end, 3),
                          "word": (w.word or "").strip()})
    if on_progress:
        on_progress(1.0, "Chép lời xong")
    total = segments[-1]["end"] if segments else 0.0
    return {
        "language": getattr(r, "language", None) or language or "",
        "duration": total, "segments": segments, "words": words,
        "text": " ".join(full).strip(),
    }


def _g(o, k, d=0):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _transcribe_groq(audio_path: str, language, on_progress) -> dict:
    """Nghe-chép qua GROQ (mây, FREE, rất nhanh) — máy yếu không cần GPU vẫn nhanh.
    Xoay vòng nhiều key. Lỗi -> ném để transcribe() lùi về Local."""
    from openai import OpenAI
    keys = settings.groq_keys()
    if not keys:
        raise RuntimeError("Chưa có GROQ key.")
    last = ""
    for key in keys:
        try:
            if on_progress:
                on_progress(0.2, "Đang chép lời (Groq mây)...")
            client = OpenAI(api_key=key,
                            base_url="https://api.groq.com/openai/v1")
            with open(audio_path, "rb") as f:
                r = client.audio.transcriptions.create(
                    file=f, model=settings.GROQ_WHISPER_MODEL,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"],
                    language=language or None)
            segs, words, full = [], [], []
            for s in (_g(r, "segments", None) or []):
                tx = (_g(s, "text", "") or "").strip()
                segs.append({"start": round(float(_g(s, "start", 0)), 3),
                             "end": round(float(_g(s, "end", 0)), 3), "text": tx})
                full.append(tx)
            for w in (_g(r, "words", None) or []):
                words.append({"start": round(float(_g(w, "start", 0)), 3),
                              "end": round(float(_g(w, "end", 0)), 3),
                              "word": (_g(w, "word", "") or "").strip()})
            if on_progress:
                on_progress(1.0, "Chép lời xong (Groq)")
            return {"language": _g(r, "language", None) or language or "",
                    "duration": segs[-1]["end"] if segs else 0.0,
                    "segments": segs, "words": words,
                    "text": (_g(r, "text", "") or " ".join(full)).strip()}
        except Exception as e:  # noqa: BLE001
            last = str(e).lower()
            if any(s in last for s in ("429", "rate", "quota", "limit")):
                continue                       # key hết lượt -> xoay key kế
            raise
    raise RuntimeError(f"Groq whisper lỗi (hết key/quota): {last}")


def transcribe(
    audio_path: str,
    model_name: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    language: Optional[str] = None,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    Trả về:
      {
        "language": "vi",
        "duration": 123.4,
        "segments": [{"start","end","text"}],
        "words": [{"start","end","word"}],
        "text": "toàn bộ"
      }
    Ưu tiên stable-ts (căn từ chuẩn hơn); lỗi -> lùi faster-whisper.
    """
    if not is_available():
        raise RuntimeError(
            "Chưa cài faster-whisper. Chạy: pip install faster-whisper"
        )

    language = language or settings.WHISPER_LANGUAGE
    # GROQ (mây): nếu chọn provider=groq + có key -> chép trên mây (máy yếu vẫn nhanh)
    if settings.WHISPER_PROVIDER == "groq" and settings.groq_keys():
        try:
            return _transcribe_groq(audio_path, language, on_progress)
        except Exception:  # noqa: BLE001 - Groq lỗi -> lùi Local cho chắc
            pass
    if _stable_available():
        try:
            return _transcribe_stable(audio_path, model_name, device,
                                      compute_type, language, on_progress)
        except Exception:  # noqa: BLE001 - stable-ts lỗi -> dùng faster-whisper thường
            pass
    model = _get_model(model_name, device, compute_type)

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,  # bỏ qua khoảng lặng -> nhanh + chính xác hơn
    )

    total = float(getattr(info, "duration", 0) or 0)
    segments: list[dict] = []
    words: list[dict] = []
    full_text: list[str] = []

    for seg in segments_iter:
        segments.append(
            {"start": round(seg.start, 3), "end": round(seg.end, 3),
             "text": seg.text.strip()}
        )
        full_text.append(seg.text.strip())
        for w in (seg.words or []):
            words.append(
                {"start": round(w.start, 3), "end": round(w.end, 3),
                 "word": w.word.strip()}
            )
        if on_progress and total:
            on_progress(min(1.0, seg.end / total), "Đang chép lời...")

    return {
        "language": getattr(info, "language", language) or "",
        "duration": total,
        "segments": segments,
        "words": words,
        "text": " ".join(full_text).strip(),
    }
