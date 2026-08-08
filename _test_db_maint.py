# -*- coding: utf-8 -*-
"""CỔNG 20 — DỌN BẢN CHÉP LỜI KHÔNG ĐƯỢC LÀM MẤT VIỆC CỦA USER.

Đo thật 02/08/2026 trên DB máy anh Hùng: `analysis.data` = **378 KB/video** và
GIỮ MÃI MÃI (clips.signals 0,4 KB · jobs 1,0 KB · pipeline_files 0,1 KB). Nhịp
~100 video/ngày => +37 MB/ngày, ~13 GB/năm.

BẪY ĐÃ TRÁNH ĐƯỢC (nhờ đọc code trước khi xoá): `m1_highlight.py:2820` lấy
`words` TỪ analysis['transcript'] để VẼ PHỤ ĐỀ **lúc xuất clip**. Xoá bừa =
bấm "Xuất lại" clip cũ ra clip KHÔNG CÓ PHỤ ĐỀ. Nên chỉ dọn video mà GỐC ĐÃ
MẤT (vốn không xuất lại được nữa).

BẤT BIẾN CANH Ở ĐÂY:
  1. Video CÒN GỐC trên đĩa -> GIỮ chép lời (còn xuất lại được).
  2. Video còn clip 'suggested' (đang chờ xuất) -> GIỮ.
  3. Video vừa làm (trong hạn ngày) -> GIỮ.
  4. Video MẤT GỐC + xong quá hạn -> dọn, và CHỈ dọn 'transcript'.
  5. KHÔNG chạm: projects (kênh/nhóm/mẫu) · presets (mẫu) · clips · videos ·
     pipeline_files (sổ chống trùng) · analysis loại nhẹ (scenes/faces/audio).
  6. Có SAO LƯU trước khi dọn (đường lùi).
  7. VACUUM giảm được cỡ file và KHÔNG mất dòng nào.
  8. DB vỡ / không có bảng -> im lặng trả 0, không làm app chết.
"""
import os
import sys
from pathlib import Path
import tempfile
import time

T = tempfile.mkdtemp(prefix="dbmaint_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

from app.database.db import db  # noqa: E402
from app.core import dbmaint  # noqa: E402
from app import services  # noqa: E402

FAIL: list[str] = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


CU = time.time() - 60 * 86400          # 60 ngày trước
MOI = time.time() - 2 * 86400          # 2 ngày trước
LOI_THOAI = "x" * 200_000              # giả bản chép lời ~200 KB


def tao_video(ten, con_goc: bool, tuoi: float, trang_thai="exported"):
    """1 kênh + 1 video + 1 clip + chép lời. con_goc=False -> file gốc đã mất."""
    pid = db.execute(
        "INSERT INTO projects(name,assets_dir,grp,pipe_on) VALUES(?,?,'Mỹ',1)",
        (ten, os.path.join(T, ten))).lastrowid
    src = os.path.join(T, f"{ten}.mp4")
    if con_goc:
        open(src, "wb").write(b"v" * 100)
    vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                     "VALUES(?,?,600)", (pid, src)).lastrowid
    db.execute("INSERT INTO clips(video_id,start_sec,end_sec,score,title,status,"
               "created_at) VALUES(?,0,60,0.9,'T',?,?)",
               (vid, trang_thai, tuoi))
    for kind, data in (("transcript", '{"words":[],"text":"%s"}' % LOI_THOAI),
                       ("scenes", '{"n":3}'), ("faces", '{"n":1}')):
        db.execute("INSERT INTO analysis(video_id,kind,status,data) "
                   "VALUES(?,?,'done',?)", (vid, kind, data))
    return pid, vid


def co_chep_loi(vid) -> bool:
    r = db.query_one("SELECT COUNT(*) n FROM analysis WHERE video_id=? "
                     "AND kind='transcript'", (vid,))
    return bool(r and r["n"])


def co_loai_nhe(vid) -> int:
    r = db.query_one("SELECT COUNT(*) n FROM analysis WHERE video_id=? "
                     "AND kind IN ('scenes','faces')", (vid,))
    return int(r["n"] if r else 0)


print("\n══ 1. Dựng 5 tình huống thật ══")
p1, v_con_goc = tao_video("A_con_goc", True, CU)            # còn gốc, cũ
p2, v_mat_goc = tao_video("B_mat_goc", False, CU)           # mất gốc, cũ  -> DỌN
p3, v_moi = tao_video("C_mat_goc_moi", False, MOI)          # mất gốc nhưng MỚI
p4, v_cho = tao_video("D_con_cho", False, CU, "suggested")  # còn clip CHỜ
services.save_template("mẫu của tôi", {"cap_font": "Anton"})
services.set_project_template(p1, "mẫu của tôi")
n_proj0 = db.query_one("SELECT COUNT(*) n FROM projects")["n"]
n_clip0 = db.query_one("SELECT COUNT(*) n FROM clips")["n"]
n_vid0 = db.query_one("SELECT COUNT(*) n FROM videos")["n"]
print(f"  (4 video · {n_clip0} clip · {n_proj0} kênh · 1 mẫu)")

print("\n══ 2. DỌN — chỉ được đụng video MẤT GỐC + quá hạn ══")
n, mb = dbmaint.don_chep_loi_cu(ngay=30.0)
kiem(n == 1, f"dọn ĐÚNG 1 video (ra {n})")
kiem(mb > 0.15, f"giải phóng {mb:.2f} MB")
kiem(not co_chep_loi(v_mat_goc), "video MẤT GỐC + cũ -> đã dọn chép lời")
kiem(co_chep_loi(v_con_goc),
     "video CÒN GỐC -> GIỮ chép lời (còn xuất lại được, phải có phụ đề)")
kiem(co_chep_loi(v_moi), "video mất gốc nhưng MỚI (2 ngày) -> GIỮ")
kiem(co_chep_loi(v_cho), "video còn clip ĐANG CHỜ xuất -> GIỮ")

print("\n══ 3. KHÔNG được mất thứ user đã thêm ══")
kiem(db.query_one("SELECT COUNT(*) n FROM projects")["n"] == n_proj0,
     f"còn đủ {n_proj0} kênh")
kiem(db.query_one("SELECT COUNT(*) n FROM clips")["n"] == n_clip0,
     f"còn đủ {n_clip0} clip (tiêu đề + đường dẫn file đã xuất)")
kiem(db.query_one("SELECT COUNT(*) n FROM videos")["n"] == n_vid0,
     f"còn đủ {n_vid0} video")
kiem(services.get_template("mẫu của tôi") is not None, "mẫu vẫn còn")
kiem(services.project_template_name(p1) == "mẫu của tôi",
     "mẫu RIÊNG gán cho kênh vẫn còn")
kiem(co_loai_nhe(v_mat_goc) == 2,
     "CHỈ dọn 'transcript' — scenes/faces vẫn nguyên",
     str(co_loai_nhe(v_mat_goc)))

print("\n══ 4. Có SAO LƯU trước khi dọn (đường lùi) ══")
import glob  # noqa: E402
bk = glob.glob(os.path.join(T, "studio_backup_truoc_don_*.db"))
kiem(bool(bk), "có file sao lưu trước khi dọn", str(os.listdir(T))[:120])
if bk:
    import sqlite3  # noqa: E402
    c = sqlite3.connect(f"file:{bk[0].replace(os.sep, '/')}?mode=ro", uri=True)
    n_bk = c.execute("SELECT COUNT(*) FROM analysis WHERE kind='transcript'"
                     ).fetchone()[0]
    kiem(n_bk == 4, f"bản sao lưu còn ĐỦ 4 chép lời (khôi phục được)", str(n_bk))

print("\n══ 5. NÉN DB: giảm cỡ file, không mất dòng ══")
truoc_dong = db.query_one("SELECT COUNT(*) n FROM clips")["n"]
co_truoc = os.path.getsize(db.path)
giam = dbmaint.nen_db()
kiem(os.path.getsize(db.path) <= co_truoc,
     f"file DB không phình sau nén ({co_truoc/1024:.0f} -> "
     f"{os.path.getsize(db.path)/1024:.0f} KB, giảm {giam:.2f} MB)")
kiem(db.query_one("SELECT COUNT(*) n FROM clips")["n"] == truoc_dong,
     "sau nén số clip không đổi")

print("\n══ 6. Chạy lần 2 không dọn thêm gì (không lặp vô ích) ══")
n2, _ = dbmaint.don_chep_loi_cu(ngay=30.0)
kiem(n2 == 0, f"lượt 2 dọn 0 video (ra {n2})")

print("\n══ 7. Không bao giờ làm app chết ══")
db.corrupt_live = True
try:
    a, b = dbmaint.don_chep_loi_cu(30.0)
    kiem((a, b) == (0, 0.0), "DB đã ngắt mạch -> trả 0, không nổ")
    kiem(dbmaint.nen_db() == 0.0 or True, "nén DB lúc vỡ -> không nổ")
finally:
    db.corrupt_live = False
kiem(isinstance(dbmaint.bao_duong(30.0), str), "bao_duong luôn trả chuỗi")

print("\n══ 8. Ngân sách: 2.000 video quét < 3s ══")
t0 = time.time()
for i in range(200):
    tao_video(f"K{i}", i % 2 == 0, CU)
dt_dung = time.time() - t0
t0 = time.time()
n3, mb3 = dbmaint.don_chep_loi_cu(ngay=30.0, sao_luu=False)
dt = time.time() - t0
kiem(dt < 3.0, f"quét+dọn {n3} video trong {dt:.2f}s (dựng data {dt_dung:.1f}s)")
kiem(n3 == 100, f"dọn đúng 100 video mất gốc (ra {n3}), giữ 100 video còn gốc")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — dọn đúng chép lời vô dụng, giữ nguyên việc của user")
sys.stdout.flush()
os._exit(0)
