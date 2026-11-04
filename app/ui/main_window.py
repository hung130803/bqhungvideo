"""
Cửa sổ chính: Video & clip, theo dõi hàng loạt và lối tắt cài đặt.
Studio luôn tồn tại để bộ điều phối dây chuyền tiếp tục khi đổi màn.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget, QScrollArea, QSplitter, QStackedWidget,
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
        # BỐ CỤC: [thanh bên CAO TRỌN cửa sổ] | [vùng làm việc / Tiến trình].
        # Bản cũ để Tiến trình là QDockWidget đáy -> nó chạy dưới CẢ thanh bên,
        # ép thanh bên thấp lại (tài khoản/phiên bản bị cuộn mất). Nay Tiến
        # trình nằm trong QSplitter dọc CHỈ ở cột phải; vạch kéo 7px giữ nguyên
        # cách kéo to/nhỏ như cũ.
        root.addWidget(self._sidebar())            # thanh bên trái (brand + máy)
        right = QSplitter(Qt.Orientation.Vertical)
        right.setObjectName("workSplit")
        right.setHandleWidth(7)
        right.setChildrenCollapsible(False)
        self._work_split = right
        wrap = QWidget()
        wl = QVBoxLayout(wrap); wl.setContentsMargins(16, 16, 16, 0); wl.setSpacing(0)
        self.studio = StudioPage(state)
        from app.ui.batch_page import BatchPage
        self.batch = BatchPage(state)
        self.studio.open_pipeline_center.connect(self._open_pipeline_center)
        self.batch.open_video.connect(self._open_batch_video)
        self.batch.open_folder.connect(self._open_batch_folder)
        self.batch.configure_pipeline.connect(self._batch_pipeline)
        self.batch.run_factory=lambda:self.studio._pipeline_dialog(embed=True)
        self.batch.channels.manage.connect(lambda:self._batch_manage('groups'))
        self.batch.channels.add.connect(lambda group:self._batch_manage('add',group))
        self.batch.channels.edit.connect(lambda pid:self._batch_manage('edit',pid))
        self.batch.channels.paths.connect(lambda pid:self._batch_manage('paths',pid))
        self.workspace = QStackedWidget()
        self.workspace.addWidget(self.studio)
        self.workspace.addWidget(self.batch)
        wl.addWidget(self.workspace, 1)
        right.addWidget(wrap)

        # khu Tiến trình: tiêu đề nhỏ (vai "section") + bảng hàng đợi
        from app.ui.theme import SP_1, SP_4, section
        dock = QWidget()
        dock.setObjectName("queueArea")
        dock.setWindowTitle("Tiến trình")
        dl = QVBoxLayout(dock); dl.setContentsMargins(0, 0, 0, 0); dl.setSpacing(0)
        head = QWidget(); head.setObjectName("dockTitle")
        hl = QHBoxLayout(head); hl.setContentsMargins(SP_4 - 2, 6, SP_4, SP_1)
        hl.addWidget(section("Tiến trình")); hl.addStretch(1)
        from app.ui.theme import set_size, set_variant
        self.queue_toggle = QPushButton("Thu gọn")
        set_variant(self.queue_toggle, "subtle"); set_size(self.queue_toggle, "compact")
        self.queue_toggle.setToolTip("Thu gọn / mở rộng khu Tiến trình (nhường chỗ cho danh sách clip).")
        self.queue_toggle.clicked.connect(lambda: self._set_queue_collapsed(
            not self.queue_panel.is_collapsed()))
        dl.addWidget(head)
        head.hide()                    # tiêu đề + nút thu gọn nằm luôn trong hàng chip
        dock.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.queue_dock = dock
        self.queue_panel = QueuePanel(state)
        self.queue_panel.add_header_widget(self.queue_toggle)
        dl.addWidget(self.queue_panel, 1)
        right.addWidget(dock)
        right.setStretchFactor(0, 1)
        right.setStretchFactor(1, 0)
        self._queue_h = 220
        right.setSizes([max(200, self.height() - self._queue_h), self._queue_h])
        try:
            _qc = app_settings().value("queue_collapsed", False, type=bool)
        except Exception:  # noqa: BLE001
            _qc = False
        if _qc:
            self._set_queue_collapsed(True, save=False)
        root.addWidget(right, 1)
        self.setCentralWidget(central)

        self._show_workspace(0)
        self._ban_sua_theo_doi()
        self._tam_dung_theo_doi()
        self._bot_noi_giao_dien()
        self._tu_chay_noi()
        # Tự kiểm tra bản mới (nền, im lặng nếu lỗi mạng)
        self._update_found.connect(self._notify_update)
        self._start_update_check()

        # DB hỏng + không cứu được -> đang chạy tạm trong RAM. Tiến trình con
        # (phân tích) KHÔNG dùng chung được DB này -> sẽ báo "không tìm thấy
        # video". Cảnh báo user RÕ ngay thay vì để lỗi khó hiểu về sau.
        self._warn_if_db_in_memory()

    # ---- BOT TELEGRAM: lệnh cần giao diện chạy ở LUỒNG GIAO DIỆN ----
    def _bot_noi_giao_dien(self):
        """Bot chạy ở luồng nền, KHÔNG được đụng Qt. Lệnh "chạy dây chuyền" được
        bot đẩy vào hàng đợi; QTimer này rút ra ở luồng giao diện (chạy cả khi
        đang mở hộp thoại modal — QTimer vẫn nhảy trong vòng lặp lồng)."""
        try:
            from PyQt6.QtCore import QTimer
            from app.core import tele_bot
            tele_bot.dang_ky_ui("chay_day_chuyen", self.studio._bot_chay_day_chuyen)
            tele_bot.dang_ky_ui("dang_nhan", self.studio._bot_dang_nhan)
            tele_bot.dang_ky_ui("nen_xem_truoc", self.studio._bot_nen_xem_truoc)
            # nhóm mới tạo còn rỗng + bật cả nhóm (lỗi thật 02/11/2026: nhóm
            # chưa tích 'Bật' biến mất khỏi bot không một lời giải thích)
            tele_bot.dang_ky_ui("nhom_rong", self.studio._bot_nhom_rong)
            tele_bot.dang_ky_ui("bat_nhom", self.studio._bot_bat_nhom)
            tele_bot.dang_ky_ui("dong_app", self._bot_dong_app)
            t = QTimer(self)
            t.timeout.connect(self._bot_rut_lenh)
            t.start(150)
            self._bot_timer = t
        except Exception:  # noqa: BLE001 - bot là phụ, không làm hỏng app
            pass

    # ---- TỰ CHẠY DÂY CHUYỀN (INTEGRATION.md mục 5, 11, 12) ----
    def _tu_chay_noi(self):
        """QTimer RIÊNG của MainWindow (không treo vào _poll_tick). Công tắc
        mặc định TẮT -> mọi nhịp trả về ngay, app chạy y như trước."""
        self._tu_chay = None
        try:
            from app.ui.tu_chay_ui import TuChayUI
            self._tu_chay = TuChayUI(self, self.studio, self.state)
            self._tu_chay.bat_dau()
            from app.core import tele_bot
            tele_bot.dang_ky_ui("tu_chay", self._tu_chay.lenh)
        except Exception as e:  # noqa: BLE001 - tự chạy là phụ, không làm hỏng app
            # dựng dở (vd đăng ký bot lỗi SAU bat_dau): DỪNG timer, không để
            # nửa Tự chạy chạy ngầm.
            try:
                self._tu_chay.dung()            # cả 3 timer, kể cả lượt đo đầu
            except Exception:  # noqa: BLE001
                pass
            self._tu_chay = None
            loi = f"{type(e).__name__}: {e}"
            try:
                self.studio._pipe_log(f"⚠ Tự chạy KHÔNG khởi động được — {loi}")
            except Exception:  # noqa: BLE001
                pass
            # 1b-V6: báo lên bot của CHÍNH app — thử lại tới khi GỬI ĐƯỢC
            self._tu_chay_loi_dung = {"loi": loi, "lan": 0, "xong": False,
                                      "cho": self.TC_BAO_CHO_MS, "tong": 0}
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(self.TC_BAO_CHO_MS, self._tu_chay_bao_loi_dung)

    #: chờ bot lên rồi báo "Tự chạy KHÔNG khởi động được"; thử lại GIÃN DẦN
    #: (x2, tối đa 1 giờ/lần) tới khi gửi được, trong tối đa 24 giờ (N4).
    TC_BAO_CHO_MS = 60_000
    TC_BAO_TRAN_MS = 3_600_000
    TC_BAO_TONG_MS = 24 * 3_600_000

    def _tu_chay_bao_loi_dung(self) -> None:
        st = getattr(self, "_tu_chay_loi_dung", None)
        if not st or st["xong"]:
            return
        st["lan"] += 1
        try:
            import html as _h
            from app.core import tele_bot
            b = tele_bot._bot
            if b is not None:
                txt = ("🔴 <b>Tự chạy dây chuyền KHÔNG khởi động được</b> — "
                       + _h.escape(st["loi"][:300], quote=False))

                def gui():
                    if b._gui_het(txt):
                        st["xong"] = True
                b._viec.submit(gui)
        except Exception:  # noqa: BLE001
            pass
        st["tong"] += st["cho"]
        if st["tong"] < self.TC_BAO_TONG_MS:
            st["cho"] = min(self.TC_BAO_TRAN_MS, st["cho"] * 2)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(st["cho"], self._tu_chay_bao_loi_dung)

    def _bot_dong_app(self) -> dict:
        """Bot xin ĐÓNG APP. Trả lời ngay rồi mới đóng sau 3 giây: bot kịp gửi tin
        báo + kịp xác nhận offset với Telegram (không thì mở lại nhận lại lệnh)."""
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._dong_that)
        return {"ok": True}

    def _dong_that(self):
        """Đóng y như bấm X: hộp thoại đang mở (Dây chuyền, Thay giọng…) phải
        đóng trước, không thì vòng exec() lồng của nó giữ app sống."""
        from PyQt6.QtWidgets import QApplication, QDialog
        for w in QApplication.topLevelWidgets():
            try:
                if isinstance(w, QDialog) and w.isVisible():
                    w.reject()
            except Exception:  # noqa: BLE001
                pass
        self.close()
        QApplication.quit()

    def _bot_rut_lenh(self):
        try:
            from app.core import tele_bot
            tele_bot.chay_hang_ui()
        except Exception:  # noqa: BLE001
            pass

    # ---- TẠM DỪNG (bot Telegram có thể bật từ xa): hiện lên tiêu đề ----
    def _tam_dung_theo_doi(self):
        """Người ngồi tại máy phải THẤY app đang tạm dừng — không thì tưởng
        dây chuyền treo. Đọc cờ 3s/lần (rẻ: chỉ đọc biến RAM của pool)."""
        from PyQt6.QtCore import QTimer
        t = QTimer(self)
        t.timeout.connect(self._tam_dung_kiem)
        t.start(3000)
        self._tam_dung_timer = t
        self._tam_dung_kiem()

    def _tam_dung_kiem(self):
        try:
            dung = self.state.pool.dang_tam_dung()
        except Exception:  # noqa: BLE001
            return
        tieu_de = f"BQ Hung Video v{__version__}" + (
            "  —  ⏸ ĐANG TẠM DỪNG nhận việc (bot Telegram: /chaytiep)" if dung else "")
        if self.windowTitle() != tieu_de:
            self.setWindowTitle(tieu_de)

    # ---- NGUỒN SỐNG: phát hiện bản sửa mới khi app đang mở ----
    def _ban_sua_theo_doi(self):
        try:
            import _nguon_song as _ns
        except Exception:  # noqa: BLE001
            return
        if not _ns.dang_bat():
            return
        from PyQt6.QtCore import QTimer
        self._ban_sua_goc = _ns.moc_moi_nhat()
        self._ban_sua_thay = 0.0
        t = QTimer(self)
        t.timeout.connect(self._ban_sua_kiem)
        t.start(60_000)
        self._ban_sua_timer = t

    def _ban_sua_kiem(self):
        import time as _t
        try:
            import _nguon_song as _ns
            moi = _ns.moc_moi_nhat()
        except Exception:  # noqa: BLE001
            return
        if moi <= getattr(self, "_ban_sua_goc", 0):
            return
        # chờ nguồn đứng yên >= 1 phút (đang ghi dở nhiều file)
        if moi != getattr(self, "_ban_sua_thay", 0):
            self._ban_sua_thay = moi
            return
        if _t.time() - moi < 60:
            return
        # chỉ TỰ mở lại khi KHÔNG có việc nào đang chạy/chờ; còn việc -> hiện nút
        try:
            from app import services
            c = services.queue_counts() or {}
            ban = sum(int(c.get(k, 0) or 0) for k in ("analyzing", "exporting", "waiting"))
        except Exception:  # noqa: BLE001
            ban = 1
        from PyQt6.QtWidgets import QApplication
        if ban == 0 and QApplication.activeModalWidget() is None:
            self._mo_lai_app()
            return
        if not self.btn_ban_sua.isVisible():
            self.btn_ban_sua.show()
            try:
                from app.ui.anim import toast
                toast(self, "Có bản sửa mới. App sẽ tự mở lại khi hết việc, "
                            "hoặc bấm nút ở góc trái dưới để mở lại ngay.", kind="info", ms=8000)
            except Exception:  # noqa: BLE001
                pass

    def _mo_lai_app(self):
        """Mở lại app (việc đang chờ được giữ — mở lên tự chạy tiếp)."""
        import os, sys
        from PyQt6.QtCore import QProcess
        args = [a for a in sys.argv[1:] if a != "--doi-pid"]
        ok = QProcess.startDetached(sys.executable, ["--doi-pid", str(os.getpid())] + args)
        if isinstance(ok, tuple):
            ok = ok[0]
        if ok:
            self.close()

    def _set_queue_collapsed(self, collapsed, save=True):
        """Thu gọn khu Tiến trình còn 1 hàng chip đếm; mở lại về chiều cao cũ."""
        sp = self._work_split
        if collapsed and not self.queue_panel.is_collapsed():
            self._queue_h = max(120, sp.sizes()[1] if len(sp.sizes()) > 1 else 220)
        self.queue_panel.set_collapsed(collapsed)
        self.queue_toggle.setText("Mở rộng" if collapsed else "Thu gọn")
        total = sum(sp.sizes()) or max(400, self.height())
        if collapsed:
            h = self.queue_dock.sizeHint().height()
            h = max(64, min(h, 110))
            self.queue_dock.setMaximumHeight(h)
        else:
            self.queue_dock.setMaximumHeight(16777215)
            h = self._queue_h
        sp.setSizes([max(200, total - h), h])
        if save:
            try:
                app_settings().setValue("queue_collapsed", bool(collapsed))
            except Exception:  # noqa: BLE001
                pass

    def _show_workspace(self, index):
        changed = self.workspace.currentIndex() != index
        self.workspace.setCurrentIndex(index)
        self.queue_dock.setVisible(index == 0)
        if changed:
            # trang mới "hiện dần" ~160 ms: 1 lớp phủ màu nền trơn làm trong dần
            # (không opacity-effect lên cả trang — xem app/ui/anim.py). Lỗi gì
            # cũng bỏ qua: hiệu ứng là phụ, đổi trang mới là chính.
            try:
                from app.ui.anim import fade_in
                from app.ui.theme import WINDOW
                fade_in(self.workspace, WINDOW)
            except Exception:  # noqa: BLE001
                pass
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
        """Thẻ 'Chạy dây chuyền' của màn Dây chuyền: bảng kênh NHÚNG thẳng vào
        màn (không còn hộp thoại riêng). Lần đầu dựng; các lần sau chỉ đồng bộ
        NHÓM đang chọn bên Theo dõi sang bảng chạy."""
        group=self.batch.group.currentData()
        if group is not None:self.studio._settings.setValue('pipe_grp_sel',group)
        if self.batch.run_panel is None:
            self.batch.ensure_run_panel()
            return
        cb=getattr(self.studio,'_pipe_grp_cb',None)
        if cb is not None and group is not None:
            try:
                i=cb.findData(group)
                if i>=0 and i!=cb.currentIndex():cb.setCurrentIndex(i)
            except RuntimeError:
                pass

    def _guide(self):
        from PyQt6.QtWidgets import QDialog, QPlainTextEdit
        dlg = QDialog(self)
        dlg.setWindowTitle("Hướng dẫn sử dụng")
        dlg.resize(740, 540)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "VIDEO & CLIP\n"
            "1. Chọn nhóm, kênh và video. Thêm file hoặc tải từ YouTube.\n"
            "2. Chọn mẫu và tùy chỉnh cắt. Bấm Tạo clip cho video đang chọn; "
            "Tạo nhiều để chọn nhiều video trong kênh.\n"
            "3. Duyệt clip, chỉnh điểm đầu/cuối, rồi xuất. Bật tự động xuất nếu muốn bỏ bước duyệt.\n\n"
            "DÂY CHUYỀN (2 thẻ trong cùng một màn)\n"
            "• Chọn kênh & chạy: chọn nhóm, tích các kênh cần chạy, bấm ▶ Chạy dây chuyền; "
            "báo cáo lần chạy hiện ngay bên dưới.\n"
            "• Theo dõi từng video: chọn nhóm đã lưu và kênh ở bên trái; bảng bên phải hiển thị video của kênh. "
            "Dùng Đổi đường dẫn… để chọn nơi lưu Part và nguồn Dây chuyền. "
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
        close.setProperty("primary", True)
        close.clicked.connect(dlg.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
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
        # Thanh bên dựng bằng TOKEN + vai QSS (theme.py): không stylesheet riêng
        # từng nhãn. Thứ tự đọc từ trên xuống: thương hiệu -> ĐIỀU HƯỚNG (2 khu
        # làm việc) -> CÔNG CỤ (mở hộp thoại) -> CHẠY SONG SONG -> THIẾT BỊ ->
        # tài khoản + phiên bản ở đáy.
        from app.ui.theme import (
            H_DEFAULT, SP_1, SP_2, SP_3, SP_4, divider, fit_width, muted, pad,
            section, set_role, set_tone, set_variant,
        )
        w = QWidget(); w.setObjectName("sidebar"); w.setMinimumWidth(190)
        v = QVBoxLayout(w); pad(v, SP_3, SP_4, SP_3, SP_3, spacing=SP_1)

        def group_lbl(text):
            # nhãn nhóm: chữ HOA nhỏ, mờ (vai "section"), cách nhóm trên 1 nhịp
            v.addSpacing(SP_3)
            g = section(text)
            g.setContentsMargins(SP_1, 0, 0, SP_1)
            v.addWidget(g)
            return g

        # --- Thương hiệu ---
        brand_row = QHBoxLayout(); brand_row.setSpacing(6)
        brand = QLabel("BQ Hung"); brand.setObjectName("brand")
        brand2 = QLabel("VIDEO"); brand2.setObjectName("brandAccent")
        brand_row.addWidget(brand); brand_row.addWidget(brand2); brand_row.addStretch(1)
        v.addLayout(brand_row)
        tag = muted("Cắt clip viral tự động")
        tag.setContentsMargins(0, 0, 0, SP_1)
        v.addWidget(tag)

        # --- Điều hướng: 2 khu làm việc (nút bật/tắt, đang chọn = nền accent) ---
        group_lbl("Không gian làm việc")
        self.nav_video = QPushButton("Video && clip")
        self.nav_batch = QPushButton("Dây chuyền")
        self.nav_video.setToolTip("Chọn kênh, video; tạo, duyệt và xuất clip.")
        self.nav_batch.setToolTip("Theo dõi dây chuyền nhiều kênh và lịch sử đã xuất.")
        for button in (self.nav_video, self.nav_batch):
            button.setCheckable(True)
            set_variant(button, "nav")
            button.setMinimumHeight(H_DEFAULT + 4)
            v.addWidget(button)
        self.nav_video.clicked.connect(lambda: self._show_workspace(0))
        self.nav_batch.clicked.connect(lambda: self._show_workspace(1))

        # --- Công cụ: mở hộp thoại (không đổi trang) ---
        group_lbl("Công cụ")
        voice = QPushButton("Thay giọng")
        voice.setToolTip("Lồng/đổi giọng cả thư mục video (video gốc giữ nguyên).")
        voice.clicked.connect(lambda: self.studio._thay_giong_dialog())
        ai = QPushButton("Cài đặt AI")
        ai.setToolTip("Key, mô hình AI và kiểm tra kết nối.")
        ai.clicked.connect(lambda: self.studio._ai_settings())
        help_button = QPushButton("Hướng dẫn")
        help_button.clicked.connect(self._guide)
        for button in (voice, ai, help_button):
            set_variant(button, "nav")
            button.setMinimumHeight(H_DEFAULT)
            v.addWidget(button)

        # --- Luồng chạy song song ---
        group_lbl("Máy & tốc độ")

        def spin_row(label, val, slot):
            r = QHBoxLayout(); r.setSpacing(SP_2)
            r.setContentsMargins(SP_1, 0, 0, 0)
            lb = QLabel(label)
            r.addWidget(lb, 1)
            # 58px từng bị CẮT SỐ ở scale 125/150% -> đo fontMetrics, tối thiểu 76
            sp = _NoWheelSpin(); sp.setRange(1, 16); sp.setValue(val)
            fit_width(sp, "88", pad_px=48, minimum=76)
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
        self.cb_eco = QCheckBox("Tiết kiệm máy")
        self.cb_eco.setChecked(settings.ECO_MODE)
        self.cb_eco.setToolTip(
            "BẬT (khuyên dùng): app chỉ chạy 1 video xuất + 1 phân tích cùng "
            "lúc, encode dùng ít luồng CPU và luôn NHƯỜNG app khác — máy vẫn "
            "dùng bình thường (lướt web, mở app khác không giật).\n"
            "TẮT = Hiệu năng tối đa: chạy đủ số luồng ở trên, xuất nhanh hơn "
            "khi cần làm hàng loạt (vẫn chừa 2 nhân cho hệ thống).")
        self.cb_eco.toggled.connect(self._set_eco)
        eco_row = QHBoxLayout(); eco_row.setContentsMargins(SP_1, 0, 0, 0)
        eco_row.addWidget(self.cb_eco)
        v.addSpacing(SP_1)
        v.addLayout(eco_row)

        # --- Dòng trạng thái ENCODER (GPU/CPU) + cảnh báo driver cũ ---
        # Máy có RTX mà driver cũ hơn bản ffmpeg yêu cầu -> NVENC bị tắt ngầm,
        # xuất chậm bằng CPU và user không biết vì sao. Hiện rõ + cách sửa.
        try:
            from app.core.ffmpeg_utils import detect_encoder, nvenc_note
            _enc = detect_encoder()          # đã cache lúc khởi động, không chậm
            enc_lbl = muted("Xuất bằng GPU (NVENC) ⚡" if _enc == "h264_nvenc"
                            else "Xuất bằng CPU (libx264)", wrap=False)
            enc_lbl.setContentsMargins(SP_1, SP_1, 0, 0)
            v.addWidget(enc_lbl)
            _note = nvenc_note()
            if _enc != "h264_nvenc" and _note:
                # GỌN: 1 dòng vàng, chi tiết nằm trong tooltip (bản cũ 4 dòng
                # chữ vàng chen giữa thanh bên)
                enc_lbl.setText("⚠ Đang xuất bằng CPU")
                set_tone(enc_lbl, "warn")
                enc_lbl.setToolTip(_note)
        except Exception:  # noqa: BLE001 - nhãn phụ, không được cản mở app
            pass

        # --- Thông tin thiết bị (thu gọn mặc định) ---
        v.addSpacing(SP_1)
        hardware_toggle = QPushButton("Thông tin thiết bị")
        hardware_toggle.setCheckable(True)
        set_variant(hardware_toggle, "nav")
        hardware_toggle.setToolTip("Bấm để xem/ẩn cấu hình máy, card đồ họa, ffmpeg.")
        details = QWidget()
        hardware_layout = QVBoxLayout(details)
        pad(hardware_layout, SP_2, SP_1, SP_2, 0, spacing=SP_2)
        v.addWidget(hardware_toggle)
        v.addWidget(details)
        details.hide()
        hardware_toggle.toggled.connect(details.setVisible)

        def info(label, val, tone=None):
            box = QVBoxLayout(); box.setSpacing(1)
            a = muted(label, role="hint", wrap=False)
            b = QLabel(val); set_role(b, "value")
            if tone:
                set_tone(b, tone)
            b.setWordWrap(True)
            box.addWidget(a); box.addWidget(b)
            hardware_layout.addLayout(box)

        gpu = HARDWARE.gpu_name if HARDWARE.has_cuda else "CPU (không GPU)"
        info("Máy", f"{HARDWARE.cpu_cores} luồng · {HARDWARE.ram_gb}GB")
        info("Card đồ họa", gpu, "accent" if HARDWARE.has_cuda else "muted")
        info("ffmpeg", "Sẵn sàng" if HARDWARE.has_ffmpeg else "THIẾU!",
             "success" if HARDWARE.has_ffmpeg else "danger")

        v.addStretch(1)

        # --- Tài khoản đang đăng nhập (thẻ nhỏ ở đáy) ---
        v.addSpacing(SP_3)
        v.addWidget(divider())
        v.addSpacing(SP_3)
        who = QLabel(f"Tài khoản: {self.state.user or '—'}"
                     + ("  (Admin)" if self.state.role == "admin" else ""))
        set_role(who, "muted"); who.setWordWrap(True)
        who.setContentsMargins(SP_1, 0, 0, SP_1)
        v.addWidget(who)
        if self.state.role == "admin":
            admin_btn = QPushButton("Quản lý tài khoản")
            admin_btn.setToolTip("Tạo / khoá / xoá tài khoản cho team.")
            admin_btn.clicked.connect(self._open_admin)
            set_variant(admin_btn, "ghost")
            v.addWidget(admin_btn)
        if self.state.user:
            out = QPushButton("Đăng xuất")
            out.setToolTip("Xoá mật khẩu đã lưu + thoát để đăng nhập tài khoản khác.")
            out.clicked.connect(self._logout)
            set_variant(out, "subtle")
            v.addWidget(out)
        v.addSpacing(SP_2)

        import os as _os
        _ban_sua = _os.environ.get("BQ_BAN_SUA", "")
        ver = muted(f"v{__version__}" + (f" · bản sửa {_ban_sua}" if _ban_sua else ""),
                    role="hint", wrap=False)
        ver.setToolTip(f"BQ Hung Video phiên bản {__version__}"
                       + (f"\nĐang chạy bản sửa mới nhất ({_ban_sua}) — không cần đóng gói lại."
                          if _ban_sua else ""))
        ver.setContentsMargins(SP_1, 0, 0, 0)
        v.addWidget(ver)
        # BẢN SỬA MỚI khi app đang mở (nguồn sống): hiện nút mở lại 1 chạm
        self.btn_ban_sua = QPushButton("Có bản sửa mới — mở lại app")
        set_variant(self.btn_ban_sua, "primary")
        self.btn_ban_sua.setToolTip("Mở lại app để dùng bản sửa mới. Việc đang chạy/chờ "
                                    "được giữ và tự chạy tiếp sau khi mở lại.")
        self.btn_ban_sua.clicked.connect(self._mo_lai_app)
        self.btn_ban_sua.hide()
        v.addWidget(self.btn_ban_sua)
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
        # Trạng thái bận cho PCBot: ghi lần cuối ban=false (mục 12) TRƯỚC khi
        # bật cờ đóng (sau đó mọi việc nền im lặng bỏ).
        try:
            if getattr(self, "_tu_chay", None) is not None:
                self._tu_chay.thoat()
        except Exception:  # noqa: BLE001
            pass
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
