# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 93 — gỡ HẲN từng chốt rồi đòi cổng phải ĐỎ.

BA LUẬT (đã trả giá ở các lượt phá trước, đừng bỏ):
1. Neo phải **DUY NHẤT** trong file. Neo trùng thì `replace(..., 1)` sửa nhầm
   chỗ khác -> file `SyntaxError` -> cổng chết lúc import -> mã thoát 1 ->
   bảng ghi "BẮT" cho một chốt phép thử **chưa hề chạm tới** (bẫy đã sập ở
   `_pha_doc_lan.py`).
2. **`compile()` lại bản đã phá.** Không biên dịch được = **KHÔNG PHÁ ĐƯỢC**,
   KHÔNG phải "BẮT".
3. Phá thì **GỠ SẠCH chốt**, đừng đổi giá trị bên trong nó — đổi giá trị có
   thể làm hàm CHẶT HƠN rồi bảng đọc thành "cổng không bắt được" (bẫy cổng 80
   LỌT 7).
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
DICH = REPO / "app" / "core" / "thay_giong.py"
CONG = REPO / "_test_dich_me.py"

PHEP = [
    ("chia mẻ -> MỘT mẻ (dựng lại bản CŨ)",
     "        if cur and (can > mt or len(thu) > ME_TOI_DA):",
     "        if False:"),
    ("gỡ hệ số rộng chỗ trả lời (ME_HE_SO_ROI)",
     "ME_HE_SO_ROI = 4.0",
     "ME_HE_SO_ROI = 1.0"),
    ("gỡ NGỮ CẢNH hai bên khỏi prompt dịch",
     '                + f\'\\nĐOẠN NGAY TRƯỚC (KHÔNG dịch, chỉ để nối mạch): \'\n'
     '                  f\'"{truoc or "(đầu bài)"}"\\n\'',
     '                + ""'),
    ("cổng CHẤM quay về MỘT prompt cho cả loạt",
     "    for phan in chia_me_dich(cap, list(range(len(goc))),\n"
     "                             token_ra_moi_cau=12):",
     "    for phan in [list(range(len(goc)))]:"),
    ("một mẻ hỏng -> BỎ CẢ LOẠT (all-or-nothing)",
     "                loi_dau = loi_dau or e\n                continue",
     "                loi_dau = loi_dau or e\n                break"),
]


def main() -> int:
    goc = DICH.read_text(encoding="utf-8")
    sao = DICH.with_suffix(".py.bak_pha")
    shutil.copy2(DICH, sao)
    bat = lot = khong = 0
    try:
        # ĐỐI CHỨNG: cổng phải XANH trước khi phá, nếu không mọi cột vô nghĩa.
        r = subprocess.run([sys.executable, str(CONG)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ — dừng, không đo được gì.")
            return 2
        print("đối chứng: cổng XANH trước khi phá\n")
        for ten, tim, thay in PHEP:
            n = goc.count(tim)
            if n != 1:
                print("KHÔNG PHÁ ĐƯỢC | %-46s | neo xuất hiện %d lần"
                      % (ten, n))
                khong += 1
                continue
            pha = goc.replace(tim, thay, 1)
            try:
                compile(pha, str(DICH), "exec")
            except SyntaxError as e:
                print("KHÔNG PHÁ ĐƯỢC | %-46s | bản phá không biên dịch: %s"
                      % (ten, e))
                khong += 1
                continue
            DICH.write_text(pha, encoding="utf-8")
            try:
                r = subprocess.run([sys.executable, str(CONG)],
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                do = (r.returncode != 0)
                dong = [x for x in (r.stdout or "").splitlines()
                        if x.startswith("  HỎNG")]
                print("%-14s | %-46s | %d mục HỎNG"
                      % ("BẮT" if do else "LỌT", ten, len(dong)))
                for x in dong[:3]:
                    print("      " + x.strip())
                bat += 1 if do else 0
                lot += 0 if do else 1
            finally:
                DICH.write_text(goc, encoding="utf-8")
    finally:
        DICH.write_text(goc, encoding="utf-8")
        sao.unlink(missing_ok=True)
    print("\nKETQUA: BẮT %d · LỌT %d · KHÔNG PHÁ ĐƯỢC %d" % (bat, lot, khong))
    return 1 if (lot or khong) else 0


if __name__ == "__main__":
    sys.exit(main())
