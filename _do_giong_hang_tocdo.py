# -*- coding: utf-8 -*-
"""TỐC ĐỘ GIÓNG HÀNG — video 10 PHÚT tốn bao nhiêu giây, GPU và CPU.

VÌ SAO PHẢI ĐO CẢ CPU: máy anh Hùng có RTX 3060 nhưng **máy nhân viên KHÔNG
có GPU**. Một tính năng chỉ chạy nổi trên máy dev thì không bán được — đúng
bài học Demucs (cổng 55: *"muốn bán ra thật phải chọn 1 trong 3"*).

CÁCH ĐO — ĐAN XEN, BẮT BUỘC:
  Đo liền mạch (GPU trước, CPU sau) đã cho kết luận SAI **3 lần** trên máy
  này (rõ nhất: cổng 55 đo ra *"2 luồng CHẬM HƠN 0,62 lần"*, đo đan xen lại
  ra *nhanh 1,37 lần*). Máy luôn có việc nền, và lượt ĐẦU còn nuốt phí nạp
  model + làm nóng cache đĩa. Nên chạy **GPU · CPU · CPU · GPU** rồi lấy
  TRUNG VỊ từng arm.

TÁCH HAI CỘT THỜI GIAN — đọc gộp là kết luận sai:
  · `nạp`   = mở tiến trình + import torch + đọc model 1,18 GB. **HẰNG SỐ**
              mỗi lượt gọi, KHÔNG phụ thuộc độ dài video.
  · `gióng` = phần thật sự chạy model trên tiếng. Cái này mới tỉ lệ với phim.
  Video 10 phút chỉ tốn phí nạp MỘT lần (app gọi `giong_hang_loat` một lượt
  cho cả video), nên gộp nó vào rồi chia cho 10 phút là thổi phồng giá.

DÙNG LẠI CÙNG FILE TIẾNG cho mọi lượt: chi phí gióng hàng phụ thuộc ĐỘ DÀI
tiếng và SỐ TOKEN, không phụ thuộc nội dung — nên lặp lại danh sách file để
đủ 10 phút là hợp lệ, và nó bỏ được biến động của mạng edge-tts khỏi phép đo.

  .venv\\Scripts\\python -u _do_giong_hang_tocdo.py
  BQ_PHUT=5 .venv\\Scripts\\python -u _do_giong_hang_tocdo.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

PHUT = float(os.environ.get("BQ_PHUT", "10"))
DICH = PHUT * 60.0
SAN = Path(os.environ.get("TEMP", "/tmp")) / f"bq_ghtd_{os.getpid()}"
RA = REPO / "_do_giong_hang_tocdo.json"
#: GPU · CPU · CPU · GPU — đan xen VÀ đảo thứ tự, để arm chạy sau không phải
#: lúc nào cũng là arm gánh phần máy đã nóng.
VONG = ["gpu", "cpu", "cpu", "gpu"]


def do_dai(p: str) -> float:
    from config import settings
    try:
        return float(subprocess.run(
            [settings.FFPROBE_PATH, "-v", "error", "-show_entries",
             "format=duration", "-of", "default=nw=1:nk=1", p],
            capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    except Exception:                                    # noqa: BLE001
        return 0.0


def dung_corpus() -> tuple[list[str], list[str], str]:
    """Sinh tiếng bằng edge-tts rồi LẶP danh sách cho đủ `DICH` giây."""
    from app.core import dubbing
    sys.path.insert(0, str(REPO))
    import _do_giong_hang as D

    SAN.mkdir(parents=True, exist_ok=True)
    wavs: list[str] = []
    texts: list[str] = []
    for nn in ("vi", "en", "zh", "ja"):
        cau = D.nap_cau(nn)[:8]
        ps = [str(SAN / f"{nn}{i:02d}.mp3") for i in range(len(cau))]
        ok, _ = asyncio.run(dubbing._synth_all_words(
            cau, D.GIONG[nn], ps, lang=nn))
        for i, o in enumerate(ok):
            if o and Path(ps[i]).is_file():
                wavs.append(ps[i])
                texts.append(cau[i])
    if not wavs:
        raise SystemExit("edge-tts không đọc được câu nào")
    giay1 = [do_dai(w) for w in wavs]
    tong1 = sum(giay1)
    # LẶP cho đủ 10 phút (xem docstring: chi phí theo độ dài, không theo nội
    # dung) — mỗi lần lặp là một câu RIÊNG với model, không có cache nào.
    W, T, tong = [], [], 0.0
    i = 0
    while tong < DICH:
        W.append(wavs[i % len(wavs)])
        T.append(texts[i % len(texts)])
        tong += giay1[i % len(giay1)]
        i += 1
    return W, T, (f"{len(wavs)} câu gốc ({tong1:.1f}s) -> lặp thành "
                  f"{len(W)} câu = {tong:.1f}s tiếng")


def mot_luot(W: list[str], T: list[str], gpu: bool) -> dict:
    from app.core import giong_hang as gh
    tt: dict = {}
    t0 = time.time()
    moc = gh.giong_hang_loat(W, T, lang="", gpu=gpu, thong_tin=tt,
                             timeout=7200)
    wall = time.time() - t0
    return {
        "wall": round(wall, 2),
        "giay_align": tt.get("giay_align"),
        "nap": round(wall - float(tt.get("giay") or 0), 2),
        "thiet_bi": tt.get("thiet_bi"),
        "co_moc": sum(1 for m in moc if m), "n": len(W),
    }


def main() -> int:
    from app.core import giong_hang as gh
    print("=" * 78)
    print(f"TỐC ĐỘ GIÓNG HÀNG — đích {PHUT:.0f} phút tiếng · đan xen "
          f"{' · '.join(VONG)}")
    print("=" * 78)
    t = gh.tinh_trang_giong_hang()
    if not t["co"]:
        print("THIẾU:", t["thieu"])
        return 2
    try:
        import psutil
        print(f"máy: {psutil.cpu_count(logical=True)} luồng CPU · "
              f"CPU nền {psutil.cpu_percent(interval=1.0):.1f}%")
    except Exception:                                    # noqa: BLE001
        pass

    W, T, mo_ta = dung_corpus()
    print(mo_ta)
    tong_giay = sum(do_dai(w) for w in W)

    kq: dict[str, list[dict]] = {"gpu": [], "cpu": []}
    for k, arm in enumerate(VONG):
        print(f"\n--- vòng {k + 1}/{len(VONG)} · {arm.upper()} ---")
        r = mot_luot(W, T, gpu=(arm == "gpu"))
        print(f"    thiết bị THẬT={r['thiet_bi']} · wall {r['wall']}s · "
              f"riêng gióng {r['giay_align']}s · nạp {r['nap']}s · "
              f"{r['co_moc']}/{r['n']} câu có mốc")
        kq[arm].append(r)
        RA.write_text(json.dumps({"kq": kq, "giay_tieng": tong_giay},
                                 ensure_ascii=False, indent=1),
                      encoding="utf-8")

    print()
    print("=" * 78)
    print(f"KẾT QUẢ — {tong_giay:.0f} giây tiếng ({tong_giay / 60:.1f} phút) "
          f"· {len(W)} câu · TRUNG VỊ {len(VONG) // 2} vòng")
    print("=" * 78)
    print(f"  {'arm':<6} {'thiết bị':<8} {'CẢ LƯỢT':>10} {'riêng gióng':>13} "
          f"{'nạp model':>11} {'so thời gian thật':>19}")
    goc = {}
    for arm in ("gpu", "cpu"):
        v = kq[arm]
        if not v:
            continue
        wall = statistics.median(x["wall"] for x in v)
        al = statistics.median(float(x["giay_align"] or 0) for x in v)
        nap = statistics.median(x["nap"] for x in v)
        goc[arm] = (wall, al)
        print(f"  {arm.upper():<6} {str(v[0]['thiet_bi']):<8} {wall:>9.1f}s "
              f"{al:>12.1f}s {nap:>10.1f}s {al / max(0.001, tong_giay):>18.4f}x")
    if "gpu" in goc and "cpu" in goc:
        print(f"\n  GPU nhanh hơn CPU: cả lượt "
              f"{goc['cpu'][0] / max(0.01, goc['gpu'][0]):.2f}x · "
              f"riêng phần gióng {goc['cpu'][1] / max(0.01, goc['gpu'][1]):.2f}x")
        for arm in ("gpu", "cpu"):
            w, a = goc[arm]
            print(f"  {arm.upper()}: video {PHUT:.0f} phút -> "
                  f"**{w:.0f} giây** (trong đó gióng {a:.0f}s, "
                  f"nạp model {w - a:.0f}s — phí nạp là HẰNG SỐ, "
                  f"video dài hơn KHÔNG tốn thêm)")
    print(f"\nGhi: {RA}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(SAN, ignore_errors=True)
