# -*- coding: utf-8 -*-
"""ĐO đường XUẤT có che chữ cháy — 3 câu hỏi, mỗi câu một số.

 1. "RÒ RA NGOÀI DẢI" đo trên FILE XUẤT là RÒ THẬT hay là NHIỄU CỦA MÃ HOÁ MẤT
    DỮ LIỆU? (bài học cổng 46: `-crf 18` TỰ NÓ làm 0,157% điểm ảnh ngoài cửa sổ
    lệch >12 — không phân biệt nổi với rò thật; `-qp 0` mới ra 0,0000%).
 2. Chi phí THÊM mỗi phút phim khi GỘP vào lượt mã hoá sẵn có (đan xen, trung
    vị — đo liền mạch đã ra kết luận sai 2 lần ở repo này).
 3. Chi phí DÒ dải (một lần cho cả video, 3 Part dùng chung).

Chạy: .venv\\Scripts\\python _do_che_chu_xuat.py [so_lan]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_DATA_DIR", r"D:\claude\_do_che_chu\_sandbox")
os.environ.setdefault("BQ_DB_PATH", r"D:\claude\_do_che_chu\_sandbox\studio.db")

import _test_guard  # noqa: E402,F401  chặn cửa sổ ngoài
from app.core import che_chu as C                 # noqa: E402
from app.core import ffmpeg_utils as FU           # noqa: E402

SAN = Path(r"D:\claude\_do_che_chu\_do")
SAN.mkdir(parents=True, exist_ok=True)
SRC = Path(r"D:\claude\_do_che_chu\nguon\zh_ep12.mp4")
RECT = (0.5, 0.5, 1.0)
OW, OH = 1080, 1920
_NOWIN = C._CREATE_NO_WINDOW


def xuat(dst: Path, segs: list, che: bool) -> float:
    t = time.perf_counter()
    FU.export_canvas_clip(str(SRC), str(dst), segs, RECT, bg="blur",
                          out_w=OW, out_h=OH, fx_fade=False, fx_whoosh=False,
                          hieu_ung="tat", chuyen_canh="tat", che_chu=che,
                          che_chu_cach="mo", che_chu_muc=1.0)
    return time.perf_counter() - t


def dai_ra(d) -> tuple:
    cx, cy, sw = RECT
    vw = max(2, int(round(sw * OW)) // 2 * 2)
    vh = int(round(vw * d.cao / d.rong))
    vh += vh % 2
    yt = cy * OH - vh / 2.0
    return int(yt + d.y0 * vh / d.cao), int(yt + d.y1 * vh / d.cao) + 1


def psnr_ngoai(a: Path, b: Path, y0: int, y1: int, le: int) -> float:
    """PSNR phần NGOÀI [y0-le, y1+le]. `le` = lề bỏ qua quanh dải."""
    yy = max(0, y0 - le)
    hh = min(OH, y1 + le) - yy
    vf = (f"[0:v]drawbox=x=0:y={yy}:w=iw:h={hh}:color=black@1:t=fill[a];"
          f"[1:v]drawbox=x=0:y={yy}:w=iw:h={hh}:color=black@1:t=fill[b];"
          "[a][b]psnr")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(a),
                        "-i", str(b), "-filter_complex", vf,
                        "-f", "null", "-"], capture_output=True,
                       creationflags=_NOWIN)
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            v = ln.split("average:")[1].split()[0]
            return float("inf") if v == "inf" else float(v)
    return -1.0


def ti_le_doi(a: Path, b: Path, y0: int, y1: int, le: int) -> float:
    """% điểm ảnh NGOÀI dải(+lề) lệch |dY| > 12 — thước của cổng 43/46."""
    yy = max(0, y0 - le)
    hh = min(OH, y1 + le) - yy
    vf = (f"[0:v]drawbox=x=0:y={yy}:w=iw:h={hh}:color=black@1:t=fill[a];"
          f"[1:v]drawbox=x=0:y={yy}:w=iw:h={hh}:color=black@1:t=fill[b];"
          "[a][b]blend=all_mode=difference,"
          "lutyuv=y='if(gt(val,12),255,0)':u=128:v=128,signalstats,"
          "metadata=print:key=lavfi.signalstats.YAVG:file=-")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-v", "info",
                        "-i", str(a), "-i", str(b), "-filter_complex", vf,
                        "-f", "null", "-"], capture_output=True,
                       creationflags=_NOWIN)
    vs = []
    for ln in (r.stdout or b"").decode("utf-8", "replace").splitlines():
        if "YAVG=" in ln:
            try:
                vs.append(float(ln.split("YAVG=")[1]))
            except ValueError:
                pass
    return (sum(vs) / len(vs) / 255.0 * 100.0) if vs else -1.0


def main() -> int:
    lan = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    if not SRC.exists():
        print("KHÔNG có nguồn", SRC)
        return 1
    print(f"nguồn: {SRC.name} · {C.thong_tin(SRC)['rong']}x"
          f"{C.thong_tin(SRC)['cao']}")

    # ---- 3. CHI PHÍ DÒ (một lần / video) ----
    C._DAI_NHO.clear()
    t = time.perf_counter()
    d = C.dai_theo_video(SRC)
    t_do = time.perf_counter() - t
    t = time.perf_counter()
    C.dai_theo_video(SRC)
    t_nho = time.perf_counter() - t
    print(f"\n[3] DÒ DẢI: lần đầu {t_do:.2f}s · lần sau (đã nhớ) {t_nho*1000:.2f} ms"
          f" -> 3 Part một video tốn {t_do:.2f}s CHỨ KHÔNG PHẢI {t_do*3:.2f}s")
    print(f"    dải: {d.ly_do}")
    if not d.co_chu:
        return 1
    y0, y1 = dai_ra(d)
    print(f"    dải trên FILE XUẤT 1080x1920: y={y0}..{y1}")

    # ---- 1. RÒ THẬT hay NHIỄU MÃ HOÁ? ----
    print("\n[1] RÒ RA NGOÀI DẢI — tách 'rò thật' khỏi 'nhiễu mã hoá'")
    segs = [(30.0, 40.0)]
    a, b, c2 = SAN / "r_tat.mp4", SAN / "r_bat.mp4", SAN / "r_tat2.mp4"
    xuat(a, segs, False)
    xuat(b, segs, True)
    xuat(c2, segs, False)
    print(f"    ĐỐI CHỨNG (TẮT vs TẮT, 2 lượt riêng): PSNR toàn khung = "
          f"{psnr_ngoai(a, c2, 0, 0, 0)} dB  <- libx264 TIỀN ĐỊNH hay không")
    for le in (0, 2, 4, 8, 16, 32):
        p = psnr_ngoai(a, b, y0, y1, le)
        t_ = ti_le_doi(a, b, y0, y1, le)
        print(f"    lề {le:3d} px -> PSNR ngoài dải {p:8.2f} dB · "
              f"{t_:.4f}% điểm ảnh lệch >12")
    # LOSSLESS: che TRÊN NGUỒN, không qua khung/scale -> phân biệt được nguyên
    # nhân. Rò của CHÍNH filter thì đây phải ra inf.
    f = C.loc_che(d, cach="mo", do_manh=1.0)
    l1, l2 = SAN / "ll_goc.mkv", SAN / "ll_che.mkv"
    for dst, vf in ((l1, None), (l2, f)):
        cmd = [C._bin("ffmpeg"), "-y", "-v", "error", "-ss", "30", "-t", "3",
               "-i", str(SRC)]
        if vf:
            cmd += ["-filter_complex", vf]
        cmd += ["-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p",
                "-an", str(dst)]
        subprocess.run(cmd, capture_output=True, creationflags=_NOWIN)
    vf = (f"[0:v]drawbox=x=0:y={d.y0}:w=iw:h={d.cao_dai}:color=black@1:t=fill[a];"
          f"[1:v]drawbox=x=0:y={d.y0}:w=iw:h={d.cao_dai}:color=black@1:t=fill[b];"
          "[a][b]psnr")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(l1),
                        "-i", str(l2), "-filter_complex", vf, "-f", "null",
                        "-"], capture_output=True, creationflags=_NOWIN)
    ps = "?"
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            ps = ln.split("average:")[1].split()[0]
    print(f"    LOSSLESS (-qp 0) che THẲNG trên nguồn, PSNR ngoài dải = {ps}"
          "  <- rò của CHÍNH filter")

    # ---- 2. CHI PHÍ THÊM / PHÚT PHIM (ĐAN XEN + TRUNG VỊ) ----
    print(f"\n[2] CHI PHÍ THÊM — clip 60s, {lan} vòng ĐAN XEN, lấy TRUNG VỊ")
    segs60 = [(30.0, 90.0)]
    tat, bat = [], []
    for i in range(lan):
        tat.append(xuat(SAN / f"p_tat{i}.mp4", segs60, False))
        bat.append(xuat(SAN / f"p_bat{i}.mp4", segs60, True))
        print(f"    vòng {i+1}: TẮT {tat[-1]:6.2f}s · BẬT {bat[-1]:6.2f}s "
              f"({bat[-1]-tat[-1]:+.2f}s)")
    tv = sorted(tat)[lan // 2], sorted(bat)[lan // 2]
    print(f"    TRUNG VỊ: TẮT {tv[0]:.2f}s · BẬT {tv[1]:.2f}s -> "
          f"**{tv[1]-tv[0]:+.2f} giây/phút phim**")
    print(f"\ncửa sổ ngoài bị chặn: {len(_test_guard.DA_CHAN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
