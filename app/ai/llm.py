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


def bo_khoi_suy_nghi(text: str) -> str:
    """Bỏ khối SUY NGHĨ `<think>…</think>` của model suy luận, trả phần đáp án.

    Vì sao cần (đo 06/08/2026): mọi chỗ bóc JSON trong repo đều dò dấu ngoặc
    (`re.search(r"\\[.*\\]")` / find('[')), mà khối suy nghĩ đầy '[' ']' của bản
    NHÁP -> bắt nhầm bản nháp. Đo thật: đặt khâu chấm sang qwen3.6 (model suy
    luận duy nhất còn trên Groq) thì **3/3 lượt parse hỏng** dù model trả lời
    đúng. Thẻ thiếu đóng (model bị cắt vì hết max_tokens) cũng phải chịu được:
    coi như CHƯA có đáp án -> trả rỗng, đừng lấy bản nháp."""
    t = (text or "").strip()
    if "</think>" in t:
        return t.rsplit("</think>", 1)[1].strip()
    i = t.find("<think>")
    if i < 0:
        return t
    # THIẾU thẻ đóng. Chỉ được coi là "khối nghĩ" khi nó nằm TRƯỚC mọi dấu mở
    # JSON. LỖI THẬT (cổng 28 bắt 06/08/2026): bản đầu cắt ở MỌI chỗ có
    # '<think>' -> mô tả khung hình chứa đúng chữ đó thì JSON bị chặt đôi
    # ('[{"i":0,"desc":"x <think>…' -> chuỗi hở -> mất cả batch).
    dau = min([p for p in (t.find("["), t.find("{")) if p >= 0] or [-1])
    if dau >= 0 and dau < i:
        return t                    # '<think>' nằm TRONG dữ liệu -> ĐỪNG đụng
    return ""                       # nghĩ dở dang -> coi như CHƯA có đáp án


def _bo_phay_thua(s: str) -> str:
    """Bỏ dấu phẩy THỪA ngay trước `]`/`}` — model hay để lại, `json` thì cấm.

    Hàm thuần. KHÔNG đụng dấu phẩy nằm trong chuỗi vì mẫu đòi ngay sau nó phải
    là dấu đóng (chuỗi có `, ]` bên trong là cực hiếm và bản gốc cũng đã hỏng)."""
    return re.sub(r",(\s*[\]}])", r"\1", s or "")


def _bo_qua_trang(t: str, j: int, them: str = "") -> int:
    while j < len(t) and (t[j].isspace() or t[j] in them):
        j += 1
    return j


def vot_json_cut(text: str):
    """VỚT phần ĐỌC ĐƯỢC của một JSON bị **CẮT NGANG**. Trả None nếu vô vọng.

    VÌ SAO TỒN TẠI — LỖI CHẶN SẢN XUẤT 18/08/2026 (anh Hùng, đường Thay giọng,
    v2.34.0): Groq áp **trần token đầu ra MẶC ĐỊNH** khi app không đặt
    `max_tokens` (đo được: `openai/gpt-oss-120b` -> **3072**, `gpt-oss-20b` ->
    **2048**). Bản dịch cả video cần ~3.100 token nên mảng JSON bị chặt giữa
    chừng -> `json.loads` ném *"Expecting value: line 1 column 1838"* ->
    `_dich_loat` **mất TRẮNG cả 50 câu** dù model đã dịch đúng 43 câu đầu.

    Vớt được thì caller còn đường tự chữa: `_dich_loat` đếm nhãn thiếu rồi
    ĐÒI LẠI đúng phần thiếu ở vòng sau (vòng đó đã có sẵn, chỉ chưa bao giờ
    chạy tới vì mất sạch dữ liệu).

    Vớt theo TỪNG PHẦN TỬ HOÀN CHỈNH bằng `raw_decode`, gặp phần tử dở thì
    DỪNG — tuyệt đối không "đoán nốt" phần model chưa viết ra.
    Hàm thuần, không mạng.
    """
    t = (text or "").strip()
    if not t:
        return None
    dau = [p for p in (t.find("["), t.find("{")) if p >= 0]
    if not dau:
        return None
    i = min(dau)
    dec = json.JSONDecoder()

    if t[i] == "[":
        ra: list = []
        j = i + 1
        while True:
            j = _bo_qua_trang(t, j, ",")
            if j >= len(t) or t[j] == "]":
                break
            try:
                gt, j = dec.raw_decode(t, j)
            except ValueError:
                # PHẦN TỬ DỞ DANG THÌ BỎ HẲN, KHÔNG vớt nửa vời. Các phần tử
                # của một mảng là NGANG HÀNG nhau, trả về một cái viết dở
                # (`{"i":3}` thiếu `"t"`) chẳng thêm thông tin gì mà lại đẻ ra
                # một mục trông như thật — đúng loại "phép đo phát chứng nhận"
                # repo này đang chống. Thiếu thì caller ĐÒI LẠI, tốt hơn.
                break
            ra.append(gt)
        return ra or None

    ra_d: dict = {}
    j = i + 1
    while True:
        j = _bo_qua_trang(t, j, ",")
        if j >= len(t) or t[j] == "}":
            break
        if t[j] != '"':
            break
        try:
            khoa, j = dec.raw_decode(t, j)
        except ValueError:
            break
        j = _bo_qua_trang(t, j)
        if j >= len(t) or t[j] != ":":
            break
        j = _bo_qua_trang(t, j + 1)
        if j >= len(t):
            break
        try:
            gt, j = dec.raw_decode(t, j)
        except ValueError:
            # Giá trị cuối là MỘT CONTAINER bị cắt -> vớt tầng trong. Đây là ca
            # THƯỜNG GẶP của recap: {"title":"…","parts":[ {…}, {…  <- cắt.
            # Khác ca "phần tử mảng dở dang" ở trên: ở đây cái dở dang chính là
            # container NGOÀI CÙNG của nhánh con, mà vớt container ngoài cùng
            # đúng là việc của hàm này; bên trong nó vẫn chỉ lấy phần tử HOÀN
            # CHỈNH nên không có mục nửa vời nào lọt ra.
            con = vot_json_cut(t[j:]) if t[j] in "[{" else None
            if con:
                ra_d[khoa] = con
            break
        ra_d[khoa] = gt
    return ra_d or None


def _extract_json(text: str, cho_vot: bool = True):
    """Bóc JSON ra khỏi câu trả lời (phòng khi model bọc trong ```json hoặc thêm chữ).

    `cho_vot=True` (mặc định): hết đường thì VỚT phần đọc được của JSON bị cắt
    ngang (xem `vot_json_cut`). Đặt False khi caller muốn biết chắc "đủ hay
    không" để còn gọi lại — `complete_json` dùng đúng kiểu đó cho 2 lượt đầu.

    BẤT BIẾN: JSON HỢP LỆ đi qua đây phải ra kết quả Y HỆT bản cũ — mọi bước
    thêm vào đều nằm SAU các bước cũ và chỉ chạy khi bước cũ đã ném.
    """
    text = bo_khoi_suy_nghi(text)
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    else:
        # khối markdown MỞ mà chưa kịp ĐÓNG (model bị cắt giữa khối) — bản cũ
        # để nguyên cả dòng ```json nên không parse nổi.
        mo = re.search(r"```(?:json)?\s*", text)
        if mo and "```" not in text[mo.end():]:
            text = text[mo.end():].strip()
    # thử parse trực tiếp trước
    try:
        return json.loads(text)
    except ValueError:
        pass
    # CẤU TRÚC NGOÀI CÙNG BỊ CẮT MẤT DẤU ĐÓNG -> VỚT NGAY.
    # Vì sao phải chặn TRƯỚC bước "ứng viên" dưới (lỗi cổng 74 bắt được):
    # `{"mach_lac":8,"thu_tu":[1,0,2],"vi_sao":"đảo cho x` <- object ngoài cùng
    # không có `}` nào, nên bước dưới đi bắt **MẢNH LỒNG BÊN TRONG** `[1,0,2]`
    # rồi trả về một LIST. `mach_lac.doc_ket` đòi dict -> vứt sạch kết quả, mà
    # lỗi lại đội lốt "model trả sai kiểu". Sai HÌNH DẠNG nguy hiểm hơn hẳn
    # không parse được: caller không có cách nào biết mình vừa nhận nhầm ruột.
    mo = [(p, c) for p, c in ((text.find("["), "]"), (text.find("{"), "}"))
          if p >= 0]
    if cho_vot and mo:
        som, dong = min(mo)
        if text.rfind(dong) < som:          # ngoài cùng chưa hề được đóng
            vot = vot_json_cut(text)
            if vot is not None:
                return vot
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
            pass
        try:                       # dấu phẩy thừa trước dấu đóng
            return json.loads(_bo_phay_thua(frag))
        except ValueError:
            continue
    if cho_vot:
        vot = vot_json_cut(text)
        if vot is not None:
            return vot
    return json.loads(text)  # ném lỗi nếu vẫn không parse được


#: tên CÔNG KHAI của bộ bóc JSON BAO DUNG — mọi chỗ trong repo phân tích phản
#: hồi LLM phải đi qua đây, đừng viết bộ dò dấu ngoặc mới (xem VIỆC 3 v2.35.0).
boc_json = _extract_json


def is_rate_limit_error(msg: str) -> bool:
    """Lỗi có phải RATE-LIMIT không (429/quota/hết lượt). Lỗi khác (mạng,
    key sai...) KHÔNG được tính — đừng giết oan key vì lỗi mạng."""
    m = (msg or "").lower()
    return any(s in m for s in ("429", "quota", "rate limit", "ratelimit",
                                "rate_limit", "resource_exhausted",
                                "too many requests"))


_is_rate_limit = is_rate_limit_error  # tên cũ, giữ tương thích


class LLMTooLarge(LLMError):
    """YÊU CẦU QUÁ LỚN cho hạn mức token/phút — KHÔNG phải key hết lượt."""


class LLMCatCut(LLMError):
    """CÂU TRẢ LỜI BỊ CẮT vì hết chỗ (`finish_reason=length`) — model có trả
    lời, chỉ là chưa viết xong thì hết ngân sách token.

    LỖI THẬT 18/08/2026 (anh Hùng, đường Thay giọng v2.34.0): app báo
    *"LLM trả về không phải JSON hợp lệ: Expecting value: line 1 column
    1838"*. Lời đó chỉ đúng phần NGỌN — nghe như model trả rác, nên người đọc
    đi soi prompt/parser trong khi bệnh nằm ở **trần token đầu ra**. Đây đúng
    là vết xe vừa mới đi qua: 404 model chết bị báo thành "Dữ liệu không hợp
    lệ" và anh Hùng tưởng hết hạn mức 41 key.

    TUYỆT ĐỐI KHÔNG phạt key (mọi key cùng trần) — cùng luật với
    `LLMTooLarge`/`LLMModelMissing`."""


class LLMModelMissing(LLMError):
    """MODEL đã bị nhà cung cấp GỠ/đổi tên (404) — LỖI CỦA APP, KHÔNG PHẢI
    CỦA KEY.

    LỖI THẬT 17/08/2026: Groq khai tử `llama-3.3-70b-versatile` (model CHÍNH
    **và** model dự phòng của app đều trỏ vào đúng nó, nên lưới rơi-về-fallback
    bị vô hiệu: `_call_once` chỉ đổi model khi `model != fb`). Mọi lượt gọi ra
    404, cả dây chuyền cắt/thay giọng/reup chết theo, và anh Hùng đọc lời lỗi
    rồi tưởng **hết hạn mức 41 key** ("key groq tôi bao nhiêu mà sao hết
    được").

    Vì vậy lớp lỗi này tồn tại để tách BẠCH khỏi hết-lượt:
      * TUYỆT ĐỐI KHÔNG `mark_limited`/`mark_invalid` — mọi key đều 404 y nhau,
        phạt key là đốt sạch vòng xoay cho một lỗi chả liên quan tới key (đúng
        vết xe 413 đã đốt 38 key, xem `is_too_large_error`).
      * Lời lỗi phải nói RÕ là app cần cập nhật, đừng để nó trông như hết lượt.
    """


def is_too_large_error(msg: str) -> bool:
    """Lỗi 413 'Request too large … please reduce your message size'.

    LỖI THẬT tìm được 06/08/2026 khi bật AI XEM HÌNH: Groq trả 413 kèm
    `'code': 'rate_limit_exceeded'` nên `is_rate_limit_error` khớp -> app coi
    là KEY HẾT LƯỢT -> `mark_limited` khoá key 120 giây (parse_retry_wait
    không ra số nên rơi mặc định). Gửi 1 yêu cầu quá to = **đốt sạch cả 38
    key trong 2 phút**, cả dây chuyền cắt đứng theo, mà nguyên nhân chả liên
    quan gì tới lượt còn hay hết. Đây là lỗi CỦA YÊU CẦU (mọi key đều giới hạn
    y nhau) -> phải THU NHỎ yêu cầu, tuyệt đối đừng phạt key.
    (Đã ghi trong config.py: prompt chọn đoạn với gpt-oss-120b cũng ra 413 —
    tức bẫy này đã có sẵn từ trước, không riêng gì vision.)"""
    m = (msg or "").lower()
    return ("413" in m and "too large" in m) or "reduce your message size" in m


def is_org_restricted(msg: str) -> bool:
    """Tài khoản Groq của key bị Groq KHOÁ ('Organization has been
    restricted') — mã 400, KHÔNG phải 401/429 nên cả nhánh auth lẫn
    rate-limit đều không bắt được.

    VÌ SAO NGUY HIỂM (đo thật 30/07: 2/27 key của anh Hùng dính): key khoá
    đứng ĐẦU vòng xoay thì mọi lượt gọi chết ngay tại nó (lỗi 'lạ' -> dừng
    luôn) dù 25 key sau còn sống — nguồn 'Cắt cơ bản' hàng loạt. Phải coi
    như KEY HỎNG VĨNH VIỄN: mark_invalid + nhảy key kế TỨC THÌ."""
    m = (msg or "").lower()
    return "organization has been restricted" in m \
        or "organization_restricted" in m \
        or ("organization" in m and "restricted" in m)


def is_transient_error(msg: str) -> bool:
    """Lỗi THOÁNG QUA (mạng/timeout/5xx phía server) — thử lại là hết, KHÔNG
    phải lỗi key hay hết lượt.

    VÌ SAO CẦN (bug anh Hùng 28/07: "key còn rất nhiều mà thỉnh thoảng vẫn
    'Cắt cơ bản'"): complete_text gặp lỗi KHÔNG-phải-429 là dừng ngay lập tức
    → 1 cú timeout (máy đang tải 5 luồng + xuất 5 clip, mạng nghẹt là thường)
    làm cả lượt phân tích rơi về heuristic dù mọi key vẫn sống. Chuỗi lỗi của
    SDK openai: "Connection error.", "Request timed out.", 5xx của Groq."""
    m = (msg or "").lower()
    return any(s in m for s in (
        "timeout", "timed out", "connection", "connect",
        "temporarily unavailable", "service unavailable",
        "internal server error", "bad gateway", "gateway timeout",
        "error code: 5", "remote end closed", "incomplete read",
        "reset by peer", "aborted", "eof occurred", "ssl"))


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
# 17/08/2026: `llama-3.3-70b-versatile` bị Groq GỠ -> phép dò hạn mức ăn 404 ở
# MỌI key. Nhánh `e.code in (400, 404)` bên dưới `continue` nên không kết tội
# key oan, nhưng nếu MỌI model dò đều chết thì kết quả ra "error: không dò được
# model nào" = anh Hùng nhìn bảng key thấy đỏ hết mà key vẫn tốt.
_GROQ_PROBE_MODEL = "openai/gpt-oss-20b"


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

    # DÒ MỌI MODEL APP DÙNG THẬT — hạn mức Groq tính RIÊNG THEO TỪNG MODEL.
    # Bug anh Hùng 28/07: chỉ dò model chính -> key ĐÃ CHẾT ở model đánh bóng
    # tiêu đề (SMART) / viết kịch bản (CREATIVE) mà nút Kiểm tra vẫn xanh hết,
    # "dùng như hết giới hạn rồi mà không thấy báo gì".
    probe_models: list = []
    for _m in (settings.GROQ_LLM_MODEL,
               getattr(settings, "GROQ_LLM_MODEL_SMART", ""),
               getattr(settings, "GROQ_LLM_MODEL_CREATIVE", ""),
               getattr(settings, "GROQ_LLM_MODEL_HQ", ""),
               getattr(settings, "GROQ_LLM_FALLBACK", "") or _GROQ_PROBE_MODEL):
        _m = (_m or "").strip()
        if _m and _m not in probe_models:
            probe_models.append(_m)

    def _probe(model_id):
        body = json.dumps({
            "model": model_id,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}",
                     "User-Agent": "Mozilla/5.0",
                     "Content-Type": "application/json",
                     "Accept": "application/json"},
            method="POST")
        return urllib.request.urlopen(req, timeout=timeout)

    def _short(mid: str) -> str:
        # "openai/gpt-oss-120b" -> "gpt-oss-120b" cho dòng báo gọn
        return mid.rsplit("/", 1)[-1]

    dead: list = []           # "model: lý do" — model nào kẹt/hết lượt
    ok_any = False
    got_headers = False
    for pm in probe_models:
        try:
            with _probe(pm) as resp:
                if not got_headers:   # số hiển thị = model CHÍNH (dò đầu tiên)
                    _read_headers(resp.headers)
                    got_headers = True
                rr = _to_int(resp.headers.get("x-ratelimit-remaining-requests"))
                rt = _to_int(resp.headers.get("x-ratelimit-remaining-tokens"))
                if rr is not None and rr <= 0:
                    dead.append(f"{_short(pm)}: hết request hôm nay")
                elif rt is not None and rt <= 0:
                    # TOKEN cạn cũng là kẹt thật (bug cũ: chỉ nhìn request
                    # nên token về 0 vẫn báo xanh) — nhưng token/PHÚT tự hồi.
                    reset = resp.headers.get("x-ratelimit-reset-tokens") or ""
                    dead.append(f"{_short(pm)}: cạn token"
                                + (f" (hồi sau {reset})" if reset else ""))
                else:
                    ok_any = True
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                out["kind"] = "invalid"
                out["note"] = f"key sai/không hợp lệ ({e.code})"
                return out
            if e.code in (400, 404):
                # 400 có 2 nghĩa: model bị gỡ (bỏ qua model) HOẶC tài khoản
                # bị Groq KHOÁ ('Organization has been restricted' — đo thật
                # 30/07: 2/27 key anh Hùng dính mà check cũ báo mù mờ).
                try:
                    body = e.read().decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    body = ""
                if is_org_restricted(body):
                    out["kind"] = "invalid"
                    out["note"] = ("tài khoản Groq bị KHOÁ (organization "
                                   "restricted) — xoá key này, không cứu được")
                    return out
                continue        # model bị gỡ/đổi tên — không kết tội key
            if e.code == 429:
                if not got_headers:
                    _read_headers(e.headers)
                    got_headers = True
                reset = (e.headers.get("x-ratelimit-reset-requests")
                         or e.headers.get("x-ratelimit-reset-tokens"))
                if not reset:
                    try:
                        wait = parse_retry_wait(
                            e.read().decode("utf-8", "replace"))
                        if wait:
                            reset = f"{wait:.0f}s"
                    except Exception:  # noqa: BLE001
                        pass
                dead.append(f"{_short(pm)}: hết lượt (429)"
                            + (f", hồi sau {reset}" if reset else ""))
                continue
            dead.append(f"{_short(pm)}: HTTP {e.code}")
        except Exception as e:  # noqa: BLE001 — timeout/DNS: các model sau
            out["kind"] = "error"       # cũng sẽ lỗi y vậy, dừng sớm cho nhanh
            out["note"] = str(e)[:120]
            return out

    if dead:
        # CÓ model kẹt là phải BÁO — dù model chính còn lượt, vì các pass
        # đánh bóng/kịch bản dùng model kẹt đó sẽ lỗi thật khi chạy.
        out["kind"] = "exhausted"
        out["note"] = ("; ".join(dead[:4])
                       + (" — model còn lại vẫn chạy được" if ok_any else ""))
    elif ok_any:
        out["kind"] = "ok"
    else:
        out["kind"] = "error"
        out["note"] = "không dò được model nào (model trong cấu hình bị gỡ?)"
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


# Model Groq bị phát hiện "không tồn tại/đã gỡ" trong phiên này -> né, dùng
# model kế ngay (đỡ tốn 1 request lỗi mỗi lần). Groq thi thoảng đổi tên/gỡ
# model — máy khách tự cập nhật KHÔNG được chết vì chuyện đó.
_GROQ_DEAD_MODELS: set = set()


def _is_model_missing_error(msg: str) -> bool:
    """Lỗi do MODEL không tồn tại/bị gỡ (khác lỗi key/quota/mạng)."""
    m = (msg or "").lower()
    return any(s in m for s in (
        "model_not_found", "model not found", "does not exist",
        "decommissioned", "model_decommissioned", "unknown model",
        "invalid model", "no longer supported", "has been deprecated"))


#: tên CÔNG KHAI (cổng test + complete_text dùng) — giữ tên cũ cho tương thích.
is_model_missing_error = _is_model_missing_error


# --------------------------------------------------------------------------
# DÂY CHUYỀN MODEL GROQ + TỰ DÒ MODEL CÒN SỐNG
#
# Vì sao phải có (lỗi thật 17/08/2026): app ghi CỨNG một tên model, Groq gỡ
# model đó là **mọi lượt gọi chết**. Ghi cứng thêm một tên nữa cũng không cứu
# được — bản cũ đặt CẢ `GROQ_LLM_MODEL` lẫn `GROQ_LLM_FALLBACK` bằng đúng
# `llama-3.3-70b-versatile`, nên lưới `if model != fb` không bao giờ chạy.
# Hai chốt ở đây:
#   1) DÂY CHUYỀN nhiều model KHÁC HỌ -> model đầu 404 thì tự sang model kế.
#   2) TỰ DÒ `/models` -> lọc theo danh sách Groq ĐANG trả về, thay vì tin tên
#      ghi trong mã. Có cache (RAM + đĩa) nên không gọi mạng mỗi lượt.
# --------------------------------------------------------------------------
_GROQ_SONG_TTL = 6 * 3600.0       # 6 giờ — Groq đổi model theo tháng, không theo phút
_GROQ_SONG_LOCK = threading.Lock()
_GROQ_SONG: dict = {"ts": 0.0, "models": frozenset()}


def _duong_cache_model() -> str:
    """File nhớ danh sách model (đọc `config.DATA_DIR` MỖI LẦN — không cất hằng
    số: bản đóng gói đổi DATA_DIR lúc chạy, xem bài học `tg_so.duong_so`)."""
    import os
    from config import DATA_DIR
    return os.path.join(str(DATA_DIR), "groq_models.json")


def models_groq_con_song(force: bool = False, timeout: float = 12.0):
    """Hỏi Groq xem HIỆN CÒN model nào -> `frozenset` tên model.

    **`frozenset()` RỖNG = "KHÔNG BIẾT", không phải "không còn model nào".**
    Đọc nhầm hai cái đó là lọc sạch dây chuyền rồi app chết trong khi Groq vẫn
    sống — nên mọi nơi dùng phải coi rỗng là "thôi đừng lọc".

    KHÔNG BAO GIỜ NÉM: mất mạng/hết key thì trả về cache cũ (hoặc rỗng), lượt
    gọi thật vẫn đi tiếp và vẫn có lưới 404 của `_call_once` đỡ.
    """
    import os
    now = time.time()
    with _GROQ_SONG_LOCK:
        if not force and _GROQ_SONG["models"] and \
                now - _GROQ_SONG["ts"] < _GROQ_SONG_TTL:
            return _GROQ_SONG["models"]
        # cache ĐĨA: mở app lên là có ngay, không phải chờ 1 lượt mạng
        if not force and not _GROQ_SONG["models"]:
            try:
                with open(_duong_cache_model(), encoding="utf-8") as f:
                    d = json.load(f)
                if now - float(d.get("ts") or 0) < _GROQ_SONG_TTL:
                    _GROQ_SONG["ts"] = float(d["ts"])
                    _GROQ_SONG["models"] = frozenset(d.get("models") or ())
                    if _GROQ_SONG["models"]:
                        return _GROQ_SONG["models"]
            except Exception:  # noqa: BLE001 — file chưa có/hỏng: dò lại
                pass
    ms: set = set()
    try:
        import urllib.error
        import urllib.request
        for key in (settings.groq_keys() or [])[:3]:   # 1 key sống là đủ
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                # User-Agent BẮT BUỘC: Groq nấp sau Cloudflare, urllib trần bị
                # chặn 403 "error code: 1010" (xem check_groq_key_valid).
                headers={"Authorization": f"Bearer {key}",
                         "User-Agent": "Mozilla/5.0",
                         "Accept": "application/json"}, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.load(resp)
                ms = {str(m.get("id") or "") for m in (data.get("data") or [])}
                ms.discard("")
                if ms:
                    break
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    continue               # key này hỏng -> thử key kế
                break
            except Exception:  # noqa: BLE001 — mạng: thôi, dùng cache cũ
                break
    except Exception:  # noqa: BLE001
        ms = set()
    if not ms:
        return _GROQ_SONG["models"]        # giữ cache cũ, đừng xoá thành rỗng
    with _GROQ_SONG_LOCK:
        _GROQ_SONG["ts"], _GROQ_SONG["models"] = time.time(), frozenset(ms)
    try:
        os.makedirs(os.path.dirname(_duong_cache_model()), exist_ok=True)
        with open(_duong_cache_model(), "w", encoding="utf-8") as f:
            json.dump({"ts": _GROQ_SONG["ts"],
                       "models": sorted(ms)}, f, ensure_ascii=False)
    except Exception:  # noqa: BLE001 — ghi cache hỏng thì thôi, không phải lỗi
        pass
    return _GROQ_SONG["models"]


def chuoi_model_groq(model: Optional[str] = None) -> list:
    """DÂY CHUYỀN model để thử lần lượt: [model chính, dự phòng, dự phòng 2...].

    Thứ tự: model caller chỉ định (nếu có) -> `GROQ_LLM_MODEL` ->
    `GROQ_LLM_FALLBACK` -> `GROQ_LLM_CHAIN`. Bỏ trùng, bỏ rỗng, bỏ model đã
    biết chết trong phiên.

    LỌC THEO DANH SÁCH SỐNG chỉ khi ĐÃ dò được (xem `models_groq_con_song`) và
    **chỉ khi còn lại ít nhất 1 model** — thà thử một tên có thể sai còn hơn
    trả danh sách rỗng rồi app đứng hình."""
    ra: list = []
    tho = [model or "", getattr(settings, "GROQ_LLM_MODEL", "") or "",
           getattr(settings, "GROQ_LLM_FALLBACK", "") or ""]
    tho += [s.strip() for s in
            str(getattr(settings, "GROQ_LLM_CHAIN", "") or "").split(",")]
    for m in tho:
        m = (m or "").strip()
        if m and m not in ra and m not in _GROQ_DEAD_MODELS:
            ra.append(m)
    song = models_groq_con_song()
    if song:
        loc = [m for m in ra if m in song]
        if loc:
            return loc
        # Không tên nào khớp danh sách sống (user gõ sai / Groq vừa đổi hết):
        # lấy model MẠNH NHẤT còn sống làm phao, đừng để dây chuyền rỗng.
        for uu in ("openai/gpt-oss-120b", "groq/compound", "openai/gpt-oss-20b"):
            if uu in song:
                return [uu]
    return ra


def _is_model_unfit_error(msg: str) -> bool:
    """Lỗi do MODEL không KHAM NỔI request này trên tier hiện tại (413
    request too large — hạn mức token/request của model thấp hơn prompt).
    Đổi key vô ích; RƠI VỀ fallback (hạn mức rộng hơn) là đúng."""
    m = (msg or "").lower()
    return "request too large" in m or "error code: 413" in m \
        or "reduce your message size" in m


# --------------------------------------------------------------------------
# TRẦN TOKEN ĐẦU RA — GỐC RỄ LỖI CHẶN SẢN XUẤT 18/08/2026
#
# App KHÔNG đặt `max_tokens` (chú thích cũ: "cắt cụt -> hỏng kết quả"). Nhưng
# **không đặt KHÔNG có nghĩa là không giới hạn**: Groq tự áp trần MẶC ĐỊNH.
# Đo thật 18/08/2026, cùng một prompt dịch 50 câu, 6/6 lượt:
#     openai/gpt-oss-120b -> finish_reason=length, completion_tokens=3072
#     openai/gpt-oss-20b   -> finish_reason=length, completion_tokens=2048
# Bản dịch cần ~3.100 token -> hụt vài chục token -> JSON đứt -> mất cả video.
# Hụt ÍT nên bệnh CHẬP CHỜN: video ngắn lọt, video dài chết (đúng ảnh anh Hùng
# gửi: 1 xong · 1 LỖI trong cùng một lượt).
#
# ĐẶT max_tokens thì phải biết TRẦN TRÊN, không được đặt bừa: Groq tính **cả
# `max_tokens`** vào cỡ yêu cầu. Nguyên văn lời lỗi đo được:
#   413 - Request too large for model `openai/gpt-oss-120b` in organization
#   `org_…` service tier `on_demand` on tokens per minute (TPM): Limit 8000…
# Đo: prompt 551 token + max_tokens 7168 = 7719 -> CHẠY · + 8192 = 8743 -> 413.
# Tức ràng buộc là `prompt + max_tokens <= 8000`, và 413 chính là cái bẫy đã
# đốt sạch 38 key một lần (xem `is_too_large_error`) — nới bừa là dẫm lại.
GROQ_TPM_TRAN = 8000        # token/phút mỗi yêu cầu, đo từ chính lời lỗi 413
GROQ_BIEN_AN_TOAN = 500     # chừa cho phần Groq tự thêm (schema json_object…)
GROQ_OUT_TOI_THIEU = 1024
GROQ_OUT_TOI_DA = 6144      # đo: 6144 CHẠY ở prompt 1413 token; 8192 -> 413


def _uoc_token(s: str) -> int:
    """ƯỚC LƯỢNG token của một chuỗi. Phải ước THỪA, tuyệt đối đừng ước hụt —
    hụt là `max_tokens` đặt quá tay rồi ăn 413.

    Hiệu chuẩn `_do_uoc_token.py` trên `usage.prompt_tokens` THẬT của Groq
    (prompt dịch 10 / 25 / 50 câu Trung-Việt -> 551 / 874 / 1413 token):
    hệ CJK 1,1 + phần còn lại chia 2,2 cho ra 560 / 884 / 1424 = phồng nhiều
    nhất **1,02x** và KHÔNG mốc nào hụt. Hàm thuần."""
    if not s:
        return 0
    cjk = sum(1 for ch in s
              if "⺀" <= ch <= "鿿" or "가" <= ch <= "힣"
              or "豈" <= ch <= "﫿" or "　" <= ch <= "ヿ")
    return int(cjk * 1.1 + (len(s) - cjk) / 2.2) + 8


def max_tokens_groq(prompt: str, system: str = "") -> int:
    """Chỗ trả lời XIN ĐƯỢC mà không đụng trần 8.000 token/phút của Groq.

    Prompt càng dài thì chỗ cho câu trả lời càng hẹp — đó là lý do việc CHIA
    NHỎ yêu cầu (ít câu hơn mỗi lượt) không phải chuyện tuỳ hứng mà là ràng
    buộc số học. Hàm thuần."""
    con = GROQ_TPM_TRAN - _uoc_token(prompt) - _uoc_token(system) \
        - GROQ_BIEN_AN_TOAN
    return max(GROQ_OUT_TOI_THIEU, min(GROQ_OUT_TOI_DA, con))


#: LÝ DO KẾT THÚC của lượt gọi GẦN NHẤT **trên chính luồng này** (`length` =
#: bị cắt vì hết chỗ). Để theo LUỒNG vì 3 làn AI chạy song song — biến toàn
#: cục là đọc phải lý do của lượt khác (đúng bệnh `_SFX_LAST_PICK`).
_LAN = threading.local()


def ly_do_ket_thuc() -> str:
    """`finish_reason` của lượt gọi gần nhất trên luồng hiện tại ("" nếu chưa
    có). `length` = model bị CẮT vì hết chỗ, KHÔNG phải nó trả rác."""
    return str(getattr(_LAN, "ket_thuc", "") or "")


def _ghi_ket_thuc(resp) -> None:
    try:
        _LAN.ket_thuc = str(getattr(resp.choices[0], "finish_reason", "") or "")
    except Exception:  # noqa: BLE001 — sổ ghi chú, không được làm chết lượt gọi
        _LAN.ket_thuc = ""


def _nhan_json_mode(model: str) -> bool:
    """Model có nhận `response_format={"type":"json_object"}` không.

    Đo 18/08/2026 (mỗi model 2 lượt): `openai/gpt-oss-120b` và `gpt-oss-20b`
    ĐẠT 2/2, `finish_reason=stop`, và **hình dạng KHÔNG đổi** — vẫn là MẢNG
    `[{"i":..,"t":..}]` chứ không bị bọc thành object, nên `_theo_nhan` của
    `thay_giong` lấy đủ 12/12. `groq/compound` trả 413 `request_too_large`
    -> để ngoài."""
    m = (model or "").lower()
    return "gpt-oss" in m or m.startswith("openai/")


def la_loi_tham_so_them(msg: str) -> bool:
    """Lỗi 400 do MỘT THAM SỐ THÊM, không phải do prompt/key -> gọi lại kiểu
    TRẦN là xong. Ba thân lỗi ĐO ĐƯỢC của Groq:

    * *"`reasoning_effort` must be one of `low`, `medium`, or `high`"* — model
      khác không nhận tham số đó.
    * *"`response_format` … not supported"* — model không nhận json_object.
    * **"Failed to generate JSON. Please adjust your prompt."** — ca NGUY HIỂM
      NHẤT, bắt được đúng lúc chạy cổng 74 với Groq THẬT (18/08/2026): bật
      `json_object` là Groq dùng bộ giải mã có RÀNG BUỘC, và khi model không
      sinh nổi JSON hợp lệ trong ràng buộc đó thì nó **trả 400 chứ không trả
      câu nào**. Tức bật json_object mà thiếu lưới này là ĐỔI một bệnh chập
      chờn lấy một bệnh chập chờn KHÁC, và bệnh mới còn tệ hơn vì lời lỗi
      "Gọi groq thất bại" chẳng nói gì về nguyên nhân. Hàm thuần."""
    m = (msg or "").lower()
    if "400" not in m:
        return False
    return any(s in m for s in ("reasoning_effort", "response_format",
                                "json_object", "failed to generate json"))


def _nhan_reasoning(model: str) -> bool:
    """Model gpt-oss là model SUY LUẬN: phần "nghĩ" ăn CHUNG ngân sách đầu ra.

    Đo 18/08/2026 (cùng prompt, max_tokens=4096): mặc định 3.247 token / 7,3s ·
    `reasoning_effort="low"` **1.214 token / 3,2s**, bản dịch vẫn ĐẠT đủ 50
    câu. Tức nghĩ ít đi thì vừa còn chỗ cho câu trả lời vừa nhanh gấp 2,3 lần.
    LƯU Ý: **`"none"` bị Groq TỪ CHỐI** (400 *"`reasoning_effort` must be one
    of `low`, `medium`, or `high`"*) — khác `qwen3.6` bên vision, đừng chép
    tham số từ đó sang."""
    return "gpt-oss" in (model or "").lower()


def _call_once(provider: str, key: str, prompt: str, system: str,
               temperature: float, model: Optional[str] = None,
               json_mode: bool = False) -> str:
    # openai/deepseek/ollama/groq đều dùng SDK openai (chỉ khác base_url + model)
    if provider in ("openai", "deepseek", "ollama", "groq"):
        from openai import OpenAI
        extra = None
        if provider == "deepseek":
            base_url, model = "https://api.deepseek.com", settings.DEEPSEEK_MODEL
        elif provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
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
        _LAN.ket_thuc = ""
        if provider != "groq":
            # KHÔNG giới hạn token cứng ở provider khác: hạn mức của họ không
            # tính `max_tokens` vào cỡ yêu cầu như Groq nên đặt vào chỉ có hại.
            resp = client.chat.completions.create(
                model=model, messages=msgs, temperature=temperature,
                extra_body=extra,
            )
            _ghi_ket_thuc(resp)
            return resp.choices[0].message.content or ""

        # ---- GROQ: đi hết DÂY CHUYỀN model, model đầu chết thì sang model kế ----
        # Chỉ 3 loại lỗi mới được sang model kế (đều là lỗi CỦA MODEL):
        #   404 model bị gỡ · 413 model không kham nổi prompt · content RỖNG
        #     (model reasoning tiêu hết chỗ output — lỗi thật của gpt-oss-120b).
        # Lỗi CỦA KEY (429/401/mạng) phải NỔI LÊN NGAY cho `complete_text` xoay
        # key: nuốt ở đây là mất cả vòng xoay 41 key.
        chuoi = chuoi_model_groq(model)
        if not chuoi:
            raise LLMModelMissing(
                "Không còn model Groq nào dùng được. Groq đã bỏ model cũ — "
                "app cần cập nhật (đây KHÔNG phải lỗi hết hạn mức key).")
        loi_model = ""
        # CHỖ TRẢ LỜI phải XIN TRƯỚC, đừng để Groq tự áp trần mặc định 2048-3072
        # (xem khối ghi chú GROQ_TPM_TRAN — đây là gốc rễ lỗi 18/08/2026).
        mt = max_tokens_groq(prompt, system)
        for i, md in enumerate(chuoi):
            cuoi = (i == len(chuoi) - 1)
            them: dict = {"max_tokens": mt}
            if json_mode and _nhan_json_mode(md):
                them["response_format"] = {"type": "json_object"}
            if _nhan_reasoning(md):
                them["reasoning_effort"] = "low"
            try:
                try:
                    resp = client.chat.completions.create(
                        model=md, messages=msgs, temperature=temperature,
                        extra_body=extra, **them,
                    )
                except Exception as e_th:  # noqa: BLE001
                    # Tham số THÊM bị từ chối (model không nhận, hoặc bộ giải
                    # mã json_object không sinh nổi JSON) -> gọi lại kiểu TRẦN.
                    # Một TUỲ CHỌN không bao giờ được phép giết cả lượt: bản
                    # trần chính là hành vi app đã chạy suốt từ trước.
                    if not la_loi_tham_so_them(str(e_th)):
                        raise
                    resp = client.chat.completions.create(
                        model=md, messages=msgs, temperature=temperature,
                        extra_body=extra, max_tokens=mt,
                    )
            except Exception as e:  # noqa: BLE001
                if _is_model_missing_error(str(e)):
                    # NHỚ trong phiên: các lượt sau đi thẳng model kế, khỏi
                    # tốn thêm một request 404 mỗi lần.
                    _GROQ_DEAD_MODELS.add(md)
                    loi_model = str(e)
                    if cuoi:
                        raise LLMModelMissing(
                            f"Groq đã bỏ model «{md}» — app cần cập nhật "
                            f"(KHÔNG phải hết hạn mức key). Chi tiết: {e}")
                    continue
                if _is_model_unfit_error(str(e)) and not cuoi:
                    # 413: model này không kham nổi prompt dài trên tier hiện
                    # tại. KHÔNG memo (prompt ngắn vẫn dùng nó được) và KHÔNG
                    # phạt key — đổi key vô ích, mọi key cùng hạn mức.
                    loi_model = str(e)
                    continue
                raise          # lỗi CỦA KEY -> để complete_text xoay key
            _ghi_ket_thuc(resp)
            out = resp.choices[0].message.content or ""
            if out.strip() or cuoi:
                return out
            loi_model = "model trả về content RỖNG"
        raise LLMModelMissing(
            f"Mọi model Groq trong dây chuyền đều hỏng ({', '.join(chuoi)}): "
            f"{loi_model}")

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
                  provider: Optional[str] = None,
                  model: Optional[str] = None,
                  json_mode: bool = False) -> str:
    """`model`: đè model CHỈ với provider groq (vd kimi-k2 cho pass viết
    kịch bản); provider khác bỏ qua — an toàn khi user chọn gemini/ollama.

    `json_mode`: xin model trả JSON đúng chuẩn (`response_format`). Chỉ
    `complete_json` bật; model không hỗ trợ thì tự bỏ qua, KHÔNG chết."""
    provider = provider or active_provider()
    keys = settings.llm_keys_for(provider)
    if not keys:
        raise LLMError(f"Chưa cấu hình API key cho provider '{provider}' trong .env")

    # local (ollama) -> gọi tuần tự qua khóa để không tranh VRAM khi chạy đa luồng
    guard = _LLM_LOCK if provider == "ollama" else nullcontext()
    last = ""
    with guard:
        # ĐỢI-THỬ-LẠI khi TẤT CẢ key kẹt token/phút (TPM/429): tối đa 3 vòng,
        # mỗi vòng xoay hết key; hết vòng mà mọi key vừa 429 với reset NGẮN
        # (cùng nick chung hạn mức/phút) -> ĐỢI key sắp hồi rồi thử lại thay vì
        # fail (đỡ hiện "AI lỗi, thử lại" ở recap — chỉ là quá tải tạm thời).
        for _round in range(3):
            # XOAY VÒNG key theo SỔ TRẠNG THÁI: key ready trước (đúng thứ tự
            # settings), key limited còn cooldown xếp cuối (hết sớm nhất trước).
            # saw_retryable: vòng này CÓ lỗi kiểu chờ-được (429/mạng) không —
            # quyết định đợi-thử-lại hay bỏ cuộc. Dựa vào `last` (lỗi CUỐI)
            # là sai khi key cuối cùng là key bị Groq khoá: last=khoá -> tưởng
            # hết đường dù các key trước chỉ đang cooldown ngắn.
            saw_retryable = False
            for key in pick_keys(provider, keys):
                mark_used(provider, key)
                try:
                    out = _call_once(provider, key, prompt, system,
                                     temperature, model=model,
                                     json_mode=json_mode)
                    mark_ok(provider, key)
                    return out
                except LLMError:
                    raise
                except Exception as e:  # noqa: BLE001
                    last = str(e)
                    if is_too_large_error(last):
                        # KHÔNG phạt key, KHÔNG thử key khác (mọi key cùng hạn
                        # mức) — nổi lên để caller thu nhỏ prompt. Xem
                        # is_too_large_error: trước đây rơi vào nhánh dưới và
                        # khoá lần lượt CẢ 38 key trong 120s.
                        raise LLMTooLarge(f"Yêu cầu quá lớn cho hạn mức "
                                          f"token/phút: {last}")
                    if _is_model_missing_error(last):
                        # 404 MODEL BỊ GỠ: lỗi CỦA APP, mọi key đều 404 y nhau.
                        # KHÔNG phạt key, KHÔNG xoay key (vô ích) — nổi lên với
                        # lời báo nói RÕ là app cần cập nhật, đừng để nó trông
                        # giống hết hạn mức (xem LLMModelMissing).
                        raise LLMModelMissing(
                            f"Groq đã bỏ model đang dùng nên app không gọi "
                            f"được — cần cập nhật app. KHÔNG phải hết hạn mức "
                            f"key (41 key vẫn còn nguyên). Chi tiết: {last}")
                    if is_rate_limit_error(last):
                        mark_limited(provider, key, last)
                        saw_retryable = True
                        continue               # key này hết lượt -> thử key tiếp
                    if is_org_restricted(last):
                        # TÀI KHOẢN bị Groq KHOÁ (400) -> loại key vĩnh viễn
                        # khỏi vòng xoay, nhảy key kế NGAY — không cho 1 key
                        # ban giết cả lượt phân tích khi 25 key sau còn sống.
                        mark_invalid(provider, key)
                        continue
                    if is_auth_error(last):
                        mark_invalid(provider, key)
                        continue               # KEY SAI -> bỏ qua, thử key khác
                    if is_transient_error(last):
                        # MẠNG/5XX THOÁNG QUA: không giết key, thử key khác
                        # (kết nối mới) + còn vòng ngoài. Trước đây dừng ngay
                        # → 1 cú timeout là cả video rơi về "Cắt cơ bản" dù
                        # key còn đầy (bug anh Hùng 28/07).
                        time.sleep(1.0)
                        saw_retryable = True
                        continue
                    # lỗi KHÁC (không nhận diện được) -> dừng luôn, báo rõ
                    raise LLMError(f"Gọi {provider} thất bại: {last}")
            # hết vòng: không có lỗi nào kiểu chờ-được (chỉ key sai/bị khoá)
            # -> đợi cũng vô ích, thoát báo luôn.
            if not saw_retryable:
                break
            # 429: key sắp hồi trong ~ngắn (TPM/phút) -> đợi rồi thử lại vòng sau.
            # Reset DÀI (hết lượt NGÀY) -> đợi vô ích, thoát báo lỗi.
            wait = soonest_ready_wait(provider, keys)
            if wait is None or wait <= 0:
                wait = _RATE_WAIT
            if _round < 2 and wait <= 45.0:
                time.sleep(wait + 0.3)
                continue
            break
    # phân biệt lý do để user biết đường sửa
    if _is_model_missing_error(last):
        raise LLMModelMissing(
            f"Groq đã bỏ model đang dùng nên app không gọi được — cần cập "
            f"nhật app. KHÔNG phải hết hạn mức key. Chi tiết: {last}")
    if is_auth_error(last):
        raise LLMError(
            f"Tất cả key {provider} đều SAI/không hợp lệ. Vào 'Cài đặt AI' "
            f"kiểm tra lại key (xóa dấu cách thừa, dán lại key đúng). Chi tiết: {last}")
    raise LLMError(f"Gọi {provider} thất bại (hết lượt/lỗi tất cả key): {last}")


def complete_json(prompt: str, system: str = "", provider: Optional[str] = None,
                  model: Optional[str] = None):
    """Gọi LLM và parse JSON. Ném LLMError nếu không parse được.
    `model`: đè model chỉ với groq (xem complete_text).

    JSON HỎNG THÌ GỌI LẠI (tối đa 3 lần): model free thỉnh thoảng nhả JSON
    cụt/lẫn chữ — trước đây ném LLMError NGAY, xuyên qua mọi lớp xoay key,
    làm cả video rơi về "Cắt cơ bản" dù key còn đầy (bug anh Hùng 28/07).
    Lần gọi lại kèm nhắc "chỉ trả JSON" — lỗi kiểu này gọi lại gần như luôn
    hết. Key Groq của user gần vô hạn, ưu tiên CHẤT LƯỢNG (xem MEMORY).

    HAI THỨ THÊM 18/08/2026 (lỗi chặn sản xuất đường Thay giọng):
    * **BỊ CẮT thì phải NÓI LÀ BỊ CẮT.** `finish_reason=length` -> ném
      `LLMCatCut` với lời "AI trả lời quá dài bị cắt". Lời cũ *"không phải
      JSON hợp lệ"* chỉ đúng phần NGỌN và đẩy người đọc đi tìm nhầm chỗ —
      đúng vết xe 404-model-chết bị báo thành "Dữ liệu không hợp lệ".
    * **LƯỢT CUỐI mới được VỚT.** 2 lượt đầu parse NGHIÊM (`cho_vot=False`)
      để còn cơ hội đòi bản ĐỦ; hết lượt mới lấy phần vớt được, và lấy bản
      vớt ĐƯỢC NHIỀU NHẤT trong 3 lượt. Trả phần thiếu vẫn hơn trả TAY
      TRẮNG: `_dich_loat` đếm nhãn thiếu rồi đòi lại đúng phần đó.

    KHÔNG PHẠT KEY ở đây: JSON hỏng là lỗi ĐỊNH DẠNG, mọi key đều như nhau.
    """
    last_exc: Optional[LLMError] = None
    sys_now = system
    vot_tot: object = None
    so_vot = -1
    bi_cat = False
    for _attempt in range(3):
        cuoi = (_attempt == 2)
        raw = complete_text(prompt, system=sys_now, temperature=0.3,
                            provider=provider, model=model, json_mode=True)
        cat = (ly_do_ket_thuc() == "length")
        bi_cat = bi_cat or cat
        try:
            return _extract_json(raw, cho_vot=False)
        except (ValueError, json.JSONDecodeError) as e:
            try:
                v = vot_json_cut(bo_khoi_suy_nghi(raw))
            except Exception:  # noqa: BLE001
                v = None
            if v is not None and len(v) > so_vot:
                vot_tot, so_vot = v, len(v)
            last_exc = (
                LLMCatCut(
                    f"AI trả lời quá dài nên bị CẮT giữa chừng "
                    f"(finish_reason=length, {len(raw)} ký tự) — hãy chia nhỏ "
                    f"yêu cầu. KHÔNG phải hết hạn mức key. Chi tiết: {e}"
                    f"\n---\n{raw[:500]}")
                if cat else
                LLMError(
                    f"LLM trả về không phải JSON hợp lệ: {e}\n---\n{raw[:500]}"))
            if cuoi:
                break
            # nhắc CỨNG cho lần sau — model đã trả rác 1 lần rồi
            sys_now = (system + "\n\nQUAN TRỌNG: CHỈ trả về đúng MỘT khối "
                       "JSON hợp lệ. KHÔNG chữ dẫn, KHÔNG markdown, KHÔNG "
                       "giải thích, KHÔNG cắt cụt.")
            if cat:
                sys_now += ("\nLần trước câu trả lời DÀI QUÁ nên bị cắt mất "
                            "đuôi: hãy viết NGẮN GỌN hơn, bỏ mọi chữ thừa, "
                            "giữ đủ MỌI mục.")
    if vot_tot is not None:
        return vot_tot
    raise last_exc


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
    if provider == "groq":
        # Groq: chỉ cần key + model cấu hình. LƯU Ý (đo 06/08/2026): hàm này
        # KHÔNG chứng minh model còn sống — llama-4-scout đã bị Groq gỡ và trả
        # 404 trong khi hàm vẫn báo True, nên "AI xem hình" ra 0 mốc mà im
        # lặng. Muốn biết chắc thì gọi thật 1 lần (xem _do_vision_buoc.py).
        return bool(getattr(settings, "GROQ_VISION_MODEL", "")) \
            and bool(settings.groq_keys())
    return False


def vision_max_images(provider: Optional[str] = None) -> int:
    """SỐ ẢNH TỐI ĐA gửi được trong MỘT lời gọi vision.

    Đo thật 06/08/2026: `qwen/qwen3.6-27b` (model vision duy nhất còn sống trên
    Groq) trả 400 "Too many images provided. This model supports up to 3
    images" khi gửi 4 ảnh. Gửi quá là MẤT TRẮNG cả batch (caller nào cũng
    `except: continue`) nên phải chia batch theo số này, đừng đoán."""
    provider = provider or active_provider()
    if provider == "groq":
        return 3
    return 8


def _b64(path: str) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def complete_vision_json(prompt: str, image_paths: list, system: str = "",
                         provider: Optional[str] = None, key_dau: int = 0):
    """
    Gửi NHIỀU ẢNH + text cho model vision -> JSON. Dùng để chấm viral theo khung hình.
    Hỗ trợ ollama (qwen2.5vl) và gemini. Ném LLMError nếu lỗi.

    `key_dau`: **BẮT ĐẦU XOAY TỪ KEY THỨ MẤY** (chỉ có nghĩa với groq). Mặc
    định 0 = hành xử Y HỆT bản cũ. Vì sao cần (ĐO 09/08/2026,
    `_do_vision_219.py`): gọi nhiều lượt SONG SONG mà lượt nào cũng bắt đầu từ
    key[0] thì chúng chen vào ĐÚNG MỘT hàng đợi — đo được 40-45 giây/lượt. Cho
    mỗi lượt một mốc xuất phát KHÁC NHAU thì 3/4 lượt xong trong 0,9 giây.
    **KHÔNG ghim CỨNG một key**: vẫn đi hết vòng `pick_keys` kể từ mốc đó, nên
    key hết lượt/sai vẫn lùi sang key kế đúng như cũ và `mark_limited` giữ
    nguyên ý nghĩa.
    """
    provider = provider or active_provider()
    guard = _LLM_LOCK if provider == "ollama" else nullcontext()
    used_key = ""                       # key đang dùng -> ghi sổ trạng thái
    try:
      with guard:
        if provider == "groq":
            # Groq: XOAY VÒNG key như complete_text (429 -> key kế, 401 -> bỏ)
            from openai import OpenAI
            keys = settings.groq_keys()
            if not keys:
                raise LLMError("Chưa cấu hình key Groq cho vision")
            content = [{"type": "text", "text": prompt}]
            for p in image_paths:
                content.append({"type": "image_url", "image_url":
                                {"url": f"data:image/jpeg;base64,{_b64(p)}"}})
            msgs = ([{"role": "system", "content": system}] if system else []) \
                + [{"role": "user", "content": content}]
            last = ""
            _vong = pick_keys("groq", keys)
            if key_dau and _vong:
                _i = int(key_dau) % len(_vong)
                _vong = _vong[_i:] + _vong[:_i]
            for key in _vong:
                mark_used("groq", key)
                try:
                    client = OpenAI(api_key=key,
                                    base_url="https://api.groq.com/openai/v1",
                                    timeout=120, max_retries=1)
                    # TẮT PHẦN "SUY NGHĨ": model vision còn sống trên Groq
                    # (qwen3.6) là model SUY LUẬN, mặc định nó viết cả khối
                    # <think> dài trước khi ra JSON. ĐO 06/08/2026 với 2 ảnh:
                    #   có nghĩ  -> 527 token trả về, 1,5s
                    #   không    -> 104 token trả về, 1,0s  (mô tả VẪN ĐÚNG)
                    # Ít token = ít cạn hạn mức 8.000 token/PHÚT của Groq = cả
                    # dây chuyền không phải ngồi chờ. Mô tả cảnh không cần suy
                    # luận nhiều bước nên tắt là đúng việc.
                    _kw = {"model": settings.GROQ_VISION_MODEL,
                           "messages": msgs, "temperature": 0.3,
                           "max_tokens": 900}
                    try:
                        resp = client.chat.completions.create(
                            reasoning_effort="none", **_kw)
                    except Exception as e_re:  # noqa: BLE001
                        # model KHÁC không nhận tham số này (Groq trả 400
                        # "`reasoning_effort` must be one of…") -> gọi lại
                        # kiểu thường, đừng để user đổi model là chết vision.
                        if "reasoning_effort" not in str(e_re):
                            raise
                        resp = client.chat.completions.create(
                            max_tokens=2600,
                            **{k: v for k, v in _kw.items()
                               if k != "max_tokens"})
                    mark_ok("groq", key)
                    return _extract_json(resp.choices[0].message.content or "")
                except (ValueError, json.JSONDecodeError) as e:
                    raise LLMError(f"Vision groq trả về không phải JSON: {e}")
                except Exception as e:  # noqa: BLE001
                    last = str(e)
                    if is_too_large_error(last):
                        # gửi quá nhiều/quá to -> caller giảm số ảnh. ĐỪNG phạt
                        # key: đây là lối đã đốt sạch 38 key (xem
                        # is_too_large_error).
                        raise LLMTooLarge(f"Vision: yêu cầu quá lớn cho hạn "
                                          f"mức token/phút: {last}")
                    if is_rate_limit_error(last):
                        mark_limited("groq", key, last)
                        continue         # key hết lượt -> thử key kế
                    if is_auth_error(last):
                        mark_invalid("groq", key)
                        continue         # key sai -> bỏ qua
                    raise LLMError(f"Vision groq lỗi: {last}")
            raise LLMError(
                f"Vision groq thất bại (hết lượt/lỗi tất cả key): {last}")

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
        # chỉ đánh dấu limited khi ĐÚNG là rate-limit (lỗi mạng thì tha key;
        # 413 'quá lớn' cũng THA — xem is_too_large_error)
        if is_too_large_error(str(e)):
            raise LLMTooLarge(f"Vision {provider}: yêu cầu quá lớn: {e}")
        if used_key and is_rate_limit_error(str(e)):
            mark_limited(provider, used_key, str(e))
        raise LLMError(f"Vision {provider} lỗi: {e}")
    raise LLMError(f"Provider không hỗ trợ vision: {provider}")
