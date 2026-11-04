# -*- coding: utf-8 -*-
"""ĐO DỮ LIỆU THẬT của combo giọng, để thiết kế bộ lọc theo SỐ chứ không đoán."""
from __future__ import annotations
import os, sys, tempfile, re
from pathlib import Path
REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
T = Path(tempfile.mkdtemp(prefix="doloc_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _test_guard  # noqa
from PyQt6.QtWidgets import QApplication, QMessageBox
for _n in ("warning", "information", "critical"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))
QMessageBox.exec = lambda self: 0
_app = QApplication.instance() or QApplication([])
from app.ui import theme
_app.setStyleSheet(theme.QSS)
import app.ui.thay_giong_dialog as TGD
from app.core import giong_bang as GB
from app.core.dubbing import list_recap_voices

TGD._CACHE_GIONG[:] = list_recap_voices()
dlg = TGD.ThayGiongDialog(None, None)
dlg.show(); _app.processEvents()
ds = dlg._giong_phang()
giong = [(i, n, v, g) for i, n, v, g in ds if v]
print(f"TONG dong combo = {len(ds)} · dong GIONG (co ma) = {len(giong)}")
print(f"tieu de nhom = {sum(1 for i,n,v,g in ds if not v)}")

from collections import Counter
print("\n=== MA NGON NGU (giong_bang.ma_ngon_ngu) ===")
c = Counter(GB.ma_ngon_ngu(v) for _i, _n, v, _g in giong)
for k, n in c.most_common():
    print(f"  {k or '(rong=da ngu/khong biet)':28s} {n}")
print(f"\nda_ngu=True: {sum(1 for _i,_n,v,_g in giong if GB.da_ngu(v))}")
print(f"mien_phi=True: {sum(1 for _i,_n,v,_g in giong if GB.mien_phi(v))}")
print(f"tren_may=True: {sum(1 for _i,_n,v,_g in giong if GB.tren_may(v))}")
print("\n=== NGUON ===")
for k, n in Counter(GB.nguon(v) for _i,_n,v,_g in giong).most_common():
    print(f"  {k:14s} {n}  ten={GB.TEN_NGUON.get(k)} mien_phi={k in GB._MIEN_PHI} can_tai={GB._CAN_TAI.get(k,'')!r}")

print("\n=== GIOI TINH suy tu NHAN (khong doan tu ma) ===")
# nhan day du = tooltip dong dau; nhan tren dong da bi nhan_gon rut
pat_nu = re.compile(r"(?:^|[—·\-]\s*)Nữ\b|\bNữ\s")
pat_nam = re.compile(r"(?:^|[—·\-]\s*)Nam\b(?!\s*Minh)|\bNam\s+(?:tr|kh|d|ấ|c|m|g)")
nu = nam = ko = 0
vd_ko = []
for i, n, v, g in giong:
    it = dlg.cb_giong.model().item(i)
    tt = it.toolTip() if it is not None else ""
    kho = (n or "") + "\n" + (tt or "")
    a, b = bool(pat_nu.search(kho)), bool(pat_nam.search(kho))
    if a and not b: nu += 1
    elif b and not a: nam += 1
    else:
        ko += 1
        if len(vd_ko) < 25: vd_ko.append((v, (n or "")[:70], a, b))
print(f"  NU={nu}  NAM={nam}  KHONG-RO/CA-HAI={ko}")
for v, n, a, b in vd_ko:
    print(f"    {v[:44]:46s} nu={a} nam={b} | {n}")

print("\n=== 12 NHAN DAU + tooltip dong 1 (de xem cau tao) ===")
for i, n, v, g in giong[:12]:
    it = dlg.cb_giong.model().item(i)
    tt = (it.toolTip() if it is not None else "").split("\n")
    print(f"  [{v[:36]:38s}] {n[:66]}")
    for d in tt[:3]:
        print(f"        tt: {d[:100]}")

print("\n=== doc_duoc() theo tung tieng (nguon: app/core/da_ngu.py) ===")
from app.core import da_ngu as DN
for nn in ("vi", "en", "ko", "ja", "zh"):
    t = sum(1 for _i,_n,v,_g in giong if DN.doc_duoc(v, nn) is True)
    f = sum(1 for _i,_n,v,_g in giong if DN.doc_duoc(v, nn) is False)
    x = sum(1 for _i,_n,v,_g in giong if DN.doc_duoc(v, nn) is None)
    print(f"  {nn}: True={t:4d}  False={f:4d}  None={x:4d}")
print("\n  giong VIET bi None (doc_duoc None) — nguon nao:")
from collections import Counter as C2
cc = C2(GB.nguon(v) for _i,_n,v,_g in giong if DN.doc_duoc(v,'vi') is None)
print("   ", dict(cc))
print("\n  ma vbee + piper + vieneu -> doc_duoc('vi'):")
for _i,_n,v,_g in giong:
    if GB.nguon(v) in ("vbee","piper") or v.startswith("vn:"):
        print(f"    {v[:40]:42s} vi={DN.doc_duoc(v,'vi')} en={DN.doc_duoc(v,'en')}")

print("\n=== GIOI TINH v2: bat '(Nam)' '(Nữ)' va '— Nam' '— Nữ' ===")
import re as _re
P_NU = _re.compile(r"\(Nữ\)|[—-]\s*Nữ\b|\bNữ\s+[a-zàáâãèéêìíòóôõùúăđĩũơưạ-ỹ]")
P_NAM = _re.compile(r"\(Nam\)|[—-]\s*Nam\b|\bNam\s+(?:trầm|trẻ|chuẩn|ấm|khỏe|kiểu|trung|sâu|cuốn)")
nu2 = nam2 = ko2 = ca2 = 0
vd2 = []
for i, n, v, g in giong:
    it = dlg.cb_giong.model().item(i)
    tt = it.toolTip() if it is not None else ""
    kho = (n or "") + "\n" + (tt or "")
    a, b = bool(P_NU.search(kho)), bool(P_NAM.search(kho))
    if a and b: ca2 += 1
    elif a: nu2 += 1
    elif b: nam2 += 1
    else:
        ko2 += 1
        if len(vd2) < 20: vd2.append((v, (n or "")[:72]))
print(f"  NU={nu2}  NAM={nam2}  CA-HAI={ca2}  KHONG-RO={ko2}")
for v, n in vd2: print(f"    {v[:40]:42s} | {n}")
