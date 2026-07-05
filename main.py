"""
AI Content Studio — điểm khởi động.

Chạy:  python main.py
"""
from __future__ import annotations

import sys

# Console Windows mặc định cp1252 -> ép UTF-8 (log/print không lỗi tiếng Việt)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def main() -> int:
    # ---- Chế độ TIẾN TRÌNH CON PHÂN TÍCH (bản .exe không chạy được -m module) ----
    if len(sys.argv) >= 3 and sys.argv[1] == "--analyze":
        import app.core.analysis_runner as ar
        sys.argv = [sys.argv[0]] + sys.argv[2:]   # -> [exe, video_id, force?]
        return ar.main()

    # Trình phát xem trước dùng backend FFMPEG (Qt6 kèm sẵn): backend Windows
    # mặc định không giải mã VP9/AV1 (video yt-dlp hay tải về) -> MÀN ĐEN.
    os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")
    from PyQt6.QtWidgets import QApplication

    # Nạp DB + đăng ký toàn bộ job handler (analyze, m1_*)
    import app.queue.jobs  # noqa: F401  (side-effect: register_handler)
    from app.ui.main_window import MainWindow
    from app.ui.state import AppState

    qapp = QApplication(sys.argv)
    qapp.setApplicationName("BQ Hung Video")

    # ---- CHỐNG MỞ 2 APP: 2 instance cùng đọc/ghi studio.db sẽ tranh job
    # (1 job chạy 2 lần, gọi AI đôi, clip ghi đè lẫn nhau). ----
    from PyQt6.QtCore import QLockFile
    from config import DATA_DIR
    lock = QLockFile(str(DATA_DIR / "app.lock"))
    # (Qt tự kiểm tra PID trong lock: app crash -> lock tự phá, không khoá chết)
    if not lock.tryLock(100):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            None, "BQ Hung Video",
            "App đang mở rồi (kiểm tra thanh taskbar).\n"
            "Không thể chạy 2 cửa sổ cùng lúc.")
        return 0
    qapp._single_lock = lock          # giữ tham chiếu tới khi thoát

    from app.ui.theme import apply_theme
    apply_theme(qapp)

    state = AppState()

    # ---- ĐĂNG NHẬP: chỉ bắt buộc KHI đã cấu hình máy chủ tài khoản (Supabase).
    # Bản phát hành cho team sẽ nướng sẵn cấu hình -> luôn bắt đăng nhập.
    # Chưa cấu hình -> mở thẳng (tránh khoá chết khi đang cài đặt/test). ----
    from app.auth_config import is_configured
    if is_configured():
        from PyQt6.QtWidgets import QDialog
        from app.ui.login import LoginDialog
        login = LoginDialog()
        if login.exec() != QDialog.DialogCode.Accepted:
            return 0                       # huỷ/đóng -> thoát app
        state.user = login.user
        state.role = login.role
        state.admin_pass = login.password

    win = MainWindow(state)
    win.show()

    # Khởi động worker pool SAU khi cửa sổ đã hiện (tránh giành tài nguyên lúc
    # mở app làm cửa sổ lâu hiện). Model sẽ tự nạp khi bấm "Tạo clip".
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(800, state.start)

    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
