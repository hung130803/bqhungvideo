# -*- coding: utf-8 -*-
"""FILE NGHE THỬ hướng "ĐỌC CHẬM VỪA KHUNG" — **VIDEO**, cặp TRƯỚC/SAU.

Phải là VIDEO chứ không phải chỉ wav: cột chết người của cả 4 hướng trước là
**lệch tiếng-hình**, mà nghe wav thì không kiểm được cột đó.

Hai file của MỘT CẶP ra từ **CÙNG MỘT LƯỢT CHẠY** — chúng dùng chung đúng bộ
`khop_*.wav` mà `_do_doc_cham.py` dựng, tức cùng bản tách / chép lời / dịch /
**FILE GIỌNG**. Khác nhau đúng một thứ: có kéo dài câu cho đầy khung hay không.

Chuẩn hoá **cùng −14 LUFS** bằng chính `chuan_do_to` (nằm trong
`tron_thay_giong`, đã chạy ở `_do_doc_cham.py`), rồi **ĐO LẠI bằng `loudnorm`
chạy RIÊNG** — không chuẩn hoá thì phép nghe biến thành *"file nào TO hơn"*
(bài học `_NGHE_THU_ANH_HUNG/adam_v2`: lệch 4 LU).

    .venv\\Scripts\\python -u _nghe_thu_lien_mach3.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _do_kho_tg as kho                              # noqa: E402
from config import settings                           # noqa: E402
from app.core import thay_giong as tg                 # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
RA = REPO / "_NGHE_THU_ANH_HUNG" / "lien_mach_3"
KQ = REPO / "_kq_doc_cham.json"
_NW = 0x0800_0000 if os.name == "nt" else 0

#: 1,00 = ĐÚNG app hôm nay (arm ĐỐI CHỨNG) · 1,25 = mức đo được ăn nhất.
CAP = ((1.00, "TRUOC"), (1.25, "SAU"))


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def lufs_rieng(p: Path) -> tuple[float, float]:
    """Thước ĐỘC LẬP với `chuan_do_to` — `loudnorm` chạy riêng trên FILE CUỐI
    (sau đời nén AAC, đúng thứ anh Hùng nghe)."""
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-nostdin", "-i", str(p),
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NW, timeout=1800)
    s = r.stderr or ""
    i = s.rfind("{")
    if i < 0:
        return 0.0, 0.0
    try:
        d = json.loads(s[i:s.rfind("}") + 1])
        return float(d["input_i"]), float(d["input_tp"])
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def main() -> int:
    if not KQ.exists():
        print("Chưa có _kq_doc_cham.json — chạy _do_doc_cham.py trước")
        return 2
    tat = json.loads(KQ.read_text(encoding="utf-8"))
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    for i, p in enumerate(vids[:2]):
        kho.NGUON.append((f"lt{i + 1}", p))
    RA.mkdir(parents=True, exist_ok=True)
    ghi = []
    for r in tat:
        ten, giong, hs = r["ten"], r["giong"], r["he_so_hinh"]
        k = kho.chuan_bi(ten)
        arms = {a["cham_toi_da"]: a for a in r["arms"]}
        for muc, nhan in CAP:
            a = arms.get(muc)
            if not a or not Path(a["_wav"]).exists():
                print(f"  thiếu arm {muc} của {ten}/{giong}")
                continue
            out = RA / (f"{nhan}_{ten}_{giong}_im{a['im_pt']:.1f}pt_"
                        f"{a['im_so_05']}quang_troi{a['troi_max_ms']:.0f}ms.mp4")
            tg.thay_audio_video(k["video"], a["_wav"], out, che_chu=False,
                                he_so_hinh=hs)
            I, TP = lufs_rieng(out)
            ghi.append({"file": out.name, "md5": md5(out),
                        "I_loudnorm_RIENG": round(I, 2),
                        "TP_loudnorm_RIENG": round(TP, 2),
                        "I_chuan_do_to": a["lufs_I"],
                        "im_pt": a["im_pt"], "im_so_05": a["im_so_05"],
                        "im_dai_nhat": a["im_dai_nhat"],
                        "troi_max_ms": a["troi_max_ms"],
                        "meo_db_tb": a["meo_db_tb"]})
            print(f"  {out.name}\n     md5 {ghi[-1]['md5']} · "
                  f"chuan_do_to I {a['lufs_I']:.2f} · loudnorm RIÊNG "
                  f"I {I:.2f} / TP {TP:.2f}")
    n = len({g["md5"] for g in ghi})
    print(f"\nMD5 khác nhau: {n}/{len(ghi)}"
          + ("" if n == len(ghi) else "   <-- TRÙNG NHAU, phép nghe VÔ NGHĨA"))
    (RA / "_so_do.json").write_text(
        json.dumps(ghi, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Thư mục: {RA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
