# -*- coding: utf-8 -*-
"""ĐO: DEMUCS CHẠY GPU (RTX 3060) NHANH HƠN CPU BAO NHIÊU — VÀ CÓ ĐỔI TIẾNG KHÔNG.

Anh Hùng chụp màn hình *"Đang tách nhạc/giọng (249 giây, **cpu**)"*: máy có
RTX 3060 mà bước tách giọng — bước ĐẦU dây chuyền thay tiếng, nhân với 200-300
kênh — vẫn chạy CPU.

**GỐC BỆNH KHÔNG PHẢI Ở MÃ CHỌN THIẾT BỊ.** `thay_giong._MA_TACH` đã viết
đúng từ đầu:

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src = apply_model(model, w[None], device=dev, ...)

Chỗ hỏng là GÓI: `.venv` cài `torch 2.13.0+cpu` — bản dựng KHÔNG có CUDA, nên
`is_available()` trả False vĩnh viễn dù máy có GPU. Tức đây là việc ĐỔI GÓI,
không phải việc sửa mã.

CÁCH ĐO — HAI ARM ĐI CHUNG ĐÚNG MỘT ĐƯỜNG MÃ:
cả hai arm chạy CHÍNH `_bq_tach_runner.py` mà app đang dùng (không dựng đường
riêng cho phép đo — bài học "test xanh oan vì tự dựng dữ liệu giả không đi qua
đường thật"). Khác biệt DUY NHẤT là `PYTHONPATH` trỏ vào thư mục chứa torch
bản CUDA, nên `is_available()` trả True và chính dòng mã trên tự chọn "cuda".

  * **ĐAN XEN** GPU,CPU,GPU,CPU… — đo liền mạch trên máy này đã ra kết luận
    NGƯỢC 2 lần (lượt đầu nuốt chi phí nạp model + đĩa nguội).
  * **TRUNG VỊ**, không lấy trung bình: một lượt bị nhiễu không được kéo cả bảng.
  * Lấy `giay` do CHÍNH runner trả về (thời gian `apply_model` thuần) **và**
    wall của cả tiến trình — hai cột nói hai chuyện: cột đầu là phần GPU tăng
    tốc được, cột sau mới là cái anh Hùng ngồi đợi (gồm nạp model, ghi WAV).
  * **CHẤT LƯỢNG PHẢI ĐO, ĐỪNG ĐOÁN**: so lớp nhạc/giọng hai arm bằng số
    (lệch RMS theo dB + tương quan). GPU dùng kernel khác CPU nên KHÔNG bao giờ
    giống từng bit — câu hỏi đúng là "lệch có nghe ra không", không phải
    "có giống hệt không".
  * **VRAM**: đo đỉnh trong lúc chạy để trả lời "có đủ chỗ khi xuất NVENC chạy
    cùng không". 3 làn xuất + tách giọng là cảnh thật của máy anh Hùng.

    .venv\\Scripts\\python -u _do_demucs_gpu.py [số_vòng]
"""
from __future__ import annotations

import json
import os
import statistics as stt
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

FF = REPO / "bin" / "ffmpeg.exe"
LIB_CUDA = REPO / "_do_cuda"          # torch bản CUDA (thư mục THỬ, không phải _lib)
SAN = REPO / "_do_demucs_gpu_out"
GIAY = 60                              # độ dài đoạn đem đo


def nguon() -> Path:
    """Video THẬT của anh Hùng — không ghi cứng tên file (bài học cổng 47/68)."""
    for kho in (Path(r"C:\Users\Admin\Downloads\longtieng"),
                Path(r"C:\Users\Admin\Downloads\Video")):
        if kho.is_dir():
            ds = sorted(kho.glob("*.mp4"))
            if ds:
                return ds[0]
    raise SystemExit("KHONG CO video nguon de do")


def lam_wav(src: Path, ra: Path) -> Path:
    """Rút 60 giây, 44.1 kHz stereo — đúng thứ `_tach_demucs` nhận."""
    ra.parent.mkdir(parents=True, exist_ok=True)
    if ra.exists():
        return ra
    r = subprocess.run(
        [str(FF), "-v", "error", "-y", "-ss", "30", "-t", str(GIAY),
         "-i", str(src), "-vn", "-ac", "2", "-ar", "44100",
         "-c:a", "pcm_s16le", str(ra)],
        capture_output=True, timeout=600)
    if r.returncode != 0 or not ra.exists() or ra.stat().st_size < 10000:
        raise SystemExit(f"ffmpeg hong: {r.stderr[:300]!r}")
    return ra


def vram_dang_dung() -> int:
    """MiB VRAM đang dùng trên GPU 0 (0 nếu không hỏi được)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20)
        return int(r.stdout.strip().splitlines()[0])
    except Exception:                                        # noqa: BLE001
        return 0


def chay(arm: str, wav: Path, ra_dir: Path) -> dict:
    """Chạy CHÍNH runner của app. arm='gpu' chỉ khác ở PYTHONPATH."""
    from app.core.thay_giong import _viet_runner, lib_demucs
    lib = lib_demucs()
    runner = _viet_runner(lib)
    ra_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if arm == "gpu":
        # torch CUDA đứng TRƯỚC site-packages -> `is_available()` = True ->
        # chính dòng `dev = "cuda" if ...` trong runner tự chọn GPU.
        env["PYTHONPATH"] = str(LIB_CUDA)
    else:
        env.pop("PYTHONPATH", None)
        # ép CPU-only kể cả khi ai đó cài CUDA torch vào .venv sau này
        env["CUDA_VISIBLE_DEVICES"] = ""

    v0 = vram_dang_dung()
    t0 = time.time()
    p = subprocess.run([sys.executable, str(runner), str(lib), str(wav),
                        str(ra_dir), "htdemucs", "0"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=5400)
    wall = time.time() - t0
    vpeak = max(v0, vram_dang_dung())

    ket = {}
    for d in (p.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            ket = json.loads(d.split("\t", 1)[1])
    if not ket.get("ok"):
        raise SystemExit(f"[{arm}] tach HONG: {ket.get('loi') or p.stderr[-400:]}")
    ket["wall"] = wall
    ket["vram_mib"] = vpeak
    return ket


def do_lech(a: Path, b: Path) -> tuple[float, float]:
    """(lệch RMS theo dB, tương quan) giữa 2 file WAV cùng độ dài."""
    import numpy as np
    import soundfile as sf
    x, _ = sf.read(str(a), dtype="float32", always_2d=True)
    y, _ = sf.read(str(b), dtype="float32", always_2d=True)
    n = min(len(x), len(y))
    x, y = x[:n].mean(1), y[:n].mean(1)
    rx = float(np.sqrt((x ** 2).mean())) or 1e-12
    rd = float(np.sqrt(((x - y) ** 2).mean())) or 1e-12
    tq = float(np.corrcoef(x, y)[0, 1])
    return 20.0 * float(np.log10(rd / rx)), tq


def main() -> int:
    vong = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    SAN.mkdir(parents=True, exist_ok=True)
    src = nguon()
    wav = lam_wav(src, SAN / "vao.wav")
    print("=" * 74)
    print(f"ĐO DEMUCS GPU vs CPU · nguồn «{src.name}» · {GIAY}s · {vong} vòng ĐAN XEN")
    print("=" * 74)

    kq: dict[str, list[dict]] = {"gpu": [], "cpu": []}
    for i in range(vong):
        for arm in ("gpu", "cpu"):        # ĐAN XEN trong từng vòng
            r = chay(arm, wav, SAN / f"{arm}_{i}")
            kq[arm].append(r)
            print(f"  vòng {i+1} · {arm.upper():3} -> thiết bị={r['thiet_bi']:4} "
                  f"apply={r['giay']:7.2f}s  wall={r['wall']:7.2f}s  "
                  f"VRAM={r['vram_mib']:5} MiB  torch={r['torch']}")

    print("-" * 74)
    out = {}
    for arm in ("gpu", "cpu"):
        ap = stt.median(r["giay"] for r in kq[arm])
        wl = stt.median(r["wall"] for r in kq[arm])
        out[arm] = (ap, wl)
        print(f"  {arm.upper():3} trung vị: apply {ap:7.2f}s · wall {wl:7.2f}s "
              f"· tỉ lệ so thời gian thật {wl/GIAY:5.3f}x")
    if out["gpu"][0] > 0:
        print(f"\n  NHANH GẤP: apply_model {out['cpu'][0]/out['gpu'][0]:.2f}x "
              f"· CẢ LƯỢT (wall) {out['cpu'][1]/out['gpu'][1]:.2f}x")
    print(f"  VRAM đỉnh khi chạy GPU: {max(r['vram_mib'] for r in kq['gpu'])} MiB "
          f"/ 12288 MiB")

    print("\n  CHẤT LƯỢNG — GPU vs CPU (kernel khác nhau, không bao giờ giống bit):")
    for ten in ("lop_nhac.wav", "stem_vocals.wav"):
        a, b = SAN / "gpu_0" / ten, SAN / "cpu_0" / ten
        if a.exists() and b.exists():
            db, tq = do_lech(a, b)
            print(f"    {ten:16} lệch RMS {db:7.2f} dB · tương quan {tq:.6f}")
        else:
            print(f"    {ten:16} KHÔNG CÓ FILE để so")
    json.dump({k: v for k, v in kq.items()},
              open(SAN / "ket_qua.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
