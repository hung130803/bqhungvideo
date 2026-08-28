# -*- coding: utf-8 -*-
"""KIỂM BỘ FILE NGHE THỬ `_NGHE_THU_ANH_HUNG/doc_cham/` — 3 điều, đo THẬT.

Vì sao phải có file này chứ không tin `chuan_do_to`: phép nghe so sánh mà hai
file lệch độ to thì tai chỉ nghe ra *"file nào TO hơn"*, không nghe ra cái đang
so. `tron_thay_giong` CÓ gọi `chuan_do_to`, nhưng đó là **cùng một bộ đo** đã
dùng để chuẩn hoá — tự chấm điểm cho mình. Nên ở đây đo lại bằng **`loudnorm`
chạy RIÊNG** (thước ĐỘC LẬP với `astats` mà app dùng).

Ba điều:
  1. **CÁC FILE ĐEM RA SO PHẢI NGANG ĐỘ TO NHAU** — cùng video + cùng máy đọc
     thì lệch nhau <= 0,5 LU, và cả bộ nằm trong dải −16..−13 LUFS.
     **CỐ Ý KHÔNG đòi đúng −14 ở mọi file.** `chuan_do_to` là NÂNG THUẦN +
     HẠN ĐỈNH, nên nguồn đã master hết chỗ trống thì nó DỪNG LẠI — đúng thiết
     kế ("clip dừng ở −21,40 là CỐ Ý, ai nới ngân sách cho đẹp bảng là đổi
     tiếng lấy con số"). Đo được: `lt1/goc.wav` I −11,91 · **TP +0,61 dBTP**
     (master vượt 0 dBTP, KHÔNG còn chỗ) -> cả 3 arm dừng ở −15,2..−15,5;
     `lt2/goc.wav` TP −0,08 -> cả 3 arm về −14,0. Lượt đo TRƯỚC trên cùng
     video `lt1` cũng ra −15,07..−15,36 (`_kq_doc_cham.json`), tức đây là
     tính chất của NGUỒN chứ không phải hồi quy.
     Thứ THẬT SỰ hỏng phép nghe là hai file **lệch nhau**, và cột đó mới là
     cột chấm.
  2. **MD5 KHÁC NHAU** — hai file trùng byte nghĩa là phép so vô nghĩa (bẫy
     cache đã sập ở bộ `adam_v2`).
  3. **Có TIẾNG và có HÌNH** — `probe_duration` > 0 + đếm khung.

    .venv\\Scripts\\python -u _kiem_nghe_cham.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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

from config import settings                              # noqa: E402
from app.core import thay_giong as tg                    # noqa: E402

NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "doc_cham"
_NW = 0x0800_0000 if os.name == "nt" else 0
DAT = HONG = 0


def ok(dieu: bool, ten: str, ct: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


def loudnorm_i(p: Path) -> tuple[float, float]:
    """(I, TP) đo bằng `loudnorm` PHA ĐO chạy RIÊNG — thước ĐỘC LẬP."""
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-hide_banner", "-nostdin", "-i", str(p),
         "-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:print_format=json",
         "-f", "null", "-"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", creationflags=_NW, timeout=900)
    m = re.findall(r"\{[^{}]*input_i[^{}]*\}", (r.stderr or ""), re.S)
    if not m:
        raise RuntimeError(f"loudnorm không in JSON cho {p.name}")
    d = json.loads(m[-1])
    return float(d["input_i"]), float(d["input_tp"])


def main() -> int:
    fs = sorted(NGHE.rglob("*.mp4"))
    if not fs:
        print(f"KHÔNG có file nào trong {NGHE} — chạy `_do_cham_that.py` trước")
        return 1
    print(f"{len(fs)} file trong {NGHE}\n")
    md5: dict = {}
    bo: dict = {}
    for p in fs:
        h = hashlib.md5(p.read_bytes()).hexdigest()
        md5.setdefault(h, []).append(p.name)
        i, tp = loudnorm_i(p)
        kh = tg.do_khung_hinh(p)
        d = tg.probe_duration(p)
        bo.setdefault(f"{p.parent.parent.name}/{p.parent.name}", []).append(
            (p.name, i))
        print(f"  {p.parent.parent.name}/{p.parent.name}/{p.name}")
        print(f"      I {i:>7.2f} LUFS · TP {tp:>6.2f} dBTP · {d:>7.2f}s · "
              f"{kh} khung · md5 {h[:10]}")
        ok(-16.0 <= i <= -13.0,
           f"  đã qua chuẩn hoá, trong dải -16..-13 LUFS · {p.name[:30]}",
           f"{i:.2f}")
        ok(d > 1.0 and kh > 10, f"  có tiếng + có hình · {p.name[:30]}",
           f"{d:.2f}s · {kh} khung")
    # CỘT CHẤM CHÍNH: các file ĐEM RA SO với nhau phải NGANG ĐỘ TO.
    for ten, v in sorted(bo.items()):
        ds = [x[1] for x in v]
        lech = max(ds) - min(ds)
        ok(lech <= 0.5,
           f"BỘ {ten}: {len(v)} file NGANG ĐỘ TO nhau (lệch <= 0,5 LU) — "
           "không thì phép nghe thành 'file nào TO hơn'",
           f"lệch {lech:.2f} LU · {min(ds):.2f}..{max(ds):.2f}")
    trung = {h: v for h, v in md5.items() if len(v) > 1}
    ok(not trung, "MD5 KHÁC NHAU ở mọi file (trùng byte = phép so vô nghĩa)",
       str(list(trung.values())[:2]) if trung else f"{len(md5)}/{len(fs)} khác")
    print(f"\nĐẠT {DAT} · HỎNG {HONG}")
    return 0 if HONG == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
