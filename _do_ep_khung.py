# -*- coding: utf-8 -*-
"""ĐO ĐÍCH DANH: `_ep_khung` ghi ra `.mp3` ĐƯỢC nhưng bị CHÍNH NÓ vứt.

Đường thật: `thay_giong.doc_nhanh_vua_khung` (bước 4c) đặt
`paths = out_dir/f"nhanh_{i:04d}.mp3"` và `rates = ["+N%"]` (N >= 1, nên
tempo LUÔN != 1.0) -> `giong_vieneu._doc_vieneu` gọi
`_ep_khung(raw.wav, nhanh_XXXX.mp3, tempo)`.

Bản vá 20/08 đã chữa **codec** (`-c:a pcm_s16le` chỉ khi đích là `.wav`),
nhưng CHỐT CUỐI vẫn là `dai_wav()` — hàm chỉ đọc được **WAV** (`wave.open`).
Nên với `.mp3`: ffmpeg rc=0, file có nội dung thật, `dai_wav` trả 0.0,
`0.0 <= 0.02` -> "Ép khung ra file 0 giây" -> **return False**.

Đo cả `giong_ngoai._ep_khung` — bản này CHƯA được vá codec.
"""
from __future__ import annotations

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)

HOP = Path(tempfile.mkdtemp(prefix="bq_do_epk_"))
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "studio.db")
(HOP / "data").mkdir(parents=True, exist_ok=True)

from config import settings                                    # noqa: E402
from app.core import giong_vieneu as VN                        # noqa: E402
from app.core import giong_ngoai as GN                         # noqa: E402


def sinh(p: Path, giay=1.5):
    subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}",
         "-ac", "1", "-ar", "24000", str(p)], capture_output=True)


def dai_that(p: Path) -> float:
    """Độ dài THẬT bằng ffprobe — thước ĐỘC LẬP với `dai_wav`."""
    r = subprocess.run(
        [settings.FFMPEG_PATH.replace("ffmpeg", "ffprobe"), "-v", "error",
         "-show_entries", "format=duration", "-of",
         "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


print("=" * 74)
print("ĐO 1 — `_ep_khung` trên ĐÚNG tên file bước 4c sinh ra")
print("=" * 74)
src = HOP / "raw.wav"
sinh(src, 1.5)
print(f"nguồn raw.wav: {src.stat().st_size} byte · {dai_that(src):.3f} s\n")

print(f"{'hàm':<14} {'đuôi':<6} {'tempo':>6} | {'trả về':>7} {'byte':>7} "
      f"{'ffprobe(s)':>11} {'dai_wav(s)':>11}")
print("-" * 74)
BANG = []
for ten, fn, dw in (("giong_vieneu", VN._ep_khung, VN.dai_wav),
                    ("giong_ngoai", GN._ep_khung, GN.dai_wav)):
    for d in (".wav", ".mp3"):
        for tempo in (1.25,):
            dst = HOP / f"{ten}_t{d}"
            if dst.exists():
                dst.unlink()
            tra = fn(src, dst, tempo)
            byte = dst.stat().st_size if dst.exists() else 0
            dt = dai_that(dst) if byte else 0.0
            dwv = dw(dst) if byte else 0.0
            BANG.append((ten, d, tra, byte, dt, dwv))
            print(f"{ten:<14} {d:<6} {tempo:>6.2f} | {str(tra):>7} {byte:>7} "
                  f"{dt:>11.3f} {dwv:>11.3f}")

print("\n>>> ĐỌC BẢNG: cột `ffprobe` là ĐỘ DÀI THẬT · cột `dai_wav` là thứ")
print("    `_ep_khung` dùng để quyết định. Dòng nào ffprobe > 0 mà trả về")
print("    False = file TỐT bị chính hàm vứt đi.")

print("\n" + "=" * 74)
print("ĐO 2 — LỜI LOG của app khi chuyện đó xảy ra")
print("=" * 74)
for ten, mod in (("giong_vieneu", VN), ("giong_ngoai", GN)):
    lg = Path(os.environ["BQ_DATA_DIR"])
    for f in list(lg.rglob("*.log")):
        try:
            f.unlink()
        except OSError:
            pass
    dst = HOP / f"log_{ten}.mp3"
    mod._ep_khung(src, dst, 1.25)
    dong = []
    for f in sorted(lg.rglob("*.log")):
        dong += [x.rstrip() for x in
                 f.read_text("utf-8", "replace").splitlines() if x.strip()]
    print(f"\n--- {ten} ---")
    for x in dong[-4:]:
        print(f"   {x}")
    if not dong:
        print("   (không có dòng log nào)")

print("\n" + "=" * 74)
print("ĐO 3 — HẬU QUẢ: `_doc_vieneu` với runner GIẢ (đọc THÀNH CÔNG 12/12)")
print("=" * 74)
# giả lập tiến trình con VieNeu: nó ĐỌC ĐƯỢC hết, ghi WAV thật ra sandbox.
N = 12
texts = [f"cau {i}" for i in range(N)]
out = HOP / "b4c"
out.mkdir(exist_ok=True)
paths_mp3 = [str(out / f"nhanh_{i:04d}.mp3") for i in range(N)]
paths_wav = [str(out / f"nhanh_{i:04d}.wav") for i in range(N)]
sb = HOP / "sandbox"
sb.mkdir(exist_ok=True)
for i in range(N):
    sinh(sb / f"c{i:04d}.wav", 1.2)


def chay_gia(*a, **kw):
    return {"ok": True, "nap": 9.8, "gen": 430.6, "sr": 24000,
            "watermark": "no", "_sandbox": "",
            "ra": [{"i": i, "p": str(sb / f"c{i:04d}.wav")}
                   for i in range(N)]}


that = VN._chay_vieneu
VN._chay_vieneu = chay_gia
try:
    for nhan, ps, rt in (
            ("bước 4c THẬT (.mp3 + rate)", paths_mp3,
             [f"+{5+i}%" for i in range(N)]),
            ("đối chứng (.wav + rate)", paths_wav,
             [f"+{5+i}%" for i in range(N)]),
            ("bước 4a (.mp3 + rate +0%)", paths_mp3, "+0%")):
        ok, _w = VN._doc(texts, ps, "vn:Adam",
                         {"co": True, "thieu": [], "python": "py"},
                         rt, "vi", False, 600, None)
        print(f"   {nhan:<28} -> ĐỌC ĐƯỢC {sum(ok)}/{N} câu")
finally:
    VN._chay_vieneu = that

print("\n" + "=" * 74)
print(f"[hộp cát] {HOP}")
shutil.rmtree(HOP, ignore_errors=True)
