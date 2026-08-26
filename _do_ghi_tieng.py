# -*- coding: utf-8 -*-
"""ĐO CẢ LỚP BỆNH: hàm nào ghi file tiếng ra `paths[i]` (đuôi `.mp3`)?

Mọi cửa `dubbing._synth_all` / `_synth_all_words` đều nhận `paths` đuôi
**`.mp3`** (`thay_giong.doc_ban_dich` · `rut_gon_vua_khung` ·
`doc_nhanh_vua_khung` đều đặt `.mp3`; `dubbing` cũng vậy). Mỗi bộ giọng
chạy-trên-máy có một hàm ghi ra đúng đường dẫn đó — script này gọi THẬT
từng hàm với đích `.mp3` rồi đối chiếu:
  · file có nội dung THẬT không (ffprobe, thước ĐỘC LẬP)
  · hàm TRẢ VỀ gì

Dòng nào `ffprobe > 0` mà hàm trả `False` = **file tốt bị chính hàm vứt**.
Dòng nào `ffprobe = 0` = ffmpeg không ghi được gì (codec sai container).
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

HOP = Path(tempfile.mkdtemp(prefix="bq_do_ghitieng_"))
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "studio.db")
(HOP / "data").mkdir(parents=True, exist_ok=True)

from config import settings                                    # noqa: E402


def sinh(p: Path, giay=1.5):
    subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}",
         "-ac", "1", "-ar", "24000", str(p)], capture_output=True)


def dai_ffprobe(p: Path) -> float:
    if not p.exists():
        return 0.0
    r = subprocess.run(
        [settings.FFPROBE_PATH, "-v", "error", "-show_entries",
         "format=duration", "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


src = HOP / "raw.wav"
sinh(src, 1.5)
au = src.read_bytes()

from app.core import giong_vieneu as VN                        # noqa: E402
from app.core import giong_ngoai as GN                         # noqa: E402
from app.core import giong_vbee as VB                          # noqa: E402

CA = [
    ("giong_vieneu._ep_khung", "vn",
     lambda d: VN._ep_khung(src, d, 1.25)),
    ("giong_ngoai._ep_khung", "ov/cb",
     lambda d: GN._ep_khung(src, d, 1.25)),
    ("giong_vbee._ghi_wav", "vbee",
     lambda d: VB._ghi_wav(au, d)),
]

print("=" * 78)
print("ĐÍCH `.mp3` — đúng thứ mọi cửa `_synth_all*` truyền vào")
print("=" * 78)
print(f"{'hàm':<26} {'giọng':<7} | {'trả về':>7} {'byte':>7} "
      f"{'ffprobe(s)':>11}  kết luận")
print("-" * 78)
xau = []
for ten, ma, fn in CA:
    d = HOP / f"{ma.replace('/', '_')}.mp3"
    if d.exists():
        d.unlink()
    tra = bool(fn(d))
    byte = d.stat().st_size if d.exists() else 0
    dt = dai_ffprobe(d)
    if dt > 0.02 and not tra:
        kl = "FILE TỐT bị VỨT"
    elif dt <= 0.02:
        kl = "ffmpeg KHÔNG ghi được"
    else:
        kl = "ok"
    if kl != "ok":
        xau.append(ten)
    print(f"{ten:<26} {ma:<7} | {str(tra):>7} {byte:>7} {dt:>11.3f}  {kl}")

print("\nĐỐI CHỨNG — cùng hàm, đích `.wav` (phép đo CÓ RĂNG):")
print("-" * 78)
for ten, ma, fn in CA:
    d = HOP / f"{ma.replace('/', '_')}.wav"
    if d.exists():
        d.unlink()
    tra = bool(fn(d))
    byte = d.stat().st_size if d.exists() else 0
    dt = dai_ffprobe(d)
    print(f"{ten:<26} {ma:<7} | {str(tra):>7} {byte:>7} {dt:>11.3f}")

print(f"\n>>> SỐ HÀM HỎNG TRÊN ĐÍCH .mp3: {len(xau)}/{len(CA)}  {xau}")

print("\n" + "=" * 78)
print("LỜI LOG app ghi ra (đúng thứ đọc được trên máy anh Hùng)")
print("=" * 78)
lg = Path(os.environ["BQ_DATA_DIR"])
for f in sorted(lg.rglob("*.log")):
    dong = [x.rstrip() for x in
            f.read_text("utf-8", "replace").splitlines() if x.strip()]
    if dong:
        print(f"\n--- {f.name} ---")
        for x in dong[-3:]:
            print(f"   {x}")

print(f"\n[hộp cát] {HOP}")
shutil.rmtree(HOP, ignore_errors=True)
