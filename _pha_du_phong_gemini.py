# -*- coding: utf-8 -*-
"""Thử phá cổng 114: gỡ từng chốt, cổng PHẢI đỏ. Bản phá hỏng cú pháp không tính là BẮT."""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
LLM = REPO / "app/ai/llm.py"
M1 = REPO / "app/modules/m1_highlight.py"
PHEP = [
    ("không bao giờ chuyển Gemini", LLM, "    if provider_arg is not None or active_provider() != 'groq':\n        return False\n",
     "    return False\n"),
    ("gọi provider tường minh vẫn chuyển", LLM, "    if provider_arg is not None or active_provider() != 'groq':\n", "    if active_provider() != 'groq':\n"),
    ("hết ngân sách job vẫn chuyển", LLM, "        if 'phản hồi quá lâu' in str(g):\n            raise            # hết ngân sách thời gian của job, không đổi nhà cung cấp\n", ""),
    ("413 cũng cho Groq nghỉ", LLM, "    if isinstance(loi, (LLMTooLarge, LLMCatCut, LLMRong)):\n        return 0.0           # lỗi của RIÊNG yêu cầu này, Groq vẫn khoẻ\n", ""),
    ("không nhớ Groq đang nghỉ", LLM, "        dang_nghi = time.monotonic() < _DP_GROQ_NGHI_TOI\n", "        dang_nghi = False\n"),
    ("không đặt model dự phòng", LLM, "    _LAN.gemini_model = settings.GEMINI_DU_PHONG_MODEL\n", "    _LAN.gemini_model = ''\n"),
    ("model dự phòng rò sang lượt sau", LLM, "    finally:\n        _LAN.gemini_model = cu\n", "    finally:\n        pass\n"),
    ("Gemini 429 không đợi", LLM, "                if vong >= _DP_VONG_429 or not is_rate_limit_error(str(e)):\n                    raise\n", "                raise\n"),
    ("key hết tiền không xoay", LLM, "if provider == 'gemini' and 'credits are depleted' in last.lower():", "if False:"),
    ("không ghi nhật ký", LLM, '        _ghi_log_du_phong(f"Groq lỗi ({type(g).__name__}) -> chuyển Gemini "\n                          f"{settings.GEMINI_DU_PHONG_MODEL}, nghỉ Groq {nghi:.0f}s: {g}")\n', ""),
    ("Gemini không gọn số đoạn", M1, '            c["segments"] = _gon_so_doan(c.get("segments") or [])\n', "            pass\n"),
    ("Groq cũng bị gọn số đoạn", M1, "    if llm.so_luot_du_phong():\n        # Gemini dự phòng hay ghép", "    if True:\n        # Gemini dự phòng hay ghép"),
    ("đoạn hook có thể bị bỏ", M1, "min(ds[1:], key=", "min(ds, key="),
    ("Part không ghi dấu dự phòng", M1, '                signals["ai_du_phong"] = "gemini"\n', "                pass\n"),
]
bat = lot = hong = 0
for ten, f, a, b in PHEP:
    goc = f.read_bytes()
    s = goc.decode("utf-8")
    nl = "\r\n" if "\r\n" in s else "\n"
    a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
    if s.count(a2) != 1:
        hong += 1
        print("KHÔNG PHÁ ĐƯỢC", ten, s.count(a2))
        continue
    moi = s.replace(a2, b2)
    try:
        compile(moi, str(f), "exec")
    except SyntaxError as e:
        hong += 1
        print("KHÔNG PHÁ ĐƯỢC (cú pháp)", ten, e)
        continue
    try:
        f.write_bytes(moi.encode("utf-8"))
        r = subprocess.run([sys.executable, "_test_du_phong_gemini.py"], cwd=REPO, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=240, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    finally:
        f.write_bytes(goc)
    if r.returncode:
        bat += 1
        d = [x for x in r.stdout.splitlines() if "HỎNG" in x and "CỔNG" not in x]
        print("BẮT", ten, "|", (d[0].strip()[:90] if d else (r.stderr.strip().splitlines() or ["?"])[-1][:90]))
    else:
        lot += 1
        print("LỌT", ten)
print(f"\nBẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {hong}")
sys.exit(1 if lot or hong else 0)
