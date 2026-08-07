# -*- coding: utf-8 -*-
"""HIỆU ỨNG THẤY ĐƯỢC NGAY ở ĐIỂM NHẤN — kho hiệu ứng + luật AI chọn theo cảnh.

VÌ SAO CÓ FILE NÀY (nguyên văn anh Hùng 07/08/2026): *"hiệu ứng cơ mà, bạn cứ làm
cái gì đó tôi có thấy đâu"*. Lượt trước chỉ làm **chuyển cảnh** `xfade` 0,3 s ở
2-3 chỗ nối — quá tinh tế, mở demo ra KHÔNG THẤY GÌ. File này làm loại **thấy
được bằng mắt**: zoom nhồi, rung lắc, glitch khối, quầng sáng phim, tối viền…

=== 4 LUẬT CHỐNG LOÈ (BẮT BUỘC — vì sao xem `VIEC_HIEU_UNG.md`) ===
1. Hiệu ứng chỉ **0,3-0,8 giây** ở ĐIỂM NHẤN, KHÔNG phủ toàn clip  -> `DAI_MIN/MAX`
2. Độ đậm **<= 25%** thang riêng của từng hiệu ứng                  -> `DAM_MAX`
3. **KHÔNG đổi màu da**: lệch U/V < 3 đơn vị, vượt thì TỰ BỎ        -> `UV_MAX`,
   `an_toan_mau` (đo THẬT bằng cổng 37, không tin tên hiệu ứng)
4. Mỗi clip **tối đa 3 điểm** có hiệu ứng                            -> `DIEM_MAX`
Anh Hùng đã TỪ CHỐI demo "tim bay" vì file phủ lệch hồng V=142 làm tím cả khung.

=== VÌ SAO `enable=` LÀM ĐƯỢC ĐIỀU NÀY ===
`ffmpeg -h filter=frei0r` -> *"This filter has support for timeline through the
'enable' option"*. Nhờ vậy MỌI hiệu ứng frei0r bật/tắt được theo giây mà KHÔNG
phải tách nhánh graph. `scale`/`crop`/`zoompan` thì **KHÔNG** có timeline (bẫy đã
sập: "zoom nhồi" báo 0,03 CPU-giây thực ra `scale` không nhận biểu thức theo thời
gian) -> zoom phải dùng `zoompan` với cổng thời gian NẰM TRONG biểu thức `z`, còn
rung lắc dùng `crop` biểu thức x/y (crop pan được theo t nhưng KHÔNG zoom được:
w/h chốt ở config_input).

=== BỐ CỤC frei0r (mã nguồn mở, GPL/LGPL — anh Hùng đã duyệt) ===
Plugin nằm ở `app/assets/hieu_ung/frei0r/*.dll`; ffmpeg tìm qua biến môi trường
`FREI0R_PATH`. 3 DLL runtime (`libstdc++-6`, `libgcc_s_seh-1`, `libwinpthread-1`)
phải nằm **CẠNH ffmpeg.exe** — không phải cạnh plugin: ffmpeg gọi `LoadLibraryExA`
với `LOAD_LIBRARY_SEARCH_APPLICATION_DIR|SYSTEM32|USER_DIRS`, tức KHÔNG tìm theo
`PATH` và KHÔNG tìm cạnh DLL được nạp. Đo thật: để runtime cạnh plugin ->
`Could not find module 'vignette'`; để cạnh ffmpeg.exe -> nạp được 87 plugin
(thay vì 63). Thiếu plugin/thiếu runtime -> `co_frei0r()` trả False và app **TỰ
TẮT nhóm frei0r, KHÔNG nổ lỗi** (máy nhân viên).
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------- 4 luật số
DAI_MIN = 0.30          # luật 1: ngắn nhất (dưới nữa mắt không kịp thấy)
DAI_MAX = 0.80          # luật 1: dài nhất (dài hơn là "phủ clip" = loè)
DAM_MAX = 0.25          # luật 2: độ đậm tối đa (thang riêng từng hiệu ứng)
UV_MAX = 3.0            # luật 3: lệch U/V cho phép (đơn vị 0..255)
DIEM_MAX = 3            # luật 4: số điểm nhấn tối đa mỗi clip
CACH_MIN = 2.5          # 2 điểm nhấn phải cách nhau ít nhất (giây)

MUC: tuple = ("tat", "nhe", "vua", "manh")
MUC_NHAN: dict = {
    "tat": "Tắt (không hiệu ứng)",
    "nhe": "Nhẹ (chỉ 1-2 điểm, rất kín)",
    "vua": "Vừa (khuyên dùng)",
    "manh": "Mạnh (thấy rõ nhất)",
}
# Độ đậm theo mức — TẤT CẢ <= DAM_MAX (luật 2). "manh" = 25%, đúng trần.
MUC_DAM: dict = {"nhe": 0.12, "vua": 0.18, "manh": 0.25}
# Số điểm nhấn theo mức — TẤT CẢ <= DIEM_MAX (luật 4).
MUC_DIEM: dict = {"nhe": 2, "vua": 3, "manh": 3}


# ------------------------------------------------------- nơi ở của frei0r
def _root() -> Path:
    try:
        from config import ROOT_DIR
        return Path(ROOT_DIR)
    except Exception:  # noqa: BLE001 — dùng được cả khi chạy rời config
        return Path(__file__).resolve().parents[2]


def thu_muc_frei0r() -> Path:
    return _root() / "app" / "assets" / "hieu_ung" / "frei0r"


def _ffmpeg() -> str:
    """ffmpeg mà ĐƯỜNG XUẤT thật sự dùng, đã đổi ra ĐƯỜNG DẪN TUYỆT ĐỐI.

    Phải là CÙNG MỘT file với `settings.FFMPEG_PATH` (đường xuất dùng nó), nếu
    không thì thử-nạp-được-ở-đây mà lúc xuất lại lỗi. Dev mode `.env` để trống
    -> `settings.FFMPEG_PATH == "ffmpeg"` -> `shutil.which` ra `C:\\ffmpeg\\
    ffmpeg.exe` (KHÔNG phải `bin/ffmpeg.exe`) — đó mới là file phải đặt DLL
    runtime cạnh. Bản đóng gói thì config.py đã trỏ tuyệt đối vào `_internal/`.
    """
    import shutil
    try:
        from config import settings
        p = settings.FFMPEG_PATH
    except Exception:  # noqa: BLE001
        p = "ffmpeg"
    if p and os.path.isabs(p) and os.path.exists(p):
        return p
    w = shutil.which(p or "ffmpeg")
    if w:
        return w
    return str(_root() / "bin" / "ffmpeg.exe")


def dat_frei0r_path() -> str:
    """Ghi `FREI0R_PATH` vào môi trường tiến trình (ffmpeg con thừa hưởng).

    `ffmpeg_utils._run_khong_cho` gọi `Popen` KHÔNG truyền `env` -> con thừa
    hưởng `os.environ`, nên đặt ở đây là đủ cho mọi đường xuất. GIỮ giá trị user
    đã đặt (nối thêm, ngăn cách `;` — ffmpeg dùng `;` trên Windows, `:` trên
    Unix; `C:\\...` có dấu `:` nên `:` sẽ vỡ đường dẫn Windows).
    """
    d = thu_muc_frei0r()
    if not d.is_dir():
        return os.environ.get("FREI0R_PATH", "")
    sep = ";" if os.name == "nt" else ":"
    cu = os.environ.get("FREI0R_PATH", "")
    if str(d) not in cu.split(sep):
        os.environ["FREI0R_PATH"] = (cu + sep + str(d)) if cu else str(d)
    return os.environ["FREI0R_PATH"]


#: 3 DLL runtime của mingw mà 2 plugin C++ (`nosync0r`, `scanline0r`) cần.
RUNTIME_DLL: tuple = ("libstdc++-6.dll", "libgcc_s_seh-1.dll",
                      "libwinpthread-1.dll")


def bao_dam_runtime() -> str:
    """Chép 3 DLL runtime sang CẠNH ffmpeg.exe nếu còn thiếu. Trả lời nhắn lỗi.

    PHẢI cạnh ffmpeg.exe, KHÔNG phải cạnh plugin: ffmpeg nạp plugin bằng
    `LoadLibraryExA(..., LOAD_LIBRARY_SEARCH_APPLICATION_DIR|SYSTEM32|USER_DIRS)`
    -> Windows KHÔNG tìm phụ thuộc theo `PATH`, cũng KHÔNG tìm cạnh DLL vừa nạp.
    Đo thật 07/08/2026: để cạnh plugin -> 63/159 nạp được; để cạnh ffmpeg.exe ->
    87/159. Bản đóng gói thì CI `--add-binary ...;.` đã để sẵn ở `_internal/`
    nên hàm này không phải làm gì. Chép thất bại (không quyền ghi) -> IM LẶNG:
    `co_frei0r`/`module_co` sẽ tự loại 2 hiệu ứng cần chúng.
    """
    ff = _ffmpeg()
    if not os.path.exists(ff):
        return "khong biet ffmpeg.exe o dau"
    dich = Path(ff).resolve().parent
    nguon = thu_muc_frei0r() / "runtime"
    if not nguon.is_dir():
        return ""
    import shutil
    thieu = []
    for n in RUNTIME_DLL:
        d = dich / n
        if d.exists():
            continue
        s = nguon / n
        if not s.exists():
            continue
        try:
            shutil.copy2(s, d)
        except OSError as e:
            thieu.append(f"{n}: {e}")
    return "; ".join(thieu)


_F0R_OK: Optional[bool] = None
_F0R_LY_DO = ""


def co_frei0r(bat_buoc_do_lai: bool = False) -> bool:
    """frei0r DÙNG ĐƯỢC THẬT hay không — thử NẠP bằng ffmpeg, không đoán theo file.

    Máy nhân viên thiếu plugin/thiếu runtime -> False -> nhóm frei0r bị loại khỏi
    `dung_duoc()` và app chạy bình thường (KHÔNG ném lỗi). Nhớ kết quả trong
    tiến trình (1 lần/lần chạy app) vì mỗi lần thử là 1 lệnh ffmpeg ~0,25 s.
    """
    global _F0R_OK, _F0R_LY_DO
    if _F0R_OK is not None and not bat_buoc_do_lai:
        return _F0R_OK
    dat_frei0r_path()
    bao_dam_runtime()
    d = thu_muc_frei0r()
    if not d.is_dir() or not any(d.glob("*.dll")):
        _F0R_OK, _F0R_LY_DO = False, f"khong co plugin trong {d}"
        return False
    # thử nạp 1 plugin C (glow) + 1 plugin C++ (vignette, cần libstdc++ cạnh
    # ffmpeg.exe). C++ lỗi -> vẫn coi là CÓ frei0r nhưng `dung_duoc` sẽ tự loại
    # các hiệu ứng cần plugin đó (kiểm bằng `module_co()`).
    _F0R_OK = _thu_module("glow")
    _F0R_LY_DO = "" if _F0R_OK else "ffmpeg khong nap duoc module 'glow'"
    return _F0R_OK


def ly_do_khong_co_frei0r() -> str:
    co_frei0r()
    return _F0R_LY_DO


_MOD_CACHE: dict = {}


def _thu_module(ten: str) -> bool:
    if ten in _MOD_CACHE:
        return _MOD_CACHE[ten]
    cmd = [_ffmpeg(), "-hide_banner", "-nostats", "-v", "error",
           "-f", "lavfi", "-i", "color=c=gray:s=64x64:d=0.04",
           "-vf", f"frei0r=filter_name={ten}", "-frames:v", "1",
           "-f", "null", os.devnull]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ok = p.returncode == 0
    except Exception:  # noqa: BLE001
        ok = False
    _MOD_CACHE[ten] = ok
    return ok


def module_co(ten: str) -> bool:
    """1 module frei0r cụ thể có nạp được không (có nhớ kết quả)."""
    if not ten:
        return True
    if not co_frei0r():
        return False
    return _thu_module(ten)


# ------------------------------------------------------------------ KHO
@dataclass
class HieuUng:
    """1 hiệu ứng. `mau` là khuôn chuỗi filter, thay:
      {en}  -> `:enable='between(t,A,B)'`   (filter CÓ timeline)
      {a}{b}-> mốc bắt/kết (dùng cho zoompan/crop — KHÔNG có timeline)
      {W}{H}{FPS} -> khung ra
      {p1}..-> tham số đã nội suy theo `dam`
    """
    khoa: str
    ten: str                    # tên TIẾNG VIỆT cho anh Hùng
    capcut: str                 # tên trong bảng Effects của CapCut
    nhom: str                   # "thuan" | "frei0r"
    mau: str
    module: str = ""            # module frei0r cần (rỗng = filter thuần ffmpeg)
    # tham số: mỗi phần tử (min, max) — nội suy theo dam 0..DAM_MAX/DAM_MAX
    ts: tuple = ()
    dai: float = 0.45           # thời lượng ưa dùng (giây) — trong [DAI_MIN, DAI_MAX]
    hop: tuple = ("caotrao",)   # loại điểm nhấn phù hợp
    can_font: bool = False
    #: DỜI CHỖ pixel (zoom/rung/glitch/méo) chứ KHÔNG pha lại màu. Với loại này,
    #: đo lệch U/V TỪNG PIXEL là SAI: da vẫn đúng màu, chỉ nằm chỗ khác. Cổng 37
    #: đổi sang kiểm PHÂN BỐ chroma (trung bình + độ lệch chuẩn U/V phải giữ) —
    #: đó mới là "không đổi màu da". Loại KHÔNG dời chỗ thì kiểm cả từng pixel
    #: (bắt được desaturate: `bw0r` đẩy U,V về 128, trung bình chỉ lệch 2,8 mà
    #: từng pixel lệch cả chục).
    doi_cho: bool = False
    #: ngưỡng "THẤY ĐƯỢC": % pixel |dY|>12 ở giữa cửa sổ. Chữ (đếm ngược) chiếm
    #: ít DIỆN TÍCH nhưng mắt thấy ngay -> hạ ngưỡng diện tích, bù bằng ngưỡng
    #: `manh` (% pixel |dY|>60). Cùng bài học cổng 21: ngưỡng phải theo BẢN CHẤT.
    nguong_thay: float = 8.0
    nguong_manh: float = 1.0
    ghi_chu: str = ""

    def chuoi(self, dam: float, a: float, b: float, W: int, H: int,
              fps: float = 30, font: str = "") -> str:
        d = max(0.0, min(DAM_MAX, float(dam))) / DAM_MAX      # 0..1
        s = self.mau
        for i, (lo, hi) in enumerate(self.ts, start=1):
            s = s.replace("{p%d}" % i, f"{lo + (hi - lo) * d:g}")
        s = (s.replace("{en}", f":enable='between(t,{a:.3f},{b:.3f})'")
              .replace("{a}", f"{a:.3f}").replace("{b}", f"{b:.3f}")
              .replace("{W}", str(W)).replace("{H}", str(H))
              # `%g` chứ không `str()`: nguồn 29,97 fps ra
              # "29.970029970029973" -> zoompan bắt lỗi cú pháp video_rate.
              .replace("{FPS}", f"{float(fps):g}")
              .replace("{FONT}", font.replace("\\", "/").replace(":", "\\:")))
        return s


def _f0r(mod: str, params: str = "") -> str:
    s = f"frei0r=filter_name={mod}"
    if params:
        s += f":filter_params={params}"
    return s + "{en}"


# LOẠI ĐIỂM NHẤN (dùng cho luật chọn):
#   caotrao : tiếng to đột biến (gào/khóc/va chạm)      -> nhấn mạnh
#   dong    : hình đổi nhiều (rượt/đánh/xe chạy)        -> glitch/vỡ hình
#   tinh    : hình gần như đứng (người ngồi nói)        -> KHÔNG ĐỤNG (chỉ mood)
#   chot    : câu chốt / cuối clip                      -> nháy rồi tối dần
#   ke      : đang kể chậm, đều                         -> mood phim, rất kín
#   noi     : chỗ ghép đoạn                             -> nhấn ngay sau chỗ nối
KHO: dict = {}


def _dk(h: HieuUng) -> None:
    KHO[h.khoa] = h


# ---- NHÓM 1: NHẤN / CAO TRÀO (thuần ffmpeg — chạy MỌI máy) ----
_dk(HieuUng(
    "zoom_nhoi", "Zoom nhồi (giật vào)", "Zoom Lens", "thuan",
    # zoompan KHÔNG có timeline -> cổng thời gian nằm TRONG biểu thức z.
    # d=1 + s=WxH: mỗi khung vào ra đúng 1 khung, kích thước ra CỐ ĐỊNH.
    "zoompan=z='if(between(it,{a},{b}),{p1},1)':d=1:"
    "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}",
    ts=((1.06, 1.16),), dai=0.40, hop=("caotrao", "chot", "noi"),
    doi_cho=True))
_dk(HieuUng(
    "zoom_day", "Zoom đẩy chậm", "Zoom In", "thuan",
    "zoompan=z='if(between(it,{a},{b}),1+({p1}-1)*(it-{a})/({b}-{a}),1)':d=1:"
    "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}",
    ts=((1.06, 1.16),), dai=0.70, hop=("ke", "caotrao"), doi_cho=True))
_dk(HieuUng(
    "rung_lac", "Rung lắc", "Spin & Shake", "thuan",
    # BẢN ĐẦU DÙNG `crop`+`scale` VÀ ĐÃ SAI (cổng 37 bắt): crop 36 px rồi
    # scale lại làm khung ĐỔI CẢ NGOÀI cửa sổ -> đo **18,7% pixel khác** ở giây
    # 0,40 (ngoài [a,b]) = hiệu ứng RÒ ra toàn clip, đúng cái luật 1 cấm.
    # `crop` KHÔNG có timeline nên `enable` không gate được nó.
    # ĐÚNG: zoompan — ngoài cửa sổ zoom=1 VÀ biên độ nhân `between()` = 0 nên
    # x = iw/2 - iw/2 + 0 = 0 -> khung Y NGUYÊN.
    "zoompan=z='if(between(it,{a},{b}),1.05,1)':d=1:"
    "x='iw/2-(iw/zoom/2)+{p1}*sin(37*it)*between(it,{a},{b})':"
    "y='ih/2-(ih/zoom/2)+{p1}*cos(29*it)*between(it,{a},{b})':"
    "s={W}x{H}:fps={FPS}",
    ts=((6, 16), ), dai=0.45, hop=("caotrao", "dong"), doi_cho=True))
_dk(HieuUng(
    "loe_sang", "Loé sáng", "Flash", "thuan",
    "eq=brightness={p1}:contrast={p2}{en}",
    ts=((0.10, 0.26), (1.02, 1.10)), dai=0.30, hop=("caotrao", "noi", "chot")))
_dk(HieuUng(
    "sup_toi", "Sụp tối", "Flicker Blackout", "thuan",
    "eq=brightness=-{p1}{en}",
    ts=((0.14, 0.34), ), dai=0.35, hop=("chot", "noi")))
_dk(HieuUng(
    "nhay_sang", "Nháy sáng liên tục", "Flickery Shots", "thuan",
    # eval=frame BẮT BUỘC: mặc định `eq` chỉ tính biểu thức 1 LẦN lúc init ->
    # đo thật ra 0,0% pixel đổi (hiệu ứng KHÔNG xảy ra) mà ffmpeg vẫn mã 0.
    "eq=brightness='{p1}*sin(3.14159*9*t)':eval=frame{en}",
    ts=((0.10, 0.24), ), dai=0.50, hop=("caotrao", "chot")))
# ĐÃ BỎ "Nét gắt" (`unsharp`): đo ở trần 5,0 (biên độ tối đa của filter) vẫn
# chỉ 6,3% pixel đổi -> anh Hùng KHÔNG THẤY. Làm nét là chỉnh màu, không phải
# hiệu ứng. Đừng thêm lại mà không đo.
_dk(HieuUng(
    "tuong_phan", "Tăng tương phản", "Contrast Punch", "thuan",
    "eq=contrast={p1}:saturation=1.0{en}",
    ts=((1.18, 1.55), ), dai=0.40, hop=("caotrao", "ke")))

# ---- NHÓM 2: GLITCH / VỠ HÌNH (cảnh ĐỘNG) ----
_dk(HieuUng(
    "o_vuong", "Ô vuông vỡ", "Pixel Glitch", "thuan",
    "pixelize=w={p1}:h={p1}:mode=avg{en}",
    ts=((22, 52), ), dai=0.32, hop=("dong", "noi"), doi_cho=True))
_dk(HieuUng(
    "xao_dong", "Xáo dòng ngang", "Glitch Scrub", "thuan",
    "shufflepixels=direction=inverse:mode=horizontal:width={p1}:height={p1}{en}",
    ts=((24, 56), ), dai=0.30, hop=("dong",), doi_cho=True))
# LUẬT 3 ĐÃ TỰ BỎ "Lệch màu RGB" (`rgbashift`): nó SINH RA viền màu mới nên
# phân bố chroma phồng **U +7,16 · V +12,04** (trần 3,0) — đúng loại "đổi màu"
# anh Hùng từ chối. Mà nó cũng chỉ đổi 5,6% pixel SÁNG. Glitch đã có 3 kiểu khác.
_dk(HieuUng(
    "glitch_khoi", "Glitch khối", "Polygon Glitch", "frei0r",
    # tham số 4 là "Color glitching INTENSITY" (số thực) chứ KHÔNG phải bool ->
    # truyền `n` làm ffmpeg FAIL cả lệnh (cổng 37 bắt). 0 = không đổi màu.
    _f0r("glitch0r", "{p1}|0.28|{p2}|0"), module="glitch0r",
    ts=((0.28, 0.62), (0.30, 0.60)), dai=0.35, hop=("dong", "caotrao"),
    doi_cho=True))
_dk(HieuUng(
    "lech_bang", "Lệch băng cũ (VHS)", "Glitch Scrub", "frei0r",
    _f0r("nosync0r", "{p1}"), module="nosync0r",
    ts=((0.04, 0.14), ), dai=0.40, hop=("dong", "noi"), doi_cho=True))
_dk(HieuUng(
    "dong_quet", "Dòng quét màn hình", "Scanline", "frei0r",
    _f0r("scanline0r", "{p1}|0.35"), module="scanline0r",
    ts=((0.25, 0.55), ), dai=0.45, hop=("dong", "ke")))
_dk(HieuUng(
    "nhieu_analog", "Nhiễu băng analog", "Filmstrip Noise", "frei0r",
    # mức 0,75 đo ra |dU| 6,5 / |dV| 7,1 = LOÈ MÀU (luật 3) -> trần còn 0,32.
    _f0r("ntsc", "{p1}|n|y"), module="ntsc",
    ts=((0.08, 0.16), ), dai=0.50, hop=("ke", "dong"), doi_cho=True))

# ---- NHÓM 3: PHIM / KHÍ CHẤT (hợp tài liệu-drama Nhật) ----
_dk(HieuUng(
    "quang_sang", "Quầng sáng phim", "Film Radiance", "frei0r",
    _f0r("glow", "{p1}"), module="glow",
    ts=((0.16, 0.42), ), dai=0.60, hop=("ke", "chot", "tinh")))
_dk(HieuUng(
    "sang_diu", "Sáng dịu vùng chói", "Light Haze", "frei0r",
    _f0r("softglow", "{p1}|0.55|0.5|0.5"), module="softglow",
    ts=((0.20, 0.45), ), dai=0.60, hop=("ke", "tinh")))
_dk(HieuUng(
    "hat_phim", "Hạt phim", "Film Grain", "frei0r",
    _f0r("filmgrain", "{p1}"), module="filmgrain",
    ts=((0.25, 0.60), ), dai=0.60, hop=("ke", "tinh")))
_dk(HieuUng(
    "hat_nhieu", "Hạt nhiễu tài liệu", "Filmstrip Noise", "thuan",
    # `alls` rắc nhiễu vào CẢ mặt màu -> đo |dU| 7,2 / |dV| 10,7 = LOÈ MÀU.
    # `c0s` chỉ rắc vào mặt SÁNG (plane 0) — cũng đúng bản chất hạt phim thật.
    "noise=c0s={p1}:c0f=t+u{en}",
    ts=((16, 40), ), dai=0.50, hop=("ke", "tinh")))
# ĐÃ BỎ "Rung phim nhựa" (frei0r `gateweave`): mức trần `1|1|1` đo ra **0,1%**
# pixel đổi. Hiệu ứng thật của nó là xê dịch dưới 1 pixel — đúng bản chất "gate
# weave" nhưng vô hình trên khung dọc 1080x1920. Muốn rung thì dùng "Rung lắc".
_dk(HieuUng(
    "toi_vien", "Tối viền ống kính", "Vignette", "thuan",
    "vignette=a='{p1}'{en}",
    ts=((0.70, 1.05), ), dai=0.70, hop=("ke", "tinh", "chot")))
_dk(HieuUng(
    "vien_phim", "Viền đen kiểu phim", "Cinema Bars", "frei0r",
    _f0r("letterb0xed", "{p1}|y"), module="letterb0xed",
    ts=((0.05, 0.13), ), dai=0.70, hop=("ke", "chot"), doi_cho=True))
_dk(HieuUng(
    "mo_net", "Mờ nét nhanh", "Focus Pull", "thuan",
    # sigma 12 do o 540x960 ra 9,7% nhung o 1080x1920 chi 5,4% (ban kinh mo la
    # SO PIXEL TUYET DOI, khung to gap doi thi mo tuong doi nho di 1 nua).
    # gblur khong nhan bieu thuc theo ih -> noi tran len 26 cho khung doc 1080.
    "gblur=sigma={p1}{en}",
    ts=((10, 26), ), dai=0.35, hop=("noi", "chot")))
_dk(HieuUng(
    "mo_vuong", "Mờ khối", "Blur Burst", "frei0r",
    _f0r("squareblur", "{p1}"), module="squareblur",
    ts=((0.10, 0.28), ), dai=0.35, hop=("noi",)))

# ---- NHÓM 4: CHUYỂN ĐỘNG / VỆT ----
# ĐÃ THỬ 5 CÁCH CHO "VỆT ĐUÔI CHUYỂN ĐỘNG", KHÔNG CÁCH NÀO QUA ĐƯỢC — ghi lại
# để phiên sau đừng thử lại:
#   `lagfun=decay=0.94`  -> 0,0% pixel đổi. Filter giữ trạng thái giữa các khung,
#                           bị `enable` bật/tắt là mất trạng thái nên không kịp
#                           tạo vệt.
#   `tmix` / `tblend`    -> 0,0% VÀ **DỜI THỜI GIAN** (đệm N khung mới ra) nên
#                           khung ở cùng mốc là nội dung KHÁC -> đo `tmix` ra
#                           dU=-34 dV=-65: tưởng loè màu, thật ra là LỆCH GIỜ.
#   `aech0r`/`delay0r`/`nervous` (frei0r) -> 0,0%.
#   `baltan` (frei0r)    -> 94,5% pixel đổi (thấy rất rõ) NHƯNG trộn khung làm
#                           PHẲNG chroma: phân bố U -3,08 V -3,16, vượt trần 3,0
#                           -> **LUẬT 3 TỰ BỎ**. Plugin không có tham số để hạ.
# LUAT 3 DA TU BO "Bong chong xoay" (frei0r `vertigo`): tron khung voi ban
# zoom+quay nen lam PHANG chroma -> phan bo U -2,83 V -3,10, vuot tran 3,0. Da
# thu ha tran tham so tu 0,035 ve 0,022, so do KHONG doi (muc tron nam trong
# ruot plugin, khong co num). Cung benh voi `baltan`: moi hieu ung TRON KHUNG
# deu lam phang chroma -> dung thu them kieu nay.
_dk(HieuUng(
    "vien_net", "Viền sáng nét", "Neon Flow", "thuan",
    "edgedetect=mode=colormix:high={p1}{en}",
    ts=((0.30, 0.16), ), dai=0.35, hop=("dong",),
    ghi_chu="high THẤP = viền ĐẬM -> ts nghịch"))
_dk(HieuUng(
    "meo_kinh", "Méo ống kính", "Lens Warp", "frei0r",
    _f0r("lenscorrection", "0.5|0.5|{p1}|0.5|0.5"), module="lenscorrection",
    ts=((0.545, 0.60), ), dai=0.45, hop=("caotrao", "dong"), doi_cho=True))
_dk(HieuUng(
    "song_meo", "Sóng méo mặt nước", "Wave Warp", "frei0r",
    _f0r("distort0r", "{p1}|0.32|n|0.5"), module="distort0r",
    ts=((0.02, 0.06), ), dai=0.50, hop=("dong", "ke"), doi_cho=True))
_dk(HieuUng(
    "dem_nguoc", "Đếm ngược 3-2-1", "Countdown 3", "thuan",
    # 3 drawtext, mỗi số 1/3 cửa sổ. Không dùng emoji/ký tự lạ (máy anh Hùng
    # từng ra Ô ĐEN vì thiếu glyph) — chỉ chữ số.
    "drawtext=fontfile='{FONT}':text='3':fontsize=h/3.2:fontcolor=white@{p1}:"
    "borderw=4:bordercolor=black@{p1}:x=(w-text_w)/2:y=(h-text_h)/2"
    ":enable='between(t,{a},{a}+0.30)',"
    "drawtext=fontfile='{FONT}':text='2':fontsize=h/3.2:fontcolor=white@{p1}:"
    "borderw=4:bordercolor=black@{p1}:x=(w-text_w)/2:y=(h-text_h)/2"
    ":enable='between(t,{a}+0.30,{a}+0.60)',"
    "drawtext=fontfile='{FONT}':text='1':fontsize=h/3.2:fontcolor=white@{p1}:"
    "borderw=4:bordercolor=black@{p1}:x=(w-text_w)/2:y=(h-text_h)/2"
    ":enable='between(t,{a}+0.60,{b})'",
    ts=((0.55, 0.95), ), dai=0.80, hop=("noi",), can_font=True,
    nguong_thay=2.0, nguong_manh=0.8))


# ------------------------------------------------------ HIỆU ỨNG DÙNG ĐƯỢC
#: Hiệu ứng ĐO RA lệch màu >= UV_MAX -> KHÔNG BAO GIỜ tự chọn (luật 3). Danh
#: sách này là KẾT QUẢ ĐO của cổng 37 (`_test_hieu_ung.py`), không phải đoán:
#: mọi hiệu ứng đổi hue/độ bão hoà đều bị loại — `colortap` dU=14,1 dV=-18,4;
#: `saturat0r` dU=-4,1 dV=6,3; `colorize` dU=-6,5; `hueshift0r` dV=-4,4;
#: `tmix` dU=-34,1 dV=-65,5 (nặng nhất). Chúng KHÔNG có trong KHO.
LOAI_DOI_MAU: tuple = ("colortap", "saturat0r", "colorize", "hueshift0r",
                       "tint0r", "bw0r", "luminance", "threshold0r",
                       "emboss", "colorhalftone", "sigmoidaltransfer", "tmix",
                       "rgbashift", "baltan", "vertigo", "sobel", "cartoon")


def dung_duoc(co_font: bool = True) -> list[str]:
    """Khoá các hiệu ứng CHẠY ĐƯỢC trên máy này (đã kiểm frei0r thật)."""
    ra = []
    for k, h in KHO.items():
        if h.can_font and not co_font:
            continue
        if h.module and not module_co(h.module):
            continue
        ra.append(k)
    return ra


def thong_ke() -> dict:
    """Đếm hiệu ứng theo nhóm (cho báo cáo/UI)."""
    dd = set(dung_duoc())
    return {
        "tong_kho": len(KHO),
        "dung_duoc": len(dd),
        "thuan": sum(1 for k in dd if KHO[k].nhom == "thuan"),
        "frei0r": sum(1 for k in dd if KHO[k].nhom == "frei0r"),
        "co_frei0r": co_frei0r(),
    }


# ------------------------------------------------- AI CHỌN THEO CẢNH
def _tv(xs: list) -> float:
    ys = sorted(x for x in xs if x is not None)
    if not ys:
        return 0.0
    n = len(ys)
    return ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2.0


def loai_diem(giay: int, nl: list, cd: list, moc_noi: list,
              tong: float) -> str:
    """LOẠI của giây thứ `giay` trên timeline ĐẦU RA — suy từ SỐ ĐO, không bốc thăm.

    Khuôn y hệt `m1_highlight._loai_theo_khoang_nhay` (đang chạy tốt cho tiếng
    động + chuyển cảnh): đọc dữ liệu CÓ SẴN rồi suy, KHÔNG thêm lượt LLM.
      nl = mức âm RMS từng giây (`chon_doan.nang_luong`)
      cd = mức chuyển động từng giây (`chon_doan.chuyen_dong`)
    Ngưỡng lấy theo TRUNG VỊ của chính clip (mỗi video một mức ồn khác nhau —
    ngưỡng cứng thì video êm không bao giờ có "cao trào", video ồn thì chỗ nào
    cũng "cao trào").
    """
    for m in moc_noi or []:
        if abs(giay - m) <= 0.6:
            return "noi"
    if tong and giay >= tong - 3.0:
        return "chot"
    nl_tv = _tv(nl) if nl else 0.0
    cd_tv = _tv(cd) if cd else 0.0
    a = nl[giay] if nl and giay < len(nl) else 0.0
    v = cd[giay] if cd and giay < len(cd) else 0.0
    # cảnh TĨNH: hình gần như đứng -> luật anh Hùng: KHÔNG ĐỤNG hiệu ứng động
    if cd and v <= cd_tv * 0.55:
        return "tinh"
    if nl and nl_tv > 0 and a >= nl_tv * 1.7:
        return "caotrao"
    if cd and cd_tv > 0 and v >= cd_tv * 1.5:
        return "dong"
    return "ke"


def _diem_hap_dan(nl: list, cd: list) -> list[tuple[int, float]]:
    """Giây nào ĐÁNG đặt hiệu ứng nhất -> [(giây, điểm)] giảm dần.

    Điểm = mức âm chuẩn hoá + mức động chuẩn hoá, cộng thưởng cho ĐỘT BIẾN so
    với 2 giây trước (cú va chạm/tiếng gào bắt đầu ở đó, không phải ở giữa)."""
    n = max(len(nl or []), len(cd or []))
    if not n:
        return []
    nl_tv = _tv(nl) or 1e-6
    cd_tv = _tv(cd) or 1e-6
    ra = []
    for i in range(n):
        a = (nl[i] / nl_tv) if nl and i < len(nl) else 0.0
        v = (cd[i] / cd_tv) if cd and i < len(cd) else 0.0
        truoc_a = _tv([nl[j] for j in range(max(0, i - 3), i)
                       if j < len(nl)]) if nl else 0.0
        dot = max(0.0, ((nl[i] - truoc_a) / nl_tv)) if (nl and i < len(nl)) else 0.0
        ra.append((i, a + v + 1.5 * dot))
    ra.sort(key=lambda x: -x[1])
    return ra


def chon_hieu_ung(tong_giay: float, muc: str = "vua",
                  nl: Optional[list] = None, cd: Optional[list] = None,
                  moc_noi: Optional[list] = None,
                  co_the_dung: Optional[list] = None) -> list[dict]:
    """AI CHỌN HIỆU ỨNG THEO CẢNH — TIỀN ĐỊNH, KHÔNG RANDOM.

    Trả [{bat, het, khoa, dam, loai, vi_sao}] trên timeline ĐẦU RA (giây).
    Anh Hùng: *"AI tự quyết cảnh nào phần nào chọn hiệu ứng nào… k phải mấy cảnh
    vớ vẩn k phù hợp lại thêm vào ngớ ngẩn"*. Vì vậy:
      - chọn ĐIỂM theo SỐ ĐO (âm lượng đột biến + mức chuyển động), không bốc thăm;
      - cảnh **TĨNH** (hình gần đứng) chỉ được nhận hiệu ứng MOOD (quầng sáng /
        hạt phim / tối viền), KHÔNG bao giờ nhận zoom/rung/glitch;
      - mỗi clip tối đa `MUC_DIEM[muc]` điểm và 2 điểm cách >= `CACH_MIN` giây;
      - **KHÔNG lặp 1 kiểu** ở mọi điểm (đúng lỗi cũ "mọi Part một tiếng ding").
    Hàm THUẦN: không gọi ffmpeg, không đọc settings -> unit test được.
    """
    m = str(muc or "").strip().lower()
    if m not in MUC_DAM or float(tong_giay or 0) < 2.0:
        return []
    dung = list(co_the_dung if co_the_dung is not None else dung_duoc())
    if not dung:
        return []
    dam = MUC_DAM[m]
    n_diem = min(DIEM_MAX, MUC_DIEM[m])
    nl = list(nl or [])
    cd = list(cd or [])
    moc = [float(x) for x in (moc_noi or [])]

    # ---- ứng viên điểm: theo số đo nếu có; không có thì theo CẤU TRÚC
    if nl or cd:
        uv = [g for g, _s in _diem_hap_dan(nl, cd)]
    else:
        # Không đo được (clip cũ / video câm) -> vẫn phải thông minh: đặt ngay
        # SAU chỗ nối (chỗ đổi mạch, mắt đang chờ) + 1 điểm ở câu chốt.
        uv = [int(round(x)) for x in moc]
        uv.append(max(0, int(float(tong_giay)) - 2))
        uv.append(int(float(tong_giay) * 0.28))

    ra: list[dict] = []
    da_dung: list[str] = []
    for g in uv:
        if len(ra) >= n_diem:
            break
        g = int(max(0, min(int(float(tong_giay)) - 1, g)))
        if any(abs(g - r["bat"]) < CACH_MIN for r in ra):
            continue
        loai = loai_diem(g, nl, cd, moc, float(tong_giay))
        chon = _chon_kieu(loai, dung, da_dung, len(ra))
        if not chon:
            continue
        h = KHO[chon]
        dai = max(DAI_MIN, min(DAI_MAX, h.dai))
        bat = float(g)
        het = min(float(tong_giay) - 0.05, bat + dai)
        if het - bat < DAI_MIN:
            continue
        ra.append({"bat": round(bat, 3), "het": round(het, 3), "khoa": chon,
                   "dam": dam, "loai": loai,
                   "vi_sao": _vi_sao(loai, g, nl, cd, moc, float(tong_giay))})
        da_dung.append(chon)
    ra.sort(key=lambda r: r["bat"])
    return ra


#: Ứng viên theo LOẠI điểm — thứ tự = ưu tiên. Cảnh TĨNH chỉ có mood.
_UV_THEO_LOAI: dict = {
    "caotrao": ("zoom_nhoi", "rung_lac", "loe_sang", "nhay_sang",
                "tuong_phan", "meo_kinh"),
    "dong": ("glitch_khoi", "o_vuong", "xao_dong", "lech_bang",
             "vien_net", "dong_quet", "song_meo"),
    "tinh": ("quang_sang", "hat_phim", "toi_vien", "sang_diu", "nhieu_analog",
             "hat_nhieu", "vien_phim"),
    "chot": ("sup_toi", "nhay_sang", "toi_vien", "quang_sang", "zoom_nhoi",
             "vien_phim"),
    "noi": ("mo_net", "loe_sang", "o_vuong", "mo_vuong", "lech_bang",
            "zoom_nhoi", "dem_nguoc"),
    "ke": ("quang_sang", "hat_phim", "nhieu_analog", "dong_quet", "toi_vien",
           "zoom_day", "hat_nhieu", "tuong_phan"),
}


def _chon_kieu(loai: str, dung: list, da_dung: list, i: int) -> str:
    """Kiểu cho loại điểm này, ƯU TIÊN kiểu CHƯA dùng trong clip (không lặp)."""
    uv = [k for k in _UV_THEO_LOAI.get(loai, ()) if k in dung]
    if not uv:
        return ""
    moi = [k for k in uv if k not in da_dung]
    if moi:
        # xoay theo chỉ số điểm -> 2 clip khác nhau không ra y hệt một bộ
        return moi[i % len(moi)]
    return uv[i % len(uv)]


_LOAI_NHAN = {"caotrao": "cao trào (tiếng vọt lên)",
              "dong": "cảnh động mạnh", "tinh": "cảnh tĩnh",
              "chot": "câu chốt cuối clip", "noi": "chỗ ghép đoạn",
              "ke": "đang kể đều"}


def _vi_sao(loai: str, g: int, nl: list, cd: list, moc: list,
            tong: float) -> str:
    s = _LOAI_NHAN.get(loai, loai)
    ch = []
    if nl and g < len(nl):
        tv = _tv(nl) or 1e-9
        ch.append(f"âm {nl[g]:.3f} = {nl[g] / tv:.1f}x trung vị")
    if cd and g < len(cd):
        tv = _tv(cd) or 1e-9
        ch.append(f"động {cd[g]:.3f} = {cd[g] / tv:.1f}x trung vị")
    if loai == "noi":
        ch.append("sát mốc ghép " + ", ".join(f"{x:.1f}s" for x in moc))
    return f"giây {g}: {s}" + (" — " + "; ".join(ch) if ch else "")


# ------------------------------------------------------- DỰNG CHUỖI FILTER
def font_mac_dinh(goi_y: str = "") -> str:
    """1 FILE font .ttf/.otf để `drawtext` dùng (hiệu ứng "Đếm ngược 3-2-1").

    `drawtext` cần ĐƯỜNG DẪN FILE, không nhận thư mục — truyền thư mục là
    ffmpeg FAIL cả lệnh. `goi_y` có thể là file hoặc thư mục (app truyền
    `fonts_dir`); không tìm được file nào -> "" và `chuoi_filter` TỰ BỎ hiệu ứng
    cần font (KHÔNG nổ lỗi trên máy nhân viên thiếu font).
    """
    if goi_y and os.path.isfile(goi_y):
        return goi_y
    for d in [x for x in (goi_y, str(_root() / "app" / "assets" / "fonts")) if x]:
        try:
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".ttf", ".otf")):
                    return os.path.join(d, f)
        except OSError:
            continue
    return ""


def chuoi_filter(chon: list, W: int, H: int, fps: float = 30,
                 font: str = "") -> str:
    """Nối các hiệu ứng đã chọn thành 1 chuỗi filter (dấu phẩy).

    Rỗng -> "" (caller BỎ HẲN, đường cũ y nguyên — bất biến sống còn).
    `font` nhận cả FILE và THƯ MỤC (tự tìm ra file — xem `font_mac_dinh`).
    """
    font = font_mac_dinh(font) if font else ""
    out = []
    for c in chon or []:
        h = KHO.get(str(c.get("khoa", "")))
        if not h:
            continue
        if h.can_font and not font:
            continue
        out.append(h.chuoi(float(c.get("dam", MUC_DAM["vua"])),
                           float(c["bat"]), float(c["het"]), W, H, fps, font))
    return ",".join(out)


def bang_ghi_chu(chon: list) -> str:
    """Bảng 'giây thứ mấy -> hiệu ứng gì -> vì sao' (tiếng Việt) cho anh Hùng."""
    if not chon:
        return "(không có hiệu ứng nào)"
    d = ["giây     | hiệu ứng                  | CapCut            | vì sao chọn",
         "-" * 100]
    for c in chon:
        h = KHO.get(c["khoa"])
        d.append(f"{c['bat']:6.2f}-{c['het']:5.2f} | {(h.ten if h else c['khoa']):<25} "
                 f"| {(h.capcut if h else ''):<17} | {c.get('vi_sao', '')}")
    return "\n".join(d)


# --------------------------------------------------------- ĐO NHỊP CLIP
def duong_filter(p: str) -> str:
    r"""Đường dẫn Windows -> dạng NHÉT ĐƯỢC vào chuỗi filter của ffmpeg.

    **LỖI THẬT tìm ra 08/08/2026 — im lặng nên đã che mất cả tính năng:**
    `metadata=print:file='C:/…/v.txt'` bị ffmpeg **báo vỡ cú pháp** ("Error
    parsing filterchain … Invalid argument") vì dấu `:` của ổ `C:` là dấu ngăn
    tham số — dấu nháy đơn KHÔNG cứu được. Hậu quả: `do_nhip` LUÔN trả
    `([], [])` trên Windows -> `chon_hieu_ung` mất hết số đo tiếng/động và tụt
    về đường chọn THEO CẤU TRÚC. Nhìn vào bản demo thì vẫn "có hiệu ứng", chỉ
    dòng "vì sao" là thiếu số — đúng kiểu bẫy `0,03 CPU-giây` của việc này.
    Phải escape `:` thành `\:` (đo lại: 22 dòng YAVG thay vì 0).
    """
    return str(p).replace("\\", "/").replace(":", "\\:")



def do_nhip(path: str, ffmpeg: str = "",
            dau_vao: Optional[list] = None) -> tuple[list, list]:
    """Đo mức ÂM + mức ĐỘNG từng giây của 1 FILE (timeline = timeline file).

    1 LỆNH ffmpeg, 1 lượt giải mã, 2 nhánh filter (audio astats + video
    tblend/signalstats) — rẻ hơn 2 lệnh. Dùng ĐÚNG khuôn `chon_doan.nang_luong`
    / `chon_doan.chuyen_dong` để số liệu so được với khâu chọn đoạn.
    Lỗi/không có tiếng -> trả ([], []) và caller vẫn chọn được theo CẤU TRÚC.

    `dau_vao`: THAY chỗ `-i <path>` bằng danh sách tham số đầu vào của caller —
    dùng để đo ĐÚNG timeline ĐẦU RA mà không phải xuất file trung gian:
      nhiều đoạn: ["-f","concat","-safe","0","-i", <file danh sách>]
      một đoạn  : ["-ss", s, "-t", e-s, "-i", <nguồn>]
    Không truyền -> đo cả file `path` như cũ.
    """
    import re
    import tempfile
    ff = ffmpeg or _ffmpeg()
    td = tempfile.mkdtemp(prefix="_nhip_")
    fa, fv = os.path.join(td, "a.txt"), os.path.join(td, "v.txt")
    ga = (f"[0:a]aresample=16000,asetnsamples=n=16000,"
          f"astats=metadata=1:reset=1,ametadata=print:"
          f"key=lavfi.astats.Overall.RMS_level:file='{duong_filter(fa)}'"
          f"[ao]")
    gv = (f"[0:v]fps=4,scale=160:-2,format=gray,tblend=all_mode=difference,"
          f"signalstats,metadata=print:key=lavfi.signalstats.YAVG:"
          f"file='{duong_filter(fv)}'[vo]")
    nl: list = []
    cd: list = []
    vao = [str(x) for x in (dau_vao or ["-i", str(path)])]
    for graph, maps in ((gv + ";" + ga, ["-map", "[vo]", "-map", "[ao]"]),
                        (gv, ["-map", "[vo]"])):
        cmd = [ff, "-y", "-hide_banner", "-nostats", "-v", "error",
               *vao, "-filter_complex", graph, *maps,
               "-f", "null", os.devnull]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                               errors="replace",
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:  # noqa: BLE001
            break
        if p.returncode == 0:
            break                       # có tiếng -> xong; không thì thử nhánh 2
    try:
        if os.path.exists(fa):
            for mm in re.finditer(r"RMS_level=(-?[0-9.]+|-inf)",
                                  open(fa, encoding="utf-8", errors="replace").read()):
                v = mm.group(1)
                nl.append(0.0 if v == "-inf" else min(1.0, 10 ** (float(v) / 20.0)))
        if os.path.exists(fv):
            diem = [min(1.0, float(mm.group(1)) / 64.0) for mm in re.finditer(
                r"signalstats\.YAVG=([0-9.]+)",
                open(fv, encoding="utf-8", errors="replace").read())]
            cd = [min(1.0, max(diem[i:i + 4])) for i in range(0, len(diem), 4)]
    except OSError:
        pass
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    return nl, cd


if __name__ == "__main__":         # in kho ra cho người đọc
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"frei0r: {co_frei0r()}  ({ly_do_khong_co_frei0r() or 'ok'})")
    print(f"thư mục: {thu_muc_frei0r()}")
    dd = set(dung_duoc())
    print(f"{'khoá':<14}{'tên tiếng Việt':<26}{'CapCut':<19}{'nhóm':<8}dùng được")
    for k, h in KHO.items():
        print(f"{k:<14}{h.ten:<26}{h.capcut:<19}{h.nhom:<8}{'CÓ' if k in dd else 'KHÔNG'}")
    print(thong_ke())
