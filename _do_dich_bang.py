# -*- coding: utf-8 -*-
"""BẢNG SO SÁNH MỌI ARM — chạy thước lên từng arm rồi in một bảng duy nhất.

3 cột số, đọc theo đúng thứ tự này:
  · **LỆCH BẬC %** — bản dịch câu #i thật ra là câu #i+k. Đây là cột QUYẾT
    ĐỊNH: nó là thứ người xem nghe ra thành "linh tinh, không hiểu gì".
  · **điểm trung thành 1-5** (model chấm KHÁC model dịch) + **chrF dịch ngược**
  · **F/E** — rớt câu · lẫn ngôn ngữ (thuần code).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _dich_do_chung as C                                    # noqa: E402
import _do_dich_benh as B                                     # noqa: E402
import _do_dich_lechbac as L                                  # noqa: E402


def mot(ten: str, lai_lech=False, lai_benh=False) -> dict:
    pl = C.HOP / ("lech_%s.json" % ten)
    pb = C.HOP / ("benh_%s.json" % ten)
    if lai_lech or not pl.exists():
        L.chay(ten)
    if lai_benh or not pb.exists():
        B.chay(ten)
    lech = json.loads(pl.read_text(encoding="utf-8"))
    benh = json.loads(pb.read_text(encoding="utf-8"))
    kq = json.loads((C.HOP / (ten + ".json")).read_text(encoding="utf-8"))
    return {"ten": ten, "lech": lech, "benh": benh, "kq": kq}


def bang(tens) -> None:
    rows = []
    for t in tens:
        try:
            rows.append(mot(t))
        except Exception as e:                                # noqa: BLE001
            print("BỎ QUA %s: %s" % (t, e))
    print()
    print("%-30s %6s %7s %7s %6s %6s %5s %5s %6s %6s"
          % ("arm", "câu", "LỆCH%", "(dò/n)", "điểm", "chrF", "F", "E",
             "lượt", "giây"))
    print("-" * 100)
    for r in rows:
        le, be, kq = r["lech"], r["benh"], r["kq"]
        print("%-30s %6d %6.1f%% %7s %6.2f %6.1f %5d %5d %6d %6.0f"
              % (r["ten"], be["so_cau"], le["ty_le_lech"],
                 "%d/%d" % (le["do_duoc"], le["so_cau"]),
                 be["diem_tb"], be["chrf_tb"],
                 len(kq["F_tra_nguyen_goc"]) + len(kq["F_rong"]),
                 sum(len(v) for v in (kq.get("E_he_chu_la") or {}).values()),
                 (kq.get("goi") or {}).get("so_luot", 0), kq.get("giay", 0)))
    print()
    print("%-30s %6s %6s %6s %6s %6s %6s %6s"
          % ("arm", "A%", "B%", "C%", "D%", "E%", "F%", "LÀNH%"))
    print("-" * 80)
    for r in rows:
        t = r["benh"]["ty_le"]
        print("%-30s %6s %6s %6s %6s %6s %6s %6s"
              % (r["ten"], t["A"], t["B"], t["C"], t["D"], t["E"], t["F"],
                 t["lanh"]))
    print()
    for r in rows:
        print("%-30s mã lỗi LLM chấm: %s"
              % (r["ten"], r["benh"]["loi_theo_ma"]))


if __name__ == "__main__":
    bang(sys.argv[1:])
