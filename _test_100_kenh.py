# ĐO QUY MÔ 100 KÊNH: anh Hùng hỏi "chạy ví dụ 100 kênh có sao không".
# Đo bằng số, không đoán: thời gian bấm ▶ Chạy (chạy trên LUỒNG GIAO DIỆN nên
# lâu là app đứng), thời gian dựng bảng 100 dòng, thời gian nhận hết 100 video,
# và giữ bất biến vàng "số dòng sổ 'taken' = số ctx đang dõi".
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="k100_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = Path(__file__).resolve().parent / "bin" / "ffmpeg.exe"
N_KENH = int(os.environ.get("N_KENH", "100"))
STABLE = 90

import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtWidgets import QApplication  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402

qapp = QApplication(sys.argv)
st_q = app_settings()

from app.core import pipeline as P  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL: list[str] = []


def kiem(dk: bool, nhan: str, ct: str = "") -> None:
    print(f"  {'✓' if dk else '✗'} {nhan}" + ("" if dk else f"  << {ct}"))
    if not dk:
        FAIL.append(f"{nhan} — {ct}")


print(f"\n══ Dựng {N_KENH} kênh, mỗi kênh 1 video thật ══")
t0 = time.perf_counter()
for i in range(N_KENH):
    ten = f"kênh {i:03d}"
    src = T / "nguon" / ten
    src.mkdir(parents=True)
    p = src / f"v{i}.mp4"
    subprocess.run(
        [str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
         "testsrc=size=320x240:rate=15:duration=1", "-f", "lavfi", "-i",
         f"sine=frequency={300 + i}:duration=1", "-c:v", "libx264",
         "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(p)], check=True)
    old = time.time() - STABLE
    os.utime(p, (old, old))
    db.execute(
        "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_src, "
        "pipe_on, pipe_mode, pipe_daily) VALUES(?,?,'Mỹ',?,?,1,'auto',0)",
        (ten, str(T / "assets" / ten), str(src), str(src)))
print(f"   xong trong {time.perf_counter() - t0:.1f}s")

st_q.setValue("pipe_root", str(T / "nguon"))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.setValue("pipe_recycle_dir", str(T / "thungrac"))
st_q.sync()

state = AppState()
pg = StudioPage(state)
pg._pipe_report = []
# pool KHÔNG start -> job đứng 'pending', đo riêng phần điều phối/UI

print(f"\n══ 1. Bấm ▶ Chạy dây chuyền ({N_KENH} kênh) ══")
print("   (hàm này chạy trên LUỒNG GIAO DIỆN — lâu quá là app đứng)")
t0 = time.perf_counter()
pg._pipe_run()
t_run = time.perf_counter() - t0
cho = len(getattr(pg, "_pipe_intake_q", []) or [])
print(f"   _pipe_run: {t_run * 1000:.0f} ms — xếp {cho} video vào hàng đợi")
kiem(t_run < 10.0, f"bấm ▶ Chạy không treo giao diện quá 10s ({N_KENH} kênh)",
     f"mất {t_run:.1f}s — user tưởng app treo")
# _pipe_run gọi _pipe_intake_step() ở cuối nên NHẬN NGAY 1 video trước khi ta
# đếm -> hàng đợi còn N-1. Không phải thiếu video (mục 2 kiểm nhận đủ N).
kiem(cho >= N_KENH - 1, f"xếp đủ {N_KENH} video vào hàng đợi",
     f"chỉ xếp {cho}")

print(f"\n══ 2. Nhận hết {N_KENH} video (từng cái qua QTimer) ══")
t0 = time.perf_counter()
lau_nhat = 0.0
for _ in range(N_KENH * 3):
    if not (getattr(pg, "_pipe_intake_q", None) or []):
        break
    t1 = time.perf_counter()
    qapp.processEvents()
    time.sleep(0.005)
    qapp.processEvents()
    lau_nhat = max(lau_nhat, time.perf_counter() - t1)
t_nhan = time.perf_counter() - t0
taken = db.query("SELECT COUNT(*) n FROM pipeline_files "
                 "WHERE status='taken'")[0]["n"]
jobs = db.query("SELECT COUNT(*) n FROM jobs")[0]["n"]
ctx = len({c["entry"] for c in pg._pipe_cut.values()}
          | {c["entry"] for c in pg._pipe_by_vid.values()})
print(f"   nhận {taken} video trong {t_nhan:.1f}s "
      f"({t_nhan / max(1, taken) * 1000:.0f} ms/video) · "
      f"nhịp lâu nhất {lau_nhat * 1000:.0f} ms")
print(f"   job tạo ra: {jobs} · ctx đang dõi: {ctx}")
kiem(taken == N_KENH, f"nhận đủ {N_KENH} video", f"chỉ nhận {taken}")
kiem(taken == ctx, "bất biến vàng: số dòng 'taken' = số ctx đang dõi",
     f"taken={taken} nhưng dõi {ctx} ctx")
kiem(lau_nhat < 1.0, "không nhịp nào chiếm giao diện quá 1s",
     f"nhịp lâu nhất {lau_nhat * 1000:.0f} ms")

print(f"\n══ 3. Điều phối job khi có {jobs} job chờ ══")
from config import settings  # noqa: E402

settings.ECO_MODE = False
# giả lập: 1 video đã phân tích xong -> phải có job XUẤT chạy được ngay
jid0 = list(pg._pipe_cut)[0]
vid0 = pg._pipe_cut[jid0]["vid"]
db.execute("INSERT INTO clips(video_id,start_sec,end_sec,score,title,status) "
           "VALUES(?,0.0,0.5,0.9,'C','ready')", (vid0,))
db.execute("UPDATE jobs SET status='done', progress=100 WHERE id=?", (jid0,))
t0 = time.perf_counter()
pg._check_auto_export()
t_exp = time.perf_counter() - t0
xuat = db.query("SELECT COUNT(*) n FROM jobs WHERE type='m1_export_clip'"
                )[0]["n"]
print(f"   _check_auto_export: {t_exp * 1000:.0f} ms — tạo {xuat} job xuất")
kiem(xuat >= 1, "video phân tích xong TẠO ĐƯỢC job xuất", "không job xuất nào")

pool = state.pool
pool._dispatch_once()
chay_cpu = sum(1 for g in pool._inflight_gpu.values() if not g)
chay_gpu = sum(1 for g in pool._inflight_gpu.values() if g)
print(f"   điều phối: {chay_gpu} phân tích + {chay_cpu} xuất đang chạy")
kiem(chay_cpu >= 1,
     f"job XUẤT được chạy dù có {jobs - xuat} job phân tích chờ (ngưỡng 50 cũ)",
     "làn cắt vẫn chết đói")

print(f"\n══ 4. Dựng bảng dây chuyền {N_KENH} dòng ══")
from PyQt6.QtWidgets import QDialog  # noqa: E402

QDialog.exec = lambda self: 0
t0 = time.perf_counter()
pg._pipeline_dialog()
qapp.processEvents()
t_dlg = time.perf_counter() - t0
print(f"   mở hộp + dựng bảng: {t_dlg * 1000:.0f} ms")
kiem(t_dlg < 15.0, f"mở hộp Dây chuyền với {N_KENH} kênh dưới 15s",
     f"mất {t_dlg:.1f}s")

print("\n" + "=" * 64)
print(f"TÓM TẮT {N_KENH} KÊNH: ▶Chạy {t_run * 1000:.0f}ms · nhận "
      f"{t_nhan:.1f}s · nhịp lâu nhất {lau_nhat * 1000:.0f}ms · "
      f"mở bảng {t_dlg * 1000:.0f}ms")
if FAIL:
    print(f"❌ {len(FAIL)} LỖI:")
    for f in FAIL:
        print("   -", f)
else:
    print("✅ TẤT CẢ ĐẠT")
print("=" * 64)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
