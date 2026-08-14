# -*- coding: utf-8 -*-
"""CHỮ CHÁY SẴN TRONG HÌNH — dò dải chữ, CHE đi, VIẾT chữ mới đè lên.

BÀI TOÁN (anh Hùng 14/08/2026): video nguồn có phụ đề nằm TRONG HÌNH (Douyin
đốt chữ vào khung, gỡ ra không được). Thay tiếng sang ngôn ngữ khác thì dòng
chữ Trung cũ vẫn nằm đó — phải che nó rồi viết bản dịch vào đúng chỗ, đúng mốc.
Ví dụ thật: «男人只是在潜水时» ở dải đáy.

BA VIỆC TÁCH RỜI, gọi độc lập được:
  1. `do_dai_chu(video)`  -> `DaiChu` (toạ độ dải + CÓ/KHÔNG có chữ + độ tin)
  2. `loc_che(dai, ...)`  -> chuỗi filter ffmpeg che dải (mờ / khối đặc)
  3. `ghi_ass(dong, ...)` -> file .ass viết chữ MỚI vào đúng dải, đúng mốc
  `che_va_viet()` gộp cả 3 thành 1 lượt ffmpeg.

VÌ SAO KHÔNG "XOÁ CHỮ" (inpaint, đoán lại hình phía sau) — ĐÃ CÂN NHẮC, LOẠI:
  · Nội dung phía sau chữ KHÔNG có ở đâu để lấy: dải đáy bị chữ che liên tục
    hàng chục giây, không có khung nào "sạch" cùng cảnh để vá vào.
  · Inpaint theo từng khung (Navier-Stokes/Telea của OpenCV) trên video ĐỘNG ra
    vệt nhoè NHẤP NHÁY giữa các khung — hỏng hơn cả để nguyên; muốn ổn định
    phải chạy mô hình video (E2FGVI/ProPainter) = GPU + hàng phút/clip, trong
    khi anh Hùng chạy 200-300 kênh.
  · Và không cần: chữ MỚI sẽ đè lên đúng chỗ đó, người xem không nhìn thấy nền.
  Vì vậy ở đây chỉ có 2 cách CHE (mờ / khối đặc) — cả hai đều rẻ và tiền định.

RANH GIỚI: file này KHÔNG sửa gì của module khác. Nó chỉ ĐỌC lại 2 thứ đã đo
kỹ ở nơi khác: `captions.font_cjk` (chọn font CÓ GLYPH cho chữ Hán — khai bừa
là ffmpeg vẫn trả mã 0 mà chữ ra Ô VUÔNG tofu) và `thay_giong.kiem_video_ra`
(bẫy "mã 0 nhưng file 0 KiB / 0 khung").

ĐÃ NỐI VÀO ĐƯỜNG XUẤT (14/08/2026) — xem `loc_cho_xuat` + `dai_theo_video` ở
CUỐI file. Chuỗi filter được GỘP vào lượt mã hoá SẴN CÓ của
`ffmpeg_utils.export_canvas_clip`, KHÔNG thêm lượt ffmpeg thứ hai: chạy riêng
một lượt tốn **35-76 giây cho video 10 phút** (nhân 200-300 kênh là khoản
thật).

CHI PHÍ THẬT CỦA CHUỖI CHE — ĐO LẠI, ĐỪNG CHÉP SỐ CŨ (`_do_che_chu_gia.py`,
3 vòng ĐAN XEN, cùng máy): **"làm mờ" +1,30 giây/phút phim** · **"phủ khối"
−0,01 giây/phút** (tức không tốn gì). Con số **+0,1-0,2** từng ghi ở đây CHỈ
đúng với "phủ khối". Phần đắt là chính `boxblur` TRANH CPU với libx264, KHÔNG
phải kiến trúc filter: đo riêng phần lọc (`-f null`, không mã hoá) ra +0,34
s/phút, trong đó split/overlay chỉ **+0,05**. Vì vậy đừng "tối ưu" bằng cách
đổi cách nối filter — muốn rẻ thì đổi sang "phủ khối".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np

_CREATE_NO_WINDOW = 0x0800_0000 if os.name == "nt" else 0


# ───────────────────────── NGƯỠNG (đã ĐO, xem `_do_che_chu.py`) ─────────────
#: Top-hat > mức này = "nét chữ sáng". Chữ phụ đề luôn là nét SÁNG mảnh có viền
#: tối — top-hat 9x9 giữ đúng loại đó và vứt mảng sáng lớn (tường trắng, trời).
NGUONG_NET = 55
#: Mật độ nét trên MỘT HÀNG để coi hàng đó "đang có chữ".
NGUONG_HANG = 0.045
#: Dải MỌC RA TỪ HÀNG ĐẬM NHẤT, dừng khi mật độ tụt dưới `TY_LE_DINH` lần đỉnh.
#: NGƯỠNG CỨNG KHÔNG DÙNG ĐƯỢC — đo trên video Douyin `dy3` (bãi đá/cát ngay
#: dưới dòng chữ): hàng chữ 0,19-0,27 còn hàng CÁT 0,05-0,09, cả hai đều vượt
#: 0,045 nên dải mọc từ 88% xuống tận 99% = cao 29,4% khung -> bị luật CAO_MAX
#: đá ra -> BỎ SÓT cả video CÓ chữ. Lấy 0,40 lần đỉnh thì 0,40x0,26 = 0,104 >
#: 0,09 -> cắt sạch cát mà vẫn ôm trọn nét chữ.
TY_LE_DINH = 0.40
#: Khe hở (tỉ lệ chiều cao khung) được phép BẮC CẦU khi mọc dải — phụ đề 2
#: dòng có khoảng trắng giữa 2 dòng, không bắc cầu là chỉ che được 1 dòng.
KHE_TOI_DA = 0.018
#: Tỉ lệ khung có chữ trong dải -> mới dám kết luận "video CÓ chữ cháy".
#: Đây là con số chặn CA SAI NGUY HIỂM NHẤT (che nhầm video không chữ).
TY_LE_KHUNG_MIN = 0.50
#: MẬT ĐỘ TUYỆT ĐỐI trong dải. Đây là cửa chặn CHÍNH, đo được là tách sạch:
#: 5 video Trung có phụ đề cháy 0,186..0,309 · dải "ma" đậm nhất dò ra trên 10
#: video Mỹ không phụ đề 0,055. Lấy 0,10 = giữa hai đám, cách mỗi bên ~2 lần.
MAT_DO_MIN = 0.10
#: Mật độ trong dải / mật độ NỀN. CHỈ LÀ CỬA PHỤ — đặt cao là GIẾT OAN.
#: Đo trên `dy3` (Douyin, cảnh bãi đá + rừng): dải chữ mật độ 0,20-0,29, rõ
#: mồn một bằng mắt, nhưng NỀN cũng đầy vân nên tỉ số chỉ 1,97-2,49 -> ngưỡng
#: 2,5 làm BỎ SÓT 3/6 cửa sổ của một video CÓ chữ. Hạ về 1,5.
TY_SO_NEN_MIN = 1.5
#: Chỉ dò từ mốc này trở xuống (dải đáy cố định — ca phủ phần đông video reup).
VUNG_DAY = 0.55
#: Chiều cao dải hợp lệ (tỉ lệ chiều cao khung). Ngoài khoảng = KHÔNG phải chữ.
#: PHỤ ĐỀ LÀ DẢI MỎNG — đo trên 5 video Trung: 36..52 px / 720 = **5,0..7,2%**
#: (kể cả loại 2 dòng cũng chỉ ~13%). Ca CHE OAN duy nhất bắt được (`en7`: áo
#: in chữ "OLD NAVY" + giá treo quần áo phía sau) mọc ra dải **148 px = 20,6%**
#: — chặn ở 16% là giết đúng nó mà vẫn còn 2,2 lần dư cho phụ đề thật.
CAO_MIN, CAO_MAX = 0.015, 0.16
#: Pixel bật ở >= tỉ lệ này số khung = HẰNG (logo/watermark/khung viền) -> TRỪ
#: RA. Đây là cửa phân biệt PHỤ ĐỀ (chữ đổi liên tục) với WATERMARK (đứng im).
TY_LE_HANG = 0.85
#: Bề rộng dò khung khi phân tích (px). Nhỏ = nhanh, nhưng nét chữ mảnh quá thì
#: top-hat bắt hụt. 640 đo được là đủ cho nguồn 720p-1080p.
RONG_DO = 640
#: Số khung lấy mẫu mặc định.
SO_KHUNG = 16

# ═══════════ HỘP CHỮ — che ĐÚNG CHỖ CÓ CHỮ, không che cả dải ngang ══════════
# Anh Hùng 14/08/2026: *"sao phần text hiện trong video nó không xác định rồi
# che mờ ĐÚNG VỊ TRÍ chữ xuất hiện thôi không được à"*.
#
# VÌ SAO DÒ BỀ NGANG KHÓ HƠN DÒ DẢI (đo, không đoán): bộ dò DẢI làm việc trên
# profile TRUNG BÌNH nhiều khung nên vân nền tự triệt tiêu. Bề NGANG thì phải
# dò trên TỪNG khung — và ở đó **nền cho mực ngang ngửa chữ**. Đã NHÌN TẬN MẮT
# (`_do_hieu_chuan_hop.py`, `zh_dongho` t=7,75s): chữ ở x≈495..790 còn lan can
# + thang kim loại ở x≈900..1280 cũng là NÉT SÁNG MẢNH — đúng thứ top-hat sinh
# ra để bắt. Nâng ngưỡng nét KHÔNG cứu được (ngưỡng 150 vẫn nhô sai 256 px).
#
# CÁCH CHỮA ĐO ĐƯỢC — **GIAO NHAU THEO THỜI GIAN**: một dòng phụ đề đứng YÊN
# TỪNG ĐIỂM ẢNH suốt 1,5-3 giây, còn nền thì trôi. Giữ điểm ảnh nào CÒN BẬT ở
# khung liền trước HOẶC liền sau thì nền chết, chữ sống. Đo trên 3 khung hỏng
# nặng nhất của `zh_dongho`: mực nhiễu bên phải **186 -> 0**, mực chữ giữ
# nguyên chỗ. Vì vậy bước này BẮT BUỘC phải lấy mẫu DÀY (khung cách nhau ~0,5s)
# — dò thưa thì không có "khung liền trước" để giao.
#
#: Số khung/giây khi quét dày. 2 = cách nhau 0,5s.
#: GIÁ ĐÃ ĐO (`_do_gia_lay_mau.py`): MỘT lượt giải mã `fps=` tốn **0,62-0,84
#: s/phút phim** và cho 1-2 khung/giây, trong khi 48 lượt `-ss` tốn **0,78-1,84
#: s/phút** mà chỉ được 48 khung. Tức quét dày RẺ HƠN mà dày gấp 7 lần — đừng
#: "tối ưu" bằng cách quay lại kiểu nhiều lượt `-ss`.
HOP_FPS = 2.0
#: Mỗi đoạn thời gian dài bao nhiêu giây thì đổi hộp một lần.
HOP_DOAN = 8.0
#: Đệm quanh hộp (px ở hệ RONG_DO). Đo `_do_hieu_chuan_hop.py`: đệm 10px đưa
#: số khung "nhô ra ngoài hộp" của `zh_ep12` từ 2 về **0**.
HOP_DEM = 10
#: Trần SỐ HỘP khác nhau trong MỘT LƯỢT XUẤT. Mỗi hộp = 1 nhánh
#: split/crop/boxblur/overlay; nhiều nhánh làm đồ thị filter phình.
HOP_TOI_DA = 6
#: Trần số mốc NHỚ THEO VIDEO. Phải LỚN HƠN HẲN `HOP_TOI_DA`: một clip 60 giây
#: cắt ra từ video 6 phút chỉ dùng ~1/6 số mốc, gộp sớm về 6 ở mức VIDEO là
#: vứt hết độ mịn trước khi biết clip lấy đoạn nào (đo trên `zh_ep12`: gộp
#: sớm ra 6 mốc dài ~58 giây/mốc — bằng cả một Part).
HOP_NHO_TOI_DA = 64
#: Ngưỡng cột = tỉ lệ này nhân ĐỈNH cột. Mọc ra từ cột đậm nhất.
HOP_TY_COT = 0.20
#: Mật độ nét tối thiểu trong dải để coi khung đó "đang có chữ".
HOP_MD_MIN = 0.012
#: Tỉ lệ khung phải dò ra chữ thì mới dám thu hộp. Dưới mức này = bộ dò không
#: nắm được nội dung -> GIỮ NGUYÊN DẢI (thà che thừa còn hơn sót chữ).
HOP_TY_KHUNG_MIN = 0.50
#: Hộp không được hẹp hơn tỉ lệ này của bề rộng khung — chốt chống "hộp ma"
#: (một khung bắt trúng đốm nhiễu rồi đẻ ra hộp 20px).
HOP_HEP_MIN = 0.06
#: Tắt hẳn bước thu-về-hộp (đo A/B, gỡ rối máy user): `BQ_CHE_HOP=0`.
_BAT_HOP = os.environ.get("BQ_CHE_HOP", "1").strip() not in ("0", "false", "no")

# ─────────────── SÀN MỨC MỜ — ĐÃ ĐO, TUYỆT ĐỐI ĐỪNG HẠ ──────────────────────
#: Mức mờ THẤP NHẤT được phép cho cách che "mo".
#:
#: **VÌ SAO CÓ SÀN NÀY** (đo trên clip Douyin THẬT, xem cổng 56 CA 6 + CA 14):
#: mức **0,40** đưa mật độ nét trong dải về **0,0030** — nghĩa là MỌI THƯỚC ĐO
#: BẰNG MÁY đều bảo "dải đã sạch, không còn chữ". Nhưng trích khung ra PNG rồi
#: NHÌN BẰNG MẮT thì **vẫn đọc được bóng chữ** `这时医生灵机一动`. Chỉ từ
#: **0,60** trở lên mắt mới thật sự không đọc nổi.
#: Đây là đúng loại bẫy cả repo này đang chống: *phép đo "sạch" phát chứng nhận
#: cho một thứ vẫn hỏng*. Vì vậy sàn nằm TRONG MÃ (`chuan_muc_mo`), không chỉ
#: nằm ở thanh kéo — user gõ 0,3 vào mẫu cũ / sửa JSON tay cũng bị kẹp về 0,60.
MUC_MO_SAN = 0.60
#: Trần: trên mức này `boxblur` đã bị kẹp bởi bề rộng/cao dải nên tăng thêm
#: không đổi gì mà chỉ làm người dùng tưởng còn nút để xoay.
MUC_MO_TRAN = 2.0
#: Mặc định — mức cổng 56 dùng và đã đo là kín (mật độ 0,0000-0,0006).
MUC_MO_MAC_DINH = 1.0


def chuan_muc_mo(x) -> float:
    """Kẹp mức mờ vào [MUC_MO_SAN, MUC_MO_TRAN]. Rác/None -> mặc định.

    CỬA DUY NHẤT ép sàn 0,60 (xem ghi chú `MUC_MO_SAN`). Mọi đường vào (UI,
    mẫu cũ đọc từ đĩa, payload job, test) phải đi qua đây — đặt sàn ở thanh
    kéo thôi thì mẫu lưu sẵn 0,30 vẫn lọt.
    """
    try:
        v = float(x)
    except (TypeError, ValueError):
        return MUC_MO_MAC_DINH
    if not (v == v) or v in (float("inf"), float("-inf")):   # NaN / vô cực
        return MUC_MO_MAC_DINH
    return max(MUC_MO_SAN, min(MUC_MO_TRAN, v))


def chuan_cach(x) -> str:
    """Chuẩn hoá cách che về đúng {"mo","khoi"}. Lạ/rỗng -> "mo".

    "hat" (pixelate) CỐ Ý không có ở đây: nó chỉ để đối chứng trong cổng 56,
    đo ra ô vuông to còn lộ hơn khối đặc mà VẪN đọc ra chữ — đưa vào UI là mời
    người dùng chọn cái tệ nhất.
    """
    c = str(x or "").strip().lower()
    return c if c in ("mo", "khoi") else "mo"


# ───────────────────────────── kết quả dò ───────────────────────────────────
@dataclass
class DaiChu:
    """Dải chữ cháy sẵn. Toạ độ tính theo PIXEL CỦA KHUNG GỐC."""
    co_chu: bool = False
    y0: int = 0
    y1: int = 0
    x0: int = 0
    x1: int = 0
    rong: int = 0                 # bề rộng khung gốc
    cao: int = 0                  # chiều cao khung gốc
    ty_le_khung: float = 0.0      # tỉ lệ khung có chữ trong dải
    mat_do: float = 0.0           # mật độ nét trong dải
    mat_do_nen: float = 0.0       # mật độ nét phần còn lại của khung
    ty_so_nen: float = 0.0        # mat_do / mat_do_nen
    so_khung: int = 0
    ly_do: str = ""
    moc: list = field(default_factory=list)   # các giây đã lấy mẫu
    #: HỘP THEO ĐOẠN THỜI GIAN — [(t0, t1, x0, x1), …] ở **THỜI GIAN NGUỒN** và
    #: **PIXEL NGUỒN**. Rỗng = chưa dò hộp (dùng x0..x1 cho cả clip).
    hop: list = field(default_factory=list)
    #: bề rộng dải TRƯỚC khi thu về hộp (để báo cáo "giảm bao nhiêu %")
    x0_dai: int = 0
    x1_dai: int = 0

    @property
    def cao_dai(self) -> int:
        return max(0, self.y1 - self.y0)

    @property
    def ty_le_thu(self) -> float:
        """Tỉ lệ DIỆN TÍCH che còn lại so với dải ngang gốc (1,0 = chưa thu).

        Tính theo THỜI LƯỢNG: hộp hẹp mà chỉ dùng 1 giây thì không được tính
        như hộp hẹp dùng cả clip.
        """
        rong_dai = max(1, self.x1_dai - self.x0_dai)
        if not self.hop:
            return (self.x1 - self.x0) / float(rong_dai)
        tong = sum((b - a) for a, b, _, _ in self.hop)
        if tong <= 0:
            return (self.x1 - self.x0) / float(rong_dai)
        return sum((b - a) * (x1 - x0) for a, b, x0, x1 in self.hop) / \
            float(tong * rong_dai)

    def dict(self) -> dict:
        d = asdict(self)
        d["cao_dai"] = self.cao_dai
        d["ty_le_thu"] = round(self.ty_le_thu, 4)
        return d


# ───────────────────────────── ffmpeg / ffprobe ─────────────────────────────
def _root() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parents[2]


def _bin(ten: str) -> str:
    """Đường dẫn ffmpeg/ffprobe — CÙNG quy tắc `hieu_ung._ffmpeg` (tuyệt đối ->
    `which` -> `bin/`). Không import hieu_ung để module này nhẹ và test được
    độc lập."""
    import shutil
    try:
        from config import settings
        p = getattr(settings, "FFMPEG_PATH" if ten == "ffmpeg"
                    else "FFPROBE_PATH", ten)
    except Exception:                                          # noqa: BLE001
        p = ten
    if p and os.path.isabs(p) and os.path.exists(p):
        return p
    w = shutil.which(p or ten)
    if w:
        return w
    return str(_root() / "bin" / (ten + (".exe" if os.name == "nt" else "")))


def _chay(cmd: list, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout,
                          creationflags=_CREATE_NO_WINDOW,
                          stdin=subprocess.DEVNULL)


def thong_tin(src: str | Path) -> dict:
    """{rong, cao, do_dai, co_tieng, fps}. Lỗi -> dict rỗng-an-toàn."""
    cmd = [_bin("ffprobe"), "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", str(src)]
    try:
        r = _chay(cmd, timeout=120)
        d = json.loads(r.stdout.decode("utf-8", "replace") or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"rong": 0, "cao": 0, "do_dai": 0.0, "co_tieng": False,
                "fps": 0.0}
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"),
             {})
    a = any(s.get("codec_type") == "audio" for s in d.get("streams", []))
    fps = 0.0
    try:
        n, m = str(v.get("r_frame_rate", "0/1")).split("/")
        fps = float(n) / float(m) if float(m) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "rong": int(v.get("width") or 0), "cao": int(v.get("height") or 0),
        "do_dai": float(d.get("format", {}).get("duration") or 0),
        "co_tieng": a, "fps": fps,
    }


# ───────────────────────────── xử lý ảnh (numpy thuần) ──────────────────────
def _truot(a: np.ndarray, k: int, truc: int, lay: str) -> np.ndarray:
    """min/max trượt cửa sổ k trên 1 trục (phần tử cấu trúc CHỮ NHẬT tách được).

    numpy thuần — KHÔNG cần cv2. Module này hay bị gọi ở luồng nền/tiến trình
    con, thêm một dependency nặng là thêm một cửa chết.
    """
    pad = k // 2
    b = np.pad(a, [(pad, pad) if i == truc else (0, 0) for i in range(2)],
               mode="edge")
    w = np.lib.stride_tricks.sliding_window_view(b, k, axis=truc)
    return w.min(axis=-1) if lay == "min" else w.max(axis=-1)


def _top_hat(g: np.ndarray, k: int = 9) -> np.ndarray:
    """Top-hat trắng = ảnh − mở(ảnh). Giữ NÉT SÁNG MẢNH (chữ), vứt mảng sáng to.

    Đây là chỗ quyết định "rẻ nhất chạy được": không OCR, không mô hình, chỉ 4
    lượt trượt cửa sổ trên ảnh 640px -> ~2 ms/khung.
    """
    g = g.astype(np.int16)
    er = _truot(_truot(g, k, 0, "min"), k, 1, "min")
    mo = _truot(_truot(er, k, 0, "max"), k, 1, "max")
    return np.clip(g - mo, 0, 255).astype(np.uint8)


def _mat_na(g: np.ndarray) -> np.ndarray:
    """Mặt nạ nhị phân 'nét chữ sáng' của MỘT khung."""
    return (_top_hat(g) > NGUONG_NET).astype(np.uint8)


def _doc_khung(src: str | Path, moc: Sequence[float],
               rong: int = RONG_DO) -> tuple[list, int, int]:
    """Đọc các khung tại `moc` (giây) -> (list ảnh xám, rộng, cao).

    Mỗi mốc một lượt `-ss` TRƯỚC `-i` (seek đầu vào, không giải mã từ đầu).
    Rẻ hơn hẳn `fps=` vốn phải giải mã cả video.
    """
    tt = thong_tin(src)
    if not tt["rong"] or not tt["cao"]:
        return [], 0, 0
    w = rong if rong % 2 == 0 else rong + 1
    h = int(round(tt["cao"] * w / tt["rong"]))
    h += h % 2
    ra = []
    for t in moc:
        cmd = [_bin("ffmpeg"), "-v", "error", "-ss", f"{max(0.0, t):.3f}",
               "-i", str(src), "-frames:v", "1", "-vf", f"scale={w}:{h}",
               "-f", "rawvideo", "-pix_fmt", "gray", "-"]
        try:
            r = _chay(cmd, timeout=120)
        except subprocess.TimeoutExpired:
            continue
        if r.returncode != 0 or len(r.stdout) != w * h:
            continue
        ra.append(np.frombuffer(r.stdout, np.uint8).reshape(h, w))
    return ra, w, h


def _chan(v: int, xuong: bool = False) -> int:
    """Làm tròn về số CHẴN (xuống hoặc lên) — bắt buộc cho yuv420p."""
    v = int(v)
    if v % 2 == 0:
        return v
    return v - 1 if xuong else v + 1


def dai_mac_dinh(rong: int, cao: int, ny: float = 0.88,
                 cao_ty: float = 0.075) -> DaiChu:
    """Dải ĐÁY MẶC ĐỊNH khi không dò ra gì — CHỈ để ĐẶT CHỮ MỚI, không để che.

    `co_chu=False` nên `loc_che` vẫn trả rỗng: viết chữ lên hình thì không bao
    giờ hỏng hình, còn LÀM MỜ nhầm chỗ thì có.
    """
    h = _chan(max(8, int(cao * cao_ty)))
    y1 = _chan(min(cao, int(cao * ny) + h // 2))
    return DaiChu(co_chu=False, y0=max(0, _chan(y1 - h, xuong=True)), y1=y1,
                  x0=0, x1=_chan(rong), rong=rong, cao=cao,
                  ly_do="dải đáy mặc định (không dò ra chữ cháy)")


def _moc_lay_mau(bat_dau: float, ket_thuc: float, n: int) -> list:
    """n mốc RẢI ĐỀU, tránh 2 mép (mép hay là logo mở đầu / bảng kết thúc)."""
    if ket_thuc <= bat_dau:
        return [max(0.0, bat_dau)]
    lo = bat_dau + (ket_thuc - bat_dau) * 0.04
    hi = bat_dau + (ket_thuc - bat_dau) * 0.96
    if n <= 1:
        return [(lo + hi) / 2]
    b = (hi - lo) / (n - 1)
    return [round(lo + i * b, 3) for i in range(n)]


# ───────────────────────────── PHẦN 1 — DÒ DẢI CHỮ ──────────────────────────
def do_dai_chu(src: str | Path, bat_dau: float = 0.0,
               ket_thuc: float = 0.0, so_khung: int = SO_KHUNG,
               vung_day: float = VUNG_DAY,
               ty_le_khung_min: float = TY_LE_KHUNG_MIN,
               ty_so_nen_min: float = TY_SO_NEN_MIN,
               mat_do_min: float = MAT_DO_MIN) -> DaiChu:
    """Dò DẢI NGANG chứa chữ cháy sẵn ở đáy khung.

    CÁCH LÀM (3 tín hiệu cộng lại, mỗi cái chặn một loại nhầm):
      (1) MẬT ĐỘ NÉT theo hàng — chữ là nét sáng mảnh, top-hat bắt rất gọn.
      (2) TRỪ PHẦN HẰNG — pixel bật ở >= 85% số khung là WATERMARK/logo/khung
          viền, KHÔNG phải phụ đề. Không trừ thì mọi kênh có logo góc dưới đều
          bị coi là "có chữ cháy" rồi bị che oan.
      (3) LẶP LẠI QUA THỜI GIAN — dải phải có chữ ở >= `ty_le_khung_min` số
          khung. Một khung lẻ có bảng hiệu/màn hình máy tính không đủ tư cách.
      (4) MẬT ĐỘ TUYỆT ĐỐI >= `mat_do_min` — cửa chặn CHÍNH. Tỉ số với nền chỉ
          là cửa PHỤ vì cảnh nhiều vân (bãi đá, rừng) làm nền cũng đậm.

    Không đạt bất kỳ điều nào -> `co_chu=False` + `ly_do` nói rõ vì sao.
    KHÔNG BAO GIỜ ném lỗi: nguồn hỏng cũng chỉ trả co_chu=False.
    """
    tt = thong_tin(src)
    W, H = tt["rong"], tt["cao"]
    kq = DaiChu(rong=W, cao=H)
    if not W or not H:
        kq.ly_do = "không đọc được kích thước video"
        return kq
    if ket_thuc <= 0:
        ket_thuc = tt["do_dai"]
    moc = _moc_lay_mau(bat_dau, ket_thuc, max(4, so_khung))
    kq.moc = moc
    gs, w, h = _doc_khung(src, moc)
    kq.so_khung = len(gs)
    if len(gs) < 4:
        kq.ly_do = f"chỉ đọc được {len(gs)} khung (cần >= 4)"
        return kq

    mns = np.stack([_mat_na(g) for g in gs])            # (N, h, w)
    n = mns.shape[0]
    hang = mns.sum(axis=0)                              # số khung bật/pixel
    const = (hang >= TY_LE_HANG * n).astype(np.uint8)   # (2) mặt nạ HẰNG
    doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)

    prof = doi.mean(axis=2)                             # (N, h) mật độ/hàng
    tb = prof.mean(axis=0)                              # (h,) mật độ TB/hàng

    y_min = int(h * vung_day)
    y_dinh = int(y_min + np.argmax(tb[y_min:]))
    dinh = float(tb[y_dinh])
    if dinh < NGUONG_HANG:
        kq.ly_do = (f"hàng đậm nhất vùng đáy chỉ {dinh:.4f} "
                    f"(cần >= {NGUONG_HANG})")
        return kq

    # MỌC RA TỪ ĐỈNH, bắc cầu khe hở nhỏ (phụ đề 2 dòng)
    ng = max(NGUONG_HANG, TY_LE_DINH * dinh)
    khe = max(2, int(h * KHE_TOI_DA))
    tot_y0 = tot_y1 = y_dinh
    i, hut = y_dinh, 0
    while i + 1 < h:
        i += 1
        if tb[i] >= ng:
            tot_y1, hut = i, 0
        else:
            hut += 1
            if hut > khe:
                break
    i, hut = y_dinh, 0
    while i - 1 >= y_min:
        i -= 1
        if tb[i] >= ng:
            tot_y0, hut = i, 0
        else:
            hut += 1
            if hut > khe:
                break
    tot_y1 += 1

    cao_ty = (tot_y1 - tot_y0) / h
    if cao_ty < CAO_MIN or cao_ty > CAO_MAX:
        kq.ly_do = (f"dải cao {cao_ty*100:.1f}% khung — ngoài khoảng "
                    f"{CAO_MIN*100:.1f}..{CAO_MAX*100:.0f}%")
        return kq

    # (3) tỉ lệ khung THẬT SỰ có chữ trong dải
    trong = doi[:, tot_y0:tot_y1, :]
    md_khung = trong.reshape(n, -1).mean(axis=1)
    kq.ty_le_khung = float((md_khung > NGUONG_HANG).mean())
    kq.mat_do = float(md_khung.mean())
    ngoai = np.ones(h, bool)
    ngoai[tot_y0:tot_y1] = False
    kq.mat_do_nen = float(doi[:, ngoai, :].mean())
    kq.ty_so_nen = float(kq.mat_do / max(1e-6, kq.mat_do_nen))

    # bề ngang: HỢP của mọi khung + đệm 2%
    cot = trong.sum(axis=(0, 1))
    cot_co = np.nonzero(cot > max(1, int(0.02 * n * (tot_y1 - tot_y0))))[0]
    if cot_co.size:
        dem = int(w * 0.02)
        cx0 = max(0, int(cot_co[0]) - dem)
        cx1 = min(w, int(cot_co[-1]) + 1 + dem)
    else:
        cx0, cx1 = 0, w

    # TOẠ ĐỘ PHẢI CHẴN — yuv420p lấy mẫu màu 2x1/2x2, `crop`+`overlay` ở toạ độ
    # LẺ buộc ffmpeg nội suy lại mặt phẳng màu -> BẨN 1 hàng/cột NGAY BÊN
    # NGOÀI dải. Đo trong cổng 56 CA 5: dải y0=311 (lẻ) -> PSNR ngoài dải
    # 45,2 dB; snap về chẵn -> `inf` (không lệch một điểm ảnh nào).
    ty = H / h
    kq.y0 = _chan(max(0, int(round(tot_y0 * ty)) - 2), xuong=True)
    kq.y1 = min(H, _chan(min(H, int(round(tot_y1 * ty)) + 2)))
    kq.x0 = _chan(max(0, int(round(cx0 * ty))), xuong=True)
    kq.x1 = min(W, _chan(min(W, int(round(cx1 * ty)))))
    kq.x0_dai, kq.x1_dai = kq.x0, kq.x1   # bề rộng DẢI, để so khi thu về hộp

    if kq.ty_le_khung < ty_le_khung_min:
        kq.ly_do = (f"chỉ {kq.ty_le_khung*100:.0f}% khung có chữ trong dải "
                    f"(cần >= {ty_le_khung_min*100:.0f}%)")
        return kq
    if kq.mat_do < mat_do_min:
        kq.ly_do = (f"mật độ nét trong dải {kq.mat_do:.4f} — quá nhạt để là "
                    f"chữ (cần >= {mat_do_min})")
        return kq
    if kq.ty_so_nen < ty_so_nen_min:
        kq.ly_do = (f"dải chỉ đậm gấp {kq.ty_so_nen:.2f} lần nền "
                    f"(cần >= {ty_so_nen_min})")
        return kq
    kq.co_chu = True
    kq.ly_do = (f"dải y={kq.y0}..{kq.y1} ({kq.cao_dai}px), "
                f"{kq.ty_le_khung*100:.0f}% khung có chữ, "
                f"đậm gấp {kq.ty_so_nen:.1f} lần nền")
    return kq


# ────────────────── PHẦN 1b — THU DẢI VỀ HỘP CHỮ (bề NGANG) ─────────────────
def _doc_dai_day(src: str | Path, dai: DaiChu, fps: float = HOP_FPS,
                 rong: int = RONG_DO) -> tuple:
    """MỘT lượt giải mã: `fps=` + `crop` đúng dải hàng -> (ảnh, w, hàng_đầu).

    `crop` NGAY SAU `scale` (không phải trước) để toạ độ khớp hệ RONG_DO mà cả
    file này đang dùng. Cắt sớm giảm hẳn byte qua ống — dải chỉ ~7% chiều cao.
    """
    tt = thong_tin(src)
    if not tt["rong"] or not tt["cao"]:
        return None, 0, 0
    w = rong if rong % 2 == 0 else rong + 1
    h = int(round(tt["cao"] * w / tt["rong"]))
    h += h % 2
    ty = h / float(tt["cao"])
    a = max(0, int(dai.y0 * ty) - 12)
    b = min(h, max(a + 4, int(dai.y1 * ty) + 12))
    ch = b - a
    cmd = [_bin("ffmpeg"), "-v", "error", "-i", str(src), "-vf",
           f"fps={fps},scale={w}:{h},crop={w}:{ch}:0:{a}", "-f", "rawvideo",
           "-pix_fmt", "gray", "-"]
    try:
        r = _chay(cmd, timeout=1800)
    except subprocess.TimeoutExpired:
        return None, 0, 0
    n = len(r.stdout) // (w * ch)
    if n < 6:
        return None, 0, 0
    return (np.frombuffer(r.stdout[:n * w * ch], np.uint8)
            .reshape(n, ch, w), w, a)


def _loc_thoi_gian(m: np.ndarray) -> np.ndarray:
    """Giữ điểm ảnh CÒN BẬT ở khung liền trước HOẶC liền sau.

    Đây là cửa tách CHỮ khỏi NỀN: phụ đề đứng yên từng điểm ảnh 1,5-3 giây,
    nền thì trôi. Xem khối ghi chú "HỘP CHỮ" ở đầu file cho số đo.
    """
    if len(m) < 2:
        return m
    tr = np.empty_like(m)
    sa = np.empty_like(m)
    tr[1:] = m[:-1]
    tr[0] = m[1]
    sa[:-1] = m[1:]
    sa[-1] = m[-2]
    return (m & (tr | sa)).astype(np.uint8)


def _be_ngang(mm: np.ndarray, r0: int, r1: int, w: int) -> Optional[tuple]:
    """[x0,x1) của chữ trong MỘT khung đã lọc. None = khung này không có chữ."""
    sub = mm[r0:r1]
    if sub.size == 0 or float(sub.mean()) < HOP_MD_MIN:
        return None
    cot = sub.sum(axis=0).astype(np.float32)
    if cot.max() <= 0:
        return None
    cs = np.convolve(cot, np.ones(3, np.float32) / 3.0, mode="same")
    dinh = int(np.argmax(cs))
    ng = max(1.0, HOP_TY_COT * float(cs[dinh]))
    khe = max(2, r1 - r0)          # bắc cầu khe = 1 chiều cao chữ (dấu cách)
    a = b = dinh
    i, hut = dinh, 0
    while i + 1 < w:
        i += 1
        if cs[i] >= ng:
            b, hut = i, 0
        else:
            hut += 1
            if hut > khe:
                break
    i, hut = dinh, 0
    while i - 1 >= 0:
        i -= 1
        if cs[i] >= ng:
            a, hut = i, 0
        else:
            hut += 1
            if hut > khe:
                break
    return a, b + 1


def _gop_hop(hop: list, toi_da: int) -> list:
    """Gộp các đoạn liền kề cho tới khi còn <= `toi_da` hộp.

    Mỗi lượt gộp CẶP LIỀN KỀ nào làm DIỆN TÍCH tăng ít nhất — gộp bừa thì hai
    hộp hẹp ở hai đầu clip kéo nhau ra thành một hộp rộng bằng cả dải.
    """
    hop = [list(x) for x in hop]
    while len(hop) > toi_da:
        tot, gia_tot = 0, None
        for i in range(len(hop) - 1):
            a, b, x0, x1 = hop[i]
            c, d, y0, y1 = hop[i + 1]
            n0, n1 = min(x0, y0), max(x1, y1)
            gia = ((n1 - n0) - (x1 - x0)) * (b - a) + \
                  ((n1 - n0) - (y1 - y0)) * (d - c)
            if gia_tot is None or gia < gia_tot:
                tot, gia_tot = i, gia
        a, b, x0, x1 = hop[tot]
        c, d, y0, y1 = hop[tot + 1]
        hop[tot] = [a, d, min(x0, y0), max(x1, y1)]
        del hop[tot + 1]
    return [tuple(x) for x in hop]


def do_hop_chu(src: str | Path, dai: DaiChu, fps: float = HOP_FPS,
               doan: float = HOP_DOAN, toi_da: int = HOP_NHO_TOI_DA) -> DaiChu:
    """Thu DẢI NGANG về HỘP CHỮ: bề ngang theo mép chữ THẬT, đổi theo thời gian.

    Trả về BẢN SAO của `dai` với `x0/x1` = hộp HỢP cả video (khít) và `hop` =
    [(t0, t1, x0, x1), …] theo thời gian NGUỒN.

    **KHÔNG BAO GIỜ NÉM, KHÔNG BAO GIỜ ĐỘNG VÀO `co_chu`.** Việc "có chữ hay
    không" đã chốt ở `do_dai_chu` và đó là cửa giữ kỉ lục CHE OAN 0/76 — hàm
    này chỉ được phép làm vùng che NHỎ LẠI. Dò hỏng/ít bằng chứng -> trả
    `dai` y nguyên (che nguyên dải như trước, không sót chữ).
    """
    if not dai or not dai.co_chu or dai.cao_dai <= 0:
        return dai
    try:
        arr, w, off = _doc_dai_day(src, dai, fps=fps)
        if arr is None:
            return dai
        n = arr.shape[0]
        W = int(dai.rong)
        tyv = w / float(max(1, W))
        r0 = max(0, int(dai.y0 * tyv) - off)
        r1 = min(arr.shape[1], max(r0 + 2, int(dai.y1 * tyv) - off))
        mns = np.stack([_mat_na(g) for g in arr])
        const = (mns.sum(axis=0) >= TY_LE_HANG * n).astype(np.uint8)
        doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)
        gia = _loc_thoi_gian(doi)
        hs = [_be_ngang(gia[i], r0, r1, w) for i in range(n)]
        co = [x for x in hs if x]
        if len(co) < max(6, int(HOP_TY_KHUNG_MIN * n)):
            return dai                      # ít bằng chứng -> GIỮ NGUYÊN DẢI
        hep_min = HOP_HEP_MIN * w

        def _khit(bs) -> Optional[tuple]:
            bs = [b for b in bs if b]
            if not bs:
                return None
            a = min(b[0] for b in bs) - HOP_DEM
            z = max(b[1] for b in bs) + HOP_DEM
            if z - a < hep_min:             # nới đều 2 phía cho đủ sàn
                bu = (hep_min - (z - a)) / 2.0
                a, z = a - bu, z + bu
            return max(0.0, a), min(float(w), z)

        buoc = max(1, int(round(doan * fps)))
        tho = []
        i = 0
        while i < n:
            j = min(n, i + buoc)
            # lấy DƯ 1 mẫu mỗi phía: dòng phụ đề vắt qua mép đoạn thì mẫu của
            # nó rơi vào đoạn BÊN CẠNH
            k = _khit(hs[max(0, i - 1):min(n, j + 1)])
            tho.append([i / fps, j / fps, k])
            i = j
        # đoạn KHÔNG dò ra chữ -> mượn hộp hàng xóm (đừng bỏ trống: chữ có thể
        # có mà bộ dò trượt; thà che thừa một đoạn còn hơn để lộ)
        for idx, x in enumerate(tho):
            if x[2] is None:
                tr = next((tho[k][2] for k in range(idx - 1, -1, -1)
                           if tho[k][2]), None)
                sa = next((tho[k][2] for k in range(idx + 1, len(tho))
                           if tho[k][2]), None)
                cc = [c for c in (tr, sa) if c]
                x[2] = (min(c[0] for c in cc), max(c[1] for c in cc)) if cc \
                    else None
        tho = [x for x in tho if x[2]]
        if not tho:
            return dai
        hop = _gop_hop([(a, b, k[0], k[1]) for a, b, k in tho], toi_da)

        def _px(v: float, len_ra: int) -> int:
            return max(0, min(len_ra, int(round(v / tyv))))

        # BẢN SAO qua `asdict` — KHÔNG dùng `dai.dict()`: `dict()` cố ý thêm 2
        # khoá TÍNH RA (`cao_dai`, `ty_le_thu`) không phải trường của lớp, đưa
        # ngược vào hàm dựng là TypeError.
        ra = DaiChu(**asdict(dai))
        ra.hop = [(round(a, 3), round(b, 3),
                   _chan(_px(x0, W), xuong=True), _chan(min(W, _px(x1, W))))
                  for a, b, x0, x1 in hop]
        ra.x0 = _chan(min(h[2] for h in ra.hop), xuong=True)
        ra.x1 = min(W, _chan(max(h[3] for h in ra.hop)))
        ra.x0_dai, ra.x1_dai = dai.x0_dai or dai.x0, dai.x1_dai or dai.x1
        ra.ly_do = (f"{dai.ly_do} · HỘP CHỮ {len(ra.hop)} mốc, che còn "
                    f"{ra.ty_le_thu*100:.0f}% bề ngang dải")
        return ra
    except Exception:                                          # noqa: BLE001
        return dai              # dò hộp hỏng -> che nguyên dải, KHÔNG chết


# ───────────────────────────── PHẦN 2 — CHE ─────────────────────────────────
CACH_CHE = ("mo", "khoi", "hat")


def loc_che(dai: DaiChu, cach: str = "mo", do_manh: float = 1.0,
            mau: str = "black", khoang: Optional[Sequence] = None,
            hop_ra: Optional[Sequence] = None) -> str:
    """Chuỗi filter ffmpeg CHE chữ. Rỗng = không che gì.

    cach:
      "mo"   — LÀM MỜ (boxblur). Giữ được màu/độ sáng nền -> ít lộ, nhìn như
               nguồn nén xấu chứ không như "bị dán đè".
      "khoi" — PHỦ KHỐI ĐẶC (drawbox fill). Chắc chắn che hết, nhưng LỘ.
      "hat"  — thu nhỏ rồi phóng lại (pixelate). Để đối chứng, không khuyên
               dùng: ô vuông to nhìn còn lộ hơn khối đặc mà vẫn đọc ra chữ.
    khoang = [(bd, kt), ...] chỉ che trong các khoảng đó; None = che cả clip.
    `hop_ra` = [(t0, t1, x0, x1), …] **THEO THỜI GIAN ĐẦU RA** (caller phải quy
    đổi trước — xem `hop_theo_doan`). Có thì mỗi mốc một hộp riêng; None thì
    dùng MỘT hộp `dai.x0..x1` cho cả clip y như trước.
    """
    if not dai or not dai.co_chu or dai.cao_dai <= 0:
        return ""
    y, h = int(dai.y0), int(dai.cao_dai)
    if h <= 1:
        return ""
    if hop_ra:
        khung = [(float(a), float(b), int(x0), int(x1))
                 for a, b, x0, x1 in hop_ra
                 if float(b) > float(a) and int(x1) - int(x0) > 1]
    else:
        khung = [(0.0, 0.0, int(dai.x0), int(dai.x1))]
    khung = [k for k in khung if k[3] - k[2] > 1]
    if not khung:
        return ""
    if cach == "khoi":
        # `drawbox` CÓ timeline `enable` -> nối thẳng bằng dấu phẩy, không cần
        # split/overlay. Rẻ nhất trong 3 cách (đo −0,01 s/phút).
        ve = []
        for (a, b, x0, x1) in khung:
            en = (_bieu_thuc_enable([(a, b)]) if hop_ra
                  else _bieu_thuc_enable(khoang))
            ve.append(f"drawbox=x={x0}:y={y}:w={x1-x0}:h={h}:"
                      f"color={mau}@1:t=fill{en}")
        return ",".join(ve)
    # 'mo' và 'hat' phải CẮT RA — LÀM — DÁN LẠI (`scale` không có `enable` theo
    # vùng). Cùng khuôn "cắt mảnh" mà nhóm shader/lớp phủ đang dùng.
    ve = []
    for i, (a, b, x0, x1) in enumerate(khung):
        w = x1 - x0
        en = (_bieu_thuc_enable([(a, b)]) if hop_ra
              else _bieu_thuc_enable(khoang))
        lam = _loc_lam(cach, w, h, do_manh)
        # `boxblur` CÓ timeline `enable` -> ngoài cửa sổ nó CHO QUA NGUYÊN VẸN,
        # nên nhiều mốc không nhân chi phí lên: chỉ mốc đang bật mới làm mờ.
        # (`crop` không có timeline nhưng nó gần như không tốn gì.)
        if cach != "hat":
            lam += en
        vao = "" if i == 0 else f"[cc_d{i-1}]"
        ra_nhan = "" if i == len(khung) - 1 else f"[cc_d{i}]"
        ve.append(f"{vao}split[cc_a{i}][cc_b{i}]")
        ve.append(f"[cc_b{i}]crop={w}:{h}:{x0}:{y},{lam}[cc_c{i}]")
        ve.append(f"[cc_a{i}][cc_c{i}]overlay={x0}:{y}{en}{ra_nhan}")
    return ";".join(ve)


def _loc_lam(cach: str, w: int, h: int, do_manh: float) -> str:
    """Phần LÀM MỜ / LÀM HẠT cho một hộp w x h."""
    if cach == "hat":
        o = max(2, int(min(w, h) / max(1.0, 6.0 * do_manh)))
        return (f"scale={max(2, w // o)}:{max(2, h // o)}:flags=area,"
                f"scale={w}:{h}:flags=neighbor")
    # BÁN KÍNH PHẢI HỢP LỆ, KHÔNG CHỈ "LỚN HƠN 2".
    # LỖI THẬT (tìm ra 14/08/2026 khi đo giá từng mảnh, dựng dải giả 2x2):
    # bản cũ có `max(2, ...)` ở CẢ HAI vế kẹp nên với dải nhỏ nó ép bán
    # kính về **2** trong khi `boxblur` đòi `radius <= min(w,h)/2` -> ffmpeg
    # báo *"Invalid luma_param radius value 2, must be >= 0 and <= 1"* rồi
    # **CHẾT CẢ LƯỢT XUẤT** (0 khung, "Nothing was written into output
    # file"). Tức một dải chữ hẹp bất thường là mất trắng clip, không phải
    # "che xấu một chút". Nay kẹp bằng `min(...)` THẬT, sàn 1.
    # HỘP CHỮ làm ca này THƯỜNG GẶP HƠN HẲN: hộp hẹp hơn dải nên `w//2` là
    # trần thật sự bị chạm (dải 1280 px không bao giờ chạm, hộp 90 px thì có).
    # CHROMA: yuv420p lấy mẫu màu 2x2 nên mặt phẳng màu chỉ w/2 x h/2 ->
    # trần của chroma_radius là w//4 / h//4, KHÔNG phải r//2.
    r = max(1, int(h / 3.2 * do_manh))
    r = min(r, max(1, w // 2), max(1, h // 2))
    cr = min(max(0, r // 2), max(0, w // 4), max(0, h // 4))
    return (f"boxblur=luma_radius={r}:luma_power=3"
            f":chroma_radius={cr}:chroma_power=2")


def _bieu_thuc_enable(khoang: Optional[Sequence]) -> str:
    if not khoang:
        return ""
    ve = "+".join(f"between(t,{float(a):.3f},{float(b):.3f})"
                  for a, b in khoang if float(b) > float(a))
    return f":enable='{ve}'" if ve else ""


#: Nới hai mép mỗi cửa sổ `enable` (giây). Ba lý do, tất cả đều làm cửa sổ
#: RỘNG RA (an toàn một chiều): mốc dò cách nhau 0,5s nên biên chỉ đúng tới
#: ±0,25s · chỗ ghép đoạn có `xfade` trộn hình hai đoạn trong 0,25-0,4s ·
#: nguồn VFR làm mốc trôi vài chục ms. Hai cửa sổ chồng nhau thì CẢ HAI hộp
#: cùng che — thừa một chút, không sót.
HOP_LE_GIAY = 0.35


def hop_theo_doan(dai: DaiChu, segs: Optional[Sequence]) -> list:
    """Quy HỘP từ THỜI GIAN NGUỒN sang THỜI GIAN ĐẦU RA của clip.

    `segs` = [(bắt_đầu, kết_thúc), …] **theo đúng thứ tự sẽ ghép** (kể cả
    hook-first = NGƯỢC thời gian). Mốc đầu ra của đoạn i = TỔNG ĐỘ DÀI GỐC của
    các đoạn trước nó — đúng trục mà file `.ass` đang dùng, và `_bu_xfade` của
    `ffmpeg_utils` được viết ra chính là để giữ trục đó (xem cổng 36: lấy thêm
    `d` giây ở cuối đoạn trước rồi đặt `offset = độ_dài_GỐC`, nhờ vậy
    "KHÔNG phải sửa `.ass`").

    Trả [] nếu không quy đổi được -> caller dùng MỘT hộp cho cả clip.
    """
    if not dai or not dai.hop or not segs:
        return []
    try:
        ds = [(float(a), float(b)) for a, b in segs if float(b) > float(a)]
    except (TypeError, ValueError):
        return []
    if not ds:
        return []
    ra = []
    off = 0.0
    for (s, e) in ds:
        for (t0, t1, x0, x1) in dai.hop:
            a, b = max(float(t0), s), min(float(t1), e)
            if b <= a:
                continue
            ra.append((max(0.0, off + (a - s) - HOP_LE_GIAY),
                       off + (b - s) + HOP_LE_GIAY, int(x0), int(x1)))
        off += e - s
    if not ra:
        return []
    ra.sort()
    # gộp mốc LIỀN NHAU cùng hộp (đỡ một nhánh filter mà không đổi kết quả)
    gon = [list(ra[0])]
    for m in ra[1:]:
        p = gon[-1]
        if m[2] == p[2] and m[3] == p[3] and m[0] <= p[1] + 1e-6:
            p[1] = max(p[1], m[1])
        else:
            gon.append(list(m))
    # rồi mới hạ về TRẦN CỦA ĐỒ THỊ FILTER — gộp ở đây (sau khi đã biết clip
    # lấy đoạn nào) chứ không gộp ở mức VIDEO, xem ghi chú `HOP_NHO_TOI_DA`.
    return _gop_hop([tuple(x) for x in gon], HOP_TOI_DA)


# ───────────────────────── PHẦN 3 — VIẾT CHỮ MỚI ────────────────────────────
def _esc_ass(t: str) -> str:
    return (str(t).replace("\\", "\\\\").replace("{", "(").replace("}", ")")
            .replace("\n", "\\N"))


def _tt(t: float) -> str:
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t - h * 3600 - m * 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _font_cho(chu: str, font: str) -> str:
    """Font CÓ GLYPH cho chuỗi này. DÙNG LẠI `captions.font_cjk` — cách dò đã
    được đo (12/12 font đóng gói có 0 glyph CJK; khai thẳng 'Microsoft YaHei'
    thì libass chọn ngay, 0 lượt lùi). Không có captions -> giữ nguyên font."""
    try:
        from app.core.captions import font_cjk
        return font_cjk(chu, font)
    except Exception:                                          # noqa: BLE001
        return font


def ghi_ass(dong: Sequence, out_path: str | Path, dai: DaiChu,
            font: str = "Arial", co_chu: float = 0.0,
            mau: str = "&H00FFFFFF", vien: str = "&H00000000",
            do_vien: float = 0.0, nhieu_dong: int = 2) -> bool:
    """Ghi .ass đặt chữ MỚI vào ĐÚNG dải vừa che. True = có ít nhất 1 dòng.

    `dong` = [(bat_dau, ket_thuc, chữ), ...] — mốc đã ở TIMELINE ĐẦU RA (bên
    ngoài truyền vào; sau này là bản dịch). Không sắp lại, không remap.
    Chữ đặt bằng `\\an5\\pos(tâm dải)` nên nằm CHÍNH GIỮA dải cũ dù dải cao bao
    nhiêu — không phụ thuộc MarginV.
    """
    dong = [(float(a), float(b), str(c))
            for a, b, c in (dong or []) if str(c).strip() and float(b) > float(a)]
    if not dong or not dai or dai.cao_dai <= 0:
        Path(out_path).write_text("", encoding="utf-8")
        return False
    W, H = int(dai.rong), int(dai.cao)
    cao_dai = dai.cao_dai
    # CỠ CHỮ = 0,85 x CHIỀU CAO DẢI. Dải dò ra chính là BỀ CAO VỆT MỰC của chữ
    # cũ, mà cỡ font ~ bề cao vệt mực (CJK gần 1:1, Latin có thêm chân chữ).
    # Bản đầu để 0,62 -> chữ mới NHỎ HƠN HẲN chữ cũ, nhìn ra ngay bằng mắt
    # (dải 36 px thì chữ ra 22 px trong khi chữ Trung gốc cao ~36 px).
    cs = int(co_chu) if co_chu >= 8 else int(
        max(14, min(cao_dai * 0.85, H * 0.085)))
    cs = max(14, int(cs))
    ow = do_vien if do_vien > 0 else max(1.0, round(cs * 0.09, 1))
    ht = "".join(d[2] for d in dong[:400])
    font = _font_cho(ht, font)
    cx = (dai.x0 + dai.x1) / 2.0
    cy = (dai.y0 + dai.y1) / 2.0
    # bề rộng cho phép: đúng bề ngang dải (chữ dài tự xuống dòng trong dải)
    le = max(4, int(W - (dai.x1 - dai.x0)) // 2)
    head = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {W}\nPlayResY: {H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: CheChu,{font},{cs},{mau},{mau},{vien},&H64000000,"
        f"0,0,0,0,100,100,0,0,1,{ow},0,5,{le},{le},10,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )
    lines = [
        f"Dialogue: 0,{_tt(a)},{_tt(b)},CheChu,,0,0,0,,"
        f"{{\\an5\\pos({cx:.0f},{cy:.0f})}}{_esc_ass(c)}"
        for a, b, c in dong
    ]
    Path(out_path).write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    return True


# ───────────────────────── GỘP: CHE + VIẾT trong 1 lượt ─────────────────────
def _esc_loc(p: str) -> str:
    """Escape đường dẫn cho filter `subtitles=` (Windows: `D:\\x` -> `D\\:/x`).

    BẪY ĐÃ SẬP: escape THỪA một lớp (`\\\\:` thay vì `\\:`) thì ffmpeg đọc phần
    sau dấu hai chấm thành TÊN THAM SỐ và báo *Unable to parse "original_size"*
    — lời lỗi chẳng dính gì tới đường dẫn, rất dễ đi sửa nhầm chỗ.
    Đúng: một dấu `\\` trước `:` và trước `'`, dấu `\\` của Windows đổi thành `/`.
    """
    q = str(p).replace("\\", "/")
    return q.replace(":", "\\:").replace("'", "\\'")


def che_va_viet(src: str | Path, dst: str | Path,
                dong: Optional[Sequence] = None,
                dai: Optional[DaiChu] = None,
                cach: str = "mo", do_manh: float = 1.0,
                font: str = "Arial", co_chu: float = 0.0,
                khoang: Optional[Sequence] = None,
                bo_ma: Optional[Sequence] = None,
                thu_muc_tam: str | Path = "",
                chay: Optional[Callable] = None,
                timeout: int = 3600) -> dict:
    """CHE dải chữ cũ + VIẾT chữ mới đè lên -> file `dst`. Trả BÁO CÁO (dict).

    `dai=None` -> tự dò bằng `do_dai_chu`. Dò ra "KHÔNG có chữ" -> **KHÔNG CHE
    GÌ HẾT** (chỉ viết chữ mới nếu có) — che nhầm video sạch là làm hỏng hình,
    ca sai đắt nhất của tính năng này.
    `chay` = hàm chạy ffmpeg do caller truyền (để đi qua CỬA CHỜ ffmpeg khi nối
    vào đường xuất). None -> subprocess thẳng.
    Ném RuntimeError nếu ffmpeg lỗi HOẶC file ra không có khung hình.
    """
    src, dst = str(src), str(dst)
    tt = thong_tin(src)
    if dai is None:
        dai = do_dai_chu(src)
        if dai.co_chu and _BAT_HOP:
            dai = do_hop_chu(src, dai)
    bao = {"dai": dai.dict() if dai else None, "cach": cach,
           "che": False, "so_dong": 0, "ass": ""}
    tam = Path(thu_muc_tam or Path(dst).parent)
    tam.mkdir(parents=True, exist_ok=True)
    ass = tam / (Path(dst).stem + ".che_chu.ass")

    chuoi = []
    # Hàm này xử lý CẢ video (không `-ss`, không ghép đoạn) nên THỜI GIAN ĐẦU
    # RA = THỜI GIAN NGUỒN -> `segs` chính là [(0, độ dài)].
    hop_ra = (hop_theo_doan(dai, [(0.0, tt["do_dai"])])
              if (dai and dai.hop and not khoang and tt["do_dai"] > 0) else [])
    f_che = loc_che(dai, cach=cach, do_manh=do_manh, khoang=khoang,
                    hop_ra=hop_ra or None)
    if f_che:
        chuoi.append(f_che)
        bao["che"] = True
    co_dong = False
    if dong:
        # KHÔNG dò ra dải -> vẫn viết được chữ mới, đặt ở DẢI ĐÁY MẶC ĐỊNH.
        # Không che gì cả (bao["che"] vẫn False) — viết chữ không hỏng hình,
        # làm mờ nhầm chỗ thì có.
        d_viet = dai if (dai and dai.co_chu and dai.cao_dai > 0) else \
            dai_mac_dinh(tt["rong"] or 1080, tt["cao"] or 1920)
        co_dong = ghi_ass(dong, ass, d_viet, font=font, co_chu=co_chu)
        bao["dai_viet"] = d_viet.dict()
    if co_dong:
        chuoi.append(f"subtitles='{_esc_loc(ass)}'")
        bao["so_dong"] = len(dong)
        bao["ass"] = str(ass)
    if not chuoi:
        bao["ly_do"] = "không có gì để che và không có chữ mới -> bỏ qua"
        return bao

    enc = list(bo_ma) if bo_ma else ["-c:v", "libx264", "-preset", "veryfast",
                                     "-crf", "20", "-pix_fmt", "yuv420p"]
    # NỐI BẰNG DẤU PHẨY, KHÔNG PHẢI CHẤM PHẨY: `loc_che` trả về một GRAPH
    # (split/crop/overlay ngăn bằng `;`), chuỗi cuối của nó là `overlay=...`.
    # Nối `;subtitles=` là đẻ ra một chuỗi RỜI không có đầu vào -> ffmpeg báo
    # "Cannot find an unused video input stream". Nối `,` thì `subtitles` chạy
    # TIẾP SAU overlay — đúng thứ tự: che xong mới viết chữ mới đè lên.
    cmd = [_bin("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
           "-i", src, "-filter_complex", ",".join(chuoi),
           *enc, "-c:a", "copy", "-movflags", "+faststart", dst]
    bao["cmd"] = cmd
    r = (chay(cmd) if chay else _chay(cmd, timeout=timeout))
    ma = getattr(r, "returncode", 1)
    bao["ma_thoat"] = ma                    # MÃ THOÁT THẬT, không qua `| tail`
    if ma != 0:
        err = getattr(r, "stderr", b"") or b""
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        raise RuntimeError(f"ffmpeg lỗi khi che chữ (mã thoát {ma}): "
                           f"{err[-600:]}")
    bao["kiem"] = kiem_video_ra(dst, tt["do_dai"], co_tieng=tt["co_tieng"])
    return bao


def kiem_video_ra(dst: str | Path, do_dai_goc: float = 0.0,
                  co_tieng: bool = True, lech_toi_da: float = 1.0) -> dict:
    """Bẫy "mã 0 nhưng file 0 KiB / 0 khung" — dùng lại `thay_giong` đã đo kỹ.

    Nguồn KHÔNG có tiếng -> bỏ mục RMS (che chữ không đụng audio, đòi có tiếng
    là FAIL OAN). Không nạp được thay_giong -> tự kiểm bằng ffprobe.
    """
    if co_tieng:
        try:
            from app.core.thay_giong import kiem_video_ra as _kv
            return _kv(dst, do_dai_goc, lech_toi_da)
        except ImportError:
            pass
    p = Path(dst)
    if not p.exists():
        raise RuntimeError(f"Không có file ra {p.name}")
    co = p.stat().st_size
    if co < 10240:
        raise RuntimeError(f"File ra {p.name} rỗng ({co} byte)")
    khung = so_khung_hinh(p)
    if khung <= 0:
        raise RuntimeError(f"File ra {p.name} KHÔNG CÓ KHUNG HÌNH nào "
                           "(ffmpeg trả mã 0 nhưng video rỗng)")
    dai = thong_tin(p)["do_dai"]
    lech = abs(dai - do_dai_goc) if do_dai_goc > 0 else 0.0
    if do_dai_goc > 0 and lech > lech_toi_da:
        raise RuntimeError(f"File ra {p.name} dài {dai:.3f}s, gốc "
                           f"{do_dai_goc:.3f}s — lệch {lech:.3f}s")
    return {"co": co, "khung": khung, "do_dai": round(dai, 3),
            "lech_do_dai": round(lech, 3)}


def so_khung_hinh(path: str | Path) -> int:
    """SỐ KHUNG HÌNH thật (đếm gói)."""
    cmd = [_bin("ffprobe"), "-v", "error", "-select_streams", "v:0",
           "-count_packets", "-show_entries", "stream=nb_read_packets",
           "-of", "csv=p=0", str(path)]
    try:
        r = _chay(cmd, timeout=600)
        return int((r.stdout.decode("utf-8", "replace") or "0")
                   .strip().rstrip(",") or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


# ───────────────────────── THƯỚC ĐO (cho cổng + script đo) ──────────────────
def mat_do_vung(src: str | Path, y0: int, y1: int, moc: Sequence[float],
                x0: int = 0, x1: int = 0) -> float:
    """Mật độ NÉT CHỮ trung bình trong vùng [y0,y1) x [x0,x1) tại các mốc.

    Đây là thước "còn đọc được chữ không" sau khi che: dải còn chữ ~0,15-0,25;
    dải đã che phải tụt xuống ngang mức nền của video không chữ (~0,005-0,03).
    ĐỌC KỸ: con số này KHÔNG THAY ĐƯỢC MẮT — cổng vẫn phải trích PNG ra nhìn
    (bài học "tofu 2.961 px > chữ 一 thật 2.624 px": đếm pixel kết luận NGƯỢC).
    """
    tt = thong_tin(src)
    if not tt["cao"]:
        return 0.0
    gs, w, h = _doc_khung(src, moc)
    if not gs:
        return 0.0
    ty = h / tt["cao"]
    a, b = int(y0 * ty), max(int(y0 * ty) + 1, int(y1 * ty))
    c = int(x0 * ty) if x1 > x0 else 0
    d = int(x1 * ty) if x1 > x0 else w
    tong = 0.0
    for g in gs:
        tong += float(_mat_na(g)[a:b, c:d].mean())
    return tong / len(gs)


# ═══════════════ NỐI VÀO ĐƯỜNG XUẤT (dùng ở `ffmpeg_utils`) ═════════════════
#: Kết quả dò, nhớ theo (đường dẫn, cỡ file, mtime_ns). MỘT video ra 3 Part =
#: đường xuất đi qua đây 3 lần; dò lại 3 lần là 3 lượt đọc 16 khung vô ích.
_DAI_NHO: dict = {}
#: Khoá RIÊNG cho từng video (không phải một khoá chung): 3 làn xuất song song
#: trên 3 video KHÁC NHAU không được xếp hàng chờ nhau, mà 3 Part của CÙNG một
#: video thì chỉ được dò MỘT lượt.
_DAI_KHOA: dict = {}
_SO_KHOA = threading.Lock()
#: Trần số video nhớ — 300 kênh chạy cả ngày, giữ vô hạn là rò bộ nhớ chậm.
_NHO_TOI_DA = 512


def _khoa_video(src: str | Path) -> Optional[tuple]:
    """(đường dẫn tuyệt đối, cỡ, mtime_ns) — None nếu không đọc được.

    PHẢI có cỡ + mtime: `thay_giong` ghi file MỚI vào ĐÚNG chỗ file cũ, khoá
    chỉ theo tên là đọc lại dải của bản trước (dải cũ nằm sai chỗ trên hình
    mới) mà không một dòng báo.
    """
    try:
        p = Path(src).resolve()
        st = p.stat()
        return (str(p).lower(), st.st_size, st.st_mtime_ns)
    except OSError:
        return None


def dai_theo_video(src: str | Path, so_khung: int = SO_KHUNG) -> DaiChu:
    """`do_dai_chu` NHỚ KẾT QUẢ theo video. Không bao giờ ném lỗi.

    Vì sao phải nhớ: dò = 16 lượt `ffmpeg -ss ... -frames:v 1` + 2 lượt
    `ffprobe`. Đó là phần ĐẮT của tính năng này (chuỗi filter thì gần như miễn
    phí). Một video 3 Part -> nhớ được là bỏ 2/3 chi phí; 200-300 kênh thì đó
    là khoản thật.
    """
    key = _khoa_video(src)
    if key is None:                       # file lạ/mất -> dò thẳng, không nhớ
        return do_dai_chu(src, so_khung=so_khung)
    with _SO_KHOA:
        if key in _DAI_NHO:
            return _DAI_NHO[key]
        khoa = _DAI_KHOA.get(key)
        if khoa is None:
            khoa = _DAI_KHOA[key] = threading.Lock()
    with khoa:
        with _SO_KHOA:                    # người khác vừa dò xong khi ta đợi
            if key in _DAI_NHO:
                return _DAI_NHO[key]
        d = do_dai_chu(src, so_khung=so_khung)
        # THU DẢI VỀ HỘP CHỮ — chỉ chạy khi ĐÃ kết luận CÓ chữ. Video không chữ
        # (phần đông kho của anh Hùng) vì thế KHÔNG tốn thêm một giây nào, và
        # kỉ lục "che oan 0/76" không bị đụng tới: `do_hop_chu` không được phép
        # đổi `co_chu`, nó chỉ làm vùng che NHỎ LẠI.
        if d.co_chu and _BAT_HOP:
            d = do_hop_chu(src, d)
        with _SO_KHOA:
            if len(_DAI_NHO) >= _NHO_TOI_DA:
                _DAI_NHO.clear()
                _DAI_KHOA.clear()
            _DAI_NHO[key] = d
    return d


def loc_cho_xuat(src: str | Path, cach: str = "mo", muc: float = 1.0,
                 dai: Optional[DaiChu] = None,
                 so_khung: int = SO_KHUNG,
                 segs: Optional[Sequence] = None) -> tuple:
    """(chuỗi_filter, DaiChu, lý_do) cho ĐƯỜNG XUẤT. Chuỗi rỗng = KHÔNG che.

    Chuỗi trả về là một MẢNH chuỗi filter THIẾU nhãn hai đầu, đúng khuôn
    `parts` của `export_canvas_clip` đang dùng: caller ghép
    `f"{nhãn_vào}{chuỗi}[nhãn_ra]"`. `loc_che` trả về một GRAPH ngăn bằng `;`
    mà chuỗi ĐẦU bắt đầu bằng `split` và chuỗi CUỐI kết bằng `overlay=x:y`, nên
    bọc hai đầu là ra graph hợp lệ (cách "khoi" chỉ có `drawbox` nối bằng `,`).

    `segs` = các đoạn nguồn sẽ ghép thành clip, ĐÚNG THỨ TỰ (hook-first thì
    NGƯỢC thời gian — cứ truyền y như `export_canvas_clip` nhận). Có `segs` thì
    hộp chữ đổi THEO MỐC; không có thì dùng MỘT hộp HỢP cả video (vẫn hẹp hơn
    dải, chỉ là không bám theo từng dòng).

    KHÔNG dò ra chữ -> trả rỗng: **che oan video sạch là ca sai đắt nhất** của
    tính năng này (đo ở cổng 56: 0/76 video không chữ bị che).
    """
    try:
        d = dai if dai is not None else dai_theo_video(src, so_khung=so_khung)
    except Exception:                                          # noqa: BLE001
        return "", None, "dò dải chữ lỗi -> KHÔNG che"
    if d is None:
        return "", None, "dò dải chữ lỗi -> KHÔNG che"
    if not d.co_chu:
        return "", d, f"KHÔNG che ({d.ly_do})"
    hop_ra = hop_theo_doan(d, segs)
    f = loc_che(d, cach=chuan_cach(cach), do_manh=chuan_muc_mo(muc),
                hop_ra=hop_ra or None)
    if not f:
        return "", d, f"dải không dùng được (cao {d.cao_dai}px) -> KHÔNG che"
    ten = "làm mờ" if chuan_cach(cach) == "mo" else "phủ khối"
    # dấu PHẨY thập phân (tiếng Việt) — chỉ đổi TRONG SỐ, đừng `.replace('.',
    # ',')` cả câu: bản đầu làm thế và biến `y=678..714` thành `y=678,,714`.
    mm = f"{chuan_muc_mo(muc):.2f}".replace(".", ",")
    if hop_ra:
        tb = sum((b - a) * (x1 - x0) for a, b, x0, x1 in hop_ra) / \
            max(1e-6, sum(b - a for a, b, _, _ in hop_ra))
        rong_dai = max(1, (d.x1_dai or d.x1) - (d.x0_dai or d.x0))
        vi = (f"che HỘP CHỮ {len(hop_ra)} mốc, rộng TB {tb:.0f}px "
              f"(dải cũ {rong_dai}px = {tb/rong_dai*100:.0f}%)")
    else:
        vi = f"che dải x={d.x0}..{d.x1}"
    return f, d, (f"{vi} y={d.y0}..{d.y1} ({d.cao_dai}px) — {ten} mức {mm}")


def trich_khung(src: str | Path, t: float, dst: str | Path,
                rong: int = 0) -> bool:
    """Trích 1 khung ra PNG để NGƯỜI/LLM TỰ NHÌN (cổng bắt buộc phải nhìn)."""
    vf = f"scale={int(rong)}:-2" if rong else "null"
    cmd = [_bin("ffmpeg"), "-y", "-v", "error", "-ss", f"{max(0.0, t):.3f}",
           "-i", str(src), "-frames:v", "1", "-vf", vf, str(dst)]
    try:
        return _chay(cmd, timeout=120).returncode == 0
    except subprocess.TimeoutExpired:
        return False
