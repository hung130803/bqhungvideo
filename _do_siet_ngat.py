# -*- coding: utf-8 -*-
"""ƯỚC LƯỢNG TRƯỚC KHI VIẾT: siết ngắt giữa câu có ăn không, và giá bao nhiêu?

Đo trên **184 file tiếng THẬT của anh Hùng** (đường CŨ, tiếng Anh) + **181
file v2.44.0 tiếng Việt** + **TRẦN edge bản ngữ**. Hàm THUẦN trên các khoảng
có tiếng đã dò được — chưa đụng ffmpeg, chưa viết bản vá.

Câu hỏi: nếu ép mọi khoảng lặng GIỮA CÂU xuống trần `TRAN`, thì
  * bao nhiêu câu bị đụng tới?
  * bớt được bao nhiêu giây?
  * bảng ngắt/100 ký tự về đâu so với TRẦN bản ngữ?
  * **TRẦN bản ngữ có bị đụng không** (nếu có thì trần đang bị ép quá tay).
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from app.core import piper_tts  # noqa: E402

GOC = Path(r"C:\Users\Admin\AppData\Local\BQHungVideo\_giong_vieneu")
HOP_EN = REPO / "_kq_danhvan" / "hung_that"      # trần en đã sinh
HOP_VI = REPO / "_kq_danhvan" / "hung_viet"      # trần vi đã sinh


def khoang(w: Path):
    return piper_tts.khoang_co_tieng(w)


def gom(ten: str, ws: list[Path], kts: list[int], tran: float):
    n_cau = n_dung = 0
    ngat_truoc = ngat_sau = 0
    giay_bot = 0.0
    tieng_tong = 0.0
    dai_tong = 0.0
    ds_ngat = []
    for w, kt in zip(ws, kts):
        kh, tong = khoang(w)
        if tong <= 0 or not kh:
            continue
        n_cau += 1
        g = [kh[i + 1][0] - kh[i][1] for i in range(len(kh) - 1)]
        ds_ngat.append(len(g))
        ngat_truoc += len(g)
        bot = sum(max(0.0, x - tran) for x in g)
        giay_bot += bot
        if bot > 0.005:
            n_dung += 1
        ngat_sau += sum(1 for x in g if min(x, tran) >= 0.05)
        tieng_tong += sum(b - a for a, b in kh)
        dai_tong += tong
    kt_tong = sum(kts[:n_cau]) or 1
    return {
        "ten": ten, "n": n_cau,
        "ngat_cau": round(ngat_truoc / max(1, n_cau), 2),
        "ngat_100kt": round(100.0 * ngat_truoc / kt_tong, 2),
        "cau_bi_dung": n_dung,
        "ty_cau_bi_dung": round(100.0 * n_dung / max(1, n_cau), 1),
        "giay_bot": round(giay_bot, 2),
        "giay_bot_cau": round(giay_bot / max(1, n_cau), 4),
        "ty_giay_bot": round(100.0 * giay_bot / max(0.01, dai_tong), 2),
        "tieng_s": round(tieng_tong, 1), "dai_s": round(dai_tong, 1),
    }


def main() -> int:
    tran_thu = [0.30, 0.20, 0.15, 0.12, 0.10]
    print("Ý TƯỞNG: ép mọi khoảng lặng GIỮA CÂU xuống <= TRẦN giây.\n"
          "Cột phải đọc là **TRẦN BẢN NGỮ bị đụng bao nhiêu** — trần bị đụng "
          "nhiều\nnghĩa là đang ép cả nhịp nói bình thường, không phải chỉ "
          "ép chỗ vụn.\n")

    # ── nạp 3 bộ ─────────────────────────────────────────────────────────
    en_w, en_kt = [], []
    for jd in sorted(GOC.glob("_job_5148_*")):
        d = json.loads((jd / "job.json").read_text("utf-8"))
        for it in d["items"]:
            p = Path(it["raw"])
            if p.exists():
                en_w.append(p)
                en_kt.append(len(it["text"]))
    vi_w, vi_kt = [], []
    jd = GOC / "_job_12084_59739"
    if (jd / "job.json").exists():
        d = json.loads((jd / "job.json").read_text("utf-8"))
        for it in d["items"][:-1]:
            p = Path(it["raw"])
            if p.exists():
                vi_w.append(p)
                vi_kt.append(len(it["text"]))
    tren_w = sorted(HOP_EN.glob("t*.wav"))
    trvi_w = sorted(HOP_VI.glob("t*.wav"))
    # độ dài chữ của trần = đúng 40 câu đầu của bộ tương ứng
    tren_kt = en_kt[:len(tren_w)]
    trvi_kt = vi_kt[:len(trvi_w)]
    print(f"bộ: ANH {len(en_w)} · VIỆT {len(vi_w)} · "
          f"trần-en {len(tren_w)} · trần-vi {len(trvi_w)}\n")

    print(f"{'TRẦN':>6} | {'bộ':<24}{'ngắt/câu':>9}{'ngắt/100kt':>11}"
          f"{'câu bị đụng':>13}{'giây bớt':>10}{'%thời lượng':>12}")
    ket = {}
    for tr in tran_thu:
        print("-" * 88)
        for ten, ws, kts in (("ANH · anh Hùng (thật)", en_w, en_kt),
                             ("ANH · TRẦN edge en", tren_w, tren_kt),
                             ("VIỆT · v2.44.0 thật", vi_w, vi_kt),
                             ("VIỆT · TRẦN edge vi", trvi_w, trvi_kt)):
            if not ws:
                continue
            r = gom(ten, ws, kts, tr)
            ket.setdefault(str(tr), []).append(r)
            print(f"{tr:>6.2f} | {ten:<24}{r['ngat_cau']:>9.2f}"
                  f"{r['ngat_100kt']:>11.2f}{r['ty_cau_bi_dung']:>12.1f}%"
                  f"{r['giay_bot']:>10.2f}{r['ty_giay_bot']:>11.2f}%")

    Path(REPO / "_kq_siet_ngat.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), "utf-8")
    print("\nĐÃ GHI _kq_siet_ngat.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
