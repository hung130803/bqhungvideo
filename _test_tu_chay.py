# -*- coding: utf-8 -*-
"""CỔNG 110 — TỰ CHẠY DÂY CHUYỀN (Đợt 1, 04/11/2026; INTEGRATION.md mục 5, 12).

Ca V1–V9, V21–V24 (phần ổ đĩa) của tài liệu "Quy trình dây chuyền tự động",
cộng #5 (báo kẹt màn đăng nhập). Thành phần THẬT: DB, quét thư mục, ffprobe,
băm, `_bot_chay_day_chuyen` / `_pipe_run(nen=True)`. Chỉ thay ĐỒNG HỒ của Tự
chạy (đồng hồ giả) và không start pool (job nằm 'pending' — không gọi AI).

Luật được canh:
  - bật ô KHÔNG chạy ngay (smoke bấm mọi ô); tới nhịp gọi ĐÚNG 1 lần hàm của
    nút ▶ với NHÓM ĐÃ LƯU (truyền tường minh), không hộp thoại;
  - lượt tự chạy KHÔNG nhảy màn hình, kể cả khi có lượt bấm tay chạy song song
    (lượt tay vẫn nhảy tới video CỦA NÓ);
  - không treo vào `_poll_tick`; nhịp vẫn chạy khi hộp Dây chuyền mở; hoãn khi
    hộp chọn file hệ thống mở;
  - huỷ là huỷ (V22); restart nhặt lại video AI lỗi trong 1 nhịp (V21);
  - file trạng thái bận do luồng giao diện dựng (V24).
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

T = Path(tempfile.mkdtemp(prefix="tu_chay_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
os.environ["BQ_PCBOT_EXCHANGE"] = str(T / "exchange")
os.environ["BQ_DAYCHUYEN_DIR"] = str(T / "daychuyen")
os.environ["BQ_TAT_BOT"] = "1"
# key GIẢ (không gọi mạng): soonest_ready_wait chỉ xét key có trong settings,
# không có key nào thì nó trả None = "hết lượt" (S3) -> mọi nhịp bị chặn oan.
os.environ["GROQ_API_KEYS"] = "khoa_gia_test_1,khoa_gia_test_2"
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = REPO / "bin" / "ffmpeg.exe"
_SEED = [0]


def lam_video(p: Path, tuoi: float = 70, quan_sat: bool = True) -> None:
    _SEED[0] += 1
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
         "testsrc=size=160x120:rate=10:duration=1", "-f", "lavfi",
         "-i", f"sine=frequency={300 + _SEED[0] * 17}:duration=1",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-metadata", f"comment=seed{_SEED[0]}", "-shortest", str(p)], check=True)
    old = time.time() - tuoi
    os.utime(p, (old, old))
    if quan_sat:
        from app.core.pipeline import observe_source
        observe_source(p, now=time.monotonic() - 11)


import app.queue.jobs  # noqa: F401,E402 - cv2 TRƯỚC Qt (thứ tự main.py)

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

qapp = QApplication(sys.argv)
from app.ui import theme  # noqa: E402
qapp.setStyleSheet(theme.QSS)

from app.core import pipeline as P  # noqa: E402
from app.core import phieu_dot as PD  # noqa: E402
from app.core import tu_chay as TC  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402
from app.ui.tu_chay_ui import TuChayUI, mo_hop  # noqa: E402
from app.ai import llm as _llm  # noqa: E402

DAT: list[str] = []
HONG: list[str] = []


def ok(dk, nhan, ct=""):
    (DAT if dk else HONG).append(nhan + ("" if dk else f" — {ct}"))
    print(("  ✓ " if dk else "  ✗ ") + nhan + ("" if dk else f"  << {ct}"))


# ---- vá mọi hộp thoại: đếm, không chặn ----
SO_HOP = [0]
_goc_exec = QDialog.exec
QDialog.exec = lambda self: (SO_HOP.__setitem__(0, SO_HOP[0] + 1), 0)[1]
QMessageBox.exec = lambda self: (SO_HOP.__setitem__(0, SO_HOP[0] + 1), 0)[1]
for _n in ("question", "information", "warning", "critical"):
    setattr(QMessageBox, _n, staticmethod(
        lambda *a, **k: (SO_HOP.__setitem__(0, SO_HOP[0] + 1), None)[1]))
_llm.is_configured = lambda *a, **k: True

st = app_settings()
(T / "daychuyen").mkdir(exist_ok=True)       # thư mục phiếu (Lưu kiểm tồn tại)
st.setValue("pipe_root", str(T / "nguon"))
st.setValue("pipe_recycle_dir", str(T / "thungrac"))
st.sync()


def lam_kenh(ten, nhom, n=1, on=1):
    src = T / "nguon" / ten
    src.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        lam_video(src / f"{ten}_v{i}.mp4")
    pid = db.execute(
        "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, pipe_mode, "
        "pipe_daily, pipe_src, pipe_hidden) VALUES(?,?,?,?,?,'auto',0,?,0)",
        (ten, str(T / "assets" / ten), nhom, str(src), on, str(src))).lastrowid
    return int(pid), src


def don_sach():
    for t in ("pipeline_files", "jobs", "clips", "videos", "projects"):
        db.execute(f"DELETE FROM {t}")


def bom(giay=3.0, dk=None):
    t = time.time()
    while time.time() - t < giay:
        qapp.processEvents()
        time.sleep(0.01)
        if dk is not None and dk():
            return True
    return dk() if dk else True


def cau_hinh(bat=True, tu="00:00", den="23:59", phut=10, nhom="__ALL__"):
    for k, v in (("bat", bat), ("tu", tu), ("den", den), ("phut", phut), ("nhom", nhom)):
        st.setValue(TC.KHOA + k, v)
    st.sync()


def trang():
    state = AppState()
    pg = StudioPage(state)
    pg._pipe_report = []
    return pg


def gan_spy(pg):
    goi = []
    goc = pg._bot_chay_day_chuyen

    def spy(nhom, tu_dong=False, **k):
        goi.append((nhom, tu_dong))
        return goc(nhom, tu_dong=tu_dong, **k)
    pg._bot_chay_day_chuyen = spy
    nhay = []
    goc_f = pg._pipe_focus
    pg._pipe_focus = lambda pid, vid: (nhay.append((pid, vid)), goc_f(pid, vid))
    return goi, nhay


def doi_nhan_xong(pg, giay=20):  # noqa: E302
    """Đợi quét + nhận xong. Hàng rỗng chưa phải là xong: bước KẾT THÚC lượt
    nhận (chỗ gọi _pipe_focus) còn nằm trong singleShot(0) -> bơm thêm."""
    r = bom(giay, lambda: pg._pipe_dang_quet_n() == 0 and not pg._bot_dang_nhan())
    bom(0.4)
    return r


# ======================================================================
print("RULE + V1 — bật ô không chạy ngay; tới nhịp gọi ĐÚNG 1 lần, nhóm đã lưu")
don_sach()
pidA, srcA = lam_kenh("KenhA", "Mỹ", 2)
pidB, srcB = lam_kenh("KenhB", "Hàn", 1)
cau_hinh(bat=False)
pg = trang()
goi, nhay = gan_spy(pg)
NOW = [time.time()]
tc = TuChayUI(None, pg, pg.state, dong_ho=lambda: NOW[0])
tc.o_dia = (True, "")
ok(tc.nhip() == "tat" and not goi, "công tắc mặc định TẮT -> không làm gì")
cau_hinh(bat=True, nhom="Mỹ", phut=10)
SO_HOP[0] = 0
ok(tc.nhip() == "cho" and not goi, "vừa BẬT -> KHÔNG chạy ngay")
NOW[0] += 9 * 60
ok(tc.nhip() == "cho" and not goi, "9 phút sau vẫn chưa chạy")
NOW[0] += 61
r = tc.nhip()
ok(r == "chay" and goi == [("Mỹ", True)], "tới nhịp -> gọi đúng 1 lần, nhóm 'Mỹ' TƯỜNG MINH", str(goi))
doi_nhan_xong(pg)
taken = [r["project_id"] for r in db.query("SELECT project_id FROM pipeline_files WHERE status='taken'")]
ok(sorted(set(taken)) == [pidA] and len(taken) == 2, "chỉ nhận video nhóm Mỹ (2/2), nhóm Hàn không đụng", str(taken))
ok(SO_HOP[0] == 0, "không mở hộp thoại nào", str(SO_HOP[0]))
ok(not nhay, "lượt tự chạy KHÔNG nhảy màn hình (_pipe_focus không được gọi)", str(nhay))
log = "\n".join((T / "logs").glob("pipeline_*.log").__next__().read_text(encoding="utf-8").splitlines()[-40:])
ok("Tự chạy: chạy dây chuyền" in log, "nhật ký ghi rõ lượt Tự chạy")
ok(tc.nhip() == "cho", "ngay sau lượt chạy -> chờ nhịp kế")

print("\nKHÔNG NHẢY MÀN HÌNH khi lượt tay chạy song song")
don_sach()
P._OBSERVATIONS.clear()
pidA, srcA = lam_kenh("TayA", "A", 1)
pidB, srcB = lam_kenh("TuB", "B", 2)
cau_hinh(bat=True, nhom="B", phut=10)
pg2 = trang()
goi2, nhay2 = gan_spy(pg2)
NOW2 = [time.time()]
tc2 = TuChayUI(None, pg2, pg2.state, dong_ho=lambda: NOW2[0])
tc2.o_dia = (True, "")
tc2.nhip()
NOW2[0] += 601
ok(tc2.nhip() == "chay", "lượt tự chạy nhóm B bắt đầu")
pg2._pipe_run(nen=True, nhom="A")          # bấm tay song song nhóm A
doi_nhan_xong(pg2)
vA = db.query_one("SELECT id FROM videos WHERE project_id=?", (pidA,))
ok(len(nhay2) == 1 and vA and nhay2[0] == (pidA, int(vA["id"])),
   "lượt TAY vẫn nhảy tới ĐÚNG video của nó, không nhảy tới video lượt tự chạy", str(nhay2))
nB = db.query_one("SELECT COUNT(*) n FROM pipeline_files WHERE project_id=? AND status='taken'", (pidB,))["n"]
ok(nB == 2, "video lượt tự chạy vẫn được nhận đủ", str(nB))
# lượt tự chạy thuần sau đó: không nhảy (dù _pipe_focus_target cũ còn)
pg2._pipe_focus_target = (pidA, int(vA["id"]))
lam_video(srcB / "TuB_v9.mp4")
NOW2[0] += 601
nhay2.clear()
tc2.nhip()
doi_nhan_xong(pg2)
ok(not nhay2, "lượt tự chạy thuần không dùng lại đích nhảy cũ", str(nhay2))

print("\nV2 — ngoài khung giờ")
from datetime import datetime  # noqa: E402
g10 = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0).timestamp()
cau_hinh(bat=True, tu="06:00", den="09:00", phut=10, nhom="__ALL__")
pg3 = trang()
goi3, _ = gan_spy(pg3)
N3 = [g10]
tc3 = TuChayUI(None, pg3, pg3.state, dong_ho=lambda: N3[0])
tc3.o_dia = (True, "")
tc3.nhip()
N3[0] += 601
ok(tc3.nhip() == "bo" and not goi3, "10:00 ngoài khung 06-09 -> không chạy")
ok(TC.trong_khung(g10, 22 * 60, 6 * 60) is False and
   TC.trong_khung(g10 - 5 * 3600, 22 * 60, 6 * 60) is True, "khung qua nửa đêm 22-06 tính đúng")

print("\nV3 — lượt trước còn quét / còn hàng nhận -> bỏ nhịp")
cau_hinh(bat=True, phut=10)
pg4 = trang()
goi4, _ = gan_spy(pg4)
N4 = [time.time()]
tc4 = TuChayUI(None, pg4, pg4.state, dong_ho=lambda: N4[0])
tc4.o_dia = (True, "")
tc4.nhip()
N4[0] += 601
pg4._pipe_intake_q = [(1, "x", "auto", Path("x.mp4"))]
ok(tc4.nhip() == "bo" and not goi4, "còn file trong hàng nhận -> bỏ nhịp")
pg4._pipe_intake_q = []
pg4._pipe_quet_tok = {-1: True}          # 1 lượt quét giả đang dở
N4[0] += 601
ok(tc4.nhip() == "bo" and not goi4, "đang quét nền -> bỏ nhịp")
pg4._pipe_quet_tok = {}
N4[0] += 601
ok(tc4.nhip() == "chay" and len(goi4) == 1, "hết bận -> nhịp kế chạy")
doi_nhan_xong(pg4)

print("\nV3' — chồng lượt THẬT (giống CA4 overlap): chỉ MỘT vòng nhận")
for i in range(3):
    lam_kenh(f"V3_{i}", "V3", 3)
cau_hinh(bat=True, nhom="V3", phut=10)
pg3b = trang()
N3b = [time.time()]
tc3b = TuChayUI(None, pg3b, pg3b.state, dong_ho=lambda: N3b[0])
tc3b.o_dia = (True, "")
tc3b.nhip()
N3b[0] += 601
r0 = tc3b.nhip()                         # lượt tự chạy: quét nền
bo_nhip = 0
pg3b._pipe_run(nhom="V3")                # lượt TAY chen giữa lúc quét nền
for _ in range(6):                       # nhịp tự chạy dồn tới trong lúc nhận
    bom(0.05)
    N3b[0] += 601
    bo_nhip += tc3b.nhip() == "bo"
doi_nhan_xong(pg3b, 40)
v3_ids = [r_["id"] for r_ in db.query("SELECT id FROM projects WHERE grp='V3'")]
q = ",".join("?" * len(v3_ids))
taken = db.query_one(f"SELECT COUNT(*) n FROM pipeline_files WHERE status='taken' "
                     f"AND project_id IN ({q})", v3_ids)["n"]
ctx = len({c["entry"] for c in list(pg3b._pipe_cut.values()) + list(pg3b._pipe_by_vid.values())
           if c["pid"] in v3_ids})
n_tong = sum(1 for d_ in pg3b._pipe_report if "tổng nhận" in d_)
ok(r0 == "chay" and bo_nhip >= 1, "nhịp tới lúc còn quét/nhận -> bị BỎ", f"r0={r0} bo={bo_nhip}")
ok(taken == 9 and ctx == 9, "9 file / 9 dòng sổ / 9 ctx — không trùng, không mất", f"{taken}/{ctx}")
ok(n_tong == 1, "chỉ MỘT vòng nhận (log 'tổng nhận' 1 lần)", str(n_tong))

print("\nV4 — hộp Dây chuyền THẬT (_pipeline_dialog, exec modal) đang mở -> vẫn chạy")
cau_hinh(bat=True, phut=10)
KQ4 = {}
_cu_exec = QDialog.exec


def _exec_co_nhip(self):
    self.setModal(True)
    self.show()
    qapp.processEvents()
    if getattr(pg4, "_pipe_dlg", None) is self:
        N4[0] += 601
        KQ4["modal"] = QApplication.activeModalWidget() is self
        KQ4["nhip"] = tc4.nhip()
    self.close()
    return 0


QDialog.exec = _exec_co_nhip
try:
    pg4._pipeline_dialog()
finally:
    QDialog.exec = _cu_exec
ok(KQ4.get("modal") and KQ4.get("nhip") == "chay",
   "_pipeline_dialog đang mở modal -> nhịp vẫn chạy (bài học cổng 14)", str(KQ4))
doi_nhan_xong(pg4)

print("\nV5 — hộp chọn file hệ thống (_modal_busy) -> hoãn, không crash")
N4[0] += 601
pg4._modal_busy = True
n0 = len(goi4)
ok(tc4.nhip() == "hoan" and len(goi4) == n0, "_modal_busy -> HOÃN")
pg4._modal_busy = False
ok(tc4.nhip() == "chay" and len(goi4) == n0 + 1, "hộp đóng -> nhịp kế chạy ngay (không mất lượt)")
doi_nhan_xong(pg4)

print("\nV6 — hàng tạm dừng: không chạy, log 1 lần mỗi giờ")
logs = []
pg4._pipe_log = lambda s, _g=pg4._pipe_log: (logs.append(s), _g(s))
pg4.state.pool.tam_dung("test")
n0 = len(goi4)
for i in range(4):
    N4[0] += 601
    tc4.nhip()
ok(len(goi4) == n0, "tạm dừng -> 4 nhịp không chạy lượt nào")
ok(sum("TẠM DỪNG" in s for s in logs) == 1, "lý do ghi log ĐÚNG 1 lần trong 40 phút",
   str([s for s in logs if "TẠM" in s]))
N4[0] += 3600
tc4.nhip()
ok(sum("TẠM DỪNG" in s for s in logs) == 2, "qua 1 giờ -> nhắc lại 1 lần")
pg4.state.pool.chay_tiep()

print("\nV7 — không có key AI: không chạy, báo Telegram 1 lần")
tele = []
tc4.tele = lambda t, khi_ok=None, khi_xong=None: (tele.append(t), khi_ok and khi_ok(), True)[-1]
_llm.is_configured = lambda *a, **k: False
n0 = len(goi4)
for i in range(3):
    N4[0] += 601
    tc4.nhip()
ok(len(goi4) == n0, "thiếu key -> không chạy")
ok(sum("key AI" in t for t in tele) == 1, "báo Telegram ĐÚNG 1 lần", str(tele))
_llm.is_configured = lambda *a, **k: True

print("\nV8 — file mới 20 giây: lượt này bỏ qua, lượt kế nhận")
don_sach()
P._OBSERVATIONS.clear()
pid8, src8 = lam_kenh("K8", "G8", 0)
f8 = src8 / "moi.mp4"
lam_video(f8, tuoi=20, quan_sat=False)
cau_hinh(bat=True, nhom="G8", phut=10)
pg8 = trang()
gan_spy(pg8)
N8 = [time.time()]
tc8 = TuChayUI(None, pg8, pg8.state, dong_ho=lambda: N8[0])
tc8.o_dia = (True, "")
tc8.nhip()
N8[0] += 601
tc8.nhip()
doi_nhan_xong(pg8)
ok(not db.query("SELECT 1 FROM pipeline_files WHERE project_id=?", (pid8,)),
   "file 20 giây tuổi -> KHÔNG nhận")
old = time.time() - 70
os.utime(f8, (old, old))
from app.core.pipeline import observe_source  # noqa: E402
observe_source(f8, now=time.monotonic() - 11)
N8[0] += 601
tc8.nhip()
doi_nhan_xong(pg8)
ok(bool(db.query("SELECT 1 FROM pipeline_files WHERE project_id=? AND status='taken'", (pid8,))),
   "lượt kế (file đủ tuổi + đứng yên) -> nhận")
ok(tc8.lich.them_kich("20261104-01", "yt:1", N8[0] - 10, N8[0]) and
   tc8.lich.quyet_dinh(TC.doc_cau_hinh(st), tc8.tinh_trang(), N8[0] + 30)[0] == "cho" and
   tc8.lich.quyet_dinh(TC.doc_cau_hinh(st), tc8.tinh_trang(), N8[0] + 36)[0] == "chay",
   "kích theo phiếu bắn đúng xong_luc + 45 giây")
ok(not tc8.lich.them_kich("20261104-01", "yt:1", N8[0], N8[0]),
   "kích khử trùng theo dot_id + id video")
ok(not tc8.lich.them_kich("20261104-01", "yt:2", N8[0] - 3600, N8[0]),
   "xong_luc cũ (mở lại app) -> không kích dồn")

print("\nV9 — file đang lớn dần: không nhận tới khi đứng yên 10 s + mtime >= 30 s")
don_sach()
P._OBSERVATIONS.clear()
pid9, src9 = lam_kenh("K9", "G9", 0)
f9 = src9 / "dang_tai.mp4"
lam_video(f9, tuoi=0, quan_sat=False)
with open(f9, "ab") as fh:
    fh.write(b"\0" * 1000)
ready, busy = P.scan_dir(src9)
ok(f9 in busy and f9 not in ready, "mtime mới -> 'đang tải', không sẵn sàng")
old = time.time() - 70
os.utime(f9, (old, old))
t0 = 1000.0
ok(P.observe_source(f9, now=t0) is False, "quan sát đầu tiên -> chưa nhận")
with open(f9, "ab") as fh:
    fh.write(b"\0" * 1000)
os.utime(f9, (old, old))
ok(P.observe_source(f9, now=t0 + 11) is False, "cỡ đổi giữa 2 lần -> đếm lại từ đầu")
ok(P.observe_source(f9, now=t0 + 15) is False, "mới đứng yên 4 giây -> chưa")
ok(P.observe_source(f9, now=t0 + 22) is True, "đứng yên >= 10 giây -> nhận")

print("\nV21 — tắt app giữa lượt, mở lại: video lỗi AI được làm lại trong 1 nhịp")
don_sach()
P._OBSERVATIONS.clear()
pid21, src21 = lam_kenh("K21", "G21", 1)
cau_hinh(bat=True, nhom="G21", phut=10)
pgA = trang()
pgA._pipe_run(nen=True, nhom="G21")
doi_nhan_xong(pgA)
e = db.query_one("SELECT id FROM pipeline_files WHERE project_id=? AND status='taken'", (pid21,))
ok(bool(e), "lượt đầu nhận video")
# AI lỗi tạm thời -> app gỡ sổ + hẹn thử lại TRONG BỘ NHỚ (rồi app tắt)
P.unmark_taken(int(e["id"]))
db.execute("UPDATE jobs SET status='failed', error='7/8 phần transcript gọi AI lỗi'")
pgB = trang()                              # mở lại app: hẹn trong RAM đã mất
gan_spy(pgB)
N21 = [time.time()]
tcB = TuChayUI(None, pgB, pgB.state, dong_ho=lambda: N21[0])
tcB.o_dia = (True, "")
tcB.nhip()                                 # mở app lúc đã bật: hẹn sau 120 s
N21[0] += TC.LUOT_DAU_GIAY + 1
ok(tcB.nhip() == "chay", "mở lại app -> lượt đầu sau 2 phút")
doi_nhan_xong(pgB)
ok(bool(db.query("SELECT 1 FROM pipeline_files WHERE project_id=? AND status='taken'", (pid21,))),
   "video AI lỗi được nhận lại trong 1 nhịp")
nj = db.query_one("SELECT COUNT(*) n FROM jobs WHERE status='pending'")["n"]
ok(nj == 1, "không chạy trùng (đúng 1 job chờ)", str(nj))

print("\nV22 — huỷ job trong lượt tự chạy: nhịp sau KHÔNG tự nhận lại")
don_sach()
P._OBSERVATIONS.clear()
pid22, src22 = lam_kenh("K22", "G22", 1)
cau_hinh(bat=True, nhom="G22", phut=10)
pg22 = trang()
gan_spy(pg22)
N22 = [time.time()]
tc22 = TuChayUI(None, pg22, pg22.state, dong_ho=lambda: N22[0])
tc22.o_dia = (True, "")
tc22.nhip()
N22[0] += 601
tc22.nhip()
doi_nhan_xong(pg22)
j = db.query_one("SELECT id FROM jobs WHERE status='pending'")
db.execute("UPDATE jobs SET status='canceled', cancel_req=1 WHERE id=?", (int(j["id"]),))
pg22._pipe_poll_cut()                       # nhánh huỷ thật: trả dòng sổ, giữ gốc
ok(not db.query("SELECT 1 FROM pipeline_files WHERE status='taken'"), "huỷ -> trả dòng sổ (như cũ)")
for _ in range(3):
    N22[0] += 601
    tc22.nhip()
    doi_nhan_xong(pg22)
nj = db.query_one("SELECT COUNT(*) n FROM jobs")["n"]
ok(nj == 1 and not db.query("SELECT 1 FROM pipeline_files WHERE status='taken'"),
   "3 nhịp sau: KHÔNG tự nhận lại video đã huỷ", f"jobs={nj}")
ok(any(src22.glob("*.mp4")), "video gốc giữ nguyên trong thư mục")
pg22._pipe_run(nen=True, nhom="G22")         # bấm tay: vẫn làm lại được như cũ
doi_nhan_xong(pg22)
ok(bool(db.query("SELECT 1 FROM pipeline_files WHERE status='taken'")),
   "bấm Chạy TAY vẫn nhận lại (hành vi cũ giữ nguyên)")

print("\nKHOÁ KHÔNG-NHẢY gỡ ở MỌI lối ra (file hỏng ở lượt tự chạy)")
don_sach()
P._OBSERVATIONS.clear()
pidK, srcK = lam_kenh("KHong", "GK", 0)
fk = srcK / "hong.mp4"
fk.write_bytes(b"khong phai video" * 100)
old = time.time() - 70
os.utime(fk, (old, old))
observe_source(fk, now=time.monotonic() - 11)
cau_hinh(bat=True, nhom="GK", phut=10)
pgK = trang()
gan_spy(pgK)
NK = [time.time()]
tcK = TuChayUI(None, pgK, pgK.state, dong_ho=lambda: NK[0])
tcK.o_dia = (True, "")
tcK.nhip()
NK[0] += 601
tcK.nhip()
doi_nhan_xong(pgK)
ok(not (pgK.__dict__.get("_pipe_im_khoa") or set()),
   "file hỏng (mark_bad) ở lượt tự chạy -> khoá không-nhảy đã gỡ",
   str(pgK.__dict__.get("_pipe_im_khoa")))

print("\nV23 (ổ đĩa) — kiểm TỪNG ổ chứa thư mục kênh")
ok(TC.kiem_o_dia([r"D:\a", r"E:\b"], 30, 10,
                 dung_luong=lambda o: {"C:\\": 50, "D:\\": 100, "E:\\": 12}[o])
   == (False, "ổ E: còn 12.0 GB (cần ≥ 30 GB)"), "ổ E dưới 30 GB -> dừng, nói đúng ổ")
ok(TC.kiem_o_dia([r"D:\a"], 30, 10,
                 dung_luong=lambda o: {"C:\\": 8, "D:\\": 100}[o])[0] is False,
   "ổ C dưới 10 GB -> dừng")
ok(TC.kiem_o_dia([r"C:\kenh"], 30, 10, dung_luong=lambda o: 20)[0] is False,
   "thư mục kênh nằm trên C -> C phải >= 30 GB (ngưỡng lớn hơn thắng)")


def _sap(o):
    raise OSError("ổ chưa cắm")
ok(TC.kiem_o_dia([r"Z:\x"], 30, 10, dung_luong=_sap)[0] is True,
   "ổ không đọc được không tính là đầy")
tc4.o_dia = (False, "ổ E: còn 12 GB")
tele.clear()
n0 = len(goi4)
N4[0] += 601
ok(tc4.nhip() == "bo" and len(goi4) == n0, "ổ đầy -> không chạy lượt mới")
ok(any("DỪNG" in t for t in tele), "báo Telegram rõ lý do ổ đầy", str(tele))
tc4.o_dia = None
N4[0] += 601
ok(tc4.nhip() == "hoan", "chưa đo ổ lần nào -> hoãn, không chạy mù")
_lg5 = []
_g5 = pg4._pipe_log
pg4._pipe_log = lambda x: _lg5.append(x)
tc4.lich.da_noi.pop("cho_do_o", None)
for _ in range(3):
    N4[0] += 601
    tc4.nhip()
pg4._pipe_log = _g5
ok(sum("HOÃN" in x for x in _lg5) == 1, "hoãn vì chưa đo được ổ -> NÓI RA 1 lần (không im lặng)",
   str(_lg5))


def _cham(o):
    time.sleep(3)
    return 999
t0 = time.time()
kq5 = TC.kiem_o_dia([r"Q:\mang"], 30, 10, dung_luong=_cham, han=0.3)
ok(kq5[0] is True and time.time() - t0 < 2.5, "ổ mạng treo -> quá hạn thì bỏ qua ổ đó, không treo cả lượt",
   f"{kq5} {time.time() - t0:.1f}s")
tc4.nhip_60(N4[0])
tc4._nen_tu = N4[0] - 10_000          # giả: lượt nền trước treo quá lâu
n_nen = tc4.lan_nen
tc4.nhip_60(N4[0])
ok(bom(15, lambda: tc4.lan_nen > n_nen), "lượt nền treo quá hạn -> nhịp sau đo lại")
the_moi = tc4._nen_the
tc4._nen_dang = True
tc4._nen_xong((True, {"o": (True, ""), "phieu": None, "goc": None}), the_moi - 1)
ok(tc4._nen_dang is True, "lượt nền CŨ về muộn KHÔNG xoá cờ của lượt mới")
tc4._nen_xong((True, {"o": (True, ""), "phieu": None, "goc": None}), the_moi)
ok(tc4._nen_dang is False, "lượt nền đúng thế hệ thì xoá cờ")
import threading as _thd  # noqa: E402
_tha = threading_ev = _thd.Event()


def _treo(o):
    _tha.wait(20)
    return 999


TC._DANG_DO.clear()
n_luong0 = sum(1 for t in _thd.enumerate() if t.name == "bq-do-o")
for _ in range(4):
    TC.kiem_o_dia([r"Q:\chet"], 30, 10, dung_luong=_treo, han=0.1)
n_luong = sum(1 for t in _thd.enumerate() if t.name == "bq-do-o") - n_luong0
ok(n_luong == 2, "ổ chết (Q + C đều treo): 4 lượt đo chỉ có 1 luồng treo MỖI Ổ, không rò luồng",
   str(n_luong))
_tha.set()
tc4.o_dia = (True, "")

print("\nV24 — file trạng thái bận")
_th_dung = []
_goc_nd = PD.noi_dung_ban


def _nd_spy(*a, **k):
    import threading as _t
    _th_dung.append(_t.current_thread() is _t.main_thread())
    return _goc_nd(*a, **k)


PD.noi_dung_ban = _nd_spy
ex = T / "exchange"
_nl = []
_gl = pg4._pipe_log
pg4._pipe_log = lambda x: _nl.append(x)
ok(tc4.ghi_ban(time.time()) is False and not _nl, "chưa có thư mục exchange -> bỏ qua IM LẶNG")
pg4._pipe_log = _gl
ex.mkdir()
don_sach()
pid24, src24 = lam_kenh("K24", "G24", 1)
pg24 = trang()
tc24 = TuChayUI(None, pg24, pg24.state)
tc24.o_dia = (True, "")
tc24.ghi_ban(time.time())
bom(2, lambda: (ex / PD.TEN_FILE_BAN).exists())
d0, _ = PD.doc_json(ex / PD.TEN_FILE_BAN)
ok(isinstance(d0, dict) and d0["ban"] is False and d0["app"] == "bqhungvideo"
   and d0["pid"] == os.getpid(), "hết job -> ban=false", str(d0))
pg24._pipe_run(nen=True, nhom="G24")
doi_nhan_xong(pg24)
tc24.so_ghi_ban = 0
tc24.ghi_ban(time.time())
bom(2, lambda: tc24.so_ghi_ban > 0)
d1, _ = PD.doc_json(ex / PD.TEN_FILE_BAN)
ok(d1["ban"] is True and d1["cho"] >= 1, "có job chờ -> ban=true", str(d1))
ok(PD.doc_iso(d1["cap_nhat"]) and abs(PD.doc_iso(d1["cap_nhat"]) - time.time()) < 30
   and "+" in d1["cap_nhat"], "cap_nhat ISO có múi giờ, mới")
db.execute("UPDATE jobs SET status='done'")
tc24.so_ghi_ban = 0
tc24.ghi_ban(time.time())
bom(2, lambda: tc24.so_ghi_ban > 0)
ok(PD.doc_json(ex / PD.TEN_FILE_BAN)[0]["ban"] is False, "job xong -> ban=false")
# UI treo 5 phút: không nhịp nào chạy -> không ai ghi -> file cũ đi
m0 = (ex / PD.TEN_FILE_BAN).stat().st_mtime
import threading as _th  # noqa: E402
bom(0.5)
ten_luong = [t.name for t in _th.enumerate()]
ok(not any("ban" in n for n in ten_luong if n != "MainThread"),
   "không có luồng nền nào sống để ghi hộ", str(ten_luong))
time.sleep(1.2)                        # không gọi nhịp (giả UI treo)
ok((ex / PD.TEN_FILE_BAN).stat().st_mtime == m0, "UI không chạy nhịp -> file đứng yên (cũ đi)")
cau_hinh(bat=True)
tc24.thoat()
d3, _ = PD.doc_json(ex / PD.TEN_FILE_BAN)
ok(d3["ban"] is False, "thoát êm -> ghi lần cuối ban=false (đồng bộ)")
import inspect  # noqa: E402
import app.ui.tu_chay_ui as _tcu  # noqa: E402
src_ui = inspect.getsource(_tcu.TuChayUI.ghi_ban)
ok(_th_dung and all(_th_dung), "MỌI lần dựng nội dung bận đều ở LUỒNG GIAO DIỆN",
   str(_th_dung))
PD.noi_dung_ban = _goc_nd
cau_hinh(bat=False)
(ex / PD.TEN_FILE_BAN).unlink()
tc24.so_ghi_ban = 0
tc24.nhip_60()
bom(2, lambda: tc24.so_ghi_ban > 0)
ok((ex / PD.TEN_FILE_BAN).exists(), "Tự chạy TẮT vẫn ghi file bận (PCBot biết app bận khi cắt tay)")
ok("noi_dung_ban(now" in src_ui and src_ui.index("noi_dung_ban(now") < src_ui.index("def ghi():"),
   "nội dung bận dựng ở luồng giao diện TRƯỚC khi đẻ luồng ghi")

print("\nKHÔNG TREO VÀO _poll_tick + nhịp rẻ")
import app.ui.studio_page as _sp  # noqa: E402
ok("tu_chay" not in inspect.getsource(_sp.StudioPage._poll_tick),
   "_poll_tick không gọi Tự chạy")
import app.ui.main_window as _mw  # noqa: E402
ok("TuChayUI" in inspect.getsource(_mw.MainWindow._tu_chay_noi), "MainWindow giữ QTimer Tự chạy")
cau_hinh(bat=True, phut=10)
tcp = TuChayUI(None, pg24, pg24.state)
tcp.o_dia = (True, "")
tcp.nhip()
t0 = time.perf_counter()
for _ in range(50):
    tcp.nhip()
ms = (time.perf_counter() - t0) * 1000 / 50
ok(ms < 30, f"1 nhịp (chưa tới giờ) tốn {ms:.2f} ms < 30 ms")

print("\nHỘP CÀI ĐẶT — bật ô KHÔNG chạy gì ngay")
cau_hinh(bat=False)
pgH = trang()
goiH, _ = gan_spy(pgH)
dlg = mo_hop(pgH, exec_=False)
from PyQt6.QtWidgets import QPushButton  # noqa: E402
nhan = [b.text() for b in dlg.findChildren(QPushButton)]
ok(set(nhan) >= {"Lưu", "Đóng", "Chọn thư mục"}, "đủ nút bằng CHỮ", str(nhan))
ok(not any(ord(c) > 0x2FFF for t in nhan for c in t), "nhãn nút không emoji")
dlg._o["bat"].setChecked(True)
dlg._luu()
bom(6, lambda: getattr(dlg, "_ket_luu", None) is not None)
ok(TC.doc_cau_hinh(app_settings()).bat is True, "Lưu -> ghi QSettings tiền tố pipe_auto_")
ok(all(k.startswith("pipe_auto_") for k in app_settings().allKeys() if "auto_" in k and "pipe" in k),
   "khoá đều tiền tố pipe_auto_")
tcH = TuChayUI(None, pgH, pgH.state)
tcH.o_dia = (True, "")
tcH._mo_app = False
ok(tcH.nhip() == "cho" and not goiH, "vừa bật qua hộp -> KHÔNG chạy ngay")

print("\n#5 — kẹt màn đăng nhập > 5 phút: báo đỏ 1 lần (chỉ khi bật Tự chạy)")
from app.core import tele_gac as G  # noqa: E402
gui = []
g = G.Gac("tok", {7}, goi=lambda m, d, **k: gui.append(d.get("text", "")) or [])
ok(g.kiem_ket_dang_nhap(now=0, pid=123, song=False, tu_chay=True) is None, "vừa thấy -> chưa báo")
ok(g.kiem_ket_dang_nhap(now=299, pid=123, song=False, tu_chay=True) is None, "4 phút 59 -> chưa báo")
ok(bool(g.kiem_ket_dang_nhap(now=301, pid=123, song=False, tu_chay=True)) and len(gui) == 1,
   "quá 5 phút -> báo đỏ")
g.kiem_ket_dang_nhap(now=900, pid=123, song=False, tu_chay=True)
ok(len(gui) == 1, "không báo lặp")
g.kiem_ket_dang_nhap(now=901, pid=123, song=True, tu_chay=True)
g.kiem_ket_dang_nhap(now=902, pid=123, song=False, tu_chay=True)
ok(g.kiem_ket_dang_nhap(now=1300, pid=123, song=False, tu_chay=True) is None and len(gui) == 1,
   "bot chính TỪNG sống ở pid này rồi im = app TREO (đã có tin riêng) -> không báo kẹt đăng nhập")
g.kiem_ket_dang_nhap(now=1301, pid=456, song=False, tu_chay=True)
ok(g.kiem_ket_dang_nhap(now=1700, pid=456, song=False, tu_chay=True) and len(gui) == 2,
   "app mở lại (pid mới) rồi kẹt ở màn đăng nhập -> báo lần mới")
g3 = G.Gac("tok", {7}, goi=lambda m, d, **k: [])
_goc_pid = G.app_pid


def _cam_doc():
    raise AssertionError("đọc app_pid khi Tự chạy tắt")


G.app_pid = _cam_doc
try:
    g3._tc_doc = (1e18, False)
    ok(g3.kiem_ket_dang_nhap(now=1e18 + 1) is None, "Tự chạy tắt -> KHÔNG đọc app_pid mỗi vòng")
finally:
    G.app_pid = _goc_pid
g2 = G.Gac("tok", {7}, goi=lambda m, d, **k: gui.append("x") or [])
g2.kiem_ket_dang_nhap(now=0, pid=1, song=False, tu_chay=False)
ok(g2.kiem_ket_dang_nhap(now=9999, pid=1, song=False, tu_chay=False) is None,
   "Tự chạy TẮT -> hành vi như cũ (không báo)")
ok(G.Gac("tok", {7}).kiem_ket_dang_nhap(now=0, pid=0, song=False, tu_chay=True) is None,
   "app tắt hẳn -> không phải ca kẹt đăng nhập")

print("\n" + "=" * 60)
print(f"KETQUA CỔNG 110 tự chạy: ĐẠT {len(DAT)} · HỎNG {len(HONG)}")
for h in HONG:
    print("  HỎNG:", h)
sys.stdout.flush()
os._exit(1 if HONG else 0)
