# -*- coding: utf-8 -*-
"""LỖI 2 — CHẠY TÁCH GIỌNG THẬT RỒI ĐO "GIÂY NÀO MẤT NHẠC".

Đo bước 1 (`tach_giong`) trên video THẬT của anh Hùng, giữ lại mọi stem, rồi
so ĐƯỜNG BAO RMS của lớp NHẠC với bản GỐC trên cùng trục thời gian.

Câu hỏi phải trả lời bằng SỐ (không phải "có vẻ ổn"):
  1. Lớp nhạc có khoảng nào IM HẲN trong khi gốc đang có tiếng không?
  2. Các khoảng đó có rơi ĐỀU ĐẶN theo chu kỳ không -> dấu hiệu RANH GIỚI
     ĐOẠN của Demucs (`apply_model(split=True)`), khác hẳn "nhạc vốn im".
  3. Tổng năng lượng: `nhac + vocals` có bằng `gốc` không -> bắt ca "rơi mất
     một đoạn" / "nhân đôi".

BẪY tránh sẵn: astats tiền tố `[Parsed...]` -> dùng `in`; `-inf` -> -120;
mọi subprocess có `timeout=`; stdout utf-8; KHÔNG đụng file gốc (copy sẵn).
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_mat_tieng import (BUOC, FFMPEG, duong_bao, duration,  # noqa: E402
                           gom_khoang)

#: Lớp nhạc dưới mức này = IM (dBFS).
NHAC_IM_DB = -60.0
#: Gốc trên mức này = "đang có tiếng, đáng lẽ nhạc phải còn gì đó".
GOC_CO_DB = -45.0


def chay_tach(video: Path, lam: Path) -> dict:
    from app.core import thay_giong as tg

    lam.mkdir(parents=True, exist_ok=True)
    goc_wav = lam / "goc.wav"
    t0 = time.time()
    tong = tg.tach_wav(video, goc_wav)
    print(f"  rút audio: {tong:.3f}s  ({time.time() - t0:.1f}s)")
    t1 = time.time()
    t = tg.tach_giong(goc_wav, lam / "tach", cach="demucs",
                      on_progress=lambda p, m: None)
    print(f"  tách xong: {time.time() - t1:.1f}s  cách={t.get('cach')} "
          f"thiết bị={t.get('thiet_bi')} tỉ lệ={t.get('ty_le')}")
    t["goc_wav"] = str(goc_wav)
    t["do_dai_goc"] = tong
    return t


def tong_nang_luong(path: str | Path) -> float:
    """RMS toàn file (tuyến tính) — để so 'nhạc+giọng' với 'gốc'."""
    from app.core import thay_giong as tg
    return tg.do_rms(path)


def chu_ky(khoang: list[tuple[float, float]]) -> dict:
    """Khoảng cách giữa các lần mất tiếng — đều đặn = ranh giới đoạn."""
    if len(khoang) < 3:
        return {"n": len(khoang)}
    moc = [a for a, _ in khoang]
    d = [round(moc[i + 1] - moc[i], 2) for i in range(len(moc) - 1)]
    tb = sum(d) / len(d)
    do_lech = math.sqrt(sum((x - tb) ** 2 for x in d) / len(d))
    return {"n": len(khoang), "khoang_cach": d[:20],
            "tb": round(tb, 2), "do_lech": round(do_lech, 2)}


def main() -> int:
    video = Path(sys.argv[1] if len(sys.argv) > 1
                 else REPO / "_do_lt" / "goc.mp4")
    lam = Path(sys.argv[2] if len(sys.argv) > 2 else REPO / "_do_lt" / "tam")
    print(f"VIDEO: {video.name}  ({duration(video):.2f}s)")

    t = chay_tach(video, lam)
    goc_wav = t["goc_wav"]
    nhac = t["nhac"]
    stems = t.get("stems") or {}
    giong = stems.get("vocals", "")

    print("\n== ĐƯỜNG BAO RMS ==")
    bao_goc = duong_bao(goc_wav)
    bao_nhac = duong_bao(nhac)
    bao_giong = duong_bao(giong) if giong else []
    print(f"  gốc  : {len(bao_goc)} cửa sổ, cao {max(bao_goc):.1f} "
          f"thấp {min(bao_goc):.1f} dB")
    print(f"  nhạc : {len(bao_nhac)} cửa sổ, cao {max(bao_nhac):.1f} "
          f"thấp {min(bao_nhac):.1f} dB")
    if bao_giong:
        print(f"  giọng: {len(bao_giong)} cửa sổ, cao {max(bao_giong):.1f} "
              f"thấp {min(bao_giong):.1f} dB")

    n = min(len(bao_goc), len(bao_nhac))
    im: list[int] = []
    for i in range(n):
        if bao_goc[i] >= GOC_CO_DB and bao_nhac[i] < NHAC_IM_DB:
            im.append(i)
    kh = gom_khoang(im)
    tong = t["do_dai_goc"]
    print(f"\n== LỚP NHẠC IM TRONG KHI GỐC CÓ TIẾNG ==")
    print(f"  {len(im)} cửa sổ = {len(im) * BUOC:.2f}s "
          f"({100.0 * len(im) * BUOC / max(0.001, tong):.1f}% video)")
    for a, b in kh:
        print(f"    {a:7.2f}s -> {b:7.2f}s   ({b - a:5.2f}s)")
    print("  chu kỳ:", json.dumps(chu_ky(kh), ensure_ascii=False))

    print("\n== BẢO TOÀN NĂNG LƯỢNG (bắt ca rơi/nhân đôi đoạn) ==")
    r_goc = tong_nang_luong(goc_wav)
    r_nhac = tong_nang_luong(nhac)
    r_giong = tong_nang_luong(giong) if giong else 0.0
    print(f"  RMS gốc {r_goc:.6f} · nhạc {r_nhac:.6f} · giọng {r_giong:.6f}")
    if r_goc > 0:
        cong = math.sqrt(r_nhac ** 2 + r_giong ** 2)
        print(f"  căn(nhạc²+giọng²) = {cong:.6f}  -> lệch so gốc "
              f"{20 * math.log10(max(1e-9, cong) / r_goc):+.2f} dB")

    # 20 cửa sổ nhạc thấp nhất — để thấy có "hố" hay không
    thap = sorted(range(n), key=lambda i: bao_nhac[i])[:20]
    print("\n== 20 CỬA SỔ NHẠC THẤP NHẤT ==")
    print("   giây      gốc dB    nhạc dB   chênh")
    for i in sorted(thap):
        print(f"  {i * BUOC:7.2f}   {bao_goc[i]:7.1f}   {bao_nhac[i]:7.1f}   "
              f"{bao_goc[i] - bao_nhac[i]:6.1f}")
    (lam / "_ket.json").write_text(json.dumps(
        {"tach": {k: v for k, v in t.items() if k != "stems"},
         "im_khoang": kh, "bao_goc": bao_goc, "bao_nhac": bao_nhac,
         "bao_giong": bao_giong}, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
