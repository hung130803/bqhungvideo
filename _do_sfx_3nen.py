# -*- coding: utf-8 -*-
r"""ĐO TIẾNG ĐỘNG TRÊN 3 MỨC NỀN — clip THẬT, đo từ PCM của .mp4 đã xuất.

Cổng 44 chỉ đo trên MỘT nguồn nền yên nên không thấy lỗi "clip ồn thì tiếng
động mất hút". Script này xuất 2 bản (BẬT / TẮT tiếng động) trên 3 video THẬT
có nền khác nhau rồi đo tại từng mốc điểm nhấn:

    nền cục bộ   bpv20 đường bao RMS 50 ms trong ±1,5 s quanh mốc (bản TẮT)
    nổi          đỉnh RMS bản BẬT − nền cục bộ            (mốc yêu cầu: >= +6 dB)
    Δ bật−tắt    đỉnh RMS bản BẬT − đỉnh RMS bản TẮT      (không được ÂM)
    lớp SFX      sóng HIỆU (bật − tắt) = riêng tiếng động
    mức lời      bpv90 đường bao RMS của bản TẮT

    .venv\Scripts\python.exe _do_sfx_3nen.py
"""
from __future__ import annotations

import array
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_dosfx3_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as FU        # noqa: E402
from config import settings                    # noqa: E402

FF = settings.FFMPEG_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0
HZ = 8000
CUA = 0.05
RONG = 0.35
KHO = Path("D:/video test/Đã tải")

#: 3 nguồn THẬT đã đo sẵn (`_do_nen_clip.py`): nền yên / trung bình / ồn.
#: mean_volume là thước `_muc_nen_dB` bản cũ dùng — cũng là thước lượt kiểm
#: độc lập báo cáo (-23,6 nguồn cổng 44 · -15,7 clip thật).
CA_NGUON = [
    ("YÊN",  "CHEATING ON GIRLFRIEND PRANK!!", 240.0),        # mean -23,5
    ("T.BÌNH", "Parker and Chester actually saving", 420.0),   # mean -16,4
    ("ỒN",   "BEST CHRISTMAS EVER!!!", 300.0),                 # mean -14,8
]
#: 3 điểm nhấn + 1 điểm nối (giây 7,0 trên timeline đầu ra)
HU_MOC = [
    {"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25},
    {"bat": 4.60, "het": 5.00, "khoa": "glitch_khoi", "dam": 0.25},
    {"bat": 10.40, "het": 10.80, "khoa": "loe_sang", "dam": 0.25},
]


def tim(mo_ta: str) -> str:
    for p in sorted(KHO.iterdir()):
        if p.name.startswith(mo_ta):
            return str(p)
    raise RuntimeError(f"không thấy nguồn: {mo_ta}")


def pcm(path: str) -> array.array:
    r = subprocess.run([FF, "-v", "error", "-nostdin", "-threads", "1",
                        "-i", path, "-vn", "-ac", "1", "-ar", str(HZ),
                        "-f", "s16le", "-"],
                       capture_output=True, creationflags=_NOWIN, timeout=300)
    a = array.array("h")
    a.frombytes(r.stdout or b"")
    return a


def bao_rms(a) -> list[float]:
    n = int(HZ * CUA)
    out = []
    for i in range(0, len(a) - n + 1, n):
        s = 0
        for v in a[i:i + n]:
            s += v * v
        out.append(math.sqrt(s / n))
    return out


def dB(x: float) -> float:
    return 20 * math.log10(max(x, 1e-7) / 32768.0)


def bpv(rs: list, q: float) -> float:
    y = sorted(rs)
    return y[min(len(y) - 1, int(len(y) * q))] if y else 0.0


def nen_cuc_bo(rs: list, giay: float, rong: float = 3.0) -> float:
    """NỀN CỤC BỘ quanh mốc = bpv20 của đường bao trong cửa sổ ±rong/2."""
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    return bpv(rs[i0:i1], 0.20)


def dinh(rs: list, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    return max(rs[i0:i1] or [0.0])


def dinh_mau(a, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) * HZ))
    i1 = min(len(a), int((giay + rong / 2) * HZ))
    return max((abs(v) for v in a[i0:i1]), default=0.0)


def hieu(a, b):
    n = min(len(a), len(b))
    d = array.array("h", bytes(2 * n))
    for i in range(n):
        d[i] = max(-32768, min(32767, a[i] - b[i]))
    return d


def cham_tran(path: str) -> tuple[int, float]:
    """(số mẫu CHẠM TRẦN, đỉnh dBFS) đọc từ `astats` — bằng chứng KHÔNG méo."""
    r = subprocess.run([FF, "-v", "info", "-nostdin", "-threads", "1",
                        "-i", path, "-vn",
                        "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NOWIN, timeout=300)
    # BẪY: mỗi dòng astats bắt đầu bằng "[Parsed_astats_0 @ ...]" nên
    # `startswith("Peak level dB:")` KHÔNG BAO GIỜ khớp -> lượt đo đầu ra
    # -99 dBFS cho mọi file và tưởng là "không có tiếng".
    n, pk = 0, -99.0
    for ln in (r.stderr or "").splitlines():
        if "Peak level dB:" in ln:
            try:
                pk = max(pk, float(ln.split("Peak level dB:")[1]))
            except (ValueError, IndexError):
                pass
        elif "Abs Peak count:" in ln:
            try:
                n = max(n, int(float(ln.split("Abs Peak count:")[1])))
            except (ValueError, IndexError):
                pass
    return (n if pk >= -0.05 else 0), pk


def xuat(src: str, dst: str, segs: list, whoosh: bool, seed: int) -> list:
    random.seed(seed)
    FU._SFX_GAN_DAY.clear()
    log: list = []
    FU.export_canvas_clip(src, dst, segs, (0.5, 0.5, 1.0), bg="blur",
                          out_w=540, out_h=960, encoder="libx264",
                          fx_whoosh=whoosh, join_categories=["impact"],
                          hieu_ung=[dict(c) for c in HU_MOC],
                          tieng_dong_log=log, chuyen_canh="tat")
    return log


def do_mot_ca(ten: str, src: str, ss: float, td: str, seed: int) -> dict:
    segs = [(ss, ss + 7.0), (ss + 30.0, ss + 37.0)]      # nối ở giây 7,0
    os.makedirs(td, exist_ok=True)
    a = os.path.join(td, f"on_{seed}.mp4")
    b = os.path.join(td, "off.mp4")
    log = xuat(src, a, segs, True, seed)
    if not os.path.exists(b):
        xuat(src, b, segs, False, seed)
    pa, pb = pcm(a), pcm(b)
    ra, rb = bao_rms(pa), bao_rms(pb)
    pl = hieu(pa, pb)
    rl = bao_rms(pl)
    loi = dB(bpv(rb, 0.90))
    mocs = sorted([7.0] + [float(c["bat"]) for c in HU_MOC])
    hang = []
    for g in mocs:
        nb = dB(nen_cuc_bo(rb, g))
        on, off = dB(dinh(ra, g)), dB(dinh(rb, g))
        hang.append({"giay": g, "nen": nb, "on": on, "off": off,
                     "noi": on - nb, "delta": on - off,
                     "sfx_rms": dB(dinh(rl, g)),
                     "sfx_dinh": dB(dinh_mau(pl, g))})
    ncham, pk = cham_tran(a)
    ncham_b, pk_b = cham_tran(b)          # bản TẮT: mốc đối chứng cho đỉnh
    return {"ten": ten, "loi": loi, "dinh_tat": pk_b, "cham_tat": ncham_b,
            "mean_nen": dB(
        math.sqrt(sum(float(v) * v for v in pb) / max(1, len(pb)))),
        "hang": hang, "cham_tran": ncham, "dinh_file": pk,
        "log": [(x["giay"], x["loai"], x["ten"], x["db"]) for x in log]}


def in_ca(k: dict) -> None:
    print(f"\n=== NỀN {k['ten']} · mean {k['mean_nen']:.1f} dBFS · "
          f"mức lời (bpv90) {k['loi']:.1f} dBFS ===")
    print(f"  {'mốc':>6} {'nền cục bộ':>11} {'BẬT':>8} {'TẮT':>8} "
          f"{'NỔI':>7} {'Δ b−t':>7} {'lớp SFX rms/đỉnh':>19}")
    for h in k["hang"]:
        c = "  " if h["noi"] >= 6.0 else "!!"
        print(f"{c}{h['giay']:>5.2f}s {h['nen']:>11.1f} {h['on']:>8.1f} "
              f"{h['off']:>8.1f} {h['noi']:>+7.1f} {h['delta']:>+7.1f} "
              f"{h['sfx_rms']:>10.1f} /{h['sfx_dinh']:>7.1f}")
    print(f"  đỉnh file BẬT {k['dinh_file']:.2f} / TẮT {k['dinh_tat']:.2f} dBFS · mẫu chạm trần "
          f"{k['cham_tran']} · SFX đã bốc: "
          + " · ".join(f"{g}s {c}({d:+.0f}dB)" for g, c, _n, d in k["log"]))


def main() -> int:
    td = tempfile.mkdtemp(prefix="_sfx3_", dir=str(_SB))
    ket = []
    try:
        for ten, mota, ss in CA_NGUON:
            src = tim(mota)
            print(f"\n[{ten}] {Path(src).name[:56]} @ {ss:.0f}s")
            k = do_mot_ca(ten, src, ss, os.path.join(td, ten.replace(".", "").replace("Ề","E").replace("Ì","I").replace("Ồ","O")),
                          seed=4242)
            ket.append(k)
            in_ca(k)
        print("\n" + "=" * 78)
        xau = [(k["ten"], h["giay"], h["noi"])
               for k in ket for h in k["hang"] if h["noi"] < 6.0]
        nho = [(k["ten"], h["giay"], h["delta"])
               for k in ket for h in k["hang"] if h["delta"] < 0]
        print(f"mốc KHÔNG đạt +6 dB: {len(xau)}/"
              f"{sum(len(k['hang']) for k in ket)}"
              + ("" if not xau else "  -> " + " · ".join(
                  f"{t}@{g:.2f}s {v:+.1f}" for t, g, v in xau)))
        print(f"mốc NHỎ ĐI (Δ âm): {len(nho)}"
              + ("" if not nho else "  -> " + " · ".join(
                  f"{t}@{g:.2f}s {v:+.1f}" for t, g, v in nho)))
        (REPO / "_ket_sfx3.json").write_text(
            json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
