# -*- coding: utf-8 -*-
"""CỔNG 112 — TỰ CHẠY ĐỢT 1b (04/11/2026): nút + bot + trạng thái sống + rà
mọi lối chạy (nhanh/chậm/tắt giữa chừng/bấm nhiều), xong mới nhận tiếp, lỗi
báo lên bot của CHÍNH app này.

Ca: DB hỏng không phá phiếu (1b-V1) · nút Chạy ngay/Dừng/Bỏ qua + trạng thái
tự cập nhật + lệnh bot /tuchay… (1b-V2) · ngưỡng việc chờ + backlog lớn +
hết lượt AI (1b-V3) · quét/nhận treo tự gỡ (1b-V4) · đổi nhịp/khung giữa
chừng, qua nửa đêm ở mức tick, ngủ đông rồi dậy (1b-V5) · báo bot 1 lần/giờ,
hết lỗi báo "đã ổn", không bot thì không đánh dấu (1b-V6) · log gọn (1b-V7).
Thành phần THẬT: DB, quét thư mục, ffprobe, `_pipe_run`, `BotQuanLy.xu_ly`,
`goi_ui`/`chay_hang_ui`. Đồng hồ Tự chạy giả, pool không start (không gọi AI).
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

T = Path(tempfile.mkdtemp(prefix="tu_chay_1b_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
os.environ["BQ_PCBOT_EXCHANGE"] = str(T / "exchange")
os.environ["BQ_DAYCHUYEN_DIR"] = str(T / "daychuyen")
os.environ["BQ_TAT_BOT"] = "1"
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = REPO / "bin" / "ffmpeg.exe"
_SEED = [0]


def lam_video(p: Path, tuoi: float = 70) -> None:
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
    from app.core.pipeline import observe_source
    observe_source(p, now=time.monotonic() - 11)


import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton  # noqa: E402

qapp = QApplication(sys.argv)
from app.ui import theme  # noqa: E402
qapp.setStyleSheet(theme.QSS)
QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: 0
TRA_LOI = {"v": QMessageBox.StandardButton.No}
QMessageBox.question = staticmethod(lambda *a, **k: TRA_LOI["v"])
CANH_BAO: list = []
QMessageBox.warning = staticmethod(lambda *a, **k: CANH_BAO.append(a[2] if len(a) > 2 else ""))

from app.core import pipeline as P  # noqa: E402
from app.core import phieu_dot as PD  # noqa: E402
from app.core import tu_chay as TC  # noqa: E402
from app.core import tele_bot as TB  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402
from app.ui.tu_chay_ui import TuChayUI, mo_hop, doc_khung  # noqa: E402
from app.ai import llm as _llm  # noqa: E402
_llm.is_configured = lambda *a, **k: True

DAT: list[str] = []
HONG: list[str] = []


def ok(dk, nhan, ct=""):
    (DAT if dk else HONG).append(nhan + ("" if dk else f" — {ct}"))
    print(("  ✓ " if dk else "  ✗ ") + nhan + ("" if dk else f"  << {ct}"))


st = app_settings()
st.setValue("pipe_root", str(T / "nguon"))
st.setValue("pipe_recycle_dir", str(T / "thungrac"))
st.sync()


def cau_hinh(**kv):
    base = {"bat": True, "tu": "00:00", "den": "24:00", "phut": 10, "nhom": "__ALL__",
            "nguong_cho": 20, "bo_ngay": ""}
    base.update(kv)
    for k, v in base.items():
        st.setValue(TC.KHOA + k, v)
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
    P._OBSERVATIONS.clear()


def bom(giay=3.0, dk=None):
    t = time.time()
    while time.time() - t < giay:
        TB.chay_hang_ui()
        qapp.processEvents()
        time.sleep(0.01)
        if dk is not None and dk():
            return True
    return dk() if dk else True


def doi_xong(pg, giay=30):
    r = bom(giay, lambda: pg._pipe_dang_quet_n() == 0 and not pg._bot_dang_nhan())
    bom(0.4)
    return r


def trang():
    pg = StudioPage(AppState())
    pg._pipe_report = []
    return pg


class Moi:
    """1 bộ trang + TuChayUI với đồng hồ giả + Telegram giả (ghi sổ)."""

    def __init__(self, gio=None):
        self.pg = trang()
        self.now = [gio or time.time()]
        self.tc = TuChayUI(None, self.pg, self.pg.state, dong_ho=lambda: self.now[0])
        self.tc.o_dia = (True, "")
        self.tele: list = []
        self.gui_ok = True
        self.tc.tele = self._tele
        self.goi: list = []
        goc = self.pg._bot_chay_day_chuyen

        def spy(nhom, tu_dong=False, **k):
            self.goi.append((nhom, tu_dong, k.get("toi_da")))
            return goc(nhom, tu_dong=tu_dong, **k)
        self.pg._bot_chay_day_chuyen = spy
        self.tc.nhip()

    def _tele(self, t, khi_ok=None):
        self.tele.append(t)
        if self.gui_ok and khi_ok:
            khi_ok()
        return True

    def toi(self, giay=601):
        self.now[0] += giay
        return self.tc.nhip()

    def log(self):
        return "\n".join(self.pg._pipe_report)


def dem(ds, chu):
    return sum(chu in x for x in ds)


# ======================================================================
print("1b-V1 — DB HỎNG: không cập nhật phiếu cắt, không báo cáo nhóm sai, báo bot 1 lần")
don_sach()
GOC = T / "daychuyen"
(GOC / "dot").mkdir(parents=True)
pidD, srcD = lam_kenh("KDB", "Mỹ", 0)
phieu = {"schema": 1, "dot_id": "20261104-01", "nhom": "Mỹ", "seq": 1,
         "mo_luc": PD.gio_iso(time.time() - 3600), "trang_thai": "da_dong",
         "dong_luc": PD.gio_iso(time.time() - 60), "ly_do_dong": "xong",
         "kenh": [{"thu_muc": str(srcD), "video": [
             {"id": "yt:1", "trang_thai": "xong", "file": "a.mp4",
              "xong_luc": PD.gio_iso(time.time() - 60)}]}], "kenh_khong_co_video": []}
PD.ghi_nguyen_tu(GOC / "dot" / "20261104-01.json", phieu)
cau_hinh()
m = Moi()
db.corrupt_live = True
for _ in range(2):
    n = m.tc.lan_nen
    m.tc.nhip_60(m.now[0])
    bom(10, lambda: m.tc.lan_nen > n)
    m.now[0] += 60
ok(not (GOC / "cat" / "20261104-01.json").exists(),
   "DB hỏng -> KHÔNG dựng phiếu cắt (không gán bừa khong_co_kenh rồi đóng 'xong')")
ok(dem(m.tele, "cơ sở dữ liệu hỏng") == 1, "báo bot ĐÚNG 1 lần", str(m.tele))
ok(not any("Nhóm «" in t for t in m.tele) and not any("Không có kênh cắt" in t for t in m.tele),
   "không gửi báo cáo nhóm / báo kck nhầm")
db.corrupt_live = False
_goc_nc = PD.ngu_canh_db
PD.ngu_canh_db = lambda root: {"kenh": {}, "so": None, "moi": None, "co_file": None}
n = m.tc.lan_nen
m.tc.nhip_60(m.now[0])
bom(10, lambda: m.tc.lan_nen > n)
PD.ngu_canh_db = _goc_nc
ok(not (GOC / "cat" / "20261104-01.json").exists(),
   "đọc được 0 kênh nào (DB vừa hỏng giữa lượt) -> vẫn KHÔNG ghi phiếu")
n = m.tc.lan_nen
m.tc.nhip_60(m.now[0])
bom(10, lambda: m.tc.lan_nen > n)
ok(dem(m.tele, "đã ổn lại") == 1, "DB lành lại -> báo 'đã ổn lại'", str(m.tele))
ok((GOC / "cat" / "20261104-01.json").exists(), "DB lành -> phiếu cắt dựng bình thường")

print("\n1b-V2 — hộp: nút Chạy ngay / Dừng lượt / Bỏ qua + trạng thái TỰ CẬP NHẬT")
don_sach()
pidA, srcA = lam_kenh("KA", "A", 3)
cau_hinh(nhom="A")
m = Moi()
m.pg._tu_chay = m.tc                          # studio.window() = chính trang khi đứng riêng
dlg = mo_hop(m.pg, exec_=False)
o = dlg._o
nhan = [b.text() for b in dlg.findChildren(QPushButton)]
ok({"Chạy ngay", "Dừng lượt đang chạy", "Bỏ qua hôm nay", "Lưu", "Đóng", "Chọn thư mục"}
   <= set(nhan), "đủ nút bằng CHỮ", str(nhan))
ok(not any(ord(c) > 0x2FFF for t in nhan for c in t), "nhãn nút không emoji")
t0 = o["trang_thai"].text()
ok("Lượt tới" in t0 and "Việc phân tích đang chờ" in t0, "ô trạng thái có lượt tới + việc chờ", t0)
TRA_LOI["v"] = QMessageBox.StandardButton.No
o["ngay"].click()
ok(not m.goi, "Chạy ngay HỎI xác nhận — bấm Không thì không chạy (smoke bấm mọi nút an toàn)")
TRA_LOI["v"] = QMessageBox.StandardButton.Yes
o["ngay"].click()
o["ngay"].click()                              # bấm 2 lần
ok(len(m.goi) == 1, "Chạy ngay bấm 2 lần -> CHỈ 1 lượt", str(m.goi))
bom(1.5)
ok(o["trang_thai"].text() != t0 and "QUÉT" in o["trang_thai"].text() or
   "NHẬN" in o["trang_thai"].text() or "Đã chạy 1 lượt" in o["trang_thai"].text(),
   "ô trạng thái TỰ CẬP NHẬT (không phải nhãn tĩnh)", o["trang_thai"].text())
bom(5, lambda: m.pg._bot_dang_nhan() > 0)
o["dung"].click()
ok(not m.pg._bot_dang_nhan(), "Dừng lượt -> hàng nhận rỗng")
doi_xong(m.pg)
nj = db.query_one("SELECT COUNT(*) n FROM jobs")["n"]
ok(all(p.exists() for p in srcA.glob("*.mp4")) and len(list(srcA.glob("*.mp4"))) == 3,
   f"Dừng lượt không phá gì: video gốc còn đủ, job đã xếp giữ nguyên ({nj})")
o["bo_qua"].click()
ok(TC.doc_cau_hinh(app_settings()).bo_ngay == TC.hom_nay(m.now[0]) and o["bo_qua"].text()
   == "Chạy lại hôm nay", "Bỏ qua hôm nay -> lưu + nút đổi thành 'Chạy lại hôm nay'")
n0 = len(m.goi)
ok(m.toi() == "bo" and len(m.goi) == n0 and m.tc.lich.ly_do_cuoi == "bo_qua_ngay",
   "đã bỏ qua hôm nay -> nhịp tới không chạy")
m.now[0] = datetime.fromtimestamp(m.now[0]).replace(hour=23, minute=59).timestamp() + 120
m.tc.lich.hen = m.now[0] - 1
ok(m.tc.nhip() == "chay", "sang ngày mới -> tự chạy lại")
doi_xong(m.pg)
o["bo_qua"].click()
o["bo_qua"].click()
ok(TC.doc_cau_hinh(app_settings()).bo_ngay == "", "bấm lại -> 'Chạy lại hôm nay' gỡ bỏ qua")
# Lưu: thư mục phiếu không tồn tại -> không lưu
o["thu_muc"].setText(str(T / "khong_co"))
CANH_BAO.clear()
ok(dlg._luu() is False and CANH_BAO and "không tồn tại" in CANH_BAO[0],
   "thư mục phiếu không tồn tại -> báo, KHÔNG lưu", str(CANH_BAO))
o["thu_muc"].setText(str(T))
o["het_ngay"].setChecked(True)
o["phut"].setValue(5)
ok(dlg._luu() is not False and TC.doc_cau_hinh(app_settings()).den == 1440,
   "ô 'đến hết ngày (24:00)' -> lưu 24:00")
ok(TC.doc_cau_hinh(app_settings()).phut == 5 and m.tc.lich.hen is not None and
   m.tc.lich.hen <= m.now[0] + 5 * 60 + 1, "Lưu nhịp mới -> HẸN LẠI NGAY theo nhịp mới",
   f"{m.tc.lich.hen - m.now[0]:.0f}s")

print("\n1b-V2 — lệnh bot /tuchay… (luồng bot thật -> goi_ui -> luồng giao diện)")
don_sach()
pidB, srcB = lam_kenh("KB", "B", 2)
cau_hinh(nhom="B", bat=False)
m = Moi()
TB.dang_ky_ui("tu_chay", m.tc.lenh)
TB.dang_ky_ui("chay_day_chuyen", m.pg._bot_chay_day_chuyen)
TB.dang_ky_ui("dang_nhan", m.pg._bot_dang_nhan)
TB.dang_ky_ui("nhom_rong", m.pg._bot_nhom_rong)
SO: list = []
bot = TB.BotQuanLy("tok", {9}, m.pg.state.pool, gui=lambda cid, t: SO.append(t))


def bot_lenh(text):
    th = threading.Thread(target=bot.xu_ly, args=(9, text))
    th.start()
    t = time.time()
    while th.is_alive() and time.time() - t < 20:
        TB.chay_hang_ui()
        qapp.processEvents()
        time.sleep(0.01)
    th.join(1)
    return SO[-1] if SO else ""


ok("TẮT" in bot_lenh("/tuchay"), "/tuchay hiện trạng thái (đang TẮT)")
ok("đang TẮT" in bot_lenh("/tuchayngay"), "/tuchayngay khi TẮT -> từ chối, nói rõ")
bot_lenh("/tuchaybat")
ok(TC.doc_cau_hinh(app_settings()).bat and not m.goi, "/tuchaybat -> BẬT, KHÔNG chạy ngay")
r1 = bot_lenh("/tuchayngay")
r2 = bot_lenh("/tuchayngay")
ok(len(m.goi) == 1 and "1 lượt" in r1 and "chưa chạy thêm" in r2,
   "bấm Chạy ngay trên bot 2 lần -> 1 lượt, lần 2 nói rõ", f"{m.goi} | {r1} | {r2}")
ok("CŨ" in bot_lenh(f"/tuchayngay t{int(time.time()) - 3600}"), "nút tin cũ hết hạn -> báo, không làm")
doi_xong(m.pg)
bot_lenh("/chayok 0")                         # /chay (tay) lúc vừa tự chạy xong: không trùng
bot._nhom_map = {0: "B"}
bot_lenh("/chayok 0")
doi_xong(m.pg)
nt = db.query_one("SELECT COUNT(*) n FROM pipeline_files WHERE status='taken'")["n"]
ok(nt == 2, "bot /chay ngay sau lượt tự chạy -> không nhận trùng (2 video / 2 dòng sổ)", str(nt))
ok("cả ngày" in bot_lenh("/tuchaygio 06:00-06:00"), "/tuchaygio 06:00-06:00 = cả ngày")
ok("24:00" in bot_lenh("/tuchaygio 06:00-24:00") and TC.doc_cau_hinh(app_settings()).den == 1440,
   "/tuchaygio ...-24:00 = tới hết ngày")
ok("Sai dạng" in bot_lenh("/tuchaygio 25:00-99"), "giờ sai dạng -> báo, không lưu")
hen_cu = m.tc.lich.hen
ok("5 phút" in bot_lenh("/tuchaynhip 5") and m.tc.lich.hen != hen_cu,
   "/tuchaynhip 5 -> hẹn lại ngay", f"{hen_cu} -> {m.tc.lich.hen}")
ok("1 đến 240" in bot_lenh("/tuchaynhip 0"), "nhịp ngoài 1..240 -> báo")
ok("Dừng lượt" in bot_lenh("/tuchaydung"), "/tuchaydung HỎI xác nhận trước")
ok("Đã dừng lượt" in bot_lenh(f"/tuchaydungok t{int(time.time())}"), "xác nhận -> dừng lượt")
bot._nhom_map = {1: "B"}
ok("«B»" in bot_lenh("/tuchaynhomok 1") and TC.doc_cau_hinh(app_settings()).nhom == "B",
   "đổi nhóm qua bot")
ok("đã cũ" in bot_lenh("/tuchaynhomok 77"), "số nhóm lạ -> báo danh sách cũ")
ok("BỎ QUA" in bot_lenh("/tuchayboqua"), "/tuchayboqua")
ok("bỏ" in bot_lenh("/tuchaylai").lower(), "/tuchaylai gỡ bỏ qua")
ok(any(c == "tuchay" for c, _ in TB.LENH_MENU) and "/tuchay" in TB.TRO_GIUP,
   "lệnh mới có trong menu + trợ giúp")
ok(all(not any(ord(c) > 0x2FFF for c in b["text"]) for r in bot._phim_tu_chay()["inline_keyboard"]
       for b in r), "nút bot bằng chữ")
bot_lenh("/tuchaytat")
ok(not TC.doc_cau_hinh(app_settings()).bat, "/tuchaytat -> TẮT")

print("\n1b-V3 — XONG MỚI NHẬN TIẾP: ngưỡng việc chờ + backlog lớn + hết lượt AI")
don_sach()
for i in range(3):
    lam_kenh(f"BL{i}", "BL", 10)
cau_hinh(nhom="BL", nguong_cho=12)
m = Moi()
m.toi()
doi_xong(m.pg, 60)
ids = [r["id"] for r in db.query("SELECT id FROM projects WHERE grp='BL'")]
theo = [db.query_one("SELECT COUNT(*) n FROM pipeline_files WHERE project_id=?", (i,))["n"]
        for i in ids]
ok(sum(theo) == 12 and max(theo) - min(theo) <= 1,
   "backlog 30 video, ngưỡng 12 -> nhận 12, CHIA ĐỀU 3 kênh", str(theo))
ok("GIỮ LẠI 18" in m.log(), "log nói rõ giữ lại 18 cho lượt sau")
ok(m.toi() == "bo" and m.tc.lich.ly_do_cuoi == "nhieu_viec",
   "còn 12 việc chờ >= ngưỡng -> KHÔNG nhận thêm")
db.execute("UPDATE jobs SET status='done' WHERE id IN (SELECT id FROM jobs LIMIT 8)")
ok(m.toi() == "chay" and m.goi[-1][2] == 8, "xong bớt 8 -> nhận tiếp đúng 8 (12 - 4 đang chờ)",
   str(m.goi[-1]))
doi_xong(m.pg, 60)
m.tc.het_luot_ai = True
ok(m.toi() == "bo" and m.tc.lich.ly_do_cuoi == "het_luot_ai", "AI hết lượt kéo dài -> ngừng nhận")
m.toi()
ok(dem(m.tele, "hết lượt kéo dài") == 1, "báo bot 1 lần", str(m.tele))
m.tc.het_luot_ai = False
db.execute("UPDATE jobs SET status='done'")
m.toi()
ok(dem(m.tele, "đã ổn lại") >= 1, "có lại lượt -> báo 'đã ổn lại'", str(m.tele))
doi_xong(m.pg, 60)

print("\n1b-V4 — quét / nhận TREO quá 20 phút: báo bot + tự gỡ cờ")
don_sach()
lam_kenh("KT", "TREO", 0)                    # nhóm có kênh nhưng thư mục trống
cau_hinh(nhom="TREO")
m = Moi()
m.tc.lich.hen = m.now[0] + 10 ** 9           # tách bạch: chỉ đo phần canh treo
m.pg._pipe_dang_quet = 1
m.toi(60)
m.toi(600)
ok(m.pg._pipe_dang_quet_n() == 1, "10 phút -> chưa coi là treo")
m.toi(700)
ok(m.pg._pipe_dang_quet_n() == 0 and dem(m.tele, "đã gỡ cờ") == 1
   and dem(m.tele, "đã ổn lại") == 0, "quá 20 phút -> gỡ cờ + báo bot (chưa báo 'ổn' cùng nhịp)",
   str(m.tele))
m.pg._pipe_intake_q = [(1, "x", "auto", T / "x.mp4")]
m.pg._pipe_intake_cho = True
m.toi(60)
m.toi(600)
ok(len(m.pg._pipe_intake_q) == 1, "hàng nhận đứng im 10 phút -> chưa đụng")
m.toi(700)
ok(not m.pg._pipe_intake_q and dem(m.tele, "đứng im") == 1 and "Dừng lượt" in m.log(),
   "hàng nhận đứng im 20 phút -> dừng lượt + báo", str(m.tele))
m.toi(60)
ok(dem(m.tele, "đã ổn lại") == 2, "nhịp sau hết treo -> báo 'đã ổn lại' (quét + nhận)", str(m.tele))
m.tc.lich.hen = m.now[0]
ok(m.toi(1) == "chay", "không còn kẹt 'dang_nhan' mãi -> nhịp sau chạy được")
doi_xong(m.pg)

print("\n1b-V5 — đổi nhịp / khung giữa chừng · nửa đêm ở mức tick · ngủ đông")
L = TC.LichTuChay()
c60 = TC.CauHinh(bat=True, phut=60)
L.dong_bo(c60, 1000.0)
ok(L.hen == 1000 + 3600, "nhịp 60 -> hẹn +60 phút")
L.dong_bo(TC.CauHinh(bat=True, phut=10), 1200.0)
ok(L.hen == 1000 + 600, "đổi sang 10 phút -> hẹn lại NGAY theo mốc cũ (không đợi hết 60)", str(L.hen))
L.dong_bo(TC.CauHinh(bat=True, phut=1), 5000.0)
ok(L.hen == 5000 + 60, "đổi nhịp khi mốc đã quá -> chạy sau 60 s, KHÔNG chạy tức thì", str(L.hen))
g = datetime.now().replace(hour=21, minute=59, second=0, microsecond=0).timestamp()
cfgN = TC.CauHinh(bat=True, tu=22 * 60, den=6 * 60, phut=1)
kq = []
for dt in (0, 60, 8 * 3600, 8 * 3600 + 60, 8 * 3600 + 120):
    L2 = TC.LichTuChay(hen=g + dt - 1, dang_bat=True, phut=1)
    kq.append(L2.quyet_dinh(cfgN, TC.TinhTrang(), g + dt)[0])
ok(kq == ["bo", "chay", "chay", "bo", "bo"],
   "khung 22:00-06:00: 21:59 bỏ · 22:00 chạy · 05:59 chạy · 06:00 bỏ · 06:01 bỏ", str(kq))
cA = TC.CauHinh(bat=True, tu=6 * 60, den=6 * 60)
ok(all(TC.trong_khung(g + h * 3600, cA.tu, cA.den) for h in range(24)), "từ = đến -> CẢ NGÀY")
ok(TC.trong_khung(datetime.now().replace(hour=23, minute=59).timestamp(), 6 * 60, 1440),
   "đến 24:00 -> 23:59 vẫn trong khung")
ok(doc_khung("06:00-24:00") == ("06:00", "24:00") and doc_khung("24:30-01:00") == (None, None),
   "đọc khung giờ bot: 24:00 hợp lệ ở ô đến, sai thì từ chối")
don_sach()
lam_kenh("KN", "N", 1)
cau_hinh(nhom="N", phut=10)
m = Moi()
m.toi()
doi_xong(m.pg)
n0 = len(m.goi)
m.toi(8 * 3600)                               # ngủ đông 8 tiếng rồi dậy
doi_xong(m.pg)
r_sau = m.toi(15)
ok(len(m.goi) == n0 + 1 and r_sau == "cho", "ngủ đông dậy -> chạy ĐÚNG 1 lượt, không chạy bù dồn",
   f"{len(m.goi) - n0} {r_sau}")
cau_hinh(nhom="N", bat=False)
m.toi()
lam_video(T / "nguon" / "KN" / "moi.mp4")
m.pg._pipe_dang_quet = 0
ok(m.toi() == "tat" and m.toi() == "tat" and len(m.goi) == n0 + 1,
   "tắt giữa chừng -> không lượt nào nữa")

print("\n1b-V6 — báo bot: 1 lần/giờ, hết lỗi báo 'đã ổn', không bot thì không đánh dấu")
cau_hinh(nhom="NhomDaXoa")
m = Moi()
m.toi()
m.toi()
ok(dem(m.tele, "không còn kênh") == 1, "nhóm đã chọn không còn kênh -> báo 1 lần/giờ", str(m.tele))
m.toi(3600)
ok(dem(m.tele, "không còn kênh") == 2, "qua 1 giờ vẫn lỗi -> nhắc lại")
cau_hinh(nhom="N")
m.toi()
ok(dem(m.tele, "đã ổn lại") == 1, "nhóm có kênh lại -> báo 'đã ổn lại'", str(m.tele))
doi_xong(m.pg)
m = Moi()
m.gui_ok = False                              # Telegram lỗi: không đánh dấu -> lượt sau thử lại
_goc_nhan = m.pg._bot_dang_nhan
m.pg._bot_dang_nhan = lambda: 1 / 0
for _ in range(3):
    m.now[0] += 200
    ok_r = m.tc.nhip()
ok(ok_r == "loi" and dem(m.tele, "lỗi trong nhịp") >= 2, "gửi lỗi -> KHÔNG đánh dấu, lượt sau gửi lại",
   str(m.tele))
m.gui_ok = True
m.tele.clear()
for _ in range(4):
    m.now[0] += 200
    m.tc.nhip()
ok(dem(m.tele, "lỗi trong nhịp") == 1, "gửi được -> sau đó 1 lần/giờ (không mỗi 15 s)", str(m.tele))
ok(dem(m.pg._pipe_report, "lỗi trong nhịp") <= 2, "log lỗi cũng gộp 1/giờ")
m.pg._bot_dang_nhan = _goc_nhan
m.tc.nhip()
ok(dem(m.tele, "đã ổn lại") == 1, "hết lỗi -> 'đã ổn lại'")
os.environ["BQ_DAYCHUYEN_DIR"] = str(T / "khong_co_thu_muc")
cau_hinh(nhom="N")
m = Moi()
for _ in range(2):
    n = m.tc.lan_nen
    m.tc.nhip_60(m.now[0])
    bom(10, lambda: m.tc.lan_nen > n)
ok(dem(m.tele, "thư mục phiếu") == 1, "thư mục phiếu không có -> báo bot (1/giờ)", str(m.tele))
os.environ["BQ_DAYCHUYEN_DIR"] = str(GOC)
# không có bot đang chạy -> KHÔNG đánh dấu báo cáo nhóm
for f in (GOC / "cat").glob("*.json"):
    f.unlink()
db.execute("UPDATE projects SET pipe_on=0 WHERE name='KDB'")
TB._bot = None
mR = Moi()
mR.tc.tele = TuChayUI.tele.__get__(mR.tc)     # đường thật (không bot)
n = mR.tc.lan_nen
mR.tc.nhip_60(mR.now[0])
bom(10, lambda: mR.tc.lan_nen > n)
pc = PD.doc_json(GOC / "cat" / "20261104-01.json")[0] or {}
ok(pc.get("trang_thai") == "da_dong" and not pc.get("bao_cao_luc"),
   "không có bot -> phiếu đóng nhưng KHÔNG đánh dấu đã báo", str(pc.get("bao_cao_luc")))
TB._BAO_NHOM.clear()
TB._bot = TB.BotQuanLy("tok", {9}, None, gui=lambda *a: None)
n = mR.tc.lan_nen
mR.tc.nhip_60(mR.now[0])
bom(10, lambda: mR.tc.lan_nen > n)
ok(len(TB._BAO_NHOM) == 1, "có bot rồi -> báo cáo được đưa đi gửi", str(TB._BAO_NHOM))
TB._bot = None
TB._BAO_NHOM.clear()

print("\n1b-V7 — log gọn: lượt tự chạy 1 dòng tổng, lượt bấm tay giữ như cũ")
don_sach()
for i in range(5):
    lam_kenh(f"G{i}", "GON", 0)
cau_hinh(nhom="GON")
m = Moi()
m.toi()
doi_xong(m.pg)
ok(dem(m.pg._pipe_report, "không có video mới để cắt") == 0 and
   dem(m.pg._pipe_report, "Tự chạy: quét 5 kênh") == 1, "tự chạy 5 kênh trống -> 1 dòng tổng",
   str(m.pg._pipe_report[-6:]))
m.pg._pipe_report.clear()
m.pg._pipe_run(nen=True, nhom="GON")
doi_xong(m.pg)
ok(dem(m.pg._pipe_report, "không có video mới để cắt") == 5, "bấm tay -> vẫn từng kênh 1 dòng như cũ")

print("\n" + "=" * 60)
print(f"KETQUA CỔNG 112 tự chạy 1b: ĐẠT {len(DAT)} · HỎNG {len(HONG)}")
for h in HONG:
    print("  HỎNG:", h)
sys.stdout.flush()
os._exit(1 if HONG else 0)
