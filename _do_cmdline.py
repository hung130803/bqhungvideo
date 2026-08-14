# -*- coding: utf-8 -*-
"""ĐO MỐC GÃY của DÒNG LỆNH Windows — `WinError 206` tới từ đâu.

Giả thuyết ban đầu ("đường dẫn vượt MAX_PATH 260") đã bị `_do_duong_dai.py`
BÁC BỎ: đường dài nhất trong 6 video thật của anh Hùng chỉ **183 ký tự**.

Script này thử nghi phạm thứ hai: **CreateProcess từ chối khi DÒNG LỆNH quá
32.767 ký tự** — và mã lỗi nó trả về đúng là `ERROR_FILENAME_EXCED_RANGE`
(206) "The filename or extension is too long", tên lỗi gây hiểu lầm y hệt cái
anh Hùng thấy trên màn hình.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                # noqa: BLE001
    pass

FF = str(Path(__file__).resolve().parent / "bin" / "ffmpeg.exe")


def thu(n: int) -> str:
    """Gọi ffmpeg với một tham số dài `n` ký tự -> lỗi gì."""
    cmd = [FF, "-hide_banner", "-f", "lavfi", "-i",
           "color=c=black:s=64x64:d=0.1",
           "-metadata", "comment=" + "x" * n,
           "-frames:v", "1", "-f", "null", "-"]
    tong = sum(len(c) + 3 for c in cmd)          # ước dòng lệnh sau khi trích dẫn
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=60)
        return f"cmdline~{tong:6d}  -> CHẠY ĐƯỢC (rc={p.returncode})"
    except OSError as e:
        return (f"cmdline~{tong:6d}  -> HỎNG: {type(e).__name__} "
                f"[WinError {getattr(e, 'winerror', '?')}] {e.strerror}")


def main() -> int:
    print("=" * 70)
    print("MỐC GÃY DÒNG LỆNH — gọi ffmpeg thật với tham số dài dần")
    print("=" * 70)
    for n in (1_000, 10_000, 30_000, 32_000, 32_600, 32_700, 32_760,
              33_000, 40_000, 100_000):
        print(f"  tham số {n:7d} ký tự · {thu(n)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
