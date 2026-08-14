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
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry thật
os.environ["WHISPER_PROVIDER"] = "groq"          # chép lời nhanh bằng key sống
# LỖI CỦA BỘ TEST (bắt được 05/08/2026): key Groq nằm trong `<DATA_DIR>\.env`
# (config.py:46 `load_dotenv(DATA_DIR / ".env")`), mà test lại trỏ BQ_DATA_DIR
# vào thư mục TẠM -> sandbox có 0 key -> transcribe() lùi về whisper MÁY ->
# tải model faster-whisper large-v3 ~3 GB vào sandbox rỗng -> job 'transcript'
# chạy quá 420s -> cổng báo FAIL oan (đo: job kẹt 'running', thư mục
# models--Systran--faster-whisper-large-v3 vừa được tạo). Nay CHUYỀN key qua
# BIẾN MÔI TRƯỜNG của tiến trình test (không ghi ra file nào — đúng luật key).
# IN ĐƯỢC TIẾNG VIỆT KỂ CẢ KHI stdout BỊ CHUYỂN HƯỚNG RA FILE. Cổng này CÓ
# `import _test_guard` (guard đã reconfigure utf-8) nhưng nó `print` từ dòng 29
# — TRƯỚC lời import đó — nên vẫn chết cp1252 khi chạy hồi quy hàng loạt.
# Quét tĩnh "có import _test_guard không" KHÔNG bắt được ca này: phải hỏi
# "reconfigure có chạy TRƯỚC print ĐẦU TIÊN không".
import sys as _sys_utf8
for _f in (_sys_utf8.stdout, _sys_utf8.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

_env_that = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo" / ".env"
if _env_that.exists():
    for _ln in _env_that.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)
print("key Groq cho sandbox:",
      len([x for x in os.environ.get("GROQ_API_KEYS", "").replace(",", "\n")
           .splitlines() if x.strip()]), "(0 = sẽ tụt về whisper máy, RẤT CHẬM)")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

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

# file HỎNG để test quarantine (-> _Loi)
bad = chdir / "hong.mp4"
bad.write_bytes(b"RAC" * 5000)
os.utime(bad, (old_t - 60, old_t - 60))         # mtime cũ hơn -> bị nhặt TRƯỚC
# BỎ ca "quá hạn mức": UI đã BỎ HẲN cột "video/ngày", plan_channel giờ cắt HẾT
# video sẵn sàng trong thư mục (xem chú thích trong plan_channel). Giữ ca cũ là
# test đòi một hành vi mà sản phẩm đã cố ý loại bỏ.

# ---- 2. app offscreen + kênh dây chuyền ----
# đăng ký handler TRƯỚC khi đụng Qt (main.py thật cùng thứ tự — cv2 trong
# m1_highlight phải nạp trước QApplication kẻo xung đột plugin Qt)
import app.queue.jobs  # noqa: F401

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from app.ui.appsettings import app_settings

app = QApplication(sys.argv)
st_q = app_settings()
_saved = {k: st_q.value(k) for k in ("pipe_root", "chan_group",
                                     "chan_groups_extra", "pipe_grp_sel")}
st_q.setValue("pipe_root", str(root))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")
# CHỐT nhóm để chạy + SYNC: QSettings là registry DÙNG CHUNG với app thật, và
# instance khác (self._settings trong StudioPage) KHÔNG thấy giá trị vừa ghi nếu
# chưa sync. Trước đây test ăn may giá trị 'pipe_grp_sel' còn sót lại nên có
# lần chạy sai nhóm ("Mỹ mới 1") rồi FAIL oan.
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()

from app.database.db import db

# MÔ HÌNH 1 THƯ MỤC (đúng cách anh Hùng dùng, xem plan_channel): thư mục kênh
# vừa là NGUỒN vừa là chỗ xuất Part. Trước đây test khai export_dir sang chỗ
# khác nên app đi tìm video ở đó -> "thư mục trống" -> FAIL oan.
out_dir = chdir
pid = db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_src, pipe_on, "
    "pipe_mode, pipe_daily) VALUES('Kênh Test', ?, 'Mỹ', ?, ?, 1, 'auto', 0)",
    (str(T / "assets"), str(out_dir), str(chdir))).lastrowid

# KIỂU PHỤ ĐỀ cho kênh: đặt BQ_E2E_PRESET="Ô sáng chạy từ (đa màu)" để chạy
# đúng cảnh sản xuất với mẫu-theo-kênh (mặc định: mẫu chung như trước).
_pre = os.environ.get("BQ_E2E_PRESET", "").strip()
if _pre:
    from app import services as _sv
    _sv.save_template("mau e2e", {"cap_on": True, "cap_preset": _pre,
                                  "cap_ny": 0.70, "cap_size": 0.052})
    _sv.set_project_template(pid, "mau e2e")
    print(f"mau cua kenh: 'mau e2e' -> kieu phu de '{_pre}'")

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
parts = sorted(out_dir.glob("Part *.mp4"))   # Part xuất thẳng vào thư mục kênh
print(f"part xuat ra: {len(parts)} -> {[p.name for p in parts][:5]}")
print("goc da xoa:", not src.exists())
print("hong vao _Loi:", (root / "_Loi" / "Kênh Test" / "hong.mp4").exists())
rep = "\n".join(pg._pipe_report)
print("--- bao cao ---")
print(rep)

ok = (final and final["status"] == "done" and len(parts) >= 1
      and not src.exists()
      and (root / "_Loi" / "Kênh Test" / "hong.mp4").exists())
print("TONG:", "PASS" if ok else "FAIL")

for k, v in _saved.items():
    if v is None:
        st_q.remove(k)
    else:
        st_q.setValue(k, v)
st_q.sync()
