# -*- coding: utf-8 -*-
"""CỔNG 99 — APP KHÔNG ĐƯỢC LÀM NGHẼN Ổ CỨNG CƠ + KHÔNG DỊCH LẠI MÃ MỖI LẦN MỞ.

Gốc (đo trên máy anh Hùng 31/10/2026, anh kêu "app đơ, bot mở app mãi không
mở được"): ổ D: là ổ cứng CƠ, hàng đợi đĩa 14-19, mỗi lần đọc chờ ~138 ms.
  * pha phân tích đọc TRỌN mỗi video gốc 3 lần; 2 lượt đo gọi ffmpeg thẳng
    không qua cửa chờ nào, cửa chờ ffmpeg thì riêng TỪNG tiến trình -> 8 lệnh
    ffmpeg của app cùng đọc file GB một lúc;
  * bản .exe chạy thẳng mã nguồn dịch thử 139 file (26,5 giây CPU) MỖI lần mở
    app và MỖI tiến trình phân tích con, rồi lại dịch lần nữa lúc import vì
    không ghi bộ đệm .pyc (nạp giao diện 9,0 s, có bộ đệm 0,95 s).

Cổng này canh:
  1. `chon_doan.nghe_va_xem` (1 lượt đọc) ra SỐ GIỐNG HỆT 2 hàm cũ — ffmpeg
     THẬT, nguồn có tiếng + nguồn KHÔNG tiếng (phải lùi về đường cũ).
  2. `cua_doc_dia.giu_cho` là cửa CHUNG MỌI TIẾN TRÌNH: 4 tiến trình thật, 2
     chỗ -> không bao giờ quá 2 cùng lúc; tiến trình bị GIẾT khi đang giữ chỗ
     thì chỗ tự nhả; Huỷ lúc đang đợi thì rời hàng ngay; ổ không quay -> không
     chặn gì.
  3. 3 chỗ đọc trọn video gốc đều đi qua cửa (quét AST).
  4. `_nguon_song.bat()` chỉ dịch thử file ĐÃ ĐỔI; file lỗi cú pháp vẫn bị
     chặn và KHÔNG được ghi vào sổ "đã kiểm" (chạy ở tiến trình con vì bat()
     gỡ module app khỏi sys.modules).
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
import _test_guard  # noqa: E402,F401  (cổng 17: mọi test nhắc MainWindow phải có canh cổng)
T = Path(tempfile.mkdtemp(prefix="muot_o_cung_"))
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "t.db")
FF = str(GOC / "bin" / "ffmpeg.exe")
if not os.path.exists(FF):
    from config import settings as _s
    FF = _s.FFMPEG_PATH

DAT = HONG = 0


def ok(dk: bool, ten: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


def ma_that(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


# ───────────────────────── MỤC 1: nghe_va_xem = 2 hàm cũ ─────────────────────
print("MỤC 1 — một lượt đọc ra số GIỐNG HỆT hai lượt cũ")
from app.ai import chon_doan as cd  # noqa: E402

nguon = T / "co_tieng.mp4"
subprocess.run([FF, "-y", "-v", "quiet",
                "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=24",
                "-f", "lavfi", "-i",
                "sine=frequency=330:duration=24,volume='if(lt(mod(t,6),1.2),1.0,0.05)':eval=frame",
                "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
                str(nguon)], check=True)
cu_nl = cd.nang_luong(str(nguon), FF)
cu_cd = cd.chuyen_dong(str(nguon), FF)
moi_nl, moi_cd = cd.nghe_va_xem(str(nguon), FF)
ok(len(cu_nl) > 10 and len(cu_cd) > 10, "1a hai hàm cũ đo được (thước có răng)",
   f"nl {len(cu_nl)} giá trị · cd {len(cu_cd)} giá trị")
ok(moi_nl == cu_nl, "1b mức âm từng giây GIỐNG HỆT", f"{len(moi_nl)} vs {len(cu_nl)}")
ok(moi_cd == cu_cd, "1c độ động từng giây GIỐNG HỆT", f"{len(moi_cd)} vs {len(cu_cd)}")
ok(max(cu_nl) / max(1e-9, min(v for v in cu_nl if v > 0)) > 5,
   "1d nguồn có cao trào thật (không so hai dãy phẳng)")

cam = T / "khong_tieng.mp4"
subprocess.run([FF, "-y", "-v", "quiet", "-f", "lavfi", "-i",
                "testsrc2=size=320x240:rate=25:duration=10", "-c:v", "libx264",
                "-preset", "ultrafast", str(cam)], check=True)
c2 = (cd.nang_luong(str(cam), FF), cd.chuyen_dong(str(cam), FF))
m2 = cd.nghe_va_xem(str(cam), FF)
ok(m2 == c2, "1e video KHÔNG tiếng -> lùi về đường cũ, kết quả y hệt",
   f"nl {len(m2[0])} · cd {len(m2[1])}")

# đếm số lần mở file nguồn: phải là 1 lệnh ffmpeg (trước: 2)
goi = []
_run_that = subprocess.run


def _dem(cmd, *a, **k):
    if cmd and str(cmd[0]).lower().endswith("ffmpeg.exe") or "ffmpeg" in str(cmd[0]).lower():
        goi.append(cmd)
    return _run_that(cmd, *a, **k)


cd.subprocess.run = _dem
try:
    cd.nghe_va_xem(str(nguon), FF)
finally:
    cd.subprocess.run = _run_that
ok(len(goi) == 1, "1f nghe + xem = ĐÚNG 1 lệnh ffmpeg đọc nguồn", f"{len(goi)} lệnh")

# ───────────────────────── MỤC 2: cửa chờ đĩa chung mọi tiến trình ───────────
print("MỤC 2 — cửa chờ đọc đĩa dùng chung MỌI tiến trình")
from app.core import cua_doc_dia as cdd  # noqa: E402

ok(cdd.o_quay(r"C:\Windows") in (True, False, None), "2a hỏi Windows không nổ",
   f"C: quay={cdd.o_quay(r'C:\Windows')} · D: quay={cdd.o_quay('D:\\')}")

CON = textwrap.dedent(r"""
    import os, sys, time, json
    sys.path.insert(0, sys.argv[1])
    from app.core import cua_doc_dia as c
    c._CACHE_QUAY[sys.argv[2][:2].upper()] = True      # ép coi là ổ quay
    with c.giu_cho(sys.argv[2]):
        vao = time.time()
        with open(sys.argv[3], "a") as h:     # DẤU "đã vào" cho mục 2e/2f/2g (chỉ 1 tiến trình)
            h.write("vao\n")
        time.sleep(float(sys.argv[4]))
        ra = time.time()
    # MỖI tiến trình MỘT file (31/10/2026): 4 tiến trình cùng ghi NỐI vào một
    # file trên Windows làm MẤT/CHÈN HỎNG dòng -> hồi quy đo ra "7 sự kiện ·
    # đỉnh 3" và một lượt chết không in kết quả, trong khi cửa chờ vẫn đúng.
    # Mốc "ra" lấy TRƯỚC khi nhả chỗ nên không thể chồng lên "vào" của người sau.
    with open(sys.argv[3] + "." + str(os.getpid()), "w") as h:
        h.write(json.dumps([["vao", os.getpid(), vao], ["ra", os.getpid(), ra]]))
""")
con_py = T / "tien_trinh_giu_cho.py"  # KHÔNG đặt "con.py": CON là tên THIẾT BỊ Windows
con_py.write_text(CON, encoding="utf-8")
so = T / "so.jsonl"
env = dict(os.environ, BQ_DOC_DIA_SLOTS="2")
t0 = time.time()
ps = [subprocess.Popen([sys.executable, str(con_py), str(GOC), r"D:\gia.mp4", str(so), "1.5"],
                       env=env) for _ in range(4)]
[p.wait(timeout=60) for p in ps]
dt = time.time() - t0
ev = [e for f in sorted(T.glob("so.jsonl.*")) for e in json.loads(f.read_text())]
dong = cao = 0
for kind, _, _ in sorted(ev, key=lambda e: (e[2], e[0] == "vao")):
    dong += 1 if kind == "vao" else -1
    cao = max(cao, dong)
ok(len(ev) == 8, "2b cả 4 tiến trình đều vào và ra", f"{len(ev)} sự kiện")
ok(cao == 2, "2c KHÔNG BAO GIỜ quá 2 tiến trình đọc cùng lúc", f"đỉnh {cao}")
ok(dt >= 2.9, "2d thật sự phải xếp hàng (4 việc × 1,5s / 2 chỗ >= 3s)", f"{dt:.2f}s")

# tiến trình bị GIẾT khi đang giữ chỗ -> chỗ tự nhả
so2 = T / "so2.jsonl"
env1 = dict(os.environ, BQ_DOC_DIA_SLOTS="1")
p = subprocess.Popen([sys.executable, str(con_py), str(GOC), r"D:\gia.mp4", str(so2), "60"],
                     env=env1)
for _ in range(100):
    if so2.exists() and so2.read_text().strip():
        break
    time.sleep(0.1)
p.kill(); p.wait()
os.environ["BQ_DOC_DIA_SLOTS"] = "1"
cdd._CACHE_QUAY["D:"] = True
t1 = time.time()
with cdd.giu_cho(r"D:\gia.mp4", kiem_huy=lambda: None):
    cho = time.time() - t1
ok(cho < 2.0, "2e tiến trình bị GIẾT khi đang giữ chỗ -> chỗ TỰ NHẢ", f"đợi {cho:.2f}s")

# Huỷ lúc đang đợi -> rời hàng ngay
class Huy(Exception):
    pass


so3 = T / "so3.jsonl"
p = subprocess.Popen([sys.executable, str(con_py), str(GOC), r"D:\gia.mp4", str(so3), "6"],
                     env=env1)
for _ in range(100):
    if so3.exists() and so3.read_text().strip():
        break
    time.sleep(0.1)
dem = {"n": 0}


def _huy():
    dem["n"] += 1
    if dem["n"] >= 3:
        raise Huy()


t2 = time.time()
try:
    with cdd.giu_cho(r"D:\gia.mp4", kiem_huy=_huy):
        roi = "VÀO được (sai)"
except Huy:
    roi = "rời hàng"
ok(roi == "rời hàng" and time.time() - t2 < 2, "2f bấm Huỷ lúc đang đợi -> rời hàng ngay",
   f"{roi} sau {time.time()-t2:.2f}s")
bao = []
p2 = None
try:
    with cdd.giu_cho(r"D:\gia.mp4", bao=bao.append,
                     kiem_huy=lambda: (_ for _ in ()).throw(Huy()) if len(bao) >= 2 else None):
        pass
except Huy:
    pass
ok(any("đang đợi lượt đọc ổ D" in b for b in bao), "2g đang đợi thì BÁO cho thanh tiến trình",
   (bao[:1] or ["(không báo)"])[0])
p.kill(); p.wait()

# ổ không quay -> không chặn (2 người cùng giữ 1 chỗ vẫn vào ngay)
cdd._CACHE_QUAY["Q:"] = False
t3 = time.time()
with cdd.giu_cho(r"Q:\a.mp4"):
    with cdd.giu_cho(r"Q:\b.mp4"):
        pass
ok(time.time() - t3 < 0.2, "2h ổ SSD/không quay -> KHÔNG chặn gì (y hệt trước)")
cdd._CACHE_QUAY["D:"] = True
with cdd.giu_cho(r"D:\a.mp4", kiem_huy=lambda: None):
    try:
        with cdd.giu_cho(r"D:\b.mp4", kiem_huy=lambda: (_ for _ in ()).throw(Huy())):
            trong = "vào (sai)"
    except Huy:
        trong = "phải đợi"
ok(trong == "phải đợi", "2i cùng tiến trình, 2 luồng, 1 chỗ -> luồng thứ 2 phải đợi")
os.environ.pop("BQ_DOC_DIA_SLOTS", None)

# ───────────────────────── MỤC 3: mọi chỗ đọc trọn nguồn qua cửa ─────────────
print("MỤC 3 — chỗ đọc TRỌN video gốc đều đi qua cửa chờ đĩa")


def _with_goi(tree: ast.AST, ten_ham: str) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == ten_ham:
            for w in ast.walk(n):
                if isinstance(w, ast.With):
                    for it in w.items:
                        c = it.context_expr
                        if isinstance(c, ast.Call) and getattr(c.func, "id", getattr(c.func, "attr", "")) in ("giu_cho", "_giu_doc"):
                            return True
    return False


ok(_with_goi(ma_that(GOC / "app" / "core" / "ffmpeg_utils.py"), "extract_audio_wav_why"),
   "3a tách tiếng (extract_audio_wav_why) giữ chỗ đọc đĩa")
ok(_with_goi(ma_that(GOC / "app" / "ai" / "chon_doan.py"), "nghe_va_xem"),
   "3b nghe + xem giữ chỗ đọc đĩa")
m1 = ma_that(GOC / "app" / "modules" / "m1_highlight.py")
# 13/11/2026: khi MUSE BẬT, `_chi_nghe` chỉ đo TIẾNG (file tiếng đã tách trên ổ C,
# lùi về luồng tiếng của video gốc TRONG `giu_cho`) và BỎ hẳn đo chuyển động ->
# vẫn tối đa 1 lượt đọc video gốc. Lời gọi `nang_luong` nằm trong hàm đó là hợp lệ;
# `chuyen_dong` thì cấm ở mọi chỗ.
_cn = [f for f in ast.walk(m1) if isinstance(f, ast.FunctionDef) and f.name == "_chi_nghe"]
_trong_cn = {id(n) for f in _cn for n in ast.walk(f)}
goi_cu = [n for n in ast.walk(m1) if isinstance(n, ast.Call)
          and (getattr(n.func, "attr", "") == "chuyen_dong"
               or (getattr(n.func, "attr", "") == "nang_luong" and id(n) not in _trong_cn))]
ok(bool(_cn) and _with_goi(m1, "_chi_nghe"),
   "3c' Muse bật: đo tiếng trên video gốc (đường lùi) vẫn GIỮ CHỖ đọc đĩa")
goi_moi = [n for n in ast.walk(m1) if isinstance(n, ast.Call)
           and getattr(n.func, "attr", "") == "nghe_va_xem"]
ok(not goi_cu and goi_moi, "3c m1 dùng 1 lượt `nghe_va_xem`, không gọi lẻ 2 hàm cũ",
   f"gọi cũ {len(goi_cu)} · gọi mới {len(goi_moi)}")
# tự kiểm bộ dò: dựng lại đúng dòng cũ -> phải bắt được
gia = ast.parse("x = _cd_mod.nang_luong(a, b)")
ok(any(getattr(n.func, "attr", "") == "nang_luong" for n in ast.walk(gia) if isinstance(n, ast.Call)),
   "3d TỰ KIỂM BỘ DÒ: lời gọi cũ dựng lại thì bộ dò bắt được")

# ───────────────────────── MỤC 4: nguồn sống chỉ dịch file đã đổi ────────────
print("MỤC 4 — mở app không dịch lại mã đã kiểm")
KIEM = textwrap.dedent(r"""
    import builtins, json, os, sys
    goc_repo, exe_dir = sys.argv[1], sys.argv[2]
    sys.path.insert(0, goc_repo)
    import _nguon_song as ns
    sys.frozen = True
    sys.executable = os.path.join(exe_dir, "BQHungVideo.exe")
    dem = {"n": 0}
    that = builtins.compile
    def dem_compile(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    ns.compile = dem_compile
    kq = ns.bat()
    print(json.dumps({"bat": kq, "dich": dem["n"], "ly_do": ns.LY_DO,
                      "pyc": getattr(sys, "pycache_prefix", None)}))
""")
kiem_py = T / "kiem_ns.py"
kiem_py.write_text(KIEM, encoding="utf-8")
src = T / "nguon"
(src / "app").mkdir(parents=True)
(src / "config.py").write_text("A = 1\n", encoding="utf-8")
(src / "app" / "__init__.py").write_text("", encoding="utf-8")
for i in range(5):
    (src / "app" / f"m{i}.py").write_text(f"X = {i}\n", encoding="utf-8")
exe = T / "exe"
exe.mkdir()
(exe / "nguon_ma.txt").write_text(str(src), encoding="utf-8")


def chay_bat() -> dict:
    r = subprocess.run([sys.executable, str(kiem_py), str(GOC), str(exe)],
                       capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, BQ_DATA_DIR=str(T / "dd")))
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"loi": r.stderr[-400:]}


k1 = chay_bat()
ok(k1.get("bat") is True and k1.get("dich") == 7, "4a lần đầu: dịch thử đủ 7 file", str(k1))
k2 = chay_bat()
ok(k2.get("bat") is True and k2.get("dich") == 0, "4b lần sau, không file nào đổi: dịch 0 file", str(k2))
ok(str(k2.get("pyc") or "").startswith(str(T / "dd")), "4c bật bộ đệm mã vào thư mục dữ liệu",
   str(k2.get("pyc")))
time.sleep(0.05)
(src / "app" / "m3.py").write_text("X = 33  # đổi\n", encoding="utf-8")
k3 = chay_bat()
ok(k3.get("bat") is True and k3.get("dich") == 1, "4d sửa 1 file -> chỉ dịch đúng 1 file", str(k3))
(src / "app" / "m4.py").write_text("def x(:\n", encoding="utf-8")
k4 = chay_bat()
ok(k4.get("bat") is False and "m4.py" in k4.get("ly_do", ""), "4e file LỖI cú pháp vẫn bị chặn", str(k4))
k5 = chay_bat()
ok(k5.get("bat") is False and k5.get("dich") == 1,
   "4f file lỗi KHÔNG được ghi vào sổ đã kiểm (lần sau vẫn dịch lại nó)", str(k5))
(src / "app" / "m4.py").write_text("X = 4\n", encoding="utf-8")
k6 = chay_bat()
ok(k6.get("bat") is True and k6.get("dich") == 1, "4g sửa xong file lỗi -> bật lại", str(k6))

# app/__init__ bật bộ đệm mã cho bản .exe CŨ (chưa đóng gói lại _nguon_song)
init = ma_that(GOC / "app" / "__init__.py")
ok(any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
       and getattr(n.value.func, "id", "") == "_bo_dem_ma_nguon_song" for n in init.body),
   "4h app/__init__.py tự bật bộ đệm mã lúc nạp (bản .exe cũ cũng hưởng)")

# ---- CA 5: mức ưu tiên hệ điều hành của ffmpeg (10/11/2026) ----
# Khâu xuất (UT_XUAT) chạy THƯỜNG; phân tích + mọi lệnh đo nặng chạy
# BELOW_NORMAL. Đo: cùng lượt dựng hình, THƯỜNG 28-34 s vs BELOW_NORMAL 68-236 s.
print("\nCA 5 — mức ưu tiên ffmpeg: xuất THƯỜNG, phân tích/đo BELOW_NORMAL")
import threading as _th5  # noqa: E402
import psutil as _ps5  # noqa: E402
from app.core import ffmpeg_utils as _fu5  # noqa: E402
from app.core import hieu_ung as _hu5  # noqa: E402
BN = 0x00004000
NP = 0x00000020
_roi_that = _fu5.giay_roi_may
_r0 = _roi_that()
ok(_r0 is not None and _r0 >= 0, "5k đọc được số giây rời máy THẬT (GetLastInputInfo)", str(_r0))
_fu5.giay_roi_may = lambda: 3.0
ok(_fu5._muc_uu_tien(_fu5.UT_XUAT) == BN, "5a TỰ ĐỘNG + đang dùng máy -> xuất BELOW_NORMAL (máy mượt)")
_fu5.giay_roi_may = lambda: 999.0
ok(_fu5._muc_uu_tien(_fu5.UT_XUAT) == NP, "5a' TỰ ĐỘNG + rời máy 999 s -> xuất THƯỜNG")
_fu5.giay_roi_may = lambda: None
ok(_fu5._muc_uu_tien(_fu5.UT_XUAT) == BN, "5a'' không đọc được giờ rời máy -> BELOW_NORMAL (an toàn)")
_fu5.giay_roi_may = lambda: 999.0
os.environ["BQ_XUAT_UU_TIEN_THUONG"] = "0"
ok(_fu5._muc_uu_tien(_fu5.UT_XUAT) == BN, "5l ép =0 thì kể cả rời máy vẫn BELOW_NORMAL")
os.environ.pop("BQ_XUAT_UU_TIEN_THUONG")
_fu5.giay_roi_may = lambda: 3.0
ok(_fu5._muc_uu_tien(_fu5.UT_PHAN_TICH) == BN, "5b lệnh PHÂN TÍCH -> BELOW_NORMAL")
os.environ["BQ_XUAT_UU_TIEN_THUONG"] = "1"
ok(_fu5._muc_uu_tien(_fu5.UT_XUAT) == NP, "5c bật BQ_XUAT_UU_TIEN_THUONG=1 -> xuất THƯỜNG")
sys.argv.append("--analyze")
ok(_fu5._muc_uu_tien(_fu5.UT_XUAT) == BN, "5d trong tiến trình phân tích con -> BELOW_NORMAL")
sys.argv.remove("--analyze")
os.environ.pop("BQ_XUAT_UU_TIEN_THUONG")
ok(cd._NO_WIN & BN == BN, "5e lệnh nghe+xem (chon_doan) mang cờ BELOW_NORMAL")


def _muc_that(goi):
    """Chạy THẬT 1 lệnh ffmpeg ~3 s qua `goi`, đọc mức ưu tiên tiến trình con."""
    kq = []
    t = _th5.Thread(target=goi)
    t.start()
    for _ in range(40):
        time.sleep(0.1)
        ff = [p for p in _ps5.Process().children(recursive=True) if p.name().lower() == "ffmpeg.exe"]
        if ff:
            kq.append(ff[0].nice())
            break
    t.join()
    return int(kq[0]) if kq else None


_lenh5 = [_fu5.settings.FFMPEG_PATH, "-v", "error", "-re", "-f", "lavfi",
          "-i", "testsrc2=d=3:s=320x240", "-f", "null", "NUL"]
m_xuat = _muc_that(lambda: _fu5._run(list(_lenh5)))
m_pt = _muc_that(lambda: _fu5._run(list(_lenh5), uu_tien=_fu5.UT_PHAN_TICH))
m_nhip = _muc_that(lambda: _hu5._chay_ffmpeg(list(_lenh5), 30))
ok(m_xuat == BN, "5f CHẠY THẬT: ffmpeg khâu xuất MẶC ĐỊNH là BELOW_NORMAL", str(m_xuat))
ok(m_pt == BN, "5g CHẠY THẬT: ffmpeg phân tích là BELOW_NORMAL", str(m_pt))
ok(m_nhip == BN, "5h CHẠY THẬT: ffmpeg đo nhịp là BELOW_NORMAL", str(m_nhip))

# 5i — lệnh xuất ĐANG CHẠY phải đổi mức theo việc anh rời/quay lại máy
_fu5._CANH_NHIP = 0.3
_trang = {"roi": 3.0}
_fu5.giay_roi_may = lambda: _trang["roi"]
_lenh_dai = list(_lenh5); _lenh_dai[_lenh_dai.index("testsrc2=d=3:s=320x240")] = "testsrc2=d=8:s=320x240"
_th_dai = _th5.Thread(target=lambda: _fu5._run(list(_lenh_dai)))
_th_dai.start()
_ff = None
for _ in range(40):
    time.sleep(0.1)
    _l = [p for p in _ps5.Process().children(recursive=True) if p.name().lower() == "ffmpeg.exe"]
    if _l:
        _ff = _l[0]; break
_dau = _ff.nice() if _ff else None
_trang["roi"] = 999.0
time.sleep(1.5)
_giua = _ff.nice() if _ff else None
_trang["roi"] = 1.0
time.sleep(1.5)
_cuoi = _ff.nice() if _ff else None
_th_dai.join()
ok(_dau == BN, "5i lúc đầu (đang dùng máy) lệnh xuất BELOW_NORMAL", str(_dau))
ok(_giua == NP, "5i' anh rời máy -> lệnh ĐANG CHẠY tự lên THƯỜNG", str(_giua))
ok(_cuoi == BN, "5i'' anh quay lại -> lệnh đang chạy tự về BELOW_NORMAL", str(_cuoi))
time.sleep(1.0)
ok(not _fu5._XUAT_DANG_CHAY and _fu5._CANH_LUONG is None,
   "5m xuất xong -> sổ theo dõi rỗng + luồng canh tự thoát",
   f"{len(_fu5._XUAT_DANG_CHAY)} · {_fu5._CANH_LUONG}")
_fu5.giay_roi_may = _roi_that

# ---- CA 6: NHƯỜNG NHÂN MẠNH khi anh Hùng đang ngồi máy (11/11/2026) ----
# Đo trên máy anh: app vẫn chạy, tiến trình con chỉ ở 8 nhân phụ -> "k đơ giật".
print("\nCA 6 — nhường nhân mạnh: đang dùng máy -> tiến trình con chỉ ở nhân phụ")
import ast as _ast6  # noqa: E402
import subprocess as _sp6  # noqa: E402
from app.core import nhuong_may as _nm  # noqa: E402
_phu, _tat = _nm.nhan_phu_va_tat_ca()
ok(len(_tat) == (os.cpu_count() or 1), "6a đọc đủ mọi nhân logic", f"{len(_tat)}")
_lai = len(_phu) > 0
ok(not _lai or (0 < len(_phu) < len(_tat)), "6b máy hai loại nhân -> nhân phụ là tập con THẬT SỰ",
   f"phụ {_phu}")
_con = _sp6.Popen([_fu5.settings.FFMPEG_PATH, "-v", "error", "-re", "-f", "lavfi", "-i",
                   "testsrc2=d=15:s=160x120", "-f", "null", "NUL"],
                  stdout=_sp6.DEVNULL, stderr=_sp6.DEVNULL, creationflags=0x08000000)
time.sleep(0.5)
_pc = _ps5.Process(_con.pid)
_toi = _ps5.Process()
_mat_toi = sorted(_toi.cpu_affinity())
if _lai:
    _n = _nm.ap_mot_luot(goc=_toi, phu=_phu, tat_ca=_tat, che_do="nhuong")
    ok(_n >= 1 and sorted(_pc.cpu_affinity()) == _nm.mat_na_nhuong(_phu, _tat),
       "6c ĐANG DÙNG MÁY: tiến trình con bị giới hạn vào nhân phụ", f"{_n} · {sorted(_pc.cpu_affinity())}")
    ok(sorted(_toi.cpu_affinity()) == _mat_toi, "6d tiến trình GIAO DIỆN (chính app) KHÔNG bị giới hạn")
    _nm.ap_mot_luot(goc=_toi, phu=_phu, tat_ca=_tat, che_do="het_suc")
    ok(sorted(_pc.cpu_affinity()) == _tat, "6e RỜI MÁY: trả lại MỌI nhân", f"{len(_pc.cpu_affinity())}")
    _fu5.giay_roi_may = lambda: 5.0
    ok(_nm.che_do_bay_gio() == "nhuong", "6f vừa chạm chuột 5 s trước -> nhường")
    _fu5.giay_roi_may = lambda: 999.0
    ok(_nm.che_do_bay_gio() == "het_suc", "6g rời máy 999 s -> hết sức")
    _fu5.giay_roi_may = lambda: None
    ok(_nm.che_do_bay_gio() == "nhuong", "6h không đọc được giờ rời máy -> nhường (an toàn)")
    _fu5.giay_roi_may = _roi_that
else:
    print("  (máy MỘT loại nhân — bỏ qua 6c-6h)")
ok(_nm.ap_mot_luot(goc=_toi, phu=[], tat_ca=_tat, che_do="nhuong") == 0
   and sorted(_pc.cpu_affinity()) == _tat,
   "6i máy MỘT loại nhân (máy nhân viên) -> không đụng gì")
_con.kill(); _con.wait()
os.environ["BQ_NHUONG_MAY"] = "0"
ok(_nm.khoi_dong() is False, "6j BQ_NHUONG_MAY=0 -> không chạy luồng canh")
os.environ.pop("BQ_NHUONG_MAY")
_main = _ast6.parse(Path(__file__).resolve().parent.joinpath("main.py").read_text(encoding="utf-8"))
_goi = [n for n in _ast6.walk(_main) if isinstance(n, _ast6.ImportFrom)
        and n.module == "app.core.nhuong_may" and any(a.name == "khoi_dong" for a in n.names)]
_ham = [n for n in _ast6.walk(_main) if isinstance(n, _ast6.Call)
        and isinstance(n.func, _ast6.Name) and n.func.id == "_nhuong_may"]
ok(bool(_goi) and bool(_ham), "6k main.py THẬT SỰ gọi nhuong_may.khoi_dong lúc mở app")
# bản .exe chạy main.py ĐÓNG GÓI SẴN, chỉ lấy app/ từ mã nguồn -> lời gọi
# trong main.py KHÔNG chạy trên máy anh Hùng (đo 11/11: 0/25 tiến trình con
# bị giới hạn). Cửa sổ chính (app/ui) phải tự gọi.
_mw = _ast6.parse(Path(__file__).resolve().parent.joinpath("app", "ui", "main_window.py").read_text(encoding="utf-8"))
_init = [f for c in _ast6.walk(_mw) if isinstance(c, _ast6.ClassDef) and c.name == "MainWindow"
         for f in c.body if isinstance(f, _ast6.FunctionDef) and f.name == "__init__"]
_goi2 = [n for f in _init for n in _ast6.walk(f) if isinstance(n, _ast6.ImportFrom)
         and n.module == "app.core.nhuong_may" and any(a.name == "khoi_dong" for a in n.names)]
_ham2 = [n for f in _init for n in _ast6.walk(f) if isinstance(n, _ast6.Call)
         and isinstance(n.func, _ast6.Name) and n.func.id == "_nhuong_may"]
ok(bool(_goi2) and bool(_ham2), "6l MainWindow.__init__ (mã nguồn sống) gọi nhuong_may.khoi_dong")

# CA 6m — LỖI THẬT 13/11/2026: "mở lại app" đẻ app MỚI làm CON của app cũ; vòng
# canh của app cũ ghim luôn cửa sổ app mới vào nhân phụ (đo: GUI mở 20:23:31 chạy
# trọn trên [16..23]) và mọi ffmpeg sau đó thừa hưởng mặt nạ đó.
if _lai:
    _gia = _sp6.Popen([sys.executable, "-c", "import time; time.sleep(20)", "--doi-pid", "1"],
                      creationflags=0x08000000)
    time.sleep(0.6)
    _pg = _ps5.Process(_gia.pid)
    _pg.cpu_affinity(_tat)
    _nm.ap_mot_luot(goc=_toi, phu=_phu, tat_ca=_tat, che_do="nhuong")
    ok(sorted(_pg.cpu_affinity()) == _tat,
       "6m app MỚI (--doi-pid) là con của app cũ -> KHÔNG bị ghim vào nhân phụ",
       f"{len(_pg.cpu_affinity())} nhân")
    # tự kiểm bộ dò: bỏ chốt thì tiến trình đó PHẢI bị ghim (phép đo có răng)
    _goc_chot = _nm._la_app_moi
    _nm._la_app_moi = lambda ch: False
    _nm.ap_mot_luot(goc=_toi, phu=_phu, tat_ca=_tat, che_do="nhuong")
    ok(sorted(_pg.cpu_affinity()) == _nm.mat_na_nhuong(_phu, _tat), "6m' tự kiểm: gỡ chốt thì app mới BỊ ghim (bộ dò có răng)")
    _nm._la_app_moi = _goc_chot
    _gia.kill(); _gia.wait()
    _toi.cpu_affinity(_phu)
    ok(_nm.tra_nhan_cho_chinh_minh(_tat) and sorted(_toi.cpu_affinity()) == _tat,
       "6n app ĐÃ bị ghim vào nhân phụ -> tự trả lại mọi nhân cho chính mình")
    ok(not _nm.tra_nhan_cho_chinh_minh(_tat), "6n' đã đủ nhân -> không đụng gì")
    _toi.cpu_affinity(_mat_toi)

print(f"\nKẾT QUẢ: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
