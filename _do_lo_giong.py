"""ĐẾM: mỗi NGUỒN giọng hỗ trợ bao nhiêu · combo đang LỘ bao nhiêu.

**VÌ SAO PHẢI ĐẾM BẰNG MÁY, KHÔNG ĐỌC DOCSTRING.** Việc này được giao với
mệnh đề *"app đang lộ 191 giọng"* — con số đó là ``len(nhan_nha.BANG)``, tức số
giọng ĐÃ ĐO nhấn nhá, **không phải** số giọng combo thật sự hiện ra. Đo thật ra
**76 giọng edge-tts**: ``giong_mo.nen_mo`` chưa được nối vào cửa nào, nên 185
giọng "đã mở khoá" là mã chết. Muốn biết combo lộ bao nhiêu thì phải gọi ĐÚNG
hàm dựng combo rồi đếm — đúng luật "gọi thật rồi xem nó rẽ vào đâu".

**KHÔNG ĐỐT HẠN MỨC ElevenLabs**: ``_eleven_voices()`` chỉ gọi ``GET /voices``
(không tiêu ký tự nào) và có cache 7 ngày. Nguồn nào cần key mà máy không có
key thì cột "đang lộ" ghi 0 kèm lý do, **không đoán**.

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


def ho_tro() -> dict[str, tuple[int, str]]:
    """{nguồn: (số giọng nguồn đó HỖ TRỢ, ghi chú)} — hỏi CHÍNH module nguồn."""
    from app.core import dubbing as D
    ra: dict[str, tuple[int, str]] = {}

    kho = json.loads((REPO / "_kq_edge_voices.json").read_text("utf-8"))
    ra["edge"] = (len({v["ShortName"] for v in kho}),
                  f"{len({v['Locale'].split('-')[0] for v in kho})} thứ tiếng")

    def _dem(ten: str, goi, ghi: str = "") -> None:
        try:
            ra[ten] = (len(goi()), ghi)
        except Exception as e:                                 # noqa: BLE001
            ra[ten] = (-1, f"{type(e).__name__}: {e}")

    from app.core import giong_ngoai, giong_vbee, giong_vieneu
    _dem("vieneu", lambda: giong_vieneu.danh_sach_giong(du_chua_tai=True),
         "giọng Việt dựng sẵn")
    _dem("ov", giong_ngoai.danh_sach_giong, "chỉ hiện khi máy có model 6,1 GB")
    _dem("vbee", giong_vbee.danh_sach_giong, "cần key trả tiền")

    from app.core import piper_tts
    ra["piper"] = (1, "3 giọng Việt tồn tại, 2 bị CẤM vì giấy phép "
                      f"(chỉ {piper_tts.TEN_MODEL} bán được)")

    # ElevenLabs: premade + giọng của tài khoản. GET /voices KHÔNG tiêu ký tự.
    try:
        ra["el"] = (len(D._eleven_voices()),
                    "có key" if D._eleven_available() else "CHƯA có key")
    except Exception as e:                                     # noqa: BLE001
        ra["el"] = (-1, f"{type(e).__name__}")

    from app.core import giong_chatter
    ra["chatter"] = (0, f"NHÂN BẢN từ mẫu, {len(giong_chatter.TIENG)} thứ "
                        "tiếng — KHÔNG có danh sách giọng dựng sẵn")
    return ra


def dang_lo() -> dict:
    from app.core import giong_bang as GB
    from app.core import dubbing
    from app.ui.thay_giong_dialog import giong_dung_duoc

    ds = giong_dung_duoc(dubbing.list_recap_voices())
    ma = {v for _n, v in ds if v}
    theo: dict[str, set] = {}
    for v in ma:
        theo.setdefault(GB.nguon(v), set()).add(v)
    return {"dong": len(ds), "ma": ma, "theo": theo}


def main() -> int:
    from app.core import giong_bang as GB
    ht = ho_tro()
    lo = dang_lo()
    bt = {v for v in lo["ma"] if "|" in v and GB.nguon(v) == GB.EDGE}
    print("=" * 78)
    print("MỖI NGUỒN HỖ TRỢ BAO NHIÊU  vs  COMBO ĐANG LỘ BAO NHIÊU")
    print("=" * 78)
    print(f"{'nguồn':10s} {'hỗ trợ':>7s} {'đang lộ':>8s}  ghi chú")
    print("-" * 78)
    for ng in ("edge", "vieneu", "ov", "piper", "chatter", "el", "vbee"):
        so_ht, ghi = ht.get(ng, (0, ""))
        co = lo["theo"].get(ng, set())
        n = len(co) - (len(bt) if ng == "edge" else 0)
        print(f"{GB.TEN_NGUON.get(ng, ng):10s} {so_ht:7d} {n:8d}  {ghi}")
    print("-" * 78)
    print(f"combo: {lo['dong']} dòng · {len(lo['ma'])} mã "
          f"(trong đó {len(bt)} là BIẾN THỂ cao độ, không phải giọng mới)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
