"""
Giao diện dùng chung — HỆ THIẾT KẾ (design tokens) + QSS toàn app, theme TỐI.
Gọi apply_theme(app) một lần lúc khởi động.

=============================================================================
HOW TO USE (đọc trước khi sửa UI — nhất là đợt 2: studio_page, thay_giong_dialog,
batch_page, batch_channels, recap_settings)
=============================================================================
1. KHÔNG viết hex / px tuỳ hứng. Lấy từ token:
     màu  : WINDOW BASE ELEV SURFACE SURFACE_HOVER BORDER TEXT MUTED SUBTLE
            ACCENT ACCENT_HOVER SUCCESS DANGER WARN PURPLE TEAL (tên cũ GIỮ NGUYÊN)
     cách : SP_1..SP_6 = 4 8 12 16 24 32  (lưới 8 pt; SPACE = tuple)
     bo   : R_SM R_MD R_LG = 6 10 14
     chữ  : FS_XS FS_SM FS_MD FS_LG FS_XL FS_XXL = 11 12 13 15 18 24  (CHỈ px)
     cao  : H_COMPACT H_DEFAULT H_HERO = 26 32 40
2. KHÔNG setStyleSheet() trên widget lẻ để đổi màu/cỡ chữ. Gán VAI qua property,
   QSS chung đã có sẵn luật:
     set_role(label, "title"|"heading"|"h1"|"display"|"section"|"muted"|"hint"|"value")
     set_style(label, role, tone)   # cả hai + xoá stylesheet inline cũ
     set_tone(widget, "accent"|"success"|"danger"|"warn"|"muted"|"analyze"|"export")
     set_variant(button, "primary"|"ghost"|"danger"|"subtle"|"nav"|None)
     set_size(button, "compact"|"hero"|None)   (property "density")
     set_phase(progressbar, "analyze"|"export"|"done"|"failed"|"warn"|None)
   Các hàm này chỉ unpolish/polish KHI GIÁ TRỊ ĐỔI -> gọi mỗi nhịp timer cũng rẻ
   (setStyleSheet mỗi nhịp bắt Qt dựng lại style cả cây con = thứ làm đơ).
   Property cũ primary/ghost/danger=True vẫn chạy (88+ chỗ đang dùng).
3. Khung/thẻ: `fr, lay = card()` (QFrame#card, lề SP_4, cách SP_2); thẻ nổi:
   card(elevated=True). Nhãn: h_title("..."), section("NHÓM"), muted("...").
   Lề layout: pad(lay, SP_4) / pad(lay, 16, 12) / pad(lay, l, t, r, b, spacing=8).
4. Bề ngang cố định cho chữ: fit_width(widget, "chữ dài nhất", ...) — đo bằng
   fontMetrics, KHÔNG số px cứng (cổng _test_nut_khong_cut).
5. Thanh tiến trình mượt + thông báo không chặn: app/ui/anim.py
     SmoothProgressBar (value() trả ĐÍCH ngay, phần vẽ trôi 300 ms)
     toast(parent, "Đã lưu", kind="success")   # thay QMessageBox.information
6. Màu theo dữ liệu (ô màu chữ người dùng chọn, màu kênh...) thì được inline,
   nhưng đặt 1 lần lúc dựng / khi giá trị đổi — không đặt lại mỗi nhịp.
   Màu kênh: set_chan(label, project_id) (10 màu CHANNEL_COLORS, có luật QSS).
=============================================================================
"""
from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QPalette

# ---------------------------------------------------------------------------
# TOKENS — màu (giữ đủ tên cũ: file khác import trực tiếp)
# ---------------------------------------------------------------------------
WINDOW = "#0F1420"          # nền trang (xanh-than sâu, không đen tuyền)
BASE = "#161D2E"            # thẻ / panel (sáng hơn nền -> tách lớp)
ELEV = "#1A2233"            # thẻ nổi / hover thẻ
SURFACE = "#1C2438"         # input / nút
SURFACE_HOVER = "#273350"
BORDER = "#2A3550"          # viền THẤY ĐƯỢC (giúp phân biệt khối)
BORDER_SOFT = "#222B40"     # viền mảnh trong thẻ / kẻ phân cách
TEXT = "#E8EDF7"
MUTED = "#8B96AC"           # chữ phụ (tương phản ~6:1 trên WINDOW)
SUBTLE = "#6E7A92"          # chữ gợi ý rất phụ (~4.3:1 — chỉ cỡ >= 11px)
ACCENT = "#4C8DFF"          # accent xanh dương
ACCENT_HOVER = "#6EA3FF"
ACCENT_PRESSED = "#3A78E6"
SUCCESS = "#2EA97A"         # xanh lá DỊU (xong/đã có) — không neon
DANGER = "#E25B64"          # đỏ (xóa) — dịu
WARN = "#D9A13F"            # vàng (đang chạy/chú ý)
PURPLE = "#A78BFA"          # tím (nhãn phụ / giai đoạn phân tích)
TEAL = "#14B8A6"            # xanh ngọc (giai đoạn cắt/xuất)
ON_ACCENT = "#FFFFFF"
VIDEO_BG = "#000000"         # ô ảnh/khung video (nội dung, luôn đen)

#: màu theo GIAI ĐOẠN việc (thanh tiến trình, chip đếm)
PHASE_COLORS = {"analyze": PURPLE, "export": TEAL, "done": SUCCESS,
                "failed": DANGER, "warn": WARN, "accent": ACCENT}
#: màu phân biệt KÊNH (mỗi kênh 1 màu cố định theo id) — dùng set_chan()
CHANNEL_COLORS = ["#4F7DFF", "#22C55E", "#F59E0B", "#EC4899", "#06B6D4",
                  "#A78BFA", "#EF4444", "#14B8A6", "#F97316", "#8B5CF6"]

# ---- khoảng cách (lưới 8 pt) / bo góc / cỡ chữ (px) / chiều cao control ----
SP_1, SP_2, SP_3, SP_4, SP_5, SP_6 = 4, 8, 12, 16, 24, 32
SPACE = (SP_1, SP_2, SP_3, SP_4, SP_5, SP_6)
R_SM, R_MD, R_LG = 6, 10, 14
RADIUS = (R_SM, R_MD, R_LG)
FS_XS, FS_SM, FS_MD, FS_LG, FS_XL, FS_XXL = 11, 12, 13, 15, 18, 24
FONT = (FS_XS, FS_SM, FS_MD, FS_LG, FS_XL, FS_XXL)
H_COMPACT, H_DEFAULT, H_HERO = 26, 32, 40
FONT_FAMILIES = ["Segoe UI", "Be Vietnam Pro", "Inter", "Noto Sans", "sans-serif"]
_FAM_QSS = ", ".join(f'"{f}"' if " " in f else f for f in FONT_FAMILIES)


def rgba(hex_color: str, a: float) -> str:
    """'#RRGGBB' -> 'rgba(r,g,b,a)' — nền mờ theo màu."""
    h = hex_color.lstrip("#")
    return (f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},"
            f"{int(h[4:6], 16)},{a})")


def _tone_rules() -> str:
    out = []
    tones = dict(PHASE_COLORS, success=SUCCESS, danger=DANGER, muted=MUTED,
                 text=TEXT, purple=PURPLE, teal=TEAL)
    # màu KÊNH trước: tone (nếu có, vd "muted" khi việc đã xong) ĐÈ được màu kênh
    for i, col in enumerate(CHANNEL_COLORS):
        out.append(f'QLabel[chan="{i}"] {{ color: {col}; }}')
    for name, col in tones.items():
        out.append(f'QLabel[tone="{name}"], QCheckBox[tone="{name}"] {{ color: {col}; }}')
        out.append(f'QFrame#chip[tone="{name}"] {{ background: {rgba(col, 0.13)};'
                   f' border: 1px solid {rgba(col, 0.35)}; }}')
        out.append(f'QFrame#chip[tone="{name}"] QLabel#chipNum {{ color: {col}; }}')
        out.append(f'QLabel#score[tone="{name}"] {{ color: {col}; border-color: {col}; }}')
    for name, col in PHASE_COLORS.items():
        out.append(f'QProgressBar[phase="{name}"]::chunk {{ background: {col}; }}')
    return "\n".join(out)


def _banner_rules() -> str:
    """QLabel[banner=ok|err|wait|info]: dải thông báo màu nhạt trong hộp thoại."""
    out = []
    for kind, col in (("ok", SUCCESS), ("err", DANGER), ("wait", WARN), ("info", MUTED)):
        bg = "transparent" if kind == "info" else rgba(col, 0.14)
        out.append(f'QLabel[banner="{kind}"] {{ color: {col}; background: {bg}; '
                   f'border-radius: 8px; padding: 9px 11px; font-size: {FS_MD}px; '
                   'font-weight: 600; }')
    return "\n".join(out)


def build_qss() -> str:
    """QSS toàn app dựng từ token. KHÔNG có luật `*` / `QWidget {background}`:
    luật phổ quát bắt MỌI widget (kể cả QLabel con) mang font/nền từ stylesheet
    -> restyle đắt + đè setFont(). Nền đặt ở cửa sổ gốc, chữ/màu qua palette
    (apply_theme) + luật theo loại widget bên dưới."""
    return f"""
QMainWindow, QDialog {{ background: {WINDOW}; color: {TEXT}; }}
QMessageBox, QInputDialog {{ background: {BASE}; }}
QToolTip {{
    background: {ELEV}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 6px 9px; border-radius: {R_SM}px; font-size: {FS_SM}px;
}}
QLabel {{ background: transparent; color: {TEXT}; }}
QCheckBox, QRadioButton {{ background: transparent; color: {TEXT}; }}

/* ---- vai chữ (set_role) ---- */
QLabel[role="display"] {{ font-size: {FS_XXL}px; font-weight: 800; }}
QLabel[role="h1"] {{ font-size: {FS_XL}px; font-weight: 700; }}
QLabel[role="title"] {{ font-size: {FS_LG}px; font-weight: 600; }}
QLabel[role="heading"] {{ font-size: {FS_LG}px; font-weight: 700; }}
QLabel[role="tag"] {{ font-size: {FS_XS}px; font-weight: 700; }}
QLabel[role="value"] {{ font-size: {FS_MD}px; font-weight: 600; }}
QLabel[role="section"] {{ color: {SUBTLE}; font-size: {FS_XS}px; font-weight: 700;
    letter-spacing: 1px; }}
QLabel[role="muted"] {{ color: {MUTED}; font-size: {FS_SM}px; }}
QLabel[role="hint"] {{ color: {MUTED}; font-size: {FS_XS}px; }}
QLabel[link="true"] {{ text-decoration: underline; }}
{_tone_rules()}

/* ---- thẻ (card()) ---- */
QFrame#card {{ background: {BASE}; border: 1px solid {BORDER_SOFT};
    border-radius: {R_LG}px; }}
QFrame#card[elevated="true"] {{ background: {ELEV}; border-color: {BORDER}; }}
QFrame#chip {{ border-radius: {R_SM + 2}px; }}
QFrame#chip QLabel {{ background: transparent; border: none; }}
QFrame#chip QLabel#chipNum {{ font-size: {FS_SM}px; font-weight: 700; }}
QFrame#chip QLabel#chipLabel {{ color: {MUTED}; font-size: {FS_XS}px; }}
QFrame#divider {{ background: {BORDER_SOFT}; border: none; }}

/* ---- Nút mặc định: GHOST TỐI (nền surface + viền, hover sáng nhẹ) ---- */
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {SURFACE_HOVER}; border-color: {MUTED}; }}
QPushButton:pressed {{ background: {BASE}; border-color: {ACCENT}; }}
QPushButton:focus {{ outline: none; }}
QPushButton:disabled {{ color: {SUBTLE}; background: {BASE}; border-color: {BORDER_SOFT}; }}
QPushButton:checked {{ background: {ACCENT}; color: {ON_ACCENT}; border-color: {ACCENT}; }}
QPushButton::menu-indicator {{ subcontrol-position: right center; right: 6px; }}
QPushButton[primary="true"], QPushButton[variant="primary"] {{
    background: {ACCENT}; color: {ON_ACCENT}; font-weight: 600; padding: 8px 18px;
    border: none;
}}
QPushButton[primary="true"]:hover, QPushButton[variant="primary"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[primary="true"]:pressed, QPushButton[variant="primary"]:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton[primary="true"]:disabled, QPushButton[variant="primary"]:disabled {{
    background: {SURFACE}; color: {SUBTLE}; }}
/* danger: bình thường chỉ CHỮ + VIỀN đỏ nhạt — hover mới đỏ đặc */
QPushButton[danger="true"], QPushButton[variant="danger"] {{ background: transparent;
    color: {DANGER}; border: 1px solid {rgba(DANGER, 0.35)}; }}
QPushButton[danger="true"]:hover, QPushButton[variant="danger"]:hover {{
    background: {DANGER}; color: {ON_ACCENT}; border-color: {DANGER}; }}
QPushButton[danger="true"]:pressed, QPushButton[variant="danger"]:pressed {{
    background: {rgba(DANGER, 0.75)}; }}
QPushButton[ghost="true"], QPushButton[variant="ghost"] {{ background: transparent;
    color: {MUTED}; border: 1px solid {BORDER}; }}
QPushButton[ghost="true"]:hover, QPushButton[variant="ghost"]:hover {{
    background: {SURFACE}; color: {TEXT}; border-color: {MUTED}; }}
QPushButton[variant="subtle"] {{ background: transparent; border: 1px solid transparent;
    color: {MUTED}; }}
QPushButton[variant="subtle"]:hover {{ background: {SURFACE}; color: {TEXT}; }}
/* điều hướng (thanh bên): chữ trái, nền trong; đang chọn = nền accent mờ + vạch trái */
QPushButton[variant="nav"] {{ background: transparent; border: 1px solid transparent;
    border-radius: {R_SM + 2}px; padding: 7px 12px; text-align: left; color: {TEXT};
    font-size: {FS_MD}px; }}
QPushButton[variant="nav"]:hover {{ background: {SURFACE}; }}
QPushButton[variant="nav"]:pressed {{ background: {SURFACE_HOVER}; }}
QPushButton[variant="nav"]:checked {{ background: {rgba(ACCENT, 0.16)}; color: {ACCENT_HOVER};
    border: 1px solid {rgba(ACCENT, 0.30)}; font-weight: 600; }}
/* nút lọc dạng chip (thay giọng: lọc giọng theo nhóm) */
QPushButton[variant="chip"] {{ background: {SURFACE}; color: {MUTED}; border: 1px solid {BORDER};
    border-radius: {R_SM}px; padding: 2px 8px; font-size: {FS_XS}px; }}
QPushButton[variant="chip"]:hover {{ color: {TEXT}; border-color: {MUTED}; }}
QPushButton[variant="chip"]:checked {{ background: {ACCENT}; color: {ON_ACCENT};
    border-color: {ACCENT}; font-weight: 600; }}
QPushButton[variant="chip"][tab="true"] {{ font-size: {FS_MD}px; font-weight: 600; padding: 6px 16px; border-radius: {R_MD}px; }}
QPushButton[density="compact"] {{ padding: 3px 10px; font-size: {FS_SM}px; border-radius: {R_SM}px; }}
QPushButton[density="hero"] {{ padding: 10px 22px; font-size: {FS_LG - 1}px; font-weight: 600;
    border-radius: {R_MD}px; }}

/* ---- Input / combobox: LUÔN có viền (dễ thấy ô nhập), đậm khi focus ---- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
    selection-color: {ON_ACCENT};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {SURFACE_HOVER}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {SUBTLE}; background: {BASE}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; selection-background-color: {ACCENT}; outline: none;
    padding: 4px;
}}
/* Ô SỐ: đủ rộng + chừa chỗ nút tăng/giảm — máy scale khác không bị CẮT SỐ */
QSpinBox, QDoubleSpinBox {{
    min-width: 64px;
    padding-right: 22px;          /* chừa chỗ cột nút up/down (16px + viền) */
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {SURFACE_HOVER}; border: none; width: 16px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{ background: {MUTED}; }}

/* ---- Menu chuột phải ---- */
QMenu {{
    background: {ELEV}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 6px 16px; border-radius: {R_SM}px; }}
QMenu::item:selected {{ background: {ACCENT}; color: {ON_ACCENT}; }}
QMenu::item:disabled {{ color: {SUBTLE}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* ---- Tables: explicit alternate background for Windows dark mode ---- */
QTableView {{
    background: {WINDOW}; alternate-background-color: {BASE};
    color: {TEXT}; gridline-color: {BORDER}; border: 1px solid {BORDER};
    selection-background-color: {SURFACE_HOVER}; selection-color: {TEXT};
}}
QHeaderView::section {{ background: {SURFACE}; color: {TEXT}; padding: 6px;
    border: none; border-right: 1px solid {BORDER}; }}
QTableCornerButton::section {{ background: {SURFACE}; border: none; }}

/* ---- List ---- */
QListWidget {{
    background: {BASE}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {R_MD}px;
    outline: none; padding: 4px;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: 7px; margin: 2px; }}
QListWidget::item:hover {{ background: {SURFACE}; }}
QListWidget::item:selected {{ background: {ACCENT}; color: {ON_ACCENT}; }}

/* ---- Tabs ---- */
QTabWidget::pane {{ border: 1px solid {BORDER_SOFT}; border-radius: {R_MD}px; top: -1px;
    background: {BASE}; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 7px 14px;
    border: none; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}

/* ---- Slider ---- */
QSlider::groove:horizontal {{ height: 5px; background: {SURFACE}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}

/* ---- Checkbox (to, rõ để tích chọn) ---- */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 2px solid {MUTED}; background: {SURFACE};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QCheckBox::indicator:disabled {{ border-color: {BORDER}; background: {BASE}; }}
QCheckBox:disabled {{ color: {SUBTLE}; }}

/* ---- Progress (mảnh, dịu); màu theo GIAI ĐOẠN qua set_phase() ---- */
QProgressBar {{
    background: {SURFACE}; border: none; border-radius: 5px;
    text-align: center; color: {TEXT}; font-size: 10px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}

/* ---- Thanh bên + dock ---- */
QWidget#sidebar {{ background: {BASE}; }}
QScrollArea#navigation {{ background: {BASE}; border: none;
    border-right: 1px solid {BORDER_SOFT}; }}
QLabel#brand {{ font-size: {FS_XL + 2}px; font-weight: 800; color: {TEXT}; }}
QLabel#brandAccent {{ font-size: {FS_XL + 2}px; font-weight: 800; color: {ACCENT};
    letter-spacing: 2px; }}
QFrame#account {{ background: {SURFACE}; border: 1px solid {BORDER_SOFT};
    border-radius: {R_MD}px; }}
QWidget#queueArea {{ background: {WINDOW}; border-top: 1px solid {BORDER}; }}
QWidget#dockTitle {{ background: {WINDOW}; border-top: 1px solid {BORDER_SOFT}; }}
QDockWidget {{ color: {MUTED}; }}
QDockWidget::title {{
    background: {WINDOW}; padding: 6px 14px;
    font-size: {FS_XS}px; font-weight: 700; letter-spacing: 1px;
}}
/* thanh KÉO to/nhỏ khu Tiến trình — đổi màu khi rê chuột cho dễ thấy */
QMainWindow::separator {{ background: {BORDER_SOFT}; height: 7px; width: 1px; }}
QMainWindow::separator:hover {{ background: {ACCENT}; }}
/* vạch kéo vùng làm việc / Tiến trình (main_window) — như separator dock cũ */
QSplitter#workSplit::handle {{ background: {BASE}; }}
QSplitter#workSplit::handle:hover {{ background: {ACCENT}; }}

/* ---- studio_page: thẻ điều khiển 3 bước, thẻ clip, khối tiến trình ---- */
QWidget#ctlPanel {{ background: {BASE}; border: 1px solid {BORDER_SOFT};
    border-radius: {R_LG}px; }}
QLabel#stepDot {{ background: {ACCENT}; color: {ON_ACCENT}; border-radius: 11px;
    font-size: {FS_SM}px; font-weight: 800; }}
QLabel#aiStatus {{ font-size: {FS_SM}px; font-weight: 600; padding: 4px 10px;
    border-radius: 11px; background: {SURFACE}; border: 1px solid {BORDER}; }}
QLabel#aiStatus[tone="success"] {{ background: {rgba(SUCCESS, 0.12)}; border-color: {rgba(SUCCESS, 0.35)}; }}
QLabel#aiStatus[tone="danger"] {{ background: {rgba(DANGER, 0.12)}; border-color: {rgba(DANGER, 0.45)}; }}
QFrame#ctlSep {{ background: {BORDER_SOFT}; border: none; }}

QWidget#clipCard {{ background: {BASE}; border: 1px solid transparent;
    border-radius: {R_LG}px; }}
QWidget#clipCard:hover {{ background: {ELEV}; border-color: {BORDER_SOFT}; }}
QLabel#thumb {{ background: {VIDEO_BG}; border-radius: {R_SM + 2}px; }}
QLabel#score {{ background: {SURFACE}; border: 1px solid {MUTED}; border-radius: 19px;
    font-size: {FS_MD}px; font-weight: 700; color: {MUTED}; }}
QWidget#jobProgBox {{ background: {BASE}; border: 1px solid {BORDER};
    border-radius: {R_LG}px; }}
QWidget#jobProgBox QProgressBar, QWidget#jobProgBox QProgressBar::chunk {{ border-radius: 6px; }}
QLabel#jobPct {{ font-size: {FS_XXL + 4}px; font-weight: 800; }}
QLabel#jobIcon {{ font-size: {FS_XXL}px; }}
QWidget#jobProgBox[compact="true"] QLabel#jobPct {{ font-size: {FS_XL}px; }}
QWidget#jobProgBox[compact="true"] QLabel#jobIcon {{ font-size: {FS_LG}px; }}
QLabel#heroIcon {{ font-size: 44px; font-weight: 700; }}

QFrame#giongPick {{ background: {BASE}; border: 1px solid {BORDER}; border-radius: {R_MD}px; }}
QFrame#chanPick {{ background: {BASE}; border: 1px solid {BORDER}; border-radius: {R_MD}px; }}
QFrame#aiCard {{ background: {ELEV}; border: 1px solid {BORDER_SOFT};
    border-radius: {R_LG}px; }}
QFrame#aiCard QLabel {{ background: transparent; }}
QLabel#key_status_label {{ color: {TEXT}; background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px 10px; font-size: {FS_SM}px; }}
QLabel#pipeOverview {{ font-size: {FS_SM}px; padding: 2px; border-bottom: 1px solid {BORDER_SOFT}; }}
{_banner_rules()}
/* bảng dữ liệu (studio/thay giọng): viền bo + header đậm có vạch dưới */
QTableView[table] {{ background: {BASE}; border: 1px solid {BORDER}; border-radius: 8px;
    gridline-color: {BORDER}; color: {TEXT}; }}
QTableView[table="data"]::item {{ padding: 3px 8px; }}
QTableView[table="data"]::item:selected {{ background: {ACCENT}; color: {ON_ACCENT}; }}
QTableView[table] QHeaderView::section {{ background: {SURFACE}; color: {TEXT}; padding: 6px 8px;
    border: none; border-bottom: 1px solid {BORDER}; font-weight: 600; }}
QLineEdit[density="compact"] {{ padding: 4px 8px; border-radius: {R_SM}px; }}

/* ---- hàng đợi (queue_panel) ---- */
QFrame#qrow {{ background: transparent; border: 1px solid transparent;
    border-radius: {R_MD}px; }}
QFrame#qrow:hover {{ background: {BASE}; border-color: {BORDER_SOFT}; }}
QFrame#qrow QProgressBar, QFrame#qrow QProgressBar::chunk {{ border-radius: 4px; }}

/* ---- thông báo nổi (anim.toast) ---- */
QFrame#toast {{ background: {ELEV}; border: 1px solid {BORDER}; border-radius: {R_MD}px; }}
QFrame#toast[kind="success"] {{ border-left: 3px solid {SUCCESS}; }}
QFrame#toast[kind="error"] {{ border-left: 3px solid {DANGER}; }}
QFrame#toast[kind="warn"] {{ border-left: 3px solid {WARN}; }}
QFrame#toast[kind="info"] {{ border-left: 3px solid {ACCENT}; }}
QFrame#toast QLabel {{ background: transparent; font-size: {FS_MD}px; }}

/* ---- scroll ---- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SURFACE_HOVER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SURFACE_HOVER}; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QGraphicsView {{ border: none; background: {BASE}; }}
QMessageBox QLabel, QInputDialog QLabel {{ background: transparent; }}
"""


QSS = build_qss()


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _repolish(w) -> None:
    st = w.style()
    st.unpolish(w)
    st.polish(w)
    w.update()


def set_prop(w, name: str, value) -> bool:
    """Đặt dynamic property + repolish CHỈ KHI giá trị đổi. Trả True nếu đổi.
    None = xoá property (về kiểu mặc định)."""
    cur = w.property(name)
    if cur == value or (cur is None and value is None):
        return False
    w.setProperty(name, value)
    _repolish(w)
    return True


def set_role(w, role):
    """Vai chữ: title/h1/display/section/muted/hint/value (None = thường)."""
    return set_prop(w, "role", role)


def set_style(w, role=None, tone=None):
    """Vai chữ + màu cùng lúc (thay cho setStyleSheet("color:..; font-size:..")).
    Widget còn stylesheet inline cũ -> xoá để luật QSS chung có hiệu lực."""
    if w.styleSheet():
        w.setStyleSheet("")
    a = set_role(w, role)
    b = set_tone(w, tone)
    return a or b


def set_tone(w, tone):
    """Màu ngữ nghĩa: accent/success/danger/warn/muted/analyze/export/purple/teal."""
    return set_prop(w, "tone", tone)


def set_phase(bar, phase):
    """Màu thanh tiến trình: analyze/export/done/failed/warn (None = accent)."""
    return set_prop(bar, "phase", phase)


def phase_for_color(col) -> str:
    """Màu cũ (hex) -> tên phase QSS — cho code còn trả màu (vd _job_phase)."""
    c = str(col or "").upper()
    for name, v in PHASE_COLORS.items():
        if v.upper() == c:
            return name
    return "accent"


#: màu cũ (hex rải trong code) -> tone QSS gần nghĩa nhất
_LEGACY_TONE = {"#F9E2AF": "warn", "#A6E3A1": "success", "#F38BA8": "danger",
                "#FFB86C": "warn", "#B0B0B0": "muted", "#7CC4FF": "accent"}


def tone_for_color(col):
    """Màu (token hoặc hex cũ) -> tên tone cho set_tone/set_style; lạ -> 'text'."""
    c = str(col or "").upper()
    for name, v in (("success", SUCCESS), ("danger", DANGER), ("warn", WARN),
                     ("accent", ACCENT), ("muted", MUTED), ("text", TEXT),
                     ("analyze", PURPLE), ("export", TEAL)):
        if v.upper() == c:
            return name
    return _LEGACY_TONE.get(c, "text")


def set_size(btn, size):
    """Cỡ nút: compact (26) / hero (40) / None (32)."""
    # property tên "density" (KHÔNG phải "size": QWidget đã có Q_PROPERTY size
    # kiểu QSize -> setProperty("size", "compact") bị Qt từ chối âm thầm)
    return set_prop(btn, "density", size)


def set_chan(w, pid):
    """Màu kênh cố định theo id (0..9 trong CHANNEL_COLORS)."""
    return set_prop(w, "chan", str((int(pid) if pid else 0) % len(CHANNEL_COLORS)))


def chan_color(pid) -> str:
    return CHANNEL_COLORS[(int(pid) if pid else 0) % len(CHANNEL_COLORS)]


def set_variant(btn, variant):
    """primary/ghost/danger/subtle/nav/None. Đồng bộ luôn property cũ
    (primary/ghost/danger=True) để code đọc property cũ vẫn đúng."""
    changed = False
    for old in ("primary", "ghost", "danger"):
        want = True if variant == old else None
        cur = btn.property(old)
        if bool(cur) != bool(want):
            btn.setProperty(old, want)
            changed = True
    if btn.property("variant") != variant:
        btn.setProperty("variant", variant)
        changed = True
    if changed:
        _repolish(btn)
    return changed


def pad(layout, *m, spacing=None):
    """Lề layout theo token: pad(l, 16) | pad(l, 16, 12) | pad(l, l, t, r, b)."""
    if len(m) == 1:
        m = (m[0],) * 4
    elif len(m) == 2:
        m = (m[0], m[1], m[0], m[1])
    elif len(m) != 4:
        raise ValueError("pad(): 1, 2 hoặc 4 số")
    layout.setContentsMargins(*m)
    if spacing is not None:
        layout.setSpacing(spacing)
    return layout


def card(parent=None, *, elevated=False, layout="v", margins=SP_4, spacing=SP_2,
         name="card"):
    """Thẻ chuẩn: QFrame#card + layout có lề token. Trả (frame, layout)."""
    from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout
    fr = QFrame(parent)
    fr.setObjectName(name)
    if elevated:
        fr.setProperty("elevated", True)
    lay = (QHBoxLayout if layout == "h" else QVBoxLayout)(fr)
    pad(lay, *(margins if isinstance(margins, tuple) else (margins,)),
        spacing=spacing)
    return fr, lay


def divider(parent=None):
    """Đường kẻ mảnh 1px ngăn nhóm."""
    from PyQt6.QtWidgets import QFrame
    ln = QFrame(parent)
    ln.setObjectName("divider")
    ln.setFixedHeight(1)
    return ln


def _label(text, role, parent=None, wrap=False):
    from PyQt6.QtWidgets import QLabel
    lb = QLabel(text, parent)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def h_title(text, parent=None, level="title"):
    """Tiêu đề: level = title (15) / h1 (18) / display (24)."""
    return _label(text, level, parent)


def section(text, parent=None):
    """Nhãn NHÓM: chữ HOA nhỏ, mờ."""
    return _label(text.upper(), "section", parent)


def muted(text, parent=None, wrap=True, role="muted"):
    return _label(text, role, parent, wrap)


def fit_width(w, *texts, pad_px=12, minimum=0, fixed=True):
    """Bề ngang đủ cho chữ DÀI NHẤT theo fontMetrics thật (không px cứng)."""
    fm = w.fontMetrics()
    need = max([fm.horizontalAdvance(t) for t in texts if t] + [0]) + pad_px
    need = max(need, minimum)
    if fixed:
        w.setFixedWidth(need)
    else:
        w.setMinimumWidth(need)
    return need


def app_font() -> QFont:
    f = QFont()
    f.setFamilies(FONT_FAMILIES)
    f.setPixelSize(FS_MD)
    return f


def palette() -> QPalette:
    """Palette tối: widget KHÔNG có luật QSS (cửa sổ phụ, popup) vẫn tối + chữ sáng."""
    p = QPalette()
    roles = QPalette.ColorRole
    for role, col in ((roles.Window, WINDOW), (roles.WindowText, TEXT),
                      (roles.Base, SURFACE), (roles.AlternateBase, BASE),
                      (roles.Text, TEXT), (roles.Button, SURFACE),
                      (roles.ButtonText, TEXT), (roles.ToolTipBase, ELEV),
                      (roles.ToolTipText, TEXT), (roles.Highlight, ACCENT),
                      (roles.HighlightedText, ON_ACCENT), (roles.Link, ACCENT_HOVER),
                      (roles.PlaceholderText, SUBTLE), (roles.BrightText, ON_ACCENT),
                      (roles.Mid, BORDER), (roles.Dark, WINDOW), (roles.Light, SURFACE_HOVER)):
        p.setColor(role, QColor(col))
    for role in (roles.WindowText, roles.Text, roles.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(SUBTLE))
    return p


def card_style(hover: bool = False) -> str:
    """(cũ) chuỗi style thẻ — nên dùng card() / QFrame#card thay thế."""
    return f"background:{BASE}; border:1px solid {BORDER}; border-radius:{R_LG}px;"


def apply_theme(app) -> None:
    from app.ui.fonts import load_fonts
    load_fonts()                       # nạp font đẹp (Montserrat, Anton...) trước UI
    app.setFont(app_font())            # 13 px — MỘT đơn vị (px) cho cả app
    app.setPalette(palette())
    app.setStyleSheet(QSS)
