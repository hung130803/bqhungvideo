# -*- coding: utf-8 -*-
"""CỔNG 111 — PHIẾU ĐỢT + PHIẾU CẮT (Đợt 1, 04/11/2026; INTEGRATION.md mục 11).

Ca V10–V20 của tài liệu "Quy trình dây chuyền tự động" + luật đọc/ghi chung
(ghi nguyên tử, JSON hỏng giữ bản trước, schema lạ, khớp theo THƯ MỤC). Thành
phần THẬT: DB, quét thư mục, ffprobe, băm, `TuChayUI.nhip_60` chạy luồng nền
`_chay_nen`, `BotQuanLy.soi_mot_lan` (không gửi mạng — `gui` giả).

Bất biến sống còn: phiếu KHÔNG BAO GIỜ là điều kiện bắt buộc — phiếu mất /
hỏng / schema lạ thì video vẫn được cắt theo quét thư mục.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

T = Path(tempfile.mkdtemp(prefix="phieu_dot_"))
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
GOC = T / "daychuyen"
(GOC / "dot").mkdir(parents=True)
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

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

qapp = QApplication(sys.argv)
from app.ui import theme  # noqa: E402
qapp.setStyleSheet(theme.QSS)
QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: 0

from app.core import pipeline as P  # noqa: E402
from app.core import phieu_dot as PD  # noqa: E402
from app.core import tu_chay as TC  # noqa: E402
from app.core import tele_bot as TB  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402
from app.ui.tu_chay_ui import TuChayUI  # noqa: E402
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
for k, v in (("bat", True), ("tu", "00:00"), ("den", "23:59"), ("phut", 10),
             ("nhom", "__ALL__")):
    st.setValue(TC.KHOA + k, v)
st.sync()


def lam_kenh(ten, nhom, files=(), on=1, kieu_duong="/"):
    src = T / "nguon" / ten
    src.mkdir(parents=True, exist_ok=True)
    for f in files:
        lam_video(src / f)
    # DB lưu kiểu D:/video ssmatool/... (gạch xuôi) như máy thật
    luu = str(src).replace("\\", "/") if kieu_duong == "/" else str(src)
    pid = db.execute(
        "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, pipe_mode, "
        "pipe_daily, pipe_src, pipe_hidden) VALUES(?,?,?,?,?,'auto',0,?,0)",
        (ten, str(T / "assets" / ten), nhom, luu, on, luu)).lastrowid
    return int(pid), src


def phieu_tai(dot_id, nhom, kenh, trang_thai="dang_tai", mo=None, dong=None, schema=1):
    mo = time.time() - 3600 if mo is None else mo
    d = {"schema": schema, "dot_id": dot_id, "nhom": nhom, "seq": 1,
         "mo_luc": PD.gio_iso(mo), "han_chot": PD.gio_iso(mo + 3 * 3600),
         "trang_thai": trang_thai, "dong_luc": PD.gio_iso(dong) if dong else None,
         "ly_do_dong": "xong" if trang_thai == "da_dong" else None,
         "kenh": kenh, "kenh_khong_co_video": []}
    PD.ghi_nguyen_tu(GOC / "dot" / f"{dot_id}.json", d)
    return d


def vd(id_, file, tt="xong", xong=None):
    return {"id": id_, "trang_thai": tt, "file": file, "size": 1,
            "xong_luc": PD.gio_iso(time.time() - 600 if xong is None else xong), "loi": None}


def bom(giay=3.0, dk=None):
    t = time.time()
    while time.time() - t < giay:
        qapp.processEvents()
        time.sleep(0.01)
        if dk is not None and dk():
            return True
    return dk() if dk else True


def phieu_cat(dot_id):
    return PD.doc_json(GOC / "cat" / f"{dot_id}.json")[0]


def tt_video(dot_id, id_):
    pc = phieu_cat(dot_id) or {}
    for k in pc.get("kenh") or []:
        for v in k.get("video") or []:
            if v["id"] == id_:
                return v
    return {}


def trang():
    pg = StudioPage(AppState())
    pg._pipe_report = []
    return pg


pg = trang()
NOW = [time.time()]
tc = TuChayUI(None, pg, pg.state, dong_ho=lambda: NOW[0])
TELE: list = []
tc.tele = lambda t, khi_ok=None: (TELE.append(t), khi_ok and khi_ok(), True)[-1]
tc.nhip(NOW[0])                     # nhịp đầu: khởi động sổ hẹn (mở app)


def nen60():
    n = tc.lan_nen
    tc.nhip_60(NOW[0])
    bom(15, lambda: tc.lan_nen > n)


def chay_tu_dong():
    tc.lich.hen = NOW[0] - 1
    r = tc.nhip(NOW[0])
    bom(20, lambda: pg._pipe_dang_quet_n() == 0 and not pg._bot_dang_nhan())
    return r


# ======================================================================
print("V18 — chuẩn hoá đường dẫn (ca mẫu dùng chung với D18)")
nfd = unicodedata.normalize("NFD", "mỹ")
mau = ["D:/video ssmatool/video mỹ/kênh 3",
       "D:\\video ssmatool\\video mỹ\\kênh 3\\",
       f"d:\\VIDEO SSMATOOL\\video {nfd}\\kênh 3"]
kh = {PD.chuan_hoa_duong(m) for m in mau}
ok(len(kh) == 1 and kh == {"d:\\video ssmatool\\video mỹ\\kênh 3"},
   "3 ca mẫu -> CÙNG một khoá", str(kh))
ok(PD.chuan_hoa_duong("D:/a/b") != PD.chuan_hoa_duong("D:/a/c"), "thư mục khác -> khoá khác")
ok(PD.chuan_hoa_duong("D:\\日本\\채널//") == "d:\\日本\\채널", "chữ Nhật/Hàn + nhiều gạch cuối")

print("\nV10 — phiếu ghi xong, file có trong thư mục -> nhận; phiếu cắt dang_lam -> xong + số Part")
pid10, src10 = lam_kenh("K10", "Mỹ", ["v10.mp4"])
phieu_tai("20261104-01", "Mỹ mới", [{"thu_muc": str(src10), "ten_dich": "K10",
                                     "video": [vd("yt:10", "v10.mp4")]}])
nen60()
ok(tt_video("20261104-01", "yt:10").get("trang_thai") == "chua_thay", "chưa nhận -> chua_thay",
   str(tt_video("20261104-01", "yt:10")))
ok(chay_tu_dong() == "chay", "lượt tự chạy")
nen60()
ok(tt_video("20261104-01", "yt:10").get("trang_thai") == "dang_lam", "đã nhận -> dang_lam",
   str(tt_video("20261104-01", "yt:10")))
e = db.query_one("SELECT id, video_id FROM pipeline_files WHERE project_id=?", (pid10,))
for i in range(3):
    db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, status) "
               "VALUES(?,?,?,?,?, 'exported')", (int(e["video_id"]), i, i + 1, 1.0, f"p{i}"))
P.mark_done(int(e["id"]), video_id=int(e["video_id"]), note="xong")
nen60()
v = tt_video("20261104-01", "yt:10")
ok(v.get("trang_thai") == "xong" and v.get("part") == 3, "xuất xong -> xong kèm 3 Part", str(v))
pc = phieu_cat("20261104-01")
ok(pc and pc["schema"] == 1 and "+" in pc["tao_luc"], "phiếu cắt có schema + giờ ISO múi giờ")
ok(not list((src10).glob("*.json")), "KHÔNG ghi JSON nào vào thư mục kênh (collect_wipe)")

print("\nV11 — phiếu xong mà 10 phút không có file, không có trong sổ -> mat_file + báo")
pid11, src11 = lam_kenh("K11", "Mỹ")
phieu_tai("20261104-02", "Mỹ", [{"thu_muc": str(src11), "video": [
    vd("yt:11a", "mat.mp4", xong=time.time() - 11 * 60),
    vd("yt:11b", "moi_xong.mp4", xong=time.time() - 3 * 60)]}])
TELE.clear()
nen60()
ok(tt_video("20261104-02", "yt:11a").get("trang_thai") == "mat_file", "quá 10 phút -> mat_file")
ok(tt_video("20261104-02", "yt:11b").get("trang_thai") == "chua_thay", "mới 3 phút -> chưa kết luận")
ok(sum("MẤT FILE" in t for t in TELE) == 1, "báo mat_file 1 lần", str(TELE))
nen60()
ok(sum("MẤT FILE" in t for t in TELE) == 1, "lượt sau không báo lặp")

print("\nV12 — file đã bị tool cắt dọn sang Thùng rác -> KHÔNG mat_file, giữ xong")
pid12, src12 = lam_kenh("K12", "Mỹ", ["v12.mp4"])
phieu_tai("20261104-03", "Mỹ", [{"thu_muc": str(src12), "video": [
    vd("yt:12", "v12.mp4", xong=time.time() - 20 * 60)]}])
chay_tu_dong()
e = db.query_one("SELECT id, video_id FROM pipeline_files WHERE project_id=?", (pid12,))
db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, status) "
           "VALUES(?,?,?,?,?, 'exported')", (int(e["video_id"]), 0, 1, 1.0, "p"))
P.mark_done(int(e["id"]), video_id=int(e["video_id"]), note="xong")
act, _ = P.delete_or_recycle(src12 / "v12.mp4", "K12", str(T / "thungrac"))
ok(not (src12 / "v12.mp4").exists(), f"gốc đã dọn ({act})")
nen60()
v = tt_video("20261104-03", "yt:12")
ok(v.get("trang_thai") == "xong" and v.get("part") == 1, "giữ xong (không phải mat_file)", str(v))

print("\nV13 — file tải tay, không có trong phiếu nào -> vẫn cắt")
pid13, src13 = lam_kenh("K13", "Mỹ", ["tay.mp4"])
chay_tu_dong()
ok(bool(db.query("SELECT 1 FROM pipeline_files WHERE project_id=? AND file_name='tay.mp4'", (pid13,))),
   "file không phiếu vẫn được nhận")

print("\nV14 — phiếu JSON hỏng / cụt: giữ bản trước, vẫn cắt; hỏng 3 lần thì báo")
pid14, src14 = lam_kenh("K14", "Hàn", ["v14.mp4"])
phieu_tai("20261104-04", "Hàn", [{"thu_muc": str(src14), "video": [vd("yt:14", "v14.mp4")]}])
nen60()
f14 = GOC / "dot" / "20261104-04.json"
f14.write_text(f14.read_text(encoding="utf-8")[:60], encoding="utf-8")   # cụt nửa
TELE.clear()
nen60()
ok(tt_video("20261104-04", "yt:14").get("trang_thai") == "chua_thay",
   "JSON cụt -> giữ bản đọc được lần trước (không coi là rỗng)")
nen60()
ok(not any("hỏng" in t for t in TELE), "hỏng 2 lần -> chưa báo")
nen60()
ok(sum("hỏng 3 lần" in t for t in TELE) == 1, "hỏng 3 lần liên tiếp -> báo", str(TELE))
chay_tu_dong()
ok(bool(db.query("SELECT 1 FROM pipeline_files WHERE project_id=?", (pid14,))),
   "vẫn cắt theo quét thư mục")
pc14 = phieu_cat("20261104-04")
ok(pc14 and pc14["kenh"][0]["video"], "phiếu cắt không bị xoá trắng")

print("\nV15 — schema = 2: bỏ qua phiếu, báo 1 lần, vẫn cắt")
pid15, src15 = lam_kenh("K15", "Hàn", ["v15.mp4"])
phieu_tai("20261104-05", "Hàn", [{"thu_muc": str(src15), "video": [vd("yt:15", "v15.mp4")]}],
          schema=2)
TELE.clear()
nen60()
nen60()
ok(sum("schema 2" in t for t in TELE) == 1, "báo schema lạ ĐÚNG 1 lần", str(TELE))
ok(phieu_cat("20261104-05") is None, "không dựng phiếu cắt từ phiếu không hiểu")
chay_tu_dong()
ok(bool(db.query("SELECT 1 FROM pipeline_files WHERE project_id=?", (pid15,))), "vẫn cắt")

print("\nV16 — video 'tre' xong SAU khi phiếu đã đóng -> cắt, ghi vào phiếu cắt đợt cũ")
pid16, src16 = lam_kenh("K16", "Nhật")
mo16 = time.time() - 4 * 3600
phieu_tai("20261104-06", "Nhật", [{"thu_muc": str(src16), "video": [
    {"id": "yt:16", "trang_thai": "tre", "file": None, "size": None,
     "xong_luc": None, "loi": None}]}], trang_thai="da_dong", mo=mo16, dong=time.time() - 3600)
nen60()
ok(tt_video("20261104-06", "yt:16").get("trang_thai") == "chua_thay", "trễ, chưa có file -> chua_thay")
lam_video(src16 / "tre_ve_sau.mp4")
chay_tu_dong()
nen60()
v = tt_video("20261104-06", "yt:16")
ok(v.get("trang_thai") == "dang_lam" and v.get("file") == "tre_ve_sau.mp4",
   "video trễ về sau -> được cắt + ghi vào phiếu cắt CŨ", str(v))
ok(json.loads((GOC / "dot" / "20261104-06.json").read_text(encoding="utf-8"))["trang_thai"]
   == "da_dong", "phiếu tải (của tool tải) KHÔNG bị app sửa")

print("\nV17 — kênh trong phiếu có pipe_on=0 -> kenh_tat, báo cáo nêu số, không tính lỗi")
pid17, src17 = lam_kenh("K17Nhat", "Nhật", ["n1.mp4"], on=0)
pid17b, src17b = lam_kenh("K17b", "Nhật", ["n2.mp4"])
p17 = phieu_tai("20261104-07", "NHẬT", [
    {"thu_muc": str(src17), "video": [vd("yt:17", "n1.mp4")]},
    {"thu_muc": str(src17b), "video": [vd("yt:17b", "n2.mp4")]}],
    trang_thai="da_dong", dong=time.time() - 60)
chay_tu_dong()
ok(not db.query("SELECT 1 FROM pipeline_files WHERE project_id=?", (pid17,)),
   "kênh tắt -> không cắt")
e = db.query_one("SELECT id, video_id FROM pipeline_files WHERE project_id=?", (pid17b,))
P.mark_done(int(e["id"]), video_id=int(e["video_id"]), note="x")
nen60()
ok(tt_video("20261104-07", "yt:17").get("trang_thai") == "kenh_tat", "ghi kenh_tat")
pc = phieu_cat("20261104-07")
bc = PD.bao_cao_nhom(p17, pc)
ok(pc["trang_thai"] == "da_dong" and " · lỗi " not in bc and "kênh tắt dây chuyền 1" in bc,
   "báo cáo: không tính là lỗi, có nêu số kênh tắt", bc)

print("\nV19 — thư mục không có kênh cắt (kênh 39) -> khong_co_kenh, báo mỗi ngày 1 lần")
hom = time.strftime("%Y%m%d")
phieu_tai(f"{hom}-09", "MỸ", [{"thu_muc": str(T / "nguon" / "kenh 39"),
                                "video": [vd("yt:39", "x.mp4")]}])
TELE.clear()
nen60()
ok(tt_video(f"{hom}-09", "yt:39").get("trang_thai") == "khong_co_kenh", "ghi khong_co_kenh")
ok(sum("Không có kênh cắt" in t for t in TELE) == 1, "báo 1 lần", str(TELE))
nen60()
ok(sum("Không có kênh cắt" in t for t in TELE) == 1, "cùng ngày không báo lại")

print("\nV20 + #28 — cả 2 phiếu đóng: gửi ĐÚNG 1 tin, gộp vào 'HẾT hàng chờ'; mở lại không gửi")
for f in (GOC / "dot").glob("*.json"):
    f.unlink()
for f in (GOC / "cat").glob("*.json"):
    f.unlink()
db.execute("UPDATE jobs SET status='done'")
pid20, src20 = lam_kenh("K20", "Mỹ mới", ["a.mp4"])
p20 = phieu_tai("20261104-10", "Mỹ mới", [{"thu_muc": str(src20), "video": [
    vd("yt:20", "a.mp4"), {"id": "yt:20b", "trang_thai": "loi", "file": None,
                           "xong_luc": None, "loi": "bot chặn"}]}],
    trang_thai="da_dong", dong=time.time() - 60)
chay_tu_dong()
e = db.query_one("SELECT id, video_id FROM pipeline_files WHERE project_id=?", (pid20,))
for i in range(2):
    db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, status) "
               "VALUES(?,?,?,?,?, 'exported')", (int(e["video_id"]), i, i + 1, 1.0, "p"))
P.mark_done(int(e["id"]), video_id=int(e["video_id"]), note="x")
db.execute("UPDATE jobs SET status='done'")
GUI: list = []
bot = TB.BotQuanLy("tok", {1}, None, gui=lambda *a, **k: GUI.append(a))
TB._bot = bot
bot._lan_dau = False
bot._co_viec = True
bot._rong_dem = 1
TB._BAO_NHOM.clear()
nen60()
ok(len(TB._BAO_NHOM) == 1, "báo cáo nhóm được đưa cho bot đúng 1 lần", str(TB._BAO_NHOM))
nen60()
ok(len(TB._BAO_NHOM) == 1, "nhịp sau không đưa trùng")
tin = bot.soi_mot_lan()
het = [t for t in tin if "HẾT hàng chờ" in t or "Hết việc đang chạy" in t]
ok(len(het) == 1 and "Nhóm «Mỹ mới»" in het[0] and "Part mới 2" in het[0]
   and sum("Nhóm «" in t for t in tin) == 1,
   "báo cáo GỘP vào tin HẾT hàng chờ (1 tin, không báo trùng)", str(tin))
ok("tải 1/2" in het[0] and "tải lỗi 1" in het[0], "báo cáo nêu tải x/y + lỗi tải", het[0])
ok(not (phieu_cat("20261104-10") or {}).get("bao_cao_luc"),
   "CHƯA gửi thật -> CHƯA đánh dấu (gửi lỗi mà đã đánh dấu là mất báo cáo)")
# gửi THẬT lần 1: Telegram lỗi (gui trả None, không có gui_ngoai)
bot._gui_ngoai = None
_lan = {"n": 0}


def _gui_gia(cid, text, phim=False, html=True):
    _lan["n"] += 1
    GUI.append((cid, text))
    return None if _lan["n"] == 1 else 99


bot.gui = _gui_gia
bot.gui_tin_soi(tin)
ok(not (phieu_cat("20261104-10") or {}).get("bao_cao_luc") and len(bot._bao_nhom_lai) == 1,
   "Telegram lỗi -> KHÔNG đánh dấu, báo cáo xếp lại để lượt sau gửi", str(bot._bao_nhom_lai))
bot._co_viec = True
bot._rong_dem = 1
tin = bot.soi_mot_lan()
bot.gui_tin_soi(tin)
ok(bool((phieu_cat("20261104-10") or {}).get("bao_cao_luc")) and not bot._bao_nhom_lai,
   "lượt sau gửi được -> mới đánh dấu đã báo")

pgR = trang()                                  # mở lại app
tcR = TuChayUI(None, pgR, pgR.state, dong_ho=lambda: NOW[0])
tcR.tele = lambda t, khi_ok=None: True
nR = tcR.lan_nen
tcR.nhip_60(NOW[0])
bom(15, lambda: tcR.lan_nen > nR)
ok(not TB._BAO_NHOM, "mở lại app -> KHÔNG gửi lại", str([(x["text"][:60]) for x in TB._BAO_NHOM]))
TB._BAO_NHOM.clear()
TB.them_bao_cao_nhom("📦 <b>Nhóm «X»</b>", None)
bot._co_viec = False
tin2 = bot.soi_mot_lan()
ok(sum("Nhóm «X»" in t for t in tin2) == 1, "không có tin HẾT -> báo cáo vẫn gửi riêng 1 tin")
TB._bot = None

print("\nBÁO CÁO NHÓM: nhớ chat đã nhận + thử lại có giới hạn + bản chữ thường")
b2 = TB.BotQuanLy("tok", {1, 2}, None)
NHAN: list = []
LOI_CHAT = {2}


def _g2(cid, text, phim=False, html=True):
    NHAN.append((cid, html, text))
    return None if cid in LOI_CHAT else 7


b2.gui = _g2
DD = []
TB._BAO_NHOM.clear()
TB.them_bao_cao_nhom("📦 <b>Nhóm «A &amp; B»</b>", lambda: DD.append(1))
b2._lan_dau = False
t2 = b2.soi_mot_lan()
b2.gui_tin_soi(t2)
NHAN.clear()
b2.gui_tin_soi(b2.soi_mot_lan())
ok([c for c, _, t in NHAN if "Nhóm «A" in t] == [2], "thử lại CHỈ gửi cho chat còn thiếu (chat 1 không nhận lại)",
   str(NHAN))
for _ in range(TB.BAO_NHOM_THU):
    b2.gui_tin_soi(b2.soi_mot_lan())
tron = [(c, h, t) for c, h, t in NHAN if h is False]
ok(len(tron) == 1 and tron[0][0] == 2 and "<b>" not in tron[0][2] and "A & B" in tron[0][2],
   "quá BAO_NHOM_THU lượt -> gửi 1 bản CHỮ THƯỜNG cho chat thiếu", str(tron))
ok(DD == [1] and not b2._bao_nhom_lai, "rồi đánh dấu + thôi thử (không thử vô hạn)", f"{DD} {b2._bao_nhom_lai}")
n0 = len(NHAN)
b2.gui_tin_soi(b2.soi_mot_lan())
ok(not any("Nhóm «A" in t for _, _, t in NHAN[n0:]), "lượt sau không gửi lại nữa")
dai = "<b>" + "x" * 3895 + "&amp;y</b>"
c = TB.cat_html(dai, 3900)
import re as _re2  # noqa: E402
ok(c.endswith("</b>") and "&am" not in c[-8:] and len(c) <= 3905,
   "cắt 3900 ký tự không cắt giữa thực thể + đóng lại <b>", c[-12:])
c2 = TB.cat_html("a" * 3897 + "<b>zz</b>", 3900)
ok(not c2.endswith("<") and not _re2.search(r"<[^>]*$", c2), "không cắt giữa thẻ", c2[-6:])

print("\n#4 — file KHÔNG đọc được (mark_bad, vẫn nằm trong thư mục) là kết quả CUỐI")
pidB, srcB = lam_kenh("KBad", "B", ["bad.mp4"])
phieu_tai("20261104-15", "B", [{"thu_muc": str(srcB), "video": [vd("yt:b", "bad.mp4")]}],
          trang_thai="da_dong", dong=time.time() - 60)
P.mark_bad(pidB, "bad.mp4", "Không đọc được metadata; giữ nguồn")
nen60()
vb = tt_video("20261104-15", "yt:b")
ok(vb.get("trang_thai") == "loi" and not vb.get("tam") and "file hỏng" in (vb.get("loi") or ""),
   "bad -> loi CUỐI, lý do 'file hỏng/không đọc được'", str(vb))
ok((phieu_cat("20261104-15") or {}).get("trang_thai") == "da_dong",
   "phiếu cắt đóng ngay, không giữ mở 6 giờ")

print("\nHTML — tên chứa & < > không làm Telegram từ chối tin")
import re as _re  # noqa: E402


def html_hop_le(t):
    """parse_mode=HTML: bỏ thẻ app tự đặt (<b> <i>), phần còn lại không được
    còn '<' '>' thô hay '&' không phải thực thể."""
    t2 = _re.sub(r"</?(b|i)>", "", t)
    return "<" not in t2 and ">" not in t2 and not _re.search(r"&(?!amp;|lt;|gt;)", t2)


pidH, srcH = lam_kenh("Tom & Jerry kênh", "Nhóm <A> & B")
phieu_tai("20261104-11", "Nhóm <A> & B", [{"thu_muc": str(srcH), "video": [
    vd("yt:h1", "Tom & Jerry <1>.mp4", xong=time.time() - 20 * 60)]}],
    trang_thai="da_dong", dong=time.time() - 7 * 3600)
phieu_tai(f"{time.strftime('%Y%m%d')}-12", "X", [{"thu_muc": str(T / "nguon" / "A & <B>"),
                                                   "video": [vd("yt:h2", "x.mp4")]}])
st.setValue(TC.KHOA + "kck_ngay", "")
TELE.clear()
TB._BAO_NHOM.clear()
TB._bot = None
GOM = []
_goc_dua = tc._dua_bao_cao
tc._dua_bao_cao = lambda goc, dot, text: GOM.append(text)
tc._da_dua_bao.discard("20261104-11")
nen60()
tc._dua_bao_cao = _goc_dua
ok(any("MẤT FILE" in t for t in TELE) and any("Không có kênh cắt" in t for t in TELE),
   "có đủ tin MẤT FILE + không có kênh cắt", str(TELE))
ok(all(html_hop_le(t) for t in TELE), "mọi tin Telegram là HTML hợp lệ", str(TELE))
ok(any("Tom &amp; Jerry &lt;1&gt;.mp4" in t for t in TELE), "tên file được thoát &amp; &lt; &gt;")
ok(GOM and all(html_hop_le(t) for t in GOM) and "Nhóm &lt;A&gt; &amp; B" in GOM[0],
   "báo cáo nhóm: tên nhóm được thoát", str(GOM))
bd_h = PD.BoDoc()
f_s = T / "hong & x"
f_s.mkdir()
fs = f_s / "20261104-13.json"
fs.write_text('{"schema": 9, "dot_id": "20261104-13"}', encoding="utf-8")
_, bao_s = bd_h.doc(fs)
ok(bao_s and all(html_hop_le("⚠ <b>Phiếu đợt</b>: " + PD._h(x)) for x in bao_s),
   "lời báo phiếu (có đường dẫn) thoát đúng")

print("\n#8 — lỗi TẠM (gốc còn trong thư mục, sẽ thử lại) chưa là kết quả cuối")
pid8, src8 = lam_kenh("K8L", "L", ["l.mp4"])
p8 = phieu_tai("20261104-14", "L", [{"thu_muc": str(src8), "video": [vd("yt:8", "l.mp4")]}],
               trang_thai="da_dong", dong=time.time() - 60)
e8 = P.take_file(pid8, "l.mp4", "h8")
P.mark_error(e8, "gián đoạn — lượt sau thử lại")
nen60()
v8 = tt_video("20261104-14", "yt:8")
ok(v8.get("trang_thai") == "loi" and v8.get("tam") is True, "gốc còn -> loi TẠM", str(v8))
ok((phieu_cat("20261104-14") or {}).get("trang_thai") != "da_dong",
   "lỗi tạm -> phiếu cắt CHƯA đóng")
(src8 / "l.mp4").rename(T / "l_da_doi.mp4")      # gốc bị dời ra _Loi
nen60()
ok((phieu_cat("20261104-14") or {}).get("trang_thai") == "da_dong",
   "gốc đã dời khỏi thư mục -> lỗi CUỐI -> phiếu đóng")

print("\n#23 — ghi nguyên tử + đọc chịu lỗi")
f = T / "nt" / "20261104-99.json"
f.parent.mkdir()
PD.ghi_nguyen_tu(f, {"a": 1})
(f.parent / (f.name + ".tmp")).write_text('{"a": 2, "cụt', encoding="utf-8")  # giết giữa lúc ghi
ok(PD.doc_json(f)[0] == {"a": 1}, "file thật vẫn là bản trước khi tiến trình chết giữa lúc ghi .tmp")
ok([p.name for p in PD.ds_phieu(f.parent)] == ["20261104-99.json"], "danh sách phiếu bỏ qua .tmp")
ok(not (f.name + ".tmp").endswith((".mp4", ".part", ".ytdl")), "file tạm không mang đuôi video/.part")
fh = open(f, "r", encoding="utf-8")
ra = {}


def _ghi():
    try:
        PD.ghi_nguyen_tu(f, {"a": 3})
        ra["ok"] = True
    except OSError as e:
        ra["loi"] = e
th = threading.Thread(target=_ghi)
th.start()
time.sleep(0.5)
fh.close()
th.join(5)
ok(ra.get("ok") and PD.doc_json(f)[0] == {"a": 3},
   "bên kia đang mở đọc -> thử lại, không mất cập nhật", str(ra))
bd = PD.BoDoc()
bd.doc(f)
f.write_text("rác{", encoding="utf-8")
ok(bd.doc(f)[0] == {"a": 3}, "JSON hỏng -> trả bản đọc được lần trước")
old = time.time() - 15 * 86400
cu = T / "cat_cu"
cu.mkdir()
(cu / "20261001-01.json").write_text("{}", encoding="utf-8")
(cu / "ghi_chu.json").write_text("{}", encoding="utf-8")
for x in cu.iterdir():
    os.utime(x, (old, old))
ok(PD.don_phieu_cu(cu) == 1 and (cu / "ghi_chu.json").exists(),
   "dọn phiếu > 14 ngày, CHỈ file đúng mẫu tên")
s = json.dumps(PD.noi_dung_ban(1, 0, 0, False, 1, "x"), ensure_ascii=False)
ok("gsk_" not in s and "token" not in s.lower(), "file bận không chứa key/token")
ok(PD.noi_dung_ban(0, 0, 0, True, 1, "x")["ban"] is True, "đang quét nền -> bận")
ok(PD.noi_dung_ban(0, 0, 3, False, 1, "x")["ban"] is True, "còn file trong hàng nhận -> bận")
ok(PD.noi_dung_ban(5, 1, 0, False, 1, "x", dang_thoat=True)["ban"] is False,
   "thoát êm -> ban=false")

print("\nHỘP CÁT — không đụng thư mục thật")
os.environ.pop("BQ_DAYCHUYEN_DIR")
os.environ.pop("BQ_PCBOT_EXCHANGE")
ok(PD.thu_muc_phieu("") is None and PD.thu_muc_exchange() is None,
   "đang trong test, không đặt env -> KHÔNG trỏ C:\\ProgramData thật")

print("\n" + "=" * 60)
print(f"KETQUA CỔNG 111 phiếu đợt: ĐẠT {len(DAT)} · HỎNG {len(HONG)}")
for h in HONG:
    print("  HỎNG:", h)
sys.stdout.flush()
os._exit(1 if HONG else 0)
