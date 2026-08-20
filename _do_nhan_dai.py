"""ĐO độ dài nhãn giọng nhân bản — TRƯỚC và SAU `gom_nhom`.

Vì sao cần script này: cổng 88 mục **8d** đo nhãn **SAU `gom_nhom(loi_tat=True)`**
còn `nhan_ban_giong.nhan()` lại tự đo **CHUỖI CỦA CHÍNH NÓ**. Hai chỗ đo hai
chuỗi khác nhau nên trần 130 trong `nhan()` không chặn được cái cổng chấm.
Script này in ra CẢ HAI để biết `gom_nhom` cộng thêm bao nhiêu ký tự.
"""
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")            # type: ignore[union-attr]
os.environ.setdefault("BQ_QSETTINGS_INI",
                      tempfile.mkdtemp(prefix="bq_do_nhan_"))

import config                                        # noqa: E402,F401
from app.core import giong_bang as GB                # noqa: E402
from app.core import nhan_ban_giong as NB            # noqa: E402

print("thieu_de_nhan_ban('vieneu') THẬT =", NB.thieu_de_nhan_ban("vieneu"))
print("TRAN_NHAN =", NB.TRAN_NHAN)

mau = pathlib.Path(NB.thu_muc_mau()) / "_do_nhan_dai.wav"
mau.parent.mkdir(parents=True, exist_ok=True)
if not mau.exists():
    mau.write_bytes(b"RIFF")

NB._ghi_so({
    "Giọng của tôi": {"mau": str(mau), "may": "vieneu", "lang": "vi",
                      "giay": 8.4},
    "Giọng chị Lan": {"mau": str(mau), "may": "vieneu", "lang": "vi",
                      "giay": 5.0},
})

ds = NB.danh_sach()
print("\n--- nhan() tự đo (cái `nhan` so với TRAN_NHAN) ---")
for ma, nh in ds:
    print(f"  len={len(nh):3d}  {nh}")

nhom = GB.gom_nhom([(n, m) for m, n in ds], "vi", loi_tat=True)
dong = [(n, v) for n, v in nhom if v]
print("\n--- SAU gom_nhom(loi_tat=True) — ĐÚNG cái cổng 8d chấm ---")
for n, v in sorted(dong, key=lambda t: -len(t[0]))[:5]:
    print(f"  len={len(n):3d}  {n}")

_dai_truoc = max((len(n) for _m, n in ds), default=0)
_dai_sau = max((len(n) for n, _v in dong), default=0)
print(f"\nDÀI NHẤT trước={_dai_truoc} · sau={_dai_sau} · "
      f"gom_nhom CỘNG THÊM {_dai_sau - _dai_truoc} ký tự")
