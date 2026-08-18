# -*- coding: utf-8 -*-
"""ĐO SAU BẢN VÁ: tỉ lệ hỏng của ĐÚNG đường app đi (`thay_giong._dich_loat`).

Không dựng lại prompt bằng tay nữa — gọi THẲNG `_dich_loat` để đo cả chuỗi
`complete_json` -> `complete_text` -> `_call_once` -> `_extract_json` -> vòng
đòi lại nhãn thiếu.

Chạy: .venv\\Scripts\\python.exe -u _do_json_sau.py [so_luot]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import llm                          # noqa: E402
from app.core import thay_giong as tg           # noqa: E402
from config import settings                     # noqa: E402
from _do_json_dut import nap_cau                # noqa: E402

SO_LUOT = int(sys.argv[1]) if len(sys.argv) > 1 else 6


def main() -> int:
    cau, goc = nap_cau()
    if not settings.llm_keys_for("groq"):
        print("không có key groq")
        return 2
    print(f"{len(cau)} câu THẬT · gốc={goc} -> vi · "
          f"model={llm.chuoi_model_groq()[0]}")
    print(f"max_tokens app xin = {llm.max_tokens_groq('x' * 2200, 'y' * 110)} "
          f"(prompt 50 câu)\n")
    hong = 0
    con_goc = 0
    for n in range(SO_LUOT):
        t0 = time.time()
        try:
            ra = tg._dich_loat(cau, "vi", goc)
        except Exception as e:                  # noqa: BLE001
            hong += 1
            print(f"[{n+1}] HỎNG {type(e).__name__}: {str(e)[:150]}")
            continue
        # câu nào KHÔNG dịch được thì `_dich_loat` trả lại nguyên câu gốc
        giu = sum(1 for i, c in enumerate(cau) if ra[i] == c["text"])
        con_goc += giu
        print(f"[{n+1}] ĐẠT  {len(ra)}/{len(cau)} câu · giữ nguyên gốc={giu} · "
              f"{time.time()-t0:.1f}s · ví dụ: {ra[0][:60]!r}")
    print()
    print(f"TỔNG: {SO_LUOT} lượt · HỎNG {hong} "
          f"({hong*100.0/SO_LUOT:.1f}%) · câu còn nguyên tiếng gốc "
          f"{con_goc} / {SO_LUOT*len(cau)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
