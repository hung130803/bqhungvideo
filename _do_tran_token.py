# -*- coding: utf-8 -*-
"""ĐO: 3072 token đầu ra là TRẦN MẶC ĐỊNH của Groq hay do app đặt?

Gọi CÙNG prompt với `max_tokens` không đặt / đặt rõ, trên cả 3 model của dây
chuyền, in `finish_reason` + `completion_tokens` + chi tiết usage.

Chạy: .venv\\Scripts\\python.exe -u _do_tran_token.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import llm                    # noqa: E402
from config import settings               # noqa: E402
from _do_json_dut import dung_prompt, nap_cau   # noqa: E402


def goi(key: str, model: str, prompt: str, system: str,
        max_tokens=None, json_mode: bool = False) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1",
                    timeout=180, max_retries=1)
    kw: dict = {}
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
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
        llm._extract_json(raw)
        ok = "ĐẠT"
    except Exception:                      # noqa: BLE001
        ok = "HỎNG"
    return {"len": len(raw), "fr": getattr(ch, "finish_reason", None),
            "out": getattr(us, "completion_tokens", None),
            "inp": getattr(us, "prompt_tokens", None),
            "giay": time.time() - t0, "parse": ok}


def main() -> int:
    cau, goc = nap_cau()
    prompt, system = dung_prompt(cau, "vi", goc)
    keys = settings.llm_keys_for("groq")
    if not keys:
        print("không có key")
        return 2
    chuoi = llm.chuoi_model_groq()
    print(f"prompt {len(prompt)} ký tự · {len(cau)} câu\n")

    print("== A. KHÔNG đặt max_tokens (đúng như app hôm nay) ==")
    for i, md in enumerate(chuoi):
        try:
            r = goi(keys[i % len(keys)], md, prompt, system)
            print(f"  {md:24s} len={r['len']:5d} out_tok={r['out']} "
                  f"finish={r['fr']} parse={r['parse']} {r['giay']:.1f}s")
        except Exception as e:             # noqa: BLE001
            print(f"  {md:24s} LỖI: {str(e)[:140]}")

    print("\n== B. ĐẶT max_tokens=16000 ==")
    for i, md in enumerate(chuoi):
        try:
            r = goi(keys[(i + 3) % len(keys)], md, prompt, system,
                    max_tokens=16000)
            print(f"  {md:24s} len={r['len']:5d} out_tok={r['out']} "
                  f"finish={r['fr']} parse={r['parse']} {r['giay']:.1f}s")
        except Exception as e:             # noqa: BLE001
            print(f"  {md:24s} LỖI: {str(e)[:140]}")

    print("\n== C. max_tokens=16000 + response_format=json_object ==")
    for i, md in enumerate(chuoi):
        try:
            r = goi(keys[(i + 6) % len(keys)], md, prompt, system,
                    max_tokens=16000, json_mode=True)
            print(f"  {md:24s} len={r['len']:5d} out_tok={r['out']} "
                  f"finish={r['fr']} parse={r['parse']} {r['giay']:.1f}s")
        except Exception as e:             # noqa: BLE001
            print(f"  {md:24s} LỖI: {str(e)[:140]}")

    print("\n== D. hỏi /models: trần token từng model ==")
    import urllib.request
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {keys[0]}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
        for m in d.get("data", []):
            if m.get("id") in chuoi:
                print(f"  {m.get('id'):24s} ctx={m.get('context_window')} "
                      f"max_out={m.get('max_completion_tokens')}")
    except Exception as e:                 # noqa: BLE001
        print(f"  lỗi hỏi /models: {str(e)[:140]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
