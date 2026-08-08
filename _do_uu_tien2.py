# -*- coding: utf-8 -*-
"""CHỐT câu hỏi ƯU TIÊN — đan xen 4 vòng, 3 mức, cùng 1 lệnh.

Hai lượt đo trước cho kết quả TRÁI NGƯỢC nên không được tin cái nào:
  · _do_uu_tien.py  (đo liền mạch): idle 53,1 vs thường 34,2 CPU-giây (-36%)
  · _do_vaxuat.py   (đan xen)     : idle 53,9 vs dưới-TB 53,6 (-1%)
Chỉ khác nhau ở chỗ ĐAN XEN hay không -> phải đo lại cả 3 mức TRONG CÙNG vòng.
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_SBOX = Path(tempfile.gettempdir()) / "_do_luong_sbox"
_SBOX.mkdir(exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SBOX))
os.environ.setdefault("BQ_DB_PATH", str(_SBOX / "do.db"))
os.environ.setdefault("ECO_MODE", "0")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from _do_luong_xuat import chon_video, lam_ass, probe          # noqa: E402
from _do_pha_xuat import bat_lenh                              # noqa: E402
from _do_uu_tien import _chay_prio                             # noqa: E402

MUC = [("idle (app đang dùng)", 0x40), ("dưới trung bình", 0x4000),
       ("trung bình", 0x20)]


def main() -> int:
    lap = 4
    print("═" * 66)
    print(f"CHỐT ƯU TIÊN ffmpeg — đan xen {lap} vòng × 3 mức")
    print("═" * 66)
    src = chon_video(1)[0]
    inf = probe(src)
    out = Path(tempfile.mkdtemp(prefix="_do_ut2_"))
    g = max(30.0, inf["dur"] * 0.3)
    segs = [(g, g + 30.0), (g + 70.0, g + 100.0)]
    ass = lam_ass(out, segs, 1080, 1920)
    D = list(next(c for c in bat_lenh(src, segs, ass, out)
                  if "-filter_complex" in " ".join(c)))
    D[-1] = str(out / "thu.mp4")
    ket: dict[str, list] = {t: [] for t, _ in MUC}
    for k in range(lap):
        print(f"  vòng {k+1}:", end="")
        for ten, co in MUC:
            r = _chay_prio(D, co)
            ket[ten].append(r)
            print(f"  {ten.split(' ')[0]}={r['cpu_giay']:.1f}s/{r['giay']:.1f}s",
                  end="")
        print()
    print("\n" + "═" * 66)
    print(f"{'mức ưu tiên':<24}{'CPU-giây':>12}{'giây tường':>13}{'đổi CPU':>12}")
    print("-" * 66)
    goc = statistics.median([x["cpu_giay"] for x in ket[MUC[0][0]]])
    for ten, _ in MUC:
        c = statistics.median([x["cpu_giay"] for x in ket[ten]])
        s = statistics.median([x["giay"] for x in ket[ten]])
        print(f"{ten:<24}{c:>12.1f}{s:>13.1f}{(c-goc)/goc*100:>11.0f}%")
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
