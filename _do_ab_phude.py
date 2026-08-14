# -*- coding: utf-8 -*-
r"""A/B NHÌN ĐƯỢC — phụ đề tiếng Trung TRƯỚC và SAU bản vá gom chữ Hán.

    .venv\Scripts\python _do_ab_phude.py

Dựng .ass bằng HAI bản mã (bản mốc = CHA của commit đưa `_gom_cjk` vào, và bản
NAY) từ CÙNG một bản chép lời Groq thật, CÙNG timeline, rồi đốt lên CÙNG một
khung phim THẬT của anh Hùng. Xuất 2 ảnh PNG để mở bằng mắt.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
OUT = WORK / "ab"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(WORK / "settings.ini")
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
NGUON = Path(r"C:\Users\Admin\Downloads\Video") / (
    "一只手表牵扯出一个巨大的秘密 #我的观影报告 #电影解说 #悬疑电影.mp4")
W, H = 1080, 1920
MOC = 12.0          # giây trên timeline ĐẦU RA = timeline nguồn (segs 0..30)


def _esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def _nap_moc():
    m = os.environ.get("BQ_MOC_REF", "")
    if not m:
        r = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H",
                            "--reverse", "-S", "_gom_cjk", "--",
                            "app/core/captions.py"], capture_output=True)
        ds = (r.stdout or b"").decode().split()
        m = f"{ds[0]}^" if ds else "HEAD"
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        f"{m}:app/core/captions.py"], capture_output=True)
    nay = (REPO / "app" / "core" / "captions.py").read_bytes()
    if r.returncode != 0 or r.stdout.strip() == nay.strip():
        print(f"DỪNG: mốc `{m[:12]}` trùng bản đang test -> A/B vô nghĩa.")
        return None, m
    f = OUT / "captions_cu.py"
    f.write_bytes(r.stdout)
    spec = importlib.util.spec_from_file_location("captions_cu", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)   # type: ignore
    return mod, m


def main() -> int:
    tj = WORK / "trung_transcript.json"
    if not tj.exists():
        print("DỪNG: chưa có bản chép lời (chạy _do_trung.py trước).")
        return 2
    if not NGUON.exists():
        print(f"DỪNG: không thấy nguồn {NGUON}")
        return 2
    tr = json.loads(tj.read_text(encoding="utf-8"))
    words = tr.get("words") or []
    print(f"[nguồn] {NGUON.name}")
    print(f"[chép lời] {len(words)} mốc-từ · "
          f"{sum(1 for w in words if len(str(w.get('word', '')).strip()) == 1)}"
          " mốc chỉ 1 KÝ TỰ")

    from app.core import captions as C
    CU, moc = _nap_moc()
    if CU is None:
        return 2
    print(f"[mốc đối chứng] {moc[:12]} (bản TRƯỚC khi sửa)")

    ket = {}
    for nhan, mod in (("TRUOC", CU), ("SAU", C)):
        ass = OUT / f"{nhan}.ass"
        ok = mod.build_ass(words, [[0.0, 30.0]], str(ass), W, H,
                           font="Montserrat", size=int(0.055 * H), ny=0.78,
                           preset="Trắng đơn giản", delay=0.0)
        txt = ass.read_text(encoding="utf-8")
        dl = [ln for ln in txt.splitlines() if ln.startswith("Dialogue:")]
        style = [ln for ln in txt.splitlines()
                 if ln.startswith("Style: Default")][0]
        png = OUT / f"{nhan}.png"
        r = subprocess.run(
            [FF, "-y", "-v", "error", "-ss", f"{MOC:g}", "-i", str(NGUON),
             # nguồn 1280x720 -> dựng khung dọc 1080x1920 giống app: video vừa
             # bề ngang, nền đen trên/dưới (đủ để NHÌN chữ, không cần blur).
             "-vf", (f"scale={W}:-2,pad={W}:{H}:0:(oh-ih)/2:black,"
                     f"subtitles='{_esc(ass)}':fontsdir='{_esc(FONTS)}'"),
             "-frames:v", "1", str(png)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=900, creationflags=_NOWIN)
        # chữ đang hiện tại mốc MOC
        hien = ""
        for ln in dl:
            c = ln.split(",", 9)
            a = sum(x * y for x, y in zip(
                [3600, 60, 1], [float(v) for v in c[1].split(":")]))
            b = sum(x * y for x, y in zip(
                [3600, 60, 1], [float(v) for v in c[2].split(":")]))
            if a <= MOC < b:
                hien = re.sub(r"\{[^}]*\}", "", c[9])
        crop = OUT / f"{nhan}_vungchu.png"
        subprocess.run(
            [FF, "-y", "-v", "error", "-i", str(png),
             "-vf", "crop=1080:260:0:1400"],
            capture_output=True, timeout=300, creationflags=_NOWIN)
        subprocess.run(
            [FF, "-y", "-v", "error", "-i", str(png),
             "-vf", "crop=1080:260:0:1400", str(crop)],
            capture_output=True, timeout=300, creationflags=_NOWIN)
        print(f"\n  ── {nhan} ──  build_ass={ok} · ffmpeg rc={r.returncode}")
        print(f"     Style: {style[:80]}")
        print(f"     {len(dl)} dòng Dialogue trong 30 giây "
              f"= {30.0/max(1,len(dl)):.3f} giây/dòng")
        print(f"     chữ hiện tại giây {MOC:g}: «{hien}» ({len(hien)} ký tự)")
        print(f"     ảnh: {png}\n     vùng chữ: {crop}")
        ket[nhan] = (len(dl), hien)

    a, b = ket["TRUOC"], ket["SAU"]
    print(f"\n  KẾT: {a[0]} dòng -> {b[0]} dòng · «{a[1]}» -> «{b[1]}»")
    return 0


if __name__ == "__main__":
    sys.exit(main())
