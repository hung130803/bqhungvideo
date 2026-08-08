# -*- coding: utf-8 -*-
r"""ĐẾM KEY GROQ CÒN SỐNG — câu 4 của anh Hùng ("đếm lượt Groq + key còn sống").

    .venv\Scripts\python _ra_key_groq.py [--thu-that]

MẶC ĐỊNH chỉ ĐẾM + soi trạng thái (không gọi mạng). `--thu-that` thì gọi 1 lượt
`/models` cho TỪNG key để biết key nào chết thật (401/403) hay chỉ hết lượt (429).

QUY TẮC SẮT: key đọc từ `%LOCALAPPDATA%\BQHungVideo\.env`, truyền qua **BIẾN MÔI
TRƯỜNG**, KHÔNG ghi ra file, KHÔNG in ra màn hình (chỉ in 4 ký tự cuối).
LƯU Ý: dùng SDK OpenAI, ĐỪNG dùng urllib — Cloudflare trả 403 error 1010 vì
User-Agent (bài học cổng 22).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="ra_key_"))
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "t.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "s.ini"))

_env = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo" / ".env"
if _env.exists():
    for ln in _env.read_text(encoding="utf-8", errors="replace").splitlines():
        k, _, v = ln.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and v:
            os.environ.setdefault(k, v)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thu-that", action="store_true",
                    help="gọi /models THẬT cho từng key (tốn 1 lượt/key)")
    a = ap.parse_args()

    from config import settings
    keys = settings.groq_keys()
    print(f"nguồn key: {_env}  ({'CÓ' if _env.exists() else 'KHÔNG CÓ'})")
    print(f"tổng key nạp được: {len(keys)}")
    if not keys:
        print("DỪNG: 0 key -> app sẽ tụt về whisper MÁY (chậm hàng chục lần).")
        return 2

    from app.ai import llm
    san = llm.soonest_ready_wait("groq", keys)
    print(f"key đang bị khoá (cooldown)? soonest_ready_wait = {san} "
          f"(None = KHÔNG key nào bị khoá)")

    ket = {"tong": len(keys), "cooldown": san, "song": None, "chet": []}
    if a.thu_that:
        from openai import OpenAI     # SDK, KHÔNG urllib (Cloudflare 403 1010)
        song = 0
        chet = []
        for i, k in enumerate(keys):
            try:
                c = OpenAI(api_key=k, base_url="https://api.groq.com/openai/v1",
                           timeout=25.0)
                n = len(c.models.list().data)
                song += 1
                print(f"  key #{i+1:02d} …{k[-4:]}  SỐNG ({n} model)")
            except Exception as e:      # noqa: BLE001
                m = f"{type(e).__name__}: {e}"[:90]
                chet.append(f"…{k[-4:]}: {m}")
                print(f"  key #{i+1:02d} …{k[-4:]}  LỖI  {m}")
            sys.stdout.flush()
        print(f"\n=> {song}/{len(keys)} key SỐNG · {len(chet)} lỗi")
        ket["song"] = song
        ket["chet"] = chet
    (REPO / "_ket__ra_key_groq.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
