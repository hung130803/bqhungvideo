# -*- coding: utf-8 -*-
"""Render QueuePanel offscreen voi DB gia -> PNG o nhieu be ngang. (artifact test, se xoa)"""
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
TMP = tempfile.mkdtemp(prefix="qp_test_")
os.environ["BQ_DB_PATH"] = os.path.join(TMP, "test.db")
sys.path.insert(0, r"D:\claude\ai-content-studio")

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from app.ui.theme import apply_theme  # noqa: E402
apply_theme(app)

from app.database.db import db  # noqa: E402
assert db.path == os.environ["BQ_DB_PATH"], f"DB path sai: {db.path}"

pid1 = db.insert("INSERT INTO projects(name, assets_dir) VALUES(?,?)",
                 ("Kênh Gaming", TMP))
pid2 = db.insert("INSERT INTO projects(name, assets_dir) VALUES(?,?)",
                 ("Kênh Phim Hài", TMP))
vid1 = db.insert("INSERT INTO videos(project_id, src_path) VALUES(?,?)",
                 (pid1, r"C:\vid\Trận chung kết nghẹt thở.mp4"))
LONG = ("Tập 12 - Anh chàng nhà quê lên thành phố lập nghiệp gặp chuyện "
        "dở khóc dở cười không thể tin nổi phần hai.mp4")
vid2 = db.insert("INSERT INTO videos(project_id, src_path) VALUES(?,?)",
                 (pid2, r"C:\vid\{}".format(LONG)))


def add(t, pid, vid, status, prog, msg=None, err=None, payload=None):
    return db.insert(
        "INSERT INTO jobs(type,project_id,video_id,payload,status,progress,"
        "message,error) VALUES(?,?,?,?,?,?,?,?)",
        (t, pid, vid, json.dumps(payload or {}), status, prog, msg, err))


j_run1 = add("analyze", pid1, vid1, "running", 0.45,
             "Đang tách âm thanh và nhận dạng lời thoại (bước 2/5)...")
j_run2 = add("m1_export_clip", pid2, vid2, "running", 0.80,
             "Đang render đoạn 2/3", payload={"part_no": 3})
j_pend = add("m1_export_clip", pid2, vid2, "pending", 0, payload={"part_no": 4})
add("analyze", pid1, vid1, "pending", 0)
add("m1_export_clip", pid1, vid1, "done", 1, payload={"part_no": 1})
add("analyze", pid2, vid2, "failed", 0.3, "Đang gọi AI chấm điểm",
    "OpenAI API key không hợp lệ (401 Unauthorized)")
add("m1_export_clip", pid2, vid2, "canceled", 0.1, "Đã hủy",
    payload={"part_no": 2})
add("m1_highlights", pid1, vid1, "done", 1)


class _FakePool:
    """Pool gia: cancel/retry cap nhat DB nhu WorkerPool that (khong thread)."""
    def cancel(self, job_id):
        db.execute("UPDATE jobs SET status='canceled', message='Đã hủy' "
                   "WHERE id=? AND status='pending'", (job_id,))
        db.execute("UPDATE jobs SET message='Đang hủy...' "
                   "WHERE id=? AND status='running'", (job_id,))

    def cancel_all(self):
        db.execute("UPDATE jobs SET status='canceled', message='Đã hủy' "
                   "WHERE status='pending'")

    def retry(self, job_id):
        db.execute("UPDATE jobs SET status='pending', attempts=0, error=NULL,"
                   " progress=0, message='Đưa lại hàng đợi' "
                   "WHERE id=? AND status IN ('failed','canceled')", (job_id,))


class _FakeState:
    pool = _FakePool()


from app.ui.queue_panel import QueuePanel  # noqa: E402

qp = QueuePanel(_FakeState())
qp.timer.stop()                      # dieu khien refresh bang tay
OUT = r"D:\claude\ai-content-studio"
for wpx in (360, 700, 1200):
    qp.resize(wpx, 340)
    qp.refresh()
    app.processEvents()
    qp.grab().save(os.path.join(OUT, f"_qp_{wpx}.png"))
    print(f"saved _qp_{wpx}.png")

# ---- test 1: poll khi DB doi status -> khong crash ----
db.execute("UPDATE jobs SET status='done', progress=1 WHERE id=?", (j_run1,))
db.execute("UPDATE jobs SET progress=0.92, message='Đang ghép nhạc nền' "
           "WHERE id=?", (j_run2,))
qp.refresh(); app.processEvents()
qp.refresh(); app.processEvents()
print("poll after status change: OK")

# ---- test 2: huy 1 job pending qua nut ----
row = qp._rows.get(j_pend)
assert row is not None, "khong co row pending"
row["btn"].click()
app.processEvents()
st = db.query_one("SELECT status FROM jobs WHERE id=?", (j_pend,))["status"]
assert st == "canceled", f"cancel khong an: {st}"
qp.refresh(); app.processEvents()
print("cancel via button: OK (status=canceled)")

# ---- render sau thay doi (kiem tra rebuild khong vo) ----
qp.resize(700, 340)
qp.refresh(); app.processEvents()
qp.grab().save(os.path.join(OUT, "_qp_700_after.png"))
print("saved _qp_700_after.png")
print("ALL OK")
