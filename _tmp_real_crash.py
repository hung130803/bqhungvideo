# -*- coding: utf-8 -*-
# CHẨN ĐOÁN CRASH THẬT: chạy trên NỀN TẢNG THẬT (không offscreen) vì popup
# completer của Qt chỉ tạo cửa sổ native khi có màn hình. error.log của anh
# Hùng KHÔNG có dòng nào hôm nay => crash NATIVE (Qt abort), không phải
# exception Python. faulthandler ghi ra file để bắt frame native.
import faulthandler
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="real_crash_")
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")

CRASH_LOG = open(os.path.join(r"D:\bq_test_tmp", "faulthandler.txt"), "w")
faulthandler.enable(file=CRASH_LOG, all_threads=True)


def buoc(n):
    print(f"[BUOC] {n}", flush=True)
    CRASH_LOG.write(f"[BUOC] {n}\n")
    CRASH_LOG.flush()


import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtCore import QPoint, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

qapp = QApplication(sys.argv)

from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

# 300 kênh — đúng cỡ máy anh Hùng
for i in range(1, 301):
    db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES(?,?,?)",
               (f"Kenh {i} News", os.path.join(T, f"a{i}"),
                "Mỹ" if i % 2 else "Mỹ mới"))

pg = StudioPage(AppState())
pg.resize(900, 500)
pg.move(-2000, -2000)          # đẩy ra ngoài màn hình, không cướp việc anh Hùng
pg.show()
qapp.processEvents()
cb = pg.proj
le = cb.lineEdit()
print(f"(items={cb.count()} editable={cb.isEditable()})", flush=True)

buoc("1. bam vao o tim + go 'Kenh 12'")
le.setFocus()
for ch in "Kenh 12":
    QTest.keyClicks(le, ch)
    qapp.processEvents()

buoc("2. EP popup completer mo that")
comp = cb.completer()
comp.setCompletionPrefix("Kenh 12")
comp.complete()
qapp.processEvents()
print("   popup visible:", comp.popup().isVisible(), flush=True)

buoc("3. CHON 1 goi y bang Enter (duong anh Hung di)")
QTest.keyClick(comp.popup(), Qt.Key.Key_Down)
qapp.processEvents()
QTest.keyClick(comp.popup(), Qt.Key.Key_Return)
qapp.processEvents()
print("   pid sau chon:", pg.state.project_id, flush=True)

buoc("4. showPopup (duoi trang thai) LUC dang co chu")
le.clear()
QTest.keyClicks(le, "Kenh")
qapp.processEvents()
cb.showPopup()
qapp.processEvents()
cb.hidePopup()
qapp.processEvents()

comp.setCompletionPrefix("Ken"); comp.complete(); qapp.processEvents()
buoc("5. _refresh_proj_marks 300 item luc popup completer MO")
le.clear()
QTest.keyClicks(le, "Ken")
qapp.processEvents()
pg._refresh_proj_marks()
qapp.processEvents()

comp.setCompletionPrefix("Ken"); comp.complete(); qapp.processEvents()
buoc("6. clear() model luc popup completer MO (reload_projects)")
le.clear()
QTest.keyClicks(le, "Ken")
qapp.processEvents()
pg._reload_projects()
qapp.processEvents()

buoc("7. doi NHOM luc dang go")
le.clear()
QTest.keyClicks(le, "Kenh 2")
qapp.processEvents()
if hasattr(pg, "grp") and pg.grp.count() > 1:
    pg.grp.setCurrentIndex(1 if pg.grp.currentIndex() != 1 else 0)
    qapp.processEvents()

buoc("8. bao: 30 vong go + popup + reload")
for v in range(30):
    le.clear()
    QTest.keyClicks(le, "Kenh 1")
    if v % 4 == 0:
        cb.showPopup(); qapp.processEvents(); cb.hidePopup()
    if v % 6 == 0:
        pg._reload_projects()
    qapp.processEvents()

buoc("9. XONG — khong crash")
print("KET QUA: KHONG CRASH tren nen tang that", flush=True)
CRASH_LOG.flush()
os._exit(0)
