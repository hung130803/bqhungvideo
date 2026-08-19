# -*- coding: utf-8 -*-
"""ROUND-TRIP HỘP CHỌN GIỌNG — chọn X, lưu, mở lại phải VẪN LÀ X.

Đây là mệnh đề "chọn X ra Y" ở tầng GIAO DIỆN. Cổng 79 CA 10 đã chứng minh
tầng ĐỌC (mã `vn:` rẽ đúng sang VieNeu); chỗ này canh tầng trên nó: cái người
dùng bấm có được ghi xuống và đọc lại đúng không.

VÌ SAO KHÔNG THỪA: `_dung_combo_giong` nay dựng lại danh sách **theo NGÔN NGỮ
ĐANG CHỌN** và nhóm "Khuyên dùng" **chép giọng thành HAI DÒNG**. Cả hai đều là
chỗ dễ làm `findData` trỏ nhầm dòng, hoặc làm giọng đã lưu biến mất khỏi danh
sách rồi bị ghi đè bằng "" (đúng lỗi thật cổng 55 đã bắt: *"mở hộp rồi Lưu
ngay là ghi đè giọng user đã chọn bằng chuỗi rỗng"*).

KHÔNG ghi vào QSettings THẬT của anh Hùng — `BQ_QSETTINGS_INI=1`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BQ_QSETTINGS_INI"] = "1"

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

import _test_guard  # noqa: F401,E402

from PyQt6.QtWidgets import QApplication  # noqa: E402

DAT = 0
HONG = 0


def ok(dieu: str, dung: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dung:
        DAT += 1
        print(f"  ĐẠT  {dieu}" + (f" -- {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {dieu}" + (f" -- {chi_tiet}" if chi_tiet else ""))


def main() -> int:
    app = QApplication(sys.argv)  # noqa: F841
    from app.ui import thay_giong_dialog as TGD
    from app.ui.thay_giong_dialog import ThayGiongDialog, K_GIONG
    from app.core import giong_bang as GB

    # NẠP SẴN danh sách giọng vào cache TRƯỚC khi dựng hộp. Không làm bước này
    # thì hộp chỉ có mấy giọng thêm ĐỒNG BỘ (VieNeu/Piper) — danh sách edge-tts
    # đi qua thread nền nên chưa kịp về, và phép thử round-trip sẽ bỏ sót đúng
    # những ca đáng ngờ nhất (biến thể cao độ, mã nằm ở HAI dòng).
    from app.core.dubbing import list_recap_voices
    TGD._CACHE_GIONG[:] = list_recap_voices()
    print(f"[đo] nạp sẵn {len(TGD._CACHE_GIONG)} dòng giọng thô vào cache")

    dlg = ThayGiongDialog(None, None)
    n = dlg.cb_giong.count()
    ma_co = [dlg.cb_giong.itemData(i) for i in range(n)]
    thuc = [m for m in ma_co if m]
    print(f"[đo] combo dựng ra {n} dòng · {len(thuc)} dòng chọn được · "
          f"{len(set(thuc))} giọng khác nhau")

    # Chọn ra các ca ĐÁNG NGỜ NHẤT, không phải giọng đầu tiên cho xong:
    #  - một giọng VieNeu (`vn:`) = mã mới toanh, nhóm "Trên máy"
    #  - một BIẾN THỂ CAO ĐỘ (`|`) = mã có ký tự lạ
    #  - một giọng nằm ở nhóm "Khuyên dùng" = mã xuất hiện HAI dòng
    #  - một giọng TRẢ TIỀN (nếu có) = nhóm cuối danh sách
    ca: list[tuple[str, str]] = []
    for nhan, loc in (
            ("giọng VieNeu", lambda m: m.startswith("vn:")),
            ("biến thể cao độ", lambda m: "|" in m),
            ("giọng ở nhóm Khuyên dùng (mã có HAI dòng)",
             lambda m: thuc.count(m) > 1),
            ("giọng edge-tts thường", lambda m: m.startswith("en-US-")),
    ):
        got = next((m for m in thuc if loc(m)), None)
        if got:
            ca.append((nhan, got))
        else:
            print(f"  BỎ QUA {nhan} — combo máy này không có mã nào như vậy")

    for nhan, ma in ca:
        i = dlg.cb_giong.findData(ma)
        dlg.cb_giong.setCurrentIndex(i)
        # ĐÚNG đường mà nút Lưu đi (`_luu`), không tự gọi setValue cho tiện
        dlg._s.setValue(K_GIONG, dlg.cb_giong.currentData() or "")

        d2 = ThayGiongDialog(None, None)          # mở lại hộp = tiến trình sau
        lai = d2.cb_giong.currentData()
        ok(f"{nhan}: chọn `{ma}` -> mở lại vẫn `{ma}`", lai == ma,
           f"đọc lại được {lai!r}")
        # và dòng đang hiện phải là dòng CHỌN ĐƯỢC, không phải nhãn nhóm
        ok(f"{nhan}: dòng đang hiện không phải nhãn nhóm",
           bool(d2.cb_giong.currentText().strip()) and bool(lai))
        d2.deleteLater()

    # ĐỔI NGÔN NGỮ RỒI QUAY LẠI: combo dựng lại theo tiếng đích, giọng đã lưu
    # KHÔNG được rơi mất (đây là chỗ `gom_nhom(nn)` mới thêm vào).
    if ca:
        _nhan, ma = ca[0]
        dlg._s.setValue(K_GIONG, ma)
        d3 = ThayGiongDialog(None, None)
        d3.cb_nn.setCurrentIndex(
            max(0, d3.cb_nn.findData("en")))       # -> `_doi_ngon_ngu`
        sau_en = d3.cb_giong.currentData()
        d3.cb_nn.setCurrentIndex(max(0, d3.cb_nn.findData("vi")))
        sau_vi = d3.cb_giong.currentData()
        ok("đổi ngôn ngữ đích rồi quay lại: giọng đã chọn KHÔNG rơi mất",
           sau_en == ma and sau_vi == ma,
           f"sau khi sang 'en': {sau_en!r} · quay lại 'vi': {sau_vi!r}")
        d3.deleteLater()

    # Mỗi mã chỉ được lặp NHIỀU NHẤT hai lần (lối tắt), và bản lối tắt phải tự
    # nói ra — nếu không thì `findData` trỏ vào một dòng mà người dùng không
    # phân biệt được với giọng khác.
    dem: dict[str, int] = {}
    for m in thuc:
        dem[m] = dem.get(m, 0) + 1
    qua = {m: k for m, k in dem.items() if k > 2}
    ok("không mã nào xuất hiện quá HAI lần trong combo", not qua, f"{qua}")
    lap = [m for m, k in dem.items() if k == 2]
    thieu = []
    for m in lap:
        nhan_ds = [dlg.cb_giong.itemText(i) for i in range(n)
                   if dlg.cb_giong.itemData(i) == m]
        if not any(GB.DAU_LOI_TAT in t for t in nhan_ds):
            thieu.append(m)
    ok("mã xuất hiện hai lần thì có ĐÚNG một dòng ghi 'lối tắt'",
       not thieu, f"{len(thieu)} mã thiếu dấu: {thieu[:2]}")

    print()
    print(f"TỔNG: ĐẠT {DAT} · HỎNG {HONG}")
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
