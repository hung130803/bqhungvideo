# -*- coding: utf-8 -*-
"""CỔNG 17 — TEST KHÔNG ĐƯỢC MỞ CỬA SỔ TRÊN MÁY USER.

LỖI THẬT 31/07/2026, anh Hùng: "sao mỗi lần tôi yêu cầu bạn làm hay hỏi gì cái
thư mục kia đều nhảy lên là sao thế rất nhiều lần" — kèm ảnh Explorer mở
`%TEMP%\\pipe_dlg_p2hn9104\\logs`.

Đường đi: `_test_pipe_dialogs.py` bấm MỌI QPushButton trong hộp 🤖 Dây chuyền
-> nút "📂 Mở thư mục log" -> `open_log_dir()` -> `os.startfile(DATA_DIR/logs)`.
`_test_app_smoke.py` CÓ vá os.startfile nhưng vá RIÊNG trong file nó, test khác
không thừa hưởng. Nay có `_test_guard` dùng chung + cổng này canh 3 việc:

  A. TĨNH: mọi `_test_*.py` dựng UI / bấm nút PHẢI import `_test_guard`.
  B. ĐỘNG: dựng StudioPage thật, bấm HẾT nút hộp Dây chuyền -> đếm số cú mở
     cửa sổ bị chặn > 0 và KHÔNG có tiến trình explorer/ffplay nào sinh ra.
  C. Guard phải CHO QUA ffmpeg (quy tắc sắt: test bằng thành phần thật) và
     tự dọn rác %TEMP% của các lần chạy trước (ổ C từng đầy 100%).
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:                                  # chạy được cả khi console là cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

T = Path(tempfile.mkdtemp(prefix="nopopup_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "s.ini")
REPO = Path(str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO))

FFMPEG = REPO / "bin" / "ffmpeg.exe"
FAIL: list[str] = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


# ══ A. TĨNH: file test nào dựng UI/bấm nút mà thiếu canh cổng = FAIL ══
print("\n══ A. Mọi test dựng UI phải import _test_guard ══")
CAN_GUARD = []
for f in sorted(REPO.glob("_test_*.py")):
    if f.name in ("_test_guard.py", "_test_no_popup.py"):
        continue
    s = f.read_text(encoding="utf-8", errors="ignore")
    dung_ui = ("StudioPage" in s or "MainWindow" in s
               or re.search(r"\.click\(\)|\.toggle\(\)", s))
    if dung_ui:
        CAN_GUARD.append(f.name)
        kiem("import _test_guard" in s, f"{f.name} có canh cổng",
             "thiếu dòng `import _test_guard` -> test này có thể mở Explorer")
kiem(len(CAN_GUARD) >= 12, f"quét được {len(CAN_GUARD)} test dựng UI",
     str(CAN_GUARD))

import _test_guard  # noqa: E402 - phải import SAU khi quét tĩnh cho sạch nghĩa

# ══ C1. Guard che đủ 4 cửa + tu_kiem chạy được ══
print("\n══ C. Canh cổng che đủ cửa, nhưng KHÔNG cản ffmpeg ══")
_test_guard.tu_kiem(im=True)
kiem(os.startfile("bat_ky_dau") is None, "os.startfile bị chặn (trả None)")
kiem(len(_test_guard.DA_CHAN) >= 1, "cú mở cửa sổ được GHI LẠI để kiểm đếm")
n0 = len(_test_guard.DA_CHAN)
p = subprocess.Popen(["explorer", str(T)])
kiem(p.poll() == 0 and p.pid == 0, "Popen(explorer) bị nuốt, không sinh tiến trình",
     f"pid={p.pid}")
subprocess.run(["cmd", "/c", "start", str(T)])
import webbrowser  # noqa: E402

webbrowser.open("https://github.com")
kiem(len(_test_guard.DA_CHAN) - n0 == 3,
     "chặn đủ 3 đường: Popen · run · webbrowser",
     str(_test_guard.DA_CHAN[n0:]))

# ffmpeg PHẢI chạy thật (mock từng giấu bug -> quy tắc sắt của repo)
if FFMPEG.exists():
    ra = subprocess.run([str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
                         "testsrc=size=160x120:rate=10:duration=1", "-c:v",
                         "libx264", "-preset", "ultrafast", str(T / "v.mp4")])
    kiem(ra.returncode == 0 and (T / "v.mp4").stat().st_size > 0,
         "ffmpeg VẪN chạy thật qua canh cổng", f"rc={ra.returncode}")
    pr = subprocess.Popen([str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi",
                           "-i", "testsrc=size=160x120:rate=10:duration=1",
                           str(T / "v2.mp4")])
    kiem(pr.wait() == 0 and (T / "v2.mp4").exists(),
         "Popen(ffmpeg) vẫn chạy thật (chỉ chặn lệnh mở cửa sổ)")
else:
    kiem(False, "có bin/ffmpeg.exe để kiểm ffmpeg không bị chặn", str(FFMPEG))

# ══ B. ĐỘNG: bấm HẾT nút hộp Dây chuyền, đếm tiến trình cửa sổ sinh ra ══
print("\n══ B. Bấm mọi nút hộp 🤖 Dây chuyền -> KHÔNG cửa sổ nào bật ══")
import app.queue.jobs  # noqa: F401,E402
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,  # noqa: E402
                             QInputDialog, QMenu, QMessageBox, QPushButton)

qapp = QApplication(sys.argv)
from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: 0
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: None)
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QMenu.exec = lambda self, *a, **k: None
_test_guard.tu_kiem(im=True)

pid = db.execute(
    "INSERT INTO projects(name,assets_dir,grp,pipe_on) VALUES('K1',?,'Mỹ',1)",
    (str(T / "as"),)).lastrowid
pg = StudioPage(AppState())
pg._pipe_report = []
pg.state.project_id = pid


def _dem_cua_so() -> int:
    """Đếm CỬA SỔ Explorer đang mở (COM Shell.Application).

    KHÔNG đếm tiến trình explorer.exe: Windows mở mọi cửa sổ trong CÙNG 1 tiến
    trình nên đếm tiến trình là kiểm hớ, luôn PASS dù cửa sổ nhảy lên.
    Phải qua `chay_that` — `subprocess.run` đã bị canh cổng chặn powershell,
    dùng thẳng nó thì PHÉP ĐO bị nuốt và luôn trả -1 (bẫy tôi đã sập 1 lần)."""
    try:
        ra = _test_guard.chay_that(
            ["powershell", "-NoProfile", "-Command",
             "$s=New-Object -ComObject Shell.Application;"
             "@($s.Windows()).Count"],
            capture_output=True, text=True, timeout=60)
        return int((ra.stdout or "").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return -1


truoc = _dem_cua_so()
n1 = len(_test_guard.DA_CHAN)
pg._pipeline_dialog()
qapp.processEvents()
nut = pg._pipe_dlg.findChildren(QPushButton)
ten_mo = []
for b in nut:
    if "Chạy dây chuyền" in b.text():
        continue
    try:
        b.click()
        qapp.processEvents()
    except Exception as e:  # noqa: BLE001
        FAIL.append(f"bấm nút '{b.text()}' nổ: {type(e).__name__}: {e}")
kiem(len(nut) >= 5, f"hộp Dây chuyền có {len(nut)} nút để bấm")
moi = _test_guard.DA_CHAN[n1:]
kiem(any("startfile" in m for m in moi),
     "bấm '📂 Mở thư mục log' -> ĐÃ BỊ CHẶN (trước đây Explorer nhảy lên)",
     f"chỉ thấy: {moi}")
time.sleep(1.0)
sau = _dem_cua_so()
kiem(truoc >= 0 and sau <= truoc,
     f"số CỬA SỔ Explorer không tăng ({truoc} -> {sau})",
     "bấm nút xong có cửa sổ mới bật lên = đúng lỗi anh Hùng báo")

# ══ C2. Dọn rác %TEMP% các lần chạy trước ══
print("\n══ C2. Tự dọn thư mục tạm test cũ (ổ C từng đầy 100%) ══")
cu = Path(tempfile.gettempdir()) / "pipe_dlg_TEST_RAC_CU"
cu.mkdir(exist_ok=True)
(cu / "x.bin").write_bytes(b"z" * 2048)
gia = time.time() - 7200
os.utime(cu, (gia, gia))
n_xoa, mb = _test_guard.don_rac_cu(gio=1.0)
kiem(not cu.exists(), f"xoá được rác cũ hơn 1 giờ ({n_xoa} thư mục / {mb:.1f} MB)")
kiem(T.exists(), "KHÔNG xoá thư mục của lần chạy ĐANG diễn ra")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print(f"KẾT QUẢ: TẤT CẢ ĐẠT — test không mở cửa sổ nào trên máy user "
      f"(chặn {len(_test_guard.DA_CHAN)} cú), ffmpeg vẫn chạy thật")
sys.stdout.flush()
os._exit(0)
