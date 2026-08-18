# -*- coding: utf-8 -*-
"""ĐO Ô NHẬP KEY VBEE trong hộp "Cài đặt AI" — KHÔNG gọi mạng, KHÔNG tốn điểm.

VÌ SAO CÓ FILE NÀY THAY VÌ DỰA VÀO `_test_app_smoke.py`: cổng smoke ĐANG HỎNG
SẴN ở bước "bấm mọi nút trên cửa sổ chính" (mã thoát 127, chết câm không
traceback). Đã chứng minh KHÔNG phải do việc Vbee, bằng 3 lượt chạy:
    · có bản vá Vbee            -> RC 127, chết đúng chỗ đó
    · gỡ bản vá studio_page     -> RC 127, chết đúng chỗ đó
    · gỡ SẠCH (config + module) -> RC 127, chết đúng chỗ đó
Tức nó hỏng từ trước commit Vbee. Nút trên màn chính có nút mở
`thay_giong_dialog.py` — file hai luồng khác ĐANG GIỮ và sửa dở. Không đụng
vào, chỉ tự canh phần của mình.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
_SB = Path(tempfile.mkdtemp(prefix="bq_vbeeui_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ.pop("VBEE_APP_ID", None)
os.environ.pop("VBEE_TOKEN", None)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _test_guard  # noqa: F401,E402  - BẮT BUỘC với test dựng UI

from PyQt6.QtWidgets import (QApplication, QCheckBox, QDialog, QLabel,  # noqa: E402
                             QLineEdit, QPushButton, QWidget)

DAT = HONG = 0


def ok(dieu: str, tot: bool, ghi: str = "") -> None:
    global DAT, HONG
    if tot:
        DAT += 1
        print(f"  DAT   {dieu}" + (f"  [{ghi}]" if ghi else ""))
    else:
        HONG += 1
        print(f"  HONG  {dieu}" + (f"  [{ghi}]" if ghi else ""))


app = QApplication.instance() or QApplication(sys.argv)
from app.ui.theme import QSS  # noqa: E402
app.setStyleSheet(QSS)          # ÁP QSS THẬT (bài học cổng 9 v2.6.23a)

# Hộp thoại phải KHÔNG chặn: exec() -> no-op, và ta giữ lại con trỏ để soi.
_hop: list = []
QDialog.exec = lambda self: (_hop.append(self), 0)[1]   # type: ignore

from app.ui.studio_page import StudioPage  # noqa: E402

# Dựng StudioPage bằng __new__ + QWidget.__init__ — KHÔNG dựng UI đầy đủ
# (treo/chậm trong sandbox). QWidget.__init__ là BẮT BUỘC, thiếu là
# QDialog(self) nổ "super-class __init__ never called" (bài học cổng 29).
sp = StudioPage.__new__(StudioPage)
QWidget.__init__(sp)

print("\n=== 1. HOP CAI DAT AI MO DUOC, CO THE VBEE ===")
try:
    sp._ai_settings()
    nem = False
except Exception as e:  # noqa: BLE001
    nem = True
    print(f"    (da nem: {type(e).__name__}: {e})")
ok("_ai_settings() KHONG nem", not nem)
ok("dung duoc 1 hop thoai", len(_hop) == 1)

dlg = _hop[0] if _hop else None
labels = [w.text() for w in dlg.findChildren(QLabel)] if dlg else []
edits = dlg.findChildren(QLineEdit) if dlg else []
btns = dlg.findChildren(QPushButton) if dlg else []
checks = dlg.findChildren(QCheckBox) if dlg else []

ok("co the 'Giong Vbee AIVoice'",
   any("Vbee AIVoice" in t for t in labels),
   next((t for t in labels if "Vbee AIVoice" in t), "KHONG THAY"))
ok("co o 'Vbee App ID'", any("Vbee App ID" in t for t in labels))
ok("co o 'Vbee Access token'", any("Vbee Access token" in t for t in labels))
ok("co nut 'Kiem tra key Vbee'",
   any("Kiểm tra key Vbee" in b.text() for b in btns))
ok("co o tich 'Hien token'", any("Hiện token" in c.text() for c in checks))

print("\n=== 2. TOKEN BI CHE MAC DINH ===")
vb_tk = None
for i, w in enumerate(edits):
    if w.echoMode() == QLineEdit.EchoMode.Password:
        vb_tk = w
ok("o token dat EchoMode.Password", vb_tk is not None)
if vb_tk is not None:
    hien = next((c for c in checks if "Hiện token" in c.text()), None)
    if hien is not None:
        hien.setChecked(True)
        ok("tich 'Hien token' -> hien ro",
           vb_tk.echoMode() == QLineEdit.EchoMode.Normal)
        hien.setChecked(False)
        ok("bo tich -> che lai",
           vb_tk.echoMode() == QLineEdit.EchoMode.Password)

print("\n=== 3. BAM 'KIEM TRA' KHI CHUA CO KEY -> BAO EM, KHONG GOI MANG ===")
# Chặn mọi lượt mở mạng: bấm lúc chưa có key mà vẫn gọi ra ngoài là sai.
import urllib.request as _u  # noqa: E402
_goi_mang = {"n": 0}
_that_urlopen = _u.urlopen


def _cam_mang(*a, **k):
    _goi_mang["n"] += 1
    raise AssertionError("KHONG duoc goi mang khi chua co key")


_u.urlopen = _cam_mang
vbbtn = next((b for b in btns if "Kiểm tra key Vbee" in b.text()), None)
try:
    if vbbtn is not None:
        vbbtn.click()
    nem2 = False
except Exception as e:  # noqa: BLE001
    nem2 = True
    print(f"    (da nem: {type(e).__name__}: {e})")
_u.urlopen = _that_urlopen
ok("bam nut KHONG nem", not nem2)
ok("KHONG goi mang mot lan nao", _goi_mang["n"] == 0, f"{_goi_mang['n']} lan")
vbstat = dlg.findChild(QLabel, "vbee_status_label") if dlg else None
ok("nhan bao 'Chua du key Vbee'",
   vbstat is not None and "Chưa đủ key" in vbstat.text(),
   (vbstat.text()[:70] if vbstat is not None else "KHONG THAY"))
ok("nhan noi ro can CA HAI thu",
   vbstat is not None and "App ID" in vbstat.text()
   and "token" in vbstat.text())

print("\n=== 4. NHAN KHONG EMOJI (may anh Hung thieu glyph -> o den) ===")


def co_emoji(s: str) -> bool:
    return any(ord(c) > 0x2100 for c in s)


vb_txt = [t for t in labels if "Vbee" in t]
for t in vb_txt:
    ok(f"nhan Vbee khong emoji: {t[:44]}...", not co_emoji(t))
ok("nut 'Kiem tra key Vbee' khong emoji",
   vbbtn is not None and not co_emoji(vbbtn.text()))
ok("3 dieu canh bao co mat trong nhan",
   any("98,6%" in t for t in vb_txt) and any("1 điểm" in t for t in vb_txt)
   and any("kiếm tiền" in t for t in vb_txt))

print("\n=== 5. TU KIEM BO DO (cong khong phai con dau) ===")
ok("bo do emoji BAT duoc emoji that", co_emoji("Giọng Vbee 🎧"))
ok("bo do emoji KHONG bat oan chu Viet co dau",
   not co_emoji("Giọng HN - Ngọc Huyền (nữ), điểm, kiếm tiền"))

print("\n" + "=" * 62)
print(f"DAT {DAT} · HONG {HONG}")
sys.exit(1 if HONG else 0)
