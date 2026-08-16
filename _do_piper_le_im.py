# -*- coding: utf-8 -*-
"""ĐO LỀ IM CỦA WAV PIPER — CÂU và CHỮ RỜI, bằng HAI THƯỚC ĐỘC LẬP.

VÌ SAO CÓ FILE NÀY: `CLAUDE.md` chẩn `_co_gian` lệch +33,0 ms vì *"Piper cũng
chèn lề im như edge-tts"* — nhưng đó là SUY LUẬN, chưa ai đo. Bản vá đầu tiên
neo mốc theo lề im thì bộ tự-kiểm của cổng 64 báo **lề = 0,000 s**, tức hoặc
thước hỏng, hoặc chẩn đoán sai. Phải tách hai khả năng đó ra bằng số.

HAI THƯỚC:
  · `piper_tts.le_im_wav`      — đọc thẳng mẫu WAV (thước mới, đang nghi)
  · `thay_giong.do_le_im`      — ffmpeg `silencedetect` (thước app vẫn dùng)
Hai thước cùng ngưỡng −45 dBFS. Chúng phải GẶP NHAU; lệch nhau là thước mới sai.

    .venv\\Scripts\\python -u _do_piper_le_im.py
"""
from __future__ import annotations

import shutil
import sys
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

CAU = ["Con đường gần nhà tôi giờ đã khác xưa rất nhiều rồi.",
       "Tôi đi bộ trên con đường đó tới tận bây giờ vẫn thấy vui.",
       "Hôm nay, tôi sẽ chia sẻ với các bạn một câu chuyện rất thú vị, "
       "mà tôi đã gặp cách đây ba phút, khi đang đi bộ trên con đường "
       "quen thuộc gần nhà mình."]


def im_ben_trong(p, nguong_db: float = -45.0, cua_so: float = 0.01):
    """Liệt kê MỌI khoảng im trong file, kể cả im GIỮA câu.

    Đây là chỗ phép đo trước bỏ sót: `do_le_im` cố ý CHỈ nhìn im DÍNH MÉP.
    """
    import array
    import wave
    with wave.open(str(p), "rb") as w:
        sr = float(w.getframerate() or 1)
        n = w.getnframes()
        raw = w.readframes(n)
    a = array.array("h")
    a.frombytes(raw[:(len(raw) // 2) * 2])
    nguong = 32768.0 * (10.0 ** (nguong_db / 20.0))
    buoc = max(1, int(sr * cua_so))
    to = []
    for i in range(0, len(a), buoc):
        k = a[i:i + buoc]
        to.append(max(max(k), -min(k)) >= nguong)
    khoang, i = [], 0
    while i < len(to):
        if to[i]:
            i += 1
            continue
        j = i
        while j < len(to) and not to[j]:
            j += 1
        khoang.append((i * buoc / sr, j * buoc / sr))
        i = j
    return khoang, n / sr


def main() -> int:
    from app.core import piper_tts as PT
    from app.core import thay_giong as TG

    d = REPO / f"bq_leim_{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    try:
        ps = [str(d / f"c{i}.wav") for i in range(len(CAU))]
        ok, moc = PT.doc_loat(CAU, ps, lay_moc=False)
        print(f"đọc câu: ok={ok}")
        if not all(ok):
            print("KHÔNG đọc được -> dừng, KHÔNG kết luận")
            return 1

        print("\n--- LỀ IM CỦA *CÂU* (đây là chỗ `_co_gian` neo vào) ---")
        print(f"{'file':<8} {'tổng':>8} | {'MỚI đầu':>9} {'MỚI cuối':>9} "
              f"| {'ffmpeg đầu':>11} {'ffmpeg cuối':>12}")
        for p in ps:
            a1, b1, t1 = PT.le_im_wav(p)
            a2, b2, t2 = TG.do_le_im(p)
            print(f"{Path(p).name:<8} {t1:>8.3f} | {a1:>9.3f} {b1:>9.3f} "
                  f"| {a2:>11.3f} {b2:>12.3f}")

        print("\n--- IM *BÊN TRONG* CÂU (chỗ `do_le_im` cố ý KHÔNG nhìn) ---")
        for p in ps:
            kh, tong = im_ben_trong(p)
            for nguong in (0.03, 0.06, 0.10):
                loc = [(a, b) for a, b in kh if b - a >= nguong]
                tong_im = sum(b - a for a, b in loc)
                print(f"  {Path(p).name:<8} im>={nguong * 1000:>3.0f}ms: "
                      f"{len(loc):>2} khoảng · tổng {tong_im:>6.3f}s "
                      f"= {100 * tong_im / max(tong, 1e-9):>4.1f}% câu "
                      f"· {[f'{a:.2f}-{b:.2f}' for a, b in loc[:6]]}")

        # --- chữ rời: đây mới là chỗ có thể có lề ---
        print("\n--- LỀ IM CỦA *CHỮ RỜI* (chỗ lấy độ dài để chia tỉ lệ) ---")
        d_tu = d / "tu"
        d_tu.mkdir(parents=True, exist_ok=True)
        rieng = []
        for c in CAU:
            for t in c.split():
                s = PT._lam_sach(t).lower()
                if s and s not in rieng:
                    rieng.append(s)
        rc, err = PT._chay(["-d", str(d_tu), "--output-dir-naming", "text"],
                           vao="\n".join(rieng), han=600)
        print(f"đọc {len(rieng)} chữ rời: rc={rc} {err[:80] if rc else ''}")
        if rc != 0:
            return 1
        print(f"{'chữ':<12} {'tổng':>8} {'MỚI đầu':>9} {'MỚI cuối':>9} "
              f"{'ffmpeg đầu':>11} {'ffmpeg cuối':>12} {'CÓ TIẾNG':>9}")
        tong_file = tong_tieng = 0.0
        for t in rieng[:12]:
            p = PT._tra_file(d_tu, t)
            if p is None:
                print(f"{t:<12}  KHÔNG tra ra file")
                continue
            a1, b1, t1 = PT.le_im_wav(p)
            a2, b2, _t2 = TG.do_le_im(p)
            print(f"{t:<12} {t1:>8.3f} {a1:>9.3f} {b1:>9.3f} "
                  f"{a2:>11.3f} {b2:>12.3f} {t1 - a1 - b1:>9.3f}")
        for t in rieng:
            p = PT._tra_file(d_tu, t)
            if p is None:
                continue
            a1, b1, t1 = PT.le_im_wav(p)
            tong_file += t1
            tong_tieng += max(0.0, t1 - a1 - b1)
        print(f"\nTỔNG {len(rieng)} chữ rời: theo FILE {tong_file:.3f}s · "
              f"theo CÓ TIẾNG {tong_tieng:.3f}s "
              f"({(tong_tieng / max(tong_file, 1e-9) - 1) * 100:+.1f}%)")
        print(f"  => lề im chiếm {tong_file - tong_tieng:.3f}s trên "
              f"{len(rieng)} chữ = "
              f"{(tong_file - tong_tieng) / max(1, len(rieng)) * 1000:.1f} "
              f"ms/chữ")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
