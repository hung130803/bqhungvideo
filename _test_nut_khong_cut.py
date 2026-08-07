# -*- coding: utf-8 -*-
"""CỔNG 31 — NÚT KHÔNG ĐƯỢC CỤT CHỮ (mọi font, mọi DPI).

LỖI THẬT: ảnh anh Hùng gửi 06/08/2026 cho thấy 2 nút mới trên thẻ clip hiện ra
"Hav" và "Nha" (đúng ra là "Hay"/"Nhạt"). Tôi đặt cứng setFixedWidth(52), mà ĐO
với QSS thật: "Hay" cần 69px, "Nhạt" cần 82px. Máy anh Hùng font còn to hơn máy
dev nên cả nút CŨ cũng đã sát mép (Caption đặt 78px trong khi cần 121px).

BÀI HỌC: **số px cứng KHÔNG BAO GIỜ đúng cho mọi máy**. Phải đo fontMetrics lúc
chạy (`_vua_chu` trong `_clip_row`). Cổng này quét MỌI nút trên thẻ clip ở 3 cỡ
font (mô phỏng máy DPI khác nhau) và FAIL nếu nút hẹp hơn chữ. Có ĐỐI CHỨNG ÂM:
dựng lại đúng lỗi cũ (52px) rồi đòi phép kiểm phải báo sai — không có bước đó
thì cổng dễ "luôn xanh" mà chẳng canh gì.
"""
from __future__ import annotations

import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="nutcut_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  OK  {ten}" + (f" - {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} - {ct}")
        print(f"  SAI {ten} - {ct}")


from pathlib import Path  # noqa: E402

from PyQt6.QtGui import QFont, QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

_app.setStyleSheet(theme.QSS)         # QSS THẬT - không có thì đo ra nhẹ giả

pid = services.create_project("Kênh Thử Nút", "M")
vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                 "VALUES(?,?,?)", (pid, os.path.join(T, "v.mp4"),
                                   600.0)).lastrowid


def _tao_clip(trang_thai="suggested", path=""):
    return db.execute(
        "INSERT INTO clips(video_id,title,start_sec,end_sec,status,signals,"
        "transcript,score,reason,export_path) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (vid, "Cãi nhau to ở cửa hàng tiện lợi", 100.0, 170.0, trang_thai,
         db.dumps({"segments": [[100.0, 135.0], [135.0, 170.0]]}),
         "You lied to my face", 88.0, "vì cãi nhau to", path)).lastrowid


class _St:
    project_id = pid
    video_id = vid


def _the_clip(cid):
    sp = StudioPage.__new__(StudioPage)
    QWidget.__init__(sp)
    sp.state = _St()
    sp.layout_tpl = {}
    sp._thumb = lambda *a, **k: None
    row = dict(db.query_one("SELECT * FROM clips WHERE id=?", (cid,)))
    w = sp._clip_row(row, None, 1)
    w.resize(1600, 110)
    w.show()
    _app.processEvents()
    return w


print("\n=== 1. Mọi nút trên thẻ clip phải ĐỦ RỘNG cho chữ của nó ===")
for ten_cs, cs in (("font mặc định", 0), ("font to 13px", 13),
                   ("font rất to 16px (máy DPI cao)", 16)):
    if cs:
        f = QFont(_app.font())
        f.setPixelSize(cs)
        _app.setFont(f)
    cid = _tao_clip()
    w = _the_clip(cid)
    nut = [b for b in w.findChildren(QPushButton) if b.text()]
    cut = []
    for b in nut:
        can = b.fontMetrics().horizontalAdvance(b.text())
        if b.width() < can + 8:      # +8: chừa mép; dưới mức này là dính/cụt
            cut.append(f"{b.text()!r} rộng {b.width()}px < chữ {can}px")
    ok(not cut, f"1 {ten_cs}: không nút nào cụt chữ",
       f"{len(nut)} nút đều đủ rộng" if not cut else " · ".join(cut))
    db.execute("DELETE FROM clips WHERE id=?", (cid,))
_app.setFont(QFont())                # trả font mặc định

print("\n=== 2. Nút ĐỔI CHỮ (Xuất -> Xuất lại) vẫn không cụt ===")
cid2 = _tao_clip("exported", os.path.join(T, "ra.mp4"))
w2 = _the_clip(cid2)
_xl = [b for b in w2.findChildren(QPushButton) if "xuất" in b.text().lower()]
_can_xl = _xl[0].fontMetrics().horizontalAdvance("Xuất lại") if _xl else 0
ok(bool(_xl) and _xl[0].width() >= _can_xl + 8,
   "2a nút 'Xuất lại' đủ rộng",
   f"{_xl[0].width()}px cho chữ {_can_xl}px" if _xl else "(không thấy nút)")
ok(any(b.text() == "Mở" for b in w2.findChildren(QPushButton)),
   "2b clip đã xuất thì có nút 'Mở'")

print("\n=== 3. Hay/Nhạt: 2 nút CÙNG bề rộng (thẳng hàng) ===")
_hn = [b for b in w2.findChildren(QPushButton) if b.text() in ("Hay", "Nhạt")]
ok(len(_hn) == 2, "3a có đủ 2 nút Hay/Nhạt", str([b.text() for b in _hn]))
ok(len(_hn) == 2 and _hn[0].width() == _hn[1].width(),
   "3b 2 nút bằng nhau", str([b.width() for b in _hn]))
_can_nhat = _hn[0].fontMetrics().horizontalAdvance("Nhạt") if _hn else 0
ok(bool(_hn) and all(b.width() >= _can_nhat + 8 for b in _hn),
   "3c đủ rộng cho chữ DÀI HƠN trong 2 chữ ('Nhạt')",
   f"{[b.width() for b in _hn]}px cho chữ {_can_nhat}px")

print("\n=== 4. KHÔNG còn số px CỨNG cho nút thẻ clip (chống tái phát) ===")
_src = Path(REPO, "app", "ui", "studio_page.py").read_text(
    encoding="utf-8", errors="replace")
_i0 = _src.find("def _clip_row(")
_i1 = _src.find("def _thumb(", _i0)
_than = _src[_i0:_i1]
_cung = [ln.strip()[:64] for ln in _than.splitlines()
         if "QPushButton(" in ln and "setFixedWidth(" in ln]
ok(not _cung, "4a trong _clip_row không còn setFixedWidth cứng cho nút",
   str(_cung[:3]))
ok("_vua_chu(" in _than, "4b dùng _vua_chu (đo font lúc chạy)")

print("\n=== 5. SOI PIXEL + ĐỐI CHỨNG ÂM (cổng có bắt được lỗi cũ không?) ===")
if _hn:
    _b = _hn[0]
    img = QImage(_b.size(), QImage.Format.Format_RGB32)
    _b.render(img)
    mau = set()
    for y in range(0, img.height(), 2):
        for x in range(0, img.width(), 2):
            mau.add(img.pixel(x, y))
    ok(len(mau) >= 3, "5a nút có >= 3 màu (nền + chữ + viền) = chữ vẽ ra THẬT",
       f"{len(mau)} màu")
else:
    ok(False, "5a có nút để soi pixel")

_xau = QPushButton("Nhạt")
_xau.setProperty("ghost", True)
_xau.setFixedWidth(52)               # con số đã gây lỗi thật trên máy anh Hùng
_xau.ensurePolished()
_can = _xau.fontMetrics().horizontalAdvance("Nhạt")
ok(_xau.width() < _can + 8,
   "5b ĐỐI CHỨNG: bề rộng cứng 52px BỊ bắt là cụt (cổng có tác dụng thật)",
   f"52px < chữ {_can}px + mép")
_tot = QPushButton("Nhạt")
_tot.setProperty("ghost", True)
_tot.ensurePolished()
_tot.setFixedWidth(max(56, _tot.fontMetrics().horizontalAdvance("Nhạt") + 30))
ok(_tot.width() >= _can + 8,
   "5c cách MỚI (đo font + padding) thì đủ rộng", f"{_tot.width()}px")

print(f"\n{'=' * 62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  SAI {x}")
    sys.exit(1)
print("CỔNG 31 ĐẠT — nút trên thẻ clip không cụt chữ ở mọi cỡ font")
