# -*- coding: utf-8 -*-
"""CỔNG 28 — LIÊN THÔNG: các luồng vừa sửa KHÔNG được phá nhau.

Cổng 25/26/27 kiểm từng tính năng. Cổng này đi tìm chỗ 2 bản vá ĐÚNG cộng lại
thành SAI — đúng cái anh Hùng yêu cầu ("đảm bảo hệ thống hoạt động đúng, các
luồng hỗ trợ với nhau"). Đã bắt được 2 lỗi thật khi viết nó:
  (a) `LLMTooLarge` mang lời lỗi có chứa 'rate_limit_exceeded' -> vòng
      ĐỢI-HẾT-LƯỢT của m1 tưởng là hết lượt và đợi THẬT tới 15 PHÚT cho một
      yêu cầu không bao giờ thành công -> treo dây chuyền từng video;
  (b) đường CHÉP LỜI (mọi video đều đi qua) cũng khoá key khi gặp 413.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="lienthong_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
# 2 key GIẢ (cổng này KHÔNG gọi mạng): cần có key trong cấu hình mới dựng được
# bẫy "mọi key đang cooldown" — soonest_ready_wait chỉ xét key CÓ trong settings,
# không có key nào thì nó trả None và hàm báo lỗi ngay (đúng, khỏi đợi vô ích).
os.environ["GROQ_API_KEYS"] = "gsk_kiemthu_mot,gsk_kiemthu_hai"
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  ✅ {ten}" + (f" — {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} — {ct}")
        print(f"  ❌ {ten} — {ct}")


from pathlib import Path  # noqa: E402

from app import services  # noqa: E402
from app.ai import llm  # noqa: E402
from app.core import vision_digest as VD  # noqa: E402
from app.database.db import db  # noqa: E402
from app.modules import m1_highlight as M  # noqa: E402

LOI_413 = ("Error code: 413 - {'error': {'message': 'Request too large for "
           "model `x` in organization `org_x` service tier `on_demand` on "
           "tokens per minute (TPM): Limit 8000, Requested 8632, please reduce "
           "your message size and try again. Visit "
           "https://console.groq.com/docs/rate-limits for more information.', "
           "'code': 'rate_limit_exceeded'}}")

# ══════════ 1. NÂNG CẤP DB trên dữ liệu ĐANG CHẠY quy mô 300 kênh ══════════
print("\n=== 1. Nâng cấp DB: 300 kênh / 1.800 clip / 207 mẫu ===")
t0 = time.time()
con = db.conn()
for i in range(300):
    con.execute("INSERT INTO projects(name,assets_dir,grp) VALUES(?,?,?)",
                (f"Kênh {i}", os.path.join(T, f"k{i}"), "Mỹ" if i % 2 else "Việt"))
for i in range(600):
    con.execute("INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)",
                ((i % 300) + 1, os.path.join(T, f"v{i}.mp4"), 900.0))
for i in range(1800):
    con.execute(
        "INSERT INTO clips(video_id,title,start_sec,end_sec,status,signals,"
        "transcript) VALUES(?,?,?,?,'suggested',?,?)",
        ((i % 600) + 1, f"Clip {i}", 10.0 * i, 10.0 * i + 70.0,
         '{"segments":[[1,2]]}', "loi thoai mau"))
for i in range(207):
    con.execute("INSERT INTO presets(module,name,data) VALUES('m1',?,?)",
                (f"Mẫu {i}", '{"cap_preset":"Trắng đơn giản"}'))
con.commit()
dem = {t: db.query_one(f"SELECT COUNT(*) AS n FROM {t}")["n"]
       for t in ("projects", "videos", "clips", "presets")}
print(f"    dựng xong {dem} trong {time.time()-t0:.1f}s")
# giả lập DB CŨ: xoá bảng mới rồi mở lại -> bước nâng cấp phải tự dựng lại
db.execute("DROP TABLE IF EXISTS clip_gu")
co_truoc = bool(db.query_one("SELECT name FROM sqlite_master WHERE "
                             "name='clip_gu'"))
ok(not co_truoc, "1a đã giả lập được DB CŨ (chưa có bảng clip_gu)")
t0 = time.time()
db.init_schema()                    # ĐÚNG cảnh MỞ APP: init_schema mới nâng cấp
dt_mig = time.time() - t0
sau = {t: db.query_one(f"SELECT COUNT(*) AS n FROM {t}")["n"]
       for t in dem}
ok(sau == dem, "1b nâng cấp KHÔNG mất dòng nào", f"trước {dem} · sau {sau}")
ok(bool(db.query_one("SELECT name FROM sqlite_master WHERE name='clip_gu'")),
   "1c bảng clip_gu được dựng lại")
ok(dt_mig < 2.0, "1d nâng cấp nhanh (không làm app khởi động lâu)",
   f"{dt_mig*1000:.0f}ms")
for _ in range(3):                  # mở app nhiều lần -> không nổ, không nhân bản
    db.init_schema()
_n_idx = db.query_one("SELECT COUNT(*) AS n FROM sqlite_master WHERE "
                      "type='index' AND name='idx_clipgu_clip'")["n"]
ok(_n_idx == 1, "1e mở app 4 lần -> chỉ 1 chỉ mục (bước nâng cấp lặp lại được)",
   f"{_n_idx}")
_t0 = time.time()
_ = services.gu_cua_kenh(7)
ok(time.time() - _t0 < 0.05, "1f đọc gu của 1 kênh vẫn nhanh với DB 300 kênh",
   f"{(time.time()-_t0)*1000:.1f}ms")

# ══════════ 2. TÊN MẪU không được rò vào mẫu lưu trên đĩa ══════════
print("\n=== 2. `_ten_mau` là dấu TẠM, không được lưu vào mẫu ===")
from app.ui.studio_page import StudioPage  # noqa: E402

sp = StudioPage.__new__(StudioPage)
sp.layout_tpl = {"cap_preset": "Trắng đơn giản", "video_rect": [0, 0, 1, 1]}
services.save_template("Mẫu Gốc", {"cap_preset": "Ô sáng chạy từ (đa màu)",
                                   "video_rect": [0, 0, 1, 1]})
pid = 1
services.set_project_template(pid, "Mẫu Gốc")
t1 = sp._tpl_for_project(pid)
ok(t1.get("_ten_mau") == "Mẫu Gốc", "2a bản sao CÓ dấu tên (để ghi nhật ký)")
# user mở Chỉnh mẫu rồi Lưu trong lúc bản sao đang mang dấu -> KHÔNG được lưu dấu
services.save_template("Mẫu Gốc", t1)
_lai = services.get_template("Mẫu Gốc") or {}
ok("_ten_mau" not in _lai,
   "2b lưu mẫu -> dấu tạm bị GỠ, mẫu trên đĩa vẫn sạch", str(list(_lai)[:6]))
ok(_lai.get("cap_preset") == "Ô sáng chạy từ (đa màu)",
   "2c nội dung mẫu không bị hỏng khi gỡ dấu")

# ══════════ 3. LỖI 413 KHÔNG ĐƯỢC TREO DÂY CHUYỀN ══════════
print("\n=== 3. 413 không treo dây chuyền, không đốt key ===")
# BẪY CẦN DỰNG: phải có key ĐANG COOLDOWN, vì chỉ khi đó nhánh "đợi hết lượt"
# mới có cái để đợi. Dùng key THẬT trong cấu hình (key giả không nằm trong
# settings.groq_keys() nên soonest_ready_wait bỏ qua -> không dựng được bẫy).
from config import settings as _stt28  # noqa: E402
_keys = list(_stt28.groq_keys() or [])
_K = _keys[0] if _keys else ("gsk_" + "z" * 20)
llm.mark_limited("groq", _K, "429 rate limit, try again in 200s")
_truoc_cho = llm.soonest_ready_wait("groq")
print(f"    (key đang cooldown -> nhánh đợi sẽ chờ {_truoc_cho}s nếu không chặn)")


class _Ctx:
    def progress(self, *a, **k):
        pass

    def check_canceled(self):
        pass


def _nem_413():
    raise llm.LLMTooLarge(f"Yêu cầu quá lớn: {LOI_413}")


t0 = time.time()
try:
    M._call_waiting_quota(_nem_413, _Ctx(), "groq")
    _da_nem = False
except llm.LLMError:
    _da_nem = True
dt = time.time() - t0
ok(_da_nem and dt < 1.0,
   "3a 413 -> BÁO NGAY, không đợi 15 phút dù có key đang cooldown",
   f"{dt*1000:.0f}ms (nhánh đợi sẽ là {_truoc_cho}s)")


def _nem_413_thuong():           # lỗi 413 gói trong LLMError thường
    raise llm.LLMError(f"Vision groq lỗi: {LOI_413}")


t0 = time.time()
try:
    M._call_waiting_quota(_nem_413_thuong, _Ctx(), "groq")
    _n2 = False
except llm.LLMError:
    _n2 = True
ok(_n2 and time.time() - t0 < 1.0,
   "3b 413 gói trong LLMError thường cũng KHÔNG bị đợi",
   f"{(time.time()-t0)*1000:.0f}ms")
# 429 THẬT thì vẫn phải đợi (không được sửa quá tay)
_lan = {"n": 0}


def _429_roi_ok():
    _lan["n"] += 1
    if _lan["n"] == 1:
        raise llm.LLMError("429 rate limit reached, try again in 1s")
    return ["xong"]


# BẪY ĐÚNG: phải khoá HẾT key mới có gì để đợi — còn 1 key rảnh thì
# soonest_ready_wait trả None và hàm báo lỗi NGAY (đúng, khỏi đợi vô ích).
for _k in (_keys or [_K]):
    llm.mark_limited("groq", _k, "429 rate limit, try again in 1s")
_cho1 = llm.soonest_ready_wait("groq")
print(f"    (đã khoá {len(_keys or [_K])} key, chờ ngắn nhất {_cho1}s)")
t0 = time.time()
try:
    _ra = M._call_waiting_quota(_429_roi_ok, _Ctx(), "groq", budget=30.0)
    ok(_ra == ["xong"] and _lan["n"] == 2,
       "3c 429 THẬT vẫn đợi rồi thử lại (không phá tính năng cũ)",
       f"gọi {_lan['n']} lần / {time.time()-t0:.1f}s")
except llm.LLMError as e:
    ok(False, "3c 429 THẬT vẫn đợi rồi thử lại", str(e)[:120])

# ══════════ 4. 413 ở đường CHÉP LỜI: không khoá key, lùi whisper máy ══════════
print("\n=== 4. 413 ở đường CHÉP LỜI (mọi video đều đi qua) ===")
_tsrc = Path(REPO, "app", "core", "transcribe.py").read_text(
    encoding="utf-8", errors="replace")
_i413 = _tsrc.find("is_too_large_error")
_irate = _tsrc.find("if llm.is_rate_limit_error(last)")
ok(0 < _i413 < _irate,
   "4a nhánh 413 đặt TRƯỚC nhánh hết-lượt (nếu sau thì vô tác dụng)")
ok("LLMTooLarge" in _tsrc, "4b chép lời ném LLMTooLarge, không mark_limited")
# caller phải BẮT được -> lùi whisper máy, không làm video thành _Loi
_j = _tsrc.find("_transcribe_groq(audio_path, None, on_progress)")
ok("except Exception" in _tsrc[_j:_j + 260],
   "4c nơi gọi vẫn bắt mọi lỗi -> lùi chép lời bằng MÁY, video không vào _Loi")

# ══════════ 5. HUỶ giữa lúc AI xem hình phải dừng ngay ══════════
print("\n=== 5. Bấm Huỷ giữa lúc AI xem hình ===")
from app.queue.worker import CanceledError  # noqa: E402


class _CtxHuy:
    def __init__(self, sau=1):
        self.n = 0
        self.sau = sau

    def progress(self, *a, **k):
        pass

    def check_canceled(self):
        self.n += 1
        if self.n >= self.sau:
            raise CanceledError("user bấm Huỷ")


_v = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                "VALUES(?,?,?)", (1, os.path.join(T, "khong-co.mp4"),
                                  600.0)).lastrowid
_ctxh = _CtxHuy(sau=1)
try:
    VD.build_vision_digest(_v, os.path.join(T, "khong-co.mp4"), 600.0,
                           ctx=_ctxh, bat_buoc=True)
    ok(True, "5a file không tồn tại -> trả rỗng êm (không nổ)")
except CanceledError:
    ok(True, "5a Huỷ -> CanceledError nổi lên (không bị nuốt)")
except Exception as e:  # noqa: BLE001
    ok(False, "5a huỷ/thiếu file phải êm", f"{type(e).__name__}: {e}")
_vsrc = Path(REPO, "app", "core", "vision_digest.py").read_text(
    encoding="utf-8", errors="replace")
ok(_vsrc.find("except CanceledError") < _vsrc.find("except Exception as e:  "
                                                   "# noqa: BLE001 - lỗi khác"),
   "5b `except CanceledError` đặt TRƯỚC `except Exception` (không nuốt lệnh Huỷ)")

# ══════════ 6. model KHÁC không nhận reasoning_effort -> vẫn chạy ══════════
print("\n=== 6. Đổi model vision khác -> không được chết vì reasoning_effort ===")
_lsrc = Path(REPO, "app", "ai", "llm.py").read_text(
    encoding="utf-8", errors="replace")
ok('reasoning_effort="none"' in _lsrc, "6a có dùng reasoning_effort=none")
ok('if "reasoning_effort" not in str(e_re):' in _lsrc and "raise" in _lsrc,
   "6b có đường gọi LẠI khi model không nhận tham số đó")
ok(_lsrc.count("max_tokens=2600") >= 1,
   "6c đường dự phòng nới max_tokens (model suy luận cần chỗ nghĩ)")

# ══════════ 7. bỏ khối <think> KHÔNG phá các đường JSON cũ ══════════
print("\n=== 7. Bất biến: JSON của model CŨ vẫn bóc đúng ===")
_MAU_THINK = ("<think>" + chr(10) + "nhap [1,2,3]" + chr(10)
              + "</think>" + chr(10) + '[{"i":0,"desc":"ok","act":9}]')
MAU = [
    ('[{"start":10,"end":70,"title":"a"}]', list, "mảng thuần"),
    ('```json\n{"clips":[{"start":1,"end":2}]}\n```', dict, "bọc ```json"),
    ('Đây là kết quả:\n[{"index":0,"score":80}]', list, "có chữ dẫn trước"),
    ('{"parts":[{"mode":"orig","start":1,"end":2}]}', dict, "object recap"),
    ('[{"i":0,"desc":"x <think> trong chuỗi","act":3}]', list,
     "chữ '<think>' NẰM TRONG dữ liệu"),
    (_MAU_THINK, list, "model suy luận: có khối nghĩ đóng đủ"),
]
for raw, kieu, nhan in MAU:
    try:
        d = llm._extract_json(raw)
        ok(isinstance(d, kieu) and d, f"7 {nhan} -> vẫn bóc đúng {kieu.__name__}",
           str(d)[:70])
    except Exception as e:  # noqa: BLE001
        ok(False, f"7 {nhan}", f"{type(e).__name__}: {e}")

# ══════════ 8. Thẻ clip thêm 2 nút -> KHÔNG tràn hàng ══════════
print("\n=== 8. Thẻ clip có 2 nút mới mà không tràn hàng ===")
from PyQt6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402

_app.setStyleSheet(theme.QSS)
_cid = db.query_one("SELECT id FROM clips LIMIT 1")["id"]
_c = dict(db.query_one("SELECT * FROM clips WHERE id=?", (_cid,)))
_c["status"] = "exported"
_c["export_path"] = os.path.join(T, "ra.mp4")


class _St2:
    project_id = 1
    video_id = 1


sp2 = StudioPage.__new__(StudioPage)
sp2.state = _St2()
sp2.layout_tpl = {}
try:
    w = sp2._clip_card(_c, 1) if hasattr(sp2, "_clip_card") else None
except Exception as e:  # noqa: BLE001
    w = None
    print(f"    (không dựng được thẻ trực tiếp: {type(e).__name__}) -> đo qua nhãn")
from PyQt6.QtWidgets import QPushButton  # noqa: E402

if w is not None:
    nut = w.findChildren(QPushButton)
    tong = sum(b.sizeHint().width() for b in nut)
    ok(len(nut) >= 6, f"8a thẻ có {len(nut)} nút (đã thêm Hay/Nhạt)",
       str([b.text() for b in nut]))
    ok(tong <= 900, "8b tổng bề rộng nút vừa khung 1080 (không tràn)",
       f"{tong}px")
else:
    _u = Path(REPO, "app", "ui", "studio_page.py").read_text(
        encoding="utf-8", errors="replace")
    # ĐÃ ĐỔI 07/08/2026: bản đầu đặt CỨNG 52px và ĐÓ CHÍNH LÀ LỖI — ảnh anh
    # Hùng cho thấy nút ra "Hav"/"Nha" vì máy anh font to hơn máy dev. Nay bề
    # rộng đo theo fontMetrics lúc chạy (`_vua_chu`); cổng 31
    # `_test_nut_khong_cut.py` canh riêng chuyện cụt chữ ở 3 cỡ font.
    ok("_vua_chu(" in _u and "b.setFixedWidth(52)" not in _u,
       "8a nút thẻ clip đo bề rộng THEO FONT, không còn số cứng 52px")
    ok(_u.count('b.setFixedHeight(28)') >= 1,
       "8b nút mới cùng chiều cao 28px với nút cũ (không lệch hàng)")

# ══════════ 9. LUỒNG THẬT: dạy gu -> prompt chọn đoạn có ví dụ ══════════
print("\n=== 9. Luồng THẬT: bấm Nhạt -> prompt lần cắt sau CÓ ví dụ ===")
from app.ai import chon_doan as CD  # noqa: E402

_cl = db.query("SELECT id FROM clips WHERE video_id=1 LIMIT 2")
for r in _cl:
    services.dat_gu_clip(r["id"], -1)
_gu = services.gu_cua_kenh(1)
_khoi = CD.khoi_prompt_gu(_gu)
ok(len(_gu["khong"]) == 2 and "KHÔNG THÍCH" in _khoi,
   "9a gu vào được khối prompt", f"{len(_khoi)} ký tự")
_msrc = Path(REPO, "app", "modules", "m1_highlight.py").read_text(
    encoding="utf-8", errors="replace")
_i_gu = _msrc.find("khoi_prompt_gu")
_i_goi = _msrc.find("nghe_xem=_khoi_nghe_xem")
ok(0 < _i_gu < _i_goi,
   "9b khối gu được cộng vào TRƯỚC lúc gọi AI chọn đoạn (nếu sau thì vô dụng)")
# gu của kênh KHÁC không được lẫn vào
ok(CD.khoi_prompt_gu(services.gu_cua_kenh(2)) == "",
   "9c kênh khác vẫn prompt y hệt cũ (không rò gu)")

# ══════════ 10. TIẾNG ĐỘNG: loại mới có đủ tham số trong bộ xuất ══════════
print("\n=== 10. Loại tiếng mới phải chạy được tới ffmpeg ===")
from app.core import ffmpeg_utils as FU  # noqa: E402

_kho = FU._sfx_library() or {}
for _cat in ("impact", "pop", "transition", "reveal", "riser"):
    ok(_cat in FU.SFX_CATEGORIES and (_kho.get(_cat) or []),
       f"10 nhóm '{_cat}': có trong bộ xuất + có file thật",
       f"{len(_kho.get(_cat) or [])} file")
_cats = M._context_join_categories([(300.0, 305.0), (10.0, 60.0)], {}, seed=1)
_chuan = [c if c in FU.SFX_CATEGORIES else "transition" for c in _cats]
ok(_cats == _chuan, "10f loại do m1 sinh ra KHÔNG bị ffmpeg đổi thầm sang mặc định",
   f"{_cats}")

print(f"\n{'='*62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 28 ĐẠT — các luồng khớp nhau, 413 không treo/không đốt key")
