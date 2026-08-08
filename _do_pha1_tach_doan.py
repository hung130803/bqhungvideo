# -*- coding: utf-8 -*-
"""SOI PHA 1 (`_build_seg` — tách từng đoạn ra .mkv): núm luồng nào an toàn?

VÌ SAO RIÊNG FILE NÀY: lần thử 07/08/2026 thất bại ĐÚNG Ở ĐÂY — thêm
`-threads`+`-filter_threads` vào `_build_seg` cho CẢ 2 encoder rồi đo ra "chậm
3,4 lần (61,2s -> 208,3s)" nên revert. Nhưng pha 1 KHÔNG có filter nào (chỉ
-ss/-t + encode lại), nó là **giải-mã-bound**: đây là chỗ duy nhất mà giới hạn
luồng CÓ THỂ làm chậm thật. Phải đo tách riêng, và phải LOG ENCODER THỰC.

Chạy: .venv\\Scripts\\python _do_pha1_tach_doan.py
"""
from __future__ import annotations

import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

_SB = Path(tempfile.gettempdir()) / f"do_pha1_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))

sys.path.insert(0, str(Path(__file__).parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

from _do_luong_ffmpeg import _may_ranh, tim_video_nhat   # noqa: E402
from _do_nut_luong import chay_dem                       # noqa: E402

_NOWIN = 0x08000000


def main() -> int:
    ok, vi = _may_ranh()
    print(f"[máy] {vi}")
    if not ok:
        print("DỪNG: máy bận.")
        return 2
    vids = tim_video_nhat(1)
    if not vids:
        return 2
    src = vids[0]
    from config import settings
    ff = settings.FFMPEG_PATH
    out = _SB / "seg.mkv"

    def lenh(inop: list[str], encop: list[str]) -> list[str]:
        """Y HỆT `_build_seg`: -ss/-t, encode lại, ép CFR + PCM 48k stereo."""
        return [ff, "-y", *inop, "-ss", "60.000", "-t", "10.000", "-i", str(src),
                *encop, "-r", "30", "-fps_mode:v", "cfr",
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)]

    NV = ["-c:v", "h264_nvenc", "-preset", "p1", "-rc", "vbr", "-cq", "16",
          "-pix_fmt", "yuv420p"]
    X264 = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16"]
    ca = [
        ("A0. HIỆN TẠI nvenc (KHÔNG giới hạn gì)", [], NV),
        ("A1. nvenc + giải mã 4", ["-threads", "4"], NV),
        ("A2. nvenc + giải mã 2", ["-threads", "2"], NV),
        ("A3. nvenc + giải mã 1", ["-threads", "1"], NV),
        ("A4. nvenc + -threads 4 SAU -i (như lần thử trước)", [],
         NV + ["-threads", "4"]),
        ("B0. HIỆN TẠI libx264 (-threads 7 encode)", [],
         X264 + ["-threads", "7"]),
        ("B1. libx264 + giải mã 4 + encode 4", ["-threads", "4"],
         X264 + ["-threads", "4"]),
        ("B2. libx264 + giải mã 2 + encode 2", ["-threads", "2"],
         X264 + ["-threads", "2"]),
        ("B3. libx264 + giải mã 1 + encode 1", ["-threads", "1"],
         X264 + ["-threads", "1"]),
    ]
    print(f"\n{'ca':52s} {'wall':>6s} {'CPU-s':>7s} {'đỉnh':>5s} {'TB':>6s} "
          f"{'enc THỰC':>11s} {'KB':>7s}")
    ket = []
    for ten, inop, encop in ca:
        rs = [chay_dem(lenh(inop, encop)) for _ in range(3)]
        r = {k: statistics.median(x[k] for x in rs)
             for k in ("wall", "cpu", "dinh", "tb")}
        r["enc"] = rs[-1]["enc"]
        r["rc"] = max(x["rc"] for x in rs)
        kb = out.stat().st_size // 1024 if out.exists() else 0
        ket.append((ten, r))
        print(f"{ten:52s} {r['wall']:6.2f} {r['cpu']:7.2f} {int(r['dinh']):5d} "
              f"{r['tb']:6.1f} {r['enc']:>11s} {kb:7d}"
              + ("" if r["rc"] == 0 else f"  RC={r['rc']} {rs[-1]['log_cuoi']}"))
        out.unlink(missing_ok=True)

    for goc, nhom in ((0, ket[1:5]), (5, ket[6:])):
        b = ket[goc][1]
        print(f"\n=== SO VỚI {ket[goc][0]} ===")
        for ten, r in nhom:
            print(f"{ten:52s} luồng {r['dinh'] / max(1, b['dinh']):.2f}x · "
                  f"CPU {r['cpu'] / max(0.01, b['cpu']):.2f}x · "
                  f"wall {r['wall'] / max(0.01, b['wall']):.2f}x")
    ok2, vi2 = _may_ranh(3)
    print(f"\n[máy SAU khi đo] {vi2}"
          + ("" if ok2 else "  <-- CẢNH BÁO: máy đã bận, số trên có thể nhiễu"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
