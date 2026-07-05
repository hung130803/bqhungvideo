"""Hộp thoại CẬP NHẬT PHIÊN BẢN — tự tải + tự cài, không bắt người dùng mở web.

Luồng người dùng:
  "Có bản mới vX.Y.Z" [ghi chú phát hành]
  [Cập nhật ngay]  -> thanh tiến trình tải -> "Sẵn sàng" -> app tự đóng,
                      script nền thay file, app TỰ MỞ LẠI bản mới.
  [Để sau]         -> đóng, không phiền.

Bản dev (chạy từ mã nguồn) hoặc Release không có file zip -> nút chuyển thành
"Mở trang tải" (fallback như cũ).
"""
from __future__ import annotations

import threading
import webbrowser

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from app.version import __version__


class UpdateDialog(QDialog):
    _prog = pyqtSignal(int, int)          # (đã tải, tổng) bytes
    _done = pyqtSignal(str)               # "" = ok, khác rỗng = thông điệp lỗi

    def __init__(self, info: dict, parent=None):
        """info: dict từ updater.check_latest() — tag/page/asset_url/notes."""
        super().__init__(parent)
        self.info = info
        self._canceled = False
        self._downloading = False
        self.setWindowTitle("Cập nhật phiên bản")
        self.setMinimumWidth(440)

        from app.core.self_update import can_auto_update
        self.auto_ok = bool(can_auto_update() and info.get("asset_url"))

        v = QVBoxLayout(self)
        v.setSpacing(10)
        head = QLabel(f"<b>Đã có phiên bản mới {info['tag']}</b>"
                      f"  (bạn đang dùng v{__version__})")
        head.setWordWrap(True)
        v.addWidget(head)

        notes = (info.get("notes") or "").strip()
        if notes:
            if len(notes) > 800:
                notes = notes[:800] + "…"
            nl = QLabel(notes)
            nl.setWordWrap(True)
            nl.setStyleSheet("font-size:12px;")
            nl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            v.addWidget(nl)

        self.status = QLabel(
            "Bấm «Cập nhật ngay»: app tự tải bản mới, tự cài rồi mở lại — "
            "không phải làm gì thêm." if self.auto_ok else
            "Bản này không hỗ trợ tự cập nhật — bấm nút để mở trang tải.")
        self.status.setWordWrap(True)
        v.addWidget(self.status)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.hide()
        v.addWidget(self.bar)

        row = QHBoxLayout()
        row.addStretch(1)
        self.later = QPushButton("Để sau")
        self.later.clicked.connect(self.reject)
        row.addWidget(self.later)
        self.go = QPushButton("Cập nhật ngay" if self.auto_ok else "Mở trang tải")
        self.go.setDefault(True)
        self.go.clicked.connect(self._on_go)
        row.addWidget(self.go)
        v.addLayout(row)

        self._prog.connect(self._on_progress)
        self._done.connect(self._on_done)

    # ---- hành động ----
    def _on_go(self):
        if not self.auto_ok:
            webbrowser.open(self.info.get("page") or "")
            self.accept()
            return
        self._downloading = True
        self.go.setEnabled(False)
        self.later.setText("Hủy")
        self.bar.show()
        self.status.setText("Đang tải bản cập nhật…")
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        from app.core import self_update as su
        try:
            zip_path = su.download(
                self.info["asset_url"], self.info["tag"],
                on_progress=lambda a, b: self._prog.emit(a, b),
                is_canceled=lambda: self._canceled)
            if self._canceled:            # bấm Hủy đúng lúc vừa tải xong
                raise su.UpdateCanceled()
            new_dir = su.extract(zip_path)
            if self._canceled:
                raise su.UpdateCanceled()
            su.launch_swap_script(new_dir, zip_path)
            self._done.emit("")
        except su.UpdateCanceled:
            self._done.emit("__canceled__")
        except Exception as e:  # noqa: BLE001
            self._done.emit(str(e) or "Lỗi không rõ")

    def _on_progress(self, got: int, total: int):
        if total > 0:
            self.bar.setRange(0, 100)
            self.bar.setValue(min(100, int(got * 100 / total)))
            self.status.setText(
                f"Đang tải bản cập nhật… {got / (1 << 20):.0f}"
                f"/{total / (1 << 20):.0f} MB")
        else:
            self.bar.setRange(0, 0)   # không rõ tổng -> chạy vô định
            self.status.setText(f"Đang tải bản cập nhật… {got / (1 << 20):.0f} MB")

    def _on_done(self, err: str):
        self._downloading = False
        if err == "__canceled__":
            self.reject()
            return
        if err:
            self.bar.hide()
            self.go.setEnabled(True)
            self.later.setText("Để sau")
            self.status.setText(
                f"⚠ Tải bản cập nhật lỗi: {err}\n"
                "Thử lại, hoặc bấm «Mở trang tải» để tải tay.")
            self.go.setText("Mở trang tải")
            self.auto_ok = False
            return
        # Tải + chuẩn bị xong -> đóng app để script nền thay file rồi tự mở lại
        self.bar.setValue(100)
        self.status.setText("✓ Đã sẵn sàng. App sẽ đóng và tự mở lại bản mới "
                            "sau vài giây…")
        self.go.setEnabled(False)
        self.later.setEnabled(False)
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        def _quit():
            # closeAllWindows -> MainWindow.closeEvent chạy (dừng worker, giết
            # ffmpeg/tiến trình con) — quit() thẳng sẽ bỏ qua bước dọn này.
            QApplication.closeAllWindows()
            QApplication.quit()
        QTimer.singleShot(1200, _quit)

    def reject(self):
        if self._downloading:
            self._canceled = True      # báo luồng tải dừng; _on_done sẽ đóng
            self.status.setText("Đang hủy…")
            return
        super().reject()
