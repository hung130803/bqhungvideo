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

# ---- SỔ TRẠNG THÁI KEY tập trung (thread-safe) ----
# _KEY_STATE[(provider, key)] = {"state": "ready|limited", "until": ts hết cooldown,
#   "last_used": ts, "last_ok": ts, "calls": n, "note": "lỗi gần nhất"}
# Nhiều worker thread (LLM + Groq whisper) cùng ghi -> khóa riêng.
_KEY_STATE: dict = {}
_KEY_LOCK = threading.Lock()

# Cooldown mặc định khi KHÔNG parse được thời gian chờ từ message lỗi:
_COOLDOWN_DAILY = 3600.0   # lỗi "per day/TPD": đừng đợi cả ngày, thử lại mỗi giờ
_COOLDOWN_DEFAULT = 120.0  # rate-limit thường (per minute...)
_COOLDOWN_MAX = 3600.0     # trần: kể cả server bảo chờ 4h cũng chỉ nghỉ 1h
_IN_USE_WINDOW = 10.0      # key vừa dùng < Ns -> coi là "đang dùng" trên UI


def _state_for(provider: str, key: str) -> dict:
    """Lấy (hoặc tạo) bản ghi trạng thái. GỌI KHI ĐANG GIỮ _KEY_LOCK."""
    st = _KEY_STATE.get((provider, key))
    if st is None:
        st = _KEY_STATE[(provider, key)] = {
            "state": "ready", "until": 0.0, "last_used": 0.0,
            "last_ok": 0.0, "calls": 0, "note": "",
        }
    return st


def mark_used(provider: str, key: str) -> None:
    """Ghi nhận: sắp gọi API bằng key này."""
    with _KEY_LOCK:
        st = _state_for(provider, key)
        st["last_used"] = time.time()
        st["calls"] += 1


def mark_ok(provider: str, key: str) -> None:
    """Ghi nhận: gọi thành công -> key chắc chắn còn sống, xóa cờ limited."""
    with _KEY_LOCK:
        st = _state_for(provider, key)
        st["last_ok"] = time.time()
        st["state"] = "ready"
        st["until"] = 0.0
        st["note"] = ""


# Chuỗi thời lượng kiểu Groq/OpenAI: "7m30.5s", "1h2m3s", "1.234s", "232ms"
_DUR_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|h|m|s)", re.IGNORECASE)
_DUR_AFTER_IN = re.compile(
    r"\bin\s+((?:\d+(?:\.\d+)?\s*(?:ms|h|m|s)\s*)+)", re.IGNORECASE)
_RETRY_AFTER = re.compile(r"retry[-_ ]?after\D{0,4}(\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_retry_wait(err_text: str):
    """Bóc SỐ GIÂY phải chờ từ message lỗi rate-limit.

    Bắt các dạng: "Please try again in 7m30.5s" -> 450.5, "in 32s" -> 32,
    "in 1.234s" -> 1.234, "in 232ms" -> 0.232, header "retry-after: 30" -> 30.
    Không thấy -> None.
    """
    if not err_text:
        return None
    m = _DUR_AFTER_IN.search(err_text)
    if m:
        total, found = 0.0, False
        for num, unit in _DUR_TOKEN.findall(m.group(1)):
            found = True
            total += float(num) * {"ms": 0.001, "s": 1.0, "m": 60.0,
                                   "h": 3600.0}[unit.lower()]
        if found and total > 0:
            return total
    m = _RETRY_AFTER.search(err_text)
    if m:
        try:
            v = float(m.group(1))
            if v > 0:
                return v
        except ValueError:
            pass
    return None


def mark_limited(provider: str, key: str, err_text: str = "") -> float:
    """Ghi nhận: key dính rate-limit. PARSE thời gian chờ từ message lỗi;
    không parse được thì: lỗi daily -> 1h, còn lại 120s. Trả về số giây cooldown."""
    wait = parse_retry_wait(err_text or "")
    if wait is None:
        low = (err_text or "").lower()
        if any(s in low for s in ("per day", "daily", "tpd", "rpd",
                                  "tokens per day", "requests per day")):
            wait = _COOLDOWN_DAILY
        else:
            wait = _COOLDOWN_DEFAULT
    wait = min(float(wait), _COOLDOWN_MAX)
    with _KEY_LOCK:
        st = _state_for(provider, key)
        st["state"] = "limited"
        st["until"] = time.time() + wait
        st["note"] = (err_text or "").strip()[:200]
    return wait


def _is_limited(st: dict, now: float) -> bool:
    """Limited CÒN cooldown? (hết cooldown = tự về ready)."""
    return bool(st) and st.get("state") == "limited" and st.get("until", 0) > now


def _is_invalid(st: dict) -> bool:
    return bool(st) and st.get("state") == "invalid"


def pick_keys(provider: str, keys=None) -> list:
    """DANH SÁCH key đã SẮP THỨ TỰ ƯU TIÊN để xoay vòng:
    ready trước (giữ thứ tự settings), limited giữa (hết cooldown sớm nhất
    trước), key SAI xếp CUỐI (thử sau cùng, phòng khi user vừa sửa key).
    Không bao giờ rỗng nếu settings có key."""
    if keys is None:
        keys = settings.llm_keys_for(provider)
    now = time.time()
    ready, limited, invalid = [], [], []
    with _KEY_LOCK:
        for k in keys:
            st = _KEY_STATE.get((provider, k))
            if st is not None and _is_invalid(st):
                invalid.append(k)
            elif st is not None and _is_limited(st, now):
                limited.append((st["until"], k))
            else:
                ready.append(k)
    limited.sort(key=lambda t: t[0])
    return ready + [k for _, k in limited] + invalid


def soonest_ready_wait(provider: str, keys=None):
    """SỐ GIÂY tới khi có key ĐẦU TIÊN hồi (cooldown ngắn nhất trong các key
    limited). Có key ready sẵn -> 0.0. KHÔNG key nào (rỗng) -> None. Dùng để
    quyết định 'đợi TPM rồi thử lại' vs 'báo hết lượt' (reset dài = hết ngày).
    """
    if keys is None:
        keys = settings.llm_keys_for(provider)
    if not keys:
        return None
    now = time.time()
    soonest = None
    with _KEY_LOCK:
        for k in keys:
            st = _KEY_STATE.get((provider, k))
            if st is None or not _is_limited(st, now):
                if not (st is not None and _is_invalid(st)):
                    return 0.0            # có key sẵn sàng ngay
                continue                  # invalid -> bỏ qua
            left = st.get("until", 0) - now
            if soonest is None or left < soonest:
                soonest = left
    return soonest


def key_status(provider: str) -> list:
    """Trạng thái từng key (đúng THỨ TỰ trong settings) cho UI — chỉ đọc RAM,
    KHÔNG gọi mạng. Mỗi phần tử: key_masked/state/wait_left/last_used_ago/
    calls/in_use/note."""
    keys = settings.llm_keys_for(provider)
    now = time.time()
    # key "được chọn kế tiếp" = key READY đầu tiên theo thứ tự settings
    next_key = None
    with _KEY_LOCK:
        for k in keys:
            st = _KEY_STATE.get((provider, k))
            if st is None or (not _is_limited(st, now) and not _is_invalid(st)):
                next_key = k
                break
        out = []
        for k in keys:
            st = _KEY_STATE.get((provider, k)) or {
                "state": "ready", "until": 0.0, "last_used": 0.0,
                "last_ok": 0.0, "calls": 0, "note": ""}
            invalid = _is_invalid(st)
            limited = _is_limited(st, now)
            state = "invalid" if invalid else ("limited" if limited else "ready")
            recently = st["last_used"] and (now - st["last_used"]) < _IN_USE_WINDOW
            out.append({
                "key_masked": "…" + k[-6:],
                "state": state,
                "wait_left": max(0.0, st["until"] - now) if limited else 0.0,
                "last_used_ago": (now - st["last_used"]) if st["last_used"] else None,
                "last_ok_ago": (now - st["last_ok"]) if st["last_ok"] else None,
                "calls": st["calls"],
                "in_use": bool((k == next_key and not limited and not invalid)
                               or recently),
                "note": st["note"],
            })
    return out

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


def is_rate_limit_error(msg: str) -> bool:
    """Lỗi có phải RATE-LIMIT không (429/quota/hết lượt). Lỗi khác (mạng,
    key sai...) KHÔNG được tính — đừng giết oan key vì lỗi mạng."""
    m = (msg or "").lower()
    return any(s in m for s in ("429", "quota", "rate limit", "ratelimit",
                                "rate_limit", "resource_exhausted",
                                "too many requests"))


_is_rate_limit = is_rate_limit_error  # tên cũ, giữ tương thích


def is_daily_limit_error(msg: str) -> bool:
    """429 có phải HẾT LƯỢT NGÀY (per day / TPD / RPD) không — khác hết TOKEN/
    PHÚT (TPM, reset vài giây). Hết ngày -> phải THÊM KEY NICK KHÁC/đợi mai;
    hết phút -> chỉ cần đợi ~vài giây. Hàm thuần."""
    m = (msg or "").lower()
    return any(s in m for s in ("per day", "daily", "tpd", "rpd",
                                "tokens per day", "requests per day",
                                "per-day"))


def classify_rate_limit(msg: str) -> str:
    """Phân loại lỗi hạn mức để BÁO RÕ cho user:
      "auth"  -> key sai/hết hạn (401)
      "day"   -> hết lượt NGÀY (cần key nick khác / đợi mai)
      "minute"-> hết TOKEN/PHÚT (TPM — chỉ đợi ~vài giây, tự thử lại)
      "rate"  -> rate-limit chung không rõ chu kỳ
      ""      -> không phải lỗi hạn mức
    Hàm thuần — dùng cho thông báo UI."""
    if is_auth_error(msg):
        return "auth"
    if not is_rate_limit_error(msg):
        return ""
    if is_daily_limit_error(msg):
        return "day"
    # có reset ngắn (<= 120s) trong message -> TPM (per-minute)
    wait = parse_retry_wait(msg)
    if wait is not None and wait <= 120.0:
        return "minute"
    if wait is not None and wait > 120.0:
        return "day"        # reset dài = gần như hết ngày
    return "rate"


def is_auth_error(msg: str) -> bool:
    """Lỗi KEY SAI/không hợp lệ (401, invalid api key, unauthorized...) —
    key này hỏng hẳn, phải BỎ QUA dùng key khác chứ không dừng cả job."""
    m = (msg or "").lower()
    return any(s in m for s in ("invalid_api_key", "invalid api key",
                                "401", "unauthorized", "authentication",
                                "no auth credentials", "api key not valid"))


def mark_invalid(provider: str, key: str) -> None:
    """Đánh dấu key SAI (không hợp lệ). Xếp cuối hàng ưu tiên + hiện 'sai key'
    trên UI. Không hết hạn (chờ user sửa key rồi lưu lại)."""
    with _KEY_LOCK:
        st = _state_for(provider, key)
        st["state"] = "invalid"
        st["until"] = time.time() + 3650 * 86400   # ~không bao giờ tự hồi
        st["note"] = "API key sai/không hợp lệ"


def check_groq_key_valid(key: str, timeout: float = 15.0) -> str:
    """Kiểm tra NHANH 1 key Groq CÓ HỢP LỆ không (KHÔNG tốn lượt): GET /models.

    KHÔNG đọc được hạn mức thật (key hết lượt ngày VẪN trả 200 ở /models) —
    chỉ dùng khi chỉ cần biết key đúng/sai nhanh. Muốn biết CÒN BAO NHIÊU
    LƯỢT thật -> dùng check_groq_key().

    Trả về phân loại:
      "ok"      -> 200: key HỢP LỆ
      "invalid" -> 401/403: key SAI/không hợp lệ
      "limited" -> 429: hết hạn mức (tạm thời)
      "error"   -> lỗi mạng/khác (timeout, DNS, 5xx...)
    Dùng urllib (không thêm dependency). Không cập nhật sổ trạng thái RAM."""
    import urllib.error
    import urllib.request
    key = (key or "").strip()
    if not key:
        return "invalid"
    # User-Agent BẮT BUỘC: Groq sau Cloudflare, urllib không header trình
    # duyệt bị chặn 403 code 1010 (KHÔNG phải key sai) -> báo nhầm mọi key.
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}",
                 "User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return "ok" if resp.status == 200 else "error"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return "invalid"
        if e.code == 429:
            return "limited"
        return "error"
    except Exception:  # noqa: BLE001 — timeout, URLError (DNS/SSL), v.v.
        return "error"


# Model NHẸ để đọc hạn mức (chat completions trả header ratelimit đầy đủ).
_GROQ_PROBE_MODEL = "llama-3.3-70b-versatile"


def _to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def check_groq_key(key: str, timeout: float = 15.0) -> dict:
    """Kiểm tra 1 key Groq + ĐỌC HẠN MỨC THẬT còn lại (tốn ~1 request/vài token).

    CÁCH DUY NHẤT đọc remaining thật: gọi POST /chat/completions max_tokens=1
    -> Groq trả các header x-ratelimit-*. (GET /models luôn 200 kể cả khi HẾT
    LƯỢT ngày -> báo 'sống' SAI, nên KHÔNG dùng ở đây.)

    Trả về dict:
      kind: "ok"        -> 200, còn lượt (remaining_requests > 0)
            "exhausted" -> 200 nhưng remaining_requests <= 0, HOẶC 429 (hết lượt)
            "invalid"   -> 401/403 (key sai/không hợp lệ)
            "error"     -> lỗi mạng/khác (timeout, DNS, 5xx...)
      remaining_requests / limit_requests / remaining_tokens / limit_tokens: int|None
      reset_requests / reset_tokens: str|None (vd "1m26.4s")
      note: mô tả ngắn (lý do lỗi/hết lượt) — hiển thị cho user
    Dùng urllib (không thêm dependency). Không cập nhật sổ trạng thái RAM."""
    import urllib.error
    import urllib.request
    out = {"kind": "error", "remaining_requests": None, "limit_requests": None,
           "remaining_tokens": None, "limit_tokens": None,
           "reset_requests": None, "reset_tokens": None, "note": ""}
    key = (key or "").strip()
    if not key:
        out["kind"] = "invalid"
        out["note"] = "key rỗng"
        return out

    def _read_headers(h):
        out["limit_requests"] = _to_int(h.get("x-ratelimit-limit-requests"))
        out["remaining_requests"] = _to_int(h.get("x-ratelimit-remaining-requests"))
        out["limit_tokens"] = _to_int(h.get("x-ratelimit-limit-tokens"))
        out["remaining_tokens"] = _to_int(h.get("x-ratelimit-remaining-tokens"))
        out["reset_requests"] = h.get("x-ratelimit-reset-requests")
        out["reset_tokens"] = h.get("x-ratelimit-reset-tokens")

    body = json.dumps({
        "model": _GROQ_PROBE_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}",
                 "User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
                 "Accept": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _read_headers(resp.headers)
            rr = out["remaining_requests"]
            if rr is not None and rr <= 0:
                out["kind"] = "exhausted"
                out["note"] = "hết lượt request hôm nay"
            else:
                out["kind"] = "ok"
            return out
    except urllib.error.HTTPError as e:
        _read_headers(e.headers)
        if e.code in (401, 403):
            out["kind"] = "invalid"
            out["note"] = f"key sai/không hợp lệ ({e.code})"
        elif e.code == 429:
            out["kind"] = "exhausted"
            # reset time có thể nằm trong header hoặc body message
            reset = out["reset_requests"] or out["reset_tokens"]
            if not reset:
                try:
                    msg = e.read().decode("utf-8", "replace")
                    wait = parse_retry_wait(msg)
                    if wait:
                        reset = f"{wait:.0f}s"
                except Exception:  # noqa: BLE001
                    pass
            out["note"] = ("hết lượt (429)"
                           + (f", thử lại sau {reset}" if reset else ""))
        else:
            out["kind"] = "error"
            out["note"] = f"HTTP {e.code}"
        return out
    except Exception as e:  # noqa: BLE001 — timeout, URLError (DNS/SSL), v.v.
        out["kind"] = "error"
        out["note"] = str(e)[:120]
        return out


def check_groq_keys(keys, progress=None, max_workers: int = 6,
                    timeout: float = 20.0) -> dict:
    """Kiểm tra NHIỀU key Groq SONG SONG + ĐỌC HẠN MỨC THẬT (ThreadPool giới hạn).

    Mỗi key tốn ~1 request qua check_groq_key() (chat call chậm hơn GET /models
    nên giảm workers còn 6). keys: danh sách key. progress(done,total): gọi sau
    mỗi key xong (tùy chọn).

    LƯU Ý: Groq giới hạn theo TÀI KHOẢN, không theo key — nhiều key CÙNG 1 nick
    dùng chung hạn mức -> remaining giống nhau (KHÔNG dedup, chỉ ghi chú).

    Trả về dict:
      counts: {"ok","exhausted","invalid","error"} — số lượng mỗi loại
      results: [(key, info_dict), ...] giữ thứ tự đầu vào (info từ check_groq_key)
      invalid: [key, ...] các key SAI (401/403) — để user xoá
      total_remaining_requests: TỔNG remaining_requests của các key SỐNG (kind=ok)
    Dùng để hiển thị tổng kết + hạn mức từng key."""
    from concurrent.futures import ThreadPoolExecutor
    keys = [k.strip() for k in (keys or []) if k and k.strip()]
    total = len(keys)
    result_map: dict = {}
    done = 0
    counts = {"ok": 0, "exhausted": 0, "invalid": 0, "error": 0}
    if not keys:
        if progress:
            progress(0, 0)
        return {"counts": counts, "results": [], "invalid": [],
                "total_remaining_requests": 0}
    lock = threading.Lock()

    def work(k):
        return k, check_groq_key(k, timeout=timeout)

    workers = max(1, min(int(max_workers or 1), total))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for k, info in ex.map(work, keys):
            with lock:
                result_map[k] = info
                counts[info["kind"]] = counts.get(info["kind"], 0) + 1
                done += 1
                if progress:
                    progress(done, total)
    default = {"kind": "error", "remaining_requests": None, "note": ""}
    results = [(k, result_map.get(k, default)) for k in keys]
    invalid = [k for k, info in results if info["kind"] == "invalid"]
    total_remaining = sum(
        (info.get("remaining_requests") or 0)
        for _, info in results if info["kind"] == "ok")
    return {"counts": counts, "results": results, "invalid": invalid,
            "total_remaining_requests": total_remaining}


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
        # XOAY VÒNG key theo SỔ TRẠNG THÁI: key ready trước (đúng thứ tự
        # settings), key limited còn cooldown xếp cuối (hết sớm nhất trước) —
        # tất cả limited thì vẫn thử key sắp hồi trước thay vì fail luôn.
        for key in pick_keys(provider, keys):
            mark_used(provider, key)
            try:
                out = _call_once(provider, key, prompt, system, temperature)
                mark_ok(provider, key)
                return out
            except LLMError:
                raise
            except Exception as e:  # noqa: BLE001
                last = str(e)
                if is_rate_limit_error(last):
                    mark_limited(provider, key, last)
                    continue                   # key này hết lượt -> thử key tiếp
                if is_auth_error(last):
                    mark_invalid(provider, key)
                    continue                   # KEY SAI -> bỏ qua, thử key khác
                # lỗi KHÁC (mạng...) -> KHÔNG giết key, dừng luôn
                raise LLMError(f"Gọi {provider} thất bại: {last}")
        # tất cả key hết quota; chỉ 1 key -> chờ rồi thử lại 1 lần (free tier)
        if len(keys) == 1 and is_rate_limit_error(last):
            time.sleep(_RATE_WAIT)
            mark_used(provider, keys[0])
            try:
                out = _call_once(provider, keys[0], prompt, system, temperature)
                mark_ok(provider, keys[0])
                return out
            except Exception as e:  # noqa: BLE001
                last = str(e)
                if is_rate_limit_error(last):
                    mark_limited(provider, keys[0], last)
    # phân biệt lý do để user biết đường sửa
    if is_auth_error(last):
        raise LLMError(
            f"Tất cả key {provider} đều SAI/không hợp lệ. Vào 'Cài đặt AI' "
            f"kiểm tra lại key (xóa dấu cách thừa, dán lại key đúng). Chi tiết: {last}")
    raise LLMError(f"Gọi {provider} thất bại (hết lượt/lỗi tất cả key): {last}")


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
    used_key = ""                       # key đang dùng -> ghi sổ trạng thái
    try:
      with guard:
        if provider in ("ollama", "openai"):
            from openai import OpenAI
            if provider == "ollama":
                base_url, key = settings.OLLAMA_BASE_URL, "ollama"
                model = settings.OLLAMA_VL_MODEL
            else:
                base_url, key, model = None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL
            used_key = key
            mark_used(provider, key)
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
            mark_ok(provider, used_key)
            return _extract_json(resp.choices[0].message.content or "")

        if provider == "gemini":
            import google.generativeai as genai
            parts = [prompt]
            for p in image_paths:
                with open(p, "rb") as f:
                    parts.append({"mime_type": "image/jpeg", "data": f.read()})
            used_key = (settings.llm_key_for("gemini")
                        or settings.GEMINI_API_KEY)
            mark_used(provider, used_key)
            with _GEMINI_LOCK:
                genai.configure(api_key=used_key)
                model = genai.GenerativeModel(settings.GEMINI_MODEL,
                                              system_instruction=system or None)
                resp = model.generate_content(
                    parts, request_options={"timeout": 120})
            um = getattr(resp, "usage_metadata", None)
            if um:
                _add_usage(getattr(um, "prompt_token_count", 0),
                           getattr(um, "candidates_token_count", 0))
            mark_ok(provider, used_key)
            return _extract_json(resp.text or "")
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001
        # chỉ đánh dấu limited khi ĐÚNG là rate-limit (lỗi mạng thì tha key)
        if used_key and is_rate_limit_error(str(e)):
            mark_limited(provider, used_key, str(e))
        raise LLMError(f"Vision {provider} lỗi: {e}")
    raise LLMError(f"Provider không hỗ trợ vision: {provider}")
