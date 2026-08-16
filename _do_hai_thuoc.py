# -*- coding: utf-8 -*-
"""HAI THƯỚC LỆCH 0,58 LU TRÊN MỘT FILE — TRUY XEM THƯỚC NÀO HỎNG.

Luật đã chốt: *đo bằng HAI thước độc lập, lệch > 0,5 LU thì DỪNG*. Lượt hiệu
chuẩn `_do_got_lra.py` DỪNG thật ở `cat_7963.mp4` (loudnorm −10,78 · ebur128
−10,20). Trước khi đi tiếp phải trả lời được: **thước nào sai, và có ảnh hưởng
tới phép tính hệ số nâng không?**

Ba phép, mỗi phép trả lời một câu:
 1. LỆCH CÓ TIỀN ĐỊNH KHÔNG (chạy lại 2 lượt) — nhiễu hay tính chất của file.
 2. **THƯỚC CÓ TUYẾN TÍNH KHÔNG**: nhân file với một hệ số ĐÃ BIẾT rồi xem cả
    hai thước có dịch đúng bằng đó không. Đây mới là tính chất mà việc "nâng
    thuần" cần: nếu cả hai đều dịch đúng, thì hệ số tính từ thước A vẫn đưa
    thước A về đích, và phần lệch A-B chỉ là chỗ hai bộ CỔNG (gating) chia
    khối khác nhau — không phải phép đo hỏng.
 3. THƯỚC THỨ BA ĐỘC LẬP (tự viết theo ITU-R BS.1770-4 bằng numpy, không dùng
    ffmpeg) để phá thế hoà: nó đứng gần thước nào.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_lufs import do_ebur128, do_loudnorm  # noqa: E402

FF = REPO / "bin" / "ffmpeg.exe"


def _lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _nhan(src: Path, dst: Path, db: float) -> None:
    """Nhân biên độ với hệ số TĨNH đã biết — KHÔNG hạn đỉnh, KHÔNG nén."""
    r = subprocess.run(
        [str(FF), "-y", "-hide_banner", "-nostdin", "-i", str(src),
         "-map", "0:a:0", "-af", f"volume={db:.4f}dB",
         "-c:a", "pcm_s24le", "-ar", "48000", str(dst)],
        capture_output=True, timeout=900, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-400:])
    if not dst.exists() or dst.stat().st_size < 1024:
        raise RuntimeError(f"ffmpeg mã 0 mà file rỗng: {dst}")


# ---------------------------------------------------------------- thước 3
def thuoc_python(wav: Path) -> dict:
    """ITU-R BS.1770-4 tự viết: K-weighting + cổng tuyệt đối/tương đối.

    KHÔNG gọi ffmpeg — đây là điểm của phép này. Đọc wav 24-bit bằng `wave`
    rồi tính bằng numpy.
    """
    import wave

    import numpy as np

    with wave.open(str(wav), "rb") as w:
        nch, sw, sr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if sw == 3:            # 24-bit little endian -> int32
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        x = (a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16))
        x = np.where(x & 0x800000, x - 0x1000000, x).astype(np.float64) / 8388608.0
    elif sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    else:
        raise RuntimeError(f"bề rộng mẫu chưa hỗ trợ: {sw}")
    x = x.reshape(-1, nch)

    # --- bộ lọc K (BS.1770-4, hệ số cho 48 kHz) ---
    def _iir(sig, b, a):
        from scipy.signal import lfilter          # noqa: PLC0415
        return lfilter(b, a, sig, axis=0)

    # tầng 1: shelf cao
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    # tầng 2: thông cao
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    if sr != 48000:
        raise RuntimeError(f"hệ số bộ lọc K chỉ cho 48 kHz, file {sr} Hz")
    y = _iir(_iir(x, b1, a1), b2, a2)

    # --- khối 400 ms, chồng 75% ---
    import numpy as np
    n_blk = int(0.4 * sr)
    hop = n_blk // 4
    G = np.array([1.0, 1.0, 1.0, 1.41, 1.41][:y.shape[1]])
    nb = 1 + max(0, (len(y) - n_blk) // hop)
    z = np.empty(nb)
    for i in range(nb):
        seg = y[i * hop:i * hop + n_blk]
        z[i] = float(np.sum(G[:seg.shape[1]] * np.mean(seg ** 2, axis=0)))
    with np.errstate(divide="ignore"):
        l_blk = -0.691 + 10.0 * np.log10(np.maximum(z, 1e-30))

    giu = l_blk > -70.0                     # cổng TUYỆT ĐỐI
    if not giu.any():
        return {"I": float("-inf"), "n_khoi": int(nb)}
    l_tb = -0.691 + 10.0 * np.log10(np.mean(z[giu]))
    giu2 = giu & (l_blk > l_tb - 10.0)      # cổng TƯƠNG ĐỐI
    I = -0.691 + 10.0 * np.log10(np.mean(z[giu2]))
    return {"I": float(I), "n_khoi": int(nb), "nguong_tuong_doi": float(l_tb - 10.0),
            "khoi_qua_cong": int(giu2.sum())}


def main() -> int:
    tam = REPO / "_do_duong"
    files = sorted(tam.glob("cat_*.mp4")) + sorted(tam.glob("ghep_*.mp4"))
    print("=" * 90)
    print("PHÉP 1 — LỆCH GIỮA HAI THƯỚC TRÊN CẢ 8 BẢN XUẤT (có tiền định không)")
    print("=" * 90)
    print(f"{'file':16} {'loudnorm I':>11} {'ebur128 I':>10} {'lệch':>7} "
          f"{'LRA ln':>7} {'LRA eb':>7}")
    bang = []
    for f in files:
        ln, eb = do_loudnorm(f), do_ebur128(f)
        d = ln["input_i"] - eb["I"]
        bang.append({"file": f.name, "ln": ln["input_i"], "eb": eb["I"],
                     "lech": round(d, 3), "lra_ln": ln["input_lra"],
                     "lra_eb": eb["LRA"]})
        co = "   <-- LỆCH > 0,5" if abs(d) > 0.5 else ""
        print(f"{f.name:16} {ln['input_i']:11.2f} {eb['I']:10.2f} {d:+7.3f} "
              f"{ln['input_lra']:7.2f} {eb['LRA']:7.2f}{co}")

    xau = max(bang, key=lambda r: abs(r["lech"]))
    src = tam / xau["file"]
    print(f"\nCa lệch nhất: {xau['file']} ({xau['lech']:+.3f} LU)")

    print("\n" + "=" * 90)
    print("PHÉP 2 — THƯỚC CÓ TUYẾN TÍNH KHÔNG (nhân hệ số ĐÃ BIẾT rồi đo lại)")
    print("=" * 90)
    print(f"{'hệ số':>8} {'loudnorm I':>11} {'dịch':>8} {'ebur128 I':>10} "
          f"{'dịch':>8} {'lệch A-B':>9}")
    quet = []
    goc_ln, goc_eb = xau["ln"], xau["eb"]
    for db in (-6.0, -3.0, 0.0, +3.0):
        w = tam / f"_tt_{int(abs(db) * 10):03d}{'m' if db < 0 else 'p'}.wav"
        _nhan(src, w, db)
        ln, eb = do_loudnorm(w), do_ebur128(w)
        quet.append({"db": db, "ln": ln["input_i"], "eb": eb["I"],
                     "d_ln": round(ln["input_i"] - goc_ln, 3),
                     "d_eb": round(eb["I"] - goc_eb, 3)})
        print(f"{db:+8.2f} {ln['input_i']:11.2f} {ln['input_i'] - goc_ln:+8.3f} "
              f"{eb['I']:10.2f} {eb['I'] - goc_eb:+8.3f} "
              f"{ln['input_i'] - eb['I']:+9.3f}")
        if abs(db) < 0.01:
            gia = w          # giữ bản 0 dB cho phép 3
        else:
            w.unlink(missing_ok=True)

    print("\n" + "=" * 90)
    print("PHÉP 3 — THƯỚC THỨ BA (tự viết BS.1770-4, KHÔNG dùng ffmpeg)")
    print("=" * 90)
    try:
        t3 = thuoc_python(gia)
        print(f"  thước 3 (python)  I = {t3['I']:+.2f} LUFS   "
              f"({t3['khoi_qua_cong']}/{t3['n_khoi']} khối qua cổng, "
              f"ngưỡng tương đối {t3['nguong_tuong_doi']:.2f})")
        print(f"  loudnorm          I = {goc_ln:+.2f}   -> lệch "
              f"{t3['I'] - goc_ln:+.3f} LU")
        print(f"  ebur128           I = {goc_eb:+.2f}   -> lệch "
              f"{t3['I'] - goc_eb:+.3f} LU")
        gan = "loudnorm" if abs(t3["I"] - goc_ln) < abs(t3["I"] - goc_eb) else "ebur128"
        print(f"  => thước 3 ĐỨNG GẦN **{gan}**")
    except Exception as e:      # noqa: BLE001
        t3 = {"loi": str(e)}
        print(f"  thước 3 KHÔNG chạy được: {e}")
    gia.unlink(missing_ok=True)

    (REPO / "_kq_hai_thuoc.json").write_text(
        json.dumps({"bang": bang, "tuyen_tinh": quet, "thuoc3": t3},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi: {REPO / '_kq_hai_thuoc.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
