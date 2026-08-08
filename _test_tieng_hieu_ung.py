# -*- coding: utf-8 -*-
"""CỔNG 44 — MỖI ĐIỂM NHẤN HÌNH PHẢI CÓ TIẾNG, ĐO BẰNG dB (không đọc lệnh).

VÌ SAO CÓ CỔNG NÀY (anh Hùng xem clip THẬT, 08/08/2026):
  *"âm thanh hiệu ứng hay gì ấy thậm chí còn không nghe được gì cả luôn, không
  biết chỗ nào chèn chỗ nào không"* · *"có hiệu ứng mà không có âm thanh cứ sao
  sao ấy"*.

ĐO RA (bản TRƯỚC khi sửa, clip THẬT 10 s / 2 đoạn / 2 điểm nhấn):
  * ĐIỂM NHẤN HÌNH: bật-tắt tiếng động lệch **0,0 dB** -> KHÔNG một mẫu âm nào.
    Đúng thiết kế cũ: tiếng chỉ chèn ở ĐIỂM NỐI đoạn, mà điểm nối do cắt ghép
    quyết định. Clip 1 đoạn thì tuyệt đối câm dù có 3 hiệu ứng.
  * ĐIỂM NỐI: chỉ nhô hơn nền **+0,7 dB** = tai người coi như không đổi. Gốc:
    hệ số `volume` cứng theo nhóm, trong khi 184 file trong kho trải **26,5 dB**
    mức nghe được.

CỔNG NÀY KIỂM **KẾT QUẢ**, KHÔNG KIỂM Ý ĐỊNH: không có ca nào đọc chuỗi lệnh
ffmpeg. Mọi kết luận lấy từ PCM của file .mp4 đã xuất:
  nền   = trung vị RMS cửa sổ 50 ms của cả clip
  đỉnh  = RMS lớn nhất trong 0,35 s quanh mốc
  LỚP TIẾNG ĐỘNG = HIỆU sóng giữa bản BẬT và bản TẮT (hai bản cùng nguồn, cùng
  timeline nên trừ được từng mẫu) -> đây là số ĐỘC LẬP với tiếng gốc, không bị
  một câu thoại to che mất.

Chạy: .venv\\Scripts\\python.exe _test_tieng_hieu_ung.py
Env : BQ_TEST=1 · BQ_FFMPEG_SLOTS=1 (LUẬT SỐ 1)
"""
from __future__ import annotations

import array
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_tieng_hu_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401  (cổng 17)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as FU      # noqa: E402
from app.core import hieu_ung as HU          # noqa: E402
from config import settings                  # noqa: E402

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF = settings.FFMPEG_PATH
SR = 16000
CUA = 0.05                     # cửa sổ RMS 50 ms
RONG = 0.35                    # bề rộng cửa sổ tìm đỉnh quanh mốc

#: Dải anh Hùng yêu cầu: tiếng động cao hơn nền 6-10 dB. Sàn cổng đặt 3,0 dB
#: (không phải 6) vì thước ở đây là RMS cửa sổ 0,35 s của CẢ CLIP: cú va ngắn
#: 0,17 s đã chuẩn hoá đỉnh sẵn thì RMS bị pha loãng — xem `dinh_mau`. Bù lại
#: cổng bắt buộc thêm tiêu chí ĐỈNH MẪU so với MỨC LỜI NÓI, chặt hơn nhiều.
#: Mốc để so: bản CŨ đo được **+0,7 dB** (và 0,0 dB ở điểm nhấn).
CHENH_MIN = 3.0
#: Trần AN TOÀN (giữ đúng cổng 40): đỉnh <= 12x RMS nền = +21,6 dB.
AT_LOI_MAX = 21.6

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


# ------------------------------------------------------------------ đo tiếng
def pcm(path: str) -> array.array:
    r = subprocess.run([FF, "-v", "error", "-i", path, "-vn", "-ac", "1",
                        "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, creationflags=_NOWIN, timeout=300)
    a = array.array("h")
    a.frombytes(r.stdout or b"")
    return a


def rms_day(a) -> list[float]:
    n = int(SR * CUA)
    out = []
    for i in range(0, len(a) - n + 1, n):
        s = 0
        for v in a[i:i + n]:
            s += v * v
        out.append(math.sqrt(s / n))
    return out


def db(x: float) -> float:
    return 20 * math.log10(max(x, 1e-7) / 32768.0)


def nen(rs: list) -> float:
    y = sorted(rs)
    return y[len(y) // 2] if y else 0.0


def muc_loi(rs: list) -> float:
    """MỨC LỜI NÓI ~ bách phân vị 90 của RMS cửa sổ. Đây mới là cái tiếng động
    phải "đấu" với — trung vị là mức lúc IM LẶNG giữa các câu, lấy nó làm mốc
    thì kết luận "tiếng động to gấp mấy" bị thổi phồng."""
    y = sorted(rs)
    return y[int(len(y) * 0.90)] if y else 0.0


def dinh(rs: list, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    return max(rs[i0:i1] or [0.0])


def dinh_mau(a, giay: float, rong: float = RONG) -> float:
    """ĐỈNH MẪU (peak) trong cửa sổ quanh mốc — dùng cho tiếng động NGẮN.

    VÌ SAO PHẢI CÓ CẢ PEAK: nhiều file trong kho là cú va CỰC NGẮN đã chuẩn hoá
    đỉnh sẵn (max_volume = 0,0 dBFS, mean -16,7 -> hệ số đỉnh **16,7 dB**). App
    KHÔNG được nhân to hơn nữa (đỉnh phải <= -1 dBFS, nếu không vỡ tiếng), nên
    RMS của nó nằm thấp — mà tai vẫn nghe rất rõ vì đó là TRANSIENT. Lấy RMS
    cửa sổ 0,35 s làm thước duy nhất là đo sai bản chất: một cú 0,17 s bị chia
    đều cho 0,35 s là tự trừ đi 3 dB. Nên cổng đo CẢ HAI."""
    i0 = max(0, int((giay - rong / 2) * SR))
    i1 = min(len(a), int((giay + rong / 2) * SR))
    return max((abs(v) for v in a[i0:i1]), default=0.0)


def hieu(a, b) -> array.array:
    """Sóng HIỆU (bản bật − bản tắt) = chính lớp tiếng động + phần ducking."""
    n = min(len(a), len(b))
    d = array.array("h", bytes(2 * n))
    for i in range(n):
        v = a[i] - b[i]
        d[i] = max(-32768, min(32767, v))
    return d


def nguon_co_tieng() -> str:
    kho = Path("D:/video test/Đã tải")
    if kho.is_dir():
        for p in sorted((q for q in kho.iterdir()
                         if q.suffix.lower() in (".mp4", ".mkv", ".webm")),
                        key=lambda q: q.stat().st_size):
            try:
                if FU.probe(str(p)).has_audio:
                    return str(p)
            except Exception:  # noqa: BLE001
                continue
    raise RuntimeError("máy không có video THẬT có tiếng để đo")


def xuat(src: str, dst: str, segs: list, hu, whoosh: bool,
         cats=None, **kw) -> list:
    log: list = []
    FU.export_canvas_clip(src, dst, segs, (0.5, 0.5, 1.0), bg="blur",
                          out_w=540, out_h=960, encoder="libx264",
                          fx_whoosh=whoosh, join_categories=cats,
                          hieu_ung=hu, tieng_dong_log=log,
                          chuyen_canh="tat", **kw)
    return log


# =====================================================================
def ca_ham_thuan() -> None:
    """Hàm tính hệ số là hàm THUẦN -> kiểm được biên mà không tốn ffmpeg."""
    print("\n[CA 1] HÀM TÍNH HỆ SỐ (thuần) — chuẩn hoá + kẹp biên")
    g_to = FU.tinh_gain_sfx("transition", -4.0, -1.0, -24.0)
    g_nho = FU.tinh_gain_sfx("transition", -28.0, -3.0, -24.0)
    bao("file TO và file NHỎ ra hệ số KHÁC nhau (đã chuẩn hoá)",
        abs(20 * math.log10(g_nho / g_to)) > 12.0,
        f"file -4 dB -> {20*math.log10(g_to):+.1f} dB · "
        f"file -28 dB -> {20*math.log10(g_nho):+.1f} dB")
    # đỉnh sau khi nhân KHÔNG được vượt trần -> không vỡ tiếng
    xau = []
    for mean, mx in ((-4.0, 0.0), (-28.0, -3.0), (-12.0, -1.0), (-20.0, -10.0)):
        for nn in (-40.0, -24.0, -12.0, -6.0):
            g = 20 * math.log10(FU.tinh_gain_sfx("impact", mean, mx, nn))
            if mx + g > FU._SFX_DINH_TRAN_DB + 0.01:
                xau.append((mean, mx, nn, round(mx + g, 2)))
    bao("đỉnh sau khi nhân luôn <= -1 dBFS (16 tổ hợp)", not xau, str(xau[:4]))
    bao("mọi kiểu hiệu ứng trong KHO đều có nhóm tiếng",
        all(FU.loai_sfx_theo_hieu_ung(k) in FU.SFX_CATEGORIES for k in HU.KHO),
        f"{len(HU.KHO)} kiểu -> "
        f"{sorted({FU.loai_sfx_theo_hieu_ung(k) for k in HU.KHO})}")
    bao("zoom/rung -> impact · loé sáng -> reveal · glitch -> scratch",
        FU.loai_sfx_theo_hieu_ung("zoom_nhoi") == "impact"
        and FU.loai_sfx_theo_hieu_ung("rung_lac") == "impact"
        and FU.loai_sfx_theo_hieu_ung("loe_sang") == "reveal"
        and FU.loai_sfx_theo_hieu_ung("glitch_khoi") == "scratch",
        "zoom_nhoi/rung_lac/loe_sang/glitch_khoi = "
        + "/".join(FU.loai_sfx_theo_hieu_ung(k) for k in
                   ("zoom_nhoi", "rung_lac", "loe_sang", "glitch_khoi")))
    d = FU._bieu_thuc_duck([1.0, 5.0])
    bao("biểu thức ducking vào/ra ÊM (không bậc thang) + có `eval=frame`",
        "sin(" in d and "eval=frame" in d and "between(" in d, d[:80] + "...")
    bao("không có mốc nào -> KHÔNG thêm filter ducking",
        FU._bieu_thuc_duck([]) == "", "chuỗi rỗng")
    bao("bảng mức kho tiếng động đọc được", len(FU._sfx_bang_muc()) >= 150,
        f"{len(FU._sfx_bang_muc())} file có sẵn mức đo")
    ms = [v[0] for v in FU._sfx_bang_muc().values()]
    bao("kho THẬT SỰ chênh lệch mức (nên mới phải chuẩn hoá)",
        bool(ms) and (max(ms) - min(ms)) > 15.0,
        f"mean_volume trải {max(ms)-min(ms):.1f} dB "
        f"({min(ms):.1f} .. {max(ms):.1f})")


def ca_diem_nhan_co_tieng(src: str, td: str) -> None:
    print("\n[CA 2] MỖI ĐIỂM NHẤN HÌNH CÓ TIẾNG ĐI KÈM (clip 1 ĐOẠN — không có "
          "điểm nối nào)")
    segs = [(240.0, 250.0)]
    hu = [{"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25},
          {"bat": 4.60, "het": 5.00, "khoa": "glitch_khoi", "dam": 0.25},
          {"bat": 7.80, "het": 8.20, "khoa": "loe_sang", "dam": 0.25}]
    a, b = os.path.join(td, "d_on.mp4"), os.path.join(td, "d_off.mp4")
    log = xuat(src, a, segs, hu, True)
    xuat(src, b, segs, hu, False)
    pa, pb = pcm(a), pcm(b)
    ra = rms_day(pa)
    rl = rms_day(hieu(pa, pb))
    n_db = db(nen(ra))
    bao("clip 1 đoạn vẫn có tiếng động (bản cũ: KHÔNG có cái nào)",
        len(log) == len(hu), f"{len(log)} tiếng / {len(hu)} điểm nhấn: "
        + ", ".join(f"{x['giay']}s {x['loai']}" for x in log))
    bao("nhật ký ghi ĐÚNG nhóm theo kiểu hiệu ứng",
        [x["loai"] for x in log] == [FU.loai_sfx_theo_hieu_ung(c["khoa"])
                                     for c in hu],
        " · ".join(f"{c['khoa']}->{x['loai']}" for c, x in zip(hu, log)))
    xau = []
    for c in hu:
        g = float(c["bat"])
        lop = db(dinh(rl, g))                 # lớp tiếng động RIÊNG
        chenh = db(dinh(ra, g)) - n_db        # nổi hơn nền bao nhiêu
        print(f"      {c['khoa']:<14} {g:5.2f}s · lớp tiếng {lop:6.1f} dBFS · "
              f"đỉnh nổi {chenh:+5.1f} dB so nền {n_db:.1f} dB")
        if lop < n_db + 3.0:
            xau.append(f"{c['khoa']}@{g}s lớp {lop:.1f} dB")
    bao("mốc nào cũng CÓ lớp tiếng động thật (không phải 0 như bản cũ)",
        not xau, "; ".join(xau) if xau else
        f"3/3 mốc có tiếng, nền clip {n_db:.1f} dB")
    # RÒ RA NGOÀI — đo TƯƠNG ĐỐI, đừng đo bằng ngưỡng tuyệt đối.
    # BẪY ĐÃ SẬP: ngưỡng cứng `nền - 6 dB` bắt oan 5 cửa sổ ở giây 2,2-2,4 —
    # chỗ đó KHÔNG có tiếng động nào, mà là **nhiễu lượng tử của AAC**: hai bản
    # (bật/tắt) mã hoá RIÊNG, đoạn tiếng gốc to thì sàn nhiễu AAC cũng cao lên,
    # nên sóng HIỆU có năng lượng thật. Số đúng phải là: chỗ ngoài mốc phải
    # THẤP HƠN HẲN chỗ có tiếng động.
    trong_i = {i for i in range(len(rl))
               if any(abs(i * CUA - float(c["bat"])) < 0.8 for c in hu)}
    ngoai = [db(rl[i]) for i in range(len(rl)) if i not in trong_i]
    trong = [db(rl[i]) for i in range(len(rl)) if i in trong_i]
    bao("lớp tiếng động NGOÀI điểm nhấn thấp hơn hẳn (>= 10 dB) chỗ CÓ tiếng",
        bool(ngoai) and bool(trong) and max(ngoai) <= max(trong) - 10.0,
        f"ngoài cao nhất {max(ngoai or [-99]):.1f} dB · trong cao nhất "
        f"{max(trong or [-99]):.1f} dB · cách "
        f"{max(trong or [-99]) - max(ngoai or [-99]):.1f} dB")
    bao("bản TẮT tiếng động thì lớp tiếng = 0 (đối chứng)",
        max((db(x) for x in rms_day(hieu(pb, pb))), default=-99) < -60,
        "hiệu của bản tắt với chính nó")


def ca_muc_do(src: str, td: str) -> None:
    print("\n[CA 3] MỨC TIẾNG: nghe RÕ nhưng KHÔNG ĐÈ GIỌNG (6-10 dB trên nền)")
    segs = [(240.0, 245.0), (260.0, 265.0)]        # điểm nối ở 5,00 s
    hu = [{"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25},
          {"bat": 7.60, "het": 8.00, "khoa": "o_vuong", "dam": 0.25}]
    a, b = os.path.join(td, "m_on.mp4"), os.path.join(td, "m_off.mp4")
    log = xuat(src, a, segs, hu, True, cats=["impact"])
    xuat(src, b, segs, hu, False, cats=["impact"])
    pa, pb = pcm(a), pcm(b)
    ra = rms_day(pa)
    n_db = db(nen(ra))
    moc = sorted([5.00] + [float(c["bat"]) for c in hu])
    pl = hieu(pa, pb)                    # sóng LỚP TIẾNG ĐỘNG (đã trừ nền)
    rl = rms_day(pl)
    l_db = db(muc_loi(rms_day(pb)))      # MỨC LỜI NÓI (bách phân vị 90)
    ch, so_loi, so_loi_d = [], [], []
    for g in moc:
        ch.append(db(dinh(ra, g)) - n_db)
        so_loi.append(db(dinh(rl, g)) - l_db)
        so_loi_d.append(db(dinh_mau(pl, g)) - l_db)
        print(f"      mốc {g:5.2f}s -> cả clip đỉnh {db(dinh(ra,g)):6.1f} dB "
              f"(nổi {ch[-1]:+5.1f} so nền) · LỚP tiếng động RMS "
              f"{db(dinh(rl,g)):6.1f} / đỉnh mẫu {db(dinh_mau(pl,g)):6.1f} dB")
    print(f"      nền (trung vị) {n_db:.1f} dB · MỨC LỜI NÓI {l_db:.1f} dB")
    bao(f"không mốc nào ÁT LỜI (<= {AT_LOI_MAX} dB = 12x RMS nền, cổng 40)",
        max(ch) <= AT_LOI_MAX, f"cao nhất {max(ch):+.1f} dB")
    bao("tiếng động KHÔNG ĐÈ lời (đỉnh mẫu <= lời + 20 dB)",
        max(so_loi_d) <= 20.0, f"cao nhất {max(so_loi_d):+.1f} dB so mức lời")
    # NGHE ĐƯỢC: đo CẢ HAI thước (xem `dinh_mau`). Cú va ngắn đã chuẩn hoá đỉnh
    # thì RMS 0,35 s thấp là ĐÚNG BẢN CHẤT, không phải app làm nhỏ — nên tiêu
    # chí là "đạt MỘT trong hai": RMS đủ nổi HOẶC đỉnh mẫu đủ nổi.
    dat = [(a1 >= 0.0) or (a2 >= 6.0) for a1, a2 in zip(so_loi, so_loi_d)]
    bao("mốc nào cũng NGHE ĐƯỢC bên cạnh lời (RMS >= lời, hoặc đỉnh >= lời+6)",
        all(dat),
        " · ".join(f"{g:.2f}s RMS{a1:+.1f}/đỉnh{a2:+.1f}"
                   for g, a1, a2 in zip(moc, so_loi, so_loi_d)))
    bao(f"mọi mốc nổi >= {CHENH_MIN} dB trên nền clip "
        f"(bản cũ đo được +0,7 dB)", min(ch) >= CHENH_MIN,
        f"thấp nhất {min(ch):+.1f} dB · từng mốc "
        + " · ".join(f"{x:+.1f}" for x in ch))
    bao("điểm NỐI và điểm NHẤN đều có mặt trong nhật ký",
        {x.get("vai") for x in log} == {"nối", "điểm nhấn"},
        " · ".join(f"{x['giay']}s {x['vai']}/{x['loai']} {x['db']:+.1f}dB"
                   for x in log))
    # ---- DUCKING: ĐO RIÊNG, KHÔNG ĐO CHUNG VỚI TIẾNG ĐỘNG ----
    # BẪY ĐÃ SẬP 1 LẦN: so bản BẬT với bản TẮT ở giây (mốc + 0,30) rồi bảo
    # "phải thấp hơn" — nhưng chính TIẾNG ĐỘNG vẫn đang ngân ở đó (file dài
    # 0,17-0,62 s) nên hiệu ra DƯƠNG và cổng FAIL OAN (đo: +2,7 / +10,7 / +3,7).
    # ĐÚNG: dựng một lượt có ĐỦ mốc tiếng động nhưng file tiếng gần như IM
    # LẶNG (thư mục `fx_sfx_dir` chứa 1 file -66 dBFS). Lượt đó ducking vẫn
    # chạy y hệt còn lớp tiếng động thì không nghe thấy -> hiệu với bản TẮT
    # chính là DUCKING THUẦN.
    im = os.path.join(td, "sfx_im")
    os.makedirs(im, exist_ok=True)
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    "sine=f=1000:d=0.30", "-af", "volume=0.0005",
                    "-ac", "2", "-ar", "48000",
                    os.path.join(im, "im.wav")],
                   capture_output=True, creationflags=_NOWIN, timeout=120)
    c = os.path.join(td, "m_duck.mp4")
    xuat(src, c, segs, hu, True, cats=["impact"], fx_sfx_dir=im)
    rc_ = rms_day(pcm(c))
    rb = rms_day(pb)
    giam = []
    for g in moc:
        i0 = max(0, int((g - 0.06) / CUA))
        i1 = min(len(rc_), len(rb), int((g + 0.39) / CUA) + 1)
        xs = [db(rc_[i]) - db(rb[i]) for i in range(i0, i1) if rb[i] > 30]
        if xs:
            giam.append(min(xs))
    bao("CÓ ducking THẬT: tiếng gốc bị hạ trong cửa sổ tiếng động "
        f"(đặt {FU._SFX_DUCK_DB:.0f} dB)",
        bool(giam) and max(giam) <= -2.0,
        " · ".join(f"{x:+.1f} dB" for x in giam) or "không đo được")
    ngoai = [db(rc_[i]) - db(rb[i]) for i in range(min(len(rc_), len(rb)))
             if rb[i] > 30 and all(abs(i * CUA - g) > 1.2 for g in moc)]
    bao("ducking KHÔNG rò ra ngoài cửa sổ (tiếng gốc giữ nguyên)",
        not ngoai or min(ngoai) > -1.0,
        f"hạ nhiều nhất ngoài cửa sổ {min(ngoai or [0]):+.2f} dB")


def ca_tat_la_tat(src: str, td: str) -> None:
    print("\n[CA 4] TẮT LÀ TẮT: fx_whoosh=False -> KHÔNG một mẫu âm nào thêm")
    segs = [(240.0, 244.0), (260.0, 264.0)]
    hu = [{"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25}]
    a = os.path.join(td, "t_off1.mp4")
    b = os.path.join(td, "t_off2.mp4")
    l1 = xuat(src, a, segs, hu, False, cats=["impact"])
    l2 = xuat(src, b, segs, hu, False, cats=["impact"])
    bao("nhật ký tiếng động RỖNG khi tắt", not l1 and not l2,
        f"{len(l1)} / {len(l2)}")
    d = rms_day(hieu(pcm(a), pcm(b)))
    bao("2 lượt xuất TẮT tiếng ra sóng GIỐNG NHAU (không có gì ngẫu nhiên)",
        max((db(x) for x in d), default=-99) < -55,
        f"hiệu lớn nhất {max((db(x) for x in d), default=-99):.1f} dBFS")
    print("\n[CA 5] MỌI ĐIỂM NỐI 'none' -> KHÔNG chèn (tôn trọng ý đồ AI)")
    c = os.path.join(td, "t_none.mp4")
    ln = xuat(src, c, segs, "tat", True, cats=["none"])
    bao("join_categories=['none'] + hiệu ứng tắt -> 0 tiếng", not ln,
        f"{len(ln)} tiếng")


def ca_hook(src: str, td: str) -> None:
    print("\n[CA 6] HOOK MỞ ĐẦU: 2 giây đầu phải CÓ điểm nhấn + CÓ tiếng")
    # hook-first = đoạn đầu nằm SAU đoạn sau trên timeline gốc (nhảy ngược)
    hook_segs = [(300.0, 303.0), (240.0, 250.0)]
    thuong_segs = [(240.0, 250.0), (300.0, 303.0)]
    bao("nhận diện hook-first bằng mốc NGƯỢC THỜI GIAN",
        FU._la_hook_first(hook_segs) and not FU._la_hook_first(thuong_segs),
        f"ngược={FU._la_hook_first(hook_segs)} · "
        f"xuôi={FU._la_hook_first(thuong_segs)}")
    a = os.path.join(td, "h_on.mp4")
    b = os.path.join(td, "h_off.mp4")
    hlog: list = []
    tlog = xuat(src, a, hook_segs, "manh", True, hieu_ung_log=hlog)
    xuat(src, b, hook_segs, "manh", False)
    dau = [c for c in hlog if float(c["bat"]) < 0.5]
    bao("clip hook-first CÓ điểm nhấn trong 0,5 giây đầu", bool(dau),
        " · ".join(f"{c['bat']}s {c['khoa']}" for c in hlog) or "không có")
    bao("điểm nhấn hook dùng kiểu MẠNH (không phải mood)",
        bool(dau) and dau[0]["khoa"] in HU._UV_THEO_LOAI["hook"],
        f"{dau[0]['khoa'] if dau else '-'} "
        f"(pool hook: {HU._UV_THEO_LOAI['hook']})")
    rl = rms_day(hieu(pcm(a), pcm(b)))
    ra = rms_day(pcm(a))
    n_db = db(nen(ra))
    dau_db = db(dinh(rl, 0.20, 0.60))
    bao("hook CÓ tiếng đi kèm ngay 2 giây đầu", dau_db > n_db + 3.0,
        f"lớp tiếng ở 0,0-0,5 s = {dau_db:.1f} dBFS · nền {n_db:.1f} dB")
    bao("nhật ký ghi tiếng cho mốc hook", any(x["giay"] < 0.6 for x in tlog),
        " · ".join(f"{x['giay']}s {x['loai']}" for x in tlog))
    bao("hook KHÔNG phá luật độ đậm (<= DAM_MAX)",
        all(float(c.get("dam", 0)) <= HU.DAM_MAX + 1e-9 for c in hlog),
        f"đậm nhất {max((float(c.get('dam',0)) for c in hlog), default=0)}")
    bao("hook KHÔNG phá luật 10% thời lượng",
        HU.ty_le_co_hieu_ung(hlog, 13.0) <= HU.TY_LE_MAX * 100 + 0.01,
        f"{HU.ty_le_co_hieu_ung(hlog, 13.0):.1f}% (trần "
        f"{HU.TY_LE_MAX*100:.0f}%)")
    # clip THƯỜNG (không hook-first) KHÔNG được tự thêm điểm ở giây 0
    hlog2: list = []
    xuat(src, os.path.join(td, "h_thuong.mp4"), thuong_segs, "manh", True,
         hieu_ung_log=hlog2)
    bao("clip KHÔNG hook-first thì KHÔNG tự nhét điểm ở giây 0",
        not [c for c in hlog2 if float(c["bat"]) < 0.5],
        " · ".join(f"{c['bat']}s {c['khoa']}" for c in hlog2) or "không có")


def main() -> int:
    HU.dat_frei0r_path()
    td = tempfile.mkdtemp(prefix="_tienghu_", dir=str(_SB))
    try:
        src = nguon_co_tieng()
        print(f"  [nguồn] {Path(src).name[:56]}")
        ca_ham_thuan()
        ca_diem_nhan_co_tieng(src, td)
        ca_muc_do(src, td)
        ca_tat_la_tat(src, td)
        ca_hook(src, td)
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)
    print("\n" + "=" * 72)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for x in _LOI:
        print("  FAIL:", x)
    return 1 if _LOI else 0


if __name__ == "__main__":
    sys.exit(main())
