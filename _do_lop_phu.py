# -*- coding: utf-8 -*-
"""BỘ ĐO cho nhóm LỚP PHỦ HẠT — chạy ffmpeg THẬT, đếm pixel THẬT.

Không phải cổng chặn (cổng là `_test_lop_phu.py`). Đây là cái THƯỚC dùng lúc
dò tham số: mỗi lần đổi biểu thức `geq` thì chạy lại để biết kiểu đó có THẤY
ĐƯỢC (>= 8% pixel |dY|>12) và có LOÈ MÀU (|dU|,|dV| >= 3) hay không.

Đo ở ĐÚNG 1080x1920 (bài học cổng 43: thu nhỏ rồi mới đo thì hạt bị san phẳng
-> kết luận oan "không hoạt động").

Chạy: .venv\\Scripts\\python.exe _do_lop_phu.py [khoá ...]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"do_lop_phu_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401

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
DAI = 4.0
BAT, HET = 1.20, 2.00


def chay(cmd: list, giay: int = 420) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    r = subprocess.run([str(x) for x in cmd], capture_output=True,
                       creationflags=_NOWIN, timeout=giay)
    return (r.returncode, (r.stderr or b"").decode("utf-8", "replace"),
            time.perf_counter() - t0)


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def _doc(p: str, khoa: str) -> list[float]:
    if not os.path.exists(p):
        return []
    out = []
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            if khoa in ln:
                m = re.search(r"=\s*([-\d.]+)\s*$", ln.strip())
                if m:
                    try:
                        out.append(float(m.group(1)))
                    except ValueError:
                        pass
    return out


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", p], capture_output=True,
                       creationflags=_NOWIN, timeout=300)
    try:
        return int((r.stdout or b"").decode().strip().split(",")[0])
    except (ValueError, IndexError):
        return -1


def do_cap(goc: str, sau: str, td: str) -> dict:
    """1 lệnh ffmpeg -> %pixel đổi + sáng + PHÂN BỐ CHROMA từng khung, ĐPG GỐC.

    === ĐO LỆCH MÀU THẾ NÀO CHO ĐÚNG (bản đầu của bộ đo này đã SAI) ===
    Bản đầu lấy `UAVG` của khung HIỆU (`blend=difference`) = lệch U trung bình
    TỪNG ĐIỂM ẢNH. Với lớp phủ thì số đó luôn to (tuyết đo 11,6) mà **không nói
    lên điều anh Hùng sợ**: che 20% khung bằng hạt TRẮNG không hề làm "tím cả
    khung", nó chỉ đặt vật thể trung tính lên trước.
    Bảng loại trừ trong `LOAI_DOI_MAU` (rgbashift U +7,16 · baltan U −3,08 ·
    vertigo U −2,83) là đo **PHÂN BỐ CHROMA CẢ KHUNG**: UAVG/VAVG trước và sau.
    Đây là thước đúng, và cũng là thước duy nhất phân biệt được "phủ vật thể"
    với "pha lại màu". Thêm `SATAVG` để bắt kiểu làm BẠC MÀU cả khung (đúng
    bệnh của `baltan`), thứ UAVG một mình không thấy.
    Bẫy đã ghi ở cổng 43: KHÔNG `format=gray` giữa chuỗi (dải đầy vs dải hẹp
    làm mọi kiểu ra 100%).
    """
    fd, f0, f1 = (os.path.join(td, x) for x in
                  ("_dd.txt", "_l0.txt", "_l1.txt"))
    for f in (fd, f0, f1):
        try:
            os.remove(f)
        except OSError:
            pass
    g = (f"[0:v]format=yuv420p,split=2[a][a2];"
         f"[1:v]format=yuv420p,split=2[b][b2];"
         f"[a][b]blend=all_mode=difference,"
         f"lutyuv=y='if(gt(val,12),255,0)',signalstats,"
         f"metadata=print:key=lavfi.signalstats.YAVG:file='{_esc(fd)}'[d];"
         f"[a2]signalstats,metadata=print:file='{_esc(f0)}'[x0];"
         f"[b2]signalstats,metadata=print:file='{_esc(f1)}'[x1];"
         f"[x0]nullsink;[x1]nullsink")
    rc, err, _ = chay([FF, "-v", "error", "-i", goc, "-i", sau,
                       "-filter_complex", g, "-map", "[d]", "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError("lệnh đo hỏng: " + err[-500:])
    return {"doi": [v / 2.55 for v in _doc(fd, "YAVG")],
            "sang0": _doc(f0, ".YAVG"), "sang1": _doc(f1, ".YAVG"),
            "u0": _doc(f0, ".UAVG"), "u1": _doc(f1, ".UAVG"),
            "v0": _doc(f0, ".VAVG"), "v1": _doc(f1, ".VAVG"),
            "s0": _doc(f0, ".SATAVG"), "s1": _doc(f1, ".SATAVG")}


def nguon(td: str) -> str:
    """Nguồn 4 giây TỰ SINH bằng lavfi — không phụ thuộc file trên máy user.

    `testsrc2` có ô màu bão hoà + chuyển động; đủ khắc nghiệt cho phép đo lệch
    màu và không bao giờ "gần đen" (bẫy FAIL OAN của cổng 36).
    """
    dst = os.path.join(td, "goc.mp4")
    rc, err, _ = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                       f"testsrc2=s={W}x{H}:r={FPS}:d={DAI}", "-an", "-c:v",
                       "libx264", "-preset", "ultrafast", "-qp", "0",
                       "-pix_fmt", "yuv420p", dst])
    if rc != 0:
        raise RuntimeError("không dựng nổi nguồn: " + err[-300:])
    return dst


def do_mot(khoa: str, src: str, td: str, n_goc: int) -> dict:
    ch = HU.chuoi_filter([{"khoa": khoa, "bat": BAT, "het": HET,
                           "dam": HU.DAM_MAX}], W, H, FPS,
                         HU.font_mac_dinh(""))
    if not ch:
        return {"kq": "BỎ-QUA", "ghi": "chuỗi filter rỗng"}
    dst = os.path.join(td, f"e_{khoa}.mp4")
    # MÃ HOÁ KHÔNG MẤT DỮ LIỆU (`-qp 0`): với crf 18 thì chính phép nén đã làm
    # 0,15% pixel ngoài cửa sổ lệch >12 — không phân biệt nổi với RÒ THẬT.
    rc, err, wall = chay([FF, "-y", "-v", "error", "-i", src, "-an", "-vf", ch,
                          "-c:v", "libx264", "-preset", "ultrafast", "-qp",
                          "0", "-pix_fmt", "yuv420p", dst])
    if rc != 0:
        return {"kq": "FFMPEG-LỖI", "wall": wall,
                "ghi": (err.strip().splitlines() or [""])[-1][:160]}
    n = dem_khung(dst)
    d = do_cap(src, dst, td)
    m = min(len(d["doi"]), len(d["sang0"]), len(d["sang1"]))
    i0, i1 = int(BAT * FPS), int(HET * FPS)
    trong_i = list(range(max(0, i0 + 1), min(m, i1)))
    ngoai_i = [i for i in range(m) if i < i0 - 1 or i > i1 + 1]
    trong = max((d["doi"][i] for i in trong_i), default=-1.0)
    ngoai = max((d["doi"][i] for i in ngoai_i), default=0.0)
    du = max((abs(d["u1"][i] - d["u0"][i]) for i in trong_i
              if i < len(d["u1"]) and i < len(d["u0"])), default=0.0)
    dv = max((abs(d["v1"][i] - d["v0"][i]) for i in trong_i
              if i < len(d["v1"]) and i < len(d["v0"])), default=0.0)
    sat = min((d["s1"][i] / d["s0"][i] for i in trong_i
               if i < len(d["s1"]) and i < len(d["s0"]) and d["s0"][i] > 1),
              default=1.0)
    ty = min((d["sang1"][i] / d["sang0"][i]) for i in trong_i
             if d["sang0"][i] > 5) if trong_i else 1.0
    ty_max = max((d["sang1"][i] / d["sang0"][i]) for i in trong_i
                 if d["sang0"][i] > 5) if trong_i else 1.0
    return {"kq": "ĐẠT" if (n == n_goc and trong >= 8.0 and ngoai <= 0.005
                            and du < HU.UV_MAX and dv < HU.UV_MAX)
            else "XEM-LẠI",
            "khung": n, "trong": round(trong, 2), "ngoai": round(ngoai, 4),
            "du": round(du, 2), "dv": round(dv, 2), "sat": round(sat, 3),
            "wall": round(wall, 2),
            "sang_day": round(ty, 3), "sang_dinh": round(ty_max, 3), "ghi": ""}


def main() -> int:
    xin = [a for a in sys.argv[1:] if not a.startswith("-")]
    td = tempfile.mkdtemp(prefix="_dolp_", dir=str(_SB))
    try:
        src = nguon(td)
        n_goc = dem_khung(src)
        d0 = do_cap(src, src, td)
        print(f"[đối chứng] gốc vs gốc = {max(d0['doi']):.4f}% "
              f"({len(d0['doi'])} khung, sáng TB "
              f"{sum(d0['sang0'])/max(1,len(d0['sang0'])):.1f}/255)")
        ds = [k for k, h in HU.KHO.items() if h.nhom == "lop_phu"]
        keys = [k for k in (xin or ds) if k in HU.KHO]
        print(f"\n{'khoá':<16}{'kết quả':<11}{'%trong':>8}{'%ngoài':>9}"
              f"{'|dU|':>7}{'|dV|':>7}{'sáng đáy':>10}{'sáng đỉnh':>11}"
              f"{'wall(s)':>9}")
        print("-" * 88)
        for k in keys:
            s = do_mot(k, src, td, n_goc)
            print(f"{k:<16}{s.get('kq',''):<11}{s.get('trong',-1):>8.2f}"
                  f"{s.get('ngoai',-1):>9.4f}{s.get('du',-1):>6.2f}"
                  f"{s.get('dv',-1):>6.2f}{s.get('sat',-1):>9}"
                  f"{s.get('sang_day',-1):>10}"
                  f"{s.get('sang_dinh',-1):>11}{s.get('wall',-1):>9}"
                  f"  {s.get('ghi','')}")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
