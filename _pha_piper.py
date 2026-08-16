# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 64 — gỡ từng chốt ra, cổng PHẢI đỏ.

Cổng không tự kiểm thì chỉ là CON DẤU. Cổng 62 lượt trước lôi ra 3 lỗi của
CHÍNH NÓ đúng theo cách này.

HAI CỘT PHẢI TÁCH RỜI (bài học cổng 54, đã báo cáo ngược sự thật một lần):
  · **LỌT**  = phá được mà cổng vẫn xanh  -> cổng hỏng, phải sửa cổng
  · **KHÔNG PHÁ ĐƯỢC** = không tìm thấy chỗ để phá -> LỖI CỦA PHÉP THỬ,
    KHÔNG được đếm vào cột "cổng bắt được". File repo là CRLF nên chuỗi tìm
    nhiều dòng rất dễ trượt; đọc bằng chế độ văn bản (Python tự quy CRLF về
    `\\n`) rồi mới tìm.

    .venv\\Scripts\\python -u _pha_piper.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
DUB = REPO / "app" / "core" / "dubbing.py"
PIP = REPO / "app" / "core" / "piper_tts.py"

#: (tên phép phá, file, chuỗi tìm, chuỗi thay, mục cổng phải kêu)
PHEP = [
    ("gỡ nhánh Piper khỏi `_synth_all_words` (cửa CÓ mốc)", DUB,
     "        return piper_tts.doc_loat(texts, paths, on_done=on_done, rate=rate)",
     "        pass",
     "CA 4 — 3 chỗ gọi phải tới Piper"),

    ("gỡ nhánh Piper khỏi `_synth_all` (cửa KHÔNG mốc)", DUB,
     "    dung_piper, voice = _piper_hay_khong(voice)\n"
     "    if dung_piper:\n"
     "        from app.core import piper_tts\n"
     "        ok_p, _moc = piper_tts.doc_loat(texts, paths, on_done=on_done,\n"
     "                                        rate=rate, lay_moc=False)\n"
     "        return ok_p\n",
     "",
     "CA 7c — sót 1 cửa = video lẫn hai giọng"),

    ("thiếu Piper thì NÉM thay vì lùi êm", DUB,
     "    return False, lui",
     "    raise RuntimeError('chưa cài Piper')",
     "CA 3 — thiếu Piper phải lùi êm"),

    ("đưa giọng CẤM `vivos` vào app", PIP,
     'TEN_MODEL = "vi_VN-vais1000-medium"',
     'TEN_MODEL = "vi_VN-vivos-x_low"',
     "CA 2 — chỉ `vais1000`"),

    ("bỏ co giãn mốc về độ dài tiếng thật", PIP,
     "    he = dai_that / tong",
     "    he = 1.0",
     "CA 5d — mốc cuối khớp độ dài tiếng"),

    ("tra hụt chữ thì ĐOÁN BỪA một file thay vì bỏ mốc", PIP,
     "            return p\n    return None",
     "            return p\n    return next(iter(co.values()), None)",
     "CA 5f — tra hụt phải BỎ MỐC"),
]


def chay_cong() -> tuple[int, str]:
    r = subprocess.run([PY, "-u", "_test_piper.py"], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    return r.returncode, (r.stdout or "")


def main() -> int:
    print("=" * 74)
    print("THỬ PHÁ CỔNG 64 — gỡ chốt ra thì cổng PHẢI đỏ")
    print("=" * 74)

    rc0, out0 = chay_cong()
    print(f"\nMốc: cổng chưa phá -> mã thoát {rc0} "
          f"({[d for d in out0.splitlines() if d.startswith('ĐẠT ')][-1:]})")
    if rc0 != 0:
        print("  DỪNG: cổng đang ĐỎ sẵn, phá nữa thì không đọc được gì.")
        return 2

    bat = lot = khong_pha = 0
    for ten, f, tim, thay, muc in PHEP:
        goc = f.read_text(encoding="utf-8")
        if tim not in goc:
            khong_pha += 1
            print(f"\n[?] {ten}")
            print(f"    KHÔNG PHÁ ĐƯỢC — không tìm thấy chỗ phá trong "
                  f"{f.name}. Đây là LỖI CỦA PHÉP THỬ, không phải cổng đạt.")
            continue
        f.write_text(goc.replace(tim, thay, 1), encoding="utf-8", newline="\n")
        try:
            rc, out = chay_cong()
        finally:
            f.write_text(goc, encoding="utf-8", newline="\n")
        dong = [d.strip() for d in out.splitlines() if d.strip().startswith("HỎNG")]
        if rc != 0:
            bat += 1
            print(f"\n[BẮT] {ten}")
            print(f"    cổng đỏ (mã {rc}) · {len(dong)} mục hỏng · chờ: {muc}")
            for d in dong[:3]:
                print(f"      {d[:110]}")
        else:
            lot += 1
            print(f"\n[LỌT] {ten}")
            print(f"    cổng VẪN XANH -> mục «{muc}» chỉ là con dấu, phải sửa cổng")

    print("\n" + "=" * 74)
    print(f"BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha} "
          f"(trên {len(PHEP)} phép)")
    print("=" * 74)
    # `khong_pha` cũng là hỏng: phép thử không chạy thì không chứng minh gì
    return 1 if (lot or khong_pha) else 0


if __name__ == "__main__":
    raise SystemExit(main())
