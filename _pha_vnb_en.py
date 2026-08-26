# -*- coding: utf-8 -*-
"""THỬ PHÁ CA 11 của cổng 91 — mỗi phép gỡ ĐÚNG MỘT chốt, cổng phải ĐỎ.

Một cổng chỉ đáng tin khi nó **BẮT được** phép phá. Cổng xanh mà gỡ chốt vẫn
xanh thì nó là đồ trang trí — repo này đã có tiền lệ (cổng 56d/64 PASS OAN vì
mục chỉ hỏi "chuỗi có mặt không").

Mỗi lượt: sửa **một** file trong bản sao, chạy cổng, đòi nó **HỎNG >= 1**, rồi
trả file về nguyên trạng. Bản gốc được cất bằng nội dung BYTE và trả lại trong
`finally` — kể cả khi cổng nổ hay bị Ctrl-C.

CHẠY:  .venv\\Scripts\\python -u _pha_vnb_en.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
CONG = REPO / "_test_nhan_ban_da_ngu.py"

NB = REPO / "app" / "core" / "nhan_ban_giong.py"
UI = REPO / "app" / "ui" / "thay_giong_dialog.py"
DUB = REPO / "app" / "core" / "dubbing.py"
SV = REPO / "app" / "services.py"


def chay() -> tuple[int, str]:
    r = subprocess.run([PY, "-u", str(CONG)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    ra = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"KETQUA: ĐẠT (\d+) · HỎNG (\d+)", ra)
    if not m:
        return (-1, ra[-400:])
    return (int(m.group(2)), f"ĐẠT {m.group(1)} · HỎNG {m.group(2)}")


def pha(ten: str, f: Path, doi) -> bool:
    """`doi(src) -> src_moi`. Trả True nếu cổng BẮT được (HỎNG >= 1).

    **CHUẨN HOÁ XUỐNG DÒNG VỀ `\\n` TRƯỚC KHI KHỚP.** Repo này trộn `\\r\\n`
    (file cũ) với `\\n` (dòng mới thêm vào), nên một phép phá viết `"...()\\n"`
    sẽ **im lặng không khớp** ở file CRLF — và lượt trước đã có 3 mục báo
    "BỎ QUA" đúng vì thế. Ghi lại thì ghi bằng `\\n`; bản gốc vẫn được trả về
    NGUYÊN BYTE trong `finally` nên đĩa không đọng thay đổi nào.
    """
    goc = f.read_bytes()
    try:
        src = goc.decode("utf-8").replace("\r\n", "\n")
        moi = doi(src)
        if moi == src:
            print(f"  BỎ QUA {ten}: phép phá KHÔNG đổi được gì "
                  f"(mã đã khác — sửa lại phép phá, đừng bỏ mục)")
            return False
        f.write_bytes(moi.encode("utf-8"))
        hong, tom = chay()
        bat = hong >= 1
        print(f"  {'BẮT ' if bat else 'LỌT'} {ten}  [{tom}]")
        return bat
    finally:
        f.write_bytes(goc)


def main() -> int:
    print("=" * 74)
    print("THỬ PHÁ CA 11 (cổng 91) — gỡ từng chốt, cổng phải ĐỎ")
    print("=" * 74)
    hong0, tom0 = chay()
    print(f"  NỀN (chưa phá): {tom0}")
    if hong0 != 0:
        print("  DỪNG: cổng đang ĐỎ sẵn -> phép thử phá vô nghĩa")
        return 2

    kq: list[tuple[str, bool]] = []

    # 1) NỐI `goi_y_may` VÀO ĐƯỜNG ĐỌC — đúng cái "bản sửa" mà CA 11 sinh ra để
    #    chặn. Đổi máy ngay ở cửa chung: `vnb:` + tiếng khác `vi` -> `cb:`.
    def p1(s: str) -> str:
        cu = "    dung_vn, voice = _vieneu_hay_khong(voice)\n"
        moi = (
            "    if voice.startswith('vnb:') and (lang or '')[:2] not in "
            "('', 'vi'):\n"
            "        voice = 'cb:' + (lang or 'en')[:2] + '|' + voice[4:]\n"
            + cu)
        return s.replace(cu, moi, 1)
    kq.append(("1 nối `goi_y_may` vào đường đọc (đổi máy theo tiếng đích)",
               pha("1", DUB, p1)))

    # 2) XOÁ BẢNG SỐ `SO_DO_EN` -> mọi mục đọc số phải sập.
    def p2(s: str) -> str:
        # `re.escape` cho phần khai báo: `dict[str, dict[str, str]]` đầy
        # `[` `]` — để trần là chúng thành LỚP KÝ TỰ, regex không khớp gì và
        # phép phá "thành công" trong im lặng (đúng lỗi lượt chạy đầu).
        dau = re.escape("SO_DO_EN: dict[str, dict[str, str]] = {")
        return re.sub(r"\n" + dau + r".*?\n\}\n",
                      "\nSO_DO_EN: dict = {}\n", s, count=1, flags=re.S)
    kq.append(("2 xoá bảng `SO_DO_EN`", pha("2", NB, p2)))

    # 3) ĐẢO CHIỀU số của Chatterbox (17,9% -> 1,79%): mặt chữ VẪN CÓ `"17"`
    #    hay không không quan trọng — mục 11j đọc **SỐ**, nên nó phải bắt.
    #    Đây đúng phép phá đã LỌT ở cổng 56d/64 hồi quét chuỗi.
    def p3(s: str) -> str:
        return s.replace('"cb": {"cau": "17,9%"', '"cb": {"cau": "1,79%"', 1)
    kq.append(("3 đảo chiều số `cb` (17,9% -> 1,79%) — bẫy quét-chuỗi",
               pha("3", NB, p3)))

    # 4) GÕ TAY con số vào câu cảnh báo thay vì đọc bảng -> mục 11r phải bắt.
    def p4(s: str) -> str:
        return s.replace('f"nó sai chữ trong câu {cb[\'cau\']} so với '
                         '{v[\'cau\']} của VieNeu, "',
                         'f"nó sai chữ trong câu 17,9% so với 2,6-5,1% '
                         'của VieNeu, "', 1)
    kq.append(("4 gõ tay số vào câu cảnh báo (bảng thành đồ trang trí)",
               pha("4", NB, p4)))

    # 5) CẢNH BÁO KÊU OAN cả khi đích là TIẾNG VIỆT -> mục 11m phải bắt.
    def p5(s: str) -> str:
        return s.replace(
            'if not m.startswith("vnb:") or l in _NN_CUA_VIENEU:',
            'if not m.startswith("vnb:"):', 1)
    kq.append(("5 cảnh báo kêu oan khi đích là tiếng Việt", pha("5", NB, p5)))

    # 6) CẮT DÂY UI — hàm còn đó nhưng không ai gọi. Đây là **ca thứ bảy** của
    #    "hàm xong ≠ tính năng xong"; mục 11t/11v phải bắt.
    def p6(s: str) -> str:
        return s.replace("        self._ve_canh_bao_nhan_ban()\n", "", 1)
    kq.append(("6 cắt dây UI (`_ve_goi_y` thôi gọi) — hàm chết", pha("6", UI, p6)))

    # 7) ĐỔI DEDUP_KEY — 200-300 kênh xuất lại. Mục 11y phải bắt.
    def p7(s: str) -> str:
        return s.replace(
            'khoa = f"thaygiong:{duong.lower()}:{dich_sang}:{voice}"',
            'khoa = f"thaygiong:{duong.lower()}:{dich_sang}:{voice}:v2"', 1)
    kq.append(("7 đổi `dedup_key` của `enqueue_thay_giong`", pha("7", SV, p7)))

    # 8) TỰ KIỂM BỘ DÒ CỦA CHÍNH CỔNG: làm `_noi_goi_ham` đếm cả docstring +
    #    ghi chú (quay lại lối quét chuỗi) -> mục 11a phải tự bắt mình.
    def p8(s: str) -> str:
        return s.replace("    Di().visit(ast.parse(src))\n    return ra\n",
                         "    Di().visit(ast.parse(src))\n"
                         "    return ra or ([ten_ham] if ten_ham in src "
                         "else [])\n", 1)
    kq.append(("8 bộ dò quay lại quét chuỗi (docstring/ghi chú bị tính)",
               pha("8", CONG, p8)))

    print("\n" + "=" * 74)
    bat = sum(1 for _t, b in kq if b)
    print(f"KETQUA THỬ PHÁ: BẮT {bat}/{len(kq)} · LỌT {len(kq) - bat}")
    for t, b in kq:
        print(f"   {'BẮT ' if b else 'LỌT'} {t}")
    # Cổng phải trở lại XANH sau khi trả hết file — nếu không thì một phép phá
    # đã không được hoàn nguyên, và đó là chuyện nghiêm trọng hơn cả LỌT.
    h, tom = chay()
    print(f"\n  HOÀN NGUYÊN: {tom} -> "
          f"{'OK' if h == 0 else 'HỎNG — file CHƯA về nguyên trạng!'}")
    return 0 if (bat == len(kq) and h == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
