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
goi_cu = [n for n in ast.walk(m1) if isinstance(n, ast.Call)
          and getattr(n.func, "attr", "") in ("nang_luong", "chuyen_dong")]
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

print(f"\nKẾT QUẢ: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
