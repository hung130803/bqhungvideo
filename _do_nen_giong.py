# -*- coding: utf-8 -*-
"""QUÉT THAM SỐ NÉN LỚP GIỌNG — chọn bằng số, không chỉnh mò.

Đích của bước nén KHÔNG phải "làm giọng to hơn" mà là **hạ hệ số đỉnh/RMS**
để còn chỗ mà nâng. Giọng edge-tts đo được hệ số 15,31 dB (đỉnh -5,33 · lời
-20,64): vài phụ âm bật chiếm hết chỗ trống.

Đặt ngưỡng SÁT mức lời (+3 dB) thì nén luôn cả thân câu -> mức lời tụt 2,93 dB
-> phải hạ nhạc bù -> nhạc mất 10,46 dB. Nên phải quét.

4 cột phải đọc CÙNG NHAU, tối ưu một cột là hỏng cột khác:
  · giọng/nhạc  — càng dương càng nghe rõ (ĐÍCH >= 9)
  · nhạc mất    — càng gần 0 càng giữ được nhạc nền (mục tiêu tính năng)
  · RMS trộn    — bản cuối có nhỏ tiếng hơn bản cũ không
  · chạm trần   — hạn đỉnh phải gọt bao nhiêu (bản cũ 36 mẫu)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))


def main() -> int:
    from app.core import thay_giong as tg

    e2e = Path(sys.argv[1] if len(sys.argv) > 1 else REPO / "_do_lt" / "e2e")
    giong = e2e / "tieng_moi.giong.wav"
    nhac = e2e / "tach" / "lop_nhac.wav"
    tam = e2e / "_nen"
    tam.mkdir(parents=True, exist_ok=True)

    cb0 = tg.can_bang_giong_nhac(giong, nhac)
    muc_loi = cb0["muc_giong_luc_noi_db"]
    r0_nhac = tg.do_rms(nhac)
    print(f"lời {muc_loi:.2f} · đỉnh {cb0['dinh_giong_db']:.2f} · hệ số đỉnh "
          f"{cb0['he_so_dinh_db']:.2f} dB · nhạc {cb0['muc_nhac_luc_noi_db']:.2f}")
    print(f"\n{'ngưỡng':>8} {'tỉ lệ':>6} {'lời sau':>9} {'đỉnh sau':>9} "
          f"{'+giọng':>7} {'-nhạc':>7} {'giọng/nhạc':>11} {'chìm%':>7} "
          f"{'nhạc mất':>9} {'RMS trộn':>9} {'trần':>6}")

    for tren in (3.0, 6.0, 9.0, 12.0):
        for ratio in (3.0, 4.0, 6.0):
            nen_p = tam / f"g_{int(tren)}_{int(ratio)}.wav"
            ng = 10.0 ** ((muc_loi + tren) / 20.0)
            tg._ffmpeg(["-i", str(giong), "-af",
                        f"acompressor=level_in=1:threshold={ng:.6f}:"
                        f"ratio={ratio:.1f}:attack=5:release=150:makeup=1:"
                        "knee=6", "-ac", "2", "-ar", str(tg.SR_TACH),
                        "-c:a", "pcm_s16le", str(nen_p)], "nén")
            cb = tg.can_bang_giong_nhac(nen_p, nhac)
            gg, gn = cb["gain_giong_db"], cb["gain_nhac_db"]
            gp, np_ = tam / "gg.wav", tam / "nn.wav"
            tg._ffmpeg(["-i", str(nen_p), "-af", f"volume={gg:.2f}dB", "-ac",
                        "2", "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                        str(gp)], "nâng")
            nd, rt = tg._tham_so_duck(cb["muc_nhac_luc_noi_db"] + gn)
            fc = (f"[0:a]volume={gn:.2f}dB[nh0];[1:a]volume={gg:.2f}dB[gi];"
                  f"[nh0][gi]sidechaincompress=threshold={nd:.6f}:"
                  f"ratio={rt:.3f}:attack=20:release=300:makeup=1:"
                  "level_sc=1[out]")
            tg._ffmpeg(["-i", str(nhac), "-i", str(nen_p), "-filter_complex",
                        fc, "-map", "[out]", "-ac", "2", "-ar",
                        str(tg.SR_TACH), "-c:a", "pcm_s16le", str(np_)], "né")
            d = tg.do_giong_tren_nhac(gp, np_)
            out = tam / "tron.wav"
            fc2 = ("[0:a][1:a]amix=inputs=2:duration=first:normalize=0[mx];"
                   f"[mx]alimiter=level_in=1:level_out=1:limit="
                   f"{10.0 ** (tg.TRAN_DINH_DB / 20.0):.6f}:level=0:"
                   "latency=1[out]")
            tg._ffmpeg(["-i", str(np_), "-i", str(gp), "-filter_complex", fc2,
                        "-map", "[out]", "-ac", "2", "-ar", str(tg.SR_TACH),
                        "-c:a", "pcm_s16le", str(out)], "trộn")
            m = tg.do_meo(out)
            print(f"{tren:>8.0f} {ratio:>6.0f} "
                  f"{cb['muc_giong_luc_noi_db']:>9.2f} "
                  f"{cb['dinh_giong_db']:>9.2f} {gg:>7.2f} {gn:>7.2f} "
                  f"{d['giong_tren_nhac_tb']:>+11.2f} {d['ty_le_chim']:>7} "
                  f"{20 * math.log10(max(1e-9, tg.do_rms(np_) / r0_nhac)):>+9.2f} "
                  f"{tg.do_rms(out):>9.4f} {m.get('cham_tran'):>6}")
    print("\n(mốc BẢN CŨ: giọng/nhạc -7,32 · chìm 90,1% · nhạc mất -2,00 dB · "
          "RMS trộn 0,2469 · chạm trần 36)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
