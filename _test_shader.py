# -*- coding: utf-8 -*-
r"""CỔNG 41 — NHÓM HIỆU ỨNG **SHADER GPU** (`libplacebo` + 6 file `.hook`).

Chạy: `.venv\Scripts\python _test_shader.py`

=== VÌ SAO CÓ CỔNG NÀY ===
6 shader `app/assets/hieu_ung/shaders/*.hook` **đóng gói vào .exe từ
08/08/2026 mà KHÔNG nối vào đường xuất** — hồ sơ ghi lý do: *"`libplacebo`
không có timeline `enable` -> áp là áp TOÀN CLIP, trái luật chống loè số 1"*.
Tài nguyên nằm trong bản phát hành mà không một dòng mã nào gọi tới = thứ
KHÔNG AI PHÁT HIỆN ĐƯỢC khi nó hỏng. Cổng này vừa nối vừa canh.

**CÁCH VÒNG QUA `enable`** (đã đo cả 2, xem `_SH_MAU` trong `hieu_ung.py`):
  (C) `split` + nhánh shader CẢ CLIP + `overlay` có `enable` -> đúng nhưng
      **2,18x wall · 1,41x CPU-giây**. LOẠI.
  (D) `trim` CHỈ cửa sổ điểm nhấn -> GPU -> `concat` nối lại ->
      **1,16x wall · 1,01x CPU-giây**. ĐANG DÙNG.
Ca H1 quét tĩnh để không ai "dọn dẹp" (D) về (C).

=== 3 BẪY ĐÃ SẬP KHI LÀM, MỖI CÁI 1 CA ===
1. **`blend` bật ngược.** Dựng `[shader][gốc]blend=all_opacity=…:enable=…`
   thì lúc `enable=0` filter cho qua đầu vào **THỨ NHẤT** = bản CÓ shader ->
   hiệu ứng phủ TOÀN CLIP còn trong cửa sổ lại nhạt đi. Đo: ngoài cửa sổ
   **34,45%** pixel lệch, trong cửa sổ **4,29%** — đúng ngược. rc=0, đủ 92
   khung, không một dòng lỗi. Ca B canh chiều này.
2. **`libplacebo` không tự mở được Vulkan** trong bản `bin/ffmpeg.exe` này:
   *"No `vkGetInstanceProcAddr` function provided"*. Bắt buộc phải có
   `-init_hw_device vulkan=vk -filter_hw_device vk` trên DÒNG LỆNH. May là nó
   FAIL TO (rc!=0, không ra file) chứ không im lặng.
3. **2 shader trong 1 clip dùng TRÙNG NHÃN** `[q0a]` -> ffmpeg báo "Duplicate
   output pad" và chết cả lượt xuất. Ca D canh.

=== BẪY ĐO (kế thừa cổng 36/37/38, đừng lặp) ===
· mốc cắt phải ở **CẢNH SÁNG** (nguồn Nhật giây 20 sáng TB 3,3/255 -> đếm
  pixel ra ~0 và FAIL OAN). Dùng mốc 100s.
· so 2 file **mp4** thì nhiễu rate-control che mất/phóng đại lệch thật ->
  mọi phép so ở đây render **x264 `-qp 0` (LOSSLESS)**.
· **ĐẾM KHUNG bằng ffprobe** sau mọi lần xuất — `rc=0` không chứng minh gì
  (bài học `xfade_opencl`: rc=0, file có kích thước, bên trong 0 khung).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_shader_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

import numpy as np  # noqa: E402

import _nguon_nhat  # noqa: E402
from app.core import ffmpeg_utils as fu  # noqa: E402
from app.core import hieu_ung as HU  # noqa: E402
from app.core import hieu_ung_gpu as HG  # noqa: E402
from config import settings  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_NOWIN = 0x08000000
_OK: list[str] = []
_LOI: list[str] = []
W, H = 1080, 1920           # ĐÚNG khung sản xuất — bán kính mờ/nét là SỐ PIXEL
FPS = 30
GIAY = 6.0
BAT = 2.0                   # mốc bắt đầu cửa sổ điểm nhấn (giây)


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, creationflags=_NOWIN)
    s = (r.stdout or "").strip().splitlines()
    return int(s[0]) if s and s[0].strip().isdigit() else 0


def dai(p: str) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, text=True, creationflags=_NOWIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def khung(p: str, t: float):
    """1 khung ở giây `t`, dạng YUV int16 (3,H,W). `-ss` SAU `-i` = tìm CHÍNH XÁC."""
    raw = _SB / f"k{abs(hash((str(p), t))) % 10 ** 9}.raw"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(p), "-ss", f"{t:.3f}",
                    "-frames:v", "1", "-pix_fmt", "yuv444p", "-f", "rawvideo",
                    str(raw)], capture_output=True, creationflags=_NOWIN)
    if not raw.exists() or raw.stat().st_size < W * H * 3:
        return None
    d = np.fromfile(raw, dtype=np.uint8)
    os.unlink(raw)
    return d[: W * H * 3].reshape(3, H, W).astype(np.int16)


def so_khung(a, b) -> dict:
    """% pixel |dY|>12 · lệch U/V trung bình · PSNR. a = gốc, b = có hiệu ứng."""
    if a is None or b is None:
        return {"pct": -1.0, "du": 99.0, "dv": 99.0, "psnr": -1.0}
    d = b.astype(float) - a.astype(float)
    mse = float(np.mean(d ** 2))
    return {"pct": round(float(np.mean(np.abs(d[0]) > 12)) * 100.0, 2),
            "du": round(float(np.mean(d[1])), 2),
            "dv": round(float(np.mean(d[2])), 2),
            "psnr": round(99.0 if mse < 1e-9 else
                          float(10 * np.log10(255 * 255 / mse)), 2)}


# ---------------------------------------------------------------- NGUỒN THẬT
def nguon() -> str:
    """6 giây phim THẬT ở mốc 100s (CẢNH SÁNG), cắt về đúng khung dọc 1080x1920."""
    p = _SB / "goc.mkv"
    if p.exists():
        return str(p)
    ds = _nguon_nhat.liet_ke()
    if not ds:
        print("KHÔNG có video Nhật thật trên máy -> cổng này không chạy được "
              "(quy tắc sắt: thành phần THẬT, cấm mock).")
        sys.exit(2)
    subprocess.run(
        [FF, "-y", "-v", "error", "-ss", "100", "-t", f"{GIAY:g}",
         "-i", ds[9] if len(ds) > 9 else ds[0],
         "-vf", f"crop=ih*9/16:ih,scale={W}:{H},setsar=1",
         "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode:v", "cfr",
         "-an", str(p)], capture_output=True, creationflags=_NOWIN)
    return str(p)


def render(ten: str, src: str, chuoi: str, vk: bool) -> tuple[str, int, str]:
    """Chạy ffmpeg với ĐÚNG chuỗi filter mà app dựng ra. LOSSLESS -> so được."""
    out = _SB / f"{ten}.mkv"
    cmd = [FF, "-y", "-v", "error"]
    if vk:
        cmd += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
    g = f"[0:v]null[v]" if not chuoi else f"[0:v]{chuoi}[v]"
    cmd += ["-i", str(src), "-an", "-filter_complex", g, "-map", "[v]",
            "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0",
            "-pix_fmt", "yuv420p", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       creationflags=_NOWIN)
    return str(out), r.returncode, (r.stderr or "")[-300:]


# =====================================================================
#  A — libplacebo CHẠY THẬT (bẫy rc=0 mà 0 khung) + ống dẫn KHÔNG đổi màu
# =====================================================================
def ca_a(src: str) -> None:
    print("\n[CA A] libplacebo chạy THẬT + bản thân nó KHÔNG đổi màu")
    n0 = dem_khung(src)
    bao("dò máy `co_libplacebo()` (render thật + đếm khung)",
        HG.co_libplacebo() is True, f"{HG.co_libplacebo()}")
    if not HG.co_libplacebo():
        print("     -> máy này không có Vulkan; các ca B/D/E sẽ bỏ qua.")
        return
    # ĐỐI CHỨNG: libplacebo KHÔNG shader. Bắt buộc — nếu chính cái ống dẫn đã
    # đổi màu/tone thì mọi số của 6 shader bên dưới là số của nó, không phải
    # của shader.
    o, rc, log = render(
        "doi_chung", src,
        "format=yuv420p,hwupload,libplacebo,hwdownload,format=yuv420p", True)
    n = dem_khung(o)
    d = so_khung(khung(src, 3.0), khung(o, 3.0))
    bao("libplacebo KHÔNG shader: đủ khung (không phải bẫy rc=0/0 khung)",
        rc == 0 and n == n0 and n > 0, f"rc={rc} · {n}/{n0} khung · {log[:80]}")
    bao("libplacebo KHÔNG shader: KHÔNG tự đổi màu (dU,dV < 1,0)",
        abs(d["du"]) < 1.0 and abs(d["dv"]) < 1.0,
        f"dU {d['du']} · dV {d['dv']} · PSNR {d['psnr']} dB · "
        f"{d['pct']}% pixel")


# =====================================================================
#  B — 6 SHADER: THẤY ĐƯỢC trong cửa sổ · KHÔNG RÒ ra ngoài · KHÔNG LOÈ MÀU
# =====================================================================
def ca_b(src: str) -> None:
    print("\n[CA B] 6 shader: thấy được · không rò ngoài cửa sổ · không loè màu")
    if not HG.co_libplacebo():
        return
    n0 = dem_khung(src)
    goc_tr, goc_ng1, goc_ng2 = (khung(src, BAT + 0.15), khung(src, 0.60),
                                khung(src, 5.20))
    sh = [k for k, h in HU.KHO.items() if h.shader]
    bao("đủ 6 shader trong kho", len(sh) == 6, f"{len(sh)}: {sorted(sh)}")
    for k in sorted(sh):
        h = HU.KHO[k]
        het = BAT + max(HU.DAI_MIN, min(HU.DAI_MAX, h.dai))
        # mức 'nhe' = mặc định của 200-300 kênh -> phải THẤY ĐƯỢC ngay ở đây,
        # không được chỉ đẹp ở mức 'manh'.
        chuoi = HU.chuoi_filter(
            [{"bat": BAT, "het": het, "khoa": k, "dam": HU.MUC_DAM["nhe"]}],
            W, H, FPS)
        o, rc, log = render(f"b_{k}", src, chuoi, True)
        n = dem_khung(o)
        if rc != 0 or n < 1:
            bao(f"{k}: ra file có khung", False,
                f"rc={rc} · {n} khung · {log[:150]}")
            continue
        tr = so_khung(goc_tr, khung(o, BAT + 0.15))
        ng1 = so_khung(goc_ng1, khung(o, 0.60))
        ng2 = so_khung(goc_ng2, khung(o, 5.20))
        bao(f"{k}: số khung + độ dài GIỮ NGUYÊN",
            n == n0 and abs(dai(o) - dai(src)) < 0.040,
            f"{n}/{n0} khung · {dai(o):.3f}s vs {dai(src):.3f}s")
        bao(f"{k}: THẤY ĐƯỢC ở mức 'nhe' (>= {h.nguong_thay}% pixel)",
            tr["pct"] >= h.nguong_thay,
            f"{tr['pct']}% pixel |dY|>12 · PSNR {tr['psnr']} dB")
        bao(f"{k}: KHÔNG LOÈ MÀU (|dU|,|dV| < {HU.UV_MAX})",
            abs(tr["du"]) < HU.UV_MAX and abs(tr["dv"]) < HU.UV_MAX,
            f"dU {tr['du']} · dV {tr['dv']}")
        # LUẬT 1 — đây là ca bắt bẫy "blend bật ngược" (ngoài 34%, trong 4%)
        bao(f"{k}: KHÔNG RÒ ra ngoài cửa sổ (2 mốc, trước và sau)",
            ng1["pct"] < 0.01 and ng2["pct"] < 0.01
            and ng1["psnr"] > 60 and ng2["psnr"] > 60,
            f"giây 0,60: {ng1['pct']}% / {ng1['psnr']} dB · "
            f"giây 5,20: {ng2['pct']}% / {ng2['psnr']} dB")


# =====================================================================
#  C — BẤT BIẾN SỐNG CÒN: KHÔNG shader -> lệnh ffmpeg KHÔNG có Vulkan
# =====================================================================
def ca_c(src: str) -> None:
    print("\n[CA C] BẤT BIẾN: không shader -> KHÔNG mở Vulkan, chuỗi y như cũ")
    cpu = [{"bat": 1.0, "het": 1.4, "khoa": "zoom_nhoi", "dam": 0.18}]
    gpu = [{"bat": 1.0, "het": 1.4, "khoa": "sh_net_hon", "dam": 0.18}]
    bao("`can_vulkan([])` = False (mức Tắt)", HU.can_vulkan([]) is False, "[]")
    bao("`can_vulkan` bộ TOÀN hiệu ứng CPU = False",
        HU.can_vulkan(cpu) is False, "zoom_nhoi")
    bao("`can_vulkan` bộ CÓ shader = True", HU.can_vulkan(gpu) is True,
        "sh_net_hon")
    bao("`bo_shader` giữ CPU, bỏ đúng shader",
        [c["khoa"] for c in HU.bo_shader(cpu + gpu)] == ["zoom_nhoi"],
        f"{[c['khoa'] for c in HU.bo_shader(cpu + gpu)]}")
    # chuỗi filter của MỌI hiệu ứng CPU không được dính một chữ libplacebo nào
    s = HU.chuoi_filter([{"bat": 1.0, "het": 1.4, "khoa": k, "dam": 0.18}
                         for k in ("zoom_nhoi", "loe_sang", "toi_vien")],
                        W, H, FPS)
    bao("chuỗi hiệu ứng CPU KHÔNG chứa libplacebo/hwupload",
        "libplacebo" not in s and "hwupload" not in s, f"{len(s)} ký tự")
    # và bộ CÓ shader phải ra chuỗi chạy được KHI ĐÃ mở Vulkan, KHÔNG chạy được
    # khi CHƯA mở -> chứng minh cửa `can_vulkan` là bắt buộc, không phải trang trí
    if HG.co_libplacebo():
        g = HU.chuoi_filter(gpu, W, H, FPS)
        _o1, rc1, _l1 = render("c_co_vk", src, g, True)
        _o2, rc2, log2 = render("c_khong_vk", src, g, False)
        bao("chuỗi shader: CÓ `-init_hw_device vulkan` -> chạy; KHÔNG có -> "
            "FAIL TO (không im lặng ra clip trơn)",
            rc1 == 0 and rc2 != 0 and dem_khung(_o2) == 0,
            f"rc có VK={rc1} · rc không VK={rc2} · {log2[:90]}")


# =====================================================================
#  D — 2 SHADER TRONG 1 CLIP (bẫy trùng nhãn) + mốc rơi ĐÚNG chỗ
# =====================================================================
def ca_d(src: str) -> None:
    print("\n[CA D] 2 shader trong 1 clip: nhãn KHÔNG trùng, mốc ĐÚNG chỗ")
    if not HG.co_libplacebo():
        return
    n0 = dem_khung(src)
    chon = [{"bat": 1.0, "het": 1.6, "khoa": "sh_hat_phim", "dam": 0.25},
            {"bat": 3.5, "het": 3.9, "khoa": "sh_tuong_phan", "dam": 0.25},
            {"bat": 4.8, "het": 5.2, "khoa": "loe_sang", "dam": 0.25}]
    s = HU.chuoi_filter(chon, W, H, FPS)
    o, rc, log = render("d_hai_shader", src, s, True)
    n = dem_khung(o)
    bao("3 hiệu ứng (2 shader + 1 CPU) trong 1 clip: chạy được",
        rc == 0 and n == n0, f"rc={rc} · {n}/{n0} khung · {log[:120]}")
    bao("độ dài GIỮ NGUYÊN sau 2 lần trim+concat",
        abs(dai(o) - dai(src)) < 0.040, f"{dai(o):.3f}s vs {dai(src):.3f}s")
    if rc != 0:
        return
    for ten, t, phai_doi in (("shader 1 (giây 1,2)", 1.2, True),
                             ("giữa 2 shader (giây 2,5)", 2.5, False),
                             ("shader 2 (giây 3,6)", 3.6, True),
                             ("sau cùng (giây 5,6)", 5.6, False)):
        d = so_khung(khung(src, t), khung(o, t))
        ok = (d["pct"] >= 5.0) if phai_doi else (d["pct"] < 0.01)
        bao(f"mốc {ten}: {'ĐỔI' if phai_doi else 'y hệt gốc'}", ok,
            f"{d['pct']}% pixel · PSNR {d['psnr']} dB")


# =====================================================================
#  E — CA BIÊN: cửa sổ Ở NGAY ĐẦU clip (mảnh trước RỖNG) và SÁT CUỐI
# =====================================================================
def ca_e(src: str) -> None:
    print("\n[CA E] ca biên: cửa sổ ở NGAY ĐẦU (mảnh trước rỗng) và SÁT CUỐI")
    if not HG.co_libplacebo():
        return
    n0, d0 = dem_khung(src), dai(src)
    for ten, a, b in (("đầu clip", 0.0, 0.45),
                      ("sát cuối", GIAY - 0.50, GIAY - 0.05)):
        s = HU.chuoi_filter(
            [{"bat": a, "het": b, "khoa": "sh_hat_phim", "dam": 0.25}],
            W, H, FPS)
        o, rc, log = render(f"e_{abs(hash(ten)) % 999}", src, s, True)
        n = dem_khung(o)
        bao(f"cửa sổ {ten} ({a:.2f}-{b:.2f}s): đủ khung + đúng độ dài",
            rc == 0 and n == n0 and abs(dai(o) - d0) < 0.040,
            f"rc={rc} · {n}/{n0} khung · {dai(o):.3f}s vs {d0:.3f}s · "
            f"{log[:80]}")
        d = so_khung(khung(src, (a + b) / 2), khung(o, (a + b) / 2))
        bao(f"cửa sổ {ten}: hiệu ứng CÓ chạy", d["pct"] >= 5.0,
            f"{d['pct']}% pixel ở giây {(a + b) / 2:.2f}")


# =====================================================================
#  F — FALLBACK ÊM: máy nhân viên KHÔNG Vulkan / công tắc BQ_SHADER=0
# =====================================================================
def ca_f(src: str) -> None:
    print("\n[CA F] fallback ÊM: không Vulkan / BQ_SHADER=0 -> tự bỏ, KHÔNG lỗi")
    that = HG._CO.copy()
    try:
        HG._CO["vulkan"] = False            # giả máy nhân viên không có Vulkan
        dd = HU.dung_duoc()
        bao("không Vulkan -> `dung_duoc()` KHÔNG còn shader nào, KHÔNG nổ lỗi",
            not any(k.startswith("sh_") for k in dd),
            f"{len(dd)} hiệu ứng, shader còn "
            f"{sum(1 for k in dd if k.startswith('sh_'))}")
        chon = HU.chon_hieu_ung(20.0, "manh", nl=[0.1] * 20, cd=[0.1] * 20,
                                moc_noi=[6.0, 13.0], co_the_dung=dd)
        bao("không Vulkan -> AI chọn KHÔNG bao giờ ra shader",
            not any(str(c["khoa"]).startswith("sh_") for c in chon),
            f"{[c['khoa'] for c in chon]}")
        bao("không Vulkan -> `can_vulkan` của bộ vừa chọn = False",
            HU.can_vulkan(chon) is False, f"{len(chon)} điểm")
        tk = HU.thong_ke()
        bao("`thong_ke()` báo đúng trạng thái máy",
            tk["co_shader"] is False and tk["shader"] == 0, f"{tk}")
    finally:
        HG._CO.clear()
        HG._CO.update(that)
    # công tắc tay
    cu = os.environ.get("BQ_SHADER")
    try:
        os.environ["BQ_SHADER"] = "0"
        bao("`BQ_SHADER=0` tắt hẳn nhóm shader", HU.co_shader() is False,
            f"co_shader()={HU.co_shader()} · "
            f"shader trong dung_duoc()="
            f"{sum(1 for k in HU.dung_duoc() if k.startswith('sh_'))}")
    finally:
        if cu is None:
            os.environ.pop("BQ_SHADER", None)
        else:
            os.environ["BQ_SHADER"] = cu
    # thiếu FILE .hook (bản đóng gói hụt tài nguyên) -> bỏ hiệu ứng, không dựng
    # chuỗi `custom_shader_path=''` rồi để ffmpeg chết cả lượt
    that2 = HG.duong_shader
    try:
        HG.duong_shader = lambda _t: ""      # type: ignore
        s = HU.chuoi_filter(
            [{"bat": 1.0, "het": 1.4, "khoa": "sh_hat_phim", "dam": 0.25},
             {"bat": 3.0, "het": 3.4, "khoa": "loe_sang", "dam": 0.25}],
            W, H, FPS)
        bao("mất file .hook -> BỎ hiệu ứng đó, giữ hiệu ứng CPU",
            "libplacebo" not in s and "eq=brightness" in s, f"{s[:70]}…")
    finally:
        HG.duong_shader = that2              # type: ignore


# =====================================================================
#  G — LÙI ÊM khi GPU chết GIỮA LÚC XUẤT (đường xuất THẬT, đầu-tới-cuối)
# =====================================================================
def ca_g(src: str) -> None:
    print("\n[CA G] đường xuất THẬT + lùi êm khi shader hỏng giữa chừng")
    enc = fu.detect_encoder()
    o1 = _SB / "g_that.mp4"
    hu = [{"bat": 1.0, "het": 1.6, "khoa": "sh_hat_phim", "dam": 0.25}]
    log: list = []
    try:
        fu.export_canvas_clip(src, str(o1), [(0.0, 5.0)], (0.5, 0.5, 1.0),
                              out_w=540, out_h=960, encoder=enc,
                              fx_fade=False, fx_whoosh=False,
                              hieu_ung=(hu if HG.co_libplacebo() else "nhe"),
                              hieu_ung_log=log)
        n = dem_khung(o1)
        bao("xuất THẬT qua `export_canvas_clip` có shader: ra clip đủ khung",
            n >= 140 and abs(dai(str(o1)) - 5.0) < 0.10,
            f"{n} khung · {dai(str(o1)):.3f}s · nhật ký "
            f"{[c['khoa'] for c in log]}")
    except Exception as e:                                   # noqa: BLE001
        bao("xuất THẬT qua `export_canvas_clip` có shader", False,
            f"{type(e).__name__}: {e}")
    if not HG.co_libplacebo():
        return
    # GPU CHẾT GIỮA CHỪNG. Phải chọn ĐÚNG kiểu hỏng: `.hook` sai CÚ PHÁP thì
    # ffmpeg FAIL TO ("Failed parsing custom shader!", rc!=0) — đó mới là ca
    # nhánh lùi êm phải bắt. `.hook` đúng cú pháp mà chạy không được thì
    # libplacebo IM LẶNG cho qua (xem ca I), lệnh vẫn rc=0 nên KHÔNG kích hoạt
    # nhánh này — dùng nó làm bẫy là test PASS OAN.
    xau = _SB / "hong_cu_phap.hook"
    xau.write_text("day khong phai shader\n", encoding="utf-8")
    that = HG.duong_shader
    o2 = _SB / "g_lui.mp4"
    log2: list = []
    try:
        HG.duong_shader = lambda _t: str(xau)                # type: ignore
        fu.export_canvas_clip(src, str(o2), [(0.0, 5.0)], (0.5, 0.5, 1.0),
                              out_w=540, out_h=960, encoder=enc,
                              fx_fade=False, fx_whoosh=False,
                              hieu_ung=[dict(hu[0]),
                                        {"bat": 3.0, "het": 3.4,
                                         "khoa": "loe_sang", "dam": 0.25}],
                              hieu_ung_log=log2)
        n = dem_khung(o2)
        bao("shader HỎNG giữa lúc xuất -> LÙI ÊM, clip vẫn ra đủ khung",
            n >= 140 and abs(dai(str(o2)) - 5.0) < 0.10,
            f"{n} khung · {dai(str(o2)):.3f}s")
        bao("lùi êm rồi thì NHẬT KÝ phải bỏ shader (không khoe cái không có)",
            not any(str(c.get("khoa", "")).startswith("sh_") for c in log2)
            and any(c.get("khoa") == "loe_sang" for c in log2),
            f"{[c['khoa'] for c in log2]}")
    except Exception as e:                                   # noqa: BLE001
        bao("shader HỎNG giữa lúc xuất -> LÙI ÊM", False,
            f"{type(e).__name__}: {str(e)[:200]}")
    finally:
        HG.duong_shader = that                               # type: ignore


# =====================================================================
#  H — QUÉT TĨNH: không ai được lặng lẽ tháo bản vá ra
# =====================================================================
def ca_h() -> None:
    print("\n[CA H] quét tĩnh: khuôn rẻ · cửa Vulkan · không còn file mồ côi")
    m = HU._SH_MAU
    bao("khuôn shader dùng `trim`+`concat` (cách RẺ 1,16x), KHÔNG phải "
        "`overlay` cả clip (2,18x)",
        "trim=" in m and "concat=" in m and "overlay" not in m,
        f"{len(m)} ký tự")
    bao("khuôn shader có `{i}` (nhãn riêng từng hiệu ứng — chống trùng pad)",
        "{i}" in m, "có")
    fus = (REPO / "app" / "core" / "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    bao("`ffmpeg_utils` mở Vulkan CÓ ĐIỀU KIỆN `_can_vk` (không mở bừa)",
        "if _can_vk:" in fus and "vulkan=vk" in fus
        and "can_vulkan" in fus, "có `if _can_vk:` + `vulkan=vk`")
    bao("`ffmpeg_utils` có nhánh LÙI ÊM `bo_shader`", "bo_shader" in fus,
        "có")
    # ĐÚNG CÁI BỆNH CỔNG NÀY CHỮA: file tài nguyên đóng gói mà KHÔNG mã nào gọi
    d = HG.thu_muc_shader()
    tren_dia = {f for f in os.listdir(d) if f.endswith(".hook")} if d else set()
    trong_kho = {h.shader for h in HU.KHO.values() if h.shader}
    bao("MỌI file .hook đóng gói đều được kho hiệu ứng dùng "
        "(không còn tài nguyên mồ côi)",
        tren_dia == trong_kho and len(tren_dia) == 6,
        f"đĩa {len(tren_dia)} · kho {len(trong_kho)} · "
        f"thừa {sorted(tren_dia - trong_kho)} · thiếu "
        f"{sorted(trong_kho - tren_dia)}")
    spec = (REPO / "BQHungVideo.spec").read_text(encoding="utf-8",
                                                 errors="replace")
    wf = (REPO / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8", errors="replace")
    bao("bản đóng gói (.spec + CI) vẫn mang theo `app/assets/hieu_ung`",
        "app/assets/hieu_ung" in spec and "app/assets/hieu_ung" in wf,
        "cả 2 file đều có")
    # shader phải TỚI ĐƯỢC trong luật chọn, nếu không thì "nối" chỉ là hình thức
    kho_uv = {k for v in HU._UV_THEO_LOAI.values() for k in v}
    thieu = {k for k, h in HU.KHO.items() if h.shader} - kho_uv
    bao("mọi shader đều có mặt trong luật chọn `_UV_THEO_LOAI`",
        not thieu, f"thiếu {sorted(thieu)}" if thieu else "đủ 6")
    # và phải nằm ở 3 VỊ TRÍ ĐẦU của ít nhất 1 loại điểm (xem `_chon_kieu`:
    # chỉ `moi[0..2]` tới được) — đặt cuối danh sách = nối cho có, không dùng
    toi_duoc = {k for v in HU._UV_THEO_LOAI.values() for k in v[:3]
                if k.startswith("sh_")}
    bao("shader nằm ở vị trí AI thật sự chọn tới (3 vị trí đầu)",
        len(toi_duoc) >= 4, f"{len(toi_duoc)}/6 tới được: {sorted(toi_duoc)}")


# =====================================================================
#  I — BẪY "THÀNH CÔNG GIẢ" SỐ 2: shader biên dịch được nhưng CHẠY không được
# =====================================================================
def ca_i(src: str) -> None:
    print("\n[CA I] shader bị libplacebo TỰ TẮT mà rc=0 -> cửa dò phải bắt")
    if not HG.co_libplacebo():
        return
    # `.hook` có `//!HOOK` đúng nhưng thân GLSL sai -> libplacebo in "Failed
    # executing hook, disabling" rồi CHO QUA KHUNG NGUYÊN VẸN. Đo thật:
    # rc=0, đủ khung, kích thước bình thường, mà KHÔNG có hiệu ứng nào.
    xau = _SB / "hong_than.hook"
    xau.write_text("//!HOOK MAIN\n//!BIND HOOKED\n//!DESC hong\n"
                   "vec4 hook() { KHONG PHAI GLSL ; }\n", encoding="utf-8")
    o, rc, _log = render(
        "i_hong", src,
        f"format=yuv420p,hwupload,libplacebo="
        f"custom_shader_path='{HG.duong_filter(str(xau))}',"
        f"hwdownload,format=yuv420p", True)
    n = dem_khung(o)
    d = so_khung(khung(src, 3.0), khung(o, 3.0))
    bao("(mô tả bẫy) shader hỏng THÂN -> rc=0 + đủ khung + KHÔNG hiệu ứng",
        rc == 0 and n == dem_khung(src) and d["pct"] < 0.01,
        f"rc={rc} · {n} khung · chỉ {d['pct']}% pixel đổi -> nếu chỉ xem "
        f"rc+khung thì TƯỞNG chạy tốt")
    # -> vì vậy `co_libplacebo()` KHÔNG được chỉ đếm khung: nó phải đo PIXEL.
    bao("`_shader_chay_that()` chứng minh shader ĐỔI ĐƯỢC pixel thật",
        HG._shader_chay_that() is True, f"{HG._shader_chay_that()}")
    # và khi shader KHÔNG chạy được thì `co_libplacebo()` phải trả False
    that = HG.thu_muc_shader
    try:
        rong = _SB / "shader_rong"
        rong.mkdir(exist_ok=True)
        (rong / "toi_vien.hook").write_text(
            "//!HOOK MAIN\n//!BIND HOOKED\nvec4 hook() { SAI ; }\n",
            encoding="utf-8")
        (rong / "tuong_phan.hook").write_text(
            "//!HOOK MAIN\n//!BIND HOOKED\n//!DESC x\n"
            "vec4 hook() { return HOOKED_tex(HOOKED_pos); }\n",
            encoding="utf-8")
        HG.thu_muc_shader = lambda: str(rong)                # type: ignore
        bao("shader không chạy được -> `co_libplacebo(do_lai=True)` = False "
            "(không báo nhầm là dùng được)",
            HG.co_libplacebo(do_lai=True) is False,
            f"{HG.co_libplacebo()}")
    finally:
        HG.thu_muc_shader = that                             # type: ignore
        HG.co_libplacebo(do_lai=True)   # dò lại bằng thư mục THẬT


def main() -> None:
    print("=" * 74)
    print("CỔNG 41 — NHÓM HIỆU ỨNG SHADER GPU (libplacebo + 6 .hook)")
    print("=" * 74)
    src = nguon()
    print(f"nguồn: {dem_khung(src)} khung · {dai(src):.3f}s · {W}x{H} · "
          f"lossless {os.path.getsize(src) / 1e6:.1f} MB")
    print(f"máy: frei0r={HU.co_frei0r()} · Vulkan/libplacebo="
          f"{HG.co_libplacebo()} · kho {HU.thong_ke()}")
    ca_a(src)
    ca_b(src)
    ca_c(src)
    ca_d(src)
    ca_e(src)
    ca_f(src)
    ca_g(src)
    ca_h()
    ca_i(src)
    print("\n" + "=" * 74)
    print(f"KẾT: {len(_OK)} OK · {len(_LOI)} FAIL")
    for x in _LOI:
        print(f"  FAIL · {x}")
    print("=" * 74)
    sys.exit(1 if _LOI else 0)


if __name__ == "__main__":
    try:
        main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
