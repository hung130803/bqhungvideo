# -*- coding: utf-8 -*-
"""HIỆU CHUẨN ĐỘ SÂU "NHẠC NÉ GIỌNG" — `ratio` KHÔNG PHẢI SỐ dB TỤT XUỐNG.

Bản đầu tính `ratio` từ giả định "nhạc nằm đúng 12 dB trên ngưỡng" rồi tin
luôn. Đo lại ra sai HẲN: đặt đích tụt 4 dB mà tổng cộng nhạc mất 10,42 dB và
giọng vọt lên +15,48 dB (đích 10,0). Lý do: `muc_nhac_luc_noi_db` là TRUNG VỊ
của cửa sổ RMS 0,2 s, còn bộ nén nhìn mức TỨC THỜI — đỉnh nhạc cao hơn trung
vị nhiều nên nó nén sâu hơn.

Nên quét THẬT rồi tra bảng, đúng cách mọi hằng số khác trong repo này ra đời.
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
    tam = e2e / "_duck"
    tam.mkdir(parents=True, exist_ok=True)

    cb = tg.can_bang_giong_nhac(giong, nhac)
    gg = cb["gain_giong_db"]
    gn = -2.0 + cb["gain_nhac_db"]
    nhac_sau = cb["muc_nhac_luc_noi_db"] + gn
    print(f"giọng +{gg:.2f} dB · nhạc {gn:.2f} dB · nhạc lúc nói sau chỉnh "
          f"{nhac_sau:.2f} dBFS")

    g_p = tam / "giong.wav"
    tg._ffmpeg(["-i", str(giong), "-af", f"volume={gg:.2f}dB", "-ac", "2",
                "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le", str(g_p)],
               "giọng đã nâng")

    # mốc 0: nhạc chỉ chỉnh mức, KHÔNG né
    n0 = tam / "nhac_khongne.wav"
    tg._ffmpeg(["-i", str(nhac), "-af", f"volume={gn:.2f}dB", "-ac", "2",
                "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le", str(n0)],
               "nhạc không né")
    r0 = tg.do_rms(n0)
    d0 = tg.do_giong_tren_nhac(g_p, n0)
    print(f"\nKHÔNG NÉ: giọng trên nhạc TB {d0['giong_tren_nhac_tb']:+.2f} dB "
          f"· chìm {d0['ty_le_chim']}% · RMS nhạc mốc {r0:.6f}")

    print(f"\n{'ratio':>7} {'trên ngưỡng':>12} {'nhạc tụt TB':>12} "
          f"{'giọng/nhạc':>11} {'chìm %':>8}")
    for tren in (8.0, 12.0, 18.0):
        for ratio in (1.3, 1.6, 2.0, 3.0):
            nguong = 10.0 ** ((nhac_sau - tren) / 20.0)
            dst = tam / f"n_{int(tren)}_{int(ratio * 10)}.wav"
            fc = (f"[0:a]volume={gn:.2f}dB[nh0];"
                  f"[1:a]volume={gg:.2f}dB[gi];"
                  f"[nh0][gi]sidechaincompress=threshold={nguong:.6f}:"
                  f"ratio={ratio:.3f}:attack=20:release=300:makeup=1:"
                  "level_sc=1[out]")
            tg._ffmpeg(["-i", str(nhac), "-i", str(giong),
                        "-filter_complex", fc, "-map", "[out]", "-ac", "2",
                        "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                        str(dst)], f"né {tren}/{ratio}")
            r = tg.do_rms(dst)
            d = tg.do_giong_tren_nhac(g_p, dst)
            tut = 20 * math.log10(max(1e-9, r / r0))
            print(f"{ratio:>7.1f} {tren:>12.0f} {tut:>+12.2f} "
                  f"{d['giong_tren_nhac_tb']:>+11.2f} {d['ty_le_chim']:>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
