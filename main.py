"""
AI Content Studio — điểm khởi động.

Chạy:  python main.py
"""
from __future__ import annotations

import os
import sys

# Console Windows mặc định cp1252 -> ép UTF-8 (log/print không lỗi tiếng Việt)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def _pick_media_backend() -> None:
    """Đặt QT_MEDIA_BACKEND = backend phát media dùng được trên máy này.

    "ffmpeg" chỉ khi tìm thấy DLL FFmpeg (avcodec*.dll) đi kèm Qt — cả khi
    chạy nguồn (site-packages/PyQt6/Qt6) lẫn bản .exe (sys._MEIPASS/PyQt6/Qt6).
    Không thấy -> "windows" (Media Foundation). User tự set biến môi trường
    thì tôn trọng, không đè."""
    if os.environ.get("QT_MEDIA_BACKEND"):
        return
    import glob
    roots = []
    base = getattr(sys, "_MEIPASS", None)          # bản đóng gói PyInstaller
    if base:
        roots.append(os.path.join(base, "PyQt6", "Qt6"))
    try:
        import PyQt6
        roots.append(os.path.join(os.path.dirname(PyQt6.__file__), "Qt6"))
    except ImportError:
        pass
    for r in roots:
        for sub in ("bin", os.path.join("plugins", "multimedia"), ""):
            if glob.glob(os.path.join(r, sub, "avcodec*.dll")):
                os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"
                return
    os.environ["QT_MEDIA_BACKEND"] = "windows"


def main() -> int:
    # ---- Chế độ TIẾN TRÌNH CON PHÂN TÍCH (bản .exe không chạy được -m module) ----
    if len(sys.argv) >= 3 and sys.argv[1] == "--analyze":
        import app.core.analysis_runner as ar
        sys.argv = [sys.argv[0]] + sys.argv[2:]   # -> [exe, video_id, force?]
        return ar.main()

    # ---- Chọn backend QtMultimedia HOẠT ĐỘNG THẬT trên máy này ----
    # Qt >= 6.5 mặc định dùng backend "ffmpeg", nhưng wheel PyQt6/Windows chỉ
    # kèm ffmpegmediaplugin.dll mà THIẾU bộ DLL FFmpeg (avcodec/avformat...)
    # -> plugin nạp thất bại IM LẶNG, QMediaPlayer thành backend rỗng: không
    # phát, không lỗi, không tín hiệu (Nghe thử/Demo/Xem & sửa bấm im re).
    # => chỉ dùng "ffmpeg" khi DLL FFmpeg thật sự có; không thì ép "windows"
    # (Windows Media Foundation - luôn sẵn, phát tốt H.264/mp3/wav; nhược:
    # không giải mã VP9/AV1 nhưng app đã ưu tiên tải H.264 nên ít gặp).
    _pick_media_backend()
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

    # ---- LƯỚI CHỐNG SẬP TOÀN CỤC: PyQt6 mặc định ABORT cả app khi 1 slot
    # (nút bấm/timer) ném exception chưa bắt -> user thấy "bấm cái là app tự
    # thoát" mà không dấu vết (exe windowed nuốt stderr, WER không ghi).
    # Đặt sys.excepthook TÙY BIẾN: PyQt sẽ gọi hook này và KHÔNG abort nữa —
    # app sống tiếp, lỗi được GHI FILE logs/error.log + hiện hộp thoại cho
    # user chụp gửi dev. Luồng nền cũng ghi log (không hiện hộp thoại). ----
    import threading
    import traceback
    from datetime import datetime

    def _log_crash(text: str) -> None:
        try:
            logd = DATA_DIR / "logs"
            logd.mkdir(parents=True, exist_ok=True)
            with open(logd / "error.log", "a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
                f.write(text)
        except OSError:
            pass

    def _global_excepthook(tp, val, tb):
        text = "".join(traceback.format_exception(tp, val, tb))
        _log_crash(text)
        try:
            print(text, file=sys.__stderr__)
        except Exception:  # noqa: BLE001
            pass
        try:
            if threading.current_thread() is threading.main_thread():
                from PyQt6.QtWidgets import QMessageBox
                tail = "\n".join(text.strip().splitlines()[-6:])
                QMessageBox.warning(
                    None, "Có lỗi xảy ra (app vẫn chạy tiếp)",
                    "Thao tác vừa rồi gặp lỗi — app KHÔNG thoát, cứ dùng "
                    "tiếp.\nLỗi đã ghi vào logs/error.log (gửi dev để sửa "
                    "tận gốc).\n\n" + tail)
        except Exception:  # noqa: BLE001 - hộp thoại lỗi không được gây lỗi
            pass

    sys.excepthook = _global_excepthook

    def _thread_hook(args):
        _log_crash("".join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback)))

    threading.excepthook = _thread_hook

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
