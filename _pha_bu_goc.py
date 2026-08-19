# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 78 — gỡ chốt ra thì cổng PHẢI ĐỎ (19/08/2026).

Cổng xanh KHÔNG chứng minh được gì nếu chưa ai thử phá nó. Ba lượt hồi quy
trong repo này đã ĐẠT OAN vì lượt chạy chết TRƯỚC khi tới chốt.

**CHẠY TRONG `git worktree` RIÊNG, KHÔNG SỬA CÂY MÃ ĐANG DÙNG.** Máy này có
3-4 luồng khác đang sửa/chạy trên cùng cây mã; sửa `app/core/thay_giong.py`
tại chỗ rồi bị giết giữa chừng là để lại bản HỎNG trong file của người khác.
Worktree được nối `bin/` bằng junction (`bin/` nằm trong `.gitignore`), và
cổng dùng `Path(__file__).resolve().parent` nên nó nạp `app/` CỦA WORKTREE —
đúng bài học "cổng test phải trỏ về bản mã của chính nó".

BA PHÉP PHÁ, mỗi phép gỡ ĐÚNG MỘT chốt của bản vá `bu_giong_goc`. Chốt thứ
tư — cửa *"gốc phải CÓ TIẾNG mới bù"* — đã có MỤC 5 của chính cổng tự kiểm
(vá `duong_bao_muc` rồi đòi bộ dò phải kêu), nên không lặp lại ở đây:
  1. `BU_GOC_BUOC` 0,05 -> 0,20 — ĐÚNG con bug đã xảy ra thật: cửa sổ 0,20 s
     trung bình mất khoảng lặng giữa từ nên sàn ước leo sát mức lời, ngưỡng
     vượt cả đỉnh, bản vá **im lặng không bù mảnh nào** (`so_bu=0`).
  2. Gỡ LƯỚI AN TOÀN (`min(san+12, dinh-3)` -> `san+12`) — cùng hậu quả,
     nhưng chỉ lộ ra trên lớp giọng DẢI HẸP.
  3. `BU_GOC_NOI_DB` 12 -> 10 — lệch với thước đo `_do_mat_giong` (cũng dùng
     `sàn+12`); lệch bộ dò thì có cửa sổ cổng đếm là "mất" mà bản vá không bù.

`KHÔNG PHÁ ĐƯỢC` (không tìm thấy chuỗi cần đổi) được tách HẲN khỏi `LỌT` —
gộp hai cái là báo cáo NGƯỢC sự thật (bài học cổng 54: file CRLF làm 4/6 phép
phá im lặng không phá được gì mà bảng vẫn đếm vào cột LỌT).

Chạy: .venv\\Scripts\\python -u _pha_bu_goc.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
WT = Path(r"D:\claude\_wt_pha78")
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

MUC_TIEU = WT / "app" / "core" / "thay_giong.py"
CONG = WT / "_test_bu_giong_goc.py"


def doc(p: Path) -> str:
    """`Path.read_text(newline=...)` chỉ có từ Python 3.13 — máy này 3.12, gọi
    vào là `TypeError`. Và `newline=""` là BẮT BUỘC: repo này CRLF, đọc kiểu
    text mode rồi ghi lại là đổi xuống dòng CẢ FILE (bài học cổng 54)."""
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def ghi(p: Path, s: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)

#: (nhãn, chuỗi TÌM, chuỗi THAY) — mỗi phép đổi ĐÚNG MỘT lần (`replace(..., 1)`).
PHEP = [
    ("1. BU_GOC_BUOC 0,05 -> 0,20 (bộ dò MÙ, đúng bug đã xảy ra)",
     "BU_GOC_BUOC = 0.05", "BU_GOC_BUOC = 0.20"),
    ("2. gỡ LƯỚI AN TOÀN (ngưỡng được phép leo trên mức lời)",
     "nguong = min(san + BU_GOC_NOI_DB, dinh - BU_GOC_DUOI_DINH_DB)",
     "nguong = san + BU_GOC_NOI_DB"),
    ("3. BU_GOC_NOI_DB 12 -> 10 (lệch với thước `_do_mat_giong`)",
     "BU_GOC_NOI_DB = 12.0", "BU_GOC_NOI_DB = 10.0"),
]


def chay_cong() -> tuple[int, str]:
    r = subprocess.run([PY, "-u", str(CONG)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(WT),
                       timeout=3600)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def tong_ket(s: str) -> str:
    m = re.findall(r"CỔNG 78 — ĐẠT (\d+) · HỎNG (\d+)", s)
    return f"ĐẠT {m[-1][0]} · HỎNG {m[-1][1]}" if m else "KHÔNG CÓ DÒNG TỔNG KẾT"


def hong_nao(s: str) -> list[str]:
    return re.findall(r"\[HỎNG\] (.+?)(?: — |$)", s, re.M)


def main() -> int:
    if not MUC_TIEU.exists() or not CONG.exists():
        print(f"KHÔNG CÓ worktree {WT} — tạo bằng:\n"
              f"  git worktree add --detach {WT} HEAD\n"
              f"  mklink /J {WT}\\bin <repo>\\bin")
        return 2
    goc = doc(MUC_TIEU)
    luu = MUC_TIEU.with_suffix(".py.goc")
    shutil.copy2(MUC_TIEU, luu)

    print("=" * 74)
    print("LƯỢT 0 — CỔNG NGUYÊN VẸN (phải XANH, nếu không thì mọi số dưới vô nghĩa)")
    print("=" * 74)
    rc, out = chay_cong()
    print(f"  mã thoát {rc} · {tong_ket(out)}")
    if rc != 0:
        print("  DỪNG: cổng đã đỏ sẵn, không thử phá được")
        ghi(MUC_TIEU, goc)
        luu.unlink(missing_ok=True)
        return 3

    bat = lot = khong = 0
    try:
        for nhan, tim, thay in PHEP:
            print(f"\n{'=' * 74}\nPHÉP PHÁ {nhan}\n{'=' * 74}")
            if tim not in goc:
                khong += 1
                print(f"  KHÔNG PHÁ ĐƯỢC — không tìm thấy chuỗi: {tim[:60]!r}")
                print("  (đây là LỖI CỦA PHÉP THỬ, KHÔNG phải 'cổng để lọt')")
                continue
            ghi(MUC_TIEU, goc.replace(tim, thay, 1))
            rc, out = chay_cong()
            hong = hong_nao(out)
            if rc != 0:
                bat += 1
                print(f"  BẮT ĐƯỢC — mã thoát {rc} · {tong_ket(out)}")
            else:
                lot += 1
                print(f"  ***LỌT*** — mã thoát {rc} · {tong_ket(out)}")
            for h in hong[:8]:
                print(f"     [HỎNG] {h}")
    finally:
        # PHẢI dùng `ghi`, KHÔNG `write_text(newline=...)`: kwarg đó chỉ có từ
        # Python 3.13, máy này 3.12 -> `TypeError` NGAY TRONG `finally` = để
        # lại bản ĐÃ PHÁ trong worktree. Bản đầu của file này viết như vậy.
        ghi(MUC_TIEU, goc)
        luu.unlink(missing_ok=True)

    print(f"\n{'=' * 74}")
    print(f"THỬ PHÁ CỔNG 78 — BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong}")
    print("=" * 74)
    r = subprocess.run(["git", "diff", "--stat", "--", "app/core/thay_giong.py"],
                       capture_output=True, text=True, cwd=str(WT), timeout=120)
    print(f"  worktree đã trả nguyên: "
          f"{'SẠCH' if not (r.stdout or '').strip() else 'CÒN BẨN — ' + r.stdout}")
    return 0 if (lot == 0 and khong == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
