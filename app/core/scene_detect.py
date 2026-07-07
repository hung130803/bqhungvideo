"""
Scene detection bằng PySceneDetect -> danh sách mốc chuyển cảnh.
Dùng cho: chọn điểm cắt highlight (M1) + beat sync (M2).
"""
from __future__ import annotations

from typing import Callable, Optional


def is_available() -> bool:
    try:
        import scenedetect  # noqa: F401
        return True
    except ImportError:
        return False


def detect_scenes(
    video_path: str,
    threshold: float = 27.0,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    Trả về:
      {"scenes": [{"start","end"}], "cut_points": [giây,...]}
    cut_points = mốc bắt đầu mỗi cảnh (trừ cảnh đầu).
    """
    if not is_available():
        raise RuntimeError(
            "Chưa cài PySceneDetect. Chạy: pip install scenedetect[opencv]"
        )

    from scenedetect import detect, ContentDetector

    # cv2 mặc định mở luồng = số nhân máy -> ghìm lại (PySceneDetect đã tự
    # downscale khung hình khi dò nên chỉ cần giới hạn luồng).
    try:
        import cv2
        cv2.setNumThreads(2)
    except Exception:  # noqa: BLE001
        pass

    if on_progress:
        on_progress(0.1, "Đang dò chuyển cảnh...")

    scene_list = detect(video_path, ContentDetector(threshold=threshold))

    scenes = []
    cut_points = []
    for i, (start, end) in enumerate(scene_list):
        s, e = start.get_seconds(), end.get_seconds()
        scenes.append({"start": round(s, 3), "end": round(e, 3)})
        if i > 0:
            cut_points.append(round(s, 3))

    if on_progress:
        on_progress(1.0, f"Tìm thấy {len(scenes)} cảnh")

    return {"scenes": scenes, "cut_points": cut_points}
