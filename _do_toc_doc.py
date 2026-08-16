# -*- coding: utf-8 -*-
"""ĐO TỐC ĐỘ ĐỌC THẬT CỦA GIỌNG VIỆT — nền móng cho việc DỊCH THEO NGÂN SÁCH.

CLAUDE.md VIỆC 3 nói rõ: *"kèm ước lượng số âm tiết tiếng Việt đọc được trong
ngần ấy giây (**đo tốc độ đọc thật, đừng đoán hằng số**)"*. File này là phép đo
đó, và nó phải đo trên ĐÚNG thứ app dùng: `thay_giong.doc_ban_dich` (edge-tts
+ **đã cắt lề im**). Đo trên file TTS THÔ là sai 1,07 giây/câu — repo đã đo:
edge-tts chèn ~0,20 s im ở đầu và ~0,87 s ở cuối MỖI câu, câu 12 ký tự ra file
1,848 s trong khi tiếng thật chỉ 0,762 s.

MÔ HÌNH: `giây = a * âm_tiết + b`, khớp bình phương tối thiểu.
  · `a` = giây/âm tiết ở phần thân câu
  · `b` = phần cố định (hơi lấy đà, phụ âm đầu/cuối câu)
Đo cả HAI vì tỉ lệ thuần (`giây/âm_tiết`) trên câu NGẮN luôn cao hơn câu DÀI —
lấy một hằng số trung bình rồi áp cho mọi câu là ước lượng sai hệ thống ở hai
đầu, đúng chỗ đau nhất (câu ngắn của video).

Ngữ liệu: câu tiếng Việt THẬT — 20 bản dịch tốt viết tay (`_do_bo_hong.TOT`)
cộng bản dịch của chính video anh Hùng nếu đã có cache.

  .venv\\Scripts\\python -u _do_toc_doc.py
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

from _do_bo_hong import TOT                              # noqa: E402
from app.ai.cham_dich import am_tiet_viet                # noqa: E402

RA = REPO / "_do_toc_doc.json"


def _don(p: Path) -> None:
    shutil.rmtree(p, ignore_errors=True)


def _quet_san_cu() -> None:
    for p in REPO.glob("bq_tocdoc_*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def cau_do() -> list[str]:
    """Ngữ liệu: bản dịch tốt viết tay + bản dịch thật của video (nếu có)."""
    ds = [d for _g, d in TOT]
    ct = REPO / "_do_dich_moc.json"
    if ct.exists():
        try:
            d = json.loads(ct.read_text(encoding="utf-8"))
            ds += [x for x in d.get("ban_dich", []) if x and x.strip()]
        except Exception:                                # noqa: BLE001
            pass
    # bỏ trùng, giữ thứ tự
    thay, ra = set(), []
    for x in ds:
        k = x.strip()
        if k and k not in thay:
            thay.add(k)
            ra.append(k)
    return ra


def khop_tuyen_tinh(x: list[float], y: list[float]) -> tuple[float, float, float]:
    """Bình phương tối thiểu y = a*x + b. Trả (a, b, R²)."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sxx = sum((x[i] - mx) ** 2 for i in range(n))
    a = sxy / sxx if sxx else 0.0
    b = my - a * mx
    sst = sum((y[i] - my) ** 2 for i in range(n))
    sse = sum((y[i] - (a * x[i] + b)) ** 2 for i in range(n))
    return a, b, (1.0 - sse / sst) if sst else 0.0


def main() -> int:
    _quet_san_cu()
    from app.core.thay_giong import doc_ban_dich, probe_duration

    texts = cau_do()
    print("=" * 74)
    print(f"ĐO TỐC ĐỘ ĐỌC GIỌNG VIỆT — {len(texts)} câu THẬT, edge-tts, "
          "ĐÃ CẮT LỀ IM")
    print("=" * 74)

    san = REPO / f"bq_tocdoc_{os.getpid()}"
    san.mkdir(parents=True, exist_ok=True)
    atexit.register(_don, san)

    kq = doc_ban_dich(texts, san, dich_sang="vi")
    print(f"giọng: {kq['voice']} · hỏng {kq['so_hong']}/{len(texts)} · "
          f"cắt lề TB {kq['cat_le']['giay_cat_tb']:.3f}s/câu "
          f"(tổng {kq['cat_le']['giay_cat_tong']:.1f}s)")

    hang = []
    for i, t in enumerate(texts):
        if not kq["ok"][i]:
            continue
        f = kq["files"][i]
        if not f or not Path(f).exists():
            continue
        d = probe_duration(f)
        at = am_tiet_viet(t)
        if at <= 0 or d <= 0:
            continue
        hang.append({"text": t, "am_tiet": at, "giay": round(d, 3),
                     "giay_moi_at": round(d / at, 4)})

    hang.sort(key=lambda r: r["am_tiet"])
    x = [float(r["am_tiet"]) for r in hang]
    y = [r["giay"] for r in hang]
    a, b, r2 = khop_tuyen_tinh(x, y)

    print(f"\nĐO ĐƯỢC {len(hang)} câu · âm tiết {int(min(x))}..{int(max(x))} · "
          f"độ dài {min(y):.2f}..{max(y):.2f}s")
    print(f"\n  MÔ HÌNH:  giây = {a:.4f} * âm_tiết + {b:.4f}   (R² = {r2:.4f})")
    print(f"  tức {1/a:.2f} âm tiết/giây ở phần thân câu, "
          f"cộng {b:.3f}s cố định mỗi câu")

    tho = sum(y) / sum(x)
    print(f"  (tỉ lệ THÔ nếu bỏ hằng số: {tho:.4f} s/âm tiết = "
          f"{1/tho:.2f} âm tiết/giây — dùng số này là ước lượng SAI HỆ THỐNG "
          "ở câu ngắn)")

    print("\n  TỈ LỆ THÔ THEO NHÓM ĐỘ DÀI (chứng minh vì sao cần hằng số b):")
    print("   âm tiết | n  | giây TB | s/âm tiết | âm tiết/giây")
    for lo, hi in ((1, 4), (5, 7), (8, 10), (11, 14), (15, 99)):
        nh = [r for r in hang if lo <= r["am_tiet"] <= hi]
        if not nh:
            continue
        gt = sum(r["giay"] for r in nh) / len(nh)
        sa = sum(r["giay"] for r in nh) / sum(r["am_tiet"] for r in nh)
        print(f"   {lo:>3}-{hi:<3} | {len(nh):<2} | {gt:7.2f} | {sa:9.4f} | "
              f"{1/sa:12.2f}")

    # SAI SỐ CỦA MÔ HÌNH — cái này quyết định ngân sách có dùng được không
    sai = [abs(y[i] - (a * x[i] + b)) for i in range(len(x))]
    sai_s = sorted(sai)
    print(f"\n  SAI SỐ MÔ HÌNH: TB {sum(sai)/len(sai):.3f}s · "
          f"trung vị {sai_s[len(sai_s)//2]:.3f}s · "
          f"90% {sai_s[int(0.9*len(sai_s))]:.3f}s · max {max(sai):.3f}s")

    # ĐẢO NGƯỢC: mấy âm tiết thì lọt N giây
    print("\n  NGÂN SÁCH ÂM TIẾT THEO KHUNG (đảo mô hình, làm tròn xuống):")
    print("   khung(s) | âm tiết tối đa")
    for g in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0):
        n = int((g - b) / a)
        print(f"   {g:>8.1f} | {max(0, n):>3}")

    RA.write_text(json.dumps({
        "voice": kq["voice"], "n": len(hang), "a": a, "b": b, "r2": r2,
        "tho": tho, "hang": hang}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nđã ghi {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
