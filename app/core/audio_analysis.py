"""
Phân tích audio bằng librosa: beat, audio peak (đoạn năng lượng cao),
và khoảng lặng. Dùng cho: cắt highlight (M1) + beat sync (M2) +
filler/silence removal.
"""
from __future__ import annotations

from typing import Callable, Optional


def is_available() -> bool:
    try:
        import librosa  # noqa: F401
        return True
    except ImportError:
        return False


def analyze_audio(
    audio_path: str,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    Trả về:
      {
        "tempo": float (BPM),
        "beats": [giây,...],
        "peaks": [{"t": giây, "energy": 0..1}],   # các đỉnh năng lượng
        "rms_envelope": {"hop_sec": float, "values": [0..1,...]},
        "silences": [{"start","end"}]              # khoảng lặng dài
      }
    """
    if not is_available():
        raise RuntimeError("Chưa cài librosa. Chạy: pip install librosa")

    import numpy as np
    import librosa

    if on_progress:
        on_progress(0.1, "Đang nạp audio...")

    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    if len(y) == 0:
        return {"tempo": 0, "beats": [], "peaks": [],
                "rms_envelope": {"hop_sec": 0, "values": []}, "silences": []}

    hop = 512
    hop_sec = hop / sr

    # ---- Beat ----
    if on_progress:
        on_progress(0.4, "Đang dò beat...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    beats = [round(float(t), 3)
             for t in librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)]

    # ---- RMS energy envelope ----
    if on_progress:
        on_progress(0.7, "Đang đo năng lượng...")
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms_norm = rms / (rms.max() + 1e-9)

    # ---- Peaks: đỉnh cục bộ của RMS ----
    peaks = []
    try:
        peak_idx = librosa.util.peak_pick(
            rms_norm, pre_max=20, post_max=20, pre_avg=40, post_avg=40,
            delta=0.15, wait=int(1.0 / hop_sec),
        )
        for i in peak_idx:
            peaks.append({"t": round(float(i * hop_sec), 3),
                          "energy": round(float(rms_norm[i]), 3)})
    except Exception:
        peaks = []

    # ---- Silences: vùng RMS dưới ngưỡng kéo dài >= 0.4s ----
    silences = []
    thr = 0.06
    quiet = rms_norm < thr
    min_len = int(0.4 / hop_sec)
    run_start = None
    for i, q in enumerate(quiet):
        if q and run_start is None:
            run_start = i
        elif not q and run_start is not None:
            if i - run_start >= min_len:
                silences.append({"start": round(run_start * hop_sec, 3),
                                 "end": round(i * hop_sec, 3)})
            run_start = None
    if run_start is not None and len(quiet) - run_start >= min_len:
        silences.append({"start": round(run_start * hop_sec, 3),
                         "end": round(len(quiet) * hop_sec, 3)})

    if on_progress:
        on_progress(1.0, f"Tempo {float(tempo):.0f} BPM, {len(peaks)} đỉnh")

    # Lấy mẫu envelope thưa lại để JSON nhẹ (mỗi ~0.1s)
    step = max(1, int(0.1 / hop_sec))
    env_vals = [round(float(v), 3) for v in rms_norm[::step]]

    return {
        "tempo": round(float(tempo), 2),
        "beats": beats,
        "peaks": peaks,
        "rms_envelope": {"hop_sec": round(hop_sec * step, 4), "values": env_vals},
        "silences": silences,
    }
