# -*- coding: utf-8 -*-
"""CHỤP HỘP CHỌN GIỌNG — TRƯỚC / SAU, để NGƯỜI TỰ NHÌN.

Đếm điểm ảnh KHÔNG phát hiện được tofu (ô vuông) — bài học cổng 68: tofu
2.431 px vs chữ thật 517 px, tức đếm điểm ảnh ra số NGƯỢC 4,7 lần. Vì vậy
file này chỉ có một việc: đẻ ra 2 file PNG rồi để người MỞ RA XEM.

**BẪY BỘ DỰNG ẢNH, phải tự canh:** Qt chạy `offscreen` mà không có họ phông
nào thì MỌI chữ ra ô vuông — lúc đó ảnh xấu là lỗi CỦA PHÉP CHỤP, không phải
lỗi của app. Nên script DỪNG HẲN (mã thoát 2) nếu `QFontDatabase.families()`
rỗng hoặc phông đang dùng không dựng nổi chữ có dấu.

BẢN "TRƯỚC" nạp bằng `git show <mốc>:app/ui/thay_giong_dialog.py` chứ không
phải chép tay lại vòng lặp cũ — chép tay là chụp cái mình NHỚ, không phải cái
đã chạy.
"""
from __future__ import annotations

import os
import subprocess
import sys
import types
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("BQ_QSETTINGS_INI", "1")

# **NẠP PHÔNG WINDOWS TRƯỚC KHI DỰNG QApplication.** Nền `offscreen` của Qt
# dùng bộ phông "basic", và nó KHÔNG tự đọc kho phông của Windows -> đo được
# **0 họ phông** -> mọi chữ ra ô vuông tofu. Phải trỏ `QT_QPA_FONTDIR` vào
# `C:\Windows\Fonts`; đặt SAU khi QApplication dựng lên thì không ăn.
if os.name == "nt" and not os.environ.get("QT_QPA_FONTDIR"):
    _kho = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    if _kho.is_dir():
        os.environ["QT_QPA_FONTDIR"] = str(_kho)

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

import _test_guard  # noqa: F401,E402

from PyQt6.QtCore import QSize, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication, QListWidget, QListWidgetItem  # noqa: E402

#: mốc = commit NGAY TRƯỚC lượt nối `gom_nhom` vào hộp chọn giọng
MOC = os.environ.get("BQ_MOC_COMBO", "b5bd003")


def _nap_moc(sha: str, duong: str, ten: str) -> types.ModuleType:
    """Nạp một file .py của commit `sha` thành module RIÊNG."""
    ma = subprocess.run(["git", "show", f"{sha}:{duong}"], cwd=str(GOC),
                        capture_output=True, timeout=60)
    if ma.returncode != 0:
        raise RuntimeError(f"git show {sha}:{duong} hỏng: "
                           f"{ma.stderr.decode('utf-8', 'replace')[:200]}")
    mod = types.ModuleType(ten)
    mod.__file__ = str(GOC / duong)
    exec(compile(ma.stdout.decode("utf-8"), f"{sha}:{duong}", "exec"),
         mod.__dict__)
    return mod


def _kiem_phong(app: QApplication) -> None:
    """DỪNG nếu bộ dựng ảnh không có phông — ảnh tofu là lỗi của phép chụp."""
    ho = QFontDatabase.families()
    print(f"[phông] {len(ho)} họ phông")
    if not ho:
        print("DỪNG: 0 họ phông -> ảnh sẽ toàn ô vuông tofu. Đó là lỗi BỘ "
              "DỰNG ẢNH, không phải lỗi app.")
        sys.exit(2)
    # dựng thử một chữ có dấu: phông không có glyph thì bề rộng thụt hẳn
    from PyQt6.QtGui import QFontMetrics
    f = QFont(ho[0] if "Segoe UI" not in ho else "Segoe UI", 12)
    fm = QFontMetrics(f)
    if fm.horizontalAdvance("Tiếng Việt có dấu") < 40:
        print("DỪNG: phông không dựng nổi chữ có dấu.")
        sys.exit(2)
    print(f"[phông] dùng {f.family()!r} — chữ có dấu rộng "
          f"{fm.horizontalAdvance('Tiếng Việt có dấu')} px: OK")


#: Chỉ vẽ ngần này dòng ĐẦU. Combo mở ra cũng chỉ hiện chừng ấy, và đây đúng
#: là phần quyết định "có dễ chọn không" — nhồi cả 115 dòng vào một ảnh thì
#: chữ nhỏ tới mức chính tôi đọc không ra, tức phép chứng minh tự vô hiệu.
SO_DONG_VE = 22


def _chup(dong: list[tuple[str, str]], ten_file: str, tieu_de: str) -> None:
    """Vẽ danh sách giọng ra PNG, đúng kiểu combo lúc MỞ."""
    tong = len(dong)
    dong = dong[:SO_DONG_VE]
    lw = QListWidget()
    lw.setFont(QFont("Segoe UI", 11))
    lw.setStyleSheet(
        "QListWidget{background:#12161d;color:#e6edf3;border:1px solid #30363d;"
        "font-size:15px;}"
        "QListWidget::item{padding:4px 8px;}")
    for nhan, vid in dong:
        it = QListWidgetItem(nhan)
        if not vid:                          # nhãn nhóm
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            it.setForeground(QColor("#f0b849"))
            f = QFont("Segoe UI", 11)
            f.setBold(True)
            it.setFont(f)
        lw.addItem(it)
    lw.setFixedSize(QSize(1080, 18 + 27 * len(dong)))

    anh = QImage(lw.size(), QImage.Format.Format_RGB32)
    anh.fill(QColor("#12161d"))
    p = QPainter(anh)
    lw.render(p)
    p.end()
    ra = GOC / ten_file
    anh.save(str(ra))
    print(f"[ảnh] {tieu_de}: {ra.name} — vẽ {len(dong)}/{tong} dòng · "
          f"{anh.width()}x{anh.height()} px")


def main() -> int:
    app = QApplication(sys.argv)
    _kiem_phong(app)

    from app.core.dubbing import list_recap_voices
    from app.core import giong_bang as GB
    from app.core import nhan_nha as NN
    from app.ui.thay_giong_dialog import giong_dung_duoc

    tho = list_recap_voices()

    # ---- TRƯỚC: đúng mã đã chạy ở mốc, không chép tay ----
    cu_mod = _nap_moc(MOC, "app/ui/thay_giong_dialog.py", "tgd_moc")
    cu = [(n + NN.nhan(v), v) for n, v in cu_mod.giong_dung_duoc(tho)]
    _chup(cu, "_ANH_COMBO_TRUOC.png", "TRƯỚC")

    # ---- SAU: đúng cái `_dung_combo_giong` đang dựng ----
    moi = GB.gom_nhom(giong_dung_duoc(tho), "vi", loi_tat=True)
    _chup(moi, "_ANH_COMBO_SAU.png", "SAU")

    print()
    print(f"[đo] TRƯỚC {len(cu)} dòng · {len({v for _n, v in cu if v})} giọng "
          f"· {sum(1 for _n, v in cu if not v)} nhãn nhóm")
    print(f"[đo] SAU   {len(moi)} dòng · {len({v for _n, v in moi if v})} giọng"
          f" · {sum(1 for _n, v in moi if not v)} nhãn nhóm")
    vt_cu = [i for i, (_n, v) in enumerate([d for d in cu if d[1]])
             if GB.ma_ngon_ngu(v) == "vi"]
    vt_moi = [i for i, (_n, v) in enumerate([d for d in moi if d[1]])
              if GB.ma_ngon_ngu(v) == "vi"]
    print(f"[đo] giọng Việt đầu tiên: TRƯỚC vị trí {min(vt_cu)} · "
          f"SAU vị trí {min(vt_moi)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
