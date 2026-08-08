# -*- coding: utf-8 -*-
"""SOI dòng nhãn 2 của bảng mẫu — vì sao ô hiệu ứng MẤT dòng 2 mà ô GỐC thì có.

KẾT LUẬN (đo 08/08/2026): ký tự `%` là thủ phạm. `drawtext` mặc định
`expansion=normal` -> nó coi `%` là mở đầu hàm `%{...}`; gặp `%` trơ thì **bỏ
sạch phần còn lại của chuỗi và VẪN trả rc=0**. Nhãn `đổi 16% khung hình` ra
**0 pixel** trong im lặng. Chữa: `expansion=none`.
"""
import os
import subprocess
import sys
import tempfile

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = os.path.join(tempfile.gettempdir(), "hu_soi")
os.makedirs(_SB, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _do_hieu_ung_bang as B  # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
td = tempfile.mkdtemp(prefix="_soinhan_")
font = B._font_viet()
print("font:", font)

CA = [
    "0/25",
    "1/25  ·  CapCut: Zoom Lens  ·  đổi 16% khung hình",
    "đổi 16% khung hình",
    "100%",
    "đổi 16 phần trăm khung hình",
]
for i, s in enumerate(CA):
    p = os.path.join(td, f"c{i}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)
    dong = []
    for nhan, ex in (("mặc định", False), ("expansion=none", True)):
        png = os.path.join(td, f"c{i}_{int(ex)}.png")
        dt = B._dt(p, font, "40", 40, "0xC8E6C9")
        if ex and "expansion" not in dt:
            dt += ":expansion=none"
        r = subprocess.run(
            [B._ff(), "-y", "-hide_banner", "-v", "error", "-f", "lavfi",
             "-i", "color=c=black:s=1080x200", "-frames:v", "1", "-vf", dt, png],
            capture_output=True, text=True, errors="replace", creationflags=CNW)
        im = cv2.imread(png)
        px = 0 if im is None else int((cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) > 40).sum())
        dong.append(f"{nhan}: px={px:6d} rc={r.returncode}")
    print(f"{i}  {' | '.join(dong)}   {s[:50]!r}")
print("\nthu muc:", td)
