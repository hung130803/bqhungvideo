"""
Khu "Tiến trình": mỗi việc 1 dòng có thanh % rõ ràng + thông báo bước hiện tại.
Cập nhật TẠI CHỖ (không dựng lại widget mỗi nhịp) -> thanh chạy MƯỢT, không giật.

BỐ CỤC 1 DÒNG (dùng hết bề ngang, không gì bị cắt):
[chấm kênh] [TÊN VIỆC — chiếm mọi chỗ thừa, elide "…" ở giữa] [thanh %] [trạng
thái "45% · Đang cắt" — bề ngang CỐ ĐỊNH đo theo font, không bao giờ cụt] [nút].
Header: chips đếm (trái) + nút Hủy tất cả/Xóa lịch sử (phải) CÙNG 1 hàng khi đủ
rộng; panel hẹp thì chips tự xuống dòng riêng.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from app import services
from app.ui.state import AppState
from app.ui.theme import ACCENT, DANGER, MUTED, SUCCESS, SURFACE, WARN

_TYPE = {"auto": "Tạo clip", "analyze": "Phân tích", "m1_highlights": "Tìm highlight",
         "m1_mixed_cut": "Mixed-Cut", "auto_mixed": "Mixed-Cut",
         "m1_export_clip": "Xuất clip"}
# Nhãn NGẮN + icon theo GIAI ĐOẠN (hiện ở TRƯỚC để biết ngay đang làm gì)
_TYPE_TAG = {"auto": "🔍 Phân tích", "analyze": "🔍 Phân tích",
             "auto_mixed": "🔍 Mixed-Cut", "m1_mixed_cut": "🔍 Mixed-Cut",
             "m1_highlights": "🔍 Tìm clip", "m1_export_clip": "✂ Xuất"}
_STATUS = {"running": ("Đang chạy", ACCENT), "pending": ("Đang chờ", MUTED),
           "done": ("✓ Hoàn tất", SUCCESS), "failed": ("✕ Lỗi · bấm xem", DANGER),
           "canceled": ("Đã hủy", MUTED), "skipped": ("Bỏ qua", MUTED)}
# MÀU THANH theo GIAI ĐOẠN: phân tích/AI = TÍM; cắt/xuất video = XANH NGỌC.
_PHASE_ANALYZE = "#A78BFA"      # phân tích + AI chọn clip
_PHASE_EXPORT = "#14B8A6"       # cắt + xuất video
_EXPORT_TYPES = {"m1_export_clip"}
# chữ giai đoạn khi ĐANG CHẠY (đặt sau %): "45% · Đang cắt"
_RUN_ANALYZE = "Đang phân tích"
_RUN_EXPORT = "Đang cắt"
_NARROW_PX = 520                # dưới cỡ này: trạng thái rút gọn "45%" / "✕ Lỗi"
# màu phân biệt KÊNH (mỗi kênh 1 màu cố định theo id)
_PALETTE = ["#4F7DFF", "#22C55E", "#F59E0B", "#EC4899", "#06B6D4",
            "#A78BFA", "#EF4444", "#14B8A6", "#F97316", "#8B5CF6"]


def _chan_color(pid):
    return _PALETTE[(int(pid) if pid else 0) % len(_PALETTE)]


def _rgba(hex_color: str, a: float) -> str:
    """'#RRGGBB' -> 'rgba(r,g,b,a)' — làm NỀN MỜ cho chip đếm theo màu."""
    h = hex_color.lstrip("#")
    return (f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},"
            f"{int(h[4:6], 16)},{a})")


def _phase_color(jtype: str) -> str:
    """Màu thanh theo giai đoạn: xuất video = xanh ngọc, còn lại = tím."""
    return _PHASE_EXPORT if jtype in _EXPORT_TYPES else _PHASE_ANALYZE


def _part_no(j) -> int:
    """Số Part của việc XUẤT clip (đọc từ payload). 0 nếu không có."""
    if j["type"] != "m1_export_clip":
        return 0
    try:
        import json
        p = j["payload"] if "payload" in j.keys() else ""
        return int((json.loads(p) or {}).get("part_no", 0) or 0)
    except (ValueError, TypeError, KeyError):
        return 0


def _job_name(j):
    """Nhãn: '<GIAI ĐOẠN> [Part N] · Kênh · Video' — hiện rõ loại việc + Part
    Ở TRƯỚC để user biết ngay đang làm gì cho video nào."""
    import os
    chan = j["chan_name"] if "chan_name" in j.keys() and j["chan_name"] else "—"
    vid = ""
    if "vid_path" in j.keys() and j["vid_path"]:
        vid = os.path.splitext(os.path.basename(j["vid_path"]))[0]
    tag = _TYPE_TAG.get(j["type"], _TYPE.get(j["type"], j["type"]))
    part = _part_no(j)
    if part > 0:
        tag = f"{tag} Part {part}"          # ✂ Xuất Part 3
    who = vid or _TYPE.get(j["type"], j["type"])
    return f"{tag} · {chan} · {who}", chan, who


class _ElideLabel(QLabel):
    """QLabel tự elide '…' theo bề ngang thật: PHẦN ĐẦU (loại việc + Part) luôn
    giữ nguyên, phần dài phía sau (kênh · video) elide Ở GIỮA — đầu và đuôi tên
    video vẫn thấy; tooltip giữ tên đầy đủ."""

    def __init__(self):
        super().__init__()
        self._full = ""
        self._prefix = ""               # "✂ Xuất Part 3" — không bao giờ mất
        self._rest = ""                 # " · Kênh · Video dài..."
        # Ignored ngang -> layout KHÔNG phình theo chữ; label ăn đúng phần
        # stretch được chia, chữ dài tự elide theo width thật.
        self.setSizePolicy(QSizePolicy.Policy.Ignored,
                           QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(48)

    def set_full_text(self, text: str) -> None:
        if text == self._full:
            return
        self._full = text
        self._prefix, sep, rest = text.partition(" · ")
        self._rest = sep + rest
        self.setToolTip(text)
        self._refit()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self._refit()

    def _refit(self) -> None:
        fm = self.fontMetrics()
        w = max(24, self.width() - 2)
        if fm.horizontalAdvance(self._full) <= w:
            self.setText(self._full)    # đủ chỗ -> hiện nguyên
            return
        pw = fm.horizontalAdvance(self._prefix)
        if pw + 20 >= w:                # hẹp tới mức prefix cũng không lọt
            self.setText(fm.elidedText(self._prefix,
                                       Qt.TextElideMode.ElideRight, w))
            return
        self.setText(self._prefix + fm.elidedText(
            self._rest, Qt.TextElideMode.ElideMiddle, w - pw))


class QueuePanel(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setMinimumHeight(70)        # cho phép kéo to/nhỏ (như terminal)

        # ---- font + BỀ NGANG CỐ ĐỊNH đo bằng font metrics (không bao giờ cụt) --
        self._name_font = QFont(self.font())
        self._name_font.setPixelSize(13)
        self._name_font.setWeight(QFont.Weight.DemiBold)
        self._st_font = QFont(self.font())
        self._st_font.setPixelSize(12)
        fm = QFontMetrics(self._st_font)
        longest = [f"100% · {_RUN_ANALYZE}", f"100% · {_RUN_EXPORT}"]
        longest += [t for t, _ in _STATUS.values()]
        self._st_w_full = max(fm.horizontalAdvance(s) for s in longest) + 8
        # panel HẸP: trạng thái rút còn "45%" / "✕ Lỗi" (màu vẫn nói giai đoạn)
        shorts = ["100%", "✕ Lỗi"] + [t for t, _ in _STATUS.values()
                                      if t != "✕ Lỗi · bấm xem"]
        self._st_w_short = max(fm.horizontalAdvance(s) for s in shorts) + 8
        self._narrow = False            # bật khi width < _NARROW_PX
        self._btn_w = max(fm.horizontalAdvance(s)
                          for s in ("Hủy", "Thử lại")) + 26

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 8)
        outer.setSpacing(6)

        # ---- HEADER 1 hàng: chips đếm (trái) + Hủy tất cả/Xóa lịch sử (phải).
        # Hẹp quá -> chips tự xuống hàng riêng (xem _layout_header).
        self._chips_w = QWidget()
        chips = QHBoxLayout(self._chips_w)
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(6)
        self.chip_analyze = self._make_chip("🔍", "phân tích", _PHASE_ANALYZE)
        self.chip_export = self._make_chip("✂", "đang cắt", _PHASE_EXPORT)
        self.chip_wait = self._make_chip("⏳", "đợi", WARN)
        self.chip_done = self._make_chip("✅", "xong", SUCCESS)
        self.chip_fail = self._make_chip("❌", "lỗi", DANGER)
        self.chip_fail["w"].hide()      # chỉ hiện khi CÓ lỗi (đỡ dọa user)
        for ch in (self.chip_analyze, self.chip_export, self.chip_wait,
                   self.chip_done, self.chip_fail):
            chips.addWidget(ch["w"])
        self._counts = None             # cache -> chỉ vẽ lại chip khi số ĐỔI

        self._btns_w = QWidget()
        bh = QHBoxLayout(self._btns_w)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(6)
        ca = QPushButton("Hủy tất cả"); ca.setProperty("danger", True)
        ca.setToolTip("Hủy MỌI việc đang chạy & đang chờ cùng lúc.")
        ca.setStyleSheet("QPushButton{padding:3px 12px; font-size:12px;}")
        ca.clicked.connect(self._cancel_all)
        bh.addWidget(ca)
        clr = QPushButton("Xóa lịch sử"); clr.setProperty("ghost", True)
        clr.setToolTip("Xóa việc đã xong/lỗi khỏi danh sách (việc đang chạy giữ nguyên).")
        clr.setStyleSheet("QPushButton{padding:3px 12px; font-size:12px;}")
        clr.clicked.connect(self._clear_history)
        bh.addWidget(clr)

        self._hdr = QGridLayout()
        self._hdr.setContentsMargins(0, 0, 0, 0)
        self._hdr.setHorizontalSpacing(8)
        self._hdr.setVerticalSpacing(4)
        self._hdr.setColumnStretch(0, 1)
        self._hdr.addWidget(self._btns_w, 0, 1,
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter)
        self._hdr_wide = None           # None -> ép xếp lần đầu
        self._layout_header()
        outer.addLayout(self._hdr)

        # ---- vùng CUỘN chứa các dòng (xem lại việc trước) ----
        host = QWidget()
        self.lay = QVBoxLayout(host)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(4)
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

    # ---- header co giãn: đủ rộng = chips + nút CÙNG hàng; hẹp = 2 hàng ----
    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self._layout_header()
        # panel HẸP: cột trạng thái rút gọn ("45%", "✕ Lỗi") nhường chỗ cho TÊN
        narrow = self.width() < _NARROW_PX
        if narrow != self._narrow:
            self._narrow = narrow
            w = self._st_w_short if narrow else self._st_w_full
            for row in self._rows.values():
                row["st"].setFixedWidth(w)
            self._sig = None            # ép viết lại chữ trạng thái theo cỡ mới
            self.refresh()

    def _layout_header(self):
        avail = self.width() - 24       # trừ margin outer trái+phải
        need = (self._chips_w.sizeHint().width()
                + self._btns_w.sizeHint().width() + 24)
        wide = need <= avail
        if wide == self._hdr_wide:
            return
        self._hdr_wide = wide
        self._hdr.removeWidget(self._chips_w)
        if wide:                        # chips trái + nút phải CÙNG 1 hàng
            self._hdr.addWidget(self._chips_w, 0, 0,
                                Qt.AlignmentFlag.AlignLeft
                                | Qt.AlignmentFlag.AlignVCenter)
        else:                           # hẹp: nút hàng trên, chips hàng dưới
            self._hdr.addWidget(self._chips_w, 1, 0, 1, 2,
                                Qt.AlignmentFlag.AlignLeft)

    # ---- chip đếm trạng thái ----
    @staticmethod
    def _make_chip(icon: str, label: str, color: str) -> dict:
        """1 ô đếm GỌN: 'icon SỐ nhãn' — ôm sát nội dung, xếp cạnh nhau."""
        w = QFrame()
        w.setStyleSheet(
            f"QFrame{{background:{_rgba(color, 0.13)}; "
            f"border:1px solid {_rgba(color, 0.35)}; border-radius:8px;}}")
        w.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 3, 8, 3)
        h.setSpacing(4)
        num = QLabel(f"{icon} 0")
        num.setStyleSheet(f"color:{color}; font-size:12px; font-weight:700; "
                          f"background:transparent; border:none;")
        lab = QLabel(label)
        lab.setStyleSheet(f"color:{MUTED}; font-size:11px; "
                          f"background:transparent; border:none;")
        h.addWidget(num)
        h.addWidget(lab)
        return {"w": w, "num": num, "icon": icon}

    def _update_chips(self):
        """Đếm từ DB (1 GROUP BY nhẹ) rồi đổ số vào chip — mỗi nhịp poll."""
        try:
            c = services.queue_counts()
        except Exception:
            return                      # DB bận/khóa thoáng qua -> giữ số cũ
        if c == self._counts:
            return                      # số không đổi -> không đụng widget
        self._counts = c
        for ch, key in ((self.chip_analyze, "analyzing"),
                        (self.chip_export, "exporting"),
                        (self.chip_wait, "waiting"),
                        (self.chip_done, "done"),
                        (self.chip_fail, "failed")):
            ch["num"].setText(f"{ch['icon']} {c[key]}")
        self.chip_analyze["w"].setToolTip(
            f"{c['analyzing']} video đang phân tích")
        self.chip_export["w"].setToolTip(
            f"{c['exporting']} clip đang cắt/xuất (mỗi Part là 1 clip)")
        self.chip_wait["w"].setToolTip(
            f"Đang đợi {c['waiting']} việc — đợi phân tích "
            f"{c['wait_analyze']} · đợi cắt {c['wait_export']}")
        self.chip_done["w"].setToolTip(
            f"{c['done']} việc hoàn tất hôm nay")
        self.chip_fail["w"].setToolTip(
            f"{c['failed']} việc lỗi hôm nay — bấm 'Thử lại' ở dòng lỗi")
        # chip LỖI chỉ hiện khi có lỗi thật (failed>0)
        self.chip_fail["w"].setVisible(c["failed"] > 0)
        self._hdr_wide = None           # bề ngang chips đổi -> xếp lại header
        self._layout_header()

    def _cancel_all(self):
        # 1 lời gọi: pending -> canceled ngay (1 SQL), job đang chạy -> kill
        # tiến trình con tức thì. Không join/chờ gì -> UI không đơ.
        self.state.pool.cancel_all()
        self._sig = None
        self.refresh()

    def _clear_history(self):
        services.clear_finished_jobs()
        self._sig = None                # ép dựng lại danh sách
        self.refresh()

    # ---- vòng cập nhật ----
    def refresh(self):
        self._update_chips()            # bảng đếm dùng CHUNG nhịp poll này
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

    # ---- 1 dòng việc: [chấm] [tên co giãn] [thanh %] [trạng thái] [nút] ----
    def _make_row(self, j):
        w = QWidget()
        w.setFixedHeight(30)            # dòng thấp, đều nhau, sát hợp lý
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        col = _chan_color(j["project_id"])
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{col}; border-radius:5px;")
        lay.addWidget(dot)

        full_name, _, _ = _job_name(j)
        name = _ElideLabel()
        name.setFont(self._name_font)
        name.setStyleSheet(f"color:{col};")
        name.set_full_text(full_name)
        lay.addWidget(name, 2)          # TÊN ăn PHẦN LỚN chỗ thừa, tự elide "…"

        bar = QProgressBar()
        bar.setFixedHeight(10)          # thanh MẢNH, dịu mắt
        bar.setRange(0, 100)
        bar.setTextVisible(False)       # % hiện ở nhãn trạng thái (thanh quá mảnh)
        # bề ngang VỪA PHẢI: chia chỗ thừa với TÊN theo tỉ lệ 1:2, nở tới
        # 240px là dừng (dư dồn hết cho tên); panel hẹp co dần, tối thiểu 40px.
        bar.setMinimumWidth(40)
        bar.setMaximumWidth(240)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding,
                          QSizePolicy.Policy.Fixed)
        lay.addWidget(bar, 1)

        st = QLabel()
        st.setFont(self._st_font)
        # đo theo chuỗi DÀI NHẤT có thể hiện -> không bao giờ cụt chữ
        st.setFixedWidth(self._st_w_short if self._narrow else self._st_w_full)
        lay.addWidget(st)

        btn = QPushButton()
        btn.setFixedSize(self._btn_w, 24)
        btn.setStyleSheet("QPushButton{padding:2px 6px; font-size:12px;}")
        sp = btn.sizePolicy()
        sp.setRetainSizeWhenHidden(True)   # ẩn vẫn GIỮ CHỖ -> cột thẳng hàng
        btn.setSizePolicy(sp)
        lay.addWidget(btn)

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
        # màu thanh: lỗi=đỏ, xong=xanh dịu; ĐANG CHẠY/CHỜ = màu theo GIAI ĐOẠN
        # (phân tích=tím, cắt/xuất=xanh ngọc) -> nhìn màu biết ngay đang làm gì
        chunk = {"failed": DANGER, "done": SUCCESS}.get(
            j["status"], _phase_color(j["type"]))
        bar.setStyleSheet(
            f"QProgressBar{{background:{SURFACE}; border:none; border-radius:5px;}} "
            f"QProgressBar::chunk{{background:{chunk}; border-radius:5px;}}")
        # việc đã xong/hủy: MỜ BỚT tên (đỡ tranh chú ý với việc đang chạy)
        faded = j["status"] in ("done", "canceled", "skipped")
        row["name"].setStyleSheet(f"color:{MUTED if faded else row['col']};")
        msg = (j["message"] or j["error"] or "").strip()
        if j["status"] == "running":
            # chữ CỐ ĐỊNH "45% · Đang cắt"/"· Đang phân tích" (vừa khít cột,
            # KHÔNG cụt); bước chi tiết dài -> tooltip. Panel hẹp: chỉ "45%"
            # (màu tím/xanh ngọc vẫn nói đang ở giai đoạn nào).
            phase = (_RUN_EXPORT if j["type"] in _EXPORT_TYPES
                     else _RUN_ANALYZE)
            txt = f"{pct}%" if self._narrow else f"{pct}% · {phase}"
            color = _phase_color(j["type"])
        else:
            txt, color = _STATUS.get(j["status"], (j["status"], MUTED))
            if self._narrow and j["status"] == "failed":
                txt = "✕ Lỗi"           # vẫn gạch chân + bấm xem đầy đủ
        row["st"].setText(txt)
        if j["status"] == "failed":
            # LỖI: nhãn phải nói được VÌ SAO — tooltip đủ lỗi trên cả tên +
            # trạng thái, và CLICK vào nhãn trạng thái mở popup đầy đủ.
            err = self._fail_text(j)
            tip = "LỖI: " + err + "\n\n(Bấm vào nhãn '✕ Lỗi' để xem đầy đủ)"
            row["st"].setToolTip(tip)
            row["name"].setToolTip(row["name"].full_text() + "\n\n" + tip)
            row["st"].setCursor(Qt.CursorShape.PointingHandCursor)
            title = row["name"].full_text()
            row["st"].mousePressEvent = \
                lambda _e, t=title, m=err: self._show_error(t, m)
            row["st"].setStyleSheet(
                f"color:{color}; text-decoration:underline;")
        else:
            row["st"].setStyleSheet(f"color:{color};")
            # đang chạy: bước chi tiết ("Đang tách âm thanh...") nằm ở tooltip
            row["st"].setToolTip(msg if j["status"] == "running" and msg
                                 else txt)

    @staticmethod
    def _fail_text(j) -> str:
        """Ghép LÝ DO LỖI đầy đủ: error chính + thông báo bước cuối (nếu khác)."""
        err = (j["error"] or "").strip()
        last = (j["message"] or "").strip()
        if err and last and last not in err:
            return err + "\n\nBước cuối trước khi lỗi: " + last
        return err or last or "Không rõ nguyên nhân (thử bấm 'Thử lại')."

    def _show_error(self, title, err):
        """Popup lỗi ĐẦY ĐỦ khi user bấm vào nhãn '✕ Lỗi' của việc thất bại."""
        QMessageBox.warning(self, f"Việc thất bại — {title}", err)

    # ---- hành động ----
    def _cancel(self, i):
        self.state.pool.cancel(i)
        self.refresh()

    def _retry(self, i):
        self.state.pool.retry(i)
        self.refresh()
