# -*- coding: utf-8 -*-
"""CỔNG 108 — KEY DÁN VÀO CÀI ĐẶT AI KHÔNG ĐƯỢC MẤT ÂM THẦM.

03/11/2026 anh Hùng dán 2 key Groq lúc 11h, key chạy được (nút Kiểm tra áp TẠM
vào bộ nhớ) nhưng file .env vẫn là bản 01/11 -> tắt app là mất. Kèm lỗi thứ
hai: hộp dựng ô key từ BỘ NHỚ nên key ghi vào .env từ ngoài không hiện ra, và
bấm Lưu lúc đó GHI ĐÈ mất chúng.

CA 1: `config.nap_lai_tu_dia` đọc file -> áp vào app đang chạy; khoá không có
      trong file giữ nguyên; file hỏng/không có -> [] (không ném).
CA 2: mở hộp thật -> ô Groq hiện key mới có trên ĐĨA (không phải bộ nhớ cũ).
CA 3: sửa key rồi đóng -> HỎI. "Quay lại" = hộp còn mở; "Không lưu" = bộ nhớ
      trả về đúng file, file không đổi; "Lưu" = key vào file.
CA 4: không sửa gì mà đóng -> KHÔNG hỏi.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
TMP = Path(tempfile.mkdtemp(prefix="bq_test_luu_key_"))
os.environ["BQ_DATA_DIR"] = str(TMP)
os.environ["BQ_DB_PATH"] = str(TMP / "studio.db")
os.environ["GROQ_API_KEYS"] = ""
(TMP / ".env").write_text("LLM_PROVIDER=groq\nGROQ_API_KEYS=gsk_A,gsk_B\n",
                          encoding="utf-8")

import _test_guard  # noqa: E402,F401
import config  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print("  ĐẠT ", ten, chi_tiet)
    else:
        HONG += 1
        print("  HỎNG", ten, chi_tiet)


def tren_dia():
    from dotenv import dotenv_values
    return dotenv_values(TMP / ".env").get("GROQ_API_KEYS", "")


print("CA 1: nạp lại từ đĩa")
config.Settings.GROQ_API_KEYS = "gsk_A"
config.Settings.GEMINI_MODEL = "giu-nguyen"
doi = config.nap_lai_tu_dia(("GROQ_API_KEYS", "GEMINI_MODEL"))
ok(config.Settings.GROQ_API_KEYS == "gsk_A,gsk_B", "key trên đĩa áp vào app",
   config.Settings.GROQ_API_KEYS)
ok(doi == ["GROQ_API_KEYS"], "chỉ báo khoá thật sự đổi", str(doi))
ok(config.Settings.GEMINI_MODEL == "giu-nguyen", "khoá không có trong file giữ nguyên")
_cu = config.DATA_DIR
config.DATA_DIR = TMP / "khong_co"
try:
    ok(config.nap_lai_tu_dia(("GROQ_API_KEYS",)) == [], "không có file -> [] không ném")
finally:
    config.DATA_DIR = _cu

print("CA 2-4: hộp Cài đặt AI thật")
from PyQt6.QtWidgets import (QApplication, QLabel, QMessageBox,  # noqa: E402
                             QPlainTextEdit, QWidget)
_APP = QApplication.instance() or QApplication([])
from app.ui import studio_page as SP  # noqa: E402


class Gia(QWidget):
    def __init__(self):
        super().__init__()
        self.status = QLabel()

    def _update_ai_status(self):
        pass

    def __getattr__(self, ten):          # thuộc tính phụ không liên quan
        raise AttributeError(ten)


tra_loi = []          # nhãn nút bấm trong hộp hỏi
da_hoi = []


def _hoi_exec(self):
    da_hoi.append(self.text())
    nhan = tra_loi.pop(0) if tra_loi else "Quay lại"
    for b in self.buttons():
        if b.text() == nhan:
            self._bam = b
    return 0


QMessageBox.exec = _hoi_exec
QMessageBox.clickedButton = lambda self: getattr(self, "_bam", None)
kich_ban = []


def _hop_exec(self):
    o = [w for w in self.findChildren(QPlainTextEdit)
         if "gsk_A" in w.toPlainText()]
    kich_ban[0](self, o[0] if o else None)
    return 0


SP._HopCaiDatAI.exec = _hop_exec


def mo(f):
    kich_ban[:] = [f]
    SP.StudioPage._ai_settings(Gia())


# đĩa có thêm gsk_C, bộ nhớ chưa biết
(TMP / ".env").write_text("LLM_PROVIDER=groq\nGROQ_API_KEYS=gsk_A,gsk_B,gsk_C\n",
                          encoding="utf-8")
kq = {}


def ca2(dlg, o):
    kq["o"] = o.toPlainText() if o else ""
    da_hoi.clear()
    dlg.reject()                         # không sửa gì
    kq["hoi"] = len(da_hoi)
    kq["mo"] = dlg.isVisible() or dlg.result() != 0


mo(ca2)
ok("gsk_C" in kq["o"], "CA2 ô Groq hiện key mới trên ĐĨA", repr(kq["o"]))
ok(kq["hoi"] == 0, "CA4 không sửa gì -> đóng không hỏi")


def ca3(dlg, o):
    o.setPlainText(o.toPlainText() + ",gsk_MOI")
    tra_loi[:] = ["Quay lại"]
    da_hoi.clear()
    dlg.setVisible(True)
    dlg.reject()
    kq["quay_lai_con_mo"] = dlg.isVisible()
    kq["hoi1"] = len(da_hoi)
    tra_loi[:] = ["Không lưu"]
    config.Settings.GROQ_API_KEYS = "gsk_TAM"      # như nút Kiểm tra áp tạm
    dlg.reject()
    kq["bo_dong"] = not dlg.isVisible()


mo(ca3)
ok(kq["hoi1"] == 1 and "CHƯA bấm Lưu" in "".join(da_hoi), "CA3 sửa rồi đóng -> HỎI")
ok(kq["quay_lai_con_mo"], "CA3 'Quay lại' -> hộp còn mở")
ok(kq["bo_dong"], "CA3 'Không lưu' -> đóng")
ok(config.Settings.GROQ_API_KEYS == "gsk_A,gsk_B,gsk_C",
   "CA3 'Không lưu' -> bộ nhớ trả về đúng file", config.Settings.GROQ_API_KEYS)
ok("gsk_MOI" not in tren_dia(), "CA3 'Không lưu' -> file không đổi")


def ca3b(dlg, o):
    o.setPlainText(o.toPlainText() + ",gsk_MOI")
    tra_loi[:] = ["Lưu"]
    dlg.reject()


mo(ca3b)
ok("gsk_MOI" in tren_dia(), "CA3 'Lưu' -> key vào file", tren_dia())
ok("gsk_MOI" in config.Settings.GROQ_API_KEYS, "CA3 'Lưu' -> app dùng ngay")

print(f"\nCỔNG 108: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
