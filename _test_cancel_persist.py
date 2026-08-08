# -*- coding: utf-8 -*-
# TÁI HIỆN LỖI (anh Hùng 30/07): bấm HUỶ lúc job đang chạy ('Đang hủy...'),
# rồi TẮT APP / CẬP NHẬT -> mở lại -> job đã huỷ TỰ CHẠY LẠI.
#
# 3 đường hồi sinh, test đủ cả 3:
#   1. WorkerPool.stop(): running -> 'pending' (kể cả job đang bị huỷ).
#   2. WorkerPool._recover_crashed(): như trên cho ca crash/kill.
#   3. _pipe_resume_taken(): job huỷ -> "xếp lại job MỚI" + reattach xuất.
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="cancel_persist_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = Path(__file__).resolve().parent / "bin" / "ffmpeg.exe"
STABLE = 70

import app.queue.jobs  # noqa: F401,E402 - handler + cv2 TRƯỚC Qt

from PyQt6.QtWidgets import QApplication  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402

qapp = QApplication(sys.argv)
st_q = app_settings()

from app.core import pipeline as P  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL: list = []


def kiem(ok: bool, nhan: str, chi_tiet: str = "") -> None:
    if ok:
        print(f"  ✓ {nhan}")
    else:
        FAIL.append(nhan)
        print(f"  ✗ {nhan}  << {chi_tiet}")


def job_gia(status: str, cancel_req: int = 0, jtype: str = "auto",
            vid=None) -> int:
    return db.insert(
        "INSERT INTO jobs(type, payload, status, cancel_req, video_id, "
        "attempts, max_attempts) VALUES(?, '{}', ?, ?, ?, 0, 3)",
        (jtype, status, cancel_req, vid))


def st_cua(jid: int) -> tuple:
    r = db.query_one("SELECT status, cancel_req FROM jobs WHERE id=?", (jid,))
    return (r["status"], r["cancel_req"]) if r else (None, None)


# ═════════ PHẦN 1: WorkerPool — ý định huỷ phải BỀN qua restart ═════════
print("\n══ 1. WorkerPool: cancel_req bền vào DB ══")
state = AppState()
pool = state.pool

# 1a. cancel job PENDING -> canceled ngay (hành vi cũ giữ nguyên)
j = job_gia("pending")
pool.cancel(j)
kiem(st_cua(j)[0] == "canceled", "huỷ job pending -> canceled ngay",
     str(st_cua(j)))

# 1b. cancel job RUNNING -> ghi cancel_req=1 (ý định huỷ nằm trong DB)
j = job_gia("running")
pool.cancel(j)
st, cr = st_cua(j)
kiem(st == "running" and cr == 1,
     "huỷ job running -> cancel_req=1 (chờ job tự thoát)", f"{st},{cr}")

# 1c. stop() (tắt app): job 'Đang hủy...' phải CHỐT canceled,
#     job running thường mới được về pending
j_huy = job_gia("running", cancel_req=1)
j_thuong = job_gia("running", cancel_req=0)
pool.stop()
kiem(st_cua(j_huy)[0] == "canceled",
     "tắt app: job ĐANG HUỶ -> canceled (không hồi sinh)", str(st_cua(j_huy)))
kiem(st_cua(j_thuong)[0] == "pending",
     "tắt app: job thường -> pending (chạy tiếp lần sau)",
     str(st_cua(j_thuong)))

# 1d. _recover_crashed (mở app sau crash): y hệt
j_huy2 = job_gia("running", cancel_req=1)
j_thuong2 = job_gia("running", cancel_req=0)
pool._recover_crashed()
kiem(st_cua(j_huy2)[0] == "canceled",
     "khôi phục sau crash: job ĐANG HUỶ -> canceled", str(st_cua(j_huy2)))
kiem(st_cua(j_thuong2)[0] == "pending",
     "khôi phục sau crash: job thường -> pending", str(st_cua(j_thuong2)))

# 1e. Thử lại job đã huỷ -> pending + XOÁ ý định huỷ (không bị huỷ oan lần sau)
pool.retry(j_huy)
st, cr = st_cua(j_huy)
kiem(st == "pending" and cr == 0,
     "Thử lại job huỷ -> pending + cancel_req=0", f"{st},{cr}")


# ═════════ PHẦN 2: dây chuyền — huỷ rồi thì HỒI PHỤC không chạy lại ═════════
print("\n══ 2. Dây chuyền: huỷ + tắt app -> mở lại KHÔNG tự chạy ══")
_SEED = [0]


def lam_video(p: Path) -> None:
    _SEED[0] += 1
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
         "testsrc=size=320x240:rate=15:duration=1", "-f", "lavfi",
         "-i", f"sine=frequency={300 + _SEED[0] * 17}:duration=1",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-metadata", f"comment=seed{_SEED[0]}", "-shortest", str(p)],
        check=True)
    old = time.time() - STABLE
    os.utime(p, (old, old))


def bom_nhip(n: int) -> None:
    for _ in range(n):
        qapp.processEvents()
        time.sleep(0.01)
        qapp.processEvents()


def tat_trang(pg) -> None:
    """Vô hiệu trang CŨ giữa các cảnh test: dừng mọi QTimer (poll/scan) kẻo
    trang cũ vẫn quét thư mục nguồn và nhận file của cảnh sau (nhiễu chéo —
    chính là 3 FAIL lần chạy đầu của test này)."""
    from PyQt6.QtCore import QTimer
    for t in pg.findChildren(QTimer):
        t.stop()
    for s in ("_pipe_cut", "_pipe_by_vid", "_pipe_exports",
              "_pending_export"):
        getattr(pg, s, {}).clear()


def don_canh(*pages) -> None:
    """Dọn giữa các cảnh: DB + file video cũ trên đĩa + trang cũ."""
    for p in pages:
        tat_trang(p)
    db.execute("DELETE FROM pipeline_files")
    db.execute("DELETE FROM jobs")
    db.execute("DELETE FROM videos")
    for f in (T / "nguon" / "KenhA").glob("*.mp4"):
        try:
            f.unlink()
        except OSError:
            pass


db.execute("DELETE FROM pipeline_files")
db.execute("DELETE FROM jobs")
db.execute("DELETE FROM videos")
db.execute("DELETE FROM projects")

src = T / "nguon" / "KenhA"
out = T / "xuat" / "KenhA"
out.mkdir(parents=True, exist_ok=True)
lam_video(src / "video1.mp4")
pid = db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, "
    "pipe_mode, pipe_daily, pipe_src) VALUES('KenhA', ?, 'Mỹ', ?, 1, "
    "'auto', 0, ?)", (str(T / "assets"), str(out), str(src))).lastrowid

st_q.setValue("pipe_root", str(T / "nguon"))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.setValue("pipe_recycle_dir", str(T / "thungrac"))
st_q.sync()

pg = StudioPage(AppState())          # pool KHÔNG start -> job nằm pending
pg._pipe_run()
bom_nhip(30)
row = db.query_one("SELECT id FROM pipeline_files WHERE status='taken'")
jrow = db.query_one("SELECT id FROM jobs WHERE type IN ('auto','auto_recap')")
kiem(bool(row and jrow), "dựng cảnh: 1 video đã nhận + 1 job phân tích",
     f"entry={bool(row)} job={bool(jrow)}")

# 2a. USER BẤM HUỶ (job -> canceled) rồi TẮT APP ngay (poll chưa kịp dọn,
#     sổ RAM chết theo app -> dòng sổ vẫn 'taken')
db.execute("UPDATE jobs SET status='canceled', message='Đã hủy' WHERE id=?",
           (jrow["id"],))
n_job_truoc = db.query_one("SELECT COUNT(*) AS n FROM jobs")["n"]

pg2 = StudioPage(AppState())         # "mở lại app"
noi_lai = pg2._pipe_resume_taken()
n_job_sau = db.query_one("SELECT COUNT(*) AS n FROM jobs")["n"]
con_taken = db.query_one(
    "SELECT COUNT(*) AS n FROM pipeline_files WHERE status='taken'")["n"]
kiem(n_job_sau == n_job_truoc,
     "mở lại app: KHÔNG xếp job mới cho video đã huỷ",
     f"job {n_job_truoc} -> {n_job_sau}")
kiem(noi_lai == 0, "không nối lại ctx nào", f"nối {noi_lai}")
kiem(con_taken == 0, "dòng sổ được trả (hết kẹt 'taken')",
     f"còn {con_taken}")
kiem((src / "video1.mp4").exists(), "video gốc GIỮ NGUYÊN trong thư mục kênh")

# 2b. Phân tích XONG nhưng job XUẤT bị huỷ rồi tắt app -> cũng không tự xuất lại
don_canh(pg, pg2)
lam_video(src / "video2.mp4")
pg3 = StudioPage(AppState())
pg3._pipe_run()
bom_nhip(30)
jrow = db.query_one("SELECT id, video_id FROM jobs "
                    "WHERE type IN ('auto','auto_recap')")
kiem(bool(jrow), "dựng cảnh 2b: video2 đã nhận")
db.execute("UPDATE jobs SET status='done' WHERE id=?", (jrow["id"],))
job_gia("canceled", jtype="m1_export_clip", vid=jrow["video_id"])
n_truoc = db.query_one("SELECT COUNT(*) AS n FROM jobs")["n"]

pg4 = StudioPage(AppState())
noi_lai = pg4._pipe_resume_taken()
n_sau = db.query_one("SELECT COUNT(*) AS n FROM jobs")["n"]
kiem(noi_lai == 0 and n_sau == n_truoc,
     "xuất đã huỷ + tắt app -> mở lại KHÔNG tự xuất lại",
     f"nối {noi_lai}, job {n_truoc}->{n_sau}")

# 2c. ĐỐI CHỨNG: job pending bình thường thì hồi phục PHẢI nối lại (đừng vá
#     quá tay làm hỏng tính năng cứu-việc-dở)
don_canh(pg3, pg4)
lam_video(src / "video3.mp4")
pg5 = StudioPage(AppState())
pg5._pipe_run()
bom_nhip(30)
pg6 = StudioPage(AppState())
noi_lai = pg6._pipe_resume_taken()
kiem(noi_lai == 1, "đối chứng: việc DỞ thật (pending) vẫn được nối lại",
     f"nối {noi_lai}")

# 2d. Poll xử lý huỷ khi app ĐANG SỐNG cũng phải trả dòng sổ
don_canh(pg5, pg6)
lam_video(src / "video4.mp4")
pg7 = StudioPage(AppState())
pg7._pipe_run()
bom_nhip(30)
jrow = db.query_one("SELECT id FROM jobs WHERE type IN ('auto','auto_recap')")
db.execute("UPDATE jobs SET status='canceled' WHERE id=?", (jrow["id"],))
pg7._pipe_poll_cut()
con_taken = db.query_one(
    "SELECT COUNT(*) AS n FROM pipeline_files WHERE status='taken'")["n"]
kiem(con_taken == 0, "poll huỷ (app sống): dòng sổ được trả ngay",
     f"còn {con_taken}")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — huỷ là huỷ, tắt app mở lại không tự chạy")
