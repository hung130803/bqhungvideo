"""
Cửa sổ chính — MỘT màn hình (StudioPage) cho đơn giản, dễ dùng.
Banner phần cứng ở trên, dock hàng đợi (tiến trình) ở dưới.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDockWidget, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
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
    _update_found = pyqtSignal(object)          # dict từ updater.check_latest()

    def __init__(self, state: AppState):
        super().__init__()
        # Chặn cuộn chuột vô tình đổi giá trị combo/ô số/slider (lỗi Qt mặc
        # định). Cài ở đây để CHẮC CHẮN áp dụng dù app khởi động bằng entry
        # nào (idempotent — gọi nhiều lần không sao).
        try:
            from PyQt6.QtWidgets import QApplication
            from app.ui.wheelguard import install as _wg
            _wg(QApplication.instance())
        except Exception:  # noqa: BLE001 - chặn cuộn là phụ, lỗi thì bỏ qua
            pass
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

        # DB hỏng + không cứu được -> đang chạy tạm trong RAM. Tiến trình con
        # (phân tích) KHÔNG dùng chung được DB này -> sẽ báo "không tìm thấy
        # video". Cảnh báo user RÕ ngay thay vì để lỗi khó hiểu về sau.
        self._warn_if_db_in_memory()

    def _warn_if_db_in_memory(self):
        from app.database import db
        if getattr(db, "in_memory", False):
            QMessageBox.warning(
                self, "Ổ đĩa/CSDL đang lỗi",
                "Không mở được cơ sở dữ liệu trên ổ đĩa (file hỏng hoặc ổ lỗi), "
                "app đang chạy TẠM trong bộ nhớ.\n\n"
                "• Dữ liệu phiên này sẽ KHÔNG được lưu lại.\n"
                "• Chức năng phân tích/tạo clip có thể KHÔNG chạy được "
                "(báo 'không tìm thấy video').\n\n"
                "👉 Hãy KHỞI ĐỘNG LẠI app và kiểm tra ổ đĩa còn trống/không bị "
                "chặn bởi OneDrive hay phần mềm diệt virus.")

    def _start_update_check(self):
        import threading

        def work():
            try:
                # dọn rác của lần cập nhật trước (zip/thư mục tạm/_internal.old)
                from app.core.self_update import cleanup_leftovers
                cleanup_leftovers()
                # dọn file tạm mồ côi (>3 ngày) trong projects/*/_cache: audio/
                # dub wav 30-50MB mỗi cái sót lại khi job bị hủy/app tắt ngang
                from app.services import cleanup_stale_temp
                cleanup_stale_temp()
                from app.core.updater import check_latest
                res = check_latest()
                if res:
                    self._update_found.emit(res)
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=work, daemon=True).start()

    def _notify_update(self, info: dict):
        # Tự tải + tự cài + tự mở lại (bản dev fallback mở trang tải)
        from app.ui.update_dialog import UpdateDialog
        UpdateDialog(info, self).exec()

    def _sidebar(self):
        from app.ui.theme import BASE, WINDOW, BORDER, MUTED, TEXT, ACCENT, SUCCESS, DANGER
        w = QWidget(); w.setObjectName("sidebar"); w.setFixedWidth(230)
        w.setStyleSheet(f"#sidebar{{background:{BASE}; border-right:1px solid {BORDER};}}"
                        f"#sidebar QLabel{{background:transparent;}}")
        v = QVBoxLayout(w); v.setContentsMargins(18, 24, 18, 18); v.setSpacing(6)

        def hline():
            # đường kẻ MẢNH ngăn cách các nhóm
            ln = QWidget(); ln.setFixedHeight(1)
            ln.setStyleSheet(f"background:{BORDER};")
            return ln

        def group_lbl(text):
            # nhãn nhóm: chữ HOA nhỏ, mờ
            g = QLabel(text)
            g.setStyleSheet(f"color:{MUTED}; font-size:10px; font-weight:700;"
                            "letter-spacing:2px;")
            return g

        # --- Thương hiệu ---
        brand = QLabel("BQ Hung")
        brand.setStyleSheet(f"color:{TEXT}; font-size:21px; font-weight:800;")
        brand2 = QLabel("VIDEO")
        brand2.setStyleSheet(f"color:{ACCENT}; font-size:21px; font-weight:800;"
                             "letter-spacing:3px;")
        tag = QLabel("Cắt clip viral tự động")
        tag.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        v.addWidget(brand); v.addWidget(brand2); v.addSpacing(2); v.addWidget(tag)
        v.addSpacing(18)
        v.addWidget(hline())
        v.addSpacing(14)
        v.addWidget(group_lbl("THIẾT BỊ"))
        v.addSpacing(8)

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
        v.addSpacing(4)
        v.addWidget(hline())
        v.addSpacing(14)
        v.addWidget(group_lbl("CHẠY SONG SONG"))
        v.addSpacing(8)

        def spin_row(label, val, slot):
            r = QHBoxLayout()
            lb = QLabel(label); lb.setStyleSheet(f"color:{TEXT}; font-size:13px;")
            r.addWidget(lb, 1)
            # 58px bị CẮT SỐ trên máy scale 125/150% -> 76px (đủ số 2 chữ số + nút)
            sp = _NoWheelSpin(); sp.setRange(1, 16); sp.setFixedWidth(76); sp.setValue(val)
            sp.valueChanged.connect(slot); r.addWidget(sp)
            v.addLayout(r); v.addSpacing(2)
            return sp

        self.sp_ai = spin_row("Luồng AI", self.state.pool.max_gpu, self._set_ai)
        self.sp_ai.setToolTip("Số video phân tích/AI song song.")
        self.sp_cut = spin_row("Luồng cắt", self.state.pool.max_cpu, self._set_cut)
        self.sp_cut.setToolTip(
            "Số video cắt/xuất song song.\n"
            "⚠ Để cao quá sẽ ĐƠ MÁY khi encode bằng CPU (libx264).")

        # --- Tiết kiệm máy (mặc định BẬT) ---
        from config import settings
        v.addSpacing(6)
        self.cb_eco = QCheckBox("Tiết kiệm máy")
        self.cb_eco.setChecked(settings.ECO_MODE)
        self.cb_eco.setToolTip(
            "BẬT (khuyên dùng): app chỉ chạy 1 video xuất + 1 phân tích cùng "
            "lúc, encode dùng ít luồng CPU và luôn NHƯỜNG app khác — máy vẫn "
            "dùng bình thường (lướt web, mở app khác không giật).\n"
            "TẮT = Hiệu năng tối đa: chạy đủ số luồng ở trên, xuất nhanh hơn "
            "khi cần làm hàng loạt (vẫn chừa 2 nhân cho hệ thống).")
        self.cb_eco.toggled.connect(self._set_eco)
        v.addWidget(self.cb_eco)

        # --- Dòng trạng thái ENCODER (GPU/CPU) + cảnh báo driver cũ ---
        # Máy có RTX mà driver cũ hơn bản ffmpeg yêu cầu -> NVENC bị tắt ngầm,
        # xuất chậm bằng CPU và user không biết vì sao. Hiện rõ + cách sửa.
        try:
            from app.core.ffmpeg_utils import detect_encoder, nvenc_note
            _enc = detect_encoder()          # đã cache lúc khởi động, không chậm
            enc_lbl = QLabel("Xuất video: GPU (NVENC) ⚡" if _enc == "h264_nvenc"
                             else "Xuất video: CPU (libx264)")
            enc_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            v.addWidget(enc_lbl)
            _note = nvenc_note()
            if _enc != "h264_nvenc" and _note:
                warn = QLabel("⚠ " + _note)
                warn.setWordWrap(True)
                warn.setStyleSheet("color:#F59E0B; font-size:11px;")
                v.addWidget(warn)
        except Exception:  # noqa: BLE001 - nhãn phụ, không được cản mở app
            pass

        v.addStretch(1)

        # --- Tài khoản đang đăng nhập ---
        v.addWidget(hline())
        v.addSpacing(10)
        who = QLabel(f"Tài khoản: {self.state.user or '—'}"
                     + ("  (Admin)" if self.state.role == "admin" else ""))
        who.setStyleSheet(f"color:{MUTED}; font-size:12px;"); who.setWordWrap(True)
        v.addWidget(who)
        if self.state.role == "admin":
            admin_btn = QPushButton("Quản lý tài khoản")
            admin_btn.setToolTip("Tạo / khoá / xoá tài khoản cho team.")
            admin_btn.clicked.connect(self._open_admin)
            v.addWidget(admin_btn)
        if self.state.user:
            out = QPushButton("Đăng xuất")
            out.setToolTip("Xoá mật khẩu đã lưu + thoát để đăng nhập tài khoản khác.")
            out.clicked.connect(self._logout)
            v.addWidget(out)
        v.addSpacing(6)

        ver = QLabel(f"v{__version__}"); ver.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        v.addWidget(ver)
        return w

    def _open_admin(self):
        from app.ui.login import AdminUsersDialog
        AdminUsersDialog(self.state.user, self.state.admin_pass, self).exec()

    def _logout(self):
        if QMessageBox.question(
            self, "Đăng xuất",
            "Xoá mật khẩu đã lưu và thoát app? Lần sau mở sẽ phải đăng nhập lại."
        ) == QMessageBox.StandardButton.Yes:
            QSettings("AIContentStudio", "studio").remove("save_pass")
            # close() -> closeEvent chạy (dừng worker + giết tiến trình con);
            # quit() thẳng sẽ để ffmpeg/phân tích thành mồ côi.
            self.close()

    def _set_ai(self, v):
        self.state.pool.set_limits(max_gpu=v)
        QSettings("AIContentStudio", "studio").setValue("ai_workers", v)

    def _set_cut(self, v):
        self.state.pool.set_limits(max_cpu=v)
        QSettings("AIContentStudio", "studio").setValue("cut_workers", v)

    def _set_eco(self, on: bool):
        # Lưu .env (tiến trình con phân tích cũng đọc được) + áp NGAY vào
        # settings đang chạy — worker/_enc_args đọc settings.ECO_MODE mỗi lần.
        from config import update_env
        update_env({"ECO_MODE": "1" if on else "0"})
        self.state.pool._notify()      # đánh thức dispatcher áp giới hạn mới

    def closeEvent(self, event):
        # dừng worker + GIẾT tiến trình con (ffmpeg/phân tích) để không mồ côi
        try:
            from app.core.ffmpeg_utils import terminate_all_children
            terminate_all_children()
        except Exception:  # noqa: BLE001
            pass
        self.state.stop()
        super().closeEvent(event)
