# -*- coding: utf-8 -*-
"""SINH FILE ĐỂ ANH HÙNG TỰ NGHE — tôi không có tai, số đo không thay được nghe.

Ra hai thứ, đặt ở `D:\\claude\\ai-content-studio\\_NGHE_THU_ANH_HUNG`:

 A. **CẶP A/B ĐỘ TO** — cùng một video, chỉ khác bước chuẩn hoá:
      `1_TRUOC_nho_tieng.mp4`  = đúng bản anh Hùng xuất 16/08 (−16,0 LUFS)
      `2_SAU_da_chuan_hoa.mp4` = cũng video đó, tiếng đã nâng về −14 LUFS
    Hình GIỮ NGUYÊN (`-c:v copy`) nên nghe được đúng phần tiếng đổi, và mở
    hai file bật qua lại là so được ngay.

 B. **TIẾNG THỬ TỪNG GIỌNG** — đúng cái nút "Nghe thử" sẽ phát.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

RA = REPO / "_NGHE_THU_ANH_HUNG"


def main() -> int:
    from app.core import thay_giong as tg

    RA.mkdir(exist_ok=True)
    goc = (Path.home() / "Downloads" / "longtieng" / "xuất"
           / "近期热播的7部新片推荐。 #电影推荐 #新片速递.mp4")
    if not goc.exists():
        print(f"THIẾU {goc}")
        return 2

    print("== A. CẶP A/B ĐỘ TO ==")
    truoc = RA / "1_TRUOC_nho_tieng.mp4"
    sau = RA / "2_SAU_da_chuan_hoa.mp4"
    if not truoc.exists():
        shutil.copyfile(goc, truoc)

    # tách tiếng -> chuẩn hoá -> ghép lại, GIỮ NGUYÊN HÌNH
    wav0 = RA / "_tam_goc.wav"
    wav1 = RA / "_tam_chuan.wav"
    tg._ffmpeg(["-i", str(goc), "-vn", "-ac", "2", "-ar", "48000",
                "-c:a", "pcm_s16le", str(wav0)], "rút tiếng")
    kq = tg.chuan_do_to(wav0, wav1)
    tg._ffmpeg(["-i", str(goc), "-i", str(wav1), "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                str(sau)], "ghép tiếng đã chuẩn hoá")
    for p in (wav0, wav1):
        p.unlink(missing_ok=True)

    d0 = tg.do_do_to(truoc)
    d1 = tg.do_do_to(sau)
    print(f"  1_TRUOC_nho_tieng.mp4   I {d0['I']:+7.2f} LUFS · "
          f"TP {d0['TP']:+6.2f} dBTP · LRA {d0['LRA']:5.2f}")
    print(f"  2_SAU_da_chuan_hoa.mp4  I {d1['I']:+7.2f} LUFS · "
          f"TP {d1['TP']:+6.2f} dBTP · LRA {d1['LRA']:5.2f}")
    print(f"  -> to hơn {d1['I'] - d0['I']:+.2f} LU, "
          f"dải động đổi {d1['LRA'] - d0['LRA']:+.2f} LU "
          f"(0,00 = KHÔNG nén dập)")
    print(f"  nâng {kq['nang_db']:+.2f} dB · đạt đích: {kq['dat_dich']} · "
          f"quá trần đỉnh: {kq['qua_tran_dinh']}")

    print("\n== B. TIẾNG THỬ TỪNG GIỌNG (đúng cái nút Nghe thử phát) ==")
    ds = [("edge_HoaiMy", "vi-VN-HoaiMyNeural"),
          ("edge_NamMinh", "vi-VN-NamMinhNeural"),
          ("edge_NamMinh_tram", tg.ma_bien_the("vi-VN-NamMinhNeural", "-20Hz")),
          ("edge_NamMinh_cao", tg.ma_bien_the("vi-VN-NamMinhNeural", "+20Hz")),
          ("edge_HoaiMy_tram", tg.ma_bien_the("vi-VN-HoaiMyNeural", "-20Hz")),
          ("edge_HoaiMy_cao", tg.ma_bien_the("vi-VN-HoaiMyNeural", "+20Hz"))]
    try:
        from app.core import piper_tts
        ds.append(("piper_vais1000", piper_tts.MA_GIONG))
    except Exception:  # noqa: BLE001
        pass
    for ten, ma in ds:
        p = RA / f"giong_{ten}.wav"
        kq2 = tg.doc_thu(ma, p, dung_cache=False)
        if kq2["ra"]:
            print(f"  giong_{ten + '.wav':32} nguồn={kq2['nguon']:10} "
                  f"{tg.probe_duration(p):.2f} s")
        else:
            print(f"  giong_{ten + '.wav':32} LỖI: {kq2['loi'][:60]}")

    print(f"\nTẤT CẢ NẰM Ở:\n  {RA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
