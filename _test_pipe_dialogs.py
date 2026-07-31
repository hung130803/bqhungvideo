# SMOKE MỌI HỘP THOẠI: mở từng hộp thoại một lần để bắt lỗi NGAY KHI BẤM.
#
# LỖI THẬT (anh Hùng, v2.5.0): bấm 🗑 Thùng rác là nổ
#   NameError: name 'NoWheelComboBox' is not defined
# vì file studio_page.py import CỤC BỘ TỪNG HÀM — tên import trong
# _pipeline_dialog KHÔNG dùng được ở _pipe_recycle_dialog. compileall và
# import-module đều KHÔNG bắt được loại này (chỉ nổ khi thân hàm chạy thật).
#
# Test này mở TỪNG hộp thoại với QDialog.exec / QMessageBox.exec / QFileDialog
# bị vá thành no-op, nên chạy nhanh và không cần người bấm.
# Chạy CÙNG `python -m pyflakes app/` trước mỗi lần phát hành.
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="pipe_dlg_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry thật
sys.path.insert(0, r"D:\claude\ai-content-studio")
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = Path(r"D:\claude\ai-content-studio\bin\ffmpeg.exe")

import app.queue.jobs  # noqa: F401,E402 - handler + cv2 TRƯỚC Qt

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,  # noqa: E402
                             QInputDialog, QMenu, QMessageBox)
from app.ui.appsettings import app_settings  # noqa: E402

qapp = QApplication(sys.argv)
st_q = app_settings()
_saved = {k: st_q.value(k) for k in
          ("pipe_root", "chan_group", "chan_groups_extra", "pipe_grp_sel",
           "pipe_recycle_dir")}

from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL: list[str] = []

# ── dựng 1 kênh + 1 video thật + 1 video trong Thùng rác để hộp thoại có data ──
src = T / "nguon" / "Kênh Smoke"
src.mkdir(parents=True)
vid_f = src / "v1.mp4"
subprocess.run([str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
                "testsrc=size=320x240:rate=15:duration=1", "-c:v", "libx264",
                "-preset", "ultrafast", str(vid_f)], check=True)
old = time.time() - 90
os.utime(vid_f, (old, old))
rac = T / "thungrac"
(rac / "_DaXoa" / "2026-07-26" / "Kênh Smoke").mkdir(parents=True)
(rac / "_DaXoa" / "2026-07-26" / "Kênh Smoke" / "cu.mp4").write_bytes(b"x" * 100)
(rac / "_Loi" / "Kênh Smoke").mkdir(parents=True)
(rac / "_Loi" / "Kênh Smoke" / "hong.mp4").write_bytes(b"y" * 100)

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
    (pid, str(vid_f), "hash_smoke", 1.0, 320, 240, 15.0))
db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
           "status) VALUES(?,0.0,0.5,0.9,'Clip smoke','ready')", (vid,))

# ── vá mọi thứ CHẶN người dùng: dialog exec + hộp chọn file/thư mục ──
QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: 0
QMessageBox.question = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.No)     # luôn HUỶ -> không phá data
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: None)
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))
QMenu.exec = lambda self, *a, **k: None
# CANH CỔNG: nút "📂 Mở thư mục log" trong hộp Dây chuyền gọi os.startfile ->
# TRƯỚC v2.6.25 mỗi lần chạy test là 1 cửa sổ Explorer nhảy lên máy anh Hùng.
_test_guard.tu_kiem()

state = AppState()
pg = StudioPage(state)
pg._pipe_report = []
pg.state.project_id = pid
pg.state.video_id = vid

HOP_THOAI = [
    ("🤖 Dây chuyền tự động", lambda: pg._pipeline_dialog()),
    ("🗑 Thùng rác / Khôi phục", lambda: pg._pipe_recycle_dialog()),
    ("🧹 Dọn file rác", lambda: pg._pipe_clean_junk_dialog()),
    ("🔧 Cứu video kẹt", lambda: pg._pipe_resume_dialog()),
    ("Quản lý nhóm & kênh", lambda: pg._manage_groups()),
    ("Quản lý video", lambda: pg._manage_videos()),
    ("Quản lý kênh", lambda: pg._manage_projects()),
    ("Sửa tên/cấu hình kênh", lambda: pg._build_edit_proj_dialog(pid)),
]

print("\n══ SMOKE: mở từng hộp thoại (bắt lỗi ngay khi bấm) ══")
for ten, mo in HOP_THOAI:
    try:
        mo()
        qapp.processEvents()
        print(f"  ✓ {ten}")
    except Exception as e:  # noqa: BLE001
        FAIL.append(f"{ten} — {type(e).__name__}: {e}")
        print(f"  ✗ {ten}  << {type(e).__name__}: {e}")

# Trong hộp Dây chuyền còn các nút con: bấm HẾT (trừ ▶ Chạy — đã có test riêng)
print("\n══ SMOKE: bấm mọi nút trong hộp Dây chuyền ══")
try:
    pg._pipeline_dialog()
    from PyQt6.QtWidgets import QPushButton
    nut = pg._pipe_dlg.findChildren(QPushButton)
    for b in nut:
        t = b.text()
        if "Chạy dây chuyền" in t:
            continue                 # có _test_pipe_overlap.py lo
        try:
            b.click()
            qapp.processEvents()
            print(f"  ✓ nút '{t}'")
        except Exception as e:  # noqa: BLE001
            FAIL.append(f"nút '{t}' — {type(e).__name__}: {e}")
            print(f"  ✗ nút '{t}'  << {type(e).__name__}: {e}")
except Exception as e:  # noqa: BLE001
    FAIL.append(f"mở hộp Dây chuyền để bấm nút — {type(e).__name__}: {e}")
    print(f"  ✗ không mở được hộp Dây chuyền: {e}")

for k, v in _saved.items():
    if v is None:
        st_q.remove(k)
    else:
        st_q.setValue(k, v)
st_q.sync()
print("\n" + "=" * 62)
# ═══ GỌN HOÁ hàng nút (v2.6.19, anh Hùng 31/07 "nhiều phần thừa quá") ═══
# BẤT BIẾN: gom nút vào menu KHÔNG được làm mất chức năng nào.
print("\n══ GỌN HOÁ: 3 menu gom phải mở được + đủ mục ══")
from PyQt6.QtWidgets import QMenu as _QMenu, QPushButton as _QPB
_neo = _QPB(pg)


def _muc_menu(fn):
    """Mở menu bằng fn(anchor) nhưng CHẶN exec (modal) -> đọc danh sách mục."""
    ra = []
    _goc = _QMenu.exec

    def _fake(self, *a, **k):
        ra.extend([a.text() for a in self.actions() if a.text()])
        return None
    _QMenu.exec = _fake
    try:
        fn(_neo)
    finally:
        _QMenu.exec = _goc
    return ra


for _ten, _fn, _can in (
        ("🗑 Kho video & dọn dẹp", pg._pipe_menu_kho, ["Thùng rác", "Dọn file rác"]),
        ("🔧 Sửa & làm lại", pg._pipe_menu_fix,
         ["Cứu video kẹt", "Cắt cơ bản", "Làm lại cả nhóm"]),
        ("⋮ thêm", pg._pipe_menu_more, ["kênh đã ẩn"])):
    _m = _muc_menu(_fn)
    _thieu = [c for c in _can if not any(c.lower() in x.lower() for x in _m)]
    if _thieu:
        FAIL.append(f"menu '{_ten}' THIẾU mục {_thieu} — chỉ có {_m}")
        print(f"  ✗ menu '{_ten}' thiếu {_thieu}")
    else:
        print(f"  ✓ menu '{_ten}' đủ mục ({len(_m)} mục)")

if FAIL:
    print(f"❌ {len(FAIL)} LỖI:")
    for f in FAIL:
        print("   -", f)
else:
    print("✅ MỌI HỘP THOẠI + NÚT MỞ ĐƯỢC, KHÔNG LỖI")
print("=" * 62)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
