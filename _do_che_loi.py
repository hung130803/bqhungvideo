# -*- coding: utf-8 -*-
"""ĐO: TIẾNG ĐỘNG CÓ BỊ **LỜI NÓI** CHE KHÔNG (không phải "có nổi trên NỀN không").

GIẢ THUYẾT anh Hùng tự đoán ra khi nghe clip v2.19.0:
  *"hiệu ứng âm thanh nhỏ quá, nó dùng mà không nghe thấy luôn, NÓI ÁT RỒI hay
  sao"*.

Cổng 44 đang đo **NỔI TRÊN NỀN CỤC BỘ** (bpv20 quanh mốc = lúc IM LẶNG). Tai
người KHÔNG nghe "so với nền" — tai nghe **so với thứ đang phát CÙNG LÚC**. Nếu
mốc rơi đúng lúc đang nói thì thứ phát cùng lúc là GIỌNG NÓI, to hơn nền 10-20
dB. Tiếng động nổi +9 dB trên NỀN vẫn có thể thấp hơn LỜI 8 dB -> bị che.

BA THƯỚC ĐO, mỗi cái trả lời một câu hỏi khác nhau:
  NOI   = đỉnh(BẬT) − nền cục bộ        -> "có nổi trên khoảng lặng không"
                                           (chính là thước của cổng 44)
  SMR   = đỉnh(lớp SFX) − đỉnh(TẮT)      -> "to hơn hay nhỏ hơn thứ đang phát"
  D_DAI = ON_dải − OFF_dải TẠI MỐC       -> **CÁI TAI THẬT SỰ NGHE**

Vì sao D_DAI mới là thước của tai: trong CÙNG một dải tới hạn, tai KHÔNG tách
được tiếng động ra khỏi giọng nói — nó chỉ nghe dải đó TO LÊN bao nhiêu. Cộng 2
nguồn không tương quan: D = 10log10(1 + 10^(SMR/10)).
  SMR  0 dB -> dải to thêm 3,0 dB (nghe rõ)
  SMR −6 dB -> dải to thêm 1,0 dB (đúng ngưỡng vừa phân biệt được — JND cường
               độ của âm phức hợp ~0,5-1 dB)
  SMR −10 dB -> dải to thêm 0,4 dB (DƯỚI ngưỡng = KHÔNG NGHE RA)
Nên mốc "nghe ra được" = có ÍT NHẤT MỘT DẢI to thêm >= 1 dB; "nghe RÕ" >= 3 dB.
Đo D_DAI trên file ĐÃ XUẤT (không phải trên lớp SFX rời) nên nó tính luôn cả
ducking lẫn lớp hạn đỉnh — tức đúng thứ phát ra loa.

Chạy: .venv\\Scripts\\python.exe _do_che_loi.py
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"do_che_loi_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

import numpy as np                            # noqa: E402
from app.core import ffmpeg_utils as FU       # noqa: E402
from app.core import hieu_ung as HU           # noqa: E402
from config import settings                   # noqa: E402

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF = settings.FFMPEG_PATH
SR = 16000
CUA = 0.05                     # cửa sổ RMS 50 ms
RONG = 0.35                    # cửa sổ tìm đỉnh quanh mốc (±0,175 s)
NEN_RONG = 3.0

#: DẢI TẦN. Giọng người dồn 300-3400 Hz; đó là 3 dải giữa. Dải <300 và >4000 là
#: chỗ giọng nói KHÔNG có mấy -> tiếng động đặt năng lượng vào đó thì "được
#: nghe không mất tiền" (không phải đấu với lời).
DAI = [(60, 300), (300, 1000), (1000, 2400), (2400, 4000), (4000, 7800)]
TEN_DAI = ["<300", "300-1k", "1k-2.4k", "2.4k-4k", ">4k"]
#: Ngưỡng "vừa đủ phân biệt" (JND cường độ âm phức hợp) và "nghe rõ".
JND_DB, RO_DB = 1.0, 3.0

KHO_VIDEO = Path(os.environ.get("BQ_KHO_VIDEO") or "D:/video test/Đã tải")


def tim_nguon(mo_ta: str) -> str:
    if KHO_VIDEO.is_dir():
        for p in sorted(KHO_VIDEO.iterdir()):
            if p.name.startswith(mo_ta):
                return str(p)
    raise RuntimeError(f"máy không có video THẬT để đo: {mo_ta}")


def pcm(path: str, dau_vao: list | None = None) -> np.ndarray:
    cmd = [FF, "-v", "error", "-nostdin"]
    cmd += [str(x) for x in (dau_vao or ["-i", path])]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True, creationflags=_NOWIN,
                       timeout=300)
    return np.frombuffer(r.stdout or b"", dtype="<i2").astype(np.float64)


def bao_rms(a: np.ndarray) -> np.ndarray:
    """Đường bao RMS cửa sổ 50 ms, không chồng lấn."""
    n = int(SR * CUA)
    m = len(a) // n
    if m <= 0:
        return np.zeros(0)
    return np.sqrt((a[:m * n].reshape(m, n) ** 2).mean(axis=1))


def db(x) -> float:
    return 20.0 * math.log10(max(float(x), 1e-7) / 32768.0)


def dinh_quanh(rs: np.ndarray, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    seg = rs[i0:i1]
    return float(seg.max()) if len(seg) else 0.0


def nen_cuc_bo(rs: np.ndarray, giay: float) -> float:
    i0 = max(0, int((giay - NEN_RONG / 2) / CUA))
    i1 = min(len(rs), int((giay + NEN_RONG / 2) / CUA) + 1)
    seg = rs[i0:i1]
    return float(np.percentile(seg, 20)) if len(seg) else 0.0


def pho_dai(a: np.ndarray, giay: float, rong: float = RONG) -> np.ndarray:
    """Mức dBFS TỪNG DẢI trong cửa sổ quanh mốc (cửa sổ Hann + FFT).

    Trả mảng len(DAI) giá trị dBFS. Dùng chuẩn hoá theo số mẫu để mức dải cộng
    lại xấp xỉ RMS toàn dải -> so sánh được với các số dB khác trong bài."""
    i0 = max(0, int((giay - rong / 2) * SR))
    i1 = min(len(a), int((giay + rong / 2) * SR))
    x = a[i0:i1]
    if len(x) < 64:
        return np.full(len(DAI), -99.0)
    w = np.hanning(len(x))
    # bù năng lượng cửa sổ Hann (RMS của hann = sqrt(3/8))
    X = np.fft.rfft(x * w) / (len(x) * math.sqrt(3.0 / 8.0) / 2.0)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    out = []
    for lo, hi in DAI:
        m = (f >= lo) & (f < hi)
        e = float((np.abs(X[m]) ** 2).sum()) / 2.0 if m.any() else 0.0
        out.append(20.0 * math.log10(max(math.sqrt(e), 1e-7) / 32768.0))
    return np.array(out)


def do_dinh_file(path: str) -> tuple[float, int]:
    """(đỉnh dBFS, số mẫu CHẠM TRẦN) — `in`, KHÔNG `startswith` (mỗi dòng
    astats mở đầu bằng `[Parsed_astats_0 @ ...]`)."""
    r = subprocess.run([FF, "-v", "info", "-nostdin", "-threads", "1",
                        "-i", path, "-vn",
                        "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NOWIN, timeout=300)
    pk, n = -99.0, 0
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
    return pk, (n if pk >= -0.05 else 0)


def xuat(src: str, dst: str, segs: list, hu, whoosh: bool, **kw) -> list:
    log: list = []
    FU.export_canvas_clip(src, dst, segs, (0.5, 0.5, 1.0), bg="blur",
                          out_w=540, out_h=960, encoder="libx264",
                          fx_whoosh=whoosh, hieu_ung=hu, tieng_dong_log=log,
                          chuyen_canh="tat", **kw)
    return log


# --------------------------------------------------------------- chọn mốc
def chon_moc(src: str, ss: float, dai: float) -> tuple[list, list, dict]:
    """Dò TRƯỚC trên tiếng nguồn: chọn 3 mốc rơi đúng lúc ĐANG NÓI và 3 mốc rơi
    vào KHOẢNG LẶNG. Chỉ giải mã audio, không đụng cửa chờ ffmpeg."""
    a = pcm("", ["-ss", f"{ss:.3f}", "-t", f"{dai:.3f}", "-i", src])
    rs = bao_rms(a)
    loi = float(np.percentile(rs, 90))
    nen = float(np.percentile(rs, 20))
    to, im = [], []
    for i, v in enumerate(rs):
        t = i * CUA
        if t < 1.0 or t > dai - 1.2:
            continue
        # ĐANG NÓI = cửa sổ này nằm trong nhóm to nhất; KHOẢNG LẶNG = nhóm nhỏ
        if v >= loi * 0.9:
            to.append((float(v), t))
        elif v <= nen * 1.6:
            im.append((float(v), t))
    to.sort(reverse=True)
    im.sort()

    def thua(ds, n):
        ra: list[float] = []
        for _v, t in ds:
            if all(abs(t - x) >= 1.6 for x in ra):
                ra.append(t)
            if len(ra) >= n:
                break
        return ra
    m_noi, m_im = thua(to, 3), thua(im, 3)
    # 2 nhóm phải cách nhau >= 1,6 s để `_SFX_CACH_MIN` không nuốt mốc nào
    m_im = [t for t in m_im if all(abs(t - x) >= 1.6 for x in m_noi)]
    return m_noi, m_im, {"loi": db(loi), "nen": db(nen)}


KHOA = ["zoom_nhoi", "glitch_khoi", "loe_sang", "rung_lac", "tuong_phan",
        "quang_sang"]


def do_mot_clip(ten: str, mo_ta: str, ss: float, dai: float, td: str) -> list:
    src = tim_nguon(mo_ta)
    m_noi, m_im, mc = chon_moc(src, ss, dai)
    mocs = sorted([(t, "ĐANG NÓI") for t in m_noi]
                  + [(t, "KHOẢNG LẶNG") for t in m_im])
    hu = [{"bat": round(t, 2), "het": round(t + 0.40, 2),
           "khoa": KHOA[i % len(KHOA)], "dam": 0.25}
          for i, (t, _k) in enumerate(mocs)]
    d = os.path.join(td, ten)
    os.makedirs(d, exist_ok=True)
    a, b = os.path.join(d, "on.mp4"), os.path.join(d, "off.mp4")
    segs = [(ss, ss + dai)]
    log = xuat(src, a, segs, [dict(c) for c in hu], True)
    xuat(src, b, segs, [dict(c) for c in hu], False)
    pa, pb = pcm(a), pcm(b)
    n = min(len(pa), len(pb))
    pa, pb = pa[:n], pb[:n]
    pd = pa - pb                          # LỚP TIẾNG ĐỘNG (+ phần ducking)
    ra, rb, rd = bao_rms(pa), bao_rms(pb), bao_rms(pd)
    l_db = db(np.percentile(rb, 90))
    pk_a, ch_a = do_dinh_file(a)
    pk_b, ch_b = do_dinh_file(b)
    print(f"\n=== {ten} · {Path(src).name[:42]} · mức LỜI {l_db:.1f} dBFS · "
          f"nền {mc['nen']:.1f} dBFS · {len(log)} tiếng động · đỉnh file BẬT "
          f"{pk_a:+.2f} ({ch_a} mẫu) / TẮT {pk_b:+.2f} ({ch_b} mẫu) ===")
    print(f"    {'mốc':>6} {'ca':<12} {'nền':>6} {'TẮT':>6} {'BẬT':>6} "
          f"{'NỔI':>6} {'SFX':>6} {'SMR':>6} | "
          + " ".join(f"{x:>7}" for x in TEN_DAI) + "  D_MAX  D_LOA  nghe?")
    ket = []
    for t, ca in mocs:
        n_db = db(nen_cuc_bo(rb, t))
        on, off = db(dinh_quanh(ra, t)), db(dinh_quanh(rb, t))
        sfx = db(dinh_quanh(rd, t))
        noi = on - n_db                    # thước CỔNG 44
        smr = sfx - off                    # tiếng động so với thứ ĐANG PHÁT
        pa_d, pb_d = pho_dai(pa, t), pho_dai(pb, t)
        dd = pa_d - pb_d                   # dải to thêm bao nhiêu -> TAI NGHE
        dmax = float(dd.max())
        # LOA ĐIỆN THOẠI: bỏ dải <300 Hz. Khán giả Shorts nghe bằng loa điện
        # thoại/laptop, thứ gần như KHÔNG tái tạo được dưới 300 Hz — tiếng động
        # chỉ nhô ở dải trầm là "đo thì thấy, nghe thì không".
        dloa = float(dd[1:].max())
        nghe = "RÕ" if dloa >= RO_DB else ("mờ" if dloa >= JND_DB else "KHÔNG")
        print(f"    {t:5.2f}s {ca:<12} {n_db:6.1f} {off:6.1f} {on:6.1f} "
              f"{noi:+6.1f} {sfx:6.1f} {smr:+6.1f} | "
              + " ".join(f"{v:+7.1f}" for v in dd)
              + f" {dmax:+6.1f} {dloa:+6.1f}  {nghe}")
        ket.append({"clip": ten, "giay": t, "ca": ca, "nen": n_db, "off": off,
                    "on": on, "noi": noi, "sfx": sfx, "smr": smr,
                    "dai": [float(v) for v in dd], "dmax": dmax,
                    "dloa": dloa, "nghe": nghe, "loi": l_db,
                    "pk_on": pk_a, "pk_off": pk_b, "ch_on": ch_a,
                    "ch_off": ch_b})
    # ---- KHÔNG ÁT LỜI: NGOÀI cửa sổ mốc, dải giọng nói phải KHÔNG đổi ----
    ngoai = []
    for i in range(len(rb)):
        t = i * CUA
        # ±2,0 s: kho có tiếng dài tới ~1,5 s (riser/whoosh), phần NGÂN của nó
        # là tiếng động hợp lệ chứ không phải "át lời".
        if any(abs(t - g) < 2.0 for g, _k in mocs):
            continue
        if rb[i] < 300:                    # bỏ chỗ im lặng (nhiễu AAC)
            continue
        pa_d, pb_d = pho_dai(pa, t, 0.10), pho_dai(pb, t, 0.10)
        ngoai.append(float((pa_d - pb_d)[1:4].max()))   # 300 Hz - 4 kHz
    if ngoai:
        print(f"    [không át lời] NGOÀI mốc, dải giọng 300-4k đổi nhiều nhất "
              f"{max(ngoai):+.2f} dB / thấp nhất {min(ngoai):+.2f} dB "
              f"({len(ngoai)} cửa sổ)")
    return ket


BA = [("YEN", "CHEATING ON GIRLFRIEND PRANK!!", 240.0, 14.0),
      ("TBINH", "Parker and Chester actually saving", 420.0, 14.0),
      ("ON", "BEST CHRISTMAS EVER!!!", 300.0, 14.0)]


def main() -> int:
    HU.dat_frei0r_path()
    td = tempfile.mkdtemp(prefix="_chelo_", dir=str(_SB))
    tat_ca: list = []
    try:
        for ten, mo_ta, ss, dai in BA:
            try:
                tat_ca += do_mot_clip(ten, mo_ta, ss, dai, td)
            except RuntimeError as e:
                print(f"  BỎ QUA {ten}: {e}")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)

    print("\n" + "=" * 78)
    for ca in ("ĐANG NÓI", "KHOẢNG LẶNG"):
        g = [x for x in tat_ca if x["ca"] == ca]
        if not g:
            continue
        n_ro = sum(1 for x in g if x["nghe"] == "RÕ")
        n_mo = sum(1 for x in g if x["nghe"] == "mờ")
        n_ko = sum(1 for x in g if x["nghe"] == "KHÔNG")
        print(f"\nCA **{ca}** — {len(g)} mốc")
        print(f"  cổng 44 (NỔI trên nền >= +6 dB) : "
              f"{sum(1 for x in g if x['noi'] >= 6.0)}/{len(g)} ĐẠT "
              f"(thấp nhất {min(x['noi'] for x in g):+.1f} dB)")
        print(f"  SMR (SFX so với thứ đang phát)  : "
              f"trung vị {sorted(x['smr'] for x in g)[len(g)//2]:+.1f} dB · "
              f"dải {min(x['smr'] for x in g):+.1f} .. "
              f"{max(x['smr'] for x in g):+.1f}")
        print(f"  TAI NGHE trên LOA ĐIỆN THOẠI (dải 300 Hz-7,8 kHz to thêm "
              f">= {JND_DB:.0f} dB): RÕ {n_ro} · mờ {n_mo} · "
              f"**KHÔNG NGHE RA {n_ko}** (D_LOA thấp nhất "
              f"{min(x['dloa'] for x in g):+.1f} dB · D_MAX cả dải thấp nhất "
              f"{min(x['dmax'] for x in g):+.1f} dB)")
    print("\n>>> KẾT LUẬN: cổng 44 đo NỔI-TRÊN-NỀN; ca ĐANG NÓI có thể ĐẠT cổng "
          "mà tai KHÔNG nghe ra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
