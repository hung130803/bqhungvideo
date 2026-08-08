# TÍCH HỢP THẬT: video do CHÍNH yt-dlp của prodown tải từ YouTube về
# (Big Buck Bunny 10 phút — file container/timing thật) -> dây chuyền ăn:
# nhận -> phân tích -> cắt -> xuất Part -> XÓA GỐC.
#
# 08/08/2026 — ĐỪNG ĐỂ FAIL TRƠ. Bản cũ `shutil.copy(SRC_REAL, ...)` nổ
# `FileNotFoundError` trên MỌI máy không có sẵn file đặt tay ở `%TEMP%`, nên ai
# chạy cũng tưởng dây chuyền hỏng thật. Nay có 3 đường lấy nguồn, luôn IN RA
# đường nào được dùng (xem `_tim_nguon`).
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
SRC_REAL = Path(r"C:\Users\Admin\AppData\Local\Temp\pipe_integ"
                r"\Kênh Integ\video_that.mp4")
#: kho video THẬT trên máy anh Hùng — quy tắc sắt của repo là test bằng THÀNH
#: PHẦN THẬT, nên video tự sinh `lavfi` chỉ là đường lùi CUỐI CÙNG.
KHO_THAT = (
    Path(r"D:\video ssmatool\video nhật dài"),    # có file 1-10 phút, cỡ vừa
    Path(r"D:\video ssmatool\video mỹ"),          # đúng nhóm 'Mỹ' của test
    Path(r"C:\Users\Admin\Downloads\thùng rác"),
)
_NOWIN = 0x08000000 if os.name == "nt" else 0


def _do_dai(p: Path) -> float:
    """Độ dài video (giây); không đọc được -> 0."""
    ff = REPO / "bin" / "ffprobe.exe"
    try:
        r = subprocess.run(
            [str(ff) if ff.exists() else "ffprobe", "-v", "quiet",
             "-print_format", "json", "-show_format", str(p)],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
            creationflags=_NOWIN)
        return float(json.loads(r.stdout or "{}").get(
            "format", {}).get("duration") or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def _sinh_lavfi(dich: Path, giay: float = 120.0) -> None:
    """Đường lùi CUỐI: tự sinh nguồn bằng `lavfi` (y cổng 37) — không phụ thuộc
    file trên máy. Nhược điểm: không có LỜI NÓI thật nên dây chuyền sẽ đi nhánh
    'video không lời' (XEM HÌNH), vẫn là đường hợp lệ."""
    ff = REPO / "bin" / "ffmpeg.exe"
    subprocess.run(
        [str(ff) if ff.exists() else "ffmpeg", "-y", "-hide_banner",
         "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=s=1280x720:r=30:d={giay:g}",
         "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={giay:g}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest",
         str(dich)],
        capture_output=True, timeout=600, creationflags=_NOWIN)


def _tim_nguon(dich: Path) -> str:
    """Đặt 1 video nguồn vào `dich`. Trả về MÔ TẢ nguồn đã dùng (để in ra)."""
    if SRC_REAL.exists():
        shutil.copy(SRC_REAL, dich)
        return f"file đặt tay: {SRC_REAL}"
    for thu in KHO_THAT:
        if not thu.is_dir():
            continue
        thu_ung = []
        for p in thu.rglob("*.mp4"):
            try:
                mb = p.stat().st_size / (1024 * 1024)
            except OSError:
                continue
            if 20 <= mb <= 600:             # đủ dài để có Part, đủ nhẹ để copy
                thu_ung.append((-mb, p))
        thu_ung.sort()                      # to trước = dài trước
        for _m, p in thu_ung[:60]:          # chặn trần: đừng ffprobe cả nghìn file
            # PHẢI ĐỦ DÀI: bản gốc của test dùng video YouTube 10 PHÚT. Video
            # dưới ~4 phút không đủ chỗ cho 3 Part >= 60s -> dây chuyền chạy
            # xong mà "không có Part nào được xuất" (đã đo: nguồn 88,8s ra 0 Part).
            # Trần 700s: bước PHÂN TÍCH (cảnh + mặt + chép lời) tỉ lệ thuận với
            # độ dài; nguồn 1.062s đo thật ăn hết hạn 540s mà chưa xong.
            if not (240 <= _do_dai(p) <= 700):
                continue
            shutil.copy(p, dich)
            return f"video THẬT trên máy: {p}"
    _sinh_lavfi(dich)
    return ("TỰ SINH bằng lavfi (không tìm thấy video thật) — nhánh 'không lời'")
T = Path(tempfile.mkdtemp(prefix="pipe_integ_run_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry thật
os.environ["WHISPER_PROVIDER"] = "groq"
# KEY GROQ PHẢI CHUYỀN VÀO SANDBOX — bài học cổng 22, và cổng này đang dính:
# `config.py` nạp `.env` từ `DATA_DIR`, mà `BQ_DATA_DIR` trỏ vào thư mục TẠM ->
# sandbox 0 key -> `transcribe()` lùi về whisper MÁY và `llm.is_configured()`
# False -> AI chọn đoạn KHÔNG chạy -> **0 clip -> 0 Part** rồi báo "không có
# Part nào được xuất". Đo thật 08/08/2026: cột `analysis.engine` ghi
# `stable-ts:large-v3` (không phải `groq:...`) — đúng dấu vết của lỗi này.
# Đọc `.env` THẬT rồi chuyền qua BIẾN MÔI TRƯỜNG, KHÔNG ghi ra file nào.
_env_that = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
             / "BQHungVideo" / ".env")
if _env_that.exists():
    for _ln in _env_that.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)
sys.path.insert(0, r"D:\claude\ai-content-studio")
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

root = T / "daychuyen"
chdir = root / "Kênh Integ"
chdir.mkdir(parents=True)
src = chdir / "video_that.mp4"
_nk = len([x for x in os.environ.get("GROQ_API_KEYS", "").replace(",", "\n")
           .splitlines() if x.strip()])
print(f"[key Groq] {_nk} key (0 = tụt whisper MÁY, AI chọn đoạn KHÔNG chạy)")
print("[nguồn]", _tim_nguon(src))
if not src.exists() or src.stat().st_size == 0:
    print("BO QUA: khong dung duoc video nguon nao (khong co file dat tay, "
          "khong co kho video that, lavfi cung hong). KHONG PHAI LOI APP.")
    raise SystemExit(0)
print(f"[nguồn] {src.stat().st_size / 1048576:.1f} MB · "
      f"{_do_dai(src):.1f}s")
old_t = time.time() - 120
os.utime(src, (old_t, old_t))

import app.queue.jobs  # noqa: F401 - handler + cv2 TRƯỚC Qt (thứ tự main.py)

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from app.ui.appsettings import app_settings

app = QApplication(sys.argv)
st_q = app_settings()
_saved = {k: st_q.value(k) for k in ("pipe_root", "chan_group",
                                     "chan_groups_extra")}
st_q.setValue("pipe_root", str(root))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")

from app.database.db import db

out_dir = T / "xuat"
out_dir.mkdir(parents=True)
# pipe_src PHẢI đặt rõ: `pipeline.plan_channel` coi `export_dir` là NGUỒN khi
# không có pipe_src (mô hình "1 thư mục dùng chung"), nên để trống là dây
# chuyền đi quét thư mục XUẤT (rỗng) rồi báo "không có video mới để cắt".
pid = db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_src, "
    "pipe_on, pipe_mode, pipe_daily) "
    "VALUES('Kênh Integ', ?, 'Mỹ', ?, ?, 1, 'auto', 1)",
    (str(T / "assets"), str(out_dir), str(chdir))).lastrowid

from app.ui.state import AppState
from app.ui.studio_page import StudioPage

state = AppState()
state.start()
pg = StudioPage(state)

n = pg._pipe_run()
print(f"nhan {n} video (video YouTube THAT 10 phut)")

deadline = time.time() + 900   # 540s không đủ cho video thật ~10 phút
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
# ĐỪNG BÁO "FAIL" TRƠ: in luôn BẰNG CHỨNG để biết hỏng ở ĐÂU (bước phân tích /
# chọn đoạn / xuất). Trước đây chỉ có 1 dòng "không có Part nào được xuất".
print("--- bang chung ---")
for r in db.query("SELECT kind, status, engine, substr(error,1,160) AS e "
                  "FROM analysis WHERE video_id IN "
                  "(SELECT id FROM videos WHERE project_id=?)", (pid,)):
    print(f"  analysis {r['kind']:12s} {r['status']:8s} {r['engine'] or '-'} "
          f"{r['e'] or ''}")
for r in db.query("SELECT type, status, attempts, substr(error,1,200) AS e "
                  "FROM jobs ORDER BY id"):
    print(f"  job {r['type']:16s} {r['status']:8s} thu {r['attempts']} "
          f"{r['e'] or ''}")
for r in db.query("SELECT id, start_sec, end_sec, status, substr(signals,1,90) "
                  "AS s FROM clips ORDER BY id"):
    print(f"  clip {r['id']} {r['start_sec']:.0f}-{r['end_sec']:.0f}s "
          f"{r['status']} {r['s']}")
_lg = T / "logs"
if _lg.is_dir():
    for f in sorted(_lg.glob("*.log")):
        d = f.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"  --- {f.name} ({len(d)} dòng, 12 dòng cuối) ---")
        for ln in d[-12:]:
            print("   ", ln[:170])
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
