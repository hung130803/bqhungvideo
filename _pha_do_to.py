# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 65 — gỡ từng chốt ra, cổng PHẢI ĐỎ.

Cổng nào không tự kiểm được thì chỉ là CON DẤU. Phiên này đã bắt 3 ca "cổng
ĐẠT OAN vì lượt chạy chết trước khi tới chốt", nên mỗi chốt phải chứng minh
được là nó ĐANG ĐO THẬT.

**BA KẾT CỤC, KHÔNG PHẢI HAI** (bài học cổng 54): `BẮT` = cổng đỏ đúng như
phải đỏ · `LỌT` = phá được mà cổng vẫn xanh (LỖI CỦA CỔNG) · `KHÔNG PHÁ ĐƯỢC`
= không tìm thấy chỗ phá (LỖI CỦA PHÉP THỬ, KHÔNG được đếm vào cột LỌT — file
repo là CRLF nên chuỗi nhiều dòng viết `\\n` sẽ không khớp và im lặng trượt).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "Scripts" / "python.exe")

TG = REPO / "app" / "core" / "thay_giong.py"
UI = REPO / "app" / "ui" / "thay_giong_dialog.py"

#: (nhãn, file, chuỗi tìm, chuỗi thay, ca dự kiến đỏ)
PHEP = [
    ("gỡ lời gọi `chuan_do_to` khỏi `tron_thay_giong`", TG,
     "            do_to = chuan_do_to(out_wav, _tam_ch)",
     "            do_to = {}",
     "CA 8"),
    ("bỏ biên trừ hao đỉnh thật (0,5 -> 0,0)", TG,
     "BIEN_DINH_THAT_DB = 0.5",
     "BIEN_DINH_THAT_DB = 0.0",
     "CA 1 + CA 3"),
    ("đổi đích -14 -> -20 LUFS (nhỏ tiếng như cũ)", TG,
     "DICH_LUFS = -14.0",
     "DICH_LUFS = -20.0",
     "CA 1"),
    ("thay nâng-thuần bằng `loudnorm` ĐỘNG (nén dập)", TG,
     '             f"volume={can:.3f}dB,alimiter=level_in=1:level_out=1:"\n'
     '             f"limit={10.0 ** (tran_lim / 20.0):.6f}:level=0:latency=1",',
     '             f"loudnorm=I={dich}:TP={tran_tp}:LRA=11,'
     'aresample=44100",',
     "CA 3 (LRA)"),
    ("`do_do_to` nuốt lỗi, trả số 0 im lặng", TG,
     '        raise RuntimeError(f"loudnorm KHÔNG trả JSON khi đo '
     '{Path(path).name}")',
     '        return {"I": 0.0, "TP": 0.0, "LRA": 0.0, "thresh": 0.0}',
     "CA 2"),
    ("bỏ CACHE của nghe thử", TG,
     "    if dung_cache and cache.exists() and cache.stat().st_size > 1024:",
     "    if False:",
     "CA 6"),
    ("gỡ nút Nghe thử khỏi hộp", UI,
     '        self.b_nghe = QPushButton("Nghe thử")',
     '        self.b_nghe = QPushButton("Nghe thử") if False else None',
     "CA 7"),
    ("bỏ thread nền -> nghe thử CHẶN giao diện", UI,
     "        threading.Thread(target=bg, daemon=True).start()\n\n"
     "    def _ngat_tieng(self)",
     "        bg()\n\n    def _ngat_tieng(self)",
     "CA 7 (không chặn)"),
]


def main() -> int:
    goc_tg = TG.read_text(encoding="utf-8")
    goc_ui = UI.read_text(encoding="utf-8")
    bak = {TG: goc_tg, UI: goc_ui}
    bat = lot = khong_pha = 0

    print("=" * 76)
    print("THỬ PHÁ CỔNG 65 — mỗi phép PHẢI làm cổng ĐỎ")
    print("=" * 76)
    try:
        for nhan, f, tim, thay, ca in PHEP:
            noi_dung = bak[f]
            if tim not in noi_dung:
                khong_pha += 1
                print(f"\n[KHÔNG PHÁ ĐƯỢC] {nhan}\n   -> không tìm thấy chỗ "
                      f"phá trong {f.name} (LỖI CỦA PHÉP THỬ, không phải của "
                      f"cổng)")
                continue
            f.write_text(noi_dung.replace(tim, thay, 1), encoding="utf-8")
            r = subprocess.run([PY, "-u", str(REPO / "_test_do_to_nghe_thu.py")],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=1800)
            f.write_text(noi_dung, encoding="utf-8")   # trả nguyên ngay
            do = r.returncode != 0
            if do:
                bat += 1
                dong = [l for l in (r.stdout or "").splitlines()
                        if l.strip().startswith("HỎNG")]
                print(f"\n[BẮT] {nhan}\n   mã thoát {r.returncode} · dự kiến "
                      f"{ca} · {len(dong)} mục hỏng")
                for l in dong[:3]:
                    print(f"      {l.strip()}")
            else:
                lot += 1
                print(f"\n[LỌT] {nhan}\n   mã thoát 0 — CỔNG KHÔNG BẮT ĐƯỢC "
                      f"(dự kiến {ca} phải đỏ)")
    finally:
        TG.write_text(goc_tg, encoding="utf-8")
        UI.write_text(goc_ui, encoding="utf-8")
        print("\n(đã trả 2 file về nguyên trạng)")

    print("\n" + "=" * 76)
    print(f"BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha}")
    print("=" * 76)
    return 1 if (lot or khong_pha) else 0


if __name__ == "__main__":
    raise SystemExit(main())
