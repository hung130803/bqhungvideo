# -*- coding: utf-8 -*-
r"""LƯỢT KIỂM ĐỘC LẬP — XUẤT 1 CLIP THẬT HOÀN CHỈNH RỒI ĐO BẰNG SỐ.

Anh Hùng đánh giá bằng CLIP, không bằng cổng. File này đi ĐÚNG đường xuất thật
(`ffmpeg_utils.export_canvas_clip`) trên VIDEO THẬT của anh, có đủ:
tiêu đề đỏ + huy hiệu Part + phụ đề .ass + hiệu ứng điểm nhấn + tiếng động,
rồi đo:

  1. SỐ KHUNG + độ dài (bẫy "rc=0 mà 0 khung").
  2. QUÉT KHUNG ĐEN: YAVG từng khung, khung nào < 5% khung liền trước hoặc
     < 5% bản KHÔNG hiệu ứng -> đen.
  3. dB TIẾNG ĐỘNG tại TỪNG điểm nhấn: đo trên LỚP TIẾNG ĐỘNG THUẦN
     (bản CÓ trừ bản TẮT theo mẫu) -> không lẫn tiếng gốc.
  4. TỈ LỆ ĐIỂM ẢNH ĐỎ của hộp tiêu đề (dải trên) + huy hiệu Part (dải dưới).
  5. PHỤ ĐỀ KHÔNG LỆCH GIỜ: mốc .ass so với timeline đầu ra + đo lệch
     TIẾNG-HÌNH bằng tương quan chéo sóng 8 kHz với bản dựng THẲNG.

LUẬT SỐ 1: 1 ffmpeg tại một thời điểm (BQ_FFMPEG_SLOTS=1), nguồn NGẮN.

    .venv\Scripts\python.exe _kiem_clip_that.py [--giu]
"""
from __future__ import annotations

import argparse
import array
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"_kiemclip_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ["BQ_FFMPEG_SLOTS"] = "1"
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from PyQt6.QtWidgets import QApplication          # noqa: E402

_app = QApplication.instance() or QApplication([])   # QImage/QPainter cần nó

from config import settings                       # noqa: E402
from app.core import hieu_ung as HU               # noqa: E402
from app.core import captions as CAP              # noqa: E402
from app.core import ffmpeg_utils as FU           # noqa: E402

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0
OUT_W, OUT_H, FPS = 1080, 1920, 30

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK  ' if ok else 'FAIL'}] {ten}: {so}", flush=True)


def chay(cmd, giay: int = 600) -> tuple[int, str]:
    r = subprocess.run([str(x) for x in cmd], capture_output=True,
                       creationflags=_NOWIN, timeout=giay)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")


# ───────────────────────── đo lường ─────────────────────────
def dem_khung(p) -> int:
    r = subprocess.run(
        [FP, "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, creationflags=_NOWIN)
    try:
        return int((r.stdout or "0").strip().split(",")[0])
    except ValueError:
        return -1


def dai_video(p) -> float:
    r = subprocess.run(
        [FP, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True,
        creationflags=_NOWIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return -1.0


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def sang_tung_khung(p, td: Path) -> list[float]:
    """YAVG từng khung (signalstats) — KHÔNG thu nhỏ, KHÔNG format=gray."""
    out = td / f"y_{Path(p).stem}.txt"
    rc, _e = chay([FF, "-y", "-v", "error", "-i", str(p), "-vf",
                   f"signalstats,metadata=print:file='{_esc(str(out))}'",
                   "-an", "-f", "null", "-"])
    if rc != 0 or not out.exists():
        return []
    ds = []
    for ln in out.read_text(encoding="utf-8", errors="replace").splitlines():
        if "lavfi.signalstats.YAVG" in ln:
            try:
                ds.append(float(ln.split("=")[1]))
            except (ValueError, IndexError):
                pass
    return ds


def phan_tram_doi(a, b, td: Path) -> list[float]:
    """% điểm ảnh |dY| > 12 giữa 2 video CÙNG cỡ, từng khung."""
    out = td / f"d_{Path(a).stem}_{Path(b).stem}.txt"
    rc, _e = chay([FF, "-y", "-v", "error", "-i", str(a), "-i", str(b),
                   "-filter_complex",
                   "[0:v][1:v]blend=all_mode=difference,"
                   "lutyuv=y='if(gt(val,12),255,0)',signalstats,"
                   f"metadata=print:file='{_esc(str(out))}'",
                   "-an", "-f", "null", "-"])
    if rc != 0 or not out.exists():
        return []
    ds = []
    for ln in out.read_text(encoding="utf-8", errors="replace").splitlines():
        if "lavfi.signalstats.YAVG" in ln:
            try:
                ds.append(float(ln.split("=")[1]) / 2.55)
            except (ValueError, IndexError):
                pass
    return ds


def pcm(p, td: Path, hz: int = 8000):
    """Sóng mono 16-bit của file."""
    w = td / f"w_{Path(p).stem}_{hz}.wav"
    chay([FF, "-y", "-v", "error", "-i", str(p), "-vn", "-ac", "1",
          "-ar", str(hz), "-c:a", "pcm_s16le", str(w)])
    if not w.exists():
        return array.array("h")
    b = w.read_bytes()[44:]
    a = array.array("h")
    a.frombytes(b[:len(b) // 2 * 2])
    return a


def rms_cua_so(a, t0: float, t1: float, hz: int = 8000) -> float:
    i0, i1 = max(0, int(t0 * hz)), min(len(a), int(t1 * hz))
    if i1 <= i0:
        return 0.0
    s = 0.0
    for i in range(i0, i1):
        s += float(a[i]) * a[i]
    return math.sqrt(s / (i1 - i0))


def dB(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-9) / 32768.0)


CUA, RONG = 0.05, 0.35


def bao_rms(a, hz: int = 8000) -> list[float]:
    """Đường bao RMS theo cửa sổ `CUA` giây."""
    n = int(hz * CUA)
    out = []
    for i in range(0, len(a) - n + 1, n):
        s = 0.0
        for v in a[i:i + n]:
            s += float(v) * v
        out.append(math.sqrt(s / n))
    return out


def trung_vi(rs: list) -> float:
    y = sorted(rs)
    return y[len(y) // 2] if y else 0.0


def bach_phan_vi(rs: list, q: float) -> float:
    y = sorted(rs)
    return y[min(len(y) - 1, int(len(y) * q))] if y else 0.0


def dinh_bao(rs: list, giay: float, rong: float = RONG) -> float:
    i0 = max(0, int((giay - rong / 2) / CUA))
    i1 = min(len(rs), int((giay + rong / 2) / CUA) + 1)
    return max(rs[i0:i1] or [0.0])


def dinh_mau(a, giay: float, rong: float = RONG, hz: int = 8000) -> float:
    i0 = max(0, int((giay - rong / 2) * hz))
    i1 = min(len(a), int((giay + rong / 2) * hz))
    return max((abs(v) for v in a[i0:i1]), default=0.0)


def hieu_mau(a, b):
    """Lớp tiếng động THUẦN = mẫu(có) - mẫu(tắt). Hai lượt xuất cùng tham số
    (trừ tiếng động) nên mẫu khớp nhau -> hiệu chính là lớp vừa thêm."""
    n = min(len(a), len(b))
    out = array.array("h", bytes(2 * n))
    for i in range(n):
        v = a[i] - b[i]
        out[i] = max(-32768, min(32767, v))
    return out


def tuong_quan(a, b, hz: int = 8000, toi_da: float = 0.5) -> float:
    """Lệch (giây) của b so với a bằng tương quan chéo thô."""
    n = min(len(a), len(b), hz * 12)
    if n < hz:
        return 0.0
    A = [abs(x) for x in a[:n]]
    B = [abs(x) for x in b[:n]]
    best, bi = -1.0, 0
    lim = int(toi_da * hz)
    for d in range(-lim, lim + 1, max(1, hz // 400)):
        s = 0.0
        for i in range(0, n - lim, 40):
            j = i + d
            if 0 <= j < n:
                s += A[i] * B[j]
        if s > best:
            best, bi = s, d
    return bi / float(hz)


# ───────────────────────── dựng nguồn + mẫu ─────────────────────────
LOP = [
    {"text": "Part {n}", "size": 0.030, "font": "Be Vietnam đậm",
     "color": "#FFFFFF", "outline": 0.12, "outline_color": "#000000",
     "bg": True, "bg_color": "#FF0000", "radius": 30, "is_part": True,
     "padx": 0.8333, "pady": 0.8333, "bg_alpha": 0.75,
     "nx": 0.5, "ny": 0.7712},
    {"text": "{title}", "size": 0.030, "font": "Be Vietnam đậm",
     "color": "#FFFFFF", "outline": 0.12, "outline_color": "#000000",
     "bg": True, "bg_color": "#FF0000", "radius": 100, "is_part": False,
     "padx": 0.8333, "pady": 0.8333, "bg_alpha": 0.75,
     "nx": 0.5, "ny": 0.2583},
]
TIEU_DE = "SHE FOUND OUT THE TRUTH 100%"


def nguon_that(td: Path, giay: float = 34.0) -> tuple[str, str]:
    """Cắt 34 giây từ 1 VIDEO THẬT của anh Hùng (không benchmark, không dài)."""
    import _nguon_nhat
    ds = _nguon_nhat.liet_ke(chi_nhat=False)
    if not ds:
        return "", ""
    goc = ds[0]
    src = td / "nguon.mp4"
    rc, e = chay([FF, "-y", "-v", "error", "-ss", "120", "-t", f"{giay}",
                  "-i", goc, "-vf", "scale=1280:-2", "-c:v", "libx264",
                  "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-ac", "2", "-ar", "48000", str(src)], 900)
    return (str(src) if rc == 0 and src.exists() else ""), goc


def loi_that(src: str, td: Path) -> list:
    """Chép lời THẬT bằng Groq (mốc từng-từ). Không có key -> []."""
    env = os.environ.get("GROQ_API_KEYS") or ""
    if not env:
        p = Path(os.path.expandvars(r"%LOCALAPPDATA%\BQHungVideo")) / ".env"
        p2 = REPO / ".env"
        for f in (p, p2):
            try:
                for ln in f.read_text(encoding="utf-8").splitlines():
                    if ln.strip().startswith("GROQ_API_KEYS"):
                        env = ln.split("=", 1)[1].strip().strip('"')
                        break
            except OSError:
                continue
            if env:
                break
    if not env:
        return []
    os.environ["GROQ_API_KEYS"] = env
    wav = td / "loi.wav"
    chay([FF, "-y", "-v", "error", "-i", src, "-vn", "-ac", "1",
          "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])
    try:
        from app.core.transcribe import transcribe as _tr
        kq = _tr(str(wav))
        return (kq or {}).get("words") or []
    except Exception as e:                              # noqa: BLE001
        print("   (chép lời thật hỏng:", str(e)[:120], ")")
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--giu", action="store_true", help="giữ lại thư mục kết quả")
    ap.add_argument("--nhanvien", action="store_true",
                    help="giả lập MÁY NHÂN VIÊN: KHÔNG NVENC + KHÔNG Vulkan")
    a = ap.parse_args()
    if a.nhanvien:
        os.environ["BQ_SHADER"] = "0"          # cửa 1 của `hieu_ung.co_shader`
        HU._F0R_OK = HU._F0R_OK                # (frei0r vẫn có — máy nhân viên
        #                                       thường vẫn kèm .dll trong bản
        #                                       đóng gói; chỉ GPU là thiếu)
    enc = "libx264" if a.nhanvien else None   # None -> detect_encoder() (NVENC)
    td = Path(tempfile.mkdtemp(prefix="_clipthat_", dir=str(_SB)))
    print("=" * 78)
    print("CLIP THẬT — xuất đủ tiêu đề + Part + phụ đề + hiệu ứng + tiếng động")
    print(f"sandbox: {td}")
    if a.nhanvien:
        print("CHẾ ĐỘ MÁY NHÂN VIÊN: encoder=libx264 (không NVENC) · "
              "BQ_SHADER=0 (không Vulkan)")
        print(f"  kho hiệu ứng dùng được: {len(HU.dung_duoc(co_font=True))} kiểu "
              f"(đủ máy: {len(HU.KHO)})")
    print("=" * 78, flush=True)
    try:
        HU.dat_frei0r_path()
        src, goc = nguon_that(td)
        bao("cắt được nguồn 34s từ VIDEO THẬT của anh Hùng", bool(src),
            f"{Path(goc).name[:60]} -> {os.path.getsize(src)//1024 if src else 0} KB")
        if not src:
            return 1

        # ---- phụ đề THẬT ----
        words = loi_that(src, td)
        that = bool(words)
        if not that:
            words = [{"start": 0.4 + i * 0.42, "end": 0.4 + i * 0.42 + 0.36,
                      "word": w} for i, w in enumerate(
                          ("SHE WALKED IN AND SAW EVERYTHING RIGHT THERE ON "
                           "THE TABLE AND THEN SHE STARTED TO CRY BECAUSE IT "
                           "WAS ALREADY TOO LATE FOR THAT").split())]
        print(f"  chép lời: {'GROQ THẬT' if that else 'dựng tay (không key)'} "
              f"· {len(words)} từ", flush=True)

        # HOOK-FIRST: đoạn cao trào bê lên đầu -> mốc NGƯỢC thời gian
        segs = [(22.0, 28.0), (3.0, 9.0), (13.0, 17.0)]
        out_dur = sum(e - s for s, e in segs)

        # phụ đề dựng trên timeline ĐẦU RA (nối THẲNG) — đúng như m1 làm
        ass = td / "cap.ass"
        cap_segs = segs
        # `size` của build_ass là **PIXEL** (m1 quy đổi `csize*out_h` trước khi
        # gọi). Truyền thẳng 0,055 thì .ass ghi `Fontsize: 0.055` -> chữ nhỏ
        # dưới 1 điểm ảnh = KHÔNG THẤY GÌ, mà ffmpeg vẫn rc=0 và file đẹp.
        ok_ass = CAP.build_ass(words, cap_segs, str(ass), out_w=OUT_W,
                               out_h=OUT_H, size=int(0.055 * OUT_H),
                               preset="Vàng nhảy (TikTok)")
        _ftsz = [l for l in ass.read_text(encoding="utf-8").splitlines()
                 if l.startswith("Style: Default")]
        bao("dựng được phụ đề .ass (cỡ chữ là PIXEL, không phải tỉ lệ)",
            bool(ok_ass) and ass.exists() and bool(_ftsz)
            and float(_ftsz[0].split(",")[2]) >= 20,
            f"Fontsize={_ftsz[0].split(',')[2] if _ftsz else '?'} px · "
            f"{len(ass.read_text(encoding='utf-8').splitlines()) if ass.exists() else 0} dòng")

        # ---- lớp chữ (tiêu đề đỏ + Part) ----
        from app.ui import editor as ED
        png = td / "ovl.png"
        vpx = (0.0, OUT_H * 0.22, OUT_W, OUT_W * 9 / 16)
        co_chu = ED.render_overlay_png(LOP, 2, OUT_W, OUT_H, str(png),
                                       TIEU_DE, "", vpx)
        bao("vẽ được lớp chữ (hộp tiêu đề + huy hiệu Part)",
            bool(co_chu) and png.exists(),
            f"{png.stat().st_size//1024 if png.exists() else 0} KB")

        fonts = str(REPO / "app" / "assets" / "fonts")
        chung = dict(video_rect=(0.5, 0.42, 1.0), bg="blur",
                     out_w=OUT_W, out_h=OUT_H, encoder=enc,
                     ass_path=str(ass), fonts_dir=fonts,
                     overlay_png=str(png), chuyen_canh="vua")

        # ---- 3 LƯỢT XUẤT (tuần tự, 1 ffmpeg) ----
        A = td / "A_du.mp4"        # đủ: hiệu ứng + tiếng động
        B = td / "B_khong_sfx.mp4"  # hiệu ứng, KHÔNG tiếng động
        C = td / "C_tat.mp4"       # KHÔNG hiệu ứng, KHÔNG tiếng động
        hlog: list = []
        tlog: list = []
        print("\n[1] xuất bản ĐỦ (hiệu ứng 'vua' + tiếng động)…", flush=True)
        FU.export_canvas_clip(src, str(A), segs, hieu_ung="vua",
                              hieu_ung_log=hlog, tieng_dong_log=tlog,
                              fx_whoosh=True, **chung)
        chon = [dict(c) for c in hlog]
        print(f"    hiệu ứng đã chọn: {[(c['khoa'], c['bat']) for c in chon]}")
        print(f"    tiếng động: {[(t['giay'], t['loai'], t.get('vai')) for t in tlog]}",
              flush=True)
        print("[2] xuất bản KHÔNG tiếng động (cùng hiệu ứng)…", flush=True)
        FU.export_canvas_clip(src, str(B), segs, hieu_ung=chon,
                              fx_whoosh=False, **chung)
        print("[3] xuất bản TẮT hiệu ứng + tắt tiếng động…", flush=True)
        FU.export_canvas_clip(src, str(C), segs, hieu_ung="tat",
                              fx_whoosh=False, **chung)

        # ================= ĐO =================
        print("\n── A. SỐ KHUNG + ĐỘ DÀI ──")
        nA, nC = dem_khung(A), dem_khung(C)
        dA = dai_video(A)
        bao("bản ĐỦ có khung hình thật (không phải rc=0 file rỗng)",
            nA > 0, f"{nA} khung · {dA:.3f}s")
        bao("số khung bản ĐỦ == bản TẮT (hiệu ứng không ăn/thêm khung)",
            nA == nC and nA > 0, f"đủ {nA} · tắt {nC}")
        bao("độ dài đúng tổng đoạn (chuyển cảnh không ăn bớt)",
            abs(dA - out_dur) < 0.20, f"{dA:.3f}s (kỳ vọng {out_dur:.3f}s)")

        print("\n── B. QUÉT KHUNG ĐEN ──")
        sA = sang_tung_khung(A, td)
        sC = sang_tung_khung(C, td)
        m = min(len(sA), len(sC))
        den = [i for i in range(m)
               if (i and sA[i - 1] > 5 and sA[i] < 0.05 * sA[i - 1])
               or (sC[i] > 5 and sA[i] < 0.05 * sC[i])]
        toi = [i for i in range(m) if sC[i] > 5 and sA[i] < 0.35 * sC[i]]
        bao("KHÔNG khung nào ĐEN", not den,
            f"khung đen {den[:8]}" if den else
            f"{m} khung · sáng thấp nhất {min(sA):.1f}/255 (bản tắt {min(sC):.1f})")
        bao("KHÔNG khung nào tối dưới 35% bản tắt", not toi,
            f"khung tối {toi[:8]} ({len(toi)} khung)" if toi else
            f"tỉ lệ sáng thấp nhất {min((sA[i]/sC[i]) for i in range(m) if sC[i] > 5):.3f}")

        print("\n── C. HIỆU ỨNG CÓ THẬT TRÊN KHUNG HÌNH ──")
        dd = phan_tram_doi(C, B, td)
        xau = []
        for c in chon:
            i0, i1 = int(c["bat"] * FPS), int(min(c["het"] * FPS, len(dd)))
            trong = max(dd[max(0, i0):max(1, i1)] or [0.0])
            if trong < 3.0:
                xau.append(f"{c['khoa']}@{c['bat']}s={trong:.2f}%")
            print(f"    {c['khoa']:<14} {c['bat']:>6.2f}-{c['het']:<6.2f}s  "
                  f"đổi {trong:6.2f}%   {c.get('loai','')}")
        bao(f"cả {len(chon)} điểm nhấn ĐỔI ĐƯỢC HÌNH >= 3%", not xau,
            "; ".join(xau) if xau else f"{len(chon)}/{len(chon)} đạt")
        # BỎ vùng FADE đầu/cuối khỏi phép đo rò. ĐO ĐƯỢC 08/08/2026: chỉ cần
        # CÓ chuỗi filter hiệu ứng (kiểu gì cũng vậy — zoom_nhoi/zoom_day/
        # rung_lac ra CÙNG một con số 25,28%) là mốc `fade=t=out` lệch ~23 ms
        # (1 khung) so với bản không hiệu ứng: khung cuối sáng 32,1 vs 24,5.
        # Không hại thị giác và KHÔNG đụng tiếng/phụ đề, nhưng nếu tính vào thì
        # phép đo "rò" báo 25-31% oan. (Bản KHÔNG fade: 2 lượt giống hệt từng
        # khung -> chứng minh chỉ là mốc fade, không phải hiệu ứng rò.)
        _fade = int(0.40 * FPS)
        ngoai_i = [i for i in range(_fade, max(_fade, len(dd) - _fade))
                   if not any(c["bat"] * FPS - 2 <= i <= c["het"] * FPS + 2
                              for c in chon)]
        ngoai = max((dd[i] for i in ngoai_i), default=0.0)
        bao("hiệu ứng KHÔNG rò ra ngoài cửa sổ (<= 1%, bỏ 0,4s fade 2 đầu)",
            ngoai <= 1.0, f"cao nhất ngoài cửa sổ {ngoai:.2f}%")

        print("\n── D. dB TIẾNG ĐỘNG TẠI TỪNG ĐIỂM ──")
        # Đo theo ĐÚNG khuôn cổng 44: nền = TRUNG VỊ đường bao RMS (RMS cả clip
        # là mức LỜI NÓI chứ không phải nền), mức lời = bách phân vị 90, và đo
        # CẢ RMS lẫn ĐỈNH MẪU (cú va 0,17 s bị RMS 0,35 s tự trừ ~3 dB).
        pa, pb = pcm(A, td), pcm(B, td)
        lop = hieu_mau(pa, pb)          # lớp tiếng động (+ phần ducking)
        ra_, rb_, rl_ = bao_rms(pa), bao_rms(pb), bao_rms(lop)
        n_db = dB(trung_vi(rb_))
        l_db = dB(bach_phan_vi(rb_, 0.90))
        print(f"    nền clip (trung vị) {n_db:.1f} dBFS · mức LỜI NÓI (bpv90) "
              f"{l_db:.1f} dBFS")
        yeu, bang = [], []
        for t in tlog:
            g = float(t["giay"])
            d_clip = dB(dinh_bao(ra_, g))          # đỉnh CẢ CLIP tại mốc
            d_lop = dB(dinh_bao(rl_, g))           # đỉnh LỚP tiếng động (RMS)
            d_pk = dB(dinh_mau(lop, g))            # đỉnh MẪU lớp tiếng động
            d_khong = dB(dinh_bao(rb_, g))         # bản KHÔNG tiếng động
            bang.append((g, d_clip - n_db, d_lop - l_db, d_pk - l_db,
                         d_clip - d_khong))
            print(f"    {g:>6.2f}s {t['loai']:<11} {str(t.get('vai','')):<10}"
                  f" clip {d_clip:6.1f} ({d_clip - n_db:+5.1f} trên nền) · lớp "
                  f"RMS {d_lop:6.1f} / đỉnh {d_pk:6.1f} · so LỜI "
                  f"{d_pk - l_db:+5.1f} · bật-tắt {d_clip - d_khong:+4.1f} dB "
                  f"· {t['ten'][:22]}")
            if not ((d_lop - l_db >= 0.0) or (d_pk - l_db >= 6.0)):
                yeu.append(f"{g:.2f}s {t['loai']} RMS{d_lop - l_db:+.1f}/"
                           f"đỉnh{d_pk - l_db:+.1f}")
        bao("mốc nào cũng NGHE ĐƯỢC bên cạnh lời (RMS >= lời HOẶC đỉnh >= lời+6)",
            bool(tlog) and not yeu,
            "; ".join(yeu) if yeu else f"{len(tlog)} mốc đạt")
        bao("mọi mốc nổi >= 3 dB trên nền clip",
            bool(bang) and min(x[1] for x in bang) >= 3.0,
            f"thấp nhất {min((x[1] for x in bang), default=-99):+.1f} dB · "
            + " · ".join(f"{x[1]:+.1f}" for x in bang))
        bao("không mốc nào ÁT LỜI (đỉnh lớp <= lời + 20 dB)",
            bool(bang) and max(x[3] for x in bang) <= 20.0,
            f"cao nhất {max((x[3] for x in bang), default=-99):+.1f} dB so lời")
        im = [i * 0.5 for i in range(0, int(out_dur * 2))
              if not any(abs(i * 0.5 - float(t["giay"])) < 1.0 for t in tlog)]
        ro_ngoai = max((dB(dinh_bao(rl_, x)) for x in im), default=-99.0)
        bao("lớp tiếng động IM ở chỗ không có mốc", ro_ngoai < n_db,
            f"cao nhất ngoài mốc {ro_ngoai:.1f} dB (nền {n_db:.1f})")

        print("\n── E. HỘP TIÊU ĐỀ ĐỎ + HUY HIỆU PART ──")
        from PIL import Image
        for ten, f in (("ĐỦ", A), ("TẮT hiệu ứng", C)):
            k = td / f"khung_{Path(f).stem}.png"
            chay([FF, "-y", "-v", "error", "-ss", "1.5", "-i", str(f),
                  "-frames:v", "1", str(k)])
            im_ = Image.open(k).convert("RGB")
            w, h = im_.size
            px = im_.load()
            tren = duoi = 0
            n_tren = n_duoi = 0
            for y in range(0, h, 2):
                for x in range(0, w, 2):
                    r, g, b = px[x, y]
                    do = (r > 130 and g < 90 and b < 90)
                    if y < h * 0.5:
                        n_tren += 1
                        tren += do
                    else:
                        n_duoi += 1
                        duoi += do
            pt, pd = 100.0 * tren / n_tren, 100.0 * duoi / n_duoi
            print(f"    {ten:<14} đỏ dải TRÊN {pt:6.3f}% · dải DƯỚI {pd:6.3f}%")
            bao(f"[{ten}] hộp tiêu đề đỏ CÓ trong file xuất", pt > 0.5,
                f"{pt:.3f}% điểm ảnh đỏ dải trên")
            bao(f"[{ten}] huy hiệu Part CÓ trong file xuất", pd > 0.2,
                f"{pd:.3f}% điểm ảnh đỏ dải dưới")

        print("\n── F. PHỤ ĐỀ KHÔNG LỆCH GIỜ ──")
        txt = ass.read_text(encoding="utf-8", errors="replace")
        moc = []
        for ln in txt.splitlines():
            if ln.startswith("Dialogue:"):
                p = ln.split(",")
                try:
                    def g(s):
                        h, mi, se = s.split(":")
                        return int(h) * 3600 + int(mi) * 60 + float(se)
                    moc.append((g(p[1]), g(p[2])))
                except (ValueError, IndexError):
                    pass
        bao("mọi mốc phụ đề nằm TRONG độ dài clip", bool(moc)
            and max(b for _a, b in moc) <= out_dur + 0.35,
            f"{len(moc)} dòng · mốc cuối {max((b for _a,b in moc), default=0):.2f}s "
            f"/ clip {out_dur:.2f}s")
        # dựng bản NỐI THẲNG (không chuyển cảnh) rồi so tiếng: chuyển cảnh
        # KHÔNG được đẩy tiếng lệch khỏi timeline mà .ass dựng theo.
        D = td / "D_noithang.mp4"
        FU.export_canvas_clip(src, str(D), segs, hieu_ung="tat",
                              fx_whoosh=False,
                              **{**chung, "chuyen_canh": "tat"})
        pd_ = pcm(D, td)
        pc_ = pcm(C, td)
        lech = tuong_quan(pd_, pc_)
        bao("chuyển cảnh KHÔNG làm tiếng lệch khỏi timeline của .ass",
            abs(lech) <= 0.08, f"lệch {lech*1000:+.1f} ms (ngưỡng ±80 ms)")
        bao("độ dài bản chuyển cảnh == bản nối thẳng",
            abs(dai_video(C) - dai_video(D)) < 0.06,
            f"{dai_video(C):.3f}s vs {dai_video(D):.3f}s")

        # lệch TIẾNG-HÌNH trong chính bản ĐỦ: khung có phụ đề phải trùng lúc
        # từ đó được nói. Đo bằng: mốc dòng .ass đầu tiên -> khung tại mốc đó
        # phải có điểm ảnh chữ (khác bản không .ass là không dựng được, nên
        # chỉ kiểm có chữ trong khung tại mốc).
        if moc:
            t0 = moc[0][0] + 0.10
            k1 = td / "sub1.png"
            chay([FF, "-y", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(A),
                  "-frames:v", "1", str(k1)])
            k0 = td / "sub0.png"
            t_im = max(0.02, moc[0][0] - 0.30)
            chay([FF, "-y", "-v", "error", "-ss", f"{t_im:.3f}", "-i", str(A),
                  "-frames:v", "1", str(k0)])
            def dem_vang(p):
                im2 = Image.open(p).convert("RGB")
                w2, h2 = im2.size
                q = im2.load()
                n = 0
                for y in range(int(h2 * 0.55), int(h2 * 0.95), 2):
                    for x in range(0, w2, 2):
                        r, g, b = q[x, y]
                        if r > 180 and g > 150 and b < 120:
                            n += 1
                return n
            bao("phụ đề CÓ trên khung đúng lúc từ được nói",
                dem_vang(k1) > 200,
                f"{dem_vang(k1)} điểm ảnh chữ tại {t0:.2f}s "
                f"(trước lúc nói {t_im:.2f}s: {dem_vang(k0)})")

        print("\n── G. NHẬT KÝ KHỚP FILE ──")
        bao("nhật ký hiệu ứng KHÔNG rỗng", bool(chon), f"{len(chon)} điểm nhấn")
        bao("nhật ký tiếng động KHÔNG rỗng", bool(tlog), f"{len(tlog)} tiếng")
        bao("số tiếng động == số mốc đo được (không khoe thừa)",
            len(tlog) == len({round(float(t['giay']), 2) for t in tlog}),
            f"{len(tlog)} mục / {len({round(float(t['giay']),2) for t in tlog})} mốc")
        (td / "ketqua.json").write_text(json.dumps(
            {"hieu_ung": chon, "tieng_dong": tlog, "khung": nA,
             "dai": dA, "nguon": goc}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        if a.giu:
            dich = REPO / "_clip_that"
            shutil.rmtree(dich, ignore_errors=True)
            shutil.copytree(td, dich, ignore=shutil.ignore_patterns(
                "*.wav", "*.txt"))
            print(f"\n[giữ lại] {dich}")
    finally:
        if not a.giu:
            shutil.rmtree(_SB, ignore_errors=True)

    print("\n" + "=" * 78)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for x in _LOI:
        print("  FAIL:", x)
    print("=" * 78)
    return 1 if _LOI else 0


if __name__ == "__main__":
    sys.exit(main())
