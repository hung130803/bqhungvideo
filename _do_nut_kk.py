import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import _test_guard  # noqa: F401  - cấm mở Explorer / để rác %TEMP%
import tempfile, pathlib
sb = pathlib.Path(tempfile.mkdtemp(prefix="bq_kk_nut_"))
os.environ["BQ_DATA_DIR"] = str(sb / "data")
os.environ["BQ_DB_PATH"] = str(sb / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(sb / "qs.ini")

from PyQt6.QtWidgets import QApplication, QPushButton
from app.ui import theme
qapp = QApplication.instance() or QApplication([])
qapp.setStyleSheet(theme.QSS)          # QSS THẬT (bài học cổng 9)

from app.ui.thay_giong_dialog import ThayGiongDialog, giong_dung_duoc
from app.core import giong_kokoro as KK
from app.core.dubbing import list_recap_voices

print("=== 1. COMBO CÓ GIỌNG KOKORO CHƯA ===")
try:
    tho = list_recap_voices()
except Exception as e:
    print("   (offline) list_recap_voices:", type(e).__name__); tho = []
ds = giong_dung_duoc(tho)
kk = [(n, v) for n, v in ds if str(v).startswith("kk:")]
print(f"   dòng kk: trong giong_dung_duoc = {len(kk)}")
for n, v in kk[:3]:
    print("   *", v, "->", n[:110])

print("\n=== 2. HỘP THOẠI DỰNG ĐƯỢC + NÚT TỒN TẠI ===")
d = ThayGiongDialog(None, None)
print("   hộp dựng: OK")
print("   có b_tai_kokoro:", hasattr(d, "b_tai_kokoro"))
print("   có lb_kokoro   :", hasattr(d, "lb_kokoro"))
tt = d._tt_kokoro
print("   thieu =", tt.get("thieu"), "| cai_duoc =", tt.get("cai_duoc"))
print("   nút hiện:", d.b_tai_kokoro.isVisible() or not d.isVisible(),
      "| bật được:", d.b_tai_kokoro.isEnabled())
print("   nhãn nút:", d.b_tai_kokoro.text())
print("   nhãn dòng:", d.lb_kokoro.text()[:160].replace("\n", " | "))

print("\n=== 3. NÚT BÁM `thieu` CHỨ KHÔNG BÁM `co` ===")
# Giả lập ca CÀI DỞ: máy chạy được nhưng môi trường riêng thiếu gói
that = KK.tinh_trang
KK.tinh_trang = lambda: dict(that(), co=True, du_venv=False,
                             thieu=["torch"], cai_duoc=True)
d._do_kokoro()
hien_do = d.b_tai_kokoro.isVisible() or not d.isVisible()
print("   co=True nhưng thieu=[torch] -> nút còn hiện:",
      "CÓ" if hien_do else "KHÔNG (SAI - bám `co`)")
print("   nhãn:", d.lb_kokoro.text()[:150].replace("\n", " | "))
KK.tinh_trang = that

print("\n=== 4. THIẾU PYTHON -> KHOÁ NÚT + NÓI VÌ SAO ===")
KK.tinh_trang = lambda: dict(that(), thieu=["môi trường Python riêng"],
                             cai_duoc=False,
                             vi_sao="máy chưa cài Python 3")
d._do_kokoro()
print("   bật được:", d.b_tai_kokoro.isEnabled(), "(phải là False)")
print("   nhãn có nói lý do:", "Python" in d.lb_kokoro.text())
KK.tinh_trang = that

print("\n=== 5. DÒ HỎNG THÌ HỘP KHÔNG ĐƯỢC CHẾT ===")
def no(): raise RuntimeError("dò hỏng thử")
KK.tinh_trang = no
try:
    r = d._do_kokoro()
    print("   KHÔNG chết, trả:", r.get("thieu"))
except Exception as e:
    print("   *** CHẾT:", type(e).__name__, e)
KK.tinh_trang = that

print("\n=== 6. NHÃN NÚT KHỚP PHÉP ĐO (không phải số chép tay) ===")
print("   nhan_tai()  =", KK.nhan_tai())
print("   mb_se_tai() =", round(KK.mb_se_tai(), 1), "MB")

print("\n=== 7. NHÃN KHÔNG EMOJI (bài học v2.6.22 ô đen) ===")
xau = [c for w in d.findChildren(QPushButton) for c in w.text()
       if ord(c) > 0x2100]
print("   ký tự dễ thiếu font trong MỌI nhãn nút:", xau or "KHÔNG CÓ")

d.deleteLater(); qapp.processEvents()
import shutil; shutil.rmtree(sb, ignore_errors=True)
print("\nXONG")
