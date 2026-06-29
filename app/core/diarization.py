"""
Speaker diarization bằng pyannote.audio (TÙY CHỌN).
Cần HUGGINGFACE_TOKEN. Nếu không có token / chưa cài -> bỏ qua êm,
analysis sẽ đánh dấu kind='diarization' là 'skipped'.
"""
from __future__ import annotations

from typing import Callable, Optional

from config import settings


def is_available() -> bool:
    try:
        import pyannote.audio  # noqa: F401
        return bool(settings.HUGGINGFACE_TOKEN)
    except ImportError:
        return False


def diarize(
    audio_path: str,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    Trả về:
      {"turns": [{"start","end","speaker"}], "num_speakers": int}
    """
    if not is_available():
        raise RuntimeError(
            "Diarization chưa sẵn sàng (thiếu pyannote.audio hoặc HUGGINGFACE_TOKEN)."
        )

    from pyannote.audio import Pipeline

    if on_progress:
        on_progress(0.1, "Đang nạp model tách người nói...")

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=settings.HUGGINGFACE_TOKEN,
    )

    if on_progress:
        on_progress(0.4, "Đang phân tách người nói...")

    diar = pipeline(audio_path)
    turns = []
    speakers = set()
    for turn, _, speaker in diar.itertracks(yield_label=True):
        turns.append({"start": round(turn.start, 3), "end": round(turn.end, 3),
                      "speaker": str(speaker)})
        speakers.add(str(speaker))

    if on_progress:
        on_progress(1.0, f"{len(speakers)} người nói")

    return {"turns": turns, "num_speakers": len(speakers)}
