# -*- coding: utf-8 -*-
"""MẬT ĐỘ MỐC NEO trên 4 video THẬT của anh Hùng — ĐẦY ĐỦ, không cắt 90 giây.

`_do_chay_lien.py` đo trên đoạn 90 s đầu; mật độ cắt cảnh ở đoạn mở đầu có thể
KHÔNG đại diện cho cả phim (mở đầu hay dựng nhanh). Việc của file này là trả
lời đúng một câu: **giữa hai mốc neo là bao nhiêu giây** — vì đó là thứ quyết
định độ trôi tích luỹ được bao nhiêu trước khi bị kéo về.

Nguồn: `C:\\Users\\Admin\\Downloads\\longtieng` — **CHỈ ĐỌC**.

    .venv\\Scripts\\python -u _do_mat_do_neo.py
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

from config import settings                           # noqa: E402
from app.core import scene_detect                     # noqa: E402
from app.core import thay_giong as tg                 # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
KQ = REPO / "_kq_mat_do_neo.json"
_NW = 0x0800_0000 if os.name == "nt" else 0

IM_GOC_MOC = 0.35          # im bao lâu thì coi là "người ta ngừng nói"
NGUONG_IM_GOC_DB = -30.0


def im_dai(video: Path) -> list[tuple[float, float]]:
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-nostdin", "-i", str(video),
         "-map", "0:a:0", "-af",
         f"silencedetect=n={NGUONG_IM_GOC_DB}dB:d={IM_GOC_MOC}",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NW, timeout=1800)
    out, ra, dau = r.stderr or "", [], None
    for m in re.finditer(r"silence_(start|end):\s*(-?[\d.]+)", out):
        if m.group(1) == "start":
            dau = float(m.group(2))
        elif dau is not None:
            ra.append((dau, float(m.group(2))))
            dau = None
    return ra


def khoang(moc: list[float], tong: float) -> dict:
    """Khoảng cách GIỮA hai mốc liền nhau — con số quyết định độ trôi."""
    ms = sorted(set([0.0] + [m for m in moc if 0 < m < tong] + [tong]))
    gs = [b - a for a, b in zip(ms, ms[1:])]
    if not gs:
        return {"so": 0}
    s = sorted(gs)
    return {"so": len(moc), "moi_phut": round(len(moc) / max(0.01, tong / 60), 1),
            "cach_tb": round(statistics.fmean(gs), 2),
            "cach_trung_vi": round(statistics.median(gs), 2),
            "cach_p90": round(s[min(len(s) - 1, int(0.9 * len(s)))], 2),
            "cach_dai_nhat": round(max(gs), 2)}


def main() -> int:
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    if not vids:
        print(f"KHÔNG có .mp4 trong {NGUON_DIR}")
        return 2
    tat = []
    for p in vids:
        tong = tg.probe_duration(p)
        print(f"\n### {p.name[:52]}  ({tong:.1f}s)")
        cuts = scene_detect.detect_scenes(str(p))["cut_points"] \
            if scene_detect.is_available() else []
        ig = im_dai(p)
        im_moc = [(a + b) / 2.0 for a, b in ig]
        kc, ki = khoang(cuts, tong), khoang(im_moc, tong)
        r = {"ten": p.name, "giay": round(tong, 2), "canh": kc, "im_goc": ki,
             "im_goc_dai_nhat": round(max((b - a for a, b in ig), default=0.0), 3)}
        tat.append(r)
        print(f"  CẮT CẢNH : {kc['so']:>4} mốc · {kc['moi_phut']:>5}/phút · "
              f"cách TB {kc['cach_tb']:>5.2f}s · trung vị "
              f"{kc['cach_trung_vi']:>5.2f}s · dài nhất {kc['cach_dai_nhat']:.2f}s")
        print(f"  IM GỐC   : {ki['so']:>4} mốc · {ki['moi_phut']:>5}/phút · "
              f"cách TB {ki['cach_tb']:>5.2f}s · im dài nhất "
              f"{r['im_goc_dai_nhat']:.2f}s")
        KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"\nGhi: {KQ.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
