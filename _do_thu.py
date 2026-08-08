# -*- coding: utf-8 -*-
"""THỬ MỘT CHUỖI FILTER BẤT KỲ trên clip thật -> in sáng/%đổi từng khung.

Dùng: python _do_thu.py "<chuỗi filter có {a} {b} {en}>" [tên]
Cửa sổ [BAT,HET] lấy từ _do_hieuung. Chạy 1 ffmpeg tại một thời điểm.
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import _do_hieuung as D  # noqa: E402

_CACHE = ROOT / "_dohu_nguon.mp4"


def lay_nguon(td: str) -> str:
    if _CACHE.exists():
        return str(_CACHE)
    p = D.nguon(td)
    import shutil
    shutil.copy2(p, _CACHE)
    return str(_CACHE)


def main() -> int:
    mau = sys.argv[1]
    ten = sys.argv[2] if len(sys.argv) > 2 else "thu"
    vk = "--vk" in sys.argv
    td = tempfile.mkdtemp(prefix="_dothu_")
    try:
        src = lay_nguon(td)
        a, b = D.BAT, D.HET
        t1, t2 = a + (b - a) / 3.0, a + (b - a) * 2 / 3.0
        ch = (mau.replace("{en}", f":enable='between(t,{a:.3f},{b:.3f})'")
                 .replace("{a}", f"{a:.3f}").replace("{b}", f"{b:.3f}")
                 .replace("{t1}", f"{t1:.3f}").replace("{t2}", f"{t2:.3f}")
                 .replace("{W}", str(D.W)).replace("{H}", str(D.H))
                 .replace("{FPS}", f"{D.FPS:g}"))
        dst = os.path.join(td, f"{ten}.mp4")
        cmd = [D.FF, "-y", "-v", "error"]
        if vk:
            cmd += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
        cmd += ["-i", src, "-an", "-vf", ch, "-c:v", "libx264", "-preset",
                "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst]
        rc, err = D.chay(cmd, 420)
        print(f"== {ten} rc={rc}\n   {ch[:250]}")
        if rc != 0:
            print("   LỖI:", err.strip()[-500:])
            return 1
        n = D.dem_khung(dst)
        s0, s1, dd = D.do_cap(src, dst, td)
        m = min(len(s0), len(s1), len(dd))
        print(f"   khung {n} (gốc {len(s0)})")
        print("   i  | sáng0 | sáng1 |  tỉ lệ | %đổi")
        for i in range(max(0, int(a * D.FPS) - 3), min(m, int(b * D.FPS) + 4)):
            print(f"  {i:4d}| {s0[i]:6.1f}| {s1[i]:6.1f}| "
                  f"{(s1[i]/s0[i] if s0[i] else 0):6.2f} | {dd[i]:6.2f}"
                  + ("  <<< ĐEN" if s0[i] > 5 and s1[i] < 0.05 * s0[i] else
                     ("  << tối" if s0[i] > 5 and s1[i] < 0.35 * s0[i] else "")))
        i0, i1 = int(a * D.FPS), int(b * D.FPS)
        tr = [dd[i] for i in range(i0 + 1, min(m, i1))]
        ng = [dd[i] for i in range(m) if i < i0 - 1 or i > i1 + 1]
        print(f"   -> TRONG max {max(tr or [0]):.2f}% · NGOÀI max "
              f"{max(ng or [0]):.2f}% · sáng thấp nhất trong cửa sổ "
              f"{min(s1[i0:i1+1] or [0]):.1f}/{min(s0[i0:i1+1] or [0]):.1f}")
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
