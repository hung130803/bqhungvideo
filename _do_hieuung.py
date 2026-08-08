# -*- coding: utf-8 -*-
"""ĐO HIỆU ỨNG BẰNG SỐ TRÊN KHUNG HÌNH — không đọc lệnh, không đoán.

Chạy: .venv\\Scripts\\python.exe _do_hieuung.py [khoá ...]

Với MỖI kiểu trong `hieu_ung.KHO`: áp vào ĐÚNG 1 cửa sổ trên clip THẬT rồi đo
**Ở ĐỘ PHÂN GIẢI GỐC 1080x1920** bằng chính ffmpeg (không thu nhỏ — thu nhỏ
làm TRUNG BÌNH mất hạt nhiễu/độ nét, đo ra 0% và kết luận SAI "không chạy"):

  sáng[i]   = signalstats.YAVG từng khung bản CÓ hiệu ứng
  sáng0[i]  = như trên, bản GỐC
  doi[i]    = % pixel |dY| > 12 (blend=difference -> lutyuv nhị phân -> YAVG/2,55)

  KHUNG ĐEN     : sáng[i] < 5% sáng[i-1]  HOẶC  < 5% sáng0[i]      -> LỖI
  TỐI SÂU       : sáng[i] < 35% sáng0[i] (nhìn ra "tối đen")        -> LỖI
  KHÔNG CHẠY    : max doi[] trong cửa sổ < 3%
  RÒ RA NGOÀI   : max doi[] ngoài cửa sổ > 1%
  LỆCH KHUNG    : số khung ra != số khung vào

LUẬT SỐ 1: 1 ffmpeg tại một thời điểm — script chạy TUẦN TỰ.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
FF = str(ROOT / "bin" / "ffmpeg.exe")
FP = str(ROOT / "bin" / "ffprobe.exe")
NOWIN = 0x08000000 if os.name == "nt" else 0

W, H, FPS = 1080, 1920, 30
DAI = 6.0                 # clip nguồn NGẮN (luật số 1)
BAT, HET = 2.00, 2.60     # cửa sổ hiệu ứng dùng chung để so được với nhau

NG_DEN = 0.05             # < 5% khung trước/khung gốc = ĐEN
NG_TOI = 0.35             # < 35% khung gốc = TỐI SÂU (mắt thấy "tối đen")
NG_CHAY = 3.0             # % pixel đổi tối thiểu để coi là CÓ hoạt động
NG_RO = 1.0               # % pixel đổi tối đa NGOÀI cửa sổ


def chay(cmd: list, giay: int = 300) -> tuple[int, str]:
    r = subprocess.run([str(x) for x in cmd], capture_output=True,
                       creationflags=NOWIN, timeout=giay)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", p], capture_output=True,
                       creationflags=NOWIN, timeout=180)
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
            m = re.search(r"=\s*([-\d.]+)\s*$", ln.strip())
            if m and "YAVG" in ln:
                try:
                    out.append(float(m.group(1)))
                except ValueError:
                    pass
    return out


def do_cap(goc: str, sau: str, td: str) -> tuple[list, list, list]:
    """1 lệnh ffmpeg -> (sáng0[], sáng[], %pixel_đổi[]) TỪNG KHUNG, FULL RES."""
    f0 = os.path.join(td, "_l0.txt")
    f1 = os.path.join(td, "_l1.txt")
    fd = os.path.join(td, "_dd.txt")
    for f in (f0, f1, fd):
        try:
            os.remove(f)
        except OSError:
            pass
    # BẪY ĐÃ SẬP 1 LẦN — ĐỪNG DÙNG `format=gray` Ở ĐÂY: gray là dải ĐẦY (0..255)
    # còn yuv420p là dải HẸP (16..235), nên ffmpeg tự chèn scale và mức 0 (hai
    # khung GIỐNG HỆT nhau) biến thành **16** -> `gt(val,12)` đúng -> mọi kiểu
    # đo ra **100% pixel đổi**, kể cả khi so file với CHÍNH NÓ. Giữ yuv420p suốt
    # chuỗi thì so file với chính nó ra ĐÚNG 0,00%.
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
                    "-filter_complex", g, "-map", "[d]", "-f", "null", "-"],
                   420)
    if rc != 0:
        raise RuntimeError("lệnh đo hỏng: " + err[-400:])
    return (_doc(f0), _doc(f1), [v / 2.55 for v in _doc(fd)])


def nguon(td: str) -> str:
    """Cắt 6 giây SÁNG + CÓ CHUYỂN ĐỘNG từ video THẬT trên máy anh Hùng."""
    kho = Path("D:/video test/Đã tải")
    cand = []
    if kho.is_dir():
        cand = sorted((p for p in kho.iterdir()
                       if p.suffix.lower() in (".mp4", ".mkv", ".webm")),
                      key=lambda p: p.stat().st_size)
    dst = os.path.join(td, "goc.mp4")
    for p in cand[:6]:
        for ss in (240, 120, 60):
            rc, _ = chay([FF, "-y", "-v", "error", "-ss", str(ss), "-t",
                          str(DAI), "-i", str(p), "-an",
                          "-vf", f"scale={W}:{H}:force_original_aspect_ratio="
                                 f"increase,crop={W}:{H},fps={FPS},"
                                 f"setsar=1,format=yuv420p",
                          "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "18", "-g", "30", dst], 300)
            if rc != 0 or not os.path.exists(dst):
                continue
            s0, _, _ = do_cap(dst, dst, td)
            if len(s0) < int(DAI * FPS) - 3 or not s0:
                continue
            if min(s0) > 45:
                print(f"[nguồn] {p.name[:52]} @ {ss}s · sáng TB "
                      f"{sum(s0)/len(s0):.1f}/255 · min {min(s0):.1f}")
                return dst
    rc, err = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"testsrc2=s={W}x{H}:r={FPS}:d={DAI}", "-an",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    dst], 300)
    if rc != 0:
        raise RuntimeError("không dựng nổi nguồn: " + err[-400:])
    print("[nguồn] lavfi testsrc2 (không thấy video thật)")
    return dst


def do_mot(HU, k: str, src: str, td: str, n_goc: int, font: str,
           dam: float | None = None) -> dict:
    """Đo 1 kiểu. Trả dict số đo + kết luận."""
    dam = HU.DAM_MAX if dam is None else dam
    ch = HU.chuoi_filter([{"khoa": k, "bat": BAT, "het": HET, "dam": dam}],
                         W, H, FPS, font)
    if not ch:
        return {"kq": "BỎ-QUA", "ghi": "chuỗi filter rỗng"}
    dst = os.path.join(td, f"e_{k}.mp4")
    cmd = [FF, "-y", "-v", "error"]
    if HU.can_vulkan([{"khoa": k}]):
        cmd += ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk"]
    cmd += ["-i", src, "-an", "-vf", ch, "-c:v", "libx264", "-preset",
            "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst]
    rc, err = chay(cmd, 420)
    if rc != 0:
        return {"kq": "FFMPEG-LỖI",
                "ghi": (err.strip().splitlines() or [""])[-1][:110]}
    n = dem_khung(dst)
    s0, s1, dd = do_cap(src, dst, td)
    if not s1:
        return {"kq": "0-KHUNG", "ghi": f"nb={n}"}
    m = min(len(s0), len(s1), len(dd))
    i_bat, i_het = int(BAT * FPS), int(HET * FPS)
    den, toi = [], []
    for i in range(m):
        tr = s1[i - 1] if i else 0.0
        if (tr > 5 and s1[i] < NG_DEN * tr) or \
           (s0[i] > 5 and s1[i] < NG_DEN * s0[i]):
            den.append(i)
        elif s0[i] > 5 and s1[i] < NG_TOI * s0[i]:
            toi.append(i)
    trong_i = [i for i in range(max(0, i_bat + 1), min(m, i_het))]
    ngoai_i = [i for i in range(m)
               if i < i_bat - 1 or i > i_het + 1]
    trong = max((dd[i] for i in trong_i), default=-1.0)
    ngoai = max((dd[i] for i in ngoai_i), default=0.0)
    so = {"khung": n, "trong": round(trong, 2), "ngoai": round(ngoai, 2),
          "den": len(den), "toi": len(toi), "den_i": den[:6], "toi_i": toi[:6],
          "sang_min": round(min(s1[i] for i in trong_i), 1) if trong_i else -1,
          "sang0_min": round(min(s0[i] for i in trong_i), 1) if trong_i else -1}
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
    so["ghi"] = ""
    return so


def main() -> int:
    from app.core import hieu_ung as HU
    HU.dat_frei0r_path()
    chi = [x for x in sys.argv[1:] if not x.startswith("-")]
    td = tempfile.mkdtemp(prefix="_dohu_")
    try:
        src = nguon(td)
        n_goc = dem_khung(src)
        print(f"[gốc] {n_goc} khung {W}x{H}@{FPS}\n")
        font = HU.font_mac_dinh("")
        bang = []
        for k, h in HU.KHO.items():
            if chi and k not in chi:
                continue
            so = do_mot(HU, k, src, td, n_goc, font)
            bang.append((k, h.ten, h.nhom, so))
            print(f"  {k:<16}{so['kq']:<12} trong {so.get('trong',-1):6.2f}% · "
                  f"ngoài {so.get('ngoai',-1):5.2f}% · đen {so.get('den',0)} · "
                  f"tối {so.get('toi',0)} · sáng {so.get('sang_min',-1)}/"
                  f"{so.get('sang0_min',-1)} {so.get('ghi','')}")
        print("\n" + "=" * 104)
        print(f"{'khoá':<16}{'tên':<26}{'nhóm':<8}{'kết quả':<13}"
              f"{'%trong':>8}{'%ngoài':>8}{'đen':>5}{'tối':>5}{'sáng':>7}")
        print("-" * 104)
        for k, ten, nhom, so in bang:
            print(f"{k:<16}{ten[:25]:<26}{nhom:<8}{so['kq']:<13}"
                  f"{so.get('trong', -1):>8.2f}{so.get('ngoai', -1):>8.2f}"
                  f"{so.get('den', -1):>5}{so.get('toi', -1):>5}"
                  f"{so.get('sang_min', -1):>7}  {so.get('ghi','')}")
        xau = [b for b in bang if b[3]["kq"] != "ĐẠT"]
        print(f"\nTổng {len(bang)} kiểu · ĐẠT {len(bang)-len(xau)} · "
              f"CÓ VẤN ĐỀ {len(xau)}")
        for k, ten, _n, so in xau:
            print(f"   - {k} ({ten}): {so['kq']} {so.get('ghi','')} "
                  f"đen@{so.get('den_i')} tối@{so.get('toi_i')}")
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
