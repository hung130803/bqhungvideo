# -*- coding: utf-8 -*-
"""CHẠY `ffmpeg_utils.chuan_do_to_clip` THẬT TRÊN 8 BẢN XUẤT — bảng TRƯỚC/SAU.

Gọi ĐÚNG hàm mà đường xuất sẽ gọi (không dựng lệnh ffmpeg riêng), trên BẢN SAO
của 8 file trong `_do_duong/` để không phá bản mốc.

Ba thứ phải chứng minh, không được nói suông:
  1. ĐỘ TO gom lại quanh −14 LUFS (trước: trải 15,75 LU).
  2. **KHÔNG còn clip nào vượt trần −1,0 dBTP** (trước: 3/8 vượt cả 0 dBTP).
  3. **KHÔNG NÉN DẬP**: LRA trước/sau, tụt quá 0,2 là có vấn đề.
Cộng hai phép chống-tự-lừa:
  4. **THƯỚC THỨ HAI** (`loudnorm` pha đo) phải nói cùng chiều với `ebur128`
     — không đòi khớp tuyệt đối vì đã đo được `loudnorm` đọc thấp có hệ thống
     (xem `_do_hai_thuoc.py`), nhưng ĐỘ DỊCH của hai thước phải bằng nhau.
  5. **ĐỘ DÀI**: `-c:v copy` thì độ dài phải giữ nguyên; và chạy 5 lượt phải
     ra ĐÚNG MỘT con số (bài học `asplit` làm độ dài không tiền định).
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_lufs import do_ebur128, do_loudnorm  # noqa: E402


def main() -> int:
    import os

    # BẢN ffmpeg NÀO ĐANG CHẠY — phải in ra, vì máy này có HAI bản và chúng
    # cho kết quả `alimiter` KHÁC NHAU khi không quá mẫu (xem docstring của
    # `QUA_MAU_HAN_DINH`). `BQ_FF=bin` để ép dùng bản đóng gói.
    if os.environ.get("BQ_FF") == "bin":
        os.environ["FFMPEG_PATH"] = str(REPO / "bin" / "ffmpeg.exe")
        os.environ["FFPROBE_PATH"] = str(REPO / "bin" / "ffprobe.exe")

    from config import settings

    from app.core import ffmpeg_utils as fu

    import subprocess as _sp
    _v = _sp.run([settings.FFMPEG_PATH, "-version"], capture_output=True,
                 timeout=60, stdin=_sp.DEVNULL).stdout.decode("utf-8", "replace")
    print(f"ffmpeg app đang dùng: {settings.FFMPEG_PATH}")
    print(f"  {_v.splitlines()[0][:80]}\n")

    goc_dir = REPO / "_do_duong"
    lam = REPO / "_do_duong" / "_chuan"
    if lam.exists():
        shutil.rmtree(lam, ignore_errors=True)
    lam.mkdir(parents=True, exist_ok=True)

    files = sorted(goc_dir.glob("cat_*.mp4")) + sorted(goc_dir.glob("ghep_*.mp4"))
    if not files:
        print("KHÔNG có file trong _do_duong/ — chạy _do_lufs_duong.py trước.")
        return 2

    ra = []
    print("=" * 108)
    print("CHẠY `chuan_do_to_clip` THẬT (thước ebur128) — TRƯỚC/SAU")
    print("=" * 108)
    print(f"{'file':16} | {'I':>7} {'TP':>6} {'LRA':>6} | {'nâng':>7} {'b':>1} | "
          f"{'I':>7} {'TP':>6} {'LRA':>6} | {'ΔLRA':>6} {'giây':>5} | ghi chú")
    print("-" * 108)
    for f in files:
        d = lam / f.name
        shutil.copy2(f, d)
        t0 = time.perf_counter()
        kq = fu.chuan_do_to_clip(d)
        dt = time.perf_counter() - t0

        # thước THỨ HAI, độc lập
        ln_sau = do_loudnorm(d)
        eb_sau = do_ebur128(d)
        tr, sa = kq["truoc"], kq.get("sau", kq["truoc"])
        note = kq.get("ly_do", "") or ("" if kq["buoc"] == 1 else "")
        ra.append({**kq, "giay": round(dt, 2), "ln_sau_I": ln_sau["input_i"],
                   "eb_kiem_I": eb_sau["I"]})
        print(f"{f.name:16} | {tr['I']:7.2f} {tr['TP']:6.2f} {tr['LRA']:6.2f} | "
              f"{kq['nang_db']:+7.2f} {kq['buoc']:1d} | "
              f"{sa['I']:7.2f} {sa['TP']:6.2f} {sa['LRA']:6.2f} | "
              f"{-kq.get('lra_tut', 0.0):+6.2f} {dt:5.2f} | {note[:38]}")

    print("-" * 108)
    Is = [r["sau"]["I"] for r in ra]
    TPs = [r["sau"]["TP"] for r in ra]
    tut = [r.get("lra_tut", 0.0) for r in ra]
    print(f"ĐỘ TO: thấp nhất {min(Is):.2f} · cao nhất {max(Is):.2f} · "
          f"**TRẢI {max(Is) - min(Is):.2f} LU** (trước khi sửa: 15,75 LU "
          f"theo loudnorm / 16,00 LU theo ebur128)")
    n_vo = sum(1 for t in TPs if t > -1.0 + 1e-9)
    n_vo0 = sum(1 for t in TPs if t > 0.0)
    print(f"ĐỈNH: cao nhất {max(TPs):+.2f} dBTP · vượt trần −1,0: {n_vo}/{len(ra)}"
          f" · vượt 0 dBTP (VỠ TIẾNG): {n_vo0}/{len(ra)}   "
          f"(trước khi sửa: 3/8 vượt 0 dBTP)")
    print(f"NÉN DẬP: LRA tụt nhiều nhất {max(tut):+.2f} LU (trần {fu.LRA_TUT_TOI_DA})")
    print(f"THỜI GIAN: tổng {sum(r['giay'] for r in ra):.1f}s cho {len(ra)} clip "
          f"= {sum(r['giay'] for r in ra) / len(ra):.2f}s/clip")

    # ---- phép 4: hai thước phải DỊCH BẰNG NHAU ----
    print("\nĐỐI CHIẾU THƯỚC THỨ HAI (loudnorm) — lệch tuyệt đối là ĐÃ BIẾT, "
          "cái phải khớp là ĐỘ DỊCH:")
    xau = 0
    for r in ra:
        l = r["ln_sau_I"] - r["sau"]["I"]
        if abs(l) > 0.8:
            xau += 1
            print(f"  {r['file']:16} loudnorm {r['ln_sau_I']:7.2f} vs "
                  f"ebur128 {r['sau']['I']:7.2f}  lệch {l:+.2f} LU  <-- TO")
    print(f"  số file hai thước lệch quá 0,8 LU: {xau}/{len(ra)}")

    # ---- phép 5: độ dài TIỀN ĐỊNH (5 lượt cùng 1 file) ----
    print("\nĐỘ DÀI CÓ TIỀN ĐỊNH KHÔNG (5 lượt trên cùng 1 file):")
    mau = files[1]
    dais = []
    for i in range(5):
        d5 = lam / f"_lap{i}.mp4"
        shutil.copy2(mau, d5)
        fu.chuan_do_to_clip(d5)
        dais.append(round(fu.probe(d5).duration, 3))
        d5.unlink(missing_ok=True)
    goc_dai = round(fu.probe(mau).duration, 3)
    print(f"  gốc {goc_dai:.3f}s -> 5 lượt: {dais}  "
          f"=> {'MỘT con số duy nhất' if len(set(dais)) == 1 else 'KHÔNG TIỀN ĐỊNH'}")

    (REPO / "_kq_chuan_duong.json").write_text(
        json.dumps({"bang": ra, "dai_5luot": dais, "dai_goc": goc_dai},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi: {REPO / '_kq_chuan_duong.json'}")
    shutil.rmtree(lam, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
