"""CỔNG 100 — SỔ TẠM (WAL) CŨ KHÔNG ĐƯỢC LÀM HỎNG FILE CHÍNH ĐANG LÀNH.

Sự cố thật 31/10/2026 (lần thứ 3): cạnh studio.db lành nằm một studio.db-wal CŨ
mà vẫn "hợp lệ" -> SQLite chép trang cũ đè lên dữ liệu mới -> 'malformed', job
treo 7 việc "đang phân tích" ma, analysis_worker_timeout. Phải tắt app chữa tay.

`Database._cat_wal_cu_neu_hong` (gọi ĐẦU `init_schema`) nay tự chữa. Cổng dựng
LẠI ĐÚNG sự cố bằng SQLite thật (không mock) và canh 2 chiều:
  * sổ tạm CŨ + file chính lành -> sổ tạm bị CẤT (không xoá), dữ liệu mới còn đủ;
  * sổ tạm BÌNH THƯỜNG sau khi tắt đột ngột (chứa việc MỚI NHẤT) -> GIỮ NGUYÊN;
  * có tiến trình khác đang mở DB -> KHÔNG đụng;
  * file chính tự nó hỏng -> KHÔNG cất sổ tạm (để đường cứu hộ cũ lo).
"""
import ast
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
HOP = Path(tempfile.mkdtemp(prefix="bq_test_walcu_"))
os.environ["BQ_DATA_DIR"] = str(HOP)
os.environ["BQ_DB_PATH"] = str(HOP / "khoi.db")

from app.database.db import Database  # noqa: E402

DAT = HONG = 0


def ok(dk, ten):
    global DAT, HONG
    if dk:
        DAT += 1
        print("  OK  ", ten)
    else:
        HONG += 1
        print("  HỎNG", ten)


def tao_db(thu: Path, so_dong: int, giu_mo=False):
    """DB thật chế độ WAL, bảng có dữ liệu đủ nhiều trang."""
    thu.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(thu / "studio.db"))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA wal_autocheckpoint=0")
    c.execute("CREATE TABLE IF NOT EXISTS t(id INTEGER PRIMARY KEY AUTOINCREMENT, v TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS t_v ON t(v)")
    c.executemany("INSERT INTO t(v) VALUES(?)", [(f"dong {i} " + "x" * 300,) for i in range(so_dong)])
    c.commit()
    if giu_mo:
        return c
    c.close()
    return None


def dem(path: Path, chi_file_chinh=False):
    uri = path.resolve().as_uri() + ("?immutable=1" if chi_file_chinh else "")
    c = sqlite3.connect(uri, uri=True)
    try:
        return c.execute("SELECT count(*) FROM t").fetchone()[0], c.execute("PRAGMA quick_check").fetchone()[0]
    finally:
        c.close()


def dung_su_co(thu: Path):
    """Tái hiện: chụp sổ tạm thế hệ CŨ, ghi tiếp cho file chính to ra rồi gộp
    hết, sau đó đặt sổ tạm cũ trở lại cạnh file chính."""
    c = tao_db(thu, 200, giu_mo=True)
    c.executemany("INSERT INTO t(v) VALUES(?)", [(f"cu {i} " + "y" * 300,) for i in range(300)])
    c.commit()
    shutil.copy2(thu / "studio.db-wal", thu / "wal_cu.bak")       # sổ tạm cũ, tự nhất quán
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.executemany("INSERT INTO t(v) VALUES(?)", [(f"moi {i} " + "z" * 300,) for i in range(4000)])
    c.commit()
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    for s in ("-wal", "-shm"):
        p = Path(str(thu / "studio.db") + s)
        if p.exists():
            p.unlink()
    shutil.copy2(thu / "wal_cu.bak", thu / "studio.db-wal")
    return 200 + 300 + 4000


def mo_app(thu: Path):
    """Mở như app mở. Trả (Database|None, lỗi)."""
    try:
        return Database(thu / "studio.db"), None
    except Exception as e:  # noqa: BLE001
        return None, e


def dong(d):
    if d is not None:
        d._reset_conn()


def ca1():
    print("CA 1 — sổ tạm CŨ cạnh file chính lành -> tự cất, không mất dữ liệu")
    thu = HOP / "ca1"
    dung = dung_su_co(thu)
    n_chinh, qc_chinh = dem(thu / "studio.db", chi_file_chinh=True)
    ok(n_chinh == dung and qc_chinh == "ok", f"tiền đề: file chính một mình LÀNH, đủ {dung} dòng ({n_chinh}, {qc_chinh})")
    ban = HOP / "ca1_thu"
    ban.mkdir()
    for s in ("", "-wal"):
        shutil.copy2(str(thu / "studio.db") + s, str(ban / "studio.db") + s)
    try:
        n_hai, qc_ca_hai = dem(ban / "studio.db")
    except sqlite3.Error as e:
        n_hai, qc_ca_hai = -1, str(e)
    ok(qc_ca_hai != "ok" or n_hai < dung,
       f"tiền đề: file chính + sổ tạm cũ làm HỎNG hoặc LÙI dữ liệu ({n_hai} dòng, {qc_ca_hai[:40]})")
    d, loi = mo_app(thu)
    ok(loi is None, f"app mở được, không ném lỗi ({loi})")
    ok(bool(d and d.tu_chua_note), "có lời nhắn tự chữa để báo user")
    if d is not None:
        n = d.conn().execute("SELECT count(*) FROM t").fetchone()[0]
        qc = d.conn().execute("PRAGMA quick_check").fetchone()[0]
        ok(n == dung and qc == "ok", f"sau khi mở: đủ {dung} dòng MỚI NHẤT + kiểm toàn vẹn đạt ({n}, {qc})")
    dong(d)
    cat = list((thu / "recovery").glob("wal_cu_*/studio.db-wal"))
    ok(len(cat) == 1 and cat[0].stat().st_size == (thu / "wal_cu.bak").stat().st_size,
       "sổ tạm cũ được CẤT nguyên vẹn vào recovery/wal_cu_*/ (không xoá)")
    log = thu / "logs" / "db_tu_chua.txt"
    ok(log.exists() and "sổ tạm cũ" in log.read_text(encoding="utf-8"), "ghi nhật ký logs/db_tu_chua.txt")
    d2, loi2 = mo_app(thu)
    ok(loi2 is None and d2 is not None and not d2.tu_chua_note, "mở lần 2: không còn gì để chữa")
    dong(d2)


def ca2():
    print("CA 2 — sổ tạm BÌNH THƯỜNG sau khi tắt đột ngột -> GIỮ NGUYÊN (chứa việc mới nhất)")
    thu, sap = HOP / "ca2_goc", HOP / "ca2"
    c = tao_db(thu, 300, giu_mo=True)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.executemany("INSERT INTO t(v) VALUES(?)", [(f"chua gop {i}",) for i in range(50)])
    c.commit()
    sap.mkdir()
    for s in ("", "-wal"):                      # chụp như lúc app bị tắt cứng
        shutil.copy2(str(thu / "studio.db") + s, str(sap / "studio.db") + s)
    c.close()
    n_chinh, _ = dem(sap / "studio.db", chi_file_chinh=True)
    ok(n_chinh == 300, f"tiền đề: 50 dòng mới CHỈ nằm trong sổ tạm (file chính {n_chinh})")
    d, loi = mo_app(sap)
    ok(loi is None and d is not None and not d.tu_chua_note, "không coi là hỏng, không cất")
    if d is not None:
        ok(d.conn().execute("SELECT count(*) FROM t").fetchone()[0] == 350, "đủ 350 dòng gồm 50 dòng trong sổ tạm")
    dong(d)
    ok(not (sap / "recovery").exists(), "không tạo thư mục cất nào")


def ca3():
    print("CA 3 — có kết nối khác đang mở DB -> KHÔNG đụng sổ tạm")
    thu = HOP / "ca3"
    dung_su_co(thu)
    giu = sqlite3.connect(str(thu / "studio.db-wal"))   # giữ handle tệp sổ tạm như tiến trình khác
    try:
        giu.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        pass
    d, _ = mo_app(thu)
    ok(not (d and d.tu_chua_note), "không tự chữa khi không giành được sổ tạm")
    ok((thu / "studio.db-wal").exists() and not (thu / "recovery").exists(), "sổ tạm còn nguyên chỗ cũ")
    dong(d)
    giu.close()


def ca4():
    print("CA 4 — file chính TỰ NÓ hỏng -> KHÔNG cất sổ tạm (để cứu hộ cũ lo)")
    thu = HOP / "ca4"
    c = tao_db(thu, 3000, giu_mo=True)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.executemany("INSERT INTO t(v) VALUES(?)", [(f"w {i}",) for i in range(20)])
    c.commit()
    sap = HOP / "ca4s"
    sap.mkdir()
    for s in ("", "-wal"):
        shutil.copy2(str(thu / "studio.db") + s, str(sap / "studio.db") + s)
    c.close()
    b = bytearray((sap / "studio.db").read_bytes())
    for off in range(4096 * 5, 4096 * 40, 4096):          # phá nhiều trang giữa file
        b[off:off + 64] = b"\xff" * 64
    (sap / "studio.db").write_bytes(bytes(b))
    w = (sap / "studio.db-wal").stat().st_size
    d, loi = mo_app(sap)
    ok(not (d and d.tu_chua_note), "không tự chữa khi file chính cũng hỏng")
    ok((sap / "studio.db-wal").exists() and (sap / "studio.db-wal").stat().st_size >= w or (sap / "recovery").exists() is False,
       "sổ tạm KHÔNG bị dời vào wal_cu_")
    ok(not list((sap / "recovery").glob("wal_cu_*")) if (sap / "recovery").exists() else True, "không có thư mục wal_cu_")
    dong(d)


def ca6():
    print("CA 6 — BỘ FILE THẬT của sự cố 31/10/2026 (chỉ có trên máy anh Hùng)")
    nguon = Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo" / "recovery" / "truoc_chua_31-10_134733"
    if not (nguon / "studio.db-wal").exists():
        print("  (bỏ qua: máy này không có bộ file sự cố)")
        return
    thu = HOP / "ca6"
    thu.mkdir()
    for s in ("", "-wal"):
        shutil.copy2(str(nguon / "studio.db") + s, str(thu / "studio.db") + s)
    d, loi = mo_app(thu)
    ok(loi is None and d is not None and bool(d.tu_chua_note), f"tự chữa được đúng ca thật ({loi})")
    if d is not None:
        c = d.conn()
        try:
            qc = c.execute("PRAGMA quick_check").fetchone()[0]
            n = (c.execute("SELECT count(*) FROM jobs").fetchone()[0],
                 c.execute("SELECT count(*) FROM clips").fetchone()[0])
        except sqlite3.Error as e:          # chưa chữa -> ĐỌC lỗi, phải BÁO HỎNG chứ không chết
            qc, n = f"LỖI {e}", (None, None)
        ok(qc == "ok", f"sau khi chữa: kiểm toàn vẹn đạt ({qc[:50]})")
        ok(n == (627, 7577), f"đủ 627 việc + 7.577 clip như file chính lành ({n})")
    dong(d)


def ca5():
    print("CA 5 — quét tĩnh: init_schema gọi lưới TRƯỚC khi mở/áp lược đồ")
    src = (GOC / "app" / "database" / "db.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    fn = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == "init_schema")
    goi = [n.func.attr for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    ok("_cat_wal_cu_neu_hong" in goi and goi.index("_cat_wal_cu_neu_hong") < goi.index("_apply_schema"),
       "init_schema: _cat_wal_cu_neu_hong đứng trước _apply_schema")
    cat = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == "_cat_wal_cu_neu_hong")
    co_xoa = [n for n in ast.walk(cat) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr in ("unlink", "remove", "rmtree")]
    ok(not co_xoa, "lưới KHÔNG BAO GIỜ xoá file (chỉ dời)")


try:
    for f in (ca1, ca2, ca3, ca4, ca5, ca6):
        f()
finally:
    shutil.rmtree(HOP, ignore_errors=True)
print(f"KETQUA: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
