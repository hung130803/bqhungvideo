"""ẢNH TRƯỚC/SAU cho anh Hùng TỰ NHÌN — cùng NGUỒN, cùng hệ số, cùng giây.

TRƯỚC = chính file app đã xuất cho anh Hùng (`Downloads\\longtieng\\xuất`), tức
bản MANG LỖI, không dựng lại.
SAU   = chạy lại ĐÚNG hàm `thay_audio_video` của bản đã vá trên CÙNG video gốc
với CÙNG hệ số giãn `k` (đọc từ tỉ lệ độ dài của chính file TRƯỚC), tiếng thay
bằng một dải im lặng dài `k*dur` — phần tiếng không ảnh hưởng gì tới chuỗi filter
che chữ.

Nhờ CÙNG `k`, giây T của hai file trỏ vào CÙNG nội dung nguồn (`T/k`), nên hai
ảnh so được với nhau. Kèm ảnh PHÓNG 2x dải chữ: bài học cổng 68 — **đếm điểm ảnh
KHÔNG phát hiện được chữ còn đọc được hay không, phải mở ảnh ra xem**.

CHỈ ĐỌC `Downloads\\longtieng`. Ghi ra `_kq_che_cuoi/`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

KHO = Path(r"C:\Users\Admin\Downloads\longtieng")
XUAT = KHO / "xuất"
RA = Path(__file__).resolve().parent / "_kq_che_cuoi"
#: Mốc % độ dài BẢN XUẤT để trích ảnh — đều nằm trong vùng từng hỏng.
MOC = (0.86, 0.94, 0.99)


def _ff(args: list, ten: str) -> None:
    from config import settings
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-v", "error", *args],
                       capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"{ten}: {r.stderr.decode('utf-8','replace')[:300]}")


def _zoom(src: Path, t: float, dst: Path, y0: int, y1: int) -> None:
    """Cắt DẢI CHỮ rồi phóng 2x — để mắt đọc được, không phải để đếm pixel."""
    h = max(2, (y1 - y0) // 2 * 2)
    _ff(["-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-vf",
         f"crop=iw:{h}:0:{y0},scale=iw*2:ih*2:flags=lanczos", str(dst)],
        f"zoom {dst.name}")


def main() -> int:
    from app.core import che_chu as CC
    from app.core import thay_giong as TG
    RA.mkdir(exist_ok=True)
    goc = min((p for p in KHO.glob("*.mp4") if p.is_file()),
              key=lambda p: CC.thong_tin(p)["do_dai"] or 9e9)
    truoc = XUAT / goc.name
    if not truoc.is_file():
        print("KHÔNG có bản xuất tương ứng"); return 2
    dg = float(CC.thong_tin(goc)["do_dai"] or 0)
    dt = float(CC.thong_tin(truoc)["do_dai"] or 0)
    k = dt / max(1e-9, dg)
    d = CC.dai_theo_video(goc)
    print(f"nguồn {goc.name[:50]}")
    print(f"  gốc {dg:.3f}s · TRƯỚC (app đã xuất) {dt:.3f}s · k = {k:.4f}")
    print(f"  dải chữ y={d.y0}..{d.y1}")

    im = RA / "anh_im.m4a"
    if not im.is_file():
        _ff(["-f", "lavfi", "-t", f"{dg*k:.3f}", "-i",
             "anullsrc=r=44100:cl=stereo", "-c:a", "aac", "-b:a", "96k",
             str(im)], "sinh tiếng im")
    sau = RA / "SAU_davá.mp4"
    if not sau.is_file():
        print("  đang xuất lại bằng mã ĐÃ VÁ...")
        TG.thay_audio_video(goc, im, sau, che_chu=True, che_chu_muc=1.0,
                            he_so_hinh=k)
    ds = float(CC.thong_tin(sau)["do_dai"] or 0)
    print(f"  SAU {ds:.3f}s (lệch {ds-dt:+.3f}s so với TRƯỚC)")

    xa, xb = (d.x0_dai or d.x0), (d.x1_dai or d.x1)
    print(f"\n  {'mốc':>5} {'T':>9} {'nội dung gốc':>13} {'TRƯỚC':>8} "
          f"{'SAU':>8}")
    for r in MOC:
        T = round(min(dt, ds) * r, 3)
        m_t = CC.mat_do_vung(truoc, d.y0, d.y1, [T], x0=xa, x1=xb)
        m_s = CC.mat_do_vung(sau, d.y0, d.y1, [T], x0=xa, x1=xb)
        print(f"  {int(r*100):4d}% {T:9.3f} {T/k:13.3f} {m_t:8.4f} {m_s:8.4f}")
        for ten, f in (("TRUOC", truoc), ("SAU", sau)):
            CC.trich_khung(f, T, RA / f"ANH_{ten}_{int(r*100)}.png")
            _zoom(f, T, RA / f"ANH_{ten}_{int(r*100)}_ZOOM.png",
                  max(0, d.y0 - 8), min(int(d.cao), d.y1 + 8))
    print(f"\n-> ảnh trong {RA} (ANH_TRUOC_*.png / ANH_SAU_*.png + _ZOOM)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
