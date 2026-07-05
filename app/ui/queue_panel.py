"""
Khu "Tiến trình": mỗi việc 1 dòng có thanh % rõ ràng + thông báo bước hiện tại.
Cập nhật TẠI CHỖ (không dựng lại widget mỗi nhịp) -> thanh chạy MƯỢT, không giật.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from app import services
from app.ui.state import AppState
from app.ui.theme import ACCENT, DANGER, MUTED, SUCCESS, SURFACE

_TYPE = {"auto": "Tạo clip", "analyze": "Phân tích", "m1_highlights": "Tìm highlight",
         "m1_mixed_cut": "Mixed-Cut", "m1_export_clip": "Xuất clip"}
_STATUS = {"running": ("Đang chạy", ACCENT), "pending": ("Đang chờ", MUTED),
           "done": ("✓ Hoàn tất", SUCCESS), "failed": ("✕ Lỗi", DANGER),
           "canceled": ("Đã hủy", MUTED), "skipped": ("Bỏ qua", MUTED)}
# màu phân biệt KÊNH (mỗi kênh 1 màu cố định theo id)
_PALETTE = ["#4F7DFF", "#22C55E", "#F59E0B", "#EC4899", "#06B6D4",
            "#A78BFA", "#EF4444", "#14B8A6", "#F97316", "#8B5CF6"]


def _chan_color(pid):
    return _PALETTE[(int(pid) if pid else 0) % len(_PALETTE)]


def _job_name(j):
    """Tên hiển thị: 'Kênh · Video'."""
    import os
    chan = j["chan_name"] if "chan_name" in j.keys() and j["chan_name"] else "—"
    vid = ""
    if "vid_path" in j.keys() and j["vid_path"]:
        vid = os.path.splitext(os.path.basename(j["vid_path"]))[0]
    label = _TYPE.get(j["type"], j["type"])
    if vid:
        return f"{chan} · {vid}", chan, vid
    return f"{chan} · {label}", chan, label


class QueuePanel(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setMinimumHeight(70)        # cho phép kéo to/nhỏ (như terminal)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 6, 14, 8)
        outer.setSpacing(4)
        # ---- thanh đầu: Hủy tất cả + Xóa lịch sử (canh phải) ----
        hd = QHBoxLayout()
        hd.addStretch(1)
        ca = QPushButton("Hủy tất cả"); ca.setProperty("danger", True)
        ca.setToolTip("Hủy MỌI việc đang chạy & đang chờ cùng lúc.")
        ca.clicked.connect(self._cancel_all)
        hd.addWidget(ca)
        clr = QPushButton("Xóa lịch sử"); clr.setProperty("ghost", True)
        clr.setToolTip("Xóa việc đã xong/lỗi khỏi danh sách (việc đang chạy giữ nguyên).")
        clr.clicked.connect(self._clear_history)
        hd.addWidget(clr)
        outer.addLayout(hd)
        # ---- vùng CUỘN chứa các dòng (xem lại việc trước) ----
        host = QWidget()
        self.lay = QVBoxLayout(host)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(7)
        self.empty = QLabel("Chưa có việc nào đang chạy.")
        self.empty.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        self.lay.addWidget(self.empty)
        self.lay.addStretch(1)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(host)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sc.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(sc, 1)
        self._rows: dict[int, dict] = {}
        self._sig = None                # chữ ký (id, status) để biết khi nào dựng lại
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(400)           # nhịp nhanh hơn cho mượt

    def _cancel_all(self):
        for j in services.list_jobs(limit=200):
            if j["status"] in ("running", "pending"):
                self.state.pool.cancel(j["id"])
        self._sig = None
        self.refresh()

    def _clear_history(self):
        services.clear_finished_jobs()
        self._sig = None                # ép dựng lại danh sách
        self.refresh()

    # ---- vòng cập nhật ----
    def refresh(self):
        jobs = services.list_jobs(limit=60)
        active = [j for j in jobs if j["status"] in ("running", "pending")]
        recent = [j for j in jobs
                  if j["status"] in ("done", "failed", "canceled", "skipped")][:20]
        show = active + recent
        sig = [(j["id"], j["status"]) for j in show]
        if sig != self._sig:            # tập việc/trạng thái đổi -> dựng lại bố cục
            self._rebuild(show)
            self._sig = sig
        else:                           # chỉ % / thông báo đổi -> cập nhật tại chỗ (mượt)
            for j in show:
                self._update(j)

    def _clear(self):
        while self.lay.count():
            it = self.lay.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        self._rows = {}

    def _rebuild(self, show):
        self._clear()
        if not show:
            self.empty = QLabel("Chưa có việc nào đang chạy.")
            self.empty.setStyleSheet(f"color:{MUTED}; font-size:14px;")
            self.lay.addWidget(self.empty)
            self.lay.addStretch(1)
            return
        for j in show:
            row = self._make_row(j)
            self._rows[j["id"]] = row
            self.lay.addWidget(row["w"])
        self.lay.addStretch(1)

    # ---- 1 dòng việc ----
    def _make_row(self, j):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        col = _chan_color(j["project_id"])
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(f"background:{col}; border-radius:6px;")
        lay.addWidget(dot)

        full_name, _, _ = _job_name(j)
        name = QLabel(full_name)
        # tên kênh+video, màu theo kênh, co lại được (không đẩy nút)
        name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        name.setMinimumWidth(120)
        name.setStyleSheet(f"color:{col}; font-size:13px; font-weight:600;")
        name.setToolTip(full_name)
        lay.addWidget(name, 3)

        bar = QProgressBar()
        bar.setFixedHeight(11)          # thanh MẢNH, dịu mắt
        bar.setRange(0, 100)
        bar.setTextVisible(False)       # % hiện ở nhãn trạng thái (thanh quá mảnh)
        lay.addWidget(bar, 3)

        st = QLabel()
        st.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        st.setMinimumWidth(70)
        st.setStyleSheet("font-size:12px;")
        lay.addWidget(st, 2)

        btn = QPushButton()
        btn.setFixedWidth(76)
        btn.setFixedHeight(26)
        lay.addWidget(btn, 0)

        row = {"w": w, "bar": bar, "st": st, "btn": btn, "name": name, "col": col}
        self._wire_btn(btn, j)
        self._update(j, row)
        return row

    def _wire_btn(self, btn, j):
        try:
            btn.clicked.disconnect()
        except TypeError:
            pass
        if j["status"] in ("running", "pending"):
            btn.setText("Hủy"); btn.setProperty("danger", True); btn.show()
            btn.clicked.connect(lambda _, i=j["id"]: self._cancel(i))
        elif j["status"] in ("failed", "canceled"):
            # retry() hỗ trợ cả 'canceled' -> lỡ tay hủy vẫn chạy lại được
            btn.setText("Thử lại"); btn.setProperty("ghost", True); btn.show()
            btn.clicked.connect(lambda _, i=j["id"]: self._retry(i))
        else:
            btn.hide()

    def _update(self, j, row=None):
        row = row or self._rows.get(j["id"])
        if not row:
            return
        pct = int(round((j["progress"] or 0) * 100))
        bar = row["bar"]
        if j["status"] == "done":
            pct = 100
        bar.setValue(pct)
        # màu thanh theo trạng thái: accent khi chạy, success DỊU khi xong
        chunk = {"failed": DANGER, "done": SUCCESS}.get(j["status"], ACCENT)
        bar.setStyleSheet(
            f"QProgressBar{{background:{SURFACE}; border:none; border-radius:5px;}} "
            f"QProgressBar::chunk{{background:{chunk}; border-radius:5px;}}")
        # việc đã xong/hủy: MỜ BỚT tên (đỡ tranh chú ý với việc đang chạy)
        faded = j["status"] in ("done", "canceled", "skipped")
        row["name"].setStyleSheet(
            f"color:{MUTED if faded else row['col']}; font-size:13px; font-weight:600;")
        txt, color = _STATUS.get(j["status"], (j["status"], MUTED))
        msg = (j["message"] or j["error"] or "").strip()
        # đang chạy: hiện % + bước hiện tại; lỗi: hiện lý do
        detail = msg if j["status"] in ("running", "failed") and msg else ""
        if j["status"] == "running":
            txt = f"{pct}% · {txt}"
        full = f"{txt}" + (f" · {detail}" if detail else "")
        row["st"].setText(full[:80])
        row["st"].setStyleSheet(f"color:{color}; font-size:12px;")
        row["st"].setToolTip(full)

    # ---- hành động ----
    def _cancel(self, i):
        self.state.pool.cancel(i)
        self.refresh()

    def _retry(self, i):
        self.state.pool.retry(i)
        self.refresh()
