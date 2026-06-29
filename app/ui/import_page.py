"""
Bước 1 — IMPORT: tạo/chọn/xóa project, thêm/xóa video, chạy lõi phân tích.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app import services
from app.ui.state import AppState


def _fmt_dur(sec: float) -> str:
    sec = int(sec or 0)
    return f"{sec // 60}:{sec % 60:02d}"


class ImportPage(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)

        lay.addWidget(QLabel("<h2>Bước 1 — Nhập video gốc</h2>"))
        lay.addWidget(QLabel(
            "Tạo project → thêm video gốc → bấm <b>Phân tích</b>. Lõi phân tích "
            "(chép lời, dò cảnh, beat, bám mặt) chỉ chạy MỘT LẦN, lưu lại để "
            "bước cắt highlight dùng."))

        # ---- project ----
        prow = QHBoxLayout()
        prow.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._on_project_select)
        prow.addWidget(self.project_combo, 1)
        new_btn = QPushButton("+ Project mới")
        new_btn.clicked.connect(self._new_project)
        prow.addWidget(new_btn)
        del_proj_btn = QPushButton("🗑 Xóa project")
        del_proj_btn.setProperty("danger", True)
        del_proj_btn.clicked.connect(self._delete_project)
        prow.addWidget(del_proj_btn)
        lay.addLayout(prow)

        # ---- video list ----
        vrow = QHBoxLayout()
        add_btn = QPushButton("+ Thêm video...")
        add_btn.clicked.connect(self._add_videos)
        vrow.addWidget(add_btn)
        self.del_vid_btn = QPushButton("🗑 Xóa video đang chọn")
        self.del_vid_btn.setProperty("danger", True)
        self.del_vid_btn.clicked.connect(self._delete_video)
        vrow.addWidget(self.del_vid_btn)
        vrow.addStretch(1)
        lay.addLayout(vrow)

        self.video_list = QListWidget()
        self.video_list.currentItemChanged.connect(self._on_video_select)
        lay.addWidget(self.video_list, 1)

        # ---- actions ----
        arow = QHBoxLayout()
        self.analyze_btn = QPushButton("▶  Phân tích video đang chọn")
        self.analyze_btn.setProperty("primary", True)
        self.analyze_btn.clicked.connect(lambda: self._analyze(all_videos=False))
        arow.addWidget(self.analyze_btn)
        self.analyze_all_btn = QPushButton("▶▶ Phân tích các video CHƯA xong")
        self.analyze_all_btn.clicked.connect(lambda: self._analyze(all_videos=True))
        arow.addWidget(self.analyze_all_btn)
        arow.addStretch(1)
        lay.addLayout(arow)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        self.reload_projects()

        # tự cập nhật nhãn trạng thái phân tích trong danh sách
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_labels)
        self.timer.start(1500)

    # ---- project ----
    def reload_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in services.list_projects():
            self.project_combo.addItem(p["name"], p["id"])
        self.project_combo.blockSignals(False)
        if self.project_combo.count():
            self._on_project_select(self.project_combo.currentIndex())
        else:
            self.state.project_id = None
            self.video_list.clear()

    def _new_project(self):
        name, ok = QInputDialog.getText(self, "Project mới", "Tên project:")
        if ok and name.strip():
            pid = services.create_project(name.strip())
            self.reload_projects()
            idx = self.project_combo.findData(pid)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)

    def _delete_project(self):
        pid = self.project_combo.currentData()
        if pid is None:
            return
        name = self.project_combo.currentText()
        if QMessageBox.question(
            self, "Xóa project",
            f"Xóa hẳn project '{name}' cùng TẤT CẢ video, clip và dữ liệu của nó?\n"
            "Không hoàn tác được.",
        ) != QMessageBox.StandardButton.Yes:
            return
        services.delete_project(int(pid))
        self.reload_projects()
        self.hint.setText(f"Đã xóa project '{name}'.")

    def _on_project_select(self, _idx: int):
        pid = self.project_combo.currentData()
        if pid is None:
            return
        self.state.set_project(int(pid))
        self.reload_videos()

    # ---- video ----
    def _add_videos(self):
        if self.state.project_id is None:
            QMessageBox.warning(self, "Chưa có project", "Hãy tạo project trước.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn video gốc", "",
            "Video (*.mp4 *.mov *.mkv *.avi *.webm *.m4v);;Tất cả (*.*)")
        for f in files:
            services.import_video(self.state.project_id, f)
        self.reload_videos()
        if files:
            self.hint.setText(f"Đã thêm {len(files)} video. Bấm 'Phân tích' để xử lý.")

    def _delete_video(self):
        vid = self.state.video_id
        if vid is None:
            QMessageBox.information(self, "Chưa chọn video", "Hãy chọn video cần xóa.")
            return
        cur = self.video_list.currentItem()
        name = cur.text() if cur else f"#{vid}"
        if QMessageBox.question(
            self, "Xóa video",
            f"Xóa video này khỏi project cùng dữ liệu phân tích + clip đã xuất?\n{name}",
        ) != QMessageBox.StandardButton.Yes:
            return
        services.delete_video(int(vid))
        self.state.video_id = None
        self.reload_videos()
        self.hint.setText("Đã xóa video.")

    def reload_videos(self):
        self.video_list.clear()
        if self.state.project_id is None:
            return
        for v in services.list_videos(self.state.project_id):
            item = QListWidgetItem(self._video_label(v))
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self.video_list.addItem(item)
        if self.video_list.count():
            self.video_list.setCurrentRow(0)

    @staticmethod
    def _video_label(v) -> str:
        fname = Path(v["src_path"]).name
        status = services.video_analysis_label(v["id"])
        return (f'#{v["id"]}  {fname}   '
                f'[{_fmt_dur(v["duration"])}, {v["width"]}x{v["height"]}]   {status}')

    def _refresh_labels(self):
        """Cập nhật nhãn trạng thái mà không phá lựa chọn hiện tại."""
        if self.state.project_id is None or not self.isVisible():
            return
        vids = {v["id"]: v for v in services.list_videos(self.state.project_id)}
        if self.video_list.count() != len(vids):
            self.reload_videos()
            return
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            vid = item.data(Qt.ItemDataRole.UserRole)
            if vid in vids:
                item.setText(self._video_label(vids[vid]))

    def _on_video_select(self, cur, _prev):
        if cur is None:
            return
        vid = cur.data(Qt.ItemDataRole.UserRole)
        if vid is not None:
            self.state.set_video(int(vid))

    # ---- analyze ----
    def _analyze(self, all_videos: bool):
        if self.state.project_id is None:
            return
        pid = self.state.project_id
        all_vids = services.list_videos(pid)

        if all_videos:
            todo = [v["id"] for v in all_vids if not services.video_analyzed(v["id"])]
            if not todo:
                QMessageBox.information(
                    self, "Không có gì để làm",
                    "Mọi video trong project đã phân tích xong. Qua bước 3 để cắt.")
                return
        else:
            vid = self.state.video_id
            if not vid:
                QMessageBox.information(self, "Chưa chọn video", "Hãy chọn 1 video.")
                return
            if services.video_analyzed(vid):
                QMessageBox.information(
                    self, "Đã phân tích rồi",
                    "Video này đã phân tích xong. Qua bước 3 (Cắt highlight) để cắt, "
                    "hoặc dùng nút 'Phân tích lại' ở bước 2 nếu muốn làm lại.")
                return
            todo = [vid]

        for v in todo:
            services.enqueue_analysis(self.state.pool, v, pid)
        self.hint.setText(
            f"Đã đưa {len(todo)} video vào hàng đợi phân tích. Xem tiến trình ở "
            "bảng Hàng đợi bên dưới; khi hiện '✓ đã phân tích' thì qua bước 3.")

    # gọi khi mở lại trang
    def refresh(self):
        self._refresh_labels()