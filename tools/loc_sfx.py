# -*- coding: utf-8 -*-
"""DỌN + LÀM DÀY KHO TIẾNG ĐỘNG cho ĐÚNG CHẤT video thật (không phải game).

Chạy 1 lần trên máy dev:  python tools/loc_sfx.py --ghi

VÌ SAO (soi tay 06/08/2026 sau khi tải kho CC0 về): bộ lọc theo TÊN FILE khớp
đúng chữ nhưng KHÔNG nghe được chất tiếng, nên lọt vào kho:
  reveal/k_musicjingles_*      -> nhạc game 8-bit (NES/PIZZI)
  transition/k_*laser|phaser|zap -> tiếng súng laser sci-fi
  drumroll/k_*scroll|rollover  -> tiếng LĂN CHUỘT, không phải trống dồn
  sad/k_*close_*               -> tiếng ĐÓNG CỬA SỔ
  suspense/k_digitalaudio_low* -> tiếng digital, không phải drone căng
  riser/k_*powerUp*            -> tiếng game "ăn item"
Kênh của anh Hùng là crime/drama/audit người thật -> mấy tiếng trên nổ giữa
clip là HỎNG clip. Nên BỎ HẲN.

BÙ LẠI (không tải thêm gì, 0 byte tải): sinh BIẾN THỂ từ chính các file điện
ảnh tự sinh (whoosh/riser/drone/roll/note/boing) bằng cách đổi cao độ + tốc độ
+ lọc tần số -> mỗi file gốc ra 3-4 biến thể nghe khác nhau rõ, cùng chất phim.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "app" / "assets" / "sfx"
FFMPEG = str(ROOT / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0

#: mẫu tên file TẢI VỀ phải bỏ (sai chất cho video người thật)
BO = ("k_musicjingles_", "laser", "phaser", "zap", "scroll", "rollover",
      "_close_", "lowdown", "lowrandom", "lowthreetone", "powerup")

#: nhóm cần dày thêm + số file mong muốn (đủ để 300 kênh không nghe ra trùng)
CAN = {"transition": 24, "riser": 15, "suspense": 12, "drumroll": 10,
       "sad": 10, "comedy": 12, "reveal": 16, "impact": 30, "pop": 30,
       "scratch": 13}

#: biến thể: (hậu tố, chuỗi filter). asetrate đổi CAO ĐỘ + độ dài cùng lúc
#: (nghe ra hẳn tiếng khác), atempo bù lại độ dài khi cần.
BIEN_THE = [
    ("v2", "asetrate=48000*0.82,aresample=48000"),
    ("v3", "asetrate=48000*1.22,aresample=48000"),
    ("v4", "asetrate=48000*0.68,aresample=48000,highpass=f=90"),
    ("v5", "atempo=1.35,treble=g=3"),
    ("v6", "atempo=0.78,lowpass=f=6000"),
    ("v7", "asetrate=48000*1.45,aresample=48000,lowpass=f=9000"),
]


def sinh(src: Path, dst: Path, filt: str) -> bool:
    r = subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-af", f"{filt},dynaudnorm=f=100:g=5,alimiter=limit=0.9,volume=0.9",
         "-ac", "1", "-ar", "48000", "-c:a", "libopus", "-b:a", "32k",
         "-vbr", "on", "-application", "audio", str(dst)],
        capture_output=True, creationflags=_NO_WIN)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ghi", action="store_true")
    a = ap.parse_args()
    print(f"{'nhóm':12s} {'trước':>6s} {'bỏ':>4s} {'sinh':>5s} {'sau':>5s}")
    tong_bo = tong_sinh = 0
    for nhom in sorted(CAN):
        d = SFX / nhom
        if not d.exists():
            continue
        fs = sorted(d.glob("*.opus"))
        truoc = len(fs)
        bo = [f for f in fs if any(k in f.name.lower() for k in BO)]
        if a.ghi:
            for f in bo:
                f.unlink()
        con = [f for f in fs if f not in bo]
        # nguồn để nhân bản: file TỰ SINH (không có tiền tố k_) — chất điện ảnh
        goc = [f for f in con if not f.name.startswith("k_")] or con
        sinh_n = 0
        can_them = max(0, CAN[nhom] - len(con))
        if can_them and goc:
            i = 0
            for hs, filt in BIEN_THE:
                for g in goc:
                    if sinh_n >= can_them:
                        break
                    out = g.with_name(f"{g.stem}_{hs}.opus")
                    if out.exists():
                        continue
                    if a.ghi:
                        if sinh(g, out, filt):
                            sinh_n += 1
                    else:
                        sinh_n += 1
                    i += 1
                if sinh_n >= can_them:
                    break
        tong_bo += len(bo)
        tong_sinh += sinh_n
        print(f"{nhom:12s} {truoc:6d} {len(bo):4d} {sinh_n:5d} "
              f"{len(con)+sinh_n:5d}")
    fs = list(SFX.rglob("*.opus"))
    kb = sum(f.stat().st_size for f in fs) / 1024
    print(f"\nbỏ {tong_bo} file sai chất · sinh thêm {tong_sinh} biến thể "
          f"(0 byte tải)")
    print(f"kho {'sau khi dọn' if a.ghi else 'nếu dọn'}: "
          f"{len(fs) if a.ghi else '≈' + str(len(fs) - tong_bo + tong_sinh)} "
          f"file · {kb:.0f} KB")
    if not a.ghi:
        print("(xem trước — chưa sửa gì. Thêm --ghi để làm thật)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
