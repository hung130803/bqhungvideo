# -*- coding: utf-8 -*-
"""CỔNG 18 — TỰ DỌN RÁC ĐĨA + GẤP WAL. Đo thật máy anh Hùng 31/07/2026:

  ổ C còn 3,19/926 GB · %TEMP% 11,6 GB / 39.637 file, trong đó
  _MEI* 4,69 GB (339 mục — yt-dlp bản onefile giải nén ~22 MB/lần chạy rồi bị
  tắt giữa đường) · _seg_*.mkv 1,71 GB (98 file — mảnh ghép đoạn, finally
  không chạy vì app thoát bằng os._exit) · studio.db-wal 1,78 MB tồn từ 06/07
  vì os._exit không cho SQLite checkpoint.
  Sau khi dọn: 10,94 GB trống (+7,75 GB).

Ổ ĐẦY LÀ NGUYÊN NHÂN GỐC của DB ghi dở → vỡ, nên cổng này canh 2 việc:
  A. Bộ dọn CHỈ xoá đúng thứ của mình, đúng tuổi, không bao giờ ném lỗi.
  B. Thoát app phải GẤP WAL — kiểm bằng cách đọc DB từ TIẾN TRÌNH NGOÀI.
"""
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="donrac_"))
TMPD = T / "temp"
TMPD.mkdir()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["TEMP"] = os.environ["TMP"] = str(TMPD)   # %TEMP% giả -> an toàn
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "s.ini")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

from app.core import tempsweep as TS  # noqa: E402

FAIL: list[str] = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


def gia(p: Path, gio: float) -> None:
    """Đặt lại giờ sửa cho `p` (và cả cây con) thành `gio` giờ trước."""
    t = time.time() - gio * 3600
    if p.is_dir():
        for q in p.rglob("*"):
            os.utime(q, (t, t))
    os.utime(p, (t, t))


print("\n══ 1. CHỈ xoá đúng tên · đúng tuổi · không đụng thứ của người khác ══")
(TMPD / "_MEI111").mkdir()
(TMPD / "_MEI111" / "python310.dll").write_bytes(b"x" * 5000)
gia(TMPD / "_MEI111", 5)
(TMPD / "_MEI222").mkdir()                       # MỚI -> phải giữ
(TMPD / "_MEI222" / "a.dll").write_bytes(b"y" * 100)
old_seg = TMPD / "_seg_abc_1.mkv"
old_seg.write_bytes(b"v" * 9000)
gia(old_seg, 5)
new_seg = TMPD / "_seg_dang_chay_0.mkv"          # MỚI -> đang xuất, phải giữ
new_seg.write_bytes(b"v" * 100)
quan_trong = TMPD / "video_quan_trong.mp4"       # KHÔNG khớp mẫu -> phải giữ
quan_trong.write_bytes(b"z" * 9000)
gia(quan_trong, 200)
ho_so = TMPD / "cookies_youtube.txt"
ho_so.write_bytes(b"cookie")
gia(ho_so, 200)

n, byte = TS.quet_temp(gio_min=1.0)
kiem(not (TMPD / "_MEI111").exists(), "xoá _MEI cũ (rác yt-dlp)")
kiem((TMPD / "_MEI222").exists(), "GIỮ _MEI mới (<2h — có thể đang tải)")
kiem(not old_seg.exists(), "xoá _seg_ cũ")
kiem(new_seg.exists(), "GIỮ _seg_ mới (đang xuất clip)")
kiem(quan_trong.exists(), "KHÔNG đụng file không khớp mẫu (video của user)")
kiem(ho_so.exists(), "KHÔNG đụng cookie")
kiem(n == 2 and byte > 13000, f"đếm đúng: {n} mục / {byte} byte")

print("\n══ 2. KHÔNG xoá _MEI của CHÍNH tiến trình đang chạy ══")
minh = TMPD / "_MEI_cua_minh"
minh.mkdir()
(minh / "app.dll").write_bytes(b"a" * 100)
gia(minh, 9)
sys._MEIPASS = str(minh)          # giả lập đang chạy bản .exe onefile
try:
    TS.quet_temp(gio_min=1.0)
    kiem(minh.exists(), "giữ nguyên thư mục _MEI của tiến trình này")
finally:
    del sys._MEIPASS

print("\n══ 3. File đang bị KHOÁ -> bỏ qua, không ném lỗi ══")
khoa = TMPD / "_seg_bi_khoa_0.mkv"
khoa.write_bytes(b"k" * 500)
gia(khoa, 9)
fh = open(khoa, "rb")            # giữ handle: Windows không cho xoá
try:
    n2, _ = TS.quet_temp(gio_min=1.0)
    kiem(True, "quét xong không nổ dù file bị khoá")
    kiem(khoa.exists(), "file đang khoá vẫn còn (không phá tiến trình khác)")
finally:
    fh.close()
TS.quet_temp(gio_min=1.0)
kiem(not khoa.exists(), "nhả khoá rồi thì lần quét sau xoá được")

print("\n══ 4. DATA_DIR: giữ 3 bản DB mới nhất · log 14 ngày · error.log không phình ══")
for i in range(6):
    p = T / f"studio_{1783300000 + i}.db"
    p.write_bytes(b"d" * 1000)
    gia(p, 100 - i)              # i lớn = mới hơn
(T / "studio.db.corrupt999").write_bytes(b"c" * 1000)
gia(T / "studio.db.corrupt999", 300)
logs = T / "logs"
logs.mkdir(exist_ok=True)
log_cu = logs / "pipeline_20260101.log"
log_cu.write_text("cu", encoding="utf-8")
gia(log_cu, 24 * 30)
log_moi = logs / "pipeline_20260731.log"
log_moi.write_text("moi", encoding="utf-8")
el = logs / "error.log"
el.write_bytes(b"A" * 100 + b"CUOI_CUNG" + b"B" * (3 * 1024 * 1024))
n3, _ = TS.quet_data_dir(T)
con = sorted(T.glob("studio_*.db"))
kiem(len(con) == 3, f"giữ đúng 3 bản DB cũ (còn {len(con)})", str([p.name for p in con]))
kiem((T / "studio_1783300005.db").exists(), "giữ bản MỚI NHẤT")
kiem(not (T / "studio_1783300000.db").exists(), "xoá bản cũ nhất")
kiem(not (T / "studio.db.corrupt999").exists(), "xoá bản quarantine quá hạn")
kiem(not log_cu.exists(), "xoá log quá 14 ngày")
kiem(log_moi.exists(), "GIỮ log gần đây (còn để tra lỗi)")
kiem(el.stat().st_size < 1_200_000, f"cắt error.log phình ({el.stat().st_size} byte)")
kiem(b"B" in el.read_bytes()[-100:], "giữ ĐUÔI error.log (lỗi mới nhất còn đọc được)")

print("\n══ 5. Không bao giờ làm app chết ══")
n4, mb4 = TS.quet_tat(Path(r"Z:\khong_ton_tai_gi_ca"))
kiem(True, "thư mục không tồn tại -> im lặng, không ném lỗi")
os.environ.pop("TEMP", None)
try:
    TS.quet_tat(None)
    kiem(True, "thiếu biến TEMP -> vẫn không nổ")
finally:
    os.environ["TEMP"] = os.environ["TMP"] = str(TMPD)

print("\n══ 6. Thư mục tạm RIÊNG cho yt-dlp (rác gom 1 chỗ) ══")
d = TS.temp_rieng_cho_ytdlp(T)
kiem(d and Path(d).is_dir(), "tạo được thư mục tạm riêng", str(d))
kiem(Path(d).parent == T, "nằm trong DATA_DIR của app", str(d))
rac_cu = Path(d) / "_MEI999"
rac_cu.mkdir()
(rac_cu / "x").write_bytes(b"x" * 2000)
gia(rac_cu, 5)
rac_moi = Path(d) / "_MEI888"
rac_moi.mkdir()
n5, b5 = TS.don_temp_ytdlp(T)
kiem(not rac_cu.exists() and rac_moi.exists(),
     "dọn cây tạm yt-dlp: xoá cũ, giữ mới (đang tải)")
kiem("env=_env" in (Path(str(Path(__file__).resolve().parent / 'app' / 'ui' / 'studio_page.py'))
                    .read_text(encoding="utf-8")),
     "lệnh yt-dlp được truyền env riêng (rác không rơi vào %TEMP% chung)")

print("\n══ 7. THOÁT APP PHẢI GẤP WAL — kiểm bằng đọc từ NGOÀI ══")
from app.database.db import db  # noqa: E402
db.execute("INSERT INTO projects(name,assets_dir,grp,pipe_on) "
           "VALUES('K',?,'Mỹ',1)", (str(T / "as"),))
for i in range(200):             # ghi nhiều cho WAL phình lên
    db.execute("INSERT INTO projects(name,assets_dir,grp,pipe_on) "
               "VALUES(?,?,'Mỹ',0)", (f"K{i}", str(T / f"as{i}")))
wal = Path(str(db.path) + "-wal")
truoc = wal.stat().st_size if wal.exists() else 0
kiem(truoc > 0, f"trước khi gấp: WAL {truoc} byte")
# ĐỌC TỪ NGOÀI khi CHƯA gấp: đúng cảnh anh Hùng gặp (file chính thiếu dữ liệu)
def dem_ngoai():
    """Copy CHỈ file .db (không kèm -wal) sang chỗ khác rồi đếm.

    Đây đúng là cảnh thật: sao lưu/đọc file studio.db mà thiếu WAL. Chưa gấp
    WAL thì file chính thiếu dữ liệu (máy anh Hùng: báo 'malformed'); gấp rồi
    thì file chính TỰ ĐỦ."""
    import shutil
    ra = T / f"ngoai_{time.time_ns()}.db"
    shutil.copyfile(db.path, ra)
    c = sqlite3.connect(str(ra), timeout=10)
    try:
        return c.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    finally:
        c.close()


try:
    ngoai_truoc = dem_ngoai()
except Exception as e:  # noqa: BLE001
    ngoai_truoc = f"KHONG DOC DUOC ({str(e)[:40]})"
mb = db.gap_wal()
sau = wal.stat().st_size if wal.exists() else 0
kiem(sau == 0, f"gấp WAL xong -> WAL rỗng (còn {sau} byte)")
kiem(db.query_one("SELECT COUNT(*) n FROM projects")["n"] == 201,
     "dữ liệu còn nguyên sau khi gấp")
try:
    ngoai_sau = dem_ngoai()
except Exception as e:  # noqa: BLE001
    ngoai_sau = f"LOI ({str(e)[:40]})"
kiem(ngoai_sau == 201,
     f"đọc từ NGOÀI thấy đủ 201 dòng (trước khi gấp: {ngoai_truoc})",
     str(ngoai_sau))

print("\n══ 8. gap_wal không được nổ ở mọi trạng thái ══")
db.corrupt_live = True
kiem(db.gap_wal() == 0, "DB đã ngắt mạch -> trả 0, không đụng đĩa")
db.corrupt_live = False
_p, db.path = db.path, ":memory:"
db.in_memory = True
kiem(db.gap_wal() == 0, "DB RAM -> trả 0")
db.path, db.in_memory = _p, False
kiem(isinstance(db.gap_wal(), int), "gọi 2 lần liên tiếp vẫn trả số")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — app tự dọn rác đúng thứ của mình, gấp WAL khi thoát")
sys.stdout.flush()
os._exit(0)
