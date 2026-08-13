# -*- coding: utf-8 -*-
r"""ĐO TOFU — chữ Hán mà font đang dùng KHÔNG có glyph thì ra gì?

    .venv\Scripts\python _do_tofu.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
WORK.mkdir(parents=True, exist_ok=True)
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_FFMPEG_SLOTS"] = "1"
import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF = str(REPO / "bin" / "ffmpeg.exe")
_NOWIN = 0x08000000 if os.name == "nt" else 0
FONTS = str(REPO / "app" / "assets" / "fonts")


def _esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def render(chu: str, ten: str, font: str = "Montserrat"):
    from app.core import captions
    words = [{"word": c, "start": 0.4, "end": 3.0} for c in [chu]]
    ass = WORK / f"tofu_{ten}.ass"
    ok = captions.build_ass(words, [[0.0, 4.0]], str(ass), 1080, 1920,
                            font=font, size=int(0.055 * 1920), ny=0.78,
                            preset="Trắng đơn giản", delay=0.0)
    png = WORK / f"tofu_{ten}.png"
    r = subprocess.run(
        [FF, "-y", "-loglevel", "debug", "-f", "lavfi",
         "-i", "color=c=black:s=1080x1920:d=4",
         "-vf", f"subtitles='{_esc(ass)}':fontsdir='{_esc(FONTS)}'",
         "-ss", "1.5", "-frames:v", "1", str(png)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600, creationflags=_NOWIN)
    fonts_used, thieu = [], []
    for ln in (r.stderr or "").splitlines():
        m = re.search(r"fontselect: \(.*?\) -> (\S+?),", ln)
        if m:
            fonts_used.append(m.group(1))
        m2 = re.search(r"Glyph (0x[0-9A-Fa-f]+) not found", ln)
        if m2:
            thieu.append(m2.group(1))
    import cv2
    im = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    tong = int((im >= 200).sum()) if im is not None else -1
    print(f"  [{ten}] ok_ass={ok} px={tong:6d} font={fonts_used} "
          f"glyph_thieu={thieu}")
    return tong, fonts_used, thieu


def main() -> int:
    print("Chữ Hán mà YuGothic (Nhật) KHÔNG có — 94/447 ký tự của bản chép lời:")
    ca = [
        ("co_glyph", "金属探测"),        # 金 有 (Yu Gothic có)
        ("thieu_1", "东丝为丽"),          # Yu Gothic THIẾU cả 4
        ("thieu_2", "们时查检"),
        ("thieu_3", "报现动发"),
        ("tron", "他们发现东"),
        ("latin", "ABCD"),
    ]
    for ten, chu in ca:
        print(f"\n  chữ = {chu}")
        render(chu, ten)
    return 0


if __name__ == "__main__":
    sys.exit(main())
