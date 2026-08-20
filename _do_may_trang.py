"""ĐO: máy TRẮNG có đi tới WAV CÓ TIẾNG chỉ bằng nút trong app hay không.

Bốn câu phải trả lời bằng SỐ, không bằng lập luận:

1. **python nào chạy đường đọc** — trước và sau.
2. **BẤT BIẾN HAI CHIỀU**: ``thieu_de_nhan_ban() == []`` **⇔** đọc thật ra
   tiếng. Bug anh Hùng gặp đúng là hai điều đó LỆCH nhau, nên phải đo CẢ HAI
   chiều chứ không chỉ chiều dễ.
3. **20 giọng VieNeu dựng sẵn** còn nguyên không (chúng đi `onnxruntime`,
   không cần torch) — đo TRƯỚC và SAU.
4. Môi trường đang nằm ở đâu: chỗ CHUẨN hay `%TEMP%`.

**KHÔNG SỬA GÌ, KHÔNG CÀI GÌ, KHÔNG XOÁ GÌ.** Script này chỉ ĐỌC. Nó cố ý
không gọi `cai_nhan_ban()` vì làm thế là đụng `_giong_vieneu/venv` của máy dev
(luật: tuyệt đối không phá môi trường đang dùng được).
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")            # type: ignore[union-attr]
os.environ.setdefault("BQ_QSETTINGS_INI",
                      tempfile.mkdtemp(prefix="bq_do_trang_"))

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import config                                        # noqa: E402,F401
from app.core import giong_vieneu as VN               # noqa: E402
from app.core import nhan_ban_giong as NB             # noqa: E402

KQ: dict = {}


def muc(ten: str, gia_tri) -> None:
    KQ[ten] = gia_tri
    print(f"  {ten:38s} = {gia_tri}")


print("=" * 74)
print("1. PYTHON NÀO CHẠY ĐƯỜNG ĐỌC")
print("=" * 74)
tt = VN.tinh_trang_vieneu()
py = str(tt.get("python") or "")
muc("python chạy đường đọc", py or "(KHÔNG CÓ)")
muc("venv THẬT pip sẽ cài vào", str(VN._venv_that(py)) if py else "-")
muc("thư mục CHUẨN", str(VN.thu_muc_vieneu()))
muc("đang ở %TEMP% ?", bool(tt.get("o_tam")))
if tt.get("o_tam"):
    print("     CẢNH BÁO: " + str(tt["o_tam"])[:160])
muc("ứng viên python (thứ tự)",
    [str(p) for p in VN._ung_vien_python()])

print("=" * 74)
print("2. 20 GIỌNG DỰNG SẴN — ĐO TRƯỚC (chúng đi onnxruntime, KHÔNG cần torch)")
print("=" * 74)
ds = VN.danh_sach_giong(du_chua_tai=True)
muc("số giọng dựng sẵn trong bảng", len(VN.GIONG_VN))
muc("số dòng combo dựng sẵn", len(ds))
muc("co_vieneu()", VN.co_vieneu())
muc("thiếu (bộ giọng)", tt.get("thieu"))

print("=" * 74)
print("3. BẤT BIẾN HAI CHIỀU: thieu == [] <=> đọc thật ra tiếng")
print("=" * 74)
thieu = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
muc("thieu_de_nhan_ban('vieneu')", thieu)
muc("may_chay_duoc('vieneu')", NB.may_chay_duoc(NB.MAY_VIENEU))

doc_ok = None
chi_tiet = ""
if not py:
    print("  BỎ QUA đọc thật: máy này chưa có môi trường VieNeu nào.")
else:
    with tempfile.TemporaryDirectory(prefix="bq_doc_that_") as td:
        d = Path(td)
        mau = VN._mau_thu(d)
        muc("WAV mẫu tự sinh (ffmpeg)", mau or "(HỎNG)")
        if mau:
            muc("mẫu: dài/RMS", VN.do_wav(mau))
            t0 = time.time()
            print("  ... đang ĐỌC THẬT qua đường nhân bản "
                  "(lượt đầu ~38 giây vì nạp model)")
            kq = VN._doc_thu_nhan_ban(Path(py), mau, d / "ra.wav",
                                      han_giay=900)
            doc_ok = bool(kq["ok"])
            chi_tiet = str(kq.get("loi") or "")
            muc("ĐỌC THẬT ok", doc_ok)
            muc("WAV ra: dài giây", kq.get("giay"))
            muc("WAV ra: RMS", kq.get("rms"))
            muc("giây chạy", round(time.time() - t0, 1))
            if chi_tiet:
                print("     lời lỗi: " + chi_tiet[:300])
                ten = VN._ten_thieu(chi_tiet)
                muc("gói bóc được từ lời lỗi", ten or "(không phải thiếu gói)")

print("-" * 74)
# ═══ CHẤM BẤT BIẾN ═══
# Hai chiều, và chiều nào cũng phải nói ra. Chiều "thieu=[] mà đọc HỎNG" đúng
# là bug anh Hùng gặp (hậu kiểm tĩnh xanh, đọc thật đỏ).
if doc_ok is None:
    print("BẤT BIẾN: CHƯA ĐO ĐƯỢC (không có môi trường / không dựng nổi mẫu)")
    KQ["bat_bien"] = "chua_do"
elif (not thieu) == doc_ok:
    print(f"BẤT BIẾN GIỮ: thieu=={thieu!r} và đọc-ra-tiếng=={doc_ok} — KHỚP")
    KQ["bat_bien"] = "khop"
else:
    print(f"BẤT BIẾN VỠ: thieu=={thieu!r} nhưng đọc-ra-tiếng=={doc_ok}")
    print("   -> ĐÂY LÀ ĐÚNG BUG ANH HÙNG GẶP: một bên nói đủ, bên kia hỏng.")
    KQ["bat_bien"] = "vo"

print("=" * 74)
print("4. 20 GIỌNG DỰNG SẴN — ĐO SAU (phải KHÔNG ĐỔI)")
print("=" * 74)
ds2 = VN.danh_sach_giong(du_chua_tai=True)
muc("số dòng combo dựng sẵn (sau)", len(ds2))
muc("KHÔNG ĐỔI ?", len(ds2) == len(ds))

(REPO / "_kq_may_trang.json").write_text(
    json.dumps(KQ, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nĐã ghi _kq_may_trang.json")
