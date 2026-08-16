# -*- coding: utf-8 -*-
"""BIÊN TRỪ HAO ĐỈNH CHO ĐƯỜNG **CẮT THƯỜNG** PHẢI ĐO LẠI — 0,5 dB LÀ KHÔNG ĐỦ.

Đường THAY TIẾNG đo được `alimiter` vọt **+0,06 dB** rồi AAC vọt tiếp **+0,19
dB**, nên biên 0,5 dB thừa sức. Nhưng đó là bản TRỘN (LRA 2,10, đã nén sẵn).
Nguồn CẮT THƯỜNG là phim thô: `_do_got_lra.py` đo được clip **hệ số đỉnh/độ to
22,8 dB**, và ở đó `alimiter` đặt trần −1,5 lại cho ra đỉnh thật **−0,90 dBTP**
= vọt **0,60 dB**, tức **VẪN VƯỢT trần −1,0**. Gọt càng sâu vọt càng nhiều
(gọt 10,3 dB -> −0,50 dBTP = vọt 1,00 dB).

Nên biên phải ĐO LẠI trên chính 8 bản xuất thật, quét 4 mức, rồi lấy mức NHỎ
NHẤT mà **cả 8 file** đều nằm dưới trần.

Thước: `ebur128` (xem `_do_hai_thuoc.py` — `loudnorm` pha đo đọc THẤP tới
0,58 LU, thước thứ ba tự viết đứng về phía `ebur128`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_lufs import do_ebur128  # noqa: E402

FF = REPO / "bin" / "ffmpeg.exe"
DICH = -14.0
TRAN_TP = -1.0
NGAN_SACH_GOT = 6.0             # dB — chốt từ `_do_got_lra.py` (ΔLRA = 0,00)
BIEN_QUET = [0.5, 1.0, 1.5, 2.0]


def _lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _ap(src: Path, dst: Path, nang: float, tran_lim: float) -> None:
    cmd = [str(FF), "-y", "-hide_banner", "-nostdin", "-i", str(src),
           "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
           "-af", (f"volume={nang:.3f}dB,"
                   f"alimiter=limit={_lin(tran_lim):.6f}"
                   f":level=0:latency=1:attack=1:release=10"),
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)]
    r = subprocess.run(cmd, capture_output=True, timeout=900,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-400:])
    if not dst.exists() or dst.stat().st_size < 1024:
        raise RuntimeError(f"ffmpeg mã 0 mà file rỗng: {dst}")


def main() -> int:
    tam = REPO / "_do_duong"
    files = sorted(tam.glob("cat_*.mp4")) + sorted(tam.glob("ghep_*.mp4"))
    goc = {}
    print("Đo lại 8 bản xuất (ebur128)...", flush=True)
    for f in files:
        goc[f.name] = do_ebur128(f)

    ra = []
    for bien in BIEN_QUET:
        tran_lim = TRAN_TP - bien
        print("\n" + "=" * 96)
        print(f"BIÊN = {bien:.1f} dB   (trần alimiter {tran_lim:+.1f} dBFS)")
        print("=" * 96)
        print(f"{'file':16} {'I gốc':>7} {'TP gốc':>7} {'nâng':>7} {'gọt':>6} "
              f"{'I sau':>7} {'TP sau':>7} {'LRA sau':>8} {'ΔLRA':>6} "
              f"{'vọt':>6} {'vượt trần?':>11}")
        n_vuot = 0
        for f in files:
            g = goc[f.name]
            nang_du = DICH - g["I"]
            got = max(0.0, (g["TP"] + nang_du) - tran_lim)
            nang = (nang_du if got <= NGAN_SACH_GOT
                    else (tran_lim + NGAN_SACH_GOT) - g["TP"])
            got_that = max(0.0, (g["TP"] + nang) - tran_lim)
            out = tam / f"_bd_{f.stem}.mp4"
            _ap(f, out, nang, tran_lim)
            s = do_ebur128(out)
            vot = s["TP"] - tran_lim
            vuot = s["TP"] > TRAN_TP + 1e-9
            n_vuot += int(vuot)
            ra.append({"bien": bien, "file": f.name, "nang": round(nang, 2),
                       "got": round(got_that, 2), "I": s["I"], "TP": s["TP"],
                       "LRA": s["LRA"], "d_LRA": round(s["LRA"] - g["LRA"], 2),
                       "vot": round(vot, 2), "vuot_tran": bool(vuot)})
            print(f"{f.name:16} {g['I']:7.2f} {g['TP']:7.2f} {nang:+7.2f} "
                  f"{got_that:6.2f} {s['I']:7.2f} {s['TP']:7.2f} "
                  f"{s['LRA']:8.2f} {s['LRA'] - g['LRA']:+6.2f} {vot:+6.2f} "
                  f"{'VƯỢT' if vuot else 'ok':>11}")
            out.unlink(missing_ok=True)
        print(f"  -> số file VƯỢT trần {TRAN_TP:+.1f} dBTP: {n_vuot}/{len(files)}")
        if n_vuot == 0:
            print(f"  -> BIÊN {bien:.1f} dB LÀ ĐỦ (mức nhỏ nhất tìm được)")
            break

    (REPO / "_kq_bien_dinh.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi: {REPO / '_kq_bien_dinh.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
