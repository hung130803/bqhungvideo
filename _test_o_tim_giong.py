# -*- coding: utf-8 -*-
"""CỔNG 84 — Ô DANH SÁCH GIỌNG ĐỌC ĐƯỢC: RỘNG VỪA CHỮ · NHÓM TÁCH ĐƯỢC ·
NHÃN NGẮN · CÓ Ô TÌM.

Anh Hùng 19/08/2026 (ảnh hộp Thay giọng v2.39.0): *"nhiều giọng hơn mà không có
phân chia gì à, LOẠN QUÁ"*. Nhóm ĐÃ CHẠY ĐÚNG (`giong_bang.gom_nhom`, cổng 79
xanh 84/0) — chỗ hỏng là BÀY: ô danh sách hẹp bằng chính combo nên nhãn bị cắt
GIỮA CÂU, và `QComboBox` elide kiểu **ElideMiddle** nên nó ăn đúng khúc mang
thông tin:

    KHUYÊN DÙNG cho Tiế...phí, chạy được ngay
    Nam Minh — Nam chuẩ...giọng ở nhóm dưới]

Cổng này canh 4 việc, mỗi việc một CA:

 1. **RỘNG VỪA CHỮ** — 0 nhãn bị cắt, ở CẢ HAI đường bày (popup combo + hộp
    tìm) và ở CẢ HAI bề rộng (máy chạy cổng + trần của máy anh Hùng).
 2. **TIÊU ĐỀ NHÓM KHÁC HẲN DÒNG GIỌNG** — chứng minh bằng SOI ĐIỂM ẢNH, và
    kiểm nó THẬT SỰ không chọn được (cờ `NoItemFlags`), không chỉ đổi màu.
 3. **NHÃN NGẮN, CHI TIẾT VÀO TOOLTIP** — nhưng KHÔNG BỎ GIỌNG NÀO và không
    mất thông tin phải-thấy-ngay (tên · nhấn nhá · tiếng gì · tiền · phải tải).
 4. **Ô TÌM** — tìm trên MỌI nhóm, gõ không dấu vẫn ra, nhãn ghi rõ nhóm; combo
    VẪN mở được bằng cách bấm; cửa sổ KHÔNG tự đóng khi mất focus.

BỐN BẪY CỦA CHÍNH CỔNG NÀY, đã tránh (mỗi cái đã cắn repo ít nhất một lần):

 · **offscreen Qt có 0 họ phông -> ảnh ra Ô VUÔNG TOFU.** Trỏ `QT_QPA_FONTDIR`
   vào `C:\\Windows\\Fonts` (đo 212 họ) và ĐỎ nếu 0 họ. Đếm điểm ảnh KHÔNG phát
   hiện được tofu (tofu 2.431 px vs chữ thật 517 px = ngược 4,7 lần) nên cổng
   còn LƯU ẢNH để người tự mở ra nhìn.
 · **PHẢI ÁP QSS THẬT** `setStyleSheet(theme.QSS)`. QSS chung đổi padding item
   (dòng dùng `setItemWidget` từng bị bóp còn ~0 => dòng TRỐNG TRƠN trên máy
   user mà test không QSS vẫn PASS — lỗi thật v2.6.22). Ở đây QSS còn quan
   trọng hơn: nó có `* {color: TEXT}` và **đè lên** `setForeground` của item.
 · **KIỂU CỬA SỔ phải so `flags & WindowType_Mask`**, đừng so bit —
   `Qt.Tool = Popup | Dialog` nên bit `Popup` LUÔN có, so bit là PASS OAN.
 · **NÚT PHẢI LÀ CHỮ** — máy anh Hùng thiếu glyph nên emoji ra Ô ĐEN.

    .venv\\Scripts\\python -u _test_o_tim_giong.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)   # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

T = Path(tempfile.mkdtemp(prefix="otimgiong_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")  # KHÔNG chạm registry
os.environ["BQ_FFMPEG_SLOTS"] = "1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát

from PyQt6.QtCore import QEvent, QPointF, QSize, Qt  # noqa: E402
from PyQt6.QtGui import (  # noqa: E402
    QFontDatabase, QImage, QMouseEvent, QPainter,
)
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication, QLineEdit, QMessageBox, QPushButton,
)

for _n in ("warning", "information", "critical"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))
QMessageBox.exec = lambda self: 0                          # type: ignore
QMessageBox.question = staticmethod(                       # type: ignore
    lambda *a, **k: QMessageBox.StandardButton.No)

_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
_app.setStyleSheet(theme.QSS)              # QSS THẬT (bài học cổng 9 / v2.6.23)

import app.ui.thay_giong_dialog as TGD  # noqa: E402
from app.core import giong_bang as GB  # noqa: E402
from app.core.dubbing import list_recap_voices  # noqa: E402

OK: list[str] = []
FAIL: list[str] = []


def dat(dieu: str, ok: bool, chi_tiet: str = "") -> None:
    (OK if ok else FAIL).append(f"{dieu} {chi_tiet}".strip())
    print(f"  [{'ĐẠT' if ok else 'HỎNG'}] {dieu}"
          + (f" — {chi_tiet}" if chi_tiet else ""))


#: Lề mà `QCommonStyle` chừa hai bên chữ trong một dòng danh sách.
LE_CHU = 6
#: Chỗ cho chữ trên MÁY ANH HÙNG: cửa sổ hộp 946 px trừ `LE_TRAN` của app.
RONG_A_HUNG = 946 - TGD.LE_TRAN

print("=" * 78)
print("CỔNG 84 — Ô DANH SÁCH GIỌNG: RỘNG VỪA CHỮ · NHÓM TÁCH ĐƯỢC · Ô TÌM")
print("=" * 78)

# ---------------------------------------------------------------------------
# CA 0 — MÔI TRƯỜNG ĐO PHẢI DÙNG ĐƯỢC (thiếu phông thì mọi số dưới là số rác)
# ---------------------------------------------------------------------------
print("\n[CA 0] môi trường đo")
ho = len(QFontDatabase.families())
dat("có họ phông thật (0 họ = ảnh ra ô vuông tofu, số đo vô nghĩa)",
    ho > 20, f"{ho} họ")

TGD._CACHE_GIONG[:] = list_recap_voices()
dat("danh sách giọng thật nạp được", len(TGD._CACHE_GIONG) > 100,
    f"{len(TGD._CACHE_GIONG)} dòng")

dlg = TGD.ThayGiongDialog(None, None)
dlg.show()
_app.processEvents()
cb = dlg.cb_giong
print(f"       hộp {dlg.width()}x{dlg.height()} · combo giọng {cb.width()} px "
      f"· màn hình ảo {_app.primaryScreen().availableGeometry().width()} px")


def nhan_combo() -> list[str]:
    return [cb.itemText(i) for i in range(cb.count())]


def la_nhom(i: int) -> bool:
    it = cb.model().item(i)
    return bool(it is not None and it.data(TGD.VAI_NHOM))


# ---------------------------------------------------------------------------
# CA 1 — RỘNG VỪA CHỮ: 0 NHÃN BỊ CẮT
# ---------------------------------------------------------------------------
print("\n[CA 1] bề rộng ô danh sách vừa chữ")
cb.showPopup()
_app.processEvents()
vw = cb.view()
fm = vw.fontMetrics()

# TỰ KIỂM BỘ DÒ — thiếu mục này thì "0 nhãn bị cắt" có thể là bộ dò chết
dat("TỰ KIỂM BỘ DÒ: nhãn ngắn KHÔNG bị coi là cắt",
    fm.horizontalAdvance("Nam Minh") <= 200)
dat("TỰ KIỂM BỘ DÒ: nhãn 600 ký tự PHẢI bị coi là cắt",
    fm.horizontalAdvance("x" * 600) > RONG_A_HUNG,
    f"{fm.horizontalAdvance('x' * 600)} px > {RONG_A_HUNG} px")

dat("app TỰ ĐẶT bề rộng popup (không để nó bám theo combo 300 px)",
    vw.minimumWidth() > cb.width(),
    f"minimumWidth {vw.minimumWidth()} px > combo {cb.width()} px")


def dem_cat(ds: list[str], rong: int) -> list[str]:
    return [n for n in ds if fm.horizontalAdvance(n) > rong]


for ten, rong in (("máy chạy cổng",
                   max(vw.minimumWidth(), cb.width()) - LE_CHU),
                  ("máy anh Hùng", RONG_A_HUNG - LE_CHU)):
    c = dem_cat(nhan_combo(), rong)
    dat(f"popup combo · {ten} ({rong} px): 0 nhãn bị cắt",
        not c, f"bị cắt {len(c)}/{cb.count()}"
        + (f" · tệ nhất: {c[0][:60]}" if c else ""))

pop = dlg._mo_chon_giong()
_app.processEvents()
lst = dlg._gp_lst
nhan_lst = [lst.item(i).text() for i in range(lst.count())]
fm2 = lst.fontMetrics()
rong_lst = lst.viewport().width() - LE_CHU
c = [n for n in nhan_lst if fm2.horizontalAdvance(n) > rong_lst]
dat(f"hộp TÌM GIỌNG · {rong_lst} px: 0 nhãn bị cắt",
    not c, f"bị cắt {len(c)}/{len(nhan_lst)} · hộp {pop.width()}x{pop.height()}"
    + (f" · tệ nhất: {c[0][:60]}" if c else ""))
dat("còn CHỖ DƯ, không sát mép (phông máy khác nhích 1 px là cắt lại)",
    rong_lst - max(fm2.horizontalAdvance(n) for n in nhan_lst) >= 6,
    f"dư {rong_lst - max(fm2.horizontalAdvance(n) for n in nhan_lst)} px")
dat("bề rộng CHẶN TRẦN theo cửa sổ/màn hình (không tràn ra ngoài)",
    pop.width() <= min(dlg.window().width(),
                       _app.primaryScreen().availableGeometry().width()),
    f"hộp {pop.width()} px <= trần "
    f"{min(dlg.window().width(), _app.primaryScreen().availableGeometry().width())} px")

# ---------------------------------------------------------------------------
# CA 2 — TIÊU ĐỀ NHÓM KHÁC HẲN DÒNG GIỌNG (SOI ĐIỂM ẢNH + CỜ)
# ---------------------------------------------------------------------------
print("\n[CA 2] tiêu đề nhóm tách được khỏi dòng giọng")


def anh_cua(view) -> QImage:
    kh = view.viewport()
    img = QImage(QSize(kh.width(), kh.height()), QImage.Format.Format_ARGB32)
    img.fill(0xFF101827)
    p = QPainter(img)
    kh.render(p)
    p.end()
    return img


def do_dong(view, img: QImage, i: int) -> dict:
    """Màu nền / màu chữ của MỘT dòng, đọc từ điểm ảnh ĐÃ VẼ."""
    r = view.visualRect(view.model().index(i, 0))
    if r.height() <= 0 or r.top() < 0 or r.bottom() >= img.height():
        return {}
    dem: Counter = Counter()
    for y in range(r.top() + 1, r.bottom()):
        for x in range(max(0, r.left()), min(img.width(), r.right())):
            dem[img.pixel(x, y) & 0xFFFFFF] += 1
    if not dem:
        return {}
    nen = dem.most_common(1)[0][0]
    chu = next((c for c, _n in dem.most_common() if c != nen), nen)
    tong = sum(dem.values())
    return {"nen": nen, "chu": chu, "so_mau": len(dem),
            "ty_chu": sum(n for c, n in dem.items() if c != nen) / tong}


img_lst = anh_cua(lst)
i_nhom = [i for i in range(lst.count())
          if lst.item(i).data(TGD.VAI_NHOM) and do_dong(lst, img_lst, i)]
i_giong = [i for i in range(lst.count())
           if not lst.item(i).data(TGD.VAI_NHOM) and do_dong(lst, img_lst, i)]
dat("hộp tìm có tiêu đề nhóm", len(i_nhom) >= 2, f"{len(i_nhom)} nhóm hiện ra")

nh = do_dong(lst, img_lst, i_nhom[0])
gs = [i for i in i_giong if i > i_nhom[0]][:2]
g1, g2 = do_dong(lst, img_lst, gs[0]), do_dong(lst, img_lst, gs[1])
print(f"       TIÊU ĐỀ  nền #{nh['nen']:06X} chữ #{nh['chu']:06X} "
      f"chữ {nh['ty_chu'] * 100:.2f}%   {lst.item(i_nhom[0]).text()[:46]}")
print(f"       giọng    nền #{g1['nen']:06X} chữ #{g1['chu']:06X} "
      f"chữ {g1['ty_chu'] * 100:.2f}%   {lst.item(gs[0]).text()[:46]}")

# TỰ KIỂM BỘ DÒ trước, rồi mới chấm — bộ dò kêu "khác" với mọi cặp thì vô dụng
dat("TỰ KIỂM BỘ DÒ: hai dòng GIỌNG phải ra GIỐNG nhau",
    g1["nen"] == g2["nen"] and g1["chu"] == g2["chu"],
    f"#{g1['nen']:06X}/#{g1['chu']:06X} vs #{g2['nen']:06X}/#{g2['chu']:06X}")
dat("SOI ĐIỂM ẢNH: MÀU CHỮ tiêu đề khác dòng giọng",
    nh["chu"] != g1["chu"], f"#{nh['chu']:06X} vs #{g1['chu']:06X}")
dat("SOI ĐIỂM ẢNH: MÀU NỀN tiêu đề khác dòng giọng",
    nh["nen"] != g1["nen"], f"#{nh['nen']:06X} vs #{g1['nen']:06X}")
dat("dòng tiêu đề CÓ CHỮ THẬT (không phải dải trống trơn)",
    nh["ty_chu"] > 0.02 and nh["so_mau"] >= 3,
    f"{nh['ty_chu'] * 100:.2f}% điểm ảnh chữ · {nh['so_mau']} màu")

for ten, it in (("hộp tìm", lst.item(i_nhom[0])),
                ("popup combo", cb.model().item(
                    next(i for i in range(cb.count()) if la_nhom(i))))):
    f = it.flags()
    dat(f"{ten}: tiêu đề nhóm THẬT SỰ không chọn được (NoItemFlags)",
        not (f & Qt.ItemFlag.ItemIsSelectable)
        and not (f & Qt.ItemFlag.ItemIsEnabled), f"cờ {int(f.value):#x}")

# dòng ĐẦU (`Tự chọn theo ngôn ngữ đích`) là LỰA CHỌN THẬT, KHÔNG được khoá
dat("dòng 'Tự chọn theo ngôn ngữ đích' vẫn CHỌN ĐƯỢC (mã rỗng nhưng là lựa "
    "chọn thật)",
    bool(cb.model().item(0).flags() & Qt.ItemFlag.ItemIsSelectable)
    and not la_nhom(0))

# ---------------------------------------------------------------------------
# CA 3 — NHÃN NGẮN, CHI TIẾT VÀO TOOLTIP, KHÔNG BỎ GIỌNG NÀO
# ---------------------------------------------------------------------------
print("\n[CA 3] nhãn ngắn nhưng không mất giọng, không mất thông tin")
nn = str(dlg.cb_nn.currentData() or "en")
goc = GB.gom_nhom(TGD.giong_dung_duoc(TGD._CACHE_GIONG), nn, loi_tat=True)
ma_goc = [v for _n, v in goc if v]
ma_cb = [str(cb.itemData(i) or "") for i in range(cb.count())
         if cb.itemData(i) and not la_nhom(i)]
dat("KHÔNG BỎ GIỌNG NÀO: số mã trong combo == số mã `gom_nhom` trả ra",
    ma_cb == ma_goc, f"{len(ma_cb)} vs {len(ma_goc)}")
ma_lst = [str(lst.item(i).data(Qt.ItemDataRole.UserRole)) for i in
          range(lst.count()) if not lst.item(i).data(TGD.VAI_NHOM)]
dat("hộp tìm bày ĐỦ mọi dòng của combo (kể cả dòng trùng mã của lối tắt)",
    len(ma_lst) == cb.count() - len([1 for i in range(cb.count())
                                     if la_nhom(i)]),
    f"{len(ma_lst)} dòng chọn được")

n_goc = {v: n for n, v in goc if v}
tr = TGD.tran_nhan(cb)
# NHÃN GỐC PHẢI GIỮ DẠNG **DANH SÁCH**, KHÔNG ĐƯỢC GOM VÀO DICT THEO MÃ GIỌNG.
# Bản đầu của mục dưới dùng `n_goc` (dict `{mã: nhãn}`) và **ĐỎ OAN**: nhóm lối
# tắt ở ĐẦU dùng ĐÚNG mã giọng của dòng ở nhóm dưới, nên dict bị ghi đè và
# 5 nhãn mang `DAU_LOI_TAT` biến mất sạch (đo: 364 dòng -> 359 khoá dict).
# Cổng đọc ra "app KHÔNG rút gọn đuôi lối tắt" trong khi combo THẬT có đúng
# 5 dòng `· lối tắt`. Quy tắc: nguồn nào CÓ TRÙNG KHOÁ thì đừng gom bằng dict.
ds_goc = [n for n, v in goc if v]
gon_ds = [TGD.nhan_gon(n, fm, tr) for n in ds_goc]
dat("nhãn dài nhất đã rút ngắn hẳn",
    max(len(x) for x in gon_ds) < 200,
    f"gốc {max(len(x) for x in ds_goc)} ký tự -> "
    f"{max(len(x) for x in gon_ds)} ký tự")
lt_goc = sum(1 for x in ds_goc if GB.DAU_LOI_TAT in x)
lt_gon = sum(1 for x in gon_ds if TGD.DAU_LOI_TAT_GON in x)
lt_cb = sum(1 for i in range(cb.count())
            if TGD.DAU_LOI_TAT_GON in cb.itemText(i))
dat("đuôi lối tắt 38 ký tự đã rút gọn (đo trên DANH SÁCH, không gom dict)",
    lt_goc > 0 and lt_gon == lt_goc
    and all(GB.DAU_LOI_TAT not in x for x in gon_ds)
    and lt_cb == lt_goc,
    f"gốc {lt_goc} dòng lối tắt -> rút gọn {lt_gon} · trên combo {lt_cb} · "
    f"còn đuôi dài {sum(1 for x in gon_ds if GB.DAU_LOI_TAT in x)}")
dat("ghi chú lối tắt nói MỘT LẦN ở tiêu đề nhóm",
    sum(1 for i in range(cb.count())
        if TGD.GHI_CHU_LOI_TAT in cb.itemText(i)) == 1)

thieu = []
for i in range(cb.count()):
    vid = str(cb.itemData(i) or "")
    if not vid or la_nhom(i):
        continue
    t = cb.itemText(i)
    g = n_goc.get(vid, "")
    # TIỀN / PHẢI TẢI phải còn TRÊN DÒNG — cắt mất nó là bấm nhầm mất tiền thật
    if any(k in g for k in ("miễn phí", "TỐN TIỀN", "cần key", "tốn hạn mức")) \
            and not any(k in t for k in ("miễn phí", "TỐN TIỀN", "cần key",
                                         "tốn hạn mức")):
        thieu.append(("tiền", t))
    if "cần tải" in g and "cần tải" not in t:
        thieu.append(("phải tải", t))
    if "nhấn nhá" in g and "nhấn nhá" not in t:
        thieu.append(("nhấn nhá", t))
dat("thông tin PHẢI THẤY NGAY còn trên dòng (tiền · phải tải · nhấn nhá)",
    not thieu, f"{len(thieu)} dòng thiếu"
    + (f" · vd {thieu[0]}" if thieu else ""))

# NHÃN GỐC THEO **CHỈ SỐ**, không tra theo mã giọng: dòng lối tắt dùng chung mã
# với dòng ở nhóm dưới nên tra theo mã là so dòng này với nhãn gốc của dòng KIA
# (mục dưới sẽ chấm sai đối tượng mà vẫn xanh). Combo dựng đúng thứ tự
# `[NHAN_GIONG_TU] + ds`, nên chỉ số i ứng với `goc[i-1]`.
dat("nhãn gốc gióng được theo CHỈ SỐ với combo (điều kiện của mục dưới)",
    cb.count() - 1 >= len(goc), f"combo {cb.count()} · gom_nhom {len(goc)}")
goc_theo_i = {i + 1: goc[i][0] for i in range(len(goc))
              if i + 1 < cb.count() and goc[i][1]}
bi_rut = [i for i in goc_theo_i
          if cb.itemData(i) and not la_nhom(i)
          and cb.itemText(i) != goc_theo_i[i]]
mat_chu = [i for i in bi_rut
           if goc_theo_i[i] not in (cb.model().item(i).toolTip() or "")]
dat("mọi dòng bị rút gọn đều có NGUYÊN VĂN nhãn gốc trong tooltip",
    not mat_chu, f"{len(bi_rut)} dòng rút gọn · {len(mat_chu)} dòng mất chữ")

# ---------------------------------------------------------------------------
# CA 4 — Ô TÌM GIỌNG
# ---------------------------------------------------------------------------
print("\n[CA 4] ô tìm giọng")
dat("combo VẪN mở được bằng cách bấm (không biến thành ô-gõ)",
    isinstance(cb, TGD.ComboGiong) and not cb.isEditable()
    and callable(cb.picker))
dat("hộp tìm gồm [ô tìm] + [danh sách] đúng mẫu `_open_chan_picker`",
    isinstance(dlg._gp_ed, QLineEdit) and lst.count() > 100,
    f"{lst.count()} dòng")


def tim(q: str) -> list[str]:
    dlg._gp_ed.setText(q)
    _app.processEvents()
    return [dlg._gp_lst.item(i).text() for i in range(dlg._gp_lst.count())]


def bo_dau_ho(s: str) -> str:
    t = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# GÕ TÊN GIỌNG Ở NHÓM KHÁC — bẫy đã sập 2 lần với ô tìm kênh (v2.6.12: ô lọc
# chỉ lọc TRONG nhóm đang chọn nên gõ tên ở nhóm khác không ra).
# Lấy giọng nằm ở nhóm CUỐI CÙNG (xa nhóm đầu nhất) rồi gõ tên nó.
phang = dlg._giong_phang()
nhom_ds = [g for _i, _n, v, g in phang if not v]
cuoi = [(i, n, v, g) for i, n, v, g in phang if v and g == nhom_ds[-1]]
if cuoi:
    _i, n_c, v_c, g_c = cuoi[0]
    ten_c = n_c.split(" (")[0].split(" —")[0].split(" -")[0].strip()
    ra = tim(ten_c)
    dat(f"gõ tên giọng ở NHÓM CUỐI ('{ten_c[:24]}') vẫn ra",
        any(ten_c in r for r in ra), f"{len(ra)} dòng khớp · nhóm «{g_c[:34]}»")
    dat("dòng khớp GHI RÕ nó thuộc nhóm nào",
        any("ở nhóm:" in r for r in ra),
        next((r[:88] for r in ra if "ở nhóm:" in r), "(không có)"))
else:
    dat("có giọng ở nhóm cuối để thử", False)

# tìm TRÊN MỌI NHÓM: một truy vấn phải nhặt được giọng từ >= 2 nhóm khác nhau
ra = tim("nhấn nhá")
nhom_ra = {r.split("ở nhóm:")[-1].strip() for r in ra if "ở nhóm:" in r}
dat("một lượt tìm nhặt được giọng từ NHIỀU NHÓM khác nhau",
    len(nhom_ra) >= 3, f"{len(nhom_ra)} nhóm · {len(ra)} dòng")

# GÕ KHÔNG DẤU
co_dau = next((n for _i, n, v, _g in phang
               if v and bo_dau_ho(n) != n.lower()), "")
if co_dau:
    t = co_dau.split(" (")[0].split(" —")[0].split(" -")[0].strip()
    ra = tim(bo_dau_ho(t))
    dat(f"gõ KHÔNG DẤU ('{bo_dau_ho(t)[:24]}') vẫn ra giọng có dấu",
        any(t in r for r in ra), f"{len(ra)} dòng")
else:
    dat("có giọng tên tiếng Việt để thử gõ không dấu", False)

ra = tim("zzzzkhongcogiongnao")
dat("gõ chuỗi vô nghĩa -> nói rõ không có gì khớp (không im lặng)",
    len(ra) == 1 and "không có giọng nào khớp" in ra[0], str(ra[:1]))

# CHỌN GIỌNG Ở NHÓM KHÁC -> combo đổi ĐÚNG mã đó
tim("")
muc_tieu = [(i, n, v) for i, n, v, _g in phang if v][-1]
tim(muc_tieu[1].split(" (")[0].split(" —")[0].split(" -")[0].strip())
dong = next((i for i in range(lst.count())
             if lst.item(i).data(Qt.ItemDataRole.UserRole) == muc_tieu[0]), -1)
if dong >= 0:
    lst.itemClicked.emit(lst.item(dong))
    _app.processEvents()
    dat("bấm một dòng -> combo nhận ĐÚNG mã giọng đó",
        str(cb.currentData()) == muc_tieu[2],
        f"chọn «{muc_tieu[2]}» ra «{cb.currentData()}»")
    dat("chọn giọng xong thì hộp ĐÓNG", not pop.isVisible())
else:
    dat("tìm được dòng để bấm", False)

# ---------------------------------------------------------------------------
# CA 5 — KIỂU CỬA SỔ + CÁC ĐƯỜNG ĐÓNG
# ---------------------------------------------------------------------------
print("\n[CA 5] kiểu cửa sổ + đường đóng")
pop = dlg._mo_chon_giong()
_app.processEvents()
mask = pop.windowFlags() & Qt.WindowType.WindowType_Mask
dat("KIỂU cửa sổ là Tool, KHÔNG phải Popup "
    "(so `flags & WindowType_Mask`, không so bit)",
    mask == Qt.WindowType.Tool, f"kiểu {int(mask.value):#x} "
    f"(Tool={int(Qt.WindowType.Tool.value):#x} · "
    f"Popup={int(Qt.WindowType.Popup.value):#x})")
dat("có FramelessWindowHint",
    bool(pop.windowFlags() & Qt.WindowType.FramelessWindowHint))
# CHỐT CHỐNG PASS OAN: `Qt.Tool = Popup | Dialog` nên bit Popup LUÔN có. Nếu
# phép so BIT cũng ra True thì mục trên đâu có chứng minh được gì -> in ra để
# người đọc thấy đúng cái bẫy.
dat("TỰ KIỂM: phép so BIT (sai cách) KHÔNG phân biệt được -> đúng là bẫy",
    bool(pop.windowFlags() & Qt.WindowType.Popup),
    "bit Popup vẫn bật dù kiểu là Tool")

pop.close()
_app.processEvents()
dat("nút Đóng / Esc đóng được (nút là CHỮ nên bấm được)", not pop.isVisible())

pop = dlg._mo_chon_giong()
_app.processEvents()
# PyQt6 CHỈ nhận `QPointF` ở đây — truyền `QPoint` thì `TypeError: arguments
# did not match any overloaded call` và **cổng CHẾT GIỮA CHỪNG**, mất luôn CA
# 5 (bấm ra ngoài) tới CA 8. Đúng bẫy "cổng ĐẠT OAN vì lượt chạy chết trước khi
# tới chốt": mã thoát 1 nhưng dòng tổng kết không in ra nên đọc lướt thì tưởng
# chỉ hỏng 1 mục.
ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(3, 3),
                 Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier)
_app.sendEvent(dlg.ed_thu_muc, ev)
_app.processEvents()
dat("BẤM RA NGOÀI (vào ô Thư mục nguồn) -> hộp đóng", not pop.isVisible())

pop = dlg._mo_chon_giong()
_app.processEvents()
dang_mo = pop.isVisible()
pop2 = dlg._mo_chon_giong()          # bấm lại combo khi đang mở -> ĐÓNG
_app.processEvents()
dat("bấm lại vào combo khi đang mở -> ĐÓNG (bật/tắt như dropdown thường)",
    dang_mo and not pop2.isVisible())
dat("mở/đóng nhiều lần DÙNG LẠI một hộp (không đẻ widget rác)",
    pop2 is pop)

# ---------------------------------------------------------------------------
# CA 6 — NÚT PHẢI LÀ CHỮ, KHÔNG EMOJI
# ---------------------------------------------------------------------------
print("\n[CA 6] nhãn nút không emoji")
pop = dlg._mo_chon_giong()
_app.processEvents()


def co_emoji(s: str) -> list[str]:
    return [c for c in s or ""
            if ord(c) > 0xFFFF or unicodedata.category(c) == "So"]


xau = []
nut = pop.findChildren(QPushButton)
for b in nut:
    e = co_emoji(b.text())
    if e:
        xau.append((b.text(), [hex(ord(c)) for c in e]))
dat("mọi nút trong hộp tìm là CHỮ (không glyph dễ thiếu font)",
    not xau, f"{len(nut)} nút" + (f" · xấu: {xau}" if xau else ""))
xau2 = [t for t in ([dlg._gp_ed.placeholderText()]
                    + [lst.item(i).text() for i in range(min(30, lst.count()))])
        if co_emoji(t)]
dat("chữ trong ô tìm + nhãn dòng cũng không emoji",
    not xau2, f"{len(xau2)} chỗ xấu")

# ---------------------------------------------------------------------------
# CA 7 — ROUND-TRIP: LƯU RỒI ĐỌC LẠI PHẢI GIỮ ĐÚNG GIỌNG
# ---------------------------------------------------------------------------
print("\n[CA 7] round-trip lưu/đọc lại")
pop.close()
muon = next(str(cb.itemData(i)) for i in range(cb.count() - 1, 0, -1)
            if cb.itemData(i) and not la_nhom(i))
cb.setCurrentIndex(cb.findData(muon))
dlg.luu_cai_dat()
dlg.close()
dlg2 = TGD.ThayGiongDialog(None, None)
dlg2.show()
_app.processEvents()
dat("mở lại hộp -> combo giữ ĐÚNG mã giọng đã lưu",
    str(dlg2.cb_giong.currentData()) == muon,
    f"lưu «{muon}» đọc lại «{dlg2.cb_giong.currentData()}»")
dat("đổi ngôn ngữ rồi mở lại ô tìm -> vẫn không có nhãn nào bị cắt",
    True, "")
i_vi = dlg2.cb_nn.findData("vi")
dlg2.cb_nn.setCurrentIndex(i_vi)
_app.processEvents()
p2 = dlg2._mo_chon_giong()
_app.processEvents()
l2 = dlg2._gp_lst
f2 = l2.fontMetrics()
r2 = l2.viewport().width() - LE_CHU
c2 = [l2.item(i).text() for i in range(l2.count())
      if f2.horizontalAdvance(l2.item(i).text()) > r2]
dat("đổi sang Tiếng Việt (có VieNeu 250 MB + OmniVoice 610 ký tự): 0 nhãn cắt",
    not c2, f"bị cắt {len(c2)}/{l2.count()} · chỗ cho chữ {r2} px"
    + (f" · tệ nhất {c2[0][:60]}" if c2 else ""))
dat("giọng đã lưu KHÔNG bị mất khi đổi ngôn ngữ",
    dlg2.cb_giong.findData(muon) >= 0)

# ẢNH ĐỂ NGƯỜI TỰ NHÌN (đếm điểm ảnh KHÔNG phát hiện được tofu)
img = QImage(QSize(p2.width(), p2.height()), QImage.Format.Format_ARGB32)
img.fill(0xFF101827)
pt = QPainter(img)
p2.render(pt)
pt.end()
img.save(str(Path(REPO) / "_ANH_O_TIM_GIONG.png"))
print(f"       ảnh cả hộp: _ANH_O_TIM_GIONG.png ({img.width()}x{img.height()})")

# ---------------------------------------------------------------------------
# CA 8 — THỬ PHÁ: GỠ CHỐT PHẢI ĐỎ
# ---------------------------------------------------------------------------
print("\n[CA 8] thử phá — gỡ chốt thì mục tương ứng PHẢI vỡ")
p2.close()
BAT, LOT = [], []


def pha(ten: str, vo: bool) -> None:
    (BAT if vo else LOT).append(ten)
    print(f"  [{'BẮT' if vo else 'LỌT'}] {ten}")


# (a) gỡ VIỆC 3 (nhãn gọn) -> nhãn 610 ký tự quay lại -> phải có nhãn bị cắt
_goc_gon = TGD.nhan_gon
TGD.nhan_gon = lambda nhan, fm_, tran: str(nhan or "")
dlg3 = TGD.ThayGiongDialog(None, None)
dlg3.show()
dlg3.cb_nn.setCurrentIndex(dlg3.cb_nn.findData("vi"))
_app.processEvents()
p3 = dlg3._mo_chon_giong()
_app.processEvents()
l3, f3 = dlg3._gp_lst, dlg3._gp_lst.fontMetrics()
r3 = l3.viewport().width() - LE_CHU
c3 = [1 for i in range(l3.count())
      if f3.horizontalAdvance(l3.item(i).text()) > r3]
pha(f"gỡ `nhan_gon` -> nhãn bị cắt {len(c3)}/{l3.count()} (chốt CA 1/CA 3)",
    len(c3) > 0)
p3.close()
dlg3.close()
TGD.nhan_gon = _goc_gon

# (b) gỡ VIỆC 2 (NoItemFlags) -> tiêu đề nhóm chọn được lại
_goc_nhom = TGD.to_nhan_nhom
TGD.to_nhan_nhom = lambda it: it.setEnabled(False)
dlg4 = TGD.ThayGiongDialog(None, None)
dlg4.show()
_app.processEvents()
i4 = next((i for i in range(dlg4.cb_giong.count())
           if not dlg4.cb_giong.itemData(i) and i > 0), -1)
f4 = dlg4.cb_giong.model().item(i4).flags()
pha("gỡ `NoItemFlags` (chỉ setEnabled(False)) -> tiêu đề nhóm VẪN CHỌN ĐƯỢC "
    f"(cờ {int(f4.value):#x})", bool(f4 & Qt.ItemFlag.ItemIsSelectable))
dlg4.close()
TGD.to_nhan_nhom = _goc_nhom

# (c) gỡ VIỆC 1 (nới bề rộng) -> popup bám theo combo 300 px
_goc_rong = TGD.rong_vua_chu
TGD.rong_vua_chu = lambda fm_, ds, tran: 0
dlg5 = TGD.ThayGiongDialog(None, None)
dlg5.show()
_app.processEvents()
p5 = dlg5._mo_chon_giong()
_app.processEvents()
pha(f"gỡ `rong_vua_chu` -> hộp tìm co về {p5.width()} px (bằng combo)",
    p5.width() <= dlg5.cb_giong.width() + 4)
p5.close()
dlg5.close()
TGD.rong_vua_chu = _goc_rong

# (d) gỡ VIỆC 4 (tìm trên MỌI nhóm) -> chỉ còn nhóm đầu, gõ tên nhóm khác không ra
_goc_phang = TGD.ThayGiongDialog._giong_phang
TGD.ThayGiongDialog._giong_phang = lambda self: [
    x for x in _goc_phang(self) if x[3] == ""]
dlg6 = TGD.ThayGiongDialog(None, None)
dlg6.show()
_app.processEvents()
p6 = dlg6._mo_chon_giong()
_app.processEvents()
if cuoi:
    dlg6._gp_ed.setText(ten_c)
    _app.processEvents()
    ra6 = [dlg6._gp_lst.item(i).text() for i in range(dlg6._gp_lst.count())]
    pha(f"gỡ nguồn tìm TOÀN DANH SÁCH -> gõ '{ten_c[:20]}' KHÔNG ra "
        f"({len(ra6)} dòng)", not any(ten_c in r for r in ra6))
p6.close()
dlg6.close()
TGD.ThayGiongDialog._giong_phang = _goc_phang

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print(f"THỬ PHÁ: BẮT {len(BAT)} · LỌT {len(LOT)}")
for x in LOT:
    print(f"  LỌT: {x}")
if LOT:
    FAIL.append(f"thử phá LỌT {len(LOT)} phép — cổng chỉ là con dấu")
print(f"ĐẠT {len(OK)} · HỎNG {len(FAIL)}")
for x in FAIL:
    print(f"  HỎNG: {x}")
print("=" * 78)

# ── THOÁT BẰNG `os._exit` — KHÔNG PHẢI `sys.exit` ──────────────────────────
# **ĐO ĐƯỢC (19/08/2026): `sys.exit` ở đây ra mã thoát 139 = SEGFAULT**, xảy ra
# SAU khi in xong dòng "ĐẠT 48 · HỎNG 0". Cổng in ra toàn xanh mà bộ chạy hồi
# quy đọc mã thoát THẬT thì thấy đỏ — hoặc ngược lại, ai chỉ đọc chữ thì tưởng
# xanh. Gốc: cổng dựng 6 `ThayGiongDialog` (CA 8 dựng 4 cái để thử phá) parent
# `None` + hộp chọn giọng là cửa sổ `Tool` con; lúc trình thông dịch dọn dẹp,
# Qt phá widget theo thứ tự không xác định và nổ trong C++. Đây đúng cách
# `main.py` đã chốt cho app thật ("không finalize interpreter khi luồng daemon
# còn chạy").
# PHẢI `flush` TRƯỚC: `os._exit` không xả bộ đệm, mà lượt hồi quy ghi stdout ra
# FILE (có đệm) nên thiếu flush là mất sạch báo cáo.
_ma_ra = 1 if FAIL else 0
try:
    for _w in list(_app.topLevelWidgets()):
        _w.close()
    _app.processEvents()
except Exception:                       # noqa: BLE001 - dọn được thì tốt
    pass
import shutil as _sh                     # noqa: E402 - chỉ dùng lúc thoát
_sh.rmtree(T, ignore_errors=True)        # KHÔNG để rác %TEMP% trên máy user
sys.stdout.flush()
sys.stderr.flush()
os._exit(_ma_ra)
