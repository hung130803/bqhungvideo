"""XUẤT VIDEO THẬT qua ĐÚNG chuỗi filter của đường THAY GIỌNG, rồi trích PNG.

Không kết luận bằng mã thoát ffmpeg: in KÍCH THƯỚC + ĐỘ DÀI đầu ra, đếm điểm
ảnh chữ, và để lại PNG cho người TỰ MỞ RA NHÌN (ô vuông tofu thì đếm điểm ảnh
KHÔNG bắt được — đo 14/08: tofu 2.431 px vs chữ thật 517 px, ngược 4,7 lần).

Chạy:  .venv\\Scripts\\python -u _do_kieu_chu_nhin.py
"""
from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

FFMPEG = REPO / "bin" / "ffmpeg.exe"
FFPROBE = REPO / "bin" / "ffprobe.exe"
NGUON_GOC = Path(r"C:\Users\Admin\Downloads\longtieng") / "4月新片海外电影片单.mp4"
HOP = REPO / "_kc"
#: câu thử: tiếng Việt CÓ DẤU (dấu là chỗ phông thiếu glyph hay lộ ra nhất)
CAU = "Chào các bạn, đây là chữ mới thay giọng"


def _don_hop_cu() -> None:
    """Quét hộp cát của lần chạy TRƯỚC (app thoát bằng os._exit nên `finally`
    không phải lúc nào cũng chạy)."""
    for d in REPO.glob("_kc_cu_*"):
        shutil.rmtree(d, ignore_errors=True)


def chay(cmd: list, ten: str, timeout: int = 300) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True,
                       timeout=timeout)
    if r.returncode != 0:
        loi = r.stderr.decode("utf-8", "replace")
        print(f"  ffmpeg LỖI ({ten}) mã {r.returncode}:")
        print("   " + "\n   ".join(loi.strip().splitlines()[:6]))
    return r


def do_dai(p: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, timeout=60)
    try:
        return float(r.stdout.decode().strip())
    except ValueError:
        return 0.0


def dem_diem_chu(png: Path, y0: int, y1: int) -> int:
    """Đếm điểm ảnh SÁNG (chữ) trong dải y0..y1 của khung."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, h = im.size
    y0 = max(0, min(h, y0)); y1 = max(0, min(h, y1))
    px = im.load()
    return sum(1 for y in range(y0, y1) for x in range(w) if px[x, y] > 200)


def xuat(hop: Path, ten: str, kieu: dict | None, dong: list,
         giay: float = 6.0) -> dict:
    """Dựng .ass bằng ĐÚNG `che_chu.ghi_ass` rồi đốt vào video bằng ĐÚNG chuỗi
    filter mà `thay_giong.thay_audio_video` dùng (che xong nối `,subtitles=`)."""
    from app.core import che_chu as CC
    src = hop / "nguon.mp4"
    loc, dai, ly = CC.loc_cho_xuat(str(src), cach="mo", muc=1.0,
                                   segs=[(0.0, giay)])
    if not loc or dai is None or not dai.co_chu:
        return {"ten": ten, "loi": f"không dò ra dải chữ ({ly})"}
    ass = hop / f"{ten}.ass"
    if not CC.ghi_ass(dong, ass, dai, kieu=kieu):
        return {"ten": ten, "loi": "ghi_ass trả False"}
    ra = hop / f"{ten}.mp4"
    # `chuoi_subtitles` = LUÔN kèm fontsdir; thiếu nó thì ô chọn phông im lặng
    # không làm gì (xem ghi chú của chính hàm đó).
    vf = f"{loc},{CC.chuoi_subtitles(ass)}"
    r = chay([FFMPEG, "-y", "-v", "error", "-t", giay, "-i", src,
              "-vf", vf, "-an", "-c:v", "libx264", "-crf", "18",
              "-pix_fmt", "yuv420p", str(ra)], ten)
    if r.returncode != 0 or not ra.exists():
        return {"ten": ten, "loi": f"ffmpeg mã {r.returncode}"}
    co = ra.stat().st_size
    dai_s = do_dai(ra)
    png = hop / f"{ten}.png"
    chay([FFMPEG, "-y", "-v", "error", "-ss", 2.0, "-i", ra,
          "-frames:v", 1, str(png)], f"{ten}-png")
    # cắt riêng DẢI CHỮ, phóng to 2x cho dễ nhìn bằng mắt
    zoom = hop / f"ZOOM_{ten}.png"
    if png.exists():
        chay([FFMPEG, "-y", "-v", "error", "-i", png, "-vf",
              f"crop={dai.rong}:{max(1, dai.y1 - dai.y0) + 120}:0:"
              f"{max(0, dai.y0 - 60)},scale=iw*2:ih*2", str(zoom)],
             f"{ten}-zoom")
    return {"ten": ten, "co": co, "dai_s": dai_s, "png": png, "zoom": zoom,
            "y0": dai.y0, "y1": dai.y1, "ass": ass,
            "px": dem_diem_chu(png, dai.y0 - 40, dai.y1 + 40) if png.exists() else -1}


def main() -> int:
    _don_hop_cu()
    if not NGUON_GOC.exists():
        print(f"KHÔNG thấy video nguồn: {NGUON_GOC}")
        return 2
    HOP.mkdir(exist_ok=True)
    atexit.register(lambda: None)   # hộp giữ lại để NGƯỜI xem ảnh
    src = HOP / "nguon.mp4"
    if not src.exists():
        # COPY ra chỗ khác — TUYỆT ĐỐI không đụng bản gốc của anh Hùng
        shutil.copy2(NGUON_GOC, src)
    dong = [(0.6, 5.6, CAU)]

    bo = [
        ("00_mocgoc", None),
        ("01_nho", {"preset": "Trắng viền đen", "co_chu": 0.045}),
        ("02_to", {"preset": "Trắng viền đen", "co_chu": 0.110}),
        ("03_dam", {"preset": "Trắng viền đen", "co_chu": 0.075, "dam": True}),
        ("04_nghieng", {"preset": "Trắng viền đen", "co_chu": 0.075,
                        "dam": False, "nghieng": True}),
        ("05_vien_mong", {"preset": "Trắng viền đen", "co_chu": 0.075,
                          "do_vien": 0.02}),
        ("06_vien_day", {"preset": "Trắng viền đen", "co_chu": 0.075,
                         "do_vien": 0.22}),
        ("07_mau_vang_vien_do", {"preset": "Trắng viền đen", "co_chu": 0.075,
                                 "mau": "#FFD83D", "vien": "#C00000",
                                 "do_vien": 0.10}),
        ("08_hop_den", {"preset": "Nền hộp đen", "co_chu": 0.070}),
        ("09_vi_tri_tren", {"preset": "Trắng viền đen", "co_chu": 0.065,
                            "vi_tri": "tren"}),
        ("10_phong_anton", {"preset": "Trắng viền đen", "co_chu": 0.075,
                            "font": "Anton"}),
        ("11_phong_bevn", {"preset": "Trắng viền đen", "co_chu": 0.075,
                           "font": "Be Vietnam Pro"}),
    ]
    print(f"NGUỒN: {src.name} · câu thử: «{CAU}»\n")
    print(f"{'bộ':<22}{'KB':>8}{'giây':>8}{'px chữ':>9}  ảnh")
    kq = []
    for ten, kieu in bo:
        r = xuat(HOP, ten, kieu, dong)
        kq.append(r)
        if r.get("loi"):
            print(f"{ten:<22}  LỖI: {r['loi']}")
            continue
        print(f"{ten:<22}{r['co']//1024:>8}{r['dai_s']:>8.2f}{r['px']:>9}"
              f"  {r['zoom'].name}")
    xau = [r for r in kq if r.get("loi") or r.get("co", 0) < 10000
           or r.get("dai_s", 0) < 1.0]
    print(f"\nXUẤT ĐƯỢC: {len(kq) - len(xau)}/{len(kq)}")
    print(f"ẢNH nằm ở: {HOP}  (MỞ RA NHÌN, đừng tin mỗi con số)")
    return 1 if xau else 0


if __name__ == "__main__":
    sys.exit(main())
