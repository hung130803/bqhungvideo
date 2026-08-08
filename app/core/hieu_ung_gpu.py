# -*- coding: utf-8 -*-
r"""CHUYỂN CẢNH + HIỆU ỨNG CHẠY TRÊN **GPU** — `xfade_opencl` và `libplacebo`.

VÌ SAO CÓ FILE NÀY (số đo trên máy anh Hùng): lúc xuất, **CPU 96,7% mà GPU chỉ
11,3%**. `xfade` thường và mọi hiệu ứng filter đều tính trên CPU — đúng chỗ đang
tắc. Hai đường trong file này tính trên GPU nên dùng đúng phần máy đang bỏ không.

## BẤT BIẾN SỐNG CÒN — FALLBACK PHẢI ÊM
Máy nhân viên có thể **không có OpenCL / không có Vulkan / không có GPU rời**.
  - **Nhóm PHÁT HIỆN** (`co_opencl`, `co_libplacebo`, `dung_duoc`, `shader_co`,
    `thong_ke`) **KHÔNG BAO GIỜ ném lỗi**; máy không kham được thì `dung_duoc()`
    trả **[]** -> caller (app) tự dùng `xfade` CPU như cũ, người dùng không thấy
    một dòng lỗi nào. Phát hiện chạy **1 lần** rồi cache (mỗi lần thử ~0,3 s).
  - **Nhóm DỰNG LỆNH** (`lenh_vung_chong`, `lenh_shader`) thì **CỐ Ý NÉM LỖI**
    khi kiểu không có trong kho hoặc thiếu file kernel/shader — đúng như đường
    `xfade` CPU: thà FAIL TO còn hơn im lặng ra clip cắt khô (cổng 36 có ca canh
    đúng điều này). **Caller BẮT BUỘC hỏi `dung_duoc()` TRƯỚC**; hỏi rồi thì
    không bao giờ chạm tới nhánh ném lỗi.

## BẪY SỐ 0 — NẶNG NHẤT: `xfade_opencl` TRẢ MỐC THỜI GIAN RÁC
`xfade_opencl` (build `bin/ffmpeg.exe` hiện tại) gắn **AV_NOPTS_VALUE** lên khung
ra. `showinfo` in `pts_time:-600479950316066` (≈ **-6,0e14 giây**). Hai hậu quả,
cả hai đều **IM LẶNG** (rc=0, không một dòng lỗi):
  1. Muxer bỏ hết khung -> file ra **0 KHUNG** dù `rc=0` và file có kích thước.
     Đây là lý do bảng đo trước ra **0/24 kiểu ĐẠT**, không phải kernel sai.
  2. Ai "chữa" bằng cách chèn `fps=30` sau `hwdownload` thì **CHẾT MÁY**: bộ lọc
     `fps` cố lấp khoảng từ -6e14 giây tới 0 nên sinh khung vô tận. **ĐO THẬT
     08/08/2026: 19,1 GB RSS + 364 CPU-giây trong 9 phút và vẫn chạy, phải giết
     tay.** Cùng loại tai nạn "1 lệnh trim+concat phình 19,6 GB" trong hồ sơ.

**CHỮA: `setpts=N/FR/TB` ngay sau `hwdownload`** — đánh lại mốc theo SỐ THỨ TỰ
khung. Đo trên file thật, 3 độ dài: 8/8 · 9/9 · 15/15 khung, PTS trùng khít bản
`xfade` CPU (0 · 0,0333 · 0,0667 …). **KHÔNG dùng `setpts=PTS-STARTPTS`** — nó
giữ khoảng cách rác nên MẤT khung (đo: 6/8 · 7/9 · 11/15). Kiểu dựng sẵn của
`xfade_opencl` (`fade`, `wipeleft`) cũng dính y hệt -> lỗi của filter, không phải
của kernel gl-transitions.

## BẪY SỐ 1/2 — `xfade_opencl` ĐỌC `duration` Ở TIMEBASE KHÁC
Chữa xong PTS rác thì số khung ra đã đúng (15/15) nhưng **mọi kiểu đều ra y hệt
đoạn B**: đo % pixel từng khung được `khác B = 0` ở CẢ 15 khung. Kiểu **DỰNG SẴN
của chính ffmpeg** (`xfade_opencl=fade`) cũng hỏng y như vậy -> **không phải
kernel gl-transitions sai**.

Gốc: đoạn mezzanine .mp4 mang `time_base = 1/15360` còn `xfade_opencl` quy đổi
`duration` theo timebase KHUNG-HÌNH (1/fps) -> lệch 512 lần -> chuyển cảnh chạy
hết trong 1 khung. **Chữa: `settb=1/<fps>` trên MỖI đầu vào TRƯỚC `hwupload`**
(hàm `dau_vao`). Đo lại `xfade_opencl=fade` so `xfade=fade` CPU trên cùng cặp
đoạn: đường cong **lệch 0,2** (0 = trùng khít), mức trộn khung giữa 1,5 vs 1,6.
Nhân `duration` để bù thì VÔ ÍCH (thử x16 và x1/512, kết quả y hệt).

**BẪY ĐO của chính tôi khi truy cái này:** lần đầu tôi chấm kernel `gl_gat_trai`
(kiểu TRƯỢT) bằng đường cong tham chiếu `xfade=fade` (kiểu MỜ DẦN) -> ca nào
cũng "lệch" và suýt kết luận hớ. **Chấm chuyển cảnh phải so CÙNG MỘT KIỂU.**

## 3 BẪY THẬT ĐÃ SẬP KHI LÀM (đừng lặp — mỗi cái mất nửa giờ)
1. **`hwupload` 2 lần = 2 NGỮ CẢNH KHUNG khác nhau.** Dựng
   `[0:v]…hwupload[a];[1:v]…hwupload[b];[a][b]xfade_opencl=…` thì ffmpeg chạy
   được phần chuyển cảnh rồi **CHẾT** ngay khi hết chuyển cảnh, vì `xfade_opencl`
   CHUYỂN THẲNG khung của đầu vào #1 sang đầu ra mà khung đó thuộc ngữ cảnh
   khác: `Input frame is not the in the configured hwframe context`. Đo thật:
   output chỉ **53/90 khung** (1,77 s thay vì 3,0 s) mà mã trả về vẫn có file
   -> **im lặng ra clip cụt**. Vì vậy hàm ở đây **chỉ render ĐÚNG VÙNG CHỒNG**
   (`duration = d`, `offset = 0`, hai đầu vào đều dài đúng `d`), nên KHÔNG có
   khung nào chạy tiếp sau chuyển cảnh -> không sập. Đo lại: **đúng 30/30 khung**.
2. **Lệch metadata màu là đủ để cả graph vỡ.** Hai đầu vào khác `color_range`/
   `color_space` (`unknown` vs `tv/bt470bg`) -> ffmpeg chèn `auto_scale` giữa
   `hwupload` và `xfade_opencl`, mà `scale` không chạy trên khung OpenCL:
   `Impossible to convert between the formats…` + `-40 (Function not
   implemented)`. Phải `setparams` CHUẨN HOÁ cả 2 nhánh trước khi upload.
3. **Dấu `:` của ổ `C:` phá cú pháp filter.** `custom_shader_path=C:/…` ->
   `No option name near '/Users/…'`. Phải escape `\:` — đúng lỗi đã sập một lần
   ở `hieu_ung.duong_filter`.

## GIẤY PHÉP
Kernel trong `app/assets/hieu_ung/gl_transitions.cl` chuyển từ **gl-transitions**
(MIT). Shader trong `app/assets/hieu_ung/shaders/` là **tự viết** (công thức
toán, 0 tải về). Xem `app/assets/hieu_ung/NGUON_GIAY_PHEP.md`.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

#: Chuẩn hoá màu + SAR TRƯỚC `hwupload`. Thiếu dòng này là bẫy #2 ở docstring.
CHUAN_HOA = ("format=yuv420p,setsar=1,"
             "setparams=range=tv:colorspace=bt709:"
             "color_primaries=bt709:color_trc=bt709")

#: Đuôi BẮT BUỘC sau `hwupload`/`xfade_opencl` — đánh lại mốc thời gian theo SỐ
#: THỨ TỰ khung. Xem "BẪY SỐ 0" ở docstring: thiếu nó là **0 khung**, thay bằng
#: `fps=` là **19 GB RAM + treo vĩnh viễn**. Đừng gỡ, đừng đổi sang `fps=`.
VE_LAI_MOC = "hwdownload,format=yuv420p,setpts=N/FR/TB"


def dau_vao(fps: float = 30.0) -> str:
    """Chuỗi filter cho MỖI đầu vào, đặt TRƯỚC `hwupload`.

    **`settb=1/fps` là phần QUYẾT ĐỊNH — xem "BẪY SỐ 1/2 TIMEBASE" ở docstring.**
    Không có nó thì `xfade_opencl` chạy hết chuyển cảnh trong ĐÚNG 1 khung (đo:
    'khác B' = 0% ở cả 15/15 khung, tức khung nào cũng là đoạn B).

    `fps=` đặt ở ĐÂY (trước `hwupload`, khi mốc còn tốt) là an toàn; đặt SAU
    `hwdownload` mới là chỗ gây 19 GB RAM.
    """
    f = max(1.0, float(fps or 30.0))
    return f"{CHUAN_HOA},fps={f:g},settb=1/{f:g}"

_CO: dict = {}          # cache phát hiện: {"opencl": bool, "vulkan": bool}
_CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def duong_kernel() -> str:
    """File .cl chứa kernel gl-transitions (rỗng nếu không có -> tự tắt nhóm)."""
    p = _root() / "app" / "assets" / "hieu_ung" / "gl_transitions.cl"
    return str(p) if p.is_file() else ""


def thu_muc_shader() -> str:
    p = _root() / "app" / "assets" / "hieu_ung" / "shaders"
    return str(p) if p.is_dir() else ""


def duong_filter(p: str) -> str:
    r"""Đường dẫn Windows -> dạng nhét được vào chuỗi filter (`C:` -> `C\:`).

    Bẫy #3 ở docstring module. Giống `hieu_ung.duong_filter`, để riêng cho khỏi
    phụ thuộc vòng.
    """
    return str(p).replace("\\", "/").replace(":", "\\:")


def _ffmpeg() -> str:
    try:
        from config import settings
        return settings.FFMPEG_PATH
    except Exception:                                        # noqa: BLE001
        return str(_root() / "bin" / "ffmpeg.exe")


def _chay(args: list, giay: int = 90) -> tuple[int, str]:
    """Chạy 1 lệnh ffmpeg, KHÔNG BAO GIỜ ném lỗi (trả (rc, log cuối))."""
    try:
        p = subprocess.run([_ffmpeg(), "-y", "-hide_banner", "-v", "error",
                            *[str(x) for x in args]],
                           capture_output=True, text=True, errors="replace",
                           timeout=giay, creationflags=_CNW)
        return p.returncode, (p.stderr or "")[-400:]
    except Exception as e:                                   # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


# =====================================================================
#  PHÁT HIỆN MÁY — chạy 1 lần, cache, không bao giờ nổ lỗi
# =====================================================================
def _dem_khung(p: str) -> int:
    """Số khung ĐỌC ĐƯỢC của file (0 nếu hỏng/không có). Không bao giờ ném lỗi."""
    try:
        from config import settings
        fp = settings.FFPROBE_PATH
    except Exception:                                        # noqa: BLE001
        fp = str(_root() / "bin" / "ffprobe.exe")
    try:
        r = subprocess.run([fp, "-v", "error", "-select_streams", "v:0",
                            "-count_frames", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", p],
                           capture_output=True, text=True, timeout=60,
                           creationflags=_CNW)
        s = (r.stdout or "").strip().splitlines()
        return int(s[0]) if s and s[0].strip().isdigit() else 0
    except Exception:                                        # noqa: BLE001
        return 0


def co_opencl(do_lai: bool = False) -> bool:
    """Máy này chạy được `xfade_opencl` với kernel tự viết hay không.

    KHÔNG chỉ hỏi "ffmpeg có filter không" (bẫy `0,03 CPU-giây`: có filter mà
    lệnh vẫn fail) — mà **render thật 1 chuyển cảnh rồi ĐẾM KHUNG RA**. Máy nhân
    viên không có OpenCL -> False -> app tự dùng CPU.

    **VÌ SAO PHẢI ĐẾM KHUNG chứ không chỉ xem `rc` + kích thước file:** bẫy số 0
    ở docstring module — `xfade_opencl` trả PTS rác thì `rc=0`, file VẪN có kích
    thước, mà bên trong **0 khung**. Bản kiểm cũ chỉ xem `rc`+`size` nên báo
    `OpenCL=True` trong khi mọi kiểu đều ra clip rỗng. Cửa "fallback êm" mà báo
    nhầm thì app bật nhóm GPU hỏng trên máy user — tệ hơn là tắt hẳn.
    """
    if "opencl" in _CO and not do_lai:
        return _CO["opencl"]
    ok = False
    ker = duong_kernel()
    if ker:
        td = tempfile.mkdtemp(prefix="_gpuchk_")
        out = os.path.join(td, "o.mp4")
        rc, _log = _chay([
            "-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
            "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=0.2",
            "-f", "lavfi", "-i", "smptebars=s=64x64:r=30:d=0.2",
            "-filter_complex",
            f"[0:v]{dau_vao(30)},hwupload[a];[1:v]{dau_vao(30)},hwupload[b];"
            f"[a][b]xfade_opencl=transition=custom:"
            f"source='{duong_filter(ker)}':kernel=kiem_chieu:"
            f"duration=0.2:offset=0[o];[o]{VE_LAI_MOC}[v]",
            # TRẦN CỨNG số khung: nếu bản ffmpeg nào đó lại sinh khung vô tận
            # thì lệnh KIỂM cũng không được phép ăn hết RAM máy anh Hùng.
            "-map", "[v]", "-frames:v", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        ok = (rc == 0 and os.path.exists(out) and _dem_khung(out) >= 5)
        try:
            import shutil
            shutil.rmtree(td, ignore_errors=True)
        except Exception:                                    # noqa: BLE001
            pass
    _CO["opencl"] = ok
    return ok


def co_libplacebo(do_lai: bool = False) -> bool:
    """Máy này chạy được `libplacebo` + shader GLSL tự viết hay không (Vulkan)."""
    if "vulkan" in _CO and not do_lai:
        return _CO["vulkan"]
    ok = False
    sh = os.path.join(thu_muc_shader(), "tuong_phan.hook")
    if os.path.isfile(sh):
        td = tempfile.mkdtemp(prefix="_lpchk_")
        out = os.path.join(td, "o.mp4")
        rc, _log = _chay([
            "-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk",
            "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=0.2",
            "-filter_complex",
            f"[0:v]format=yuv420p,hwupload[x];"
            f"[x]libplacebo=custom_shader_path='{duong_filter(sh)}'[o];"
            f"[o]hwdownload,format=yuv420p[v]",
            "-map", "[v]", "-frames:v", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        # ĐẾM KHUNG, không chỉ xem rc+size — cùng lý do ở `co_opencl`.
        # (libplacebo GIỮ ĐÚNG PTS, đo 30/30 khung, nên không cần `setpts`.)
        ok = (rc == 0 and os.path.exists(out) and _dem_khung(out) >= 5)
        try:
            import shutil
            shutil.rmtree(td, ignore_errors=True)
        except Exception:                                    # noqa: BLE001
            pass
    _CO["vulkan"] = ok
    return ok


# =====================================================================
#  KHO CHUYỂN CẢNH GPU (kernel OpenCL, nguồn gl-transitions — MIT)
# =====================================================================
@dataclass(frozen=True)
class ChuyenCanhGPU:
    khoa: str          # tên `__kernel` trong gl_transitions.cl
    ten: str           # tên TIẾNG VIỆT, ghi theo cái MẮT THẤY (đã xem khung)
    capcut: str        # tên tương đương trong CapCut (để anh Hùng đối chiếu)
    goc: str           # tên gốc trong gl-transitions + tác giả


#: **21 kernel ĐÃ ĐO ĐẠT** (render thật + đếm pixel + đo U/V, xem
#: `_do_gpu_chuyen_canh.py` -> `_ket_gpu.json`). Tên tiếng Việt ghi theo cái MẮT
#: THẤY sau khi render khung thật — KHÔNG theo tên gốc (trục y ảnh OpenCL đi từ
#: TRÊN xuống, GLSL từ dưới lên nên "lên/xuống" bị đảo).
#:
#: **3 kernel VIẾT RỒI NHƯNG KHÔNG ĐƯA VÀO KHO** (mã vẫn nằm trong
#: `gl_transitions.cl` để đối chiếu, nhưng app KHÔNG bao giờ chọn) — lý do là SỐ
#: ĐO, không phải cảm tính:
#:   · `gl_dom_tron` (polka dots curtain) — khung GIỮA đã giống đoạn B tới
#:     94,4% (đo "khác B" 5,6%): bản gốc gl-transitions vốn phủ hết trong ~1/3
#:     đầu, nhìn ra thành cắt khô chứ không phải chuyển cảnh.
#:   · `gl_hut_giua` (simplezoom) — lệch màu U+3,3 V−3,6, **vượt trần U/V < 3**.
#:   · `gl_chong_toi` (fadecolor) — lệch màu U−21,7 V−43,3 (nó tối sầm giữa
#:     chừng). Muốn kiểu này thì đã có `fadeblack` của `xfade` CPU, không cần.
KHO_GPU: dict = {h.khoa: h for h in (
    ChuyenCanhGPU("gl_crosswarp", "Méo đẩy vào nhau", "Warp", "crosswarp · Eke Péter"),
    ChuyenCanhGPU("gl_gat_trai", "Gạt mềm sang trái", "Swipe", "directional · gre"),
    ChuyenCanhGPU("gl_gat_len", "Gạt mềm lên trên", "Swipe Up", "directional · gre"),
    ChuyenCanhGPU("gl_gat_cheo_meo", "Gạt chéo có méo", "Warp Swipe", "directionalwarp · pschroen"),
    ChuyenCanhGPU("gl_gio", "Gió thổi vệt ngang", "Wind", "wind · gre"),
    ChuyenCanhGPU("gl_gon_song", "Gợn sóng lan từ giữa", "Ripple", "ripple · gre"),
    ChuyenCanhGPU("gl_vo_o", "Vỡ ô rồi hiện lại", "Pixel Glitch", "pixelize · gre"),
    ChuyenCanhGPU("gl_luoi_vuong", "Lưới ô vuông quét chéo", "Grid Wipe", "squareswire · gre"),
    ChuyenCanhGPU("gl_quat_quay", "Quạt quay quét vòng", "Clock Wipe", "radial · Xaychru"),
    ChuyenCanhGPU("gl_gach_cheo", "Gạch chéo quét qua", "Diagonal", "diagonal"),
    ChuyenCanhGPU("gl_nhoe_mo", "Nhoè mờ chuyển cảnh", "Blur Dissolve", "crossblur"),
    ChuyenCanhGPU("gl_xoay_tron", "Xoay tròn đổi cảnh", "Spin", "rotate"),
    ChuyenCanhGPU("gl_bien_hinh", "Biến hình mềm", "Morph", "morph"),
    ChuyenCanhGPU("gl_soc_doc", "Sọc dọc kéo màn", "Blinds", "verticalstripes"),
    ChuyenCanhGPU("gl_o_ngau", "Ô vuông hiện ngẫu nhiên", "Random Squares", "randomsquares"),
    ChuyenCanhGPU("gl_giot_nuoc", "Giọt nước lan", "Water Drop", "waterdrop"),
    ChuyenCanhGPU("gl_kim_dong_ho", "Kim đồng hồ quét", "Clock", "angular"),
    ChuyenCanhGPU("gl_vong_mo", "Vòng mờ loang", "Radial Blur", "radialblur"),
    ChuyenCanhGPU("gl_chong_chong", "Chong chóng quay", "Pinwheel", "pinwheel"),
    ChuyenCanhGPU("gl_troi_mem", "Trôi mềm sang bên", "Smooth Slide", "swap"),
    ChuyenCanhGPU("gl_giat_khoi", "Giật khối glitch", "Glitch", "glitchmemories"),
)}


def dung_duoc(do_lai: bool = False) -> list[str]:
    """Danh sách khoá chuyển cảnh GPU DÙNG ĐƯỢC trên máy này.

    Máy không có OpenCL / thiếu file .cl -> **[]** (app tự dùng `xfade` CPU,
    KHÔNG một dòng lỗi). Đây là cửa "fallback êm" duy nhất mà caller cần biết.
    """
    if not duong_kernel() or not co_opencl(do_lai):
        return []
    return list(KHO_GPU.keys())


def thong_ke() -> dict:
    return {"tong_kho": len(KHO_GPU), "dung_duoc": len(dung_duoc()),
            "co_opencl": co_opencl(), "co_libplacebo": co_libplacebo()}


# =====================================================================
#  DỰNG LỆNH: chuyển cảnh GPU cho ĐÚNG VÙNG CHỒNG
# =====================================================================
def lenh_vung_chong(vao_a: str, vao_b: str, ra: str, kieu: str, d: float,
                    enc: Optional[list] = None, fps: float = 0.0,
                    am: bool = False) -> list:
    """Args ffmpeg dựng ĐÚNG `d` giây chuyển cảnh GPU từ 2 file dài đúng `d`.

    Vì sao chỉ làm vùng chồng chứ không cả clip: **bẫy #1** ở docstring module
    (2 `hwupload` = 2 ngữ cảnh khung -> ffmpeg chết ngay khi hết chuyển cảnh và
    ra clip CỤT trong im lặng). Vùng chồng thì không có khung nào chạy tiếp.

    Caller ghép: `A[0 .. dài(A)-d]` + `<file này>` + `B[d .. hết]`.

    `fps` (nếu biết) -> thêm **trần cứng `-frames:v`**. Không bắt buộc cho đúng
    đắn (đã có `setpts=N/FR/TB`), nhưng là cái phanh cuối cùng cho tai nạn 19 GB
    ở bẫy số 0: dù filter có sinh khung vô tận thì ffmpeg vẫn dừng đúng chỗ.
    """
    if kieu not in KHO_GPU:
        raise ValueError(f"kiểu chuyển cảnh GPU không có trong kho: {kieu!r}")
    ker = duong_kernel()
    if not ker:
        raise RuntimeError("thiếu app/assets/hieu_ung/gl_transitions.cl")
    dv = dau_vao(fps or 30.0)
    graph = (f"[0:v]{dv},hwupload[a];[1:v]{dv},hwupload[b];"
             f"[a][b]xfade_opencl=transition=custom:"
             f"source='{duong_filter(ker)}':kernel={kieu}:"
             f"duration={d:.3f}:offset=0[o];"
             f"[o]{VE_LAI_MOC}[v]")
    # `am=True`: mảnh chuyển cảnh phải MANG THEO TIẾNG, nếu không thì đường
    # ghép-3-mảnh ra clip **mất tiếng đúng chỗ nối** (concat demuxer đòi mọi
    # mảnh cùng số luồng). `acrossfade` c1/c2=tri y hệt nhánh CPU `_graph_xfade`
    # nên tiếng ở chỗ nối nghe giống nhau dù hình chạy GPU hay CPU.
    if am:
        graph += f";[0:a][1:a]acrossfade=d={d:.3f}:c1=tri:c2=tri[a]"
    tran = (["-frames:v", str(int(d * fps) + 3)] if fps > 0 else [])
    return ["-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
            "-i", str(vao_a), "-i", str(vao_b),
            "-filter_complex", graph, "-map", "[v]",
            *(["-map", "[a]"] if am else []), *tran,
            *(enc or ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                      "-pix_fmt", "yuv420p"]), str(ra)]


def lenh_shader(vao: str, ra: str, shader: str,
                enc: Optional[list] = None) -> list:
    """Args ffmpeg áp 1 shader GLSL (libplacebo, GPU) lên `vao`."""
    p = shader if os.path.isfile(shader) else os.path.join(thu_muc_shader(),
                                                           shader)
    if not os.path.isfile(p):
        raise RuntimeError(f"không có shader {shader!r}")
    graph = (f"[0:v]format=yuv420p,hwupload[x];"
             f"[x]libplacebo=custom_shader_path='{duong_filter(p)}'[o];"
             f"[o]hwdownload,format=yuv420p[v]")
    return ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk",
            "-i", str(vao), "-filter_complex", graph, "-map", "[v]",
            *(enc or ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                      "-pix_fmt", "yuv420p"]), str(ra)]


def shader_co(  ) -> list[str]:
    """Tên các shader GLSL có trên đĩa (rỗng nếu máy không chạy được Vulkan)."""
    d = thu_muc_shader()
    if not d or not co_libplacebo():
        return []
    try:
        return sorted(f for f in os.listdir(d) if f.endswith(".hook"))
    except OSError:
        return []


if __name__ == "__main__":       # xem nhanh máy này kham được gì
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    tk = thong_ke()
    print(f"OpenCL: {tk['co_opencl']} · libplacebo/Vulkan: {tk['co_libplacebo']}")
    print(f"kho chuyển cảnh GPU {tk['tong_kho']} · dùng được {tk['dung_duoc']}")
    print(f"shader: {shader_co()}")
