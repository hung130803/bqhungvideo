# -*- coding: utf-8 -*-
"""A/B: CHUẨN HOÁ ĐỘ TO **MỘT LƯỢT (động)** so với **HAI LƯỢT (tuyến tính)**.

Việc phải trả lời bằng SỐ, không bằng lời:
 1. Cách nào đưa bản trộn về đích −14 LUFS sát hơn, đỉnh thật vẫn ≤ −1 dBTP?
 2. Cách nào **KHÔNG NÉN DẬP** (LRA trước/sau)?
 3. Cách nào **KHÔNG PHÁ tỉ lệ giọng-trên-nhạc** vừa chữa xong?

**PHÉP ĐO CHO CÂU 3 — đây là chỗ dễ tự lừa nhất.** "Giọng trên nhạc" đo trên
HAI LỚP RỜI, còn chuẩn hoá lại chạy trên BẢN ĐÃ TRỘN. Nên đo THẲNG cái làm
hỏng cân bằng: **hệ số mà phép chuẩn hoá áp lên theo thời gian**. Lấy đường
bao 0,2 s của bản SAU trừ đường bao bản TRƯỚC:
  · hệ số HẰNG (độ lệch chuẩn ~0) = phép NHÂN thuần -> tỉ lệ giọng/nhạc
    **KHÔNG THỂ đổi**, đúng theo toán học chứ không phải theo hy vọng;
  · hệ số BIẾN THIÊN = bộ nén đang tự ý kéo chỗ này lên dìm chỗ kia xuống ->
    chính là thứ sẽ phá lại cân bằng vừa sửa.
Kèm phép đo trực tiếp: áp ĐÚNG hệ số đó lên hai lớp rời rồi chạy lại
`do_giong_tren_nhac`.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_lufs import do_ebur128, do_loudnorm  # noqa: E402

DICH_I = -14.0
DICH_TP = -1.0


def main() -> int:
    from app.core import thay_giong as tg

    e2e = REPO / "_do_lt" / "e2e"
    tron = e2e / "_cantieng" / "tron_MỚI.wav"     # bản trộn v2.30.0
    giong = e2e / "_cantieng" / "moi_giong.wav"   # lớp giọng ĐÃ nâng
    nhac = e2e / "_cantieng" / "moi_nhac.wav"     # lớp nhạc ĐÃ hạ + né
    for p in (tron, giong, nhac):
        if not p.exists():
            print(f"THIẾU {p}")
            return 2
    tam = e2e / "_dolt"
    tam.mkdir(parents=True, exist_ok=True)

    print("== TRƯỚC KHI CHUẨN HOÁ ==")
    t0 = do_loudnorm(tron)
    e0 = do_ebur128(tron)
    print(f"  I {t0['input_i']:+7.2f} LUFS · TP {t0['input_tp']:+6.2f} dBTP "
          f"· LRA {t0['input_lra']:5.2f} LU")
    cb0 = tg.do_giong_tren_nhac(giong, nhac)
    print(f"  giọng trên nhạc TB {cb0['giong_tren_nhac_tb']:+.2f} dB "
          f"· cửa sổ CHÌM {cb0['ty_le_chim']}")

    ket = {"truoc": {"I": t0["input_i"], "TP": t0["input_tp"],
                     "LRA": t0["input_lra"], "eb": e0, "can_bang": cb0}}

    # ---------- ARM A: MỘT LƯỢT (động) ----------
    ra_a = tam / "a_motluot.wav"
    ta = time.perf_counter()
    tg._ffmpeg(["-i", str(tron), "-af",
                f"loudnorm=I={DICH_I}:TP={DICH_TP}:LRA=11,"
                f"aresample={tg.SR_TACH}", "-ac", "2",
                "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le", str(ra_a)],
               "chuẩn hoá 1 lượt")
    giay_a = time.perf_counter() - ta

    # ---------- ARM B: HAI LƯỢT (tuyến tính) ----------
    ra_b = tam / "b_hailuot.wav"
    tb = time.perf_counter()
    m = do_loudnorm(tron)          # lượt quét THÊM (giá phải trả của cách này)
    tg._ffmpeg(["-i", str(tron), "-af",
                f"loudnorm=I={DICH_I}:TP={DICH_TP}:LRA=11"
                f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
                f":measured_LRA={m['input_lra']}"
                f":measured_thresh={m['input_thresh']}"
                f":linear=true:print_format=summary,"
                f"aresample={tg.SR_TACH}", "-ac", "2",
                "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le", str(ra_b)],
               "chuẩn hoá 2 lượt")
    giay_b = time.perf_counter() - tb

    print(f"\n{'':26} {'MỘT LƯỢT (động)':>18} {'HAI LƯỢT (tuyến tính)':>22}")
    hang = []
    for ten, p, giay in (("A", ra_a, giay_a), ("B", ra_b, giay_b)):
        d = do_loudnorm(p)
        e = do_ebur128(p)
        # ĐƯỜNG BAO: hệ số áp theo thời gian = SAU − TRƯỚC
        bao0 = tg.duong_bao_muc(tron)
        bao1 = tg.duong_bao_muc(p)
        n = min(len(bao0), len(bao1))
        hs = [bao1[i] - bao0[i] for i in range(n)
              if bao0[i] > -100 and bao1[i] > -100]
        hang.append({"arm": ten, "I": d["input_i"], "TP": d["input_tp"],
                     "LRA": d["input_lra"], "eb_I": e["I"], "eb_TP": e["TP"],
                     "giay": round(giay, 2),
                     "hs_tb": round(statistics.fmean(hs), 3),
                     "hs_dolech": round(statistics.pstdev(hs), 3),
                     "hs_min": round(min(hs), 2), "hs_max": round(max(hs), 2)})

    def _d(k: str, fm: str = "{:+7.2f}") -> str:
        return (f"{fm.format(hang[0][k]):>18} {fm.format(hang[1][k]):>22}")

    print(f"{'I (LUFS) — đích -14':26}" + _d("I"))
    print(f"{'TP (dBTP) — trần -1':26}" + _d("TP"))
    print(f"{'LRA (LU)':26}" + _d("LRA"))
    print(f"{'giây (wall)':26}" + _d("giay", "{:7.2f}"))
    print(f"\n  HỆ SỐ ÁP THEO THỜI GIAN (cái quyết định có phá cân bằng không)")
    print(f"{'  trung bình (dB)':26}" + _d("hs_tb", "{:+7.2f}"))
    print(f"{'  ĐỘ LỆCH CHUẨN (dB)':26}" + _d("hs_dolech", "{:7.3f}"))
    print(f"{'  thấp nhất / cao nhất':26}"
          f"{f'{hang[0]["hs_min"]:+.2f} .. {hang[0]["hs_max"]:+.2f}':>18} "
          f"{f'{hang[1]["hs_min"]:+.2f} .. {hang[1]["hs_max"]:+.2f}':>22}")

    # ---- áp ĐÚNG hệ số trung bình của arm B lên 2 lớp rời rồi đo lại ----
    g = hang[1]["hs_tb"]
    gp, np_ = tam / "b_giong.wav", tam / "b_nhac.wav"
    for src, dst in ((giong, gp), (nhac, np_)):
        tg._ffmpeg(["-i", str(src), "-af", f"volume={g:.3f}dB", "-ac", "2",
                    "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le", str(dst)],
                   f"nâng {dst.name}")
    cb1 = tg.do_giong_tren_nhac(gp, np_)
    print(f"\n== CÂN BẰNG SAU KHI NÂNG {g:+.2f} dB (arm B, áp lên 2 lớp rời) ==")
    for nhan, k in (("giọng trên nhạc — TB", "giong_tren_nhac_tb"),
                    ("— trung vị", "giong_tren_nhac_trung_vi"),
                    ("— thấp nhất", "giong_tren_nhac_min"),
                    ("cửa sổ giọng CHÌM", "so_cua_so_chim"),
                    ("  = % thời lượng nói", "ty_le_chim")):
        print(f"  {nhan:28} {str(cb0.get(k, '-')):>10} -> "
              f"{str(cb1.get(k, '-')):>10}")

    ket["arm"] = hang
    ket["can_bang_sau"] = cb1
    (REPO / "_kq_chuan_do_to.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi: {REPO / '_kq_chuan_do_to.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
