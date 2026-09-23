"""
Cửa sổ chính: Video & clip, theo dõi hàng loạt và lối tắt cài đặt.
Studio luôn tồn tại để bộ điều phối dây chuyền tiếp tục khi đổi màn.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDockWidget, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget, QScrollArea, QStackedWidget,
)

from app.queue.resource_manager import HARDWARE, PROFILE
from app.ui.appsettings import app_settings
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
        from app.ui.layout_tools import fit_dialog
        fit_dialog(self, 1366, 850)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(self._sidebar())            # thanh bên trái (brand + máy)
        wrap = QWidget()
        wl = QVBoxLayout(wrap); wl.setContentsMargins(16, 14, 16, 0); wl.setSpacing(0)
        self.studio = StudioPage(state)
        from app.ui.batch_page import BatchPage
        self.batch = BatchPage(state)
        self.studio.open_pipeline_center.connect(self._open_pipeline_center)
        self.batch.open_video.connect(self._open_batch_video)
        self.batch.open_folder.connect(self._open_batch_folder)
        self.batch.configure_pipeline.connect(self._batch_pipeline)
        self.batch.channels.manage.connect(lambda:self._batch_manage('groups'))
        self.batch.channels.add.connect(lambda group:self._batch_manage('add',group))
        self.batch.channels.edit.connect(lambda pid:self._batch_manage('edit',pid))
        self.batch.channels.paths.connect(lambda pid:self._batch_manage('paths',pid))
        self.workspace = QStackedWidget()
        self.workspace.addWidget(self.studio)
        self.workspace.addWidget(self.batch)
        wl.addWidget(self.workspace, 1)
        root.addWidget(wrap, 1)
        self.setCentralWidget(central)

        dock = QDockWidget("Tiến trình", self)
        self.queue_dock = dock
        self.queue_panel = QueuePanel(state)
        dock.setWidget(self.queue_panel)
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self.resizeDocks([dock], [220], Qt.Orientation.Vertical)

        self._show_workspace(0)
        # Tự kiểm tra bản mới (nền, im lặng nếu lỗi mạng)
        self._update_found.connect(self._notify_update)
        self._start_update_check()

        # DB hỏng + không cứu được -> đang chạy tạm trong RAM. Tiến trình con
        # (phân tích) KHÔNG dùng chung được DB này -> sẽ báo "không tìm thấy
        # video". Cảnh báo user RÕ ngay thay vì để lỗi khó hiểu về sau.
        self._warn_if_db_in_memory()

    def _show_workspace(self, index):
        self.workspace.setCurrentIndex(index)
        self.queue_dock.setVisible(index == 0)
        if index == 0:
            self.queue_panel.timer.start(400)
            self.queue_panel.refresh()
        else:
            self.queue_panel.timer.stop()
        self.nav_video.setChecked(index == 0)
        self.nav_batch.setChecked(index == 1)

    def _open_batch_video(self, project_id, video_id):
        self.studio._select_project(project_id)
        self.studio._reload_videos(select_id=video_id)
        self._show_workspace(0)

    def _open_batch_folder(self, project_id, video_id, kind):
        try:
            from app.ui.folder_access import perform
            message=perform(self.batch,kind,project_id,video_id,self.studio._lib_root(),self.studio._pipe_root())
        except Exception as error:
            message='Không đọc được cấu hình thư mục: '+str(error)
        self.batch.feedback.setText(message)

    def _batch_manage(self, action, target=None):
        """Keep both pollers out of modal editing; resume even after an error."""
        was_active=self.batch.timer.isActive()
        self.batch.timer.stop()
        try:
            def edit():
                from PyQt6.QtWidgets import QDialog, QInputDialog
                from app import services
                if action=='groups':
                    self.studio._manage_groups()
                elif action=='edit':
                    self.studio._rename_proj(target)
                    self.batch.channels.select_project(target)
                elif action=='paths':
                    from app.ui.batch_channels import ChannelPathsDialog
                    if ChannelPathsDialog(target,self.batch).exec()==QDialog.DialogCode.Accepted:
                        self.batch.feedback.setText('Đã lưu đường dẫn. File đã xuất giữ tại vị trí cũ; lần xử lý sau dùng cấu hình mới.')
                elif action=='add':
                    name,ok=QInputDialog.getText(self.batch,'Thêm kênh',f'Tên kênh trong nhóm “{target or "Chưa phân nhóm"}”:')
                    if ok and name.strip():
                        pid=services.create_project(name.strip(),target or '')
                        self.studio._reload_projects()
                        self.batch.channels.select_project(pid)
            self.studio._busy_dialog(edit)
        except Exception as error:
            self.batch.feedback.setText('Không thực hiện được: '+str(error))
        finally:
            self.batch.refresh()
            if was_active and self.batch.isVisible():self.batch.timer.start()

    def _open_pipeline_center(self):
        pid=self.studio.proj.currentData()
        if pid:self.batch.channels.select_project(pid)
        self._show_workspace(1)

    def _batch_pipeline(self):
        group=self.batch.group.currentData()
        if group is not None:self.studio._settings.setValue('pipe_grp_sel',group)
        was_active=self.batch.timer.isActive()
        self.batch.timer.stop()
        try:
            self.studio._pipeline_dialog()
        finally:
            self.batch.refresh()
            if was_active and self.batch.isVisible():self.batch.timer.start()

    def _guide(self):
        from PyQt6.QtWidgets import QDialog, QPlainTextEdit
        dlg = QDialog(self)
        dlg.setWindowTitle("Hướng dẫn sử dụng")
        dlg.resize(740, 540)
        layout = QVBoxLayout(dlg)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "VIDEO & CLIP\n"
            "1. Chọn nhóm, kênh và video. Thêm file hoặc tải từ YouTube.\n"
            "2. Chọn mẫu và tùy chỉnh cắt. Bấm Tạo clip cho video đang chọn; "
            "Tạo nhiều để chọn nhiều video trong kênh.\n"
            "3. Duyệt clip, chỉnh điểm đầu/cuối, rồi xuất. Bật tự động xuất nếu muốn bỏ bước duyệt.\n\n"
            "DÂY CHUYỀN & LỊCH SỬ\n"
            "Chọn nhóm đã lưu và kênh ở bên trái; bảng bên phải hiển thị video của kênh. "
            "Dùng Thêm / đổi đường dẫn để chọn nơi lưu Part và nguồn Dây chuyền. "
            "Kênh còn việc chạy/chờ phải xử lý xong trước khi đổi đường dẫn. "
            "Mở Video & clip để xem kết quả. "
            "Cần xử lý và Lịch sử đã xuất được tách riêng. Hồ sơ là video từng nhập, không phải file còn trên ổ đĩa. "
            "Kiểm tra file đối chiếu đường dẫn gốc và Part; không tìm thấy chưa có nghĩa đã bị app xóa. "
            "Chọn cách xếp theo tên, thời gian nhập hoặc ưu tiên xử lý.\n"
            "Chọn kênh & chạy: quét video mới trong thư mục nguồn; chỉ chạy các kênh bật trong nhóm đang chọn. "
            "Chỉ Dây chuyền quản lý chuyển gốc vào Thùng rác sau khi xác minh đủ Part.\n\n"
            "THAY GIỌNG\n"
            "Chọn thư mục nguồn/đích, ngôn ngữ và giọng. Nghe thử trước khi chạy. "
            "Video gốc được giữ nguyên. Có thể kéo vạch chia để xem thêm bảng tiến trình.\n\n"
            "CÀI ĐẶT & XỬ LÝ LỖI\n"
            "Trong AI hoặc Chỉnh mẫu, dùng Đi tới để tìm nhanh nhóm cài đặt. "
            "Kiểm tra kết nối chỉ xác nhận các dịch vụ/key được ghi trong kết quả thử.\n"
            "Phân tích xong chưa đồng nghĩa xuất xong. Dấu ~ là tiến độ ước tính của một việc. "
            "Hủy chỉ áp cho phạm vi ghi trên nút; các việc khác vẫn tiếp tục. "
            "Khi có lỗi, đọc chi tiết trước khi thử lại; không xóa video gốc khi chưa đủ Part.")
        layout.addWidget(text, 1)
        close = QPushButton("Đóng")
        close.clicked.connect(dlg.accept)
        layout.addWidget(close)
        dlg.exec()

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
        w = QWidget(); w.setObjectName("sidebar"); w.setMinimumWidth(190)
        w.setStyleSheet(f"#sidebar{{background:{BASE}; border-right:1px solid {BORDER};}}"
                        f"#sidebar QLabel{{background:transparent;}}")
        v = QVBoxLayout(w); v.setContentsMargins(12, 16, 12, 12); v.setSpacing(6)

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
        v.addSpacing(10)
        self.nav_video = QPushButton("Video && clip")
        self.nav_batch = QPushButton("Dây chuyền")
        for button in (self.nav_video, self.nav_batch):
            button.setCheckable(True)
            button.setMinimumHeight(36)
            v.addWidget(button)
        self.nav_video.clicked.connect(lambda: self._show_workspace(0))
        self.nav_batch.clicked.connect(lambda: self._show_workspace(1))
        voice = QPushButton("Thay giọng")
        voice.clicked.connect(lambda: self.studio._thay_giong_dialog())
        v.addWidget(voice)
        ai = QPushButton("Cài đặt AI")
        ai.clicked.connect(lambda: self.studio._ai_settings())
        v.addWidget(ai)
        help_button = QPushButton("Hướng dẫn")
        help_button.clicked.connect(self._guide)
        v.addWidget(help_button)
        v.addSpacing(6)
        v.addWidget(hline())
        v.addSpacing(14)
        hardware_toggle = QPushButton("Thông tin thiết bị")
        hardware_toggle.setCheckable(True)
        details = QWidget()
        hardware_layout = QVBoxLayout(details)
        hardware_layout.setContentsMargins(0, 4, 0, 0)
        v.addWidget(hardware_toggle)
        v.addWidget(details)
        details.hide()
        hardware_toggle.toggled.connect(details.setVisible)

        # --- Thông tin máy (gọn, dọc) ---
        def info(label, val, col=None):
            box = QVBoxLayout(); box.setSpacing(1)
            a = QLabel(label); a.setStyleSheet(f"color:{MUTED}; font-size:11px;")
            b = QLabel(val); b.setStyleSheet(
                f"color:{col or TEXT}; font-size:13px; font-weight:600;")
            b.setWordWrap(True)
            box.addWidget(a); box.addWidget(b)
            hardware_layout.addLayout(box); hardware_layout.addSpacing(6)

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
        scroll = QScrollArea()
        scroll.setObjectName("navigation")
        scroll.setFixedWidth(212)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(w)
        return scroll

    def _open_admin(self):
        from app.ui.login import AdminUsersDialog
        AdminUsersDialog(self.state.user, self.state.admin_pass, self).exec()

    def _logout(self):
        if QMessageBox.question(
            self, "Đăng xuất",
            "Xoá mật khẩu đã lưu và thoát app? Lần sau mở sẽ phải đăng nhập lại."
        ) == QMessageBox.StandardButton.Yes:
            app_settings().remove("save_pass")
            # close() -> closeEvent chạy (dừng worker + giết tiến trình con);
            # quit() thẳng sẽ để ffmpeg/phân tích thành mồ côi.
            self.close()

    def _set_ai(self, v):
        self.state.pool.set_limits(max_gpu=v)
        app_settings().setValue("ai_workers", v)

    def _set_cut(self, v):
        self.state.pool.set_limits(max_cpu=v)
        app_settings().setValue("cut_workers", v)

    def _set_eco(self, on: bool):
        # Lưu .env (tiến trình con phân tích cũng đọc được) + áp NGAY vào
        # settings đang chạy — worker/_enc_args đọc settings.ECO_MODE mỗi lần.
        from config import update_env
        update_env({"ECO_MODE": "1" if on else "0"})
        self.state.pool._notify()      # đánh thức dispatcher áp giới hạn mới

    def closeEvent(self, event):
        # ĐẦU TIÊN bật cờ ĐANG ĐÓNG: 19 luồng nền (ảnh thu nhỏ/tải/TTS) phải im
        # lặng dừng, KHÔNG emit vào widget đang bị Qt phá — đó là gốc crash
        # 0xc0000005 mà WER ghi 8 lần (xem app/ui/shutdown.py).
        try:
            from app.ui.shutdown import set_closing
            set_closing()
        except Exception:  # noqa: BLE001
            pass
        # dừng worker + GIẾT tiến trình con (ffmpeg/phân tích) để không mồ côi
        try:
            from app.core.ffmpeg_utils import terminate_all_children
            terminate_all_children()
        except Exception:  # noqa: BLE001
            pass
        self.state.stop()
        super().closeEvent(event)
