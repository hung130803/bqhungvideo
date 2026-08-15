# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 62 — chứng minh `_test_toan_khung.py` KHÔNG phải con dấu.

Cổng nào cũng phải trả lời được câu: *gỡ chốt ra thì mày có đỏ không?* Nếu
không thì nó chỉ là một lượt chạy tốn 30 giây rồi in "TẤT CẢ ĐẠT".

Cách chạy: sửa MỘT chỗ trong mã app -> chạy cổng -> đòi cổng FAIL -> TRẢ LẠI
nguyên trạng (dùng `finally`, và so lại nội dung file cuối lượt).

BA BÀI HỌC ĐÃ SẬP CỦA CHÍNH LOẠI SCRIPT NÀY (cổng 54), đừng lặp:
  1. **File repo là CRLF.** Chuỗi tìm viết `\\n` KHÔNG BAO GIỜ khớp -> phép
     phá im lặng không phá được gì. Nay chỉ dùng chuỗi MỘT DÒNG và đọc/ghi
     bằng `newline=""` để giữ nguyên `\\r\\n`.
  2. **"Không tìm thấy chỗ phá" là LỖI CỦA PHÉP THỬ, không phải LỌT.** Gộp
     hai cột đó là báo cáo ngược sự thật. Nay tách 3 cột: BẮT · LỌT · HỎNG.
  3. Đòi cổng FAIL thì phải đòi **mã thoát != 0**, đừng đọc chữ trong log.

  .venv\\Scripts\\python -u _pha_toan_khung.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
CONG = REPO / "_test_toan_khung.py"

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


def doc(p: Path) -> str:
    """Đọc GIỮ NGUYÊN xuống dòng (repo là CRLF).

    Dùng `open(newline="")` chứ KHÔNG `Path.read_text(newline=...)`: tham số
    đó mới có từ Python 3.13, máy này 3.12 -> `TypeError`.
    """
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def ghi(p: Path, s: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


#: (tên, file, chuỗi CŨ, chuỗi MỚI) — mỗi phép phá gỡ ĐÚNG MỘT chốt.
PHEP = [
    ("1. `studio_page` truyền HẰNG SỐ False (giữ nguyên mặt chữ, đổi ý nghĩa)",
     "app/ui/studio_page.py",
     "                    None if self.layout_tpl.get(\"che_chu_toan_khung\") is None",
     "                    False if True"),
    ("2. `loc_cho_xuat` ép `bool()` -> mất trạng thái thứ ba (theo env)",
     "app/core/che_chu.py",
     "    _tk = _BAT_TOAN_KHUNG if toan_khung is None else bool(toan_khung)",
     "    _tk = bool(toan_khung)"),
    ("3. `doc_che_chu` ép `bool()` -> `None` rơi thành False",
     "app/modules/m1_highlight.py",
     "            tk = bool(payload.get(\"che_chu_toan_khung\"))",
     "            tk = bool(payload.get(\"che_chu_toan_khung\"))\n    tk = bool(tk)",
     ),
    ("4. cờ KHÔNG vào `sig` -> bật ô xong bấm Xuất cả kênh bị smart-skip",
     "app/services.py",
     "        if che_chu_toan_khung:",
     "        if False and che_chu_toan_khung:"),
    ("5. ô MẶC ĐỊNH BẬT (đổi mặc định = đổi hành vi 200-300 kênh)",
     "app/ui/editor.py",
     "        self.che_chu_tk.setChecked(False)",
     "        self.che_chu_tk.setChecked(True)"),
    ("6. `_collect` KHÔNG lưu khoá -> round-trip mất cờ",
     "app/ui/editor.py",
     "        lay[\"che_chu_toan_khung\"] = self.che_chu_tk.isChecked()",
     "        pass"),
    # Phá phải viết MỘT DÒNG (repo CRLF: chuỗi nhiều dòng viết `\n` không khớp
    # -> phép thử im lặng không phá được gì). Ở đây gỡ ô con khỏi vòng lặp
    # bằng cách đổi chính tên biến trên DÒNG chứa nó.
    ("7. ô con KHÔNG theo ô cha -> user tắt che chữ mà ô vẫn bấm được",
     "app/ui/editor.py",
     "                  self.che_chu_tk):",
     "                  ):"),
    ("8. tooltip BỎ cảnh báo camera cố định (mất lời cảnh báo đắt nhất)",
     "app/ui/editor.py",
     "            \"ĐỪNG BẬT cho video quay bằng CAMERA CỐ ĐỊNH (máy đặt yên một \"",
     "            \"Dung bat cho video quay bang CAMERA CO DINH (may dat yen mot \""),
]


def chay_cong() -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("BQ_FFMPEG_SLOTS", "1")
    r = subprocess.run(
        [sys.executable, "-u", str(CONG)], cwd=str(REPO), env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    print("=" * 72)
    print("THỬ PHÁ CỔNG 62 — gỡ chốt ra thì cổng PHẢI đỏ")
    print("=" * 72)

    ma0, log0 = chay_cong()
    print(f"\nĐỐI CHỨNG (chưa phá): mã thoát {ma0} · "
          f"{[l for l in log0.splitlines() if l.startswith('ĐẠT ')][-1:]}")
    if ma0 != 0:
        print("  !! Cổng đã ĐỎ TỪ ĐẦU — không thử phá được. Sửa cổng trước.")
        return 2

    bat = lot = hong = 0
    for ten, rel, cu, moi in PHEP:
        p = REPO / rel
        goc = doc(p)
        if cu not in goc:
            hong += 1
            print(f"\n[HỎNG PHÉP THỬ] {ten}\n    -> KHÔNG TÌM THẤY chỗ phá "
                  f"trong {rel} (chuỗi đã đổi? CRLF?). ĐÂY LÀ LỖI CỦA PHÉP "
                  "THỬ, không phải cổng lọt.")
            continue
        try:
            ghi(p, goc.replace(cu, moi, 1))
            ma, log = chay_cong()
        finally:
            ghi(p, goc)
            assert doc(p) == goc, f"KHÔNG trả lại được nguyên trạng {rel}!"
        hong_muc = [l.strip() for l in log.splitlines()
                    if l.strip().startswith("HỎNG ")]
        if ma != 0:
            bat += 1
            print(f"\n[BẮT ĐƯỢC] {ten}\n    mã thoát {ma} · {len(hong_muc)} mục hỏng"
                  + ("".join(f"\n      · {x}" for x in hong_muc[:4]) if hong_muc
                     else "\n      · (chết giữa chừng — cũng là đỏ)"))
        else:
            lot += 1
            print(f"\n[LỌT !!!] {ten}\n    cổng VẪN XANH sau khi phá — "
                  "chốt này là con dấu, phải viết lại.")

    print("\n" + "=" * 72)
    print(f"BẮT {bat} · LỌT {lot} · HỎNG-PHÉP-THỬ {hong} / {len(PHEP)} phép")
    print("=" * 72)
    # LỌT = cổng dở. HỎNG phép thử cũng phải đỏ: không đo được thì không được
    # khoe là đã đo.
    return 1 if (lot or hong) else 0


if __name__ == "__main__":
    raise SystemExit(main())
