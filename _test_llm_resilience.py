# -*- coding: utf-8 -*-
"""Test độ lì của lớp gọi LLM — bug anh Hùng 28/07: "key còn rất nhiều mà
thỉnh thoảng vẫn 'Cắt cơ bản (chưa qua AI)'".

Hai đường nổ XUYÊN QUA mọi lớp xoay key (trước bản sửa):
  1. Lỗi mạng/5xx thoáng qua -> complete_text dừng NGAY (không thử key khác).
  2. Model trả JSON hỏng -> complete_json ném LLMError NGAY (không gọi lại).

Test 1-5 patch `_call_once`/`complete_text` — có chủ đích: đây là test LOGIC
THỬ LẠI CỦA MÌNH, phải ép được đúng chuỗi lỗi (mạng thật không hẹn giờ được).
Test 6 gọi Groq THẬT (có key mới chạy) theo quy tắc thành-phần-thật.

Chạy: .venv\\Scripts\\python _test_llm_resilience.py  (exit 0 = pass)
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.ai import llm            # noqa: E402
from config import settings       # noqa: E402

FAILS: list = []


def check(name: str, cond: bool, note: str = ""):
    print(("  [OK ] " if cond else "  [FAIL] ") + name + (f" — {note}" if note else ""))
    if not cond:
        FAILS.append(name)


# ---------- 1. is_transient_error: nhận đúng, không nhận nhầm ----------
print("== 1. is_transient_error ==")
for msg in ("Connection error.", "Request timed out.",
            "Error code: 502 - Bad Gateway", "Error code: 503",
            "EOF occurred in violation of protocol (ssl)",
            "('Connection aborted.', RemoteDisconnected(...))"):
    check(f"transient: {msg[:40]!r}", llm.is_transient_error(msg))
for msg in ("Error code: 429 - rate limit reached", "invalid api key",
            "Error code: 413 - request too large",
            "LLM trả về không phải JSON hợp lệ", ""):
    check(f"KHONG transient: {msg[:40]!r}", not llm.is_transient_error(msg))
# 429 phải được nhận là rate-limit (đi đường cooldown, không phải transient)
check("429 van la rate-limit", llm.is_rate_limit_error("Error code: 429 x"))

# ---------- 2. complete_text: lỗi mạng thoáng qua -> thử key khác ----------
print("== 2. complete_text thu lai khi mang chap chon ==")
_orig_call = llm._call_once
_orig_keys = settings.llm_keys_for
calls = {"n": 0}


def _fake_call_fail_once(provider, key, prompt, system, temperature, model=None):
    calls["n"] += 1
    if calls["n"] == 1:
        raise RuntimeError("Connection error.")
    return "ket qua ok"


try:
    settings.llm_keys_for = lambda p: ["key_test_1", "key_test_2"]
    llm._call_once = _fake_call_fail_once
    out = llm.complete_text("hi", provider="groq")
    check("tra ve ket qua sau 1 cu timeout", out == "ket qua ok",
          f"goi {calls['n']} lan")
    check("goi dung 2 lan (key 2 cuu)", calls["n"] == 2)
finally:
    llm._call_once = _orig_call
    settings.llm_keys_for = _orig_keys

# ---------- 3. lỗi LẠ (không nhận diện) vẫn dừng ngay như cũ ----------
print("== 3. loi la van dung ngay (khong lap vo tan) ==")
calls["n"] = 0


def _fake_call_weird(provider, key, prompt, system, temperature, model=None):
    calls["n"] += 1
    raise RuntimeError("loi gi do rat la khong ai biet")


try:
    settings.llm_keys_for = lambda p: ["key_test_1", "key_test_2"]
    llm._call_once = _fake_call_weird
    try:
        llm.complete_text("hi", provider="groq")
        check("phai nem LLMError", False)
    except llm.LLMError:
        check("nem LLMError dung", True)
    check("chi goi 1 lan (khong retry loi la)", calls["n"] == 1,
          f"goi {calls['n']} lan")
finally:
    llm._call_once = _orig_call
    settings.llm_keys_for = _orig_keys

# ---------- 4. complete_json: JSON hỏng -> gọi lại kèm nhắc cứng ----------
print("== 4. complete_json goi lai khi JSON hong ==")
_orig_ct = llm.complete_text
jcalls: list = []


def _fake_ct_bad_then_good(prompt, system="", temperature=0.4,
                           provider=None, model=None):
    jcalls.append(system)
    if len(jcalls) == 1:
        return "day khong phai json dau nhe"
    return '{"clips": [1, 2]}'


try:
    llm.complete_text = _fake_ct_bad_then_good
    data = llm.complete_json("chon clip", system="he thong goc")
    check("parse duoc sau khi goi lai", data == {"clips": [1, 2]},
          f"goi {len(jcalls)} lan")
    check("goi dung 2 lan", len(jcalls) == 2)
    check("lan 2 co nhac CHI tra JSON", "CHỈ trả về" in jcalls[1])
    check("lan 2 giu system goc", "he thong goc" in jcalls[1])
finally:
    llm.complete_text = _orig_ct

# ---------- 5. JSON hỏng cả 3 lần -> bo cuoc, bao ro ----------
print("== 5. JSON hong ca 3 lan -> LLMError ==")
jcalls.clear()


def _fake_ct_always_bad(prompt, system="", temperature=0.4,
                        provider=None, model=None):
    jcalls.append(system)
    return "van khong phai json"


try:
    llm.complete_text = _fake_ct_always_bad
    try:
        llm.complete_json("chon clip")
        check("phai nem LLMError", False)
    except llm.LLMError as e:
        check("nem LLMError dung", "JSON" in str(e))
    check("goi dung 3 lan roi thoi", len(jcalls) == 3, f"goi {len(jcalls)} lan")
finally:
    llm.complete_text = _orig_ct

# ---------- 7. check_groq_key: dò ĐỦ MỌI model, kẹt model nào báo model đó ----------
print("== 7. check_groq_key do du moi model ==")
import io                          # noqa: E402
import urllib.error                # noqa: E402
import urllib.request              # noqa: E402
from email.message import Message  # noqa: E402

_orig_urlopen = urllib.request.urlopen
_orig_cfg = {n: getattr(settings, n, None) for n in
             ("GROQ_LLM_MODEL", "GROQ_LLM_MODEL_SMART",
              "GROQ_LLM_MODEL_CREATIVE", "GROQ_LLM_MODEL_HQ",
              "GROQ_LLM_FALLBACK")}


class _FakeResp:
    def __init__(self, hdrs: dict):
        self.headers = Message()
        for k, v in hdrs.items():
            self.headers[k] = str(v)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _mk_urlopen(per_model: dict):
    """per_model: model_id -> dict header (200) | int mã lỗi HTTP."""
    def _fake(req, timeout=None):
        import json as _j
        model = _j.loads(req.data.decode())["model"]
        spec = per_model.get(model, {"x-ratelimit-remaining-requests": 99,
                                     "x-ratelimit-remaining-tokens": 9999})
        if isinstance(spec, int):
            h = Message()
            h["x-ratelimit-reset-requests"] = "12m"
            raise urllib.error.HTTPError(
                "https://api.groq.com", spec, "err", h, io.BytesIO(b"{}"))
        return _FakeResp(spec)
    return _fake


try:
    settings.GROQ_LLM_MODEL = "m-main"
    settings.GROQ_LLM_MODEL_SMART = "co/m-smart"
    settings.GROQ_LLM_MODEL_CREATIVE = "m-creative"
    settings.GROQ_LLM_MODEL_HQ = ""
    settings.GROQ_LLM_FALLBACK = ""

    # 7a. moi model deu song -> ok
    urllib.request.urlopen = _mk_urlopen({})
    r = llm.check_groq_key("gsk_test")
    check("moi model song -> ok", r["kind"] == "ok", r["note"])

    # 7b. model SMART het luot (429) -> phai bao exhausted + neu ten model
    #     (bug cu: chi do model chinh nen van xanh)
    urllib.request.urlopen = _mk_urlopen({"co/m-smart": 429})
    r = llm.check_groq_key("gsk_test")
    check("smart 429 -> exhausted", r["kind"] == "exhausted", r["note"])
    check("note neu ten m-smart", "m-smart" in (r["note"] or ""), r["note"])
    check("note noi model khac van chay", "còn lại" in (r["note"] or ""))

    # 7c. model chinh CAN TOKEN (remaining_tokens=0) -> khong duoc xanh
    urllib.request.urlopen = _mk_urlopen(
        {"m-main": {"x-ratelimit-remaining-requests": 50,
                    "x-ratelimit-remaining-tokens": 0,
                    "x-ratelimit-reset-tokens": "8s"}})
    r = llm.check_groq_key("gsk_test")
    check("can token -> exhausted", r["kind"] == "exhausted", r["note"])
    check("note noi can token", "token" in (r["note"] or ""))

    # 7d. key sai (401) -> invalid ngay
    urllib.request.urlopen = _mk_urlopen({"m-main": 401})
    r = llm.check_groq_key("gsk_test")
    check("401 -> invalid", r["kind"] == "invalid", r["note"])

    # 7e. model bi go (404) khong ket toi key — cac model con lai song -> ok
    urllib.request.urlopen = _mk_urlopen({"m-creative": 404})
    r = llm.check_groq_key("gsk_test")
    check("404 model go -> van ok", r["kind"] == "ok", r["note"])
finally:
    urllib.request.urlopen = _orig_urlopen
    for n, v in _orig_cfg.items():
        setattr(settings, n, v)

# ---------- 8. KEY BỊ GROQ KHOÁ (org restricted, mã 400) ----------
print("== 8. key bi Groq KHOA (organization restricted) ==")
ORG_MSG = ("Error code: 400 - {'error': {'message': 'Organization has been "
           "restricted. Please reach out to support', 'type': 'invalid_request_error'}}")
check("nhan dien org restricted", llm.is_org_restricted(ORG_MSG))
check("khong nham voi 429", not llm.is_org_restricted("Error code: 429 rate limit"))
check("khong nham voi model go", not llm.is_org_restricted("model_not_found abc"))

# 8a. runtime: key DAU bi khoa -> mark_invalid + nhay key ke, van ra ket qua
calls["n"] = 0


def _fake_call_banned_first(provider, key, prompt, system, temperature, model=None):
    calls["n"] += 1
    if key == "key_bi_ban":
        raise RuntimeError(ORG_MSG)
    return "song nho key 2"


try:
    settings.llm_keys_for = lambda p: ["key_bi_ban", "key_song"]
    llm._call_once = _fake_call_banned_first
    out = llm.complete_text("hi", provider="groq")
    check("key ban khong giet ca luot", out == "song nho key 2",
          f"goi {calls['n']} lan")
    # key bi ban phai bi danh dau invalid -> lan sau xep CUOI vong xoay
    order = llm.pick_keys("groq", ["key_bi_ban", "key_song"])
    check("key ban xep cuoi vong xoay", order[-1] == "key_bi_ban", str(order))
finally:
    llm._call_once = _orig_call
    settings.llm_keys_for = _orig_keys

# 8b. TAT CA key deu bi khoa -> bao loi ngay, khong ngoi doi vo ich
calls["n"] = 0


def _fake_call_all_banned(provider, key, prompt, system, temperature, model=None):
    calls["n"] += 1
    raise RuntimeError(ORG_MSG)


try:
    settings.llm_keys_for = lambda p: ["ban1", "ban2"]
    llm._call_once = _fake_call_all_banned
    import time as _t
    t0 = _t.time()
    try:
        llm.complete_text("hi", provider="groq")
        check("phai nem LLMError", False)
    except llm.LLMError:
        check("nem LLMError dung", True)
    check("khong ngoi doi 7s vo ich", _t.time() - t0 < 5.0,
          f"{_t.time()-t0:.1f}s")
finally:
    llm._call_once = _orig_call
    settings.llm_keys_for = _orig_keys

# 8c. checker: 400 kem body org-restricted -> invalid + note KHOA
try:
    settings.GROQ_LLM_MODEL = "m-main"
    settings.GROQ_LLM_MODEL_SMART = ""
    settings.GROQ_LLM_MODEL_CREATIVE = ""
    settings.GROQ_LLM_MODEL_HQ = ""
    settings.GROQ_LLM_FALLBACK = ""

    def _fake_urlopen_org(req, timeout=None):
        h = Message()
        raise urllib.error.HTTPError(
            "https://api.groq.com", 400, "err", h,
            io.BytesIO(b'{"error":{"message":"Organization has been restricted."}}'))

    urllib.request.urlopen = _fake_urlopen_org
    r = llm.check_groq_key("gsk_test")
    check("checker: 400 org -> invalid", r["kind"] == "invalid", r["note"])
    check("checker: note noi bi KHOA", "KHOÁ" in (r["note"] or ""), r["note"])
finally:
    urllib.request.urlopen = _orig_urlopen
    for n, v in _orig_cfg.items():
        setattr(settings, n, v)

# ---------- 6. GROQ THẬT (có key mới chạy): complete_json ra dict ----------
print("== 6. Groq that (smoke) ==")
real_keys = settings.llm_keys_for("groq")
if real_keys:
    try:
        data = llm.complete_json(
            'Trả về đúng JSON này, không thêm gì khác: {"ok": true}')
        check("Groq that tra JSON parse duoc", isinstance(data, dict))
    except llm.LLMError as e:
        check("Groq that", False, str(e)[:120])
else:
    print("  [BO QUA] khong co key groq trong env")

print()
if FAILS:
    print(f"KET QUA: {len(FAILS)} FAIL -> {FAILS}")
    sys.exit(1)
print("KET QUA: TAT CA PASS")
