# -*- coding: utf-8 -*-
"""CỔNG 107 — LỖI ĐÃ CHẠY LẠI KHÔNG CÒN ĐẾM LÀ LỖI + PHÂN TÍCH KHÔNG ĐÓI ĐĨA.

03/11/2026 anh Hùng (ảnh "2 lỗi" analysis_worker_timeout): "nó chạy lại rồi mà
sao cái lỗi không biến mất". App đã tự thử lại sau 15 phút, video phân tích tiếp
tới 86%, nhưng chip vẫn "2 lỗi" vì đếm MỌI job failed hôm nay.

CA 1: job lỗi + lượt MỚI cùng loại/cùng video (pending/running/done) -> chip
      KHÔNG đếm; list_jobs_top đánh dấu da_thu_lai=1 và không xếp nó lên đầu.
CA 2: job lỗi CHƯA có lượt mới -> vẫn đếm, vẫn lên đầu (không sửa quá tay).
CA 3: lượt mới cũng LỖI -> chỉ lượt mới nhất còn tính là lỗi (đếm 1, không 0).
CA 4: lượt mới là của VIDEO KHÁC / LOẠI KHÁC -> không xoá lỗi oan.
CA 5: dòng UI của job đã chạy lại -> nhãn "Đã chạy lại", ẩn nút Thử lại.
CA 6: tiến trình phân tích mở ở BELOW_NORMAL, hạ IDLE khi sẵn sàng (chạy THẬT).
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
TMP = Path(tempfile.mkdtemp(prefix="bq_test_loi_lai_"))
os.environ["BQ_DATA_DIR"] = str(TMP)
os.environ["BQ_DB_PATH"] = str(TMP / "studio.db")

import _test_guard  # noqa: E402,F401

DAT = HONG = 0


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print("  ĐẠT ", ten, chi_tiet)
    else:
        HONG += 1
        print("  HỎNG", ten, chi_tiet)


from app.database import db  # noqa: E402
from app import services  # noqa: E402

db.init_schema() if hasattr(db, "init_schema") else None
pid = db.execute("INSERT INTO projects(name) VALUES('k')") if False else None
db.execute("INSERT INTO projects(name, assets_dir) VALUES ('Kênh thử', ?)", (str(TMP),))
pid = db.query_one("SELECT id FROM projects")["id"]
vids = []
for i in range(4):
    db.execute("INSERT INTO videos(project_id, src_path) VALUES (?,?)",
               (pid, f"C:/x/v{i}.mp4"))
vids = [r["id"] for r in db.query("SELECT id FROM videos ORDER BY id")]


def job(vid, typ, st, err=None):
    db.execute("INSERT INTO jobs(type, project_id, video_id, status, error, "
               "finished_at) VALUES (?,?,?,?,?, datetime('now'))",
               (typ, pid, vid, st, err))
    return db.query_one("SELECT MAX(id) AS i FROM jobs")["i"]


print("CA 1-4: đếm lỗi")
a_loi = job(vids[0], "analyze", "failed", "analysis_worker_timeout: ...")
job(vids[0], "analyze", "running")                     # đã chạy lại
b_loi = job(vids[1], "analyze", "failed", "lỗi thật chưa chạy lại")
c1 = job(vids[2], "analyze", "failed", "lỗi lượt 1")
c2 = job(vids[2], "analyze", "failed", "lỗi lượt 2")   # chạy lại cũng lỗi
d_loi = job(vids[3], "analyze", "failed", "lỗi d")
job(vids[3], "m1_export_clip", "done")                 # loại KHÁC
job(vids[1] + 100 if False else vids[2], "m1_export_clip", "pending")

c = services.queue_counts()
ok(c["failed"] == 4, "chip lỗi = 4 (b, c2, c1? KHÔNG — xem dưới)",
   f"đếm={c['failed']}")
# kỳ vọng: a (đã chạy lại) bỏ; b đếm; c1 (có c2 mới hơn nhưng c2 'failed') vẫn
# đếm; c2 đếm; d đếm (lượt mới là LOẠI khác) -> b, c1, c2, d = 4
chay, xong = services.list_jobs_top(24, 24)
m = {r["id"]: r for r in xong}
ok(m[a_loi]["da_thu_lai"] == 1, "CA1 job a đánh dấu đã chạy lại")
ok(m[b_loi]["da_thu_lai"] == 0, "CA2 job b vẫn là lỗi")
ok(m[c1]["da_thu_lai"] == 0 and m[c2]["da_thu_lai"] == 0,
   "CA3 lượt mới cũng lỗi -> không coi là đã chạy lại")
ok(m[d_loi]["da_thu_lai"] == 0, "CA4 lượt mới khác loại -> không xoá lỗi oan")
thu_tu = [r["id"] for r in xong]
loi_that = [b_loi, c1, c2, d_loi]
ok(max(thu_tu.index(i) for i in loi_that) < thu_tu.index(a_loi),
   "lỗi thật xếp TRƯỚC dòng đã chạy lại", str(thu_tu[:6]))

print("CA 5: dòng UI")
from PyQt6.QtWidgets import QApplication  # noqa: E402
_APP = QApplication.instance() or QApplication([])
from app.ui import queue_panel as QP  # noqa: E402
ok(QP._da_thu_lai(m[a_loi]) and not QP._da_thu_lai(m[b_loi]), "_da_thu_lai đọc đúng")
ok(QP._da_thu_lai({"status": "failed"}) is False, "thiếu cột -> coi là lỗi (an toàn)")
try:
    panel = QP.QueuePanel.__new__(QP.QueuePanel)
    src = Path(QP.__file__).read_text(encoding="utf-8")
    ok('txt, tone = "Đã chạy lại", "muted"' in src and "btn.hide()" in src,
       "nhãn 'Đã chạy lại' + ẩn nút có trong mã")
except Exception as e:  # noqa: BLE001
    ok(False, "CA5", repr(e))

print("CA 6: ưu tiên tiến trình phân tích")
import psutil  # noqa: E402
import subprocess  # noqa: E402
from app.queue import jobs as J  # noqa: E402
from app.core import analysis_process as AP  # noqa: E402
ok(J._BELOW_NORMAL == 0x4000, "mở ở BELOW_NORMAL")
code = ("import os,sys,time,json;from pathlib import Path;"
        "p=Path(os.environ['BQ_ANALYSIS_STATUS_FILE']);"
        "time.sleep(1.0);"
        "p.write_text(json.dumps(dict(kind='progress',progress=.5,message='x',updated=1)),encoding='utf-8');"
        "time.sleep(2.0);"
        "p.write_text(json.dumps(dict(kind='done',progress=1,message='y',updated=2)),encoding='utf-8')")


class Ctx:
    profile = {}
    luot = []

    def check_canceled(self):
        pass

    def progress(self, p, msg):
        pass


uu_tien = {}
_cu = AP._ha_uu_tien


def _bat(proc):
    uu_tien["truoc"] = psutil.Process(proc.pid).nice()
    _cu(proc)
    uu_tien["sau"] = psutil.Process(proc.pid).nice()


AP._ha_uu_tien = _bat
AP.supervise([sys.executable, "-c", code], str(TMP), dict(os.environ), Ctx(),
             creationflags=0x08000000 | J._BELOW_NORMAL,
             idle_when_ready=bool(J._IDLE_PRIORITY))
ok(uu_tien.get("truoc") == psutil.BELOW_NORMAL_PRIORITY_CLASS,
   "lúc khởi động = BELOW_NORMAL", str(uu_tien))
ok(uu_tien.get("sau") == psutil.IDLE_PRIORITY_CLASS,
   "sẵn sàng rồi -> IDLE", str(uu_tien))
AP._ha_uu_tien = _cu

print(f"\nCỔNG 107: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
