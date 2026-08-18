"""MỎ NEO SỰ THẬT: phụ đề CHÁY SẴN của người kể.

4 video Douyin "giải thích phim" đều đốt phụ đề cho lời NGƯỜI KỂ vào khung.
Đoạn nào có chữ trong dải phụ đề = người kể; dải TRỐNG = tiếng của chính bộ
phim (người thật trong khung / nhạc / tiếng hò).

Đây là mỏ neo ĐỘC LẬP với cả 2 tín hiệu sẽ đem đi thi (LLM đọc bản chép lời ·
đặc trưng giọng ECAPA) nên dùng làm bộ đối chứng được. Số ở đây chỉ để XẾP
THỨ TỰ việc soi bằng MẮT — nhãn cuối cùng do tôi tự nhìn khung mà ghi.

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_phude.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = GOC / "_kq_nn"
FF = str(GOC / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0
TEN = ("v1_dutu", "v2_nieu", "v3_8daodien", "v4_khuyendung")


def _khung_gray(video: str, t: float, y0: int, y1: int, W: int):
    """Đọc DẢI phụ đề của 1 khung ở giây `t` ra ma trận gray (numpy)."""
    import numpy as np
    h = y1 - y0
    if h <= 0:
        return None
    r = subprocess.run(
        [FF, "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
         "-vf", f"crop={W}:{h}:0:{y0},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, creationflags=_NO_WIN, timeout=120)
    if r.returncode != 0 or len(r.stdout) < W * h:
        return None
    return np.frombuffer(r.stdout[:W * h], dtype=np.uint8).reshape(h, W)


def main() -> None:
    from app.core import che_chu as cc

    ket = {}
    for ten in TEN:
        video = str(SAN / "video" / f"{ten}.mp4")
        d = json.loads((SAN / f"chep_{ten}.json").read_text(encoding="utf-8"))
        cau = d["cau"]

        dai = cc.do_dai_chu(video)
        tt = cc.thong_tin(video)
        W, H = tt["rong"], tt["cao"]
        print(f"== {ten}  {W}x{H}  co_chu={dai.co_chu} "
              f"y {dai.y0}-{dai.y1}  mat_do={dai.mat_do:.4f} "
              f"nen={dai.mat_do_nen:.4f}  {dai.ly_do}")
        if not dai.co_chu:
            print("   KHONG DO RA DAI CHU -> bo qua video nay")
            continue

        rows = []
        for i, c in enumerate(cau):
            t = (float(c["start"]) + float(c["end"])) / 2.0
            g = _khung_gray(video, t, dai.y0, dai.y1, W)
            if g is None:
                rows.append({"i": i, "t": round(t, 2), "md": None})
                continue
            m = cc._mat_na(g)
            md = float(m.mean())
            # bề ngang phần có mực: chữ phụ đề nằm giữa, chiếm dải rộng
            colsum = m.mean(axis=0)
            co = float((colsum > 0.02).mean())
            rows.append({"i": i, "t": round(t, 2), "md": round(md, 5),
                         "rong": round(co, 4),
                         "start": c["start"], "end": c["end"],
                         "text": c["text"][:60]})
        ket[ten] = {"y0": dai.y0, "y1": dai.y1, "W": W, "H": H,
                    "mat_do_dai": dai.mat_do, "rows": rows}
        mds = sorted(r["md"] for r in rows if r["md"] is not None)
        n = len(mds)
        print(f"   {n} doan | mat do: min {mds[0]:.5f} "
              f"| 10% {mds[n // 10]:.5f} | trung vi {mds[n // 2]:.5f} "
              f"| max {mds[-1]:.5f}")

    (SAN / "phude.json").write_text(json.dumps(ket, ensure_ascii=False),
                                    encoding="utf-8")
    print("GHI: _kq_nn/phude.json")


if __name__ == "__main__":
    main()
