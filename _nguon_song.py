"""
NGUỒN SỐNG — bản .exe chạy THẲNG mã nguồn trong thư mục dự án (27/10/2026).

Vì sao: mỗi lần sửa lỗi, anh Hùng phải chạy CAP_NHAT_APP.bat và chờ đóng gói
5-10 phút ("bấm này cập nhật lâu quá mất thời gian"). Nay bản .exe (chỉ máy
có file `nguon_ma.txt` cạnh .exe) nạp phần `app/` + `config.py` từ thư mục
dự án: Claude sửa file xong -> mở lại app là chạy bản mới, KHÔNG đóng gói.

An toàn:
  * Chỉ bật khi có `nguon_ma.txt` (CAP_NHAT_APP ghi). Máy nhân viên không có
    file này -> chạy y bản đóng gói như cũ.
  * Trước khi dùng: biên dịch thử MỌI file .py của nguồn. Lỗi cú pháp ->
    dùng bản đóng gói (ghi lý do vào logs/nguon_song.txt).
  * `thu_nap()` nạp thử các module chính; lỗi (vd mã mới cần thư viện bản
    .exe chưa có) -> `tat()` gỡ hết, chạy bản đóng gói.
  * Thư viện (PyQt6, numpy...) và ffmpeg vẫn là bản đóng gói.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import os
import sys
import time

_GOC: str | None = None
_FINDER = None
LY_DO = ""          # vì sao KHÔNG dùng nguồn sống (để hiện/ghi log)
BAN_SUA = ""        # "27/10 09:52" — giờ sửa mới nhất của nguồn đang chạy


def _ten_cua_ta(fullname: str) -> bool:
    return fullname == "config" or fullname == "app" or fullname.startswith("app.")


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self, goc: str):
        self.goc = goc

    def find_spec(self, fullname, path=None, target=None):
        if not _ten_cua_ta(fullname):
            return None
        tim = path if (path and fullname != "app" and fullname != "config") else [self.goc]
        return importlib.machinery.PathFinder.find_spec(fullname, tim)


def _exe_dir() -> str:
    return os.path.dirname(os.path.abspath(sys.executable))


def _doc_duong_dan() -> str | None:
    f = os.path.join(_exe_dir(), "nguon_ma.txt")
    try:
        with open(f, encoding="utf-8-sig") as h:
            p = h.read().strip().strip('"')
    except OSError:
        return None
    return p or None


def _file_py(goc: str):
    yield os.path.join(goc, "config.py")
    for d, ds, fs in os.walk(os.path.join(goc, "app")):
        ds[:] = [x for x in ds if x != "__pycache__"]
        for f in fs:
            if f.endswith(".py"):
                yield os.path.join(d, f)


def _ghi_log(msg: str) -> None:
    try:
        from_env = os.environ.get("BQ_DATA_DIR")
        base = from_env or os.path.join(os.environ.get("LOCALAPPDATA", _exe_dir()), "BQHungVideo")
        os.makedirs(os.path.join(base, "logs"), exist_ok=True)
        with open(os.path.join(base, "logs", "nguon_song.txt"), "a", encoding="utf-8") as h:
            h.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
    except Exception:  # noqa: BLE001
        pass


def _data_dir() -> str:
    from_env = os.environ.get("BQ_DATA_DIR")
    return from_env or os.path.join(os.environ.get("LOCALAPPDATA", _exe_dir()), "BQHungVideo")


def _so_kiem() -> str:
    return os.path.join(_data_dir(), "nguon_song_da_kiem.json")


def _doc_so_kiem() -> dict:
    """{đường_dẫn: [mtime_ns, cỡ]} của các file ĐÃ biên dịch thử thành công."""
    import json
    try:
        with open(_so_kiem(), encoding="utf-8") as h:
            d = json.load(h)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_so_kiem(d: dict) -> None:
    import json
    f = _so_kiem()
    tam = f"{f}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(tam, "w", encoding="utf-8") as h:
            json.dump(d, h)
        os.replace(tam, f)
    except OSError:
        try:
            os.remove(tam)
        except OSError:
            pass


def _bat_bo_dem_ma() -> None:
    """Cho phép lưu bộ đệm mã đã dịch (.pyc) của nguồn sống, đặt trên ổ của
    DATA_DIR (SSD) chứ không rải vào thư mục dự án.

    ĐO 31/10/2026: bản .exe không ghi .pyc nên MỖI lần mở app (và mỗi tiến trình
    `--analyze`) dịch lại mã từ đầu — riêng nạp giao diện 9,0s, có bộ đệm 0,95s.
    Chỉ ảnh hưởng module tìm thấy qua đường dẫn (nguồn sống); thư viện đóng gói
    nằm trong gói PYZ nên không đụng. Bộ đệm tự hết hạn khi file nguồn đổi
    (Python so mtime + cỡ), y như chạy Python thường."""
    try:
        d = os.path.join(_data_dir(), "_pyc_nguon")
        os.makedirs(d, exist_ok=True)
        sys.pycache_prefix = d
        sys.dont_write_bytecode = False
    except OSError:
        pass


def bat() -> bool:
    """Gọi ĐẦU TIÊN trong main(), trước mọi `import app`/`import config`."""
    global _GOC, _FINDER, LY_DO, BAN_SUA
    if not getattr(sys, "frozen", False) or os.environ.get("BQ_TAT_NGUON_SONG") == "1":
        return False
    goc = _doc_duong_dan()
    if not goc:
        return False
    if not (os.path.isfile(os.path.join(goc, "config.py"))
            and os.path.isfile(os.path.join(goc, "app", "__init__.py"))):
        LY_DO = f"không thấy mã nguồn ở {goc}"
        _ghi_log("TẮT: " + LY_DO)
        return False
    # BIÊN DỊCH THỬ CHỈ FILE ĐÃ ĐỔI. Đo 31/10/2026: dịch thử cả 139 file mất
    # 26,5 giây CPU — trả MỖI lần mở app VÀ mỗi tiến trình phân tích con (7 cái
    # chạy song song). File không đổi (cùng mtime_ns + cỡ) từ lần kiểm đạt trước
    # thì không cần dịch lại: kết quả cú pháp chỉ phụ thuộc nội dung file.
    moi = 0.0
    da_kiem = _doc_so_kiem()
    so_moi: dict = {}
    try:
        for f in _file_py(goc):
            st = os.stat(f)
            dau = [st.st_mtime_ns, st.st_size]
            if da_kiem.get(f) != dau:
                with open(f, "rb") as h:
                    compile(h.read(), f, "exec", dont_inherit=True)
            so_moi[f] = dau
            moi = max(moi, st.st_mtime)
    except SyntaxError as e:
        LY_DO = f"lỗi cú pháp {e.filename}:{e.lineno}"
        _ghi_log("TẮT: " + LY_DO)
        return False
    except OSError as e:
        LY_DO = f"không đọc được nguồn: {e}"
        _ghi_log("TẮT: " + LY_DO)
        return False
    if so_moi != da_kiem:
        _ghi_so_kiem(so_moi)
    _bat_bo_dem_ma()
    for k in [k for k in sys.modules if _ten_cua_ta(k)]:
        sys.modules.pop(k, None)
    _FINDER = _Finder(goc)
    sys.meta_path.insert(0, _FINDER)
    _GOC = goc
    BAN_SUA = time.strftime("%d/%m %H:%M", time.localtime(moi)) if moi else ""
    os.environ["BQ_BAN_SUA"] = BAN_SUA
    return True


def dang_bat() -> bool:
    return _FINDER is not None


def tat(ly_do: str = "") -> None:
    """Gỡ nguồn sống, quên module đã nạp từ nguồn -> lần import sau dùng bản đóng gói."""
    global _FINDER, _GOC, LY_DO
    if _FINDER is not None:
        try:
            sys.meta_path.remove(_FINDER)
        except ValueError:
            pass
    _FINDER = None
    _GOC = None
    os.environ.pop("BQ_BAN_SUA", None)
    LY_DO = ly_do
    for k in [k for k in sys.modules if _ten_cua_ta(k)]:
        sys.modules.pop(k, None)
    if ly_do:
        _ghi_log("TẮT: " + ly_do)


_MODULE_CHINH = (
    "config", "app.version", "app.queue.jobs", "app.ui.main_window",
    "app.ui.studio_page", "app.ui.batch_page", "app.core.ffmpeg_utils",
    "app.core.pipeline", "app.modules.m1_highlight", "app.ai.llm",
)


def thu_nap() -> bool:
    """Nạp thử module chính từ nguồn. Lỗi -> tắt nguồn sống, trả False."""
    if not dang_bat():
        return False
    import importlib
    for m in _MODULE_CHINH:
        try:
            importlib.import_module(m)
        except Exception as e:  # noqa: BLE001 - mọi lỗi -> về bản đóng gói
            tat(f"nạp {m} lỗi: {type(e).__name__}: {e}")
            return False
    _ghi_log(f"BẬT: chạy mã nguồn {_GOC} (bản sửa {BAN_SUA})")
    return True


def moc_moi_nhat() -> float:
    """Giờ sửa mới nhất của nguồn (để phát hiện bản sửa mới khi app đang mở)."""
    if not _GOC:
        return 0.0
    moi = 0.0
    try:
        for f in _file_py(_GOC):
            moi = max(moi, os.path.getmtime(f))
    except OSError:
        pass
    return moi
