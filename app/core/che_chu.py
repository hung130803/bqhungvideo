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
(bẫy "mã 0 nhưng file 0 KiB / 0 khung"). CHƯA nối vào đường xuất chính.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
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

    @property
    def cao_dai(self) -> int:
        return max(0, self.y1 - self.y0)

    def dict(self) -> dict:
        d = asdict(self)
        d["cao_dai"] = self.cao_dai
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


# ───────────────────────────── PHẦN 2 — CHE ─────────────────────────────────
CACH_CHE = ("mo", "khoi", "hat")


def loc_che(dai: DaiChu, cach: str = "mo", do_manh: float = 1.0,
            mau: str = "black", khoang: Optional[Sequence] = None) -> str:
    """Chuỗi filter ffmpeg CHE dải chữ. Rỗng = không che gì.

    cach:
      "mo"   — LÀM MỜ dải (boxblur). Giữ được màu/độ sáng nền -> ít lộ, nhìn
               như nguồn nén xấu chứ không như "bị dán đè".
      "khoi" — PHỦ KHỐI ĐẶC (drawbox fill). Chắc chắn che hết, nhưng LỘ.
      "hat"  — thu nhỏ rồi phóng lại (pixelate). Để đối chứng, không khuyên
               dùng: ô vuông to nhìn còn lộ hơn khối đặc mà vẫn đọc ra chữ.
    khoang = [(bd, kt), ...] chỉ che trong các khoảng đó; None = che cả clip.
    """
    if not dai or not dai.co_chu or dai.cao_dai <= 0:
        return ""
    x, y = int(dai.x0), int(dai.y0)
    w, h = int(dai.x1 - dai.x0), int(dai.cao_dai)
    if w <= 1 or h <= 1:
        return ""
    en = _bieu_thuc_enable(khoang)
    if cach == "khoi":
        f = (f"drawbox=x={x}:y={y}:w={w}:h={h}:color={mau}@1:t=fill")
        return f + en
    # 'mo' và 'hat' phải CẮT RA — LÀM — DÁN LẠI (boxblur/scale không có `enable`
    # theo vùng). Cùng khuôn "cắt mảnh" mà nhóm shader/lớp phủ đang dùng.
    if cach == "hat":
        o = max(2, int(min(w, h) / max(1.0, 6.0 * do_manh)))
        lam = (f"scale={max(2, w // o)}:{max(2, h // o)}:flags=area,"
               f"scale={w}:{h}:flags=neighbor")
    else:
        r = max(2, int(h / 3.2 * do_manh))
        r = min(r, max(2, w // 2 - 1), max(2, h // 2 - 1))
        lam = (f"boxblur=luma_radius={r}:luma_power=3"
               f":chroma_radius={max(1, r // 2)}:chroma_power=2")
    return (f"split[cc_a][cc_b];"
            f"[cc_b]crop={w}:{h}:{x}:{y},{lam}[cc_c];"
            f"[cc_a][cc_c]overlay={x}:{y}{en}")


def _bieu_thuc_enable(khoang: Optional[Sequence]) -> str:
    if not khoang:
        return ""
    ve = "+".join(f"between(t,{float(a):.3f},{float(b):.3f})"
                  for a, b in khoang if float(b) > float(a))
    return f":enable='{ve}'" if ve else ""


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
    bao = {"dai": dai.dict() if dai else None, "cach": cach,
           "che": False, "so_dong": 0, "ass": ""}
    tam = Path(thu_muc_tam or Path(dst).parent)
    tam.mkdir(parents=True, exist_ok=True)
    ass = tam / (Path(dst).stem + ".che_chu.ass")

    chuoi = []
    f_che = loc_che(dai, cach=cach, do_manh=do_manh, khoang=khoang)
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
