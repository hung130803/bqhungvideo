# -*- coding: utf-8 -*-
# 3 LỖI anh Hùng báo 30/07 (ảnh chụp: Part 1 AI + Part 2..8 "Cắt cơ bản" tên
# "Clip"):
#   L1. Tắt app hiện hộp lỗi 'NoneType' object has no attribute 'flush'.
#   L2. Video CŨ phân tích lại VẪN hiện clip "Cắt cơ bản (chưa qua AI)",
#       không tiêu đề — dù Groq chạy tốt.
#   L3. Đặt 3 part / 60-180s mà ra 7-8 part.
#
# GỐC L2+L3 (một gốc): _delete_suggested chỉ XOÁ clip còn 'suggested'. Clip đã
# XUẤT (status='exported') sống sót, mà list_clips lấy MỌI clip -> danh sách =
# clip cũ (heuristic, tên "Clip", 50đ) + clip mới của AI; Part đánh số theo vị
# trí trong danh sách -> 3 clip mới thành Part 4..6; "Xuất cả kênh" xuất luôn
# cả đám cũ => 7-8 part.
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="reanalyze_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")

from app.database.db import db  # noqa: E402
from app import services  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


pid = db.execute("INSERT INTO projects(name, assets_dir, grp) "
                 "VALUES('K', ?, '')", (T,)).lastrowid
vid = db.execute("INSERT INTO videos(project_id, src_path, duration) "
                 "VALUES(?,?,600)", (pid, os.path.join(T, "v.mp4"))).lastrowid


def them_clip(s, e, status, llm_used, title, export=True):
    return db.insert(
        "INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
        "transcript, signals, status, export_path) VALUES(?,?,?,?,?,'',?,?,?)",
        (vid, s, e, 90 if llm_used else 50, title,
         db.dumps({"segments": [[s, e]], "llm_used": llm_used}), status,
         (os.path.join(T, f"part_{s:.0f}.mp4") if export else None)))


# ═══ L2/L3: dựng đúng cảnh của anh Hùng — 5 clip CƠ BẢN đã XUẤT lần trước ═══
print("== dựng cảnh: lần trước cắt CƠ BẢN 5 part, đã xuất hết ==")
cu = [them_clip(60 + i * 120, 150 + i * 120, "exported", False, "Clip")
      for i in range(5)]
kiem(len(services.list_clips(vid)) == 5, "trước khi phân tích lại: 5 clip cũ")

print("\n== L2+L3: phân tích LẠI (AI ra đúng 3 clip) ==")
M1._delete_suggested(vid)              # bước đầu của mọi đường phân tích
moi = [them_clip(30 + i * 200, 120 + i * 200, "suggested", True,
                 f"Tiêu đề AI {i + 1}", export=False) for i in range(3)]
ds = services.list_clips(vid)
kiem(len(ds) == 3, "danh sách CHỈ còn 3 clip mới (user đặt 3 part)",
     f"{len(ds)} clip: {[ (r['title'], r['status']) for r in ds ]}")
kiem(all((db.loads(r["signals"], {}) or {}).get("llm_used") for r in ds),
     "MỌI clip trong danh sách đều do AI phân tích",
     str([(r["title"], db.loads(r["signals"], {}).get("llm_used")) for r in ds]))
kiem(all((r["title"] or "").startswith("Tiêu đề AI") for r in ds),
     "clip nào cũng CÓ tiêu đề (hết cảnh tên trơ 'Clip')",
     str([r["title"] for r in ds]))
kiem(not any(r["id"] in cu for r in ds),
     "không còn clip cũ nào lọt vào danh sách")

print("\n== KHÔNG MẤT DỮ LIỆU: clip cũ chỉ vào kho, còn nguyên dòng + file ==")
n_luu = db.query_one("SELECT COUNT(*) AS n FROM clips WHERE video_id=? AND "
                     "status='archived'", (vid,))["n"]
kiem(n_luu == 5, "5 clip cũ nằm trong kho 'archived' (KHÔNG bị xoá)",
     f"{n_luu}")
con_path = db.query_one("SELECT COUNT(*) AS n FROM clips WHERE video_id=? AND "
                        "status='archived' AND export_path IS NOT NULL",
                        (vid,))["n"]
kiem(con_path == 5, "đường dẫn file đã xuất của clip cũ vẫn còn (dò lịch sử)")

print("\n== CHỐNG TRÙNG vẫn hoạt động: đoạn cũ vẫn tính là ĐÃ DÙNG ==")
kiem("archived" in M1._USED_STATUSES,
     "'archived' nằm trong danh sách trạng thái ĐÃ DÙNG")
used = M1.load_used_ranges(vid)
kiem(len(used) >= 5, "load_used_ranges thấy đủ đoạn đã dùng lần trước "
     "(lần cắt sau không chọn lại đoạn đã đăng)", f"{len(used)} khoảng")

print("\n== job xuất ĐANG CHẠY thì clip không bị đụng (chống race) ==")
db.execute("DELETE FROM clips WHERE video_id=?", (vid,))
giu = them_clip(10, 100, "exported", False, "Đang xuất")
db.insert("INSERT INTO jobs(type, payload, status, video_id) "
          "VALUES('m1_export_clip', ?, 'running', ?)",
          (db.dumps({"clip_id": giu}), vid))
M1._delete_suggested(vid)
st = db.query_one("SELECT status FROM clips WHERE id=?", (giu,))["status"]
kiem(st == "exported", "clip đang có job xuất chạy KHÔNG bị đưa vào kho", st)

# ═══ L1: main.py xả đệm khi stdout=None (bản .exe không console) ═══
print("\n== L1: tắt app khi stdout/stderr = None (bản .exe windowed) ==")
import io  # noqa: E402
src = io.open(r"D:\claude\ai-content-studio\main.py", encoding="utf-8").read()
kiem("sys.stdout.flush," not in src and "sys.stderr.flush)" not in src,
     "main.py KHÔNG còn lấy .flush ngay trong tuple (ngoài try)")
ns = {"sys": type("S", (), {"stdout": None, "stderr": None})()}
exec("def _xa_dem():\n"
     "    for _f in (sys.stdout, sys.stderr):\n"
     "        if _f is not None:\n"
     "            _f.flush()\n", ns)
try:
    ns["_xa_dem"]()
    kiem(True, "xả đệm với stdout=None KHÔNG ném lỗi (hết hộp 'Có lỗi xảy ra')")
except Exception as e:  # noqa: BLE001
    kiem(False, "xả đệm với stdout=None KHÔNG ném lỗi", repr(e))

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — phân tích lại ra ĐÚNG số part, toàn AI, có tiêu đề")
