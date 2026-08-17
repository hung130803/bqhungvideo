"""ĐO END-TO-END: chạy CẢ dây chuyền thay giọng THẬT với đơn thuốc KIỂU CHỮ.

Đi qua `thay_giong.thay_giong_mot_video` — đúng hàm mà `jobs._thay_giong` gọi,
với thành phần THẬT (Demucs · Groq · edge-tts · ffmpeg). Không dựng dữ liệu
giả: bài học "101 test xanh mà tính năng không chạy".

CỐ Ý KHÔNG LÀM CỔNG: lượt này cần mạng + Groq + Demucs, chạy hàng phút và
NHẤP NHÁY theo dịch vụ ngoài (đúng bệnh cổng 55 CA6b). Cổng 68 lo phần tiền
định; script này để CHỨNG MINH BẰNG MẮT một lần.

Chạy:  .venv\\Scripts\\python -u _do_tg_e2e_kieuchu.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

FF = REPO / "bin" / "ffmpeg.exe"
FFPROBE = REPO / "bin" / "ffprobe.exe"
#: KHÔNG ghi cứng tên file: kho `longtieng` đổi theo ngày, ghi cứng là script
#: chết vì KHO ĐĨA chứ không vì mã (tên cũ `4月新片海外电影片单.mp4` nay đã
#: không còn). Lấy file mp4 đầu theo thứ tự tên -> vẫn tiền định trong 1 kho.
_KHO = Path(r"C:\Users\Admin\Downloads\longtieng")
_DS = sorted(_KHO.glob("*.mp4")) if _KHO.is_dir() else []
NGUON = _DS[0] if _DS else _KHO / "(khong-co-video-nao).mp4"
HOP = REPO / "_e2e_kc"
GIAY = float(os.environ.get("BQ_E2E_GIAY", "45"))

#: 2 bộ tham số KHÁC HẲN NHAU để nhìn ra ngay bằng mắt.
BO = [
    ("A_nho_trang", {"preset": "Trắng viền đen", "co_chu": 0.045,
                     "font": "Be Vietnam Pro", "do_vien": 0.06}),
    ("B_to_vang_dam_nghieng", {"preset": "Trắng viền đen", "co_chu": 0.085,
                               "font": "Anton", "dam": True, "nghieng": True,
                               "mau": "#FFD83D", "vien": "#C00000",
                               "do_vien": 0.18}),
]


def dai_giay(p: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, timeout=60)
    try:
        return float(r.stdout.decode().strip())
    except ValueError:
        return 0.0


def main() -> int:
    from app.core import thay_giong as TG
    if not NGUON.exists():
        print(f"KHÔNG thấy nguồn: {NGUON}")
        return 2
    if not TG.co_demucs():
        print("Máy chưa có Demucs -> không chạy được đường thật.")
        return 2
    HOP.mkdir(exist_ok=True)
    # CẮT NGẮN ra hộp cát — COPY, tuyệt đối không đụng bản gốc của anh Hùng
    ngan = HOP / "nguon_ngan.mp4"
    if not ngan.exists():
        subprocess.run([str(FF), "-y", "-v", "error", "-t", str(GIAY),
                        "-i", str(NGUON), "-c", "copy", str(ngan)],
                       capture_output=True, timeout=300)
    print(f"NGUỒN cắt {dai_giay(ngan):.2f}s · Demucs OK · bắt đầu\n")

    for ten, kieu in BO:
        thu_ra = HOP / ten
        thu_ra.mkdir(exist_ok=True)
        vin = thu_ra / "vao.mp4"
        shutil.copy2(ngan, vin)
        t0 = time.time()
        try:
            r = TG.thay_giong_mot_video(
                vin, dich_sang="vi", voice="", cach_tach="auto",
                thay_goc=False, kenh="", thung_rac="",
                thu_muc_lam=str(thu_ra / "lam"),
                che_chu=True, che_chu_cach="mo", che_chu_muc=1.0,
                viet_chu=True, kieu_chu=kieu,
            )
        except TypeError as e:
            print(f"{ten}: CHƯA NỐI được kieu_chu ({e})")
            return 3
        except Exception as e:                              # noqa: BLE001
            print(f"{ten}: LỖI {type(e).__name__}: {str(e)[:200]}")
            continue
        gio = time.time() - t0
        if not r.get("ok"):
            print(f"{ten}: KHÔNG ok — {str(r.get('loi'))[:160]}")
            continue
        ra = Path(r["ra"])
        cc = r.get("che_chu") or {}
        ctg = r.get("chu_theo_giong") or {}
        print(f"{ten}: {gio:.0f}s · {ra.stat().st_size//1024} KB · "
              f"{dai_giay(ra):.2f}s · che={cc.get('che')} "
              f"· dòng chữ={cc.get('so_dong_chu')} (dựng {ctg.get('so_dong')})")
        # trích 3 khung ở 3 mốc để NGƯỜI nhìn
        for i, gio_khung in (1, GIAY * 0.25), (2, GIAY * 0.5), (3, GIAY * 0.75):
            png = HOP / f"{ten}_{i}.png"
            subprocess.run([str(FF), "-y", "-v", "error", "-ss",
                            f"{gio_khung:.2f}", "-i", str(ra), "-frames:v", "1",
                            str(png)], capture_output=True, timeout=120)
    print(f"\nẢNH ở {HOP} — MỞ RA NHÌN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
