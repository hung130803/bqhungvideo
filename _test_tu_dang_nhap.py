# -*- coding: utf-8 -*-
"""CỔNG 98 — TỰ ĐĂNG NHẬP + BOT GÁC CỔNG (/moapp từ điện thoại).

Anh Hùng 30/10/2026: "nhỡ đt vào mà mt chưa ấn đn thì có cách nào vô luôn k"
+ "thêm tự mở đăng nhập trên bot". Bot chính chỉ sống SAU đăng nhập, nên:
  (a) `LoginDialog` có mật khẩu ghi nhớ -> đếm ngược rồi TỰ đăng nhập; mất mạng
      -> thử lại giãn dần; SAI mật khẩu -> DỪNG (thử lặp = tự khoá tài khoản);
      gõ vào ô / bấm Huỷ -> thôi đếm.
  (b) `tele_gac` (tiến trình nền riêng) nghe Telegram KHI bot chính không sống:
      /moapp -> app tắt thì MỞ app · app ở màn đăng nhập thì gửi CỜ đăng nhập ·
      bot chính sống thì KHÔNG nghe (không giành getUpdates -> 409).
Thành phần thật: Qt offscreen + LoginDialog thật; chỉ MÁY CHỦ (Supabase,
Telegram) và lệnh MỞ APP là giả — cổng không mở app, không nhắn điện thoại.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass
HC = Path(tempfile.mkdtemp(prefix="bq_tu_dn_"))
os.environ.update(BQ_DATA_DIR=str(HC), BQ_DB_PATH=str(HC / "t.db"),
                  BQ_QSETTINGS_INI=str(HC / "s.ini"), QT_QPA_PLATFORM="offscreen")
import _test_guard  # noqa: F401,E402

DAT = HONG = 0


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}")
    else:
        HONG += 1
        print(f"  HỎNG {ten}  {chi_tiet}")


from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402
_APP = QApplication.instance() or QApplication([])
import traceback as _tb
LOI_SLOT = []
# lỗi trong slot Qt ở app thật = SẬP app; ở đây đếm lại để chấm HỎNG
sys.excepthook = lambda *a: (LOI_SLOT.append(1), print("EXC:", "".join(_tb.format_exception(*a)), flush=True))

from app.core import auth, tele_gac  # noqa: E402
from app.ui import login as L  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402


def cho(dk, giay=10.0):
    han = time.time() + giay
    while time.time() < han:
        _APP.processEvents()
        if dk():
            return True
        time.sleep(0.02)
    return dk()


def dat_mk(co: bool):
    s = app_settings()
    s.setValue("save_user", "hung")
    if co:
        s.setValue("save_pass", L.LoginDialog._enc("mk-thu"))
    else:
        s.remove("save_pass")
    s.sync()


# máy chủ tài khoản GIẢ: kịch bản theo lượt
KICH = []
GOI = []


def auth_gia(u, p):
    GOI.append((u, p))
    kq = KICH.pop(0) if KICH else "ok"
    if kq == "mang":
        raise auth.AuthError("Không kết nối được máy chủ")
    if kq == "sai":
        return None
    return {"username": u, "role": "admin"}


auth.login = auth_gia
import app.auth_config as AC  # noqa: E402
AC.is_configured = lambda: True
L.TU_DANG_NHAP_GIAY = 1
_SONG = []
_LoginGoc = L.LoginDialog


def _moi(*a, **k):
    # app thật chỉ có MỘT màn đăng nhập; ở đây đóng màn cũ để nó không ăn cờ
    for x in _SONG:
        try:
            x.reject()
        except RuntimeError:
            pass
    _SONG.clear()
    x = _LoginGoc(*a, **k)
    _SONG.append(x)
    return x


print("MỤC 1 — tự đăng nhập")
dat_mk(True); KICH[:] = ["ok"]; GOI.clear()
d = _moi()
ok(d._dem.isActive() and not d.huy_tu.isHidden(), "1a có mật khẩu ghi nhớ -> đếm ngược + nút Huỷ")
ok(cho(lambda: d.result() == QDialog.DialogCode.Accepted, 8), "1b hết đếm ngược -> TỰ đăng nhập thành công")
ok(GOI == [("hung", "mk-thu")], "1c gửi ĐÚNG tài khoản/mật khẩu đã ghi nhớ", str(GOI))
log = list((HC / "logs").glob("dang_nhap_*.log"))
nd = log[0].read_text(encoding="utf-8") if log else ""
ok("THÀNH CÔNG" in nd and "mk-thu" not in nd, "1d ghi log thành công, KHÔNG ghi mật khẩu")

dat_mk(False); GOI.clear()
d = _moi()
ok(not d._dem.isActive() and d.huy_tu.isHidden(), "1e KHÔNG ghi nhớ -> không tự đăng nhập")
cho(lambda: False, 1.5)
ok(GOI == [], "1f ... và không gọi máy chủ")

print("MỤC 2 — huỷ")
dat_mk(True); GOI.clear()
L.TU_DANG_NHAP_GIAY = 3
d = _moi(); d.huy_tu.click()
cho(lambda: False, 3.5)
ok(GOI == [] and d.result() != QDialog.DialogCode.Accepted, "2a bấm Huỷ -> không đăng nhập")
d = _moi(); d.username.textEdited.emit("x")
cho(lambda: False, 3.5)
ok(GOI == [] and not d._dem.isActive(), "2b gõ vào ô -> thôi tự đăng nhập")
os.environ["BQ_TU_DANG_NHAP"] = "0"
d = _moi()
ok(not d._dem.isActive(), "2c BQ_TU_DANG_NHAP=0 tắt hẳn")
del os.environ["BQ_TU_DANG_NHAP"]
L.TU_DANG_NHAP_GIAY = 1

print("MỤC 3 — mất mạng / sai mật khẩu")
KICH[:] = ["mang"]; GOI.clear()
d = _moi()
ok(cho(lambda: len(GOI) == 1 and d.btn.isEnabled(), 6), "3a lượt 1 lỗi mạng")
ok(d._dem.isActive() and d._lan_thu == 1 and 10 <= d._con_lai <= 15,
   "3b lỗi mạng -> HẸN THỬ LẠI ~15s (không bỏ cuộc)", f"{d._lan_thu} {d._con_lai}")
d._con_lai = 1                     # tua nhanh
ok(cho(lambda: d.result() == QDialog.DialogCode.Accepted, 6), "3c thử lại -> vào được")
KICH[:] = ["sai"]; GOI.clear()
d = _moi()
ok(cho(lambda: len(GOI) == 1 and d.btn.isEnabled(), 6), "3d lượt sai mật khẩu")
cho(lambda: False, 2.5)
ok(len(GOI) == 1 and not d._dem.isActive() and d.result() != QDialog.DialogCode.Accepted,
   "3e SAI mật khẩu -> DỪNG, không thử lặp", str(len(GOI)))

print("MỤC 4 — lệnh đăng nhập từ điện thoại (cờ)")
dat_mk(True); L.TU_DANG_NHAP_GIAY = 3
d = _moi(); d.huy_tu.click(); GOI.clear(); KICH[:] = ["ok"]
tele_gac.file_co_dang_nhap().write_text("1", encoding="utf-8")
ok(cho(lambda: d.result() == QDialog.DialogCode.Accepted, 8), "4a cờ /moapp -> đăng nhập dù đã Huỷ đếm")
d_4a = d
ok(not tele_gac.file_co_dang_nhap().exists(), "4b cờ bị xoá sau khi dùng (không đăng nhập lặp)")
dat_mk(False); GOI.clear()
d = _moi()
tele_gac.file_co_dang_nhap().write_text("1", encoding="utf-8")
cho(lambda: False, 3)
ok(GOI == [] and "ghi nhớ" in d.note.text(), "4c chưa có mật khẩu ghi nhớ -> báo rõ, không gọi máy chủ")

# đăng nhập xong main.py vẫn GIỮ dialog -> cờ đến sau đó KHÔNG được làm sập
da_xong = d_4a  # dialog vừa đăng nhập ở 4a (đã accept)
tele_gac.file_co_dang_nhap().write_text("1", encoding="utf-8")
cho(lambda: False, 3)
ok(not da_xong._soi_co.isActive() and not da_xong._dem.isActive(),
   "4d đăng nhập xong -> tắt hết bộ đếm của màn đăng nhập")
tele_gac.file_co_dang_nhap().unlink(missing_ok=True)
print("MỤC 5 — bot gác cổng")
GUI, MO = [], []


def goi_gia(m, data, timeout=20):
    if m == "sendMessage":
        GUI.append(data["text"])
    return []


g = tele_gac.Gac("tok", {111}, goi=goi_gia, mo_app=lambda: MO.append(1))
g.CHO = 0
tele_gac.CHO_LEN_GIAY = 0
for f in (tele_gac.file_song(), HC / "app.lock", tele_gac.file_co_dang_nhap()):
    f.unlink(missing_ok=True)
g.xu_ly(111, "/moapp")
ok(MO == [1] and any("MỞ app" in x for x in GUI), "5a app TẮT -> /moapp MỞ app", str(GUI))
han = time.time() + 6
while time.time() < han and not any("chưa lên" in x for x in GUI):
    time.sleep(0.1)
ok(any("chưa lên" in x for x in GUI), "5a' quá hạn mà bot chính chưa lên -> BÁO lý do, không im lặng")
GUI.clear(); MO.clear()
(HC / "app.lock").write_text(f"{os.getppid()}\nBQ\nmay\n", encoding="utf-8")
ok(tele_gac.app_pid() == os.getppid(), "5b đọc PID app từ app.lock (tiến trình còn sống)")
g._dang_cho = False
g.xu_ly(111, "/moapp")
ok(MO == [] and tele_gac.file_co_dang_nhap().exists() and any("Đăng nhập hộ" in x for x in GUI),
   "5c app ở màn đăng nhập -> gửi CỜ, không mở app thứ 2")
tele_gac.file_co_dang_nhap().unlink()
tele_gac.file_song().write_text("1", encoding="utf-8")
GUI.clear()
g.xu_ly(111, "/moapp")
ok(MO == [] and not tele_gac.file_co_dang_nhap().exists() and any("rồi" in x for x in GUI),
   "5d bot chính đang sống -> không làm gì")
GUI.clear()
g.xu_ly(999, "/moapp")
ok(GUI == [] and MO == [], "5e chat LẠ -> không làm gì")
(HC / "app.lock").write_text("999999999\nBQ\n", encoding="utf-8")
ok(tele_gac.app_pid() == 0, "5f app.lock của PID đã chết -> coi là app tắt")

# vòng nghe: bot chính sống -> KHÔNG gọi getUpdates (không giành 409)
GOI_M = []


def goi_dem(m, data, timeout=20):
    GOI_M.append((m, dict(data)))
    if m == "getUpdates" and data.get("timeout"):
        return [{"update_id": 41, "message": {"chat": {"id": 111}, "text": "/trangthai"}}]
    return None


class _Dung(Exception):
    pass


_ngu_goc = tele_gac.time.sleep


def ngu_dung(s):
    raise _Dung()


tele_gac.time.sleep = ngu_dung
g2 = tele_gac.Gac("tok", {111}, goi=goi_dem, mo_app=lambda: None)
tele_gac.file_song().write_text("1", encoding="utf-8")
try:
    g2.chay()
except _Dung:
    pass
ok(not any(m == "getUpdates" for m, _ in GOI_M), "5g bot chính sống -> gác cổng KHÔNG nghe")
tele_gac.file_song().unlink()
g2.mot_vong()
xn = [d for m, d in GOI_M if m == "getUpdates"]
ok(len(xn) == 2 and xn[1].get("offset") == 42 and xn[1].get("timeout") == 0,
   "5h xử lý xong XÁC NHẬN offset ngay (bot chính không nhận lại /moapp cũ)", str(xn))
ok(any(m == "sendMessage" for m, _ in GOI_M), "5i /trangthai có trả lời")
tele_gac.time.sleep = _ngu_goc
ok(tele_gac.POLL_GIAY <= 8, "5j long-poll NGẮN để nhường bot chính nhanh")

print("MỤC 6 — bot chính <-> gác cổng")
from app.core import tele_bot  # noqa: E402
tele_bot._nhip_song()
ok(tele_gac.bot_chinh_song(), "6a bot chính ghi nhịp sống")
b = tele_bot.BotQuanLy("tok", {111}, None, gui=lambda c, t: GUI.append(t))
b.dung()
ok(not tele_gac.file_song().exists(), "6b bot chính tắt -> xoá nhịp, gác cổng nhận việc ngay")
GUI.clear(); b2 = tele_bot.BotQuanLy("tok", {111}, None, gui=lambda c, t: GUI.append(t))
b2.xu_ly(111, "/moapp")
ok(GUI and "ĐANG CHẠY" in GUI[-1], "6c bot chính nhận /moapp -> báo đang chạy (không ra trợ giúp)")
ok("/moapp" in tele_bot.TRO_GIUP, "6d trợ giúp có /moapp")
ok(tele_gac.bat_neu_chua() is False, "6e đang test (BQ_DATA_DIR) -> KHÔNG bật tiến trình gác cổng")
ok(tele_gac.giu_khoa() and tele_gac.dang_chay(), "6f khoá 1-gác-cổng giữ được")
import subprocess  # noqa: E402
r = _test_guard.chay_that([sys.executable, "-c",
                           "import sys;sys.path.insert(0,r'%s');"
                           "from app.core import tele_gac as g;print(g.giu_khoa(), g.dang_chay())" % ROOT],
                          capture_output=True, text=True, timeout=60) \
    if hasattr(_test_guard, "chay_that") else None
ok(r is not None and r.stdout.strip() == "False True",
   "6g tiến trình THỨ HAI không lấy được khoá (chỉ 1 gác cổng/máy)",
   (r.stdout + r.stderr)[-200:] if r else "")

print("MỤC 7 — cửa vào trong bản .exe")
from app.core import self_check  # noqa: E402
import inspect  # noqa: E402
src = inspect.getsource(self_check.run)
ok('output == "--gac"' in src.split("BQ_DATA_DIR")[0], "7a self_check.run('--gac') rẽ vào gác cổng TRƯỚC chốt cách ly")
main_src = (ROOT / "main.py").read_text(encoding="utf-8")
ok("len(sys.argv) == 3 and sys.argv[1] == '--self-check'" in main_src,
   "7b main.py (đã đóng gói) có sẵn cửa --self-check 3 tham số")
ok(tele_gac.lenh_gac()[-2:] == ["--self-check", "--gac"], "7c lệnh bật gác cổng đúng 3 tham số")

print("MỤC 9 — menu lệnh + bàn phím nút (khỏi gõ)")
import re as _re  # noqa: E402
ok(all(_re.fullmatch(r"[a-z0-9_]{1,32}", c) and 3 <= len(d) <= 256
       for c, d in tele_bot.LENH_MENU), "9a menu lệnh đúng luật Telegram (a-z0-9_, mô tả 3-256)")
nut = [b["text"] for hang in tele_bot.BAN_PHIM["keyboard"] for b in hang]
ok(sorted(nut) == sorted(tele_bot.NUT_DUOI), "9b mọi nút trên bàn phím đều có lệnh tương ứng")
GUI.clear()
b3 = tele_bot.BotQuanLy("tok", {111}, None, gui=lambda c, t: GUI.append(t))
tele_bot.bao_cao_loi = lambda: "BAO_CAO_LOI_GIA"
tele_bot.xoa_dem()
b3.xu_ly(111, "❗ Lỗi")
ok(GUI and "BAO_CAO_LOI_GIA" in GUI[-1], "9c bấm nút '❗ Lỗi' -> chạy đúng /loi", str(GUI[-1:]))
GUI.clear(); b3.xu_ly(111, "🔓 Mở app")
ok(GUI and "ĐANG CHẠY" in GUI[-1], "9d nút 'Mở app' tới đúng lệnh /moapp")
GUI.clear(); MO.clear(); g._dang_cho = False
tele_gac.file_song().unlink(missing_ok=True); (HC / "app.lock").unlink(missing_ok=True)
g.xu_ly(111, "🔓 Mở app")
ok(MO == [1], "9e app tắt, bấm nút 'Mở app' ở bot gác cổng -> mở app")
DK = []
tele_bot.dang_ky_menu(lambda m, d: DK.append(m))
ok(DK == ["setMyCommands", "setChatMenuButton"], "9f đăng ký menu '/' với Telegram")
tele_bot.dang_ky_menu(lambda m, d: (_ for _ in ()).throw(RuntimeError("x")))
ok(True, "9g đăng ký menu lỗi -> không ném (không làm hỏng bot)")
print("MỤC 10 — /chay xem trước TỪNG KÊNH trước khi xác nhận")
from app.database.db import db  # noqa: E402
goc = HC / "trung_chuyen"
cu = time.time() - 3600


def kenh(ten, nhom, bat=1, video=0, dang_tai=0, an=0):
    db.execute("INSERT INTO projects(name,assets_dir,grp,pipe_on,pipe_hidden) "
               "VALUES(?,?,?,?,?)", (ten, "", nhom, bat, an))
    d = goc / ten
    d.mkdir(parents=True, exist_ok=True)
    for i in range(video):
        f = d / f"v{i}.mp4"
        f.write_bytes(b"x" * 10)
        os.utime(f, (cu + i, cu + i))
    for i in range(dang_tai):
        (d / f"tai{i}.mp4").write_bytes(b"x")       # mới ghi = đang tải
    return d


dA = kenh("KenhA", "Mỹ", video=3, dang_tai=1)
kenh("KenhB", "Mỹ", video=0)
kenh("KenhC", "Mỹ", bat=0, video=5)               # TẮT -> không tính
kenh("KenhD", "Nhật", video=4)                    # nhóm khác -> không tính
kenh("KenhE", "Mỹ", video=2, an=1)                # ẩn -> không tính
pidB = db.query_one("SELECT id FROM projects WHERE name='KenhB'")["id"]
db.execute("INSERT INTO pipeline_files(project_id,file_name,status,taken_at,done_at) "
           "VALUES(?,?,'done',datetime('now'),datetime('now'))", (pidB, "z.mp4"))
bay = {os.path.normcase(os.path.abspath(str(dA / "v0.mp4")))}
x = tele_bot.xem_truoc_nhom("Mỹ", str(goc), bay)
ok(x["cho"] == 2 and x["dang"] == 1 and x["tai"] == 1 and x["kenh_co"] == 1,
   "10a đếm KHỚP cột 'Chờ cắt': 3 video - 1 đang chạy dở = 2 chờ, 1 đang tải",
   str({k: x[k] for k in ("cho", "dang", "tai", "kenh_co")}))
ok([k["ten"] for k in x["kenh"]] == ["KenhA", "KenhB"] and x["tat"] == ["KenhC"],
   "10b chỉ kênh BẬT trong ĐÚNG nhóm; kênh tắt liệt kê riêng; kênh ẩn/nhóm khác không tính")
msg = tele_bot.bao_cao_xem_truoc("Nhóm «Mỹ»", x)
ok("Sẽ cắt <b>2 video</b>" in msg and "KenhA: <b>2</b> chờ" in msg
   and "Đã làm hết hôm nay" in msg and "KenhB (1)" in msg and "Kênh TẮT" in msg,
   "10c tin xem trước nói rõ kênh nào có video / đã làm xong / tắt", msg)
x2 = tele_bot.xem_truoc_nhom("Mỹ", "", set())
ok(all(k["hong"] == "chưa đặt thư mục" for k in x2["kenh"]) and x2["cho"] == 0,
   "10d chưa đặt thư mục gốc -> báo 'chưa đặt thư mục', không coi là 0 video im lặng")
msg2 = tele_bot.bao_cao_xem_truoc("Nhóm «Mỹ»", x2)
ok("không đọc được thư mục" in msg2, "10e kênh hỏng thư mục được liệt kê riêng")
xa = tele_bot.xem_truoc_nhom("__ALL__", str(goc), set())
ok(xa["cho"] == 7, "10f TẤT CẢ nhóm = 3 (A) + 4 (D)", str(xa["cho"]))
dai = {"kenh": [{"ten": f"Kenh{i:03d}", "cho": 1, "dang": 0, "tai": 0, "xong": 0,
                 "loi": 0, "hong": ""} for i in range(400)], "tat": [], "an": 0,
       "cho": 400, "dang": 0, "tai": 0, "kenh_co": 400, "xong": 0, "loi": 0}
ok(len(tele_bot.bao_cao_xem_truoc("x", dai)) <= 3700, "10g 400 kênh -> tin vẫn dưới giới hạn Telegram")

# luồng bấm: chọn nhóm -> tin xem trước + nút "Chạy N video"; xác nhận -> nhắc lại số
GUI2 = []
b4 = tele_bot.BotQuanLy("tok", {111}, None)
b4.gui = lambda c, t, phim=False: (GUI2.append((t, phim)), 1)[1]
tele_bot._UI_FN["nen_xem_truoc"] = lambda: {"ok": True, "root": str(goc), "dang_bay": []}
tele_bot.goi_ui = (lambda ten, *a, cho=15.0: tele_bot._UI_FN[ten](*a)
                   if ten in tele_bot._UI_FN else {"ok": False})
b4.xu_ly(111, "/chay")
ok(GUI2 and "xem từng kênh" in GUI2[-1][0], "10h /chay -> danh sách nhóm, có giải thích bước xem trước")
k_my = [k for k, g in b4._nhom_map.items() if g == "Mỹ"][0]
b4.xu_ly(111, f"/chay {k_my}")
t, ph = GUI2[-1]
nut = [b["text"] for b in ph["inline_keyboard"][0]]
ok("KenhA: <b>3</b> chờ" in t and nut[0] == "✅ Chạy 3 video",
   "10i chọn nhóm -> hiện từng kênh + nút 'Chạy 3 video'", f"{nut}")
tele_bot._UI_FN["chay_day_chuyen"] = lambda g: {"ok": True, "kenh": 2}
b4._bat_theo_doi = lambda c: None
b4.xu_ly(111, f"/chayok {k_my}")
ok("sẽ cắt <b>3 video</b> ở 1 kênh" in GUI2[-1][0], "10j xác nhận -> nhắc lại sẽ cắt bao nhiêu video", GUI2[-1][0])
b4.xu_ly(111, f"/xemnhom {k_my}")
ok("KenhA" in GUI2[-1][0] and "Chạy nhóm này" in str(GUI2[-1][1]),
   "10k /xemnhom: chỉ xem từng kênh, có nút chạy")
ok("/chay" not in tele_bot.LENH_NHE, "10l /chay (quét thư mục) KHÔNG chạy ở luồng nghe")
print("MỤC 11 — ĐÓNG APP từ điện thoại")
import subprocess as _sp  # noqa: E402
ok(any(c == "dongapp" for c, _ in tele_bot.LENH_MENU) and tele_bot.doi_nut("⛔ Đóng app") == "/dongapp",
   "11a menu + nút bàn phím có ĐÓNG APP")
GUI3 = []
b5 = tele_bot.BotQuanLy("tok", {111}, None, gui=lambda c, t: GUI3.append(t))
b5.gui = lambda c, t, phim=False: (GUI3.append((t, phim)), 1)[1]


class _PoolGia:
    def dem_dang_chay(self):
        return (1, 2, 0)


b5.pool = _PoolGia()
DONG = []
tele_bot._UI_FN["dong_app"] = lambda: (DONG.append(1), {"ok": True})[1]
tele_gac.file_song().with_name("dong_app_da_dung.txt").unlink(missing_ok=True)
b5.xu_ly(111, "⛔ Đóng app")
t, ph = GUI3[-1]
cb = ph["inline_keyboard"][0][0]["callback_data"] if ph else ""
ok("Đóng app trên máy" in t and "3 việc" in t and cb.startswith("/dongappok ") and DONG == [],
   "11b bấm Đóng app -> HỎI xác nhận, nói rõ 3 việc đang chạy, CHƯA đóng", t[:80])
b5.xu_ly(111, cb)
ok(DONG == [1] and "Đang ĐÓNG" in GUI3[-1][0], "11c bấm ✅ -> đóng app (gọi giao diện 1 lần)")
b5.xu_ly(111, cb)
ok(DONG == [1], "11d CÙNG nút xử lý lần 2 (mở lại app nhận lại lệnh cũ) -> KHÔNG đóng nữa")
b5.xu_ly(111, f"/dongappok {int(time.time()) - 500}")
ok(DONG == [1] and "CŨ" in GUI3[-1][0], "11e nút quá hạn -> KHÔNG đóng, báo rõ")
b5.xu_ly(111, "/dongappok")
ok(DONG == [1], "11f lệnh không mốc giờ -> KHÔNG đóng")
tele_bot._UI_FN["dong_app"] = lambda: {"ok": False, "ly_do": "bận"}
b5.xu_ly(111, f"/dongappok {int(time.time()) + 1}")
ok("Không đóng được" in GUI3[-1][0], "11g giao diện không nhận -> báo lỗi, không im lặng")
ok("/dongappok" not in tele_bot.LENH_NHE, "11h xác nhận đóng KHÔNG chạy ở luồng nghe")

# bot gác cổng: app ở màn đăng nhập
GUI.clear()
tele_gac.CHO_DONG_GIAY = 5   # > nhịp soi cờ 2s của màn đăng nhập
for f in (tele_gac.file_song(), HC / "app.lock", tele_gac.file_co_dong_app()):
    f.unlink(missing_ok=True)
g.xu_ly(111, "⛔ Đóng app")
ok(any("TẮT sẵn" in x for x in GUI) and not tele_gac.file_co_dong_app().exists(),
   "11i app đang tắt -> báo tắt sẵn, không ghi cờ")
GUI.clear()
(HC / "app.lock").write_text(f"{os.getppid()}\nBQ\nmay\n", encoding="utf-8")
g.xu_ly(111, "/dongapp")
ok(tele_gac.file_co_dong_app().exists(), "11j app ở màn đăng nhập -> gửi CỜ đóng")
d = _moi(); d.huy_tu.click()
DONG_DN = []
d.rejected.connect(lambda: DONG_DN.append(1))
ok(cho(lambda: DONG_DN == [1], 6), "11k màn đăng nhập thấy cờ -> TỰ ĐÓNG (main.py thoát app)")
ok(not tele_gac.file_co_dong_app().exists(), "11l cờ bị xoá sau khi dùng")
ok(cho(lambda: any("CƯỠNG BỨC" in str(x) for x in GUI), 12),
   "11m app không thoát trong hạn -> HỎI tắt cưỡng bức (không tự giết)", str(GUI[-1:]))
tele_gac.file_co_dong_app().write_text(str(time.time() - 3600), encoding="utf-8")
d = _moi(); d.huy_tu.click()
DONG_DN = []
d.rejected.connect(lambda: DONG_DN.append(1))
cho(lambda: not tele_gac.file_co_dong_app().exists(), 6)
cho(lambda: False, 1)
ok(DONG_DN == [] and not tele_gac.file_co_dong_app().exists(),
   "11n cờ CŨ sót lại -> KHÔNG đóng màn đăng nhập (và xoá cờ)")
d.reject()

# tắt cưỡng bức: chỉ đúng PID, nút còn mới, bot chính KHÔNG sống
gia = _sp.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
(HC / "app.lock").write_text(f"{gia.pid}\nBQ\nmay\n", encoding="utf-8")
GUI.clear()
g.xu_ly(111, f"/dongappmanh {int(time.time()) - 500} {gia.pid}")
ok(gia.poll() is None and any("CŨ" in x for x in GUI), "11o nút cưỡng bức quá hạn -> KHÔNG tắt")
g.xu_ly(111, f"/dongappmanh {int(time.time())} {gia.pid + 99999}")
ok(gia.poll() is None, "11p sai PID -> KHÔNG tắt")
tele_gac.file_song().write_text("1", encoding="utf-8")
g.xu_ly(111, f"/dongappmanh {int(time.time())} {gia.pid}")
ok(gia.poll() is None, "11q bot chính đang sống -> KHÔNG tắt cưỡng bức")
tele_gac.file_song().unlink(missing_ok=True)
GUI.clear()
g.xu_ly(111, f"/dongappmanh {int(time.time())} {gia.pid}")
ok(cho(lambda: gia.poll() is not None, 10) and any("CƯỠNG BỨC" in x for x in GUI),
   "11r đủ điều kiện -> tắt đúng tiến trình app")
if gia.poll() is None:
    gia.kill()
(HC / "app.lock").unlink(missing_ok=True)

# cửa sổ chính: đóng cả hộp thoại đang mở rồi đóng cửa sổ
from PyQt6.QtWidgets import QMainWindow  # noqa: E402
import app.ui.main_window as MW  # noqa: E402
mw_src = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
ok('dang_ky_ui("dong_app", self._bot_dong_app)' in mw_src, "11s cửa sổ chính nối lệnh dong_app")
w = QMainWindow(); w.show()
hop = QDialog(w); hop.show()
_quit = QApplication.quit
QApplication.quit = staticmethod(lambda: None)
try:
    MW.MainWindow._dong_that(w)
finally:
    QApplication.quit = _quit
ok(not hop.isVisible() and not w.isVisible(), "11t đóng app: hộp thoại đang mở cũng đóng theo")
ok(not LOI_SLOT, "8 KHÔNG có lỗi nào trong slot Qt (ở app thật = sập app)", str(len(LOI_SLOT)))
print(f"KẾT QUẢ: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
