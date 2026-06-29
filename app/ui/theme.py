"""
Giao diện dùng chung — theme tối CAO CẤP (áp chuẩn thiết kế: ít đường kẻ, phân
biệt bằng nền/khoảng cách; 1 accent; phân cấp chữ; hover/nhấn mượt).
Gọi apply_theme(app) một lần lúc khởi động.
"""
from __future__ import annotations

from PyQt6.QtGui import QFont

# ---- Bảng màu: TỐI DỊU (xanh-than), sáng hơn đen tuyền, có VIỀN để nhận biết ----
WINDOW = "#181b23"          # nền trang (xanh-than, không đen tuyền)
BASE = "#222633"            # thẻ / panel (sáng rõ hơn nền -> tách lớp)
ELEV = "#2a2f3d"            # thẻ nổi / hover thẻ
SURFACE = "#2f3544"         # input / nút
SURFACE_HOVER = "#3a4253"
BORDER = "#3c4456"          # viền THẤY ĐƯỢC (giúp phân biệt khối)
TEXT = "#EEF0F6"
MUTED = "#9aa2b4"
ACCENT = "#5B8CFF"          # accent xanh dương
ACCENT_HOVER = "#79A2FF"
SUCCESS = "#3DD68C"         # xanh lá (xong/đã có)
DANGER = "#FF6B74"          # đỏ (xóa)
WARN = "#F5B544"            # vàng (đang chạy/chú ý)
PURPLE = "#B98CFF"          # tím (nhãn phụ)

QSS = f"""
* {{
    color: {TEXT};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 14px;
}}
QMainWindow, QWidget {{ background: {WINDOW}; }}
QToolTip {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 6px 9px; border-radius: 7px;
}}
QLabel {{ background: transparent; }}

/* ---- Nút: nền + VIỀN nhẹ (dễ nhận ra là nút bấm được) ---- */
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 16px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {SURFACE_HOVER}; border-color: {MUTED}; }}
QPushButton:pressed {{ background: {BASE}; }}
QPushButton:disabled {{ color: {MUTED}; background: {BASE}; border-color: {BORDER}; }}
QPushButton[primary="true"] {{
    background: {ACCENT}; color: white; font-weight: 600; padding: 9px 18px;
    border: none;
}}
QPushButton[primary="true"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[primary="true"]:pressed {{ background: {ACCENT}; }}
QPushButton[danger="true"] {{ background: transparent; color: {DANGER};
    border: 1px solid rgba(255,107,116,0.45); }}
QPushButton[danger="true"]:hover {{ background: rgba(255,107,116,0.16); color: {DANGER}; }}
QPushButton[ghost="true"] {{ background: transparent; color: {MUTED};
    border: 1px solid {BORDER}; }}
QPushButton[ghost="true"]:hover {{ background: {SURFACE}; color: {TEXT};
    border-color: {MUTED}; }}

/* ---- Input / combobox: LUÔN có viền (dễ thấy ô nhập), đậm khi focus ---- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 7px 11px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; selection-background-color: {ACCENT}; outline: none;
    padding: 4px;
}}

/* ---- List ---- */
QListWidget {{
    background: {WINDOW}; border: 1px solid {BORDER}; border-radius: 12px;
    outline: none; padding: 4px;
}}
QListWidget::item {{ padding: 10px 11px; border-radius: 8px; margin: 2px; }}
QListWidget::item:hover {{ background: {SURFACE}; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; }}

/* ---- Slider ---- */
QSlider::groove:horizontal {{ height: 5px; background: {SURFACE}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
}}

/* ---- Checkbox (to, rõ để tích chọn) ---- */
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{
    width: 20px; height: 20px; border-radius: 6px;
    border: 2px solid {MUTED}; background: {SURFACE};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton:checked {{ background: {ACCENT}; color: white; }}

/* ---- Progress ---- */
QProgressBar {{
    background: {SURFACE}; border: none; border-radius: 7px;
    text-align: center; height: 14px; color: {TEXT};
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 7px; }}

/* ---- Dock / scroll ---- */
QDockWidget {{ color: {MUTED}; }}
QDockWidget::title {{ background: {WINDOW}; padding: 6px 12px; }}
/* thanh KÉO to/nhỏ khu Tiến trình — làm dày + đổi màu khi rê chuột cho dễ thấy */
QMainWindow::separator {{ background: {SURFACE_HOVER}; height: 8px; }}
QMainWindow::separator:hover {{ background: {ACCENT}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SURFACE_HOVER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SURFACE_HOVER}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QGraphicsView {{ border: none; background: {BASE}; }}
QMessageBox, QInputDialog {{ background: {BASE}; }}
"""


def card_style(hover: bool = False) -> str:
    return f"background:{BASE}; border:1px solid {BORDER}; border-radius:14px;"


def apply_theme(app) -> None:
    from app.ui.fonts import load_fonts
    load_fonts()                       # nạp font đẹp (Montserrat, Anton...) trước UI
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
