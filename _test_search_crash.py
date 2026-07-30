# -*- coding: utf-8 -*-
# TÁI HIỆN CRASH (anh Hùng 30/07): "cứ vào phần tìm kiếm là crash app".
# Ô Kênh ở màn chính thành editable + QCompleter(model của chính combo) —
# nghi 3 điểm CHẾT THẬT:
#   A. Gõ chữ -> Qt đổi currentIndex -> _on_proj chạy giữa lúc đang gõ.
#   B. _reload_projects() gọi combo.clear() TRONG LÚC popup completer đang mở
#      (nhịp poll / đổi nhóm / kênh mới) -> Qt free model đang được popup dùng.
#   C. _refresh_proj_marks() đổi text item trong lúc completer đang lọc.
# PyQt6: exception trong slot = qFatal = ABORT tiến trình -> phải chạy THẬT
# bằng QTest keystroke, không mock.
import faulthandler
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="search_crash_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")
faulthandler.enable()

import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

qapp = QApplication(sys.argv)

from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  OK   " if ok else "  FAIL ") + nhan + ("" if ok else f"  << {ct}"))
    sys.stdout.flush()
    if not ok:
        FAIL.append(nhan)


# 60 kênh 2 nhóm — giống máy anh Hùng (nhiều kênh, có nhóm)
for i in range(1, 61):
    grp = "Mỹ" if i % 2 else "Mỹ mới"
    db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES(?,?,?)",
               (f"Kenh {i} News", os.path.join(T, f"a{i}"), grp))

pg = StudioPage(AppState())
pg.show()
qapp.processEvents()
cb = pg.proj
le = cb.lineEdit()
print(f"(combo Kenh: {cb.count()} item, editable={cb.isEditable()})")

# ── A. GÕ THẬT từng ký tự (đúng cái anh Hùng làm) ──
print("\n== A. go tung ky tu vao o Kenh ==")
le.setFocus()
le.clear()
for ch in "Kenh 1":
    QTest.keyClicks(le, ch)
    qapp.processEvents()
kiem(True, "go 6 ky tu khong sap")

# ── B. GÕ rồi CLEAR danh sách (nhịp poll/đổi nhóm) trong lúc popup completer mở ──
print("\n== B. reload danh sach TRONG LUC popup completer dang mo ==")
comp = cb.completer()
le.clear()
QTest.keyClicks(le, "Kenh")
qapp.processEvents()
popup_mo = comp.popup().isVisible() if comp else False
print(f"   (popup completer dang mo: {popup_mo})")
pg._reload_projects()          # <-- combo.clear() giữa lúc popup dùng model
qapp.processEvents()
kiem(True, "reload_projects luc popup mo khong sap")

# ── C. Đổi text item (đuôi trạng thái) lúc đang gõ/lọc ──
print("\n== C. _refresh_proj_marks luc dang go ==")
le.clear()
QTest.keyClicks(le, "New")
qapp.processEvents()
pg._refresh_proj_marks()
qapp.processEvents()
kiem(True, "refresh_proj_marks luc dang loc khong sap")

# ── D. ENTER với chữ KHÔNG khớp kênh nào ──
print("\n== D. Enter voi chu la ==")
truoc = pg.state.project_id
le.clear()
QTest.keyClicks(le, "zzz khong co that")
QTest.keyClick(le, Qt.Key.Key_Return)
qapp.processEvents()
kiem(pg.state.project_id == truoc, "Enter chu la KHONG doi kenh",
     f"{truoc} -> {pg.state.project_id}")

# ── E. ĐỔI NHÓM trong lúc ô tìm còn chữ (đường anh Hùng hay đi) ──
print("\n== E. doi nhom luc o tim con chu ==")
le.clear()
QTest.keyClicks(le, "Kenh 2")
qapp.processEvents()
if hasattr(pg, "grp") and pg.grp.count() > 1:
    pg.grp.setCurrentIndex(1)
    qapp.processEvents()
kiem(True, "doi nhom luc dang go khong sap")

# ── F. gõ liên tục + popup + xoá, 40 vòng (bão sự kiện) ──
print("\n== F. bao su kien: 40 vong go/xoa/popup ==")
for v in range(40):
    le.clear()
    QTest.keyClicks(le, "Kenh")
    if v % 5 == 0:
        cb.showPopup()
        qapp.processEvents()
        cb.hidePopup()
    if v % 7 == 0:
        pg._reload_projects()
    qapp.processEvents()
kiem(True, "40 vong khong sap")

# (BỎ ca chuột phải: QMenu.exec là modal, không vô hiệu được trên lớp sip ->
#  test treo. Menu chuột phải đã được cổng _test_app_smoke mở/bấm.)

print()
if FAIL:
    print(f"KET QUA: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KET QUA: KHONG SAP o moi duong go-tim")
sys.stdout.flush()
os._exit(0)
