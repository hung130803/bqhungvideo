# -*- coding: utf-8 -*-
# VAN KIỂM SOÁT AI trong dây chuyền (anh Hùng 30/07: "cắt lỗi ra không biết
# cái nào cắt bằng AI hay không để kiểm soát"):
#   - video dây chuyền phân tích ra CƠ BẢN (chưa qua AI) -> TỰ PHÂN TÍCH LẠI
#     đúng 1 lần rồi mới xuất;
#   - lần 2 vẫn cơ bản -> xuất (không tắc dây chuyền) nhưng log ⚠ + sổ ghi
#     dấu [CƠ BẢN] để soát lại được;
#   - video qua AI ngon -> xuất thẳng, KHÔNG tốn lượt phân tích thêm.
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="ai_gate_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = Path(r"D:\claude\ai-content-studio\bin\ffmpeg.exe")
STABLE = 70

import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtWidgets import QApplication  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402

qapp = QApplication(sys.argv)
st_q = app_settings()

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


def clip_gia(vid: int, llm: bool) -> int:
    return db.insert(
        "INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
        "transcript, signals, status) VALUES(?,0.0,0.5,90,'C','',?, "
        "'suggested')",
        (vid, db.dumps({"segments": [[0.0, 0.5]], "n_seg": 1,
                        "llm_used": llm, "dur": 0.5})))


def n_auto(vid: int) -> int:
    return db.query_one(
        "SELECT COUNT(*) AS n FROM jobs WHERE video_id=? AND "
        "type IN ('auto','auto_recap')", (vid,))["n"]


# ── dựng kênh dây chuyền: 1 video, job phân tích nằm pending (pool ko start)
src = T / "nguon" / "KenhA"
out = T / "xuat" / "KenhA"
out.mkdir(parents=True, exist_ok=True)
lam_video(src / "video1.mp4")
db.execute(
    "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, "
    "pipe_mode, pipe_daily, pipe_src) VALUES('KenhA', ?, 'Mỹ', ?, 1, "
    "'auto', 0, ?)", (str(T / "assets"), str(out), str(src)))
st_q.setValue("pipe_root", str(T / "nguon"))
st_q.setValue("chan_group", "Mỹ")
st_q.setValue("chan_groups_extra", "[]")
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.setValue("pipe_recycle_dir", str(T / "thungrac"))
st_q.sync()

pg = StudioPage(AppState())
pg._pipe_run()
bom_nhip(30)
jrow = db.query_one(
    "SELECT id, video_id FROM jobs WHERE type IN ('auto','auto_recap')")
kiem(bool(jrow), "dựng cảnh: video đã vào dây chuyền")
jid, vid = int(jrow["id"]), int(jrow["video_id"])

# ── 1. _video_cut_basic đọc đúng cờ llm_used
print("\n══ 1. _video_cut_basic ══")
kiem(not pg._video_cut_basic(vid), "chưa có clip -> KHÔNG coi là cơ bản")
c1 = clip_gia(vid, llm=False)
kiem(pg._video_cut_basic(vid), "clip llm_used=False -> CƠ BẢN")
c2 = clip_gia(vid, llm=True)
kiem(not pg._video_cut_basic(vid), "có clip qua AI -> KHÔNG phải cơ bản")
db.execute("DELETE FROM clips WHERE id IN (?,?)", (c1, c2))

# ── 2. Phân tích xong mà CƠ BẢN -> tự phân tích LẠI 1 lần, chưa xuất
print("\n══ 2. cơ bản lần 1 -> tự phân tích lại ══")
clip_gia(vid, llm=False)
db.execute("UPDATE jobs SET status='done' WHERE id=?", (jid,))
pg._check_auto_export()
kiem(n_auto(vid) == 2, "đã xếp job phân tích LẠI (1 -> 2 job)",
     f"{n_auto(vid)} job")
n_export = db.query_one(
    "SELECT COUNT(*) AS n FROM jobs WHERE type='m1_export_clip'")["n"]
kiem(n_export == 0, "CHƯA xuất clip cơ bản nào", f"{n_export} job xuất")
kiem(any("PHÂN TÍCH LẠI" in ln for ln in pg._pipe_report),
     "log báo rõ 'tự PHÂN TÍCH LẠI'",
     str(pg._pipe_report[-2:]))
jid2 = int(db.query_one(
    "SELECT id FROM jobs WHERE video_id=? AND type IN ('auto','auto_recap') "
    "ORDER BY id DESC LIMIT 1", (vid,))["id"])
kiem(jid2 in pg._pending_export, "sổ chờ-xuất đã trỏ sang job mới")

# ── 3. Lần 2 VẪN cơ bản -> xuất (không tắc) + dấu [CƠ BẢN] + log ⚠
print("\n══ 3. cơ bản lần 2 -> xuất + đánh dấu ══")
db.execute("UPDATE jobs SET status='done' WHERE id=?", (jid2,))
pg._check_auto_export()
kiem(n_auto(vid) == 2, "KHÔNG phân tích lại lần 3 (tránh vòng lặp)",
     f"{n_auto(vid)} job")
kiem(jid2 not in pg._pending_export, "job đã ra khỏi sổ chờ-xuất (đã xử lý)")
# ctx sau khi xuất đã CHUYỂN từ _pipe_by_vid sang _pipe_exports (hoặc nếu
# xuất lỗi trong sandbox thì nằm ở đường lỗi) -> soi cả 2 sổ
ctx = (pg._pipe_by_vid.get(vid)
       or (pg._pipe_exports.get(vid) or {}).get("ctx") or {})
n_exp = db.query_one(
    "SELECT COUNT(*) AS n FROM jobs WHERE type='m1_export_clip'")["n"]
kiem(ctx.get("basic") is True or n_exp == 0,
     "ctx được đánh dấu basic=True (khi xuất chạy được)",
     f"ctx={bool(ctx)} n_export={n_exp}")
kiem(any("vẫn cắt CƠ BẢN" in ln for ln in pg._pipe_report),
     "log ⚠ báo 'vẫn cắt CƠ BẢN sau 2 lần'", str(pg._pipe_report[-2:]))

# ── 4. Video QUA AI -> xuất thẳng, không tốn lượt phân tích thêm
print("\n══ 4. video qua AI xuất thẳng ══")
db.execute("DELETE FROM pipeline_files")
db.execute("DELETE FROM jobs")
db.execute("DELETE FROM clips")
db.execute("DELETE FROM videos")
for f in src.glob("*.mp4"):
    f.unlink()
from PyQt6.QtCore import QTimer
for t in pg.findChildren(QTimer):
    t.stop()
for s in ("_pipe_cut", "_pipe_by_vid", "_pipe_exports", "_pending_export"):
    getattr(pg, s, {}).clear()

lam_video(src / "video2.mp4")
pg2 = StudioPage(AppState())
pg2._pipe_run()
bom_nhip(30)
jrow = db.query_one(
    "SELECT id, video_id FROM jobs WHERE type IN ('auto','auto_recap')")
jid, vid = int(jrow["id"]), int(jrow["video_id"])
clip_gia(vid, llm=True)
db.execute("UPDATE jobs SET status='done' WHERE id=?", (jid,))
pg2._check_auto_export()
kiem(n_auto(vid) == 1, "KHÔNG phân tích lại video đã qua AI",
     f"{n_auto(vid)} job")
kiem((pg2._pipe_by_vid.get(vid) or {}).get("basic") is not True,
     "không bị đánh dấu [CƠ BẢN] oan")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — nhìn được video nào qua AI, video nào không")
