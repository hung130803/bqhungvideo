"""TỰ KIỂM THƯỚC PHỤ ĐỀ trước khi dùng nó dựng bộ đối chứng.

Hai thước trước đều báo sai và MẮT bắt được cả hai:
  · mật độ nét cả dải  -> báo GIẢ ở dòng phụ đề NGẮN (`另一边` 3 chữ)
  · nét sáng cả dải    -> báo GIẢ ở vân cảnh SÁNG (v4 t=1,0 bãi đá + trời)

Thước thứ ba: chữ phụ đề nằm gọn trên MỘT DÒNG -> mật độ dồn vào một cửa sổ
vài hàng, phần còn lại của dải gần sạch. Vân cảnh thì rải đều mọi hàng. Nên
đo `dinh` = mật độ cửa sổ `CAO_DONG` hàng đậm nhất, và `troi` = mật độ trung
bình các hàng NGOÀI cửa sổ đó; điểm = dinh - 1.6*troi.

16 mốc dưới đây do TÔI SOI MẮT mà ghi (ảnh ở `_kq_nn/soi/`), KHÔNG do thước
nào sinh ra. Thước nào không tách được 16 mốc này thì không được dùng.

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_thuoc.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = GOC / "_kq_nn"
FF = str(GOC / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0

NGUONG_SANG = 190
GIUA = 0.84
CAO_DONG = 14          # chiều cao một dòng chữ (px khung gốc 720p)
HE_TROI = 1.6

#: SỰ THẬT GHI BẰNG MẮT — (video, giây, CÓ chữ người kể?)
MOC_TAY = [
    ("v1_dutu", 1.50, False),      # áo khoác, không chữ
    ("v1_dutu", 30.00, True),      # 他们还定了一个规矩
    ("v1_dutu", 108.75, True),     # 另一边  (dòng NGẮN 3 chữ)
    ("v1_dutu", 362.75, False),    # cảnh tối, tiếng Anh trong phim
    ("v2_nieu", 1.50, False),      # tối, chưa có phụ đề
    ("v2_nieu", 4.00, True),       # 从来没有一部电影能让我从头尿到尾
    ("v2_nieu", 7.00, True),       # 由安娜贝尔亲自操刀的最新恐怖片
    ("v3_8daodien", 163.00, True), # 可一抬头 (dòng NGẮN 4 chữ)
    ("v3_8daodien", 200.00, True), # 一想到自己没钱还债的下场
    ("v3_8daodien", 218.75, True), # 如此一来 (dòng NGẮN)
    ("v4_khuyendung", 1.00, False),  # bãi đá SÁNG, không chữ
    ("v4_khuyendung", 2.50, False),
    ("v4_khuyendung", 3.60, False),
    ("v4_khuyendung", 4.75, False),
    ("v4_khuyendung", 6.20, False),
    ("v4_khuyendung", 40.00, True),  # 已经彻底沦为感染者的乐园
]


def _dai(ten: str, t: float, pd: dict):
    import numpy as np
    from app.core import che_chu as cc
    v = pd[ten]
    W, y0, y1 = v["W"], v["y0"], v["y1"]
    h = y1 - y0
    r = subprocess.run(
        [FF, "-v", "error", "-ss", f"{t:.3f}",
         "-i", str(SAN / "video" / f"{ten}.mp4"), "-frames:v", "1",
         "-vf", f"crop={W}:{h}:0:{y0},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, creationflags=_NO_WIN, timeout=120)
    if r.returncode != 0 or len(r.stdout) < W * h:
        return None
    x0 = int(W * (1 - GIUA) / 2)
    g = np.frombuffer(r.stdout[:W * h], dtype=np.uint8).reshape(h, W)[:, x0:W - x0]
    return cc._mat_na(g).astype(bool) & (g >= NGUONG_SANG)


def cham(m) -> tuple[float, float, float]:
    """(diem, dinh, troi) — mật độ dồn vào MỘT DÒNG thì điểm cao."""
    import numpy as np
    hang = m.mean(axis=1)
    h = len(hang)
    k = min(CAO_DONG, h)
    cs = np.concatenate([[0.0], np.cumsum(hang)])
    win = (cs[k:] - cs[:-k]) / k                      # mật độ TB từng cửa sổ
    j = int(np.argmax(win))
    dinh = float(win[j])
    ngoai = np.concatenate([hang[:j], hang[j + k:]])
    troi = float(ngoai.mean()) if ngoai.size else 0.0
    return dinh - HE_TROI * troi, dinh, troi


def main() -> None:
    pd = json.loads((SAN / "phude.json").read_text(encoding="utf-8"))
    co, khong = [], []
    print(f"{'video':16s} {'giay':>7s} {'mat':>5s} {'diem':>9s} "
          f"{'dinh':>8s} {'troi':>8s}")
    for ten, t, that in MOC_TAY:
        m = _dai(ten, t, pd)
        if m is None:
            print(f"{ten:16s} {t:7.2f}  KHONG DOC DUOC")
            continue
        d, dinh, troi = cham(m)
        (co if that else khong).append(d)
        print(f"{ten:16s} {t:7.2f} {'CO' if that else 'KHONG':>5s} "
              f"{d:9.5f} {dinh:8.5f} {troi:8.5f}")
    print()
    print(f"  CO chu    : thap nhat {min(co):.5f}  (n={len(co)})")
    print(f"  KHONG chu : cao nhat  {max(khong):.5f}  (n={len(khong)})")
    if min(co) > max(khong):
        ng = (min(co) + max(khong)) / 2
        print(f"  -> TACH ROI. Khoang trong = {min(co) - max(khong):.5f}, "
              f"nguong giua = {ng:.5f}")
        print(f"  -> bien an toan: CO gap {min(co)/max(ng,1e-9):.2f} lan nguong")
    else:
        print("  -> KHONG TACH DUOC: thuoc nay KHONG dung duoc, phai doi cach")
        sys.exit(1)


if __name__ == "__main__":
    main()
