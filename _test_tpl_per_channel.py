# -*- coding: utf-8 -*-
# MẪU RIÊNG THEO KÊNH (anh Hùng 31/07: "100 kênh dùng 1 mẫu -> clip trông
# giống nhau"). Bất biến sống còn:
#   - Kênh CÓ gán mẫu -> dây chuyền cắt/xuất bằng ĐÚNG mẫu đó.
#   - Kênh CHƯA gán  -> dùng mẫu đang chọn ở trang chính (Y NHƯ CŨ).
#   - Mẫu bị XOÁ     -> lùi về mẫu đang chọn, KHÔNG được làm chết dây chuyền.
#   - Đổi mẫu trang chính GIỮA LÚC đang chạy -> job đã chốt mẫu không bị đổi.
import os
import sys
from pathlib import Path
import tempfile

T = tempfile.mkdtemp(prefix="tpl_chan_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

import app.queue.jobs  # noqa: F401,E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

qapp = QApplication(sys.argv)
from app.ui.theme import QSS as _QSS  # noqa: E402
qapp.setStyleSheet(_QSS)              # QSS thật (bài học v2.6.23)
from app.database.db import db  # noqa: E402
from app import services  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


# 3 kênh + 2 mẫu
pids = {}
for ten in ("KenhA", "KenhB", "KenhC"):
    pids[ten] = db.execute(
        "INSERT INTO projects(name,assets_dir,grp,pipe_on) VALUES(?,?,'Mỹ',1)",
        (ten, os.path.join(T, ten))).lastrowid
services.save_template("Mẫu ĐỎ", {"dau": "DO", "cap_size": 70})
services.save_template("Mẫu XANH", {"dau": "XANH", "cap_size": 44})

pg = StudioPage(AppState())
pg.show()
qapp.processEvents()
pg.layout_tpl = {"dau": "MẶC ĐỊNH", "cap_size": 55}   # mẫu đang chọn

print("== 1. DB: cột tpl_name tự thêm, mặc định rỗng ==")
cols = [r[1] for r in db.query("PRAGMA table_info(projects)")]
kiem("tpl_name" in cols, "cột tpl_name có trong bảng kênh", str("tpl_name" in cols))
kiem(services.project_template_name(pids["KenhA"]) == "",
     "kênh mới -> chưa gán mẫu ('')")

print("== 2. gán / đọc / đổi / bỏ gán ==")
services.set_project_template(pids["KenhA"], "Mẫu ĐỎ")
kiem(services.project_template_name(pids["KenhA"]) == "Mẫu ĐỎ", "gán được mẫu")
kiem((services.project_template(pids["KenhA"]) or {}).get("dau") == "DO",
     "đọc ra ĐÚNG nội dung mẫu đã gán")
services.set_project_template(pids["KenhA"], "Mẫu XANH")
kiem((services.project_template(pids["KenhA"]) or {}).get("dau") == "XANH",
     "đổi sang mẫu khác -> đọc ra mẫu mới")
services.set_project_template(pids["KenhA"], "")
kiem(services.project_template(pids["KenhA"]) is None,
     "bỏ gán ('') -> trả None (caller dùng mẫu đang chọn)")
services.set_project_template(pids["KenhA"], "  Mẫu ĐỎ  ")
kiem(services.project_template_name(pids["KenhA"]) == "Mẫu ĐỎ",
     "cắt khoảng trắng thừa khi gán")

print("== 3. DÂY CHUYỀN dùng ĐÚNG mẫu của từng kênh ==")
services.set_project_template(pids["KenhB"], "Mẫu XANH")
# KenhC KHÔNG gán -> phải ăn mẫu đang chọn
t_a = pg._tpl_for_project(pids["KenhA"])
t_b = pg._tpl_for_project(pids["KenhB"])
t_c = pg._tpl_for_project(pids["KenhC"])
kiem(t_a.get("dau") == "DO", f"KenhA -> Mẫu ĐỎ", str(t_a))
kiem(t_b.get("dau") == "XANH", f"KenhB -> Mẫu XANH", str(t_b))
kiem(t_c.get("dau") == "MẶC ĐỊNH",
     "KenhC chưa gán -> mẫu đang chọn (hành vi CŨ)", str(t_c))
kiem(t_a.get("cap_size") == 70 and t_b.get("cap_size") == 44,
     "lấy TRỌN nội dung mẫu, không chỉ tên")

print("== 4. mẫu ĐÃ XOÁ -> lùi mẫu đang chọn, KHÔNG chết ==")
services.delete_template("Mẫu ĐỎ")
t_a2 = pg._tpl_for_project(pids["KenhA"])
kiem(t_a2.get("dau") == "MẶC ĐỊNH",
     "mẫu bị xoá -> tự lùi về mẫu đang chọn", str(t_a2))
kiem(services.project_template_name(pids["KenhA"]) == "Mẫu ĐỎ",
     "vẫn GIỮ tên đã gán trong DB (để user thấy mà sửa)")

print("== 5. pid None / pid rác -> không nổ ==")
kiem(pg._tpl_for_project(None).get("dau") == "MẶC ĐỊNH", "pid None -> mẫu đang chọn")
kiem(pg._tpl_for_project(999999).get("dau") == "MẶC ĐỊNH",
     "pid không tồn tại -> mẫu đang chọn")
kiem(services.project_template("xxx") is None, "pid không phải số -> None")

print("== 6. TRẢ BẢN SAO: sửa mẫu trả về KHÔNG đụng mẫu gốc ==")
services.save_template("Mẫu ĐỎ", {"dau": "DO", "cap_size": 70})
t1 = pg._tpl_for_project(pids["KenhA"])
t1["cap_size"] = 999
t2 = pg._tpl_for_project(pids["KenhA"])
kiem(t2.get("cap_size") == 70, "mỗi lần lấy là bản sao mới (deepcopy)",
     str(t2.get("cap_size")))
tpl_goc = pg.layout_tpl
t3 = pg._tpl_for_project(pids["KenhC"])
t3["dau"] = "BỊ SỬA"
kiem(tpl_goc.get("dau") == "MẶC ĐỊNH",
     "sửa bản trả về KHÔNG làm hỏng mẫu đang chọn của app")

print("== 7. CHỐT MẪU theo kênh khi xếp job (đổi mẫu sau không ảnh hưởng) ==")
vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                 "VALUES(?,?,600)",
                 (pids["KenhB"], os.path.join(T, "v.mp4"))).lastrowid
pg.auto_export_chk.setChecked(True)
pg._track_auto(4242, vid, pids["KenhB"])
kiem(pg._auto_tpl.get(4242, {}).get("dau") == "XANH",
     "job của KenhB chốt Mẫu XANH", str(pg._auto_tpl.get(4242)))
pg.layout_tpl = {"dau": "ĐỔI GIỮA ĐƯỜNG"}
services.set_project_template(pids["KenhB"], "Mẫu ĐỎ")
kiem(pg._auto_tpl.get(4242, {}).get("dau") == "XANH",
     "đổi mẫu trang chính + đổi mẫu kênh SAU đó -> job đã chốt KHÔNG đổi")

print("== 8. BẢNG dây chuyền: cột Mẫu hiện + chọn là lưu ==")
from PyQt6.QtWidgets import QDialog  # noqa: E402
QDialog.exec = lambda self: None
pg.layout_tpl = {"dau": "MẶC ĐỊNH"}
pg._pipeline_dialog()
qapp.processEvents()
tbl = pg._pipe_tbl
# 9 cột từ v2.6.24 (thêm cột "Mẫu") -> 10 cột từ v2.22.0 (thêm cột "AI xem
# hình", cổng 51). Cột "Mẫu" phải GIỮ NGUYÊN chỉ số 4 — cột mới chèn SAU nó,
# nếu không thì cú bấm tiêu đề "gán 1 mẫu hàng loạt" rơi vào cột khác.
kiem(tbl.columnCount() == 10, "bảng có 10 cột (Mẫu + AI xem hình)",
     str(tbl.columnCount()))
kiem(tbl.horizontalHeaderItem(4).text() == "Mẫu",
     "cột 4 tên 'Mẫu'", tbl.horizontalHeaderItem(4).text())
kiem(tbl.horizontalHeaderItem(5).text() == "AI xem hình",
     "cột 5 tên 'AI xem hình'", tbl.horizontalHeaderItem(5).text())
cb4 = tbl.cellWidget(0, 4)
kiem(cb4 is not None, "dòng đầu có ô chọn mẫu")
tens = [cb4.itemText(i) for i in range(cb4.count())]
kiem(any(t.startswith("(mẫu đang chọn") for t in tens),
     "có lựa chọn '(mẫu đang chọn: …)'", str(tens))
kiem(cb4.itemData(0) == "" and cb4.itemText(0).startswith("(mẫu đang chọn:"),
     "nhãn NÓI RÕ tên mẫu sẽ dùng thật (anh Hùng tưởng 'chưa chọn' nên định "
     "bấm tay 200 kênh)", cb4.itemText(0))
kiem(any("XANH" in t for t in tens), "liệt kê mẫu đang có", str(tens))
# chọn mẫu -> lưu vào DB
pid0 = None
for r in range(tbl.rowCount()):
    it = tbl.item(r, 0)
    if it is not None:
        pid0 = it.data(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt
                       .ItemDataRole.UserRole)
        cbx = tbl.cellWidget(r, 4)
        i_x = cbx.findData("Mẫu XANH")
        if i_x >= 0 and pid0 is not None:
            cbx.setCurrentIndex(i_x)
            cbx.activated.emit(i_x)
            break
qapp.processEvents()
kiem(services.project_template_name(pid0) == "Mẫu XANH",
     "chọn mẫu trong bảng -> LƯU vào DB ngay",
     f"pid={pid0} -> {services.project_template_name(pid0)!r}")

print("== 9. mẫu đã xoá vẫn hiện trong ô chọn (kèm dấu ⚠) ==")
services.set_project_template(pid0, "Mẫu KHÔNG TỒN TẠI")
pg._pipeline_dialog()
qapp.processEvents()
tbl = pg._pipe_tbl
found = False
for r in range(tbl.rowCount()):
    it = tbl.item(r, 0)
    if it is None:
        continue
    cbx = tbl.cellWidget(r, 4)
    if cbx and cbx.findData("Mẫu KHÔNG TỒN TẠI") >= 0:
        found = "⚠" in cbx.itemText(cbx.findData("Mẫu KHÔNG TỒN TẠI"))
        break
kiem(bool(found), "mẫu đã xoá hiện kèm ⚠ để user biết mà sửa")

print("== 10. GÁN 1 MẪU CHO MỌI KÊNH ĐANG HIỆN (khỏi bấm ~200 kênh) ==")
# anh Hùng 31/07: "giờ tôi bấm từng kênh thì chết gần 200 kênh cơ nó toàn chưa
# chọn" -> phải có đường 1-lần-chọn cho cả bảng, và CHỈ đụng phần ĐANG LỌC.
for _t in ("KenhD", "KenhE"):
    pids[_t] = db.execute(
        "INSERT INTO projects(name,assets_dir,grp,pipe_on) VALUES(?,?,'Mỹ',1)",
        (_t, os.path.join(T, _t))).lastrowid
services.set_project_template(pids["KenhD"], "")
services.set_project_template(pids["KenhE"], "")
pg._pipeline_dialog()
qapp.processEvents()
ds = pg._pipe_rows_pid()
kiem(len(ds) >= 5, f"đọc được {len(ds)} kênh ĐANG HIỆN từ bảng", str(ds))
n = pg._pipe_apply_tpl_all("Mẫu XANH")
kiem(n == len(ds), f"gán 1 lượt cho đúng {len(ds)} kênh", str(n))
kiem(all(services.project_template_name(p) == "Mẫu XANH" for p, _ in ds),
     "MỌI kênh trong bảng nhận mẫu mới (1 lần chọn thay ~200 cú bấm)")
kiem((pg._tpl_for_project(pids["KenhD"]) or {}).get("dau") == "XANH",
     "kênh vừa gán hàng loạt CẮT bằng đúng mẫu đó")

# CHỈ ĐỤNG PHẦN ĐANG LỌC: gõ ô tìm -> bảng còn 1 kênh -> gán chỉ đổi kênh đó
pg._pipe_search.setText("KenhD")
pg._pipe_fill()
qapp.processEvents()
ds2 = pg._pipe_rows_pid()
kiem(len(ds2) == 1 and ds2[0][0] == pids["KenhD"],
     "ô tìm kênh lọc bảng còn đúng 1 kênh", str(ds2))
pg._pipe_apply_tpl_all("")            # '' = ăn theo mẫu trang chính
kiem(services.project_template_name(pids["KenhD"]) == "",
     "kênh ĐANG LỌC được đổi")
kiem(services.project_template_name(pids["KenhE"]) == "Mẫu XANH",
     "kênh KHÔNG hiện (bị lọc ra) KHÔNG bị đụng")
pg._pipe_search.setText("")
pg._pipe_fill()
qapp.processEvents()

print("== 11. đường vào phải TỒN TẠI: menu 🔧 + bấm tiêu đề cột Mẫu ==")
from PyQt6.QtWidgets import QMenu as _QM, QPushButton as _QPB2  # noqa: E402
_muc = []
_goc_exec = _QM.exec
_QM.exec = lambda self, *a, **k: _muc.extend(
    [x.text() for x in self.actions() if x.text()])
try:
    pg._pipe_menu_fix(_QPB2(pg))
finally:
    _QM.exec = _goc_exec
kiem(any("mẫu cho MỌI kênh" in m for m in _muc),
     "menu 'Sửa/làm lại' có mục gán mẫu hàng loạt", str(_muc))
_hh = pg._pipe_tbl.horizontalHeader()
_truoc = services.project_template_name(pids["KenhE"])
from PyQt6.QtWidgets import QInputDialog as _QID  # noqa: E402
_QID.getItem = staticmethod(lambda *a, **k: ("Mẫu XANH", False))   # user HUỶ
_hh.sectionClicked.emit(4)
qapp.processEvents()
kiem(services.project_template_name(pids["KenhE"]) == _truoc,
     "bấm tiêu đề cột Mẫu -> user bấm Huỷ thì KHÔNG đổi gì")
_hh.sectionClicked.emit(1)             # cột khác: không được mở gì
kiem(True, "bấm tiêu đề cột khác không nổ")

print("== 12. ĐƯỜNG THẬT: user chọn mẫu + bấm Đồng ý (có dựng lại bảng) ==")
from PyQt6.QtWidgets import QMessageBox as _QMB  # noqa: E402
_QMB.question = staticmethod(lambda *a, **k: _QMB.StandardButton.Yes)
_QMB.information = staticmethod(lambda *a, **k: None)
_QID.getItem = staticmethod(lambda *a, **k: ("Mẫu ĐỎ", True))
_hh.sectionClicked.emit(4)
qapp.processEvents()
_ds3 = pg._pipe_rows_pid()
kiem(len(_ds3) >= 5, f"bảng dựng lại xong vẫn đủ {len(_ds3)} kênh", str(len(_ds3)))
kiem(all(services.project_template_name(p) == "Mẫu ĐỎ" for p, _ in _ds3),
     "MỌI kênh đang hiện nhận 'Mẫu ĐỎ' sau khi bấm Đồng ý")
_cb0 = pg._pipe_tbl.cellWidget(0, 4)
kiem(_cb0 is not None and _cb0.currentData() == "Mẫu ĐỎ",
     "bảng HIỆN NGAY mẫu mới (không phải mở lại hộp mới thấy)",
     repr(_cb0.currentData() if _cb0 else None))
# huỷ giữa đường (user chọn nhưng bấm No ở hộp xác nhận) -> không đổi
_QMB.question = staticmethod(lambda *a, **k: _QMB.StandardButton.No)
_QID.getItem = staticmethod(lambda *a, **k: ("Mẫu XANH", True))
_hh.sectionClicked.emit(4)
qapp.processEvents()
kiem(all(services.project_template_name(p) == "Mẫu ĐỎ" for p, _ in _ds3),
     "bấm KHÔNG ở hộp xác nhận -> giữ nguyên mẫu cũ")
# '(mẫu đang chọn ở trang chính)' -> bỏ gán cho cả loạt
_QMB.question = staticmethod(lambda *a, **k: _QMB.StandardButton.Yes)
_QID.getItem = staticmethod(
    lambda *a, **k: ("(mẫu đang chọn ở trang chính)", True))
_hh.sectionClicked.emit(4)
qapp.processEvents()
kiem(all(services.project_template_name(p) == "" for p, _ in _ds3),
     "chọn '(mẫu đang chọn ở trang chính)' -> BỎ gán cho cả loạt (về như cũ)")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — mỗi kênh 1 mẫu riêng, chưa gán thì như cũ")
sys.stdout.flush()
os._exit(0)
