# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 72 — gỡ từng chốt, cổng PHẢI ĐỎ.

Cổng nào không tự phá được chính mình thì nó chỉ là CON DẤU. Repo này đã có
ít nhất 5 cổng ĐẠT OAN vì đúng lý do đó (cổng 36 · 47 · 51 · 56d · 64), nên
phép thử phá là bắt buộc chứ không phải cho đẹp.

    .venv\\Scripts\\python -u _pha_giong_ngoai.py

BA THỨ FILE NÀY CỐ Ý LÀM ĐÚNG (chép nguyên tắc của `_pha_xoa_nham.py`):
 1. **"KHÔNG TÌM THẤY CHỖ PHÁ" LÀ LỖI CỦA PHÉP THỬ, KHÔNG PHẢI "LỌT".** Bài
    học cổng 54: file repo là CRLF nên chuỗi nhiều dòng viết `\\n` không khớp,
    4/6 phép phá im lặng không phá được gì mà bảng còn ĐẾM VÀO CỘT LỌT = báo
    cáo NGƯỢC sự thật.
 2. **TRẢ LẠI FILE TRONG `finally`** — để lại bản đã phá trong cây mã còn tệ
    hơn không thử.
 3. Đọc `returncode` NGUYÊN VẸN, không `| tail` (nuốt mã thoát), và ép
    `PYTHONIOENCODING=utf-8` (cp1252 làm cổng chết trong 0-1 giây).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
CONG = str(REPO / "_test_giong_ngoai.py")
GN = "app/core/giong_ngoai.py"

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass


#: (nhãn, file, chuỗi TÌM, chuỗi THAY) — mỗi phép gỡ ĐÚNG MỘT chốt.
#: **Phá thì phải GỠ SẠCH chốt, đừng đổi giá trị bên trong nó** — bài học
#: "LỌT 7" của cổng 80: phép phá đổi một biến làm hàm CHẶT HƠN, cổng xanh là
#: đúng nhưng bảng đọc thành "cổng không bắt được".
PHEP = [
    (
        "1. lệnh pip bỏ cờ `--ignore-installed` (lỗi `_lib` cổng 58)",
        GN,
        '"--disable-pip-version-check", "--upgrade",\n'
        '                "--ignore-installed", "--extra-index-url", chi_muc,',
        '"--disable-pip-version-check", "--upgrade",\n'
        '                "--extra-index-url", chi_muc,',
    ),
    (
        "2. bỏ HẬU KIỂM — tin thẳng `pip trả mã 0`",
        GN,
        '        thieu = [g for g in GOI_OV if not goi[g]["venv"]]',
        '        thieu = []',
    ),
    (
        "3. cài vào `.venv` đang chạy sản xuất thay vì môi trường riêng",
        GN,
        '        args = [vpy, "-m", "pip", "install", "--no-input",',
        '        args = [sys.executable, "-m", "pip", "install", "--no-input",',
    ),
    (
        "4. bản đóng gói để môi trường CẠNH `.exe` (cổng 58 CA5)",
        GN,
        "    if getattr(sys, \"frozen\", False):\n"
        "        goc = Path(dd) if dd else Path.home()\n"
        "        return goc / \"_giong_ngoai\"",
        "    if getattr(sys, \"frozen\", False):\n"
        "        return Path(sys.executable).resolve().parent / \"_giong_ngoai\"",
    ),
    (
        "5. trả lại bẫy `Path(\"\")` (goc or Path.home() không bao giờ lùi)",
        GN,
        "        goc = Path(dd) if dd else Path.home()",
        "        goc = Path(dd or \"\") or Path.home()",
    ),
    (
        "6. bỏ chốt mã `ov:` lạ -> đọc bằng giọng MẶC ĐỊNH (chọn X ra Y)",
        GN,
        "    if not _BANG_INSTRUCT.get(voice):",
        "    if not _BANG_INSTRUCT.get(voice) and False:",
    ),
    (
        "7. trả `ov:nu_am` về câu tả CHẾT `warm low pitch`",
        GN,
        '    ("ov:nu_am",    "female, middle-aged, low pitch",',
        '    ("ov:nu_am",    "female, warm low pitch",',
    ),
    (
        "8. đặt ứng viên `%TEMP%` LÊN TRƯỚC chỗ đúng",
        GN,
        "    ds.append(thu_muc_ngoai() / \"venv\" / \"Scripts\" / \"python.exe\")\n"
        "    ds.append(thu_muc_ngoai() / \"venv\" / \"bin\" / \"python\")\n"
        "    tam = Path(tempfile.gettempdir())\n"
        "    ds.append(tam / \"bq_tts_rr\" / \"venv_ov\" / \"Scripts\" / \"python.exe\")\n"
        "    ds.append(tam / \"bq_tts_rr\" / \"venv_ov\" / \"bin\" / \"python\")",
        "    tam = Path(tempfile.gettempdir())\n"
        "    ds.append(tam / \"bq_tts_rr\" / \"venv_ov\" / \"Scripts\" / \"python.exe\")\n"
        "    ds.append(tam / \"bq_tts_rr\" / \"venv_ov\" / \"bin\" / \"python\")\n"
        "    ds.append(thu_muc_ngoai() / \"venv\" / \"Scripts\" / \"python.exe\")\n"
        "    ds.append(thu_muc_ngoai() / \"venv\" / \"bin\" / \"python\")",
    ),
    (
        "9. nhãn nút ghi 155 MB trong khi tải 2,6 GB (lỗi cũ, đổi chiều)",
        GN,
        'NHAN_TAI_GPU = ("Tải môi trường OmniVoice bản CUDA (khoảng 2,6 GB) — "',
        'NHAN_TAI_GPU = ("Tải môi trường OmniVoice bản CUDA (khoảng 155 MB) — "',
    ),
    (
        "10. bỏ khoá chống bấm-hai-lần",
        GN,
        "    if not _KHOA_CAI.acquire(blocking=False):",
        "    if False:",
    ),
]


def doc(f: str) -> str:
    with open(REPO / f, "r", encoding="utf-8", newline="") as h:
        return h.read()


def ghi(f: str, s: str) -> None:
    with open(REPO / f, "w", encoding="utf-8", newline="") as h:
        h.write(s)


def chay_cong() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        r = subprocess.run([PY, "-u", CONG], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env,
                           cwd=str(REPO), timeout=1800)
    except subprocess.TimeoutExpired:
        return 9, "(QUÁ GIỜ)"
    dong = [d for d in (r.stdout or "").splitlines() if "CỔNG 72:" in d]
    return r.returncode, (dong[-1].strip() if dong
                          else "(KHÔNG có dòng tổng kết!)")


def main() -> int:
    print("THỬ PHÁ CỔNG 72 — mỗi phép gỡ ĐÚNG một chốt\n")
    ma0, tk0 = chay_cong()
    print(f"[mốc] chưa phá: mã thoát {ma0} · {tk0}")
    if ma0 != 0:
        print("DỪNG: cổng đang ĐỎ sẵn, phép thử phá vô nghĩa.")
        return 2

    bat = lot = khong_pha = 0
    for nhan, f, tim, thay in PHEP:
        goc = doc(f)
        crlf = "\r\n" in goc
        tim_t = tim.replace("\n", "\r\n") if crlf else tim
        thay_t = thay.replace("\n", "\r\n") if crlf else thay
        if tim_t not in goc:
            khong_pha += 1
            print(f"[!!] {nhan}\n     KHÔNG PHÁ ĐƯỢC — không thấy chỗ vá trong "
                  f"{f}. ĐÂY LÀ LỖI CỦA PHÉP THỬ, không phải cổng lọt.")
            continue
        try:
            ghi(f, goc.replace(tim_t, thay_t, 1))
            ma, tk = chay_cong()
        finally:
            ghi(f, goc)                     # TRẢ LẠI, kể cả khi nổ
        if ma != 0:
            bat += 1
            print(f"[BẮT] {nhan}\n      mã thoát {ma} · {tk}")
        else:
            lot += 1
            print(f"[LỌT] {nhan}\n      mã thoát 0 — CỔNG KHÔNG BẮT ĐƯỢC · {tk}")

    ma1, tk1 = chay_cong()
    print(f"\n[mốc] sau khi trả lại: mã thoát {ma1} · {tk1}")
    print("=" * 66)
    print(f"THỬ PHÁ CỔNG 72: BẮT {bat} · LỌT {lot} · "
          f"KHÔNG PHÁ ĐƯỢC {khong_pha}")
    print("=" * 66)
    return 0 if (lot == 0 and khong_pha == 0 and ma1 == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
