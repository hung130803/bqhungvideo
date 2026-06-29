"""
Cửa sổ chính — MỘT màn hình (StudioPage) cho đơn giản, dễ dùng.
Banner phần cứng ở trên, dock hàng đợi (tiến trình) ở dưới.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from app.queue.resource_manager import HARDWARE, PROFILE
from app.ui.queue_panel import QueuePanel
from app.ui.state import AppState
from app.ui.studio_page import StudioPage
from app.version import __version__


class _NoWheelSpin(QSpinBox):
    """Ô số KHÔNG đổi giá trị khi chỉ lăn chuột qua (tránh lỡ tay đổi luồng)."""
    def wheelEvent(self, e):
        e.ignore()


class MainWindow(QMainWindow):
    _update_found = pyqtSignal(str, str)        # (tag mới, trang tải)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setWindowTitle(f"BQ Hung Video v{__version__}")
        self.resize(1240, 840)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(self._sidebar())            # thanh bên trái (brand + máy)
        wrap = QWidget()
        wl = QVBoxLayout(wrap); wl.setContentsMargins(16, 14, 16, 0); wl.setSpacing(0)
        self.studio = StudioPage(state)
        wl.addWidget(self.studio, 1)
        root.addWidget(wrap, 1)
        self.setCentralWidget(central)

        dock = QDockWidget("Tiến trình", self)
        dock.setWidget(QueuePanel(state))
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self.resizeDocks([dock], [190], Qt.Orientation.Vertical)

        # Tự kiểm tra bản mới (nền, im lặng nếu lỗi mạng)
        self._update_found.connect(self._notify_update)
        self._start_update_check()

    def _start_update_check(self):
        import threading

        def work():
            try:
                from app.core.updater import check_latest
                res = check_latest()
                if res:
                    self._update_found.emit(res[0], res[1])
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=work, daemon=True).start()

    def _notify_update(self, tag, page):
        import webbrowser
        if QMessageBox.question(
            self, "Có bản cập nhật mới",
            f"Đã có phiên bản mới <b>{tag}</b> (bạn đang dùng v{__version__}).\n\n"
            "Mở trang tải bản mới ngay?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        ) == QMessageBox.StandardButton.Yes:
            webbrowser.open(page)

    def _sidebar(self):
        from app.ui.theme import BASE, WINDOW, BORDER, MUTED, TEXT, ACCENT, SUCCESS, DANGER
        w = QWidget(); w.setObjectName("sidebar"); w.setFixedWidth(230)
        w.setStyleSheet(f"#sidebar{{background:{BASE}; border-right:1px solid {BORDER};}}"
                        f"#sidebar QLabel{{background:transparent;}}")
        v = QVBoxLayout(w); v.setContentsMargins(18, 22, 18, 18); v.setSpacing(6)
        # --- Thương hiệu ---
        brand = QLabel("BQ Hung")
        brand.setStyleSheet(f"color:{TEXT}; font-size:21px; font-weight:800;")
        brand2 = QLabel("VIDEO")
        brand2.setStyleSheet(f"color:{ACCENT}; font-size:21px; font-weight:800;"
                             "letter-spacing:3px;")
        tag = QLabel("Cắt clip viral tự động")
        tag.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        v.addWidget(brand); v.addWidget(brand2); v.addSpacing(2); v.addWidget(tag)
        v.addSpacing(22)

        # --- Thông tin máy (gọn, dọc) ---
        def info(label, val, col=None):
            box = QVBoxLayout(); box.setSpacing(1)
            a = QLabel(label); a.setStyleSheet(f"color:{MUTED}; font-size:11px;")
            b = QLabel(val); b.setStyleSheet(
                f"color:{col or TEXT}; font-size:13px; font-weight:600;")
            b.setWordWrap(True)
            box.addWidget(a); box.addWidget(b)
            v.addLayout(box); v.addSpacing(10)

        gpu = HARDWARE.gpu_name if HARDWARE.has_cuda else "CPU (không GPU)"
        info("Máy", f"{HARDWARE.cpu_cores} luồng · {HARDWARE.ram_gb}GB")
        info("Card đồ họa", gpu, ACCENT if HARDWARE.has_cuda else MUTED)
        info("ffmpeg", "Sẵn sàng" if HARDWARE.has_ffmpeg else "THIẾU!",
             SUCCESS if HARDWARE.has_ffmpeg else DANGER)

        # --- Luồng chạy song song ---
        hr = QLabel("CHẠY SONG SONG"); hr.setStyleSheet(
            f"color:{MUTED}; font-size:11px; font-weight:700; letter-spacing:1px;")
        v.addWidget(hr); v.addSpacing(4)

        def spin_row(label, val, slot):
            r = QHBoxLayout()
            lb = QLabel(label); lb.setStyleSheet(f"color:{TEXT}; font-size:13px;")
            r.addWidget(lb, 1)
            sp = _NoWheelSpin(); sp.setRange(1, 16); sp.setFixedWidth(58); sp.setValue(val)
            sp.valueChanged.connect(slot); r.addWidget(sp)
            v.addLayout(r); v.addSpacing(2)
            return sp

        self.sp_ai = spin_row("Luồng AI", self.state.pool.max_gpu, self._set_ai)
        self.sp_ai.setToolTip("Số video phân tích/AI song song.")
        self.sp_cut = spin_row("Luồng cắt", self.state.pool.max_cpu, self._set_cut)
        self.sp_cut.setToolTip("Số video cắt/xuất song song.")

        v.addStretch(1)

        # --- Tài khoản đang đăng nhập ---
        who = QLabel(f"Tài khoản: {self.state.user or '—'}"
                     + ("  (Admin)" if self.state.role == "admin" else ""))
        who.setStyleSheet(f"color:{MUTED}; font-size:12px;"); who.setWordWrap(True)
        v.addWidget(who)
        if self.state.role == "admin":
            admin_btn = QPushButton("Quản lý tài khoản")
            admin_btn.setToolTip("Tạo / khoá / xoá tài khoản cho team.")
            admin_btn.clicked.connect(self._open_admin)
            v.addWidget(admin_btn)
        v.addSpacing(6)

        ver = QLabel(f"v{__version__}"); ver.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        v.addWidget(ver)
        return w

    def _open_admin(self):
        from app.ui.login import AdminUsersDialog
        AdminUsersDialog(self.state.user, self.state.admin_pass, self).exec()

    def _set_ai(self, v):
        self.state.pool.set_limits(max_gpu=v)
        QSettings("AIContentStudio", "studio").setValue("ai_workers", v)

    def _set_cut(self, v):
        self.state.pool.set_limits(max_cpu=v)
        QSettings("AIContentStudio", "studio").setValue("cut_workers", v)

    def closeEvent(self, event):
        # dừng worker + GIẾT tiến trình con (ffmpeg/phân tích) để không mồ côi
        try:
            from app.core.ffmpeg_utils import terminate_all_children
            terminate_all_children()
        except Exception:  # noqa: BLE001
            pass
        self.state.stop()
        super().closeEvent(event)
