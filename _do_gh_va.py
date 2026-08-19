# -*- coding: utf-8 -*-
"""ĐO BẢN VÁ: bấm nút "Tải bộ gióng hàng" trên ĐÚNG môi trường máy anh Hùng.

Gọi THẲNG `giong_hang.cai_giong_hang()` — không dựng đường riêng, không mock
pip — nhưng ép hai thứ cho khớp bản CÀI:

  · `BQ_GIONG_HANG_LIB` -> `%LOCALAPPDATA%\\BQHungVideo\\_giong_hang`
  · `BQ_DEMUCS_LIB`     -> `%LOCALAPPDATA%\\BQHungVideo\\_lib`  (torch +cpu)
  · **pip và tiến trình con chạy bằng `C:\\Python314\\python.exe`**

Chỗ thứ ba là chỗ dễ đo nhầm nhất: chạy từ nguồn thì `_lenh_pip()` trả python
của `.venv` (**3.12**) trong khi `_giong_hang`/`_lib` của bản cài gắn thẻ
**cp314**. Cài bằng 3.12 vào thư mục cp314 là làm hỏng thêm, và phép đo thì ra
một `ImportError` KHÁC HẲN rồi kết luận sai (đã sập đúng bẫy này một lần ở
lượt đo đầu — xem `_do_gh_dung.py`).

`BQ_GH_THU=1` -> cài vào thư mục NHÁP thay vì thư mục thật (đo mã, không tải
model 1,18 GB).
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo"
THU = (os.environ.get("BQ_GH_THU") or "").strip() == "1"

DICH = REPO / "_bq_gh_nhap" if THU else DATA / "_giong_hang"
LIB = DATA / "_lib"

os.environ["BQ_GIONG_HANG_LIB"] = str(DICH)
os.environ["BQ_DEMUCS_LIB"] = str(LIB)


def _py314() -> str:
    for c in (r"C:\Python314\python.exe",):
        if Path(c).is_file():
            return c
    return shutil.which("python.exe") or sys.executable


def main() -> int:
    PY = _py314()
    from app.core import giong_hang as gh
    from app.core import thay_giong as tg

    # Ép ĐÚNG bản Python mà `.exe` dùng (`_python_chay` -> which python).
    gh._python_chay = lambda: [PY]                       # noqa: SLF001
    tg._lenh_pip = lambda: [PY, "-m", "pip"]             # noqa: SLF001

    print("python cài  :", PY)
    print("thư mục đích:", gh.thu_muc_gh())
    print("lib torch   :", gh.lib_torch())
    print("torch       :", gh.ban_torch())
    print("torchaudio  :", gh.ban_torchaudio() or "(chưa có)")
    print("chỉ mục cần :", gh.chi_muc_cho_torchaudio())
    print("lệch cây    :", repr(gh.lech_cay_ban()))
    tt = gh.tinh_trang_giong_hang()
    print("TRƯỚC  co   :", tt["co"], "| thiếu:", tt["thieu"])

    print("\n--- bấm nút ---")
    t0 = time.time()
    moc = [0.0]

    def prog(p: float, m: str) -> None:
        # In thưa cho khỏi ngập, nhưng LUÔN in khi % nhảy
        if p - moc[0] >= 0.01 or p >= 0.99:
            moc[0] = p
            print(f"   [{p*100:5.1f}%] {m[:110]}")

    r = gh.cai_giong_hang(on_progress=prog)
    print(f"--- xong sau {time.time()-t0:.1f}s ---")
    print("ok   :", r.get("ok"))
    if r.get("loi"):
        print("lỗi  :", str(r["loi"])[:600])
    print("nhật ký (10 dòng cuối):")
    for x in (r.get("nhat_ky") or [])[-10:]:
        print("   ", x[:130])

    tt2 = r.get("tinh_trang") or gh.tinh_trang_giong_hang()
    print("\nSAU    co   :", tt2["co"], "| thiếu:", tt2["thieu"])
    print("torch       :", tt2.get("ban_torch"))
    print("torchaudio  :", tt2.get("ban_torchaudio"))
    print("lệch cây    :", repr(tt2.get("lech_cay")))

    print("\n--- HẬU KIỂM spec.origin (tiến trình CẮT site-packages) ---")
    k = gh.do_goi_gh()
    for kk in ("ok", "nap", "nap_loi", "ta", "torchaudio_o",
               "torchaudio_trong_dich", "uroman_o", "uroman_trong_dich",
               "torch_o", "torch_trong_lib", "loi"):
        if kk in k:
            print(f"   {kk:<24} {k[kk]}")
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
