# E2E dây chuyền B2 (sandbox): nhận file -> cắt -> xuất Part -> XÓA GỐC.
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="pipe_e2e_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["WHISPER_PROVIDER"] = "groq"          # chép lời nhanh bằng key sống
sys.path.insert(0, r"D:\claude\ai-content-studio")

# ---- 1. dựng video CÓ LỜI NÓI THẬT (edge-tts) ~100s ----
import asyncio

import edge_tts

TEXT = ("Welcome back everyone. Today we are testing the most amazing "
        "automated pipeline ever built. First we download the video, then "
        "the artificial intelligence analyzes every single moment to find "
        "the highlights. After that it cuts the best parts automatically. "
        "The results are exported directly to the channel folder. "
        "And finally the original file is deleted safely. "
        "This is the future of content creation my friends. "
        "Nobody has to do this work manually ever again. "
        "Let me show you how incredible this system really is. "
        "Stay tuned because the best part is coming right now.") * 2
wav = T / "speech.mp3"
asyncio.run(edge_tts.Communicate(TEXT, "en-US-GuyNeural").save(str(wav)))

root = T / "daychuyen"
chdir = root / "Kênh Test"
chdir.mkdir(parents=True)
src = chdir / "video_nguon.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                "-i", "testsrc2=size=1280x720:rate=30",
                "-i", str(wav), "-shortest",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", str(src)], check=True, capture_output=True)
old_t = time.time() - 120
os.utime(src, (old_t, old_t))
dur = float(subprocess.run(
    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
     "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout)
print(f"video nguon: {dur:.0f}s co loi noi that")

# file HỎNG để test quarantine + file tốt thứ 2 để test hạn mức
bad = chdir / "hong.mp4"
bad.write_bytes(b"RAC" * 5000)
os.utime(bad, (old_t - 60, old_t - 60))         # mtime cũ hơn -> bị nhặt TRƯỚC
extra = chdir / "du_han_muc.mp4"
import shutil
shutil.copy(src, extra)
os.utime(extra, (old_t + 30, old_t + 30))

# ---- 2. app offscreen + kênh dây chuyền ----
# đăng ký handler TRƯỚC khi đụng Qt (main.py thật cùng thứ tự — cv2 trong
# m1_highlight phải nạp trước QApplication kẻo xung đột plugin Qt)
import app.queue.jobs  # noqa: F401

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

out_dir = T / "xuat" / "Kênh Test"
out_dir.mkdir(parents=True)
pid = db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, "
    "pipe_mode, pipe_daily) VALUES('Kênh Test', ?, 'Mỹ', ?, 1, 'auto', 1)",
    (str(T / "assets"), str(out_dir))).lastrowid

from app.ui.state import AppState
from app.ui.studio_page import StudioPage

state = AppState()
state.start()
pg = StudioPage(state)

# ---- 3. CHẠY dây chuyền ----
n = pg._pipe_run()
print(f"nhan {n} video (mong doi 1: file tot; hong->_Loi; du->skip han muc)")

# ---- 4. đợi tới khi sổ chốt done/error (tối đa 8 phút) ----
deadline = time.time() + 420
final = None
while time.time() < deadline:
    app.processEvents()
    pg._check_auto_export()
    pg._pipe_poll()
    r = db.query_one(
        "SELECT status, note FROM pipeline_files WHERE project_id=? "
        "AND file_name='video_nguon.mp4' ORDER BY id DESC LIMIT 1", (pid,))
    if r and r["status"] in ("done", "error"):
        final = dict(r)
        break
    time.sleep(1.0)
state.stop()

print("=== JOBS ===")
for j in db.query("SELECT id,type,status,progress,message,error FROM jobs ORDER BY id"):
    print(f"#{j['id']} {j['type']:12s} {j['status']:8s} {j['progress']:.2f} "
          f"{(j['message'] or '')[:60]} | {(j['error'] or '')[:160]}")
print("=== SO ===")
for r in db.query("SELECT file_name,status,note FROM pipeline_files"):
    print(dict(r))
print("sandbox:", T)
print("so cai:", final)
parts = sorted(out_dir.glob("*.mp4"))
print(f"part xuat ra: {len(parts)} -> {[p.name for p in parts][:5]}")
print("goc da xoa:", not src.exists())
print("hong vao _Loi:", (root / "_Loi" / "Kênh Test" / "hong.mp4").exists())
print("du_han_muc con nguyen (cho ngay mai):", extra.exists())
rep = "\n".join(pg._pipe_report)
print("--- bao cao ---")
print(rep)

ok = (final and final["status"] == "done" and len(parts) >= 1
      and not src.exists()
      and (root / "_Loi" / "Kênh Test" / "hong.mp4").exists()
      and extra.exists())
print("TONG:", "PASS" if ok else "FAIL")

for k, v in _saved.items():
    if v is None:
        st_q.remove(k)
    else:
        st_q.setValue(k, v)
st_q.sync()
