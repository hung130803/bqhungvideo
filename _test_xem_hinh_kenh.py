# -*- coding: utf-8 -*-
r"""CỔNG 51 — AI XEM HÌNH BẬT/TẮT RIÊNG THEO TỪNG KÊNH (`projects.xem_hinh`).

Anh Hùng 09/08/2026: *"cứ thêm phần bật tuỳ chỉnh từng kênh đã, tôi test xem
sao, nếu oke thì mặc định tất cả"*.

VÌ SAO PHẢI CÓ Ô NÀY (đo A/B 60 lượt thật, 6 video × 5 vòng × 2 bên, đan xen):
  video 728 s (12 mốc hình) -> lựa chọn CHỒNG LẤN chỉ 6,8%  (p=0,024)
  video 150 s ( 8 mốc)      -> chồng lấn 23,4%              (p=0,008)
  video  53 s ( 3 mốc)      -> chồng lấn 100% = chọn Y HỆT bản KHÔNG xem hình
Tức xem hình ĐỔI LỰA CHỌN THẬT, nhưng chỉ khi video đủ dài để có đủ mốc; và
giá chỉ +1,6..+10,6 giây/video — TRỪ 1 video dính Groq 503 'over capacity' cả
5/5 vòng: **+244 giây**.

CỔNG NÀY KIỂM KẾT QUẢ, KHÔNG KIỂM Ý ĐỊNH:
  CA 1  ba trạng thái NULL/1/0 sống được qua DB (kể cả DB cũ chưa có cột)
  CA 2  BẤT BIẾN: kênh CHƯA ĐỤNG (NULL) -> quyết định Y HỆT v2.21.0, so với
        `git show <mốc>:app/core/vision_digest.py` (KHÔNG so với `main` —
        sau khi gộp, `main` chính là mã đang test nên cổng tự PASS OAN)
  CA 3  kênh BẬT vs TẮT -> ĐƯỜNG CHẠY KHÁC NHAU THẬT (đếm lượt gọi vision +
        số mốc digest), ffmpeg + DB THẬT
  CA 4  áp ở MỌI đường phân tích, không riêng dây chuyền (lỗi (a) của cổng 19)
  CA 5  gán 1 lượt chỉ đụng kênh ĐANG HIỆN (Huỷ · No · kênh bị lọc ra ·
        2 kênh TRÙNG TÊN khác nhóm chỉ 1 cái đổi — lỗi thật của cổng 29)
  CA 6  nguồn quá ngắn (< 8 mốc) -> BỎ QUA + ghi `logs/vision_<ngày>.log`
  CA 7  Groq 503 -> bỏ trong ngưỡng · 0 KEY BỊ KHOÁ · clip VẪN RA
  CA 8  nhãn giao diện KHÔNG EMOJI + cột nằm đúng chỗ trong bảng Dây chuyền

CHẠY:
    .venv\Scripts\python.exe _test_xem_hinh_kenh.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

T = tempfile.mkdtemp(prefix="xhkenh_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
# KEY GIẢ, KHÔNG GỌI MẠNG: `llm.vision_available()` chỉ cần "có key + có model"
# nên đây đủ để mở cửa vision; mọi lượt gọi thật đều bị thay bằng bộ đếm bên
# dưới. (Bẫy của cổng 28: key bịa NGOÀI settings thì các hàm tra sổ key trả
# None và cổng PASS OAN — nên phải đặt qua ENV để settings đọc được.)
os.environ["GROQ_API_KEYS"] = ",".join(f"gsk_test{i:02d}" + "z" * 20
                                       for i in range(4))
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


from config import DATA_DIR, settings  # noqa: E402
from app.ai import llm  # noqa: E402
from app.core import vision_digest as VD  # noqa: E402

#: mốc đối chứng = commit ĐÃ PHÁT HÀNH v2.21.0. KHÔNG dùng `main`: sau khi gộp
#: nhánh này, `main` chính là mã đang test -> "so nó với chính nó" -> cổng PASS
#: OAN vĩnh viễn (đã xảy ra thật với `_test_hlbox.py`, xem CLAUDE.md).
MOC = os.environ.get("BQ_MOC_XH", "378230e")


def _git(*a) -> str:
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 1. BA trạng thái: NULL (chưa đụng) · 1 (bật) · 0 (tắt) ===")
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402

p_a = services.create_project("Kenh A", "My")
ok(services.project_vision(p_a) is None,
   "1a kênh mới -> None = CHƯA ĐỤNG TỚI (không phải False)",
   repr(services.project_vision(p_a)))
services.set_project_vision(p_a, True)
ok(services.project_vision(p_a) is True, "1b đặt BẬT -> True")
services.set_project_vision(p_a, False)
ok(services.project_vision(p_a) is False, "1c đặt TẮT -> False")
services.set_project_vision(p_a, None)
ok(services.project_vision(p_a) is None,
   "1d bỏ lựa chọn -> QUAY VỀ None (đổi được mặc định toàn cục sau này)")
_col = db.query("SELECT xem_hinh FROM projects WHERE id=?", (p_a,))
ok(_col and _col[0]["xem_hinh"] is None,
   "1e cột trong DB đúng là NULL, KHÔNG bị ép về 0",
   repr(_col[0]["xem_hinh"] if _col else "?"))
ok(services.project_vision(10 ** 9) is None and
   services.project_vision("rác") is None,
   "1f kênh không tồn tại / id rác -> None, KHÔNG ném lỗi")

# DB CŨ (chưa có cột) phải nâng cấp được, 0 dòng mất
import sqlite3  # noqa: E402

_old = os.path.join(T, "cu.db")
_c = sqlite3.connect(_old)
_c.executescript(open(os.path.join(REPO, "app", "database", "schema.sql"),
                      encoding="utf-8").read())
_c.execute("INSERT INTO projects(name, assets_dir) VALUES('Kenh cu','x')")
_c.commit()
_c.close()
from app.database.db import Database  # noqa: E402

_db2 = Database(_old)
_db2.conn()
_r2 = _db2.query("SELECT id, name, xem_hinh FROM projects")
ok(len(_r2) == 1 and _r2[0]["name"] == "Kenh cu" and _r2[0]["xem_hinh"] is None,
   "1g DB CŨ nâng cấp: giữ đủ dòng, kênh cũ ra NULL (theo mặc định app)",
   f"{len(_r2)} dòng · xem_hinh={_r2[0]['xem_hinh'] if _r2 else '?'}")

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 2. BẤT BIẾN: kênh chưa đụng (NULL) -> Y HỆT v2.21.0 ===")
_ref_src = _git("show", f"{MOC}:app/core/vision_digest.py")
ok(len(_ref_src) > 2000, f"2a lấy được bản mốc {MOC}", f"{len(_ref_src)} ký tự")
_cur_src = open(os.path.join(REPO, "app", "core", "vision_digest.py"),
                encoding="utf-8").read()
ok(_ref_src.replace("\r\n", "\n") != _cur_src.replace("\r\n", "\n"),
   "2b bản mốc KHÁC bản đang test (chống 'so nó với chính nó' -> PASS OAN)")

import importlib.util  # noqa: E402

_rp = os.path.join(T, "vd_moc.py")
open(_rp, "w", encoding="utf-8").write(_ref_src)
_sp = importlib.util.spec_from_file_location("vd_moc_v221", _rp)
VD_MOC = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(VD_MOC)

_that = []          # ma trận (USE_VISION, VISION_CUT, LIGHT_MODE, bat_buoc)
_lech = []
_goc = (settings.USE_VISION, getattr(settings, "VISION_CUT", False),
        getattr(settings, "LIGHT_MODE", True))
for uv in (True, False):
    for vc in (True, False):
        for lm in (True, False):
            for bb in (True, False):
                settings.USE_VISION = uv
                settings.VISION_CUT = vc
                settings.LIGHT_MODE = lm
                a = VD_MOC.vision_digest_enabled(bb)
                b = VD.vision_digest_enabled(bb, None)     # kênh CHƯA ĐỤNG
                _that.append((uv, vc, lm, bb, a, b))
                if a != b:
                    _lech.append((uv, vc, lm, bb, a, b))
settings.USE_VISION, settings.VISION_CUT, settings.LIGHT_MODE = _goc
ok(not _lech,
   f"2c {len(_that)}/{len(_that)} tổ hợp cài đặt: NULL cho ra ĐÚNG quyết định "
   f"của v2.21.0", f"lệch {len(_lech)}: {_lech[:3]}")
# và nó KHÔNG phải cổng rỗng: kênh có đặt thì PHẢI khác bản mốc ít nhất 1 chỗ
settings.USE_VISION, settings.VISION_CUT, settings.LIGHT_MODE = True, False, True
ok(VD_MOC.vision_digest_enabled(False) is False
   and VD.vision_digest_enabled(False, True) is True,
   "2d TỰ KIỂM BỘ DÒ: cùng cài đặt đó, kênh BẬT ra True còn v2.21.0 ra False "
   "(nếu chỗ này bằng nhau thì CA 2c chỉ là con dấu)")
settings.USE_VISION, settings.VISION_CUT, settings.LIGHT_MODE = _goc

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 3. Kênh BẬT vs TẮT -> ĐƯỜNG CHẠY KHÁC NHAU THẬT ===")
# Nguồn THẬT bằng ffmpeg của repo (không phụ thuộc file trên máy). 170 giây để
# vượt ngưỡng 8 mốc: app rải ~20 s/khung nên 170 s -> 9 mốc.
SRC = os.path.join(T, "nguon170.mp4")
_rc = subprocess.run(
    [settings.FFMPEG_PATH, "-y", "-v", "error", "-f", "lavfi",
     "-i", "testsrc2=size=128x72:rate=5", "-t", "170",
     "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", SRC],
    capture_output=True, text=True)
ok(os.path.exists(SRC) and os.path.getsize(SRC) > 1000,
   "3a dựng được nguồn 170 s bằng ffmpeg THẬT của repo",
   f"rc={_rc.returncode} · {os.path.getsize(SRC) if os.path.exists(SRC) else 0} byte")

# BỘ ĐẾM thay cho lượt gọi mạng: cổng phải TIỀN ĐỊNH và không đốt lượt Groq
# thật. Cái đang đo là ĐƯỜNG CHẠY (có gọi hay không, gọi mấy lượt), không phải
# chất lượng mô tả — phần đó là việc của cổng 26 (có gọi Groq thật).
GOI = {"n": 0, "anh": 0}
_goc_vision = llm.complete_vision_json


def _dem(prompt, paths, **kw):
    GOI["n"] += 1
    GOI["anh"] += len(paths)
    return [{"i": i, "desc": f"scene {i} action shot", "act": 7}
            for i in range(len(paths))]


llm.complete_vision_json = _dem


def _lam_video(pid, dur=170.0, src=SRC):
    return db.execute("INSERT INTO videos(project_id, src_path, duration) "
                      "VALUES(?,?,?)", (pid, src, dur)).lastrowid


settings.USE_VISION = True
settings.VISION_CUT = False          # MẶC ĐỊNH APP = TẮT (đúng bản đang phát hành)
settings.LIGHT_MODE = True
settings.VISION_SONG_SONG = 1

p_tat = services.create_project("Kenh TAT", "My")
p_bat = services.create_project("Kenh BAT", "My")
p_null = services.create_project("Kenh CHUA DUNG", "My")
services.set_project_vision(p_tat, False)
services.set_project_vision(p_bat, True)

GOI["n"] = GOI["anh"] = 0
d_null = VD.build_vision_digest(_lam_video(p_null), SRC, 170.0)
n_null = GOI["n"]
GOI["n"] = GOI["anh"] = 0
d_tat = VD.build_vision_digest(_lam_video(p_tat), SRC, 170.0)
n_tat = GOI["n"]
GOI["n"] = GOI["anh"] = 0
d_bat = VD.build_vision_digest(_lam_video(p_bat), SRC, 170.0)
n_bat, a_bat = GOI["n"], GOI["anh"]

ok(n_null == 0 and d_null == [],
   "3b kênh CHƯA ĐỤNG + mặc định TẮT -> 0 lượt gọi, digest rỗng (y hệt v2.21.0)",
   f"{n_null} lượt · {len(d_null)} mốc")
ok(n_tat == 0 and d_tat == [],
   "3c kênh TẮT riêng -> 0 lượt gọi", f"{n_tat} lượt")
ok(n_bat > 0 and len(d_bat) >= 8,
   "3d kênh BẬT riêng -> GỌI THẬT và ra >= 8 mốc hình",
   f"{n_bat} lượt · {a_bat} ảnh · {len(d_bat)} mốc")
ok(len(d_bat) != len(d_tat) and n_bat != n_tat,
   "3e BẬT và TẮT ra ĐƯỜNG CHẠY KHÁC NHAU THẬT (không phải chỉ khác cái nhãn)",
   f"BẬT {n_bat} lượt/{len(d_bat)} mốc  vs  TẮT {n_tat} lượt/{len(d_tat)} mốc")
# và digest đó THẬT SỰ chảy vào prompt chọn đoạn (nếu không thì bật cũng vô nghĩa)
_khoi = VD.format_digest_block(d_bat)
ok(_khoi and "HÌNH ẢNH THEO MỐC" in _khoi and VD.format_digest_block(d_tat) == "",
   "3f digest của kênh BẬT ra khối chữ cho prompt; kênh TẮT ra khối RỖNG "
   "(prompt y hệt cũ)", f"{len(_khoi)} ký tự vs 0")

# mặc định toàn cục BẬT + kênh TẮT riêng -> kênh vẫn TẮT (ô của kênh nói cuối)
settings.VISION_CUT = True
GOI["n"] = 0
d2 = VD.build_vision_digest(_lam_video(p_tat), SRC, 170.0)
ok(GOI["n"] == 0 and d2 == [],
   "3g mặc định toàn cục BẬT nhưng kênh chọn TẮT -> vẫn KHÔNG xem hình",
   f"{GOI['n']} lượt")
GOI["n"] = 0
d3 = VD.build_vision_digest(_lam_video(p_null), SRC, 170.0)
ok(GOI["n"] > 0 and len(d3) >= 8,
   "3h đổi MẶC ĐỊNH toàn cục sang BẬT -> kênh chưa đụng TỰ ĐI THEO "
   "(đúng lý do cột để NULL)", f"{GOI['n']} lượt · {len(d3)} mốc")
settings.VISION_CUT = False

# VIDEO KHÔNG CÓ LỜI: tự bật, KHÔNG phụ thuộc ô của kênh
GOI["n"] = 0
d4 = VD.build_vision_digest(_lam_video(p_tat), SRC, 170.0, bat_buoc=True)
ok(GOI["n"] > 0 and len(d4) >= 8,
   "3i video KHÔNG CÓ LỜI (bat_buoc) vẫn tự xem hình dù kênh chọn TẮT "
   "(hình là căn cứ duy nhất còn lại)", f"{GOI['n']} lượt · {len(d4)} mốc")

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 4. Áp ở MỌI đường phân tích, không riêng dây chuyền ===")
import inspect  # noqa: E402

from app.modules import m1_highlight as M1  # noqa: E402
from app.modules import m2_recap as M2  # noqa: E402

_s1, _s2 = inspect.getsource(M1), inspect.getsource(M2)
ok("nen_xem_hinh" in _s1,
   "4a m1 (CẮT THƯỜNG — dây chuyền LẪN bấm tay) dùng gate có ô của kênh")
ok("nen_xem_hinh" in _s2, "4b m2 (REUP thuyết minh) cũng dùng gate đó")
def _ma_that(src: str, mau: str) -> list:
    """Dòng **MÃ CHẠY ĐƯỢC** có chứa `mau` — bỏ COMMENT và mọi CHUỖI.

    KHÔNG lọc bằng `startswith('#')`: chính DÒNG GHI CHÚ giải thích bản vá này
    có nhắc tên hàm cũ, và cổng đã ĐỎ OAN vì thế đúng một lượt (cùng bẫy mà
    cổng 47 đã sập). `tokenize` cho biết đúng loại từng token."""
    import io
    import tokenize
    dong = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            dong.setdefault(tok.start[0], []).append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return [f"KHÔNG PHÂN TÍCH ĐƯỢC {mau}"]
    return ["".join(v).strip() for _n, v in sorted(dong.items())
            if mau in "".join(v)]


_sot = []
for _root, _ds, _fs in os.walk(os.path.join(REPO, "app")):
    for _f in _fs:
        if not _f.endswith(".py"):
            continue
        _p = os.path.join(_root, _f)
        if os.path.relpath(_p, REPO).replace("\\", "/") \
                == "app/core/vision_digest.py":
            continue                      # nơi ĐỊNH NGHĨA, không tính
        if _ma_that(open(_p, encoding="utf-8", errors="replace").read(),
                    "vision_digest_enabled("):
            _sot.append(os.path.relpath(_p, REPO))
ok(not _sot,
   "4c KHÔNG nơi nào còn gọi thẳng `vision_digest_enabled()` (bỏ qua ô của "
   "kênh) — lỗi (a) của cổng 19 là áp mỗi ở dây chuyền", str(_sot))
# TỰ KIỂM BỘ DÒ (không thì 4c chỉ là con dấu): nó phải BẮT được mã thật và
# BỎ QUA ghi chú/chuỗi nói về đúng cái tên đó.
ok(_ma_that("x = vision_digest_enabled(1)\n", "vision_digest_enabled(") and
   not _ma_that("# goi vision_digest_enabled( o day\n"
                "s = 'vision_digest_enabled('\n", "vision_digest_enabled("),
   "4c' bộ dò bắt MÃ THẬT, tha GHI CHÚ và CHUỖI (bẫy đỏ-oan của cổng 47)")
# CỬA DUY NHẤT: dù caller quên hết, build_vision_digest vẫn tự tra ô của kênh
_sig = inspect.signature(VD.build_vision_digest)
ok("kenh" in _sig.parameters,
   "4d `build_vision_digest` tự tra ô của kênh (caller quên cũng không lọt)")
GOI["n"] = 0
_v_quen = _lam_video(p_tat)
VD.build_vision_digest(_v_quen, SRC, 170.0)      # gọi Y HỆT kiểu cũ, không kenh=
ok(GOI["n"] == 0,
   "4e gọi kiểu CŨ (không truyền gì) vẫn tôn trọng kênh TẮT", f"{GOI['n']} lượt")

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 6. Nguồn quá ngắn (< 8 mốc) -> BỎ QUA + ghi nhật ký ===")
ok(VD.MOC_TOI_THIEU == 8, "6a ngưỡng là HẰNG SỐ đặt tên rõ, dễ chỉnh",
   f"MOC_TOI_THIEU={VD.MOC_TOI_THIEU}")
_moc = {d: len(VD.pick_frame_times(float(d))) for d in (53, 150, 728)}
ok(_moc == {53: 3, 150: 8, 728: 12},
   "6b số mốc app tính ra KHỚP đúng bộ A/B (53s->3 · 150s->8 · 728s->12)",
   str(_moc))
SRC_NGAN = os.path.join(T, "ngan53.mp4")
subprocess.run(
    [settings.FFMPEG_PATH, "-y", "-v", "error", "-f", "lavfi",
     "-i", "testsrc2=size=128x72:rate=5", "-t", "53",
     "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
     SRC_NGAN], capture_output=True)
_logd = DATA_DIR / "logs"
_truoc = ""
from datetime import datetime  # noqa: E402

_lg = _logd / f"vision_{datetime.now():%Y%m%d}.log"
if _lg.exists():
    _truoc = _lg.read_text(encoding="utf-8")
GOI["n"] = 0
d_ngan = VD.build_vision_digest(_lam_video(p_bat, 53.0, SRC_NGAN), SRC_NGAN,
                                53.0)
ok(GOI["n"] == 0 and d_ngan == [],
   "6c kênh ĐANG BẬT nhưng nguồn 53 s (3 mốc) -> 0 lượt gọi, không tốn giây nào",
   f"{GOI['n']} lượt")
_sau = _lg.read_text(encoding="utf-8") if _lg.exists() else ""
_them = _sau[len(_truoc):]
ok("BỎ QUA" in _them and "3 mốc" in _them,
   "6d ghi LÝ DO vào logs/vision_<ngày>.log (không im lặng)",
   _them.strip().splitlines()[-1][-105:] if _them.strip() else "(rỗng)")
# nguồn ĐỦ DÀI vẫn phải chạy — ngưỡng không được chặn nhầm
GOI["n"] = 0
d_du = VD.build_vision_digest(_lam_video(p_bat), SRC, 170.0)
ok(GOI["n"] > 0 and len(d_du) >= 8,
   "6e nguồn 170 s (9 mốc) KHÔNG bị chặn nhầm", f"{GOI['n']} lượt")
# video KHÔNG LỜI thì nguồn ngắn vẫn xem (hình là căn cứ duy nhất)
GOI["n"] = 0
VD.build_vision_digest(_lam_video(p_bat, 53.0, SRC_NGAN), SRC_NGAN, 53.0,
                       bat_buoc=True)
ok(GOI["n"] > 0,
   "6f video KHÔNG LỜI + nguồn ngắn -> VẪN xem (3 mốc còn hơn không có gì)",
   f"{GOI['n']} lượt")

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 7. Groq 503 'over capacity' -> bỏ sớm · 0 key khoá · clip vẫn ra ===")
LOI_503 = ("Error code: 503 - {'error': {'message': 'Service Unavailable: the "
           "model is over capacity, please try again later', 'type': "
           "'server_error'}}")
ok(VD.la_loi_qua_tai(LOI_503), "7a nhận ra 503 quá tải")
ok(not VD.la_loi_qua_tai("Error code: 413 - Request too large ... rate_limit_"
                         "exceeded"),
   "7b 413 KHÔNG bị nhận nhầm là quá tải (413 có đường thu nhỏ riêng)")
ok(not VD.la_loi_qua_tai("Error code: 429 - Rate limit reached, try again in 4.2s"),
   "7c 429 thật KHÔNG bị nhận nhầm (429 vẫn phải đợi + phạt key như cũ)")
ok(not llm.is_rate_limit_error(LOI_503),
   "7d 503 KHÔNG khớp is_rate_limit_error -> tầng llm không phạt key")

llm._KEY_STATE.clear()


def _luon_503(prompt, paths, **kw):
    GOI["n"] += 1
    for _k in settings.groq_keys():
        llm.mark_used("groq", _k)
    raise llm.LLMError("Vision groq lỗi: " + LOI_503)


llm.complete_vision_json = _luon_503
GOI["n"] = 0
import time as _time  # noqa: E402

_t0 = _time.perf_counter()
d_503 = VD.build_vision_digest(_lam_video(p_bat), SRC, 170.0)
_dt = _time.perf_counter() - _t0
_n_batch_du = (len(VD.pick_frame_times(170.0)) + VD._BATCH - 1) // VD._BATCH
ok(GOI["n"] <= VD.VISION_503_TOI_DA,
   f"7e dừng trong ngưỡng {VD.VISION_503_TOI_DA} lượt 503 (không nướng hết "
   f"{_n_batch_du} lượt như bản cũ)", f"{GOI['n']}/{_n_batch_du} lượt · {_dt:.2f}s")
_khoa = [k for (pv, k), st in llm._KEY_STATE.items()
         if pv == "groq" and st.get("state") == "limited"]
ok(not _khoa, "7f 0/4 KEY BỊ KHOÁ (503 ≠ hết lượt — đốt key là chết dây chuyền)",
   f"{len(_khoa)} key limited")
ok(d_503 == [] and isinstance(d_503, list),
   "7g trả [] ÊM, không ném lỗi lên đường cắt", repr(d_503)[:40])
_sau2 = _lg.read_text(encoding="utf-8") if _lg.exists() else ""
ok("503" in _sau2 or "QUÁ TẢI" in _sau2,
   "7h ghi lý do quá tải vào nhật ký",
   _sau2.strip().splitlines()[-1][-105:] if _sau2.strip() else "(rỗng)")
# quá GIỜ cũng phải cắt (503 chậm rề chứ không hẳn lỗi). Chốt này ĐỘC LẬP với
# số lượt 503 nên đặt trần 503 rất cao rồi đẩy lùi mốc bắt đầu.
_chot = VD._ChotQuaTai(han_giay=25.0, so_503=99)
_chua = _chot.nen_dung()
_chot.moc -= 26.0            # giả lập "đã ngốn 26 giây"
ok(not _chua and _chot.nen_dung() and "quá 25s" in _chot.ly_do,
   "7i quá ngân sách GIÂY cũng cắt (chốt thứ hai, độc lập số lượt 503)",
   _chot.ly_do[:80])
ok(20.0 <= VD.VISION_HAN_GIAY <= 40.0 and VD.VISION_503_TOI_DA >= 1,
   "7i' hai ngưỡng là HẰNG SỐ đặt tên rõ, dễ chỉnh",
   f"VISION_HAN_GIAY={VD.VISION_HAN_GIAY} · "
   f"VISION_503_TOI_DA={VD.VISION_503_TOI_DA}")
# và digest CỤT không được đóng dấu vào cache (Groq quá tải là chuyện 5 phút)
_v_cut = _lam_video(p_bat)


def _503_sau_1(prompt, paths, **kw):
    GOI["n"] += 1
    if GOI["n"] > 1:
        raise llm.LLMError("Vision groq lỗi: " + LOI_503)
    return [{"i": i, "desc": "first batch ok", "act": 5} for i in range(len(paths))]


llm.complete_vision_json = _503_sau_1
GOI["n"] = 0
d_cut = VD.build_vision_digest(_v_cut, SRC, 170.0)
from app.core.analysis import get_analysis  # noqa: E402

ok(len(d_cut) > 0 and get_analysis(_v_cut, VD.VD_KIND) is None,
   "7j digest CỤT dùng cho lượt này nhưng KHÔNG đóng dấu cache (lần sau còn "
   "thử lại được)", f"{len(d_cut)} mốc · cache={get_analysis(_v_cut, VD.VD_KIND)}")

# ---- CLIP VẪN RA: chạy generate_highlights THẬT với vision 503 ----
llm.complete_vision_json = _luon_503
from app.core.analysis import _set as set_analysis  # noqa: E402

_v_clip = _lam_video(p_bat)
_words = []
_sents = []
for _i in range(60):
    _t = _i * 2.8
    _sents.append({"start": _t, "end": _t + 2.6,
                   "text": f"Cau noi thu {_i} ke ve chuyen bat ngo xay ra."})
set_analysis(_v_clip, "transcript", "done",
             {"language": "vi", "text": " ".join(s["text"] for s in _sents),
              "segments": _sents, "words": _words}, engine="test")
_goc_text = llm.complete_text


def _text_chet(*a, **k):
    raise llm.LLMError("mang chet (co y de test luoi cuoi)")


llm.complete_text = _text_chet
llm.complete_json = _text_chet


class _Ctx:
    def __init__(self):
        self.dong = []

    def progress(self, p, m=""):
        self.dong.append(m)

    def check_canceled(self):
        return False


_ctx = _Ctx()
_loi_clip = ""
try:
    _res = M1.generate_highlights(
        {"video_id": _v_clip,
         "preset": {"count": 2, "min_len": 15.0, "max_len": 45.0}}, _ctx)
except Exception as _e:  # noqa: BLE001
    _res, _loi_clip = {}, f"{type(_e).__name__}: {_e}"
llm.complete_text, llm.complete_json = _goc_text, _goc_text
ok(int(_res.get("count", 0)) > 0 and not _loi_clip,
   "7k CLIP VẪN RA: Groq vision 503 + LLM chữ chết -> vẫn cắt được clip "
   "(lưới cuối heuristic)", f"count={_res.get('count')} {_loi_clip}")
_khoa2 = [k for (pv, k), st in llm._KEY_STATE.items()
          if pv == "groq" and st.get("state") == "limited"]
ok(not _khoa2, "7l sau cả lượt cắt thật: vẫn 0 key bị khoá",
   f"{len(_khoa2)} key limited")
llm.complete_vision_json = _goc_vision

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 5. Gán 1 lượt: chỉ đụng kênh ĐANG HIỆN ===")
from PyQt6.QtWidgets import (QApplication, QDialog, QInputDialog,  # noqa: E402
                             QMessageBox, QPushButton, QWidget)

_DLG: list = []
QDialog.exec = lambda self: (_DLG.append(self), 0)[1]
_MB: list = []
QMessageBox.exec = lambda self: (_MB.append(self), 0)[1]
QMessageBox.information = staticmethod(lambda *a, **k: 0)
_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

_app.setStyleSheet(theme.QSS)

# 3 nhóm + 2 kênh TRÙNG TÊN khác nhóm (bẫy đã sập ở cổng 29: tra id THEO TÊN)
NHOM = {}
for _g, _n in (("Han", 5), ("Nhat", 4)):
    NHOM[_g] = [services.create_project(f"{_g} Ch {i}", _g) for i in range(_n)]
tr_han = services.create_project("Prison Doc", "Han")
tr_nhat = services.create_project("Prison Doc", "Nhat")
NHOM["Han"].append(tr_han)
NHOM["Nhat"].append(tr_nhat)
MOI_PID = NHOM["Han"] + NHOM["Nhat"]
for _p in MOI_PID:
    services.set_project_vision(_p, None)

sp = StudioPage.__new__(StudioPage)
QWidget.__init__(sp)          # thiếu bước này QMessageBox(self) nổ (cổng 29)
sp.status = QPushButton("")
sp._pipe_fill = lambda: None
# BẢNG "đang hiện" = nhóm Hàn (mô phỏng user đang lọc nhóm Hàn)
sp._pipe_rows_pid = lambda: [(p, "") for p in NHOM["Han"]]


def _dem_bat(ds):
    return sum(1 for p in ds if services.project_vision(p) is True)


def _dem_dat(ds):
    return sum(1 for p in ds if services.project_vision(p) is not None)


# -- Huỷ ở hộp chọn --
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))
sp._pipe_bulk_xem_hinh()
ok(_dem_dat(MOI_PID) == 0, "5a Huỷ ở hộp chọn -> 0 kênh bị đụng",
   f"{_dem_dat(MOI_PID)} kênh")

# -- No ở hộp xác nhận --
QInputDialog.getItem = staticmethod(
    lambda *a, **k: ("BẬT AI xem hình", True))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
sp._pipe_bulk_xem_hinh()
ok(_dem_dat(MOI_PID) == 0, "5b bấm No ở hộp xác nhận -> 0 kênh bị đụng",
   f"{_dem_dat(MOI_PID)} kênh")

# -- Yes -> chỉ nhóm ĐANG HIỆN --
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
sp._pipe_bulk_xem_hinh()
ok(_dem_bat(NHOM["Han"]) == len(NHOM["Han"]),
   "5c bấm Yes -> mọi kênh ĐANG HIỆN (nhóm Hàn) được BẬT",
   f"{_dem_bat(NHOM['Han'])}/{len(NHOM['Han'])}")
ok(_dem_dat(NHOM["Nhat"]) == 0,
   "5d kênh bị LỌC RA (nhóm Nhật) KHÔNG bị đụng — vẫn NULL",
   f"{_dem_dat(NHOM['Nhat'])} kênh nhóm Nhật bị đổi")
ok(services.project_vision(tr_han) is True
   and services.project_vision(tr_nhat) is None,
   "5e 2 kênh TRÙNG TÊN khác nhóm: CHỈ kênh nhóm Hàn đổi "
   "(bản tra-id-theo-tên sẽ sai đúng chỗ này)",
   f"Han={services.project_vision(tr_han)} Nhat={services.project_vision(tr_nhat)}")

# -- đặt TẮT rồi trả về mặc định --
QInputDialog.getItem = staticmethod(lambda *a, **k: ("TẮT AI xem hình", True))
sp._pipe_bulk_xem_hinh()
ok(all(services.project_vision(p) is False for p in NHOM["Han"]),
   "5f đặt TẮT 1 lượt cho nhóm đang hiện")
_nhan_md = [x for x in ("Theo mặc định app (TẮT)", "Theo mặc định app (BẬT)")]
QInputDialog.getItem = staticmethod(
    lambda *a, **k: (a[3][0] if len(a) > 3 and a[3] else _nhan_md[0], True))
sp._pipe_bulk_xem_hinh()
ok(all(services.project_vision(p) is None for p in NHOM["Han"]),
   "5g trả về '(theo mặc định app)' -> quay lại NULL, không kẹt ở 0/1",
   str([services.project_vision(p) for p in NHOM["Han"]][:3]))
# bảng trống -> báo, không nổ
sp._pipe_rows_pid = lambda: []
QInputDialog.getItem = staticmethod(lambda *a, **k: ("BẬT AI xem hình", True))
sp._pipe_bulk_xem_hinh()
ok(_dem_dat(MOI_PID) == 0, "5h bảng không hiện kênh nào -> báo + không đổi gì")
sp._pipe_rows_pid = lambda: [(p, "") for p in NHOM["Han"]]
ok(sp._pipe_apply_xem_hinh_all(True) == len(NHOM["Han"]),
   "5i hàm áp trả ĐÚNG số kênh đã đổi", str(len(NHOM["Han"])))
for _p in MOI_PID:
    services.set_project_vision(_p, None)

# ══════════════════════════════════════════════════════════════════════
print("\n=== CA 8. Giao diện: cột đúng chỗ · nhãn KHÔNG EMOJI ===")
_ui = open(os.path.join(REPO, "app", "ui", "studio_page.py"),
           encoding="utf-8").read()
_i0 = _ui.find('["✓", "Kênh", "Nhóm", "Chế độ", "Mẫu"')
_hdr = _ui[_i0:_ui.find("]", _i0) + 1] if _i0 > 0 else ""
ok("AI xem hình" in _hdr, "8a bảng Dây chuyền có cột 'AI xem hình'", _hdr[:96])
ok("QTableWidget(0, 10)" in _ui,
   "8b bảng khai đúng 10 cột (thêm 1 so với 9 cột của v2.21.0)")
_EMO = "🎨🔧⋮📋✕👁🖼👍👎📁🗑🔁🔄✓⏳✅🔴⚠🤖▶"
_nhan_moi = ["AI xem hình", "BẬT xem hình", "TẮT xem hình",
             "Bật/tắt AI xem hình cho MỌI kênh đang hiện…",
             "BẬT AI xem hình", "TẮT AI xem hình"]
_xau = [n for n in _nhan_moi if any(c in n for c in _EMO)]
ok(not _xau, "8c mọi NHÃN MỚI đều là chữ thuần (máy anh Hùng thiếu glyph "
              "-> ô đen)", str(_xau))
ok("_XH_MD_NHAN" in _ui and "(mặc định: " in _ui,
   "8d mục đầu của ô chọn NÓI RÕ mặc định đang là BẬT hay TẮT "
   "(bài học cổng 16 v2.6.25a)")
ok("_pipe_bulk_xem_hinh() if c == 5" in _ui,
   "8e bấm TIÊU ĐỀ cột 'AI xem hình' = gán 1 lượt (như cột 'Mẫu')")
ok("_pipe_rows_pid" in _ui.split("def _pipe_apply_xem_hinh_all")[1][:900],
   "8f đường gán 1 lượt lấy kênh từ BẢNG -> tự tôn trọng nhóm + ô tìm")

print(f"\n{'=' * 62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 51 ĐẠT — AI xem hình bật/tắt theo TỪNG KÊNH; kênh chưa đụng "
      "chạy y hệt v2.21.0; bỏ qua khi vô ích; 503 không đốt key")
