# -*- coding: utf-8 -*-
"""DÒ KIỂU THAM SỐ của 1 plugin frei0r — vì ffmpeg KHÔNG in bảng tham số ra.

Vì sao phải có: `frei0r=filter_params=` nhận 4 kiểu mã hoá KHÁC NHAU và đưa sai
kiểu là ffmpeg **chết cả lệnh** (`Invalid value 'X' for parameter 'Y'`) — đúng
cái bẫy mã nguồn đã ghi ở `glitch0r` ("tham số 4 là INTENSITY chứ không phải
bool -> truyền `n` làm FAIL cả lệnh"). 4 kiểu:
    double   -> `0.85`        bool -> `y` / `n`
    color    -> `0.1/0.2/0.3` position -> `0.25/0.75`
Lệnh chỉ báo tham số HỎNG ĐẦU TIÊN, nên dò TRÁI SANG PHẢI: chốt xong chỉ số i
thì lỗi tự nhảy sang i+1.

CHẠY:  .venv\\Scripts\\python _do_f0r_thamso.py <thư mục dll> <module> [<module>…]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF = str(REPO / "bin" / "ffmpeg.exe")
#: thứ tự thử: double trước (hay gặp nhất), rồi bool, màu, vị trí.
NEM = ("0.5", "n", "0.5/0.5/0.5", "0.5/0.5")
_RE = re.compile(r"Invalid value '(?P<gt>[^']*)' for parameter '(?P<ten>[^']*)'")


def _thu(mod: str, ps: list) -> tuple[bool, str, str]:
    cmd = [FF, "-y", "-v", "error", "-f", "lavfi",
           "-i", "testsrc2=s=320x240:r=25:d=0.08", "-vf",
           f"frei0r=filter_name={mod}:filter_params={'|'.join(ps)}",
           "-frames:v", "2", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       creationflags=_NOWIN, timeout=60)
    log = (r.stderr or "") + (r.stdout or "")
    m = _RE.search(log)
    if m:
        return False, m.group("ten"), m.group("gt")
    if r.returncode != 0:
        return False, "", (log.strip().splitlines() or [""])[0][:90]
    return True, "", ""


def _so_tham_so(mod: str) -> int:
    r = subprocess.run(
        [FF, "-hide_banner", "-v", "verbose", "-f", "lavfi",
         "-i", "testsrc2=s=64x64:r=25:d=0.04", "-vf",
         f"frei0r=filter_name={mod}", "-frames:v", "1", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
        creationflags=_NOWIN, timeout=60)
    m = re.search(r"num_params:(\d+)", (r.stderr or "") + (r.stdout or ""))
    return int(m.group(1)) if m else 0


#: giá trị SAI VỚI MỌI KIỂU — dùng để "đầu độc" đúng 1 chỉ số cho ffmpeg khai
#: ra TÊN của chỉ số đó. Không có mẹo này thì không biết tên nào ứng chỉ số nào
#: (lệnh chỉ báo tham số hỏng ĐẦU TIÊN, mà `0.5` lại HỢP LỆ với kiểu double nên
#: cứ đoán mò là chốt nhầm — bản đầu của file này đã sai đúng chỗ đó).
DOC = "zzz"


def do(mod: str) -> None:
    n = _so_tham_so(mod)
    if n <= 0:
        print(f"{mod:16s} : nạp không được / 0 tham số")
        return
    ps = ["0.5"] * n
    for i in range(n):
        doc = ps[:]
        doc[i] = DOC
        ok0, ten_i, _ = _thu(mod, doc)
        if ok0 or not ten_i:          # đầu độc mà vẫn chạy -> không dò được
            continue
        for nem in NEM:
            ps[i] = nem
            ok, ten_loi, _ = _thu(mod, ps)
            if ok or ten_loi != ten_i:
                break
        else:
            ps[i] = "?" + ten_i[:12]
    ok, ten_loi, gt = _thu(mod, ps)
    print(f"{mod:16s} np={n:<3d} {'|'.join(ps)}"
          f"{'' if ok else '   << CÒN LỖI: ' + ten_loi + ' = ' + gt}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    os.environ["FREI0R_PATH"] = sys.argv[1]
    for m in sys.argv[2:]:
        do(m)
