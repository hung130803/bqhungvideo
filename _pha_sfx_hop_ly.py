# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 105: gỡ ĐÚNG MỘT chốt mỗi lượt, cổng PHẢI đỏ.

Luật (bài học `_pha_doc_lan.py`): neo phải DUY NHẤT trong file, bản đã phá phải
`compile()` được — không thì đó là LỖI CỦA PHÉP THỬ, không phải "BẮT".
File gốc luôn được trả lại (finally + atexit).
"""
import atexit
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
PY = sys.executable
SC = REPO / "app" / "core" / "sfx_chon.py"
FU = REPO / "app" / "core" / "ffmpeg_utils.py"

PHA = [
    ("kiểu chỉnh màu lại kêu", SC,
     '"mau_am_diu": None,', '"mau_am_diu": "impact",'),
    ("chỗ nối liền mạch lại kêu", SC,
     'if m.get("vai") == "nối" and cat == "pop":',
     'if False and m.get("vai") == "nối" and cat == "pop":'),
    ("khoảng cách về 0,8 s", SC, "CACH_MIN = 2.0", "CACH_MIN = 0.8"),
    ("bỏ trần ngân sách", SC, "TOI_THIEU, TOI_DA = 2, 6",
     "TOI_THIEU, TOI_DA = 2, 60"),
    ("bỏ luật chuyện nặng", SC, '        if nc == "nang" and x.get("loai_diem") != "hook":',
     '        if False and nc == "nang":'),
    ("bỏ gỡ 'chết cười'", SC, '        t_nang = t_nang.replace(x, " ")',
     '        t_nang = t_nang'),
    ("dò từ bằng chuỗi con", SC,
     '        if re.search(r"[A-Za-zÀ-ỹ]", k):', '        if False:'),
    ("bỏ chống lặp HỌ", FU, "            choices = _c1 or _c2 or choices",
     "            choices = choices"),
    ("bỏ luật 3 cùng nhóm liền", SC,
     '        if (len(kq) >= 2 and kq[-1]["cat"] == c and kq[-2]["cat"] == c',
     '        if (False and len(kq) >= 2 and kq[-1]["cat"] == c'),
    ("ghép đường mới về đường cũ", FU,
     "    elif fx_whoosh and not _sfx_chon_tat():",
     "    elif fx_whoosh and False:"),
]

_goc = {p: p.read_text("utf-8") for p in (SC, FU)}


def _tra():
    for p, s in _goc.items():
        if p.read_text("utf-8") != s:
            p.write_text(s, "utf-8")


atexit.register(_tra)


def cong() -> int:
    return subprocess.run([PY, str(REPO / "_test_sfx_hop_ly.py")],
                          capture_output=True, cwd=str(REPO)).returncode


def main() -> int:
    if cong() != 0:
        print("CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ -> dừng")
        return 2
    bat = lot = khong = 0
    for ten, p, a, b in PHA:
        s = _goc[p]
        if s.count(a) != 1:
            print(f"  KHÔNG PHÁ ĐƯỢC  {ten} (neo xuất hiện {s.count(a)} lần)")
            khong += 1
            continue
        moi = s.replace(a, b)
        try:
            compile(moi, str(p), "exec")
        except SyntaxError as e:
            print(f"  KHÔNG PHÁ ĐƯỢC  {ten} (bản phá lỗi cú pháp: {e})")
            khong += 1
            continue
        try:
            p.write_text(moi, "utf-8")
            rc = cong()
        finally:
            _tra()
        if rc != 0:
            bat += 1
            print(f"  BẮT  {ten}")
        else:
            lot += 1
            print(f"  LỌT  {ten}")
    print(f"\nTHỬ PHÁ: BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong}")
    return 0 if lot == 0 and khong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
