# -*- coding: utf-8 -*-
r"""BÁO CÁO (KHÔNG TỰ SỬA): TIẾNG ĐỘNG CHỈ NGHE ĐƯỢC TRÊN CLIP CÓ NỀN YÊN.

Anh Hùng 08/08/2026: *"âm thanh hiệu ứng … thậm chí còn không nghe được gì cả
luôn"*. v2.18.0 chữa bằng `tinh_gain_sfx` = chuẩn hoá theo nền của chính clip:

    đích   = nền_clip + 8 dB + bù_nhóm
    gain   = đích - mean_của_file
    gain   = min(gain, -1 dBFS - max_của_file)      <-- KẸP ĐỈNH
    gain   = kẹp trong [-30, +15] dB

**CHỖ CHƯA ỔN — hai vế MÂU THUẪN NHAU.** 184 file trong kho là tiếng động ngắn
đã chuẩn hoá ĐỈNH sẵn: hệ số đỉnh (max − mean) trung vị **15,3 dB** (3,3 .. 28,5).
Với file như thế, "kẹp đỉnh" cho phép gain tối đa ~ −1 − max ≈ **−1 .. +4 dB**,
trong khi "đích" đòi +11 .. +15 dB. Nền clip càng TO thì kẹp càng thắng:

    nền clip     % file bị kẹp đỉnh khoá     thiếu so với đích (trung vị / tối đa)
    -30,0 dBFS        21 %                        0,0 /  7,5 dB
    -26,0 dBFS        40 %                        0,0 / 11,5 dB
    -23,6 dBFS        53 %                        1,0 / 13,9 dB   <- nguồn của cổng 44
    -20,0 dBFS        64 %                        4,6 / 17,5 dB
    -15,7 dBFS        74 %                        8,9 / 21,8 dB   <- clip THẬT đo được

VÌ SAO CỔNG 44 KHÔNG THẤY: nó đo trên MỘT nguồn có nền −23,6 dBFS (video Nhật,
giữa câu có khoảng lặng). Clip thật của anh Hùng hôm nay (xe tải chạy, tiếng nổ
máy liên tục) đo được nền **−15,7 dBFS** và mức lời −14,7 — gần như không có
khoảng lặng nào để tiếng động chen vào.

SỐ ĐO TRÊN CLIP THẬT (`_kiem_clip_that.py`, 16 s, 3 điểm nhấn + 2 điểm nối,
so bản BẬT tiếng động với bản TẮT, đỉnh đường bao RMS tại từng mốc):

    mốc            0,12s   5,00s   6,00s   9,00s  12,00s
    bật − tắt      +0,6    −1,1    −0,0    −1,6    +2,4   dB

Tức bật tiếng động lên gần như KHÔNG đổi gì, và **2/5 mốc còn NHỎ ĐI** vì
ducking hạ tiếng gốc 5 dB mà lớp tiếng động không bù lại nổi. Đúng triệu chứng
mà v2.18.0 định chữa (bản trước đo +0,7 dB).

KHÔNG TỰ SỬA vì đây là ĐỔI ĐỘ TO của mọi clip trên 200-300 kênh. Hướng đề xuất,
theo thứ tự rủi ro tăng dần:
  1. Kẹp đỉnh theo **ĐỈNH SAU KHI TRỘN** chứ không theo riêng lớp tiếng động:
     tiếng gốc đang bị duck −5 dB đúng lúc đó nên còn chỗ trống.
  2. Đo nền bằng **BÁCH PHÂN VỊ THẤP** (vd bpv20 của đường bao RMS) thay cho
     `mean_volume` cả clip — `mean_volume` của clip ồn CHÍNH LÀ mức lời.
  3. Dùng bảng mức đo theo **LUFS/RMS ngắn hạn** thay vì mean toàn file.
  4. Nới `_SFX_DINH_TRAN_DB` (rủi ro vỡ tiếng — phải nghe thử).

    .venv\Scripts\python.exe _do_sfx_theo_nen.py
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_dosfxnen_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_TEST", "1")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as FU          # noqa: E402


def main() -> int:
    bang = FU._sfx_bang_muc()
    ms = [(k, v) for k, v in bang.items()
          if isinstance(v, list) and len(v) >= 2]
    cr = sorted(v[1] - v[0] for _k, v in ms)
    print(f"kho tiếng động: {len(ms)} file · hệ số đỉnh (max−mean) "
          f"min {cr[0]:.1f} · trung vị {cr[len(cr)//2]:.1f} · max {cr[-1]:.1f} dB")
    print(f"\n{'nền clip':>10} {'bị kẹp đỉnh':>14} {'thiếu trung vị':>16}"
          f" {'thiếu tối đa':>14}")
    print("-" * 60)
    for nen in (-30.0, -26.0, -23.6, -20.0, -15.7, -12.0):
        thieu = []
        for k, (mean, mx) in ms:
            cat = k.split("/")[0]
            dich = nen + FU.SFX_TREN_NEN_DB + FU._SFX_CAT_DB.get(cat, 0.0)
            g_muc = dich - mean
            g_that = max(FU._SFX_GAIN_MIN,
                         min(FU._SFX_GAIN_MAX,
                             min(g_muc, FU._SFX_DINH_TRAN_DB - mx)))
            thieu.append(g_muc - g_that)
        n = sum(1 for x in thieu if x > 0.5)
        print(f"{nen:>7.1f} dB {n:>7d}/{len(thieu)} ({100*n/len(thieu):3.0f}%)"
              f"{statistics.median(thieu):>13.1f} dB{max(thieu):>12.1f} dB")
    print("\n(đọc docstring đầu file để biết ý nghĩa + hướng sửa đề xuất)")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
