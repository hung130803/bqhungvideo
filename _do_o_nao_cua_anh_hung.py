"""LỜI KÊU 4 — "nó CHỈNH TỐC ĐỘ GIỌNG ĐỌC chứ không phải tốc độ video":
ANH HÙNG ĐANG Ở Ô NÀO, Ô ĐÓ CÓ CHẠY BƯỚC 4C KHÔNG, VÀ NHÃN Ô CÓ NÓI ĐÚNG KHÔNG.

Ba câu hỏi, ba phép đo, **không câu nào trả lời bằng cách đọc mã**:

  (1) **ANH HÙNG Ở Ô NÀO** — đọc THẲNG `HKCU\\Software\\AIContentStudio\\studio`
      khoá `tg_khop_cach` (đúng khoá `K_KHOP_CACH` mà `thay_giong_dialog` ghi).
      Không suy từ ảnh màn hình, không hỏi lại.
  (2) **Ô ĐÓ CÓ CHẠY 4C KHÔNG** — **GỌI THẬT** `thay_giong_video` cho CẢ BA ô
      rồi ĐẾM số lần `doc_nhanh_vua_khung` bị gọi. Mượn đúng bộ đồ nghề của
      cổng 89 (`_test_am_va_hinh._chay_that`): 5 cửa ra mạng bị thay bản giả,
      bản giả của 4c **có đếm**. Bài học *"hàm xong ≠ tính năng xong"*: quét mã
      chỉ chứng minh CÓ nhánh, chỉ lượt chạy mới chứng minh nhánh ĐƯỢC ĐI VÀO.
      Giá trị ô đi qua ĐÚNG cửa UI dùng (`chuan_khop_cach`), không tự đặt cờ.
  (3) **NHÃN Ô CÓ NÓI ĐÚNG KHÔNG** — đối chiếu chữ trong `NHAN_KHOP_CACH` với
      số ĐÃ ĐO ở CLAUDE.md mục (11): hệ số biến thiên tốc độ đọc giữa các câu.

    .venv\\Scripts\\python _do_o_nao_cua_anh_hung.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

#: Test KHÔNG được ghi QSettings thật của anh Hùng (bài học "test đừng ghi
#: QSettings"). Đặt TRƯỚC khi import bất cứ thứ gì chạm Qt.
os.environ.setdefault(
    "BQ_QSETTINGS_INI",
    str(Path(tempfile.gettempdir()) / "bq_do_o_nao.ini"))

KQ = REPO / "_kq_o_nao_anh_hung.json"

#: Hệ số biến thiên tốc độ đọc giữa các câu (%) — CHÉP TỪ BẢNG ĐÃ ĐO ở
#: CLAUDE.md mục (11), 2 video thật × 90 s, ghép cặp MỘT lượt chạy/video.
#: Càng THẤP càng "đọc đều". Đây là số cũ, KHÔNG đo lại trong script này.
CV_DA_DO = {"": (20.11, 14.08), "hinh": (20.77, 14.26),
            "hinh_deu": (15.64, 10.88)}


def o_cua_anh_hung() -> str:
    """Đọc thẳng registry — CHỈ ĐỌC, không ghi."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\AIContentStudio\studio") as k:
            return str(winreg.QueryValueEx(k, "tg_khop_cach")[0])
    except Exception as e:                                  # noqa: BLE001
        return f"<KHÔNG ĐỌC ĐƯỢC: {e}>"


def main() -> int:
    import _test_am_va_hinh as G
    from app.core import thay_giong as TG

    ket: dict = {}

    # ---------- (1) ANH HÙNG Ở Ô NÀO ----------
    o = o_cua_anh_hung()
    hinh, deu = TG.chuan_khop_cach(o)
    muc = {v: i + 1 for i, v in enumerate(TG.KHOP_CACH)}.get(o, "?")
    ket["o_cua_anh_hung"] = {
        "tg_khop_cach": o, "muc_thu": muc,
        "nhan": TG.NHAN_KHOP_CACH.get(o, "?"),
        "hinh_theo_giong": hinh, "doc_deu": deu}
    print("=" * 76)
    print(f"(1) QSettings tg_khop_cach = {o!r}  ->  MỤC {muc}")
    print(f"    nhãn đang hiện: \"{TG.NHAN_KHOP_CACH.get(o, '?')}\"")
    print(f"    -> hinh_theo_giong={hinh} · doc_deu={deu}")

    # ---------- (2) GỌI THẬT, ĐẾM 4C ----------
    print("\n(2) GỌI THẬT `thay_giong_video` cho CẢ BA ô, đếm lượt gọi "
          "`doc_nhanh_vua_khung`:")
    ket["dem_4c"] = {}
    base = Path(tempfile.mkdtemp(prefix="bq_do_o_nao_"))
    try:
        for i, val in enumerate(TG.KHOP_CACH):
            h, d = TG.chuan_khop_cach(val)      # ĐÚNG cửa UI dùng
            kq, n = G._chay_that(base / f"o{i}",      # noqa: SLF001
                                 hinh_theo_giong=h, doc_deu=d)
            hs = (kq.get("hinh") or {}).get("he_so") or 1.0
            ket["dem_4c"][val] = {
                "muc_thu": i + 1, "nhan": TG.NHAN_KHOP_CACH[val],
                "hinh_theo_giong": h, "doc_deu": d,
                "SO_LAN_GOI_4C": n, "ok": bool(kq.get("ok")),
                "he_so_hinh": hs}
            print(f"    MỤC {i+1} ({val or 'mặc định'!r:<12}) "
                  f"hinh={int(h)} deu={int(d)}  ->  4c chạy {n} lần"
                  f"   · hệ số hình {hs}   · ra video: "
                  f"{'CÓ' if kq.get('ok') else 'KHÔNG'}")
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)

    # ---------- (3) NHÃN CÓ NÓI ĐÚNG KHÔNG ----------
    print("\n(3) NHÃN Ô vs SỐ ĐÃ ĐO (hệ số biến thiên tốc độ đọc, THẤP = đều):")
    ket["nhan_vs_so"] = {}
    for i, val in enumerate(TG.KHOP_CACH):
        cv = CV_DA_DO[val]
        ket["nhan_vs_so"][val] = {
            "muc_thu": i + 1, "nhan": TG.NHAN_KHOP_CACH[val],
            "CV_lt1": cv[0], "CV_lt2": cv[1],
            "so_lan_4c": ket["dem_4c"][val]["SO_LAN_GOI_4C"]}
        print(f"    MỤC {i+1}  CV {cv[0]:>5.2f} / {cv[1]:>5.2f} %   "
              f"4c {ket['dem_4c'][val]['SO_LAN_GOI_4C']} lần   "
              f"| \"{TG.NHAN_KHOP_CACH[val]}\"")

    deu_nhat = min(TG.KHOP_CACH, key=lambda v: sum(CV_DA_DO[v]))
    co_chu_deu = [v for v in TG.KHOP_CACH
                  if "đều" in TG.NHAN_KHOP_CACH[v].lower()]
    ket["muc_DEU_NHAT_theo_so"] = deu_nhat
    ket["muc_co_chu_deu_trong_nhan"] = co_chu_deu
    ket["NHAN_CO_NOI_SAI"] = bool(
        any(v != deu_nhat for v in co_chu_deu)
        and ket["dem_4c"][deu_nhat]["SO_LAN_GOI_4C"] == 0)

    print(f"\n    ĐỀU NHẤT theo SỐ: mục "
          f"{list(TG.KHOP_CACH).index(deu_nhat)+1} ({deu_nhat!r})")
    print(f"    Ô có chữ 'đều' trong nhãn: "
          f"{[list(TG.KHOP_CACH).index(v)+1 for v in co_chu_deu]}")
    print(f"    => NHÃN CÓ NÓI SAI KHÔNG: "
          f"{'CÓ' if ket['NHAN_CO_NOI_SAI'] else 'KHÔNG'}")

    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
