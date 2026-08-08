# -*- coding: utf-8 -*-
"""CỔNG 43 — QUÉT KHUNG HÌNH TỪNG KIỂU HIỆU ỨNG: KHÔNG ĐEN, KHÔNG CHẾT, KHÔNG RÒ.

VÌ SAO CÓ CỔNG NÀY (anh Hùng XEM CLIP THẬT do app xuất, 08/08/2026):
  *"mấy hiệu ứng tôi thấy cứ sao sao, hình như không hoạt động, ví dụ zoom nhồi
  gì đó thấy nó TỐI ĐEN không thấy gì rồi lại hiện"* · *"hiệu ứng lỏ quá"*.

Cổng cũ (`_test_hieu_ung_ai.py`, `_test_shader.py`) kiểm CHỌN ĐÚNG KIỂU và
KHÔNG RÒ RA NGOÀI, nhưng KHÔNG ai đo ĐỘ SÁNG TỪNG KHUNG -> hiệu ứng làm mất
hình mà mọi cổng vẫn xanh. Cổng này đo **SỐ TRÊN KHUNG HÌNH**, ở ĐÚNG độ phân
giải xuất (1080x1920), cho **MỌI kiểu trong `hieu_ung.KHO`**:

  sáng[i]  = signalstats.YAVG từng khung (bản CÓ hiệu ứng)
  sáng0[i] = như trên, bản GỐC
  đổi[i]   = % pixel |dY| > 12  (blend=difference -> lutyuv nhị phân -> YAVG/2,55)

  FAIL "KHUNG ĐEN"   : sáng[i] < 5% sáng[i-1]  HOẶC  < 5% sáng0[i]
  FAIL "TỐI SÂU"     : sáng[i] < 35% sáng0[i]  (mắt đọc ra là "tối đen")
  FAIL "KHÔNG CHẠY"  : max đổi[] trong cửa sổ < 3%
  FAIL "RÒ RA NGOÀI" : max đổi[] ngoài cửa sổ > 1%   (luật 1 chống loè)
  FAIL "LỆCH KHUNG"  : số khung ra != số khung vào

2 BẪY ĐO ĐÃ SẬP KHI VIẾT CỔNG NÀY — đừng lặp:
 (a) **ĐỪNG THU NHỎ KHUNG RỒI MỚI ĐO.** Bản đầu đo ở 160 px cho nhanh: phép thu
     nhỏ TRUNG BÌNH 45 pixel thành 1 nên hạt nhiễu/độ nét bị san phẳng ->
     `hat_nhieu` (noise c0s=40) đo ra **0,00%** và bị kết luận oan là "không
     hoạt động". Đo lại ở 1080x1920: **27,64%**. Nay mọi phép đo chạy ở độ phân
     giải GỐC, bằng chính ffmpeg (`blend`+`signalstats`), không vòng qua Python.
 (b) **ĐỪNG ĐỔI QUA `format=gray` GIỮA CHỪNG.** gray là dải ĐẦY (0..255) còn
     yuv420p là dải HẸP (16..235) -> ffmpeg tự chèn scale và mức 0 (hai khung
     GIỐNG HỆT) thành **16**; `gt(val,12)` đúng nên MỌI kiểu đo ra **100% pixel
     đổi**, kể cả khi so một file với CHÍNH NÓ. Ca "đối chứng" dưới đây (so gốc
     với gốc phải ra 0,00%) chính là để cổng tự bắt lại lỗi này.

Chạy: .venv\\Scripts\\python.exe _test_hieu_ung_khung.py
Env : BQ_TEST=1 · BQ_FFMPEG_SLOTS=1 (LUẬT SỐ 1 — máy anh Hùng đang làm việc)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_hu_khung_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import hieu_ung as HU          # noqa: E402
from config import settings                  # noqa: E402

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF = settings.FFMPEG_PATH
FP = settings.FFPROBE_PATH

W, H, FPS = 1080, 1920, 30
DAI = 5.0                    # clip nguồn NGẮN — luật số 1
BAT, HET = 1.60, 2.20        # cửa sổ hiệu ứng chung cho mọi kiểu
NG_DEN, NG_TOI = 0.05, 0.35
NG_CHAY, NG_RO = 3.0, 1.0

#: HIỆU ỨNG PHẢI ĐI ĐÚNG CHIỀU — ngưỡng `sáng đáy|đỉnh / gốc` trong cửa sổ.
#:
#: === VÌ SAO PHẢI CÓ (lượt kiểm ĐỘC LẬP 08/08/2026 — cổng này ĐÃ PASS OAN) ===
#: Cổng chỉ hỏi "có tối quá không · có đen không · có đổi >= 3% không · có rò
#: không". Nó KHÔNG hỏi "đổi theo CHIỀU NÀO". PHÉP THỬ PHÁ: bỏ `eval=frame` ở
#: `sup_toi` (đúng cái bẫy mã nguồn ghi là BẮT BUỘC) -> `eq` chỉ tính biểu thức
#: MỘT LẦN lúc init, gặp `t=0` nên sóng ra ÂM -> "Sụp tối" **LÀM SÁNG THÊM
#: 43%**: tỉ lệ sáng đáy **0,409 -> 1,434**. Cổng vẫn in "ĐẠT 14 · HỎNG 0" và
#: trả mã 0. Hiệu ứng làm NGƯỢC HẲN việc của nó mà không ai biết.
#: Bảng dưới chốt CHIỀU cho các kiểu ăn vào độ sáng — thứ mắt anh Hùng nhìn ra
#: ngay còn cổng thì không.
CHIEU = {
    # khoá: (trần trên, sàn dưới) của tỉ lệ sáng trong cửa sổ
    "sup_toi": (0.90, NG_TOI),      # TỐI đi: <= 0,90 (mà không dưới 0,35)
    "toi_vien": (0.90, NG_TOI),     # tối 4 góc
    "sh_toi_vien": (0.99, NG_TOI),
    "loe_sang": (99.0, 1.00),       # SÁNG lên: đỉnh không được dưới bản gốc
    "nhay_sang": (99.0, 0.95),      # nháy SÁNG (đã bỏ nửa chu kỳ âm)
}

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def chay(cmd: list, giay: int = 420) -> tuple[int, str]:
    r = subprocess.run([str(x) for x in cmd], capture_output=True,
                       creationflags=_NOWIN, timeout=giay)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", p], capture_output=True,
                       creationflags=_NOWIN, timeout=240)
    try:
        return int((r.stdout or b"").decode().strip().split(",")[0])
    except (ValueError, IndexError):
        return -1


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def _doc(p: str) -> list[float]:
    if not os.path.exists(p):
        return []
    out = []
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            if "YAVG" in ln:
                m = re.search(r"=\s*([-\d.]+)\s*$", ln.strip())
                if m:
                    try:
                        out.append(float(m.group(1)))
                    except ValueError:
                        pass
    return out


def do_cap(goc: str, sau: str, td: str) -> tuple[list, list, list]:
    """1 lệnh ffmpeg -> (sáng_gốc[], sáng_sau[], %pixel_đổi[]) TỪNG KHUNG,
    ĐỘ PHÂN GIẢI GỐC. Xem bẫy (a) và (b) ở đầu file."""
    f0, f1, fd = (os.path.join(td, x) for x in ("_l0.txt", "_l1.txt", "_dd.txt"))
    for f in (f0, f1, fd):
        try:
            os.remove(f)
        except OSError:
            pass
    g = (f"[0:v]format=yuv420p,split=2[a][a2];"
         f"[1:v]format=yuv420p,split=2[b][b2];"
         f"[a][b]blend=all_mode=difference,"
         f"lutyuv=y='if(gt(val,12),255,0)',signalstats,"
         f"metadata=print:key=lavfi.signalstats.YAVG:file='{_esc(fd)}'[d];"
         f"[a2]signalstats,"
         f"metadata=print:key=lavfi.signalstats.YAVG:file='{_esc(f0)}'[x0];"
         f"[b2]signalstats,"
         f"metadata=print:key=lavfi.signalstats.YAVG:file='{_esc(f1)}'[x1];"
         f"[x0]nullsink;[x1]nullsink")
    rc, err = chay([FF, "-v", "error", "-i", goc, "-i", sau,
                    "-filter_complex", g, "-map", "[d]", "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError("lệnh đo hỏng: " + err[-400:])
    return (_doc(f0), _doc(f1), [v / 2.55 for v in _doc(fd)])


def nguon(td: str) -> str:
    """5 giây SÁNG cắt từ video THẬT trên máy; không có thì dựng bằng lavfi.

    Mốc phải ở CẢNH SÁNG: cảnh gần đen thì mọi phép so độ sáng đều FAIL OAN
    (bài học cổng 36 — nguồn Nhật ở giây 20 sáng TB chỉ 3,3/255)."""
    dst = os.path.join(td, "goc.mp4")
    kho = Path("D:/video test/Đã tải")
    cand = (sorted((p for p in kho.iterdir()
                    if p.suffix.lower() in (".mp4", ".mkv", ".webm")),
                   key=lambda p: p.stat().st_size)[:6] if kho.is_dir() else [])
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
            s0, _, _ = do_cap(dst, dst, td)
            if len(s0) >= int(DAI * FPS) - 3 and s0 and min(s0) > 45:
                print(f"  [nguồn] {p.name[:48]} @ {ss}s · sáng "
                      f"{sum(s0)/len(s0):.1f}/255 (thấp nhất {min(s0):.1f})")
                return dst
    rc, err = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"testsrc2=s={W}x{H}:r={FPS}:d={DAI}", "-an", "-c:v",
                    "libx264", "-preset", "veryfast", "-crf", "18", dst])
    if rc != 0:
        raise RuntimeError("không dựng nổi nguồn: " + err[-300:])
    print("  [nguồn] lavfi testsrc2 (máy không có video thật)")
    return dst


def quet_mot(k: str, src: str, td: str, n_goc: int, font: str) -> dict:
    ch = HU.chuoi_filter([{"khoa": k, "bat": BAT, "het": HET,
                           "dam": HU.DAM_MAX}], W, H, FPS, font)
    if not ch:
        return {"kq": "BỎ-QUA", "ghi": "chuỗi filter rỗng (thiếu font/shader)"}
    dst = os.path.join(td, f"e_{k}.mp4")
    cmd = [FF, "-y", "-v", "error"]
    if HU.can_vulkan([{"khoa": k}]):
        cmd += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
    cmd += ["-i", src, "-an", "-vf", ch, "-c:v", "libx264", "-preset",
            "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst]
    rc, err = chay(cmd)
    if rc != 0:
        return {"kq": "FFMPEG-LỖI",
                "ghi": (err.strip().splitlines() or [""])[-1][:110]}
    n = dem_khung(dst)
    s0, s1, dd = do_cap(src, dst, td)
    if not s1:
        return {"kq": "0-KHUNG", "ghi": f"nb_read_frames={n}"}
    m = min(len(s0), len(s1), len(dd))
    i0, i1 = int(BAT * FPS), int(HET * FPS)
    den, toi = [], []
    for i in range(m):
        tr = s1[i - 1] if i else 0.0
        if (tr > 5 and s1[i] < NG_DEN * tr) or \
           (s0[i] > 5 and s1[i] < NG_DEN * s0[i]):
            den.append(i)
        elif s0[i] > 5 and s1[i] < NG_TOI * s0[i]:
            toi.append(i)
    trong_i = list(range(max(0, i0 + 1), min(m, i1)))
    ngoai_i = [i for i in range(m) if i < i0 - 1 or i > i1 + 1]
    trong = max((dd[i] for i in trong_i), default=-1.0)
    ngoai = max((dd[i] for i in ngoai_i), default=0.0)
    ty = min((s1[i] / s0[i]) for i in trong_i if s0[i] > 5) if trong_i else 1.0
    # ĐỈNH sáng trong cửa sổ — cần cho kiểu LÀM SÁNG (`loe_sang`, `nhay_sang`):
    # chúng chỉ sáng ở GIỮA cửa sổ nên `min` không nói được gì về chiều.
    ty_max = (max((s1[i] / s0[i]) for i in trong_i if s0[i] > 5)
              if trong_i else 1.0)
    so = {"khung": n, "trong": round(trong, 2), "ngoai": round(ngoai, 2),
          "den": den[:5], "toi": toi[:5], "ty_sang": round(ty, 3),
          "ty_dinh": round(ty_max, 3), "ghi": ""}
    if n != n_goc:
        so["kq"] = "LỆCH-KHUNG"
    elif den:
        so["kq"] = "KHUNG-ĐEN"
    elif toi:
        so["kq"] = "TỐI-SÂU"
    elif trong < NG_CHAY:
        so["kq"] = "KHÔNG-CHẠY"
    elif ngoai > NG_RO:
        so["kq"] = "RÒ-NGOÀI"
    else:
        so["kq"] = "ĐẠT"
    # CHIỀU (xem bảng `CHIEU`): kiểu ăn vào độ sáng phải đi ĐÚNG hướng. Kiểu
    # TỐI xét đáy (`ty_sang`), kiểu SÁNG xét đỉnh (`ty_dinh`).
    if k in CHIEU and so["kq"] == "ĐẠT":
        tren, duoi = CHIEU[k]
        do_ = ty if tren <= 1.0 else ty_max
        if not (duoi <= do_ <= tren):
            so["kq"] = "SAI-CHIỀU"
            so["ghi"] = (f"tỉ lệ sáng {do_:.3f} ngoài khoảng "
                         f"[{duoi}..{tren}] — hiệu ứng đi NGƯỢC việc của nó")
    return so


def ca_duong_xuat_that(src: str, td: str) -> None:
    """Đường xuất THẬT (`export_canvas_clip`: nền mờ + khối video + hiệu ứng)
    cũng KHÔNG được ra khung đen. Quét từng kiểu ở trên chạy `-vf` trần; ca này
    chứng minh đúng ống dẫn anh Hùng dùng cũng sạch — `zoompan` đặt SAU
    `overlay` là chỗ dễ ra viền/khung đen nhất."""
    print("\n[CA 2] ĐƯỜNG XUẤT THẬT (nền mờ + khối video) — không khung đen")
    from app.core.ffmpeg_utils import export_canvas_clip
    hu = [{"bat": 0.60, "het": 1.00, "khoa": "zoom_nhoi", "dam": HU.DAM_MAX},
          {"bat": 2.20, "het": 2.60, "khoa": "sup_toi", "dam": HU.DAM_MAX},
          {"bat": 3.40, "het": 3.80, "khoa": "loe_sang", "dam": HU.DAM_MAX}]
    a = os.path.join(td, "canvas_khong.mp4")
    b = os.path.join(td, "canvas_co.mp4")
    for dst, e in ((a, "tat"), (b, hu)):
        export_canvas_clip(src, dst, [(0.2, 4.8)], (0.5, 0.5, 1.0), bg="blur",
                           out_w=540, out_h=960, encoder="libx264",
                           hieu_ung=e, fx_whoosh=False, chuyen_canh="tat")
    s0, s1, dd = do_cap(a, b, td)
    m = min(len(s0), len(s1), len(dd))
    den = [i for i in range(m)
           if (i and s1[i - 1] > 5 and s1[i] < NG_DEN * s1[i - 1])
           or (s0[i] > 5 and s1[i] < NG_DEN * s0[i])]
    toi = [i for i in range(m) if s0[i] > 5 and s1[i] < NG_TOI * s0[i]]
    bao("đủ khung (bản có hiệu ứng == bản tắt)",
        dem_khung(a) == dem_khung(b) and dem_khung(a) > 0,
        f"{dem_khung(a)} vs {dem_khung(b)} khung")
    bao("KHÔNG khung nào đen trên đường xuất thật", not den,
        f"khung đen: {den[:8]}" if den else
        f"sáng thấp nhất {min(s1):.1f}/255 (gốc {min(s0):.1f})")
    bao("KHÔNG khung nào tối dưới 35% bản gốc", not toi,
        f"khung tối: {toi[:8]}" if toi else
        f"tỉ lệ sáng thấp nhất {min((s1[i]/s0[i]) for i in range(m) if s0[i] > 5):.2f}")
    bao("3 điểm nhấn đều ĐỔI ĐƯỢC HÌNH trên đường xuất thật",
        all(max(dd[max(0, int(c['bat']*30)):int(c['het']*30)] or [0]) >= NG_CHAY
            for c in hu),
        " · ".join(f"{c['khoa']} "
                   f"{max(dd[max(0,int(c['bat']*30)):int(c['het']*30)] or [0]):.1f}%"
                   for c in hu))


def ca_tu_kiem(src: str, td: str) -> None:
    """PHÉP ĐO PHẢI BẮT ĐƯỢC LỖI THẬT — nếu không, cổng này chỉ là con dấu.

    Dựng lại ĐÚNG công thức CŨ của "Sụp tối" (`eq=brightness=-0.34`, phép TRỪ
    THẲNG) — cái đã làm anh Hùng thấy *"tối đen không thấy gì rồi lại hiện"* —
    rồi bắt bộ dò phải kêu. Cùng lúc dựng công thức MỚI (phép NHÂN) và bắt nó
    im. Không có ca này thì đổi ngưỡng sai một chỗ là cổng xanh vĩnh viễn."""
    print("\n[CA 4] TỰ KIỂM BỘ DÒ: công thức CŨ phải bị bắt, công thức MỚI thì không")
    a, b = int(BAT * FPS), int(HET * FPS)
    song = f"sin(3.14159*(t-{BAT:.3f})/({HET:.3f}-{BAT:.3f}))"
    en = f":enable='between(t,{BAT:.3f},{HET:.3f})'"
    ca = {
        "CŨ (trừ thẳng)": f"eq=brightness=-0.34{en}",
        "MỚI (nhân)": (f"eq=contrast='1-0.55*{song}':"
                       f"brightness='-0.275*{song}':eval=frame{en}"),
    }
    kq = {}
    for ten, ch in ca.items():
        dst = os.path.join(td, f"tk_{len(kq)}.mp4")
        rc, err = chay([FF, "-y", "-v", "error", "-i", src, "-an", "-vf", ch,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                        "-pix_fmt", "yuv420p", dst])
        s0, s1, _dd = do_cap(src, dst, td)
        m = min(len(s0), len(s1))
        den = [i for i in range(m)
               if (i and s1[i - 1] > 5 and s1[i] < NG_DEN * s1[i - 1])
               or (s0[i] > 5 and s1[i] < NG_DEN * s0[i])]
        toi = [i for i in range(m) if s0[i] > 5 and s1[i] < NG_TOI * s0[i]]
        ty = min((s1[i] / s0[i]) for i in range(a + 1, min(m, b))
                 if s0[i] > 5)
        kq[ten] = (rc, den, toi, ty)
    rc, den, toi, ty = kq["CŨ (trừ thẳng)"]
    bao("công thức CŨ BỊ BẮT (khung đen hoặc tối sâu)", bool(den or toi),
        f"rc={rc} · khung đen {den[:4]} · khung tối {len(toi)} · "
        f"sáng thấp nhất còn {ty*100:.1f}% bản gốc")
    rc, den, toi, ty = kq["MỚI (nhân)"]
    bao("công thức MỚI SẠCH (không đen, không tối sâu)", not (den or toi),
        f"rc={rc} · sáng thấp nhất còn {ty*100:.1f}% bản gốc "
        f"(ngưỡng {NG_TOI*100:.0f}%)")


def main() -> int:
    HU.dat_frei0r_path()
    td = tempfile.mkdtemp(prefix="_hukhung_", dir=str(_SB))
    try:
        print("[CA 0] ĐỐI CHỨNG phép đo (bẫy `format=gray`)")
        src = nguon(td)
        n_goc = dem_khung(src)
        s0, s1, dd = do_cap(src, src, td)
        bao("so file GỐC với CHÍNH NÓ ra 0,00% pixel đổi",
            bool(dd) and max(dd) < 0.01,
            f"max {max(dd) if dd else -1:.4f}% · {len(dd)} khung")
        bao("đọc được độ sáng từng khung", len(s0) == n_goc and n_goc > 0,
            f"{len(s0)}/{n_goc} khung · sáng TB "
            f"{(sum(s0)/len(s0) if s0 else 0):.1f}/255")

        print(f"\n[CA 1] QUÉT {len(HU.KHO)} KIỂU TRONG KHO "
              f"(1080x1920, cửa sổ {BAT}-{HET}s, độ đậm {HU.DAM_MAX})")
        font = HU.font_mac_dinh("")
        bang = []
        for k in list(HU.KHO):
            so = quet_mot(k, src, td, n_goc, font)
            bang.append((k, HU.KHO[k].ten, so))
            print(f"    {k:<16}{so['kq']:<12} trong {so.get('trong',-1):6.2f}%"
                  f" · ngoài {so.get('ngoai',-1):5.2f}% · sáng đáy/đỉnh so gốc "
                  f"{so.get('ty_sang',-1)}/{so.get('ty_dinh',-1)} "
                  f"{so.get('ghi','')}")
        xau = [(k, t, s) for k, t, s in bang if s["kq"] not in ("ĐẠT",)]
        bao(f"cả {len(bang)} kiểu trong kho ĐẠT (không đen / không chết / "
            f"không rò / KHÔNG SAI CHIỀU)", not xau,
            "; ".join(f"{k}={s['kq']} {s.get('ghi','')}" for k, _t, s in xau)
            if xau else f"{len(bang)}/{len(bang)} ĐẠT")
        # bảng cho anh Hùng đọc
        print(f"\n  {'khoá':<16}{'tên':<26}{'kết quả':<12}{'%trong':>8}"
              f"{'%ngoài':>8}{'sáng đáy':>10}{'sáng đỉnh':>11}")
        print("  " + "-" * 88)
        _tra = {kk: ss for kk, _t, ss in bang}
        for k, t, s in bang:
            print(f"  {k:<16}{t[:25]:<26}{s['kq']:<12}"
                  f"{s.get('trong',-1):>8.2f}{s.get('ngoai',-1):>8.2f}"
                  f"{s.get('ty_sang',-1):>10}{s.get('ty_dinh',-1):>11}")
        # bộ dò CHIỀU phải THỰC SỰ có việc để làm (không thì lại là con dấu)
        bao("mọi kiểu bị canh CHIỀU đều có mặt trong kho + đo được số",
            all(k in _tra and _tra[k].get("ty_sang") is not None
                for k in CHIEU),
            " · ".join(f"{k}={_tra[k].get('ty_sang')}/{_tra[k].get('ty_dinh')}"
                       for k in CHIEU if k in _tra))

        ca_duong_xuat_that(src, td)

        print("\n[CA 3] KHO KHÔNG CÒN KIỂU ĐÃ GỠ")
        for k in ("sang_diu", "sh_net_hon", "sh_quang_sang", "sh_mo_net"):
            bao(f"`{k}` đã gỡ khỏi KHO", k not in HU.KHO,
                "còn trong kho!" if k in HU.KHO else "không còn")
        moi = {v for hang in HU._UV_THEO_LOAI.values() for v in hang}
        bao("bảng chọn kiểu không trỏ tới kiểu đã gỡ",
            moi <= set(HU.KHO), f"thừa: {sorted(moi - set(HU.KHO))}")

        ca_tu_kiem(src, td)
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
