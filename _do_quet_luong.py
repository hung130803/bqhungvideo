# -*- coding: utf-8 -*-
"""QUÉT ĐIỂM NGỌT: số luồng filter/giải mã + phép nội suy + nguồn tốn CPU.

    python _do_quet_luong.py --lap 2

Sau khi biết giải mã GPU giảm 17% CPU và chặn luồng giảm 46% số luồng, cần
biết CHÍNH XÁC: (a) nên chặn ở mức nào; (b) 41 CPU-giây còn lại tiêu vào đâu.
Mỗi biến thể bóc 1 lớp -> lấy hiệu số.
"""
from __future__ import annotations

import json
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
from _do_vaxuat import dat_fct, dat_hwaccel, dat_input_threads  # noqa: E402

DUOI_TB = 0x00004000


def sua_graph(cmd: list[str], cu: str, moi: str) -> list[str]:
    c = list(cmd)
    i = c.index("-filter_complex")
    c[i] = "-filter_complex"
    c[i + 1] = c[i + 1].replace(cu, moi)
    return c


def main() -> int:
    lap = 2
    if "--lap" in sys.argv:
        lap = int(sys.argv[sys.argv.index("--lap") + 1])
    print("═" * 78)
    print(f"QUÉT ĐIỂM NGỌT — đan xen {lap} lượt")
    print("═" * 78)
    src = chon_video(1)[0]
    inf = probe(src)
    out = Path(tempfile.mkdtemp(prefix="_do_quet_"))
    g = max(30.0, inf["dur"] * 0.3)
    segs = [(g, g + 30.0), (g + 70.0, g + 100.0)]
    ass = lam_ass(out, segs, 1080, 1920)
    D = list(next(c for c in bat_lenh(src, segs, ass, out)
                  if "-filter_complex" in " ".join(c)))
    D[-1] = str(out / "thu.mp4")
    NEN = dat_hwaccel(D, "cuda")          # nền chung: giải mã GPU

    BT: list = [("gốc (fct=7, cpu decode)", D)]
    for n in (1, 2, 4, 8, 16):
        BT.append((f"gpu decode, fct={n}", dat_fct(NEN, n)))
    BT.append(("gpu, fct=4, dec_thr=2",
               dat_input_threads(dat_fct(NEN, 4), 2)))
    # bóc lớp để biết CPU tiêu vào đâu (đều trên nền gpu decode + fct=4)
    B4 = dat_fct(NEN, 4)
    BT.append(("↑ nội suy bicubic", sua_graph(B4, "flags=lanczos", "flags=bicubic")))
    BT.append(("↑ bỏ làm mờ nền", sua_graph(B4, "boxblur=5:1,", "")))
    BT.append(("↑ bỏ phụ đề .ass",
               sua_graph(B4, "subtitles=", "null#")))    # hỏng -> bỏ qua nếu lỗi

    print(f"  nguồn {inf['w']}x{inf['h']} · {len(BT)} biến thể × {lap} lượt\n")
    ket: dict[str, list] = {t: [] for t, _ in BT}
    for k in range(lap):
        print(f"  ── vòng {k+1}/{lap} ──")
        for ten, cmd in BT:
            r = _chay_prio(cmd, DUOI_TB)
            ket[ten].append(r)
            print(f"    {ten:<26}{r['giay']:>6.1f}s ·{r['cpu_giay']:>6.1f} "
                  f"CPU-giây ·{r['luong_dinh']:>3} luồng"
                  + ("  ✗LỖI" if r["ma"] else ""))
    print("\n" + "═" * 78)
    print(f"{'biến thể':<28}{'CPU-giây':>10}{'đổi':>8}{'giây':>8}{'luồng':>8}")
    print("-" * 78)
    goc = statistics.median([x["cpu_giay"] for x in ket[BT[0][0]]])
    for ten, _ in BT:
        xs = [x for x in ket[ten] if x["ma"] == 0]
        if not xs:
            print(f"{ten:<28}{'(lỗi)':>10}")
            continue
        c = statistics.median([x["cpu_giay"] for x in xs])
        s = statistics.median([x["giay"] for x in xs])
        l = statistics.median([x["luong_dinh"] for x in xs])
        print(f"{ten:<28}{c:>10.1f}{(c-goc)/goc*100:>7.0f}%{s:>8.1f}{l:>8.0f}")
    (REPO / "_do_luong_cache" / "quet.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), "utf-8")
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
