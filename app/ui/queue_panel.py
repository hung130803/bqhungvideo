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
         "auto_recap": "Reup thuyết minh",
         "m1_export_clip": "Xuất clip",
         "thay_giong": "Thay giọng"}
# Nhãn NGẮN + icon theo GIAI ĐOẠN (hiện ở TRƯỚC để biết ngay đang làm gì)
_TYPE_TAG = {"auto": "🔍 Phân tích", "analyze": "🔍 Phân tích",
             "auto_mixed": "🔍 Mixed-Cut", "m1_mixed_cut": "🔍 Mixed-Cut",
             "auto_recap": "🎙 Thuyết minh",
             "m1_highlights": "🔍 Tìm clip", "m1_export_clip": "✂ Xuất",
             # KHÔNG EMOJI: máy nhân viên thiếu glyph là ra Ô ĐEN (v2.6.22).
             "thay_giong": "Thay giọng"}
_STATUS = {"running": ("Đang chạy", ACCENT), "pending": ("Đang chờ", MUTED),
           "done": ("✅ Xong", SUCCESS), "failed": ("✕ Lỗi · bấm xem", DANGER),
           "canceled": ("Đã hủy", MUTED), "skipped": ("Bỏ qua", MUTED)}
# MÀU THANH theo GIAI ĐOẠN: phân tích/AI = TÍM; cắt/xuất video = XANH NGỌC.
_PHASE_ANALYZE = "#A78BFA"      # phân tích + AI chọn clip
_PHASE_EXPORT = "#14B8A6"       # cắt + xuất video
_EXPORT_TYPES = {"m1_export_clip"}
# chữ giai đoạn khi ĐANG CHẠY (đặt sau %): "45% · Đang cắt"
_RUN_ANALYZE = "Đang phân tích"
_RUN_EXPORT = "Đang cắt"
_NARROW_PX = 520                # dưới cỡ này: trạng thái rút gọn "45%" / "✕ Lỗi"
#: TRẦN SỐ DÒNG vẽ trong bảng hàng đợi. Vì sao phải có (đo 06/08/2026, cảnh
#: 200 kênh / 900 job): vẽ 200 dòng -> 1 nhịp 246 ms trên nhịp 400 ms = 61%
#: thời gian máy chỉ để vẽ lại. Số TỔNG đã hiện ở các ô đếm phía trên nên
#: không mất thông tin; phần dư gộp thành 1 dòng "…còn N việc".
_MAX_CHAY = 24                  # việc đang chạy / đang chờ
_MAX_XONG = 12                  # việc đã xong / lỗi gần nhất
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


#: Khoá trong `payload` có thể chứa ĐƯỜNG DẪN video, xếp theo thứ tự ưu tiên.
#: `video` là khoá `jobs._thay_giong` đang dùng; hai khoá kia để job đời sau /
#: đường gọi khác vẫn hiện được tên chứ không rơi về "—".
_KHOA_DUONG = ("video", "src_path", "duong")


def _khoa_payload(j, khoa: tuple) -> str:
    """Giá trị chuỗi đầu tiên tìm được trong `payload` theo danh sách khoá.

    KHÔNG BAO GIỜ NÉM: đây là đường vẽ nhãn, payload hỏng thì mất cái tên chứ
    không được làm sập cả bảng hàng đợi.
    """
    import json
    try:
        p = j["payload"] if "payload" in j.keys() else ""
        d = json.loads(p) or {}
        if not isinstance(d, dict):
            return ""
        for k in khoa:
            v = str(d.get(k) or "").strip()
            if v:
                return v
    except (ValueError, TypeError, KeyError):
        pass
    return ""


def _ten_tu_payload(j) -> str:
    """Tên video (không đuôi) đọc từ `payload` — '' nếu không có."""
    import os
    v = _khoa_payload(j, _KHOA_DUONG)
    return os.path.splitext(os.path.basename(v))[0] if v else ""


def _job_name(j):
    """Nhãn: '<GIAI ĐOẠN> [Part N] · Kênh · Video' — hiện rõ loại việc + Part
    Ở TRƯỚC để user biết ngay đang làm gì cho video nào."""
    import os
    chan = j["chan_name"] if "chan_name" in j.keys() and j["chan_name"] else ""
    if not chan:
        chan = _khoa_payload(j, ("kenh",))     # job không gắn `projects`
    chan = chan or "—"
    vid = ""
    if "vid_path" in j.keys() and j["vid_path"]:
        vid = os.path.splitext(os.path.basename(j["vid_path"]))[0]
    if not vid:
        # JOB KHÔNG GẮN VỚI BẢNG `videos` -> `vid_path` RỖNG (LEFT JOIN trượt).
        # Đúng ca `thay_giong`: nó chạy trên FILE trong thư mục anh Hùng chọn,
        # không phải video trong DB. Trước đây dòng việc ra
        # `thay_giong · — · thay_giong` (lặp tên LOẠI việc, chỗ tên video thì
        # trống) nên chạy cả thư mục thì không biết dòng nào là video nào —
        # anh Hùng chụp màn hình đúng chỗ này. Tên video nằm trong payload.
        vid = _ten_tu_payload(j)
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
        self._name_font.setPixelSize(15)          # to hơn cho dễ đọc tên bước
        self._name_font.setWeight(QFont.Weight.DemiBold)
        self._st_font = QFont(self.font())
        self._st_font.setPixelSize(14)            # % + trạng thái rõ số, dễ nhìn
        self._st_font.setWeight(QFont.Weight.DemiBold)
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
        # GIẢI THÍCH CON SỐ 'đợi' + ƯỚC THỜI GIAN.
        # Anh Hùng 07/08/2026: "trc tôi chạy có 200 chờ mà tự nhiên con số tự
        # tăng k biết ở đâu lên 450". Không phải lỗi: MỖI video phân tích xong
        # sinh thêm ~3 việc XUẤT PART, nên số 'đợi' phải tăng khi phân tích đang
        # xong dần (đo nhật ký thật 06/08: 138 video nhận -> 449 việc chờ). Cái
        # sai là app không nói ra, để user tưởng nó hỏng.
        _wa, _we = int(c.get("wait_analyze", 0)), int(c.get("wait_export", 0))
        _ch = max(1, int(c.get("analyzing", 0)) + int(c.get("exporting", 0)))
        # nhịp thật đo được: phân tích ~2,5 phút/video · xuất ~1,2 phút/Part
        _phut = (_wa * 2.5 + _we * 1.2) / _ch
        _uoc = (f"~{_phut/60:.1f} giờ" if _phut >= 90 else f"~{_phut:.0f} phút")
        self.chip_wait["w"].setToolTip(
            f"Đang đợi {c['waiting']} việc — đợi phân tích {_wa} · đợi cắt "
            f"{_we}\n\nSỐ NÀY TĂNG LÀ BÌNH THƯỜNG: mỗi video phân tích xong "
            f"sinh thêm ~3 việc XUẤT PART.\nƯớc còn {_uoc} với "
            f"{_ch} việc chạy song song (tăng 'Luồng AI'/'Luồng cắt' ở cột "
            f"trái để nhanh hơn).")
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
        # Lấy RỘNG hơn + giữ NHIỀU job xong hơn: chạy 100 kênh xuất Part liên
        # tục, giới hạn 20 làm job "✅ Xong" bị đẩy mất → user tưởng chưa xong.
        # Chip tổng (✅ N xong) vẫn là con số chốt.
        # ── TRẦN SỐ DÒNG VẼ (đo 06/08/2026 khi anh Hùng báo "chạy hàng trăm
        # kênh cực kỳ đơ"): vẽ 200 dòng thì 1 nhịp mất 246 ms, mà nhịp là
        # 400 ms -> 61% thời gian máy chỉ để vẽ lại danh sách job. Không ai
        # đọc nổi 200 dòng; số TỔNG đã có ở các ô đếm. Chỉ vẽ phần user thực sự
        # nhìn, phần dư gộp thành 1 dòng "…còn N việc". Lấy 2 query RIÊNG để
        # việc "✅ Xong" không bị việc đang chạy chiếm hết chỗ (xem
        # services.list_jobs_top).
        active, recent = services.list_jobs_top(_MAX_CHAY, _MAX_XONG)
        _c = self._counts or {}
        _tong_chay = sum(int(_c.get(k, 0) or 0)
                         for k in ("analyzing", "exporting", "waiting"))
        n_an = max(0, _tong_chay - len(active))
        show = list(active) + list(recent)
        # ── NHỊP THÍCH ỨNG: ít việc -> 400 ms cho mượt mắt; nhiều việc -> giãn
        # ra, vì lúc đó mỗi nhịp tốn nhiều hơn mà user cũng chỉ cần thấy xu thế.
        nhip = 400 if len(show) <= 40 else 900
        if self.timer.isActive() and self.timer.interval() != nhip:
            self.timer.setInterval(nhip)
        sig = [(j["id"], j["status"]) for j in show]
        if sig != self._sig:            # tập việc/trạng thái đổi
            # CẬP NHẬT SAI KHÁC, KHÔNG đập cả danh sách. Bản cũ gọi _clear()
            # rồi dựng lại MỌI dòng (200 dòng ≈ 1.200 widget) -> đúng thứ làm
            # đơ. Cùng lỗi đã sửa cho danh sách clip ở studio_page
            # (_rows_in_place), lần này ở bảng hàng đợi.
            self._cap_nhat_sai_khac(show)
            self._sig = sig
        else:                           # chỉ % / thông báo đổi -> tại chỗ (mượt)
            for j in show:
                self._update(j)
        self._dong_con_lai(n_an)

    def _cap_nhat_sai_khac(self, show) -> None:
        """Thêm/bớt/xếp lại ĐÚNG dòng thay đổi; dòng cũ còn dùng thì GIỮ NGUYÊN
        widget (không tạo lại thanh tiến trình -> không nhấp nháy, không đơ)."""
        if not show:
            self._clear()
            self.empty = QLabel("Chưa có việc nào đang chạy.")
            self.empty.setStyleSheet(f"color:{MUTED}; font-size:14px;")
            self.lay.addWidget(self.empty)
            self.lay.addStretch(1)
            return
        if getattr(self, "empty", None) is not None:
            self.empty.setParent(None)
            self.empty = None
            while self.lay.count():             # bỏ stretch cũ
                it = self.lay.takeAt(0)
                if it.widget():
                    it.widget().setParent(None)
        con = {j["id"] for j in show}
        for jid in [k for k in self._rows if k not in con]:
            row = self._rows.pop(jid)
            self.lay.removeWidget(row["w"])
            row["w"].setParent(None)           # hết việc -> bỏ đúng dòng đó
        for i, j in enumerate(show):
            row = self._rows.get(j["id"])
            if row is None:
                row = self._make_row(j)
                self._rows[j["id"]] = row
                self.lay.insertWidget(i, row["w"])
            else:
                self._wire_btn(row["btn"], j)   # trạng thái đổi -> đổi nút
                self._update(j, row)
                if self.lay.indexOf(row["w"]) != i:
                    self.lay.removeWidget(row["w"])
                    self.lay.insertWidget(i, row["w"])
        if self.lay.itemAt(self.lay.count() - 1) is not None \
                and self.lay.itemAt(self.lay.count() - 1).widget() is not None:
            self.lay.addStretch(1)              # chỉ thêm khi chưa có

    def _dong_con_lai(self, n_an: int) -> None:
        """1 dòng chữ cuối: "…còn N việc nữa không hiện ở đây" — để user biết
        danh sách bị cắt trần chứ không tưởng app bỏ mất việc."""
        lb = getattr(self, "_lb_con", None)
        if not n_an:
            if lb is not None:
                lb.setParent(None)
                self._lb_con = None
            return
        txt = (f"… còn {n_an} việc nữa (xem số tổng ở các ô đếm phía trên) — "
               "ẩn bớt để app không bị đơ")
        if lb is None:
            lb = QLabel(txt)
            lb.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            self._lb_con = lb
            self.lay.addWidget(lb)
        else:
            lb.setText(txt)

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
        w.setFixedHeight(34)            # dòng cao hơn cho chữ to (15px) dễ đọc
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
        bar.setFixedHeight(12)          # thanh vừa phải, rõ nhưng không lấn
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
