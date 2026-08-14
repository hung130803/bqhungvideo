# -*- coding: utf-8 -*-
"""ĐO LỖI (2): che chữ cháy sẵn CÓ CHẠY trong đường THAY TIẾNG không.

Không đo bằng mã thoát ffmpeg (bẫy "rc=0 mà chẳng che gì" đã sập nhiều lần).
Cách đo: chạy ĐÚNG hàm `thay_giong.thay_audio_video` trên video Douyin THẬT,
rồi TRÍCH KHUNG ra PNG để NGƯỜI/LLM TỰ NHÌN, kèm mật độ nét trong dải chữ.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.core import che_chu as CC          # noqa: E402
from app.core import thay_giong as TG       # noqa: E402

NGUON = Path(r"D:\claude\_do_che_chu\nguon")
SAN = Path(r"D:\claude\_do_tg")
FF = str(Path(__file__).resolve().parent / "bin" / "ffmpeg.exe")


def _chay(cmd, timeout=900):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def cat(src: Path, dst: Path, bd: float, dai: float) -> None:
    _chay([FF, "-y", "-v", "error", "-ss", f"{bd}", "-t", f"{dai}",
           "-i", str(src), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", str(dst)])


def tach_audio(src: Path, dst: Path) -> None:
    _chay([FF, "-y", "-v", "error", "-i", str(src), "-vn",
           "-c:a", "pcm_s16le", "-ar", "44100", str(dst)])


def mat_do(src: Path, d, moc: float) -> float:
    """Mật độ NÉT trong dải chữ — trên CẢ BỀ NGANG DẢI (không chỉ trong hộp).

    Đo trong hộp là tự hỏi "chỗ tôi che có sạch không" (luôn sạch); câu cần
    hỏi là "chỗ tôi BỎ RA có sót chữ không" — bài học cổng 56 CA 24.
    """
    return CC.mat_do_vung(src, d.y0, d.y1, [moc],
                          d.x0_dai or d.x0, d.x1_dai or d.x1)


def main() -> int:
    SAN.mkdir(parents=True, exist_ok=True)
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh_ep12"
    goc = NGUON / f"{ten}.mp4"
    if not goc.exists():
        print(f"KHÔNG CÓ nguồn {goc}")
        return 2

    ngan = SAN / f"{ten}_20s.mp4"
    if not ngan.exists():
        cat(goc, ngan, 6.0, 20.0)
    au = SAN / f"{ten}_au.wav"
    if not au.exists():
        tach_audio(ngan, au)

    d = CC.dai_theo_video(ngan)
    print(f"[{ten}] dò dải: có_chữ={d.co_chu} y={d.y0}..{d.y1} "
          f"x={d.x0}..{d.x1} · {d.ly_do} · số hộp={len(d.hop or [])}")
    if not d.co_chu:
        print("nguồn này không dò ra chữ -> không đo được")
        return 2

    kq = {}
    for nhan, bat in (("TAT", False), ("BAT", True)):
        ra = SAN / f"{ten}_{nhan}.mp4"
        if ra.exists():
            ra.unlink()
        log: list = []
        t0 = time.time()
        TG.thay_audio_video(ngan, au, ra, che_chu=bat,
                            che_chu_cach="mo", che_chu_muc=1.0,
                            che_chu_log=log)
        gy = time.time() - t0
        # KHÔNG tin mã thoát: kiểm bằng chính lá chắn của app
        kiem = TG.kiem_video_ra(ra, TG.probe_duration(ngan))
        mocs = [3.0, 8.0, 14.0, 18.0]
        md = [mat_do(ra, d, m) for m in mocs]
        kq[nhan] = md
        print(f"\n--- {nhan} ---  {gy:.2f}s · {kiem['khung']} khung · "
              f"{kiem['co']/1e6:.1f} MB")
        print(f"    nhật ký che: {log}")
        for m, v in zip(mocs, md):
            print(f"    mật độ nét trong dải @{m:>5.1f}s = {v:.4f}")
        for m in mocs:
            CC.trich_khung(ra, m, SAN / f"{ten}_{nhan}_{int(m)}s.png")

    print("\n===== SO SÁNH (mật độ nét trong dải chữ) =====")
    for i, m in enumerate([3.0, 8.0, 14.0, 18.0]):
        a, b = kq["TAT"][i], kq["BAT"][i]
        gi = (1 - b / a) * 100 if a > 0 else 0
        print(f"  @{m:>5.1f}s  TẮT {a:.4f} -> BẬT {b:.4f}  (giảm {gi:.1f}%)")
    print(f"\nẢnh đã trích ra {SAN} — PHẢI TỰ MỞ RA NHÌN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
