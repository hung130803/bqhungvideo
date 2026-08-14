# -*- coding: utf-8 -*-
r"""THỬ PHÁ CỔNG 54 — cổng không FAIL khi bị phá thì chỉ là con dấu.

    .venv\Scripts\python _pha_dubbing_cjk.py

Mỗi phép phá: sửa `app/core/dubbing.py` đúng 1 chỗ -> chạy `_test_dubbing_cjk`
-> đếm số mục HỎNG -> `git checkout` trả lại nguyên trạng (LUÔN trả lại, kể cả
khi cổng nổ). KHÔNG commit gì.

LƯU Ý ĐÃ SẬP 1 LẦN: file trong repo là **CRLF**, nên chuỗi tìm nhiều dòng viết
bằng `\n` KHÔNG khớp -> 4/6 phép phá lặng lẽ thành "không tìm thấy chỗ để phá"
và bản đầu của script này còn **đếm chúng vào cột LỌT** — vừa không phá được
gì vừa báo cáo sai. Nay đọc bằng universal-newline, ghi lại `\r\n`, và **KHÔNG
tìm thấy chỗ phá = LỖI CỦA PHÉP THỬ (mã 2)**, không phải kết quả.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
F = REPO / "app" / "core" / "dubbing.py"
BS = chr(92)                       # dấu gạch ngược, viết thế này cho khỏi bị
                                   # dịch mất khi copy/paste qua vỏ lệnh

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

#: (tên, chuỗi CŨ, chuỗi MỚI) — mỗi cái phá đúng một chỗ. Viết bằng "\n";
#: script tự chuẩn hoá xuống dòng trước khi tìm.
PHEP = [
    ("1977 `_phrase_groups_by_speech` trả `.split()` lại",
     "    toks = _tach_tu(text)\n    if not toks or not speech_segs:",
     '    toks = str(text or "").split()\n    if not toks or not speech_segs:'),
    ("2199 `_phrase_groups_even` trả `.split()` lại",
     "    toks = _tach_tu(text)\n    if not toks or speech_dur <= 0.05:",
     '    toks = str(text or "").split()\n'
     "    if not toks or speech_dur <= 0.05:"),
    ("2312 `_align_stt_words` trả `.split()` lại",
     "    toks = _tach_tu(script_text)\n    k = len(stt_words or [])",
     '    toks = str(script_text or "").split()\n'
     "    k = len(stt_words or [])"),
    ("`_tach_tu` gọi THẲNG `recap._word_tokens` (nuốt tiếng Hàn)",
     '    ra: list = []\n    for cum in str(text or "").split():',
     '    return _word_tokens(str(text or ""))\n'
     '    ra: list = []\n    for cum in str(text or "").split():'),
    ("`_noi_tu` gọi `captions._noi_cum` (nuốt dấu cách tiếng Hàn)",
     '    ra, truoc = "", ""',
     "    from app.core.captions import _noi_cum\n"
     "    return _noi_cum([str(x) for x in toks or []])\n"
     '    ra, truoc = "", ""'),
    ("dải regex nuốt hangul (`豈` = U+8C48 thay vì " + BS + "uF900)",
     '"' + BS + "uF900-" + BS + 'uFAFF"',
     '"' + BS + "u8C48-" + BS + 'uFAFF"'),
    ("bỏ cỡ cụm riêng cho CJK (`_co_cum` luôn trả `group`)",
     "    return (_RECAP_PHRASE_MAX_CJK if _KHONG_DAU_CACH.search(str(text "
     "or \"\"))\n            else int(group))",
     "    return int(group)"),
]


def doc() -> str:
    return io.open(F, encoding="utf-8").read()      # universal newline -> \n


def ghi(s: str) -> None:
    io.open(F, "w", encoding="utf-8", newline="\r\n").write(s)


def sach() -> bool:
    return subprocess.run(("git", "diff", "--quiet", "--", str(F)),
                          cwd=str(REPO), capture_output=True).returncode == 0


def chay(env_them: dict | None = None) -> tuple[int, int]:
    """Chạy cổng 54, trả (số ĐẠT, số HỎNG). Cổng nổ giữa chừng -> (-1, 99)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.update(env_them or {})
    r = subprocess.run(
        (str(REPO / ".venv" / "Scripts" / "python.exe"),
         str(REPO / "_test_dubbing_cjk.py")),
        cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env)
    m = re.search(r"KẾT: ĐẠT (\d+) · HỎNG (\d+)", r.stdout or "")
    return (int(m.group(1)), int(m.group(2))) if m else (-1, 99)


print("=" * 74)
print("THỬ PHÁ CỔNG 54")
print("=" * 74)
if not sach():
    print("!! `app/core/dubbing.py` đang có sửa đổi chưa commit — dừng, vì "
          "script này trả lại nguyên trạng bằng `git checkout`")
    sys.exit(2)
_da, _hong = chay()
print(f"\nnguyên trạng : ĐẠT {_da} · HỎNG {_hong}"
      f"   {'<- phải là 0' if _hong else 'OK'}")
if _hong:
    print("!! cổng đang HỎNG sẵn, dừng thử phá")
    sys.exit(2)

_ket, _loi = [], []
for ten, cu, moi in PHEP:
    try:
        s = doc()
        if cu not in s:
            print(f"\n[LỖI PHÉP THỬ] {ten}\n   không tìm thấy chỗ để phá -> "
                  "phép thử này KHÔNG kết luận được gì")
            _loi.append(ten)
            continue
        ghi(s.replace(cu, moi, 1))
        da, hong = chay()
        print(f"\n[PHÁ] {ten}\n   -> ĐẠT {da} · HỎNG {hong}"
              f"   {'cổng BẮT ĐƯỢC' if hong else '<<< CỔNG VÔ DỤNG'}")
        _ket.append((ten, hong))
    finally:
        subprocess.run(("git", "checkout", "--", str(F)), cwd=str(REPO),
                       capture_output=True)

# chốt "so nó với chính nó" (bài học cổng 36/52)
_da, _hong = chay({"BQ_MOC_DUB": "HEAD"})
print(f"\n[PHÁ] BQ_MOC_DUB=HEAD (so bản vá với CHÍNH NÓ)\n"
      f"   -> ĐẠT {_da} · HỎNG {_hong}"
      f"   {'chốt chống pass oan BẮT ĐƯỢC' if _hong else '<<< PASS OAN'}")
_ket.append(("BQ_MOC_DUB=HEAD (chốt so-với-chính-mình)", _hong))

print("\n" + "=" * 74)
_bat = sum(1 for _t, h in _ket if h)
print(f"KẾT: {_bat}/{len(_ket)} phép phá bị cổng BẮT ĐƯỢC"
      + (f" · {len(_loi)} PHÉP THỬ HỎNG" if _loi else ""))
for t, h in _ket:
    print(f"   {('BẮT ' + str(h) + ' mục') if h else 'LỌT':>12}  {t}")
for t in _loi:
    print(f"   {'THỬ HỎNG':>12}  {t}")
print(f"file sạch (git diff rỗng): {sach()}")
sys.exit(0 if (_bat == len(_ket) and not _loi and sach()) else 1)
