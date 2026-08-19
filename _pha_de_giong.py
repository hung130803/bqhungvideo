# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 86 — gỡ từng chốt của chế độ "đè giọng" rồi đòi cổng phải ĐỎ.

Không có lượt này thì cổng 86 chỉ là một CON DẤU: nó xanh, nhưng không ai biết
nó xanh vì bản vá đúng hay vì nó không kiểm gì cả.

MỖI PHÉP PHÁ GỠ ĐÚNG MỘT CHỐT. **Phá thì phải GỠ SẠCH chốt, đừng đổi giá trị
bên trong nó** — bài học cổng 80 (phép phá đổi `goc` thành đường dẫn không bao
giờ khớp, làm hàm CHẶT HƠN, rồi bảng đọc thành "cổng không bắt được").

BA CỘT, ĐỪNG GỘP (bài học cổng 54): **BẮT** = cổng đỏ đúng chỗ · **LỌT** = cổng
vẫn xanh (cổng hở thật) · **KHÔNG PHÁ ĐƯỢC** = không tìm thấy chỗ phá, tức LỖI
CỦA PHÉP THỬ chứ không phải điểm cộng cho cổng. Bản đầu của script thử phá cổng
54 đếm "không tìm thấy chỗ phá" vào cột LỌT và **báo cáo ngược sự thật**.

File repo là **CRLF**; `Path.read_text`/`write_text` của Python bật universal
newlines nên chuỗi nhiều dòng viết `\\n` vẫn khớp và ghi lại vẫn CRLF. Vẫn kiểm
`dem == 1` cho mỗi phép thay để không âm thầm thay 0 chỗ hoặc 2 chỗ.

Chạy:  .venv\\Scripts\\python -u _pha_de_giong.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

F_TG = REPO / "app/core/thay_giong.py"
F_TC = REPO / "app/core/tg_chay.py"

#: (tên, file, chuỗi CŨ, chuỗi MỚI, mục cổng PHẢI kêu)
PHEP = [
    ("1. `tach_giong` gọi VÔ ĐIỀU KIỆN (không bỏ bước tách nữa)", F_TG,
     '        if not de_giong:\n'
     '            prog(0.06, "Tách giọng khỏi nhạc nền...")\n'
     '            t = tach_giong(goc_wav, tam_goc / "tach", cach=cach_tach,\n'
     '                           on_progress=lambda p, m: prog(0.06 + 0.24 * p, m))\n',
     '        prog(0.06, "Tách giọng khỏi nhạc nền...")\n'
     '        t = tach_giong(goc_wav, tam_goc / "tach", cach=cach_tach,\n'
     '                       on_progress=lambda p, m: prog(0.06 + 0.24 * p, m))\n',
     "5a"),

    ("2. gỡ chốt BÙ GIỌNG GỐC (chế độ đè cộng giọng gốc HAI LẦN)", F_TG,
     '        if de_giong:\n'
     '            kq["bu_goc"] = {\n'
     '                "bat": False,\n'
     '                "vi_sao": "chế độ đè giọng — tiếng gốc còn NGUYÊN trong lớp "\n'
     '                          "nền, bù thêm là cộng giọng gốc hai lần"}\n'
     '        elif bu_giong_goc_bat:\n',
     '        if bu_giong_goc_bat:\n',
     "5b"),

    ("3. `thay_giong_mot_video` truyền HẰNG SỐ `de_giong=False`", F_TG,
     '                         de_giong=de_giong,\n',
     '                         de_giong=False,\n',
     "5c"),

    ("4. chốt Demucs CHẶN CẢ chế độ đè (gỡ `if de_giong: return`)", F_TG,
     '    if de_giong:\n        return\n'
     '    if (cach_tach or "auto").lower().strip() == "nhe":\n',
     '    if (cach_tach or "auto").lower().strip() == "nhe":\n',
     "4b"),

    ("5. cờ KHÔNG vào hash (bấm Chạy bị smart-skip, không một dòng báo)", F_TC,
     '    if de_giong:\n        sig += ":dg=1"\n    return sig\n',
     '    return sig\n',
     "2d"),

    ("6. cờ nối vào hash VÔ ĐIỀU KIỆN (đổi khoá MỌI job cũ)", F_TC,
     '    if de_giong:\n        sig += ":dg=1"\n',
     '    sig += f":dg={1 if de_giong else 0}"\n',
     "2c"),

    ("7. payload LUÔN mọc khoá `de_giong` (job cũ đổi hình dạng)", F_TC,
     '    if de_giong:\n        tt["de_giong"] = True\n',
     '    tt["de_giong"] = bool(de_giong)\n',
     "3a"),

    ("8. `chuan_cach_tron` lùi về CÁCH MỚI khi gặp chuỗi lạ", F_TG,
     '    return c if c in CACH_TRON else "tach"\n',
     '    return c if c in CACH_TRON else "de"\n',
     "1b"),
]


def chay_cong() -> tuple[int, str]:
    r = subprocess.run([str(REPO / ".venv/Scripts/python.exe"), "-u",
                        str(REPO / "_test_de_giong.py")],
                       cwd=str(REPO), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1200)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    goc = {f: f.read_text(encoding="utf-8") for f in (F_TG, F_TC)}
    print("=" * 78)
    print("THỬ PHÁ CỔNG 86 — mỗi phép gỡ ĐÚNG một chốt")
    print("=" * 78)
    rc0, out0 = chay_cong()
    print(f"lượt ĐỐI CHỨNG (chưa phá): mã thoát {rc0} · "
          f"{[l for l in out0.splitlines() if l.startswith('ĐẠT ')][-1:]}")
    if rc0 != 0:
        print("!! cổng ĐÃ ĐỎ trước khi phá -> sửa cổng trước, đừng đọc bảng dưới")
        return 2

    bat, lot, khong = [], [], []
    try:
        for ten, f, cu, moi, muc in PHEP:
            s = goc[f]
            if s.count(cu) != 1:
                khong.append((ten, f"tìm thấy {s.count(cu)} chỗ, phải là 1"))
                print(f"\n-- {ten}\n   KHÔNG PHÁ ĐƯỢC (LỖI CỦA PHÉP THỬ): "
                      f"tìm thấy {s.count(cu)} chỗ khớp")
                continue
            f.write_text(s.replace(cu, moi), encoding="utf-8")
            rc, out = chay_cong()
            keu = [l.strip() for l in out.splitlines()
                   if l.strip().startswith("HỎNG") and muc in l]
            tong = [l for l in out.splitlines() if l.startswith("ĐẠT ")][-1:]
            print(f"\n-- {ten}\n   mã thoát {rc} · {tong}")
            if rc != 0 and keu:
                bat.append((ten, muc))
                print(f"   BẮT: {keu[0][:150]}")
            elif rc != 0:
                # đỏ nhưng KHÔNG đỏ ở mục đang canh -> vẫn là BẮT, nhưng phải
                # nói rõ mục nào kêu, không thì lần sau đọc nhầm là mục kia hở
                h = [l.strip() for l in out.splitlines()
                     if l.strip().startswith("HỎNG")]
                bat.append((ten, f"đỏ ở mục KHÁC: {h[:2]}"))
                print(f"   BẮT (nhưng ở mục khác {muc}): {h[:2]}")
            else:
                lot.append((ten, muc))
                print(f"   LỌT — cổng VẪN XANH, mục {muc} không chịu lực")
            f.write_text(goc[f], encoding="utf-8")
    finally:
        for f, s in goc.items():
            f.write_text(s, encoding="utf-8")
        print("\n(đã phục hồi nguyên trạng cả hai file)")

    print("\n" + "=" * 78)
    print(f"BẮT {len(bat)} · LỌT {len(lot)} · KHÔNG PHÁ ĐƯỢC {len(khong)}")
    for t, m in lot:
        print(f"  LỌT: {t}  (mục {m})")
    for t, m in khong:
        print(f"  KHÔNG PHÁ ĐƯỢC: {t}  ({m})")
    rc1, out1 = chay_cong()
    print(f"lượt KIỂM LẠI sau phục hồi: mã thoát {rc1} · "
          f"{[l for l in out1.splitlines() if l.startswith('ĐẠT ')][-1:]}")
    return 0 if (not lot and not khong and rc1 == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
