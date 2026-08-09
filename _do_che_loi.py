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


def xuat(src: str, dst: str, segs: list, hu, whoosh: bool, mod=None,
         **kw) -> list:
    log: list = []
    (mod or FU).export_canvas_clip(src, dst, segs, (0.5, 0.5, 1.0), bg="blur",
                                   out_w=540, out_h=960, encoder="libx264",
                                   fx_whoosh=whoosh, hieu_ung=hu,
                                   tieng_dong_log=log, chuyen_canh="tat", **kw)
    return log


#: MỐC ĐỐI CHỨNG "TRƯỚC KHI SỬA" — mặc định `7b1da35` = **v2.19.0**, đúng bản
#: anh Hùng ĐANG CHẠY và đã nghe rồi chê. KHÔNG dùng `main`: cây làm việc có
#: thể đã gộp, so-với-chính-mình thì bảng trước/sau tự trùng nhau vĩnh viễn
#: (đúng bẫy "PASS OAN sau merge" đã ghi trong CLAUDE.md).
MOC_TRUOC = os.environ.get("BQ_MOC_TRUOC", "7b1da35")


def nap_ban_truoc(moc: str):
    """Nạp `app/core/ffmpeg_utils.py` của mốc `moc` THÀNH MODULE RIÊNG.

    Vì sao phải nạp bản cũ chứ không chép số cũ từ ghi chú: bảng trước/sau chỉ
    có nghĩa khi hai bên đo trên **CÙNG mốc, cùng nguồn, cùng lượt chạy** — máy
    anh Hùng lúc nào cũng có việc nền, đo hai thời điểm khác nhau là so nhầm
    tải máy (bài học "đo A/B phải đan xen"). Chỉ lấy stdout: `git show` in cảnh
    báo CRLF ra stderr, trộn vào là file .py mở đầu bằng chữ 'warning:'."""
    import importlib.util
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        f"{moc}:app/core/ffmpeg_utils.py"],
                       capture_output=True, creationflags=_NOWIN, timeout=60)
    out = (r.stdout or b"").decode("utf-8", errors="replace")
    if r.returncode != 0 or len(out) < 5000:
        raise RuntimeError(f"không lấy được bản {moc} (rc={r.returncode})")
    nay = (REPO / "app" / "core" / "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    if out.strip() == nay.strip():
        raise RuntimeError(f"bản {moc} TRÙNG file đang đo — bảng trước/sau vô "
                           f"nghĩa (so nó với chính nó)")
    f = _SB / "fu_truoc.py"
    f.write_text(out, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("fu_truoc", str(f))
    if spec is None or spec.loader is None:
        raise RuntimeError("không nạp được module bản trước")
    m = importlib.util.module_from_spec(spec)
    sys.modules["fu_truoc"] = m
    spec.loader.exec_module(m)
    return m


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


def thu_muc_im(td: str) -> str:
    """Thư mục chứa ĐÚNG 1 file tiếng động gần như IM LẶNG (−66 dBFS).

    Xuất với `fx_sfx_dir` trỏ vào đây thì ducking chạy Y HỆT lượt thật (cùng
    mốc, cùng độ sâu) còn lớp tiếng động thì không nghe thấy -> file ra chính
    là **THỨ ĐANG CHE** tiếng động ở lượt thật. Không có bản này thì không có
    cách nào tách "dải tụt vì ducking" khỏi "tiếng động quá nhỏ"."""
    d = os.path.join(td, "_sfx_im")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "im.wav")
    if not os.path.exists(f):
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                        "sine=f=1000:d=0.30", "-af", "volume=0.0005",
                        "-ac", "2", "-ar", "48000", f],
                       capture_output=True, creationflags=_NOWIN, timeout=120)
    return d


def _do_ban(pa: np.ndarray, pb: np.ndarray, t: float,
            pm: np.ndarray | None = None) -> dict:
    """Các thước cho MỘT mốc của MỘT bản mã.

    `pa` = bản BẬT · `pb` = bản TẮT (tiếng gốc chưa hạ) · `pm` = bản **CHE**
    (ducking chạy y hệt nhưng file tiếng động gần như im lặng).

    VÌ SAO PHẢI CÓ `pm` — ĐÂY LÀ CHỖ THƯỚC ĐO TỰ BẮN VÀO CHÂN MÌNH: so bản BẬT
    với bản TẮT là hỏi "chỗ này có TO LÊN không". Nhưng ducking cố ý HẠ tiếng
    gốc để dọn chỗ, nên một bản trộn ĐÚNG NGHỀ (hạ giọng 6 dB rồi đặt tiếng
    động ngang mức giọng đã hạ) cho ra tổng dải **thấp hơn** bản TẮT 3 dB —
    thước cũ chấm "KHÔNG NGHE RA" trong khi tai nghe rất rõ.
    Cái tai thật sự hỏi là: **tiếng động có nổi lên khỏi thứ đang che nó
    không** — mà thứ đang che là giọng nói ĐÃ HẠ, tức bản CHE. Nên:
        D_CHE = mức dải(BẬT) − mức dải(CHE)
    Đây đúng là tỉ lệ tín-hiệu/che quy về dB: cộng 2 nguồn không tương quan,
    SMR = S dB làm dải to thêm `10log10(1+10^(S/10))`. S = −6 dB -> +1,0 dB
    (đúng ngưỡng vừa phân biệt được, JND cường độ ~0,5-1 dB) · S = 0 -> +3,0 dB.
    Nên `D_CHE >= 1 dB` ⟺ `SMR >= −6 dB` = ngưỡng CHE; `>= 3 dB` ⟺ SMR >= 0.
    Thiếu bản CHE thì lùi về so với bản TẮT (thước cũ, chặt hơn thực tế)."""
    ra, rb = bao_rms(pa), bao_rms(pb)
    rd = bao_rms(pa - pb)                 # LỚP TIẾNG ĐỘNG (+ phần ducking)
    n_db = db(nen_cuc_bo(rb, t))
    on, off = db(dinh_quanh(ra, t)), db(dinh_quanh(rb, t))
    sfx = db(dinh_quanh(rd, t))
    dd = pho_dai(pa, t) - pho_dai(pb, t)  # dải to thêm so với NGUỒN CHƯA HẠ
    dc = dd if pm is None else (pho_dai(pa, t) - pho_dai(pm, t))
    # LOA ĐIỆN THOẠI: bỏ dải <300 Hz. Khán giả Shorts nghe bằng loa điện
    # thoại/laptop, thứ gần như KHÔNG tái tạo được dưới 300 Hz — tiếng động
    # chỉ nhô ở dải trầm là "đo thì thấy, nghe thì không".
    dloa = float(dd[1:].max())
    dche = float(dc[1:].max())
    # HỤT TIẾNG: ducking dọn chỗ nhưng KHÔNG được thành cái hố. Dải giọng nói
    # tại mốc không được thấp hơn bản TẮT quá độ sâu ducking đã chốt.
    hut = float(dd[1:4].min())
    return {"nen": n_db, "off": off, "on": on, "noi": on - n_db, "sfx": sfx,
            "smr": sfx - off, "dai": [float(v) for v in dd],
            "dai_che": [float(v) for v in dc], "hut": hut,
            # PHỔ CỦA RIÊNG LỚP TIẾNG ĐỘNG (không phải hiệu 2 bản trộn) — trả
            # lời "tiếng động đổ năng lượng vào dải nào", tức chẩn đoán được
            # ca "đo thì to, nghe thì câm" (tất cả nằm dưới 300 Hz).
            "lop_dai": [float(v) for v in pho_dai(pa - pb, t)],
            "dmax": float(dd.max()), "dloa": dloa, "dche": dche,
            "co_che": pm is not None,
            "nghe": ("RÕ" if dche >= RO_DB
                     else ("mờ" if dche >= JND_DB else "KHÔNG"))}


def do_mot_clip(ten: str, mo_ta: str, ss: float, dai: float, td: str,
                mod_truoc=None) -> list:
    """Xuất TẮT · BẬT(bản MỚI) · BẬT(bản TRƯỚC) rồi đo TỪNG mốc cho cả hai bản.

    Bản TẮT dùng CHUNG cho cả hai: `fx_whoosh=False` không đụng một dòng nào
    trong khối tiếng động, nên đó đúng là "tín hiệu gốc tại mốc" của cả hai bản
    (bất biến này được cổng 36 canh riêng bằng PSNR)."""
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
    im = thu_muc_im(td)
    log = xuat(src, a, segs, [dict(c) for c in hu], True)
    xuat(src, b, segs, [dict(c) for c in hu], False)
    ch_new = os.path.join(d, "che.mp4")
    xuat(src, ch_new, segs, [dict(c) for c in hu], True, fx_sfx_dir=im)
    pa, pb = pcm(a), pcm(b)
    n = min(len(pa), len(pb))
    pa, pb = pa[:n], pb[:n]
    pm = pcm(ch_new)[:n]
    pt = pmt = None
    if mod_truoc is not None:
        c = os.path.join(d, "on_truoc.mp4")
        ct = os.path.join(d, "che_truoc.mp4")
        xuat(src, c, segs, [dict(x) for x in hu], True, mod=mod_truoc)
        xuat(src, ct, segs, [dict(x) for x in hu], True, mod=mod_truoc,
             fx_sfx_dir=im)
        pt = pcm(c)[:n]
        pmt = pcm(ct)[:n]
        pk_t, ch_t = do_dinh_file(c)
    rb = bao_rms(pb)
    l_db = db(np.percentile(rb, 90))
    pk_a, ch_a = do_dinh_file(a)
    pk_b, ch_b = do_dinh_file(b)
    print(f"\n=== {ten} · {Path(src).name[:42]} · mức LỜI {l_db:.1f} dBFS · "
          f"nền {mc['nen']:.1f} dBFS · {len(log)} tiếng động · đỉnh file BẬT "
          f"{pk_a:+.2f} ({ch_a} mẫu) / TẮT {pk_b:+.2f} ({ch_b} mẫu)"
          + (f" / BẬT-TRƯỚC {pk_t:+.2f} ({ch_t} mẫu)" if pt is not None
             else "") + " ===")
    print(f"    {'mốc':>6} {'ca':<12} {'nền':>6} {'TẮT':>6} {'BẬT':>6} "
          f"{'NỔI':>6} {'SFX':>6} {'SMR':>6} | "
          + " ".join(f"{x:>7}" for x in TEN_DAI)
          + "  D_LOA  D_CHE  nghe?")
    ket = []
    _theo_giay = {round(float(x.get("giay", -1)), 2): x for x in log}
    for t, ca in mocs:
        s = _do_ban(pa, pb, t, pm)
        print(f"    {t:5.2f}s {ca:<12} {s['nen']:6.1f} {s['off']:6.1f} "
              f"{s['on']:6.1f} {s['noi']:+6.1f} {s['sfx']:6.1f} "
              f"{s['smr']:+6.1f} | "
              + " ".join(f"{v:+7.1f}" for v in s["dai_che"])
              + f" {s['dloa']:+6.1f} {s['dche']:+6.1f}  {s['nghe']}")
        # CHẨN ĐOÁN: tiếng động nào được bốc + nó đổ năng lượng vào dải nào.
        # Không có dòng này thì mọi kết luận về "chọn tiếng lệch dải tần" là
        # phỏng đoán — số tổng không nói được file nào gây ra.
        _p = _theo_giay.get(round(t, 2))
        if _p:
            _f = FU._assets_sfx_dir() / _p["loai"] / _p["ten"]
            print(f"      ^ {_p['loai']}/{_p['ten'][:34]:<34} "
                  f"hệ số {_p['db']:+.1f} dB · hụt-loa "
                  f"{FU.hut_qua_loa(str(_f)):+.1f} · sáng "
                  f"{FU.do_sang_sfx(str(_f)):+.1f} | LỚP theo dải "
                  + " ".join(f"{v:+7.1f}" for v in s["lop_dai"]))
        r = {"clip": ten, "giay": t, "ca": ca, "loi": l_db, "pk_on": pk_a,
             "pk_off": pk_b, "ch_on": ch_a, "ch_off": ch_b, "sau": s, **s}
        if pt is not None:
            r["truoc"] = _do_ban(pt, pb, t, pmt)
            print(f"    {'TRƯỚC':>6} {'(' + MOC_TRUOC + ')':<12} "
                  f"{r['truoc']['nen']:6.1f} {r['truoc']['off']:6.1f} "
                  f"{r['truoc']['on']:6.1f} {r['truoc']['noi']:+6.1f} "
                  f"{r['truoc']['sfx']:6.1f} {r['truoc']['smr']:+6.1f} | "
                  + " ".join(f"{v:+7.1f}" for v in r["truoc"]["dai_che"])
                  + f" {r['truoc']['dloa']:+6.1f} "
                    f"{r['truoc']['dche']:+6.1f}  {r['truoc']['nghe']}")
        ket.append(r)
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


def so_hai_file(td: str, keys: list) -> int:
    """A/B SẠCH: cùng clip, cùng mốc, chỉ khác ĐÚNG file tiếng động được bốc.

    Ép bằng cách thay `_sfx_library` (đường dẫn vẫn nằm trong kho nên bảng mức
    tra được, hệ số tính y hệt lượt thật) — KHÔNG dùng `fx_sfx_dir` trỏ ra
    ngoài: file ngoài kho không có trong `muc_do.json` nên `_muc_sfx3` lùi về
    số suy ra, hệ số lệch và phép so mất nghĩa."""
    ten, mo_ta, ss, dai = BA[2]
    src = tim_nguon(mo_ta)
    m_noi, m_im, _mc = chon_moc(src, ss, dai)
    t = sorted(m_noi)[0]
    hu = [{"bat": round(t, 2), "het": round(t + 0.40, 2),
           "khoa": "zoom_nhoi", "dam": 0.25}]
    segs = [(ss, ss + dai)]
    im = thu_muc_im(td)
    b = os.path.join(td, "ab_off.mp4")
    c = os.path.join(td, "ab_che.mp4")
    xuat(src, b, segs, [dict(x) for x in hu], False)
    xuat(src, c, segs, [dict(x) for x in hu], True, fx_sfx_dir=im)
    pb, pm = pcm(b), pcm(c)
    n = min(len(pb), len(pm))
    goc = FU._sfx_library()
    print(f"\n=== A/B ÉP FILE · {ten} · mốc ĐANG NÓI {t:.2f}s ===")
    for i, k in enumerate(keys):
        f = str(FU._assets_sfx_dir() / k)
        FU._SFX_LIB_CACHE = dict(goc, impact=[f])
        a = os.path.join(td, f"ab_{i}.mp4")
        xuat(src, a, segs, [dict(x) for x in hu], True)
        s = _do_ban(pcm(a)[:n], pb[:n], t, pm[:n])
        print(f"    {k:<44} sáng {FU.do_sang_sfx(f):+6.1f} · hụt-loa "
              f"{FU.hut_qua_loa(f):+5.1f} -> D_CHE {s['dche']:+5.1f} dB "
              f"({s['nghe']}) · D_LOA {s['dloa']:+5.1f} · LỚP theo dải "
              + " ".join(f"{v:+6.1f}" for v in s["lop_dai"]))
    FU._SFX_LIB_CACHE = goc
    return 0


BA = [("YEN", "CHEATING ON GIRLFRIEND PRANK!!", 240.0, 14.0),
      ("TBINH", "Parker and Chester actually saving", 420.0, 14.0),
      ("ON", "BEST CHRISTMAS EVER!!!", 300.0, 14.0)]


def _tv(xs: list) -> float:
    y = sorted(xs)
    return y[len(y) // 2] if y else 0.0


def _bang_ca(g: list, khoa: str, nhan: str) -> None:
    n_ro = sum(1 for x in g if x[khoa]["nghe"] == "RÕ")
    n_mo = sum(1 for x in g if x[khoa]["nghe"] == "mờ")
    n_ko = sum(1 for x in g if x[khoa]["nghe"] == "KHÔNG")
    print(f"  {nhan:<10} cổng 44 cũ (NỔI>=+6 dB trên nền): "
          f"{sum(1 for x in g if x[khoa]['noi'] >= 6.0)}/{len(g)} "
          f"(thấp nhất {min(x[khoa]['noi'] for x in g):+5.1f})")
    print(f"  {'':<10} D_CHE (nổi khỏi thứ ĐANG CHE) trung vị "
          f"{_tv([x[khoa]['dche'] for x in g]):+5.1f} dB · thấp nhất "
          f"{min(x[khoa]['dche'] for x in g):+5.1f} · D_LOA (so nguồn chưa hạ) "
          f"trung vị {_tv([x[khoa]['dloa'] for x in g]):+5.1f} · "
          f"NGHE: RÕ {n_ro} · mờ {n_mo} · **KHÔNG {n_ko}**")


def main() -> int:
    HU.dat_frei0r_path()
    _ab = [x.strip() for x in (os.environ.get("BQ_SO_FILE") or "").split(",")
           if x.strip()]
    if _ab:
        td = tempfile.mkdtemp(prefix="_chelo_", dir=str(_SB))
        try:
            return so_hai_file(td, _ab)
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)
            shutil.rmtree(_SB, ignore_errors=True)
    mod_truoc = None
    try:
        mod_truoc = nap_ban_truoc(MOC_TRUOC)
        print(f"  [đối chứng TRƯỚC] {MOC_TRUOC} — nạp thành module riêng, "
              f"xuất ĐAN XEN cùng lượt (máy luôn có việc nền)")
    except (RuntimeError, OSError, SyntaxError) as e:
        print(f"  !! KHÔNG có bản đối chứng TRƯỚC: {e}")
    td = tempfile.mkdtemp(prefix="_chelo_", dir=str(_SB))
    tat_ca: list = []
    #: Đo MỘT clip thôi (`BQ_CHI=ON`) — dùng khi đang truy một ca hỏng cụ thể.
    #: Máy anh Hùng đang xuất clip thật, mỗi lượt đo đầy đủ là 9 lượt ffmpeg.
    _chi = [x.strip() for x in (os.environ.get("BQ_CHI") or "").split(",")
            if x.strip()]
    try:
        for ten, mo_ta, ss, dai in BA:
            if _chi and ten not in _chi:
                continue
            try:
                tat_ca += do_mot_clip(ten, mo_ta, ss, dai, td, mod_truoc)
            except RuntimeError as e:
                print(f"  BỎ QUA {ten}: {e}")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)

    print("\n" + "=" * 78)
    co_truoc = any("truoc" in x for x in tat_ca)
    for ca in ("ĐANG NÓI", "KHOẢNG LẶNG"):
        g = [x for x in tat_ca if x["ca"] == ca]
        if not g:
            continue
        print(f"\nCA **{ca}** — {len(g)} mốc  (D_LOA = dải 300 Hz-7,8 kHz to "
              f"thêm bao nhiêu dB TẠI MỐC — đây là thứ TAI nghe)")
        if co_truoc:
            _bang_ca([x for x in g if "truoc" in x], "truoc",
                     f"TRƯỚC {MOC_TRUOC}")
        _bang_ca(g, "sau", "SAU")
    print("\n>>> Thước quyết định là D_LOA, không phải NỔI-trên-nền: mốc rơi "
          "vào lúc ĐANG NÓI có thể NỔI +26 dB mà mọi dải nghe được chỉ đổi "
          "+0,1 dB = không ai nghe ra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
