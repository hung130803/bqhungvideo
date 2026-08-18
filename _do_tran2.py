# -*- coding: utf-8 -*-
"""ĐO 2: trần `max_tokens` an toàn (không 413) + tác dụng của `reasoning_effort`
+ `response_format=json_object` có được model nhận không.

Mỗi phép đo dùng KEY KHÁC NHAU (mỗi key = 1 org, hạn mức riêng) để 429/413 của
phép trước không làm bẩn phép sau.

Chạy: .venv\\Scripts\\python.exe -u _do_tran2.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import llm                    # noqa: E402
from config import settings               # noqa: E402
from _do_json_dut import dung_prompt, nap_cau   # noqa: E402

_KEYS = settings.llm_keys_for("groq")
_I = {"n": 0}


def key_ke() -> str:
    k = _KEYS[_I["n"] % len(_KEYS)]
    _I["n"] += 1
    return k


def goi(model: str, prompt: str, system: str, max_tokens=None,
        json_mode: bool = False, effort=None) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=key_ke(), base_url="https://api.groq.com/openai/v1",
                    timeout=180, max_retries=1)
    kw: dict = {}
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
    if effort is not None:
        kw["reasoning_effort"] = effort
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": prompt}],
        temperature=0.3, **kw)
    ch = resp.choices[0]
    us = getattr(resp, "usage", None)
    raw = ch.message.content or ""
    try:
        d = llm._extract_json(raw)
        parse = f"ĐẠT({len(d) if hasattr(d, '__len__') else '?'})"
    except Exception:                      # noqa: BLE001
        parse = "HỎNG"
    return {"len": len(raw), "fr": getattr(ch, "finish_reason", None),
            "out": getattr(us, "completion_tokens", None),
            "giay": time.time() - t0, "parse": parse}


def thu(nhan: str, **kw) -> None:
    try:
        r = goi(**kw)
        print(f"  {nhan:38s} len={r['len']:5d} out_tok={r['out']:5} "
              f"finish={str(r['fr']):8s} parse={r['parse']:9s} {r['giay']:5.1f}s")
    except Exception as e:                 # noqa: BLE001
        m = str(e)
        ma = "413" if "413" in m else ("429" if "429" in m else
                                       ("400" if "400" in m else "???"))
        print(f"  {nhan:38s} LỖI {ma}: {m[:110]}")


def main() -> int:
    cau, goc = nap_cau()
    prompt, system = dung_prompt(cau, "vi", goc)
    if not _KEYS:
        print("không có key")
        return 2
    print(f"key groq: {len(_KEYS)} · prompt {len(prompt)} ký tự · {len(cau)} câu\n")
    MD = "openai/gpt-oss-120b"

    print("== A. dò TRẦN max_tokens (model chính) ==")
    for mt in (2048, 3072, 4096, 6144, 8192, 10240, 12288):
        thu(f"max_tokens={mt}", model=MD, prompt=prompt, system=system,
            max_tokens=mt)

    print("\n== B. reasoning_effort (max_tokens=8192) ==")
    for ef in (None, "none", "low", "medium"):
        thu(f"effort={ef}", model=MD, prompt=prompt, system=system,
            max_tokens=8192, effort=ef)

    print("\n== C. reasoning_effort=none, KHÔNG đặt max_tokens ==")
    thu("effort=none, mac dinh", model=MD, prompt=prompt, system=system,
        effort="none")

    print("\n== D. response_format=json_object ==")
    for md in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"):
        thu(f"json_object {md}", model=md, prompt=prompt, system=system,
            max_tokens=4096, json_mode=True)

    print("\n== E. CHIA NHỎ: 25 câu/lượt, effort=none, max_tokens=4096 ==")
    for lo in (0, 25):
        p2, s2 = dung_prompt(cau[lo:lo + 25], "vi", goc)
        thu(f"câu {lo}-{lo+24}", model=MD, prompt=p2, system=s2,
            max_tokens=4096, effort="none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
