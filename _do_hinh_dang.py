# -*- coding: utf-8 -*-
"""ĐO: bật `response_format=json_object` thì model trả HÌNH DẠNG gì?

Quan trọng vì `_theo_nhan` của thay_giong đọc MẢNG [{"i":..,"t":..}]; nếu
json_object ép model bọc thành object thì bật nó là ĐỔI HÌNH DẠNG -> hỏng
đường lấy theo nhãn mà không một dòng báo.

Chạy: .venv\\Scripts\\python.exe -u _do_hinh_dang.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import llm                          # noqa: E402
from app.core import thay_giong as tg           # noqa: E402
from _do_json_dut import dung_prompt, nap_cau   # noqa: E402
from _do_tran3 import goi                       # noqa: E402


def mo_ta(d) -> str:
    if isinstance(d, list):
        return (f"LIST({len(d)}) phần tử đầu = "
                f"{json.dumps(d[0], ensure_ascii=False)[:120]}")
    if isinstance(d, dict):
        ks = list(d.keys())[:6]
        return (f"DICT({len(d)}) khoá đầu = {ks} · giá trị đầu = "
                f"{json.dumps(d[ks[0]], ensure_ascii=False)[:110] if ks else ''}")
    return f"{type(d).__name__}"


def main() -> int:
    cau, goc = nap_cau()
    p, s = dung_prompt(cau[:12], "vi", goc)
    MD = "openai/gpt-oss-120b"
    for nhan, jm in (("KHÔNG json_object", False), ("CÓ json_object", True)):
        for lan in (1, 2):
            try:
                from openai import OpenAI       # noqa: F401
                r = goi(MD, p, s, max_tokens=4096, json_mode=jm)
            except Exception as e:              # noqa: BLE001
                print(f"{nhan} lần {lan}: LỖI {str(e)[:120]}")
                continue
            # gọi lại để lấy raw: goi() không trả raw -> dựng lại bằng _extract
            print(f"{nhan} lần {lan}: len={r['len']} finish={r['fr']} "
                  f"parse={r['parse']}")
    # lấy RAW để nhìn hình dạng
    print("\n-- RAW (json_object) --")
    from openai import OpenAI
    from config import settings
    keys = settings.llm_keys_for("groq")
    for lan in range(3):
        cl = OpenAI(api_key=keys[(lan + 11) % len(keys)],
                    base_url="https://api.groq.com/openai/v1",
                    timeout=120, max_retries=1)
        try:
            resp = cl.chat.completions.create(
                model=MD, temperature=0.3, max_tokens=4096,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": s},
                          {"role": "user", "content": p}])
        except Exception as e:                  # noqa: BLE001
            print(f"  lần {lan+1}: LỖI {str(e)[:120]}")
            continue
        raw = resp.choices[0].message.content or ""
        print(f"  lần {lan+1}: {raw[:200]!r}")
        try:
            d = llm._extract_json(raw)
            print(f"           -> {mo_ta(d)}")
            bang = tg._theo_nhan(d, list(range(12)), "t")
            print(f"           -> _theo_nhan lấy được {len(bang)}/12 câu")
        except Exception as e:                  # noqa: BLE001
            print(f"           -> HỎNG {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
