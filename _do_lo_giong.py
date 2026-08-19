"""ĐẾM: mỗi NGUỒN giọng hỗ trợ bao nhiêu · combo đang LỘ bao nhiêu.

**VÌ SAO PHẢI ĐẾM BẰNG MÁY, KHÔNG ĐỌC DOCSTRING.** Việc này được giao với
mệnh đề *"app đang lộ 191 giọng"* — con số đó là `len(nhan_nha.BANG)`, tức số
giọng ĐÃ ĐO nhấn nhá, **không phải** số giọng combo thật sự hiện ra. Muốn biết
combo lộ bao nhiêu thì phải gọi ĐÚNG hàm dựng combo rồi đếm, đúng luật "gọi
thật rồi xem nó rẽ vào đâu".

Không gọi mạng ElevenLabs (5 tài khoản free, đừng đốt): số giọng ElevenLabs
đọc từ `_eleven_voices.json` đã cache nếu có, không có thì ghi "chưa đếm".

Chạy: .venv\\Scripts\\python -u _do_lo_giong.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

# Hộp cát: KHÔNG đụng `%LOCALAPPDATA%\BQHungVideo` của anh Hùng.
SAN = REPO / "_kq_san_dem_giong"
SAN.mkdir(exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(SAN))


def dem() -> dict:
    from app.core import dubbing, giong_bang as GB
    from app.ui.thay_giong_dialog import giong_dung_duoc

    ra: dict = {}

    # ---------- edge-tts ----------
    kho = json.loads((REPO / "_kq_edge_voices.json").read_text("utf-8"))
    ra["edge_ho_tro"] = len({v["ShortName"] for v in kho})
    ra["edge_tieng"] = len({v["Locale"].split("-")[0] for v in kho})

    # ---------- combo THẬT ----------
    tho = dubbing.list_recap_voices()
    ds = giong_dung_duoc(tho)
    ma = [v for _n, v in ds if v]
    ra["combo_dong"] = len(ds)
    ra["combo_ma"] = len(set(ma))
    theo: dict[str, set] = {}
    for v in set(ma):
        theo.setdefault(GB.nguon(v), set()).add(v)
    ra["combo_theo_nguon"] = {k: len(s) for k, s in sorted(theo.items())}
    ra["combo_edge"] = sorted(theo.get(GB.EDGE, ()))
    return ra


def main() -> int:
    d = dem()
    print("=" * 74)
    print("ĐẾM GIỌNG: NGUỒN HỖ TRỢ vs COMBO ĐANG LỘ")
    print("=" * 74)
    print(f"edge-tts danh mục Microsoft : {d['edge_ho_tro']} giọng / "
          f"{d['edge_tieng']} thứ tiếng")
    print(f"combo dựng ra              : {d['combo_dong']} dòng · "
          f"{d['combo_ma']} mã giọng")
    print("theo nguồn                 : " + " · ".join(
        f"{k} {v}" for k, v in d["combo_theo_nguon"].items()))
    ed = d["combo_edge"]
    bt = [v for v in ed if "|" in v]
    print(f"\nedge-tts trong combo: {len(ed)} (trong đó {len(bt)} là biến thể "
          f"cao độ của giọng Việt)")
    tien_to: dict[str, int] = {}
    for v in ed:
        tien_to[v.split("-")[0]] = tien_to.get(v.split("-")[0], 0) + 1
    print("theo tiếng: " + " · ".join(
        f"{k} {n}" for k, n in sorted(tien_to.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
