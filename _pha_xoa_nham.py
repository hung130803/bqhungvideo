# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 80 — gỡ từng chốt, cổng PHẢI ĐỎ.

Cổng nào không tự phá được chính mình thì nó chỉ là CON DẤU. Repo này đã có
ít nhất 5 cổng ĐẠT OAN vì lý do đó (cổng 36 · 47 · 51 · 56d · 64) nên phép
thử phá là bắt buộc, không phải cho đẹp.

MỖI PHÉP PHÁ GỠ ĐÚNG MỘT CHỐT rồi trả lại nguyên trạng. Chạy:

    .venv\\Scripts\\python -u _pha_xoa_nham.py

BA THỨ FILE NÀY CỐ Ý LÀM ĐÚNG:
 1. **"KHÔNG TÌM THẤY CHỖ PHÁ" LÀ LỖI CỦA PHÉP THỬ, KHÔNG PHẢI "LỌT".** Bài
    học cổng 54: file repo là CRLF nên chuỗi nhiều dòng viết `\\n` không khớp,
    4/6 phép phá im lặng không phá được gì mà bản đầu còn ĐẾM VÀO CỘT LỌT =
    báo cáo ngược sự thật. Nay đọc file với `newline=""` (giữ nguyên xuống
    dòng) và tách hẳn cột `KHÔNG PHÁ ĐƯỢC`.
 2. **TRẢ LẠI FILE TRONG `finally`**, kể cả khi bị Ctrl-C: để lại bản đã phá
    trong cây mã còn tệ hơn không thử.
 3. Chạy cổng bằng `subprocess` rồi đọc `returncode` NGUYÊN VẸN — không
    `| tail` (nuốt mã thoát) và ép `PYTHONIOENCODING=utf-8` (cp1252).
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
CONG = str(REPO / "_test_khong_xoa_nham.py")

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


#: (nhãn, file, chuỗi TÌM, chuỗi THAY) — mỗi phép gỡ ĐÚNG một chốt.
PHEP = [
    (
        "1. services.delete_project trở về `rmtree(pdir)` trần",
        "app/services.py",
        "    if pdir is not None:\n"
        "        from app.core.xoa_an_toan import don_thu_muc\n"
        "        don_thu_muc(pdir)",
        "    if pdir and pdir.exists():\n"
        "        import shutil as _sh\n"
        "        _sh.rmtree(pdir, ignore_errors=True)",
    ),
    (
        "2. jobs._don_thu_muc_tam trở về `isdir()` + rmtree trần",
        "app/queue/jobs.py",
        "    from app.core.xoa_an_toan import don_thu_muc\n"
        "\n"
        "    don_thu_muc(payload.get(\"thu_muc_lam\"))",
        "    import shutil\n"
        "\n"
        "    lam = str(payload.get(\"thu_muc_lam\") or \"\")\n"
        "    if lam and os.path.isdir(lam):\n"
        "        shutil.rmtree(lam, ignore_errors=True)",
    ),
    (
        "3. piper_tts._don trở về rmtree TRẦN",
        "app/core/piper_tts.py",
        "    from app.core.xoa_an_toan import don_thu_muc\n"
        "    don_thu_muc(d, ghi_log=_ghi_log, ten_bat_dau=\"_piper_\")",
        "    try:\n"
        "        import shutil\n"
        "        shutil.rmtree(d, ignore_errors=True)\n"
        "    except Exception:  # noqa: BLE001\n"
        "        pass",
    ),
    (
        "4. tempsweep._xoa bỏ chốt `ly_do_cam`",
        "app/core/tempsweep.py",
        "    from app.core.xoa_an_toan import ly_do_cam\n"
        "    if ly_do_cam(p):\n"
        "        return 0\n",
        "",
    ),
    (
        "5. xoa_an_toan GỠ CHỐT 'thư mục đang làm việc' (chốt cứu cây mã)",
        "app/core/xoa_an_toan.py",
        "        if p == cwd:\n"
        "            return \"THƯ MỤC ĐANG LÀM VIỆC: \" + str(p)\n"
        "        if p in cwd.parents:\n"
        "            return \"thư mục CHA của thư mục đang làm việc: \" + str(p)",
        "        pass",
    ),
    (
        "6. xoa_an_toan GỠ CHỐT 'gốc ổ đĩa'",
        "app/core/xoa_an_toan.py",
        "    if p.parent == p or str(p) == p.anchor:\n"
        "        return \"GỐC Ổ ĐĨA: \" + str(p)",
        "    pass",
    ),
    (
        # BẢN ĐẦU CỦA PHÉP NÀY SAI VÀ BỊ ĐẾM THÀNH "LỌT" — ghi lại để đừng
        # lặp: nó đổi `goc` thành một đường dẫn không bao giờ khớp, mà mệnh đề
        # là `if p == goc or goc not in p.parents: return` -> vế hai LUÔN
        # ĐÚNG -> `_don` TỪ CHỐI MỌI THỨ, tức phép "phá" làm hàm CHẶT HƠN chứ
        # không hở ra. Cổng xanh là ĐÚNG, nhưng bảng lại đọc thành "cổng không
        # bắt được". Phá thì phải GỠ SẠCH chốt, đừng đổi giá trị bên trong nó.
        "7. giong_ngoai._don gỡ SẠCH chốt (đúng bản trước b5bd003)",
        "app/core/giong_ngoai.py",
        "        if d is None or not str(d).strip():\n"
        "            return\n"
        "        p = Path(d).resolve()\n"
        "        goc = thu_muc_ngoai().resolve()\n"
        "        # `p == goc` cũng CẤM: hộp cát là thư mục CON, xoá cả gốc là"
        " xoá luôn\n"
        "        # môi trường 7,7 GB.\n"
        "        if p == goc or goc not in p.parents:\n"
        "            _ghi_log(f\"TỪ CHỐI dọn {p} — nằm ngoài {goc}\")\n"
        "            return\n",
        "        p = Path(d)\n",
    ),
]

# `app/core/giong_vieneu.py` CỐ Ý KHÔNG có phép phá: hai luồng khác đang sửa
# file đó (19/08/2026). Phép phá ghi đè file rồi trả lại, mà lượt chạy này ĐÃ
# TỪNG bị giết giữa chừng — giết đúng lúc đó là để lại bản đã phá trong file
# của người khác. Cổng 80 vẫn CHẤM `giong_vieneu._don` (đọc-only, CA 3 và 4).


def doc(f: str) -> str:
    return io.open(REPO / f, encoding="utf-8", newline="").read()


def ghi(f: str, s: str) -> None:
    io.open(REPO / f, "w", encoding="utf-8", newline="").write(s)


def chay_cong() -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run([PY, "-u", CONG], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env,
                       cwd=str(REPO.parent), timeout=900)
    dong = [d for d in (r.stdout or "").splitlines() if "TỔNG KẾT" in d]
    return r.returncode, (dong[-1] if dong else "(KHÔNG có dòng tổng kết!)")


def main() -> int:
    print("THỬ PHÁ CỔNG 80 — mỗi phép gỡ ĐÚNG một chốt\n")
    ma0, tk0 = chay_cong()
    print(f"[mốc] chưa phá: mã thoát {ma0} · {tk0}")
    if ma0 != 0:
        print("DỪNG: cổng đang ĐỎ sẵn, phép thử phá vô nghĩa.")
        return 2

    bat = lot = khong_pha = 0
    for nhan, f, tim, thay in PHEP:
        goc = doc(f)
        # File repo là CRLF -> chuỗi tìm viết \n phải đổi cho khớp.
        tim_thuc = tim.replace("\n", "\r\n") if "\r\n" in goc else tim
        thay_thuc = thay.replace("\n", "\r\n") if "\r\n" in goc else thay
        if tim_thuc not in goc:
            khong_pha += 1
            print(f"[!!] {nhan}\n     KHÔNG PHÁ ĐƯỢC — không tìm thấy chỗ vá "
                  f"trong {f}. ĐÂY LÀ LỖI CỦA PHÉP THỬ, không phải cổng lọt.")
            continue
        try:
            ghi(f, goc.replace(tim_thuc, thay_thuc, 1))
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
    print("=" * 62)
    print(f"THỬ PHÁ: BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha}")
    print("=" * 62)
    return 0 if (lot == 0 and khong_pha == 0 and ma1 == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
