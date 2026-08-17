"""THỬ PHÁ CỔNG 67 — cổng không bắt được thì nó chỉ là con dấu.

Mỗi phép phá gỡ ĐÚNG MỘT chốt của bản vá rồi chạy lại cổng 67; cổng phải ĐỎ.
Xong thì hoàn nguyên nguyên trạng.

LƯU Ý (bài học cổng 54): file repo là **CRLF**, nên chuỗi tìm phải nằm gọn
TRONG MỘT DÒNG và phải đọc/ghi bằng `newline=""`. Không tìm thấy chỗ phá =
**LỖI CỦA PHÉP THỬ**, tách hẳn khỏi cột LỌT — bản đầu của cổng 54 đếm nhầm
hai thứ đó vào nhau và báo cáo NGƯỢC sự thật.
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
CAP = REPO / "app" / "core" / "captions.py"
CHE = REPO / "app" / "core" / "che_chu.py"

PHEP = [
    ("ghi_ass BỎ QUA đơn thuốc kiểu chữ", CHE,
     "    if kieu:", "    if False:"),
    ("chuoi_subtitles BỎ fontsdir", CHE,
     '        ra += f":fontsdir=\'{_esc_loc(fd)}\'"',
     '        ra += ""'),
    ("kieu_chu_ass BỎ QUA in đậm/in nghiêng", CAP,
     '            "bold": -1 if (True if dam is None else dam) else 0,',
     '            "bold": -1,'),
    ("bỏ chốt chống CẮT ĐÁY KHUNG", CHE,
     "            cy = max(cs * 0.9, min(float(cy), H - cs * 0.9))",
     "            cy = float(cy)"),
    ("build_ass tự tính kiểu (không qua cửa chung)", CAP,
     '    ow, shadow, border_style = _k["ow"], _k["shadow"], _k["border_style"]',
     '    ow, shadow, border_style = _k["ow"], _k["shadow"] + 1, _k["border_style"]'),
    ("ghi_ass BỎ QUA ô vị trí", CHE,
     "        if vt in _VI_TRI_ASS:", "        if False:"),
    ("ghi_ass BỎ QUA ô cỡ chữ", CHE,
     "        cs = max(14, int(round(ty_co * H)))", "        cs = cs"),
]


def doc(p: Path) -> str:
    return io.open(p, encoding="utf-8", newline="").read()


def ghi(p: Path, s: str) -> None:
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def chay_cong() -> int:
    r = subprocess.run([str(REPO / ".venv" / "Scripts" / "python.exe"), "-u",
                        str(REPO / "_test_kieu_chu_tg.py")],
                       cwd=REPO, capture_output=True, timeout=1800)
    return r.returncode


def main() -> int:
    goc = {CAP: doc(CAP), CHE: doc(CHE)}
    bat = lot = khong_pha = 0
    try:
        for ten, f, tim, thay in PHEP:
            s = goc[f]
            if tim not in s:
                print(f"KHÔNG PHÁ ĐƯỢC  {ten} — không thấy chỗ phá")
                khong_pha += 1
                continue
            ghi(f, s.replace(tim, thay, 1))
            rc = chay_cong()
            ghi(f, s)                       # hoàn nguyên NGAY
            if rc != 0:
                print(f"BẮT ĐƯỢC        {ten} (cổng mã {rc})")
                bat += 1
            else:
                print(f"LỌT             {ten} (cổng VẪN XANH)")
                lot += 1
    finally:
        for f, s in goc.items():
            ghi(f, s)
    print(f"\nBẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha}")
    return 0 if lot == 0 and khong_pha == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
