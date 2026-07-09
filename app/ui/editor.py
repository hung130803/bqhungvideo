"""
Editor kiểu CapCut (mở từ nút "Chỉnh"):
- Khung 9:16 = NỀN (đen/trắng/mờ).
- KHỐI VIDEO: bấm chọn -> viền + nút kéo góc để phóng to/nhỏ, kéo để dời.
- Lớp chữ (cố định + Part) kéo-thả, cỡ/font/màu, nền bo góc.
- Trả về layout {video_rect:(cx,cy,scale), bg, layers:[...]} để áp cho mọi clip.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QGraphicsItem,
    QGraphicsLineItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsView, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSlider, QVBoxLayout,
    QWidget,
)

from app import services
from app.core.captions import CAPTION_PRESETS, NARR_SAME_LABEL, apply_case
from app.core.dubbing import LANG_LABELS as DUB_LANGS, VOICES as DUB_VOICES

# Cache danh sách giọng lồng tiếng ĐẦY ĐỦ theo ngôn ngữ (nạp 1 lần/phiên app;
# list_voices_for đã có cache file 7 ngày bên dưới nữa).
_DUB_VOICE_CACHE: dict[str, list[tuple[str, str]]] = {}

FW, FH = 348, 619          # khung xem trước TO hơn cho dễ nhìn (tỉ lệ 9:16)


class _NoWheelSlider(QSlider):
    """Thanh kéo KHÔNG đổi giá trị khi chỉ lăn chuột qua (phải bấm-kéo).
    Lăn chuột để CUỘN bảng thay vì lỡ tay đổi cỡ/độ rộng."""
    def wheelEvent(self, e):
        e.ignore()


class _NoWheelCombo(QComboBox):
    """Combo KHÔNG đổi lựa chọn khi lăn chuột qua.

    Co được (min width nhỏ) để KHÔNG đẩy nút cạnh nó bị xén chữ; ô hiển thị
    tự cắt '…' khi hẹp, còn POPUP thì luôn rộng đủ để đọc hết tên (vd tên
    giọng '⭐ Andrew — nam (US, đa ngữ)')."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        # co được: nhường chỗ cho nút cùng hàng thay vì xén nút
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(80)
        self.setMinimumContentsLength(6)   # ô hẹp vẫn hiện được vài ký tự
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)

    def wheelEvent(self, e):
        e.ignore()

    def showPopup(self):
        # popup rộng theo item DÀI NHẤT (không để tên bị cắt '…')
        fm = self.view().fontMetrics()
        w = 0
        for i in range(self.count()):
            w = max(w, fm.horizontalAdvance(self.itemText(i)))
        # + chỗ cho lề/scrollbar; không hẹp hơn chính combo
        self.view().setMinimumWidth(max(self.width(), w + 60))
        super().showPopup()


def _fit_button(btn, extra=26, minw=0):
    """Đặt bề rộng nút VỪA KHÍT chữ (theo fontMetrics) + KHÔNG cho co dưới mức
    đó -> nút không bao giờ bị xén 'Nghe thử' -> 'Nghe t'."""
    fm = btn.fontMetrics()
    w = fm.horizontalAdvance(btn.text()) + extra
    if minw:
        w = max(w, minw)
    btn.setMinimumWidth(w)
    btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return btn


_QFONT = {
    "Montserrat": ("Montserrat", True),
    "Be Vietnam đậm": ("Be Vietnam Pro", True),
    "Be Vietnam": ("Be Vietnam Pro", False),
    "Anton (to đậm)": ("Anton", False),
    "Bungee (TikTok)": ("Bungee", False),
    "Baloo 2 (tròn)": ("Baloo 2", False),
    "Oswald (cao)": ("Oswald", True),
    "Lexend (hiện đại)": ("Lexend", False),
    "Pacifico (viết tay)": ("Pacifico", False),
    "Lobster (viết tay)": ("Lobster", False),
    "Pattaya (viết tay)": ("Pattaya", False),
    "Arial": ("Arial", False), "Arial đậm": ("Arial", True),
    "Impact": ("Impact", False),
}


# Kiểu chữ HOA/thường cho MỌI phần chữ (nhãn, giá trị lưu layout). "" = giữ
# nguyên (mặc định). Khớp captions.apply_case.
_CASE_OPTS = [("Giữ nguyên", ""), ("HOA", "upper"),
              ("thường", "lower"), ("Hoa Đầu Từ", "title")]


def _case_combo(tooltip=""):
    """Combo 4 lựa chọn kiểu chữ hoa dùng chung cho từng phần chữ."""
    cb = _NoWheelCombo()
    for label, val in _CASE_OPTS:
        cb.addItem(label, val)
    if tooltip:
        cb.setToolTip(tooltip)
    return cb


# Bề rộng nhãn CỐ ĐỊNH cho 2 khu Phụ đề / Chữ AI -> nhãn thẳng cột, control
# xếp đều, 2 khu trông ĐỐI XỨNG.
_LBL_W = 76


def _frow(label, *widgets, stretch_at=0):
    """1 hàng 'Nhãn: [control...]' — nhãn rộng cố định để thẳng cột giữa 2 khu.
    stretch_at = index widget được giãn (mặc định widget đầu)."""
    row = QHBoxLayout()
    lb = QLabel(label); lb.setFixedWidth(_LBL_W)
    row.addWidget(lb)
    for i, w in enumerate(widgets):
        row.addWidget(w, 1 if i == stretch_at else 0)
    return row


# Màu CHỮ AI KỂ (Style Narrate) — (nhãn, hex). Vàng #FFD966 mặc định (đầu list).
_NARR_COLORS = [
    ("Vàng", "#FFD966"), ("Trắng", "#FFFFFF"), ("Xanh ngọc", "#16E0FF"),
    ("Hồng", "#FF5CA8"), ("Cam", "#FF9F1C"),
]
_NARR_COLOR_DEFAULT = "#FFD966"


def _qfont(name, px):
    # có trong bảng -> dùng (family,bold); không -> coi name LÀ family (font đã nạp)
    fam, bold = _QFONT.get(name, (name or "Arial", False))
    f = QFont(fam)
    f.setBold(bold)
    f.setPixelSize(max(6, int(px)))
    return f


def _wrap(text, fm, maxw):
    """Tự xuống dòng theo chiều rộng tối đa maxw (px). Từ quá dài thì chẻ ký tự."""
    out = []
    for para in (text or "").split("\n"):
        cur = ""
        for wd in para.split(" "):
            # từ dài hơn cả dòng -> chẻ theo ký tự cho khỏi tràn ngang
            while fm.horizontalAdvance(wd) > maxw and len(wd) > 1:
                cut = len(wd)
                while cut > 1 and fm.horizontalAdvance(wd[:cut]) > maxw:
                    cut -= 1
                if cur:
                    out.append(cur); cur = ""
                out.append(wd[:cut]); wd = wd[cut:]
            test = (cur + " " + wd).strip()
            if not cur or fm.horizontalAdvance(test) <= maxw:
                cur = test
            else:
                out.append(cur)
                cur = wd
        out.append(cur)
    return out or [""]


def _draw_text_path(p, path, color, outline_w, outline_color="#000000",
                    preview=False):
    """Vẽ chữ: viền màu TRƯỚC (nếu có), tô màu chữ ĐÈ lên.
    outline_w <= 0 -> KHÔNG viền (chỉ tô màu chữ).

    outline_w là bề dày viền (px) — TRÙNG semantics với lúc xuất (.ass Outline).

    preview=True (chỉ khung XEM TRƯỚC, KHÔNG áp cho render_overlay_png xuất
    thật): QPen vẽ NỬA trong / NỬA ngoài nét chữ nên phần LỘ RA chỉ ~½ bề dày
    -> nhân đôi để viền trông DÀY đúng như mắt trông đợi + phủ hẳn ra ngoài như
    .ass. Đồng thời ép bề dày TỐI THIỂU >=1px cho MỌI giá trị > 0 -> kéo mảnh
    tí vẫn HIỆN, không bị 'nuốt' như ngưỡng 0.6px cũ (viền 0.25-0.5px im lặng
    biến mất khiến user tưởng chỉnh không ăn). Xuất thật (preview=False) giữ
    NGUYÊN hành vi cũ (ngưỡng >=0.6px, bề dày = outline_w) để PNG overlay không
    đổi 1 pixel."""
    draw = (outline_w > 0) if preview else (outline_w and outline_w >= 0.6)
    if draw:
        pen_w = max(1.0, outline_w * 2.0) if preview else outline_w
        pen = QPen(QColor(outline_color), pen_w)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawPath(path)


def _caption_box_data(preset_name, *, size, font, ny, color="", outline="",
                      ow=0.0, italic=False):
    """Dựng dict style cho ô xem trước (cap_box / narr_box) SÁT với .ass mà
    build_ass sinh ra, từ 1 preset + override của user. Trả dict dùng cho
    _TextBox.apply().

    Ánh xạ (khớp build_ass):
      - màu chữ  = color (user) hoặc preset['color'] (mode active -> 'rest').
      - viền     = outline/ow (user) hoặc preset['outline']/'ow'.
                   ow là TỈ LỆ chiều cao chữ (như 'ow' preset); 0 -> theo preset.
      - preset box=True -> NỀN HỘP sau chữ (BorderStyle=3): bg=True, bg_color=
                   box_color, viền chữ TẮT (như build_ass đặt outline=box màu +
                   ow=0.20 làm bề dày hộp — ở preview thể hiện bằng nền hộp).
      - preset glow -> viền = màu glow (neon) nếu user không đặt màu viền riêng.
      - preset không box -> KHÔNG nền hộp (chỉ viền chữ).
    """
    p = CAPTION_PRESETS.get(preset_name) or {}
    # màu chữ
    if color:
        col = color
    elif p.get("mode") == "active":
        col = p.get("rest", "#FFFFFF")
    else:
        col = p.get("color", "#FFFFFF")
    is_box = bool(p.get("box"))
    # viền chữ: user ow (>0) ghi đè; else theo preset ow. glow -> màu viền = glow.
    if is_box:
        # nền hộp -> chữ KHÔNG viền (bề dày hộp thể hiện bằng nền), trừ khi
        # user tự đặt độ dày viền.
        ow_frac = float(ow) if (ow and ow > 0) else 0.0
        oc = outline or p.get("outline", "#000000")
    else:
        ow_frac = float(ow) if (ow and ow > 0) else float(p.get("ow", 0.10))
        if outline:
            oc = outline
        elif p.get("glow"):
            oc = p["glow"]
        else:
            oc = p.get("outline", "#000000")
    d = {"size": float(size), "font": font, "color": col,
         "outline": ow_frac, "outline_color": oc,
         "nx": 0.5, "ny": float(ny), "italic": bool(italic)}
    if is_box:
        d.update({"bg": True, "bg_color": p.get("box_color", "#000000"),
                  "bg_alpha": 0.9, "radius": 12, "padx": 0.5, "pady": 0.35})
    else:
        d["bg"] = False
    return d


def render_overlay_png(layers, part_no, out_w, out_h, path, title="",
                       title_vi="", video_px=None, logo=None,
                       part_case="", hook_case="") -> bool:
    """Vẽ tất cả lớp chữ ra PNG trong suốt (dùng khi xuất). Trả True nếu có chữ.
    Placeholder: {n}->số Part, {title}->tiêu đề (Anh) gắn video, {title_vi}->Việt.
    Chữ quá dài TỰ CO NHỎ + bị CLAMP để KHÔNG bao giờ tràn ra ngoài khung.
    video_px=(vx,vy,vw,vh): vùng KHỐI VIDEO -> chữ bị đẩy ra dải nền, KHÔNG đè video.
    part_case: kiểu chữ hoa cho lớp Part ("upper"/"lower"/"title"/""=giữ).
    hook_case: kiểu chữ hoa cho lớp CHỮ (tiêu đề/hook/cố định) — mọi lớp không
    phải Part. Áp lên CHỮ HIỂN THỊ (sau khi thay placeholder), KHÔNG đổi vị trí."""
    from app.core.captions import apply_case
    drawn = False
    img = QImage(out_w, out_h, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    margin = out_w * 0.04
    gap = out_w * 0.015
    for d in layers:
        raw = d.get("text", "")
        text = (raw.replace("{n}", str(part_no))
                   .replace("{title_vi}", title_vi or "")
                   .replace("{title}", title or ""))
        # lớp Part kiểu cũ không có placeholder -> nối số vào sau
        if (d.get("is_part") and "{n}" not in raw and "{title}" not in raw
                and "{title_vi}" not in raw):
            text = f'{raw} {part_no}'.strip()
        text = text.strip()
        if not text:
            continue
        # KIỂU CHỮ HOA cho phần chữ này: Part -> part_case; lớp khác (tiêu đề/
        # hook/cố định) -> hook_case. Áp lên CHỮ HIỂN THỊ, KHÔNG đổi vị trí/cỡ.
        _lcase = part_case if d.get("is_part") else hook_case
        if _lcase:
            text = apply_case(text, _lcase)
        drawn = True
        # --- chọn DẢI NỀN cho phép (trên/dưới video) để chữ KHÔNG đè khung video ---
        ay0, ay1 = margin, out_h - margin
        if video_px:
            vx, vy, vw, vh = video_px
            fy0, fy1 = max(margin, vy), min(out_h - margin, vy + vh)
            top_h, bot_h = (fy0 - gap) - margin, (out_h - margin) - (fy1 + gap)
            cyt = d["ny"] * out_h
            if cyt <= (fy0 + fy1) / 2 and top_h > 24:      # dự kiến ở trên + dải đủ
                ay0, ay1 = margin, fy0 - gap
            elif cyt > (fy0 + fy1) / 2 and bot_h > 24:     # dự kiến ở dưới
                ay0, ay1 = fy1 + gap, out_h - margin
            elif top_h >= bot_h and top_h > 24:            # ép sang dải lớn hơn
                ay0, ay1 = margin, fy0 - gap
            elif bot_h > 24:
                ay0, ay1 = fy1 + gap, out_h - margin
            # cả 2 dải quá nhỏ -> giữ cả khung (video phủ kín, không tránh được)
        avail_h = max(20.0, ay1 - ay0)
        # --- TỰ CO cỡ chữ đến khi hộp nằm gọn trong DẢI cho phép (chống tràn/đè) ---
        base = max(8.0, d["size"] * out_h)
        size, f, fm, lines, lh, bw, bh, px, py = base, None, None, [], 0, 0, 0, 0, 0
        for _ in range(20):
            f = _qfont(d["font"], size)
            fm = QFontMetricsF(f)
            if d.get("bg"):
                base_pad = max(6.0, size * 0.25)
                px = base_pad + d.get("padx", 0.83) * size   # nền RỘNG thêm
                py = base_pad + d.get("pady", 0.83) * size   # nền CAO thêm
            else:
                px = py = 0.0
            lines = _wrap(text, fm, out_w - 2 * margin - 2 * px)
            lh = fm.height()
            longest = max((fm.horizontalAdvance(ln) for ln in lines), default=0)
            bw = longest + px * 2
            bh = lh * len(lines) + py * 2
            if (bw <= out_w - 2 * margin and bh <= avail_h) or size <= base * 0.33:
                break
            size *= 0.9
        # vị trí theo tâm; CLAMP trong DẢI cho phép (an toàn tuyệt đối)
        x0 = min(max(d["nx"] * out_w - bw / 2, margin), max(margin, out_w - margin - bw))
        y0 = min(max(d["ny"] * out_h - bh / 2, ay0), max(ay0, ay1 - bh))
        if d.get("bg"):
            r = d.get("radius", 0) / 100 * (bh / 2)
            bp = QPainterPath()
            bp.addRoundedRect(QRectF(x0, y0, bw, bh), r, r)
            col = QColor(d.get("bg_color", "#000000"))
            col.setAlpha(int(max(0.0, min(1.0, d.get("bg_alpha", 0.75))) * 255))
            p.fillPath(bp, col)
        tp = QPainterPath()
        for i, ln in enumerate(lines):
            lw = fm.horizontalAdvance(ln)
            tp.addText(x0 + (bw - lw) / 2, y0 + py + fm.ascent() + i * lh, f, ln)
        _draw_text_path(p, tp, d["color"], d.get("outline", 0.12) * size,
                        d.get("outline_color", "#000000"))
    # ---- LOGO KÊNH (watermark): logo={"path","pos","size","opacity"} ----
    # pos: tl|tr|bl|br; size: % chiều rộng khung (0..1); opacity 0..1
    if logo and logo.get("path"):
        lp = QPixmap(str(logo["path"]))
        if not lp.isNull():
            lw = max(24, int(float(logo.get("size", 0.14)) * out_w))
            lp = lp.scaledToWidth(lw, Qt.TransformationMode.SmoothTransformation)
            m = int(out_w * 0.03)
            pos = logo.get("pos", "tr")
            x = m if "l" in pos else out_w - m - lp.width()
            y = m if "t" in pos else out_h - m - lp.height()
            p.setOpacity(max(0.05, min(1.0, float(logo.get("opacity", 0.9)))))
            p.drawPixmap(x, y, lp)
            p.setOpacity(1.0)
            drawn = True
    p.end()
    if drawn:
        img.save(str(path), "PNG")
    return drawn


# ============================================================
class _VideoBox(QGraphicsItem):
    """Khối video đặt trên nền; kéo dời, kéo góc phóng to (khóa tỉ lệ gốc)."""
    HS = 16

    def __init__(self, on_guide=None):
        super().__init__()
        self.on_guide = on_guide
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                      | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(2)
        self.pm = QPixmap()
        self.disp = QPixmap()      # ảnh đã thu nhỏ sẵn để vẽ NHANH
        self.aspect = 16 / 9
        self.w = FW
        self.h = FW * self.aspect
        self._resizing = False
        self._dragging = False

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange \
                and self._dragging:
            x, y = value.x(), value.y()
            snap = 9
            v = abs(x + self.w / 2 - FW / 2) < snap
            if v:
                x = FW / 2 - self.w / 2
            h = abs(y + self.h / 2 - FH / 2) < snap
            if h:
                y = FH / 2 - self.h / 2
            if self.on_guide:
                self.on_guide(v, h)
            return QPointF(x, y)
        return super().itemChange(change, value)

    def set_pixmap(self, pm):
        self.pm = pm
        if not pm.isNull():
            self.aspect = pm.height() / pm.width()
            self.h = self.w * self.aspect
            # thu nhỏ sẵn (≤3x bề rộng khung) -> vẽ nhanh mà vẫn NÉT khi
            # khung xem trước được phóng to trên màn rộng
            cap = int(FW * 3)
            self.disp = (pm.scaledToWidth(cap, Qt.TransformationMode.SmoothTransformation)
                         if pm.width() > cap else pm)
            self.prepareGeometryChange()
            self.update()

    def set_rect(self, cx, cy, scale_w):
        self.w = max(20, scale_w * FW)
        self.h = self.w * self.aspect
        self.prepareGeometryChange()
        self.setPos(cx * FW - self.w / 2, cy * FH - self.h / 2)

    def boundingRect(self):
        return QRectF(-2, -2, self.w + self.HS, self.h + self.HS)

    def _handle(self):
        s = self.HS
        return QRectF(self.w - s / 2, self.h - s / 2, s, s)

    def paint(self, p, opt, widget=None):
        src = self.disp if not self.disp.isNull() else self.pm
        if not src.isNull():
            # đang resize -> vẽ NHANH (fast), nghỉ tay -> mượt (smooth)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,
                            not self._resizing)
            p.drawPixmap(QRectF(0, 0, self.w, self.h), src, QRectF(src.rect()))
        else:
            p.fillRect(QRectF(0, 0, self.w, self.h), QColor("#333"))
        sel = self.isSelected()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#6E8BFF"), 2 if sel else 1,
                      Qt.PenStyle.DashLine if sel else Qt.PenStyle.SolidLine))
        p.drawRect(QRectF(0, 0, self.w, self.h))
        if sel:
            p.setPen(QPen(QColor("#6E8BFF"), 1)); p.setBrush(QColor("white"))
            p.drawRect(self._handle())

    def mousePressEvent(self, e):
        if self.isSelected() and self._handle().contains(e.pos()):
            self._resizing = True
            self._sx = e.scenePos().x()
            self._sw = self.w
            e.accept(); return
        self._dragging = True
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            cx, cy = self.x() + self.w / 2, self.y() + self.h / 2
            self.w = max(40, self._sw + (e.scenePos().x() - self._sx))
            self.h = self.w * self.aspect
            self.prepareGeometryChange()
            self.setPos(cx - self.w / 2, cy - self.h / 2)
            self.update(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        # PHẢI reset _dragging: nếu không, lần setPos theo CODE sau đó (áp mẫu)
        # bị itemChange tưởng đang kéo tay -> snap lệch vị trí + vạch căn kẹt.
        self._dragging = False
        was = self._resizing
        self._resizing = False
        if was:
            self.update()          # vẽ lại bản mượt sau khi thả
        if self.on_guide:
            self.on_guide(False, False)
        super().mouseReleaseEvent(e)

    def rect_norm(self):
        return (round((self.x() + self.w / 2) / FW, 4),
                round((self.y() + self.h / 2) / FH, 4),
                round(self.w / FW, 4))


class _TextBox(QGraphicsItem):
    HS = 14

    def __init__(self, lid, on_resize=None, on_guide=None, on_select=None):
        super().__init__()
        self.lid = lid
        self.on_resize = on_resize
        self.on_guide = on_guide
        self.on_select = on_select   # bấm chọn hộp -> cuộn panel phải tới nhóm
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                      | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(10)
        self.d = {}
        self.disp = ""
        self.px = 0.07 * FH
        self.w = self.h = self.pad = self.padx = self.pady = 0.0
        self._resizing = False
        self._dragging = False

    def apply(self, data, preview):
        cx, cy = self.x() + self.w / 2, self.y() + self.h / 2
        first = not self.d
        self.d = data
        self.disp = preview or ""
        self.px = max(8.0, float(data.get("size", 0.07)) * FH)
        self._recalc()
        self.setVisible(bool(self.disp))
        if first:
            cx, cy = data.get("nx", 0.5) * FW, data.get("ny", 0.5) * FH
        self.setPos(cx - self.w / 2, cy - self.h / 2)
        self.update()   # BẮT BUỘC vẽ lại (cache thiết bị không tự đổi khi chỉ đổi màu/bo/font)

    def _font(self):
        f = _qfont(self.d.get("font", "Arial"), self.px)
        if self.d.get("italic"):
            f.setItalic(True)
        return f

    def _recalc(self):
        self.prepareGeometryChange()
        fm = QFontMetricsF(self._font())
        if self.d.get("bg"):
            base_pad = max(4.0, self.px * 0.25)
            self.padx = base_pad + self.d.get("padx", 0.83) * self.px
            self.pady = base_pad + self.d.get("pady", 0.83) * self.px
        else:
            self.padx = self.pady = 0.0
        maxw = FW * 0.92 - 2 * self.padx
        self.lines = _wrap(self.disp or " ", fm, maxw)
        self.line_h = fm.height()
        self.asc = fm.ascent()
        longest = max((fm.horizontalAdvance(ln) for ln in self.lines), default=0)
        self.w = longest + 2 * self.padx
        self.h = self.line_h * len(self.lines) + 2 * self.pady

    def boundingRect(self):
        return QRectF(-2, -2, self.w + self.HS, self.h + self.HS)

    def _handle(self):
        s = self.HS
        return QRectF(self.w - s / 2, self.h - s / 2, s, s)

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.d.get("bg"):
            r = self.d.get("radius", 0) / 100 * (self.h / 2)
            bp = QPainterPath(); bp.addRoundedRect(QRectF(0, 0, self.w, self.h), r, r)
            col = QColor(self.d.get("bg_color", "#000000"))
            col.setAlpha(int(max(0.0, min(1.0, self.d.get("bg_alpha", 0.75))) * 255))
            p.fillPath(bp, col)
        f = self._font(); fm = QFontMetricsF(f)
        tp = QPainterPath()
        for i, ln in enumerate(self.lines):
            lw = fm.horizontalAdvance(ln)
            x = (self.w - lw) / 2  # căn giữa mỗi dòng trong hộp
            y = self.pady + self.asc + i * self.line_h
            tp.addText(x, y, f, ln)
        _draw_text_path(p, tp, self.d.get("color", "#FFFFFF"),
                        self.d.get("outline", 0.12) * self.px,
                        self.d.get("outline_color", "#000000"), preview=True)
        if self.isSelected():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#6E8BFF"), 1.5, Qt.PenStyle.DashLine))
            p.drawRect(QRectF(0, 0, self.w, self.h))
            p.setPen(QPen(QColor("#6E8BFF"), 1)); p.setBrush(QColor("white"))
            p.drawRect(self._handle())

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # giữ hộp chữ NẰM GỌN trong khung (không cho kéo tràn ra ngoài)
            x = max(0.0, min(max(0.0, FW - self.w), value.x()))
            y = max(0.0, min(max(0.0, FH - self.h), value.y()))
            if self._dragging:  # chỉ snap + hiện vạch khi đang KÉO tay
                snap = 9
                v = abs(x + self.w / 2 - FW / 2) < snap
                if v:
                    x = FW / 2 - self.w / 2
                h = abs(y + self.h / 2 - FH / 2) < snap
                if h:
                    y = FH / 2 - self.h / 2
                if self.on_guide:
                    self.on_guide(v, h)
            return QPointF(x, y)
        return super().itemChange(change, value)

    def mousePressEvent(self, e):
        # BẤM chọn hộp -> báo editor cuộn panel phải tới nhóm chỉnh của hộp này
        # (làm TRƯỚC khi vào nhánh resize/drag để bấm đâu cũng nhảy; KHÔNG chặn
        # sự kiện nên kéo-thả/resize vẫn chạy y như cũ).
        if self.on_select:
            self.on_select(self.lid)
        if self.isSelected() and self._handle().contains(e.pos()):
            self._resizing = True; self._sy = e.scenePos().y(); self._spx = self.px
            e.accept(); return
        self._dragging = True
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            cx, cy = self.x() + self.w / 2, self.y() + self.h / 2
            self.px = max(8.0, self._spx + (e.scenePos().y() - self._sy))
            self._recalc(); self.setPos(cx - self.w / 2, cy - self.h / 2)
            self.update(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        if self.on_guide:
            self.on_guide(False, False)
        if self._resizing:
            self._resizing = False
            if self.on_resize:
                self.on_resize(self.lid, self.px / FH)
            e.accept(); return
        super().mouseReleaseEvent(e)

    def export_data(self):
        return {**self.d, "size": round(self.px / FH, 4),
                "nx": round((self.x() + self.w / 2) / FW, 4),
                "ny": round((self.y() + self.h / 2) / FH, 4)}


class EditorCanvas(QGraphicsView):
    def __init__(self, on_resize=None, on_select=None):
        super().__init__()
        self.on_resize = on_resize
        # bấm chọn 1 hộp chữ -> editor cuộn panel phải tới nhóm chỉnh tương ứng
        self.on_select = on_select
        # KHÔNG khóa cỡ: view GIÃN theo chỗ trống của dialog; khung 9:16 tự
        # phóng to bằng fitInView (tọa độ scene FW×FH giữ nguyên -> logic
        # kéo/thả, snap, lưu layout KHÔNG đổi).
        self.setMinimumSize(420, 620)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # khung NHỎ -> vẽ lại NGUYÊN khung mỗi lần (đơn giản, không tính vùng,
        # không cache item -> kéo mượt + xem trước LUÔN cập nhật theo thanh chỉnh)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setOptimizationFlag(
            QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.scene = QGraphicsScene(0, 0, FW, FH)
        self.setScene(self.scene)
        # GỐC CLIP: mọi item nội dung là CON của khung 9:16 này -> phần tràn ra
        # ngoài khung bị CẮT (trước đây view = đúng cỡ khung nên viewport tự cắt;
        # sang fitInView view TO hơn khung -> nền mờ/video tràn sẽ lộ ra nếu
        # không clip).
        self.clip_root = QGraphicsRectItem(0, 0, FW, FH)
        self.clip_root.setPen(QPen(Qt.GlobalColor.transparent))
        self.clip_root.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.clip_root.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        self.scene.addItem(self.clip_root)
        self.bg_solid = QGraphicsRectItem(0, 0, FW, FH)
        self.bg_solid.setPen(QPen(Qt.GlobalColor.transparent))
        self.bg_solid.setZValue(0)
        self.bg_solid.setParentItem(self.clip_root)
        self.bg_blur = QGraphicsPixmapItem(); self.bg_blur.setZValue(0)
        self.bg_blur.setCacheMode(
            QGraphicsPixmapItem.CacheMode.DeviceCoordinateCache)  # nền tĩnh -> cache
        self.bg_blur.setParentItem(self.clip_root)
        self.vbox = _VideoBox(on_guide=self._set_guides)
        self.vbox.setParentItem(self.clip_root)
        border = QGraphicsRectItem(0, 0, FW, FH)
        border.setPen(QPen(QColor("#3b82f6"), 2)); border.setZValue(30)
        self.scene.addItem(border)          # viền nằm NGOÀI clip -> không bị cắt nửa nét
        # vạch căn giữa (snap guide) — ẩn mặc định
        gpen = QPen(QColor("#FF3DAE"), 2, Qt.PenStyle.DashLine)
        self.gv = QGraphicsLineItem(FW / 2, 0, FW / 2, FH)
        self.gh = QGraphicsLineItem(0, FH / 2, FW, FH / 2)
        for g in (self.gv, self.gh):
            g.setPen(gpen); g.setZValue(40); g.setVisible(False)
            g.setParentItem(self.clip_root)
        self.texts: dict[int, _TextBox] = {}
        # ô PHỤ ĐỀ kéo-thả (chỉ để chọn VỊ TRÍ; không phải lớp chữ overlay)
        self.cap_box = _TextBox(-99, on_guide=self._set_guides,
                                on_select=self._sel)
        self.cap_box.apply({"size": 0.045, "font": "Montserrat", "color": "#FFFF66",
                            "bg": True, "bg_color": "#000000", "radius": 30,
                            "nx": 0.5, "ny": 0.78}, "Phụ đề chạy chữ")
        self.cap_box.setParentItem(self.clip_root)
        # ô HOOK (câu giật tít vàng to ở ĐẦU clip) — chỉ để XEM TRƯỚC, ẩn mặc định
        self.hook_box = _TextBox(-98, on_guide=self._set_guides,
                                 on_select=self._sel)
        self.hook_box.apply({"size": 0.072, "font": "Anton", "color": "#FFD83D",
                             "bg": True, "bg_color": "#000000", "radius": 30,
                             "bg_alpha": 0.45, "nx": 0.5, "ny": 0.10},
                            "HOOK GIẬT TÍT")
        self.hook_box.setVisible(False)
        self.hook_box.setParentItem(self.clip_root)
        # ô CHỮ AI KỂ (phụ đề đoạn AI thuyết minh — recap) kéo-thả chọn VỊ TRÍ
        # DỌC; chỉ XEM TRƯỚC, ẩn mặc định (chỉ hiện khi user bật ở nhóm Chữ AI kể)
        self.narr_box = _TextBox(-97, on_guide=self._set_guides,
                                 on_select=self._sel)
        self.narr_box.apply({"size": 0.045, "font": "Montserrat",
                             "color": "#FFD966", "bg": True, "bg_color": "#000000",
                             "radius": 30, "nx": 0.5, "ny": 0.62},
                            "Chữ AI kể")
        self.narr_box.setVisible(False)
        self.narr_box.setParentItem(self.clip_root)
        self.bg = "blur"
        self._frame = QPixmap()

    def _fit(self):
        """Phóng khung 9:16 chiếm gần hết chỗ view đang có (giữ tỉ lệ)."""
        self.fitInView(QRectF(0, 0, FW, FH), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def showEvent(self, e):
        super().showEvent(e)
        self._fit()

    def show_hook(self, on):
        """Hiện/ẩn ô HOOK xem trước ở đầu clip (khớp với lúc xuất)."""
        self.hook_box.setVisible(bool(on))

    def set_hook_geom(self, nx=0.5, ny=0.10, size=0.0):
        """Đặt vị trí/cỡ ô HOOK theo layout đã lưu (nx=tâm ngang, ny=ĐỈNH ô
        — khớp neo an8 lúc render; size=cỡ chữ theo tỉ lệ chiều cao)."""
        b = self.hook_box
        if size and size > 0:
            d = dict(b.d); d["size"] = float(size)
            b.apply(d, b.disp)
        b.setPos(float(nx) * FW - b.w / 2, max(0.0, float(ny)) * FH)

    def hook_geom(self):
        """Vị trí/cỡ ô HOOK hiện tại để LƯU vào mẫu (trước đây không lưu ->
        kéo xong mở lại bị reset)."""
        b = self.hook_box
        return {"hook_nx": round((b.x() + b.w / 2) / FW, 4),
                "hook_ny": round(max(0.0, min(1.0, b.y() / FH)), 4),
                "hook_size": round(b.px / FH, 4)}

    def set_cap_top(self, ny):
        # đặt ĐỈNH ô phụ đề tại ny (khớp neo an8 lúc render); ngang căn giữa
        self.cap_box.setPos(FW / 2 - self.cap_box.w / 2, max(0.0, ny) * FH)

    def cap_ny(self):
        # đỉnh khối chữ -> khớp với neo an8 lúc render
        return max(0.0, min(1.0, self.cap_box.y() / FH))

    def show_cap(self, on):
        self.cap_box.setVisible(on)

    def show_narr(self, on):
        self.narr_box.setVisible(bool(on))

    def set_narr_geom(self, ny=0.62, size=0.0):
        """Đặt vị trí dọc (đỉnh ô, khớp neo an8 lúc render) + cỡ ô CHỮ AI KỂ
        theo layout đã lưu; ngang căn giữa."""
        b = self.narr_box
        if size and size > 0:
            d = dict(b.d); d["size"] = float(size)
            b.apply(d, b.disp)
        b.setPos(FW / 2 - b.w / 2, max(0.0, float(ny)) * FH)

    def narr_geom(self):
        """Vị trí dọc + cỡ ô CHỮ AI KỂ hiện tại để LƯU vào mẫu."""
        b = self.narr_box
        return {"narr_ny": round(max(0.0, min(1.0, b.y() / FH)), 4),
                "narr_size": round(b.px / FH, 4)}

    def set_narr_style(self, color=None, size=None):
        """Cập nhật MÀU / CỠ ô CHỮ AI KỂ xem trước (giữ vị trí dọc đang kéo)."""
        b = self.narr_box
        d = dict(b.d)
        if color:
            d["color"] = color
        ny = b.y() / FH
        if size and size > 0:
            d["size"] = float(size)
        b.apply(d, b.disp)
        b.setPos(FW / 2 - b.w / 2, max(0.0, ny) * FH)

    def _set_guides(self, v, h):
        self.gv.setVisible(v)
        self.gh.setVisible(h)

    def _sel(self, lid):
        # cầu nối: mọi _TextBox gọi vào đây khi được bấm -> chuyển cho editor
        # (đặt sau khi dialog gán self.on_select) để cuộn panel phải tới nhóm.
        if self.on_select:
            self.on_select(lid)

    def load_frame(self, path):
        pm = QPixmap(path)
        if pm.isNull():
            return
        self._frame = pm
        self.vbox.set_pixmap(pm)
        # nền mờ = ảnh phủ kín + tối
        cover = pm.scaled(FW, FH, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                          Qt.TransformationMode.SmoothTransformation)
        dark = QPixmap(cover.size())
        dark.fill(QColor(0, 0, 0, 0))
        pnt = QPainter(dark); pnt.drawPixmap(0, 0, cover)
        pnt.fillRect(dark.rect(), QColor(0, 0, 0, 110)); pnt.end()
        self.bg_blur.setPixmap(dark)
        self.bg_blur.setPos((FW - cover.width()) / 2, (FH - cover.height()) / 2)
        self.set_bg(self.bg)

    def set_bg(self, mode):
        self.bg = mode
        if mode == "blur":
            self.bg_blur.setVisible(True); self.bg_solid.setVisible(False)
        else:
            self.bg_blur.setVisible(False); self.bg_solid.setVisible(True)
            self.bg_solid.setBrush(QBrush(QColor("white" if mode == "white" else "black")))

    def upsert_text(self, lid, data, preview):
        box = self.texts.get(lid)
        if box is None:
            box = _TextBox(lid, on_resize=self.on_resize, on_guide=self._set_guides,
                           on_select=self._sel)
            box.setParentItem(self.clip_root); self.texts[lid] = box
        box.apply(data, preview)

    def remove_text(self, lid):
        box = self.texts.pop(lid, None)
        if box:
            self.scene.removeItem(box)

    def set_text_center(self, lid, nx, ny):
        box = self.texts.get(lid)
        if box:
            box.setPos(nx * FW - box.w / 2, ny * FH - box.h / 2)

    def get_layout(self, text_layers):
        return {"video_rect": self.vbox.rect_norm(), "bg": self.bg,
                "layers": text_layers}


class _LayerRow(QWidget):
    def __init__(self, lid, on_change, on_remove, is_part=False):
        super().__init__()
        self.lid = lid; self.on_change = on_change; self.is_part = is_part
        self.color = "#FFFFFF"; self.bg_color = "#000000"
        self.outline_color = "#000000"
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Part = viền xanh dương, chữ thường = viền hồng (khớp màu nhóm Lớp chữ)
        edge = "110,139,255" if is_part else "244,114,182"
        self.setStyleSheet(
            f"_LayerRow{{background:#1d1d25; border:1px solid rgba({edge},0.5);"
            f"border-left:4px solid rgb({edge}); border-radius:10px;}}")
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(6)
        r1 = QHBoxLayout()
        lbl = QLabel(f"<b>{'Part' if is_part else 'Chữ'}</b>"); lbl.setFixedWidth(34)
        r1.addWidget(lbl)
        self.text = QLineEdit("Part {n}" if is_part else "")
        self.text.setPlaceholderText("Part {n}" if is_part else "Nhập chữ...")
        r1.addWidget(self.text, 1)
        rm = QPushButton("✕"); rm.setFixedWidth(28); rm.setProperty("danger", True)
        rm.clicked.connect(lambda: on_remove(self.lid)); r1.addWidget(rm)
        lay.addLayout(r1)
        def _lb(t, w=58):
            x = QLabel(t); x.setFixedWidth(w); return x

        # r2: Cỡ chữ + kiểu chữ + MÀU CHỮ
        r2 = QHBoxLayout(); r2.addWidget(_lb("Cỡ chữ"))
        self.size = _NoWheelSlider(Qt.Orientation.Horizontal); self.size.setRange(3, 18)
        self.size.setValue(7); r2.addWidget(self.size, 1)
        self.font = _NoWheelCombo()
        for f in _QFONT:               # danh sách font khớp với cách render overlay
            self.font.addItem(f)
        r2.addWidget(self.font)
        self.color_btn = QPushButton("A"); self.color_btn.setFixedWidth(34)
        self.color_btn.setToolTip("Màu chữ")
        self.color_btn.clicked.connect(self._pc); r2.addWidget(self.color_btn)
        lay.addLayout(r2)
        # r3: VIỀN chữ (độ dày) + MÀU VIỀN
        r6 = QHBoxLayout(); r6.addWidget(_lb("Viền chữ"))
        self.outline = _NoWheelSlider(Qt.Orientation.Horizontal); self.outline.setRange(0, 30)
        self.outline.setValue(12); self.outline.setToolTip("Độ dày viền chữ (0 = không viền)")
        r6.addWidget(self.outline, 1)
        self.oc_btn = QPushButton(); self.oc_btn.setFixedWidth(34)
        self.oc_btn.setToolTip("Màu viền chữ")
        self.oc_btn.clicked.connect(self._poc); r6.addWidget(self.oc_btn)
        lay.addLayout(r6)
        # r4: bật NỀN + MÀU NỀN + bo góc
        r3 = QHBoxLayout()
        self.bg_chk = QCheckBox("Nền"); self.bg_chk.setToolTip("Bật/tắt nền sau chữ")
        r3.addWidget(self.bg_chk)
        self.bg_btn = QPushButton(); self.bg_btn.setFixedWidth(34)
        self.bg_btn.setToolTip("Màu nền"); self.bg_btn.clicked.connect(self._pbg)
        r3.addWidget(self.bg_btn)
        r3.addWidget(_lb("Bo góc"))
        self.radius = _NoWheelSlider(Qt.Orientation.Horizontal); self.radius.setRange(0, 100)
        self.radius.setValue(30); r3.addWidget(self.radius, 1)
        lay.addLayout(r3)
        # r5: KÍCH THƯỚC nền (rộng/cao)
        r4 = QHBoxLayout()
        r4.addWidget(_lb("Nền rộng"))
        self.padx = _NoWheelSlider(Qt.Orientation.Horizontal); self.padx.setRange(0, 100)
        self.padx.setValue(25); r4.addWidget(self.padx, 1)
        r4.addWidget(_lb("Nền cao"))
        self.pady = _NoWheelSlider(Qt.Orientation.Horizontal); self.pady.setRange(0, 100)
        self.pady.setValue(25); r4.addWidget(self.pady, 1)
        lay.addLayout(r4)
        # r6: ĐỘ ĐẬM nền (mờ <-> đặc)
        r5 = QHBoxLayout()
        r5.addWidget(_lb("Nền đậm"))
        self.bg_alpha = _NoWheelSlider(Qt.Orientation.Horizontal); self.bg_alpha.setRange(0, 100)
        self.bg_alpha.setValue(75); r5.addWidget(self.bg_alpha, 1)
        lay.addLayout(r5)
        self._paint()
        self.text.textChanged.connect(self._ch)
        for s in (self.size, self.outline, self.radius, self.padx, self.pady,
                  self.bg_alpha):
            s.valueChanged.connect(self._ch)
        self.font.currentIndexChanged.connect(self._ch)
        self.bg_chk.toggled.connect(self._ch)

    def _pc(self):
        c = QColorDialog.getColor(QColor(self.color))
        if c.isValid():
            self.color = c.name().upper(); self._paint(); self._ch()

    def _pbg(self):
        c = QColorDialog.getColor(QColor(self.bg_color))
        if c.isValid():
            self.bg_color = c.name().upper()
            self.bg_chk.setChecked(True)  # chọn màu nền -> tự bật Nền luôn
            self._paint(); self._ch()

    def _poc(self):
        c = QColorDialog.getColor(QColor(self.outline_color))
        if c.isValid():
            self.outline_color = c.name().upper(); self._paint(); self._ch()

    def _paint(self):
        # ô màu chữ: nền = màu chữ, chữ "A" tương phản để thấy rõ
        self.color_btn.setStyleSheet(
            f"background:{self.color}; color:{'#000' if self.color.upper() > '#888888' else '#FFF'};"
            "border:1px solid #555; font-weight:bold;")
        self.bg_btn.setStyleSheet(f"background:{self.bg_color};border:1px solid #555;")
        self.oc_btn.setStyleSheet(f"background:{self.outline_color};border:1px solid #555;")

    def _ch(self, *_):
        self.on_change(self.lid)

    def data(self):
        return {"text": self.text.text(), "size": self.size.value() / 100,
                "font": self.font.currentText(), "color": self.color,
                "outline": self.outline.value() / 100.0,
                "outline_color": self.outline_color,
                "bg": self.bg_chk.isChecked(), "bg_color": self.bg_color,
                "radius": self.radius.value(), "is_part": self.is_part,
                "padx": self.padx.value() / 30.0, "pady": self.pady.value() / 30.0,
                "bg_alpha": self.bg_alpha.value() / 100.0}

    def set_data(self, d):
        self.text.setText(d.get("text", ""))
        self.size.setValue(int(round(d.get("size", 0.07) * 100)))
        i = self.font.findText(d.get("font", "Arial"))
        if i >= 0:
            self.font.setCurrentIndex(i)
        self.color = d.get("color", "#FFFFFF"); self.bg_color = d.get("bg_color", "#000000")
        self.outline_color = d.get("outline_color", "#000000")
        self.outline.setValue(int(round(d.get("outline", 0.12) * 100)))
        self.bg_chk.setChecked(d.get("bg", False))
        self.radius.setValue(int(d.get("radius", 30)))
        self.padx.setValue(int(round(d.get("padx", 0.83) * 30)))
        self.pady.setValue(int(round(d.get("pady", 0.83) * 30)))
        self.bg_alpha.setValue(int(round(d.get("bg_alpha", 0.75) * 100)))
        self._paint()

    def set_size_fraction(self, frac):
        self.size.blockSignals(True); self.size.setValue(int(round(frac * 100)))
        self.size.blockSignals(False)


class EditorDialog(QDialog):
    """Chỉnh MẪU: nền + khối video + chữ. Trả layout qua .layout."""

    _demo_ready = pyqtSignal(str)        # đường-dẫn-mp4 demo kiểu chữ (hoặc '' nếu lỗi)
    _dub_demo_ready = pyqtSignal(str)    # đường-dẫn-mp3 nghe thử giọng (hoặc '')

    def __init__(self, frame_path, layout=None, parent=None, current_name=""):
        super().__init__(parent)
        self.setWindowTitle("Chỉnh mẫu — TỰ LƯU khi bấm Xong (bản mới)")
        # MỞ TO theo màn hình: màn rộng -> khung xem trước to, chỉnh chữ dễ nhìn
        scr = QApplication.primaryScreen().availableGeometry()
        w = int(min(1560, scr.width() * 0.9))
        h = int(scr.height() * 0.92)
        self.resize(w, h)
        # min: canvas tối thiểu + cột phải 520 + lề -> cột phải không bao giờ ép hẹp
        self.setMinimumSize(min(w, 1100), min(h, 700))
        self.move(scr.x() + (scr.width() - w) // 2,
                  scr.y() + (scr.height() - h) // 2)
        self._next = 1
        self.rows = {}
        self.layout_result = None
        self._current_name = current_name or ""
        # Cờ cho studio_page biết DB mẫu ĐÃ ĐỔI (Lưu/Lưu mới/Xóa) dù user đóng
        # dialog bằng Hủy/X — nếu không nạp lại, layout_tpl trong RAM giữ bản CŨ
        # (vd cap_hook=True) và lần mở sau/lúc xuất dùng sai mẫu.
        self._db_changed = False
        self._save_failed = False    # Xong bấm nhưng lưu DB lỗi -> studio dùng RAM
        self._frame_path = frame_path
        self._demo_ready.connect(self._play_demo)
        # Lồng tiếng AI: nạp giọng nền + nghe thử
        self._dub_voice_pending = ""     # voice trong layout chờ list nạp xong
        self._dub_loading: set[str] = set()
        self._dub_demo_ready.connect(self._play_dub_demo)

        main = QHBoxLayout(self); main.setSpacing(14)
        # ----- CỘT TRÁI (GIÃN hết phần rộng còn lại): xem trước + ghi chú -----
        left = QVBoxLayout(); left.setSpacing(8)
        self.canvas = EditorCanvas(on_resize=self._on_resized)
        left.addWidget(self.canvas, 1)
        hint = QLabel("Kéo <b>khối video</b> để dời/phóng to · kéo <b>góc chữ</b> để "
                      "đổi cỡ · kéo <b>ô vàng</b> đặt chỗ phụ đề · kéo vào giữa có "
                      "vạch căn.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9A9AA8; font-size:12px;")
        left.addWidget(hint)
        main.addLayout(left, 1)

        # ----- CỘT PHẢI: cố định ~520px, tự CUỘN dọc khi màn thấp -----
        right_host = QWidget()
        right = QVBoxLayout(right_host)
        right.setSpacing(12); right.setContentsMargins(0, 0, 8, 0)
        rscroll = QScrollArea(); rscroll.setWidgetResizable(True)
        rscroll.setWidget(right_host)
        rscroll.setFixedWidth(520)
        rscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rscroll.setStyleSheet(
            "QScrollArea{border:none; background:transparent;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}")
        rcol = QVBoxLayout(); rcol.setSpacing(8)
        rcol.addWidget(rscroll, 1)
        main.addLayout(rcol)
        self._rscroll = rscroll          # để cuộn tới nhóm khi bấm hộp preview
        self._hl_widget = None           # widget đang được làm nổi (highlight tạm)
        self._hl_qss = ""                # style gốc để trả lại sau ~1s
        self._sec_n = 0

        def _group(title, rgb):
            # 1 CARD/nhóm: thanh tiêu đề màu đặc ở trên + thân nền nhạt dưới
            # (header rời hẳn, KHÔNG đè lên viền như QGroupBox -> sạch sẽ)
            self._sec_n += 1
            r, gg, b = rgb
            head = QLabel(f"  {self._sec_n}.  {title}")
            head.setObjectName(f"secHead{self._sec_n}")
            head.setStyleSheet(
                f"#secHead{self._sec_n}{{font-weight:700; font-size:14px; color:white;"
                f"background:rgb({r},{gg},{b}); padding:7px 4px;"
                f"border-top-left-radius:11px; border-top-right-radius:11px;}}")
            body = QWidget(); body.setObjectName(f"secBody{self._sec_n}")
            body.setStyleSheet(
                f"#secBody{self._sec_n}{{background:rgba({r},{gg},{b},0.10);"
                f"border:1px solid rgba({r},{gg},{b},0.45); border-top:none;"
                f"border-bottom-left-radius:11px; border-bottom-right-radius:11px;}}")
            v = QVBoxLayout(body); v.setSpacing(8); v.setContentsMargins(12, 10, 12, 12)
            card = QWidget()
            cl = QVBoxLayout(card); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
            cl.addWidget(head); cl.addWidget(body)
            right.addWidget(card)
            return v, card

        # Nhóm: Mẫu (xanh dương)
        gt, gt_box = _group("Mẫu có sẵn", (110, 139, 255))
        mr = QHBoxLayout()
        self.tmpl = _NoWheelCombo(); mr.addWidget(self.tmpl, 1)
        self.tmpl.currentIndexChanged.connect(self._load_tmpl)
        sv = QPushButton("Lưu"); sv.setToolTip("Ghi đè LÊN mẫu đang chọn")
        sv.clicked.connect(self._save_tmpl); _fit_button(sv); mr.addWidget(sv)
        svn = QPushButton("Lưu mới"); svn.setToolTip("Lưu thành mẫu mới (đặt tên)")
        svn.clicked.connect(self._save_tmpl_new); _fit_button(svn); mr.addWidget(svn)
        dlt = QPushButton("Xóa"); dlt.setProperty("danger", True)
        dlt.setToolTip("Xóa mẫu đang chọn"); dlt.clicked.connect(self._del_tmpl)
        _fit_button(dlt); mr.addWidget(dlt)
        gt.addLayout(mr)

        # Nhóm: Nền khung (xanh lá)
        gb, gb_box = _group("Nền khung", (52, 211, 153))
        bgrow = QHBoxLayout()
        for label, mode in (("Mờ", "blur"), ("Lấp đầy", "fill"),
                            ("Đen", "black"), ("Trắng", "white")):
            b = QPushButton(label)
            b.setToolTip("Lấp đầy = crop cắt 2 bên cho video đầy khung (chuẩn TikTok)"
                         if mode == "fill" else "")
            b.clicked.connect(lambda _, m=mode: self.canvas.set_bg(m))
            _fit_button(b)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            bgrow.addWidget(b)
        gb.addLayout(bgrow)
        br = QHBoxLayout(); br.addWidget(QLabel("Độ mờ nền"))
        self.blur_amt = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.blur_amt.setRange(2, 50); self.blur_amt.setValue(22)
        self.blur_amt.setToolTip("Chỉ áp cho nền Mờ.")
        br.addWidget(self.blur_amt, 1)
        gb.addLayout(br)
        self.trim_chk = QCheckBox("Tự cắt viền đen của video gốc (nếu có)")
        gb.addWidget(self.trim_chk)
        # KHUNG TỰ KHỚP TỈ LỆ VIDEO GỐC: lúc XUẤT app tính lại khung theo tỉ lệ
        # nguồn (giữ tâm + bề ngang mẫu, clamp vừa canvas) -> nguồn vuông/ngang
        # hiện TRỌN, không bị cắt 2 bên; nền lấp phần thừa.
        self.fit_src_chk = QCheckBox("Khung tự khớp video gốc (không mất hình)")
        self.fit_src_chk.setToolTip(
            "Video vuông/ngang sẽ hiện TRỌN không bị cắt; khung mẫu chỉ định "
            "vị trí tâm + bề ngang. Lúc xuất app tự tính lại chiều cao khung "
            "theo tỉ lệ video nguồn (thu vừa canvas nếu tràn), phần thừa do "
            "nền (mờ/đen/trắng) lấp. Nền 'Lấp đầy' sẽ tự chuyển sang nền mờ "
            "khi bật.")
        gb.addWidget(self.fit_src_chk)
        # Tốc độ + đổi giọng (chống bản quyền)
        sp = QHBoxLayout(); sp.addWidget(QLabel("Tốc độ"))
        self.speed_cb = _NoWheelCombo()
        for t in ("1.0x", "1.05x", "1.1x", "1.15x", "1.2x", "1.3x"):
            self.speed_cb.addItem(t)
        sp.addWidget(self.speed_cb, 1)
        sp.addWidget(QLabel("Giọng"))
        self.voice_cb = _NoWheelCombo()
        # Đổi CAO ĐỘ giọng GỐC (né bản quyền/content-ID khi reup). Giá trị =
        # hệ số cao độ: <1 trầm hơn, >1 cao hơn.
        for label, p in (("Gốc", 1.0),
                         ("Trầm nhẹ (nam)", 0.94), ("Trầm sâu", 0.85),
                         ("Trầm rất sâu", 0.78),
                         ("Cao nhẹ (nữ)", 1.06), ("Cao (nữ)", 1.12),
                         ("The thé", 1.22),
                         ("Đổi giọng (né b.quyền)", 1.15),
                         ("Già/khàn", 0.88), ("Robot/lạ", 1.30)):
            self.voice_cb.addItem(label, p)
        sp.addWidget(self.voice_cb, 1)
        self.voice_demo_btn = QPushButton("🔊 Nghe")
        self.voice_demo_btn.setToolTip("Nghe thử giọng gốc sau khi đổi cao độ "
                                       "(dùng khung hình hiện tại của video).")
        self.voice_demo_btn.clicked.connect(self._demo_voice_pitch)
        _fit_button(self.voice_demo_btn)
        sp.addWidget(self.voice_demo_btn)
        gb.addLayout(sp)
        # HOOK-FIRST: nhá hàng khoảnh khắc cao trào lên ĐẦU clip
        self.hook_first_chk = QCheckBox("Mở đầu bằng 2-4s CAO TRÀO nhất (hook-first)")
        self.hook_first_chk.setToolTip(
            "Tự lấy khoảnh khắc sốc/cao trào nhất trong clip chiếu lên ĐẦU như "
            "'nhá hàng' rồi mới phát nội dung — giữ chân người xem 3s đầu (meta "
            "TikTok). AI chọn mốc; nếu không có thì dò theo âm thanh to nhất.")
        gb.addWidget(self.hook_first_chk)
        # HIỆU ỨNG tinh tế (mặc định BẬT nhẹ): fade hình đầu/cuối + tiếng
        # chuyển đoạn. Whoosh tổng hợp thuần ffmpeg -> không cần file, chạy
        # mọi máy khách.
        self.fx_fade_chk = QCheckBox("Fade mượt đầu/cuối clip")
        self.fx_fade_chk.setChecked(True)
        self.fx_fade_chk.setToolTip(
            "Làm hình mờ dần lên ở đầu (~0.35s) và mờ dần xuống ở cuối — "
            "chuyển cảnh tinh tế, chuyên nghiệp, không lố.")
        gb.addWidget(self.fx_fade_chk)
        self.fx_whoosh_chk = QCheckBox("Tiếng chuyển đoạn (thư viện theo ngữ cảnh)")
        self.fx_whoosh_chk.setChecked(True)
        self.fx_whoosh_chk.setToolTip(
            "Thêm tiếng chuyển đoạn NHỎ tại điểm ghép giữa các đoạn (chỉ khi "
            "clip ghép nhiều đoạn / Mixed-Cut / Reup thuyết minh). App có sẵn "
            "THƯ VIỆN tiếng động phong phú (đóng gói kèm, không cần tải): "
            "whoosh/gió/tick (chuyển đoạn), boom (khoảnh khắc mạnh), riser "
            "(hồi hộp trước cao trào), ding (chốt/lộ diện), pop/click. "
            "App tự CHỌN loại THEO NGỮ CẢNH: Reup vào cao trào tiếng gốc -> "
            "boom, đoạn kết -> ding, còn lại -> whoosh; mỗi loại chọn ngẫu "
            "nhiên 1 tiếng, không lặp liên tiếp nên nghe đa dạng. Chọn thư "
            "mục tiếng động riêng ở dưới -> ưu tiên dùng file của bạn.")
        gb.addWidget(self.fx_whoosh_chk)
        # LẬT GƯƠNG (mirror trái-phải) để NÉ content-ID khi reup. Chỉ lật HÌNH;
        # chữ tiêu đề/Part + phụ đề chồng SAU nên vẫn đọc bình thường.
        self.flip_h_chk = QCheckBox("Lật gương video (né bản quyền)")
        self.flip_h_chk.setChecked(False)
        self.flip_h_chk.setToolTip(
            "Lật gương video theo chiều NGANG (trái ↔ phải) để né hệ thống nhận "
            "dạng bản quyền (Content-ID) khi đăng lại. Chỉ HÌNH bị soi gương; "
            "tiêu đề, chữ Part và phụ đề vẫn đọc bình thường (không bị ngược). "
            "Thời lượng, tiếng, mọi thứ khác giữ nguyên.")
        gb.addWidget(self.flip_h_chk)
        # THƯ MỤC tiếng động riêng (tùy chọn): giống nhạc nền ngẫu nhiên — có
        # thư mục + có file thì mỗi điểm ghép lấy 1 file ngẫu nhiên; để trống ->
        # dùng bộ tiếng tổng hợp đa dạng ở trên.
        self._fx_sfx_dir = ""
        srow = QHBoxLayout()
        self.fx_sfx_pick = QPushButton("Chọn thư mục tiếng động…")
        self.fx_sfx_pick.setToolTip(
            "Tùy chọn: chọn 1 THƯ MỤC chứa file tiếng động (.mp3/.wav/.m4a...). "
            "Nếu có, mỗi điểm ghép sẽ lấy NGẪU NHIÊN 1 file trong đó (trộn nhỏ). "
            "Để trống -> dùng tiếng tổng hợp đa dạng.")
        self.fx_sfx_pick.clicked.connect(self._pick_fx_sfx_dir)
        srow.addWidget(self.fx_sfx_pick)
        self.fx_sfx_clear = QPushButton("Bỏ")
        self.fx_sfx_clear.clicked.connect(self._clear_fx_sfx_dir)
        _fit_button(self.fx_sfx_clear,
                    minw=self.fx_sfx_clear.fontMetrics().horizontalAdvance("Bỏ") + 26)
        srow.addWidget(self.fx_sfx_clear)
        gb.addLayout(srow)
        self.fx_sfx_lbl = QLabel("")
        self.fx_sfx_lbl.setStyleSheet("color:#9AA6BF; font-size:11px;")
        self.fx_sfx_lbl.setWordWrap(True)
        gb.addWidget(self.fx_sfx_lbl)
        self._fx_sfx_update()

        # Nhóm: Nhạc nền + Logo kênh (hồng)
        gx, gx_box = _group("Nhạc nền + Logo kênh", (244, 114, 182))
        mrow = QHBoxLayout(); mrow.addWidget(QLabel("Nhạc nền"))
        self.bgm_mode = _NoWheelCombo()
        for label, m in (("Tắt", "off"), ("Ngẫu nhiên từ thư mục", "random"),
                         ("1 bài cố định", "fixed")):
            self.bgm_mode.addItem(label, m)
        self.bgm_mode.setToolTip(
            "Ngẫu nhiên: mỗi clip xuất sẽ tự lấy 1 bài bất kỳ trong thư mục "
            "nhạc của bạn. Nhạc tự lặp/cắt cho khớp độ dài clip, trộn NHỎ dưới "
            "tiếng nói gốc.")
        self.bgm_mode.currentIndexChanged.connect(self._bgm_mode_ui)
        mrow.addWidget(self.bgm_mode, 1)
        self.bgm_pick = QPushButton("Chọn…")
        self.bgm_pick.clicked.connect(self._pick_bgm_src)
        # rộng đủ cho nhãn DÀI NHẤT ("Chọn thư mục…") -> đổi text không bị xén
        _fit_button(self.bgm_pick, minw=self.bgm_pick.fontMetrics().horizontalAdvance(
            "Chọn thư mục…") + 26)
        mrow.addWidget(self.bgm_pick)
        gx.addLayout(mrow)
        self.bgm_lbl = QLabel("")
        self.bgm_lbl.setStyleSheet("color:#9AA6BF; font-size:11px;")
        self.bgm_lbl.setWordWrap(True)
        gx.addWidget(self.bgm_lbl)
        self._bgm_dir = ""; self._bgm_file = ""
        vrow = QHBoxLayout(); vrow.addWidget(QLabel("Âm lượng nhạc"))
        self.bgm_vol = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.bgm_vol.setRange(5, 60); self.bgm_vol.setValue(15)  # 5%..60%
        vrow.addWidget(self.bgm_vol, 1)
        self.bgm_vol_lbl = QLabel("15%"); self.bgm_vol_lbl.setFixedWidth(40)
        self.bgm_vol.valueChanged.connect(
            lambda v: self.bgm_vol_lbl.setText(f"{v}%"))
        vrow.addWidget(self.bgm_vol_lbl)
        gx.addLayout(vrow)
        # ÂM LƯỢNG TIẾNG GỐC (độc lập nhạc nền): kéo nhỏ khi muốn nhạc/lồng
        # tiếng nổi hơn. Mặc định 100%. Khi có lồng tiếng, tiếng gốc tự hạ
        # (~12%) trừ khi user kéo tại đây (giá trị này luôn được ưu tiên).
        orow = QHBoxLayout(); orow.addWidget(QLabel("Âm lượng tiếng gốc"))
        self.orig_vol = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.orig_vol.setRange(0, 100); self.orig_vol.setValue(100)  # 0%..100%
        self.orig_vol.setToolTip(
            "Âm lượng TIẾNG GỐC của video (độc lập với nhạc nền). Kéo nhỏ nếu "
            "muốn nhạc nền/lồng tiếng nổi hơn. Khi bật lồng tiếng, để 100% thì "
            "tiếng gốc tự hạ nhỏ làm nền; kéo tay để tự quyết mức.")
        orow.addWidget(self.orig_vol, 1)
        self.orig_vol_lbl = QLabel("100%"); self.orig_vol_lbl.setFixedWidth(40)
        self.orig_vol.valueChanged.connect(
            lambda v: self.orig_vol_lbl.setText(f"{v}%"))
        orow.addWidget(self.orig_vol_lbl)
        gx.addLayout(orow)
        # logo kênh (watermark)
        self._logo_path = ""
        lrow = QHBoxLayout()
        self.logo_btn = QPushButton("Chọn logo (PNG)…")
        self.logo_btn.setToolTip("Ảnh PNG nền trong suốt sẽ được đóng lên góc "
                                 "mọi clip xuất ra (watermark kênh).")
        self.logo_btn.clicked.connect(self._pick_logo)
        lrow.addWidget(self.logo_btn, 1)
        lc = QPushButton("Bỏ"); lc.setProperty("ghost", True)
        lc.clicked.connect(lambda: (setattr(self, "_logo_path", ""),
                                    self.logo_lbl.setText("(chưa có logo)")))
        _fit_button(lc); lrow.addWidget(lc)
        gx.addLayout(lrow)
        self.logo_lbl = QLabel("(chưa có logo)")
        self.logo_lbl.setStyleSheet("color:#9AA6BF; font-size:11px;")
        self.logo_lbl.setWordWrap(True)
        gx.addWidget(self.logo_lbl)
        l2 = QHBoxLayout(); l2.addWidget(QLabel("Góc"))
        self.logo_pos = _NoWheelCombo()
        for label, m in (("Trên phải", "tr"), ("Trên trái", "tl"),
                         ("Dưới phải", "br"), ("Dưới trái", "bl")):
            self.logo_pos.addItem(label, m)
        l2.addWidget(self.logo_pos, 1)
        l2.addWidget(QLabel("Cỡ"))
        self.logo_size = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.logo_size.setRange(6, 30); self.logo_size.setValue(14)  # % rộng khung
        l2.addWidget(self.logo_size, 1)
        l2.addWidget(QLabel("Đậm"))
        self.logo_op = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.logo_op.setRange(20, 100); self.logo_op.setValue(90)
        l2.addWidget(self.logo_op, 1)
        gx.addLayout(l2)

        # Nhóm: Lồng tiếng AI (xanh dương nhạt)
        gd, gd_box = _group("Lồng tiếng AI (dubbing)", (96, 165, 250))
        dr1 = QHBoxLayout(); dr1.addWidget(QLabel("Ngôn ngữ"))
        self.dub_lang = _NoWheelCombo()
        self.dub_lang.addItem("Tắt", "")
        for code, label in DUB_LANGS.items():
            self.dub_lang.addItem(label, code)
        self.dub_lang.setToolTip(
            "AI dịch lời thoại rồi ĐỌC THUYẾT MINH đè lên clip (giọng Microsoft "
            "tự nhiên, khớp mốc thời gian). Phụ đề (nếu bật) cũng dùng chữ đã "
            "dịch. Cần mạng + key AI để dịch.")
        self.dub_lang.currentIndexChanged.connect(self._dub_lang_ui)
        dr1.addWidget(self.dub_lang, 1)
        dr1.addWidget(QLabel("Giọng"))
        self.dub_voice = _NoWheelCombo()
        self.dub_voice.setToolTip(
            "Giọng đọc thuyết minh. ⭐ = giọng hot tự nhiên nhất (edge-tts, "
            "free).\n🌟 Gemini = giọng nét nhất (cần key Gemini, hạn mức miễn "
            "phí thấp).")
        dr1.addWidget(self.dub_voice, 2)   # combo giọng giãn nhiều hơn (tên dài)
        gd.addLayout(dr1)
        # "Nghe thử" xuống DÒNG RIÊNG: hàng trên đã chật (2 label + 2 combo) nên
        # nhét thêm nút vào sẽ ép combo/nút hẹp -> xén chữ. Tách ra là hết xén.
        dr1b = QHBoxLayout(); dr1b.addStretch(1)
        self.dub_prev_btn = QPushButton("🔊 Nghe thử")
        self.dub_prev_btn.setToolTip(
            "Đọc thử 1 câu ngắn bằng giọng đang chọn (cần mạng).")
        self.dub_prev_btn.clicked.connect(self._dub_preview)
        _fit_button(self.dub_prev_btn); dr1b.addWidget(self.dub_prev_btn)
        gd.addLayout(dr1b)
        self.dub_mute_chk = QCheckBox("Tắt hẳn tiếng gốc (mặc định: giảm nhỏ)")
        self.dub_mute_chk.setToolTip(
            "Bỏ chọn = tiếng gốc còn 15% làm 'không khí' nền dưới lời thuyết "
            "minh. Chọn = chỉ còn giọng lồng tiếng (+ nhạc nền nếu có).")
        gd.addWidget(self.dub_mute_chk)
        dmr = QHBoxLayout(); dmr.addWidget(QLabel("Kiểu khớp"))
        self.dub_mode = _NoWheelCombo()
        self.dub_mode.addItem("Tự nhiên (đọc đều, khớp mốc)", "natural")
        self.dub_mode.addItem("Khớp chặt (ép vừa khung, có thể nhanh)", "tight")
        self.dub_mode.addItem("Khớp video (mượt nhất — hơi chậm hình)", "video")
        self.dub_mode.setToolTip(
            "Tự nhiên: đọc tốc độ thường, mỗi câu bắt đầu đúng lúc câu gốc — "
            "nghe đều, không giật. Khớp chặt: ép mỗi câu lọt khung riêng của nó "
            "(bám sát nhất nhưng có chỗ đọc nhanh). Khớp video: đọc HOÀN TOÀN "
            "tự nhiên (không tăng tốc giọng), CO GIÃN NHẸ đoạn video cho khớp "
            "lời — mượt nhất, giọng hay nhất; đổi lại hình chậm nhẹ (tối đa ~1.5x).")
        dmr.addWidget(self.dub_mode, 1)
        gd.addLayout(dmr)
        self._dub_lang_ui()

        # ============================================================
        # KHU 1 — PHỤ ĐỀ CHẠY CHỮ (lời gốc / clip thường). Thứ tự control:
        #   Kiểu · Chữ hoa · Màu chữ · Màu viền · Độ dày viền · Cỡ · Font.
        # Bố cục ĐỐI XỨNG với KHU 2 (Chữ AI đọc) bên dưới để dễ nhìn.
        # ============================================================
        gc, gc_box = _group("Phụ đề chạy chữ (lời gốc)", (251, 191, 36))
        self._grp_cap = gc_box           # nhóm để cuộn tới khi bấm ô Phụ đề
        self.cap_chk = QCheckBox("Bật phụ đề — KÉO ô vàng trên khung để đặt chỗ")
        self.cap_chk.setChecked(True)
        self.cap_chk.toggled.connect(self.canvas.show_cap)
        gc.addWidget(self.cap_chk)
        # 1. KIỂU chạy chữ (+ nút Demo xem trước) — toàn bộ preset
        self.cap_preset = _NoWheelCombo()
        for name in CAPTION_PRESETS:
            self.cap_preset.addItem(name)
        self.cap_preset.setToolTip("Chọn kiểu phụ đề (màu/viền/hiệu ứng có sẵn).")
        self.cap_preset.currentIndexChanged.connect(self._refresh_cap)
        self.cap_demo_btn = QPushButton("Demo")
        self.cap_demo_btn.setToolTip("Phát thử ~6 giây để xem kiểu chữ chạy thế nào.")
        self.cap_demo_btn.clicked.connect(self._demo_caption)
        _fit_button(self.cap_demo_btn, minw=self.cap_demo_btn.fontMetrics()
                    .horizontalAdvance("Đang tạo…") + 26)
        gc.addLayout(_frow("Kiểu chạy chữ", self.cap_preset, self.cap_demo_btn))
        # 2. CHỮ HOA
        self.cap_case = _case_combo(
            "Đổi kiểu chữ hoa cho phụ đề video gốc: Giữ nguyên / HOA / thường / "
            "Hoa Đầu Từ. Chỉ đổi cách HIỂN THỊ, không đổi lời/mốc.")
        self.cap_case.currentIndexChanged.connect(self._refresh_cap)
        gc.addLayout(_frow("Chữ hoa", self.cap_case))
        # 3. MÀU CHỮ (để trống = theo preset)
        self._capcolor = ""        # '' = theo màu của kiểu; chọn để ghi đè
        self.cap_color_btn, self._cap_color_refresh = self._color_button(
            lambda: self._capcolor, self._set_cap_color, "Màu chữ phụ đề")
        gc.addLayout(_frow("Màu chữ", self.cap_color_btn, stretch_at=-1))
        # 4. MÀU VIỀN (để trống = theo preset)
        self._cap_outline = ""
        self.cap_outline_btn, self._cap_outline_refresh = self._color_button(
            lambda: self._cap_outline, self._set_cap_outline, "Màu viền phụ đề")
        gc.addLayout(_frow("Màu viền", self.cap_outline_btn, stretch_at=-1))
        # 5. ĐỘ DÀY VIỀN (0 = theo preset)
        self.cap_ow = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.cap_ow.setRange(0, 30)      # 0=theo preset .. 0.30 tỉ lệ chiều cao chữ
        self.cap_ow.setValue(0)
        self.cap_ow.setToolTip("Độ dày viền chữ (0 = theo preset).")
        self.cap_ow.valueChanged.connect(self._refresh_cap_soon)
        self.cap_ow_lbl = QLabel("preset"); self.cap_ow_lbl.setFixedWidth(44)
        self.cap_ow.valueChanged.connect(
            lambda v: self.cap_ow_lbl.setText("preset" if v == 0 else str(v)))
        gc.addLayout(_frow("Độ dày viền", self.cap_ow, self.cap_ow_lbl))
        # 6. CỠ CHỮ
        self.cap_size = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.cap_size.setRange(18, 80); self.cap_size.setValue(40)  # = 4.0%
        self.cap_size.valueChanged.connect(self._refresh_cap_soon)   # gộp -> khỏi đơ
        self.cap_lbl_sz = QLabel("4.0%"); self.cap_lbl_sz.setFixedWidth(44)
        self.cap_size.valueChanged.connect(
            lambda v: self.cap_lbl_sz.setText(f"{v/10:.1f}%"))
        gc.addLayout(_frow("Cỡ chữ", self.cap_size, self.cap_lbl_sz))
        # KÉO góc ô caption -> ĐỒNG BỘ vào thanh Cỡ (để LƯU được).
        self.canvas.cap_box.on_resize = lambda _l, frac: self._cap_drag_size(frac)
        # 7. FONT
        self.cap_font = _NoWheelCombo()
        for f in ("Montserrat", "Be Vietnam Pro", "Anton", "Bungee", "Baloo 2",
                  "Oswald", "Lexend", "Pattaya", "Arial"):
            self.cap_font.addItem(f)
        self.cap_font.currentIndexChanged.connect(self._refresh_cap)
        gc.addLayout(_frow("Font", self.cap_font))
        # 8. VỊ TRÍ (kéo ô vàng trên khung) + KHỚP GIỜ + HOOK — phần riêng của
        # phụ đề gốc (không đối xứng sang khu AI, để cuối khu).
        cs3 = QHBoxLayout(); lb3 = QLabel("Khớp giờ"); lb3.setFixedWidth(_LBL_W)
        cs3.addWidget(lb3)
        self.cap_delay = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.cap_delay.setRange(-300, 500)      # -0.3s (sớm) .. +0.5s (trễ)
        self.cap_delay.setValue(120)            # mặc định trễ 0.12s
        self.cap_delay.setToolTip("Kéo PHẢI nếu chữ hiện SỚM hơn lời; kéo TRÁI nếu "
                                  "hiện TRỄ. Đơn vị mili-giây.")
        self.cap_lbl = QLabel("+120ms"); self.cap_lbl.setFixedWidth(56)
        self.cap_delay.valueChanged.connect(
            lambda v: self.cap_lbl.setText(f"{'+' if v >= 0 else ''}{v}ms"))
        cs3.addWidget(self.cap_delay, 1); cs3.addWidget(self.cap_lbl)
        gc.addLayout(cs3)
        self.cap_hook = QCheckBox("Hiện HOOK đầu clip (câu giật tít vàng to ~6s, AI tự chọn)")
        self.cap_hook.setChecked(False)   # mặc định TẮT (chỉ bật khi user muốn)
        self.cap_hook.toggled.connect(self.canvas.show_hook)  # bật/tắt -> hiện preview
        self.cap_hook.setToolTip("Hiện 1 câu gây tò mò TO ở đầu clip rồi ẩn — kiểu "
                                 "video viral. AI tự chọn câu từ lời thoại.")
        gc.addWidget(self.cap_hook)

        # ============================================================
        # KHU 2 — CHỮ AI ĐỌC (thuyết minh). ĐỐI XỨNG khu 1, cùng thứ tự:
        #   Kiểu chạy chữ · Chữ hoa · Màu chữ · Màu viền · Độ dày viền · Cỡ ·
        #   Vị trí · In nghiêng.
        # Chỉ dùng khi bấm "Reup thuyết minh" (clip có kịch bản AI kể); clip
        # thường KHÔNG sinh đoạn narrate nên khu này KHÔNG ảnh hưởng.
        # ============================================================
        gn, gn_box = _group("Chữ AI đọc (thuyết minh)", (167, 139, 250))
        self._grp_narr = gn_box          # nhóm để cuộn tới khi bấm ô Chữ AI kể
        self.narr_chk = QCheckBox(
            "Xem trước ô chữ AI kể — KÉO ô để đặt VỊ TRÍ DỌC")
        self.narr_chk.setToolTip(
            "Bật để KÉO ô chữ AI kể trong khung xem trước (chọn vị trí dọc). "
            "Chỉ để xem/đặt chỗ — không ảnh hưởng clip thường (clip thường "
            "không có đoạn AI kể).")
        self.narr_chk.toggled.connect(self.canvas.show_narr)
        gn.addWidget(self.narr_chk)
        # 1. KIỂU chạy chữ — mục ĐẦU = "(giống phụ đề gốc)" (= narr_same cũ),
        # còn lại là toàn bộ preset RIÊNG cho chữ AI.
        self.narr_preset = _NoWheelCombo()
        self.narr_preset.addItem(NARR_SAME_LABEL)      # data mặc định = text
        for name in CAPTION_PRESETS:
            self.narr_preset.addItem(name)
        self.narr_preset.setToolTip(
            "Kiểu chạy chữ cho đoạn AI kể. '(giống phụ đề gốc)' = dùng y hệt "
            "kiểu phụ đề gốc ở trên. Chọn kiểu khác = đoạn AI kể có kiểu/màu "
            "riêng (Style Narrate).")
        self.narr_preset.currentIndexChanged.connect(self._refresh_narr)
        gn.addLayout(_frow("Kiểu chạy chữ", self.narr_preset))
        # 2. CHỮ HOA
        self.narr_case = _case_combo(
            "Kiểu chữ hoa cho đoạn AI kể: Giữ nguyên / HOA / thường / Hoa Đầu Từ.")
        self.narr_case.currentIndexChanged.connect(self._refresh_narr)
        gn.addLayout(_frow("Chữ hoa", self.narr_case))
        # 3. MÀU CHỮ (để trống = theo kiểu chạy chữ đã chọn)
        self._narr_color = _NARR_COLOR_DEFAULT
        self.narr_color_btn, self._narr_color_refresh = self._color_button(
            lambda: self._narr_color, self._set_narr_color, "Màu chữ AI đọc")
        gn.addLayout(_frow("Màu chữ", self.narr_color_btn, stretch_at=-1))
        # 4. MÀU VIỀN (để trống = theo kiểu)
        self._narr_outline = ""
        self.narr_outline_btn, self._narr_outline_refresh = self._color_button(
            lambda: self._narr_outline, self._set_narr_outline, "Màu viền AI đọc")
        gn.addLayout(_frow("Màu viền", self.narr_outline_btn, stretch_at=-1))
        # 5. ĐỘ DÀY VIỀN (0 = theo kiểu)
        self.narr_ow = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.narr_ow.setRange(0, 30)
        self.narr_ow.setValue(0)
        self.narr_ow.setToolTip("Độ dày viền chữ AI đọc (0 = theo kiểu).")
        self.narr_ow.valueChanged.connect(self._refresh_narr_soon)
        self.narr_ow_lbl = QLabel("preset"); self.narr_ow_lbl.setFixedWidth(44)
        self.narr_ow.valueChanged.connect(
            lambda v: self.narr_ow_lbl.setText("preset" if v == 0 else str(v)))
        gn.addLayout(_frow("Độ dày viền", self.narr_ow, self.narr_ow_lbl))
        # 6. CỠ CHỮ
        self.narr_size = _NoWheelSlider(Qt.Orientation.Horizontal)
        self.narr_size.setRange(18, 80); self.narr_size.setValue(45)  # = 4.5%
        self.narr_size.valueChanged.connect(self._refresh_narr_soon)
        self.narr_sz_lbl = QLabel("4.5%"); self.narr_sz_lbl.setFixedWidth(44)
        self.narr_size.valueChanged.connect(
            lambda v: self.narr_sz_lbl.setText(f"{v/10:.1f}%"))
        gn.addLayout(_frow("Cỡ chữ", self.narr_size, self.narr_sz_lbl))
        # kéo góc ô narr -> đồng bộ thanh Cỡ (như cap_box)
        self.canvas.narr_box.on_resize = lambda _l, frac: self._narr_drag_size(frac)
        # 7. VỊ TRÍ: kéo ô AI kể trên khung (bật checkbox trên) — không có control
        #    thanh trượt riêng, giống phụ đề gốc kéo ô vàng.
        # 8. IN NGHIÊNG
        self.narr_italic = QCheckBox("In nghiêng")
        self.narr_italic.setChecked(True)      # mặc định BẬT
        self.narr_italic.setToolTip(
            "Chữ AI kể in nghiêng (mặc định BẬT — dễ phân biệt với thoại gốc).")
        self.narr_italic.toggled.connect(self._refresh_narr)
        gn.addWidget(self.narr_italic)

        # Nhóm: Lớp chữ (hồng)
        gl, gl_box = _group("Lớp chữ (Part · tiêu đề · cố định)",
                            (244, 114, 182))
        # KIỂU CHỮ HOA cho lớp chữ overlay: Tiêu đề/Hook + Part (áp lên CHỮ
        # HIỂN THỊ khi render PNG / hook ASS, không đổi vị trí).
        lcr = QHBoxLayout()
        lcr.addWidget(QLabel("Tiêu đề/Hook"))
        self.hook_case = _case_combo(
            "Kiểu chữ hoa cho TIÊU ĐỀ AI + HOOK + chữ cố định (mọi lớp không "
            "phải Part).")
        self.hook_case.currentIndexChanged.connect(self._sync_all_cases)
        lcr.addWidget(self.hook_case, 1)
        lcr.addWidget(QLabel("Part"))
        self.part_case = _case_combo(
            "Kiểu chữ hoa cho lớp Part (số phần).")
        self.part_case.currentIndexChanged.connect(self._sync_all_cases)
        lcr.addWidget(self.part_case, 1)
        gl.addLayout(lcr)
        ar = QHBoxLayout()
        a2 = QPushButton("+ Part")
        a2.clicked.connect(lambda: self._add(is_part=True))
        _fit_button(a2); ar.addWidget(a2)
        a3 = QPushButton("+ Tiêu đề AI")
        a3.clicked.connect(self._add_title)
        _fit_button(a3); ar.addWidget(a3)
        a1 = QPushButton("+ Chữ cố định")
        a1.clicked.connect(lambda: self._add(is_part=False))
        _fit_button(a1); ar.addWidget(a1)
        gl.addLayout(ar)
        self.box = QVBoxLayout(); self.box.setSpacing(8)
        host = QWidget(); host.setLayout(self.box)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(host)
        sc.setStyleSheet("QScrollArea{border:none;}")
        gl.addWidget(sc, 1)
        self._grp_layers = gl_box        # cả nhóm Lớp chữ
        self._layer_scroll = sc          # cuộn nội bộ tới đúng _LayerRow
        right.setStretchFactor(gl_box, 1)   # nhóm Lớp chữ giãn chiếm phần thừa
        # BẤM 1 hộp chữ trong khung preview -> cuộn panel phải tới nhóm chỉnh của
        # nó + làm nổi ~1s. Gán sau khi mọi nhóm/tham chiếu đã dựng.
        self.canvas.on_select = self._on_box_select
        self._reload_tmpl(select=self._current_name)

        # Nút dưới cùng
        brow = QHBoxLayout(); brow.addStretch(1)
        cancel = QPushButton("Hủy"); cancel.clicked.connect(self.reject)
        brow.addWidget(cancel)
        ok = QPushButton("Xong"); ok.setProperty("primary", True)
        ok.clicked.connect(self._accept); brow.addWidget(ok)
        rcol.addLayout(brow)   # nút nằm NGOÀI vùng cuộn -> luôn thấy

        self.canvas.load_frame(frame_path)
        self._apply_layout(layout)

    def _color_button(self, get, set_, title="Chọn màu",
                      default_label="theo preset"):
        """Nút CHỌN MÀU dùng chung: hiện ô vuông màu hiện tại; bấm mở
        QColorDialog. get() -> hex hiện tại ('' = mặc định/theo preset);
        set_(hex) lưu lại ('' = xóa về mặc định). Chuột PHẢI = xóa về mặc định.
        Trả (button, refresh) — gọi refresh() sau khi set giá trị ở nơi khác
        (vd _apply_layout) để ô màu cập nhật."""
        btn = QPushButton()
        btn.setFixedWidth(56)
        btn.setToolTip(f"{title} (bấm chọn màu · chuột phải = {default_label})")

        def refresh():
            hexv = get() or ""
            if hexv:
                # ô nền = màu đang chọn, chữ A tương phản để thấy rõ
                fg = "#000" if hexv.upper() > "#888888" else "#FFF"
                btn.setText("A")
                btn.setStyleSheet(
                    f"background:{hexv}; color:{fg}; border:1px solid #666;"
                    "font-weight:bold; border-radius:4px;")
            else:                       # mặc định/theo preset -> hiện chữ "tự"
                btn.setText("tự")
                btn.setStyleSheet(
                    "background:#2A2A34; color:#9AA6BF; border:1px dashed #666;"
                    "border-radius:4px;")

        def pick():
            cur = get() or "#FFFFFF"
            c = QColorDialog.getColor(QColor(cur), self, title)
            if c.isValid():
                set_(c.name().upper())
                refresh()

        def reset():
            set_("")
            refresh()

        btn.clicked.connect(pick)
        # chuột phải -> menu 'Về mặc định'
        from PyQt6.QtCore import Qt as _Qt
        btn.setContextMenuPolicy(_Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda _p: reset())
        refresh()
        return btn, refresh

    def _apply_layout(self, layout):
        if layout:
            vr = layout.get("video_rect")
            if vr:
                self.canvas.vbox.set_rect(*vr)
            self.canvas.set_bg(layout.get("bg", "blur"))
            self.trim_chk.setChecked(layout.get("trim_black", False))
            self.fit_src_chk.setChecked(bool(layout.get("fit_src", False)))
            self.cap_chk.setChecked(layout.get("captions", True))
            fi = self.cap_font.findText(layout.get("cap_font", "Montserrat"))
            if fi >= 0:
                self.cap_font.setCurrentIndex(fi)
            cz = layout.get("cap_size", 0)
            if cz:
                self.cap_size.setValue(int(float(cz) * 1000))
            # KHỚP TUYỆT ĐỐI tên preset đã lưu = tên trong combo (= key
            # CAPTION_PRESETS). findText EXACT + case-sensitive; tên lạ (mẫu
            # cũ / preset bị đổi tên) -> KHÔNG im lặng giữ preset đang chọn
            # (đó là mầm 'chọn X ra Y'): về index 0 (preset mặc định đầu combo)
            # để trạng thái combo luôn PHẢN ÁNH ĐÚNG cái sẽ xuất.
            _cp_name = layout.get("cap_preset", "Vàng nhảy (TikTok)")
            pi = self.cap_preset.findText(_cp_name)
            self.cap_preset.setCurrentIndex(pi if pi >= 0 else 0)
            self._capcolor = layout.get("cap_color", "") or ""
            self._cap_outline = layout.get("cap_outline", "") or ""
            self.cap_ow.setValue(int(round(float(layout.get("cap_ow", 0) or 0)
                                           * 100)))
            self._cap_color_refresh()          # ô màu chữ hiện đúng màu đã lưu
            self._cap_outline_refresh()
            self.cap_delay.setValue(int(round(float(layout.get("cap_delay", 0.12))
                                              * 1000)))
            self.cap_hook.setChecked(bool(layout.get("cap_hook", False)))
            self.canvas.show_hook(self.cap_hook.isChecked())   # khớp preview HOOK
            self.canvas.set_hook_geom(float(layout.get("hook_nx", 0.5)),
                                      float(layout.get("hook_ny", 0.10)),
                                      float(layout.get("hook_size", 0) or 0))
            self.blur_amt.setValue(int(layout.get("blur_amt", 22)))
            sv = float(layout.get("speed", 1.0))
            for i in range(self.speed_cb.count()):
                if abs(float(self.speed_cb.itemText(i).rstrip("x")) - sv) < 0.001:
                    self.speed_cb.setCurrentIndex(i); break
            pv = float(layout.get("pitch", 1.0))
            for i in range(self.voice_cb.count()):
                if abs(float(self.voice_cb.itemData(i)) - pv) < 0.001:
                    self.voice_cb.setCurrentIndex(i); break
            # hook-first + nhạc nền + logo
            self.hook_first_chk.setChecked(bool(layout.get("hook_first")))
            self.fx_fade_chk.setChecked(bool(layout.get("fx_fade", True)))
            self.fx_whoosh_chk.setChecked(bool(layout.get("fx_whoosh", True)))
            self.flip_h_chk.setChecked(bool(layout.get("flip_h", False)))
            self._fx_sfx_dir = layout.get("fx_sfx_dir", "") or ""
            self._fx_sfx_update()
            bi = self.bgm_mode.findData(layout.get("bgm_mode", "off"))
            if bi >= 0:
                self.bgm_mode.setCurrentIndex(bi)
            self._bgm_dir = layout.get("bgm_dir", "") or ""
            self._bgm_file = layout.get("bgm_file", "") or ""
            self.bgm_vol.setValue(int(float(layout.get("bgm_vol", 0.15)) * 100))
            self.orig_vol.setValue(int(float(layout.get("orig_vol", 1.0)) * 100))
            self._bgm_mode_ui()
            # lồng tiếng AI (voice để "pending" — list giọng nạp nền xong
            # sẽ tự chọn lại; _collect_layout vẫn trả pending nếu chưa kịp)
            self._dub_voice_pending = layout.get("dub_voice", "") or ""
            di = self.dub_lang.findData(layout.get("dub_lang", "") or "")
            if di >= 0:
                self.dub_lang.setCurrentIndex(di)
            self._dub_lang_ui()
            dv = self.dub_voice.findData(self._dub_voice_pending)
            if dv >= 0:
                self.dub_voice.setCurrentIndex(dv)
            self.dub_mute_chk.setChecked(bool(layout.get("dub_mute", False)))
            dmi = self.dub_mode.findData(layout.get("dub_mode", "natural"))
            if dmi >= 0:
                self.dub_mode.setCurrentIndex(dmi)
            self._logo_path = layout.get("logo_path", "") or ""
            self.logo_lbl.setText(f"Logo: {self._logo_path}" if self._logo_path
                                  else "(chưa có logo)")
            li = self.logo_pos.findData(layout.get("logo_pos", "tr"))
            if li >= 0:
                self.logo_pos.setCurrentIndex(li)
            self.logo_size.setValue(int(float(layout.get("logo_size", 0.14)) * 100))
            self.logo_op.setValue(int(float(layout.get("logo_op", 0.9)) * 100))
            # ---- CHỮ AI ĐỌC (thuyết minh) ----
            # KIỂU chạy chữ: ưu tiên key MỚI narr_preset; mẫu CŨ chỉ có narr_same
            # -> suy ra ('' -> NARR_SAME_LABEL nếu narr_same True, hoặc "Trắng
            # đơn giản" giữ nét plain + màu accent cũ nếu narr_same False).
            np_name = layout.get("narr_preset", "") or ""
            if not np_name:
                np_name = (NARR_SAME_LABEL if bool(layout.get("narr_same", False))
                           else "Trắng đơn giản")
            npi = self.narr_preset.findText(np_name)
            self.narr_preset.setCurrentIndex(max(0, npi))
            # MÀU chữ / viền: '' = theo kiểu. Mẫu CŨ luôn lưu narr_color (1 trong
            # 5 màu) -> vẫn dùng làm override để giữ nguyên màu người dùng đã chọn.
            self._narr_color = layout.get("narr_color", "") or ""
            self._narr_outline = layout.get("narr_outline", "") or ""
            self.narr_ow.setValue(int(round(float(layout.get("narr_ow", 0) or 0)
                                            * 100)))
            self._narr_color_refresh()
            self._narr_outline_refresh()
            self.narr_italic.setChecked(bool(layout.get("narr_italic", True)))
            nsz = float(layout.get("narr_size", 0) or 0)
            if nsz:
                self.narr_size.setValue(int(round(nsz * 1000)))
            self.canvas.set_narr_geom(float(layout.get("narr_ny", 0.62)),
                                      nsz)
            # ---- KIỂU CHỮ HOA từng phần chữ (đặt TRƯỚC refresh để preview áp
            # đúng hoa/thường ngay lúc mở mẫu) ----
            for cb, key in ((self.cap_case, "cap_case"),
                            (self.narr_case, "narr_case"),
                            (self.hook_case, "hook_case"),
                            (self.part_case, "part_case")):
                ci = cb.findData(layout.get(key, "") or "")
                cb.setCurrentIndex(max(0, ci))
            self._refresh_narr()           # áp màu/cỡ/viền/hoa đã lưu vào ô AI kể
            self.canvas.set_cap_top(layout.get("cap_ny", 0.78))
            self._refresh_cap()          # áp cỡ/màu/viền/font/hoa đã lưu vào ô phụ đề
            self.canvas.show_cap(self.cap_chk.isChecked())
            for d in layout.get("layers", []):
                lid = self._add(is_part=d.get("is_part", False), data=d)
                self.canvas.set_text_center(lid, d.get("nx", 0.5), d.get("ny", 0.5))
        else:
            l1 = self._add(is_part=False); self.canvas.set_text_center(l1, 0.5, 0.9)
            l2 = self._add(is_part=True); self.canvas.set_text_center(l2, 0.5, 0.1)

    def _add(self, is_part=False, data=None):
        lid = self._next; self._next += 1
        row = _LayerRow(lid, self._sync, self._remove, is_part)
        if data:
            row.set_data(data)
        self.rows[lid] = row; self.box.addWidget(row)
        self._sync(lid)
        return lid

    def _add_title(self):
        """Thêm lớp chữ TỰ ĐIỀN tiêu đề AI của từng clip (placeholder {title})."""
        lid = self._add(is_part=False, data={"text": "{title}"})
        self.canvas.set_text_center(lid, 0.5, 0.18)

    def _remove(self, lid):
        row = self.rows.pop(lid, None)
        if row:
            row.setParent(None)
        self.canvas.remove_text(lid)

    def _sync(self, lid):
        row = self.rows.get(lid)
        if not row:
            return
        d = row.data()
        preview = (d["text"].replace("{n}", "1")
                   .replace("{title}", "Tiêu đề ví dụ của clip"))
        if d["is_part"] and "{n}" not in d["text"] and "{title}" not in d["text"]:
            preview = f'{d["text"]} 1'.strip() if d["text"] else "Part 1"
        # KIỂU CHỮ HOA (khớp render_overlay_png): lớp Part -> part_case; các lớp
        # khác (tiêu đề/hook/cố định) -> hook_case. Áp lên CHỮ xem trước.
        case = (self.part_case.currentData() if d.get("is_part")
                else self.hook_case.currentData()) or ""
        if case:
            preview = apply_case(preview, case)
        self.canvas.upsert_text(lid, d, preview)

    def _sync_all_cases(self, *_):
        """Đổi Chữ hoa (Tiêu đề/Hook hoặc Part) -> vẽ lại MỌI lớp chữ + ô HOOK
        xem trước với kiểu hoa mới NGAY."""
        for lid in list(self.rows):
            self._sync(lid)
        # ô HOOK xem trước (không phải _LayerRow) cũng theo hook_case
        hb = self.canvas.hook_box
        txt = apply_case("HOOK GIẬT TÍT", self.hook_case.currentData() or "")
        hb.apply(dict(hb.d), txt)

    def _on_resized(self, lid, frac):
        row = self.rows.get(lid)
        if row:
            row.set_size_fraction(frac)

    # ---- BẤM hộp preview -> nhảy tới nhóm chỉnh bên phải ----
    def _on_box_select(self, lid):
        """Hộp chữ trong khung preview được BẤM -> cuộn panel phải tới đúng nhóm
        chỉnh + làm nổi ~1s. lid đặc biệt: -99 = Phụ đề (cap_box), -97 = Chữ AI
        kể (narr_box), -98 = HOOK (thuộc nhóm Phụ đề); lid dương = 1 lớp chữ
        (_LayerRow) trong nhóm Lớp chữ."""
        target = None       # widget nhóm để cuộn rscroll tới
        inner = None        # widget con trong scroll nội bộ (1 _LayerRow)
        if lid == -99 or lid == -98:            # phụ đề gốc / hook -> nhóm Phụ đề
            target = getattr(self, "_grp_cap", None)
        elif lid == -97:                        # chữ AI kể -> nhóm Chữ AI đọc
            target = getattr(self, "_grp_narr", None)
        else:                                   # lớp chữ (Part/tiêu đề/cố định)
            row = self.rows.get(lid)
            if row is not None:
                target = getattr(self, "_grp_layers", None)
                inner = row
        if target is None:
            return
        # cuộn panel phải chính tới NHÓM, rồi cuộn scroll nội bộ tới đúng _LayerRow
        rs = getattr(self, "_rscroll", None)
        if rs is not None:
            rs.ensureWidgetVisible(target, 0, 0)
        if inner is not None:
            ls = getattr(self, "_layer_scroll", None)
            if ls is not None:
                ls.ensureWidgetVisible(inner, 0, 0)
            self._flash_group(inner)
        else:
            self._flash_group(target)

    def _flash_group(self, w):
        """Làm nổi tạm widget (viền + nền sáng) ~1s rồi trả style cũ -> user thấy
        rõ nhóm/hàng vừa nhảy tới. Dùng objectName riêng nên selector CHỈ áp cho
        chính widget đó, KHÔNG lan xuống con. Chỉ 1 widget nổi 1 lúc."""
        if w is None:
            return
        # khôi phục widget đang nổi trước đó (nếu bấm liên tiếp)
        prev = getattr(self, "_hl_widget", None)
        if prev is not None and prev is not w:
            try:
                prev.setStyleSheet(self._hl_qss)
            except RuntimeError:
                pass
        self._hl_widget = w
        self._hl_qss = w.styleSheet()
        # gán objectName tạm (nếu chưa có) để selector nhắm ĐÚNG widget này
        nm = w.objectName()
        if not nm:
            nm = f"_hl_{id(w)}"
            w.setObjectName(nm)
        w.setStyleSheet(
            self._hl_qss
            + f"\n#{nm}{{background:rgba(110,139,255,0.30);"
              "border:2px solid #6E8BFF; border-radius:11px;}}")

        def _restore():
            if getattr(self, "_hl_widget", None) is w:
                try:
                    w.setStyleSheet(self._hl_qss)
                except RuntimeError:
                    pass
                self._hl_widget = None
        QTimer.singleShot(1000, _restore)

    # ---- Lồng tiếng AI ----
    def _dub_lang_ui(self):
        """Đổi ngôn ngữ -> nạp danh sách giọng ĐẦY ĐỦ của ngôn ngữ đó
        (edge-tts, thread nền + cache — không block UI)."""
        lang = self.dub_lang.currentData() or ""
        on = bool(lang)
        self.dub_voice.setEnabled(on)
        self.dub_mute_chk.setEnabled(on)
        self.dub_mode.setEnabled(on)
        self.dub_prev_btn.setEnabled(on)
        if not lang:
            self.dub_voice.blockSignals(True)
            self.dub_voice.clear()
            self.dub_voice.blockSignals(False)
            return
        if lang in _DUB_VOICE_CACHE:
            self._fill_dub_voices(_DUB_VOICE_CACHE[lang])
            return
        # Chưa có cache -> hiện chờ + nạp ở thread nền (QTimer poll như
        # pattern _write_caption bên studio_page — edge-tts gọi mạng).
        self.dub_voice.blockSignals(True)
        self.dub_voice.clear()
        self.dub_voice.addItem("(đang tải danh sách giọng…)", "")
        self.dub_voice.blockSignals(False)
        if lang in self._dub_loading:
            return
        self._dub_loading.add(lang)
        out: list = []

        def bg():
            try:
                from app.core.dubbing import list_voices_for
                out.append(list_voices_for(lang)
                           or list(DUB_VOICES.get(lang, [])))
            except Exception:  # noqa: BLE001
                out.append(list(DUB_VOICES.get(lang, [])))

        import threading
        threading.Thread(target=bg, daemon=True).start()
        timer = QTimer(self)

        def poll():
            if not out:
                return
            timer.stop(); timer.deleteLater()
            self._dub_loading.discard(lang)
            _DUB_VOICE_CACHE[lang] = out[0]
            if (self.dub_lang.currentData() or "") == lang:
                self._fill_dub_voices(out[0])

        timer.timeout.connect(poll)
        timer.start(150)

    def _fill_dub_voices(self, voices):
        """Đổ list giọng vào combo, giữ lựa chọn đang có / voice của layout."""
        want = self.dub_voice.currentData() or self._dub_voice_pending
        self.dub_voice.blockSignals(True)
        self.dub_voice.clear()
        for label, vid in voices:
            self.dub_voice.addItem(label, vid)
        if want:
            i = self.dub_voice.findData(want)
            if i >= 0:
                self.dub_voice.setCurrentIndex(i)
            elif want == self._dub_voice_pending:
                # voice lưu trong mẫu cũ không có trong list (vd offline chỉ
                # còn list tĩnh) -> vẫn giữ để layout round-trip không mất
                self.dub_voice.addItem(want, want)
                self.dub_voice.setCurrentIndex(self.dub_voice.count() - 1)
        self.dub_voice.blockSignals(False)
        self._dub_voice_pending = ""

    def _dub_preview(self):
        """Nghe thử giọng đang chọn: synth 1 câu ở thread nền -> phát luôn.

        Phát bằng winsound (WAV, stdlib) thay vì QMediaPlayer: backend
        QtMultimedia trên nhiều máy Windows (wheel PyQt6 thiếu DLL FFmpeg)
        chết im lặng -> bấm không kêu gì. winsound đi thẳng WinMM, luôn kêu."""
        voice = self.dub_voice.currentData() or self._dub_voice_pending
        if not voice:
            return
        import glob, os, subprocess, tempfile, threading, uuid, winsound
        # dừng tiếng demo cũ (nếu đang kêu) TRƯỚC khi dọn file
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError:
            pass
        self.dub_prev_btn.setEnabled(False)
        self.dub_prev_btn.setText("Đang đọc…")
        tmp = tempfile.gettempdir()
        # dọn demo cũ (tên duy nhất mỗi lần -> không đụng file lần trước
        # có thể còn bị giữ handle)
        for old in glob.glob(os.path.join(tmp, "_dubdemo_*.*")):
            try:
                os.remove(old)
            except OSError:
                pass
        uid = uuid.uuid4().hex[:8]
        mp3 = os.path.join(tmp, f"_dubdemo_{uid}.mp3")
        wav = os.path.join(tmp, f"_dubdemo_{uid}.wav")

        def work():
            try:
                from app.core.dubbing import synth_demo
                if not synth_demo(voice, mp3):
                    self._dub_demo_ready.emit("")
                    return
                # mp3 -> wav (winsound chỉ phát WAV)
                import shutil
                from config import settings
                from app.core.ffmpeg_utils import _CREATE_NO_WINDOW
                ff = (shutil.which("ffmpeg") or settings.FFMPEG_PATH
                      or r"C:\ffmpeg\ffmpeg.exe")
                r = subprocess.run(
                    [ff, "-nostdin", "-y", "-i", mp3, wav],
                    capture_output=True, timeout=60,
                    creationflags=_CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL)
                ok = (r.returncode == 0 and os.path.exists(wav)
                      and os.path.getsize(wav) > 5000)
                self._dub_demo_ready.emit(wav if ok else "")
            except Exception:  # noqa: BLE001
                self._dub_demo_ready.emit("")

        threading.Thread(target=work, daemon=True).start()

    def _dub_demo_done(self):
        """Trả nút Nghe thử về bình thường (tiếng vẫn kêu nốt ở nền;
        bấm Nghe thử lần nữa sẽ tự ngắt tiếng cũ)."""
        self.dub_prev_btn.setText("🔊 Nghe thử")
        self.dub_prev_btn.setEnabled(bool(self.dub_lang.currentData()))

    def _play_dub_demo(self, path):
        import os
        self._dub_demo_done()
        if not path or not os.path.exists(path):
            QMessageBox.information(
                self, "Nghe thử lỗi",
                "Không đọc thử được giọng này (kiểm tra mạng + ffmpeg rồi "
                "thử lại).")
            return
        import winsound
        try:
            winsound.PlaySound(
                path, winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_NODEFAULT)
        except RuntimeError as e:
            QMessageBox.warning(
                self, "Nghe thử lỗi",
                f"Không phát được âm thanh trên máy này:\n{e}")

    def _demo_voice_pitch(self):
        """Nghe thử ĐỔI CAO ĐỘ giọng gốc: đọc 1 câu mẫu (edge-tts) rồi áp đúng
        bộ lọc pitch (giống lúc xuất) -> nghe rõ trầm/cao/robot. winsound WAV."""
        import glob, os, subprocess, tempfile, threading, uuid, winsound
        from PyQt6.QtCore import QTimer
        pitch = float(self.voice_cb.currentData() or 1.0)
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError:
            pass
        self.voice_demo_btn.setEnabled(False); self.voice_demo_btn.setText("Đang đọc…")
        tmp = tempfile.gettempdir()
        for old in glob.glob(os.path.join(tmp, "_pitchdemo_*.*")):
            try:
                os.remove(old)
            except OSError:
                pass
        uid = uuid.uuid4().hex[:8]
        mp3 = os.path.join(tmp, f"_pitchdemo_{uid}.mp3")
        wav = os.path.join(tmp, f"_pitchdemo_{uid}.wav")
        out: list = []

        def work():
            try:
                from app.core.dubbing import synth_demo
                if not synth_demo("vi-VN-NamMinhNeural", mp3,
                                  text="Đây là giọng gốc sau khi đổi cao độ."):
                    out.append(""); return
                import shutil
                from config import settings
                from app.core.ffmpeg_utils import _CREATE_NO_WINDOW
                ff = (shutil.which("ffmpeg") or settings.FFMPEG_PATH or "ffmpeg")
                if abs(pitch - 1.0) < 0.01:
                    af = "aresample=48000"
                else:                       # đổi cao độ, giữ tốc độ (như lúc xuất)
                    af = (f"asetrate=48000*{pitch:.4f},aresample=48000,"
                          f"atempo={1.0/pitch:.4f}")
                r = subprocess.run(
                    [ff, "-nostdin", "-y", "-i", mp3, "-af", af, wav],
                    capture_output=True, timeout=60,
                    creationflags=_CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
                out.append(wav if (r.returncode == 0 and os.path.exists(wav)
                                   and os.path.getsize(wav) > 3000) else "")
            except Exception:  # noqa: BLE001
                out.append("")

        threading.Thread(target=work, daemon=True).start()
        t = QTimer(self)

        def poll():
            if not out:
                return
            t.stop()
            self.voice_demo_btn.setText("🔊 Nghe"); self.voice_demo_btn.setEnabled(True)
            if not out[0]:
                QMessageBox.information(self, "Nghe thử lỗi",
                                       "Không nghe thử được (cần mạng + ffmpeg).")
                return
            try:
                winsound.PlaySound(out[0], winsound.SND_FILENAME
                                   | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except RuntimeError:
                pass
        t.timeout.connect(poll); t.start(200)

    def done(self, r):  # noqa: N802 (tên theo Qt)
        """Đóng dialog -> ngắt tiếng nghe thử còn kêu dở (winsound chạy nền)."""
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:  # noqa: BLE001
            pass
        super().done(r)

    # ---- Nhạc nền + logo ----
    def _bgm_mode_ui(self):
        m = self.bgm_mode.currentData()
        self.bgm_pick.setEnabled(m != "off")
        self.bgm_pick.setText("Chọn thư mục…" if m == "random" else
                              "Chọn bài…" if m == "fixed" else "Chọn…")
        self._bgm_lbl_update()

    def _bgm_lbl_update(self):
        m = self.bgm_mode.currentData()
        if m == "random":
            self.bgm_lbl.setText(f"Thư mục nhạc: {self._bgm_dir or '(chưa chọn)'}")
        elif m == "fixed":
            self.bgm_lbl.setText(f"Bài: {self._bgm_file or '(chưa chọn)'}")
        else:
            self.bgm_lbl.setText("")

    def _pick_bgm_src(self):
        from PyQt6.QtWidgets import QFileDialog
        m = self.bgm_mode.currentData()
        if m == "random":
            d = QFileDialog.getExistingDirectory(
                self, "Chọn THƯ MỤC chứa nhạc nền (mp3/m4a/wav...)",
                self._bgm_dir or "")
            if d:
                self._bgm_dir = d
        elif m == "fixed":
            f, _ = QFileDialog.getOpenFileName(
                self, "Chọn bài nhạc nền", self._bgm_file or "",
                "Nhạc (*.mp3 *.m4a *.aac *.wav *.ogg *.flac)")
            if f:
                self._bgm_file = f
        self._bgm_lbl_update()

    def _fx_sfx_update(self):
        self.fx_sfx_lbl.setText(
            f"Thư mục tiếng động: {self._fx_sfx_dir or '(để trống = tiếng tổng hợp)'}")

    def _pick_fx_sfx_dir(self):
        from PyQt6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(
            self, "Chọn THƯ MỤC chứa tiếng động chuyển đoạn (mp3/wav/m4a...)",
            self._fx_sfx_dir or "")
        if d:
            self._fx_sfx_dir = d
            self._fx_sfx_update()

    def _clear_fx_sfx_dir(self):
        self._fx_sfx_dir = ""
        self._fx_sfx_update()

    def _pick_logo(self):
        from PyQt6.QtWidgets import QFileDialog
        f, _ = QFileDialog.getOpenFileName(
            self, "Chọn logo kênh (PNG nền trong suốt đẹp nhất)",
            self._logo_path or "", "Ảnh (*.png *.jpg *.jpeg *.webp)")
        if f:
            self._logo_path = f
            self.logo_lbl.setText(f"Logo: {f}")

    def _gather(self):
        return [b.export_data() for b in self.canvas.texts.values()]

    def _cap_eff_color(self):
        """Màu chữ hiệu lực: user chọn (ghi đè) hoặc màu mặc định của KIỂU."""
        if self._capcolor:
            return self._capcolor
        p = CAPTION_PRESETS.get(self.cap_preset.currentText()) or {}
        # kiểu 'cả câu' phần lớn chữ TRẮNG (chỉ từ đang nói vàng) -> preview trắng
        if p.get("mode") == "active":
            return p.get("rest", "#FFFFFF")
        return p.get("color", "#FFFFFF")

    def _set_cap_color(self, hexv):
        self._capcolor = hexv or ""
        if hasattr(self, "_cap_color_refresh"):
            self._cap_color_refresh()
        self._refresh_cap()

    def _set_cap_outline(self, hexv):
        self._cap_outline = hexv or ""
        if hasattr(self, "_cap_outline_refresh"):
            self._cap_outline_refresh()
        self._refresh_cap()

    def _narr_eff_color(self):
        """Màu chữ AI kể hiệu lực: user chọn (ghi đè) hoặc màu của KIỂU đang
        chọn cho chữ AI; '(giống phụ đề gốc)' -> theo màu phụ đề gốc."""
        if self._narr_color:
            return self._narr_color
        name = self.narr_preset.currentText()
        if name == NARR_SAME_LABEL:
            return self._cap_eff_color()
        p = CAPTION_PRESETS.get(name) or {}
        if p.get("mode") == "active":
            return p.get("rest", "#FFFFFF")
        return p.get("color", _NARR_COLOR_DEFAULT)

    def _set_narr_color(self, hexv):
        self._narr_color = hexv or ""
        if hasattr(self, "_narr_color_refresh"):
            self._narr_color_refresh()
        self._refresh_narr()

    def _set_narr_outline(self, hexv):
        self._narr_outline = hexv or ""
        if hasattr(self, "_narr_outline_refresh"):
            self._narr_outline_refresh()
        self._refresh_narr()

    def _cap_drag_size(self, frac):
        """User kéo góc ô caption -> cập nhật thanh Cỡ = đúng cỡ vừa kéo (để lưu)."""
        val = max(self.cap_size.minimum(),
                  min(self.cap_size.maximum(), int(round(frac * 1000))))
        self.cap_size.blockSignals(True)
        self.cap_size.setValue(val)
        self.cap_size.blockSignals(False)
        self.cap_lbl_sz.setText(f"{val / 10:.1f}%")

    def _refresh_cap_soon(self, *_):
        """Hoãn vẽ lại ~80ms -> kéo thanh trượt nhanh KHÔNG vẽ liên tục (đỡ đơ)."""
        t = getattr(self, "_cap_timer", None)
        if t is None:
            t = self._cap_timer = QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(self._refresh_cap)
        t.start(80)

    def _refresh_narr(self, *_):
        """Cập nhật ô CHỮ AI KỂ xem trước theo ĐÚNG kiểu/màu/viền/cỡ/nghiêng/hoa
        đang chọn (SÁT .ass Style Narrate): narr_preset='(giống phụ đề gốc)' ->
        vẽ GIỐNG cap_box (kiểu + viền/box của phụ đề gốc); chọn preset khác ->
        theo preset đó. narr_color/outline/ow ghi đè; in nghiêng -> font italic;
        hoa/thường theo narr_case."""
        nb = self.canvas.narr_box
        ny = nb.y() / FH                 # giữ vị trí dọc đang kéo
        name = self.narr_preset.currentText()
        # "(giống phụ đề gốc)" -> lấy kiểu của phụ đề gốc (như build_ass: np = p)
        preset_name = (self.cap_preset.currentText()
                       if name == NARR_SAME_LABEL else name)
        d = _caption_box_data(
            preset_name,
            size=self.narr_size.value() / 1000.0,
            font=self.cap_font.currentText(),   # Narrate dùng cùng font phụ đề
            ny=ny, color=self._narr_color, outline=self._narr_outline,
            ow=self.narr_ow.value() / 100.0,
            italic=self.narr_italic.isChecked())
        text = apply_case("Chữ AI kể", self.narr_case.currentData() or "")
        nb.apply(d, text)
        nb.setPos(FW / 2 - nb.w / 2, max(0.0, ny) * FH)

    def _refresh_narr_soon(self, *_):
        t = getattr(self, "_narr_timer", None)
        if t is None:
            t = self._narr_timer = QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(self._refresh_narr)
        t.start(80)

    def _narr_drag_size(self, frac):
        """Kéo góc ô CHỮ AI KỂ -> đồng bộ thanh Cỡ (để LƯU narr_size)."""
        val = max(self.narr_size.minimum(),
                  min(self.narr_size.maximum(), int(round(frac * 1000))))
        self.narr_size.blockSignals(True)
        self.narr_size.setValue(val)
        self.narr_size.blockSignals(False)
        self.narr_sz_lbl.setText(f"{val / 10:.1f}%")

    def _refresh_cap(self, *_):
        """Cập nhật ô PHỤ ĐỀ xem trước theo ĐÚNG kiểu/màu/viền/cỡ/font/hoa đang
        chọn (SÁT với .ass lúc xuất): màu = cap_color hoặc màu preset; viền =
        cap_outline + cap_ow (0 -> theo preset; glow -> viền neon; box -> nền
        hộp); cỡ = cap_size; font = cap_font; hoa/thường = cap_case."""
        cb = self.canvas.cap_box
        ny = cb.y() / FH                 # giữ nguyên vị trí dọc đang kéo
        d = _caption_box_data(
            self.cap_preset.currentText(),
            size=self.cap_size.value() / 1000.0,
            font=self.cap_font.currentText(),
            ny=ny, color=self._capcolor, outline=self._cap_outline,
            ow=self.cap_ow.value() / 100.0)
        text = apply_case("Phụ đề chạy chữ", self.cap_case.currentData() or "")
        cb.apply(d, text)
        self.canvas.set_cap_top(ny)      # đặt lại đỉnh tại vị trí cũ
        # narr "(giống phụ đề gốc)" ăn theo kiểu/font phụ đề gốc -> cập nhật cùng
        if (getattr(self, "narr_preset", None) is not None
                and self.narr_preset.currentText() == NARR_SAME_LABEL):
            self._refresh_narr()

    # ---- DEMO kiểu chữ: tạo clip ~6s rồi phát để xem chữ chạy ----
    def _demo_caption(self):
        import os, tempfile, threading, subprocess, shutil
        from app.core import captions
        from config import settings
        self.cap_demo_btn.setEnabled(False)
        self.cap_demo_btn.setText("Đang tạo...")
        preset = self.cap_preset.currentText()
        font = self.cap_font.currentText()
        size_px = int(self.cap_size.value() / 1000.0 * 1920)
        color = self._capcolor                       # '' = giữ màu của kiểu
        bg = self._frame_path if (self._frame_path
                                  and os.path.exists(self._frame_path)) else ""

        def work():
            try:
                # câu mẫu + mốc TỪNG TỪ giả lập (~6s)
                sent = "Nói tới đâu chữ chạy tới đó nhìn cực kỳ cuốn luôn nha".split()
                words, t = [], 0.4
                for w in sent:
                    d = 0.32 + min(0.30, len(w) * 0.03)
                    words.append({"word": w, "start": round(t, 2),
                                  "end": round(t + d, 2)})
                    t += d + 0.05
                total = round(t + 0.7, 2)
                tmp = tempfile.gettempdir()
                # dọn demo cũ (tên duy nhất mỗi lần -> không đụng file đang bị
                # QMediaPlayer của lần xem trước giữ handle)
                import glob as _glob
                for old in _glob.glob(os.path.join(tmp, "_capdemo*.mp4")):
                    try:
                        os.remove(old)
                    except OSError:
                        pass
                ass = os.path.join(tmp, "_capdemo.ass")
                captions.build_ass(words, [[0, total]], ass, out_w=1080,
                                   out_h=1920, font=font, size=size_px,
                                   color=color, ny=0.5, preset=preset)
                import uuid as _uuid
                out = os.path.join(tmp, f"_capdemo_{_uuid.uuid4().hex[:8]}.mp4")
                ff = (shutil.which("ffmpeg") or settings.FFMPEG_PATH
                      or r"C:\ffmpeg\ffmpeg.exe")
                assesc = ass.replace("\\", "/").replace(":", "\\:")
                if bg:
                    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
                          "crop=1080:1920,boxblur=10," f"subtitles='{assesc}'")
                    cmd = [ff, "-y", "-loop", "1", "-i", bg, "-t", f"{total}",
                           "-vf", vf]
                else:
                    cmd = [ff, "-y", "-f", "lavfi", "-i",
                           f"color=c=0x1A2233:s=1080x1920:d={total}",
                           "-vf", f"subtitles='{assesc}'"]
                cmd += ["-r", "25", "-pix_fmt", "yuv420p", "-c:v", "libx264",
                        "-preset", "ultrafast", out]
                cmd.insert(1, "-nostdin")
                # CREATE_NO_WINDOW: bản .exe windowed không có console -> thiếu
                # cờ này sẽ bật cửa sổ cmd đen chiếm focus suốt lúc render demo
                from app.core.ffmpeg_utils import _CREATE_NO_WINDOW
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=120, creationflags=_CREATE_NO_WINDOW,
                                   stdin=subprocess.DEVNULL)
                self._demo_ready.emit(out if (r.returncode == 0
                                              and os.path.exists(out)) else "")
            except Exception:  # noqa: BLE001
                self._demo_ready.emit("")

        threading.Thread(target=work, daemon=True).start()

    def _play_demo(self, path):
        import os
        self.cap_demo_btn.setEnabled(True)
        self.cap_demo_btn.setText("Demo")
        if not path or not os.path.exists(path):
            QMessageBox.information(self, "Demo lỗi",
                                   "Không tạo được demo (kiểm tra ffmpeg).")
            return
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtMultimediaWidgets import QVideoWidget
        from PyQt6.QtCore import QUrl
        dlg = QDialog(self); dlg.setWindowTitle("Demo kiểu chữ: " +
                                                self.cap_preset.currentText())
        dlg.resize(380, 720)
        v = QVBoxLayout(dlg)
        vw = QVideoWidget(); vw.setMinimumHeight(560); v.addWidget(vw, 1)
        pl = QMediaPlayer(); ao = QAudioOutput(); ao.setVolume(0)
        pl.setAudioOutput(ao); pl.setVideoOutput(vw)
        pl.setSource(QUrl.fromLocalFile(path))
        try:
            pl.setLoops(QMediaPlayer.Loops.Infinite)     # lặp để xem kỹ
        except Exception:  # noqa: BLE001
            pl.mediaStatusChanged.connect(
                lambda s: pl.play() if s == QMediaPlayer.MediaStatus.EndOfMedia
                else None)
        # PHÒNG HỜ: máy nào QMediaPlayer vẫn lỗi (codec/backend) -> đóng dialog
        # và mở file demo bằng trình phát mặc định của Windows, không im lặng.
        player_err = []

        def on_err(_e, msg):
            if not player_err:
                player_err.append(msg or "không rõ")
                dlg.reject()
        pl.errorOccurred.connect(on_err)
        dlg._pl = pl; dlg._ao = ao
        info = QLabel("Phát lặp lại. Ưng thì bấm Đóng — kiểu này đã được chọn sẵn.")
        info.setStyleSheet("color:#9AA6BF; font-size:12px;"); v.addWidget(info)
        cb = QPushButton("Đóng"); cb.setProperty("primary", True)
        cb.clicked.connect(lambda: (pl.stop(), dlg.accept())); v.addWidget(cb)
        pl.play()
        dlg.exec()
        # GIẢI PHÓNG file: chỉ stop() thì backend Windows Media Foundation vẫn
        # giữ handle -> ffmpeg lần Demo sau không ghi đè được. Dialog cũng phải
        # deleteLater để không tích lũy player suốt phiên chỉnh mẫu.
        pl.stop()
        pl.setSource(QUrl())
        pl.setVideoOutput(None)
        dlg.deleteLater()
        if player_err:
            try:
                os.startfile(path)               # trình phát mặc định Windows
                QMessageBox.information(
                    self, "Demo (dự phòng)",
                    "Trình phát trong app lỗi — demo đã mở bằng trình phát "
                    "mặc định của Windows.\nKiểu chữ này vẫn được chọn sẵn.")
            except OSError:
                QMessageBox.warning(
                    self, "Demo lỗi",
                    f"Không phát được demo: {player_err[0]}\nFile: {path}")

    def _reload_tmpl(self, select=None):
        self.tmpl.blockSignals(True); self.tmpl.clear()
        self.tmpl.addItem("(mẫu hiện tại)", None)
        for t in services.list_templates():
            self.tmpl.addItem(t["name"], t["name"])
        if select:
            i = self.tmpl.findData(select)
            if i >= 0:
                self.tmpl.setCurrentIndex(i)
        self.tmpl.blockSignals(False)

    def _collect_layout(self):
        """Gom ĐẦY ĐỦ layout (khung + chữ + PHỤ ĐỀ + trim) để lưu/trả về.
        TRƯỚC ĐÂY lưu mẫu chỉ lấy canvas -> mất cài đặt sub -> đã sửa."""
        lay = self.canvas.get_layout(self._gather())
        lay["trim_black"] = self.trim_chk.isChecked()
        lay["fit_src"] = self.fit_src_chk.isChecked()
        lay["captions"] = self.cap_chk.isChecked()
        lay["cap_font"] = self.cap_font.currentText()
        lay["cap_size"] = self.cap_size.value() / 1000.0
        lay["cap_color"] = self._capcolor          # '' = theo kiểu
        lay["cap_outline"] = self._cap_outline      # '' = theo kiểu
        lay["cap_ow"] = self.cap_ow.value() / 100.0  # 0 = theo kiểu
        lay["cap_preset"] = self.cap_preset.currentText()
        lay["cap_delay"] = self.cap_delay.value() / 1000.0
        lay["cap_hook"] = self.cap_hook.isChecked()
        lay.update(self.canvas.hook_geom())   # hook_nx/hook_ny/hook_size
        lay["cap_ny"] = self.canvas.cap_ny()
        lay["blur_amt"] = self.blur_amt.value()
        lay["speed"] = float(self.speed_cb.currentText().rstrip("x") or 1.0)
        lay["pitch"] = float(self.voice_cb.currentData() or 1.0)
        lay["hook_first"] = self.hook_first_chk.isChecked()
        lay["fx_fade"] = self.fx_fade_chk.isChecked()
        lay["fx_whoosh"] = self.fx_whoosh_chk.isChecked()
        lay["fx_sfx_dir"] = self._fx_sfx_dir
        lay["flip_h"] = self.flip_h_chk.isChecked()
        lay["bgm_mode"] = self.bgm_mode.currentData() or "off"
        lay["bgm_dir"] = self._bgm_dir
        lay["bgm_file"] = self._bgm_file
        lay["bgm_vol"] = self.bgm_vol.value() / 100.0
        lay["orig_vol"] = self.orig_vol.value() / 100.0
        lay["dub_lang"] = self.dub_lang.currentData() or ""
        # list giọng còn đang nạp nền -> giữ voice của layout cũ (pending)
        lay["dub_voice"] = (self.dub_voice.currentData()
                            or self._dub_voice_pending or "")
        lay["dub_mute"] = self.dub_mute_chk.isChecked()
        lay["dub_mode"] = self.dub_mode.currentData() or "natural"
        lay["logo_path"] = self._logo_path
        lay["logo_pos"] = self.logo_pos.currentData() or "tr"
        lay["logo_size"] = self.logo_size.value() / 100.0
        lay["logo_op"] = self.logo_op.value() / 100.0
        # ---- CHỮ AI ĐỌC (thuyết minh) — Style Narrate của phụ đề recap ----
        # narr_color/outline: '' = theo kiểu chạy chữ của chữ AI.
        lay["narr_color"] = self._narr_color
        lay["narr_outline"] = self._narr_outline
        lay["narr_ow"] = self.narr_ow.value() / 100.0
        lay["narr_italic"] = bool(self.narr_italic.isChecked())
        # narr_preset: kiểu chạy chữ RIÊNG cho chữ AI ('(giống phụ đề gốc)' =
        # dùng Style Default). narr_same suy ra từ narr_preset (tương thích key
        # cũ — mẫu cũ đọc lại vẫn đúng).
        lay["narr_preset"] = self.narr_preset.currentText()
        lay["narr_same"] = (self.narr_preset.currentText() == NARR_SAME_LABEL)
        lay["narr_size"] = self.narr_size.value() / 1000.0
        lay.update(self.canvas.narr_geom())   # narr_ny (+ narr_size từ ô kéo)
        # narr_geom trả narr_size theo ô kéo -> đồng nhất với thanh trượt (cùng
        # nguồn px); giữ giá trị thanh trượt cho chắc (đã set ở trên).
        lay["narr_size"] = self.narr_size.value() / 1000.0
        # ---- KIỂU CHỮ HOA từng phần chữ ----
        lay["cap_case"] = self.cap_case.currentData() or ""
        lay["narr_case"] = self.narr_case.currentData() or ""
        lay["hook_case"] = self.hook_case.currentData() or ""
        lay["part_case"] = self.part_case.currentData() or ""
        return lay

    def _save_tmpl(self):
        """Lưu = GHI ĐÈ lên mẫu đang chọn; chưa chọn mẫu nào -> hỏi tên (lưu mới)."""
        name = self.tmpl.currentData()
        if not name:
            self._save_tmpl_new()
            return
        services.save_template(name, self._collect_layout())
        self._current_name = name
        self._db_changed = True
        QMessageBox.information(self, "Đã lưu", f"Đã cập nhật mẫu “{name}”.")

    def _save_tmpl_new(self):
        name, ok = QInputDialog.getText(self, "Lưu mẫu mới", "Tên mẫu:")
        if ok and name.strip():
            services.save_template(name.strip(), self._collect_layout())
            self._current_name = name.strip()
            self._db_changed = True
            self._reload_tmpl(select=name.strip())

    def _del_tmpl(self):
        name = self.tmpl.currentData()
        if not name:
            QMessageBox.information(self, "Chưa chọn mẫu",
                                   "Chọn 1 mẫu đã lưu trong danh sách để xóa.")
            return
        if QMessageBox.question(self, "Xóa mẫu", f"Xóa mẫu “{name}”?") \
                == QMessageBox.StandardButton.Yes:
            services.delete_template(name)
            self._current_name = ""
            self._db_changed = True
            self._reload_tmpl()

    def _load_tmpl(self):
        name = self.tmpl.currentData()
        if not name:
            return
        t = services.get_template(name)
        if not t:
            return
        for lid in list(self.rows):
            self._remove(lid)
        self._apply_layout(t)

    def _accept(self):
        self.layout_result = self._collect_layout()
        # LƯU LUÔN khi bấm "Xong". Chưa có mẫu -> HỎI TÊN (để studio dùng đúng mẫu
        # này, tránh lưu 1 nơi xuất 1 nơi).
        name = self.tmpl.currentData() or self._current_name
        if not name:
            name, ok = QInputDialog.getText(
                self, "Đặt tên mẫu",
                "Đặt tên mẫu để lưu (lần sau chọn lại + xuất theo mẫu này):",
                text="Mẫu của tôi")
            name = name.strip() if (ok and name.strip()) else "Mẫu của tôi"
        self._current_name = name
        try:
            services.save_template(name, self.layout_result)
            self._db_changed = True
        except Exception as e:  # noqa: BLE001
            self._save_failed = True
            # KHÔNG nuốt im lặng: dialog hứa "tự lưu khi bấm Xong" — lưu fail
            # mà báo 'Đã lưu' thì lần xuất sau dùng mẫu CŨ, user không hề biết.
            QMessageBox.warning(
                self, "Không lưu được mẫu",
                f"Lỗi khi lưu mẫu “{name}”: {e}\n\n"
                "Layout hiện tại VẪN được áp cho phiên này, nhưng CHƯA được "
                "lưu vào máy — hãy thử bấm 'Lưu mẫu' lại sau.")
        self.accept()
