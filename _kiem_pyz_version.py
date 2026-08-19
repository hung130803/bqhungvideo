# -*- coding: utf-8 -*-
"""ĐỌC `__version__` TỪ CHÍNH FILE `.exe` — không tin `dist/` và không tin nhãn.

VÌ SAO PHẢI BÓC TỪ `.exe` CHỨ KHÔNG ĐỌC `app/version.py`:
`dist/` **VẪN CÒN bản build cũ** khi lượt build thất bại (gọi PyInstaller bằng
`.venv` là "No module named PyInstaller" mà `dist/` không bị đụng tới), nên xem
ngày sửa file hay đọc mã nguồn đều có thể ra kết luận "đã build xong" cho một
bản `.exe` của HÔM TRƯỚC. Thứ duy nhất trả lời được câu *"cái .exe NÀY mang
version nào"* là **hằng số đã biên dịch nằm trong PYZ của chính nó**.

Cách đọc: bên trong `.exe` onedir, `_internal/base_library.zip` không chứa mã
`app/`; mã `app/` nằm trong `PYZ-00.pyz`. Nhưng PYZ **không nằm rời trên đĩa** ở
bản onedir mà nhúng trong `.exe` — nên phải đi qua `CArchiveReader` để lấy nó ra,
rồi `ZlibArchiveReader` để lấy code object của `app.version`.

    .venv-build\\Scripts\\python.exe _kiem_pyz_version.py <duong_dan_exe>

Mã thoát: 0 = đọc được version · 1 = không đọc được (nói rõ vì sao).
"""
from __future__ import annotations

import marshal
import sys
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass


def _hang_so_version(code) -> list[str]:
    """Mọi chuỗi trông như số phiên bản trong code object của `app.version`.

    Quét ĐỆ QUY vào `co_consts` vì hằng số có thể nằm trong code object con.
    """
    ra: list[str] = []
    for c in getattr(code, "co_consts", ()) or ():
        if isinstance(c, str):
            p = c.strip()
            # "2.40.0" — 3 số cách nhau bằng dấu chấm
            bit = p.split(".")
            if len(bit) == 3 and all(b.isdigit() for b in bit):
                ra.append(p)
        elif hasattr(c, "co_consts"):
            ra.extend(_hang_so_version(c))
    return ra


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("THIẾU THAM SỐ: cần đường dẫn tới BQHungVideo.exe")
        return 1
    exe = Path(argv[1]).resolve()
    if not exe.is_file():
        print(f"KHÔNG CÓ FILE: {exe}")
        return 1
    print(f"exe   : {exe}")
    print(f"cỡ    : {exe.stat().st_size:,} byte")
    print(f"sửa   : {exe.stat().st_mtime}")

    try:
        from PyInstaller.archive.readers import (CArchiveReader,
                                                 ZlibArchiveReader)
    except Exception as e:  # noqa: BLE001
        print(f"KHÔNG NẠP ĐƯỢC PyInstaller.archive.readers: {e}")
        print("-> phải chạy bằng .venv-build\\Scripts\\python.exe")
        return 1

    car = CArchiveReader(str(exe))
    # Tên mục PYZ trong CArchive (thường 'PYZ-00.pyz').
    ten_pyz = [n for n in car.toc if "PYZ" in str(n).upper()]
    if not ten_pyz:
        print(f"KHÔNG THẤY MỤC PYZ trong archive. TOC có {len(car.toc)} mục.")
        return 1
    print(f"PYZ   : {ten_pyz}")

    raw = car.extract(ten_pyz[0])
    if isinstance(raw, tuple):          # bản PyInstaller cũ trả (typecode, data)
        raw = raw[1]
    tam = exe.parent / "_pyz_tam.pyz"
    tam.write_bytes(raw)
    try:
        zar = ZlibArchiveReader(str(tam))
        ten = [n for n in zar.toc if str(n) == "app.version"]
        if not ten:
            ten = [n for n in zar.toc if "version" in str(n)]
        print(f"module: {ten[:6]}")
        if not ten:
            print("KHÔNG THẤY module app.version trong PYZ")
            return 1
        dl = zar.extract("app.version")
        if isinstance(dl, tuple):
            dl = dl[1]
        code = dl if hasattr(dl, "co_consts") else marshal.loads(dl)
        vs = _hang_so_version(code)
        print(f"co_names: {[n for n in (code.co_names or ()) if 'version' in n.lower() or 'GITHUB' in n]}")
        print("=" * 60)
        if not vs:
            print("KHÔNG TÌM RA HẰNG SỐ VERSION trong app.version")
            return 1
        print(f"VERSION TRONG .EXE = {vs}")
        return 0
    finally:
        try:
            tam.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
