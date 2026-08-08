# -*- coding: utf-8 -*-
"""TIÊU ĐỀ TRÊN CLIP CÓ ĐỌC ĐƯỢC KHÔNG, hay ra Ô VUÔNG (tofu)?

    .venv\\Scripts\\python _ra_tieu_de.py

VÌ SAO CÓ FILE NÀY: lượt e2e 08/08/2026 xuất 8 Part thì **cả 8** có hộp tiêu đề
vẽ thành **ô vuông trắng** (glyph .notdef). Phải phân định: lỗi THẬT của app hay
chỉ là **tạo tác của test** (test dựng QApplication trần, không gọi
`theme.apply_theme` nên `fonts.load_fonts()` chưa nạp .ttf; cộng
`QT_QPA_PLATFORM=offscreen`).

CÁCH ĐO (không tin mắt, đếm pixel):
  · vẽ overlay bằng `editor.render_overlay_png` với CÙNG chữ, 3 cấu hình
  · đếm **số cột pixel có chữ** và **tỉ lệ pixel đặc** — chữ thật thì nét mảnh,
    ô tofu thì là KHUNG RỖNG có 4 cạnh -> đếm "đường viền ngang liên tục"
  · ca chuẩn: so với chữ vẽ bằng font hệ thống chắc chắn có ('Arial')

Đây đúng loại lỗi anh Hùng gặp rồi (v2.6.22: nút 📋/✕ ra Ô ĐEN vì thiếu glyph).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="ra_td_"))
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "t.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "s.ini"))

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

CHU = "You You? What Happens Next Will Shock You!"
CHU_JP = "都心裏路地のデザイナーズ秘密基地、見逃すな！"


def do_anh(p: Path) -> dict:
    """Đếm đặc trưng của ảnh chữ: pixel đục, số hàng có mực, và ĐỘ ĐẶC.

    Ô tofu = khung chữ nhật RỖNG -> tỉ lệ pixel đục trên hộp bao thấp và
    số 'đoạn ngang liên tục dài' cao. Chữ thật -> nét rời rạc.
    """
    import numpy as np
    from PIL import Image  # type: ignore
    im = np.array(Image.open(p).convert("RGBA"))
    a = im[:, :, 3]
    duc = a > 40
    if not duc.any():
        return {"px": 0}
    ys, xs = np.where(duc)
    h = int(ys.max() - ys.min() + 1)
    w = int(xs.max() - xs.min() + 1)
    # đoạn ngang liên tục dài >= 60% bề rộng hộp bao -> dấu hiệu KHUNG (tofu)
    dai = 0
    for y in range(int(ys.min()), int(ys.max()) + 1):
        hang = duc[y, int(xs.min()):int(xs.max()) + 1]
        run = mx = 0
        for v in hang:
            run = run + 1 if v else 0
            mx = max(mx, run)
        if mx >= 0.6 * w:
            dai += 1
    return {"px": int(duc.sum()), "hop": f"{w}x{h}",
            "dac": round(float(duc.sum()) / max(1, w * h), 3),
            "hang_ngang_dai": dai}


def main() -> int:
    from PyQt6.QtWidgets import QApplication
    qapp = QApplication(sys.argv)      # PHẢI giữ biến (bẫy 0xC0000409)
    from app.ui import editor

    ra = {}
    print(f"nền tảng Qt: {qapp.platformName()!r}")

    def ve(ten: str, font: str, chu: str) -> None:
        p = _SB / f"{ten}.png"
        lop = [{"text": "{title}", "font": font, "size": 0.055,
                "nx": 0.5, "ny": 0.12, "color": "#FFFFFF", "is_part": False,
                "bg": True, "bg_color": "#1A1A1A", "bg_alpha": 0.8,
                "radius": 30, "outline": 0.12}]
        editor.render_overlay_png(lop, 1, 1080, 1920, str(p), chu, "")
        d = do_anh(p) if p.exists() else {"px": -1}
        ra[ten] = d
        print(f"  {ten:34s} {d}")

    print("\n── A. CHƯA nạp font (đúng cảnh test e2e vừa rồi) ──")
    ve("A_montserrat_chua_nap", "Montserrat", CHU)
    ve("A_arial_chua_nap", "Arial", CHU)

    print("\n── B. ĐÃ nạp font như app thật (theme.apply_theme) ──")
    from app.ui.theme import apply_theme
    apply_theme(qapp)
    ve("B_montserrat_da_nap", "Montserrat", CHU)
    ve("B_arial_da_nap", "Arial", CHU)
    ve("B_montserrat_nhat", "Montserrat", CHU_JP)

    print("\n── KẾT LUẬN ──")
    a = ra.get("A_montserrat_chua_nap", {})
    b = ra.get("B_montserrat_da_nap", {})
    tofu_a = a.get("hang_ngang_dai", 0) > 2
    tofu_b = b.get("hang_ngang_dai", 0) > 2
    print(f"  chưa nạp font -> tofu? {tofu_a}   (hàng ngang dài "
          f"{a.get('hang_ngang_dai')})")
    print(f"  ĐÃ nạp font   -> tofu? {tofu_b}   (hàng ngang dài "
          f"{b.get('hang_ngang_dai')})")
    if tofu_a and not tofu_b:
        print("  => LỖI CỦA BỘ TEST: e2e dựng QApplication trần, thiếu "
              "theme.apply_theme() nên font .ttf chưa vào QFontDatabase.\n"
              "     App THẬT (main.py) có gọi -> tiêu đề đọc được.")
    elif tofu_b:
        print("  => LỖI THẬT CỦA APP: nạp font đầy đủ mà vẫn ra ô vuông.")
    else:
        print("  => không tái hiện được tofu ở cả 2 cấu hình.")
    (REPO / "_ket__ra_tieu_de.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[ảnh để xem] {_SB}")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
