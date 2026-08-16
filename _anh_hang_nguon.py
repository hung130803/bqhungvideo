# -*- coding: utf-8 -*-
"""CHỤP ẢNH HÀNG "Nguồn video" ĐỂ *NHÌN* — không phải để chạy qua.

3 nút bị nợ từ lượt trước: `Copy` cụt chữ (đặt cứng 52px), `✏` và `📊` là
EMOJI TRẦN — đúng họ lỗi v2.6.22 "xấu quá tự nhiên có cái ô đen" trên máy
thiếu phông màu. Sửa xong phải NHÌN, vì mọi phép kiểm bề rộng đều đo bằng
CHÍNH font mà nó vừa dùng để vẽ -> tự khớp với chính mình là chuyện thường.

    .venv\\Scripts\\python -u _anh_hang_nguon.py
"""
from __future__ import annotations

import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="anhnguon_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from PyQt6.QtGui import QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QHBoxLayout,  # noqa: E402
                             QPushButton, QWidget)

app = QApplication.instance() or QApplication([])

# NỀN `offscreen` CỦA Qt CÓ **0 PHÔNG** (đo được: `QFontDatabase.families()`
# trả danh sách RỖNG) -> mọi chữ vẽ ra Ô VUÔNG TOFU. Đó là lỗi của BỘ DỰNG
# ẢNH, không phải của app — nhưng nếu không biết mà nhìn ảnh thì kết luận
# ngược hẳn ("app hỏng phông"). Nạp thẳng file phông thật của Windows vào thì
# ảnh mới nói được điều gì về app.
from PyQt6.QtGui import QFont, QFontDatabase  # noqa: E402
_da_nap = []
for _f in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
           r"C:\Windows\Fonts\tahoma.ttf"):
    if os.path.exists(_f) and QFontDatabase.addApplicationFont(_f) >= 0:
        _da_nap.append(os.path.basename(_f))
print(f"phông nạp thêm: {_da_nap or 'KHÔNG NẠP ĐƯỢC'}")
print(f"phông Qt thấy : {len(QFontDatabase.families())} họ")
if not QFontDatabase.families():
    print("KHÔNG CÓ PHÔNG -> ảnh sẽ toàn ô vuông, ĐỪNG kết luận gì từ nó")
app.setFont(QFont("Segoe UI", 10))

from app import services  # noqa: E402
from app.ui import theme  # noqa: E402

app.setStyleSheet(theme.QSS)          # QSS THẬT — không có thì đo ra nhẹ giả

services.create_project("Kênh Thử Ảnh", "M")

from app.ui.studio_page import StudioPage, _vua_chu  # noqa: E402


def chup(w: QWidget, ten: str, rong: int, cao: int) -> str:
    w.resize(rong, cao)
    w.show()
    app.processEvents()
    img = QImage(w.size(), QImage.Format.Format_ARGB32)
    img.fill(0xFF12141A)              # nền tối như app, để thấy chữ sáng
    p = QPainter(img)
    w.render(p)
    p.end()
    ra = os.path.join(REPO, ten)
    img.save(ra)
    return ra


# ---- dựng LẠI ĐÚNG hàng Nguồn video (chỉ phần 3 nút + hàng xóm) ----
hop = QWidget()
lay = QHBoxLayout(hop)
lay.setSpacing(8)
lay.setContentsMargins(10, 8, 10, 8)

nhan = []
for txt in ("Sửa nhóm", "Chép tên", "+ Kênh", "Sửa tên", "Tình hình",
            "Kho video"):
    b = QPushButton(txt)
    b.setProperty("ghost", True)
    if txt != "+ Kênh":
        _vua_chu(b, txt)              # ĐÚNG cách studio_page đang dùng
    lay.addWidget(b)
    nhan.append(b)
lay.addStretch(1)

f = chup(hop, "_anh_hang_nguon.png", 820, 52)
print(f"ảnh: {f}")
print(f"{'nhãn':<12} {'rộng nút':>9} {'chữ cần':>9} {'dư':>6}")
xau = []
for b in nhan:
    can = b.fontMetrics().horizontalAdvance(b.text())
    du = b.width() - can
    print(f"{b.text():<12} {b.width():>9} {can:>9} {du:>6}")
    if du < 8:
        xau.append(b.text())

# EMOJI: quét CHÍNH mã nguồn hàng Nguồn video
import re  # noqa: E402
src = open(os.path.join(REPO, "app", "ui", "studio_page.py"),
           encoding="utf-8").read()
i0 = src.find("srcrow = QHBoxLayout()")
i1 = src.find('plw.addWidget(self._sec_hdr("Nguồn video"', i0)
than = src[i0:i1]
emo = []
for m in re.finditer(r'QPushButton\("([^"]*)"\)', than):
    for ch in m.group(1):
        if ord(ch) > 0x2000 and ch not in "–—…":
            emo.append(f"{m.group(1)!r} chứa U+{ord(ch):04X}")
cung = [ln.strip()[:70] for ln in than.splitlines()
        if "setFixedWidth(" in ln and "QPushButton" in ln]
print(f"\nemoji còn lại trong hàng Nguồn video: {emo or 'KHÔNG'}")
print(f"bề rộng CỨNG còn lại: {cung or 'KHÔNG'}")
print(f"nút cụt chữ: {xau or 'KHÔNG'}")
