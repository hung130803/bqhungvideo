"""CỔNG 116 — BỘ ĐIỀU TIẾT GROQ KHÔNG ĐƯỢC CHẾT VÌ "database is locked" (13/11/2026).

Nhật ký tháng 11: 22 dòng "database is locked" giết bước hậu kiểm
("Hậu kiểm chưa hoàn tất: OperationalError: database is locked" /
"LLMError: Gọi groq thất bại: database is locked"). File chung
`DATA_DIR/_cache/groq_dispatch.sqlite3` dùng nhật ký rollback (người ghi chặn
người đọc), timeout 2 s, và `pick_keys` mở 41 kết nối/lượt chọn key.

Cổng chạy SQLite + TIẾN TRÌNH THẬT (khoá file là chuyện giữa các tiến trình,
mock trong một tiến trình là giấu đúng chỗ vỡ), KHÔNG gọi mạng:
  1. journal_mode = wal (bền trong file).
  2. remaining_many == remaining từng key trên 41 key giả (có hạn / hết hạn / không có).
  3. đo thời gian 41 lượt remaining() vs 1 lượt remaining_many().
  4. tiến trình khác GIỮ KHOÁ ĐỘC QUYỀN: remaining/remaining_many trả 0.0 trong
     thời gian có trần, defer/clear không ném lỗi.
  5. tiến trình khác đang GHI (BEGIN IMMEDIATE): người đọc vẫn đọc được ngay (lợi ích WAL).
  6. file bị xoá giữa chừng: tự tạo lại bảng, không ném lỗi.
  7. 7 tiến trình tranh nhau 5 s (_claim/_release/remaining_many/defer/clear): 0 lỗi.
  8. quét AST llm.py: không còn dict-comprehension gọi groq_dispatch.remaining theo key.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
HOP = Path(tempfile.mkdtemp(prefix="bq_test_groqkhoa_"))
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "s.db")
(HOP / "data").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(GOC))
DAT = HONG = 0


def ok(dk, ten, chi=""):
    global DAT, HONG
    DAT, HONG = (DAT + 1, HONG) if dk else (DAT, HONG + 1)
    print(("  ĐẠT  " if dk else "  HỎNG ") + ten + (f" — {chi}" if chi else ""))


def env_con():
    return dict(os.environ, PYTHONIOENCODING="utf-8")


import sqlite3  # noqa: E402
from app.ai import groq_dispatch as g  # noqa: E402

DBF = HOP / "data" / "_cache" / "groq_dispatch.sqlite3"   # không dựa hàm nội bộ: bản CŨ cũng chạy được cổng
KEYS = [f"gsk_GIA_{i:02d}" for i in range(41)]

# ---------------------------------------------------------------- 1. WAL
print("CA 1 — nhật ký WAL")
g.remaining("x", "chat")
c = sqlite3.connect(str(DBF))
mode = c.execute("PRAGMA journal_mode").fetchone()[0]
c.close()
ok(str(mode).lower() == "wal", "journal_mode của file là wal", f"đo: {mode}")

# ---------------------------------------------------------------- 2. remaining_many
print("CA 2 — remaining_many khớp remaining từng key")
for i, k in enumerate(KEYS):
    if i % 3 == 0:
        g.defer(k, "chat", 30 + i)          # còn hạn
    elif i % 3 == 1:
        g.defer(k, "chat", -5)              # đã hết hạn -> 0.0
    # i%3==2: không có dòng nào -> 0.0
g.defer(KEYS[2], "vision", 99)              # scope khác không được rò sang chat
many = g.remaining_many(KEYS, "chat")
le = {k: g.remaining(k, "chat") for k in KEYS}
lech = max(abs(many[k] - le[k]) for k in KEYS)
ok(set(many) == set(KEYS), "trả đủ 41 key", f"{len(many)} key")
ok(lech < 0.5, "giá trị khớp từng key", f"lệch lớn nhất {lech:.3f} s")
ok(all(many[k] == 0.0 for i, k in enumerate(KEYS) if i % 3 != 0),
   "hết hạn / không có -> 0.0, scope khác không rò")
ok(all(many[k] > 25 for i, k in enumerate(KEYS) if i % 3 == 0), "key còn hạn -> > 0")
ok(g.remaining_many([], "chat") == {}, "danh sách rỗng -> {}")
dup = g.remaining_many([KEYS[0], KEYS[0]], "chat")
ok(list(dup) == [KEYS[0]] and dup[KEYS[0]] > 0, "key trùng không làm hỏng")

# ---------------------------------------------------------------- 3. đo thời gian
print("CA 3 — đo 41 lượt remaining() vs 1 lượt remaining_many()")
t = time.perf_counter()
for _ in range(20):
    {k: g.remaining(k, "chat") for k in KEYS}
t_le = (time.perf_counter() - t) / 20 * 1000
t = time.perf_counter()
for _ in range(20):
    g.remaining_many(KEYS, "chat")
t_many = (time.perf_counter() - t) / 20 * 1000
print(f"       41 x remaining(): {t_le:.2f} ms · remaining_many(41): {t_many:.2f} ms")
ok(t_many < t_le, "remaining_many nhanh hơn 41 lượt lẻ", f"{t_le / max(t_many, 1e-6):.1f} lần")

# ---------------------------------------------------------------- 4. khoá độc quyền
print("CA 4 — tiến trình khác giữ KHOÁ ĐỘC QUYỀN")
GIU = r"""
import sqlite3, sys, time
c = sqlite3.connect(sys.argv[1], timeout=5, isolation_level=None)
c.execute("PRAGMA locking_mode=EXCLUSIVE")
c.execute("BEGIN EXCLUSIVE")
c.execute("INSERT OR REPLACE INTO lane VALUES('giu_khoa', NULL, 0)")
open(sys.argv[2], "w").write("ok")
time.sleep(float(sys.argv[3]))
c.execute("COMMIT"); c.close()
"""
giu_py = HOP / "giu_khoa.py"
giu_py.write_text(GIU, encoding="utf-8")
co = HOP / "co_khoa.txt"
p = subprocess.Popen([sys.executable, str(giu_py), str(DBF), str(co), "30"], env=env_con())
t0 = time.time()
while not co.exists() and time.time() - t0 < 15:
    time.sleep(0.05)
ok(co.exists(), "tiến trình giữ khoá đã cầm khoá")
# Tự kiểm bộ dò: một kết nối trần PHẢI bị khoá thật, không thì ca này PASS oan.
bi_khoa = False
cc = sqlite3.connect(str(DBF), timeout=0.2)
try:
    cc.execute("SELECT count(*) FROM cooldown").fetchone()
except sqlite3.OperationalError as e:
    bi_khoa = "locked" in str(e).lower()
finally:
    cc.close()   # quên đóng = giữ handle, ca 6 không xoá được file
ok(bi_khoa, "tự kiểm: kết nối trần THẬT SỰ bị 'database is locked'")
loi = []
t = time.time()
try:
    r1 = g.remaining(KEYS[0], "chat")
except Exception as e:  # noqa: BLE001
    loi.append(repr(e)); r1 = None
d1 = time.time() - t
ok(r1 == 0.0 and d1 < 6.0, "remaining() trả 0.0 trong thời gian có trần", f"{d1:.2f} s, {r1}")
t = time.time()
try:
    rm = g.remaining_many(KEYS, "chat")
except Exception as e:  # noqa: BLE001
    loi.append(repr(e)); rm = None
d2 = time.time() - t
ok(isinstance(rm, dict) and len(rm) == 41 and not any(rm.values()) and d2 < 6.0,
   "remaining_many() trả toàn 0.0 trong thời gian có trần", f"{d2:.2f} s")
t = time.time()
for fn in (lambda: g.defer(KEYS[5], "chat", 10), lambda: g.clear(KEYS[5], "chat", time.time())):
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        loi.append(repr(e))
d3 = time.time() - t
ok(not loi and d3 < 15.0, "defer/clear không ném lỗi khi bị khoá", f"{d3:.2f} s, lỗi: {loi[:2]}")
# Qua llm: pick_keys + soonest_ready_wait không được nổ.
os.environ["GROQ_API_KEYS"] = ",".join(KEYS)
from config import settings  # noqa: E402
type(settings).GROQ_API_KEYS = ",".join(KEYS)
from app.ai import llm  # noqa: E402
loi2 = []
try:
    pk = llm.pick_keys("groq", KEYS, scope="chat")
    llm.soonest_ready_wait("groq", KEYS, scope="chat")
except Exception as e:  # noqa: BLE001
    loi2.append(repr(e)); pk = []
ok(not loi2 and len(pk) == 41, "llm.pick_keys/soonest_ready_wait sống khi file bị khoá", f"{loi2[:1]}")
p.kill(); p.wait()

# ---------------------------------------------------------------- 5. người ghi không chặn người đọc
print("CA 5 — tiến trình khác đang GHI (BEGIN IMMEDIATE): đọc vẫn được ngay")
GHI = r"""
import sqlite3, sys, time
c = sqlite3.connect(sys.argv[1], timeout=5, isolation_level=None)
c.execute("BEGIN IMMEDIATE")
c.execute("INSERT OR REPLACE INTO lane VALUES('dang_ghi', NULL, 0)")
open(sys.argv[2], "w").write("ok")
time.sleep(float(sys.argv[3]))
c.execute("COMMIT"); c.close()
"""
ghi_py = HOP / "dang_ghi.py"
ghi_py.write_text(GHI, encoding="utf-8")
co2 = HOP / "co_ghi.txt"
g.defer(KEYS[0], "chat", 60)   # hạn mới: ca 4 kéo dài > 30 s nên hạn cũ đã hết
p = subprocess.Popen([sys.executable, str(ghi_py), str(DBF), str(co2), "8"], env=env_con())
t0 = time.time()
while not co2.exists() and time.time() - t0 < 15:
    time.sleep(0.05)
t = time.time()
v = g.remaining(KEYS[0], "chat")
d = time.time() - t
ok(v > 0 and d < 0.5, "đọc ra đúng hạn chung trong lúc có người ghi", f"{d * 1000:.1f} ms, {v:.1f} s")
p.kill(); p.wait()

# ---------------------------------------------------------------- 6. file bị xoá
def xoa_file():
    loi_x = []
    for suf in ("", "-wal", "-shm"):
        f = Path(str(DBF) + suf)
        for _ in range(40):
            try:
                f.unlink()
                break
            except FileNotFoundError:
                break
            except OSError as e:   # Windows còn giữ handle vài trăm ms
                loi_x.append(repr(e)[:80]); time.sleep(0.1)
    return [x for x in loi_x if Path(str(DBF)).exists()]


print("CA 6 — file bị xoá giữa chừng")
xoa_loi = xoa_file()
loi = []
try:
    v0 = g.remaining(KEYS[0], "chat")
    g.defer(KEYS[0], "chat", 20)
    v1 = g.remaining_many([KEYS[0]], "chat")[KEYS[0]]
    with g.slot("chat"):
        pass
except Exception as e:  # noqa: BLE001
    loi.append(repr(e)); v0 = v1 = None
ok(not loi and v0 == 0.0 and v1 and v1 > 15, "tự tạo lại bảng, đọc/ghi/slot chạy", f"{loi[:1]} xoá:{xoa_loi[:1]} v0={v0}")

# Xoá giữa hai lượt mà tiến trình đã nhớ "đã tạo bảng" + file mới do người khác tạo RỖNG bảng.
xoa_loi = xoa_file()
sqlite3.connect(str(DBF)).close()   # file tồn tại nhưng KHÔNG có bảng
loi = []
try:
    v2 = g.remaining(KEYS[0], "chat")
    g.defer(KEYS[0], "chat", 20)
except Exception as e:  # noqa: BLE001
    loi.append(repr(e)); v2 = None
ok(not loi and v2 == 0.0, "file có mà mất bảng ('no such table') -> tự tạo lại", f"{loi[:1]} xoá:{xoa_loi[:1]} v2={v2}")

# ---------------------------------------------------------------- 7. tranh chấp nhiều tiến trình
print("CA 7 — 7 tiến trình tranh nhau 5 s")
TRANH = r"""
import json, os, sys, time, traceback
sys.path.insert(0, sys.argv[1])
from app.ai import groq_dispatch as g
keys = [f"gsk_GIA_{i:02d}" for i in range(41)]
het = time.time() + float(sys.argv[3]); n = 0; loi = []
owner = f"{os.getpid()}:x"
while time.time() < het:
    try:
        lan = f"chat#{n % 3}"
        if g._claim(lan, owner):
            g._release(lan, owner)
        g.remaining_many(keys, "chat")
        g.remaining(keys[n % 41], "chat")
        g.defer(keys[n % 41], "chat", 1)
        g.clear(keys[(n + 7) % 41], "chat", time.time())
        n += 1
    except Exception as e:
        loi.append(repr(e)[:200])
open(sys.argv[2] + "." + str(os.getpid()), "w", encoding="utf-8").write(json.dumps([n, loi[:5], len(loi)]))
"""
tr_py = HOP / "tranh.py"
tr_py.write_text(TRANH, encoding="utf-8")
so = HOP / "so_tranh"
ps = [subprocess.Popen([sys.executable, str(tr_py), str(GOC), str(so), "5"], env=env_con())
      for _ in range(7)]
for pp in ps:
    try:
        pp.wait(timeout=90)
    except subprocess.TimeoutExpired:
        pp.kill(); pp.wait()
kq = [json.loads(f.read_text(encoding="utf-8")) for f in HOP.glob("so_tranh.*")]
tong = sum(x[0] for x in kq)
so_loi = sum(x[2] for x in kq)
mau = [m for x in kq for m in x[1]][:2]
print(f"       {len(kq)} tiến trình · {tong} vòng (5 thao tác/vòng) · {so_loi} lỗi")
ok(len(kq) == 7, "đủ 7 tiến trình chạy xong", f"{len(kq)}")
ok(so_loi == 0, "0 lỗi khi tranh chấp", f"{mau}")
# Đo 13/11/2026: mã cũ 197 vòng · mã mới 2.652-2.833 vòng -> ngưỡng 700 ở giữa.
ok(tong > 700, "thông lượng tranh chấp đủ (WAL + 1 truy vấn/loạt)", f"{tong} vòng")

# ---------------------------------------------------------------- 8. AST llm.py
print("CA 8 — quét AST llm.py")
src = (GOC / "app" / "ai" / "llm.py").read_text(encoding="utf-8")
cay = ast.parse(src)


def goi_remaining(node):
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "remaining" and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "groq_dispatch"):
            return True
    return False


comp = [n.lineno for n in ast.walk(cay)
        if isinstance(n, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)) and goi_remaining(n)]
ok(not comp, "không còn comprehension gọi groq_dispatch.remaining theo key", f"dòng {comp}")
fns = {n.name: n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)}
for ten in ("pick_keys", "soonest_ready_wait"):
    co_many = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "remaining_many" for n in ast.walk(fns[ten]))
    ok(co_many, f"{ten} gọi groq_dispatch.remaining_many")
# Tự kiểm bộ dò: dựng lại đúng dòng cũ, bộ dò PHẢI bắt.
cu = ast.parse("shared = {k: groq_dispatch.remaining(k, scope) for k in keys}")
ok(any(isinstance(n, ast.DictComp) and goi_remaining(n) for n in ast.walk(cu)),
   "tự kiểm: bộ dò bắt được dòng mã cũ")

print(f"KETQUA cổng 116: ĐẠT {DAT} · HỎNG {HONG}")
try:
    import shutil
    shutil.rmtree(HOP, ignore_errors=True)
except Exception:  # noqa: BLE001
    pass
sys.exit(1 if HONG else 0)
