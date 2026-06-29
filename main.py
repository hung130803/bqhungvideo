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
    from PyQt6.QtWidgets import QApplication

    # Nạp DB + đăng ký toàn bộ job handler (analyze, m1_*)
    import app.queue.jobs  # noqa: F401  (side-effect: register_handler)
    from app.ui.main_window import MainWindow
    from app.ui.state import AppState

    qapp = QApplication(sys.argv)
    qapp.setApplicationName("BQ Hung Video")

    from app.ui.theme import apply_theme
    apply_theme(qapp)

    state = AppState()

    # ---- BẮT BUỘC ĐĂNG NHẬP trước khi vào app ----
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
