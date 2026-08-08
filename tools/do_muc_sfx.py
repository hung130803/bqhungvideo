# -*- coding: utf-8 -*-
"""SINH BẢNG MỨC ÂM CHO KHO TIẾNG ĐỘNG -> `app/assets/sfx/muc_do.json`.

VÌ SAO PHẢI CÓ BẢNG NÀY (đo thật 08/08/2026): kho 185 file có ĐỈNH đều nhau
(0,0 .. -3,7 dBFS) nhưng mức NGHE ĐƯỢC (mean/RMS) trải **15 dB**:
    riser/riser_fast_05   mean **-3,9** dB      <- to nhất
    pop/click_02          mean **-19,1** dB     <- nhỏ nhất
Bản cũ nhân CÙNG một hệ số `volume` theo NHÓM (0,24-0,42) nên cùng một nhóm
cũng ra tiếng lúc nghe rõ lúc mất hút, và so với tiếng gốc của clip (đo -23,6
dB) thì tiếng động chỉ nhô lên **+0,7 dB** = KHÔNG NGHE THẤY. Có bảng này thì
lúc xuất tính được hệ số để tiếng động luôn cao hơn nền ĐÚNG số dB mong muốn.

Chạy 1 lần khi kho đổi:  .venv\\Scripts\\python.exe tools\\do_muc_sfx.py
Chạy TUẦN TỰ (1 ffmpeg tại một thời điểm — luật máy anh Hùng).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FF = str(ROOT / "bin" / "ffmpeg.exe")
KHO = ROOT / "app" / "assets" / "sfx"
RA = KHO / "muc_do.json"
NOWIN = 0x08000000 if os.name == "nt" else 0
DUOI = (".wav", ".opus", ".ogg", ".mp3", ".m4a")


def do(p: Path) -> tuple[float, float] | None:
    r = subprocess.run([FF, "-hide_banner", "-v", "info", "-i", str(p),
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, creationflags=NOWIN, timeout=60)
    txt = (r.stderr or b"").decode("utf-8", "replace")
    mean = mx = None
    for ln in txt.splitlines():
        if "mean_volume:" in ln:
            mean = float(ln.split("mean_volume:")[1].split("dB")[0])
        elif "max_volume:" in ln:
            mx = float(ln.split("max_volume:")[1].split("dB")[0])
    if mean is None or mx is None:
        return None
    return (mean, mx)


def main() -> int:
    bang: dict = {}
    files = sorted(p for p in KHO.rglob("*") if p.is_file()
                   and p.suffix.lower() in DUOI)
    for i, p in enumerate(files, 1):
        kq = do(p)
        if kq is None:
            print(f"  !! bỏ qua (không đo được): {p.name}")
            continue
        key = p.relative_to(KHO).as_posix()
        bang[key] = [round(kq[0], 1), round(kq[1], 1)]
        if i % 25 == 0:
            print(f"  ... {i}/{len(files)}")
    RA.write_text(json.dumps(bang, ensure_ascii=False, indent=0,
                             sort_keys=True), encoding="utf-8")
    ms = [v[0] for v in bang.values()]
    print(f"\nĐã ghi {RA} — {len(bang)} file")
    print(f"mean_volume: thấp nhất {min(ms):.1f} dB · cao nhất {max(ms):.1f} dB"
          f" · trải {max(ms)-min(ms):.1f} dB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
