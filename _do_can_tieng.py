# -*- coding: utf-8 -*-
"""LỖI 2 — TRƯỚC/SAU cân mức giọng-nhạc, đo trên CHÍNH file của lượt chạy thật.

Không chạy lại cả dây chuyền (mỗi lượt ~9 phút): lấy `tieng_moi.giong.wav`
(track giọng mới) và `tach/lop_nhac.wav` (lớp nhạc gốc) rồi dựng lại ĐÚNG hai
cách trộn — CŨ (hai hằng số 0 / −2 dB) và MỚI (đo → nén → đo lại → nâng, cộng
nhạc né giọng) — để so bằng cùng một thước.

Thước: `thay_giong.do_giong_tren_nhac` = giọng cao hơn nhạc bao nhiêu dB **lúc
đang nói** (không phải RMS cả track: track giọng ~30% là im lặng nên RMS toàn
bài luôn thấp giả tạo).
Kèm 2 ràng buộc phải giữ: bản trộn KHÔNG méo hơn, và NHẠC KHÔNG bị mất.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))


def _ren(tg, src: Path, dst: Path, af: str) -> None:
    tg._ffmpeg(["-i", str(src), "-af", af, "-ac", "2", "-ar", str(tg.SR_TACH),
                "-c:a", "pcm_s16le", str(dst)], f"dựng {dst.name}")


def _ren_duck(tg, nhac: Path, giong: Path, dst: Path, g_nhac: float,
              g_giong: float, nguong: float, ratio: float) -> None:
    fc = (f"[0:a]volume={g_nhac:.2f}dB[nh0];"
          f"[1:a]volume={g_giong:.2f}dB[gi];"
          f"[nh0][gi]sidechaincompress=threshold={nguong:.6f}:"
          f"ratio={ratio:.3f}:attack=20:release=300:makeup=1:level_sc=1[out]")
    tg._ffmpeg(["-i", str(nhac), "-i", str(giong), "-filter_complex", fc,
                "-map", "[out]", "-ac", "2", "-ar", str(tg.SR_TACH),
                "-c:a", "pcm_s16le", str(dst)], f"dựng {dst.name}")


def main() -> int:
    from app.core import thay_giong as tg

    e2e = Path(sys.argv[1] if len(sys.argv) > 1 else REPO / "_do_lt" / "e2e")
    giong = e2e / "tieng_moi.giong.wav"
    nhac = e2e / "tach" / "lop_nhac.wav"
    if not giong.exists() or not nhac.exists():
        print(f"THIẾU {giong.name} hoặc {nhac.name}")
        return 2
    tam = e2e / "_cantieng"
    tam.mkdir(parents=True, exist_ok=True)

    print("== ĐO GỐC (chưa chỉnh gì) ==")
    print(" ", json.dumps(tg.do_giong_tren_nhac(giong, nhac),
                          ensure_ascii=False))

    cb0 = tg.can_bang_giong_nhac(giong, nhac)
    nen_p = tam / "giong_nen.wav"
    tg.nen_lop_giong(giong, nen_p, float(cb0["muc_giong_luc_noi_db"]))
    cb = tg.can_bang_giong_nhac(nen_p, nhac)
    print("\n== HỆ SỐ APP TỰ TÍNH (vòng 1 THÔ -> nén -> vòng 2) ==")
    print("  vòng 1:", json.dumps(cb0, ensure_ascii=False))
    print("  vòng 2:", json.dumps(cb, ensure_ascii=False))

    # --- CŨ: giọng +0 dB, nhạc -2 dB, KHÔNG nén, KHÔNG né
    g_cu, n_cu = tam / "cu_giong.wav", tam / "cu_nhac.wav"
    _ren(tg, giong, g_cu, "volume=0.00dB")
    _ren(tg, nhac, n_cu, "volume=-2.00dB")
    cu = tg.do_giong_tren_nhac(g_cu, n_cu)

    # --- MỚI: nén + hệ số ĐO ĐƯỢC + nhạc NÉ giọng
    g_moi, n_moi = tam / "moi_giong.wav", tam / "moi_nhac.wav"
    gg = cb["gain_giong_db"]
    gn = cb["gain_nhac_db"]
    _ren(tg, nen_p, g_moi, f"volume={gg:.2f}dB")
    ng, rt = tg._tham_so_duck(cb["muc_nhac_luc_noi_db"] + gn)
    _ren_duck(tg, nhac, nen_p, n_moi, gn, gg, ng, rt)
    moi = tg.do_giong_tren_nhac(g_moi, n_moi)

    print("\n== GIỌNG TRÊN NHẠC LÚC ĐANG NÓI (dB, càng dương càng nghe rõ) ==")
    print(f"{'':34} {'CŨ':>10} {'MỚI':>10}")
    for nhan, k in (("trung bình", "giong_tren_nhac_tb"),
                    ("trung vị", "giong_tren_nhac_trung_vi"),
                    ("thấp nhất", "giong_tren_nhac_min"),
                    ("cửa sổ giọng CHÌM dưới nhạc", "so_cua_so_chim"),
                    ("  = % thời lượng đang nói", "ty_le_chim")):
        print(f"{nhan:34} {cu.get(k, '-'):>10} {moi.get(k, '-'):>10}")
    print(f"{'ĐÍCH đặt ra':34} {'':>10} "
          f"{tg.DICH_GIONG_TREN_NHAC_DB + tg.DUCK_DB_DO_DUOC:>10}"
          f"   (tĩnh {tg.DICH_GIONG_TREN_NHAC_DB} + né {tg.DUCK_DB_DO_DUOC})")

    print("\n== NHẠC CÓ BỊ MẤT KHÔNG (RMS toàn bài, so lớp nhạc gốc) ==")
    r0 = tg.do_rms(nhac)
    for ten, p in (("CŨ  (-2 dB tĩnh)", n_cu), ("MỚI (đo + né giọng)", n_moi)):
        print(f"  {ten:24} "
              f"{20 * math.log10(max(1e-9, tg.do_rms(p) / r0)):+6.2f} dB")

    print("\n== BẢN TRỘN CUỐI: MÉO / ĐỈNH ==")
    for ten, gp, np_ in (("CŨ", g_cu, n_cu), ("MỚI", g_moi, n_moi)):
        out = tam / f"tron_{ten}.wav"
        fc = ("[0:a][1:a]amix=inputs=2:duration=first:normalize=0[mx];"
              f"[mx]alimiter=level_in=1:level_out=1:limit="
              f"{10.0 ** (tg.TRAN_DINH_DB / 20.0):.6f}:level=0:latency=1[out]")
        tg._ffmpeg(["-i", str(np_), "-i", str(gp), "-filter_complex", fc,
                    "-map", "[out]", "-ac", "2", "-ar", str(tg.SR_TACH),
                    "-c:a", "pcm_s16le", str(out)], f"trộn {ten}")
        m, mg = tg.do_meo(out), tg.do_meo(gp)
        print(f"  {ten:4} đỉnh {m.get('dinh'):8.4f} dBFS · chạm trần "
              f"{m.get('cham_tran'):5} mẫu · RMS {tg.do_rms(out):.6f}"
              f"  | đỉnh nhánh GIỌNG {mg.get('dinh'):7.2f} dBFS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
