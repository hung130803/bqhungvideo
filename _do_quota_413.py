# -*- coding: utf-8 -*-
"""HAI CHỐT PHẢI KIỂM TRƯỚC KHI TĂNG SỐ LƯỢT GỌI:

1. **413 là lỗi CỦA YÊU CẦU, KHÔNG được phạt key.** Bẫy này từng khoá cả 38
   key trong 120 giây. Nhiều-pass = nhiều yêu cầu = nhiều cơ hội chạm 413.
2. **NGÂN SÁCH THẬT của bể key** — không chỉ TPM 8.000/phút mà còn **TPD
   (token mỗi NGÀY)**. Nhân nhiều-pass lên 200-300 kênh thì TPD mới là trần
   thật, và nó KHÔNG có trong bất kỳ ghi chép nào của repo.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx                                                  # noqa: E402
from app.ai import llm                                        # noqa: E402
from config import settings                                   # noqa: E402

URL = "https://api.groq.com/openai/v1/chat/completions"
MD = "openai/gpt-oss-120b"


def goi(key: str, noi_dung: str, max_tokens: int):
    return httpx.post(URL, headers={"Authorization": "Bearer " + key},
                      json={"model": MD,
                            "messages": [{"role": "user", "content": noi_dung}],
                            "max_tokens": max_tokens}, timeout=60)


def main() -> None:
    ks = settings.groq_keys()
    con, het = [], []
    for i, k in enumerate(ks):
        try:
            r = goi(k, "hi", 1)
        except Exception:                                     # noqa: BLE001
            het.append((i, "MANG"))
            continue
        if r.status_code == 200:
            con.append((i, r.headers.get("x-ratelimit-remaining-tokens")))
        else:
            m = re.search(r"(TPD|TPM|RPD|RPM)", r.text or "")
            het.append((i, m.group(1) if m else str(r.status_code)))
    print("BỂ KEY (%s): CÒN DÙNG ĐƯỢC %d/%d" % (MD, len(con), len(ks)))
    loai = {}
    for _i, t in het:
        loai[t] = loai.get(t, 0) + 1
    print("   key HẾT: %d · lý do: %s" % (len(het), loai))
    if con:
        print("   token/phút còn lại của 5 key đầu:", [x for _i, x in con[:5]])

    if not con:
        print("KHÔNG CÒN KEY NÀO ĐỂ THỬ 413 — bỏ qua (ghi thẳng, không bịa).")
        return
    truoc = len(dict(llm.phat_key() or {}))
    k = ks[con[0][0]]
    r = goi(k, "x" * 4000, 8192)
    s = r.text or ""
    print("THỬ 413 (prompt ~1.000 token + max_tokens 8192):")
    print("   status=%s · is_too_large_error=%s · is_rate_limit_error=%s"
          % (r.status_code, llm.is_too_large_error(s),
             llm.is_rate_limit_error(s)))
    print("   ", s[:220].replace("\n", " "))
    sau = len(dict(llm.phat_key() or {}))
    print("   key bị khoá: %d -> %d · %s"
          % (truoc, sau, "KHÔNG PHẠT KEY (ĐÚNG)" if sau == truoc
             else "CÓ PHẠT KEY (SAI)"))


if __name__ == "__main__":
    main()
