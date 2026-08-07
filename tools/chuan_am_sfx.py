# -*- coding: utf-8 -*-
"""CHUẨN ÂM KHO TIẾNG ĐỘNG — mọi file cùng độ to, không còn cái nghe không thấy.

VÌ SAO (đo 07/08/2026): cổng 23 đo đỉnh quanh mốc ghép ra +11,4 / +12,6 / +12,2
dB ở 3 lượt nhưng CÓ LƯỢT chỉ +4,1 dB -> tức trong kho có file nhỏ hơn hẳn.
Hệ quả với anh Hùng: cùng một cấu hình mà Part này nghe rõ tiếng, Part kia gần
như không nghe — trông như app lỗi ngẫu nhiên.

Cách làm: đo max_volume từng file (volumedetect ghi ở mức log INFO, phải dùng
`-v info` — dùng `-v error` là KHÔNG có số, bẫy đã sập 1 lần), file nào thấp hơn
`DICH` thì tăng bù đúng phần thiếu (volume=+XdB) rồi ghi lại Opus 32k mono như
cũ (giữ nguyên dung lượng kho). KHÔNG hạ file to xuống — chỉ kéo file nhỏ lên
cho bằng, nên không mất chi tiết.

    python tools/chuan_am_sfx.py --do        # chỉ ĐO, không sửa
    python tools/chuan_am_sfx.py --lam       # đo rồi CHUẨN HOÁ
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FF = str(REPO / "bin" / "ffmpeg.exe")
KHO = REPO / "app" / "assets" / "sfx"
NW = 0x08000000 if sys.platform == "win32" else 0
DICH = -3.0          # đỉnh mục tiêu (dBFS) — chừa 3 dB cho khỏi méo khi trộn
NGUONG = 1.0         # lệch dưới 1 dB thì thôi, khỏi nén lại vô ích
DUOI = (".opus", ".wav", ".ogg", ".mp3", ".m4a")


def dinh(f: Path):
    """max_volume (dBFS) của 1 file, None nếu không đo được."""
    r = subprocess.run([FF, "-v", "info", "-i", str(f), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True,
                       creationflags=NW)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr or "")
    return float(m.group(1)) if m else None


def tang(f: Path, db: float) -> bool:
    """Tăng `db` dB rồi ghi lại CHÍNH file đó (qua file tạm cho an toàn)."""
    tmp = Path(tempfile.gettempdir()) / f"sfxnorm_{os.getpid()}{f.suffix}"
    cmd = [FF, "-y", "-v", "error", "-i", str(f), "-af", f"volume={db:.2f}dB"]
    if f.suffix.lower() == ".opus":
        cmd += ["-c:a", "libopus", "-b:a", "32k", "-ac", "1"]
    cmd += [str(tmp)]
    subprocess.run(cmd, capture_output=True, creationflags=NW, timeout=120)
    if tmp.exists() and tmp.stat().st_size > 200:
        f.write_bytes(tmp.read_bytes())
        tmp.unlink(missing_ok=True)
        return True
    tmp.unlink(missing_ok=True)
    return False


ap = argparse.ArgumentParser()
ap.add_argument("--lam", action="store_true", help="thật sự chuẩn hoá")
a = ap.parse_args()

files = sorted(p for p in KHO.rglob("*") if p.suffix.lower() in DUOI)
do = [(dinh(p), p) for p in files]
co = [(v, p) for v, p in do if v is not None]
if not co:
    print("✗ không đo được file nào — kiểm bin/ffmpeg.exe")
    sys.exit(1)
co.sort(key=lambda x: x[0])
print(f"=== KHO {len(files)} file · đo được {len(co)} ===")
print(f"nhỏ nhất {co[0][0]:+.1f} dB ({co[0][1].parent.name}/{co[0][1].name})")
print(f"to nhất  {co[-1][0]:+.1f} dB ({co[-1][1].parent.name}/{co[-1][1].name})")
print(f"ĐỘ LỆCH  {co[-1][0] - co[0][0]:.1f} dB  ·  dưới -12 dB: "
      f"{sum(1 for v, _ in co if v < -12)} file")
print("\n10 file NHỎ NHẤT (nghe gần như không thấy):")
for v, p in co[:10]:
    print(f"  {v:+7.1f} dB  {p.parent.name}/{p.name}")

if not a.lam:
    print("\n(chỉ ĐO — thêm --lam để chuẩn hoá)")
    sys.exit(0)

n = 0
for v, p in co:
    thieu = DICH - v
    if thieu > NGUONG:
        if tang(p, thieu):
            n += 1
print(f"\nđã chuẩn hoá {n}/{len(co)} file lên đỉnh ~{DICH:+.0f} dB")
lai = [x for x in ((dinh(p), p) for p in files) if x[0] is not None]
lai.sort(key=lambda x: x[0])
print(f"SAU: nhỏ nhất {lai[0][0]:+.1f} dB · to nhất {lai[-1][0]:+.1f} dB · "
      f"ĐỘ LỆCH {lai[-1][0] - lai[0][0]:.1f} dB")
tong = sum(p.stat().st_size for p in files) / 1024
print(f"dung lượng kho: {tong:.0f} KB ({len(files)} file)")
