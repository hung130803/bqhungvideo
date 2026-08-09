# -*- coding: utf-8 -*-
"""ĐO ỨNG VIÊN HIỆU ỨNG MỚI — 7 cổng, ở ĐÚNG 1080x1920, trên video THẬT.

Vì sao có file này (việc "MỞ RỘNG KHO" 09/08/2026): kho điểm nhấn đang 27 kiểu,
còn ~50 kernel gl-transitions · ~120 plugin frei0r · hàng chục filter có sẵn
trong ffmpeg CHƯA khai thác. Không được thêm bừa: mỗi kiểu phải qua 7 cổng
KIỂM KẾT QUẢ (không kiểm ý định), kiểu nào rớt thì GỠ.

CHẠY:
    .venv\\Scripts\\python _do_kho_moi.py --nhom builtin
    .venv\\Scripts\\python _do_kho_moi.py --nhom frei0r --f0r <thư mục dll>
    .venv\\Scripts\\python _do_kho_moi.py --chi <khoá,khoá>   (đo lại vài kiểu)
Ra: bảng in màn hình + `_ket_kho_moi.json` (gộp thêm, không ghi đè lượt trước).

=== 7 CỔNG (đề bài anh Hùng) ===
1. THẤY ĐƯỢC   : >= 8% điểm ảnh |dY|>12 trong cửa sổ (`NG_THAY`)
2. ĐÚNG CHIỀU  : khai trước SÁNG/TỐI/GIỮ rồi đo `ty_day`/`ty_dinh` có đúng không
3. KHÔNG LOÈ   : |dU|,|dV| trung bình < 3,0 (luật 3) + lệch TỪNG ĐIỂM có trần
4. KHÔNG ĐEN   : không khung nào < 35% độ sáng bản gốc
5. KHÔNG RÒ    : ngoài cửa sổ ~ 0,00% điểm ảnh đổi
6. KHÔNG GIẢ   : ffprobe ĐẾM KHUNG THẬT, phải bằng bản gốc
7. CHI PHÍ     : wall + CPU-giây, so với lượt render TRẦN đan xen

=== 2 BẪY ĐO ĐÃ SẬP TRƯỚC ĐÂY, FILE NÀY KHÔNG ĐƯỢC LẶP (cổng 43) ===
(a) ĐỪNG THU NHỎ RỒI MỚI ĐO — thu về 160 px là trung bình 45 điểm thành 1, hạt
    nhiễu/độ nét bị san phẳng: `hat_nhieu` ra 0,00% và bị kết luận oan "không
    hoạt động"; đo ở 1080x1920 ra 27,64%. Ở đây MỌI phép đo chạy ở cỡ gốc.
(b) ĐỪNG `format=gray` GIỮA CHUỖI ĐO — gray dải ĐẦY (0..255), yuv420p dải HẸP
    (16..235), ffmpeg tự chèn scale nên mức 0 (2 khung GIỐNG HỆT) thành 16,
    `gt(val,12)` đúng -> MỌI kiểu ra 100% điểm ảnh đổi, kể cả so file với CHÍNH
    NÓ. Ca `_doi_chung()` so gốc với gốc, phải ra 0,00% — không thì DỪNG.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"do_kho_moi_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401  (cổng 17: KHÔNG đụng máy anh Hùng)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

import psutil                                    # noqa: E402
from config import settings                      # noqa: E402

FF = settings.FFMPEG_PATH
FP = settings.FFPROBE_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0

W, H, FPS = 1080, 1920, 30
DAI = 6.0                      # clip nguồn NGẮN (luật máy anh Hùng: 5-20 s)
BAT, HET = 1.60, 2.20          # cửa sổ điểm nhấn chung cho mọi ứng viên
NG_THAY = 8.0                  # cổng 1
NG_UV = 3.0                    # cổng 3 (= hieu_ung.UV_MAX)
NG_UV_DIEM = 6.0               # cổng 3b: lệch TỪNG ĐIỂM (bắt desaturate)
NG_TOI = 0.35                  # cổng 4
NG_RO = 1.0                    # cổng 5 (% điểm ảnh ngoài cửa sổ)

KQ_JSON = REPO / "_ket_kho_moi.json"


# ------------------------------------------------------------------ chạy lệnh
def chay(cmd: list, giay: int = 600) -> tuple[int, str]:
    r = subprocess.run([str(x) for x in cmd], capture_output=True,
                       creationflags=_NOWIN, timeout=giay)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")


def chay_do_gia(cmd: list, giay: int = 600) -> tuple[int, str, float, float]:
    """Chạy 1 lệnh ffmpeg và trả (rc, log, wall, CPU-giây).

    CPU-giây lấy bằng cách SOI `psutil.cpu_times()` mỗi 50 ms (cùng cách
    `_ra_ab_chuyen_dong.py` đang dùng) — `time.perf_counter` một mình thì trên
    máy anh Hùng luôn có prodown tải nền nên wall nhảy loạn, đọc ra kết luận sai
    (bài học "Đo A/B phải đan xen").
    """
    cpu = [0.0]
    stop = threading.Event()
    t0 = time.perf_counter()
    p = subprocess.Popen([str(x) for x in cmd], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, creationflags=_NOWIN)

    def _soi() -> None:
        try:
            pr = psutil.Process(p.pid)
        except psutil.Error:
            return
        while not stop.is_set():
            try:
                ct = pr.cpu_times()
                cpu[0] = float(ct.user) + float(ct.system)
            except psutil.Error:
                return
            time.sleep(0.05)

    th = threading.Thread(target=_soi, daemon=True)
    th.start()
    try:
        _, err = p.communicate(timeout=giay)
    except subprocess.TimeoutExpired:
        p.kill()
        _, err = p.communicate(timeout=10)
    stop.set()
    th.join(timeout=2)
    return (int(p.returncode), (err or b"").decode("utf-8", "replace"),
            time.perf_counter() - t0, cpu[0])


def dem_khung(p: str) -> int:
    """ĐẾM KHUNG THẬT (cổng 6). `nb_frames` trong header là số KHAI BÁO — filter
    chết im lặng vẫn khai đủ; `-count_frames` mới là đếm."""
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(p)], capture_output=True,
                       creationflags=_NOWIN, timeout=300)
    try:
        return int((r.stdout or b"").decode().strip().split(",")[0])
    except (ValueError, IndexError):
        return -1


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


_RE_KV = re.compile(r"lavfi\.signalstats\.(\w+)=([-\d.eE+]+)")


def _doc(p: str, khoa: str) -> list[float]:
    """Đọc 1 khoá signalstats theo TỪNG KHUNG."""
    if not os.path.exists(p):
        return []
    ra = []
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = _RE_KV.search(ln)
            if m and m.group(1) == khoa:
                try:
                    ra.append(float(m.group(2)))
                except ValueError:
                    pass
    return ra


def do_cap(goc: str, sau: str) -> dict:
    """1 LỆNH ffmpeg -> mọi số đo TỪNG KHUNG ở ĐỘ PHÂN GIẢI GỐC.

    4 nhánh: sáng/màu bản GỐC · sáng/màu bản SAU · % điểm ảnh |dY|>12 ·
    lệch màu TỪNG ĐIỂM (|dU|,|dV| trung bình của ảnh HIỆU).
    """
    f0, f1, fd, fc = (str(_SB / x) for x in ("_l0.txt", "_l1.txt", "_dd.txt",
                                             "_ac.txt"))
    for f in (f0, f1, fd, fc):
        try:
            os.remove(f)
        except OSError:
            pass
    g = (f"[0:v]format=yuv420p,split=2[a][a2];"
         f"[1:v]format=yuv420p,split=2[b][b2];"
         f"[a][b]blend=all_mode=difference,split=2[d1][d2];"
         f"[d1]lutyuv=y='if(gt(val,12),255,0)',signalstats,"
         f"metadata=print:file='{_esc(fd)}'[d];"
         f"[d2]signalstats,metadata=print:file='{_esc(fc)}'[c];"
         f"[a2]signalstats,metadata=print:file='{_esc(f0)}'[x0];"
         f"[b2]signalstats,metadata=print:file='{_esc(f1)}'[x1];"
         f"[c]nullsink;[x0]nullsink;[x1]nullsink")
    rc, err = chay([FF, "-v", "error", "-i", goc, "-i", sau,
                    "-filter_complex", g, "-map", "[d]", "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError("lệnh đo hỏng: " + err[-400:])
    return {
        "y0": _doc(f0, "YAVG"), "u0": _doc(f0, "UAVG"),
        "v0": _doc(f0, "VAVG"),
        "y1": _doc(f1, "YAVG"), "u1": _doc(f1, "UAVG"),
        "v1": _doc(f1, "VAVG"),
        "pct": [x / 2.55 for x in _doc(fd, "YAVG")],
        "adu": _doc(fc, "UAVG"), "adv": _doc(fc, "VAVG"),
    }


# ------------------------------------------------------------------- nguồn
def nguon() -> str:
    """`DAI` giây CẢNH SÁNG cắt từ video THẬT trên máy, đúng khung 1080x1920.

    Mốc phải ở CẢNH SÁNG: cảnh gần đen thì mọi phép so độ sáng FAIL OAN (bài học
    cổng 36 — nguồn Nhật ở giây 20 sáng trung bình chỉ 3,3/255).
    """
    dst = str(_SB / "goc.mp4")
    if os.path.exists(dst):
        return dst
    cand: list[Path] = []
    for thu in (Path("D:/video test/Đã tải"),
                Path(r"C:\Users\Admin\Downloads\thùng rác")):
        if thu.is_dir():
            cand += sorted((p for p in thu.iterdir()
                            if p.suffix.lower() in (".mp4", ".mkv", ".webm",
                                                    ".mov")),
                           key=lambda p: p.stat().st_size)[:6]
    for p in cand:
        for ss in (240, 120, 60):
            rc, _ = chay([FF, "-y", "-v", "error", "-ss", str(ss), "-t",
                          str(DAI), "-i", str(p), "-an", "-vf",
                          f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                          f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf",
                          "18", "-g", "30", dst])
            if rc != 0 or not os.path.exists(dst):
                continue
            d = do_cap(dst, dst)
            s0 = d["y0"]
            if len(s0) >= int(DAI * FPS) - 3 and s0 and min(s0) > 45:
                print(f"  [nguồn] {p.name[:46]} @ {ss}s · sáng "
                      f"{sum(s0)/len(s0):.1f}/255 (thấp nhất {min(s0):.1f})")
                return dst
    rc, err = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"testsrc2=s={W}x{H}:r={FPS}:d={DAI}", "-an", "-c:v",
                    "libx264", "-preset", "veryfast", "-crf", "18", dst])
    if rc != 0:
        raise RuntimeError("không dựng nổi nguồn: " + err[-300:])
    print("  [nguồn] lavfi testsrc2 (máy không có video thật)")
    return dst


# ------------------------------------------------------------------ ỨNG VIÊN
#: CHIỀU khai TRƯỚC khi đo (cổng 2): "sang" | "toi" | "giu".
#: Khai sai = FAIL, đúng cái cổng 43 gọi là "SAI-CHIỀU" — hiệu ứng đi ngược việc
#: của nó mà mọi cổng khác vẫn xanh.
class UV:
    def __init__(self, khoa: str, mau: str, chieu: str, nguon_: str,
                 nhom: str = "thuan", module: str = "", ghi: str = ""):
        self.khoa, self.mau, self.chieu = khoa, mau, chieu
        self.nguon, self.nhom, self.module, self.ghi = nguon_, nhom, module, ghi


def _f0r(mod: str, params: str = "") -> str:
    s = f"frei0r=filter_name={mod}"
    if params:
        s += f":filter_params={params}"
    return s + "{en}"


#: `_SONG` = nửa hình sin trong cửa sổ (êm vào — êm ra). Chép Y HỆT
#: `hieu_ung._SONG` để số đo ở đây dùng được thẳng cho kho thật.
_SONG = "sin(3.14159*(t-{a})/({b}-{a}))"


def _lap(f: str, n: int) -> str:
    """Nối `n` bản của filter `f`, MỖI BẢN mang `enable` riêng.

    === LỖI ĐO CHÍNH FILE NÀY ĐÃ MẮC (lượt 1, 09/08/2026) ===
    Viết `"a,a,a,a" + "{en}"` thì `enable` chỉ dính vào bản CUỐI -> 3 bản đầu
    chạy CẢ CLIP. Đo ra đúng cái vân tay của lỗi đó: `erosion` x4 báo "trong
    7,44% · **ngoài 6,11%**" — tức phần lớn tác dụng đã rò ra ngoài cửa sổ và
    con số "trong" chỉ còn là phần bản thứ 4 thêm vào. Nếu tin số đó thì kết
    luận "erosion không thấy được" là SAI NGUYÊN NHÂN.
    """
    return ",".join([f + "{en}"] * n)

# ----- NHÓM A: FILTER CÓ SẴN TRONG ffmpeg (0 MB, chạy MỌI máy kể cả nhân viên)
#
# === VÌ SAO "ÊM VÀO — ÊM RA" KHÔNG ÁP ĐƯỢC CHO MỌI KIỂU (đo ra, không đoán) ===
# `_SONG` cần filter nhận BIỂU THỨC THEO `t`. Đã tra `ffmpeg -h filter=<tên>`
# từng cái: `rotate.a` · `zoompan.z/x/y` · `eq.*` · `vignette.a` nhận biểu thức;
# còn `shear.shx` · `dblur.angle` · `gblur.sigma` · `spp.qp` khai kiểu <float>
# nên chỉ bật/tắt được bằng `enable`. Với nhóm sau, hard cut CHÍNH LÀ hiệu ứng
# (glitch/vỡ hình) và kho hiện tại đã có tiền lệ đo đạt: `o_vuong` (pixelize),
# `xao_dong` (shufflepixels), `glitch_khoi`, `mo_net` (gblur).
UNG_VIEN_BUILTIN: list = [
    # --- hình học / chuyển động (dời chỗ điểm ảnh, KHÔNG pha lại màu) ---
    # `shear` fill=black -> nêm ĐEN ở mép; phải PHÓNG TO trước cho phủ kín.
    UV("ug_xien", "zoompan=z='if(between(it,{a},{b}),1.18,1)':d=1:"
       "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
       "shear=shx=0.10:shy=0.04:c=black{en}", "giu",
       "ffmpeg shear (có zoompan phủ nêm đen)"),
    # `perspective` sense=source: khung nguồn nằm TRONG ảnh rồi kéo căng ra cả
    # khung -> KHÔNG có mép đen nào. Tham số tĩnh (filter không có `eval`).
    UV("ug_phoi_canh",
       "perspective=x0='{p1}*W':y0='0.02*H':x1='W-0.02*W':y1=0:"
       "x2='0.02*W':y2=H:x3='W-{p1}*W':y3='H-0.02*H':sense=source{en}",
       "giu", "ffmpeg perspective (sense=source, không mép đen)"),
    # zoompan phóng 1,10 (che góc khuyết khi quay 0,045 rad — tính:
    # (H cos+W sin)/H = 1,024 · (W cos+H sin)/W = 1,079 -> 1,10 là đủ) rồi
    # `rotate` quay theo NỬA HÌNH SIN: hai mép cửa sổ góc = 0 = ảnh gốc.
    UV("ug_nghieng",
       "zoompan=z='if(between(it,{a},{b}),1+0.10*" + _SONG.replace("t", "it")
       + ",1)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
       "s={W}x{H}:fps={FPS},rotate=a='0.045*" + _SONG + "':c=black{en}",
       "giu", "ffmpeg zoompan+rotate (nghiêng máy, êm vào êm ra)"),
    # `hflip` KHÔNG có tuỳ chọn nào -> `hflip:enable=` vỡ cú pháp, phải
    # `hflip=enable=` (dấu `=` đầu tiên mở danh sách tuỳ chọn).
    UV("ug_lat_guong", "hflip=enable='between(t,{a},{b})'", "giu",
       "ffmpeg hflip"),
    UV("ug_truot", "scroll=horizontal=0.02:vertical=0{en}", "giu",
       "ffmpeg scroll"),
    UV("ug_doi_o", "swaprect=w=w/2:h=h/3:x1=0:y1=h/3:x2=w/2:y2=h/3{en}",
       "giu", "ffmpeg swaprect"),
    UV("ug_meo_kinh_tt", "lenscorrection=k1={p1}:k2=0:i=bilinear{en}", "giu",
       "ffmpeg lenscorrection (BẢN THUẦN — máy nhân viên không frei0r vẫn có)"),
    UV("ug_xao_khoi", "shufflepixels=direction=inverse:mode=block:"
       "width={p1}:height={p1}{en}", "giu",
       "ffmpeg shufflepixels mode=block"),
    UV("ug_xao_doc", "shufflepixels=direction=inverse:mode=vertical:"
       "width={p1}:height={p1}{en}", "giu",
       "ffmpeg shufflepixels mode=vertical"),
    UV("ug_zoom_lui",
       "zoompan=z='if(between(it,{a},{b}),1.14-0.14*(it-{a})/({b}-{a}),1)':d=1:"
       "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}",
       "giu", "ffmpeg zoompan (kiểu mới: kéo LÙI)"),
    UV("ug_luot_ngang",
       "zoompan=z='if(between(it,{a},{b}),1.10,1)':d=1:"
       "x='iw/2-(iw/zoom/2)+0.14*iw*sin(3.14159*(it-{a})/({b}-{a}))"
       "*between(it,{a},{b})':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}",
       "giu", "ffmpeg zoompan (lướt ngang)"),
    UV("ug_luot_doc",
       "zoompan=z='if(between(it,{a},{b}),1.10,1)':d=1:"
       "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+0.10*ih*sin(3.14159*"
       "(it-{a})/({b}-{a}))*between(it,{a},{b})':s={W}x{H}:fps={FPS}",
       "giu", "ffmpeg zoompan (lướt dọc)"),
    UV("ug_rung_xoay",
       "zoompan=z='if(between(it,{a},{b}),1.12,1)':d=1:"
       "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
       "rotate=a='0.035*sin(31*(t-{a}))*" + _SONG + "':c=black{en}",
       "giu", "ffmpeg zoompan+rotate (rung XOAY, khác rung lắc tịnh tiến)"),
    # --- mờ / nét (bán kính PHẢI to vì khung 1080x1920) ---
    UV("ug_mo_huong", "dblur=angle={p1}:radius=28{en}", "giu",
       "ffmpeg dblur (mờ theo HƯỚNG = vệt chuyển động)"),
    # `varblur` ĐÃ LOẠI KHÔNG CẦN ĐO: nó nhận **2 đầu vào** (#1 là ảnh bán
    # kính), `-vf` một luồng không dựng nổi. Cùng lý do với `morpho`,
    # `hysteresis`, `maskedclamp`.
    # `datascope` ĐÃ LOẠI KHÔNG CẦN ĐO: (a) KHÔNG có timeline -> không cổng
    # được theo giây, áp là áp cả clip = trái luật 1; (b) `size` là CỠ ẢNH RA
    # (mặc định hd720) nên nó ĐỔI ĐỘ PHÂN GIẢI. Là công cụ gỡ rối, không phải
    # hiệu ứng.
    UV("ug_mo_song", "yaepblur=radius=26:planes=1:sigma=160{en}", "giu",
       "ffmpeg yaepblur"),
    UV("ug_mo_bien_gio", "bilateral=sigmaS=26:sigmaR=0.3:planes=1{en}", "giu",
       "ffmpeg bilateral"),
    UV("ug_trung_vi", "median=radius=14:planes=1{en}", "giu", "ffmpeg median"),
    # --- nén / vỡ khối ---
    UV("ug_vo_nen", "spp=quality=6:qp=42:use_bframe_qp=0{en}", "giu",
       "ffmpeg spp (giả nén hỏng)"),
    UV("ug_soc_xen", "il=luma_mode=deinterleave:chroma_mode=none{en}", "giu",
       "ffmpeg il (xen dòng = băng cũ)"),
    # --- luma-only (KHÔNG thể đổi màu vì chỉ đụng mặt Y) ---
    UV("ug_bac_mau", "lutyuv=y='trunc(val/28)*28+14'{en}", "giu",
       "ffmpeg lutyuv (giảm bậc SÁNG)"),
    UV("ug_chay_sang", "lutyuv=y='if(gt(val,190),470-val,val)'{en}", "giu",
       "ffmpeg lutyuv (cháy sáng kiểu phim)"),
    UV("ug_no_sang", "inflate=threshold0=255:threshold1=0:threshold2=0{en}",
       "sang", "ffmpeg inflate (mặt Y)"),
    UV("ug_co_toi", "deflate=threshold0=255:threshold1=0:threshold2=0{en}",
       "toi", "ffmpeg deflate (mặt Y)"),
    UV("ug_no_manh", _lap("inflate=threshold0=255:threshold1=0:threshold2=0",
                          3), "sang", "ffmpeg inflate x3"),
    UV("ug_khac_net", "convolution=0m='0 -1 0 -1 5 -1 0 -1 0':0rdiv=1:"
       "1m='0 0 0 0 1 0 0 0 0':2m='0 0 0 0 1 0 0 0 0':"
       "3m='0 0 0 0 1 0 0 0 0'{en}", "giu",
       "ffmpeg convolution (nét mặt Y)"),
    UV("ug_dap_noi", "convolution=0m='-2 -1 0 -1 1 1 0 1 2':0rdiv=1:"
       "1m='0 0 0 0 1 0 0 0 0':2m='0 0 0 0 1 0 0 0 0':"
       "3m='0 0 0 0 1 0 0 0 0'{en}", "giu",
       "ffmpeg convolution (dập nổi mặt Y)"),
    UV("ug_go_dai", "deband=1thr=0.05:2thr=0.05:3thr=0.05:range=32:"
       "blur=1{en}", "giu", "ffmpeg deband"),
    UV("ug_bao_mon", _lap("erosion=threshold0=255:threshold1=0:threshold2=0",
                          4), "toi", "ffmpeg erosion x4 (mặt Y)"),
    UV("ug_phinh", _lap("dilation=threshold0=255:threshold1=0:threshold2=0",
                        4), "sang", "ffmpeg dilation x4 (mặt Y)"),
    UV("ug_mo_hop", "boxblur=luma_radius=22:luma_power=2:"
       "chroma_radius=0:chroma_power=0{en}", "giu", "ffmpeg boxblur (mặt Y)"),
    UV("ug_go_hat", "removegrain=m0=17:m1=0:m2=0{en}", "giu",
       "ffmpeg removegrain"),
    # --- ĐỔI MÀU: đo để CHỨNG MINH bị luật 3 loại, không phải đoán ---
    UV("ug_lech_chroma", "chromashift=cbh=48:crh=-48:cbv=20:crv=-20{en}",
       "giu", "ffmpeg chromashift"),
    UV("ug_muc_mau", "colorlevels=rimin=0.06:gimin=0.06:bimin=0.06{en}",
       "toi", "ffmpeg colorlevels"),
    UV("ug_phoi_sang", "exposure=exposure={p1}{en}", "sang",
       "ffmpeg exposure"),
    UV("ug_khuech_dai", "amplify=radius=2:factor=8:threshold=20{en}", "giu",
       "ffmpeg amplify"),
    UV("ug_can_bang_t", "tmidequalizer=radius=3:sigma=0.5:planes=1{en}",
       "giu", "ffmpeg tmidequalizer"),
]

# ----- NHÓM B: frei0r chưa dùng (mỗi .dll 15-40 KB)
UNG_VIEN_F0R: list = [
    UV("uf_xe_dong", _f0r("pixs0r", "{p1}|0.5|0.5|0.5"), "giu",
       "frei0r pixs0r", "frei0r", "pixs0r"),
    UV("uf_tuong_video", _f0r("tehroxx0r", "{p1}"), "giu",
       "frei0r tehroxx0r", "frei0r", "tehroxx0r"),
    # KIỂU THAM SỐ dò bằng `_do_f0r_thamso.py` (ffmpeg KHÔNG in bảng tham số;
    # đưa sai kiểu là CHẾT CẢ LỆNH — cùng bẫy `glitch0r` mã nguồn đã ghi).
    UV("uf_bon_goc", _f0r("c0rners",
                          "{p1}|0.42|0.58|{p1}|0.42|0.58|0.58|0.58|"
                          "n|0.5|0.5|0.5|n|0.5|0.5"), "giu",
       "frei0r c0rners", "frei0r", "c0rners"),
    UV("uf_meo_ca", _f0r("defish0r",
                         "{p1}|y|0.5|0.5|0.5|0.5|0.5|0.5|n|0.5|0.5"),
       "giu", "frei0r defish0r", "frei0r", "defish0r"),
    UV("uf_keo_deo", _f0r("elastic_scale", "0.5|{p1}|1|0.5"), "giu",
       "frei0r elastic_scale", "frei0r", "elastic_scale"),
    UV("uf_lat_xy", _f0r("flippo", "y|n"), "giu",
       "frei0r flippo", "frei0r", "flippo"),
    UV("uf_vien_quang", _f0r("edgeglow", "0.08|{p1}|0.5"), "sang",
       "frei0r edgeglow", "frei0r", "edgeglow"),
    UV("uf_vet_sang", _f0r("lightgraffiti",
                           "{p1}|0.5|0.55|0.5|0.5|0.02|0.5|0.5|"
                           "n|n|n|n|n|n|0.5|n"),
       "sang", "frei0r lightgraffiti", "frei0r", "lightgraffiti"),
    UV("uf_nhoe_thoi_gian", _f0r("delaygrab"), "giu",
       "frei0r delaygrab", "frei0r", "delaygrab"),
    UV("uf_trung_vi_f", _f0r("medians", "0.3|{p1}"), "giu",
       "frei0r medians", "frei0r", "medians"),
    UV("uf_mo_iir", _f0r("IIRblur", "{p1}|0.5|n"), "giu",
       "frei0r IIRblur", "frei0r", "IIRblur"),
    UV("uf_keo_muc", _f0r("normaliz0r",
                          "0.06/0.06/0.06|0.94/0.94/0.94|0.5|0.5|0.5"), "giu",
       "frei0r normaliz0r", "frei0r", "normaliz0r"),
    UV("uf_can_bang", _f0r("equaliz0r"), "giu",
       "frei0r equaliz0r", "frei0r", "equaliz0r"),
    UV("uf_phoi_canh_f", _f0r("perspective",
                              "0.16/0.04|0.84/0.00|0.00/1.00|0.90/0.96"),
       "giu", "frei0r perspective", "frei0r", "perspective"),
    UV("uf_o_vuong_f", _f0r("pixeliz0r", "{p1}|{p1}|n"), "giu",
       "frei0r pixeliz0r", "frei0r", "pixeliz0r"),
    UV("uf_run_khung", _f0r("nervous"), "giu",
       "frei0r nervous", "frei0r", "nervous"),
    UV("uf_vang_diem", _f0r("dither", "0.5|0.3"), "giu",
       "frei0r dither", "frei0r", "dither"),
    UV("uf_mo_vuong_to", _f0r("squareblur", "0.9"), "giu",
       "frei0r squareblur (trần cao hơn bản đang dùng)", "frei0r",
       "squareblur"),
]

#: tham số `{p1}` cho từng ứng viên ở mức ĐẬM NHẤT (đo trần trước; kiểu nào
#: qua thì mới dò dải cho mức 'nhe'). Không khai = không có `{p1}`.
P1: dict = {
    "ug_phoi_canh": 0.16, "ug_mo_huong": 90, "ug_phoi_sang": 0.55,
    "ug_meo_kinh_tt": -0.28, "ug_xao_khoi": 40, "ug_xao_doc": 44,
    "uf_xe_dong": 0.8, "uf_tuong_video": 0.55, "uf_meo_ca": 0.75,
    "uf_keo_deo": 0.85, "uf_vien_quang": 0.9, "uf_trung_vi_f": 0.8,
    "uf_mo_iir": 0.85, "uf_o_vuong_f": 0.05, "uf_bon_goc": 0.36,
    "uf_vet_sang": 0.75,
}


def dung_chuoi(u: UV, p1: float | None = None) -> str:
    s = u.mau
    if "{p1}" in s:
        s = s.replace("{p1}", f"{P1.get(u.khoa, 0.5) if p1 is None else p1:g}")
    return (s.replace("{en}", f":enable='between(t,{BAT:.3f},{HET:.3f})'")
             .replace("{a}", f"{BAT:.3f}").replace("{b}", f"{HET:.3f}")
             .replace("{W}", str(W)).replace("{H}", str(H))
             .replace("{FPS}", f"{FPS:g}"))


# --------------------------------------------------------------- ĐO 1 ỨNG VIÊN
def do_mot(u: UV, src: str, n_goc: int, p1: float | None = None) -> dict:
    dst = str(_SB / f"e_{u.khoa}.mp4")
    ch = dung_chuoi(u, p1)
    cmd = [FF, "-y", "-v", "error", "-i", src, "-an", "-vf", ch,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", dst]
    rc, err, wall, cpu = chay_do_gia(cmd)
    ra = {"khoa": u.khoa, "nhom": u.nhom, "nguon": u.nguon, "chieu": u.chieu,
          "p1": (P1.get(u.khoa) if p1 is None else p1), "wall": round(wall, 2),
          "cpu": round(cpu, 2), "chuoi": ch[:150]}
    if rc != 0:
        ra.update(kq="FFMPEG-LỖI",
                  ghi=(err.strip().splitlines() or [""])[-1][:130])
        return ra
    n = dem_khung(dst)
    d = do_cap(src, dst)
    y0, y1, pct = d["y0"], d["y1"], d["pct"]
    if not y1 or not pct:
        ra.update(kq="0-KHUNG", ghi=f"nb_read_frames={n}")
        return ra
    m = min(len(y0), len(y1), len(pct))
    i0, i1 = int(BAT * FPS), int(HET * FPS)
    trong_i = list(range(max(0, i0 + 1), min(m, i1)))
    ngoai_i = [i for i in range(m) if i < i0 - 1 or i > i1 + 1]
    trong = max((pct[i] for i in trong_i), default=-1.0)
    ngoai = max((pct[i] for i in ngoai_i), default=0.0)
    ty = [y1[i] / y0[i] for i in trong_i if y0[i] > 5] or [1.0]
    # lệch màu: TRUNG BÌNH (luật 3) + TỪNG ĐIỂM (bắt desaturate)
    j = max(trong_i, key=lambda i: pct[i]) if trong_i else 0
    du = (d["u1"][j] - d["u0"][j]) if j < len(d["u1"]) else 99.0
    dv = (d["v1"][j] - d["v0"][j]) if j < len(d["v1"]) else 99.0
    adu = d["adu"][j] if j < len(d["adu"]) else 99.0
    adv = d["adv"][j] if j < len(d["adv"]) else 99.0
    toi = [i for i in range(m) if y0[i] > 5 and y1[i] < NG_TOI * y0[i]]
    ra.update(khung=n, trong=round(trong, 2), ngoai=round(ngoai, 2),
              ty_day=round(min(ty), 3), ty_dinh=round(max(ty), 3),
              du=round(du, 2), dv=round(dv, 2),
              adu=round(adu, 2), adv=round(adv, 2), toi=toi[:4])
    ra["kq"], ra["ghi"] = _cham(ra, n_goc)
    return ra


def _cham(r: dict, n_goc: int) -> tuple[str, str]:
    """CHẤM 7 CỔNG. Trả (kết quả, lý do). Rớt cổng nào nói ĐÚNG cổng đó."""
    if r["khung"] != n_goc:
        return "LỆCH-KHUNG", f"{r['khung']}/{n_goc} khung"
    if r["toi"]:
        return "KHUNG-TỐI", (f"khung {r['toi']} dưới {NG_TOI:.0%} bản gốc "
                             f"(đáy {r['ty_day']:.3f})")
    if r["trong"] < NG_THAY:
        return "KHÔNG-THẤY", f"{r['trong']:.2f}% điểm ảnh (cần >= {NG_THAY})"
    if r["ngoai"] > NG_RO:
        return "RÒ-NGOÀI", f"ngoài cửa sổ {r['ngoai']:.2f}% điểm ảnh"
    if abs(r["du"]) >= NG_UV or abs(r["dv"]) >= NG_UV:
        return "LOÈ-MÀU", f"dU {r['du']} · dV {r['dv']} (trần {NG_UV})"
    if r["adu"] >= NG_UV_DIEM or r["adv"] >= NG_UV_DIEM:
        return "LOÈ-ĐIỂM", (f"|dU| {r['adu']} · |dV| {r['adv']} từng điểm "
                            f"(trần {NG_UV_DIEM})")
    ch = r["chieu"]
    if ch == "toi" and not (NG_TOI <= r["ty_day"] <= 0.94):
        return "SAI-CHIỀU", f"khai TỐI mà đáy sáng {r['ty_day']:.3f}"
    if ch == "sang" and r["ty_dinh"] < 1.02:
        return "SAI-CHIỀU", f"khai SÁNG mà đỉnh sáng {r['ty_dinh']:.3f}"
    if ch == "giu" and not (0.90 <= r["ty_day"] and r["ty_dinh"] <= 1.12):
        return "SAI-CHIỀU", (f"khai GIỮ mà sáng chạy "
                             f"{r['ty_day']:.3f}..{r['ty_dinh']:.3f}")
    return "ĐẠT", ""


def do_kieu_kho(k: str, muc: str, src: str, n_goc: int) -> dict:
    """Đo 1 kiểu ĐANG NẰM TRONG KHO, dựng chuỗi bằng CHÍNH `HU.chuoi_filter`.

    Khác `do_mot` (đo ứng viên rời): ca này đi qua đúng đường app dùng, nên nó
    trả lời được câu hỏi thật sự quan trọng — **ở mức 'nhe' (mặc định của
    200-300 kênh) kiểu này CÒN THẤY ĐƯỢC không**. Cổng 43 chỉ đo ở `DAM_MAX`;
    một kiểu đạt ở trần mà mất hút ở 'nhe' thì với anh Hùng là KHÔNG CÓ.
    """
    from app.core import hieu_ung as HU
    h = HU.KHO[k]
    ch = HU.chuoi_filter([{"khoa": k, "bat": BAT, "het": HET,
                           "dam": HU.MUC_DAM.get(muc, HU.DAM_MAX)}],
                         W, H, FPS, "")
    ra = {"khoa": k, "nhom": h.nhom, "nguon": f"KHO/{muc}", "chieu": "",
          "p1": None, "chuoi": ch[:150]}
    if not ch:
        ra.update(kq="BỎ-QUA", ghi="chuỗi rỗng (thiếu font/shader/frei0r)",
                  wall=0.0, cpu=0.0)
        return ra
    dst = str(_SB / f"k_{k}_{muc}.mp4")
    cmd = [FF, "-y", "-v", "error"]
    if HU.can_vulkan([{"khoa": k}]):
        cmd += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
    cmd += ["-i", src, "-an", "-vf", ch, "-c:v", "libx264", "-preset",
            "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst]
    rc, err, wall, cpu = chay_do_gia(cmd)
    ra.update(wall=round(wall, 2), cpu=round(cpu, 2))
    if rc != 0:
        ra.update(kq="FFMPEG-LỖI",
                  ghi=(err.strip().splitlines() or [""])[-1][:130])
        return ra
    n = dem_khung(dst)
    d = do_cap(src, dst)
    y0, y1, pct = d["y0"], d["y1"], d["pct"]
    if not y1 or not pct:
        ra.update(kq="0-KHUNG", ghi=f"nb_read_frames={n}")
        return ra
    m = min(len(y0), len(y1), len(pct))
    i0, i1 = int(BAT * FPS), int(HET * FPS)
    trong_i = list(range(max(0, i0 + 1), min(m, i1)))
    ngoai_i = [i for i in range(m) if i < i0 - 1 or i > i1 + 1]
    j = max(trong_i, key=lambda i: pct[i]) if trong_i else 0
    ty = [y1[i] / y0[i] for i in trong_i if y0[i] > 5] or [1.0]
    ra.update(khung=n,
              trong=round(max((pct[i] for i in trong_i), default=-1.0), 2),
              ngoai=round(max((pct[i] for i in ngoai_i), default=0.0), 2),
              ty_day=round(min(ty), 3), ty_dinh=round(max(ty), 3),
              du=round(d["u1"][j] - d["u0"][j], 2),
              dv=round(d["v1"][j] - d["v0"][j], 2),
              adu=round(d["adu"][j], 2), adv=round(d["adv"][j], 2),
              toi=[i for i in range(m) if y0[i] > 5
                   and y1[i] < NG_TOI * y0[i]][:4])
    if ra["khung"] != n_goc:
        ra["kq"], ra["ghi"] = "LỆCH-KHUNG", f"{n}/{n_goc} khung"
    elif ra["toi"]:
        ra["kq"], ra["ghi"] = "KHUNG-TỐI", f"khung {ra['toi']}"
    elif ra["trong"] < h.nguong_thay:
        ra["kq"], ra["ghi"] = "KHÔNG-THẤY", (f"{ra['trong']:.2f}% < ngưỡng "
                                             f"{h.nguong_thay} của kiểu này")
    elif ra["ngoai"] > NG_RO:
        ra["kq"], ra["ghi"] = "RÒ-NGOÀI", f"{ra['ngoai']:.2f}%"
    elif abs(ra["du"]) >= NG_UV or abs(ra["dv"]) >= NG_UV:
        ra["kq"], ra["ghi"] = "LOÈ-MÀU", f"dU {ra['du']} dV {ra['dv']}"
    else:
        ra["kq"], ra["ghi"] = "ĐẠT", ""
    return ra


def _doi_chung(src: str, n_goc: int) -> None:
    """SO GỐC VỚI GỐC = 0,00%. Không có ca này thì bẫy (b) `format=gray` làm
    MỌI kiểu ra 100% và cả bảng số là rác."""
    d = do_cap(src, src)
    mx = max(d["pct"]) if d["pct"] else -1.0
    print(f"  [đối chứng] gốc vs gốc = {mx:.2f}% điểm ảnh · "
          f"{len(d['y0'])} khung · đếm thật {n_goc}")
    if mx > 0.001:
        raise SystemExit("DỪNG: bộ đo hỏng (gốc vs gốc phải 0,00%) — xem bẫy (b)")


# ------------------------------------------------------------------- CHẠY
def _in(r: dict) -> None:
    if r["kq"] in ("FFMPEG-LỖI", "0-KHUNG"):
        print(f"  {r['khoa']:20s} {r['kq']:12s} {r.get('ghi','')[:80]}")
        return
    print(f"  {r['khoa']:20s} {r['kq']:12s} "
          f"trong {r['trong']:6.2f}% · ngoài {r['ngoai']:5.2f}% · "
          f"sáng {r['ty_day']:.2f}..{r['ty_dinh']:.2f} · "
          f"dU {r['du']:6.2f} dV {r['dv']:6.2f} · |d| {r['adu']:5.2f}/"
          f"{r['adv']:5.2f} · {r['wall']:.1f}s/{r['cpu']:.1f}cpu"
          + (f"  << {r['ghi']}" if r.get("ghi") else ""))


def _chay_kho(a) -> int:
    """Quét kiểu ĐANG TRONG KHO ở 1 mức đậm — trả lời "ở mức Nhẹ còn thấy không"."""
    from app.core import hieu_ung as HU
    # PHẢI ghi `FREI0R_PATH` trước, y như app làm lúc mở: không có nó thì mọi
    # kiểu nhóm frei0r ra "Invalid argument" và bị chấm oan là hỏng.
    HU.dat_frei0r_path()
    HU.bao_dam_runtime()
    muc = a.kho if a.kho in HU.MUC_DAM else "nhe"
    ks = ([x.strip() for x in a.kieu.split(",") if x.strip()]
          if a.kieu else list(HU.KHO.keys()))
    ks = [k for k in ks if k in HU.KHO]
    print(f"ĐO {len(ks)} KIỂU TRONG KHO ở mức '{muc}' "
          f"(dam={HU.MUC_DAM[muc]}) · {W}x{H} · cửa sổ [{BAT} .. {HET}] s")
    src = nguon()
    n_goc = dem_khung(src)
    _doi_chung(src, n_goc)
    ra = []
    for i, k in enumerate(ks, 1):
        try:
            r = do_kieu_kho(k, muc, src, n_goc)
        except Exception as e:                           # noqa: BLE001
            r = {"khoa": k, "kq": "NỔ", "ghi": str(e)[:150]}
        print(f"[{i}/{len(ks)}] ", end="")
        _in(r)
        ra.append(r)
    xau = [r for r in ra if r.get("kq") not in ("ĐẠT", "BỎ-QUA")]
    print(f"\n=== mức '{muc}': ĐẠT {sum(1 for r in ra if r.get('kq') == 'ĐẠT')}"
          f"/{len(ra)} · bỏ qua "
          f"{sum(1 for r in ra if r.get('kq') == 'BỎ-QUA')} ===")
    for r in xau:
        print(f"  {r['khoa']:20s} {r.get('kq',''):12s} {r.get('ghi','')[:90]}")
    (REPO / f"_ket_kho_{muc}.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if xau else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nhom", default="builtin",
                    choices=("builtin", "frei0r", "tatca"))
    ap.add_argument("--chi", default="", help="chỉ đo mấy khoá này")
    ap.add_argument("--f0r", default="", help="thư mục .dll frei0r để thử")
    ap.add_argument("--kho", default="", help="đo KIỂU ĐANG TRONG KHO ở mức "
                                              "này (nhe/vua/manh); 'all'=cả kho")
    ap.add_argument("--kieu", default="", help="với --kho: chỉ mấy khoá này")
    a = ap.parse_args()

    if a.kho:
        return _chay_kho(a)

    if a.f0r:
        os.environ["FREI0R_PATH"] = a.f0r
        print(f"FREI0R_PATH = {a.f0r}")

    ds = list(UNG_VIEN_BUILTIN if a.nhom == "builtin" else
              UNG_VIEN_F0R if a.nhom == "frei0r" else
              UNG_VIEN_BUILTIN + UNG_VIEN_F0R)
    if a.chi:
        mu = {x.strip() for x in a.chi.split(",") if x.strip()}
        ds = [u for u in (UNG_VIEN_BUILTIN + UNG_VIEN_F0R) if u.khoa in mu]
    if not ds:
        print("không có ứng viên nào khớp")
        return 2

    print(f"ĐO {len(ds)} ỨNG VIÊN ở {W}x{H} · cửa sổ [{BAT} .. {HET}] s")
    src = nguon()
    n_goc = dem_khung(src)
    _doi_chung(src, n_goc)
    # CHI PHÍ NỀN: render TRẦN (không filter) để có mốc so — máy anh Hùng luôn
    # có prodown tải nền nên số tuyệt đối vô nghĩa, phải so tương đối.
    rc, _, w0, c0 = chay_do_gia(
        [FF, "-y", "-v", "error", "-i", src, "-an", "-vf", "null",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", str(_SB / "_tran.mp4")])
    print(f"  [mốc trần] {w0:.2f}s wall · {c0:.2f} CPU-giây (rc={rc})\n")

    ra = []
    for i, u in enumerate(ds, 1):
        print(f"[{i}/{len(ds)}] {u.khoa} — {u.nguon}")
        try:
            r = do_mot(u, src, n_goc)
        except Exception as e:                       # noqa: BLE001
            r = {"khoa": u.khoa, "kq": "NỔ", "ghi": str(e)[:150],
                 "nhom": u.nhom, "nguon": u.nguon}
        r["wall_tran"], r["cpu_tran"] = round(w0, 2), round(c0, 2)
        _in(r)
        ra.append(r)

    cu = []
    if KQ_JSON.exists():
        try:
            cu = json.loads(KQ_JSON.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cu = []
    moi = {r["khoa"]: r for r in cu if isinstance(r, dict)}
    moi.update({r["khoa"]: r for r in ra})
    KQ_JSON.write_text(json.dumps(list(moi.values()), ensure_ascii=False,
                                  indent=1), encoding="utf-8")

    dat = [r for r in ra if r.get("kq") == "ĐẠT"]
    print(f"\n=== ĐẠT {len(dat)}/{len(ra)} ===")
    for r in dat:
        print(f"  {r['khoa']:20s} {r['trong']:6.2f}% · "
              f"sáng {r['ty_day']:.2f}..{r['ty_dinh']:.2f} · "
              f"dU {r['du']:5.2f} dV {r['dv']:5.2f} · "
              f"{r['cpu']:.1f} CPU-giây (trần {r['cpu_tran']:.1f})")
    print("\nRỚT:")
    for r in ra:
        if r.get("kq") != "ĐẠT":
            print(f"  {r['khoa']:20s} {r['kq']:12s} {r.get('ghi','')[:90]}")
    print(f"\n-> {KQ_JSON.name}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
