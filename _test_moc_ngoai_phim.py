# -*- coding: utf-8 -*-
"""CỔNG 34 — MỐC CẮT NGOÀI PHIM: KHÔNG ĐƯỢC RA CLIP RỖNG, KHÔNG ĐƯỢC IM LẶNG.

LỖI THẬT: anh Hùng gửi hộp lỗi 07/08/2026 — 'ffmpeg không xuất được clip' với
log toàn HỆ QUẢ ('Could not open encoder before EOF', 'Conversion failed!',
frame=0, elapsed=0:00:00.04). Truy nhật ký: 02/08 17:38 kênh リーガル探偵,
**18/19 video cùng lượt xuất tốt**, chỉ Part 3 của 1 video chết -> lỗi thuộc
ĐOẠN, không phải hệ thống.

ĐO ĐƯỢC BẰNG ffmpeg THẬT (video 10 giây, cắt [20s..25s]):
  - `-ss` vượt độ dài file -> ffmpeg **TRẢ MÃ THOÁT 0** + 'Output file is empty'
    + file ra **0 KiB**. App CHỈ xem mã thoát nên tưởng XUẤT XONG.
  - Hậu quả nặng hơn cả báo lỗi: clip 0 byte vào thư mục thành phẩm, rồi dây
    chuyền **XOÁ VIDEO GỐC** vì thấy 'xong' = mất trắng.
  - Đường xuất thật (có phụ đề .ass + tiếng động) thì bộ trộn tiếng không mở
    nổi encoder -> hard-fail = đúng hộp lỗi anh Hùng thấy.

3 BẢN VÁ CỔNG NÀY CANH:
  (a) `_cat_theo_do_dai_that` KẸP mốc vào [0, độ_dài_THẬT] -> Part vượt một
      phần vẫn XUẤT ĐƯỢC (ngắn hơn) thay vì mất cả Part; vượt HẾT thì báo lỗi
      nói rõ 'video gốc tải thiếu'. Không đọc được độ dài -> GIỮ NGUYÊN.
  (b) `_run_with_fallback` bắt 'Output file is empty' -> coi là LỖI dù mã 0,
      và KHÔNG thử lại encoder khác (đổi encoder không chữa được mốc sai).
  (c) `_gom_log` giữ DÒNG NGUYÊN NHÂN ở đầu log, không chỉ 6 dòng cuối —
      chính chỗ tôi làm mù hộp lỗi của anh Hùng.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

T = tempfile.mkdtemp(prefix="mocngoai_")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from app.core import ffmpeg_utils as fu  # noqa: E402
from config import settings  # noqa: E402

LOI: list = []
OK = 0
NW = 0x08000000


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  OK  {ten}" + (f" - {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} - {ct}")
        print(f"  SAI {ten} - {ct}")


FF = settings.FFMPEG_PATH
GOC = os.path.join(T, "goc.mp4")
subprocess.run([FF, "-v", "error", "-y",
                "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=10",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
                "-shortest", "-c:v", "libx264", "-crf", "30", "-c:a", "aac",
                "-t", "10", GOC], capture_output=True, creationflags=NW)
_d = fu.probe(GOC).duration
print(f"\nnguồn thử: {os.path.getsize(GOC)} byte · dài {_d:.2f}s")
ok(9.0 <= _d <= 11.0, "0 dựng được video nguồn 10 giây", f"{_d:.2f}s")

RECT = (0.5, 0.5, 1.0)


def _xuat(segs, ten_ra):
    ra = os.path.join(T, ten_ra)
    loi = None
    try:
        fu.export_canvas_clip(GOC, ra, segs, RECT, bg="black",
                              out_w=270, out_h=480, encoder="libx264")
    except Exception as e:                       # noqa: BLE001
        loi = e
    co = os.path.exists(ra)
    return ra, loi, (os.path.getsize(ra) if co else -1)


print("\n=== 1. Mốc VƯỢT HẾT phim -> báo lỗi RÕ, không để lại file rỗng ===")
ra1, loi1, sz1 = _xuat([(20.0, 25.0)], "ngoai_het.mp4")
ok(loi1 is not None, "1a có báo lỗi (không im lặng coi như xong)",
   type(loi1).__name__ if loi1 else "KHÔNG báo gì!")
_lm = str(loi1 or "")
ok("ngoài phim" in _lm or "tải thiếu" in _lm,
   "1b lời lỗi nói ĐÚNG nguyên nhân cho người dùng", _lm[:90])
ok("10.0s" in _lm or "10.0 s" in _lm or "20.0s" in _lm,
   "1c lời lỗi có SỐ ĐO thật (dài phim / mốc cắt)", _lm[:90])
ok(sz1 <= 0, "1d KHÔNG để lại file clip rỗng trong thư mục", f"{sz1} byte")

print("\n=== 2. Mốc VƯỢT MỘT PHẦN -> vẫn xuất được (kẹp lại), không mất Part ===")
ra2, loi2, sz2 = _xuat([(8.0, 30.0)], "vuot_mot_phan.mp4")
ok(loi2 is None, "2a xuất THÀNH CÔNG thay vì chết cả Part",
   "" if loi2 is None else f"{type(loi2).__name__}: {loi2}")
ok(sz2 > 2000, "2b clip ra có nội dung THẬT (không 0 byte)", f"{sz2} byte")
if loi2 is None:
    _i2 = fu.probe(ra2)
    ok(1.0 <= _i2.duration <= 3.0,
       "2c độ dài đúng phần còn nằm trong phim (~2s)", f"{_i2.duration:.2f}s")
    ok(_i2.has_audio, "2d clip ra CÓ tiếng (encoder tiếng mở được)")

print("\n=== 3. BẤT BIẾN: đoạn nằm TRỌN trong phim không bị bản vá đụng ===")
ra3, loi3, sz3 = _xuat([(2.0, 6.0)], "binh_thuong.mp4")
ok(loi3 is None and sz3 > 2000, "3a clip thường vẫn xuất tốt",
   f"{sz3} byte" if loi3 is None else str(loi3)[:70])
if loi3 is None:
    ok(3.5 <= fu.probe(ra3).duration <= 4.5, "3b độ dài giữ nguyên 4s",
       f"{fu.probe(ra3).duration:.2f}s")
ra4, loi4, sz4 = _xuat([(1.0, 3.0), (6.0, 9.0)], "ghep_2doan.mp4")
ok(loi4 is None and sz4 > 2000, "3c GHÉP 2 đoạn (2 pha) vẫn xuất tốt",
   f"{sz4} byte" if loi4 is None else str(loi4)[:70])

print("\n=== 4. Hàm kẹp mốc: từng ca riêng lẻ ===")
ok(fu._cat_theo_do_dai_that([(1.0, 5.0)], 10.0, "x") == [(1.0, 5.0)],
   "4a trong phim -> giữ y nguyên")
ok(fu._cat_theo_do_dai_that([(8.0, 30.0)], 10.0, "x") == [(8.0, 10.0)],
   "4b vượt một phần -> kẹp về mép phim")
ok(fu._cat_theo_do_dai_that([(1.0, 5.0)], 0.0, "x") == [(1.0, 5.0)],
   "4c KHÔNG đọc được độ dài -> GIỮ NGUYÊN (quy tắc: không rõ thì giữ)")
try:
    fu._cat_theo_do_dai_that([(9.95, 12.0)], 10.0, "x")
    ok(False, "4d phần còn lại < 0,3s -> phải báo lỗi", "không báo")
except RuntimeError:
    ok(True, "4d phần còn lại < 0,3s -> báo lỗi (0,05s không là đoạn phim)")
_n = fu._cat_theo_do_dai_that([(1.0, 3.0), (20.0, 25.0)], 10.0, "x")
ok(_n == [(1.0, 3.0)], "4e nhiều đoạn: bỏ đoạn ngoài, giữ đoạn trong", str(_n))

print("\n=== 5. ĐỐI CHỨNG ÂM: chứng minh lỗi CŨ có thật và nay bị bắt ===")
_rong = os.path.join(T, "rong.mkv")
_r = subprocess.run([FF, "-y", "-ss", "20.000", "-t", "5.000", "-i", GOC,
                     "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                     "-r", "30", "-fps_mode:v", "cfr", "-c:a", "pcm_s16le",
                     _rong], capture_output=True, text=True,
                    creationflags=NW)
_log = _r.stderr or ""
ok(_r.returncode == 0,
   "5a ĐO LẠI: ffmpeg tua quá phim vẫn TRẢ MÃ 0 (nên chỉ xem mã thoát là mù)",
   f"mã {_r.returncode}")
ok("Output city" not in _log and "Output file is empty" in _log,
   "5b log CÓ dấu hiệu 'Output file is empty' để bắt", "")
ok(any("Output file is empty" in ln for ln in _log.splitlines()),
   "5c dấu hiệu nằm trên MỘT dòng (khớp cách _run_with_fallback dò)")

print("\n=== 6. Hộp lỗi phải NÓI NGUYÊN NHÂN, không chỉ hệ quả ===")
_gia_loi = ["[in#0] Error opening input: No such file or directory"]
_gia_tail = ["frame= 0 fps=0.0 q=0.0 Lsize= 0KiB", "Conversion failed!"]
_g = fu._gom_log(_gia_loi, _gia_tail)
ok("No such file" in _g, "6a giữ được DÒNG NGUYÊN NHÂN (đầu log)", _g[:60])
ok("Conversion failed!" in _g, "6b vẫn giữ dòng cuối để đối chiếu")
_dai = [f"dong {i}" for i in range(40)]
ok(len(fu._gom_log([], _dai).splitlines()) <= 10,
   "6c chặn trần 10 dòng (không dội cả trang log vào mặt user)")
ok(fu._TU_LOI and "Output file is empty" in fu._TU_LOI,
   "6d danh sách từ khoá lỗi có cả ca file rỗng")

print(f"\n{'=' * 62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  SAI {x}")
    sys.exit(1)
print("CỔNG 34 ĐẠT — mốc ngoài phim: kẹp lại được thì xuất, không thì báo rõ")
