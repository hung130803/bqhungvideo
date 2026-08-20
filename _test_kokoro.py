"""CỔNG 87 — GIỌNG KOKORO: 28 giọng Apache 2.0, nối vào UI, gọi GỘP.

Vì sao có cổng này: `app/core/giong_kokoro.py` viết xong đủ hàm đọc + hàm cài từ
lâu mà **UI không gọi tới một dòng nào** — đo trước khi vá (v2.41.0):
`grep -c "kk:" app/ui/thay_giong_dialog.py` -> **0**. Tức mọi thứ dưới đây từng
đúng ở tầng hàm và **sai ở tầng người dùng**, mà không cổng nào bắt được.
Ca thứ TƯ của cùng bệnh sau `giong_bang`, `giong_chatter`, `giong_vbee`.

SỐ CỔNG LÀ 87, đọc bằng `_chay_hoi_quy.CONG` chứ không đếm theo trí nhớ — bảng
đó đang có **52 và 77 trùng số**, mà trùng số thì hai cổng **ghi đè `_kqNN.txt`
của nhau** (bài học 70 vs 69, 85 vs 81).

KHÔNG gọi mạng. KHÔNG tốn lượt Groq/ElevenLabs. Có đọc THẬT bằng Kokoro trên
máy (nếu máy đã tải) — xem CA 9 và phần "PHẠM VI CÓ HẠN" của nó.
"""
from __future__ import annotations

import ast
import inspect
import math
import os
import sys
import tempfile
import wave
from array import array
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")          # cp1252 giết cổng khi > file
GOC = str(Path(__file__).resolve().parent)        # KHÔNG ghi cứng đường repo
if GOC not in sys.path:
    sys.path.insert(0, GOC)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _test_guard                                # noqa: E402,F401

SB = Path(tempfile.mkdtemp(prefix="bq_kk87_"))
os.environ["BQ_DATA_DIR"] = str(SB / "data")
os.environ["BQ_DB_PATH"] = str(SB / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(SB / "qs.ini")   # KHÔNG ghi QSettings thật

DAT: list[str] = []
HONG: list[str] = []
BO_QUA: list[str] = []


def ok(dieu: bool, ten: str, chi_tiet: str = "") -> bool:
    (DAT if dieu else HONG).append(ten + (f" [{chi_tiet}]" if chi_tiet else ""))
    print(("  ĐẠT  " if dieu else "  HỎNG ") + ten + (f"  [{chi_tiet}]" if chi_tiet else ""))
    return dieu


def bo_qua(ten: str, vi_sao: str) -> None:
    """KHÔNG đếm là ĐẠT (đó là 'phép đo phát chứng nhận') và KHÔNG đếm là HỎNG
    (đỏ oan thì người ta bỏ qua cổng — bài học cổng 41/47)."""
    BO_QUA.append(f"{ten} — {vi_sao}")
    print(f"  BỎ QUA {ten}  [{vi_sao}]")


def than_ham(mod, ten: str) -> ast.AST:
    """AST của MỘT hàm, đọc file bằng utf-8 rồi lấy đúng nút theo tên.

    KHÔNG `inspect.getsource` + `ast.parse`: `getsource` mở file theo bảng mã
    MẶC ĐỊNH của máy (cp1252) nên docstring tiếng Việt ra mojibake rồi parse nổ
    — đã sập ở cổng 71. Và không tự cắt thụt lề: cắt là ăn vào THÂN docstring
    nhiều dòng -> IndentationError.
    """
    cay = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ten:
            return n
    raise AssertionError(f"không thấy hàm {ten} trong {mod.__name__}")


def goi_trong(nut: ast.AST, ten_ham: str) -> list[ast.Call]:
    return [n for n in ast.walk(nut) if isinstance(n, ast.Call)
            and (getattr(n.func, "id", "") == ten_ham
                 or getattr(n.func, "attr", "") == ten_ham)]


print("=" * 62)
print("CỔNG 87 — GIỌNG KOKORO")
print("=" * 62)

from app.core import dubbing                                     # noqa: E402
from app.core import giong_bang as GB                            # noqa: E402
from app.core import giong_kokoro as KK                          # noqa: E402

# ══════════════════════════════════════════════════════════════════════
print("\nCA 1 — ĐĂNG KÝ ĐỦ **CẢ HAI** CỬA ĐỌC")
# Sót MỘT cửa = video ra HAI GIỌNG TRỘN mà `rc` vẫn 0, không một dòng báo.
# Bẫy này đã cắn BA lần: `ov:nu_am`, `vn:`, `cb:`. Đọc bằng AST, không đọc mắt,
# và không tìm bằng chuỗi — ghi chú tiếng Việt trong file có chứa đúng tên hàm
# nên tìm chuỗi thì gỡ sạch nhánh rẽ mà cổng vẫn XANH (bài học 56d, chiều
# PASS OAN).
CUA = ("_synth_all", "_synth_all_words")
for cua in CUA:
    g = goi_trong(than_ham(dubbing, cua), "_chay_kokoro")
    ok(len(g) >= 1, f"1a {cua} có GỌI _chay_kokoro", f"{len(g)} lượt gọi")

# TỰ KIỂM BỘ DÒ: nếu bộ dò trên luôn tìm thấy thứ gì đó thì nó là con dấu.
gia = goi_trong(than_ham(dubbing, "_synth_all"), "_ham_khong_ton_tai_bao_gio")
ok(not gia, "1b TỰ KIỂM: bộ dò KHÔNG tìm thấy hàm bịa", f"{len(gia)}")

# ══════════════════════════════════════════════════════════════════════
print("\nCA 2 — 28 DÒNG GIỌNG CÓ MẶT TRONG COMBO (lỗi v2.41.0 vừa vá)")
from app.ui.thay_giong_dialog import giong_dung_duoc                # noqa: E402

ds = giong_dung_duoc([])          # danh sách thô RỖNG = ca offline, khắt khe hơn
dong_kk = [(n, v) for n, v in ds if str(v).startswith(KK.TIEN_TO)]
ok(len(dong_kk) == len(KK.GIONG_KK),
   f"2a combo có ĐỦ {len(KK.GIONG_KK)} dòng kk:", f"{len(dong_kk)}")
ok(len(KK.danh_sach_giong()) == len(KK.GIONG_KK),
   "2b danh_sach_giong trả đủ (KHÔNG ẩn dòng khi chưa tải)",
   f"{len(KK.danh_sach_giong())}")
# `gom_nhom` là chỗ combo THẬT lấy dòng ra — hàm trên đúng mà chỗ này rơi thì
# anh Hùng vẫn không thấy giọng nào.
try:
    nhom = GB.gom_nhom(ds, "en", loi_tat=True)
    con = sum(1 for x in nhom if str(x[1] if len(x) > 1 else "").startswith(KK.TIEN_TO))
    ok(con >= 1, "2c gom_nhom KHÔNG lọc mất giọng kk:", f"còn {con} dòng")
except Exception as e:                                          # noqa: BLE001
    ok(False, "2c gom_nhom chạy được", f"{type(e).__name__}: {e}")
ok(GB.nguon("kk:af_bella") == "kokoro", "2d giong_bang.nguon -> kokoro",
   str(GB.nguon("kk:af_bella")))

# ══════════════════════════════════════════════════════════════════════
print("\nCA 3 — GỌI **GỘP**, KHÔNG GỌI TỪNG CÂU")
# ĐO ĐƯỢC (`_do_kk_gom.py`, 12 câu, 2 vòng đan xen, lượt nhanh nhất mỗi bên):
#   lẻ 90,44s (7,54 s/câu) · gộp 16,91s (1,41 s/câu) = GỘP RẺ HƠN 5,35 LẦN.
# Suy ra video 45 câu: ~339s so với ~63s. Gốc: mỗi lượt gọi là một tiến trình
# rời và **nạp lại model** — lượt đầu đo 60,5s so với 9,2s các lượt sau, tức
# đắt hơn bệnh Piper ("~2,2s mỗi lượt") **27 lần**.
# Vì vậy đối số thứ nhất phải là TÊN BIẾN danh sách, KHÔNG được là `texts[i]`.
for cua in CUA:
    g = goi_trong(than_ham(dubbing, cua), "_chay_kokoro")
    xau = [c for c in g if not isinstance(c.args[0], ast.Name)] if g else []
    ok(bool(g) and not xau, f"3a {cua} truyền CẢ LOẠT vào _chay_kokoro",
       ", ".join(ast.unparse(c.args[0]) for c in (xau or g)) if g else "không có lượt gọi")

# ══════════════════════════════════════════════════════════════════════
print("\nCA 4 — HỘP THOẠI: NÚT BÁM `thieu`, **KHÔNG BÁM `co`**")
# Đây là chỗ CẢ TÍNH NĂNG có thể chết âm thầm (bài học cổng 58): bám `co` thì
# trên máy dev — nơi `co` True nhờ mượn gói của `.venv` — nút BIẾN MẤT, không
# ai bấm, và bản `.exe` mãi mãi thiếu. Máy dev xanh, máy anh Hùng đỏ.
from PyQt6.QtWidgets import QApplication, QPushButton                # noqa: E402
from app.ui import theme                                            # noqa: E402
from app.ui.thay_giong_dialog import ThayGiongDialog                 # noqa: E402

qapp = QApplication.instance() or QApplication([])
qapp.setStyleSheet(theme.QSS)          # QSS THẬT (bài học cổng 9 — dòng trống)
dlg = ThayGiongDialog(None, None)
ok(hasattr(dlg, "b_tai_kokoro") and hasattr(dlg, "lb_kokoro"),
   "4a hộp có nút + nhãn Kokoro")

that = KK.tinh_trang


def va(**kw):
    KK.tinh_trang = lambda: dict(that(), **kw)


try:
    va(co=True, du_venv=False, thieu=["torch"], cai_duoc=True)
    dlg._do_kokoro()
    # `isVisible()` là False cho mọi widget của hộp CHƯA show -> phải hỏi cờ
    # `isHidden()` (thứ `setVisible` đặt) chứ không hỏi trạng thái vẽ.
    ok(not dlg.b_tai_kokoro.isHidden(),
       "4b co=True + thieu=[torch] -> nút VẪN HIỆN (bám `thieu`)")
    ok("torch" in dlg.lb_kokoro.text(),
       "4c nhãn NÊU ĐÍCH DANH gói còn thiếu")

    print("\nCA 5 — THIẾU PYTHON -> KHOÁ NÚT **VÀ** NÓI VÌ SAO")
    # Khoá mà không nói lý do thì nút xám là một câu đố.
    va(thieu=["môi trường Python riêng"], cai_duoc=False,
       vi_sao="máy chưa cài Python 3")
    dlg._do_kokoro()
    ok(not dlg.b_tai_kokoro.isEnabled(), "5a nút bị KHOÁ")
    ok("Python" in dlg.lb_kokoro.text(), "5b nhãn nói RÕ vì sao khoá")

    print("\nCA 6 — DÒ HỎNG THÌ HỘP **KHÔNG ĐƯỢC CHẾT**")
    # `tinh_trang` hứa KHÔNG BAO GIỜ NÉM, nhưng hộp thoại không được phụ thuộc
    # vào lời hứa đó — một hộp chết là anh Hùng mất cả đường thay giọng.
    def nem():
        raise RuntimeError("dò hỏng thử")
    KK.tinh_trang = nem
    try:
        r = dlg._do_kokoro()
        ok(bool(r.get("thieu")), "6a không chết + báo là chưa dò được",
           str(r.get("thieu"))[:60])
    except Exception as e:                                      # noqa: BLE001
        ok(False, "6a không chết", f"{type(e).__name__}: {e}")
finally:
    KK.tinh_trang = that
    dlg._do_kokoro()

# ══════════════════════════════════════════════════════════════════════
print("\nCA 7 — NHÃN NÚT PHẢI KHỚP **PHÉP ĐO**, KHÔNG PHẢI SỐ CHÉP TAY")
# Bài học cổng 58: nhãn Demucs từng ghi "khoảng 2 GB" trong khi lượng tải thật
# là 154 MB (gấp 13 lần), và anh Hùng bấm nút ghi 155 MB rồi bị hộp doạ 2 GB.
mb = KK.mb_se_tai()
nhan = KK.nhan_tai()
so_trong_nhan = "".join(c for c in nhan if c.isdigit() or c == ".")
# **CỔNG PHẢI BÁO HỎNG, KHÔNG ĐƯỢC CHẾT.** Bản đầu viết `float(...)` trần: nhãn
# không có chữ số nào (đúng ca hằng số bị khai trùng bởi bản "chưa đo dung
# lượng") thì `float("")` ném ValueError -> cổng **chết giữa chừng, mất luôn
# dòng tổng kết**, đọc ra không phân biệt được với "chưa chạy tới chốt". Đúng
# bài học cổng 74; phép thử phá số 5 đã lôi ra.
try:
    khop = abs(float(so_trong_nhan.replace(".", "")) - mb) <= max(5.0, mb * 0.02)
except ValueError:
    khop = False
ok(khop, "7a số trong nhãn nút khớp mb_se_tai()",
   f"nhãn «{nhan}» vs đo {mb:.1f} MB"
   + ("" if so_trong_nhan else " — NHÃN KHÔNG CÓ CON SỐ NÀO"))

# MỘT HẰNG SỐ = MỘT CHỖ KHAI. File này từng có HAI `NHAN_TAI`, bản trên ghi
# "chưa đo dung lượng": Python lấy bản SAU nên nhãn hiện ra vẫn đúng, **nhưng
# ai đọc file từ trên xuống thì thấy bản CŨ và tưởng app chưa đo**.
src = Path(KK.__file__).read_text(encoding="utf-8")
cay = ast.parse(src)
dem = sum(1 for n in ast.walk(cay) if isinstance(n, ast.Assign)
          for t in n.targets if getattr(t, "id", "") == "NHAN_TAI")
ok(dem == 1, "7b NHAN_TAI khai ĐÚNG MỘT chỗ", f"{dem} chỗ khai")

# ══════════════════════════════════════════════════════════════════════
print("\nCA 8 — NHÃN KHÔNG EMOJI (v2.6.22: máy anh Hùng ra Ô ĐEN)")
# Chỉ soi NHÃN NÚT, KHÔNG soi cả file — emoji trong dòng ghi chú thì người dùng
# không thấy, soi cả file là ĐỎ OAN (bản đầu của cổng 27 đã sập).
xau = sorted({c for w in dlg.findChildren(QPushButton) for c in w.text()
              if ord(c) > 0x2100})
ok(not xau, "8a mọi nhãn nút KHÔNG có ký tự dễ thiếu font",
   " ".join(f"U+{ord(c):04X}" for c in xau) or "sạch")
ok(not any(ord(c) > 0x2100 for c in (KK.NHAN_TAI + KK.NHAN_TAI_CUDA)),
   "8b hằng số nhãn tải cũng sạch")

# ══════════════════════════════════════════════════════════════════════
print("\nCA 9 — ĐỌC THẬT: GIỌNG PHẢI **KÊU**, KHÔNG CÂM")
# `doc_loat` trả True/False, nhưng "True" KHÔNG đồng nghĩa "nghe được":
# `_kiem_wav` chỉ hỏi có tiếng không. Nên đọc mẫu WAV THẲNG.
#
# **PHẠM VI CÓ HẠN — NÓI RA, KHÔNG GIẤU** (luật "no silent caps"): cổng chỉ đọc
# thật MẪU dưới đây, vì mỗi giọng là một tiến trình rời ~9 giây (28 giọng ≈ 4,4
# phút, quá đắt cho một lượt hồi quy 41 cổng). Bảng ĐỦ 28 giọng đo bằng
# `_do_28_giong_kk.py` -> `_kq_kk28.json`: **28/28 KÊU, 0 CÂM**, dài 3,00-4,75 s,
# RMS 0,02967 (af_nova, thấp nhất) - 0,08133 (af_aoede).
# Mẫu chọn có chủ ý: điểm CAO nhất · điểm THẤP nhất (`am_adam` F+, dễ hỏng nhất
# theo chính tác giả) · RMS thấp nhất đã đo (`af_nova`, sát sàn nhất) · một
# giọng Anh-Anh (`bm_george`, khác bộ âm).
MAU = ["af_bella", "am_adam", "af_nova", "bm_george"]
print(f"  (đọc thật {len(MAU)}/{len(KK.GIONG_KK)} giọng: "
      f"{', '.join(MAU)} — 24 giọng còn lại xem _kq_kk28.json)")


def do_wav(p: Path) -> tuple[float, float]:
    with wave.open(str(p), "rb") as w:
        n, sr, sw = w.getnframes(), w.getframerate(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2 or not n:
        return (n / sr if sr else 0.0), 0.0
    a = array("h")
    a.frombytes(raw)
    return n / sr, math.sqrt(sum(float(v) * v for v in a) / len(a)) / 32768.0


if not KK.co_kokoro():
    bo_qua("9 đọc thật", "máy này chưa tải bộ Kokoro (đúng ca máy nhân viên)")
else:
    for m in MAU:
        p = SB / f"{m}.wav"
        try:
            r = KK.doc_loat(["This is a gate sentence."], [str(p)],
                            KK.TIEN_TO + m)
            duoc = bool(r and r[0]) and p.is_file()
        except Exception as e:                                  # noqa: BLE001
            duoc, r = False, f"{type(e).__name__}: {e}"
        d, rms = do_wav(p) if duoc else (0.0, 0.0)
        ok(duoc and d >= 0.5 and rms >= KK.RMS_TOI_THIEU,
           f"9 {m} đọc ra WAV CÓ TIẾNG",
           f"dài {d:.2f}s · rms {rms:.5f} (sàn {KK.RMS_TOI_THIEU})")

# ══════════════════════════════════════════════════════════════════════
print("\nCA 10 — GIỌNG TÁC GIẢ CHẤM THẤP PHẢI **KÊU** TRONG NHÃN")
# Anh Hùng đã chốt "cứ thêm hết, tôi tự trải nghiệm" -> KHÔNG chặn, KHÔNG giấu.
# Nhưng nhãn phải nói thật, không để anh ấy tự phát hiện sau 300 video.
tt = KK.tinh_trang()
keu = [m for m, _mo, d in KK.GIONG_KK if d in KK.DIEM_KEU]
ok(bool(keu), "10a có giọng bị tác giả chấm thấp trong bộ", ", ".join(keu))
for m in keu:
    n = KK.nhan_giong(m, tt)
    ok("TÁC GIẢ CHẤM THẤP" in n, f"10b nhãn {m} có cảnh báo", n[:80])
tot = KK.nhan_giong("af_bella", tt)
ok("TÁC GIẢ CHẤM THẤP" not in tot,
   "10c TỰ KIỂM: giọng điểm CAO không bị dán cảnh báo oan", tot[:70])

# ══════════════════════════════════════════════════════════════════════
print("\nCA 11 — THIẾU KOKORO THÌ **LÙI ÊM**, KHÔNG CHẶN, KHÔNG NỔ")
# KHÁC HẲN Demucs (cổng 55: thiếu là CHẶN). Lý do khác nhau: thiếu Demucs thì
# lùi ra video HỎNG (giọng gốc còn chồng lên giọng mới); thiếu Kokoro thì video
# ra ĐÚNG, chỉ khác giọng. Nên ở đây lùi là đúng — và phải GHI LOG, vì lùi im
# lặng là anh Hùng nghe một giọng khác cái mình chọn.
co_that = KK.co_kokoro
KK.co_kokoro = lambda: False
try:
    dung, voice = dubbing._kokoro_hay_khong("kk:af_bella")
    ok(dung is False, "11a máy thiếu -> KHÔNG đi đường Kokoro", f"dung={dung}")
    ok(bool(voice) and not str(voice).startswith(KK.TIEN_TO),
       "11b lùi sang giọng KHÁC, không trả mã kk: trơ", str(voice))
finally:
    KK.co_kokoro = co_that
dung2, _v2 = dubbing._kokoro_hay_khong("vi-VN-HoaiMyNeural")
ok(dung2 is False, "11c TỰ KIỂM: giọng KHÔNG phải kk: thì cửa này không nhận")

# ══════════════════════════════════════════════════════════════════════
print("\nCA 12 — TIỀN TỐ ĐĂNG KÝ ĐỦ Ở `giong_bang` (đường gom nhóm)")
ok(KK.la_giong_kokoro("kk:af_bella") and not KK.la_giong_kokoro("vn:Adam"),
   "12a la_giong_kokoro nhận đúng, không nhận bừa")
ok(KK.tach_ma("kk:af_bella") == "af_bella",
   "12b tach_ma bỏ tiền tố", KK.tach_ma("kk:af_bella"))
try:
    ok(GB.mien_phi("kk:af_bella") is True,
       "12c đánh dấu MIỄN PHÍ (Apache 2.0, không tốn hạn mức)")
    ok(GB.tren_may("kk:af_bella") is True, "12d đánh dấu chạy TRÊN MÁY")
except Exception as e:                                          # noqa: BLE001
    ok(False, "12c/12d giong_bang trả lời được", f"{type(e).__name__}: {e}")

# ══════════════════════════════════════════════════════════════════════
dlg.deleteLater()
qapp.processEvents()
import shutil                                                    # noqa: E402
shutil.rmtree(SB, ignore_errors=True)

print("\n" + "=" * 62)
print(f"ĐẠT {len(DAT)} · HỎNG {len(HONG)}"
      + (f" · BỎ QUA {len(BO_QUA)}" if BO_QUA else ""))
for h in HONG:
    print("  HỎNG:", h)
for b in BO_QUA:
    print("  BỎ QUA:", b)
print("=" * 62)
sys.exit(1 if HONG else 0)
