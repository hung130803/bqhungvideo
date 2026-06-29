"""
Editor kiểu CapCut (mở từ nút "Chỉnh"):
- Khung 9:16 = NỀN (đen/trắng/mờ).
- KHỐI VIDEO: bấm chọn -> viền + nút kéo góc để phóng to/nhỏ, kéo để dời.
- Lớp chữ (cố định + Part) kéo-thả, cỡ/font/màu, nền bo góc.
- Trả về layout {video_rect:(cx,cy,scale), bg, layers:[...]} để áp cho mọi clip.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QGraphicsItem,
    QGraphicsLineItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsView, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from app import services
from app.core.captions import CAPTION_PRESETS

FW, FH = 348, 619          # khung xem trước TO hơn cho dễ nhìn (tỉ lệ 9:16)


class _NoWheelSlider(QSlider):
    """Thanh kéo KHÔNG đổi giá trị khi chỉ lăn chuột qua (phải bấm-kéo).
    Lăn chuột để CUỘN bảng thay vì lỡ tay đổi cỡ/độ rộng."""
    def wheelEvent(self, e):
        e.ignore()


class _NoWheelCombo(QComboBox):
    """Combo KHÔNG đổi lựa chọn khi lăn chuột qua."""
    def wheelEvent(self, e):
        e.ignore()


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


def _draw_text_path(p, path, color, outline_w, outline_color="#000000"):
    """Vẽ chữ: viền màu TRƯỚC (nếu có), tô màu chữ ĐÈ lên.
    outline_w <= 0 -> KHÔNG viền (chỉ tô màu chữ)."""
    if outline_w and outline_w >= 0.6:
        pen = QPen(QColor(outline_color), outline_w)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawPath(path)


def render_overlay_png(layers, part_no, out_w, out_h, path, title="",
                       title_vi="", video_px=None) -> bool:
    """Vẽ tất cả lớp chữ ra PNG trong suốt (dùng khi xuất). Trả True nếu có chữ.
    Placeholder: {n}->số Part, {title}->tiêu đề (Anh) gắn video, {title_vi}->Việt.
    Chữ quá dài TỰ CO NHỎ + bị CLAMP để KHÔNG bao giờ tràn ra ngoài khung.
    video_px=(vx,vy,vw,vh): vùng KHỐI VIDEO -> chữ bị đẩy ra dải nền, KHÔNG đè video."""
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
            # thu nhỏ sẵn (≤2x bề rộng khung) -> vẽ rất nhanh khi kéo/resize
            cap = int(FW * 2)
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

    def __init__(self, lid, on_resize=None, on_guide=None):
        super().__init__()
        self.lid = lid
        self.on_resize = on_resize
        self.on_guide = on_guide
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
        return _qfont(self.d.get("font", "Arial"), self.px)

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
                        self.d.get("outline_color", "#000000"))
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
    def __init__(self, on_resize=None):
        super().__init__()
        self.on_resize = on_resize
        self.setFixedSize(FW + 2, FH + 2)
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
        self.bg_solid = QGraphicsRectItem(0, 0, FW, FH)
        self.bg_solid.setPen(QPen(Qt.GlobalColor.transparent))
        self.bg_solid.setZValue(0)
        self.scene.addItem(self.bg_solid)
        self.bg_blur = QGraphicsPixmapItem(); self.bg_blur.setZValue(0)
        self.bg_blur.setCacheMode(
            QGraphicsPixmapItem.CacheMode.DeviceCoordinateCache)  # nền tĩnh -> cache
        self.scene.addItem(self.bg_blur)
        self.vbox = _VideoBox(on_guide=self._set_guides)
        self.scene.addItem(self.vbox)
        border = QGraphicsRectItem(0, 0, FW, FH)
        border.setPen(QPen(QColor("#3b82f6"), 2)); border.setZValue(30)
        self.scene.addItem(border)
        # vạch căn giữa (snap guide) — ẩn mặc định
        gpen = QPen(QColor("#FF3DAE"), 2, Qt.PenStyle.DashLine)
        self.gv = QGraphicsLineItem(FW / 2, 0, FW / 2, FH)
        self.gh = QGraphicsLineItem(0, FH / 2, FW, FH / 2)
        for g in (self.gv, self.gh):
            g.setPen(gpen); g.setZValue(40); g.setVisible(False)
            self.scene.addItem(g)
        self.texts: dict[int, _TextBox] = {}
        # ô PHỤ ĐỀ kéo-thả (chỉ để chọn VỊ TRÍ; không phải lớp chữ overlay)
        self.cap_box = _TextBox(-99, on_guide=self._set_guides)
        self.cap_box.apply({"size": 0.045, "font": "Montserrat", "color": "#FFFF66",
                            "bg": True, "bg_color": "#000000", "radius": 30,
                            "nx": 0.5, "ny": 0.78}, "Phụ đề chạy chữ")
        self.scene.addItem(self.cap_box)
        self.bg = "blur"
        self._frame = QPixmap()

    def set_cap_top(self, ny):
        # đặt ĐỈNH ô phụ đề tại ny (khớp neo an8 lúc render); ngang căn giữa
        self.cap_box.setPos(FW / 2 - self.cap_box.w / 2, max(0.0, ny) * FH)

    def cap_ny(self):
        # đỉnh khối chữ -> khớp với neo an8 lúc render
        return max(0.0, min(1.0, self.cap_box.y() / FH))

    def show_cap(self, on):
        self.cap_box.setVisible(on)

    def _set_guides(self, v, h):
        self.gv.setVisible(v)
        self.gh.setVisible(h)

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
            box = _TextBox(lid, on_resize=self.on_resize, on_guide=self._set_guides)
            self.scene.addItem(box); self.texts[lid] = box
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

    def __init__(self, frame_path, layout=None, parent=None, current_name=""):
        super().__init__(parent)
        self.setWindowTitle("Chỉnh mẫu (nền + video + chữ)")
        self.resize(940, 820)
        self._next = 1
        self.rows = {}
        self.layout_result = None
        self._current_name = current_name or ""
        self._frame_path = frame_path
        self._demo_ready.connect(self._play_demo)

        main = QHBoxLayout(self); main.setSpacing(14)
        # ----- CỘT TRÁI: khung xem trước + hướng dẫn ngắn -----
        left = QVBoxLayout(); left.setSpacing(8)
        self.canvas = EditorCanvas(on_resize=self._on_resized)
        left.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignTop)
        hint = QLabel("Kéo <b>khối video</b> để dời/phóng to · kéo <b>góc chữ</b> để "
                      "đổi cỡ · kéo <b>ô vàng</b> đặt chỗ phụ đề · kéo vào giữa có "
                      "vạch căn.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9A9AA8; font-size:12px;")
        hint.setFixedWidth(FW + 2)
        left.addWidget(hint)
        left.addStretch(1)
        main.addLayout(left)

        # ----- CỘT PHẢI: các nhóm điều khiển gọn gàng -----
        right = QVBoxLayout(); right.setSpacing(12); main.addLayout(right, 1)
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
        sv.clicked.connect(self._save_tmpl); mr.addWidget(sv)
        svn = QPushButton("Lưu mới"); svn.setToolTip("Lưu thành mẫu mới (đặt tên)")
        svn.clicked.connect(self._save_tmpl_new); mr.addWidget(svn)
        dlt = QPushButton("Xóa"); dlt.setProperty("danger", True)
        dlt.setToolTip("Xóa mẫu đang chọn"); dlt.clicked.connect(self._del_tmpl)
        mr.addWidget(dlt)
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
        # Tốc độ + đổi giọng (chống bản quyền)
        sp = QHBoxLayout(); sp.addWidget(QLabel("Tốc độ"))
        self.speed_cb = _NoWheelCombo()
        for t in ("1.0x", "1.05x", "1.1x", "1.15x", "1.2x", "1.3x"):
            self.speed_cb.addItem(t)
        sp.addWidget(self.speed_cb, 1)
        sp.addWidget(QLabel("Giọng"))
        self.voice_cb = _NoWheelCombo()
        for label, p in (("Gốc", 1.0), ("Trầm (nam)", 0.92), ("Cao (nữ)", 1.08),
                        ("Đổi giọng (chống b.quyền)", 1.12), ("Già/lạ", 0.85)):
            self.voice_cb.addItem(label, p)
        sp.addWidget(self.voice_cb, 1)
        gb.addLayout(sp)

        # Nhóm: Phụ đề chạy chữ (vàng)
        gc, gc_box = _group("Phụ đề chạy chữ (khớp lời)", (251, 191, 36))
        self.cap_chk = QCheckBox("Bật phụ đề — KÉO ô vàng trên khung để đặt chỗ")
        self.cap_chk.setChecked(True)
        self.cap_chk.toggled.connect(self.canvas.show_cap)
        gc.addWidget(self.cap_chk)
        # KIỂU phụ đề (vàng nhảy / karaoke / hộp đen / neon...)
        cps = QHBoxLayout()
        cps.addWidget(QLabel("Kiểu"))
        self.cap_preset = _NoWheelCombo()
        for name in CAPTION_PRESETS:
            self.cap_preset.addItem(name)
        self.cap_preset.setToolTip("Chọn kiểu phụ đề (màu/viền/hiệu ứng có sẵn).")
        self.cap_preset.currentIndexChanged.connect(self._refresh_cap)
        cps.addWidget(self.cap_preset, 1)
        self.cap_demo_btn = QPushButton("Demo")
        self.cap_demo_btn.setToolTip("Phát thử ~6 giây để xem kiểu chữ chạy thế nào.")
        self.cap_demo_btn.clicked.connect(self._demo_caption)
        cps.addWidget(self.cap_demo_btn)
        gc.addLayout(cps)
        cs1 = QHBoxLayout()
        cs1.addWidget(QLabel("Font"))
        self.cap_font = _NoWheelCombo()
        for f in ("Montserrat", "Be Vietnam Pro", "Anton", "Bungee", "Baloo 2",
                  "Oswald", "Lexend", "Pattaya", "Arial"):
            self.cap_font.addItem(f)
        self.cap_font.currentIndexChanged.connect(self._refresh_cap)
        cs1.addWidget(self.cap_font, 1)
        self._capcolor = ""        # '' = theo màu của kiểu; chọn để ghi đè
        self.cap_color_btn = QPushButton("Màu chữ")
        self.cap_color_btn.setToolTip("Đổi màu chữ (ghi đè màu mặc định của kiểu).")
        self.cap_color_btn.clicked.connect(self._pick_cap_color)
        cs1.addWidget(self.cap_color_btn)
        gc.addLayout(cs1)
        cs2 = QHBoxLayout()
        cs2.addWidget(QLabel("Cỡ"))
        self.cap_size = _NoWheelSlider(Qt.Orientation.Horizontal)
        # 18..80 = 1.8%..8.0% chiều cao -> kéo nhỏ hơn nhiều so với trước (min 30)
        self.cap_size.setRange(18, 80); self.cap_size.setValue(40)  # = 4.0%
        self.cap_size.valueChanged.connect(self._refresh_cap)
        self.cap_lbl_sz = QLabel("4.0%"); self.cap_lbl_sz.setFixedWidth(44)
        self.cap_size.valueChanged.connect(
            lambda v: self.cap_lbl_sz.setText(f"{v/10:.1f}%"))
        cs2.addWidget(self.cap_size, 1); cs2.addWidget(self.cap_lbl_sz)
        gc.addLayout(cs2)
        # KHỚP GIỜ: đẩy phụ đề sớm/trễ (ms) cho khít lời (whisper hay hiện sớm)
        cs3 = QHBoxLayout()
        cs3.addWidget(QLabel("Khớp giờ"))
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
        # HOOK: câu giật tít to ở đầu clip (AI tự chọn) — giữ chân người xem
        self.cap_hook = QCheckBox("Hiện HOOK đầu clip (câu giật tít to ~6s, AI tự chọn)")
        self.cap_hook.setChecked(True)
        self.cap_hook.setToolTip("Hiện 1 câu gây tò mò TO ở đầu clip rồi ẩn — kiểu "
                                 "video viral. AI tự chọn câu từ lời thoại.")
        gc.addWidget(self.cap_hook)

        # Nhóm: Lớp chữ (hồng)
        gl, gl_box = _group("Lớp chữ (Part · tiêu đề · cố định)",
                            (244, 114, 182))
        ar = QHBoxLayout()
        a2 = QPushButton("+ Part")
        a2.clicked.connect(lambda: self._add(is_part=True)); ar.addWidget(a2)
        a3 = QPushButton("+ Tiêu đề AI")
        a3.clicked.connect(self._add_title); ar.addWidget(a3)
        a1 = QPushButton("+ Chữ cố định")
        a1.clicked.connect(lambda: self._add(is_part=False)); ar.addWidget(a1)
        gl.addLayout(ar)
        self.box = QVBoxLayout(); self.box.setSpacing(8)
        host = QWidget(); host.setLayout(self.box)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(host)
        sc.setStyleSheet("QScrollArea{border:none;}")
        gl.addWidget(sc, 1)
        right.setStretchFactor(gl_box, 1)   # nhóm Lớp chữ giãn chiếm phần thừa
        self._reload_tmpl(select=self._current_name)

        # Nút dưới cùng
        brow = QHBoxLayout(); brow.addStretch(1)
        cancel = QPushButton("Hủy"); cancel.clicked.connect(self.reject)
        brow.addWidget(cancel)
        ok = QPushButton("Xong"); ok.setProperty("primary", True)
        ok.clicked.connect(self._accept); brow.addWidget(ok)
        right.addLayout(brow)

        self.canvas.load_frame(frame_path)
        self._apply_layout(layout)

    def _apply_layout(self, layout):
        if layout:
            vr = layout.get("video_rect")
            if vr:
                self.canvas.vbox.set_rect(*vr)
            self.canvas.set_bg(layout.get("bg", "blur"))
            self.trim_chk.setChecked(layout.get("trim_black", False))
            self.cap_chk.setChecked(layout.get("captions", True))
            fi = self.cap_font.findText(layout.get("cap_font", "Montserrat"))
            if fi >= 0:
                self.cap_font.setCurrentIndex(fi)
            cz = layout.get("cap_size", 0)
            if cz:
                self.cap_size.setValue(int(float(cz) * 1000))
            pi = self.cap_preset.findText(layout.get("cap_preset",
                                                     "Vàng nhảy (TikTok)"))
            if pi >= 0:
                self.cap_preset.setCurrentIndex(pi)
            self._capcolor = layout.get("cap_color", "") or ""
            if self._capcolor:
                self.cap_color_btn.setStyleSheet(f"color:{self._capcolor};")
            self.cap_delay.setValue(int(round(float(layout.get("cap_delay", 0.12))
                                              * 1000)))
            self.cap_hook.setChecked(bool(layout.get("cap_hook", True)))
            self.blur_amt.setValue(int(layout.get("blur_amt", 22)))
            sv = float(layout.get("speed", 1.0))
            for i in range(self.speed_cb.count()):
                if abs(float(self.speed_cb.itemText(i).rstrip("x")) - sv) < 0.001:
                    self.speed_cb.setCurrentIndex(i); break
            pv = float(layout.get("pitch", 1.0))
            for i in range(self.voice_cb.count()):
                if abs(float(self.voice_cb.itemData(i)) - pv) < 0.001:
                    self.voice_cb.setCurrentIndex(i); break
            self.canvas.set_cap_top(layout.get("cap_ny", 0.78))
            self._refresh_cap()          # áp cỡ/màu/font đã lưu vào ô xem trước
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
        self.canvas.upsert_text(lid, d, preview)

    def _on_resized(self, lid, frac):
        row = self.rows.get(lid)
        if row:
            row.set_size_fraction(frac)

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

    def _pick_cap_color(self):
        c = QColorDialog.getColor(QColor(self._cap_eff_color()), self,
                                  "Màu chữ phụ đề")
        if c.isValid():
            self._capcolor = c.name().upper()
            self.cap_color_btn.setStyleSheet(f"color:{self._capcolor};")
            self._refresh_cap()

    def _refresh_cap(self, *_):
        """Cập nhật ô PHỤ ĐỀ trong xem trước theo kiểu/cỡ/màu/font (giữ vị trí)."""
        cb = self.canvas.cap_box
        ny = cb.y() / FH                 # giữ nguyên vị trí dọc đang kéo
        cb.apply({"size": self.cap_size.value() / 1000.0,
                  "font": self.cap_font.currentText(), "color": self._cap_eff_color(),
                  "bg": True, "bg_color": "#000000", "radius": 30,
                  "nx": 0.5, "ny": ny}, "Phụ đề chạy chữ")
        self.canvas.set_cap_top(ny)      # đặt lại đỉnh tại vị trí cũ

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
                ass = os.path.join(tmp, "_capdemo.ass")
                captions.build_ass(words, [[0, total]], ass, out_w=1080,
                                   out_h=1920, font=font, size=size_px,
                                   color=color, ny=0.5, preset=preset)
                out = os.path.join(tmp, "_capdemo.mp4")
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
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
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
        dlg._pl = pl; dlg._ao = ao
        info = QLabel("Phát lặp lại. Ưng thì bấm Đóng — kiểu này đã được chọn sẵn.")
        info.setStyleSheet("color:#9AA6BF; font-size:12px;"); v.addWidget(info)
        cb = QPushButton("Đóng"); cb.setProperty("primary", True)
        cb.clicked.connect(lambda: (pl.stop(), dlg.accept())); v.addWidget(cb)
        pl.play()
        dlg.exec(); pl.stop()

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
        lay["captions"] = self.cap_chk.isChecked()
        lay["cap_font"] = self.cap_font.currentText()
        lay["cap_size"] = self.cap_size.value() / 1000.0
        lay["cap_color"] = self._capcolor          # '' = theo kiểu
        lay["cap_preset"] = self.cap_preset.currentText()
        lay["cap_delay"] = self.cap_delay.value() / 1000.0
        lay["cap_hook"] = self.cap_hook.isChecked()
        lay["cap_ny"] = self.canvas.cap_ny()
        lay["blur_amt"] = self.blur_amt.value()
        lay["speed"] = float(self.speed_cb.currentText().rstrip("x") or 1.0)
        lay["pitch"] = float(self.voice_cb.currentData() or 1.0)
        return lay

    def _save_tmpl(self):
        """Lưu = GHI ĐÈ lên mẫu đang chọn; chưa chọn mẫu nào -> hỏi tên (lưu mới)."""
        name = self.tmpl.currentData()
        if not name:
            self._save_tmpl_new()
            return
        services.save_template(name, self._collect_layout())
        self._current_name = name
        QMessageBox.information(self, "Đã lưu", f"Đã cập nhật mẫu “{name}”.")

    def _save_tmpl_new(self):
        name, ok = QInputDialog.getText(self, "Lưu mẫu mới", "Tên mẫu:")
        if ok and name.strip():
            services.save_template(name.strip(), self._collect_layout())
            self._current_name = name.strip()
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
        try:
            services.save_template(name, self.layout_result)
            self._current_name = name
        except Exception:  # noqa: BLE001
            pass
        self.accept()
