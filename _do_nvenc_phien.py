# -*- coding: utf-8 -*-
"""ĐO GIỚI HẠN SỐ PHIÊN NVENC — bẫy CHẾT NGƯỜI của kế hoạch "10 luồng cắt".

    python _do_nvenc_phien.py

VÌ SAO PHẢI ĐO: card GeForce (không phải Quadro) GIỚI HẠN số phiên encode chạy
CÙNG LÚC ở mức driver. Vượt hạn -> ffmpeg trả lỗi
"OpenEncodeSessionEx failed: out of memory" NGAY LÚC MỞ.
Hậu quả trong app HIỆN TẠI:
  1. `_run_with_fallback` thấy nvenc lỗi -> encode LẠI bằng libx264 (CPU) ->
     tốn gấp nhiều lần CPU đúng lúc máy đang tải nặng nhất;
  2. tệ hơn: `_looks_nvenc_failure` khớp "out of memory" -> ghi cache
     `_ENCODER_CACHE = libx264` -> **MỌI clip sau đó bỏ GPU chạy CPU**, và nếu
     `_looks_nvenc_env_failure` cũng khớp thì ghi ra ĐĨA, kéo dài 7 NGÀY.
Vậy "tăng lên 10 luồng cắt" có thể tự tay tắt GPU của cả app.

Cách đo: mở dần 1..12 phiên encode NVENC CÙNG LÚC (mỗi phiên 1 ffmpeg encode
video giả dài, chạy nền), phiên nào lỗi thì in log thật.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FF = str(REPO / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0


def mot_phien():
    """1 ffmpeg encode NVENC chạy dài (nguồn lavfi -> không đụng đĩa)."""
    return subprocess.Popen(
        [FF, "-y", "-v", "error", "-f", "lavfi",
         "-i", "testsrc2=s=1080x1920:r=30:d=60",
         "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19",
         "-pix_fmt", "yuv420p", "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN)


def main() -> int:
    print("═" * 68)
    print("ĐO GIỚI HẠN PHIÊN NVENC CÙNG LÚC (RTX 3060)")
    print("═" * 68)
    r = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version",
                        "--format=csv,noheader"], capture_output=True,
                       text=True, creationflags=_NO_WIN)
    print(f"  GPU: {r.stdout.strip()}")

    procs = []
    gioi_han = None
    log_loi = ""
    for n in range(1, 13):
        p = mot_phien()
        procs.append(p)
        time.sleep(2.5)                 # đủ để nó mở phiên hoặc chết
        chet = [q for q in procs if q.poll() is not None]
        if chet:
            q = chet[0]
            try:
                log_loi = (q.stdout.read() or "").strip()[:400]
            except (OSError, ValueError):
                log_loi = "(không đọc được log)"
            gioi_han = n - 1
            print(f"  phiên thứ {n}: ✗ CHẾT")
            print(f"     log: {log_loi}")
            break
        print(f"  phiên thứ {n}: ✓ đang chạy ({n} phiên song song)")
    for p in procs:
        try:
            if p.poll() is None:
                p.kill()
        except OSError:
            pass
    print()
    if gioi_han is None:
        print("  ➜ chạy được ÍT NHẤT 12 phiên NVENC cùng lúc — 10 luồng cắt AN TOÀN")
    else:
        print(f"  ➜ GIỚI HẠN = {gioi_han} phiên NVENC cùng lúc")
        print(f"     10 luồng cắt sẽ có {max(0, 10 - gioi_han)} luồng rơi về CPU")
    # bản vá app có nhận diện đúng lỗi này không?
    if log_loi:
        from app.core import ffmpeg_utils as fu
        print(f"\n  app đọc log này ra sao:")
        print(f"     _looks_nvenc_failure     = {fu._looks_nvenc_failure(log_loi)}"
              "   (True = thử lại bằng CPU cho lượt này)")
        print(f"     _looks_nvenc_env_failure = "
              f"{fu._looks_nvenc_env_failure(log_loi)}"
              "   (True = GHI ĐĨA, tắt GPU 7 NGÀY)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
