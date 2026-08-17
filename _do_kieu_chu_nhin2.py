# -*- coding: utf-8 -*-
"""NHÌN THẤY KIỂU CHỮ: chạy `thay_audio_video` THẬT rồi trích khung ra PNG.

Đi qua ĐÚNG cửa mà job thay giọng đi (`thay_giong.thay_audio_video` ->
`che_chu.loc_cho_xuat` + `che_chu.ghi_ass(kieu=...)` + `chuoi_subtitles`),
với ffmpeg + libass THẬT trên video Douyin THẬT có chữ cháy sẵn.

CỐ Ý KHÔNG gọi Demucs/Groq/edge-tts: phần đang cần nhìn là CHỮ, mà chữ chỉ
phụ thuộc `dong_chu` + `kieu_chu`. Lượt end-to-end đủ 6 bước nằm ở
`_do_tg_e2e_kieuchu.py`.

Chạy:  .venv\\Scripts\\python -u _do_kieu_chu_nhin2.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

FF = REPO / "bin" / "ffmpeg.exe"
FFPROBE = REPO / "bin" / "ffprobe.exe"
KHO = Path(r"C:\Users\Admin\Downloads\longtieng")
HOP = REPO / "_kc_nhin"
GIAY = float(os.environ.get("BQ_KC_GIAY", "20"))
#: mốc trích khung — phải nằm trong khoảng CÓ dòng chữ ở dưới.
MOC = 6.0

#: Câu tiếng Việt ĐỦ DẤU (dấu mũ, dấu móc, dấu nặng chồng dấu) — phông thiếu
#: glyph là ra Ô VUÔNG TOFU, nhìn ra ngay.
CAU = [
    (2.0, 7.0, "Đây là bộ phim đáng xem nhất"),
    (7.2, 12.0, "Những cảnh quay tuyệt đẹp"),
    (12.2, 18.0, "Hãy xem tới cuối video nhé"),
]

BO = [
    ("0_MOC_khong_dat_gi", None),
    ("1_to_vang_dam", {"preset": "Vàng nhảy (TikTok)", "co_chu": 0.075,
                       "font": "Anton", "dam": True}),
    ("2_nho_nghieng_do", {"preset": "Trắng viền đen", "co_chu": 0.040,
                          "font": "Be Vietnam Pro", "nghieng": True,
                          "mau": "#FF3B30", "vien": "#FFFFFF",
                          "do_vien": 0.20}),
    ("3_giua_khung_xanh", {"preset": "Xanh neon điện", "co_chu": 0.060,
                           "font": "Montserrat", "vi_tri": "giua",
                           "dam": False}),
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
    vids = sorted(KHO.glob("*.mp4"))
    if not vids:
        print(f"KHÔNG thấy video nào trong {KHO}")
        return 2
    nguon = vids[0]
    HOP.mkdir(exist_ok=True)
    # CẮT NGẮN ra hộp cát — chỉ ĐỌC video của anh Hùng, không đụng bản gốc.
    ngan = HOP / "nguon_ngan.mp4"
    if not ngan.exists():
        subprocess.run([str(FF), "-y", "-v", "error", "-t", str(GIAY),
                        "-i", str(nguon), "-c", "copy", str(ngan)],
                       capture_output=True, timeout=300)
    au = HOP / "tieng.m4a"
    if not au.exists():
        subprocess.run([str(FF), "-y", "-v", "error", "-i", str(ngan),
                        "-vn", "-c:a", "aac", "-b:a", "192k", str(au)],
                       capture_output=True, timeout=300)
    print(f"NGUỒN: {nguon.name}\ncắt {dai_giay(ngan):.2f}s · tiếng "
          f"{dai_giay(au):.2f}s\n")

    for ten, kieu in BO:
        ra = HOP / f"{ten}.mp4"
        log: list = []
        TG.thay_audio_video(ngan, au, ra, che_chu=True, che_chu_cach="mo",
                            che_chu_muc=1.0, che_chu_log=log,
                            dong_chu=CAU, kieu_chu=kieu)
        cc = log[0] if log else {}
        kb = ra.stat().st_size // 1024 if ra.exists() else 0
        print(f"{ten}: {kb} KB · {dai_giay(ra):.2f}s · che={cc.get('che')} "
              f"· dòng chữ={cc.get('so_dong_chu')} · lỗi chữ="
              f"{cc.get('chu_loi', '')}")
        ass = ra.with_suffix(".chu_theo_giong.ass")
        if ass.exists():
            for d in ass.read_text(encoding="utf-8").splitlines():
                if d.startswith("Style: "):
                    print(f"    {d}")
        png = HOP / f"{ten}.png"
        subprocess.run([str(FF), "-y", "-v", "error", "-ss", f"{MOC:.2f}",
                        "-i", str(ra), "-frames:v", "1", str(png)],
                       capture_output=True, timeout=120)
    print(f"\nẢNH ở {HOP} — MỞ RA NHÌN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
