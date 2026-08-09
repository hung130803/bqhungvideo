# -*- coding: utf-8 -*-
"""CỔNG 44 — MỖI ĐIỂM NHẤN HÌNH PHẢI **NGHE RA ĐƯỢC**, ĐO THEO DẢI TẦN.

VÌ SAO CÓ CỔNG NÀY (anh Hùng xem clip THẬT, 08/08/2026):
  *"âm thanh hiệu ứng hay gì ấy thậm chí còn không nghe được gì cả luôn, không
  biết chỗ nào chèn chỗ nào không"* · *"có hiệu ứng mà không có âm thanh cứ sao
  sao ấy"*.

=========================== BẢN THỨ BA CỦA CỔNG NÀY ===========================
Bản 1 (07/08) đo trên MỘT nguồn nền yên -> vô dụng.
Bản 2 (v2.19.0, 08/08) đo trên 3 nguồn, tiêu chí **"NỔI >= +6 dB trên NỀN CỤC
BỘ"** -> báo **12/12 ĐẠT, 41/41 mục xanh**. Anh Hùng xem clip v2.19.0 xuất ra
và vẫn chê: *"hiệu ứng âm thanh nhỏ quá, nó dùng mà không nghe thấy luôn, NÓI
ÁT RỒI hay sao"*.
**ANH ẤY ĐÚNG, VÀ CỔNG ĐANG ĐO SAI THỨ.** Chứng minh bằng chính số của bản 2
(`_do_che_loi.py`, 09/08/2026, 13 mốc trên 3 video thật):
  * "NỀN CỤC BỘ" là bpv20 = mức lúc IM LẶNG. Mốc rơi vào lúc ĐANG NÓI thì
    **CHÍNH GIỌNG NÓI** đã nổi +23,9 dB trên nền đó rồi — tiêu chí +6 dB được
    thoả bởi NGUỒN, không phải bởi tiếng động. Đo được mốc YÊN@1,30s:
    cổng chấm **NỔI +26,0 dB (ĐẠT 4 lần dư)** trong khi mọi dải tần chỉ đổi
    **+0,1 dB** = KHÔNG MỘT AI NGHE RA GÌ.
  * Tai người không nghe "so với nền", tai nghe **so với thứ đang phát CÙNG
    LÚC**. Đo tỉ lệ tiếng động / thứ đang phát: mốc khoảng lặng **+7,0 dB**
    (nghe rõ) · mốc đang nói **−1,6 dB** (bị che).

NAY tiêu chí chính là **"CÓ NGHE RA KHÔNG"**, không phải "có nổi trên nền":
  D_CHE = mức dải tần của bản BẬT − của bản **CHE**, TẠI MỐC, lấy dải LỚN NHẤT
          trong 300 Hz - 7,8 kHz.
  Bản CHE = xuất y hệt bản BẬT (ducking chạy, cùng mốc, cùng độ sâu) nhưng file
  tiếng động là một file gần IM LẶNG (−66 dBFS) -> đó ĐÚNG là **thứ đang che**
  tiếng động ở lượt thật.
  Vì sao thước này phản ánh cái tai nghe:
   (a) Trong CÙNG một dải tới hạn tai KHÔNG tách được tiếng động ra khỏi giọng
       nói — nó chỉ nghe dải đó TO LÊN bao nhiêu SO VỚI THỨ ĐANG CHE. Cộng 2
       nguồn không tương quan: tỉ lệ tín-hiệu/che S dB -> dải to thêm
       `10log10(1+10^(S/10))` dB. S=0 -> +3,0; S=−6 -> +1,0; S=−10 -> +0,4 dB.
       Nên `D_CHE >= 1 dB` ⟺ `SMR >= −6 dB` = ĐÚNG NGƯỠNG CHE.
   (b) Ngưỡng vừa phân biệt được (JND) cường độ của âm phức hợp là ~0,5-1 dB
       -> `NGHE_MIN = 1,0 dB`; "nghe RÕ" = 3,0 dB (SMR 0 dB).
   (c) BỎ DẢI <300 Hz: khán giả Shorts nghe bằng loa điện thoại/laptop, thứ
       gần như không phát được dưới 300 Hz. Đây KHÔNG phải suy đoán — kho 184
       file có 51 file hụt quá 6 dB khi cắt <300 Hz, tệ nhất
       `impact/boom_deep_05.opus` hụt **44,7 dB**; ép đúng file đó vào một mốc
       đang nói thì D_CHE ra **−0,5 dB = KHÔNG NGHE RA** trong khi dải <300 Hz
       vọt lên. Trên máy đo: "rất to". Trên điện thoại: câm. Đúng câu *"dùng mà
       không nghe thấy luôn"*.
   (d) Đo trên FILE .mp4 ĐÃ XUẤT nên tính luôn cả ducking lẫn 2 lớp hạn đỉnh —
       tức đúng thứ phát ra loa, không phải ý định.

**BẪY THƯỚC ĐO ĐÃ SẬP 1 LẦN (09/08/2026) — ĐỪNG LẶP:** bản đầu của cổng này
lấy MỐC là bản **TẮT** (tiếng gốc CHƯA hạ), tức hỏi "chỗ này có TO LÊN không".
Ducking thì CỐ Ý hạ tiếng gốc để dọn chỗ, nên một bản trộn ĐÚNG NGHỀ — hạ giọng
6 dB rồi đặt tiếng động ngang mức giọng đã hạ — cho tổng dải **THẤP HƠN** bản
TẮT 3 dB và bị chấm "KHÔNG NGHE RA". Đo thật trên clip ỒN, mốc 4,40 s: so với
bản TẮT ra **−1,5 dB** (chấm hỏng) trong khi so với bản CHE ra **+4,2 dB**
(nghe rõ). Cùng một file .mp4, hai kết luận ngược nhau — khác nhau đúng ở chỗ
lấy gì làm "thứ đang che". D_LOA (so bản TẮT) vẫn được TÍNH VÀ IN để thấy mốc
có bị thành cái hố không, nhưng nó KHÔNG phải tiêu chí đạt/hỏng.

CỔNG NÀY KIỂM **KẾT QUẢ**, KHÔNG KIỂM Ý ĐỊNH: không ca nào đọc chuỗi lệnh
ffmpeg. Mọi kết luận lấy từ PCM của file .mp4 đã xuất:
  mức tại mốc = RMS 50 ms lớn nhất trong ±0,175 s quanh mốc
  nền cục bộ  = bpv20 đường bao RMS 50 ms trong ±1,5 s quanh mốc (bản TẮT)
  mức lời     = bpv90 đường bao RMS cả clip (bản TẮT)
  LỚP TIẾNG ĐỘNG = HIỆU sóng giữa bản BẬT và bản TẮT (hai bản cùng nguồn, cùng
  timeline nên trừ được từng mẫu) -> số ĐỘC LẬP với tiếng gốc.
  KHÔNG MÉO = `astats` trên chính file .mp4 (đỉnh + số mẫu chạm trần).

MỐC KHÔNG ĐƯỢC ĐẶT CỨNG NỮA: cổng tự DÒ tiếng nguồn rồi đặt mốc vào ĐÚNG chỗ
đang nói và ĐÚNG chỗ im lặng (`chon_moc`). Đặt cứng giây 1,20/4,60/10,40 là phó
mặc cho may rủi xem mốc rơi vào đâu — đúng cách bản 2 bỏ lọt lỗi này.

Chạy: .venv\\Scripts\\python.exe _test_tieng_hieu_ung.py
Env : BQ_TEST=1 · BQ_FFMPEG_SLOTS=1 (LUẬT SỐ 1)
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

import numpy as np                            # noqa: E402
from app.core import ffmpeg_utils as FU      # noqa: E402
from app.core import hieu_ung as HU          # noqa: E402
from config import settings                  # noqa: E402

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF = settings.FFMPEG_PATH
SR = 16000
CUA = 0.05                     # cửa sổ RMS 50 ms
RONG = 0.35                    # bề rộng cửa sổ tìm đỉnh quanh mốc
NEN_RONG = 3.0                 # bề rộng cửa sổ đo NỀN CỤC BỘ

#: DẢI TẦN đo. Giọng người dồn 300-3400 Hz. Dải đầu (<300 Hz) bị LOẠI khỏi mọi
#: kết luận "có nghe ra không" — loa điện thoại không phát được (xem docstring).
DAI = [(60, 300), (300, 1000), (1000, 2400), (2400, 4000), (4000, 7800)]
TEN_DAI = ["<300", "300-1k", "1k-2.4k", "2.4k-4k", ">4k"]

#: ===================== TIÊU CHÍ CHÍNH: CÓ NGHE RA KHÔNG =====================
#: Dải tần (300 Hz trở lên) phải NỔI LÊN KHỎI THỨ ĐANG CHE ít nhất ngần này dB
#: tại mốc. 1,0 dB = ngưỡng vừa phân biệt được (JND) cường độ của âm phức hợp,
#: và cũng ĐÚNG BẰNG tỉ lệ tín-hiệu/che −6 dB. Dưới mức này thì dù máy đo có
#: báo "tiếng động -12 dBFS" cũng KHÔNG ai nghe ra.
NGHE_MIN = 1.0
#: "Nghe RÕ" (không phải chỉ vừa đủ phân biệt) — dùng cho phần lớn số mốc.
NGHE_RO = 3.0
#: Số mốc tối thiểu phải đạt mức "nghe RÕ" (phần còn lại vẫn phải >= NGHE_MIN).
#: 70% chứ không phải 100%: file tiếng động bốc NGẪU NHIÊN (anh Hùng cần 3 Part
#: không kêu giống hệt), nên luôn có mốc trúng file hiền hơn. Đo 5 lượt sau khi
#: sửa: 12-13/13 mốc "RÕ", không lượt nào dưới 70%.
RO_TY_LE = 0.70
#: Anh Hùng chốt 08/08/2026: mốc điểm nhấn phải **nổi >= +6 dB trên nền cục
#: bộ**. GIỮ LẠI nhưng CHỈ CHO CA KHOẢNG LẶNG — ở ca đang nói tiêu chí này vô
#: nghĩa (chính giọng nói đã nổi +24 dB, xem docstring) và nay còn PHẢN TÁC
#: DỤNG: ducking 6 dB dọn chỗ cho cú va làm "NỔI" TỤT xuống trong khi mốc nghe
#: RÕ HƠN HẲN (đo: +5,0 dB nổi nhưng dải to thêm +7,3 dB).
NOI_MIN = 6.0
#: CHỐNG ÁT LỜI: đỉnh RMS lớp tiếng động <= 1,5x mức lời = +3,5 dB. NAY so với
#: **mức lời CỤC BỘ tại chính mốc đó** (hoặc mức lời cả clip, lấy cái CAO hơn)
#: — cùng bất biến, nhưng đo đúng chỗ. So với bpv90 cả clip là vừa quá chặt ở
#: mốc đang nói (mức tại mốc cao hơn bpv90 tới +5,2 dB) vừa quá lỏng ở mốc im.
AT_LOI_LAN = 1.5
#: KHÔNG ÁT LỜI (2): NGOÀI cửa sổ tiếng động, dải giọng nói 300 Hz-4 kHz phải
#: gần như KHÔNG đổi. Đây là vế bảo vệ "video cho người xem, không phải bản
#: demo hiệu ứng" — đo được sau khi sửa: lệch nhiều nhất +0,29 dB.
NGOAI_MOC_MAX = 1.0
#: KHÔNG ĐƯỢC THÀNH CÁI HỐ: ducking dọn chỗ cho tiếng động, nhưng NGAY TẠI MỐC
#: dải giọng nói không được TỤT so với bản TẮT quá ngần này dB — nếu tụt sâu mà
#: tiếng động không lấp lại thì khán giả chỉ nghe thấy giọng bị hụt một cái,
#: tệ hơn là không làm gì. Đặt bằng đúng độ sâu ducking ở mốc đang nói
#: (`_SFX_DUCK_DB_NOI` = 6 dB) + 1,5 dB dung sai đo (phổ FFT cửa sổ 0,35 s có
#: cả phần ngân của âm tiết bên cạnh). Đo sau khi sửa: sâu nhất −5,2 dB.
HUT_MOC_MAX = -7.5
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
def pcm(path: str, dau_vao: list | None = None) -> np.ndarray:
    cmd = [FF, "-v", "error", "-nostdin"]
    cmd += [str(x) for x in (dau_vao or ["-i", path])]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True, creationflags=_NOWIN,
                       timeout=300)
    return np.frombuffer(r.stdout or b"", dtype="<i2").astype(np.float64)


def rms_day(a) -> np.ndarray:
    n = int(SR * CUA)
    m = len(a) // n
    if m <= 0:
        return np.zeros(0)
    return np.sqrt((a[:m * n].reshape(m, n) ** 2).mean(axis=1))


def db(x: float) -> float:
    return 20 * math.log10(max(float(x), 1e-7) / 32768.0)


def bpv(rs, q: float) -> float:
    y = sorted(rs)
    return y[min(len(y) - 1, int(len(y) * q))] if len(y) else 0.0


def nen(rs) -> float:
    return bpv(rs, 0.50)


def pho_dai(a: np.ndarray, giay: float, rong: float = RONG) -> np.ndarray:
    """Mức dBFS TỪNG DẢI trong cửa sổ quanh mốc (cửa sổ Hann + FFT).

    Chuẩn hoá sao cho tổng năng lượng các dải ~ RMS toàn dải của cửa sổ, nên
    con số so sánh được với các mức dB khác trong cổng."""
    i0 = max(0, int((giay - rong / 2) * SR))
    i1 = min(len(a), int((giay + rong / 2) * SR))
    x = a[i0:i1]
    if len(x) < 64:
        return np.full(len(DAI), -99.0)
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w) / (len(x) * math.sqrt(3.0 / 8.0) / 2.0)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    out = []
    for lo, hi in DAI:
        m = (f >= lo) & (f < hi)
        e = float((np.abs(X[m]) ** 2).sum()) / 2.0 if m.any() else 0.0
        out.append(20.0 * math.log10(max(math.sqrt(e), 1e-7) / 32768.0))
    return np.array(out)


def do_nghe_ra(pa: np.ndarray, pb: np.ndarray, giay: float,
               rong: float = RONG) -> tuple[float, np.ndarray]:
    """**THƯỚC CHÍNH CỦA CỔNG**: tại mốc `giay`, dải tần nào NỔI LÊN KHỎI THỨ
    ĐANG CHE nhiều nhất và bao nhiêu dB — chỉ tính từ 300 Hz trở lên (loa điện
    thoại).

    `pa` = bản BẬT · `pb` = **THỨ ĐANG CHE** (bản CHE: ducking chạy y hệt, file
    tiếng động im lặng). Truyền bản TẮT vào đây là ra D_LOA — con số THAM KHẢO,
    không phải tiêu chí (xem "BẪY THƯỚC ĐO" ở đầu file).

    Trả (D_CHE, mảng chênh lệch từng dải). Đây là "có nghe ra không" chứ không
    phải "có to hơn nền không": trong cùng một dải tới hạn, tai chỉ nghe được
    dải đó to lên bao nhiêu so với thứ đang che, không tách được tiếng động
    khỏi giọng nói."""
    d = pho_dai(pa, giay, rong) - pho_dai(pb, giay, rong)
    return float(d[1:].max()), d


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


def dinh(rs, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    seg = rs[i0:i1]
    return float(seg.max()) if len(seg) else 0.0


def hieu(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Sóng HIỆU (bản bật − bản tắt) = chính lớp tiếng động + phần ducking."""
    n = min(len(a), len(b))
    return np.clip(a[:n] - b[:n], -32768, 32767)


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
#: Kiểu hiệu ứng dùng cho mốc tự dò — trải đủ nhóm tiếng (impact/scratch/
#: reveal/riser) để không vô tình chỉ kiểm một nhóm.
KHOA_DO = ["zoom_nhoi", "glitch_khoi", "loe_sang", "rung_lac", "tuong_phan",
           "quang_sang"]


def chon_moc(src: str, ss: float, dai: float) -> tuple[list, list]:
    """DÒ TRƯỚC tiếng nguồn rồi trả (mốc ĐANG NÓI, mốc KHOẢNG LẶNG).

    ĐÂY LÀ CHỖ BẢN 2 CỦA CỔNG BỎ LỌT LỖI: nó đặt CỨNG mốc ở giây 1,20/4,60/
    10,40 rồi mặc kệ mốc rơi vào đâu. Muốn bắt được ca "nói át rồi" thì phải
    CỐ Ý đặt mốc vào đúng lúc đang nói — và cũng phải cố ý đặt vào đúng khoảng
    lặng để chứng minh ca kia không bị làm hỏng theo.

    Chỉ giải mã ÂM THANH của đoạn sắp cắt (không qua cửa chờ ffmpeg, ~0,2 s)."""
    a = pcm("", ["-ss", f"{ss:.3f}", "-t", f"{dai:.3f}", "-i", src])
    rs = rms_day(a)
    if not len(rs):
        return [], []
    loi = float(np.percentile(rs, 90))
    nn = float(np.percentile(rs, 20))
    to, im = [], []
    for i, v in enumerate(rs):
        t = i * CUA
        if t < 1.0 or t > dai - 1.2:
            continue
        if v >= loi * 0.9:
            to.append((float(v), t))
        elif v <= nn * 1.6:
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
    m_noi = thua(to, 3)
    m_im = [t for t in thua(im, 3) if all(abs(t - x) >= 1.6 for x in m_noi)]
    return m_noi, m_im


def hu_tu_moc(mocs: list) -> list:
    return [{"bat": round(t, 2), "het": round(t + 0.40, 2),
             "khoa": KHOA_DO[i % len(KHOA_DO)], "dam": 0.25}
            for i, t in enumerate(sorted(mocs))]


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
    # ---- BỊ **LỜI NÓI** CHE: đích phải bám MỨC LỜI CỤC BỘ TẠI MỐC ----
    # TỰ KIỂM BỘ DÒ: dựng lại đúng công thức CŨ (v2.19.0, không có `loi_moc`)
    # và bắt nó phải THUA — không thì cổng chỉ là con dấu.
    # Cái sai của công thức cũ KHÔNG phải "đặt đích thấp", mà là **đích KHÔNG
    # PHỤ THUỘC MỐC**: nó chỉ biết bpv90 CẢ CLIP. Đo 3 video thật, mức lời NGAY
    # TẠI mốc cao hơn bpv90 tới **+5,2 dB** (YÊN: bpv90 -19,6 · tại mốc -14,4).
    # Nên cứ mốc nào rơi vào chỗ nói to hơn trung bình là đích cũ thua.
    DO_LECH = 5.2                  # mức lời tại mốc − bpv90, đo được cao nhất
    xau2 = []
    for nn, ll in ((-37.0, -19.6), (-21.8, -13.6), (-22.3, -11.2),
                   (-30.0, -18.0)):
        cu = FU.dich_sfx_dB("impact", nn, ll)          # công thức CŨ
        if cu > ll + DO_LECH:      # đích cũ vẫn với tới mức lời tại mốc?
            xau2.append((nn, ll, round(cu, 1)))
        if abs(cu - FU.dich_sfx_dB("impact", nn, ll, ll + DO_LECH)) < 0.01:
            xau2.append(("KHÔNG ĐỔI THEO MỐC", nn, ll))
    bao(f"TỰ KIỂM: công thức CŨ mù mốc -> THUA mức lời tại mốc (+{DO_LECH} dB "
        f"trên bpv90, đo thật)", not xau2,
        "4/4 cảnh đo thật đều thua: "
        + " · ".join(f"lời tại mốc {ll+DO_LECH:.1f} nhưng đích cũ "
                     f"{FU.dich_sfx_dB('impact', nn, ll):.1f} dBFS"
                     for nn, ll in ((-37.0, -19.6), (-22.3, -11.2)))
        if not xau2 else str(xau2[:3]))
    xau3 = []
    for nn, ll, lm in ((-37.0, -19.6, -14.4), (-21.8, -13.6, -9.9),
                       (-22.3, -11.2, -10.2), (-30.0, -18.0, -12.0),
                       (-22.3, -11.2, -6.0)):
        moi = FU.dich_sfx_dB("impact", nn, ll, lm)     # công thức MỚI
        if moi < lm + FU._SFX_TREN_LOI_MOC_DB - 0.01:
            xau3.append((nn, ll, lm, round(moi, 1)))
        if moi > max(ll, lm) + tran + 0.01:            # vẫn không được át lời
            xau3.append(("ÁT LỜI", nn, ll, lm, round(moi, 1)))
    bao(f"công thức MỚI luôn đạt lời cục bộ +{FU._SFX_TREN_LOI_MOC_DB:.1f} dB "
        f"mà VẪN dưới {AT_LOI_LAN}x mức lời", not xau3,
        " · ".join(f"lời tại mốc {lm:.1f} -> đích "
                   f"{FU.dich_sfx_dB('impact', nn, ll, lm):.1f} dBFS"
                   for nn, ll, lm in ((-37.0, -19.6, -14.4),
                                      (-22.3, -11.2, -10.2)))
        if not xau3 else str(xau3[:3]))
    bao("mốc rơi vào KHOẢNG LẶNG KHÔNG bị hạ đích theo (trần lấy max)",
        abs(FU.dich_sfx_dB("impact", -37.0, -19.6, -34.0)
            - FU.dich_sfx_dB("impact", -37.0, -19.6)) < 0.01,
        f"lời cả clip -19,6 · tại mốc -34,0 -> đích "
        f"{FU.dich_sfx_dB('impact', -37.0, -19.6, -34.0):.1f} dBFS "
        f"(đúng bằng bản không truyền mức cục bộ)")
    # ĐO MỨC TẠI MỐC: hàm thuần, dựng đường bao giả có 1 chỗ to
    _bao = [-40.0] * 40
    _bao[20] = -12.0                       # giây 1,00 có tiếng to
    bao("`muc_tai_moc` lấy ĐỈNH trong cửa sổ ±0,175 s (không phải trung bình)",
        abs(FU.muc_tai_moc(_bao, 0.05, 1.0) + 12.0) < 0.01
        and abs(FU.muc_tai_moc(_bao, 0.05, 1.5) + 40.0) < 0.01,
        f"tại 1,00 s -> {FU.muc_tai_moc(_bao, 0.05, 1.0):.1f} dBFS · "
        f"tại 1,50 s -> {FU.muc_tai_moc(_bao, 0.05, 1.5):.1f} dBFS")
    bao("`la_moc_dang_noi` tách được mốc ĐANG NÓI với mốc KHOẢNG LẶNG",
        FU.la_moc_dang_noi(_bao, 0.05, 1.0)
        and not FU.la_moc_dang_noi(_bao, 0.05, 1.5),
        f"chỗ to -> {FU.la_moc_dang_noi(_bao, 0.05, 1.0)} · chỗ im -> "
        f"{FU.la_moc_dang_noi(_bao, 0.05, 1.5)} "
        f"(ngưỡng {FU._SFX_DANG_NOI_DB:.0f} dB trên nền cục bộ)")
    bao("thiếu đường bao -> trả None/False (rơi đúng về đường cũ, không nổ)",
        FU.muc_tai_moc([], 0.05, 1.0) is None
        and not FU.la_moc_dang_noi([], 0.05, 1.0), "[] -> None + False")
    # LOA ĐIỆN THOẠI + LỆCH DẢI TẦN — 2 cột mới của bảng mức
    _bang = FU._sfx_bang_muc()
    _tram = [k for k, v in _bang.items()
             if len(v) >= 5 and float(v[4]) < FU._SFX_LOA_HUT_MAX]
    bao("bảng mức có cột 5 (HỤT QUA LOA) và kho THẬT SỰ có file trầm câm",
        all(len(v) >= 5 for v in _bang.values()) and len(_tram) >= 20,
        f"{len(_tram)}/{len(_bang)} file hụt quá {-FU._SFX_LOA_HUT_MAX:.0f} dB "
        f"khi cắt <300 Hz · tệ nhất "
        f"{min(float(v[4]) for v in _bang.values()):.1f} dB")
    bao("bảng mức có cột 6 (ĐỘ SÁNG >4 kHz) và đo được thật (không phải -99)",
        all(len(v) >= 6 for v in _bang.values())
        and max(float(v[5]) for v in _bang.values()) > -20.0,
        f"sáng nhất {max(float(v[5]) for v in _bang.values()):.1f} dB · "
        f"trung vị "
        f"{sorted(float(v[5]) for v in _bang.values())[len(_bang)//2]:.1f} dB")
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
    # MỐC KHOẢNG LẶNG: bướu NẰM SAU mốc (giữ đúng cách v2.19.0 — đang chạy tốt)
    bao("mốc KHOẢNG LẶNG: ducking bắt đầu SAU mốc (cú va tự xuyên qua)",
        FU._SFX_DUCK_SOM < 0.0
        and f"between(t,{1.0 - FU._SFX_DUCK_SOM:.3f}" in d,
        f"mốc 1,00 s -> bướu bắt đầu {1.0 - FU._SFX_DUCK_SOM:.2f} s, "
        f"sâu {FU._SFX_DUCK_DB:.0f} dB, dài {FU._SFX_DUCK_DAI:.2f} s")
    # MỐC ĐANG NÓI: bướu phải MỞ RA TRƯỚC mốc và SÂU HƠN — dọn chỗ cho cú va
    dn = FU._bieu_thuc_duck([1.0], sau_db=[FU._SFX_DUCK_DB_NOI],
                            dang_noi=[True])
    _a_noi = 1.0 - FU._SFX_DUCK_SOM_NOI
    bao("mốc ĐANG NÓI: bướu mở ra TRƯỚC mốc và đỉnh bướu rơi ĐÚNG vào mốc",
        FU._SFX_DUCK_SOM_NOI > 0.0
        and f"between(t,{_a_noi:.3f}" in dn
        and abs(_a_noi + FU._SFX_DUCK_DAI_NOI / 2.0 - 1.0) < 0.01,
        f"mốc 1,00 s -> bướu {_a_noi:.3f}..{_a_noi+FU._SFX_DUCK_DAI_NOI:.3f} s, "
        f"đỉnh ở {_a_noi + FU._SFX_DUCK_DAI_NOI/2.0:.3f} s, sâu "
        f"{FU._SFX_DUCK_DB_NOI:.0f} dB")
    bao("mốc ĐANG NÓI được dọn chỗ SÂU HƠN mốc khoảng lặng",
        FU._SFX_DUCK_DB_NOI > FU._SFX_DUCK_DB,
        f"đang nói {FU._SFX_DUCK_DB_NOI:.0f} dB · khoảng lặng "
        f"{FU._SFX_DUCK_DB:.0f} dB")
    # 2 mốc SÂU KHÁC NHAU trong CÙNG một biểu thức -> mỗi bướu mang hệ số riêng
    d2 = FU._bieu_thuc_duck([1.0, 5.0], sau_db=[3.0, 6.0],
                            dang_noi=[False, True])
    _h3 = 1.0 - 10.0 ** (-3.0 / 20.0)
    _h6 = 1.0 - 10.0 ** (-6.0 / 20.0)
    bao("2 mốc sâu KHÁC NHAU cùng một biểu thức -> mỗi bướu một hệ số riêng",
        f"{_h3:.3f}*between" in d2 and f"{_h6:.3f}*between" in d2,
        f"có cả hệ số {_h3:.3f} (3 dB) và {_h6:.3f} (6 dB)")
    bao("ducking KHÔNG bao giờ hạ quá 100% (2 bướu chồng nhau vẫn không câm)",
        "min(1," in d2, "min(1,...) bọc ngoài tổng các bướu")
    # HẠN ĐỈNH: 3 tuỳ chọn bắt buộc, thiếu cái nào cũng là một lỗi ÂM THẦM
    h = FU._han_dinh(-2.0)
    bao("chuỗi hạn đỉnh có `level=0` (không tự nâng) + `latency=1` (0 ms trễ)",
        "level=0" in h and "latency=1" in h and "alimiter" in h, h)


def thu_muc_im(td: str) -> str:
    """Thư mục chứa ĐÚNG 1 file tiếng động gần IM LẶNG (−66 dBFS).

    Xuất với `fx_sfx_dir` trỏ vào đây thì ducking chạy Y HỆT lượt thật (cùng
    mốc, cùng độ sâu, cùng lớp hạn đỉnh) còn lớp tiếng động thì không nghe
    thấy -> file ra chính là **THỨ ĐANG CHE**. Không có bản này thì không cách
    nào tách "dải tụt vì ducking" khỏi "tiếng động quá nhỏ" — và đó đúng là chỗ
    bản đầu của cổng chấm hỏng oan (xem "BẪY THƯỚC ĐO" ở đầu file). Cùng mẹo mà
    CA 5 đã dùng để đo DUCKING THUẦN."""
    d = os.path.join(td, "_sfx_im")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "im.wav")
    if not os.path.exists(f):
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                        "sine=f=1000:d=0.30", "-af", "volume=0.0005",
                        "-ac", "2", "-ar", "48000", f],
                       capture_output=True, creationflags=_NOWIN, timeout=120)
    return d


def do_mot_clip(ten: str, src: str, ss: float, dai: float, td: str,
                voice_vol: float = 1.0) -> dict:
    """Xuất BẬT / TẮT / CHE với mốc TỰ DÒ (đang nói + khoảng lặng) rồi đo.

    Trả dict gom mọi vi phạm — caller quyết định báo mục nào."""
    m_noi, m_im = chon_moc(src, ss, dai)
    if not m_noi or not m_im:
        raise RuntimeError(f"{ten}: đoạn này không đủ cả chỗ nói lẫn chỗ im "
                           f"({len(m_noi)} nói / {len(m_im)} im)")
    ca_theo_moc = {round(t, 2): "ĐANG NÓI" for t in m_noi}
    ca_theo_moc.update({round(t, 2): "KHOẢNG LẶNG" for t in m_im})
    hu = hu_tu_moc(m_noi + m_im)
    d = os.path.join(td, ten)
    os.makedirs(d, exist_ok=True)
    a, b = os.path.join(d, "on.mp4"), os.path.join(d, "off.mp4")
    ch = os.path.join(d, "che.mp4")
    segs = [(ss, ss + dai)]
    log = xuat(src, a, segs, [dict(c) for c in hu], True, orig_vol=voice_vol)
    xuat(src, b, segs, [dict(c) for c in hu], False, orig_vol=voice_vol)
    xuat(src, ch, segs, [dict(c) for c in hu], True, orig_vol=voice_vol,
         fx_sfx_dir=thu_muc_im(td))
    pa, pb = pcm(a), pcm(b)
    n = min(len(pa), len(pb))
    pa, pb = pa[:n], pb[:n]
    pm = pcm(ch)[:n]
    ra, rb = rms_day(pa), rms_day(pb)
    rl = rms_day(hieu(pa, pb))
    l_db = db(muc_loi(rb))
    pk, cham = do_dinh_file(a)
    pk_t, cham_t = do_dinh_file(b)
    print(f"    --- {ten} · {Path(src).name[:30]} · mức lời {l_db:.1f} dBFS · "
          f"{len(log)} tiếng · đỉnh BẬT {pk:+.2f} ({cham} mẫu) / TẮT "
          f"{pk_t:+.2f} ({cham_t} mẫu) ---")
    print(f"      {'mốc':>6} {'ca':<12} {'nền':>6} {'TẮT':>6} {'BẬT':>6} "
          f"{'NỔI':>6} {'SFX':>6} | " + " ".join(f"{x:>7}" for x in TEN_DAI)
          + "  D_LOA  D_CHE nghe?")
    kq: dict = {"cam": [], "at": [], "meo": [], "noi_thap": [], "moc": [],
                "loi_db": l_db, "hut": 0.0}
    for g in sorted(ca_theo_moc):
        ca = ca_theo_moc[g]
        n_db = db(nen_cuc_bo(rb, g))
        on, off = db(dinh(ra, g)), db(dinh(rb, g))
        lop = db(dinh(rl, g))
        dche, dd = do_nghe_ra(pa, pm, g)     # so với THỨ ĐANG CHE  <- tiêu chí
        dloa, dd_tat = do_nghe_ra(pa, pb, g)  # so với nguồn CHƯA hạ <- tham khảo
        nghe = "RÕ" if dche >= NGHE_RO else ("mờ" if dche >= NGHE_MIN
                                             else "KHÔNG")
        c = "  " if dche >= NGHE_MIN else "!!"
        print(f"    {c} {g:5.2f}s {ca:<12} {n_db:6.1f} {off:6.1f} {on:6.1f} "
              f"{on - n_db:+6.1f} {lop:6.1f} | "
              + " ".join(f"{v:+7.1f}" for v in dd)
              + f" {dloa:+6.1f} {dche:+6.1f} {nghe}")
        kq["moc"].append({"giay": g, "ca": ca, "dloa": dloa, "dche": dche,
                          "nghe": nghe})
        if dche < NGHE_MIN:
            kq["cam"].append(f"{ten}@{g:.2f}s [{ca}] nổi khỏi thứ đang che "
                             f"{dche:+.1f} dB")
        # KHÔNG ĐƯỢC THÀNH CÁI HỐ: ducking hạ giọng mà tiếng động không lấp
        # lại thì khán giả chỉ nghe "hụt một cái" — tệ hơn không làm gì.
        _hut = float(dd_tat[1:4].min())
        kq["hut"] = min(kq["hut"], _hut)
        if _hut < HUT_MOC_MAX:
            kq["at"].append(f"{ten}@{g:.2f}s [{ca}] dải giọng TỤT {_hut:+.1f} "
                            f"dB so bản TẮT (trần {HUT_MOC_MAX:+.1f})")
        # CHỐNG ÁT LỜI — so với mức lời CỤC BỘ tại mốc (hoặc cả clip, cái CAO
        # hơn): lớp tiếng động không được vượt 1,5x. +2,0 dB dung sai đo vì lớp
        # SFX tách bằng phép trừ sóng nên dính cả nhiễu lượng tử AAC.
        _tran = max(l_db, off) + 20 * math.log10(AT_LOI_LAN) + 2.0
        if lop > _tran:
            kq["at"].append(f"{ten}@{g:.2f}s lớp {lop:.1f} > trần {_tran:.1f}")
        if ca == "KHOẢNG LẶNG" and (on - n_db) < NOI_MIN:
            kq["noi_thap"].append(f"{ten}@{g:.2f}s {on - n_db:+.1f} dB")
    # ---- KHÔNG ÁT LỜI (2): NGOÀI cửa sổ tiếng động, giọng nói giữ nguyên ----
    ngoai = []
    for i in range(len(rb)):
        t = i * CUA
        if any(abs(t - g) < 2.0 for g in ca_theo_moc):
            continue
        if rb[i] < 300:                      # bỏ chỗ im (nhiễu lượng tử AAC)
            continue
        ngoai.append(float((pho_dai(pa, t, 0.10)
                            - pho_dai(pb, t, 0.10))[1:4].max()))
    kq["ngoai"] = (max(ngoai) if ngoai else 0.0)
    kq["n_ngoai"] = len(ngoai)
    if ngoai and max(ngoai) > NGOAI_MOC_MAX:
        kq["at"].append(f"{ten}: NGOÀI mốc dải giọng đổi {max(ngoai):+.2f} dB")
    print(f"      [không át lời] ngoài mốc, dải giọng 300-4k đổi nhiều nhất "
          f"{kq['ngoai']:+.2f} dB ({kq['n_ngoai']} cửa sổ)")
    sach = (pk <= TRAN_DINH_DB and cham == 0)
    khong_te_hon = (pk <= pk_t + 0.01 and cham <= cham_t)
    if not (sach or (pk_t > TRAN_DINH_DB and khong_te_hon)):
        kq["meo"].append(f"{ten} BẬT {pk:+.2f} dBFS/{cham} mẫu vs TẮT "
                         f"{pk_t:+.2f}/{cham_t} mẫu")
    if not log:
        kq["cam"].append(f"{ten}: KHÔNG có tiếng động nào")
    return kq


def _gom(ket: list) -> None:
    """Báo cáo chung cho CA 2 và CA 3 — TÁCH RIÊNG 2 ca."""
    moc = [m for k in ket for m in k["moc"]]
    xau = [x for k in ket for x in k["cam"]]
    at = [x for k in ket for x in k["at"]]
    meo = [x for k in ket for x in k["meo"]]
    nt = [x for k in ket for x in k["noi_thap"]]
    for ca in ("ĐANG NÓI", "KHOẢNG LẶNG"):
        g = [m for m in moc if m["ca"] == ca]
        if not g:
            continue
        n_ro = sum(1 for m in g if m["nghe"] == "RÕ")
        print(f"      >> ca {ca:<12}: {len(g)} mốc · RÕ {n_ro} · mờ "
              f"{sum(1 for m in g if m['nghe'] == 'mờ')} · KHÔNG "
              f"{sum(1 for m in g if m['nghe'] == 'KHÔNG')} · D_CHE "
              f"{min(m['dche'] for m in g):+.1f} .. "
              f"{max(m['dche'] for m in g):+.1f} dB (D_LOA "
              f"{min(m['dloa'] for m in g):+.1f} .. "
              f"{max(m['dloa'] for m in g):+.1f})")
    n_ro = sum(1 for m in moc if m["nghe"] == "RÕ")
    bao(f"MỌI mốc NGHE RA ĐƯỢC (dải 300 Hz+ nổi khỏi THỨ ĐANG CHE >= "
        f"{NGHE_MIN:.0f} dB) — {len(moc)} mốc, cả ca ĐANG NÓI lẫn KHOẢNG LẶNG",
        not xau, "; ".join(xau) or f"{len(moc)}/{len(moc)} đạt · thấp nhất "
        f"{min(m['dche'] for m in moc):+.1f} dB")
    bao(f"phần lớn mốc nghe RÕ (>= {NGHE_RO:.0f} dB, tối thiểu "
        f"{RO_TY_LE*100:.0f}% số mốc)",
        bool(moc) and n_ro >= RO_TY_LE * len(moc),
        f"{n_ro}/{len(moc)} mốc RÕ ({100.0*n_ro/max(1,len(moc)):.0f}%)")
    bao(f"tiếng động KHÔNG ÁT LỜI, cũng KHÔNG thành CÁI HỐ (lớp SFX <= "
        f"{AT_LOI_LAN}x mức lời tại mốc · ngoài mốc dải giọng đổi <= "
        f"{NGOAI_MOC_MAX:.1f} dB · tại mốc không tụt quá {-HUT_MOC_MAX:.1f} dB)",
        not at, "; ".join(at) or
        f"ngoài mốc đổi nhiều nhất {max(k['ngoai'] for k in ket):+.2f} dB · "
        f"tại mốc tụt sâu nhất {min(k['hut'] for k in ket):+.2f} dB")
    bao(f"mốc KHOẢNG LẶNG vẫn NỔI >= {NOI_MIN:+.0f} dB trên nền cục bộ "
        f"(giữ đúng bất biến v2.19.0)", not nt, "; ".join(nt) or "đạt hết")
    bao(f"KHÔNG MÉO: đỉnh file <= {TRAN_DINH_DB:.0f} dBFS + 0 mẫu chạm trần "
        f"(nguồn đã méo sẵn -> BẬT phải không tệ hơn TẮT)",
        not meo, "; ".join(meo) or f"{len(ket)}/{len(ket)} file đạt")


def ca_ba_nen(td: str) -> None:
    """CA CHÍNH — 3 VIDEO THẬT NỀN KHÁC NHAU, mốc TỰ DÒ vào đúng chỗ đang nói
    và đúng chỗ im lặng. Đây là ca bắt được lỗi "nói át rồi"."""
    print(f"\n[CA 2] BA MỨC NỀN x (mốc ĐANG NÓI + mốc KHOẢNG LẶNG) — mọi mốc "
          f"phải NGHE RA ĐƯỢC (dải 300 Hz+ nổi khỏi THỨ ĐANG CHE >= "
          f"{NGHE_MIN:.0f} dB)")
    ket = []
    for ten, mo_ta, ss, _n_seg in BA_NEN:
        ket.append(do_mot_clip(ten.replace(" ", "_").replace("Ề", "E")
                               .replace("Ì", "I").replace("Ồ", "O"),
                               tim_nguon(mo_ta), ss, 13.0, td))
    _gom(ket)


def ca_giong_to_nho(td: str) -> None:
    """GIỌNG TO vs GIỌNG NHỎ — cùng một nguồn, chỉ khác mức lời.

    Vì sao phải có: đích tiếng động bám MỨC LỜI, nên nếu chỗ nào tính thiếu bù
    `voice_vol` thì clip giọng nhỏ sẽ có tiếng động to lố (hoặc ngược lại) mà
    ca "3 mức nền" không thấy — cả 3 nguồn đó đều để `voice_vol=1,0`."""
    print("\n[CA 3] GIỌNG TO (lời ~-12 dBFS) vs GIỌNG NHỎ — đích phải bám lời")
    ket = []
    ket.append(do_mot_clip("giong_TO", tim_nguon(BA_NEN[2][1]), 300.0, 13.0,
                           td, voice_vol=1.0))
    ket.append(do_mot_clip("giong_NHO", tim_nguon(BA_NEN[0][1]), 240.0, 13.0,
                           td, voice_vol=0.25))
    to, nho = ket[0]["loi_db"], ket[1]["loi_db"]
    bao("2 ca THẬT SỰ khác mức lời (không thì ca này vô nghĩa)",
        to - nho >= 10.0, f"giọng TO {to:.1f} dBFS · giọng NHỎ {nho:.1f} dBFS "
        f"· cách {to - nho:.1f} dB")
    bao("giọng TO đạt mức lời ~-12 dBFS (đúng ca anh Hùng nêu)",
        to >= -15.0, f"{to:.1f} dBFS")
    _gom(ket)


def ca_tu_kiem_bo_do(td: str) -> None:
    """TỰ KIỂM BỘ DÒ — cổng phải BIẾT KÊU, không thì nó chỉ là con dấu.

    Ép ĐÚNG 1 file tiếng động vào cùng một mốc ĐANG NÓI, cùng clip, cùng hệ số
    (thay `_sfx_library`, đường dẫn vẫn trong kho nên `muc_do.json` tra được —
    trỏ `fx_sfx_dir` ra ngoài kho thì `_muc_sfx3` lùi về số suy ra, hệ số lệch
    và phép so mất nghĩa):
      * file SÁNG, không hụt qua loa -> cổng phải chấm NGHE RA;
      * file TRẦM `boom_deep_05` (hụt **44,7 dB** khi cắt <300 Hz) -> cổng phải
        chấm **KHÔNG NGHE RA**.
    Đây đúng ca anh Hùng gặp: trên máy đo nó "to đúng đích", trên điện thoại nó
    câm. Bản trước của cổng chấm ca này ĐẠT."""
    print("\n[CA 3B] TỰ KIỂM BỘ DÒ: ép file TRẦM vào mốc đang nói -> cổng phải "
          "chấm KHÔNG NGHE RA")
    ten, mo_ta, ss = "tu_kiem", BA_NEN[2][1], 300.0
    src = tim_nguon(mo_ta)
    m_noi, _m_im = chon_moc(src, ss, 13.0)
    if not m_noi:
        bao("tìm được mốc ĐANG NÓI để ép file", False, "không có mốc nào")
        return
    g = sorted(m_noi)[0]
    hu = [{"bat": round(g, 2), "het": round(g + 0.40, 2),
           "khoa": "zoom_nhoi", "dam": 0.25}]
    segs = [(ss, ss + 13.0)]
    d = os.path.join(td, ten)
    os.makedirs(d, exist_ok=True)
    b, ch = os.path.join(d, "off.mp4"), os.path.join(d, "che.mp4")
    xuat(src, b, segs, [dict(x) for x in hu], False)
    xuat(src, ch, segs, [dict(x) for x in hu], True,
         fx_sfx_dir=thu_muc_im(td))
    pb, pm = pcm(b), pcm(ch)
    n = min(len(pb), len(pm))
    goc = FU._sfx_library()
    ra = {}
    try:
        for nhan, key in (("SÁNG", "impact/k_impactsounds_impactGlass_light_"
                                   "001.opus"),
                          ("TRẦM", "impact/boom_deep_05.opus")):
            f = str(FU._assets_sfx_dir() / key)
            if not os.path.exists(f):
                bao(f"kho có file {key}", False, "không thấy file")
                return
            FU._SFX_LIB_CACHE = dict(goc, impact=[f])
            a = os.path.join(d, f"on_{nhan}.mp4")
            xuat(src, a, segs, [dict(x) for x in hu], True)
            dche, _dd = do_nghe_ra(pcm(a)[:n], pm[:n], g)
            dloa, _d2 = do_nghe_ra(pcm(a)[:n], pb[:n], g)
            ra[nhan] = dche
            print(f"      {nhan:<5} {os.path.basename(f):<38} sáng "
                  f"{FU.do_sang_sfx(f):+6.1f} · hụt-loa "
                  f"{FU.hut_qua_loa(f):+6.1f} -> D_CHE {dche:+5.1f} dB · "
                  f"D_LOA {dloa:+5.1f} dB")
    finally:
        FU._SFX_LIB_CACHE = goc
    bao("file SÁNG (không hụt qua loa điện thoại) -> NGHE RA ĐƯỢC",
        ra.get("SÁNG", -99) >= NGHE_RO,
        f"D_CHE {ra.get('SÁNG', -99):+.1f} dB (cần >= {NGHE_RO:.0f})")
    bao("file TRẦM (hụt 44,7 dB qua loa) -> cổng KÊU 'KHÔNG NGHE RA' "
        "(chứng minh cổng biết chấm hỏng)",
        ra.get("TRẦM", 99) < NGHE_MIN,
        f"D_CHE {ra.get('TRẦM', 99):+.1f} dB (phải < {NGHE_MIN:.0f})")
    bao("cùng mốc, cùng hệ số — chỉ khác file: chênh nhau rõ rệt",
        ra.get("SÁNG", -99) - ra.get("TRẦM", 99) >= 5.0,
        f"SÁNG {ra.get('SÁNG', 0):+.1f} vs TRẦM {ra.get('TRẦM', 0):+.1f} = "
        f"cách {ra.get('SÁNG', 0) - ra.get('TRẦM', 0):+.1f} dB")


def ca_diem_nhan_co_tieng(src: str, td: str) -> None:
    print("\n[CA 4] MỖI ĐIỂM NHẤN HÌNH CÓ TIẾNG ĐI KÈM (clip 1 ĐOẠN — không có "
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
    print("\n[CA 5] DUCKING: có thật, êm, và KHÔNG trùm lên chính cú va")
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
    # ---- MỖI MỐC MỘT KIỂU DUCKING — PHẢI ĐO ĐÚNG CỬA SỔ CỦA KIỂU ĐÓ ----
    # BẪY ĐÃ SẬP (bản trước của ca này, 09/08/2026): dùng cửa sổ của ca KHOẢNG
    # LẶNG (bắt đầu SAU mốc 0,22 s) để đo mốc ĐANG NÓI (bướu TRÙM mốc, tắt ở
    # mốc+0,225 s) -> đo trúng chỗ bướu đã tắt, ra **−0,1 dB** rồi kết luận
    # "KHÔNG có ducking" trong khi ducking đang hạ **5,9 dB**. Cửa sổ phải lấy
    # từ chính cờ `noi` APP ghi ra nhật ký, cổng KHÔNG được đoán.
    _noi = {round(float(x["giay"]), 2): bool(x.get("noi"))
            for x in (log or [])}
    bao("nhật ký ghi RÕ mốc nào rơi vào lúc ĐANG NÓI (cổng không phải đoán)",
        len(_noi) == len(moc) and all("noi" in x for x in (log or [])),
        " · ".join(f"{g:.2f}s {'NÓI' if _noi.get(round(g, 2)) else 'lặng'}"
                   for g in moc))

    def _cua(g: float) -> tuple:
        """(đầu cửa sổ, độ dài, ĐỘ SÂU ĐÃ CHỐT) của bướu ducking tại mốc `g`."""
        if _noi.get(round(g, 2)):
            return (g - FU._SFX_DUCK_SOM_NOI, FU._SFX_DUCK_DAI_NOI,
                    FU._SFX_DUCK_DB_NOI)
        return (g - FU._SFX_DUCK_SOM, FU._SFX_DUCK_DAI, FU._SFX_DUCK_DB)

    def _min_trong(t0: float, t1: float):
        i0 = max(0, int(t0 / CUA))
        i1 = min(len(rc_), len(rb), int(t1 / CUA) + 1)
        xs = [db(rc_[i]) - db(rb[i]) for i in range(i0, i1) if rb[i] > 30]
        return min(xs) if xs else None

    co, qua, lang_moc, noi_moc, mep = [], [], [], [], []
    for g in moc:
        a0, dai_, sau = _cua(g)
        v = _min_trong(a0, a0 + dai_)
        if v is None:
            continue
        co.append((g, v))
        if v < -(sau + 1.5):        # hạ SÂU HƠN mức đã chốt = ăn mất tiếng gốc
            qua.append(f"{g:.2f}s hạ {v:+.1f} dB > mức chốt {sau:.0f} dB")
        for t in (a0, a0 + dai_):   # hai MÉP bướu phải ~0 (êm vào - êm ra)
            e = _min_trong(t - 0.05, t + 0.05)
            if e is not None:
                mep.append(e)
        cv = _min_trong(g - RONG / 2, g + RONG / 2)   # cửa sổ CHÍNH CÚ VA
        if cv is not None:
            (noi_moc if _noi.get(round(g, 2)) else lang_moc).append((g, cv))
    bao("MỌI mốc đều có ducking THẬT trong ĐÚNG cửa sổ của kiểu mốc đó "
        f"(lặng {FU._SFX_DUCK_DB:.0f} dB sau mốc · nói "
        f"{FU._SFX_DUCK_DB_NOI:.0f} dB trùm mốc)",
        bool(co) and max(v for _g, v in co) <= -1.0,
        " · ".join(f"{g:.2f}s{'N' if _noi.get(round(g, 2)) else 'L'} {v:+.1f}"
                   for g, v in co) or "không đo được")
    bao("ducking KHÔNG hạ SÂU HƠN mức đã chốt (không ăn mất tiếng gốc)",
        not qua, "; ".join(qua) or
        f"sâu nhất {min([v for _g, v in co] or [0]):+.2f} dB")
    # Mốc KHOẢNG LẶNG: bất biến CŨ giữ nguyên — không có gì che thì đừng đụng
    # vào cú va (đây đúng là gốc lỗi "mốc nhỏ đi" của v2.18.0).
    bao("mốc KHOẢNG LẶNG: ducking KHÔNG trùm lên cửa sổ cú va "
        "(giữ bất biến v2.19.0)",
        all(v > -1.5 for _g, v in lang_moc),
        " · ".join(f"{g:.2f}s {v:+.2f}" for g, v in lang_moc) or "không có mốc")
    # Mốc ĐANG NÓI: NGƯỢC LẠI — bướu PHẢI trùm mốc. Không trùm thì lúc cú va
    # đánh xuống giọng nói vẫn còn nguyên, tiếng động lại bị che (đúng lời anh
    # Hùng *"nói át rồi hay sao"*). Đòi hạ ÍT NHẤT 70% mức đã chốt.
    _can = -0.7 * FU._SFX_DUCK_DB_NOI
    bao("mốc ĐANG NÓI: ducking đã hạ TRỌN giọng nói TRƯỚC khi cú va đánh "
        f"xuống ({-_can:.1f} dB ngay tại mốc)",
        bool(noi_moc) and all(v <= _can for _g, v in noi_moc),
        " · ".join(f"{g:.2f}s {v:+.2f}" for g, v in noi_moc)
        or "clip này không có mốc ĐANG NÓI nào")
    bao("bướu ducking VÀO/RA ÊM: hai mép cửa sổ gần như không hạ "
        "(không bậc thang -> không nghe thành tiếng 'bụp')",
        not mep or min(mep) > -1.2,
        f"mép hạ nhiều nhất {min(mep or [0]):+.2f} dB ({len(mep)} mép)")
    ngoai = [db(rc_[i]) - db(rb[i]) for i in range(min(len(rc_), len(rb)))
             if rb[i] > 30 and all(abs(i * CUA - g) > 1.2 for g in moc)]
    bao("ducking KHÔNG rò ra ngoài cửa sổ (tiếng gốc giữ nguyên)",
        not ngoai or min(ngoai) > -1.0,
        f"hạ nhiều nhất ngoài cửa sổ {min(ngoai or [0]):+.2f} dB")


def ca_tat_la_tat(src: str, td: str) -> None:
    print("\n[CA 6] TẮT LÀ TẮT: fx_whoosh=False -> KHÔNG một mẫu âm nào thêm")
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
    print("\n[CA 7] MỌI ĐIỂM NỐI 'none' -> KHÔNG chèn (tôn trọng ý đồ AI)")
    c = os.path.join(td, "t_none.mp4")
    ln = xuat(src, c, segs, "tat", True, cats=["none"])
    bao("join_categories=['none'] + hiệu ứng tắt -> 0 tiếng", not ln,
        f"{len(ln)} tiếng")


def ca_hook(src: str, td: str) -> None:
    print("\n[CA 8] HOOK MỞ ĐẦU: 2 giây đầu phải CÓ điểm nhấn + CÓ tiếng")
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
        ca_giong_to_nho(td)
        ca_tu_kiem_bo_do(td)
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
