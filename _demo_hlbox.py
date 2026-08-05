# -*- coding: utf-8 -*-
"""DEMO 'Ô NỀN SÁNG CHẠY THEO TỪ ĐANG NÓI' — render clip THẬT bằng ffmpeg.

Chạy:  python _demo_hlbox.py
Ra:    D:\\claude\\demo-phu-de\\  (6 clip .mp4 dọc 1080x1920 + ảnh chụp khung)

Mốc từ giả nhưng ĐÚNG nhịp nói thật (0,30-0,48s/từ) để nhìn được ô nền nhảy
theo từng chữ. Nền là gradient động cho dễ soi độ đọc của chữ + ô màu.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.core.captions import build_ass  # noqa: E402

RA = r"D:\claude\demo-phu-de"
FF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
W, H = 1080, 1920

CAU = [("Chuyện", .40), ("này", .30), ("không", .38), ("ai", .28),
       ("dám", .36), ("kể", .34), ("cho", .28), ("bạn", .36),
       ("nghe", .40), ("nhưng", .34), ("nó", .28), ("đổi", .34),
       ("hết", .32), ("mọi", .32), ("thứ", .46)]

KIEU = ["Ô sáng chạy từ (đa màu)", "Ô sáng chạy từ (vàng)",
        "Ô sáng chạy từ (xanh neon)", "Ô sáng chạy từ (xanh lá)",
        "Ô sáng chạy từ (hồng)", "Ô sáng chạy từ (đỏ)",
        "Cả câu, từ đang nói ĐỎ (CapCut)",
        "Cả câu, từ đang nói CAM (CapCut)",
        "Cả câu, từ đang nói vàng"]     # kiểu cũ để SO SÁNH


def dung_words():
    t, ws = 0.35, []
    for tu, d in CAU:
        ws.append({"start": t, "end": t + d - 0.03, "word": tu})
        t += d
    return ws, t + 0.6


#: tên file ASCII (ffmpeg trên Windows đọc đường dẫn có dấu rất dễ lỗi)
TEN = {"Ô sáng chạy từ (đa màu)": "o-sang-da-mau",
       "Ô sáng chạy từ (vàng)": "o-sang-vang",
       "Ô sáng chạy từ (xanh neon)": "o-sang-xanh-neon",
       "Ô sáng chạy từ (xanh lá)": "o-sang-xanh-la",
       "Ô sáng chạy từ (hồng)": "o-sang-hong",
       "Ô sáng chạy từ (đỏ)": "o-sang-do",
       "Cả câu, từ đang nói ĐỎ (CapCut)": "capcut-do",
       "Cả câu, từ đang nói CAM (CapCut)": "capcut-cam",
       "Cả câu, từ đang nói vàng": "zz-kieu-cu-ca-cau-vang"}


def ten_file(k):
    return TEN[k]


def main():
    os.makedirs(RA, exist_ok=True)
    words, dur = dung_words()
    print(f"ffmpeg: {FF} (có: {os.path.exists(FF)})")
    print(f"{len(words)} từ · clip {dur:.1f}s · ra: {RA}\n")
    for k in KIEU:
        nen = ten_file(k)
        ass = os.path.join(RA, nen + ".ass")
        mp4 = os.path.join(RA, nen + ".mp4")
        ok = build_ass(words, [(0.0, dur)], ass, out_w=W, out_h=H,
                       font="Montserrat", size=int(H * 0.052), ny=0.70,
                       preset=k)
        if not ok:
            print(f"  ✗ {k}: build_ass trả False")
            continue
        n_dong = sum(1 for ln in open(ass, encoding="utf-8")
                     if ln.startswith("Dialogue:"))
        t0 = time.time()
        # nền: gradient động + chữ mờ giả 'video' -> soi được độ đọc
        # chạy NGAY trong thư mục ra + tên file tương đối -> khỏi phải escape
        # "D:" trong filter graph (lỗi original_size khi escape sai).
        cmd = [FF, "-y", "-v", "error",
               "-f", "lavfi", "-i",
               f"gradients=s={W}x{H}:c0=0x1b2a4a:c1=0x6b2a5a:d={dur:.2f}"
               f":speed=0.12:n=3,fps=30",
               "-vf", f"format=yuv420p,ass={nen}.ass",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-t", f"{dur:.2f}", nen + ".mp4"]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           errors="replace", cwd=RA)
        if r.returncode != 0 or not os.path.exists(mp4):
            print(f"  ✗ {k}: ffmpeg rc={r.returncode} {r.stderr[:300]}")
            continue
        # chụp 3 khung giữa clip cho xem nhanh
        for i, gio in enumerate((dur * 0.30, dur * 0.55, dur * 0.80), 1):
            subprocess.run([FF, "-y", "-v", "error", "-ss", f"{gio:.2f}",
                            "-i", mp4, "-frames:v", "1",
                            os.path.join(RA, f"{nen}_khung{i}.png")],
                           capture_output=True)
        print(f"  ✓ {k}\n      {os.path.basename(mp4)} · "
              f"{os.path.getsize(mp4)/1024:.0f} KB · {n_dong} dòng ASS · "
              f"render {time.time()-t0:.1f}s")
    print(f"\nXong. Mở: {RA}")


if __name__ == "__main__":
    main()
