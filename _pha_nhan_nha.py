"""THỬ PHÁ CỔNG 76 — gỡ từng chốt ra, cổng PHẢI đỏ.

Cổng nào không có phép thử này thì chỉ là con dấu: nó xanh vì mã đúng, hay
xanh vì nó không kiểm gì cả? Mỗi phép dưới đây gỡ ĐÚNG MỘT chốt rồi chạy lại
cổng và đọc **mã thoát thật** (không qua `| tail`, mã thoát bị nuốt).

**"KHÔNG PHÁ ĐƯỢC" LÀ LỖI CỦA PHÉP THỬ, KHÔNG PHẢI THÀNH TÍCH** — file repo là
CRLF nên chuỗi tìm nhiều dòng viết `\\n` sẽ KHÔNG khớp và phép phá âm thầm
không phá được gì (bài học cổng 54). Vì vậy cột đó tách hẳn khỏi cột LỌT.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
PY = str(REPO / ".venv" / "Scripts" / "python.exe")

#: (tên phép phá, file, chuỗi CŨ, chuỗi MỚI, mục cổng phải kêu)
PHEP = [
    ("gỡ số khỏi nhãn combo recap", "app/core/dubbing.py",
     'nn = nhan_nha.nhan(short)                        '
     "# ' - nhấn nhá 5,4 ...'\n    return (f\"   {star}{name} ({g}, đa ngữ){nn}\"",
     'nn = ""\n    return (f"   {star}{name} ({g}, đa ngữ){nn}"',
     "5a"),
    ("gỡ khoá sắp xếp theo nhấn nhá (nhóm ngôn ngữ)", "app/core/dubbing.py",
     "key=lambda v: (nhan_nha.khoa_sap(\n"
     "                                                   v[\"ShortName\"]),\n"
     "                                               v[\"ShortName\"] not in",
     "key=lambda v: (\n"
     "                                               v[\"ShortName\"] not in",
     "5c"),
    ("trả câu tả ov:nu_am về bản hỏng 'warm low pitch'",
     "app/core/giong_ngoai.py",
     '("ov:nu_am",    "female, middle-aged, low pitch"',
     '("ov:nu_am",    "female, middle-aged, warm low pitch"',
     "2a"),
    ("trả khoá Piper về tên gõ tay 'piper:vais1000'",
     "app/core/nhan_nha.py",
     '"piper:vi_VN-vais1000-medium": 3.11,',
     '"piper:vais1000": 3.11,',
     "3a/3b"),
    ("chấm ngưỡng trên SỐ THÔ (bỏ làm tròn trước)", "app/core/nhan_nha.py",
     "lam_tron = round(v, 1)\n    return f\" - nhấn nhá {lam_tron:.1f} "
     "{chu(lam_tron)}\"",
     "lam_tron = round(v, 1)\n    return f\" - nhấn nhá {lam_tron:.1f} "
     "{chu(v)}\"",
     "6a/6b"),
    ("bỏ số khỏi nhãn Piper", "app/core/piper_tts.py",
     'NHAN_GIONG = ("Giọng Việt chạy trên máy (Piper)"\n'
     '              + _nhan_nha.nhan(MA_GIONG))',
     'NHAN_GIONG = "Giọng Việt chạy trên máy (Piper)"',
     "9b"),
    ("bỏ số khỏi nhãn OmniVoice", "app/core/giong_ngoai.py",
     'return (f"{ten} (OmniVoice, 4 thứ tiếng){nhan_nha.nhan(ma)} - "',
     'return (f"{ten} (OmniVoice, 4 thứ tiếng) - "',
     "9a"),
]


def chay_cong(env_them: dict | None = None) -> tuple[int, str]:
    import os
    e = dict(os.environ)
    e.update(env_them or {})
    r = subprocess.run([PY, "-u", "_test_nhan_nha.py"], capture_output=True,
                       cwd=str(REPO), env=e, timeout=600)
    return r.returncode, r.stdout.decode("utf-8", "replace")


if __name__ == "__main__":
    rc0, out0 = chay_cong()
    print(f"CỔNG NGUYÊN VẸN: mã thoát {rc0} — "
          f"{out0.strip().splitlines()[-1] if out0.strip() else '?'}")
    if rc0 != 0:
        print("DỪNG: cổng phải XANH trước khi thử phá.")
        sys.exit(2)
    bat = lot = khong_pha = 0
    print("\n" + "=" * 72)
    for ten, f, cu, moi, muc in PHEP:
        p = REPO / f
        goc = p.read_text(encoding="utf-8")
        if cu not in goc:
            khong_pha += 1
            print(f"KHÔNG PHÁ ĐƯỢC  {ten}\n   -> không tìm thấy chỗ phá trong "
                  f"{f} (LỖI CỦA PHÉP THỬ, không phải của cổng)")
            continue
        p.write_text(goc.replace(cu, moi, 1), encoding="utf-8")
        try:
            rc, out = chay_cong()
        finally:
            p.write_text(goc, encoding="utf-8")
        dong = [x for x in out.splitlines() if x.startswith("HỎNG:")]
        if rc != 0:
            bat += 1
            print(f"BẮT  {ten}  (mong mục {muc})\n   -> mã thoát {rc} · "
                  f"{dong[0] if dong else ''}")
        else:
            lot += 1
            print(f"LỌT  {ten}  (mong mục {muc})\n   -> cổng VẪN XANH = con dấu")
    # chốt chống PASS OAN của CA 7
    rc, out = chay_cong({"BQ_MOC_REF": "HEAD"})
    dong = [x for x in out.splitlines() if x.startswith("HỎNG:")]
    if rc != 0:
        bat += 1
        print(f"BẮT  mốc đối chứng = HEAD (so nó với chính nó)\n"
              f"   -> mã thoát {rc} · {dong[0] if dong else ''}")
    else:
        lot += 1
        print("LỌT  mốc đối chứng = HEAD -> cổng VẪN XANH = tự PASS OAN")
    print("=" * 72)
    print(f"BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha}")
    sys.exit(1 if (lot or khong_pha) else 0)
