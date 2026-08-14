# -*- coding: utf-8 -*-
"""CỔNG 58 — `_lib` PHẢI TỰ ĐỨNG ĐƯỢC, VÀ PHÉP DÒ PHẢI NÓI THẬT.

LỖI THẬT ANH HÙNG GẶP (14/08/2026): *"trước tôi nhớ báo cài rồi mà nay nó ghi
chưa có bộ tách giọng"*. Đo ra:
· `_lib` CÓ demucs nhưng KHÔNG CÓ torch (và cũng không có soundfile).
· `co_demucs()` bản cũ chèn `_lib` vào `sys.path` rồi hỏi `find_spec` "import
  được không" -> trên máy dev nó **ăn torch của `.venv`** -> trả True, `thieu`
  rỗng -> app báo "đã cài".
· Bản `.exe` không có `.venv` để mượn -> cùng `_lib` đó lại báo "chưa có bộ
  tách giọng". **Máy dev XANH, máy thật ĐỎ, không ai phát hiện.**

Cổng này canh đúng chỗ lệch đó. Mệnh đề trung tâm (CA 1a):

    *danh sách gói THIẾU mà máy DEV nói ra phải GIỐNG HỆT danh sách mà một
    tiến trình KHÔNG có `.venv` (tức bản .exe) nói ra.*

Bản cũ vi phạm mệnh đề này (CA 4 chứng minh bằng cách chạy lại chính mã cũ),
bản mới thì không. Đây là loại cổng "so hai môi trường", không phải cổng đọc
lời hứa trong docstring.

CHẠY: `.venv\\Scripts\\python.exe _test_lib_du.py`
"""
from __future__ import annotations

import sys

# Vá utf-8 TRƯỚC lời gọi `print` ĐẦU TIÊN — chạy hồi quy là
# `python _test_lib_du.py > file.txt`, lúc đó Python lấy cp1252 và dòng tiếng
# Việt đầu tiên ném UnicodeEncodeError (cổng đỏ oan, đã sập nhiều lần).
try:
    sys.stdout.reconfigure(encoding="utf-8")       # type: ignore[union-attr]
except Exception:                                   # noqa: BLE001
    pass

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)         # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

import _test_guard  # noqa: E402,F401  (dọn %TEMP%, chặn mở cửa sổ trên máy user)

from app.core import thay_giong as TG  # noqa: E402

OK = 0
HONG = 0
SAN = Path(REPO) / f"bq_test_lib_{os.getpid()}"      # sandbox NGOÀI %TEMP%


def dat(ten: str, dieu_kien: bool, ghi: str = "") -> None:
    global OK, HONG
    if dieu_kien:
        OK += 1
        print(f"  ĐẠT  {ten}" + (f"  [{ghi}]" if ghi else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f"  [{ghi}]" if ghi else ""))


# ======================================================================
# Bộ đồ nghề: dựng `_lib` giả + chạy phép dò ở TIẾN TRÌNH RIÊNG
# ======================================================================
_RUNNER = r'''# -*- coding: utf-8 -*-
"""Dò bộ tách giọng trong môi trường ĐẶT SẴN — chạy ở tiến trình RIÊNG."""
import json, os, sys, types

repo, kieu, bo_venv = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, repo)
from app.core import thay_giong as TG          # import XONG rồi mới cắt đường

# App thật LÀ app Qt, nên `thiet_bi_tach()` phải thấy Qt đã nạp và trả '' thay
# vì `import torch` (bẫy ACCESS VIOLATION). Giả lập đúng cảnh đó cho nhanh và
# an toàn — cổng này đo phép DÒ, không đo thiết bị.
sys.modules.setdefault("PyQt6", types.ModuleType("PyQt6"))

if bo_venv == "1":
    # GIẢ LẬP BẢN .exe: không có `.venv` site-packages nào để mượn.
    # Cắt SAU khi app đã import xong (bản .exe vẫn có đủ dotenv/PyQt6 trong
    # `_internal`) -> phần khác biệt duy nhất còn lại đúng là chỗ tìm torch.
    sys.path[:] = [p for p in sys.path if "site-packages" not in p.lower()]

if kieu == "cu":
    # ===== BẢN CŨ v2.27.0, chép nguyên si — dùng cho phép THỬ PHÁ =====
    import importlib.util
    from pathlib import Path

    def _mo_duong():
        lib = TG.lib_demucs()
        if lib and lib not in sys.path and Path(lib).is_dir():
            sys.path.insert(0, lib)

    def thieu_cu():
        _mo_duong()
        t = []
        for ten, goi in (("torch", "torch"), ("demucs.pretrained", "demucs"),
                         ("soundfile", "soundfile")):
            try:
                if importlib.util.find_spec(ten) is None:
                    t.append(goi)
            except Exception:
                t.append(goi)
        return t

    tc = thieu_cu()
    ra = {"co": not tc, "thieu": tc, "du_lib": not tc, "nguon": {}}
else:
    tt = TG.tinh_trang_demucs()
    ra = {"co": TG.co_demucs(), "thieu": tt["thieu"], "du_lib": tt["du_lib"],
          "nguon": tt["nguon"]}

sys.stdout.write("BQJSON" + json.dumps(ra, ensure_ascii=False) + "\n")
'''


def lam_stub(lib: Path, *goi: str) -> None:
    """Dựng gói GIẢ trong `lib` — cổng đo phép DÒ, không cần mã chạy được."""
    lib.mkdir(parents=True, exist_ok=True)
    for g in goi:
        if g == "soundfile":                     # bản thật là 1 file .py
            (lib / "soundfile.py").write_text("# stub\n", encoding="utf-8")
            continue
        d = lib / g
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").write_text("# stub\n", encoding="utf-8")
        if g == "demucs":                        # `pretrained.py` = dấu cài ĐỦ
            (d / "pretrained.py").write_text("# stub\n", encoding="utf-8")


def chay_do(lib: str, kieu: str = "moi", bo_venv: bool = False) -> dict:
    """Chạy phép dò ở tiến trình RIÊNG với `BQ_DEMUCS_LIB=lib`."""
    runner = SAN / "_runner_do.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text(_RUNNER, encoding="utf-8")
    env = dict(os.environ)
    env["BQ_DEMUCS_LIB"] = lib
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(runner), REPO, kieu,
                        "1" if bo_venv else "0"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, env=env)
    for dong in (r.stdout or "").splitlines():
        if dong.startswith("BQJSON"):
            return json.loads(dong[6:])
    raise RuntimeError(f"runner không trả JSON (rc={r.returncode}): "
                       f"{(r.stdout or '')[-300:]} {(r.stderr or '')[-400:]}")


print("=" * 70)
print("CỔNG 58 — `_lib` tự đứng được + phép dò nói thật")
print("=" * 70)

LIB_THAT = TG.lib_demucs()
print(f"\n_lib THẬT của máy này: {LIB_THAT}")
print(f"  tồn tại: {Path(LIB_THAT).is_dir()}")

try:
    # ==================================================================
    print("\n=== CA 1: GIẢ LẬP MÔI TRƯỜNG .exe (không có `.venv` để mượn) ===")
    # Đây là ca quan trọng nhất — đúng chỗ máy dev và máy thật lệch nhau.
    r_dev = chay_do(LIB_THAT, "moi", bo_venv=False)
    r_exe = chay_do(LIB_THAT, "moi", bo_venv=True)
    print(f"  máy DEV (có .venv) : thiếu={r_dev['thieu']} · co={r_dev['co']}"
          f" · du_lib={r_dev['du_lib']}")
    print(f"  giả lập .exe       : thiếu={r_exe['thieu']} · co={r_exe['co']}"
          f" · du_lib={r_exe['du_lib']}")
    print(f"  nguồn từng gói (dev): {r_dev['nguon']}")

    dat("CA1a máy DEV và bản .exe nói GIỐNG NHAU về `_lib` (mệnh đề trung tâm)",
        r_dev["thieu"] == r_exe["thieu"],
        f"dev={r_dev['thieu']} · exe={r_exe['thieu']}")
    dat("CA1b `du_lib` cũng giống nhau ở hai môi trường",
        r_dev["du_lib"] == r_exe["du_lib"],
        f"dev={r_dev['du_lib']} · exe={r_exe['du_lib']}")
    dat("CA1c trong môi trường .exe, `co_demucs()` ĐÚNG BẰNG '`_lib` có đủ'",
        r_exe["co"] == (not r_exe["thieu"]),
        f"co={r_exe['co']} · thiếu={r_exe['thieu']}")

    lib_du = SAN / "lib_du"
    lam_stub(lib_du, "torch", "demucs", "soundfile")
    r_exe_du = chay_do(str(lib_du), "moi", bo_venv=True)
    dat("CA1d `_lib` ĐỦ 3 gói -> môi trường .exe báo CÓ (không phải luôn False)",
        r_exe_du["co"] is True and r_exe_du["thieu"] == [],
        f"co={r_exe_du['co']} · thiếu={r_exe_du['thieu']}")
    dat("CA1e và nguồn của cả 3 gói phải ghi là `_lib`",
        all(v == "_lib" for v in r_exe_du["nguon"].values()),
        str(r_exe_du["nguon"]))

    # ==================================================================
    print("\n=== CA 2: TRẠNG THÁI CÀI DỞ (có demucs, thiếu torch) ===")
    lib_do = SAN / "lib_do"
    lam_stub(lib_do, "demucs")                   # ĐÚNG cảnh `_lib` anh Hùng
    goi_do = TG.do_goi_tach_giong(str(lib_do))
    dat("CA2a demucs dò ra nằm trong `_lib`",
        goi_do["demucs"]["nguon"] == "_lib", goi_do["demucs"]["lib"])
    dat("CA2b torch KHÔNG được coi là đã cài (dù `.venv` máy này có)",
        goi_do["torch"]["lib"] == "" and goi_do["torch"]["nguon"] != "_lib",
        f"nguồn={goi_do['torch']['nguon']} · {goi_do['torch']['he'][:60]}")

    os.environ["BQ_DEMUCS_LIB"] = str(lib_do)
    try:
        tt_do = TG.tinh_trang_demucs()
    finally:
        os.environ.pop("BQ_DEMUCS_LIB", None)
    dat("CA2c `thieu` PHẢI có torch (không được báo đã cài)",
        "torch" in tt_do["thieu"], f"thiếu={tt_do['thieu']}")
    dat("CA2d `du_lib` = False", tt_do["du_lib"] is False)
    dat("CA2e gói đang MƯỢN của hệ thống phải được nêu đích danh",
        "torch" in tt_do["ngoai_lib"], f"ngoai_lib={tt_do['ngoai_lib']}")
    nhan = TG.nhan_nut_tai(tt_do)
    dat("CA2f nút ghi 'Cài tiếp phần còn thiếu', KHÔNG phải 'Tải bộ tách giọng'",
        TG.NHAN_CAI_TIEP in nhan and TG.NHAN_TAI_DEMUCS not in nhan, nhan)
    dat("CA2g nhãn nút nêu ĐÍCH DANH gói còn thiếu", "torch" in nhan, nhan)

    lib_rong = SAN / "lib_rong"
    lib_rong.mkdir(parents=True, exist_ok=True)
    os.environ["BQ_DEMUCS_LIB"] = str(lib_rong)
    try:
        tt_rong = TG.tinh_trang_demucs()
    finally:
        os.environ.pop("BQ_DEMUCS_LIB", None)
    dat("CA2h `_lib` RỖNG thì nút ghi 'tải cả bộ' (nhãn hai trạng thái khác nhau)",
        TG.NHAN_TAI_DEMUCS == TG.nhan_nut_tai(tt_rong),
        TG.nhan_nut_tai(tt_rong))

    # ==================================================================
    print("\n=== CA 3: CÀI ĐỦ -> `spec.origin` CỦA CẢ 3 GÓI NẰM DƯỚI `_lib` ===")
    goi_du = TG.do_goi_tach_giong(str(lib_du))
    duoi_het = all(
        Path(goi_du[g]["lib"]).resolve().is_relative_to(lib_du.resolve())
        for g in TG.GOI_TACH_GIONG if goi_du[g]["lib"])
    dat("CA3a cả 3 gói dò ra nguồn `_lib`",
        all(goi_du[g]["nguon"] == "_lib" for g in TG.GOI_TACH_GIONG),
        str({g: goi_du[g]["nguon"] for g in TG.GOI_TACH_GIONG}))
    dat("CA3b `spec.origin` của cả 3 THẬT SỰ nằm dưới `_lib`", duoi_het,
        " · ".join(Path(goi_du[g]["lib"]).name for g in TG.GOI_TACH_GIONG))

    # --- 3c: pip THẬT, gói NHỎ. Chứng minh cơ chế `--target`+`--ignore-installed`
    # Cố ý chọn `soundfile`: nó ĐÃ CÓ trong `.venv` máy này, nên đây đúng là ca
    # mà pip có thể "đã có rồi thì thôi". KHÔNG tải torch (155 MB) — cơ chế
    # giống hệt, chỉ khác dung lượng, và máy anh Hùng đang chạy sản xuất.
    lib_pip = SAN / "lib_pip"
    args = [sys.executable, "-m", "pip", "install", "-q", "--no-input",
            "--disable-pip-version-check", "--upgrade", "--ignore-installed",
            "--target", str(lib_pip), "soundfile"]
    rp = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=900)
    goi_pip = TG.do_goi_tach_giong(str(lib_pip))
    dat("CA3c pip `--target --ignore-installed` ĐẶT ĐƯỢC gói mà `.venv` đã có "
        "vào đúng `_lib` (gói nhỏ, suy ra cho torch)",
        rp.returncode == 0 and goi_pip["soundfile"]["nguon"] == "_lib",
        f"rc={rp.returncode} · {goi_pip['soundfile']['lib'][-70:]}")

    # --- 3d: quét TĨNH bằng AST. Bắt buộc AST chứ không tìm chuỗi: chính phần
    # ghi chú của `cai_demucs` có chữ "--ignore-installed", nên tìm bằng chuỗi
    # thì gỡ cờ khỏi lệnh mà cổng VẪN XANH (bài học cổng 56d).
    cay = ast.parse(Path(REPO, "app", "core", "thay_giong.py")
                    .read_text(encoding="utf-8"))
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "cai_demucs"),
               None)
    hang_so = {n.value for n in ast.walk(ham) if isinstance(n, ast.Constant)
               and isinstance(n.value, str)} if ham else set()
    dat("CA3d lệnh pip của `cai_demucs` có `--ignore-installed` (đọc bằng AST)",
        "--ignore-installed" in hang_so)
    dat("CA3e và vẫn cài vào `--target` (không đụng `.venv` đang chạy 300 kênh)",
        "--target" in hang_so and "--user" not in hang_so)

    # ==================================================================
    print("\n=== CA 4: THỬ PHÁ — trả `co_demucs` về kiểu `find_spec` cũ ===")
    # Chạy lại CHÍNH mã bản cũ ở cả hai môi trường. Nếu cổng này là con dấu thì
    # bản cũ cũng sẽ qua; nó phải TRƯỢT.
    c_dev = chay_do(LIB_THAT, "cu", bo_venv=False)
    c_exe = chay_do(LIB_THAT, "cu", bo_venv=True)
    print(f"  BẢN CŨ · máy DEV : thiếu={c_dev['thieu']} · co={c_dev['co']}")
    print(f"  BẢN CŨ · .exe    : thiếu={c_exe['thieu']} · co={c_exe['co']}")
    pha_lech = c_dev["thieu"] != c_exe["thieu"]
    dat("CA4a bản CŨ nói KHÁC NHAU ở hai môi trường -> CA1a sẽ FAIL "
        "(cổng không phải con dấu)", pha_lech,
        f"dev={c_dev['thieu']} · exe={c_exe['thieu']}")
    dat("CA4b bản CŨ trên máy dev báo 'đã cài' trong khi `_lib` thật sự thiếu",
        c_dev["co"] is True and r_exe["thieu"] != [],
        f"cũ.co={c_dev['co']} · `_lib` thiếu thật={r_exe['thieu']}")
    dat("CA4c bản MỚI thì không lệch (đối chứng của CA4a)",
        r_dev["thieu"] == r_exe["thieu"])

    # ==================================================================
    print("\n=== CA 5: `_lib` CỦA BẢN .exe PHẢI SỐNG SÓT QUA LƯỢT TỰ CẬP NHẬT ===")
    # `self_update.py` cập nhật bằng `ren _internal -> _internal.old` rồi
    # `rmdir /S /Q _internal.old`. Đặt `_lib` trong `_internal` = mỗi lượt tự
    # cập nhật xoá sạch 155 MB vừa tải. App này tự cập nhật liên tục.
    bat = Path(REPO, "app", "core", "self_update.py").read_text(
        encoding="utf-8", errors="replace")
    dat("CA5a xác nhận bản cập nhật THẬT SỰ xoá cả thư mục `_internal`",
        "_internal.old" in bat and "rmdir" in bat)

    # Giả lập bản .exe: `frozen` = True + DATA_DIR trỏ ra ngoài.
    ma_fz = (
        "import sys, json, os\n"
        "sys.frozen = True\n"
        "sys.path.insert(0, %r)\n"
        "import config\n"
        "from app.core import thay_giong as TG\n"
        "print('BQJSON' + json.dumps({'lib': TG.lib_demucs(),\n"
        "      'data': str(config.DATA_DIR)}))\n" % REPO)
    fz = SAN / "_fz.py"
    fz.write_text(ma_fz, encoding="utf-8")
    env = dict(os.environ)
    env.pop("BQ_DEMUCS_LIB", None)
    env["BQ_DATA_DIR"] = str(SAN / "data_gia")
    env["PYTHONUTF8"] = "1"
    rf = subprocess.run([sys.executable, str(fz)], capture_output=True,
                        text=True, encoding="utf-8", errors="replace",
                        timeout=300, env=env)
    ra_fz = json.loads([d for d in (rf.stdout or "").splitlines()
                        if d.startswith("BQJSON")][0][6:])
    print(f"  bản .exe -> _lib = {ra_fz['lib']}")
    dat("CA5b bản .exe đặt `_lib` NGOÀI `_internal` (không bị cập nhật xoá)",
        "_internal" not in ra_fz["lib"], ra_fz["lib"])
    dat("CA5c và đặt trong DATA_DIR — chỗ config.py cố ý tách ra để giữ dữ liệu",
        Path(ra_fz["lib"]).resolve().parent == Path(ra_fz["data"]).resolve(),
        f"{ra_fz['lib']} vs {ra_fz['data']}")
    dat("CA5d chạy từ NGUỒN vẫn là `<repo>/_lib` y như cũ "
        "(không bỏ rơi `_lib` máy dev đã tải)",
        Path(TG.lib_demucs()).resolve() == Path(REPO, "_lib").resolve(),
        TG.lib_demucs())

except Exception as e:  # noqa: BLE001
    HONG += 1
    import traceback
    traceback.print_exc()
    print(f"\nHỎNG vì lỗi ngoài dự kiến: {type(e).__name__}: {e}")
finally:
    shutil.rmtree(SAN, ignore_errors=True)

print("\n" + "=" * 70)
print(f"CỔNG 58: ĐẠT {OK} · HỎNG {HONG}")
print("=" * 70)
sys.exit(1 if HONG else 0)
