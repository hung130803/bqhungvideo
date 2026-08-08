# -*- coding: utf-8 -*-
"""ĐO CHI PHÍ THÊM VÀO ĐƯỜNG XUẤT của việc chuẩn hoá tiếng động.

Thêm 1 lệnh ffmpeg CHỈ GIẢI MÃ ÂM THANH (`_muc_nen_dB`) mỗi lượt xuất — với
200-300 kênh thì phải biết nó tốn bao nhiêu, không được đoán.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core import ffmpeg_utils as FU  # noqa: E402

kho = Path("D:/video test/Đã tải")
src = next(str(p) for p in sorted(kho.iterdir(), key=lambda q: q.stat().st_size)
           if p.suffix.lower() == ".mp4")
print("nguồn:", Path(src).name[:60])
for dur in (30, 60, 120):
    vao = ["-ss", "240", "-t", str(dur), "-i", src]
    t = time.time()
    m = FU._muc_nen_dB(vao)
    dt = time.time() - t
    print(f"  clip {dur:3d}s -> nền {m} dB · tốn {dt*1000:6.0f} ms")
p = str(FU._assets_sfx_dir() / "impact" / "boom_deep_05.opus")
t = time.time()
for _ in range(200):
    FU._muc_sfx(p)
print(f"  tra BẢNG mức SFX 200 lần: {(time.time()-t)*1000:.2f} ms "
      f"(mức {FU._muc_sfx(p)})")
