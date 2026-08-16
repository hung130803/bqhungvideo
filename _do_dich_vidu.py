# -*- coding: utf-8 -*-
"""IN CÂU CỤ THỂ TRƯỚC/SAU từ `_do_dich_ab.json` — để NGƯỜI TỰ ĐỌC.

Bảng số nói được "tốt hơn bao nhiêu", nó KHÔNG nói được "đọc lên có xuôi
không". Repo này đã dính đúng loại bẫy đó nhiều lần (mức mờ 0,40 mọi thước
máy bảo sạch mà mắt vẫn đọc được chữ). Nên mọi kết luận về chất lượng dịch
phải kèm câu thật, và người đọc tự phán.

  .venv\\Scripts\\python -u _do_dich_vidu.py            # câu MỚI khác MỐC nhiều nhất
  BQ_LUOT=1 BQ_SO=12 .venv\\Scripts\\python -u _do_dich_vidu.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

from app.ai.cham_dich import am_tiet_viet                # noqa: E402
from app.ai.dich import ngan_sach, giay_doc              # noqa: E402

LUOT = int(os.environ.get("BQ_LUOT", "0"))
SO = int(os.environ.get("BQ_SO", "14"))


def main() -> int:
    ab = json.loads((REPO / "_do_dich_ab.json").read_text(encoding="utf-8"))
    cau = json.loads((REPO / "_do_dich_cache.json").read_text(
        encoding="utf-8"))["cau"]
    m = ab[LUOT]
    ten = [t for t in ("MỐC", "MỚI", "MỚI+VD") if t in m]
    print("=" * 78)
    print(f"CÂU CỤ THỂ — lượt {LUOT + 1}, các nhánh: {', '.join(ten)}")
    print("=" * 78)

    bd = {t: m[t]["ban_dich"] for t in ten}
    cham = {t: m[t]["cau_cham"] for t in ten}

    def diem(t, i):
        c = cham[t][i]
        return (f"đạt={'CÓ' if c['dat'] else 'KHÔNG'} "
                f"nghia={c.get('nghia')} xuoi={c.get('xuoi')} "
                f"noi={c.get('noi')} tron={c.get('tron')}"
                + (f" LỖI-MÁY={c['loi']}" if c["loi"] else "")
                + (f" THUẬT-NGỮ={c['thuat_ngu']}" if c["thuat_ngu"] else ""))

    # xếp theo mức KHÁC BIỆT: câu mà 2 nhánh đánh giá khác nhau đứng trước
    thu_tu = sorted(
        range(len(cau)),
        key=lambda i: -(abs((cham["MỐC"][i].get("nghia") or 0)
                            - (cham["MỚI"][i].get("nghia") or 0))
                        + abs(len(bd["MỐC"][i]) - len(bd["MỚI"][i])) / 20.0)
        if "MỚI" in bd else 0)

    for i in thu_tu[:SO]:
        c = cau[i]
        g = float(c["end"]) - float(c["start"])
        ns = ngan_sach(g, c["text"])
        print(f"\n#{i}  khung {g:.2f}s · gốc {ns['do_goc']} chữ Hán · "
              f"ngân sách ~{ns['dich']} chữ (ép {ns['ep_min']}-{ns['ep_max']})")
        print(f"   GỐC   : {c['text']}")
        for t in ten:
            a = am_tiet_viet(bd[t][i])
            print(f"   {t:<7}: {bd[t][i]}")
            print(f"           {a} chữ · đọc ~{giay_doc(a):.2f}s "
                  f"= {giay_doc(a)/g:.2f}× khung · {diem(t, i)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
