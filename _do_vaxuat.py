# -*- coding: utf-8 -*-
"""SO CÁC BẢN VÁ khâu xuất — đan xen + lặp 3 lượt, lấy TRUNG VỊ.

    python _do_vaxuat.py [--lap 3]

VÌ SAO ĐAN XEN: máy anh Hùng lúc nào cũng có prodown tải video nền, đo liền
mạch từng biến thể thì biến thể nào rơi đúng lúc máy bận sẽ bị oan. Chạy vòng
A,B,C - A,B,C - A,B,C rồi lấy TRUNG VỊ thì nhiễu chia đều.

Số nền đã đo (07/08/2026, lệnh dựng khung 60s, 1080p -> 1080x1920 nền mờ +
phụ đề .ass, NVENC):
  · app HIỆN TẠI chạy ffmpeg ở ưu tiên IDLE  -> ~53 CPU-giây
  · CÙNG lệnh đó ở ưu tiên THƯỜNG            -> ~35 CPU-giây  (idle tốn +50%)
  · chỉ giải mã (bỏ hết filter+encode)       -> 14,8 CPU-giây (38% tổng)
  · bỏ phụ đề .ass                           -> KHÔNG rẻ hơn (libass ~miễn phí)
  · bỏ làm mờ nền                            -> rẻ 3,6 CPU-giây
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
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

IDLE, DUOI_TB = 0x00000040, 0x00004000


def dat_input_threads(cmd: list[str], n: int) -> list[str]:
    """`-threads N` đặt TRƯỚC MỌI `-i` = giới hạn luồng GIẢI MÃ (không phải
    encode). Đặt sau -i là tham số ENCODER — nhầm chỗ này là bẫy đã sập."""
    c, ra = list(cmd), []
    i = 0
    while i < len(c):
        if c[i] == "-i":
            ra += ["-threads", str(n), "-i", c[i + 1]]
            i += 2
            continue
        ra.append(c[i])
        i += 1
    return ra


def dat_hwaccel(cmd: list[str], loai: str) -> list[str]:
    """`-hwaccel` cũng là tham số ĐẦU VÀO -> đặt trước mỗi -i."""
    c, ra = list(cmd), []
    i = 0
    while i < len(c):
        if c[i] == "-i":
            ra += ["-hwaccel", loai, "-i", c[i + 1]]
            i += 2
            continue
        ra.append(c[i])
        i += 1
    return ra


def dat_fct(cmd: list[str], n: int) -> list[str]:
    c = list(cmd)
    if "-filter_complex_threads" in c:
        c[c.index("-filter_complex_threads") + 1] = str(n)
    return c


def main() -> int:
    lap = 3
    if "--lap" in sys.argv:
        lap = int(sys.argv[sys.argv.index("--lap") + 1])
    print("═" * 76)
    print(f"SO BẢN VÁ KHÂU XUẤT — đan xen {lap} lượt, lấy TRUNG VỊ")
    print("═" * 76)
    vid = chon_video(1)
    src = vid[0]
    inf = probe(src)
    print(f"  nguồn: {Path(src).name[:54]} · {inf['w']}x{inf['h']} "
          f"{inf['fps']:.0f}fps {inf['codec']}")
    out = Path(tempfile.mkdtemp(prefix="_do_va_"))
    g = max(30.0, inf["dur"] * 0.3)
    segs = [(g, g + 30.0), (g + 70.0, g + 100.0)]
    ass = lam_ass(out, segs, 1080, 1920)
    lenh = bat_lenh(src, segs, ass, out)
    D = list(next(c for c in lenh if "-filter_complex" in " ".join(c)))
    D[-1] = str(out / "thu.mp4")

    # ---- các biến thể (tên, lệnh, cờ ưu tiên) ----
    BT = [
        ("A. app HIỆN TẠI (idle)", D, IDLE),
        ("B. chỉ đổi ưu tiên", D, DUOI_TB),
        ("C. B + giải mã GPU", dat_hwaccel(D, "cuda"), DUOI_TB),
        ("D. C + chặn luồng 2/4", dat_fct(dat_input_threads(
            dat_hwaccel(D, "cuda"), 2), 4), DUOI_TB),
        ("E. B + chặn luồng 2/4", dat_fct(dat_input_threads(D, 2), 4),
         DUOI_TB),
    ]
    print(f"  {len(BT)} biến thể × {lap} lượt = {len(BT)*lap} lượt xuất\n")

    ket: dict[str, list[dict]] = {t: [] for t, _, _ in BT}
    for k in range(lap):
        print(f"  ── vòng {k+1}/{lap} ──")
        for ten, cmd, prio in BT:
            r = _chay_prio(cmd, prio)
            ket[ten].append(r)
            print(f"    {ten:<26} {r['giay']:>6.1f}s · "
                  f"{r['cpu_giay']:>6.1f} CPU-giây · {r['luong_dinh']:>3} luồng"
                  + ("  ✗LỖI" if r["ma"] else ""))
    print()

    def tv(ten, k):
        return statistics.median([x[k] for x in ket[ten]])

    goc_cpu = tv(BT[0][0], "cpu_giay")
    goc_giay = tv(BT[0][0], "giay")
    goc_luong = tv(BT[0][0], "luong_dinh")
    print("═" * 76)
    print(f"{'biến thể':<26}{'CPU-giây':>10}{'đổi':>8}{'giây':>8}{'đổi':>8}"
          f"{'luồng':>7}{'đổi':>8}")
    print("-" * 76)
    for ten, _, _ in BT:
        c, s, l = tv(ten, "cpu_giay"), tv(ten, "giay"), tv(ten, "luong_dinh")
        print(f"{ten:<26}{c:>10.1f}{(c-goc_cpu)/goc_cpu*100:>7.0f}%"
              f"{s:>8.1f}{(s-goc_giay)/goc_giay*100:>7.0f}%"
              f"{l:>7.0f}{(l-goc_luong)/goc_luong*100:>7.0f}%")
    (REPO / "_do_luong_cache" / "vaxuat.json").write_text(
        json.dumps({t: ket[t] for t in ket}, ensure_ascii=False, indent=1),
        "utf-8")
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
