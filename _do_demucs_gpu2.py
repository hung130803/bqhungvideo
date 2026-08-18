# -*- coding: utf-8 -*-
"""ĐO BỔ SUNG — VÁ 2 CHỖ HỚ CỦA `_do_demucs_gpu.py`.

(1) **VRAM ĐỈNH đo sai**: lượt đo đầu lấy mẫu TRƯỚC và SAU tiến trình con, mà
    tiến trình thoát là trả sạch VRAM -> ra 639 MiB = đúng bằng mức nền, tức
    phép đo đó **không đo gì cả** (đúng họ "phép đo hỏng phát chứng nhận" đã
    ghi ở cổng 44/53). Nay POLL `nvidia-smi` 0,2 giây/lần TRONG lúc chạy.
    Câu hỏi thật cần trả lời: 3 làn xuất NVENC chạy cùng thì còn đủ chỗ không.

(2) **Lệch chất lượng −19 dB chưa có SÀN NHIỄU để so.** Demucs không tiền định
    tuyệt đối, nên "GPU khác CPU 19 dB" chỉ có nghĩa khi biết "CPU khác CHÍNH
    NÓ bao nhiêu". Không có cột đối chứng này thì con số là số trần trụi, và
    repo này đã sập 3 lần vì đọc số thô (xem "số thô là SỐ LỪA").
    Dùng lại đúng các file lượt trước đã ghi ra, không chạy lại.

    .venv\\Scripts\\python -u _do_demucs_gpu2.py
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
SAN = REPO / "_do_demucs_gpu_out"
LIB_CUDA = REPO / "_do_cuda"


def do_lech(a: Path, b: Path) -> tuple[float, float]:
    import numpy as np
    import soundfile as sf
    x, _ = sf.read(str(a), dtype="float32", always_2d=True)
    y, _ = sf.read(str(b), dtype="float32", always_2d=True)
    n = min(len(x), len(y))
    x, y = x[:n].mean(1), y[:n].mean(1)
    rx = float(np.sqrt((x ** 2).mean())) or 1e-12
    rd = float(np.sqrt(((x - y) ** 2).mean())) or 1e-12
    return 20.0 * float(np.log10(rd / rx)), float(np.corrcoef(x, y)[0, 1])


def main() -> int:
    import os

    from app.core.thay_giong import _viet_runner, lib_demucs

    print("=" * 76)
    print("(2) SÀN NHIỄU: cùng một arm chạy 2 lượt có ra giống nhau không?")
    print("=" * 76)
    print("  Nếu CPU-vs-CPU cũng lệch cỡ GPU-vs-CPU thì con số kia là NHIỄU")
    print("  của chính Demucs, KHÔNG phải 'GPU làm đổi tiếng'.\n")
    cap = [
        ("CPU lượt0 vs CPU lượt1  (SÀN NHIỄU)", SAN / "cpu_0", SAN / "cpu_1"),
        ("CPU lượt1 vs CPU lượt2  (SÀN NHIỄU)", SAN / "cpu_1", SAN / "cpu_2"),
        ("GPU lượt0 vs GPU lượt1  (SÀN NHIỄU)", SAN / "gpu_0", SAN / "gpu_1"),
        ("GPU lượt0 vs CPU lượt0  (ĐANG HỎI)", SAN / "gpu_0", SAN / "cpu_0"),
        ("GPU lượt1 vs CPU lượt1  (ĐANG HỎI)", SAN / "gpu_1", SAN / "cpu_1"),
        ("GPU lượt2 vs CPU lượt2  (ĐANG HỎI)", SAN / "gpu_2", SAN / "cpu_2"),
    ]
    for ten in ("lop_nhac.wav", "stem_vocals.wav"):
        print(f"  --- {ten}")
        for nhan, da, db_ in cap:
            fa, fb = da / ten, db_ / ten
            if not (fa.exists() and fb.exists()):
                print(f"    {nhan:38} THIẾU FILE")
                continue
            d, t = do_lech(fa, fb)
            print(f"    {nhan:38} lệch RMS {d:7.2f} dB · tương quan {t:.6f}")
        print()

    print("=" * 76)
    print("(1) VRAM ĐỈNH — poll 0,2s/lần TRONG lúc Demucs chạy trên GPU")
    print("=" * 76)
    lib = lib_demucs()
    runner = _viet_runner(lib)
    wav = SAN / "vao.wav"
    ra = SAN / "vram_do"
    ra.mkdir(parents=True, exist_ok=True)

    dinh = {"mib": 0}
    dung = threading.Event()

    def poll() -> None:
        while not dung.is_set():
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10)
                v = int(r.stdout.strip().splitlines()[0])
                dinh["mib"] = max(dinh["mib"], v)
            except Exception:                                # noqa: BLE001
                pass
            time.sleep(0.2)

    nen = dinh["mib"]
    t = threading.Thread(target=poll, daemon=True)
    t.start()
    time.sleep(0.6)
    nen = dinh["mib"]
    print(f"  VRAM nền trước khi chạy: {nen} MiB")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(LIB_CUDA)
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    p = subprocess.run([sys.executable, str(runner), str(lib), str(wav),
                        str(ra), "htdemucs", "0"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=5400)
    wall = time.time() - t0
    time.sleep(0.3)
    dung.set()
    t.join(timeout=3)
    ok = "BQJSON" in (p.stdout or "") and '"ok": true' in (p.stdout or "").lower()
    print(f"  chạy xong {wall:.2f}s · ok={ok}")
    print(f"  VRAM ĐỈNH đo được:       {dinh['mib']} MiB / 12288 MiB")
    print(f"  -> Demucs chiếm thêm:    {dinh['mib'] - nen} MiB")
    print(f"  -> còn trống cho việc khác: {12288 - dinh['mib']} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
