"""BẢNG TỔNG 4 ARM — "ANH HÙNG ĐỔI Ô THÌ BỚT ĐƯỢC BAO NHIÊU GIÂY TIẾNG TRUNG".

Gom `_kq_bu_goc_that_*.json` (4 lượt chạy THẬT trên video gốc của anh Hùng,
cùng giọng `vnb:` nhân bản, cùng cách trộn `tach`, cùng che chữ + nhấn nhá)
thành một bảng đọc được.

**GHÉP CẶP TỚI ĐÂU, NÓI THẲNG:** bốn arm là bốn LƯỢT CHẠY RIÊNG, không phải một
lượt tách nhánh — LLM (bản dịch) và VieNeu (giọng) đều KHÔNG tiền định, nên số
câu và độ dài giọng mỗi lượt một khác. Riêng cặp BAT/TAT thì ghép cặp THEO CẤU
TẠO: `giay_bu` và `giay_trong` là hai nhánh của CÙNG một phép
`khoang_khong_giong` trong CÙNG lượt BAT, nên cột "bật -> dính bao nhiêu tiếng
Trung" và cột "tắt -> im bao nhiêu giây" so được thẳng với nhau.

    .venv\\Scripts\\python _ra_bang_bon_loi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

TEN = {"BAT": "MỤC 2 + bù BẬT  (ĐANG CHẠY)",
       "TAT": "MỤC 2 + bù TẮT",
       "MUC1": "MỤC 1 (không chỉnh hình)",
       "MUC3": "MỤC 3 (chỉnh hình + đọc ĐỀU)"}


def main() -> int:
    from app.core.thay_giong import probe_duration
    rows = []
    for a in ("BAT", "TAT", "MUC1", "MUC3"):
        p = REPO / f"_kq_bu_goc_that_{a}.json"
        if not p.exists():
            print(f"  (chưa có {p.name})")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if not d.get("ra"):
            print(f"  ({a} lỗi: {str(d.get('loi'))[:80]})")
            continue
        bu = d.get("bu_goc") or {}
        h = d.get("hinh") or {}
        try:
            dai = probe_duration(Path(d["ra"]))
        except Exception:                                   # noqa: BLE001
            dai = 0.0
        cb = d.get("chep_manh_bu") or {}
        rows.append({
            "arm": a, "ten": TEN[a], "giay_video": round(dai, 2),
            "giay_bu": bu.get("giay_bu", 0.0), "so_bu": bu.get("so_bu", 0),
            "giay_trong": bu.get("giay_trong", 0.0),
            "so_trong": bu.get("so_trong", 0), "bo_qua": bu.get("bo_qua", 0),
            "phan_tram_bu": (round(100.0 * bu.get("giay_bu", 0.0) / dai, 2)
                             if dai else 0.0),
            "k_dung": h.get("k_dung"), "cham_tran": h.get("cham_tran"),
            "tempo_max": (d.get("khop") or {}).get("tempo_max"),
            "nhan_ngon_ngu_manh_bu": cb.get("nhan_ngon_ngu"),
            "ty_le_han_manh_bu": cb.get("ti_le_han"),
            "giay_chay": d.get("giay_chay"),
        })

    w = 34
    print("=" * 112)
    print(f"| {'arm':<{w}} | {'giây video':>10} | {'GIÂY BÙ':>8} | "
          f"{'mảnh':>5} | {'% video':>8} | {'im nếu TẮT':>11} | {'k hình':>7} |")
    print("-" * 112)
    for r in rows:
        print(f"| {r['ten']:<{w}} | {r['giay_video']:>10.2f} | "
              f"{r['giay_bu']:>8.2f} | {r['so_bu']:>5} | "
              f"{r['phan_tram_bu']:>7.2f}% | {r['giay_trong']:>11.2f} | "
              f"{str(r['k_dung']):>7} |")
    print("=" * 112)
    for r in rows:
        print(f"  {r['arm']:<5} tempo_max {str(r['tempo_max']):<7} · chạm trần "
              f"{r['cham_tran']} · mảnh bù chép ra: "
              f"{r['nhan_ngon_ngu_manh_bu']} "
              f"(Hán {r['ty_le_han_manh_bu']}) · {r['giay_chay']}s")

    b = next((r for r in rows if r["arm"] == "BAT"), None)
    if b:
        print("\n  ĐÁNH ĐỔI của chính ô anh Hùng đang dùng (MỤC 2), ghép cặp "
              "theo cấu tạo trong CÙNG lượt:")
        print(f"    · bù BẬT (mặc định) -> **{b['giay_bu']} giây tiếng Trung** "
              f"chèn vào {b['so_bu']} chỗ = {b['phan_tram_bu']}% thời lượng")
        print(f"    · bù TẮT            -> **{b['giay_trong']} giây IM** ở "
              f"{b['so_trong']} chỗ ({b['bo_qua']} chỗ gốc cũng im)")
        for r in rows:
            if r["arm"] in ("MUC1", "MUC3"):
                d = b["giay_bu"] - r["giay_bu"]
                print(f"    · ĐỔI sang {r['ten']:<32} -> {r['giay_bu']:>6.2f} "
                      f"giây (bớt {d:>6.2f} s = "
                      f"{100.0*d/b['giay_bu'] if b['giay_bu'] else 0:.1f}%)")

    (REPO / "_kq_bang_bon_loi.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n=> {REPO / '_kq_bang_bon_loi.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
