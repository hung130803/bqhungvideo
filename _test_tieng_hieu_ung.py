# -*- coding: utf-8 -*-
"""CỔNG 44 — MỖI ĐIỂM NHẤN HÌNH PHẢI CÓ TIẾNG **TRÊN MỌI LOẠI CLIP**, ĐO BẰNG dB.

VÌ SAO CÓ CỔNG NÀY (anh Hùng xem clip THẬT, 08/08/2026):
  *"âm thanh hiệu ứng hay gì ấy thậm chí còn không nghe được gì cả luôn, không
  biết chỗ nào chèn chỗ nào không"* · *"có hiệu ứng mà không có âm thanh cứ sao
  sao ấy"*.

VÌ SAO CỔNG NÀY TỪNG VÔ DỤNG (lượt kiểm độc lập, cùng ngày):
  Bản đầu chỉ đo trên **MỘT nguồn nền yên** (-23,6 dBFS) và kết luận "+10..+17
  dB, ĐẠT". Đo lại trên CLIP THẬT của anh Hùng (nền -15,7 dBFS) thì bật/tắt
  tiếng động chỉ lệch **+0,6 / −1,1 / −0,0 / −1,6 / +2,4 dB** — **2/5 mốc còn
  NHỎ ĐI**. Một cổng chỉ đo một loại nguồn thì không bắt được gì.
  Nó còn **NHẤP NHÁY**: chạy 5 lượt hỏng 1 (file tiếng động bốc ngẫu nhiên,
  trúng file mức thấp là mốc đó câm).
  NAY: **CA 2 đo trên 3 VIDEO THẬT có nền khác hẳn nhau** (yên / trung bình /
  ồn) và mọi ngưỡng đều so với **NỀN CỤC BỘ quanh chính mốc đó**, không phải
  trung vị cả clip (trung vị của clip ồn là mức LỜI, lấy nó làm nền là tự cho
  điểm).

CỔNG NÀY KIỂM **KẾT QUẢ**, KHÔNG KIỂM Ý ĐỊNH: không ca nào đọc chuỗi lệnh
ffmpeg. Mọi kết luận lấy từ PCM của file .mp4 đã xuất:
  nền cục bộ = bpv20 đường bao RMS 50 ms trong ±1,5 s quanh mốc (bản TẮT)
  đỉnh       = RMS lớn nhất trong 0,35 s quanh mốc
  mức lời    = bpv90 đường bao RMS cả clip (bản TẮT)
  LỚP TIẾNG ĐỘNG = HIỆU sóng giữa bản BẬT và bản TẮT (hai bản cùng nguồn, cùng
  timeline nên trừ được từng mẫu) -> số ĐỘC LẬP với tiếng gốc.
  KHÔNG MÉO = `astats` trên chính file .mp4 (đỉnh + số mẫu chạm trần).

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
NEN_RONG = 3.0                 # bề rộng cửa sổ đo NỀN CỤC BỘ

#: Anh Hùng chốt 08/08/2026: mốc điểm nhấn phải **nổi >= +6 dB trên nền cục
#: bộ**. Bản trước đặt 3,0 dB và đo trên trung vị CẢ CLIP -> quá dễ.
NOI_MIN = 6.0
#: "Không mốc nào được NHỎ ĐI" so với bản tắt tiếng động. Sàn -1,0 dB chứ
#: không phải 0,0 — và đây là chỗ phải nói THẲNG, không được giấu:
#:   * hai bản là hai lượt mã hoá AAC RIÊNG -> nhiễu ±0,2 dB;
#:   * nguồn của anh Hùng có bản đã master VƯỢT 0 dBFS (bản TẮT của "Parker
#:     and Chester" xuất ra **+0,51 dBFS, 1 mẫu chạm trần**). Ở một mốc rơi
#:     đúng tiếng hét trên nguồn như thế thì **KHÔNG THỂ cộng thêm năng lượng
#:     mà không hạ cái đang có** — muốn không méo thì phải gọt, gọt thì mốc
#:     đứng yên. Đo được: mốc đó lệch **-0,2 .. +0,2 dB** = đứng yên, trong khi
#:     vẫn NỔI **+16 dB** trên nền cục bộ (nghe rất rõ).
#: 1,0 dB nằm ở ngưỡng tai người vừa mới phân biệt được, và VẪN BẮT ĐƯỢC lỗi
#: gốc: lượt kiểm độc lập đo bản v2.18.0 ra **-1,1 và -1,6 dB** -> cả hai đều
#: FAIL ở sàn này.
NHO_TOI_DA = -1.0
#: CHỐNG ÁT LỜI: đỉnh RMS lớp tiếng động <= 1,5x mức lời (bpv90) = +3,5 dB.
AT_LOI_LAN = 1.5
#: Trần AN TOÀN cũ (giữ đúng cổng 40): đỉnh <= 12x RMS nền = +21,6 dB.
AT_LOI_MAX = 21.6
#: KHÔNG MÉO: đỉnh đọc được TỪ FILE .mp4 phải <= mức này và 0 mẫu chạm trần.
#: NGOẠI LỆ DUY NHẤT, có bằng chứng: nguồn của anh Hùng có bản đã master VƯỢT
#: 0 dBFS — bản TẮT tiếng động của "Parker and Chester" xuất ra **+0,51 dBFS,
#: 1 mẫu chạm trần**, tức app đang ra file méo sẵn TRƯỚC KHI có tiếng động
#: nào. Với nguồn như thế thì "vừa không hạ mốc điểm nhấn, vừa <= -1 dBFS" là
#: BẤT KHẢ THI (không thể cộng thêm năng lượng vào tín hiệu đã kịch trần mà
#: không hạ cái đang có). Luật đúng: **bản BẬT không bao giờ được méo hơn bản
#: TẮT** — và phải <= -1 dBFS ở mọi nguồn còn chỗ trống.
TRAN_DINH_DB = -1.0

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


def bpv(rs: list, q: float) -> float:
    y = sorted(rs)
    return y[min(len(y) - 1, int(len(y) * q))] if y else 0.0


def nen(rs: list) -> float:
    return bpv(rs, 0.50)


def nen_cuc_bo(rs: list, giay: float) -> float:
    """NỀN CỤC BỘ quanh mốc = bpv20 đường bao trong ±NEN_RONG/2.

    VÌ SAO KHÔNG DÙNG TRUNG VỊ CẢ CLIP: clip ồn (xe chạy, nhạc nền) có trung vị
    CHÍNH LÀ mức lời; lấy nó làm "nền" thì tiếng động chỉ cần bằng lời đã coi
    như "nổi 0 dB" — che mất đúng cái lỗi anh Hùng nghe thấy. Và nền của một
    clip 60 giây thay đổi liên tục, nên phải đo NGAY CHỖ có điểm nhấn."""
    i0 = max(0, int((giay - NEN_RONG / 2) / CUA))
    i1 = min(len(rs), int((giay + NEN_RONG / 2) / CUA) + 1)
    return bpv(rs[i0:i1], 0.20)


def muc_loi(rs: list) -> float:
    """MỨC LỜI NÓI ~ bách phân vị 90 của RMS cửa sổ. Đây mới là cái tiếng động
    phải "đấu" với — trung vị là mức lúc IM LẶNG giữa các câu, lấy nó làm mốc
    thì kết luận "tiếng động to gấp mấy" bị thổi phồng."""
    return bpv(rs, 0.90)


def dinh(rs: list, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    return max(rs[i0:i1] or [0.0])


def dinh_mau(a, giay: float, rong: float = RONG) -> float:
    """ĐỈNH MẪU (peak) trong cửa sổ quanh mốc — dùng cho tiếng động NGẮN.

    VÌ SAO PHẢI CÓ CẢ PEAK: nhiều file trong kho là cú va CỰC NGẮN đã chuẩn hoá
    đỉnh sẵn, RMS 0,35 s của nó bị pha loãng mà tai vẫn nghe rất rõ vì đó là
    TRANSIENT. Nên cổng đo CẢ HAI."""
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


def do_dinh_file(path: str) -> tuple[float, int]:
    """(đỉnh dBFS, số mẫu CHẠM TRẦN) đọc bằng `astats` từ chính file .mp4.

    BẪY ĐÃ SẬP KHI VIẾT: mỗi dòng astats mở đầu bằng `[Parsed_astats_0 @ ...]`
    nên `startswith("Peak level dB:")` KHÔNG BAO GIỜ khớp -> mọi file ra
    -99 dBFS và ca "không méo" tự PASS vĩnh viễn."""
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


# ------------------------------------------------------------------- nguồn
#: Kho video THẬT của anh Hùng. KHÔNG phải đường dẫn trong repo (mã nguồn luôn
#: lấy theo `__file__` — xem khối "CỔNG TEST PHẢI TRỎ VỀ BẢN MÃ CỦA CHÍNH NÓ"),
#: mà là thư mục phim trên máy; đặt `BQ_KHO_VIDEO` để trỏ chỗ khác.
KHO_VIDEO = Path(os.environ.get("BQ_KHO_VIDEO") or "D:/video test/Đã tải")

#: 3 VIDEO THẬT có nền khác hẳn nhau — đo sẵn bằng `_do_nen_clip.py`
#: (mean_volume của đoạn: -23,5 / -16,4 / -14,8 dBFS; đây chính là thước mà
#: `_muc_nen_dB` bản cũ dùng và lượt kiểm độc lập báo cáo).
#: Ca YÊN cố ý để **1 ĐOẠN** -> chứng minh điểm nhấn có tiếng KHÔNG cần điểm
#: nối (bản trước v2.18.0 clip 1 đoạn là câm tuyệt đối).
BA_NEN = [
    ("nền YÊN", "CHEATING ON GIRLFRIEND PRANK!!", 240.0, 1),
    ("nền T.BÌNH", "Parker and Chester actually saving", 420.0, 2),
    ("nền ỒN", "BEST CHRISTMAS EVER!!!", 300.0, 2),
]
HU_MOC = [
    {"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25},
    {"bat": 4.60, "het": 5.00, "khoa": "glitch_khoi", "dam": 0.25},
    {"bat": 10.40, "het": 10.80, "khoa": "loe_sang", "dam": 0.25},
]
MOC_NOI = 7.0                  # điểm nối đoạn (timeline đầu ra) khi 2 đoạn


def tim_nguon(mo_ta: str) -> str:
    if KHO_VIDEO.is_dir():
        for p in sorted(KHO_VIDEO.iterdir()):
            if p.name.startswith(mo_ta):
                return str(p)
    raise RuntimeError(f"máy không có video THẬT để đo: {mo_ta}")


def nguon_co_tieng() -> str:
    """Nguồn dự phòng cho các ca không cần 3 nền (hook / tắt-là-tắt)."""
    try:
        return tim_nguon(BA_NEN[0][1])
    except RuntimeError:
        pass
    if KHO_VIDEO.is_dir():
        for p in sorted((q for q in KHO_VIDEO.iterdir()
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
    print("\n[CA 1] HÀM TÍNH HỆ SỐ (thuần) — chuẩn hoá theo ĐỈNH RMS NGẮN HẠN")
    g_to = FU.tinh_gain_sfx("transition", -4.0, -1.0, -24.0, st_db=-2.0,
                            loi_db=-14.0)
    g_nho = FU.tinh_gain_sfx("transition", -28.0, -3.0, -24.0, st_db=-24.0,
                             loi_db=-14.0)
    bao("file TO và file NHỎ ra hệ số KHÁC nhau (đã chuẩn hoá)",
        abs(20 * math.log10(g_nho / g_to) - 22.0) < 0.5,
        f"file st -2 dB -> {20*math.log10(g_to):+.1f} dB · "
        f"st -24 dB -> {20*math.log10(g_nho):+.1f} dB (đúng bằng chênh 22 dB)")
    # CHUẨN HOÁ ĐÚNG = mọi file ra CÙNG một đỉnh RMS -> hết nhấp nháy
    ra = [20 * math.log10(FU.tinh_gain_sfx("impact", -12.0, -1.0, -30.0,
                                           st_db=s, loi_db=-18.0)) + s
          for s in (-2.0, -6.0, -10.0, -14.0, -20.0)]
    bao("mọi mức file ra CÙNG một đỉnh RMS (gốc của 'hết nhấp nháy')",
        max(ra) - min(ra) < 0.01,
        f"5 file st -2..-20 dB -> đỉnh lớp {min(ra):.1f}..{max(ra):.1f} dBFS")
    # CHỐNG ÁT LỜI: đích KHÔNG BAO GIỜ vượt 1,5x mức lời, kể cả nhóm impact
    tran = 20 * math.log10(AT_LOI_LAN)
    xau = []
    for cat in FU.SFX_CATEGORIES:
        for nn, ll in ((-40.0, -28.0), (-30.0, -18.0), (-24.0, -20.0),
                       (-22.0, -11.0), (-12.0, -8.0), (-18.0, -17.0)):
            d = FU.dich_sfx_dB(cat, nn, ll)
            if d > ll + tran + 0.01:
                xau.append((cat, nn, ll, round(d, 1)))
    bao(f"đích KHÔNG bao giờ vượt {AT_LOI_LAN}x mức lời (+{tran:.1f} dB) — "
        f"{len(FU.SFX_CATEGORIES)} nhóm x 6 cảnh nền", not xau, str(xau[:3]))
    # clip ỒN: nền thấp mà lời to -> phải bám LỜI, không bám nền
    d_on = FU.dich_sfx_dB("impact", -24.0, -11.0)
    d_yen = FU.dich_sfx_dB("impact", -38.0, -20.0)
    bao("clip ỒN thì đích bám MỨC LỜI chứ không bám nền (gốc của lỗi)",
        d_on > -24.0 + FU.SFX_TREN_NEN_DB + 2.0 - 0.01,
        f"nền -24/lời -11 -> đích {d_on:.1f} dBFS (nếu chỉ bám nền là "
        f"{-24.0+FU.SFX_TREN_NEN_DB+2.0:.1f}) · nền -38/lời -20 -> "
        f"{d_yen:.1f} dBFS")
    # LỌC FILE HỢP MỨC: file quá nhỏ / hệ số đỉnh quá lớn phải bị loại
    bang = FU._sfx_bang_muc()
    bao("bảng mức kho tiếng động có ĐỦ 3 cột (mean, max, đỉnh RMS 50 ms)",
        len(bang) >= 150 and all(isinstance(v, list) and len(v) >= 3
                                 for v in bang.values()),
        f"{len(bang)} file · ví dụ {list(bang.items())[0]}")
    st = [v[2] for v in bang.values()]
    bao("kho THẬT SỰ chênh lệch mức (nên mới phải chuẩn hoá)",
        bool(st) and (max(st) - min(st)) > 15.0,
        f"đỉnh RMS 50 ms trải {max(st)-min(st):.1f} dB "
        f"({min(st):.1f} .. {max(st):.1f})")
    lib = FU._sfx_library()
    n_het = sum(len(v) for v in lib.values())
    n_hop = sum(1 for v in lib.values() for f in v
                if FU._hop_muc(f, -9.0, FU._SFX_DINH_TRAN_DB))
    bao("lọc file hợp mức có LOẠI thật nhưng VẪN CÒN nhiều để bốc ngẫu nhiên",
        0 < n_hop < n_het and n_hop >= 20,
        f"clip ồn (đích -9 dBFS): {n_hop}/{n_het} file dùng được")
    # TIẾNG VÀO CHẬM: đỉnh rơi sau mốc thì nó KHÔNG đánh dấu điểm nhấn nào.
    cham_vao = [k for k, v in bang.items()
                if len(v) >= 4 and float(v[3]) > FU._SFX_DICH_TOI_DA]
    bao("bảng có cột 4 = GIÂY xảy ra đỉnh, và kho THẬT SỰ có tiếng vào chậm",
        bool(cham_vao) and all(len(v) >= 4 for v in bang.values()),
        f"{len(cham_vao)}/{len(bang)} file đỉnh rơi sau "
        f"{FU._SFX_DICH_TOI_DA:.2f}s (vd {cham_vao[0] if cham_vao else '-'} "
        f"= {bang[cham_vao[0]][3] if cham_vao else 0:.2f}s)")
    bao("tiếng VÀO CHẬM bị loại khỏi điểm nhấn (gốc của nhấp nháy thứ 2)",
        all(not FU._hop_muc(str(FU._assets_sfx_dir() / k), -20.0,
                            FU._SFX_DINH_TRAN_DB) for k in cham_vao),
        f"{len(cham_vao)} file vào chậm đều bị loại dù mức âm vừa đẹp")
    bao("tiếng vào chậm vừa phải thì được DÓNG cho đỉnh rơi ĐÚNG mốc",
        FU._moc_dinh_sfx(str(FU._assets_sfx_dir() / "reveal"
                             / "sparkle_03_v2.opus")) >= 0.0,
        f"vd sparkle_03_v2 đỉnh ở "
        f"{FU._moc_dinh_sfx(str(FU._assets_sfx_dir()/'reveal'/'sparkle_03_v2.opus')):.2f}s"
        f" -> app đẩy sớm đúng bấy nhiêu (trần {FU._SFX_DICH_TOI_DA:.2f}s)")
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
    # DUCKING PHẢI NẰM SAU MỐC — nếu nó trùm lên chính cú va thì mốc NHỎ ĐI
    bao("ducking bắt đầu SAU mốc (cú va phải tự xuyên qua)",
        FU._SFX_DUCK_SOM < 0.0 and f"between(t,{1.0 - FU._SFX_DUCK_SOM:.3f}" in d,
        f"mốc 1,00 s -> bướu bắt đầu {1.0 - FU._SFX_DUCK_SOM:.2f} s, "
        f"sâu {FU._SFX_DUCK_DB:.0f} dB, dài {FU._SFX_DUCK_DAI:.2f} s")
    # HẠN ĐỈNH: 3 tuỳ chọn bắt buộc, thiếu cái nào cũng là một lỗi ÂM THẦM
    h = FU._han_dinh(-2.0)
    bao("chuỗi hạn đỉnh có `level=0` (không tự nâng) + `latency=1` (0 ms trễ)",
        "level=0" in h and "latency=1" in h and "alimiter" in h, h)


def ca_ba_nen(td: str) -> None:
    """CA CHÍNH — 3 VIDEO THẬT NỀN KHÁC NHAU. Đây là ca mà bản cổng cũ THIẾU."""
    print(f"\n[CA 2] BA MỨC NỀN — mọi mốc phải nổi >= {NOI_MIN:+.0f} dB trên "
          f"NỀN CỤC BỘ và KHÔNG mốc nào nhỏ đi")
    tong_xau, tong_nho, tong_at, tong_meo, n_moc = [], [], [], [], 0
    for ten, mo_ta, ss, n_seg in BA_NEN:
        src = tim_nguon(mo_ta)
        segs = ([(ss, ss + 13.0)] if n_seg == 1
                else [(ss, ss + MOC_NOI), (ss + 30.0, ss + 30.0 + 6.0)])
        d = os.path.join(td, ten.replace(" ", "_").replace("Ề", "E")
                         .replace("Ì", "I").replace("Ồ", "O"))
        os.makedirs(d, exist_ok=True)
        a, b = os.path.join(d, "on.mp4"), os.path.join(d, "off.mp4")
        log = xuat(src, a, segs, [dict(c) for c in HU_MOC], True,
                   cats=["impact"])
        xuat(src, b, segs, [dict(c) for c in HU_MOC], False, cats=["impact"])
        pa, pb = pcm(a), pcm(b)
        ra, rb = rms_day(pa), rms_day(pb)
        rl = rms_day(hieu(pa, pb))
        l_db = db(muc_loi(rb))
        mocs = sorted([float(c["bat"]) for c in HU_MOC]
                      + ([MOC_NOI] if n_seg > 1 else []))
        pk, cham = do_dinh_file(a)
        pk_t, cham_t = do_dinh_file(b)
        print(f"    --- {ten} ({n_seg} đoạn) · {Path(src).name[:34]} · "
              f"mức lời {l_db:.1f} dBFS · đỉnh file BẬT {pk:+.2f} ({cham} mẫu "
              f"chạm trần) / TẮT {pk_t:+.2f} ({cham_t} mẫu) ---")
        for g in mocs:
            n_db = db(nen_cuc_bo(rb, g))
            on, off = db(dinh(ra, g)), db(dinh(rb, g))
            lop = db(dinh(rl, g))
            noi, dl = on - n_db, on - off
            n_moc += 1
            c = "  " if (noi >= NOI_MIN and dl >= NHO_TOI_DA) else "!!"
            print(f"    {c} {g:5.2f}s nền {n_db:6.1f} · BẬT {on:6.1f} · TẮT "
                  f"{off:6.1f} · NỔI {noi:+5.1f} · Δ {dl:+5.1f} · lớp SFX "
                  f"{lop:6.1f} dBFS")
            if noi < NOI_MIN:
                tong_xau.append(f"{ten}@{g:.2f}s {noi:+.1f}")
            if dl < NHO_TOI_DA:
                tong_nho.append(f"{ten}@{g:.2f}s {dl:+.1f}")
            if lop > l_db + 20 * math.log10(AT_LOI_LAN) + 2.0:
                tong_at.append(f"{ten}@{g:.2f}s lớp {lop:.1f} vs lời {l_db:.1f}")
        sach = (pk <= TRAN_DINH_DB and cham == 0)
        khong_te_hon = (pk <= pk_t + 0.01 and cham <= cham_t)
        if not (sach or (pk_t > TRAN_DINH_DB and khong_te_hon)):
            tong_meo.append(f"{ten} BẬT {pk:+.2f} dBFS/{cham} mẫu vs TẮT "
                            f"{pk_t:+.2f}/{cham_t} mẫu")
        if not log:
            tong_xau.append(f"{ten}: KHÔNG có tiếng động nào")
    bao(f"mọi mốc NỔI >= {NOI_MIN:+.0f} dB trên nền cục bộ ({n_moc} mốc / "
        f"3 mức nền)", not tong_xau, "; ".join(tong_xau) or f"{n_moc}/{n_moc} đạt")
    bao("KHÔNG mốc nào NHỎ ĐI so với bản tắt tiếng động",
        not tong_nho, "; ".join(tong_nho) or f"{n_moc}/{n_moc} không tụt")
    bao(f"tiếng động KHÔNG ÁT LỜI (lớp SFX <= {AT_LOI_LAN}x mức lời)",
        not tong_at, "; ".join(tong_at) or "cả 3 nền đều dưới trần")
    bao(f"KHÔNG MÉO: đỉnh file <= {TRAN_DINH_DB:.0f} dBFS + 0 mẫu chạm trần "
        f"(nguồn đã méo sẵn -> BẬT phải không tệ hơn TẮT)",
        not tong_meo, "; ".join(tong_meo) or "cả 3 file đạt")


def ca_diem_nhan_co_tieng(src: str, td: str) -> None:
    print("\n[CA 3] MỖI ĐIỂM NHẤN HÌNH CÓ TIẾNG ĐI KÈM (clip 1 ĐOẠN — không có "
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


def ca_ducking(src: str, td: str) -> None:
    print("\n[CA 4] DUCKING: có thật, êm, và KHÔNG trùm lên chính cú va")
    segs = [(240.0, 245.0), (260.0, 265.0)]        # điểm nối ở 5,00 s
    hu = [{"bat": 1.20, "het": 1.60, "khoa": "zoom_nhoi", "dam": 0.25},
          {"bat": 7.60, "het": 8.00, "khoa": "o_vuong", "dam": 0.25}]
    b = os.path.join(td, "m_off.mp4")
    log = xuat(src, os.path.join(td, "m_on.mp4"), segs, hu, True,
               cats=["impact"])
    xuat(src, b, segs, hu, False, cats=["impact"])
    pb = pcm(b)
    moc = sorted([5.00] + [float(c["bat"]) for c in hu])
    bao("điểm NỐI và điểm NHẤN đều có mặt trong nhật ký",
        {x.get("vai") for x in log} == {"nối", "điểm nhấn"},
        " · ".join(f"{x['giay']}s {x['vai']}/{x['loai']} {x['db']:+.1f}dB"
                   for x in log))
    # ---- ĐO RIÊNG, KHÔNG ĐO CHUNG VỚI TIẾNG ĐỘNG ----
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
    giam, tai_moc = [], []
    for g in moc:
        a0 = g - FU._SFX_DUCK_SOM
        i0 = max(0, int(a0 / CUA))
        i1 = min(len(rc_), len(rb), int((a0 + FU._SFX_DUCK_DAI) / CUA) + 1)
        xs = [db(rc_[i]) - db(rb[i]) for i in range(i0, i1) if rb[i] > 30]
        if xs:
            giam.append(min(xs))
        # CỬA SỔ CỦA CHÍNH CÚ VA (±RONG/2) phải gần như KHÔNG bị hạ
        j0 = max(0, int((g - RONG / 2) / CUA))
        j1 = min(len(rc_), len(rb), int((g + RONG / 2) / CUA) + 1)
        ys = [db(rc_[i]) - db(rb[i]) for i in range(j0, j1) if rb[i] > 30]
        if ys:
            tai_moc.append(min(ys))
    bao("CÓ ducking THẬT: tiếng gốc bị hạ trong cửa sổ tiếng động "
        f"(đặt {FU._SFX_DUCK_DB:.0f} dB)",
        bool(giam) and max(giam) <= -1.0,
        " · ".join(f"{x:+.1f} dB" for x in giam) or "không đo được")
    bao("ducking KHÔNG trùm lên CỬA SỔ CỦA CÚ VA (gốc lỗi 'mốc nhỏ đi')",
        bool(tai_moc) and min(tai_moc) > -1.5,
        "hạ nhiều nhất ngay tại mốc "
        f"{min(tai_moc or [0]):+.2f} dB (bản cũ: -5 dB)")
    ngoai = [db(rc_[i]) - db(rb[i]) for i in range(min(len(rc_), len(rb)))
             if rb[i] > 30 and all(abs(i * CUA - g) > 1.2 for g in moc)]
    bao("ducking KHÔNG rò ra ngoài cửa sổ (tiếng gốc giữ nguyên)",
        not ngoai or min(ngoai) > -1.0,
        f"hạ nhiều nhất ngoài cửa sổ {min(ngoai or [0]):+.2f} dB")


def ca_tat_la_tat(src: str, td: str) -> None:
    print("\n[CA 5] TẮT LÀ TẮT: fx_whoosh=False -> KHÔNG một mẫu âm nào thêm")
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
    print("\n[CA 6] MỌI ĐIỂM NỐI 'none' -> KHÔNG chèn (tôn trọng ý đồ AI)")
    c = os.path.join(td, "t_none.mp4")
    ln = xuat(src, c, segs, "tat", True, cats=["none"])
    bao("join_categories=['none'] + hiệu ứng tắt -> 0 tiếng", not ln,
        f"{len(ln)} tiếng")


def ca_hook(src: str, td: str) -> None:
    print("\n[CA 7] HOOK MỞ ĐẦU: 2 giây đầu phải CÓ điểm nhấn + CÓ tiếng")
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
    pa, pb = pcm(a), pcm(b)
    rl = rms_day(hieu(pa, pb))
    ra, rb = rms_day(pa), rms_day(pb)
    n_db = db(nen_cuc_bo(rb, 0.20))
    dau_db = db(dinh(rl, 0.20, 0.60))
    bao("hook CÓ tiếng đi kèm ngay 2 giây đầu", dau_db > n_db + 3.0,
        f"lớp tiếng ở 0,0-0,5 s = {dau_db:.1f} dBFS · nền cục bộ "
        f"{n_db:.1f} dB")
    bao(f"mốc hook cũng NỔI >= {NOI_MIN:+.0f} dB trên nền cục bộ",
        db(dinh(ra, 0.20, 0.60)) - n_db >= NOI_MIN,
        f"{db(dinh(ra, 0.20, 0.60)) - n_db:+.1f} dB")
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
        print(f"  [nguồn phụ] {Path(src).name[:56]}")
        ca_ham_thuan()
        ca_ba_nen(td)
        ca_diem_nhan_co_tieng(src, td)
        ca_ducking(src, td)
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
