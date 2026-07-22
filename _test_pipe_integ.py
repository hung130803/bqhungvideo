# TÍCH HỢP THẬT: video do CHÍNH yt-dlp của prodown tải từ YouTube về
# (Big Buck Bunny 10 phút — file container/timing thật) -> dây chuyền ăn:
# nhận -> phân tích -> cắt -> xuất Part -> XÓA GỐC.
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

SRC_REAL = Path(r"C:\Users\Admin\AppData\Local\Temp\pipe_integ"
                r"\Kênh Integ\video_that.mp4")
T = Path(tempfile.mkdtemp(prefix="pipe_integ_run_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["WHISPER_PROVIDER"] = "groq"
sys.path.insert(0, r"D:\claude\ai-content-studio")

root = T / "daychuyen"
chdir = root / "Kênh Integ"
chdir.mkdir(parents=True)
src = chdir / "video_that.mp4"
shutil.copy(SRC_REAL, src)
old_t = time.time() - 120
os.utime(src, (old_t, old_t))

import app.queue.jobs  # noqa: F401 - handler + cv2 TRƯỚC Qt (thứ tự main.py)

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
st_q = QSettings("AIContentStudio", "studio")
_saved = {k: st_q.value(k) for k in ("pipe_root", "chan_group",
                                     "chan_groups_extra")}
st_q.setValue("pipe_root", str(root))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")

from app.database.db import db

out_dir = T / "xuat"
out_dir.mkdir(parents=True)
pid = db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, "
    "pipe_mode, pipe_daily) VALUES('Kênh Integ', ?, 'Mỹ', ?, 1, 'auto', 1)",
    (str(T / "assets"), str(out_dir))).lastrowid

from app.ui.state import AppState
from app.ui.studio_page import StudioPage

state = AppState()
state.start()
pg = StudioPage(state)

n = pg._pipe_run()
print(f"nhan {n} video (video YouTube THAT 10 phut)")

deadline = time.time() + 540
final = None
while time.time() < deadline:
    app.processEvents()
    pg._check_auto_export()
    pg._pipe_poll()
    r = db.query_one(
        "SELECT status, note FROM pipeline_files WHERE project_id=? "
        "ORDER BY id DESC LIMIT 1", (pid,))
    if r and r["status"] in ("done", "error"):
        final = dict(r)
        break
    time.sleep(1.0)
state.stop()

print("so cai:", final)
parts = sorted(out_dir.glob("*.mp4"))
print(f"part xuat: {len(parts)} -> {[p.name[:70] for p in parts]}")
print("goc da xoa:", not src.exists())
print("--- bao cao ---")
print("\n".join(pg._pipe_report))
ok = (final and final["status"] == "done" and len(parts) >= 1
      and not src.exists())
print("TONG:", "PASS" if ok else "FAIL")
for k, v in _saved.items():
    if v is None:
        st_q.remove(k)
    else:
        st_q.setValue(k, v)
st_q.sync()
