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
#: luật 5 (anh Hùng 08/08/2026 — "tuỳ cái, cái nào cần thì hiện thôi"): TỔNG số
#: giây CÓ hiệu ứng không được quá 10% thời lượng clip. Đây là cái phanh CUỐI:
#: dù 3 điểm nhấn đều hợp lệ, clip 12 giây (trần 1,2s) chỉ nhận được 2 điểm.
TY_LE_MAX = 0.10
#: DẢI ĐỘNG tối thiểu để coi là "clip CÓ cao trào". max/trung vị dưới mức này
#: nghĩa là clip PHẲNG (đọc đều, không va chạm) -> KHÔNG thêm gì ngoài chỗ nối.
#: Đo trên 3 video Nhật thật: dải động tiếng 2,1-6,4 · hình 1,9-4,8; nguồn
#: `sine` phẳng tuyệt đối ra 1,00. Ngưỡng 1,35 nằm giữa, không đụng video thật.
PHANG = 1.35

#: 4 mức cho ô chọn trong Chỉnh mẫu. NHÃN KHÔNG DÙNG EMOJI — máy anh Hùng thiếu
#: glyph nên emoji ra Ô ĐEN ("xấu quá tự nhiên có cái ô đen", v2.6.22; cổng 9 và
#: 27 quét mọi nhãn nút để bắt việc này).
MUC: tuple = ("tat", "nhe", "vua", "manh")
MUC_NHAN: dict = {
    "tat": "Tắt (không hiệu ứng)",
    "nhe": "Nhẹ (mặc định — 1-2 điểm, rất kín)",
    "vua": "Vừa (tối đa 3 điểm, đậm hơn)",
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


def _chay_ffmpeg(cmd: list, giay: int, qua_cua_cho: bool = False) -> int:
    """Chạy 1 lệnh ffmpeg phụ (thử plugin / đo nhịp) — CÓ VÀO SỔ TIẾN TRÌNH.

    **VÌ SAO PHẢI VÀO SỔ (lỗi rà ra 08/08/2026):** 2 chỗ trong file này trước đây
    gọi thẳng `subprocess.run`, tức KHÔNG qua `ffmpeg_utils.register_proc` ->
    `terminate_all_children()` lúc đóng app **không giết nổi** -> tắt app để lại
    **ffmpeg mồ côi** chạy tiếp. `do_nhip` giải mã TOÀN BỘ clip (tới 2 lệnh khi
    video không tiếng) và `dung_duoc()` thử tới 11 module frei0r, nên cửa sổ rò
    không hề nhỏ.

    `qua_cua_cho`: XIN CHỖ trong cửa chờ ffmpeg trước khi chạy.
      · `do_nhip` PHẢI xin (True) — đo thật 10 làn: nó chạy SONG SONG với lệnh
        xuất nên đỉnh luồng vọt **45 -> 58**, và ở mức 'manh' có lúc **10 tiến
        trình** đo cùng lúc (78 luồng = 3,25x nhân), phá mốc "<= 2x nhân".
        An toàn vì `export_canvas_clip` gọi nó khi KHÔNG giữ chỗ nào (mỗi
        `_run_with_fallback` tự xin/trả chỗ trong 1 lệnh).
      · `_thu_module` thì KHÔNG (False): nó có thể bị gọi từ UI/từ trong lượt
        xuất đang giữ chỗ -> xin chỗ ở đó là TỰ KHOÁ. Nó cũng chỉ là 1 khung
        64x64, không đáng kể về luồng.
    Không bao giờ ném lỗi ra ngoài.
    """
    p = None
    cho = False
    if qua_cua_cho:
        try:
            from app.core import ffmpeg_utils as _fu0
            cho = bool(_fu0._xin_cho_ffmpeg())
        except Exception:  # noqa: BLE001 — cửa chờ hỏng không được chặn phép đo
            cho = False
    try:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            from app.core import ffmpeg_utils as _fu
            _fu.register_proc(p)
        except Exception:  # noqa: BLE001 - vào sổ hỏng không được làm vỡ phép đo
            pass
        p.communicate(timeout=giay)
        return int(p.returncode)
    except Exception:  # noqa: BLE001
        try:
            if p is not None:
                p.kill()
                p.communicate(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        return -1
    finally:
        if p is not None:
            try:
                from app.core import ffmpeg_utils as _fu
                _fu.unregister_proc(p)
            except Exception:  # noqa: BLE001
                pass
        if cho:
            try:
                from app.core import ffmpeg_utils as _fu1
                _fu1._tra_cho_ffmpeg()
            except Exception:  # noqa: BLE001
                pass


#: KHOÁ cho bước THỬ PLUGIN. Không có nó thì 10 làn cùng khởi động sẽ CÙNG LÚC
#: thử 11 module frei0r (mỗi module 1 lệnh ffmpeg) — các lệnh này CỐ Ý không qua
#: cửa chờ (xem `_chay_ffmpeg`) nên tổng luồng vọt lên. Cùng bệnh với
#: `hieu_ung_gpu._KHOA_DO`: cache chỉ cứu từ lần 2, không cứu cơn dồn lần đầu.
_KHOA_MOD = __import__("threading").Lock()


def _thu_module(ten: str) -> bool:
    if ten in _MOD_CACHE:
        return _MOD_CACHE[ten]
    with _KHOA_MOD:
        if ten in _MOD_CACHE:
            return _MOD_CACHE[ten]
        return _thu_module_that(ten)


def _thu_module_that(ten: str) -> bool:
    cmd = [_ffmpeg(), "-hide_banner", "-nostats", "-v", "error",
           "-f", "lavfi", "-i", "color=c=gray:s=64x64:d=0.04",
           "-vf", f"frei0r=filter_name={ten}", "-frames:v", "1",
           "-f", "null", os.devnull]
    ok = _chay_ffmpeg(cmd, 30) == 0
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
      {t1}{t2}-> mốc 1/3 và 2/3 cửa sổ (đếm ngược 3-2-1 — xem LỖI 4 dưới)
    """
    khoa: str
    ten: str                    # tên TIẾNG VIỆT cho anh Hùng
    capcut: str                 # tên trong bảng Effects của CapCut
    nhom: str                   # "thuan" | "frei0r" | "shader"
    mau: str
    module: str = ""            # module frei0r cần (rỗng = filter thuần ffmpeg)
    #: file `.hook` trong `app/assets/hieu_ung/shaders/` (nhóm "shader" mới).
    #: Có giá trị = hiệu ứng chạy trên GPU qua `libplacebo`, cần Vulkan.
    shader: str = ""
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
              fps: float = 30, font: str = "", i: int = 0) -> str:
        d = max(0.0, min(DAM_MAX, float(dam))) / DAM_MAX      # 0..1
        s = self.mau
        # `{i}` = SỐ THỨ TỰ hiệu ứng trong clip -> tên nhãn `[q0a]`, `[q1a]`…
        # KHÔNG có nó thì 2 hiệu ứng shader trong cùng 1 clip dùng TRÙNG nhãn và
        # ffmpeg báo "Duplicate output pad" rồi chết cả lượt xuất.
        s = s.replace("{i}", str(int(i)))
        if self.shader:
            from app.core import hieu_ung_gpu as _HG
            s = s.replace("{SH}", _HG.duong_filter(_HG.duong_shader(self.shader)))
        for i, (lo, hi) in enumerate(self.ts, start=1):
            s = s.replace("{p%d}" % i, f"{lo + (hi - lo) * d:g}")
        # LỖI 4 (rà ra 08/08/2026): mốc chia cửa sổ phải TÍNH THEO cửa sổ, không
        # gắn cứng 0,30/0,60. Cửa sổ co theo `vspeed` (clip tua nhanh/chậm), nên
        # `{a}+0.60` với cửa sổ 0,56s ra `between(t,0.60,0.56)` — bắt đầu SAU khi
        # kết thúc => số "1" KHÔNG BAO GIỜ HIỆN mà ffmpeg vẫn rc=0.
        t1, t2 = a + (b - a) / 3.0, a + (b - a) * 2.0 / 3.0
        s = (s.replace("{en}", f":enable='between(t,{a:.3f},{b:.3f})'")
              .replace("{a}", f"{a:.3f}").replace("{b}", f"{b:.3f}")
              .replace("{t1}", f"{t1:.3f}").replace("{t2}", f"{t2:.3f}")
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


#: Khuôn filter cho nhóm **SHADER GPU** (`libplacebo` + `.hook` tự viết).
#:
#: === VÌ SAO PHẢI CẮT MẢNH CHỨ KHÔNG DÙNG `enable` ===
#: `libplacebo` **KHÔNG có timeline `enable`** (`ffmpeg -h filter=libplacebo`
#: không in dòng "supports timeline") -> áp là áp TOÀN CLIP, trái luật 1. Đây
#: đúng là lý do 6 shader nằm không từ 08/08/2026.
#:
#: 2 CÁCH VÒNG QUA, ĐÃ ĐO CẢ HAI TRÊN CLIP THẬT 24s/1080x1920/722 khung:
#:   (C) `split` -> nhánh shader chạy CẢ CLIP -> `overlay` CÓ `enable`.
#:       Cổng thời gian ĐÚNG (đo: ngoài cửa sổ 0,00% pixel lệch) nhưng
#:       **2,18x wall · 1,41x CPU-giây** — mọi khung đều phải lên/xuống GPU cho
#:       0,45 giây hiệu ứng. **LOẠI**: mặc định đang 1,98x, không được đắt thêm.
#:   (D) cắt ĐÚNG cửa sổ bằng `trim`, CHỈ mảnh đó lên GPU, `concat` nối lại.
#:       **1,16x wall · 1,01x CPU-giây** (CPU-giây mới là cái đắt khi 10 làn
#:       chạy cùng lúc — phần dư 0,16x là phí MỞ THIẾT BỊ Vulkan, cố định
#:       ~0,4 giây/lệnh chứ không theo độ dài clip). **CHỌN CÁCH NÀY.**
#:       Cùng kiến trúc "cắt mảnh rồi concat" mà `_tach_va_noi_manh` đã dùng.
#:
#: BẤT BIẾN ĐÃ ĐO (đừng đổi khuôn mà không đo lại): số khung RA = số khung VÀO
#: (722/722) và độ dài **24,066667s y hệt** — `trim` + `setpts=PTS-STARTPTS` +
#: `concat` giữ nguyên mốc, nên `.ass` và mốc tiếng động KHÔNG phải sửa.
#: Ca `bat=0` (cửa sổ ở NGAY ĐẦU clip) làm mảnh đầu RỖNG — đã đo riêng: vẫn
#: 722 khung, `concat` bỏ qua nhánh rỗng, KHÔNG treo.
#:
#: `{p1}` = alpha 0..1 = ĐỘ ĐẬM (luật 2). Shader viết cứng cường độ trong file
#: `.hook`, không có núm; `colorchannelmixer=aa` là núm duy nhất — và nó đủ:
#: đo `tuong_phan` ở aa 0,60 / 0,80 / 1,00 ra 0,38% / 6,59% / 17,62% pixel đổi.
_SH_MAU = (
    "split=3[q{i}a][q{i}b][q{i}c];"
    "[q{i}a]trim=end={a},setpts=PTS-STARTPTS[q{i}d];"
    "[q{i}b]trim=start={a}:end={b},setpts=PTS-STARTPTS,"
    "hwupload,libplacebo=custom_shader_path='{SH}',"
    "hwdownload,format=yuv420p,format=yuva420p,"
    "colorchannelmixer=aa={p1},format=yuv420p[q{i}e];"
    "[q{i}c]trim=start={b},setpts=PTS-STARTPTS[q{i}f];"
    "[q{i}d][q{i}e][q{i}f]concat=n=3:v=1:a=0"
)


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
    ":enable='between(t,{a},{t1})',"
    "drawtext=fontfile='{FONT}':text='2':fontsize=h/3.2:fontcolor=white@{p1}:"
    "borderw=4:bordercolor=black@{p1}:x=(w-text_w)/2:y=(h-text_h)/2"
    ":enable='between(t,{t1},{t2})',"
    "drawtext=fontfile='{FONT}':text='1':fontsize=h/3.2:fontcolor=white@{p1}:"
    "borderw=4:bordercolor=black@{p1}:x=(w-text_w)/2:y=(h-text_h)/2"
    ":enable='between(t,{t2},{b})'",
    ts=((0.55, 0.95), ), dai=0.80, hop=("noi",), can_font=True,
    nguong_thay=2.0, nguong_manh=0.8))

# ---- NHÓM 5: SHADER GLSL CHẠY TRÊN **GPU** (`libplacebo` + Vulkan) ----
# 6 file `.hook` TỰ VIẾT nằm sẵn trong `app/assets/hieu_ung/shaders/` từ
# 08/08/2026 nhưng **CHƯA nối vào đường xuất** (hồ sơ ghi rõ: `libplacebo`
# không có timeline `enable`). Nay nối được nhờ khuôn `_SH_MAU` ở trên.
#
# SỐ ĐO (clip THẬT 1080x1920, cửa sổ [1,00 · 1,50], `aa` = 0,60/0,80/1,00 —
# xem `_do_shader.py`). Cột "%pixel" = % pixel |dY|>12 GIỮA cửa sổ; dU/dV là
# lệch màu trung bình (luật 3: phải < 3,0):
#   hat_phim    22,37 / 39,42 / 50,81 %   dU -0,15..-0,08  dV -0,34..-0,24
#   mo_net       6,44 /  9,10 / 11,51 %   dU -0,11..-0,10  dV -0,32..-0,27
#   net_hon      7,34 / 10,16 / 12,58 %   dU -0,05.. 0,01  dV -0,35..-0,29
#   quang_sang  18,31 / 21,87 / 22,99 %   dU -1,31..-0,80  dV -0,91..-0,58
#   toi_vien    18,92 / 23,73 / 27,55 %   dU  0,16.. 0,30  dV -0,49..-0,37
#   tuong_phan   0,38 /  6,59 / 17,62 %   dU -0,99..-0,61  dV -0,13..-0,05
# -> `ts` (dải alpha) dưới đây chọn theo BẢNG NÀY: mức 'nhe' (dam 0,12 -> d
# 0,48) vẫn phải vượt `nguong_thay` = 8%, mức 'manh' (d 1,0) không được quá
# tay. `tuong_phan` dốc nhất nên dải hẹp 0,80-1,00; `hat_phim` mạnh nhất nên
# dải thấp 0,45-0,70.
# NGOÀI cửa sổ đo được **0,00% pixel lệch · PSNR 53,69 dB** ở CẢ 18 lượt ->
# KHÔNG rò ra ngoài điểm nhấn (luật 1).
# ĐỐI CHỨNG BẮT BUỘC: `libplacebo` KHÔNG shader vs gốc = PSNR 52,23 dB,
# dU -0,03 dV -0,03, 0,0% pixel -> bản thân `libplacebo` KHÔNG đổi màu, nên
# mọi con số trên là của SHADER chứ không phải của cái ống dẫn.
_dk(HieuUng(
    "sh_net_hon", "Nét gắt (GPU)", "Sharpen", "shader", _SH_MAU,
    shader="net_hon.hook", ts=((0.75, 1.00), ), dai=0.35,
    hop=("caotrao", "dong"), doi_cho=True,
    ghi_chu="KHÔNG có bản CPU: `unsharp` đã bị loại vì ở trần 5,0 chỉ đổi "
            "6,3% pixel. Bản shader đo 12,58% -> THẤY ĐƯỢC."))
_dk(HieuUng(
    "sh_hat_phim", "Hạt phim (GPU)", "Film Grain", "shader", _SH_MAU,
    shader="hat_phim.hook", ts=((0.45, 0.70), ), dai=0.60,
    hop=("ke", "tinh")))
_dk(HieuUng(
    "sh_quang_sang", "Quầng sáng phim (GPU)", "Film Radiance", "shader",
    _SH_MAU, shader="quang_sang.hook", ts=((0.55, 0.95), ), dai=0.60,
    hop=("ke", "chot", "tinh")))
_dk(HieuUng(
    "sh_toi_vien", "Tối viền ống kính (GPU)", "Vignette", "shader", _SH_MAU,
    shader="toi_vien.hook", ts=((0.50, 0.90), ), dai=0.70,
    hop=("ke", "tinh", "chot")))
_dk(HieuUng(
    "sh_mo_net", "Mờ nét nhanh (GPU)", "Focus Pull", "shader", _SH_MAU,
    shader="mo_net.hook", ts=((0.75, 1.00), ), dai=0.35,
    hop=("noi", "chot"), doi_cho=True))
_dk(HieuUng(
    "sh_tuong_phan", "Tăng tương phản (GPU)", "Contrast Punch", "shader",
    _SH_MAU, shader="tuong_phan.hook", ts=((0.80, 1.00), ), dai=0.40,
    hop=("caotrao", "ke")))


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


def co_shader() -> bool:
    """Máy này chạy được nhóm SHADER GPU hay không — KHÔNG BAO GIỜ ném lỗi.

    3 cửa, thiếu bất cứ cái nào là nhóm shader TỰ TẮT và app chạy y như cũ:
      1. `BQ_SHADER=0` — công tắc tay để anh Hùng/tôi tắt nhóm này khi gỡ rối
         mà không phải sửa mã (cùng kiểu `BQ_XFADE_NOI_CA_CLIP`).
      2. `hieu_ung_gpu.co_libplacebo()` — nó RENDER THẬT rồi **ĐẾM KHUNG**, chứ
         không chỉ hỏi "ffmpeg có filter không". Máy nhân viên không có Vulkan
         -> False.
      3. còn file `.hook` trên đĩa (bản đóng gói thiếu tài nguyên -> tự bỏ).
    Kết quả của (2) đã được `hieu_ung_gpu` cache sẵn nên gọi nhiều lần không tốn.
    """
    if str(os.environ.get("BQ_SHADER", "")).strip() == "0":
        return False
    try:
        from app.core import hieu_ung_gpu as _HG
        return bool(_HG.co_libplacebo())
    except Exception:  # noqa: BLE001 — thiếu module không được chặn lượt xuất
        return False


def dung_duoc(co_font: bool = True) -> list[str]:
    """Khoá các hiệu ứng CHẠY ĐƯỢC trên máy này (đã kiểm frei0r/Vulkan thật)."""
    ra = []
    sh_ok = None
    for k, h in KHO.items():
        if h.can_font and not co_font:
            continue
        if h.module and not module_co(h.module):
            continue
        if h.shader:
            # hỏi Vulkan ĐÚNG 1 LẦN cho cả vòng (mỗi lần dò là 1 lệnh ffmpeg)
            if sh_ok is None:
                sh_ok = co_shader()
            if not sh_ok or not _co_file_shader(h.shader):
                continue
        ra.append(k)
    return ra


def _co_file_shader(ten: str) -> bool:
    try:
        from app.core import hieu_ung_gpu as _HG
        return bool(_HG.duong_shader(ten))
    except Exception:  # noqa: BLE001
        return False


def can_vulkan(chon: list) -> bool:
    """Bộ hiệu ứng đã chọn CÓ cần mở thiết bị Vulkan hay không.

    Caller (`ffmpeg_utils`) phải hỏi hàm này để quyết định có thêm
    `-init_hw_device vulkan=vk -filter_hw_device vk` vào lệnh hay không.
    **Chỉ thêm khi THẬT SỰ cần** — đó là cách giữ BẤT BIẾN SỐNG CÒN: mức "tat"
    (và mọi bộ chọn không có shader) ra lệnh ffmpeg KHÔNG khác một ký tự nào so
    với bản cũ, nên file xuất ra giống hệt.
    """
    for c in chon or []:
        h = KHO.get(str(c.get("khoa", "")))
        if h is not None and h.shader:
            return True
    return False


def bo_shader(chon: list) -> list:
    """Bỏ các hiệu ứng nhóm shader khỏi bộ đã chọn (dùng khi GPU lỗi giữa chừng).

    `ffmpeg_utils` gọi hàm này để LÙI ÊM: lượt xuất có shader mà ffmpeg chết
    (driver Vulkan hỏng, GPU đang bận, máy ảo…) thì xuất LẠI bằng đúng bộ hiệu
    ứng đó trừ shader, thay vì để cả clip FAIL. Cùng cách `_tach_va_noi_manh`
    lùi từ GPU về CPU.
    """
    return [c for c in (chon or [])
            if not getattr(KHO.get(str(c.get("khoa", ""))), "shader", "")]


def thong_ke() -> dict:
    """Đếm hiệu ứng theo nhóm (cho báo cáo/UI)."""
    dd = set(dung_duoc())
    return {
        "tong_kho": len(KHO),
        "dung_duoc": len(dd),
        "thuan": sum(1 for k in dd if KHO[k].nhom == "thuan"),
        "frei0r": sum(1 for k in dd if KHO[k].nhom == "frei0r"),
        "shader": sum(1 for k in dd if KHO[k].nhom == "shader"),
        "co_frei0r": co_frei0r(),
        "co_shader": co_shader(),
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


def dai_dong(xs: list) -> float:
    """DẢI ĐỘNG của 1 dãy số đo = đỉnh / trung vị. 1,0 = phẳng tuyệt đối.

    Dùng để trả lời câu hỏi "clip này CÓ cao trào không". Ngưỡng cứng kiểu
    "RMS > 0,5" thì video êm không bao giờ có cao trào còn video ồn thì chỗ nào
    cũng cao trào — bài học đã ghi ở `loai_diem`.
    """
    ys = [float(x) for x in (xs or []) if x is not None]
    if len(ys) < 3:
        return 0.0
    tv = _tv(ys)
    return (max(ys) / tv) if tv > 1e-9 else 0.0


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

    # ---- LUẬT "KHÔNG THÊM GÌ Ở ĐOẠN PHẲNG" (anh Hùng: "cái nào cần thì hiện
    # thôi"). Clip đọc đều, không va chạm -> dải động ~1,0: mọi giây đều như
    # nhau nên KHÔNG có giây nào đáng gọi là điểm nhấn. Vẫn cho phép điểm ở CHỖ
    # NỐI (đó là điểm nhấn về CẤU TRÚC, không cần cao trào để biện minh).
    dd_nl, dd_cd = dai_dong(nl), dai_dong(cd)
    phang = bool(nl or cd) and dd_nl < PHANG and dd_cd < PHANG

    # trần TỔNG số giây có hiệu ứng (luật 5)
    ngan_sach = float(tong_giay) * TY_LE_MAX
    ra: list[dict] = []
    da_dung: list[str] = []
    da_dung_loai: list[str] = []
    for g in uv:
        if len(ra) >= n_diem or ngan_sach < DAI_MIN:
            break
        g = int(max(0, min(int(float(tong_giay)) - 1, g)))
        if any(abs(g - r["bat"]) < CACH_MIN for r in ra):
            continue
        loai = loai_diem(g, nl, cd, moc, float(tong_giay))
        # PHẲNG -> CHỈ nhận điểm ở CHỖ NỐI. Chỗ nối là sự kiện CÓ THẬT (app vừa
        # cắt ghép ở đó); còn "chot" chỉ suy từ VỊ TRÍ (3 giây cuối) nên nó
        # không phải bằng chứng gì — clip đọc đều mà vẫn nháy ở cuối là đúng
        # kiểu "thêm vào ngớ ngẩn" anh Hùng chê.
        if phang and loai != "noi":
            continue
        chon = _chon_kieu(loai, dung, da_dung, len(ra))
        if not chon:
            continue
        h = KHO[chon]
        dai = max(DAI_MIN, min(DAI_MAX, h.dai))
        bat = float(g)
        het = min(float(tong_giay) - 0.05, bat + dai)
        if het - bat < DAI_MIN or (het - bat) > ngan_sach + 1e-6:
            continue
        ra.append({"bat": round(bat, 3), "het": round(het, 3), "khoa": chon,
                   "dam": dam, "loai": loai,
                   "vi_sao": _vi_sao(chon, loai, g, nl, cd, moc,
                                     float(tong_giay))})
        ngan_sach -= (het - bat)
        da_dung.append(chon)
        da_dung_loai.append(loai)
    ra.sort(key=lambda r: r["bat"])
    return ra


def ty_le_co_hieu_ung(chon: list, tong_giay: float) -> float:
    """% thời lượng clip CÓ hiệu ứng (luật 5: phải <= 10%). Dùng cho ghi chú."""
    if not chon or float(tong_giay or 0) <= 0:
        return 0.0
    return sum(float(c["het"]) - float(c["bat"])
               for c in chon) / float(tong_giay) * 100.0


def loc_theo_font(chon: list, co_font: bool) -> list:
    """Bỏ các hiệu ứng CẦN FONT khi máy không có font — LỖI 5.

    `chuoi_filter` vẫn tự bỏ chúng khi dựng chuỗi, nhưng nếu caller ghi nhật ký
    TRƯỚC bước đó thì nhật ký khoe hiệu ứng **không hề tồn tại trong file**, và
    hiệu ứng bị bỏ đã ĂN MẤT 1 suất trong tối đa 3 điểm nhấn. Lọc TẠI ĐÂY để
    nhật ký và file luôn khớp nhau.
    """
    if co_font:
        return list(chon or [])
    return [c for c in (chon or [])
            if not getattr(KHO.get(str(c.get("khoa", ""))), "can_font", False)]


#: Ứng viên theo LOẠI điểm — thứ tự = ưu tiên. Cảnh TĨNH chỉ có mood.
#:
#: NHÓM SHADER GPU (`sh_*`) ĐẶT Ở ĐÂU VÀ VÌ SAO: `_chon_kieu` lấy
#: `moi[i % len(moi)]` với `i` = số điểm ĐÃ chọn (0,1,2) -> chỉ 3 vị trí ĐẦU
#: của danh sách CÒN LẠI là tới được. Đặt shader ở CUỐI danh sách = nối vào cho
#: có, máy nào có frei0r thì KHÔNG BAO GIỜ dùng tới (đúng cái bẫy "đóng gói rồi
#: mà chưa nối"). Vì vậy đặt ở **vị trí 2-3**: điểm nhấn ĐẦU TIÊN vẫn giữ
#: nguyên kiểu cũ, các điểm sau mới có cơ hội ra shader.
#: Cái được ở máy NHÂN VIÊN (không frei0r) còn lớn hơn: danh sách "tinh" vốn
#: 7 kiểu thì 5 là frei0r -> chỉ còn 2, mà 1 clip tối đa 3 điểm và CẤM lặp kiểu
#: -> điểm thứ 3 bị BỎ. Thêm 4 shader vào là "tinh" có 6 kiểu chạy được.
_UV_THEO_LOAI: dict = {
    "caotrao": ("zoom_nhoi", "rung_lac", "sh_net_hon", "loe_sang",
                "nhay_sang", "tuong_phan", "meo_kinh", "sh_tuong_phan"),
    "dong": ("glitch_khoi", "o_vuong", "sh_net_hon", "xao_dong", "lech_bang",
             "vien_net", "dong_quet", "song_meo"),
    "tinh": ("quang_sang", "hat_phim", "sh_toi_vien", "toi_vien", "sang_diu",
             "sh_hat_phim", "nhieu_analog", "hat_nhieu", "vien_phim",
             "sh_quang_sang"),
    "chot": ("sup_toi", "nhay_sang", "sh_toi_vien", "toi_vien", "quang_sang",
             "zoom_nhoi", "vien_phim", "sh_mo_net"),
    "noi": ("mo_net", "loe_sang", "sh_mo_net", "o_vuong", "mo_vuong",
            "lech_bang", "zoom_nhoi", "dem_nguoc"),
    "ke": ("quang_sang", "hat_phim", "sh_hat_phim", "nhieu_analog",
           "dong_quet", "toi_vien", "zoom_day", "hat_nhieu", "tuong_phan",
           "sh_quang_sang", "sh_tuong_phan"),
}


def _chon_kieu(loai: str, dung: list, da_dung: list, i: int) -> str:
    """Kiểu cho loại điểm này — TUYỆT ĐỐI không lặp kiểu đã dùng trong clip.

    Trước đây hết kiểu mới thì QUAY LẠI dùng kiểu cũ (`uv[i % len(uv)]`) -> một
    clip có thể ra 2 điểm CÙNG một hiệu ứng, đúng cái anh Hùng chê ở tiếng động
    ("mọi Part một tiếng ding"). Nay hết kiểu mới thì BỎ điểm đó — thà ít điểm
    hơn là lặp.
    """
    uv = [k for k in _UV_THEO_LOAI.get(loai, ()) if k in dung]
    moi = [k for k in uv if k not in da_dung]
    if not moi:
        return ""
    # xoay theo chỉ số điểm -> 2 clip khác nhau không ra y hệt một bộ
    return moi[i % len(moi)]


_LOAI_NHAN = {"caotrao": "cao trào (tiếng vọt lên)",
              "dong": "cảnh động mạnh", "tinh": "cảnh tĩnh",
              "chot": "câu chốt cuối clip", "noi": "chỗ ghép đoạn",
              "ke": "đang kể đều"}


def _so(x: float, n: int = 2) -> str:
    """Số kiểu VIỆT NAM (dấu phẩy thập phân) — anh Hùng đọc bảng ghi chú."""
    return f"{x:.{n}f}".replace(".", ",")


#: Dưới mức này thì TRUNG VỊ coi như bằng 0 — chia cho nó là ra số vô nghĩa.
_TV_TOI_THIEU = 1e-6


def _so_lan(x: float, tv: float) -> str:
    """`N,Nx trung vị` — CHỈ khi trung vị CÓ NGHĨA, không thì nói thẳng "nền ~0".

    LỖI THẬT (lượt kiểm ĐỘC LẬP 08/08/2026, lôi ra từ NHẬT KÝ DÂY CHUYỀN của
    `_test_pipe_integ` chạy trên video THẬT — không phải giả định):

        giây 14,0 · Xáo dòng ngang · cảnh động mạnh —
        RMS 0,05 = **49274701,3x trung vị**; động 10,0/10 = 513,9x trung vị

    Nguyên nhân: `tv = _tv(nl) or 1e-9`. Khi **hơn NỬA số giây im lặng** — video
    KHÔNG TIẾNG, hoặc clip có khoảng lặng dài (phỏng vấn / vlog Nhật rất hay
    gặp) — trung vị RMS ra **đúng 0,0**, `or` thay bằng `1e-9`, và
    0,05 / 1e-9 = 50 triệu.

    Vì sao KHÔNG phải chuyện nhỏ: dòng này là **bằng chứng DUY NHẤT anh Hùng đọc
    được** để tin "AI chọn có căn cứ SỐ" (anh chốt 07/08/2026: *"AI chọn sao phù
    hợp nhé"*, cấm ghi chung chung). Một con số 49 triệu lần làm hỏng cả dòng —
    người đọc chỉ thấy app tính sai.

    Sửa CHỈ Ở CHỖ IN RA: `chon_hieu_ung`/`loai_diem` KHÔNG đổi một dòng nào. Đã
    đo 4 ca biên (cảnh tĩnh đều · tĩnh + 1 giây động · >50% giây im · video
    không tiếng): loại điểm chọn ra vẫn ĐÚNG, chỉ dòng chữ là sai.
    """
    if tv <= _TV_TOI_THIEU:
        return "nền ~0"
    return f"{_so(x / tv, 1)}x trung vị"


def _vi_sao(khoa: str, loai: str, g: int, nl: list, cd: list, moc: list,
            tong: float) -> str:
    """Dòng LÝ DO KÈM SỐ. Cấm ghi chung chung kiểu "cảnh hay" (anh Hùng chốt).

    Khuôn: `giây 41,2 · zoom nhồi · cao trào — RMS 0,82 = 4,0x trung vị;
    động 7,4/10`. Mọi con số ở đây đọc từ chính clip đang xuất, không phải
    hằng số bịa.
    """
    h = KHO.get(khoa)
    ch = []
    if nl and g < len(nl):
        # `_so_lan`: trung vị ~0 (hơn nửa số giây im lặng) thì KHÔNG bịa tỉ lệ.
        # Xem docstring `_so_lan` — con số 49.274.701,3x đo được từ nhật ký THẬT.
        ch.append(f"RMS {_so(nl[g])} = {_so_lan(nl[g], _tv(nl))}")
    if cd and g < len(cd):
        ch.append(f"động {_so(cd[g] * 10, 1)}/10 = {_so_lan(cd[g], _tv(cd))}")
    if loai == "noi" and moc:
        gan = min(moc, key=lambda x: abs(x - g))
        ch.append(f"sát mốc ghép {_so(gan, 1)}s")
    if loai == "chot":
        ch.append(f"cách hết clip {_so(max(0.0, tong - g), 1)}s")
    return (f"giây {_so(float(g), 1)} · {h.ten if h else khoa} · "
            f"{_LOAI_NHAN.get(loai, loai)}"
            + (" — " + "; ".join(ch) if ch else ""))


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
        # thiếu file `.hook` (bản đóng gói hụt tài nguyên) -> BỎ hiệu ứng đó,
        # KHÔNG dựng chuỗi có `custom_shader_path=''` rồi để ffmpeg chết cả lượt
        if h.shader and not _co_file_shader(h.shader):
            continue
        # `len(out)` chứ không phải chỉ số vòng lặp: nhãn phải đánh theo hiệu
        # ứng THỰC SỰ được dựng, nếu không 2 shader có thể nhận cùng một số khi
        # có hiệu ứng bị bỏ ở giữa -> "Duplicate output pad" -> chết lượt xuất.
        out.append(h.chuoi(float(c.get("dam", MUC_DAM["vua"])),
                           float(c["bat"]), float(c["het"]), W, H, fps, font,
                           i=len(out)))
    return ",".join(out)


def bang_ghi_chu(chon: list, tong_giay: float = 0.0) -> str:
    """Bảng 'giây thứ mấy -> hiệu ứng gì -> VÌ SAO (số)' cho anh Hùng đọc.

    Có `tong_giay` thì in thêm dòng TỈ LỆ % thời lượng có hiệu ứng — con số anh
    Hùng yêu cầu để tự kiểm "không loè" (trần 10%).
    """
    if not chon:
        return "(không có hiệu ứng nào — clip phẳng hoặc mức Tắt)"
    d = ["giây          | hiệu ứng                  | CapCut            | VÌ SAO (số đo của chính clip này)",
         "-" * 128]
    for c in chon:
        h = KHO.get(c["khoa"])
        d.append(f"{c['bat']:6.2f}-{c['het']:6.2f} | "
                 f"{(h.ten if h else c['khoa']):<25} "
                 f"| {(h.capcut if h else ''):<17} | {c.get('vi_sao', '')}")
    tong_hu = sum(float(c["het"]) - float(c["bat"]) for c in chon)
    if tong_giay and float(tong_giay) > 0:
        d.append("-" * 128)
        d.append(f"clip {_so(float(tong_giay))}s · tổng giây CÓ hiệu ứng "
                 f"{_so(tong_hu)}s · tỉ lệ "
                 f"{_so(ty_le_co_hieu_ung(chon, tong_giay), 1)}% "
                 f"(trần {int(TY_LE_MAX * 100)}%)")
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
        # SIẾT LUỒNG CHO LỆNH ĐO (đo thật 08/08/2026, 10 làn): lệnh này **CỐ Ý
        # KHÔNG qua cửa chờ ffmpeg** (xem `_chay_ffmpeg`) nên 10 làn có thể sinh
        # nhiều lệnh đo CÙNG LÚC. Để mặc định `-threads 0` thì mỗi lệnh ăn ~17
        # luồng giải mã + luồng filter -> tổng luồng ffmpeg vọt lên **115
        # (4,79x số nhân)**, phá mốc "<= 2x nhân". Việc ở đây bé tí (fps=4,
        # rộng 160 px) nên 1 luồng là đủ, KHÔNG chậm đi.
        cmd = [ff, "-y", "-hide_banner", "-nostats", "-v", "error",
               "-threads", "1", "-filter_threads", "1",
               "-filter_complex_threads", "1",
               *vao, "-filter_complex", graph, *maps,
               "-f", "null", os.devnull]
        # `_chay_ffmpeg`: VÀO SỔ tiến trình để đóng app giết được (xem docstring
        # của nó). Lệnh này giải mã CẢ clip nên là chỗ rò ffmpeg mồ côi nặng nhất.
        if _chay_ffmpeg(cmd, 600, qua_cua_cho=True) == 0:
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
