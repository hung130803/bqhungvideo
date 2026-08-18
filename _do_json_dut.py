# -*- coding: utf-8 -*-
"""ĐO: vì sao `complete_json` báo "không phải JSON hợp lệ" ở đường Thay giọng.

Bắt CHUỖI THẬT model trả về + `finish_reason` + `usage`, chạy nhiều lượt để
biết TỈ LỆ hỏng (lỗi chập chờn: cùng lượt 1 video xong 1 video hỏng).

Dùng prompt Y HỆT `thay_giong._dich_loat` (dựng lại từ chính hằng số của
module, không chép tay) trên câu THẬT trong `_do_dich_cache.json`.

Chạy: .venv\\Scripts\\python.exe -u _do_json_dut.py [so_luot]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import llm                    # noqa: E402
from app.core import thay_giong as tg     # noqa: E402
from config import settings               # noqa: E402

SO_LUOT = int(sys.argv[1]) if len(sys.argv) > 1 else 6
KHO = Path(__file__).resolve().parent / "_do_dich_cache.json"


def nap_cau() -> tuple[list[dict], str]:
    d = json.loads(KHO.read_text(encoding="utf-8"))
    return d["cau"], str(d.get("language") or "zh")


def dung_prompt(cau: list[dict], dich_sang: str, goc_ma: str) -> tuple[str, str]:
    """Dựng ĐÚNG prompt của `_dich_loat` vòng 1 (mọi câu còn thiếu)."""
    ten_dich = tg._ten_nn(dich_sang)
    system = ("Bạn là chuyên gia dịch THAY TIẾNG cho video. Dịch tự nhiên như "
              "VĂN NÓI, đúng ý, đúng cảm xúc. CHỈ trả JSON thuần.")
    con = list(range(len(cau)))
    items = []
    for i in con:
        c = cau[i]
        dur = max(0.1, float(c["end"]) - float(c["start"]))
        items.append(f'#{i} [{dur:.1f} giây]: "{c["text"][:400]}"')
    prompt = (
        f"Dịch các câu thoại sau từ {tg._ten_nn(goc_ma)} sang {ten_dich}.\n"
        f"{chr(10).join(items)}\n\n"
        "QUY TẮC:\n"
        f"- Dịch sang {ten_dich}, văn NÓI tự nhiên — viết như người thật "
        "đang NÓI trong video, KHÔNG dịch máy móc từng chữ.\n"
        "- Giữ giọng điệu của câu gốc (kể chuyện, giới thiệu, cảm thán).\n"
        "- ĐỌC LÊN phải lọt khung [số giây] của câu đó — dài quá thì lược "
        "từ đệm, GIỮ Ý CHÍNH.\n"
        "- KHÔNG thêm chú thích, không phiên âm.\n"
        + tg._LUAT_KHONG_SOT + "\n"
        f"- Trả MẢNG JSON {len(con)} đối tượng "
        '{"i": <đúng số sau dấu #>, "t": "<bản dịch>"}. '
        "BẮT BUỘC đủ MỌI số #, KHÔNG bỏ câu nào, KHÔNG gộp hai câu."
    )
    return prompt, system


def goi_tho(key: str, model: str, prompt: str, system: str,
            temperature: float = 0.3) -> dict:
    """Gọi Groq y hệt `_call_once` nhưng GIỮ LẠI finish_reason + usage."""
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1",
                    timeout=120, max_retries=1)
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": prompt}]
    t0 = time.time()
    resp = client.chat.completions.create(model=model, messages=msgs,
                                          temperature=temperature)
    ch = resp.choices[0]
    us = getattr(resp, "usage", None)
    return {
        "content": ch.message.content or "",
        "finish_reason": getattr(ch, "finish_reason", None),
        "prompt_tokens": getattr(us, "prompt_tokens", None),
        "completion_tokens": getattr(us, "completion_tokens", None),
        "giay": time.time() - t0,
        "model": model,
    }


def quanh(text: str, vt: int, ban_kinh: int = 100) -> str:
    a = max(0, vt - ban_kinh)
    b = min(len(text), vt + ban_kinh)
    return ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")


def main() -> int:
    cau, goc_ma = nap_cau()
    prompt, system = dung_prompt(cau, "vi", goc_ma)
    keys = settings.llm_keys_for("groq")
    chuoi = llm.chuoi_model_groq()
    print(f"câu THẬT: {len(cau)} · gốc={goc_ma} · prompt {len(prompt)} ký tự")
    print(f"key groq: {len(keys)} · dây chuyền model: {chuoi}")
    if not keys:
        print("KHÔNG có key groq -> dừng")
        return 2

    md = chuoi[0]
    hong = 0
    dai: list[int] = []
    ly_do: dict[str, int] = {}
    mau_hong = None
    for n in range(SO_LUOT):
        key = keys[n % len(keys)]
        try:
            r = goi_tho(key, md, prompt, system)
        except Exception as e:                     # noqa: BLE001
            print(f"[{n+1}] LỖI GỌI: {str(e)[:160]}")
            continue
        raw = r["content"]
        dai.append(len(raw))
        fr = str(r["finish_reason"])
        ly_do[fr] = ly_do.get(fr, 0) + 1
        try:
            data = llm._extract_json(raw)
            ok = isinstance(data, (list, dict))
            n_pt = len(data) if isinstance(data, (list, dict)) else 0
            print(f"[{n+1}] ĐẠT  len={len(raw):5d} finish={fr:8s} "
                  f"out_tok={r['completion_tokens']} phần_tử={n_pt} "
                  f"{r['giay']:.1f}s")
        except Exception as e:                     # noqa: BLE001
            hong += 1
            ok = False
            print(f"[{n+1}] HỎNG len={len(raw):5d} finish={fr:8s} "
                  f"out_tok={r['completion_tokens']} {r['giay']:.1f}s")
            print(f"      lỗi: {type(e).__name__}: {e}")
            vt = getattr(e, "pos", len(raw))
            print(f"      quanh vị trí {vt}: {quanh(raw, vt)!r}")
            if mau_hong is None:
                mau_hong = raw
        _ = ok
    print()
    print(f"TỔNG: {SO_LUOT} lượt · HỎNG {hong} "
          f"({hong*100.0/max(1,len(dai)):.1f}%)")
    if dai:
        print(f"độ dài trả về: min={min(dai)} max={max(dai)} "
              f"TB={sum(dai)//len(dai)}")
    print(f"finish_reason: {ly_do}")
    if mau_hong is not None:
        p = Path(__file__).resolve().parent / "_do_json_dut_mau.txt"
        p.write_text(mau_hong, encoding="utf-8")
        print(f"đã ghi mẫu HỎNG ra {p.name} ({len(mau_hong)} ký tự)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
