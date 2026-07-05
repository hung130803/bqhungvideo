"""
Giao diện dùng chung — theme tối CAO CẤP (áp chuẩn thiết kế: ít đường kẻ, phân
biệt bằng nền/khoảng cách; 1 accent; phân cấp chữ; hover/nhấn mượt).
Gọi apply_theme(app) một lần lúc khởi động.
"""
from __future__ import annotations

from PyQt6.QtGui import QFont

# ---- Bảng màu: TỐI SÂU (xanh-than đậm), accent xanh dương, success DỊU ----
WINDOW = "#0F1420"          # nền trang (xanh-than sâu, không đen tuyền)
BASE = "#161D2E"            # thẻ / panel (sáng rõ hơn nền -> tách lớp)
ELEV = "#1A2233"            # thẻ nổi / hover thẻ
SURFACE = "#1C2438"         # input / nút
SURFACE_HOVER = "#273350"
BORDER = "#2A3550"          # viền THẤY ĐƯỢC (giúp phân biệt khối)
TEXT = "#E8EDF7"
MUTED = "#8B96AC"
ACCENT = "#4C8DFF"          # accent xanh dương
ACCENT_HOVER = "#6EA3FF"
SUCCESS = "#2EA97A"         # xanh lá DỊU (xong/đã có) — không neon
DANGER = "#E25B64"          # đỏ (xóa) — dịu
WARN = "#D9A13F"            # vàng (đang chạy/chú ý)
PURPLE = "#A78BFA"          # tím (nhãn phụ)

QSS = f"""
* {{
    color: {TEXT};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}
QMainWindow, QWidget {{ background: {WINDOW}; }}
QToolTip {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 6px 9px; border-radius: 6px; font-size: 12px;
}}
QLabel {{ background: transparent; }}

/* ---- Nút mặc định: GHOST TỐI (nền surface + viền, hover sáng nhẹ) ---- */
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {SURFACE_HOVER}; border-color: {MUTED}; }}
QPushButton:pressed {{ background: {BASE}; }}
QPushButton:disabled {{ color: {MUTED}; background: {BASE}; border-color: {BORDER}; }}
QPushButton[primary="true"] {{
    background: {ACCENT}; color: white; font-weight: 600; padding: 8px 18px;
    border: none;
}}
QPushButton[primary="true"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[primary="true"]:pressed {{ background: {ACCENT}; }}
QPushButton[primary="true"]:disabled {{ background: {SURFACE}; color: {MUTED}; }}
/* danger: bình thường chỉ CHỮ + VIỀN đỏ nhạt — hover mới đỏ đặc */
QPushButton[danger="true"] {{ background: transparent; color: {DANGER};
    border: 1px solid rgba(226,91,100,0.35); }}
QPushButton[danger="true"]:hover {{ background: {DANGER}; color: white;
    border-color: {DANGER}; }}
QPushButton[ghost="true"] {{ background: transparent; color: {MUTED};
    border: 1px solid {BORDER}; }}
QPushButton[ghost="true"]:hover {{ background: {SURFACE}; color: {TEXT};
    border-color: {MUTED}; }}

/* ---- Input / combobox: LUÔN có viền (dễ thấy ô nhập), đậm khi focus ---- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; selection-background-color: {ACCENT}; outline: none;
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {SURFACE_HOVER}; border: none; width: 16px;
}}

/* ---- Menu chuột phải ---- */
QMenu {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 6px 16px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACCENT}; color: white; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* ---- List ---- */
QListWidget {{
    background: {BASE}; border: 1px solid {BORDER}; border-radius: 10px;
    outline: none; padding: 4px;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: 7px; margin: 2px; }}
QListWidget::item:hover {{ background: {SURFACE}; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; }}

/* ---- Slider ---- */
QSlider::groove:horizontal {{ height: 5px; background: {SURFACE}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
}}

/* ---- Checkbox (to, rõ để tích chọn) ---- */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 2px solid {MUTED}; background: {SURFACE};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton:checked {{ background: {ACCENT}; color: white; }}

/* ---- Progress (mảnh, dịu) ---- */
QProgressBar {{
    background: {SURFACE}; border: none; border-radius: 5px;
    text-align: center; color: {TEXT}; font-size: 10px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}

/* ---- Dock / scroll ---- */
QDockWidget {{ color: {MUTED}; }}
QDockWidget::title {{
    background: {WINDOW}; padding: 6px 14px;
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
}}
/* thanh KÉO to/nhỏ khu Tiến trình — đổi màu khi rê chuột cho dễ thấy */
QMainWindow::separator {{ background: {BASE}; height: 7px; }}
QMainWindow::separator:hover {{ background: {ACCENT}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SURFACE_HOVER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SURFACE_HOVER}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QGraphicsView {{ border: none; background: {BASE}; }}
QMessageBox, QInputDialog, QDialog {{ background: {BASE}; }}
QMessageBox QLabel, QInputDialog QLabel {{ background: transparent; }}
"""


def card_style(hover: bool = False) -> str:
    return f"background:{BASE}; border:1px solid {BORDER}; border-radius:12px;"


def apply_theme(app) -> None:
    from app.ui.fonts import load_fonts
    load_fonts()                       # nạp font đẹp (Montserrat, Anton...) trước UI
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
