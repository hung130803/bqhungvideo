# -*- coding: utf-8 -*-
"""ĐO 3: chốt ràng buộc THẬT của trần token + json_object + chia nhỏ.

Câu hỏi:
  A. Lời lỗi 413 nói ĐÍCH DANH giới hạn là gì (in NGUYÊN VĂN).
  B. `prompt_tok + max_tokens <= ?` — dò bằng prompt DÀI và prompt NGẮN.
  C. `reasoning_effort=low` có nhường chỗ cho phần trả lời không.
  D. `response_format=json_object` trên từng model của dây chuyền (key sạch).
  E. Chia nhỏ 25 câu/lượt thì cần bao nhiêu token.

Chạy: .venv\\Scripts\\python.exe -u _do_tran3.py
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
            "inp": getattr(us, "prompt_tokens", None),
            "giay": time.time() - t0, "parse": parse}


def thu(nhan: str, **kw):
    try:
        r = goi(**kw)
        print(f"  {nhan:34s} in_tok={r['inp']:5} out_tok={r['out']:5} "
              f"len={r['len']:5d} finish={str(r['fr']):8s} "
              f"parse={r['parse']:9s} {r['giay']:5.1f}s")
        return r
    except Exception as e:                 # noqa: BLE001
        print(f"  {nhan:34s} LỖI: {str(e)[:200]}")
        return None


def main() -> int:
    cau, goc = nap_cau()
    prompt, system = dung_prompt(cau, "vi", goc)
    if not _KEYS:
        return 2
    MD = "openai/gpt-oss-120b"
    print(f"key={len(_KEYS)} · prompt {len(prompt)} ký tự · {len(cau)} câu\n")

    print("== A. NGUYÊN VĂN lời lỗi 413 ==")
    try:
        goi(MD, prompt, system, max_tokens=12288)
        print("  (không ra 413)")
    except Exception as e:                 # noqa: BLE001
        print("  " + str(e)[:600])
        print(f"  is_too_large_error() -> {llm.is_too_large_error(str(e))}")
        print(f"  is_rate_limit_error() -> {llm.is_rate_limit_error(str(e))}")

    print("\n== B. prompt NGẮN (10 câu) thì trần max_tokens nới ra không ==")
    p10, s10 = dung_prompt(cau[:10], "vi", goc)
    for mt in (6144, 7168, 8192):
        thu(f"10 câu · max_tokens={mt}", model=MD, prompt=p10, system=s10,
            max_tokens=mt)

    print("\n== C. reasoning_effort với max_tokens=4096 (50 câu) ==")
    for ef in (None, "low", "medium"):
        thu(f"effort={ef}", model=MD, prompt=prompt, system=system,
            max_tokens=4096, effort=ef)

    print("\n== D. json_object từng model (max_tokens=4096) ==")
    for md in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"):
        for lan in (1, 2):
            thu(f"{md} lần {lan}", model=md, prompt=prompt, system=system,
                max_tokens=4096, json_mode=True)

    print("\n== E. chia nhỏ 25 câu/lượt (max_tokens=4096) ==")
    for lo in (0, 25):
        p2, s2 = dung_prompt(cau[lo:lo + 25], "vi", goc)
        thu(f"câu {lo}-{lo+24}", model=MD, prompt=p2, system=s2,
            max_tokens=4096)
    return 0


if __name__ == "__main__":
    sys.exit(main())
