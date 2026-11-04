# -*- coding: utf-8 -*-
"""CỔNG 95 — VIDEO NGUỒN CÓ LUỒNG TIẾNG NGẮN HƠN HÌNH KHÔNG ĐƯỢC LÀM CHẾT
LƯỢT XUẤT, VÀ DÂY CHUYỀN PHẢI NHẬN RA FILE HỎNG.

Lỗi thật 27/10/2026 (ảnh anh Hùng): "Xuất Part 2 · CJSOCOOL · OMG Kids Ruined
My Jordans PRANK — ffmpeg không xuất được clip … Invalid value NaN for volume
… Conversion failed!", hỏng cả 3 lượt thử lại. Gốc: file tải về có HÌNH
1.257,4 s mà TIẾNG chỉ 9,6 s. Part 2 cắt giây 190-370 -> [0:a] RỖNG -> biểu
thức `volume=…:eval=frame` nhận khung không mốc (t = NaN) -> aac chết.
Tái hiện chỉ phần tiếng: 0,6 s, ra đúng "NaN for volume".

Canh:
 1. `tieng_hut` nhận ra file hỏng · KHÔNG báo oan file lệch vài giây ở đuôi.
 2. Xuất đoạn nằm HẲN ngoài phần có tiếng -> ra file (không tiếng gốc).
 3. Đoạn phủ MỘT PHẦN -> ra file, tiếng được đệm im lặng đủ dài bằng hình.
 4. Đoạn bình thường không đổi gì.
 5. TỰ KIỂM: giấu độ dài luồng tiếng (= bản cũ) thì ca 2 PHẢI chết.

ffmpeg THẬT, nguồn tự sinh bằng lavfi (không phụ thuộc file trên máy).
Chạy:  .venv\\Scripts\\python -u _test_tieng_hut.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass
HC = Path(tempfile.mkdtemp(prefix="bq_tieng_hut_"))
os.environ.update(BQ_DATA_DIR=str(HC), BQ_DB_PATH=str(HC / "t.db"),
                  BQ_QSETTINGS_INI=str(HC / "s.ini"), BQ_BO_MANG="1")
import _test_guard  # noqa: F401,E402
from app.core import ffmpeg_utils as F  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}")
    else:
        HONG += 1
        print(f"  HỎNG {ten}  {chi_tiet}")


FF = F.settings.FFMPEG_PATH
SRC = HC / "hinh20_tieng3.mp4"
subprocess.run([FF, "-v", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=s=320x568:r=30:d=20",
                "-f", "lavfi", "-i", "sine=f=440:r=48000:d=3",
                "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset",
                "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(SRC)],
               check=True)


def xuat(segs, ten):
    dst = HC / f"{ten}.mp4"
    try:
        F.export_canvas_clip(str(SRC), str(dst), segs, (0.5, 0.5, 1.0),
                             out_w=540, out_h=960, encoder="libx264",
                             speed=1.1, pitch=1.15)
    except Exception as e:  # noqa: BLE001
        return None, str(e)[-300:]
    return F.probe(dst), ""


def dai_tieng(p):
    r = subprocess.run([F.settings.FFPROBE_PATH, "-v", "error", "-select_streams",
                        "a", "-show_entries", "stream=duration", "-of",
                        "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0.0


print("CA 1 — bộ dò file hỏng")
info = F.probe(SRC)
ok(abs(info.audio_duration - 3.0) < 0.2, "1a probe đọc đúng độ dài luồng tiếng", info)
hong = F.MediaInfo(duration=1257.4, has_audio=True, audio_duration=9.6)
ok("9,6 s" in F.tieng_hut(hong), "1b file thật 27/10 (9,6 s / 1257,4 s) bị báo", F.tieng_hut(hong))
ok(F.tieng_hut(F.MediaInfo(duration=600, has_audio=True, audio_duration=595)) == "",
   "1c lệch 5 s ở đuôi KHÔNG báo oan")
ok(F.tieng_hut(F.MediaInfo(duration=600, has_audio=True, audio_duration=0)) == "",
   "1d không đọc được độ dài tiếng -> không kết luận")
ok(F.tieng_hut(F.MediaInfo(duration=600, has_audio=False)) == "",
   "1e video không có tiếng -> không báo")

print("CA 2 — đoạn nằm HẲN ngoài phần có tiếng (đúng lỗi 27/10)")
i2, loi = xuat([(10.0, 15.0)], "ngoai")
ok(i2 is not None and i2.duration > 4.0, "2a xuất ra file", loi or i2)

print("CA 3 — đoạn phủ MỘT PHẦN: tiếng đệm im lặng đủ bằng hình")
i3, loi = xuat([(1.0, 8.0)], "mot_phan")
ok(i3 is not None, "3a xuất ra file", loi)
if i3 is not None:
    a3 = dai_tieng(HC / "mot_phan.mp4")
    ok(abs(a3 - i3.duration) < 0.3, "3b tiếng dài bằng hình (không cụt)",
       f"tiếng {a3:.2f} s / hình {i3.duration:.2f} s")

print("CA 4 — đoạn bình thường")
i4, loi = xuat([(0.2, 2.5)], "thuong")
ok(i4 is not None and i4.has_audio, "4a xuất ra file có tiếng", loi or i4)

print("CA 5 — TỰ KIỂM: giấu độ dài luồng tiếng (= bản cũ) thì ca 2 phải chết")
_probe = F.probe
def probe_cu(p):
    i = _probe(p)
    i.audio_duration = 0.0
    return i
F.probe = probe_cu
try:
    i5, loi5 = xuat([(10.0, 15.0)], "tu_kiem")
finally:
    F.probe = _probe
ok(i5 is None, "5a bản cũ chết đúng như lỗi thật (cổng có răng)", i5)

shutil.rmtree(HC, ignore_errors=True)
print()
print(f"KẾT QUẢ: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
