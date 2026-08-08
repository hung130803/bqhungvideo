# -*- coding: utf-8 -*-
r"""ĐO LẠI SAU KHI SỬA: tiếng động còn bị "kẹp đỉnh" khoá độ to nữa không?

BỆNH (v2.18.0, lượt kiểm độc lập 08/08/2026 đo trên CLIP THẬT):
`tinh_gain_sfx` có 2 vế đá nhau — "đích = nền + 8 dB" và "kẹp đỉnh <= -1 dBFS".
Kho 184 file là tiếng ngắn đã chuẩn hoá ĐỈNH nên kẹp đỉnh gần như luôn thắng:

    nền clip     % file bị kẹp đỉnh khoá     thiếu so với đích (trung vị / tối đa)
    -23,6 dBFS        53 %                        1,0 / 13,9 dB   <- nguồn cổng 44
    -15,7 dBFS        74 %                        8,9 / 21,8 dB   <- clip THẬT

Đo trên clip thật 16 s: bật/tắt tiếng động lệch **+0,6 / −1,1 / −0,0 / −1,6 /
+2,4 dB** — 2/5 mốc còn NHỎ ĐI.

THUỐC (08/08/2026) — 4 chỗ, mỗi chỗ một số đo:
  1. **NỀN đo bằng bách phân vị**, không phải `mean_volume`. Clip ồn có
     `mean_volume` CHÍNH LÀ mức lời (-15,7) trong khi nền thật là -26..-36.
     `_do_muc_clip` trả bpv20 (nền) · bpv50 · bpv90 (MỨC LỜI) · đỉnh.
  2. **CHUẨN HOÁ THEO ĐỈNH RMS 50 ms** của từng file (`muc_do.json` cột 3),
     không theo `mean` cả file. Đo 8 file trải crest 1,5..16,6 dB: lệch so đích
     **-0,4..+0,7 dB** (trước: hàng chục dB) -> hết nhấp nháy.
  3. **BỎ vế kẹp gain theo đỉnh**; giữ đỉnh bằng `alimiter` ở nhánh SFX + một
     `alimiter` SAU KHI TRỘN. Limiter gọt đỉnh mà GIỮ độ to; kẹp gain thì hạ
     cả hai. (Phải hạn sau khi trộn vì nguồn thật đo được đỉnh **+0,51 dBFS** —
     tức bản gốc đã méo sẵn, không lớp nào kẹp riêng mà cứu được.)
  4. **DUCKING lùi ra SAU mốc 0,22 s**: bướu nửa hình sin cũ sâu nhất ở
     0,225 s SAU mốc, trùm đúng cửa sổ tai nghe cú va -> chính nó làm mốc
     NHỎ ĐI. Nay cú va tự xuyên qua, ducking chỉ dọn chỗ cho phần ngân.
  5. **DÓNG CÚ VA VÀO ĐÚNG MỐC**: kho có tiếng VÀO CHẬM (đỉnh rơi tới 0,60 s
     sau lúc bắt đầu). Chèn đúng giây điểm nhấn thì trong cửa sổ ±0,175 s nó
     hụt **8,2 dB** mà nhật ký vẫn ghi "có tiếng". Nay `muc_do.json` có cột 4
     = GIÂY xảy ra đỉnh; app đẩy sớm đúng bấy nhiêu, và loại 18/184 file vào
     chậm hơn 0,35 s khỏi điểm nhấn.
  + **MẤT 3,0 dB ÂM THẦM**: kho là file MONO, `amix` ra stereo nên ffmpeg tự
    đổi bố cục kênh với hệ số 1/căn2. Sửa bằng `pan` toán tử `<`.

File này đo lại vế (3): với cách tính MỚI thì còn bao nhiêu file bị trần đỉnh
khoá, và bốc ngẫu nhiên có ra cùng một độ to không.

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
          if isinstance(v, list) and len(v) >= 3]
    if not ms:
        print("bảng muc_do.json chưa có cột 3 — chạy tools/do_muc_sfx.py")
        return 2
    cr = sorted(v[1] - v[2] for _k, v in ms)
    print(f"kho tiếng động: {len(ms)} file")
    print(f"  hệ số đỉnh so MEAN   (cách CŨ chuẩn hoá): trung vị "
          f"{statistics.median(v[1] - v[0] for _k, v in ms):.1f} dB")
    print(f"  hệ số đỉnh so RMS50  (cách MỚI)         : trung vị "
          f"{cr[len(cr)//2]:.1f} dB  (min {cr[0]:.1f} · max {cr[-1]:.1f})")

    # (nền, mức lời) của 6 cảnh thật — cột 'nền' là bpv20, không phải mean.
    canh = [("clip rất yên", -40.0, -26.0), ("nguồn cổng 44 cũ", -36.5, -20.5),
            ("clip thường", -30.0, -18.0), ("clip THẬT anh Hùng", -26.0, -15.7),
            ("clip ồn", -22.0, -11.0), ("nhạc nền liên tục", -18.0, -12.0)]
    print(f"\n{'cảnh':<22}{'nền':>7}{'lời':>7}{'đích':>8}"
          f"{'file dùng được':>16}{'trải độ to':>12}")
    print("-" * 74)
    xau = []
    for ten, nen, loi in canh:
        dich = FU.dich_sfx_dB("impact", nen, loi)
        hop = [(k, v) for k, v in ms
               if FU._hop_muc(str(FU._assets_sfx_dir() / k), dich,
                              FU._SFX_DINH_TRAN_DB)]
        # ĐỘ TO THỰC của từng file sau khi nhân hệ số (đã tính cả vế kẹp
        # [_SFX_GAIN_MIN, _SFX_GAIN_MAX]). Chuẩn hoá đúng + lọc đúng thì mọi
        # file ra CÙNG một con số -> bốc file nào cũng kêu bằng nhau.
        ra = [v[2] + max(FU._SFX_GAIN_MIN,
                         min(FU._SFX_GAIN_MAX, dich - v[2]))
              for _k, v in hop]
        trai = (max(ra) - min(ra)) if ra else 99.0
        print(f"{ten:<22}{nen:>7.1f}{loi:>7.1f}{dich:>8.1f}"
              f"{len(hop):>10}/{len(ms):<5}{trai:>11.1f} dB")
        if not hop or trai > 0.5:
            xau.append(ten)
        if len(hop) < 20:
            xau.append(f"{ten}: quá ít file để bốc ngẫu nhiên")
    print("\n" + ("ĐẠT — mọi cảnh đều còn đủ file và mọi file ra CÙNG độ to"
                  if not xau else "HỎNG: " + " · ".join(xau)))
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 1 if xau else 0


if __name__ == "__main__":
    sys.exit(main())
