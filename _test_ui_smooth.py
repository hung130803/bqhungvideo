# -*- coding: utf-8 -*-
# MƯỢT + KHÔNG ĐỨNG IM (anh Hùng 31/07: "bấm chạy mà nó không chạy luôn, phải
# X cái kia nó mới bắt đầu chạy... chạy cực kỳ đơ, thanh tiến trình mất rồi lại
# có, chuyển động chậm delay").
#
# ĐO ĐƯỢC TRƯỚC KHI SỬA (100 kênh/600 video/1800 clip/3000 job):
#   - dialog Dây chuyền mở -> _check_auto_export chạy 0/2 nhịp (ĐỨNG IM)
#   - 1 clip đổi trạng thái -> đập cả danh sách 9,1 ms + thanh tiến trình bị
#     XOÁ rồi tạo mới (nhấp nháy mất-hiện)
# SAU SỬA: 2/2 nhịp; thanh tiến trình GIỮ NGUYÊN widget; chỉ dòng đổi mới dựng.
import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="ui_smooth_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

import app.queue.jobs  # noqa: F401,E402
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

qapp = QApplication(sys.argv)
from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


# ---- dữ liệu cỡ THẬT của anh Hùng: 100 kênh, 600 video, 1800 clip, 3000 job
for i in range(1, 101):
    grp = "Mỹ" if i <= 47 else ("Mỹ mới" if i <= 80 else "Nhật")
    db.execute("INSERT INTO projects(name,assets_dir,grp,pipe_on) "
               "VALUES(?,?,?,1)", (f"kênh {i}", os.path.join(T, f"a{i}"), grp))
for pid in range(1, 101):
    for k in range(6):
        vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                         "VALUES(?,?,600)",
                         (pid, os.path.join(T, f"v{pid}_{k}.mp4"))).lastrowid
        for c in range(3):
            db.insert("INSERT INTO clips(video_id,start_sec,end_sec,score,"
                      "title,signals,status) VALUES(?,?,?,90,'C','{}',"
                      "'suggested')", (vid, c * 90, c * 90 + 70))
for j in range(3000):
    db.insert("INSERT INTO jobs(type,payload,status,video_id) "
              "VALUES('m1_export_clip','{}',?,?)",
              ("done" if j % 3 else "running", (j % 600) + 1))

pg = StudioPage(AppState())
pg.show()
qapp.processEvents()

print("== 1. DIALOG Qt mở: 'máy' dây chuyền PHẢI chạy tiếp ==")
dlg = QDialog(pg); dlg.setModal(True); dlg.show()
qapp.processEvents()
kiem(QApplication.activeModalWidget() is not None, "dựng cảnh: có modal đang mở")
dem = {"exp": 0, "pipe": 0, "clips": 0, "chan": 0}
_o = (pg._check_auto_export, pg._pipe_poll, pg._refresh_clips,
      pg._poll_chan_activity)
pg._check_auto_export = lambda: dem.__setitem__("exp", dem["exp"] + 1)
pg._pipe_poll = lambda: dem.__setitem__("pipe", dem["pipe"] + 1)
pg._refresh_clips = lambda *a, **k: dem.__setitem__("clips", dem["clips"] + 1)
pg._poll_chan_activity = lambda: dem.__setitem__("chan", dem["chan"] + 1)
pg._poll_tick(); pg._poll_tick()
kiem(dem["exp"] == 2, "TỰ XUẤT clip chạy đủ 2/2 nhịp (hết 'phải đóng dialog')",
     f"{dem['exp']}/2")
kiem(dem["pipe"] == 2, "dõi dây chuyền chạy đủ 2/2 nhịp", f"{dem['pipe']}/2")
kiem(dem["clips"] == 0 and dem["chan"] == 0,
     "phần VẼ trang chính (bị dialog che) được bỏ -> đỡ tốn CPU",
     f"clips={dem['clips']} chan={dem['chan']}")

print("== 2. hộp CHỌN FILE native: phải dừng HẲN (giữ bản sửa cũ) ==")
dem.update(exp=0, pipe=0)
pg._modal_busy = True
pg._poll_tick()
pg._modal_busy = False
kiem(dem["exp"] == 0 and dem["pipe"] == 0,
     "đang mở hộp chọn thư mục -> KHÔNG nhịp nào chạy (không cướp focus)",
     f"exp={dem['exp']} pipe={dem['pipe']}")
pg._check_auto_export, pg._pipe_poll, pg._refresh_clips, \
    pg._poll_chan_activity = _o
dlg.close(); qapp.processEvents()

print("== 3. 1 clip đổi trạng thái: KHÔNG đập cả danh sách ==")
vid = db.query_one("SELECT id FROM videos LIMIT 1")["id"]
pg.state.video_id = vid
db.execute("UPDATE jobs SET status='running' WHERE video_id=? LIMIT 1", (vid,)) \
    if False else None
db.insert("INSERT INTO jobs(type,payload,status,video_id) "
          "VALUES('m1_export_clip','{}','running',?)", (vid,))
pg._refresh_clips(force=True)
qapp.processEvents()
bar_truoc = getattr(pg, "_job_bar", None)
rows_truoc = dict(getattr(pg, "_row_w", {}))
kiem(bar_truoc is not None, "có thanh tiến trình (video đang có job chạy)")
kiem(len(rows_truoc) == 3, "sổ dòng clip ghi đủ 3 dòng", str(len(rows_truoc)))

cid = sorted(rows_truoc)[1]                    # đổi clip GIỮA
db.execute("UPDATE clips SET status='exported' WHERE id=?", (cid,))
t0 = time.perf_counter()
pg._refresh_clips()
ms = (time.perf_counter() - t0) * 1000
qapp.processEvents()
kiem(getattr(pg, "_job_bar", None) is bar_truoc,
     "THANH TIẾN TRÌNH giữ nguyên widget (hết mất-rồi-lại-có)")
rows_sau = getattr(pg, "_row_w", {})
giu = [k for k in rows_truoc if k != cid and rows_sau.get(k) is rows_truoc[k]]
kiem(len(giu) == 2, "2 dòng KHÔNG đổi được giữ nguyên (chỉ dựng lại 1 dòng)",
     f"giữ {len(giu)}/2")
kiem(rows_sau.get(cid) is not rows_truoc[cid], "dòng vừa đổi ĐƯỢC cập nhật")
print(f"     (cập nhật tại chỗ: {ms:.1f} ms)")
kiem(ms < 8.0, f"cập nhật tại chỗ nhanh (< 8ms, đo {ms:.1f}ms — trước 9,1ms "
     "cho cả danh sách)")

print("== 4. TẬP clip thay đổi -> vẫn dựng lại đầy đủ (không sai) ==")
db.insert("INSERT INTO clips(video_id,start_sec,end_sec,score,title,signals,"
          "status) VALUES(?,400,470,90,'C4','{}','suggested')", (vid,))
pg._refresh_clips()
qapp.processEvents()
kiem(len(getattr(pg, "_row_w", {})) == 4, "thêm clip -> danh sách có 4 dòng",
     str(len(getattr(pg, "_row_w", {}))))

print("== 5. ngân sách 1 nhịp poll với 100 kênh ==")
pg._poll_tick()
t0 = time.perf_counter()
for _ in range(20):
    pg._poll_tick()
ms = (time.perf_counter() - t0) / 20 * 1000
print(f"     (_poll_tick: {ms:.2f} ms/nhịp)")
kiem(ms < 30.0, f"1 nhịp poll < 30ms (đo {ms:.2f}ms) — UI không thể là nguồn đơ")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — dialog mở vẫn chạy, danh sách không nhấp nháy")
sys.stdout.flush()
os._exit(0)
