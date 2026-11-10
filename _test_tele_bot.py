# -*- coding: utf-8 -*-
"""CỔNG 97 — BOT TELEGRAM QUẢN LÝ DÂY CHUYỀN (`app/core/tele_bot.py`).

Thành phần THẬT: DB SQLite thật (sandbox) · `WorkerPool` thật chạy job thật ·
`requests` thật nói chuyện HTTP thật · `StudioPage` thật (offscreen) chạy
`_pipe_run` thật. Chỉ MÁY CHỦ Telegram là GIẢ (http.server trên 127.0.0.1) —
cổng KHÔNG BAO GIỜ nhắn lên điện thoại anh Hùng, không giành token với app.

Mệnh đề canh:
 1. chat LẠ không điều khiển được gì, chỉ nhận lại id của mình.
 2. /tamdung: job ĐANG chạy chạy hết, job CHỜ không được lấy (đo ở làn TRỐNG);
    cờ còn sau khi dựng pool MỚI; /chaytiep -> job chờ chạy xong.
 3. /huy: huỷ đúng 1 job; số lạ / job đã xong -> không đụng gì.
 4. báo cáo chạy được trên DB rỗng, DB có lỗi, DB hỏng (corrupt_live).
 5. tự báo: không dồn lỗi CŨ lúc mở; lỗi mới gom 1 tin; kẹt; chạy hết hàng;
    ổ đầy (1 lần/3 giờ); DB hỏng (1 lần).
 6. bot hỏng KHÔNG làm app hỏng; lỗi mạng không lộ token; mạng chết lùi dần;
    409 chờ 60s.
 7. tele_bot KHÔNG import PyQt6 (đụng Qt từ luồng nền = sập 0xC0000409).
 8. không token / BQ_TAT_BOT -> không bật gì; _test_guard tự bật BQ_TAT_BOT.
 9. TỐC ĐỘ (máy chủ giả, requests thật): bấm nút -> answerCallbackQuery
    < 1 giây và tin trả lời < 1 giây; lệnh nặng KHÔNG chặn lệnh nhẹ; cùng lệnh
    làm lần lượt; 429 khi sửa tin -> bỏ qua ngay, khi gửi tin -> chờ rồi gửi
    lại; send* giãn >= 0,35s; IPv4 CHỈ ép ở luồng bot; lệnh > 3s ghi log.
10. /theodoi SỬA 1 tin (editMessageText) thay vì gửi tin mới.
11. CHẠY DÂY CHUYỀN qua giao diện THẬT: đúng nhóm đã chọn (kênh nhóm khác KHÔNG
    bị quét), thiếu key / đang tạm dừng / nhóm rỗng -> từ chối, không quét gì.
"""
from __future__ import annotations

import ast
import json
import os
import queue
import socket
import sys
import tempfile
import threading
import time
import requests
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
T = tempfile.mkdtemp(prefix="bq_test_bot_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = str(Path(T) / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(Path(T) / "settings.ini")
sys.path.insert(0, str(ROOT))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _test_guard  # noqa: E402,F401  (đặt BQ_TAT_BOT, chặn cửa sổ ngoài)
import app.queue.jobs  # noqa: E402,F401  (cv2 TRƯỚC Qt)

from app.database import db  # noqa: E402
from app.queue import worker as W  # noqa: E402
from app.core import tele_bot as B  # noqa: E402

OK = HONG = 0


def ok(dk, ten, chi=""):
    global OK, HONG
    if dk:
        OK += 1
        print(f"  ĐẠT  {ten}")
    else:
        HONG += 1
        print(f"  HỎNG {ten}  {chi}")


SO: list[tuple[int, str]] = []


def gui(cid, text):
    SO.append((cid, text))


def doi(dk, giay=10.0):
    t = time.time()
    while time.time() - t < giay:
        if dk():
            return True
        time.sleep(0.02)
    return False


def trang(jid):
    r = db.query_one("SELECT status FROM jobs WHERE id=?", (jid,))
    return r["status"] if r else None


THA: dict[int, bool] = {}


def viec_thu(payload, ctx):
    k = payload["k"]
    while not THA.get(k):
        ctx.progress(0.5, f"đang làm {k}")
        time.sleep(0.05)
    return {}


W.register_handler("thu_bot", viec_thu)
db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES('Kênh thử', ?, 'Mỹ')", (T,))
PID = db.query_one("SELECT id FROM projects")["id"]

# ====================================================================== 8
print("CA 8 — không token / BQ_TAT_BOT")
ok(os.environ.get("BQ_TAT_BOT") == "1", "_test_guard tự bật BQ_TAT_BOT")
os.environ["TELEGRAM_BOT_TOKEN"] = "123:gia"
ok(B.khoi_dong(None) is None and B._bot is None, "BQ_TAT_BOT -> không bật bot dù có token")
os.environ.pop("TELEGRAM_BOT_TOKEN")
os.environ.pop("BQ_TAT_BOT")
ok(B.khoi_dong(None) is None and B._bot is None, "không token -> không bật gì")
os.environ["BQ_TAT_BOT"] = "1"
os.environ["TELEGRAM_CHAT_IDS"] = "111, -222; x"
ok(B._cfg()[1] == {111, -222}, "đọc danh sách chat (bỏ rác, nhận id nhóm âm)")

# ====================================================================== 4
print("CA 4 — báo cáo trên DB rỗng")
bot = B.BotQuanLy("tok", {111}, None, gui=gui)
for f in (B.bao_cao_tien_do, B.bao_cao_loi, B.bao_cao_may, B.bao_cao_kenh):
    try:
        s = f() if f in (B.bao_cao_loi, B.bao_cao_kenh) else f(None)
        ok(isinstance(s, str) and s, f"{f.__name__} chạy trên DB gần rỗng")
    except Exception as e:  # noqa: BLE001
        ok(False, f"{f.__name__} chạy trên DB gần rỗng", repr(e))

# ====================================================================== 1
print("CA 1 — chat lạ")
pool = W.WorkerPool({}, max_cpu=1, max_gpu=1, poll_interval=0.05)
pool.start()
bot.pool = pool
SO.clear()
bot.xu_ly(999, "/tamdung")
ok(not pool.dang_tam_dung(), "chat lạ gõ /tamdung -> KHÔNG tạm dừng")
ok(SO and SO[-1][0] == 999 and "999" in SO[-1][1], "chat lạ nhận lại id của mình")
bot.xu_ly(999, "/chayok 0")
ok("CHƯA được phép" in SO[-1][1], "chat lạ gõ /chayok -> bị chặn")

# ====================================================================== 2
print("CA 2 — tạm dừng / chạy tiếp với job thật")
j1 = pool.enqueue("thu_bot", {"k": 1}, project_id=PID)
ok(doi(lambda: trang(j1) == "running"), "job 1 chạy")
bot.xu_ly(111, "/tamdung")
ok(pool.dang_tam_dung(), "/tamdung -> pool tạm dừng")
ok(pool._co_tam_dung().exists(), "cờ tạm dừng ghi RA ĐĨA")
# làn GPU đang TRỐNG -> nếu tạm dừng hỏng thì job 2 chạy ngay (đo đúng cửa)
j2 = pool.enqueue("thu_bot", {"k": 2}, project_id=PID, needs_gpu=True)
time.sleep(0.6)
ok(trang(j2) == "pending", "đang dừng -> job MỚI không được lấy", trang(j2))
ok(trang(j1) == "running", "job đang chạy KHÔNG bị kill")
THA[1] = True
ok(doi(lambda: trang(j1) == "done"), "job đang chạy chạy hết -> done")
time.sleep(0.4)
ok(trang(j2) == "pending", "job chờ vẫn chờ sau khi job 1 xong")
pool2 = W.WorkerPool({}, max_cpu=1, max_gpu=1)
ok(pool2.dang_tam_dung(), "pool MỚI (mở lại app) vẫn đọc ra đang tạm dừng")
txt = B.bao_cao_tien_do(pool)
ok("TẠM DỪNG" in txt and "chờ" in txt, "/tiendo nói rõ đang tạm dừng")
bot.xu_ly(111, "/chaytiep")
ok(not pool.dang_tam_dung() and not pool._co_tam_dung().exists(), "/chaytiep gỡ cờ (RAM + đĩa)")
THA[2] = True
ok(doi(lambda: trang(j2) == "done"), "chạy tiếp -> job chờ chạy xong")

# ====================================================================== 3
print("CA 3 — /huy")
j3 = pool.enqueue("thu_bot", {"k": 3}, project_id=PID)
ok(doi(lambda: trang(j3) == "running"), "job 3 chạy")
SO.clear()
bot.xu_ly(111, f"/huy {j3}")
ok(doi(lambda: trang(j3) == "canceled"), "/huy -> job canceled", trang(j3))
bot.xu_ly(111, f"/huy {j1}")
ok(trang(j1) == "done" and "không cần huỷ" in SO[-1][1], "/huy job đã xong -> không đụng")
bot.xu_ly(111, "/huy 99999")
ok("Không có" in SO[-1][1], "/huy số lạ -> báo không có")
bot.xu_ly(111, "/huy abc")
ok("Gõ /huy" in SO[-1][1], "/huy thiếu số -> hướng dẫn")
bot.xu_ly(111, "/tiendo@BQBot")
ok("Tiến độ" in SO[-1][1], "lệnh kèm @tênbot vẫn nhận")

# ====================================================================== 5
print("CA 5 — tự báo")
db.execute("INSERT INTO jobs(type,project_id,status,error,finished_at) "
           "VALUES('auto',?, 'failed','lỗi CŨ', datetime('now'))", (PID,))
b2 = B.BotQuanLy("tok", {111}, pool, gui=gui)
t0 = 1_000_000.0
tin = b2.soi_mot_lan(t0)
ok(not any("lỗi" in x for x in tin), "lượt đầu KHÔNG dồn lỗi cũ", str(tin)[:120])
for e in ("ffmpeg chết", "ffmpeg chết 2"):
    db.execute("INSERT INTO jobs(type,project_id,status,error,finished_at) "
               "VALUES('m1_export_clip',?, 'failed',?, datetime('now'))", (PID, e))
ok(not b2.soi_mot_lan(t0 + 30), "lỗi mới chưa báo ngay (đang gom)")
tin = b2.soi_mot_lan(t0 + 30 + B.GOM_LOI_GIAY)
ok(len(tin) == 1 and "2 việc lỗi mới" in tin[0], "2 lỗi mới gom thành 1 tin", str(tin)[:120])
ok(not b2.soi_mot_lan(t0 + 400), "lỗi đã báo không báo lại")
b3 = B.BotQuanLy("tok", {111}, pool, gui=gui)
db.execute("INSERT INTO jobs(type,project_id,status,progress,message,started_at) "
           "VALUES('auto',?, 'running',0.3,'đứng im',datetime('now'))", (PID,))
jk = db.query_one("SELECT max(id) i FROM jobs")["i"]
b3.soi_mot_lan(t0)
ok(not b3.soi_mot_lan(t0 + 60), "tiến độ đứng im 1 phút -> chưa báo")
tin = b3.soi_mot_lan(t0 + B.KET_PHUT * 60 + 1)
ok(any(f"#{jk} đứng im" in x for x in tin), "đứng im quá ngưỡng -> báo kẹt", str(tin)[:120])
ok(not any("đứng im" in x for x in b3.soi_mot_lan(t0 + B.KET_PHUT * 60 + 30)), "kẹt chỉ báo 1 lần")
db.execute("UPDATE jobs SET progress=0.4 WHERE id=?", (jk,))
ok(not b3.soi_mot_lan(t0 + B.KET_PHUT * 60 + 60), "nhích tiến độ -> hết kẹt, không báo")
db.execute("UPDATE jobs SET status='done', finished_at=datetime('now') WHERE id=?", (jk,))
# 01/11/2026: "HẾT" cần 2 lượt soi rỗng LIỀN NHAU (job xuất được xếp vài giây
# sau khi phân tích xong — 1 lượt rỗng chưa chắc là hết).
tin = b3.soi_mot_lan(t0 + 4000)
ok(not any("HẾT hàng chờ" in x for x in tin), "1 lượt rỗng -> CHƯA báo hết", str(tin)[:80])
tin = b3.soi_mot_lan(t0 + 4030)
ok(any("HẾT hàng chờ" in x for x in tin), "hết việc (2 lượt rỗng) -> báo đã chạy hết", str(tin)[:120])
goc = B._o_dia
B._o_dia = lambda: ("C:\\", 5.0)
tin = b3.soi_mot_lan(t0 + 5000)
ok(any("chỉ còn 5 GB" in x for x in tin), "ổ dưới ngưỡng -> báo")
ok(not any("GB" in x for x in b3.soi_mot_lan(t0 + 6000)), "ổ đầy báo tối đa 1 lần/3 giờ")
B._o_dia = goc
db.corrupt_live = True
try:
    tin = b3.soi_mot_lan(t0 + 7000)
    ok(any("Cơ sở dữ liệu" in x for x in tin), "DB hỏng -> báo")
    ok(isinstance(B.bao_cao_tien_do(pool), str), "/tiendo vẫn trả lời khi DB hỏng")
    ok(not any("Cơ sở dữ liệu" in x for x in b3.soi_mot_lan(t0 + 7100)), "DB hỏng báo 1 lần")
finally:
    db.corrupt_live = False

# ====================================================================== 6
print("CA 6 — bot hỏng không làm app hỏng")
goc = B.bao_cao_loi
B.bao_cao_loi = lambda: 1 / 0
B.xoa_dem()
try:
    bot.xu_ly(111, "/loi")
    ok("Lệnh lỗi" in SO[-1][1], "lệnh ném lỗi -> trả lời cảnh báo, không ném ra")
except Exception as e:  # noqa: BLE001
    ok(False, "lệnh ném lỗi -> không ném ra", repr(e))
B.bao_cao_loi = goc
bot._nhan_mot({"weird": 1})
bot._nhan_mot({"message": {}})
ok(True, "update rác -> không ném")
bot.gui(111, "a" * 10000)
ok(len(SO[-1][1]) < 4096, "tin quá 4096 ký tự được cắt", str(len(SO[-1][1])))


class Mang(B.BotQuanLy):
    def __init__(self, loi):
        super().__init__("tok", {111}, pool, gui=gui)
        self.loi = loi
        self.cho: list[float] = []

    def _goi(self, method, data, timeout=20):
        raise RuntimeError(self.loi)


for loi, mong in (("mạng chết", [2.0, 4.0, 8.0]), ("getUpdates 409: Conflict", [60.0, 60.0, 60.0])):
    m = Mang(loi)

    def wait(s, m=m):
        m.cho.append(s)
        if len(m.cho) >= 3:
            m._dung.set()
        return m._dung.is_set()
    m._dung.wait = wait
    m._vong_nhan()
    ok(m.cho[:3] == mong, f"'{loi}' -> chờ {mong}", str(m.cho))

goc_api = B.API
B.API = "http://127.0.0.1:9/bot{tok}/{m}"
try:
    B.BotQuanLy("999:BIMAT_TOKEN", {1})._goi("getMe", {}, timeout=2)
    ok(False, "mạng chết -> phải ném")
except Exception as e:  # noqa: BLE001
    ok("BIMAT_TOKEN" not in str(e), "lỗi mạng KHÔNG lộ token vào log", str(e))
B.API = goc_api

# ====================================================================== 9
print("CA 9 — TỐC ĐỘ (máy chủ Telegram GIẢ, requests THẬT)")


class May:
    """Máy chủ Telegram giả: ghi sổ mọi lời gọi kèm thời điểm."""
    so: list = []                     # (giờ, method, data)
    cap: "queue.Queue" = queue.Queue()   # update chờ trả cho getUpdates
    loi429: dict = {}                 # method -> số lần trả 429
    mid = 100


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        method = self.path.rsplit("/", 1)[-1]
        n = int(self.headers.get("Content-Length") or 0)
        data = json.loads(self.rfile.read(n) or b"{}")
        if method == "getUpdates":
            kq = []
            try:
                kq.append(May.cap.get(timeout=min(1.0, data.get("timeout", 0))))
            except queue.Empty:
                pass
            return self._tra(200, {"ok": True, "result": kq})
        May.so.append((time.monotonic(), method, data))
        if May.loi429.get(method, 0) > 0:
            May.loi429[method] -= 1
            return self._tra(429, {"ok": False, "error_code": 429,
                                   "description": "Too Many Requests",
                                   "parameters": {"retry_after": 1}})
        if method == "sendMessage":
            May.mid += 1
            return self._tra(200, {"ok": True, "result": {"message_id": May.mid}})
        return self._tra(200, {"ok": True, "result": True})

    def _tra(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B.API = f"http://127.0.0.1:{srv.server_address[1]}/bot{{tok}}/{{m}}"
B._bat_ipv4()
bt = B.BotQuanLy("tok", {111}, pool)
threading.Thread(target=bt._vong_nhan, daemon=True).start()
UPD = [1000]


def bam(data, chat=111):
    UPD[0] += 1
    t = time.monotonic()
    May.cap.put({"update_id": UPD[0], "callback_query": {
        "id": f"cb{UPD[0]}", "data": data,
        "message": {"chat": {"id": chat}, "message_id": 1}}})
    return t


def go(text, chat=111):
    UPD[0] += 1
    t = time.monotonic()
    May.cap.put({"update_id": UPD[0], "message": {"chat": {"id": chat}, "text": text}})
    return t


def cho_goi(method, sau, dk=lambda d: True, giay=5.0):
    t = time.monotonic()
    while time.monotonic() - t < giay:
        for g, m, d in list(May.so):
            if g >= sau and m == method and dk(d):
                return g
        time.sleep(0.005)
    return None


B.xoa_dem()
do_nut = []
for i in range(5):
    t = bam("/tiendo")
    a = cho_goi("answerCallbackQuery", t)
    s = cho_goi("sendMessage", t, lambda d: "Tiến độ" in d.get("text", ""))
    if a and s:
        do_nut.append((a - t, s - t))
    time.sleep(0.4)
ok(len(do_nut) == 5, "5/5 lần bấm nút đều có trả lời", str(len(do_nut)))
if do_nut:
    tl = max(x[0] for x in do_nut)
    tt = max(x[1] for x in do_nut)
    print(f"     đo: 'Đang làm...' chậm nhất {tl*1000:.0f} ms · "
          f"tin trả lời chậm nhất {tt*1000:.0f} ms")
    ok(tl < 1.0, f"bấm nút -> 'Đang làm...' < 1 giây ({tl*1000:.0f} ms)")
    ok(tt < 1.0, f"bấm nút -> có tin trả lời < 1 giây ({tt*1000:.0f} ms)")
nut = [d for _, m, d in May.so if m == "answerCallbackQuery"]
ok(nut and all(d.get("text") == "⏳ Đang làm..." for d in nut), "nút hiện chữ '⏳ Đang làm...'")

# lệnh nặng KHÔNG chặn lệnh nhẹ + cùng lệnh làm lần lượt
goc = B.bao_cao_loi
cung_luc = [0, 0]
khoa = threading.Lock()


def loi_cham():
    with khoa:
        cung_luc[0] += 1
        cung_luc[1] = max(cung_luc[1], cung_luc[0])
    time.sleep(1.5)
    with khoa:
        cung_luc[0] -= 1
    return "lỗi chậm"


B.bao_cao_loi = loi_cham
B.xoa_dem()
go("/loi")
time.sleep(0.05)
B.xoa_dem()
go("/loi@x")   # cùng lệnh, cùng chat -> phải đợi
time.sleep(0.05)
t2 = go("/tamdung")
s = cho_goi("sendMessage", t2, lambda d: "TẠM DỪNG" in d.get("text", ""))
ok(s is not None and s - t2 < 1.0, "lệnh nặng đang chạy 1,5s -> /tamdung vẫn trả lời < 1s",
   f"{(s - t2) if s else None}")
ok(doi(lambda: sum(1 for _, m, d in May.so if m == "sendMessage"
                   and d.get("text") == "lỗi chậm") >= 1, 6), "lệnh nặng vẫn trả lời")
pool.chay_tiep()
time.sleep(3.5)
ok(cung_luc[1] == 1, "cùng lệnh của 1 chat làm LẦN LƯỢT (không chồng)", str(cung_luc))
B.bao_cao_loi = goc

# 429
May.so.clear()
May.loi429["editMessageText"] = 1
t = time.monotonic()
bt.sua(111, 5, "x")
ok(time.monotonic() - t < 0.5, "429 khi SỬA tin -> bỏ qua ngay, không chờ")
ok(sum(1 for _, m, _ in May.so if m == "editMessageText") == 1, "429 khi sửa -> không gửi lại")
May.loi429["sendMessage"] = 1
t = time.monotonic()
mid = bt.gui(111, "thử 429")
dt = time.monotonic() - t
ok(mid is not None and 0.9 <= dt < 3, f"429 khi GỬI -> chờ retry_after rồi gửi lại ({dt:.2f}s)")
May.loi429["answerCallbackQuery"] = 1
t = time.monotonic()
try:
    bt._goi("answerCallbackQuery", {"callback_query_id": "z"})
    ok(time.monotonic() - t < 0.5, "429 khi trả lời nút -> bỏ qua ngay")
except Exception as e:  # noqa: BLE001
    ok(False, "429 khi trả lời nút -> bỏ qua ngay", repr(e))

# giãn 0,35s giữa send*, không áp cho edit
May.so.clear()
for i in range(4):
    bt.gui(111, f"g{i}")
for i in range(4):
    bt.sua(111, 5, f"s{i}")
gs = [g for g, m, _ in May.so if m == "sendMessage"]
es = [g for g, m, _ in May.so if m == "editMessageText"]
khe = min(b - a for a, b in zip(gs, gs[1:]))
# đo ở PHÍA MÁY CHỦ nên có xê dịch mạng nội bộ vài ms -> sàn 0,30s
ok(khe >= 0.30, f"send* giãn ~0,35s (khe nhỏ nhất đo ở máy chủ {khe:.3f}s)")
ok(es[-1] - es[0] < 0.6, f"edit KHÔNG bị giãn ({es[-1]-es[0]:.3f}s cho 4 lần)")

# IPv4 chỉ ở luồng bot
import urllib3.util.connection as uc  # noqa: E402
ok(not getattr(B._LUONG, "ipv4", False),
   "luồng chính đã gọi bot.gui() xong -> cờ IPv4 được TRẢ LẠI (không rò)")
ok(uc.allowed_gai_family() != socket.AF_INET or not socket.has_ipv6,
   "luồng KHÁC (Groq, edge-tts...) KHÔNG bị ép IPv4")
_bat = {}
_goc_post = requests.Session.post


def _soi_post(self, *a, **k):
    _bat["f"] = uc.allowed_gai_family()
    return _goc_post(self, *a, **k)


requests.Session.post = _soi_post
bt.sua(111, 5, "soi ipv4")
requests.Session.post = _goc_post
ok(_bat.get("f") == socket.AF_INET, "TRONG lúc gọi Telegram -> đúng là IPv4")
kq = {}


def thu():
    B._LUONG.ipv4 = True
    kq["f"] = uc.allowed_gai_family()


th = threading.Thread(target=thu)
th.start()
th.join()
ok(kq.get("f") == socket.AF_INET, "luồng bot bị ép IPv4")
ok(isinstance(bt._phien(), requests.Session) and bt._phien() is bt._phien(),
   "mỗi luồng giữ 1 requests.Session (giữ kết nối)")

# lệnh chậm > 3s -> ghi log
goc_k = B.bao_cao_kenh
B.bao_cao_kenh = lambda: (time.sleep(3.2), "kênh")[1]
B.xoa_dem()
bt.xu_ly(111, "/kenh")
B.bao_cao_kenh = goc_k
logf = Path(T) / "logs"
ok(any("CHẬM: lệnh /kenh" in f.read_text(encoding="utf-8") for f in logf.glob("telegram_*.log")),
   "lệnh xử lý > 3 giây -> ghi log CHẬM")

# ====================================================================== 10
print("CA 10 — /theodoi sửa 1 tin")
B.SONG_NHIP = 0.3
B.NHIP_THEO_DOI = 0.3
May.so.clear()
threading.Thread(target=bt._vong_soi, daemon=True).start()
bt._bat_theo_doi(111)
time.sleep(1.6)
gs = [d for _, m, d in May.so if m == "sendMessage"]
ok(len(gs) == 1, f"theo dõi gửi đúng 1 tin mới ({len(gs)})")
mid0 = bt._song.get(111, {}).get("mid")
db.execute("INSERT INTO jobs(type,project_id,status,progress,message,started_at) "
           "VALUES('auto',?, 'running',0.1,'tin sống',datetime('now'))", (PID,))
jn = db.query_one("SELECT max(id) i FROM jobs")["i"]
ok(doi(lambda: any(m == "editMessageText" and "tin sống" in d.get("text", "")
                   for _, m, d in May.so), 4), "trạng thái đổi -> SỬA tin cũ (editMessageText)")
es = [d for _, m, d in May.so if m == "editMessageText"]
ok(es and {d["message_id"] for d in es} == {mid0}, "mọi lần sửa đều vào CÙNG 1 tin",
   str({d["message_id"] for d in es}) + f" vs {mid0}")
ok(len([1 for _, m, _ in May.so if m == "sendMessage"]) == 1, "không gửi thêm tin mới nào")
db.execute("UPDATE jobs SET status='done', finished_at=datetime('now') WHERE id=?", (jn,))
ok(doi(lambda: not bt._song, 4), "chạy hết hàng -> tin theo dõi tự ngừng",
   str(db.query("SELECT id,type,status FROM jobs WHERE status IN ('pending','running')")))
ok(any("ngừng cập nhật" in d.get("text", "") for _, m, d in May.so if m == "editMessageText"),
   "lần sửa cuối ghi 'đã chạy hết — ngừng cập nhật'")

# ====================================================================== 11
print("CA 11 — chạy dây chuyền qua GIAO DIỆN THẬT")
B._UI_FN.clear()
ok(B.goi_ui("chay_day_chuyen", "Mỹ").get("ok") is False, "chưa có giao diện -> từ chối êm")
B.dang_ky_ui("cham", lambda: None)
ok("bận" in B.goi_ui("cham", cho=0.3).get("ly_do", ""), "giao diện không rút lệnh -> quá giờ, không treo")
B.chay_hang_ui()          # rút lệnh mồ côi

from PyQt6.QtWidgets import QApplication  # noqa: E402
qapp = QApplication.instance() or QApplication(sys.argv)
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402
from app.core import pipeline as P  # noqa: E402

for ten, nhom in (("Kênh Mỹ 1", "Mỹ"), ("Kênh Mỹ 2", "Mỹ"), ("Kênh Nhật", "Nhật")):
    d = Path(T) / "nguon" / ten
    d.mkdir(parents=True, exist_ok=True)
    db.execute("INSERT INTO projects(name, assets_dir, grp, pipe_src, pipe_on, pipe_hidden) "
               "VALUES(?,?,?,?,1,0)", (ten, T, nhom, str(d)))
state = AppState()
state.pool = pool
page = StudioPage(state)
B.dang_ky_ui("chay_day_chuyen", page._bot_chay_day_chuyen)
B.dang_ky_ui("dang_nhan", page._bot_dang_nhan)
QUET: list = []
goc_plan = P.plan_channel


def plan_spy(pid, ten, *a, **k):
    QUET.append(ten)
    return goc_plan(pid, ten, *a, **k)


P.plan_channel = plan_spy
bc = B.BotQuanLy("tok", {111}, pool, gui=gui)


def bot_lenh(text):
    """Bot chạy ở luồng nền; luồng chính bơm event loop như app thật (QTimer)."""
    th = threading.Thread(target=bc.xu_ly, args=(111, text))
    th.start()
    t = time.time()
    while th.is_alive() and time.time() - t < 20:
        B.chay_hang_ui()
        qapp.processEvents()
        time.sleep(0.01)
    th.join(1)


SO.clear()
bot_lenh("/chay")
ok(any("Chọn nhóm" in x for _, x in SO), "/chay -> hiện danh sách nhóm để chọn")
k_my = next(k for k, g in bc._nhom_map.items() if g == "Mỹ")
from app.ai import llm as _llm  # noqa: E402
_goc_cf = _llm.is_configured
_llm.is_configured = lambda: False
SO.clear()
bot_lenh(f"/chayok {k_my}")
ok(any("key AI" in x for _, x in SO) and not QUET, "thiếu key AI -> từ chối, KHÔNG quét kênh nào")
_llm.is_configured = lambda: True
pool.tam_dung()
SO.clear()
bot_lenh(f"/chayok {k_my}")
ok(any("TẠM DỪNG" in x for _, x in SO) and not QUET, "đang tạm dừng -> từ chối, KHÔNG quét")
pool.chay_tiep()
SO.clear()
bot_lenh(f"/chay {k_my}")
ok(any("?" in x for _, x in SO) and not QUET, "chọn nhóm -> hỏi XÁC NHẬN trước, chưa chạy")
SO.clear()
bot_lenh(f"/chayok {k_my}")
t = time.time()
while len(QUET) < 2 and time.time() - t < 15:
    qapp.processEvents()
    time.sleep(0.02)
for _ in range(30):
    qapp.processEvents()
    time.sleep(0.02)
ok(any("Đã bấm Chạy" in x and "2 kênh" in x for _, x in SO), "xác nhận -> chạy, báo đúng 2 kênh",
   str([x[:80] for _, x in SO]))
ok(sorted(QUET) == ["Kênh Mỹ 1", "Kênh Mỹ 2"], "CHỈ quét kênh nhóm Mỹ, nhóm Nhật KHÔNG bị đụng",
   str(QUET))
ok(any("Lệnh từ bot Telegram" in f.read_text(encoding="utf-8")
       for f in (Path(T) / "logs").glob("pipeline_*.log")),
   "nhật ký dây chuyền ghi rõ lệnh đến từ bot")
QUET.clear()
SO.clear()
bot_lenh("/chayok 999")
ok(any("đã cũ" in x for _, x in SO) and not QUET, "số nhóm lạ -> không chạy gì")
db.execute("UPDATE projects SET pipe_on=0 WHERE grp='Nhật'")
ok(page._bot_chay_day_chuyen("Nhật").get("ok") is False and not QUET,
   "nhóm không còn kênh bật -> từ chối")

# ---- 02/11/2026: NHÓM MỚI CHƯA BẬT / NHÓM RỖNG PHẢI HIỆN TRÊN BOT ----
# Lỗi thật: anh Hùng thêm nhóm "Mỹ BKT" (16 kênh, chưa tích 'Bật') -> bot
# không liệt kê, không giải thích, tắt/mở app vẫn không thấy.
B.dang_ky_ui("nhom_rong", page._bot_nhom_rong)
B.dang_ky_ui("bat_nhom", page._bot_bat_nhom)
for ten in ("BKT 1", "BKT 2"):
    db.execute("INSERT INTO projects(name, assets_dir, grp, pipe_src, pipe_on, "
               "pipe_hidden) VALUES(?,?,?,?,0,0)",
               (ten, T, "Mỹ BKT", str(Path(T) / "nguon" / ten)))
page._save_extra_groups(page._extra_groups() + ["Nhóm Rỗng Mới"])
SO.clear()
bot_lenh("/chay")

ok("Mỹ BKT" in bc._nhom_map.values(),
   "nhóm MỚI chưa bật kênh nào VẪN có trong danh sách bot",
   str(list(bc._nhom_map.values())))
ok("Nhật" in bc._nhom_map.values(),
   "nhóm vừa TẮT hết kênh vẫn hiện (không biến mất)")
ok("Nhóm Rỗng Mới" in bc._nhom_map.values(),
   "nhóm mới tạo CÒN RỖNG (chỉ trong cài đặt app) vẫn hiện")
k_bkt = next(k for k, g in bc._nhom_map.items() if g == "Mỹ BKT")
k_rong = next(k for k, g in bc._nhom_map.items() if g == "Nhóm Rỗng Mới")
SO.clear()
bot_lenh(f"/chay {k_bkt}")
ok(any("CHƯA kênh" in x and "BẬT" in x for _, x in SO) and not QUET,
   "chọn nhóm chưa bật -> NÓI RÕ vì sao, không chạy", str([x[:90] for _, x in SO]))
SO.clear()
bot_lenh(f"/chay {k_rong}")
ok(any("CHƯA CÓ KÊNH" in x for _, x in SO) and not QUET,
   "chọn nhóm rỗng -> nói rõ chưa có kênh + chỉ cách thêm")
SO.clear()
bot_lenh(f"/batnhom {k_bkt}")
r = db.query_one("SELECT SUM(pipe_on) n FROM projects WHERE grp='Mỹ BKT'")
ok(int(r["n"] or 0) == 2, "/batnhom -> bật ĐÚNG 2 kênh của nhóm", str(dict(r)))
r2 = db.query_one("SELECT SUM(pipe_on) n FROM projects WHERE grp='Nhật'")
ok(int(r2["n"] or 0) == 0, "nhóm KHÁC không bị đụng")
ok(any("Đã bật" in x for _, x in SO) and any("Chạy?" in x for _, x in SO)
   and not QUET, "bật xong -> chuyển sang XEM TRƯỚC + hỏi xác nhận (chưa chạy)",
   str([x[:80] for _, x in SO]))
db.execute("UPDATE projects SET pipe_hidden=1, pipe_on=0 WHERE name='BKT 2'")
SO.clear()
bot_lenh(f"/batnhom {k_bkt}")
r = db.query_one("SELECT pipe_on FROM projects WHERE name='BKT 2'")
ok(int(r["pipe_on"]) == 0, "kênh đã ẨN không bị bật lại (giống nút 'Bật tất cả')")
SO.clear()
bot_lenh(f"/batnhom {k_rong}")
ok(any("Chưa bật được" in x for _, x in SO), "/batnhom nhóm rỗng -> báo, không nổ")
SO.clear()
bot_lenh("/batnhom 999")
ok(any("đã cũ" in x for _, x in SO), "/batnhom số lạ -> danh sách cũ")
db.execute("UPDATE projects SET pipe_on=0, pipe_hidden=0 WHERE grp='Mỹ BKT'")
page._save_extra_groups([g for g in page._extra_groups() if g != "Nhóm Rỗng Mới"])

# ---- KÊNH MỚI THỪA HƯỞNG trạng thái dây chuyền của nhóm (02/11/2026) ----
from app import services as _SV  # noqa: E402
_p1 = _SV.create_project("Kênh mới vào Mỹ", "Mỹ")          # Mỹ đang có kênh bật
_p2 = _SV.create_project("Kênh mới vào BKT", "Mỹ BKT")     # nhóm chưa bật
_p3 = _SV.create_project("Kênh mới không nhóm", "")
_on = {r["id"]: int(r["pipe_on"]) for r in db.query(
    "SELECT id, pipe_on FROM projects WHERE id IN (?,?,?)", (_p1, _p2, _p3))}
ok(_on.get(_p1) == 1, "thêm kênh vào nhóm ĐANG CHẠY -> kênh mới tự BẬT", str(_on))
ok(_on.get(_p2) == 0, "thêm kênh vào nhóm CHƯA BẬT -> giữ tắt")
ok(_on.get(_p3) == 0, "kênh chưa phân nhóm -> giữ tắt")
db.execute("DELETE FROM projects WHERE id IN (?,?,?)", (_p1, _p2, _p3))
_llm.is_configured = _goc_cf
P.plan_channel = goc_plan

# ====================================================================== 12
print("CA 12 — tiến trình phân tích lỗi lúc máy nghẽn -> TỰ hẹn nhận lại")
vf = Path(T) / "nguon" / "Kênh Mỹ 1" / "goc.mp4"
vf.write_bytes(b"x" * 2048)


def dung_ctx(loi):
    e = P.take_file(PID, vf.name, "h" + str(time.time()), None)
    db.execute("INSERT INTO jobs(type,project_id,status,error,finished_at) "
               "VALUES('auto',?, 'failed',?, datetime('now'))", (PID, loi))
    jid = db.query_one("SELECT max(id) i FROM jobs")["i"]
    ctx = {"entry": e, "vid": None, "path": str(vf), "pid": PID, "name": "Kênh Mỹ 1",
           "file": vf.name, "mode": "auto"}
    page._pipe_cut = {jid: ctx}
    page._pipe_by_vid = {}
    return e


page.__dict__.pop("_ai_thu_lai_q", None)
page.__dict__.pop("_ai_thu_lai_dem", None)
LAY: list = []
page._pipe_take = lambda pid, name, mode, path, pre=None: LAY.append(Path(path).name) or True
for i, loi in enumerate(("analysis_worker_failed: Tiến trình phân tích đã dừng (mã 3221356611)",
                         "analysis_worker_timeout: Khởi động phân tích quá 180 giây.")):
    e = dung_ctx(loi)
    page._pipe_poll_cut()
    q = page.__dict__.get("_ai_thu_lai_q", {})
    ok(page._pipe_khoa(vf) in q, f"lỗi tiến trình phân tích ({loi[:23]}) -> HẸN tự nhận lại")
    ok(db.query_one("SELECT status FROM pipeline_files WHERE id=?", (e,)) is None,
       "gỡ sổ nhận (lượt sau nhận lại được)")
    ok(vf.exists(), "video gốc GIỮ NGUYÊN chỗ cũ")
    if page._pipe_khoa(vf) in q:
        q[page._pipe_khoa(vf)]["due"] = 0
    LAY.clear()
    page._pipe_ai_thu_lai_nhip()
    ok(LAY == [vf.name], "tới hẹn -> TỰ nhận lại video (không cần bấm Chạy)", str(LAY))
e = dung_ctx("analysis_worker_failed: lần 3")
page._pipe_poll_cut()
e = dung_ctx("analysis_worker_failed: lần 4")
page._pipe_poll_cut()
_k = page._pipe_khoa(vf)
ok(page.__dict__.get("_ai_thu_lai_dem", {}).get(_k) == 3
   and page.__dict__.get("_ai_thu_lai_q", {}).get(_k, {}).get("lan") == 3,
   "lần 4 -> KHÔNG hẹn thêm (trần 3 lần, không lặp vô hạn)",
   str(page.__dict__.get("_ai_thu_lai_dem")))
page.__dict__.pop("_ai_thu_lai_q", None)
e = dung_ctx("Groq 500 Internal Server Error")
page._pipe_poll_cut()
ok(not page.__dict__.get("_ai_thu_lai_q"), "lỗi KHÁC (không phải tiến trình) -> giữ cách cũ")
ok(vf.exists(), "video gốc vẫn giữ nguyên")

# ====================================================================== 7
print("CA 7 — không đụng Qt")
src = (ROOT / "app/core/tele_bot.py").read_text(encoding="utf-8")
mods = set()
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.Import):
        mods |= {a.name for a in n.names}
    elif isinstance(n, ast.ImportFrom):
        mods.add(n.module or "")
ok(not any(m.startswith("PyQt") for m in mods), "tele_bot không import PyQt", str(mods))
ok(any(m.startswith("PyQt") for m in [
    a.name for n in ast.walk(ast.parse("import PyQt6.QtCore")) if isinstance(n, ast.Import)
    for a in n.names]), "tự kiểm: bộ dò bắt được import PyQt")

# ====================================================================== 8
print("CA 8 — phiên HTTP để lâu thì mở mới (lỗi /chay treo 20 s, 10/11/2026)")
import threading as _th  # noqa: E402
_b8 = B.BotQuanLy.__new__(B.BotQuanLy)
_b8._tl = _th.local()
_s1 = _b8._phien()
ok(_b8._phien() is _s1, "gọi liền nhau -> dùng lại đúng phiên (không mở mới vô cớ)")
_b8._tl.luc -= B.PHIEN_NGHI_TOI_DA + 1          # giả lập để không quá ngưỡng
_s2 = _b8._phien()
ok(_s2 is not _s1, "để không quá ngưỡng -> mở phiên MỚI (kết nối cũ có thể đã chết)")
ok(B.PHIEN_NGHI_TOI_DA <= 60, "ngưỡng ≤ 60 s (Telegram đóng kết nối rảnh rất sớm)",
   str(B.PHIEN_NGHI_TOI_DA))
_tg = _th.Thread(target=lambda: _kq8.append(_b8._phien()))
_kq8 = []
_tg.start()
_tg.join()
ok(_kq8 and _kq8[0] is not _s2, "mỗi luồng một phiên riêng (giữ nguyên thiết kế cũ)")

bt.dung()
srv.shutdown()
pool.stop()
print(f"\nKETQUA ĐẠT {OK} · HỎNG {HONG}")
sys.stdout.flush()
os._exit(1 if HONG else 0)
