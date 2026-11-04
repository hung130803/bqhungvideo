"""
Trạng thái dùng chung của UI: worker pool + project/video đang chọn.
Phát signal khi thay đổi để các page tự cập nhật.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from app.queue.resource_manager import PROFILE, profile_dict
from app.ui.appsettings import app_settings
from app.queue.worker import WorkerPool


class AppState(QObject):
    project_changed = pyqtSignal(int)   # project_id
    video_changed = pyqtSignal(int)     # video_id
    data_changed = pyqtSignal()         # có thay đổi DB -> refresh

    def __init__(self):
        super().__init__()
        self.profile = profile_dict(PROFILE)
        from PyQt6.QtCore import QSettings
        s = app_settings()

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
        # TĂNG mỗi lần bấm "Hủy tất cả": lượt dựng lệnh xuất Part đã XẾP HÀNG
        # trước lúc hủy sẽ bỏ, không tạo job mới sau khi user đã hủy.
        self.huy_gen: int = 0
        # phiên đăng nhập (gán sau khi qua màn Login)
        self.user: str | None = None
        self.role: str | None = None
        self.admin_pass: str | None = None    # để admin gọi RPC quản lý tài khoản

    def start(self):
        self.pool.start()
        # Bot Telegram quản lý dây chuyền: không có token trong .env thì không
        # làm gì; có lỗi gì cũng KHÔNG được làm app mở hỏng.
        try:
            from app.core import tele_bot
            tele_bot.khoi_dong(self.pool)
            # bot GÁC CỔNG: tiến trình nền riêng, sống tiếp khi app tắt ->
            # điện thoại gõ /moapp vẫn mở lại được app (xem tele_gac)
            from app.core import tele_gac
            tele_gac.bat_neu_chua(log=tele_bot._ghi_log)
        except Exception as e:  # noqa: BLE001
            # nuốt im lặng là không ai biết vì sao bot không lên -> ghi log
            try:
                from datetime import datetime
                from config import LOGS_DIR
                with open(LOGS_DIR / f"telegram_{datetime.now():%Y%m%d}.log", "a",
                          encoding="utf-8") as f:
                    f.write(f"[{datetime.now():%H:%M:%S}] bot KHÔNG khởi động: {e!r}\n")
            except Exception:  # noqa: BLE001
                pass

    def stop(self):
        try:
            from app.core import tele_bot
            tele_bot.tat()
        except Exception:  # noqa: BLE001
            pass
        self.pool.stop()

    def set_project(self, pid: int):
        self.project_id = pid
        self.video_id = None
        self.project_changed.emit(pid)

    def set_video(self, vid: int):
        self.video_id = vid
        self.video_changed.emit(vid)
