# -*- coding: utf-8 -*-
"""HIỆU CHUẨN bộ ƯỚC LƯỢNG token (không gọi mạng).

Mốc ĐO THẬT lấy từ `_do_tran3.py` (Groq trả `usage.prompt_tokens`):
  10 câu -> 551 · 25 câu -> 874 · 50 câu -> 1413 (và 1441 khi bật json_object,
  chênh do Groq thêm chỉ dẫn schema).

Bộ ước lượng phải LUÔN >= số thật (ước hụt = đặt max_tokens quá cao = 413),
nhưng đừng phồng quá (phồng = cắt bớt chỗ trả lời một cách vô cớ).

Chạy: .venv\\Scripts\\python.exe -u _do_uoc_token.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _do_json_dut import dung_prompt, nap_cau      # noqa: E402

THAT = {10: 551, 25: 874, 50: 1413}


def dem_cjk(s: str) -> int:
    return sum(1 for ch in s if "⺀" <= ch <= "鿿"
               or "가" <= ch <= "힣"
               or "豈" <= ch <= "﫿"
               or "぀" <= ch <= "ヿ")


def uoc(s: str, he_cjk: float, he_khac: float) -> int:
    c = dem_cjk(s)
    return int(c * he_cjk + (len(s) - c) / he_khac) + 8


def main() -> int:
    cau, goc = nap_cau()
    print(f"{'n':>4} {'ký tự':>7} {'CJK':>6} {'THẬT':>6} "
          f"{'ước':>6} {'tỉ lệ ước/thật':>16}")
    tot = None
    for he_cjk, he_khac in ((1.0, 2.6), (1.1, 2.6), (1.0, 2.2), (1.2, 2.4),
                            (1.1, 2.2), (1.0, 2.0)):
        dong = []
        ok = True
        ty_max = 0.0
        for n, that in THAT.items():
            p, s = dung_prompt(cau[:n], "vi", goc)
            t = p + s
            u = uoc(t, he_cjk, he_khac)
            ty = u / that
            ty_max = max(ty_max, ty)
            if u < that:
                ok = False
            dong.append((n, len(t), dem_cjk(t), that, u, ty))
        trang = "ĐẠT" if ok else "HỤT (nguy hiểm)"
        print(f"-- hệ CJK={he_cjk} khác=len/{he_khac} -> {trang}")
        for n, l, c, that, u, ty in dong:
            print(f"{n:>4} {l:>7} {c:>6} {that:>6} {u:>6} {ty:>15.2f}x")
        if ok and (tot is None or ty_max < tot[2]):
            tot = (he_cjk, he_khac, ty_max)
    print()
    if tot:
        print(f"CHỌN: he_cjk={tot[0]} · khác=len/{tot[1]} · "
              f"phồng nhiều nhất {tot[2]:.2f}x")
    else:
        print("KHÔNG bộ nào an toàn -> phải nới hệ số")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
