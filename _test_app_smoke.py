# SMOKE TOÀN APP: dựng cửa sổ chính THẬT rồi BẤM MỌI NÚT ở mọi trang/hộp thoại.
#
# Vì sao cần: file UI import CỤC BỘ TỪNG HÀM nên dùng tên đã import ở hàm khác
# sẽ nổ NameError CHỈ KHI bấm nút. compileall + import mọi module + pyflakes
# đều có giới hạn — chỉ BẤM THẬT mới chắc. (Lỗi thật v2.5.0: bấm 🗑 Thùng rác
# nổ NameError, ra tới máy anh Hùng.)
#
# An toàn: DB + data trong thư mục tạm; mọi hộp xác nhận trả "No"; mọi hộp chọn
# file/thư mục trả rỗng → nút phá dữ liệu tự huỷ giữa đường.
import faulthandler
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

faulthandler.enable()      # chết cứng thì in ngăn xếp C-level
T = Path(tempfile.mkdtemp(prefix="app_smoke_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry thật
sys.path.insert(0, r"D:\claude\ai-content-studio")
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = Path(r"D:\claude\ai-content-studio\bin\ffmpeg.exe")

import app.queue.jobs  # noqa: F401,E402 - handler + cv2 TRƯỚC Qt

from PyQt6.QtCore import QSettings, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QCheckBox, QColorDialog,  # noqa: E402
                             QComboBox, QDialog, QFileDialog, QInputDialog,
                             QMenu, QMessageBox, QPushButton, QSpinBox,
                             QToolButton, QWidget)
from app.ui.appsettings import app_settings  # noqa: E402

qapp = QApplication(sys.argv)
st_q = app_settings()
_KEYS = ("pipe_root", "chan_group", "chan_groups_extra", "pipe_grp_sel",
         "pipe_recycle_dir", "last_template")
_saved = {k: st_q.value(k) for k in _KEYS}

from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402

LOI: list[str] = []

# ── dữ liệu thật tối thiểu: 1 kênh + 1 video + 1 clip + thùng rác có file ──
src = T / "nguon" / "Kênh Smoke"
src.mkdir(parents=True)
vid_f = src / "v1.mp4"
subprocess.run([str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
                "testsrc=size=320x240:rate=15:duration=1", "-f", "lavfi", "-i",
                "sine=frequency=440:duration=1", "-c:v", "libx264", "-preset",
                "ultrafast", "-c:a", "aac", "-shortest", str(vid_f)], check=True)
_o = time.time() - 90
os.utime(vid_f, (_o, _o))
rac = T / "thungrac"
for sub, fn in (("_DaXoa/2026-07-26/Kênh Smoke", "cu.mp4"),
                ("_Loi/Kênh Smoke", "hong.mp4")):
    d = rac / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / fn).write_bytes(b"x" * 100)

st_q.setValue("pipe_root", str(T / "nguon"))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.setValue("pipe_recycle_dir", str(rac))
st_q.sync()

pid = db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_src, pipe_on, "
    "pipe_mode, pipe_daily) VALUES('Kênh Smoke', ?, 'Mỹ', ?, ?, 1, 'auto', 0)",
    (str(T / "assets"), str(src), str(src))).lastrowid
vid = db.insert(
    "INSERT INTO videos(project_id, src_path, file_hash, duration, width, "
    "height, fps, has_audio) VALUES(?,?,?,?,?,?,?,1)",
    (pid, str(vid_f), "h_smoke", 1.0, 320, 240, 15.0))
db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
           "status) VALUES(?,0.0,0.5,0.9,'Clip smoke','ready')", (vid,))

# ── vá MỌI thứ chặn người dùng (không có ai bấm hộ) ──
# PHẢI vá exec của TỪNG lớp hộp thoại, không chỉ QDialog: QFileDialog /
# QColorDialog / QFontDialog tự cài lại exec nên vá QDialog KHÔNG chặn được —
# bấm "Chọn logo (PNG)…" sẽ mở hộp chọn file THẬT và treo test vĩnh viễn
# (đo được: rc=124 timeout đúng ở nút đó).
from PyQt6.QtWidgets import QFontDialog, QProgressDialog  # noqa: E402

for _cls in (QDialog, QMessageBox, QFileDialog, QColorDialog, QFontDialog,
             QProgressDialog, QInputDialog):
    _cls.exec = lambda self: 0            # type: ignore[assignment]
QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: 0
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: None)
QMessageBox.about = staticmethod(lambda *a, **k: None)
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, False))
QColorDialog.getColor = staticmethod(lambda *a, **k: None)
QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#FF8800"))
QFontDialog.getFont = staticmethod(lambda *a, **k: (QFont("Arial"), False))
QMenu.exec = lambda self, *a, **k: None

# ── TỰ KIỂM BẢN VÁ: bắt buộc, không được tin là "đã vá" ──
# Bài học đau: tôi tưởng đã vá QColorDialog nhưng lệnh vá không ăn → bấm nút
# chọn màu mở hộp màu THẬT → test treo → tôi lại tưởng app crash và đi tìm lỗi
# không tồn tại. Harness phải chứng minh chính nó đã bịt kín trước khi chạy.
def _tu_kiem() -> None:
    import threading
    xong = {"v": False}

    def thu():
        QColorDialog.getColor(QColor("#FFFFFF"), None, "tự kiểm")
        QFileDialog.getOpenFileName(None, "tự kiểm")
        QFileDialog.getExistingDirectory(None, "tự kiểm")
        QInputDialog.getText(None, "tự kiểm", "?")
        xong["v"] = True

    t = threading.Thread(target=thu, daemon=True)
    t.start()
    t.join(5.0)
    if not xong["v"]:
        print("❌ BẢN VÁ HỘP THOẠI KHÔNG ĂN — hộp thoại thật vẫn mở và chặn. "
              "Test sẽ treo, dừng ngay thay vì báo lỗi oan cho app.")
        sys.stdout.flush()
        os._exit(2)
    print("  ✓ tự kiểm: mọi hộp thoại chặn-người-dùng đã bị vô hiệu")


from app.ui.main_window import MainWindow  # noqa: E402

# CHẶN mở cửa sổ ngoài (Explorer/trình phát/link) — nay dùng CANH CỔNG CHUNG
# `_test_guard` để MỌI test đều được che, không phải mỗi file vá riêng: lỗi
# 31/07/2026 là _test_pipe_dialogs.py thiếu bản vá này nên bấm "📂 Mở thư mục
# log" là Explorer nhảy lên màn hình anh Hùng mỗi lần chạy cổng test.
_test_guard.tu_kiem()

state = AppState()
win = MainWindow(state)
if not hasattr(win.studio, "_pipe_report"):
    win.studio._pipe_report = []
win.studio.state.project_id = pid
win.studio.state.video_id = vid
qapp.processEvents()


def nhan(w, nhan_txt: str, moc: str) -> None:
    """Bấm 1 widget, ghi lỗi nếu nổ."""
    try:
        if isinstance(w, (QPushButton, QToolButton)):
            w.click()
        elif isinstance(w, QCheckBox):
            w.toggle()
        qapp.processEvents()
    except RuntimeError as e:
        if "has been deleted" in str(e):
            return                   # UI dựng lại xoá nút — không phải lỗi app
        LOI.append(f"[{moc}] '{nhan_txt}' → RuntimeError: {e}")
    except Exception as e:  # noqa: BLE001
        LOI.append(f"[{moc}] '{nhan_txt}' → {type(e).__name__}: {e}\n"
                   + "".join(traceback.format_tb(e.__traceback__)[-2:]))


def quet(goc: QWidget, moc: str, bo_qua=()) -> int:
    """Bấm mọi nút/checkbox trong 1 widget. Trả số widget đã bấm.

    Bấm 1 nút thường làm UI DỰNG LẠI → các nút khác trong danh sách bị Qt xoá,
    chạm vào là RuntimeError('wrapped C/C++ object has been deleted'). Nên phải
    bọc từng lần chạm và bỏ qua nút đã chết, chứ không phải lỗi sản phẩm.
    """
    n = 0
    for w in list(goc.findChildren((QPushButton, QToolButton, QCheckBox))):
        try:
            t = (w.text() or w.toolTip() or w.objectName() or "?").strip()
            if not w.isEnabled():
                continue
        except RuntimeError:
            continue                 # nút đã bị dựng-lại-UI xoá → bỏ qua
        if any(k.lower() in t.lower() for k in bo_qua):
            continue
        nhan(w, t, moc)
        n += 1
    return n


_tu_kiem()
print("\n" + "=" * 66)
print("SMOKE TOÀN APP — bấm mọi nút, mọi trang, mọi hộp thoại")
print("=" * 66)

# 1) đổi giá trị MỌI combo/spin trên màn chính (đổi mẫu, nhóm, chế độ…)
print("\n── 1. đổi mọi combo/spin trên màn chính ──")
n_cb = 0
for cb in win.findChildren(QComboBox):
    try:
        for i in range(min(cb.count(), 4)):
            cb.setCurrentIndex(i)
            qapp.processEvents()
        n_cb += 1
    except Exception as e:  # noqa: BLE001
        LOI.append(f"[combo] '{cb.objectName() or '?'}' → {type(e).__name__}: {e}")
for sp in win.findChildren(QSpinBox):
    try:
        sp.setValue(sp.maximum())
        sp.setValue(sp.minimum())
        qapp.processEvents()
    except Exception as e:  # noqa: BLE001
        LOI.append(f"[spin] → {type(e).__name__}: {e}")
print(f"  đã đổi {n_cb} combo + mọi spin")

# 2) bấm mọi nút trên cửa sổ chính. BỎ QUA nút đăng xuất (đóng app) và các nút
#    chạy việc nặng thật (đã có test riêng cho chúng).
print("\n── 2. bấm mọi nút trên cửa sổ chính ──")
# "Mixed-Cut" đã GỠ khỏi danh sách này: nút đó KHÔNG còn trong UI (bỏ 07/08/2026
# theo yêu cầu anh Hùng). Để tên lại thì vô hại nhưng dễ tưởng app vẫn có nút.
BO_QUA_CHINH = ("Đăng xuất", "Tạo clip", "Tất cả video", "Chọn nhiều",
                "Reup thuyết minh", "Xuất cả kênh",
                "Xuất video này", "Tải về", "Tải nhiều", "Xuất", "Cắt lại")
n = quet(win, "màn chính", BO_QUA_CHINH)
print(f"  đã bấm {n} nút")

# 3) mở TỪNG hộp thoại rồi bấm mọi nút BÊN TRONG nó
print("\n── 3. mở từng hộp thoại + bấm mọi nút bên trong ──")
S = win.studio
HOP = [
    ("🤖 Dây chuyền", lambda: S._pipeline_dialog(), "_pipe_dlg",
     ("Chạy dây chuyền",)),
    ("🗑 Thùng rác", lambda: S._pipe_recycle_dialog(), "_recycle_dlg", ()),
    ("🧹 Dọn file rác", lambda: S._pipe_clean_junk_dialog(), None, ()),
    ("🔧 Cứu video kẹt", lambda: S._pipe_resume_dialog(), None, ()),
    ("Quản lý nhóm & kênh", lambda: S._manage_groups(), None, ()),
    ("Quản lý video", lambda: S._manage_videos(), None, ()),
    ("Quản lý kênh", lambda: S._manage_projects(), None, ()),
    ("Sửa cấu hình kênh", lambda: S._build_edit_proj_dialog(pid), None, ()),
]
for ten, mo, attr, bo in HOP:
    try:
        r = mo()
        qapp.processEvents()
        print(f"  ✓ mở {ten}")
    except Exception as e:  # noqa: BLE001
        LOI.append(f"[mở hộp thoại] {ten} → {type(e).__name__}: {e}\n"
                   + "".join(traceback.format_tb(e.__traceback__)[-2:]))
        print(f"  ✗ mở {ten}  << {type(e).__name__}: {e}")
        continue
    dlg = getattr(S, attr, None) if attr else (r if isinstance(r, QWidget) else None)
    if dlg is not None:
        k = quet(dlg, f"trong {ten}", bo)
        print(f"      bấm {k} nút bên trong")

# 4) các hộp thoại module riêng: Chỉnh mẫu, Cài đặt Reup, Cài đặt AI, Tiến trình
print("\n── 4. hộp thoại module riêng ──")
RIENG = []
# Chữ ký THẬT (đọc từ code, không đoán — lần đầu tôi đoán sai và test tự báo
# lỗi oan): EditorDialog(frame_path, layout=None, parent=None, current_name="")
# · RecapSettingsDialog(parent=None) · UpdateDialog(info: dict, parent=None)
try:
    from app.ui.editor import EditorDialog
    RIENG.append(("Chỉnh mẫu (editor)",
                  lambda: EditorDialog(S._sample_frame(),
                                       dict(S.layout_tpl), win)))
except Exception as e:  # noqa: BLE001
    LOI.append(f"[import] editor → {e}")
try:
    from app.ui.recap_settings import RecapSettingsDialog
    RIENG.append(("Cài đặt Reup", lambda: RecapSettingsDialog(win)))
except Exception as e:  # noqa: BLE001
    LOI.append(f"[import] recap_settings → {e}")
try:
    from app.ui.update_dialog import UpdateDialog
    # khoá THẬT mà UpdateDialog đọc: info['tag'] + info['asset_url']
    RIENG.append(("Cập nhật", lambda: UpdateDialog(
        {"tag": "v9.9.9", "asset_url": "", "notes": "ghi chú", "size": 0}, win)))
except Exception as e:  # noqa: BLE001
    LOI.append(f"[import] update_dialog → {e}")
for ten, tao in RIENG:
    print(f"  → đang dựng {ten} ...", flush=True)
    try:
        d = tao()
        print(f"    dựng xong {ten}, bắt đầu bấm nút", flush=True)
        qapp.processEvents()
        k = quet(d, f"trong {ten}", ("Lưu", "OK", "Áp dụng"))
        print(f"  ✓ {ten} — bấm {k} nút bên trong")
    except Exception as e:  # noqa: BLE001
        LOI.append(f"[hộp riêng] {ten} → {type(e).__name__}: {e}\n"
                   + "".join(traceback.format_tb(e.__traceback__)[-2:]))
        print(f"  ✗ {ten}  << {type(e).__name__}: {e}")

# 5) đập nhịp poll nhiều lần (đường chạy mỗi 1.5s trên máy thật)
print("\n── 5. chạy nhịp poll 40 lần ──")
for i in range(40):
    try:
        S._poll_tick()
        qapp.processEvents()
    except Exception as e:  # noqa: BLE001
        LOI.append(f"[poll_tick lần {i}] {type(e).__name__}: {e}")
        break
print("  xong")

for k, v in _saved.items():
    if v is None:
        st_q.remove(k)
    else:
        st_q.setValue(k, v)
st_q.sync()
print("\n" + "=" * 66)
if LOI:
    print(f"❌ {len(LOI)} LỖI:")
    for x in LOI:
        print("   -", x)
else:
    print("✅ KHÔNG LỖI: mọi trang, mọi nút, mọi hộp thoại, 40 nhịp poll")
print("=" * 66)
sys.stdout.flush()
os._exit(1 if LOI else 0)
