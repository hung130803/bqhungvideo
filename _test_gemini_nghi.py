# -*- coding: utf-8 -*-
"""CỔNG 113 — GEMINI: PHẦN "NGHĨ" CÓ TRẦN, ĐƯỢC ĐẾM, KHÔNG XẾP HÀNG 1 LƯỢT.

Đo 06/11/2026 trên key thật: lời gọi chọn đoạn qua SDK cũ không có trần nghĩ ->
"nghĩ" 7.676 token + trả lời 309 = sát trần 8.000; phần nghĩ tính tiền nhưng SDK
không đếm (báo chi phí thấp hơn thật); SDK dùng cấu hình toàn cục nên phải giữ
_GEMINI_LOCK -> cả máy chỉ gọi được 1 lượt. Không gọi mạng, không tốn lượt.
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
TMP = tempfile.mkdtemp(prefix="bq_test_gem_")
os.environ["BQ_DATA_DIR"] = TMP
os.environ["BQ_DB_PATH"] = os.path.join(TMP, "s.db")
import requests  # noqa: E402

from app.ai import llm  # noqa: E402
from config import settings  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, ct=""):
    global DAT, HONG
    DAT, HONG = DAT + bool(dk), HONG + (not dk)
    print("  ĐẠT " if dk else "  HỎNG", ten, ct)


class Resp:
    ok = True
    status_code = 200

    def __init__(self, text="ok", finish="STOP"):
        self.text, self.finish = text, finish

    def json(self):
        return {"candidates": [{"finishReason": self.finish, "content": {"parts": [
            {"text": "đang nghĩ", "thought": True}, {"text": self.text}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20,
                              "thoughtsTokenCount": 3000}}


SO = []
DANG = [0, 0]
KHOA = threading.Lock()


def gia_post(url, headers=None, json=None, timeout=None, allow_redirects=None):
    SO.append(json)
    with KHOA:
        DANG[0] += 1
        DANG[1] = max(DANG)
    time.sleep(.15)
    with KHOA:
        DANG[0] -= 1
    return Resp('{"a":1}' if "responseMimeType" in json["generationConfig"] else "chữ")


requests.post = gia_post
settings.GEMINI_MODEL = "gemini-2.5-flash"

print("CA 1: lượt thường (không có _CALL_BUDGET) có trần nghĩ")
llm.reset_usage()
out = llm._call_once("gemini", "k", "p", "", .2, json_mode=True)
g = SO[-1]["generationConfig"]
ok(out == '{"a":1}', "JSON đi đường có trần, bỏ phần nghĩ khỏi kết quả", repr(out))
ok(g.get("thinkingConfig", {}).get("thinkingBudget") == 4096, "có trần nghĩ", str(g))
ok(g.get("maxOutputTokens", 0) >= 4096 + 8000, "chừa đủ chỗ trả lời sau khi nghĩ")
ok(llm._usage()["out"] == 3020, "đếm cả token nghĩ (tính tiền)", str(llm._usage()))

print("CA 2: lượt chữ thường không bị ép JSON")
out = llm._call_once("gemini", "k", "p", "", .2, json_mode=False)
g = SO[-1]["generationConfig"]
ok(out == "chữ" and "responseMimeType" not in g, "chữ thường không ép JSON", str(g))
ok("thinkingConfig" in g, "chữ thường cũng có trần nghĩ")

print("CA 3: nhiều luồng chạy song song, không khoá cả máy")
ts = [threading.Thread(target=llm._call_once, args=("gemini", "k", "p", "", .2),
                       kwargs={"json_mode": True}) for _ in range(4)]
DANG[:] = [0, 0]
for t in ts:
    t.start()
for t in ts:
    t.join()
ok(DANG[1] >= 3, "4 lượt cùng lúc chạy song song", f"đỉnh {DANG[1]}")

print("CA 4: bị cắt / bị chặn phải báo đúng")
requests.post = lambda *a, **k: Resp("{", "MAX_TOKENS")
llm._call_once("gemini", "k", "p", "", .2, json_mode=True)
ok(llm._LAN.ket_thuc == "length", "MAX_TOKENS -> ket_thuc=length", llm._LAN.ket_thuc)
requests.post = lambda *a, **k: Resp("x", "SAFETY")
try:
    llm._call_once("gemini", "k", "p", "", .2)
    ok(False, "chặn nội dung phải ném LLMContentBlocked")
except llm.LLMContentBlocked:
    ok(True, "chặn nội dung -> LLMContentBlocked")
src = (REPO / "app/ai/llm.py").read_text(encoding="utf-8")
ok("if provider == \"gemini\" and json_mode and getattr(_CALL_BUDGET" not in src,
   "điều kiện cũ (chỉ khi có _CALL_BUDGET) không quay lại")

print("CA 5: dòng 3.x đi cùng đường, không ép trần nghĩ")
requests.post = gia_post
settings.GEMINI_MODEL = "gemini-3.5-flash"
llm._call_once("gemini", "k", "p", "", .2, json_mode=True)
g = SO[-1]["generationConfig"]
ok("thinkingConfig" not in g and g.get("responseMimeType"), "3.5-flash: JSON, không thinkingConfig", str(g))
ok(g.get("maxOutputTokens", 0) >= 12288, "3.5-flash: đủ chỗ trả lời")

print(f"\nCỔNG 113: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
