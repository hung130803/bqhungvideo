"""
Trạng thái dùng chung của UI: worker pool + project/video đang chọn.
Phát signal khi thay đổi để các page tự cập nhật.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from app.queue.resource_manager import PROFILE, profile_dict
from app.queue.worker import WorkerPool


class AppState(QObject):
    project_changed = pyqtSignal(int)   # project_id
    video_changed = pyqtSignal(int)     # video_id
    data_changed = pyqtSignal()         # có thay đổi DB -> refresh

    def __init__(self):
        super().__init__()
        self.profile = profile_dict(PROFILE)
        from PyQt6.QtCore import QSettings
        s = QSettings("AIContentStudio", "studio")

        def _w(key, default):
            try:
                return max(1, int(s.value(key)))
            except (TypeError, ValueError):
                return default
        self.pool = WorkerPool(
            self.profile,
            max_cpu=_w("cut_workers", PROFILE.max_cpu_workers),   # luồng cắt/xuất
            max_gpu=_w("ai_workers", PROFILE.max_gpu_workers),    # luồng AI
        )
        self.project_id: int | None = None
        self.video_id: int | None = None

    def start(self):
        self.pool.start()

    def stop(self):
        self.pool.stop()

    def set_project(self, pid: int):
        self.project_id = pid
        self.video_id = None
        self.project_changed.emit(pid)

    def set_video(self, vid: int):
        self.video_id = vid
        self.video_changed.emit(vid)
