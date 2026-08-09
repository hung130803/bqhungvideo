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
#: SỐ ĐO NHỊP phải phủ ít nhất bấy nhiêu phần thời lượng mới được coi là "ĐO
#: ĐƯỢC" (xem `do_du`). Cái phanh cho lỗi ÂM THẦM "đo cụt -> 0 điểm nhấn".
DO_PHU_TOI_THIEU = 0.70

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
        # `{d}` = ĐỘ DÀI cửa sổ. Nhóm LỚP PHỦ cần nó vì lớp hạt là một NGUỒN
        # ffmpeg riêng (`color=…:d=…`) chứ không phải filter chạy trên hình —
        # nguồn phải biết mình sống bao lâu, và biểu thức bao hình sin trong
        # `geq` tính theo `T/d` (T của nguồn bắt đầu lại từ 0 sau `trim`).
        s = (s.replace("{en}", f":enable='between(t,{a:.3f},{b:.3f})'")
              .replace("{d}", f"{max(0.05, b - a):.3f}")
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


#: === KHUÔN "ÊM VÀO — ÊM RA" (nửa hình sin trong cửa sổ) ===
#: `enable=` bật/tắt filter PHÁT MỘT: khung 59 chưa có gì, khung 60 đã đủ biên
#: độ. Đo thật 08/08/2026 trên clip của anh Hùng (1080x1920, 30 fps): đúng khung
#: bật và khung tắt có 1 khung lệch **> 45% độ sáng** so với khung liền trước —
#: mắt thấy là "cụp một cái rồi hiện lại", đúng cái anh Hùng chê *"hiệu ứng lỏ
#: quá"*. Nhân biên độ với `_SONG` thì ở HAI MÉP cửa sổ biên độ = 0 nên khung
#: đầu/cuối GIỐNG HỆT bản không hiệu ứng (đo `vignette=a='0'` -> **0,00% pixel
#: đổi**), giữa cửa sổ mới đạt đỉnh. Cùng cách các bộ dựng chuyên nghiệp làm
#: (ease-in/ease-out), và nó cũng chính là thứ cho phép hạ "độ đậm cảm nhận"
#: mà KHÔNG hạ độ đậm đỉnh — tức không phải nới trần `DAM_MAX`.
#: BẮT BUỘC đi kèm `eval=frame`: thiếu nó `eq`/`vignette` chỉ tính biểu thức 1
#: LẦN lúc init -> đo ra 0,0% pixel đổi mà ffmpeg vẫn mã 0 (bẫy cũ của
#: `nhay_sang`).
_SONG = "sin(3.14159*(t-{a})/({b}-{a}))"


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
    # ÊM VÀO ÊM RA (xem `_SONG`): bản cũ `brightness={p1}` bật phát một -> khung
    # bật lệch 99,99% pixel so với khung liền trước. Nay biên độ chạy theo nửa
    # hình sin: mép cửa sổ = ảnh gốc, giữa cửa sổ mới loé đủ.
    # `{p2}` nay là ĐỘ CỘNG THÊM của contrast (cũ là giá trị tuyệt đối 1,02-1,10)
    # để nhân được với sóng — 1 + p2*sóng.
    "eq=brightness='{p1}*" + _SONG + "':contrast='1+{p2}*" + _SONG +
    "':eval=frame{en}",
    ts=((0.10, 0.26), (0.02, 0.10)), dai=0.30,
    hop=("caotrao", "noi", "chot")))
_dk(HieuUng(
    "sup_toi", "Sụp tối", "Flicker Blackout", "thuan",
    # ===== LỖI THẬT anh Hùng XEM CLIP THẤY 08/08/2026 =====
    # *"ví dụ zoom nhồi gì đó thấy nó TỐI ĐEN không thấy gì rồi lại hiện"*.
    # Bản cũ `eq=brightness=-{p1}` là phép TRỪ THẲNG trên thang 0..1: cảnh có độ
    # sáng trung bình 0,27 (đo thật 69/255) trừ 0,34 ra **ÂM** -> ffmpeg kẹp về
    # 0 = **KHUNG ĐEN TUYỆT ĐỐI**. Đo trên clip thật: khung ngay mốc bật
    # YAVG = **0,0/255**, rồi 18 khung tiếp theo chỉ **17,7/255** trong khi bản
    # gốc là 96,8 (= **18%**) — tức 0,6 giây MẤT HÌNH. Ở mức "nhẹ" (dam 0,12)
    # vẫn ra 10/255, vẫn là mất hình. Đây là LỖI, không phải thẩm mỹ.
    # ĐÚNG: nhân (không phải trừ). `eq` tính out = (in-0,5)*contrast + 0,5 +
    # brightness, nên đặt contrast = k và brightness = 0,5*(k-1) cho ra ĐÚNG
    # out = k*in — tối đi theo TỈ LỆ nên cảnh tối cỡ nào cũng KHÔNG về 0.
    # k = 1 - p1*sóng: mép cửa sổ k=1 (ảnh gốc), giữa cửa sổ k thấp nhất 0,45.
    # Đo lại: thấp nhất 41/93 = 44% độ sáng gốc, KHÔNG khung nào đen.
    "eq=contrast='1-{p1}*" + _SONG + "':brightness='-0.5*{p1}*" + _SONG +
    "':eval=frame{en}",
    ts=((0.30, 0.55), ), dai=0.35, hop=("chot", "noi")))
_dk(HieuUng(
    "nhay_sang", "Nháy sáng liên tục", "Flickery Shots", "thuan",
    # eval=frame BẮT BUỘC: mặc định `eq` chỉ tính biểu thức 1 LẦN lúc init ->
    # đo thật ra 0,0% pixel đổi (hiệu ứng KHÔNG xảy ra) mà ffmpeg vẫn mã 0.
    # 2 SỬA 08/08/2026: (a) `sin` chạy CẢ ÂM nên nửa số nháy là nháy **TỐI** —
    # đo thấp nhất 38/97 = 39% độ sáng gốc, góp phần vào cảm giác "tối đen";
    # nay `abs(sin(...))` -> chỉ nháy SÁNG. (b) nhân `_SONG` để vào/ra êm và
    # mốc pha tính từ `{a}` chứ không từ `t=0` (mốc tuyệt đối làm pha nháy phụ
    # thuộc chỗ đặt điểm nhấn -> khung bật có thể rơi đúng đỉnh = giật).
    "eq=brightness='{p1}*abs(sin(3.14159*9*(t-{a})))*" + _SONG +
    "':eval=frame{en}",
    ts=((0.10, 0.24), ), dai=0.50, hop=("caotrao", "chot")))
# ĐÃ BỎ "Nét gắt" (`unsharp`): đo ở trần 5,0 (biên độ tối đa của filter) vẫn
# chỉ 6,3% pixel đổi -> anh Hùng KHÔNG THẤY. Làm nét là chỉnh màu, không phải
# hiệu ứng. Đừng thêm lại mà không đo.
_dk(HieuUng(
    "tuong_phan", "Tăng tương phản", "Contrast Punch", "thuan",
    # ÊM VÀO ÊM RA — `{p1}` nay là ĐỘ CỘNG THÊM (cũ là contrast tuyệt đối
    # 1,18-1,55, không nhân được với sóng). 1 + p1*sóng, đỉnh 1,55 y như cũ.
    "eq=contrast='1+{p1}*" + _SONG + "':saturation=1.0:eval=frame{en}",
    ts=((0.18, 0.55), ), dai=0.40, hop=("caotrao", "ke")))

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
# ĐÃ GỠ "Sáng dịu vùng chói" (frei0r `softglow`) — 08/08/2026, ĐO TRÊN CLIP THẬT:
# tên là "sáng dịu" nhưng nó LÀM TỐI. Độ sáng trung bình cửa sổ tụt còn **29-33%**
# bản gốc (19,8/69,3) và khung ngay mốc bật là một cú **TỐI SÂU** — đúng loại
# "tối đen rồi lại hiện" anh Hùng chê. Đã quét tham số (`0.45|0.55`, `0.45|0.90`,
# `0.20|0.55`): CẢ BA đều tối như nhau -> không phải chỉnh sai, là plugin làm vậy.
# "Quầng sáng phim" (`quang_sang`, frei0r `glow`) mới là kiểu SÁNG thật: đo
# 142,3/96,8 = sáng hơn gốc, 98,22% pixel đổi. Đừng thêm lại `softglow`.
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
    # ÊM VÀO ÊM RA. `a=0` = KHÔNG tối một chút nào (đo: 0,00% pixel đổi), nên
    # nhân sóng là mép cửa sổ trùng khít ảnh gốc. `eval=frame` bắt buộc.
    "vignette=a='{p1}*" + _SONG + "':eval=frame{en}",
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
# ĐÃ GỠ 3 SHADER — 08/08/2026, ĐO LẠI TRÊN CLIP THẬT CỦA ANH HÙNG (1080x1920,
# `aa` = 1,00 = đậm nhất, cửa sổ 0,60 s). Bảng số ở trên đo trên nguồn KHÁC
# (phim tài liệu Nhật nhiều chi tiết); nguồn thật hôm nay ra:
#   sh_net_hon    **1,87%**  (bảng cũ ghi 12,58%)   -> KHÔNG THẤY
#   sh_quang_sang **0,47%**  (bảng cũ ghi 22,99%)   -> KHÔNG THẤY
#   sh_mo_net     **2,16%**  (bảng cũ ghi 11,51%)   -> KHÔNG THẤY
# Ngưỡng "THẤY ĐƯỢC" là 8% (`nguong_thay`), sàn tối thiểu 3%. Đã thử CỨU
# `net_hon`: nới bán kính 1,8 -> 3,2 px, 4 -> 8 điểm lấy mẫu, cường độ 1,9 ->
# 3,2 (`_thu_net.hook`) chỉ lên **6,00%** — vẫn dưới ngưỡng. Lý do gốc: cả 3 đều
# là phép LÂN CẬN vài PIXEL (mờ 2,2 px · nét 1,8 px · quầng sáng nhỏ) mà khung
# dọc 1080x1920 thì vài pixel là vô hình — cùng bài học `mo_net` bản CPU (sigma
# 12 thấy rõ ở 540x960, chỉ 5,4% ở 1080x1920 vì bán kính là SỐ PIXEL TUYỆT ĐỐI).
# 2 trong 3 kiểu này chỉ là BẢN SAO GPU của kiểu CPU đang chạy tốt:
#   quang_sang (frei0r glow)  = **98,22%**   ·  mo_net (gblur 26) = **13,79%**
# nên gỡ đi KHÔNG mất tính năng nào, chỉ bớt 3 dòng khoe suông trong nhật ký.
# Anh Hùng: *"thà ít mà đẹp còn hơn nhiều mà lỏ"*. ĐỪNG THÊM LẠI mà không đo
# trên clip 1080x1920 THẬT.
_dk(HieuUng(
    "sh_hat_phim", "Hạt phim (GPU)", "Film Grain", "shader", _SH_MAU,
    shader="hat_phim.hook", ts=((0.45, 0.70), ), dai=0.60,
    hop=("ke", "tinh")))
_dk(HieuUng(
    "sh_toi_vien", "Tối viền ống kính (GPU)", "Vignette", "shader", _SH_MAU,
    shader="toi_vien.hook", ts=((0.50, 0.90), ), dai=0.70,
    hop=("ke", "tinh", "chot")))
_dk(HieuUng(
    "sh_tuong_phan", "Tăng tương phản (GPU)", "Contrast Punch", "shader",
    _SH_MAU, shader="tuong_phan.hook", ts=((0.80, 1.00), ), dai=0.40,
    hop=("caotrao", "ke")))


# ---- NHÓM 6: LỚP PHỦ HẠT (chồng VẬT THỂ lên hình) ----
# Anh Hùng 09/08/2026: *"kiểu hiệu ứng tuyết rơi, trái tim bay, với rất nhiều
# kiểu khác thêm vào — NHƯNG PHẢI HỢP LÝ, TUỲ CẢNH MỚI CHỌN chứ không chọn bừa
# bãi"*. 27 kiểu cũ đều là CHỈNH MÀU/ĐỘ NÉT/NHIỄU; đây là nhóm đầu tiên chồng
# VẬT THỂ lên hình.
#
# === 3 QUYẾT ĐỊNH KIẾN TRÚC, mỗi cái có lý do đo được ===
# (1) **SINH 100% BẰNG ffmpeg, KHÔNG MỘT FILE NÀO.** Anh Hùng đã chốt *"không
#     được làm app quá nhiều dung lượng"* (gói đang 228 MB). Lớp hạt là
#     `color` + `geq` -> **0 byte tài nguyên thêm**, và `.spec` /
#     `release.yml` KHÔNG phải sửa (thư mục `app/assets/hieu_ung` từng bị bỏ
#     sót khỏi .exe làm nhân viên mất sạch hiệu ứng — nay không đụng tới nó).
#     Cũng vì thế KHÔNG có chuyện vướng bản quyền: không lấy asset của ai.
# (2) **CẮT ĐÚNG CỬA SỔ RỒI `concat`** — y hệt `_SH_MAU`. `overlay` CÓ timeline
#     `enable` nhưng cái ĐẮT là `geq`: để nó chạy cả clip thì mọi khung đều
#     phải sinh hạt cho 0,45 giây dùng tới. Cắt mảnh -> `geq` chỉ chạy trong
#     cửa sổ, và ngoài cửa sổ là ĐÚNG khung gốc đi thẳng qua `trim` nên **0,00%
#     pixel đổi** (luật 1) chứ không phải "gần 0".
# (3) **MÀU HẰNG + CHỈ ALPHA THAY ĐỔI** (`alphamerge`), rồi mới `scale` lên
#     khung ra. 2 cái lợi ĐO ĐƯỢC: `geq` chỉ tính **1 mặt phẳng** thay vì 4
#     (rẻ hơn ~4 lần) và phép phóng to KHÔNG sinh viền bẩn — nội suy giữa
#     "trắng đục" và "trắng trong suốt" vẫn ra trắng, còn nếu nền là
#     `black@0` thì mép hạt bị xám lại.
#     Lớp hạt sinh ở **270x480** rồi phóng lên khung ra: rẻ hơn 16 lần so với
#     sinh thẳng 1080x1920, và mép hạt được phép nội suy làm mềm (đúng cái
#     trông tự nhiên). Hạt to theo khung nên clip 540x960 hay 1080x1920 đều ra
#     cùng một TỈ LỆ phủ.
#
# === VÌ SAO KHÔNG CÓ KIỂU NÀO Ở `_UV_THEO_LOAI` ===
# Đây là điều kiện SỐNG CÒN của cả việc này: bảng đó là đường chọn theo SỐ ĐO
# (tiếng to / hình động). Nếu nhét lớp phủ vào đó thì tuyết sẽ rơi trên video
# nấu ăn ngay khi có một giây tiếng vọt lên. Nhóm này CHỈ được chọn qua
# `app/core/lop_phu.py` (khớp NỘI DUNG cảnh) — không khớp thì KHÔNG THÊM.
#
# === BẪY ĐÃ ĐO, ĐỪNG LẶP ===
# * `geq` dùng `st()/ld()` mà filter lại chạy đa luồng lát cắt -> nghi ngờ đua
#   trạng thái. **ĐÃ ĐO**: dựng 2 lượt + 1 lượt `-filter_threads 1`, so từng
#   khung ra **YMAX = 0** cả hai cặp (giống từng điểm ảnh). Cổng 46 giữ lại ca
#   này để bản ffmpeg sau đổi hành vi thì cổng đỏ chứ không ra hạt nhấp nháy.
# * `gradients` mặc định `seed=-1` = **NGẪU NHIÊN MỖI LƯỢT** -> confetti sẽ đổi
#   màu mỗi lần xuất và cổng nhấp nháy. PHẢI đặt `seed` cố định.
# * Hạt màu bão hoà là đường thẳng tới lỗi cũ anh Hùng đã TỪ CHỐI ("tim bay"
#   phủ lệch hồng V=142 làm tím cả khung). Nên mọi màu hạt ở đây đều là
#   **màu NHẠT gần trắng**: lệch U/V trung bình cả khung phải < `UV_MAX` = 3,0
#   ngay cả trên nguồn `testsrc2` (ô màu bão hoà 100% — khắc nghiệt hơn phim
#   thật). Ai đổi màu đậm hơn thì cổng 46 sẽ đỏ.
#: LƯỚI sinh hạt (phóng lên khung ra bằng `scale`). Cạnh ô của từng kiểu tính
#: THEO lưới này, mà độ phủ = pi*r²/S² nên thu lưới lại KHÔNG đổi tỉ lệ phủ —
#: chỉ đổi chi phí. ĐO THẬT (đường xuất thật, 3 lượt ĐAN XEN, lấy trung vị):
#: lưới 270x480 + 4 `sin`/điểm ảnh tốn **+5,25 CPU-giây**/clip cho
#: `tuyet_roi`; 216x384 + 2 `sin` (xem `_bam_lai`) còn ÍT HƠN HẲN. Nhỏ hơn
#: nữa thì mép hạt nhoè khi phóng lên 1080x1920.
_LP_GW, _LP_GH = 216, 384
#: nửa hình sin theo `T` của CHÍNH nguồn hạt — CÙNG MỘT ĐƯỜNG CONG với `_SONG`
#: của nhóm cũ, chỉ khác hệ quy chiếu: `_SONG` chạy trên `t` của cả clip
#: (`(t-a)/(b-a)`), còn ở đây `trim`+`setpts=PTS-STARTPTS` đã kéo mốc về 0 nên
#: `T/d` LÀ chính đại lượng đó. (Không dùng lại được nguyên văn chuỗi `_SONG`:
#: biến thời gian trong `geq` là `T` viết HOA, `t` thường không tồn tại.)
#:
#: VÌ SAO MẪU SỐ LÀ `{d}-1/{FPS}` CHỨ KHÔNG PHẢI `{d}`: khung CUỐI của cửa sổ
#: nằm ở `T = d - 1/fps`, nên `sin(pi*T/d)` ở đó còn **0,13** biên độ — hạt vẫn
#: hiện, mắt đọc ra là "tắt phụt". Chia cho `d-1/fps` thì khung đầu VÀ khung
#: cuối đều đúng `sin(0)=sin(pi)=0` -> cả hai mép **0,00% điểm ảnh đổi**, đo
#: được, không phải nói suông. `geq` tự kẹp giá trị âm về 0 nên thừa một khung
#: cũng không sao.
_LP_SONG = "sin(3.14159*T/({d}-1/{FPS}))"


def _bam(a: str, b: str, k1: float, k2: float) -> str:
    """Hàm BĂM tiền định trong biểu thức ffmpeg -> số 0..1 ổn định theo (a,b).

    KHÔNG dùng `random()` của ffmpeg: nó đổi trạng thái mỗi lần gọi nên ra
    NHIỄU theo từng điểm ảnh, không phải "mỗi hạt một chỗ" — hạt sẽ nhấp nháy
    loạn thay vì rơi. `mod(sin(...)*43758.5453,1)` là hàm băm quen thuộc của
    dân shader: cùng ô thì cùng số, khác ô thì khác, và LẶP LẠI ĐƯỢC.
    """
    return f"mod(sin(({a})*{k1}+({b})*{k2})*43758.5453,1)"


def _bam_lai(k: float, c: float) -> str:
    """Số 0..1 thứ HAI (thứ ba…) của cùng một ô — KHÔNG tốn thêm `sin`.

    `sin` là phép đắt nhất trong biểu thức `geq` và nó chạy TỪNG ĐIỂM ẢNH. Bản
    đầu gọi `_bam` 4-5 lần mỗi kiểu (chỗ đứng x, chỗ đứng y, cỡ hạt, pha nhấp
    nháy) -> ĐO ĐƯỢC **+5,25 CPU-giây**/clip trên đường xuất thật, trong khi
    chính kiến trúc cắt mảnh `split/trim/concat` chỉ tốn **−0,27** (tức không
    tốn gì) và một hiệu ứng `eq` cũ tốn **+0,56**. Băm LẠI từ `ld(6)` (đã tính
    rồi) bằng nhân-lấy-phần-lẻ cho ra dãy vẫn rải đều, vẫn TIỀN ĐỊNH, chi phí
    gần bằng 0. Dân shader gọi là "hash stretching": có tương quan nhẹ với số
    gốc nhưng mắt không đọc ra trên một cửa sổ 0,8 giây.
    """
    return f"mod(ld(6)*{k}+{c},1)"


def _lp(mat_na: str, nen: str = "color=c=white") -> str:
    """Khuôn filter cho 1 kiểu LỚP PHỦ.

    `mat_na`: biểu thức `geq` trả 0..255 = ĐỘ ĐỤC của lớp hạt tại điểm đó.
    `nen`   : nguồn MÀU của hạt (mặc định trắng; confetti dùng `gradients`).
    Xem khối ghi chú của nhóm để biết vì sao cắt mảnh + alphamerge + scale.
    """
    g = f"{_LP_GW}x{_LP_GH}"
    return (
        "split=3[lp{i}a][lp{i}b][lp{i}c];"
        "[lp{i}a]trim=end={a},setpts=PTS-STARTPTS[lp{i}d];"
        "[lp{i}b]trim=start={a}:end={b},setpts=PTS-STARTPTS[lp{i}m];"
        + nen + ":s=" + g + ":r={FPS}:d={d},format=rgba[lp{i}n];"
        "color=c=black:s=" + g + ":r={FPS}:d={d},format=gray,"
        "geq=lum='" + mat_na + "'[lp{i}k];"
        "[lp{i}n][lp{i}k]alphamerge,scale={W}:{H}:flags=bicubic[lp{i}g];"
        "[lp{i}m][lp{i}g]overlay=0:0:eof_action=pass,format=yuv420p[lp{i}e];"
        "[lp{i}c]trim=start={b},setpts=PTS-STARTPTS[lp{i}f];"
        "[lp{i}d][lp{i}e][lp{i}f]concat=n=3:v=1:a=0"
    )


#: Ô LƯỚI: mỗi ô đúng 1 hạt, chỗ đứng trong ô do hàm băm quyết định. Rẻ hơn
#: "tổng N hạt" hàng chục lần (biểu thức không phụ thuộc số hạt) mà mắt vẫn đọc
#: ra là ngẫu nhiên vì mỗi ô lệch một kiểu.
#:   ld(1)=cạnh ô · ld(2)=cột · ld(3)=tốc độ riêng của cột · ld(4)=Y đã trôi
#:   ld(5)=hàng · ld(6),ld(7)=chỗ đứng trong ô · ld(8)=cỡ hạt · ld(9),ld(0)=lệch
#: `+20000`: `mod`/`floor` trên số ÂM cho kết quả khó lường -> đẩy hẳn sang
#: dương trước khi chia ô (cửa sổ dài nhất 0,8 s nên không bao giờ chạm mốc đó).
def _luoi(s: float, roi: float, len_tren: bool = False, lac: float = 0.0) -> str:
    dau = "+" if len_tren else "-"
    return (f"st(1,{s});st(2,floor(X/ld(1)));"
            f"st(3,0.55+0.9*{_bam('ld(2)', '0', 12.9898, 0.0)});"
            f"st(4,Y{dau}T*ld(1)*{roi}*ld(3)+20000);"
            "st(5,floor(ld(4)/ld(1)));"
            f"st(6,{_bam('ld(2)', 'ld(5)', 127.1, 311.7)});"
            f"st(7,{_bam_lai(97.13, 0.371)});"
            "st(9,mod(X,ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(6))"
            + (f"+{lac}*ld(1)*sin(2.6*T+ld(2))" if lac else "") + ");"
            "st(0,mod(ld(4),ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(7)));")


_dk(HieuUng(
    "tuyet_roi", "Tuyết rơi", "Snow", "lop_phu",
    _lp(_luoi(18, 3.2, lac=0.10)
        + f"st(8,0.12*ld(1)+0.13*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG + "*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.6,0,1)"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="lạnh/mùa đông/tuyết — KHÔNG bao giờ tự chọn theo số đo"))
_dk(HieuUng(
    "trai_tim", "Trái tim bay", "Love Hearts", "lop_phu",
    # màu hồng RẤT NHẠT (255,226,232): lệch V chỉ +14 so với xám trung tính.
    # Hồng đậm (255,170,190) lệch V +41 -> đúng cái anh Hùng đã từ chối.
    _lp(_luoi(24, 2.2, len_tren=True, lac=0.12)
        + "st(8,0.20*ld(1));st(9,ld(9)/ld(8));st(0,-ld(0)/ld(8));"
        + "255*{p1}*" + _LP_SONG
        + "*lte(pow(ld(9)*ld(9)+ld(0)*ld(0)-1,3)-ld(9)*ld(9)*pow(ld(0),3),0)",
        nen="color=c=0xFFE2E8"),
    ts=((0.50, 0.80), ), dai=0.80, hop=(),
    ghi_chu="tình cảm/em bé/thú cưng/cưới"))
_dk(HieuUng(
    "lap_lanh", "Lấp lánh", "Sparkle", "lop_phu",
    # sao 4 cánh = siêu-ellipse mũ 0,5; nhấp nháy theo pha riêng từng ô nhưng
    # KHÔNG bao giờ tắt hẳn (sàn 0,40) — tắt hẳn thì nửa số hạt biến mất và
    # diện tích đo tụt xuống dưới ngưỡng THẤY ĐƯỢC.
    _lp(_luoi(21, 0.45)
        + f"st(8,0.50*ld(1)*(0.70+0.6*{_bam_lai(53.7, 0.117)}));"
        + f"st(3,0.55+0.45*max(0,sin(6.2*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)*clip(2.2-2.2*pow(abs(ld(9))/ld(8),0.5)"
        "-2.2*pow(abs(ld(0))/ld(8),0.5),0,1)"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="lung linh/đẹp/bất ngờ/ăn mừng"))
_dk(HieuUng(
    "confetti", "Confetti giấy màu", "Confetti", "lop_phu",
    # mảnh giấy = hình chữ nhật QUAY theo thời gian. Màu lấy từ `gradients` 4
    # màu PHẤN (đối nhau trên vòng màu nên trung bình gần trung tính) — `seed`
    # PHẢI cố định, mặc định `seed=-1` là ngẫu nhiên mỗi lượt xuất.
    _lp(_luoi(21, 2.8, lac=0.18)
        + f"st(8,4.2*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*lte(max(abs((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.13*ld(1))),"
          "abs((ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.26*ld(1)))),1)",
        nen="gradients=c0=0xFF9E9E:c1=0xFFF0A0:c2=0x9EE8FF:c3=0xCFA8FF"
            ":n=4:seed=7:speed=0.02"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="ăn mừng/thắng/sinh nhật/khai trương"))
_dk(HieuUng(
    "mua_roi", "Mưa rơi", "Rain", "lop_phu",
    # vệt mưa = hạt DẸT theo trục đứng, rơi nhanh gấp 4 lần tuyết và NGHIÊNG
    # (dùng X+0,3*Y làm trục ngang) — mưa thẳng đứng trông như song sắt.
    _lp("st(1,14);st(2,floor((X+0.30*Y)/ld(1)));"
        f"st(3,0.85+0.5*{_bam('ld(2)', '0', 12.9898, 0.0)});"
        "st(4,Y-T*ld(1)*15.0*ld(3)+40000);st(5,floor(ld(4)/ld(1)));"
        f"st(6,{_bam('ld(2)', 'ld(5)', 127.1, 311.7)});"
        f"st(7,{_bam_lai(97.13, 0.371)});"
        "st(9,mod(X+0.30*Y,ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(6)));"
        "st(0,mod(ld(4),ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(7)));"
        + "255*{p1}*" + _LP_SONG + "*clip(1-abs(ld(9))/(0.13*ld(1)),0,1)"
        "*clip(1-abs(ld(0))/(0.46*ld(1)),0,1)",
        nen="color=c=0xE6F0FF"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="buồn/chia tay/mưa/ướt"))
_dk(HieuUng(
    "dom_bokeh", "Đốm sáng bokeh", "Bokeh Lights", "lop_phu",
    # đốm ống kính = ĐĨA mờ + VIỀN sáng hơn ruột (đúng bokeh thật của ống kính
    # gương). Ô to (64) + trôi rất chậm -> cảm giác chiều sâu, không phải "hạt".
    _lp(_luoi(42, 0.5)
        + f"st(8,0.16*ld(1)+0.14*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "st(3,hypot(ld(9),ld(0)));"
        + "255*{p1}*" + _LP_SONG + "*(0.55*clip(1-ld(3)/ld(8),0,1)"
        "+0.45*clip(1-abs(ld(3)-0.86*ld(8))/(0.22*ld(8)),0,1))"),
    ts=((0.50, 0.80), ), dai=0.80, hop=(),
    ghi_chu="cảnh đêm/đèn/thành phố/quán"))
_dk(HieuUng(
    "tan_lua", "Tàn lửa bay lên", "Embers", "lop_phu",
    # tàn lửa: hạt NHỎ bay LÊN, lắc ngang, nhấp nháy. Màu vàng-trắng nhạt
    # (255,235,205) chứ không cam (255,140,40): cam lệch U -69 / V +66, phủ 8%
    # là đã vượt trần UV_MAX.
    _lp(_luoi(15, 2.6, len_tren=True, lac=0.16)
        + f"st(8,0.12*ld(1)+0.13*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.45+0.55*max(0,sin(7.5*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG
        + "*ld(3)*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.4,0,1)",
        nen="color=c=0xFFEBCD"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="lửa/nổ/hành động/bếp lửa"))
_dk(HieuUng(
    "tia_sang", "Tia sáng loé (light leak)", "Light Leak", "lop_phu",
    # KHÔNG phải hạt: một DẢI sáng chéo quét ngang khung (rò sáng máy phim).
    # Biểu thức rẻ nhất nhóm (không lưới, không băm). `W`,`H` trần trụi ở đây là
    # cỡ LƯỚI HẠT của geq (270x480), KHÔNG phải `{W}`/`{H}` khung ra.
    _lp("255*{p1}*" + _LP_SONG + "*clip(1-abs((X*0.55+Y*0.62)"
        "/(0.55*W+0.62*H)-(0.10+0.90*T/{d}))*5.0,0,1)",
        nen="color=c=0xFFF0DC"),
    ts=((0.18, 0.30), ), dai=0.70, hop=(),
    ghi_chu="cảnh đêm/đèn/hoài niệm/hoàng hôn"))
_dk(HieuUng(
    "bui_phim", "Bụi phim nhựa", "Film Dust", "lop_phu",
    # bụi + xước: chỉ ~30% số ô có hạt, và hạt ĐỔI CHỖ MỖI KHUNG (ld(4) mang cả
    # chỉ số khung) -> đúng cảm giác phim cũ.
    _lp("st(1,11);st(2,floor(X/ld(1)));st(3,floor(T*24));"
        "st(4,Y+20000);st(5,floor(ld(4)/ld(1))+ld(3)*37);"
        f"st(6,{_bam('ld(2)', 'ld(5)', 127.1, 311.7)});"
        f"st(7,{_bam_lai(97.13, 0.371)});"
        "st(9,mod(X,ld(1))-(0.1*ld(1)+0.8*ld(1)*ld(6)));"
        "st(0,mod(ld(4),ld(1))-(0.1*ld(1)+0.8*ld(1)*ld(7)));"
        f"st(8,0.14*ld(1)+0.20*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + f"*gt({_bam_lai(19.7, 0.443)},0.50)"
        "*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.2,0,1)"),
    ts=((0.55, 0.90), ), dai=0.70, hop=(),
    ghi_chu="hoài niệm/phim cũ/buồn"))
_dk(HieuUng(
    "la_roi", "Lá rơi", "Falling Leaves", "lop_phu",
    # lá = ELLIPSE quay chậm, rơi chậm hơn confetti và lắc nhiều hơn. Màu vàng
    # nhạt (255,232,190) — lá cam đậm vượt trần lệch màu y như tàn lửa.
    _lp(_luoi(24, 1.6, lac=0.22)
        + f"st(8,2.0*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(2.0-2.0*hypot((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.18*ld(1)),"
          "(ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.31*ld(1))),0,1)",
        nen="color=c=0xFFEDD2"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="mùa thu/ngoài trời/thiên nhiên"))

# ---- BIẾN THỂ NHÌN CỦA CÙNG MỘT CẢNH (09/08/2026) ----
# Anh Hùng: *"càng nhiều kiểu càng tốt, 100 kiểu cũng được, NHƯNG AI phải hiểu
# ngữ cảnh, thêm hợp lý, không thêm bừa bãi làm video chất lượng thấp đi"*.
# **CÁCH MỞ RỘNG ĐÚNG — đã chốt:** thêm BIẾN THỂ trong CÙNG một cảnh, KHÔNG bịa
# thêm ngữ cảnh không nhận ra được. Lý do là số học: mỗi ngữ cảnh mới là một cơ
# hội NHẬN NHẦM (bảng từ khoá phải đoán "cảnh này là gì"), còn biến thể thì dùng
# LẠI đúng bằng chứng đã được chấm đạt ngưỡng — rủi ro thêm bằng 0, mà 3 Part
# của một video không còn kêu giống hệt nhau.
# Vì thế mọi kiểu dưới đây đều là MỘT trong 4 phép biến đổi của khuôn đã đo
# (`_lp` + `_luoi`), không phải cơ chế mới: cỡ ô · tốc độ rơi · HÌNH hạt · MÀU.
_dk(HieuUng(
    "tuyet_bui", "Tuyết bụi bay ngang", "Snow Dust", "lop_phu",
    # bụi tuyết mịn: ô NHỎ (nhiều hạt), rơi chậm nhưng LẮC MẠNH -> mắt đọc ra là
    # gió thổi ngang chứ không phải "rơi".
    _lp(_luoi(11, 0.9, lac=0.55)
        + f"st(8,0.15*ld(1)+0.10*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG + "*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.4,0,1)"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="lạnh/gió tuyết — biến thể của cảnh «tuyet_roi»"))
_dk(HieuUng(
    "tuyet_bao", "Bão tuyết dày", "Blizzard", "lop_phu",
    # bão: ô nhỏ + rơi RẤT nhanh + lắc -> vệt hơi kéo dài, dày đặc.
    _lp(_luoi(13, 6.5, lac=0.30)
        + f"st(8,0.16*ld(1)+0.12*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1-abs(ld(9))/(ld(8)*1.15),0,1)"
          "*clip(1-abs(ld(0))/(ld(8)*1.75),0,1)"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="bão tuyết/trượt tuyết — biến thể của cảnh «tuyet_roi»"))
_dk(HieuUng(
    "tuyet_tinh_the", "Tinh thể tuyết lấp lánh", "Snow Crystals", "lop_phu",
    # bông TO, rơi rất chậm, có nhấp nháy nhẹ (sàn 0,60 — tắt hẳn thì nửa số hạt
    # biến mất và diện tích tụt dưới ngưỡng THẤY ĐƯỢC).
    _lp(_luoi(30, 1.0, lac=0.14)
        + f"st(8,0.19*ld(1)+0.10*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.60+0.40*max(0,sin(4.8*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG
        + "*ld(3)*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.8,0,1)"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="tuyết ngược sáng — biến thể của cảnh «tuyet_roi»"))
_dk(HieuUng(
    "trai_tim_nho", "Tim nhỏ bay dày", "Small Hearts", "lop_phu",
    _lp(_luoi(16, 3.0, len_tren=True, lac=0.16)
        + "st(8,0.21*ld(1));st(9,ld(9)/ld(8));st(0,-ld(0)/ld(8));"
        + "255*{p1}*" + _LP_SONG
        + "*lte(pow(ld(9)*ld(9)+ld(0)*ld(0)-1,3)-ld(9)*ld(9)*pow(ld(0),3),0)",
        nen="color=c=0xFFE2E8"),
    ts=((0.50, 0.80), ), dai=0.80, hop=(),
    ghi_chu="tình cảm/em bé — biến thể của cảnh «trai_tim»"))
_dk(HieuUng(
    "trai_tim_vo", "Tim vỡ rơi xuống", "Broken Hearts", "lop_phu",
    # CÙNG hình tim nhưng RƠI XUỐNG và bị **xẻ đôi** bằng một khe dọc (nhân với
    # `gt(abs(dx), 0,10)`) -> đọc ra ngay là "tan vỡ". Đây là biến thể có GỢI Ý
    # RIÊNG mạnh nhất nhóm: chỉ bật khi lời/hình nói tới chia tay.
    _lp(_luoi(22, 2.0, lac=0.20)
        + "st(8,0.22*ld(1));st(9,ld(9)/ld(8));st(0,-ld(0)/ld(8));"
        + "255*{p1}*" + _LP_SONG
        + "*lte(pow(ld(9)*ld(9)+ld(0)*ld(0)-1,3)-ld(9)*ld(9)*pow(ld(0),3),0)"
          "*gt(abs(ld(9)-0.16*ld(0)),0.11)",
        nen="color=c=0xFFE2E8"),
    ts=((0.50, 0.80), ), dai=0.80, hop=(),
    ghi_chu="chia tay/tan vỡ — biến thể của cảnh «trai_tim»"))
_dk(HieuUng(
    "canh_hoa", "Cánh hoa rơi", "Flower Petals", "lop_phu",
    # cánh hoa = ELLIPSE quay chậm như lá nhưng nhỏ hơn, hồng nhạt, rơi lững lờ.
    _lp(_luoi(20, 1.4, lac=0.26)
        + f"st(8,1.6*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(2.0-2.0*hypot((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.15*ld(1)),"
          "(ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.26*ld(1))),0,1)",
        nen="color=c=0xFFE6EC"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="cưới/lãng mạn — biến thể của cảnh «trai_tim»"))
_dk(HieuUng(
    "lap_lanh_bui", "Bụi kim tuyến", "Glitter Dust", "lop_phu",
    # ĐO LẦN 1: hạt 0,32*ô + sàn nhấp nháy 0,50 chỉ ra **4,43%** — dưới ngưỡng
    # THẤY ĐƯỢC 8%. Sao 4 cánh có diện tích nhỏ hơn đĩa cùng bán kính rất nhiều,
    # lại còn bị nhân với hệ số nhấp nháy. Nới lên 0,56*ô + sàn 0,62.
    _lp(_luoi(10, 0.35)
        + f"st(8,0.56*ld(1)*(0.70+0.6*{_bam_lai(53.7, 0.117)}));"
        + f"st(3,0.62+0.38*max(0,sin(9.0*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)"
        "*clip(2.2-2.2*pow(abs(ld(9))/ld(8),0.5)"
        "-2.2*pow(abs(ld(0))/ld(8),0.5),0,1)"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="lung linh/trang điểm — biến thể của cảnh «lap_lanh»"))
_dk(HieuUng(
    "lap_lanh_sao", "Sao lấp lánh to", "Big Sparkles", "lop_phu",
    _lp(_luoi(36, 0.30)
        + f"st(8,0.62*ld(1)*(0.72+0.55*{_bam_lai(53.7, 0.117)}));"
        + f"st(3,0.55+0.45*max(0,sin(5.0*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)"
        "*clip(2.6-2.6*pow(abs(ld(9))/ld(8),0.42)"
        "-2.6*pow(abs(ld(0))/ld(8),0.42),0,1)"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="phép thuật/biến hình — biến thể của cảnh «lap_lanh»"))
_dk(HieuUng(
    "lap_lanh_vang", "Ánh vàng lấp lánh", "Gold Sparkle", "lop_phu",
    _lp(_luoi(19, 0.50)
        + f"st(8,0.46*ld(1)*(0.70+0.6*{_bam_lai(53.7, 0.117)}));"
        + f"st(3,0.55+0.45*max(0,sin(6.6*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)"
        "*clip(2.2-2.2*pow(abs(ld(9))/ld(8),0.5)"
        "-2.2*pow(abs(ld(0))/ld(8),0.5),0,1)",
        nen="color=c=0xFFF3D6"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="trang sức/kim cương — biến thể của cảnh «lap_lanh»"))
_dk(HieuUng(
    "confetti_dai", "Dải giấy dài", "Streamers", "lop_phu",
    # dải giấy = hình chữ nhật DÀI, quay chậm hơn confetti.
    _lp(_luoi(26, 2.0, lac=0.24)
        + f"st(8,2.4*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*lte(max(abs((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.075*ld(1))),"
          "abs((ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.42*ld(1)))),1)",
        nen="gradients=c0=0xFF9E9E:c1=0xFFF0A0:c2=0x9EE8FF:c3=0xCFA8FF"
            ":n=4:seed=11:speed=0.02"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="tiệc/ăn mừng — biến thể của cảnh «confetti»"))
_dk(HieuUng(
    "confetti_no", "Confetti bắn lên", "Confetti Burst", "lop_phu",
    _lp(_luoi(18, 4.2, len_tren=True, lac=0.22)
        + f"st(8,5.4*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*lte(max(abs((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.15*ld(1))),"
          "abs((ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.24*ld(1)))),1)",
        nen="gradients=c0=0xFF9E9E:c1=0xFFF0A0:c2=0x9EE8FF:c3=0xCFA8FF"
            ":n=4:seed=23:speed=0.02"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="vô địch/giải thưởng — biến thể của cảnh «confetti»"))
_dk(HieuUng(
    "bong_bay", "Bóng bay lên", "Balloons", "lop_phu",
    # bóng = ĐĨA hơi dẹt đứng, bay LÊN chậm, ô to nên thưa.
    # ĐO LẦN 1: **dV 4,39** (trần 3,0) — 24% khung phủ bởi 4 màu 0xB4=180 là
    # quá đậm cho một mảng lớn. Chữa 2 vế: nhạt màu về mức 0xD8 và thu bán kính
    # (24% -> ~13% diện tích). Đây đúng bài học "tim bay hồng đậm làm tím khung"
    # anh Hùng đã từ chối một lần.
    _lp(_luoi(34, 1.3, len_tren=True, lac=0.10)
        + f"st(8,0.22*ld(1)+0.06*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1.6-1.6*hypot(ld(9)/ld(8),ld(0)/(1.20*ld(8))),0,1)",
        nen="gradients=c0=0xFFD8D8:c1=0xFFF6D8:c2=0xD8EEFF:c3=0xE8D8FF"
            ":n=4:seed=31:speed=0.02"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="sinh nhật/bóng bay — biến thể của cảnh «confetti»"))
_dk(HieuUng(
    "mua_rao", "Mưa rào dày", "Heavy Rain", "lop_phu",
    _lp("st(1,10);st(2,floor((X+0.42*Y)/ld(1)));"
        f"st(3,0.85+0.5*{_bam('ld(2)', '0', 12.9898, 0.0)});"
        "st(4,Y-T*ld(1)*22.0*ld(3)+40000);st(5,floor(ld(4)/ld(1)));"
        f"st(6,{_bam('ld(2)', 'ld(5)', 127.1, 311.7)});"
        f"st(7,{_bam_lai(97.13, 0.371)});"
        "st(9,mod(X+0.42*Y,ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(6)));"
        "st(0,mod(ld(4),ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(7)));"
        + "255*{p1}*" + _LP_SONG + "*clip(1-abs(ld(9))/(0.16*ld(1)),0,1)"
        "*clip(1-abs(ld(0))/(0.50*ld(1)),0,1)",
        nen="color=c=0xE6F0FF"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="bão/mưa to — biến thể của cảnh «mua_roi»"))
_dk(HieuUng(
    "mua_bui", "Mưa bụi lất phất", "Drizzle", "lop_phu",
    _lp("st(1,9);st(2,floor((X+0.16*Y)/ld(1)));"
        f"st(3,0.80+0.5*{_bam('ld(2)', '0', 12.9898, 0.0)});"
        "st(4,Y-T*ld(1)*7.0*ld(3)+40000);st(5,floor(ld(4)/ld(1)));"
        f"st(6,{_bam('ld(2)', 'ld(5)', 127.1, 311.7)});"
        f"st(7,{_bam_lai(97.13, 0.371)});"
        "st(9,mod(X+0.16*Y,ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(6)));"
        "st(0,mod(ld(4),ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(7)));"
        + "255*{p1}*" + _LP_SONG + "*clip(1-abs(ld(9))/(0.17*ld(1)),0,1)"
        "*clip(1-abs(ld(0))/(0.33*ld(1)),0,1)",
        nen="color=c=0xE6F0FF"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="buồn/lất phất — biến thể của cảnh «mua_roi»"))
_dk(HieuUng(
    "giot_kinh", "Giọt nước trên kính", "Rain On Glass", "lop_phu",
    # giọt ĐỌNG: gần như đứng yên (rơi 0,18) -> mắt đọc ra là nước bám mặt kính.
    _lp(_luoi(23, 0.18)
        + f"st(8,0.21*ld(1)+0.13*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1.5-1.5*hypot(ld(9)/ld(8),ld(0)/(1.35*ld(8))),0,1)",
        nen="color=c=0xEAF2FF"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="mưa ngoài cửa sổ — biến thể của cảnh «mua_roi»"))
_dk(HieuUng(
    "bokeh_nho", "Đốm bokeh nhỏ dày", "Small Bokeh", "lop_phu",
    _lp(_luoi(20, 0.35)
        + f"st(8,0.20*ld(1)+0.12*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "st(3,hypot(ld(9),ld(0)));"
        + "255*{p1}*" + _LP_SONG + "*(0.55*clip(1-ld(3)/ld(8),0,1)"
        "+0.45*clip(1-abs(ld(3)-0.86*ld(8))/(0.24*ld(8)),0,1))"),
    ts=((0.50, 0.80), ), dai=0.80, hop=(),
    ghi_chu="phố đêm/quán — biến thể của cảnh «dom_bokeh»"))
_dk(HieuUng(
    "den_nhap_nhay", "Đèn nhấp nháy", "Twinkling Lights", "lop_phu",
    _lp(_luoi(26, 0.20)
        + f"st(8,0.17*ld(1)+0.10*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.35+0.65*max(0,sin(7.8*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG
        + "*ld(3)*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.6,0,1)",
        nen="color=c=0xFFF6E0"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="đèn giáng sinh/đèn lồng — biến thể của cảnh «dom_bokeh»"))
_dk(HieuUng(
    "phao_hoa", "Tia pháo hoa", "Firework Sparks", "lop_phu",
    # tia pháo hoa = hạt nhỏ bay LÊN nhanh, đuôi kéo dài theo trục đứng.
    _lp(_luoi(14, 5.0, len_tren=True, lac=0.12)
        + f"st(8,0.14*ld(1)+0.09*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.50+0.50*max(0,sin(8.5*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)"
        "*clip(1-abs(ld(9))/(ld(8)*1.1),0,1)"
        "*clip(1-abs(ld(0))/(ld(8)*2.2),0,1)",
        nen="color=c=0xFFF2D8"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="pháo hoa/lễ hội — biến thể của cảnh «dom_bokeh»"))
_dk(HieuUng(
    "tan_lua_day", "Tàn lửa dày", "Heavy Embers", "lop_phu",
    _lp(_luoi(11, 4.0, len_tren=True, lac=0.22)
        + f"st(8,0.15*ld(1)+0.11*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.45+0.55*max(0,sin(9.5*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG
        + "*ld(3)*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.3,0,1)",
        nen="color=c=0xFFEBCD"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="đám cháy/lò rèn — biến thể của cảnh «tan_lua»"))
_dk(HieuUng(
    "khoi_bay", "Khói mỏng bay lên", "Drifting Smoke", "lop_phu",
    # khói = mảng TO, mềm, độ đục thấp; ô rất to nên chỉ vài mảng trôi lên.
    _lp(_luoi(56, 0.55, len_tren=True, lac=0.20)
        + f"st(8,0.40*ld(1)+0.16*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1.0-hypot(ld(9)/ld(8),ld(0)/(1.5*ld(8))),0,1)",
        nen="color=c=0xF2F2F2"),
    ts=((0.30, 0.50), ), dai=0.80, hop=(),
    ghi_chu="khói/hơi nóng — biến thể của cảnh «tan_lua»"))
_dk(HieuUng(
    "tia_sang_doc", "Vệt sáng dọc quét", "Vertical Light Leak", "lop_phu",
    # ĐO LẦN 1 — **MỘT dải rộng thì lệch màu, NHIỀU dải hẹp thì không**: bản đầu
    # là 1 dải rộng 0,31·W, đo ra **dU 4,49** (trần 3,0) trong khi `nang_xuyen`
    # (nhiều tia song song, tổng diện tích còn LỚN HƠN) chỉ **dU 0,74**. Lý do:
    # dU là lệch U TRUNG BÌNH CẢ KHUNG; một dải rộng nằm trọn trên MỘT vạch màu
    # của `testsrc2` nên kéo lệch hẳn về một phía, còn nhiều dải hẹp rải khắp
    # khung thì phần kéo của các vạch màu khác nhau TRIỆT TIÊU nhau. Nay 3 dải
    # hẹp quét ngang (cùng tổng diện tích, cùng ý đồ nhìn).
    # ĐO LẦN 2 (3 dải THẲNG ĐỨNG): dV còn **3,30** — vẫn chạm trần. Nguyên nhân
    # thứ hai, riêng của trục dọc: `testsrc2` có các VẠCH MÀU DỌC, mà dải sáng
    # cũng dọc -> hai lưới CỘNG HƯỞNG, dải nằm trọn trong vạch. Nay 5 dải và
    # NGHIÊNG NHẸ (X + 0,20·Y): mỗi dải cắt ngang nhiều vạch màu nên phần kéo
    # tự triệt tiêu, mà mắt vẫn đọc ra là "vệt sáng dọc quét ngang".
    _lp("st(1,mod((X+0.20*Y)/W*5.0-1.15*T/{d},1));"
        + "255*{p1}*" + _LP_SONG + "*clip(1-abs(ld(1)-0.5)*8.0,0,1)",
        nen="color=c=0xFFF0DC"),
    ts=((0.20, 0.34), ), dai=0.70, hop=(),
    ghi_chu="hoài niệm/hoàng hôn — biến thể của cảnh «tia_sang»"))
_dk(HieuUng(
    "nang_xuyen", "Nắng xuyên nhiều tia", "God Rays", "lop_phu",
    # nhiều dải song song, cùng nghiêng, quét chậm: `mod` trên trục chéo cho ra
    # dãy tia đều nhau mà không cần lưới băm.
    _lp("st(1,mod((X*0.42+Y*0.62)/W*6.0-0.55*T/{d},1));"
        + "255*{p1}*" + _LP_SONG + "*clip(1-abs(ld(1)-0.5)*4.6,0,1)",
        nen="color=c=0xFFF4E2"),
    ts=((0.20, 0.34), ), dai=0.80, hop=(),
    ghi_chu="nắng chiều/rừng cây — biến thể của cảnh «tia_sang»"))
_dk(HieuUng(
    "xuoc_phim", "Xước dọc phim nhựa", "Film Scratches", "lop_phu",
    # xước = vạch DỌC chạy suốt khung, đổi chỗ mỗi khung (như bụi phim).
    _lp("st(3,floor(T*24));st(1,17);st(2,floor(X/ld(1)));"
        f"st(5,ld(2)+ld(3)*61);"
        f"st(6,{_bam('ld(2)', 'ld(5)', 127.1, 311.7)});"
        f"st(7,{_bam_lai(97.13, 0.371)});"
        "st(9,mod(X,ld(1))-(0.15*ld(1)+0.70*ld(1)*ld(6)));"
        # ĐO LẦN 1: **5,49%** — dưới ngưỡng 8%. Vạch quá mảnh (3,8 px trên lưới
        # 216 px) và chỉ 38% số cột có vạch. Nay dày 6,4 px + 50% số cột + vệt
        # kéo dài hơn theo chiều dọc (2,4 -> 1,6).
        + "255*{p1}*" + _LP_SONG
        + f"*gt({_bam_lai(19.7, 0.443)},0.50)"
        "*clip(1-abs(ld(9))/3.2,0,1)"
        "*clip(1-abs(Y/H-ld(7))*1.6,0,1)"),
    ts=((0.55, 0.90), ), dai=0.70, hop=(),
    ghi_chu="phim cũ/tư liệu — biến thể của cảnh «bui_phim»"))
_dk(HieuUng(
    "bui_bay", "Bụi lơ lửng trong nắng", "Floating Dust", "lop_phu",
    # KHÁC `bui_phim`: hạt KHÔNG đổi chỗ mỗi khung mà trôi rất chậm -> đúng cảm
    # giác bụi trong luồng sáng, không phải nhiễu phim.
    _lp(_luoi(15, 0.22, lac=0.30)
        + f"st(8,0.13*ld(1)+0.09*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.55+0.45*max(0,sin(3.6*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG
        + "*ld(3)*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.5,0,1)",
        nen="color=c=0xFFF6E8"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="ký ức/căn phòng cũ — biến thể của cảnh «bui_phim»"))
_dk(HieuUng(
    "la_bay", "Lá bay theo gió", "Leaves In Wind", "lop_phu",
    # ĐO LẦN 1: **7,07%** — sát dưới ngưỡng 8%. Lá to lên (0,17x0,29 ->
    # 0,21x0,35 ô = +49% diện tích) và bớt lắc (0,62 -> 0,48, lắc quá mạnh làm
    # lá tràn sang ô bên cạnh rồi chồng lên nhau).
    _lp(_luoi(21, 1.1, lac=0.48)
        + f"st(8,3.0*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(2.0-2.0*hypot((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.21*ld(1)),"
          "(ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.35*ld(1))),0,1)",
        nen="color=c=0xFFEDD2"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="gió thổi/đường rừng — biến thể của cảnh «la_roi»"))
_dk(HieuUng(
    "la_kim_tuyen", "Lá vàng lấp lánh", "Golden Foliage", "lop_phu",
    _lp(_luoi(27, 1.5, lac=0.24)
        + f"st(8,1.2*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.60+0.40*max(0,sin(5.6*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)"
        "*clip(2.0-2.0*hypot((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.20*ld(1)),"
          "(ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.33*ld(1))),0,1)",
        nen="color=c=0xFFF0D8"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="mùa thu ngược sáng — biến thể của cảnh «la_roi»"))
# ---- 4 CẢNH MỚI. Chỉ nhận cảnh nào digest mô tả bằng từ RẤT khó nhầm (nước,
# ma quái, tiền, màn hình/công nghệ) — mỗi cảnh mới là một cơ hội nhận nhầm nên
# chỉ thêm khi từ khoá đủ đặc trưng, xem bảng luật `lop_phu.py`.
_dk(HieuUng(
    "bong_bong", "Bong bóng nổi lên", "Bubbles", "lop_phu",
    # bong bóng = VÒNG (viền sáng, ruột trong) bay lên, lắc nhẹ.
    _lp(_luoi(24, 1.5, len_tren=True, lac=0.18)
        + f"st(8,0.19*ld(1)+0.12*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "st(3,hypot(ld(9),ld(0)));"
        + "255*{p1}*" + _LP_SONG + "*(0.24*clip(1-ld(3)/ld(8),0,1)"
        "+0.76*clip(1-abs(ld(3)-0.82*ld(8))/(0.26*ld(8)),0,1))",
        nen="color=c=0xE8F6FF"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="dưới nước/bể bơi/bể cá"))
_dk(HieuUng(
    "bot_nuoc", "Bọt nước li ti", "Fine Bubbles", "lop_phu",
    _lp(_luoi(11, 3.4, len_tren=True, lac=0.26)
        + f"st(8,0.16*ld(1)+0.09*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.3,0,1)",
        nen="color=c=0xEAF7FF"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="lặn/sóng/thác nước"))
_dk(HieuUng(
    "song_nuoc", "Vân sáng mặt nước", "Water Caustics", "lop_phu",
    # vân nước = 3 sóng sin chéo nhau, không dùng lưới băm -> rẻ nhất nhóm.
    # ĐO LẦN 1: **dU 3,11 · dV 4,39** (trần 3,0) tuy chỉ phủ 12%. Cùng nguyên
    # nhân với `tia_sang_doc`: vân THƯA thì mỗi dải nằm trọn trên một vạch màu
    # của `testsrc2`, kéo lệch một phía. Nay tăng tần số (17/21/13 ->
    # 31/37/23) cho vân MỊN rải đều khắp khung -> phần kéo triệt tiêu nhau;
    # màu đổi về TRẮNG (bỏ ánh xanh) cho chắc.
    _lp("st(1,sin(X/W*31.0+2.3*T)+sin(Y/H*37.0-1.7*T)"
        "+sin((X/W+Y/H)*23.0+3.1*T));"
        + "255*{p1}*" + _LP_SONG + "*clip((ld(1)-1.35)/0.85,0,1)",
        nen="color=c=white"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="hồ bơi/biển/dưới nước"))
_dk(HieuUng(
    "suong_mo", "Sương mù trôi", "Drifting Fog", "lop_phu",
    # ĐO LẦN 1: **dV 3,52** (trần 3,0) với 34% khung bị phủ. Ô 64 px trên lưới
    # 216x384 = chỉ 3x6 mảng -> quá THÔ, mỗi mảng nằm trọn trên một vạch màu.
    # Nay ô 40 (nhiều mảng hơn, kéo màu triệt tiêu nhau) + mảng nhỏ lại + nhạt
    # hơn (34% -> ~20% diện tích).
    _lp(_luoi(40, 0.30, lac=0.55)
        + f"st(8,0.30*ld(1)+0.12*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1.0-hypot(ld(9)/(1.6*ld(8)),ld(0)/ld(8)),0,1)",
        nen="color=c=0xF2F2F4"),
    ts=((0.28, 0.46), ), dai=0.80, hop=(),
    ghi_chu="kinh dị/halloween/rừng đêm"))
_dk(HieuUng(
    "dom_ma", "Đốm ma lơ lửng", "Ghost Orbs", "lop_phu",
    _lp(_luoi(38, 0.28, lac=0.34)
        + f"st(8,0.20*ld(1)+0.12*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,0.40+0.60*max(0,sin(3.2*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "st(4,hypot(ld(9),ld(0)));"
        + "255*{p1}*" + _LP_SONG + "*ld(3)*(0.62*clip(1-ld(4)/ld(8),0,1)"
        "+0.38*clip(1-ld(4)/(2.1*ld(8)),0,1))",
        nen="color=c=0xEDF2EA"),
    ts=((0.50, 0.85), ), dai=0.80, hop=(),
    ghi_chu="ma quái/bí ẩn/nghĩa trang"))
_dk(HieuUng(
    "tan_tro", "Tàn tro rơi", "Falling Ash", "lop_phu",
    _lp(_luoi(16, 1.0, lac=0.34)
        + f"st(8,0.13*ld(1)+0.10*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1-(hypot(ld(9),ld(0))-ld(8))/1.4,0,1)",
        nen="color=c=0xF0EEEA"),
    ts=((0.50, 0.80), ), dai=0.80, hop=(),
    ghi_chu="tro tàn/tận thế/hoang tàn"))
_dk(HieuUng(
    "tien_roi", "Tiền rơi", "Money Rain", "lop_phu",
    _lp(_luoi(28, 2.4, lac=0.20)
        + f"st(8,3.0*T*ld(3)+6.283*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*lte(max(abs((ld(9)*cos(ld(8))+ld(0)*sin(ld(8)))/(0.30*ld(1))),"
          "abs((ld(0)*cos(ld(8))-ld(9)*sin(ld(8)))/(0.15*ld(1)))),1)",
        nen="color=c=0xE6F4E2"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="tiền/mua sắm/trúng thưởng"))
_dk(HieuUng(
    "xu_vang", "Đồng xu vàng rơi", "Gold Coins", "lop_phu",
    _lp(_luoi(25, 2.6, lac=0.14)
        + f"st(8,0.22*ld(1)+0.08*ld(1)*{_bam_lai(53.7, 0.117)});"
        + f"st(3,abs(cos(3.4*T+6.283*{_bam_lai(31.9, 0.613)})));"
        + "255*{p1}*" + _LP_SONG
        + "*clip(1.5-1.5*hypot(ld(9)/(ld(8)*(0.30+0.70*ld(3))),ld(0)/ld(8)),0,1)",
        nen="color=c=0xFFF2CC"),
    ts=((0.55, 0.90), ), dai=0.80, hop=(),
    ghi_chu="vàng/kho báu/giàu có"))
_dk(HieuUng(
    "hat_so", "Hạt dữ liệu bay lên", "Data Particles", "lop_phu",
    _lp(_luoi(17, 2.2, len_tren=True, lac=0.10)
        + f"st(8,0.19*ld(1)+0.08*ld(1)*{_bam_lai(53.7, 0.117)});"
        + "255*{p1}*" + _LP_SONG
        + "*lte(max(abs(ld(9)),abs(ld(0)))/ld(8),1)",
        nen="color=c=0xE4F6FF"),
    ts=((0.55, 0.85), ), dai=0.80, hop=(),
    ghi_chu="công nghệ/AI/lập trình"))
_dk(HieuUng(
    "luoi_so", "Lưới số quét ngang", "Digital Grid", "lop_phu",
    # lưới = 2 chùm vạch vuông góc, quét chậm; không lưới băm nên rất rẻ.
    _lp("st(1,mod(X/W*22.0+0.5*T/{d},1));st(2,mod(Y/H*38.0-0.9*T/{d},1));"
        + "255*{p1}*" + _LP_SONG
        + "*clip(max(1-abs(ld(1)-0.5)*13.0,1-abs(ld(2)-0.5)*13.0),0,1)",
        nen="color=c=0xE4F6FF"),
    ts=((0.42, 0.68), ), dai=0.80, hop=(),
    ghi_chu="màn hình/game/dữ liệu"))

#: Khoá của nhóm lớp phủ — `lop_phu.py` và cổng 46 đọc từ đây, KHÔNG chép tay
#: (chép tay là kiểu sai "gỡ khỏi kho mà bảng chọn vẫn trỏ tới").
LOP_PHU: tuple = tuple(k for k, h in KHO.items() if h.nhom == "lop_phu")


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
        "lop_phu": sum(1 for k in dd if KHO[k].nhom == "lop_phu"),
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


def do_du(nl: list, cd: list, giay: float) -> bool:
    """SỐ ĐO NHỊP có PHỦ ĐỦ clip không? Hàm THUẦN — test được.

    === VÌ SAO PHẢI CÓ (lượt kiểm ĐỘC LẬP 08/08/2026) ===
    `do_nhip` trả 1 giá trị/giây. Khi nó chỉ đo được MẤY GIÂY ĐẦU mà vẫn trả
    danh sách (không lỗi, không ngoại lệ), `chon_hieu_ung` coi đó là số đo THẬT
    của cả clip:
      * mấy giây đầu tình cờ ĐỀU  -> `dai_dong` = 1,00 < `PHANG` -> **0 ĐIỂM
        NHẤN**, clip trần trụi, KHÔNG một dòng báo;
      * mấy giây đầu có biến động -> mọi điểm nhấn DỒN vào đầu clip, phần sau
        (kể cả câu chốt) trắng trơn.
    ĐO THẬT trên chính hàm `chon_hieu_ung` (clip 16 s, 3 cao trào ở giây 7/11/14,
    mức "vua", cùng bộ kiểu dùng được):
        đo ĐỦ 16/16 giây -> **3** điểm (7,0 · 11,0 · 14,0)
        đo cụt  8/16 giây -> 3 điểm nhưng DỒN HẾT vào 0,0 · 3,0 · 7,0
        đo cụt  4/16 giây -> **0 điểm**
        KHÔNG đo được ([]) -> **3** điểm (6,0 · 11,0 · 14,0) — đường CẤU TRÚC
    Tức "đo cụt" TỆ HƠN "không đo được", mà lại là trường hợp DUY NHẤT không ai
    phát hiện ra. Đây đúng là lỗi đã xảy ra thật hôm 08/08/2026 (mảnh mezzanine
    lệch `pix_fmt` -> ffmpeg dựng lại filter graph -> `metadata=print:file=`
    GHI ĐÈ -> chỉ còn 4 giây trên 16 -> 0 điểm nhấn trên MỌI máy không NVENC).
    Bản vá hôm đó bịt đúng MỘT nguyên nhân (`-pix_fmt yuv420p`); còn CÁI DÒ thì
    chưa có — nên bất kỳ lý do nào khác làm dựng lại graph (đổi độ phân giải /
    SAR / fps giữa các mảnh, đĩa đầy, file đo bị khoá) đều tái diễn y hệt, im
    lặng. Hàm này là cái dò đó: đo cụt -> caller vứt số đo, đi đường CẤU TRÚC
    (đường đã được kiểm kỹ, vẫn ra đủ điểm nhấn).
    """
    ky_vong = max(1.0, float(giay or 0.0))
    n = max(len(nl or []), len(cd or []))
    return n >= DO_PHU_TOI_THIEU * ky_vong


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
                  co_the_dung: Optional[list] = None,
                  hook: bool = False,
                  dat_truoc: Optional[list] = None) -> list[dict]:
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

    # ---- ĐẶT TRƯỚC: điểm đã được quyết định NGOÀI hàm này, bằng bằng chứng
    # mạnh hơn số đo. Hiện chỉ có nhóm LỚP PHỦ HẠT (`app/core/lop_phu.py`, khớp
    # NỘI DUNG cảnh qua vision_digest + chép lời). Vì sao nhận ở ĐÂY chứ không
    # ghép ở caller: ngân sách 10% (`TY_LE_MAX`), trần `DIEM_MAX`, luật cách
    # nhau `CACH_MIN` và luật KHÔNG LẶP KIỂU phải được tính MỘT chỗ. Ghép sau
    # là đường thẳng tới clip 4 điểm nhấn / 14% thời lượng có hiệu ứng.
    # `dat_truoc=None` -> vòng lặp không chạy -> hàm ra Y HỆT bản cũ.
    for c in (dat_truoc or []):
        if len(ra) >= n_diem:
            break
        try:
            dai_p = float(c["het"]) - float(c["bat"])
        except (KeyError, TypeError, ValueError):
            continue
        if dai_p <= 0 or dai_p > ngan_sach + 1e-6:
            continue
        ra.append(dict(c))
        ngan_sach -= dai_p
        da_dung.append(str(c.get("khoa", "")))
        da_dung_loai.append(str(c.get("loai", "")))

    # ---- HOOK MỞ ĐẦU (anh Hùng 08/08/2026: *"phần hook mở đầu cứ thêm sao cho
    # phù hợp gây ấn tượng"*). App đã đưa 2-3 giây CAO TRÀO nhất lên đầu clip
    # (hook-first) nhưng điểm nhấn thì vẫn chọn theo số đo -> giây 0 hầu như
    # KHÔNG BAO GIỜ trúng (`_diem_hap_dan` cần một giây VỌT LÊN so với các giây
    # xung quanh, mà giây đầu không có "trước" để so). Kết quả: đoạn đắt nhất
    # của clip lại là đoạn trần trụi nhất.
    # Nay: hook-first -> ĐẶT SẴN 1 điểm ở giây 0,12, kiểu lấy từ hàng "hook"
    # (mạnh + có tiếng đắt). Vẫn ăn cùng NGÂN SÁCH 10% và cùng trần độ đậm
    # `DAM_MAX` -> không nới luật nào. Clip PHẲNG cũng vẫn được hook: chỗ này là
    # sự kiện CÓ THẬT (app vừa BÊ đoạn cao trào lên đầu), không phải suy đoán.
    # `len(ra) < n_diem` + luật CÁCH NHAU: có `dat_truoc` (lớp phủ) rồi thì hook
    # phải nhường nếu nó rơi sát chỗ đã đặt. Thiếu 2 điều kiện này là hai hiệu
    # ứng CHỒNG CỬA SỔ lên nhau — biên độ cộng dồn, đúng loại loè mà luật 4 và
    # `CACH_MIN` sinh ra để chặn. (Vòng chọn theo số đo bên dưới đã có luật này
    # từ trước; riêng khối hook thì chưa, vì trước đây nó luôn là điểm ĐẦU TIÊN.)
    if hook and float(tong_giay) >= 3.0 and len(ra) < n_diem \
            and not any(abs(HOOK_BAT - float(r["bat"])) < CACH_MIN for r in ra):
        k_hook = _chon_kieu("hook", dung, da_dung, 0)
        if k_hook:
            dai_h = min(HOOK_DAI, max(DAI_MIN, KHO[k_hook].dai))
            if dai_h <= ngan_sach + 1e-6:
                ra.append({"bat": HOOK_BAT,
                           "het": round(HOOK_BAT + dai_h, 3),
                           "khoa": k_hook, "dam": dam, "loai": "hook",
                           "vi_sao": "HOOK mở đầu: app vừa đưa đoạn cao trào "
                                     "nhất lên đầu clip -> nhấn ngay giây "
                                     f"{_so(HOOK_BAT)} cho 2 giây đầu giữ "
                                     "người xem (kèm tiếng động cùng nhịp)"})
                ngan_sach -= dai_h
                da_dung.append(k_hook)
                da_dung_loai.append("hook")

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
    # (đã bỏ `sh_net_hon`/`sh_quang_sang`/`sh_mo_net`/`sang_diu` khỏi mọi hàng —
    #  4 kiểu đó đã GỠ khỏi KHO 08/08/2026 vì đo ra không thấy / làm tối hình)
    # `sh_tuong_phan` đứng hàng 3 (chỗ `sh_net_hon` vừa bị gỡ để lại): `_chon_kieu`
    # chỉ với tới `moi[0..2]`, đặt cuối danh sách là "nối cho có" — cổng 41 canh.
    "caotrao": ("zoom_nhoi", "rung_lac", "sh_tuong_phan", "loe_sang",
                "nhay_sang", "tuong_phan", "meo_kinh"),
    "dong": ("glitch_khoi", "o_vuong", "xao_dong", "lech_bang",
             "vien_net", "dong_quet", "song_meo"),
    "tinh": ("quang_sang", "hat_phim", "sh_toi_vien", "toi_vien",
             "sh_hat_phim", "nhieu_analog", "hat_nhieu", "vien_phim"),
    "chot": ("sup_toi", "nhay_sang", "sh_toi_vien", "toi_vien", "quang_sang",
             "zoom_nhoi", "vien_phim"),
    "noi": ("mo_net", "loe_sang", "o_vuong", "mo_vuong",
            "lech_bang", "zoom_nhoi", "dem_nguoc"),
    "ke": ("quang_sang", "hat_phim", "sh_hat_phim", "nhieu_analog",
           "dong_quet", "toi_vien", "zoom_day", "hat_nhieu", "tuong_phan",
           "sh_tuong_phan"),
    # HOOK MỞ ĐẦU (2 giây đầu quyết định người xem ở lại hay lướt). Chỉ những
    # kiểu ĐO RA MẠNH NHẤT và có tiếng đi kèm đắt: zoom nhồi (impact), loé sáng
    # (reveal), tương phản (impact), rung lắc (impact). KHÔNG dùng kiểu "mood"
    # (hạt phim / tối viền) — mở clip bằng hạt phim thì chẳng ai dừng lại.
    "hook": ("zoom_nhoi", "loe_sang", "tuong_phan", "rung_lac", "nhay_sang"),
}
#: HOOK: điểm nhấn mở đầu đặt ở giây này (không đặt 0,00 — `fx_fade` đang fade
#: vào 0,35 s đầu nên biên độ ở giây 0 bị nhân với hình đang tối, phí).
HOOK_BAT = 0.12
#: HOOK: dài tối đa của điểm nhấn mở đầu — phải NGẮN, xong trước khi câu đầu
#: tiên kết thúc, nếu không nó thành "phủ clip" (luật 1).
HOOK_DAI = 0.45


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
              "ke": "đang kể đều", "hook": "hook mở đầu"}


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
