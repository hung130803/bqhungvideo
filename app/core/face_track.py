"""
Theo vết khuôn mặt theo frame bằng mediapipe -> vị trí chủ thể.
Dùng cho: face-track crop (M1) VÀ auto-reframe đa tỷ lệ (M7).

Lấy mẫu mỗi N frame để nhanh; giữa các mẫu nội suy khi crop.
Output cx/cy chuẩn hoá 0..1 theo bề rộng/cao khung.
"""
from __future__ import annotations

from typing import Callable, Optional


def is_available() -> bool:
    try:
        import mediapipe  # noqa: F401
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


def track_faces(
    video_path: str,
    sample_fps: float = 4.0,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    Trả về:
      {
        "sample_fps": 4.0,
        "frames": [{"t": giây, "cx": 0..1, "cy": 0..1, "found": bool}],
      }
    cx/cy = tâm khuôn mặt lớn nhất (người nói chính, xấp xỉ).
    found=False => không thấy mặt ở mẫu đó (giữ tâm trước đó khi crop).
    """
    if not is_available():
        raise RuntimeError(
            "Chưa cài mediapipe/opencv. Chạy: pip install mediapipe opencv-python"
        )

    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được video: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, int(round(src_fps / sample_fps)))

    mp_fd = mp.solutions.face_detection
    frames: list[dict] = []
    last_cx, last_cy = 0.5, 0.4

    with mp_fd.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
        idx = 0
        while True:
            ok = cap.grab()
            if not ok:
                break
            if idx % step == 0:
                ok, frame = cap.retrieve()
                if not ok:
                    break
                t = idx / src_fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = fd.process(rgb)
                if res.detections:
                    # chọn mặt có bbox lớn nhất
                    best = max(
                        res.detections,
                        key=lambda d: d.location_data.relative_bounding_box.width
                        * d.location_data.relative_bounding_box.height,
                    )
                    bb = best.location_data.relative_bounding_box
                    cx = min(1.0, max(0.0, bb.xmin + bb.width / 2))
                    cy = min(1.0, max(0.0, bb.ymin + bb.height / 2))
                    last_cx, last_cy = cx, cy
                    frames.append({"t": round(t, 3), "cx": round(cx, 4),
                                   "cy": round(cy, 4), "found": True})
                else:
                    frames.append({"t": round(t, 3), "cx": round(last_cx, 4),
                                   "cy": round(last_cy, 4), "found": False})
                if on_progress and total_frames:
                    on_progress(min(1.0, idx / total_frames), "Đang bám mặt...")
            idx += 1

    cap.release()
    return {"sample_fps": sample_fps, "frames": frames}


def crop_keyframes_for_range(faces: dict, start: float, end: float) -> list[dict]:
    """
    Lọc các mẫu face-track trong [start,end] và đổi sang thời gian TƯƠNG ĐỐI
    (so với start) để dùng cho export_vertical_clip.
    """
    out = []
    for f in (faces or {}).get("frames", []):
        if start <= f["t"] <= end and f.get("found", True):
            out.append({"t": round(f["t"] - start, 3), "cx": f["cx"], "cy": f["cy"]})
    return out
