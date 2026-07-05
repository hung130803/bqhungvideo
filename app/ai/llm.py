"""
Client LLM provider-agnostic: OpenAI / Gemini / DeepSeek.
Cùng một interface complete_json(). Key đọc từ .env (config.settings).

Dùng cho M1: chấm điểm 'viral' đoạn transcript. Sau này: hook analyzer, dịch.
Nếu không cấu hình key -> chạy fallback (heuristic) để app vẫn hoạt động.
"""
from __future__ import annotations

import json
import re
import threading
import time
from contextlib import nullcontext
from typing import Optional

from config import settings

# Số lần thử lại khi bị rate-limit (free tier) + thời gian chờ giữa các lần (giây)
_RATE_RETRIES = 2
_RATE_WAIT = 7.0

# KHÓA gọi LLM tuần tự: nhiều video chạy song song nhưng chỉ 1 lời gọi AI tại 1 thời
# điểm -> KHÔNG tràn VRAM card (Ollama 1 model), giữ chất lượng cắt + không lỗi.
_LLM_LOCK = threading.Lock()

# genai.configure(api_key) là STATE TOÀN CỤC của SDK Gemini: 2 thread xoay
# 2 key khác nhau sẽ đè key của nhau -> khóa riêng cho configure+generate.
_GEMINI_LOCK = threading.Lock()

# NHỚ key vừa hết quota (429): bỏ qua trong _KEY_DOWN_TTL giây thay vì mỗi
# chunk lại thử key chết trước (mỗi lần chờ retry SDK có thể tới ~60s).
_KEY_DOWN: dict = {}
_KEY_DOWN_TTL = 60.0

# ---- ĐO token Gemini để ước tính CHI PHÍ ----
# _USAGE đếm cho 1 VIDEO — để THEO THREAD (mỗi job auto chạy trọn trong 1
# worker thread): 2 video chạy AI song song không cộng chéo/reset lẫn nhau.
# _TOTAL: cả phiên (từ lúc mở app), dùng chung có khóa.
_TLS = threading.local()
_TOTAL = {"in": 0, "out": 0, "calls": 0}
_USAGE_LOCK = threading.Lock()


def _usage() -> dict:
    d = getattr(_TLS, "usage", None)
    if d is None:
        d = _TLS.usage = {"in": 0, "out": 0, "calls": 0}
    return d
# Giá Gemini (USD / 1 TRIỆU token) — (input, output). Google có thể đổi giá.
GEMINI_PRICE = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-3.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.0),
}
USD_TO_VND = 25500          # tỉ giá ước tính (đổi tại đây nếu lệch)


def reset_usage() -> None:
    _usage().update(**{"in": 0, "out": 0, "calls": 0})


def get_usage() -> dict:
    return dict(_usage())


def get_total_usage() -> dict:
    with _USAGE_LOCK:
        return dict(_TOTAL)


def _add_usage(p_in, p_out) -> None:
    d = _usage()                      # theo thread, không cần khóa
    d["in"] += int(p_in or 0)
    d["out"] += int(p_out or 0)
    d["calls"] += 1
    with _USAGE_LOCK:
        _TOTAL["in"] += int(p_in or 0)
        _TOTAL["out"] += int(p_out or 0)
        _TOTAL["calls"] += 1


def estimate_cost_vnd(usage: dict, model: str = "") -> int:
    """Ước tính chi phí (VND) từ số token đã dùng (chỉ áp cho Gemini)."""
    pin, pout = GEMINI_PRICE.get(model or settings.GEMINI_MODEL,
                                 GEMINI_PRICE["gemini-2.5-flash"])
    usd = usage.get("in", 0) / 1e6 * pin + usage.get("out", 0) / 1e6 * pout
    return round(usd * USD_TO_VND)


class LLMError(Exception):
    pass


def active_provider() -> str:
    return settings.LLM_PROVIDER or "gemini"


def is_configured(provider: Optional[str] = None) -> bool:
    provider = provider or active_provider()
    return bool(settings.llm_key_for(provider))


def _extract_json(text: str):
    """Bóc JSON ra khỏi câu trả lời (phòng khi model bọc trong ```json hoặc thêm chữ)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # thử parse trực tiếp trước
    try:
        return json.loads(text)
    except ValueError:
        pass
    # chọn cấu trúc XUẤT HIỆN TRƯỚC (mảng hay object) — tránh bắt nhầm '{' bên trong
    # mảng khi model thêm chữ thừa phía trước (vd: "Đây là...\n[ {...} ]").
    cands = []
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = text.find(opener), text.rfind(closer)
        if i != -1 and j != -1 and j > i:
            cands.append((i, text[i:j + 1]))
    cands.sort(key=lambda x: x[0])  # cái mở ra trước thắng
    for _, frag in cands:
        try:
            return json.loads(frag)
        except ValueError:
            continue
    return json.loads(text)  # ném lỗi nếu vẫn không parse được


def _is_rate_limit(msg: str) -> bool:
    m = msg.lower()
    return "429" in m or "quota" in m or "rate limit" in m or "resource_exhausted" in m


def _call_once(provider: str, key: str, prompt: str, system: str,
               temperature: float) -> str:
    # openai/deepseek/ollama/groq đều dùng SDK openai (chỉ khác base_url + model)
    if provider in ("openai", "deepseek", "ollama", "groq"):
        from openai import OpenAI
        extra = None
        if provider == "deepseek":
            base_url, model = "https://api.deepseek.com", settings.DEEPSEEK_MODEL
        elif provider == "groq":
            base_url, model = ("https://api.groq.com/openai/v1",
                               settings.GROQ_LLM_MODEL)
        elif provider == "ollama":
            base_url, model = settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL
            # QUAN TRỌNG: Ollama mặc định num_ctx=2048 -> prompt transcript dài bị
            # cắt đầu khiến model loạn, chỉ nhả 1 token rồi dừng. Nới cửa sổ ngữ
            # cảnh + cho phép output dài để JSON chọn clip không bị cụt.
            extra = {"options": {"num_ctx": 8192, "num_predict": 3000}}
        else:
            base_url, model = None, settings.OPENAI_MODEL
        # timeout: Ollama (máy) có thể chậm -> 300s; mây (groq/openai...) 120s.
        # Chống TREO cả hàng đợi AI nếu 1 lệnh gọi không bao giờ trả về.
        timeout = 300 if provider == "ollama" else 120
        client = OpenAI(api_key=key, base_url=base_url, timeout=timeout, max_retries=1)
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        # KHÔNG giới hạn token cứng: JSON chọn clip có thể dài, cắt cụt -> hỏng kết quả
        resp = client.chat.completions.create(
            model=model, messages=msgs, temperature=temperature, extra_body=extra,
        )
        return resp.choices[0].message.content or ""

    if provider == "gemini":
        import google.generativeai as genai
        with _GEMINI_LOCK:      # configure là state toàn cục -> không cho đè key
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                settings.GEMINI_MODEL, system_instruction=system or None,
            )
            resp = model.generate_content(
                prompt, generation_config={"temperature": temperature,
                                           "max_output_tokens": 8000},
                request_options={"timeout": 120},
            )
        um = getattr(resp, "usage_metadata", None)
        if um:
            _add_usage(getattr(um, "prompt_token_count", 0),
                       getattr(um, "candidates_token_count", 0))
        return resp.text or ""

    raise LLMError(f"Provider không hỗ trợ: {provider}")


def complete_text(prompt: str, system: str = "", temperature: float = 0.4,
                  provider: Optional[str] = None) -> str:
    provider = provider or active_provider()
    keys = settings.llm_keys_for(provider)
    if not keys:
        raise LLMError(f"Chưa cấu hình API key cho provider '{provider}' trong .env")

    # local (ollama) -> gọi tuần tự qua khóa để không tranh VRAM khi chạy đa luồng
    guard = _LLM_LOCK if provider == "ollama" else nullcontext()
    last = ""
    with guard:
        # BỎ QUA key vừa dính 429 (trong TTL) — nhưng nếu bỏ hết thì vẫn thử
        # tất cả (thà chờ còn hơn fail ngay).
        now = time.time()
        alive = [k for k in keys
                 if now - _KEY_DOWN.get((provider, k), 0) >= _KEY_DOWN_TTL]
        for key in (alive or keys):           # XOAY VÒNG key: hết quota -> key kế
            try:
                return _call_once(provider, key, prompt, system, temperature)
            except LLMError:
                raise
            except Exception as e:  # noqa: BLE001
                last = str(e)
                if _is_rate_limit(last):
                    _KEY_DOWN[(provider, key)] = time.time()
                    continue                   # key này hết lượt -> thử key tiếp
                raise LLMError(f"Gọi {provider} thất bại: {last}")
        # tất cả key hết quota; chỉ 1 key -> chờ rồi thử lại 1 lần (free tier)
        if len(keys) == 1 and _is_rate_limit(last):
            time.sleep(_RATE_WAIT)
            try:
                return _call_once(provider, keys[0], prompt, system, temperature)
            except Exception as e:  # noqa: BLE001
                last = str(e)
    raise LLMError(f"Gọi {provider} thất bại (hết lượt tất cả key): {last}")


def complete_json(prompt: str, system: str = "", provider: Optional[str] = None):
    """Gọi LLM và parse JSON. Ném LLMError nếu không parse được."""
    raw = complete_text(prompt, system=system, temperature=0.3, provider=provider)
    try:
        return _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise LLMError(f"LLM trả về không phải JSON hợp lệ: {e}\n---\n{raw[:500]}")


_OLLAMA_MODELS_CACHE = None


def _ollama_has(model: str) -> bool:
    """Kiểm tra Ollama đã TẢI model chưa (tránh gọi vision khi chưa có -> đỡ phí)."""
    global _OLLAMA_MODELS_CACHE
    if _OLLAMA_MODELS_CACHE is None:
        try:
            import requests
            base = settings.OLLAMA_BASE_URL.replace("/v1", "")
            r = requests.get(f"{base}/api/tags", timeout=4)
            _OLLAMA_MODELS_CACHE = [m.get("name", "")
                                    for m in r.json().get("models", [])]
        except Exception:  # noqa: BLE001
            _OLLAMA_MODELS_CACHE = []
    # khớp cả 'qwen2.5vl:7b' lẫn tiền tố
    base = model.split(":")[0]
    return any(m == model or m.split(":")[0] == base
               for m in _OLLAMA_MODELS_CACHE)


def vision_available(provider: Optional[str] = None) -> bool:
    """Có thể chấm điểm bằng HÌNH ẢNH không (cần model vision ĐÃ TẢI + USE_VISION)."""
    if not settings.USE_VISION:
        return False
    provider = provider or active_provider()
    if provider == "ollama":
        return bool(settings.OLLAMA_VL_MODEL) and _ollama_has(settings.OLLAMA_VL_MODEL)
    if provider == "gemini":
        return bool(settings.GEMINI_API_KEY)
    return False


def _b64(path: str) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def complete_vision_json(prompt: str, image_paths: list, system: str = "",
                         provider: Optional[str] = None):
    """
    Gửi NHIỀU ẢNH + text cho model vision -> JSON. Dùng để chấm viral theo khung hình.
    Hỗ trợ ollama (qwen2.5vl) và gemini. Ném LLMError nếu lỗi.
    """
    provider = provider or active_provider()
    guard = _LLM_LOCK if provider == "ollama" else nullcontext()
    try:
      with guard:
        if provider in ("ollama", "openai"):
            from openai import OpenAI
            if provider == "ollama":
                base_url, key = settings.OLLAMA_BASE_URL, "ollama"
                model = settings.OLLAMA_VL_MODEL
            else:
                base_url, key, model = None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL
            # timeout: chống 1 lời gọi vision treo giữ _LLM_LOCK -> treo cả
            # hàng đợi AI (nút Hủy vô tác dụng)
            client = OpenAI(api_key=key, base_url=base_url,
                            timeout=300 if provider == "ollama" else 120,
                            max_retries=1)
            content = [{"type": "text", "text": prompt}]
            for p in image_paths:
                content.append({"type": "image_url", "image_url":
                                {"url": f"data:image/jpeg;base64,{_b64(p)}"}})
            msgs = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": content}]
            extra = ({"options": {"num_ctx": 8192}} if provider == "ollama"
                     else None)
            resp = client.chat.completions.create(
                model=model, messages=msgs, temperature=0.3, max_tokens=1200,
                extra_body=extra)
            return _extract_json(resp.choices[0].message.content or "")

        if provider == "gemini":
            import google.generativeai as genai
            parts = [prompt]
            for p in image_paths:
                with open(p, "rb") as f:
                    parts.append({"mime_type": "image/jpeg", "data": f.read()})
            with _GEMINI_LOCK:
                genai.configure(api_key=settings.llm_key_for("gemini")
                                or settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(settings.GEMINI_MODEL,
                                              system_instruction=system or None)
                resp = model.generate_content(
                    parts, request_options={"timeout": 120})
            um = getattr(resp, "usage_metadata", None)
            if um:
                _add_usage(getattr(um, "prompt_token_count", 0),
                           getattr(um, "candidates_token_count", 0))
            return _extract_json(resp.text or "")
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"Vision {provider} lỗi: {e}")
    raise LLMError(f"Provider không hỗ trợ vision: {provider}")
