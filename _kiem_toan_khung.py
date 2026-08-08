# -*- coding: utf-8 -*-
"""KIỂM bảng mẫu có cho thấy TOÀN KHUNG hay bị PHÓNG TO CẮT hai bên.

Lỗi 2 anh Hùng báo ở bản v3: *"nó bị phóng to à"*. Bản cũ dựng ô bằng
`scale=…:force_original_aspect_ratio=increase,crop=1080:1920` trên nguồn 16:9 ->
cắt mất hai bên. Cách kiểm KHÁCH QUAN (không nhìn mắt):

  1. Lấy khung ô 0 (GỐC, không hiệu ứng) của bảng mẫu.
  2. Dựng 2 bản ĐỐI CHỨNG từ khung NGUỒN ở CÙNG mốc:
       - bản `decrease`: scale nguyên khung 16:9 về 1080 rộng (giữ hết nội dung)
       - bản `increase+crop`: crop giữa 9:16 rồi scale (kiểu SAI cũ)
  3. So dải giữa của bảng mẫu với 2 bản đó bằng PSNR. Khớp bản `decrease` hơn
     bản `crop` >= 6 dB nghĩa là TOÀN khung.

Chạy: .venv\\Scripts\\python _kiem_toan_khung.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import _nguon_nhat                                              # noqa: E402

FF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
BM = r"D:\hieu-ung-demo-v3\00_BANG_MAU_TAT_CA_HIEU_UNG.mp4"
MOC_PHIM = 100.0        # ô bảng mẫu lấy phim từ giây này (script demo in ra)
CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TD = tempfile.mkdtemp(prefix="kiem_khung_")


def khung(vid: str, t: float, ten: str):
    p = os.path.join(TD, ten + ".png")
    subprocess.run([FF, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", vid,
                    "-frames:v", "1", p], capture_output=True,
                   creationflags=CNW)
    return cv2.imread(p)


def psnr(a, b) -> float:
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 10.0 * float(np.log10(255.0 ** 2 / max(mse, 1e-9)))


def net(a) -> float:
    """Độ NÉT (phương sai Laplacian) — nền mờ phải thấp hơn dải nội dung."""
    return float(cv2.Laplacian(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY),
                               cv2.CV_64F).var())


def main() -> int:
    src = _nguon_nhat.mot("JP")
    if not src or not os.path.exists(BM):
        print("thiếu nguồn hoặc chưa có bảng mẫu")
        return 2
    print(f"[nguồn]    {os.path.basename(src)}")
    print(f"[bảng mẫu] {BM}")
    og = khung(src, MOC_PHIM + 1.5, "goc")
    od = khung(BM, 1.5, "demo")
    if og is None or od is None:
        print("không đọc được khung")
        return 2
    sh, sw = og.shape[:2]
    dh, dw = od.shape[:2]
    cao = int(round(dw * sh / sw / 2)) * 2
    y0 = (dh - cao) // 2
    print(f"nguồn {sw}x{sh} · bảng mẫu {dw}x{dh} -> dải nội dung kỳ vọng "
          f"{dw}x{cao} ở y={y0}..{y0 + cao}")
    dai = od[y0:y0 + cao, :, :]
    # đối chứng 1: decrease (giữ NGUYÊN khung, đúng cái anh Hùng yêu cầu)
    a_dec = cv2.resize(og, (dw, cao), interpolation=cv2.INTER_AREA)
    # đối chứng 2: increase+crop (kiểu SAI của bản v3 cũ)
    cw = int(sh * dw / dh)
    c0 = max(0, (sw - cw) // 2)
    a_crop = cv2.resize(og[:, c0:c0 + cw], (dw, cao),
                        interpolation=cv2.INTER_AREA)
    p_dec, p_crop = psnr(dai, a_dec), psnr(dai, a_crop)
    print(f"\nPSNR dải giữa vs bản `decrease` (TOÀN khung)     = {p_dec:5.1f} dB")
    print(f"PSNR dải giữa vs bản `increase+crop` (kiểu SAI) = {p_crop:5.1f} dB")
    ok1 = p_dec > p_crop + 6.0
    print(f"=> {'ĐẠT — TOÀN khung, không cắt hai bên' if ok1 else '** KHÔNG ĐẠT **'}"
          f"  (cần chênh >= 6 dB, đo được {p_dec - p_crop:.1f} dB)")
    # nền trên/dưới phải là NỀN MỜ
    duoi = od[y0 + cao + 40:dh - 260, :, :]
    n_dai, n_duoi = net(dai), net(duoi)
    ok2 = n_duoi < n_dai
    print(f"\nđộ NÉT: dải nội dung {n_dai:7.0f} · vùng dưới {n_duoi:7.0f} "
          f"-> {'ĐẠT — vùng ngoài là nền MỜ' if ok2 else '** vùng ngoài KHÔNG mờ **'}")
    print(f"\nKẾT QUẢ: {'ĐẠT' if ok1 and ok2 else 'KHÔNG ĐẠT'}")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
