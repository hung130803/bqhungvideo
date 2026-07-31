# -*- coding: utf-8 -*-
"""CANH CỔNG cho mọi test dựng UI thật — TEST KHÔNG ĐƯỢC ĐỤNG VÀO MÁY THẬT.

LỖI THẬT 31/07/2026 (anh Hùng: "sao mỗi lần tôi yêu cầu bạn làm hay hỏi gì cái
thư mục kia đều nhảy lên"): `_test_pipe_dialogs.py` bấm MỌI nút trong hộp
🤖 Dây chuyền, trong đó có nút "📂 Mở thư mục log" -> `os.startfile(...)` KHÔNG
bị vá -> mỗi lần chạy cổng test là 1 cửa sổ Explorer THẬT nhảy lên màn hình
(`%TEMP%\\pipe_dlg_xxxx\\logs`). `_test_app_smoke.py` có vá, nhưng vá RIÊNG
trong file nó nên test khác không thừa hưởng -> lỗi lặp lại.

CÁCH DÙNG (mọi test dựng StudioPage/MainWindow hoặc bấm nút):

    T = tempfile.mkdtemp(prefix="...")
    os.environ["BQ_DATA_DIR"] = T            # sandbox trước
    ...
    import _test_guard                       # chặn cửa sổ ngoài + dọn rác cũ
    ...
    _test_guard.tu_kiem()                    # xác nhận bản vá CÒN ăn

Chặn: os.startfile · webbrowser.open · QDesktopServices.openUrl ·
subprocess.Popen/run khi lệnh là explorer/start/cmd/powershell/rundll32...
ffmpeg/ffprobe/yt-dlp VẪN chạy thật (quy tắc sắt: test bằng thành phần thật).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

# In được tiếng Việt ở MỌI console (cp1252 -> UnicodeEncodeError làm test "FAIL"
# oan ngay dòng print đầu tiên, tưởng code hỏng).
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

# Ghi lại mọi cú bị chặn -> test in ra được "đã chặn N cửa sổ", và cổng
# _test_no_popup.py kiểm bằng con số này chứ không tin lời.
DA_CHAN: list[str] = []

# Lệnh mở cửa sổ trên máy user — chặn. Mọi lệnh khác (ffmpeg...) cho qua.
_LENH_MO_CUA = {
    "explorer", "explorer.exe", "start", "cmd", "cmd.exe",
    "powershell", "powershell.exe", "pwsh", "pwsh.exe",
    "rundll32", "rundll32.exe", "wscript", "wscript.exe",
    "cscript", "cscript.exe", "notepad", "notepad.exe",
    "mspaint", "mspaint.exe", "wmplayer", "wmplayer.exe",
    "ffplay", "ffplay.exe",          # trình phát -> cũng là cửa sổ
}

# Tiền tố thư mục tạm của các test trong repo (dùng để dọn rác lần chạy trước).
TIEN_TO = (
    "ai_gate_", "app_smoke_", "cancel_persist_", "chan_pick_", "dbguard_",
    "k100_", "lane_", "pipe_dlg_", "pipe_e2e_", "pipe_integ_run_",
    "pipe_overlap_", "quota_wait_", "reanalyze_", "reanalyze_basic_",
    "shutdown_safe_", "tpl_chan_", "ui_smooth_", "nopopup_",
)


def _ten_lenh(args) -> str:
    """Lấy tên chương trình từ tham số Popen/run (str hoặc list)."""
    try:
        if isinstance(args, (list, tuple)):
            if not args:
                return ""
            dau = args[0]
        else:
            dau = args
        if isinstance(dau, (bytes, bytearray)):
            dau = dau.decode("utf-8", "ignore")
        dau = str(dau).strip().strip('"')
        return os.path.basename(dau).lower()
    except Exception:  # noqa: BLE001 - đoán không ra thì cho qua
        return ""


def _la_cua_so_ngoai(args) -> bool:
    return _ten_lenh(args) in _LENH_MO_CUA


# ── 1. os.startfile: chặn HẲN (chỉ dùng để mở file/thư mục cho người dùng) ──
_goc_startfile = getattr(os, "startfile", None)


def _startfile_gia(path, *a, **k):
    DA_CHAN.append(f"os.startfile({path})")
    return None


os.startfile = _startfile_gia   # type: ignore[attr-defined]


# ── 2. subprocess: chặn CÓ CHỌN LỌC (ffmpeg phải chạy thật) ──
# Phải là LỚP CON của Popen, không phải hàm: `asyncio.windows_utils` kế thừa
# subprocess.Popen ở tầng import — thay bằng hàm là hỏng cả cây import
# (TypeError: function() argument 'code' must be code, not str).
_goc_popen = subprocess.Popen
_goc_run = subprocess.run


class PopenCanhCong(_goc_popen):  # type: ignore[misc,valid-type]
    """Popen thật, nhưng nuốt các lệnh mở cửa sổ."""

    def __init__(self, args, *a, **k):
        if _la_cua_so_ngoai(args):
            DA_CHAN.append(f"Popen({_ten_lenh(args)})")
            # KHÔNG gọi super().__init__ -> không sinh tiến trình. Đặt tay các
            # thuộc tính Popen.__del__ / API cơ bản cần, kẻo nổ lúc GC.
            self._child_created = False
            self._da_chan = True
            self.args = args
            self.pid = 0
            self.returncode = 0
            self.stdin = self.stdout = self.stderr = None
            return
        self._da_chan = False
        super().__init__(args, *a, **k)

    def poll(self):
        return 0 if getattr(self, "_da_chan", False) else super().poll()

    def wait(self, timeout=None):
        return 0 if getattr(self, "_da_chan", False) else super().wait(timeout)

    def communicate(self, *a, **k):
        if getattr(self, "_da_chan", False):
            return (b"", b"")
        return super().communicate(*a, **k)

    def kill(self):
        if not getattr(self, "_da_chan", False):
            super().kill()

    def terminate(self):
        if not getattr(self, "_da_chan", False):
            super().terminate()


def _run_canh_cong(args, *a, **k):
    if _la_cua_so_ngoai(args):
        DA_CHAN.append(f"run({_ten_lenh(args)})")
        return subprocess.CompletedProcess(args, 0, "", "")
    return _goc_run(args, *a, **k)


subprocess.Popen = PopenCanhCong      # type: ignore[misc,assignment]
subprocess.run = _run_canh_cong       # type: ignore[assignment]


# ── 3. webbrowser + Qt: mở link/thư mục qua đường khác cũng phải chặn ──
_goc_wb = webbrowser.open


def _wb_gia(*a, **k):
    DA_CHAN.append(f"webbrowser.open({a[0] if a else ''})")
    return True


webbrowser.open = _wb_gia            # type: ignore[assignment]
webbrowser.open_new = _wb_gia        # type: ignore[assignment]
webbrowser.open_new_tab = _wb_gia    # type: ignore[assignment]

def _chan_qt() -> None:
    """Vá QDesktopServices — gọi LÚC PyQt6 đã nạp. KHÔNG tự import PyQt6 ở đây:
    repo này bắt buộc cv2 (app.queue.jobs) nạp TRƯỚC Qt, guard mà kéo Qt lên
    sớm là hỏng thứ tự import."""
    if "PyQt6.QtGui" not in sys.modules:
        return
    try:
        from PyQt6.QtGui import QDesktopServices
        if getattr(QDesktopServices.openUrl, "_canh_cong", False):
            return

        def _mo_gia(*a, **k):
            DA_CHAN.append("QDesktopServices.openUrl")
            return True
        _mo_gia._canh_cong = True                      # type: ignore[attr-defined]
        QDesktopServices.openUrl = staticmethod(_mo_gia)   # type: ignore[assignment]
    except Exception:  # noqa: BLE001 - không có PyQt6 thì thôi
        pass


_chan_qt()


def chay_that(args, **k):
    """CỬA THOÁT CÓ KIỂM SOÁT: chạy 1 lệnh bị chặn (vd powershell để ĐO số cửa
    sổ Explorer đang mở). Dùng `_goc_run` là KHÔNG đủ — subprocess.run gọi
    Popen qua biến module, mà Popen đã bị thay -> lệnh vẫn bị nuốt và trả rỗng
    (đo ra -1). Ở đây trả Popen gốc trong đúng 1 lệnh rồi vá lại."""
    _tam = subprocess.Popen
    subprocess.Popen = _goc_popen          # type: ignore[misc,assignment]
    try:
        return _goc_run(args, **k)
    finally:
        subprocess.Popen = _tam            # type: ignore[misc,assignment]


# ── 4. Tự kiểm: bản vá phải CÒN ăn lúc bấm nút, không tin "chắc là còn" ──
def tu_kiem(im: bool = False) -> None:
    """Dừng test NGAY (exit 2) nếu canh cổng đã bị ghi đè — thà không chạy còn
    hơn để cửa sổ nhảy lên máy anh Hùng lần nữa."""
    _chan_qt()          # Qt nạp sau -> vá nốt ở đây
    xau = []
    if getattr(os, "startfile", None) is not _startfile_gia:
        xau.append("os.startfile")
    if subprocess.Popen is not PopenCanhCong:
        xau.append("subprocess.Popen")
    if subprocess.run is not _run_canh_cong:
        xau.append("subprocess.run")
    if webbrowser.open is not _wb_gia:
        xau.append("webbrowser.open")
    if xau:
        print("❌ CANH CỔNG BỊ GHI ĐÈ: " + ", ".join(xau) +
              " — dừng test, không để Explorer/trình phát nhảy lên máy user.")
        sys.stdout.flush()
        os._exit(2)
    if not im:
        print(f"  ✓ canh cổng: cấm mở cửa sổ ngoài (đã chặn {len(DA_CHAN)} cú)")


# ── 5. Dọn rác thư mục tạm của các lần chạy TRƯỚC (ổ C từng đầy 100%) ──
def don_rac_cu(gio: float = 1.0) -> tuple[int, float]:
    """Xoá thư mục tạm test cũ hơn `gio` giờ. Trả (số thư mục, số MB)."""
    goc = Path(tempfile.gettempdir())
    han = time.time() - gio * 3600
    n, byte = 0, 0
    try:
        ds = list(goc.iterdir())
    except OSError:
        return (0, 0.0)
    for d in ds:
        try:
            if not d.is_dir() or not d.name.startswith(TIEN_TO):
                continue
            if d.stat().st_mtime > han:      # có thể là lần chạy đang diễn ra
                continue
            byte += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            shutil.rmtree(d, ignore_errors=True)
            if not d.exists():
                n += 1
        except OSError:
            continue
    return (n, byte / 1048576.0)


_n_rac, _mb_rac = don_rac_cu()
if _n_rac:
    print(f"  ✓ dọn rác test cũ: {_n_rac} thư mục / {_mb_rac:.1f} MB ở %TEMP%")
