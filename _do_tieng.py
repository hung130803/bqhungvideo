# -*- coding: utf-8 -*-
"""ĐO TIẾNG ĐỘNG BẰNG dB — có trộn hay không, to hay nhỏ, đúng chỗ hay không.

Xuất 1 clip THẬT bằng chính `export_canvas_clip` (2 đoạn -> 1 điểm nối, 2 điểm
nhấn hiệu ứng), rồi bóc PCM và tính RMS từng cửa sổ 50 ms:

  nen_dB   = trung vị RMS toàn clip (nền = giọng nói + tiếng gốc)
  dinh_dB  = RMS đỉnh trong 0,35 s quanh MỖI mốc (điểm nối / điểm nhấn)
  chenh    = dinh_dB - nen_dB  -> "tiếng động nổi hơn nền bao nhiêu dB"

So bản CÓ tiếng động với bản TẮT HẲN (fx_whoosh=False) tại CÙNG mốc: chênh
lệch giữa 2 bản = phần do TIẾNG ĐỘNG đóng góp. Bằng nhau (< 1 dB) nghĩa là
KHÔNG có tiếng nào được trộn vào.

LUẬT SỐ 1: chạy tuần tự, 1 ffmpeg tại một thời điểm.
"""
from __future__ import annotations

import array
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
FF = str(ROOT / "bin" / "ffmpeg.exe")
NOWIN = 0x08000000 if os.name == "nt" else 0
SR = 16000
CUA = 0.05                       # cửa sổ RMS 50 ms


def pcm(path: str) -> array.array:
    r = subprocess.run(
        [FF, "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
         "-f", "s16le", "-"], capture_output=True, creationflags=NOWIN,
        timeout=300)
    a = array.array("h")
    a.frombytes(r.stdout or b"")
    return a


def rms_day(a: array.array) -> list[float]:
    n = int(SR * CUA)
    out = []
    for i in range(0, len(a) - n + 1, n):
        s = 0
        for v in a[i:i + n]:
            s += v * v
        out.append(math.sqrt(s / n))
    return out


def db(x: float) -> float:
    return 20 * math.log10(max(x, 1e-6) / 32768.0)


def trung_vi(xs: list) -> float:
    if not xs:
        return 0.0
    y = sorted(xs)
    return y[len(y) // 2]


def dinh(rs: list, giay: float, rong: float = 0.35) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    return max(rs[i0:i1] or [0.0])


def nguon_co_tieng() -> str:
    kho = Path("D:/video test/Đã tải")
    if kho.is_dir():
        for p in sorted((q for q in kho.iterdir()
                         if q.suffix.lower() in (".mp4", ".mkv", ".webm")),
                        key=lambda q: q.stat().st_size):
            from app.core.ffmpeg_utils import probe
            try:
                if probe(str(p)).has_audio:
                    return str(p)
            except Exception:  # noqa: BLE001
                continue
    raise RuntimeError("không tìm thấy video THẬT có tiếng")


def main() -> int:
    from app.core.ffmpeg_utils import export_canvas_clip
    src = nguon_co_tieng()
    print(f"[nguồn] {Path(src).name[:60]}")
    segs = [(240.0, 245.0), (260.0, 265.0)]     # 10 s ra, 1 điểm nối ở 5,00 s
    hu = [{"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25},
          {"bat": 7.20, "het": 7.60, "khoa": "loe_sang", "dam": 0.25}]
    moc_hu = [1.20, 7.20]
    moc_noi = [5.00]
    td = tempfile.mkdtemp(prefix="_dotieng_")
    try:
        ket = {}
        for ten, whoosh in (("CÓ tiếng động", True), ("TẮT tiếng động", False)):
            dst = os.path.join(td, f"c_{int(whoosh)}.mp4")
            log_hu, log_td = [], []
            export_canvas_clip(
                src, dst, segs, (0.5, 0.5, 1.0), bg="blur",
                out_w=540, out_h=960, encoder="libx264",
                fx_whoosh=whoosh, join_categories=["impact"],
                hieu_ung=hu, hieu_ung_log=log_hu, tieng_dong_log=log_td,
                chuyen_canh="tat")
            a = pcm(dst)
            rs = rms_day(a)
            nen = trung_vi(rs)
            print(f"\n--- {ten} --- ({len(a)/SR:.2f}s tiếng) "
                  f"nền {db(nen):.1f} dB · tiếng động ghi nhận: "
                  f"{[x.get('ten') for x in log_td]}")
            d = {"nen": db(nen)}
            for g in moc_noi:
                d[f"noi@{g}"] = db(dinh(rs, g))
                print(f"   điểm NỐI  {g:5.2f}s -> đỉnh {db(dinh(rs,g)):6.1f} dB"
                      f" (nổi {db(dinh(rs,g))-db(nen):+5.1f} dB so nền)")
            for g in moc_hu:
                d[f"hu@{g}"] = db(dinh(rs, g))
                print(f"   điểm NHẤN {g:5.2f}s -> đỉnh {db(dinh(rs,g)):6.1f} dB"
                      f" (nổi {db(dinh(rs,g))-db(nen):+5.1f} dB so nền)")
            ket[ten] = d
        print("\n" + "=" * 74)
        print(f"{'mốc':<14}{'CÓ tiếng (dB)':>16}{'TẮT tiếng (dB)':>17}"
              f"{'do SFX (dB)':>15}")
        print("-" * 74)
        a1, a0 = ket["CÓ tiếng động"], ket["TẮT tiếng động"]
        for k in a1:
            print(f"{k:<14}{a1[k]:>16.1f}{a0[k]:>17.1f}{a1[k]-a0[k]:>15.1f}")
        print("\nĐọc bảng: cột cuối ~0 dB = KHÔNG có tiếng nào được trộn vào "
              "mốc đó.")
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
