# -*- coding: utf-8 -*-
r"""KIỂM BẢN `.exe` VỪA DỰNG — CHẠY THẬT, KHÔNG CHỈ XEM NGÀY SỬA FILE.

**BẪY PHẢI CHẶN (đã sập 06/08/2026):** gọi PyInstaller bằng `.venv` (venv đó
KHÔNG có PyInstaller) thì lệnh báo lỗi mà `dist/` **VẪN CÒN bản build cũ**, nên
rất dễ tưởng đã build xong. Xem *ngày sửa* `.exe` cũng không cứu được: một lượt
build hỏng nửa đường vẫn để lại `.exe` mới. Thước duy nhất chứng minh **MÃ MỚI
đã vào bản** là **bóc PYZ ra khỏi chính file `.exe`** rồi đọc `app.version.
__version__` + tìm tên module mới.

**CHẠY VỚI `BQ_DATA_DIR` TẠM.** App thật của anh Hùng dùng
`%LOCALAPPDATA%\BQHungVideo`; trỏ vào đó là đụng DB thật. Ở đây trỏ vào thư mục
RỖNG -> vừa an toàn vừa giả lập đúng cảnh MÁY NHÂN VIÊN MỚI.

    .venv-build\Scripts\python.exe -u _kiem_exe_v239.py
"""
from __future__ import annotations

import marshal
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

DIST = REPO / "dist" / "BQHungVideo"
EXE = DIST / "BQHungVideo.exe"
INT = DIST / "_internal"

DAT = 0
HONG = 0


def ok(dieu: bool, ten: str, chi_tiet: str = "") -> bool:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f"   [{chi_tiet}]" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f"   [{chi_tiet}]" if chi_tiet else ""))
    return dieu


# ══════════════════ 1. BÓC PYZ TỪ CHÍNH FILE .exe ══════════════════
def boc_pyz() -> dict:
    """Trả {version, so_module, co: {ten module: bool}}. Đây là phép đo NỘI
    DUNG, thay cho phép đo DẤU THỜI GIAN."""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
    ca = CArchiveReader(str(EXE))
    ten = [n for n in ca.toc if str(n).lower().endswith(".pyz")]
    if not ten:
        return {"loi": "KHÔNG tìm thấy PYZ trong .exe"}
    tmp = REPO / "_kq_pyz_tam.pyz"
    d = ca.extract(ten[0])
    tmp.write_bytes(d[1] if isinstance(d, tuple) else d)
    try:
        z = ZlibArchiveReader(str(tmp))
        toc = set(z.toc)

        def lay(m):
            if m not in toc:
                return None
            o = z.extract(m)
            o = o[1] if isinstance(o, tuple) else o
            return o if hasattr(o, "co_consts") else marshal.loads(o)

        ver = None
        c = lay("app.version")
        if c is not None:
            g: dict = {}
            exec(c, g)                                       # noqa: S102
            ver = g.get("__version__")
        return {"version": ver, "so_module": len(toc),
                "so_app": len([m for m in toc
                               if m == "app" or m.startswith("app.")]),
                "toc": toc}
    finally:
        tmp.unlink(missing_ok=True)


#: Module MỚI của lượt này. Có mặt trong PYZ = mã mới đã vào bản đóng gói.
#: Chọn theo tính năng người dùng bấm được, không chọn bừa.
MODULE_MOI = [
    "app.core.giong_chatter",       # Chatterbox / nhân bản giọng
    "app.core.nhan_ban_giong",      # kho giọng nhân bản
    "app.core.giong_kenh",          # giọng riêng theo kênh + xoay vòng
    "app.core.giong_vieneu",        # 20 giọng VieNeu
    "app.core.giong_vbee",          # 3 giọng Vbee
    "app.core.giong_bang",          # gom nhóm danh sách giọng
    "app.core.giong_mo",            # mở khoá 322 giọng edge-tts
    "app.core.giong_doc",           # biên bản ĐỌC THẬT
    "app.core.giong_hang",          # gióng hàng lấy mốc từng chữ
    "app.core.xoa_an_toan",         # cửa chung chống xoá nhầm
    "app.core.doc_viet_tat",        # đọc viết tắt
]


def main() -> int:                                           # noqa: C901
    print("=" * 78)
    print("KIỂM BẢN .exe VỪA DỰNG — chạy thật + bóc PYZ")
    print("=" * 78)
    if not EXE.is_file():
        print(f"KHÔNG CÓ {EXE} — chưa build.")
        return 2

    st = EXE.stat()
    print(f"exe: {st.st_size:,} byte · sửa lúc "
          f"{time.strftime('%d/%m %H:%M:%S', time.localtime(st.st_mtime))}")

    # ---- 1. NỘI DUNG: version + module mới ----
    print("\n-- 1. BÓC PYZ (thước NỘI DUNG, không phải dấu thời gian) --")
    from app.version import __version__ as ver_nguon
    p = boc_pyz()
    if p.get("loi"):
        ok(False, "bóc được PYZ", p["loi"])
        return 1
    print(f"  PYZ: {p['so_module']:,} module · app.* = {p['so_app']}")
    ok(p["version"] == ver_nguon,
       f"__version__ trong .exe khớp mã nguồn ({ver_nguon})",
       f"trong exe = {p['version']!r}")
    thieu = [m for m in MODULE_MOI if m not in p["toc"]]
    ok(not thieu, f"đủ {len(MODULE_MOI)} module MỚI trong PYZ",
       "thiếu: " + ", ".join(thieu) if thieu else "đủ")

    # ---- 2. TÀI NGUYÊN ----
    print("\n-- 2. TÀI NGUYÊN ĐÓNG GÓI --")
    lic = INT / "LICENSES.txt"
    ok(lic.is_file() and lic.stat().st_size > 5000,
       "LICENSES.txt có mặt và không rỗng",
       f"{lic.stat().st_size:,} byte" if lic.is_file() else "KHÔNG CÓ")
    if lic.is_file():
        chu = lic.read_text(encoding="utf-8", errors="replace").lower()
        # Cổng 39 đã dặn: chỉ hỏi "file có tồn tại không" thì để lại file RỖNG
        # vẫn xanh -> phải đòi nêu ĐÍCH DANH từng thành phần.
        can = ["ffmpeg", "frei0r", "piper", "espeak", "vais1000", "edge-tts",
               "yt-dlp"]
        sot = [c for c in can if c not in chu]
        ok(not sot, "LICENSES.txt nêu ĐÍCH DANH từng thành phần",
           "thiếu: " + ", ".join(sot) if sot else f"đủ {len(can)} mục")

    nguon_sfx = len([x for x in (REPO / "app" / "assets" / "sfx").rglob("*")
                     if x.is_file()])
    dich_sfx = len([x for x in (INT / "app" / "assets" / "sfx").rglob("*")
                    if x.is_file()]) if (INT / "app" / "assets"
                                         / "sfx").is_dir() else 0
    ok(dich_sfx == nguon_sfx and dich_sfx > 0,
       "số file kho tiếng động khớp kho nguồn",
       f"exe {dich_sfx} · nguồn {nguon_sfx}")

    for ten_tn in ("fonts", "hieu_ung"):
        d = INT / "app" / "assets" / ten_tn
        n = len([x for x in d.rglob("*") if x.is_file()]) if d.is_dir() else 0
        ok(n > 0, f"app/assets/{ten_tn} có trong bản đóng gói", f"{n} file")

    for b in ("ffmpeg.exe", "ffprobe.exe"):
        # `bin/` không đi qua .spec (bộ cài kèm riêng) -> chỉ báo, không chấm.
        co = (DIST / "bin" / b).is_file() or (REPO / "bin" / b).is_file()
        print(f"  (ghi nhận) {b}: {'có' if co else 'KHÔNG có trong dist'}")

    # ---- 3. CHẠY THẬT ----
    print("\n-- 3. CHẠY THẬT với BQ_DATA_DIR tạm (giả lập máy nhân viên) --")
    san = REPO / "_kq_exe_san"
    if san.exists():
        shutil.rmtree(san, ignore_errors=True)
    san.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["BQ_DATA_DIR"] = str(san)
    env["BQ_QSETTINGS_INI"] = str(san / "cai_dat.ini")
    env["BQ_DB_PATH"] = str(san / "studio.db")

    truoc = _ffmpeg_dang_chay()
    pr = subprocess.Popen([str(EXE)], cwd=str(DIST), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ram = 0
    luong = 0
    for _ in range(30):                     # tối đa ~30 giây
        time.sleep(1)
        if pr.poll() is not None:
            break
        try:
            import psutil
            q = psutil.Process(pr.pid)
            ram = max(ram, q.memory_info().rss // (1024 * 1024))
            luong = max(luong, q.num_threads())
        except Exception:                                    # noqa: BLE001
            pass
        # Mốc "đã nạp xong": app Qt thật đo được 110 MB / 34 luồng ở bản
        # v2.29.0. Ngưỡng 60 MB + 8 luồng là để KHÔNG chờ đủ 30 giây khi app
        # đã lên, chứ không phải để chấm — mục chấm là `pr.poll() is None`.
        if ram > 60 and luong >= 8:
            break
    con = pr.poll() is None
    ok(con, "mở được và còn sống sau khi nạp xong",
       f"RAM {ram} MB · {luong} luồng"
       + ("" if con else f" · đã thoát rc={pr.poll()}"))

    # error.log PHẢI KHÔNG CÓ
    loi = list(san.rglob("error.log"))
    ok(not loi, "KHÔNG sinh error.log",
       "; ".join(str(x.relative_to(san)) for x in loi) if loi else "sạch")

    # ---- 4. ĐÓNG ÊM + KHÔNG BỎ LẠI MỒ CÔI ----
    print("\n-- 4. ĐÓNG ÊM, KHÔNG BỎ LẠI TIẾN TRÌNH MỒ CÔI --")
    if con:
        subprocess.run(["taskkill", "/PID", str(pr.pid), "/T", "/F"],
                       capture_output=True, timeout=60)
    try:
        rc = pr.wait(timeout=30)
    except Exception:                                        # noqa: BLE001
        rc = None
    out = (pr.stdout.read() or b"").decode("utf-8", "replace") if pr.stdout \
        else ""
    err = (pr.stderr.read() or b"").decode("utf-8", "replace") if pr.stderr \
        else ""
    print(f"  rc khi đóng = {rc}")
    if err.strip():
        print("  stderr (10 dòng đầu):")
        for d in err.strip().splitlines()[:10]:
            print("    " + d)
    ok("Traceback" not in err and "Traceback" not in out,
       "không có Traceback ở stdout/stderr",
       "sạch" if "Traceback" not in err + out else "CÓ Traceback")

    time.sleep(2)
    con_lai = [q for q in _ten_tien_trinh() if "bqhungvideo" in q.lower()]
    ok(not con_lai, "không bỏ lại tiến trình BQHungVideo mồ côi",
       f"{len(con_lai)} tiến trình" if con_lai else "0")
    sau = _ffmpeg_dang_chay()
    print(f"  (ghi nhận) ffmpeg trước {truoc} · sau {sau} — luồng khác trên "
          f"máy cũng chạy ffmpeg nên đây KHÔNG phải mục chấm")

    # log app tự ghi
    for ten_l in ("logs/crash_native.txt",):
        f = san / ten_l
        if f.is_file():
            print(f"  (ghi nhận) {ten_l}: {f.stat().st_size} byte")

    print("\n" + "=" * 78)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 78)
    return 1 if HONG else 0


def _ten_tien_trinh() -> list[str]:
    try:
        import psutil
        return [q.name() for q in psutil.process_iter(["name"])]
    except Exception:                                        # noqa: BLE001
        return []


def _ffmpeg_dang_chay() -> int:
    """ĐẾM THEO TÊN TIẾN TRÌNH, không theo cmdline — lọc cmdline sẽ đếm chính
    lệnh kiểm (mã nguồn có chữ 'ffmpeg') và luôn báo 'đang chạy' (đã báo sai 4
    lần, cổng 37)."""
    return sum(1 for n in _ten_tien_trinh() if n.lower() == "ffmpeg.exe")


if __name__ == "__main__":
    raise SystemExit(main())
