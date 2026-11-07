# -*- coding: utf-8 -*-
"""CỔNG 114 — GROQ KHÔNG CHẠY THÌ TỰ CHUYỂN GEMINI, VẪN ĐÚNG YÊU CẦU CẮT GHÉP.

Anh Hùng 07/11/2026: Groq hết key hay không chạy thì tự chuyển Gemini, nhưng
Gemini vẫn phải cắt ghép theo yêu cầu có sẵn của tool. Không gọi mạng, không tốn
lượt: thay `_call_once` / `requests.post` bằng kịch bản lỗi.
"""
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
TMP = tempfile.mkdtemp(prefix="bq_test_dp_")
os.environ["BQ_DATA_DIR"] = TMP
os.environ["BQ_DB_PATH"] = os.path.join(TMP, "s.db")
os.environ.pop("GEMINI_DU_PHONG", None)
import requests  # noqa: E402

from app.ai import key_health, llm  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402
from app.queue.worker import CanceledError  # noqa: E402
from config import settings  # noqa: E402

CFG = type(settings)
DAT = HONG = 0
SO_CASE = [0]
GOI = []
KICH = {}
_GOC = llm._call_once


def ok(dk, ten, ct=""):
    global DAT, HONG
    DAT, HONG = DAT + bool(dk), HONG + (not dk)
    print("  ĐẠT " if dk else "  HỎNG", ten, ct)


def gia_call(provider, key, prompt, system, temperature, **k):
    GOI.append((provider, key, prompt, system, getattr(llm._LAN, "gemini_model", "")))
    h = KICH.get(provider)
    if h is None:
        raise AssertionError("không có kịch bản cho " + provider)
    llm._LAN.ket_thuc = "stop"
    v = h(key) if callable(h) else h
    if isinstance(v, BaseException):
        raise v
    return v


def moi(groq=None, gemini=None, gem_key=True, provider="groq"):
    """Case mới: key mới hoàn toàn để sổ cooldown không dính case trước."""
    SO_CASE[0] += 1
    n = SO_CASE[0]
    CFG.GROQ_API_KEYS = f"gk{n}a,gk{n}b"
    CFG.GROQ_KEYS_FILE = ""
    CFG.GEMINI_API_KEY = f"mk{n}a" if gem_key else ""
    CFG.GEMINI_DU_PHONG = True
    CFG.LLM_PROVIDER = provider
    KICH.clear()
    if groq is not None:
        KICH["groq"] = groq
    if gemini is not None:
        KICH["gemini"] = gemini
    GOI.clear()
    llm._KEY_STATE.clear()
    llm._DP_GROQ_NGHI_TOI = 0.0
    llm.reset_usage()


def nha():
    return [g[0] for g in GOI]


llm._call_once = gia_call
llm._retry_sleep = lambda s: None
LOI = {
    "429 hết lượt": RuntimeError("Error code: 429 - rate_limit_exceeded, please retry"),
    "Groq khoá tổ chức": RuntimeError("Error code: 400 - Organization has been restricted"),
    "key sai": RuntimeError("Error code: 401 - invalid_api_key"),
    "mất mạng/503": RuntimeError("Error code: 503 - service unavailable"),
    "model bị gỡ": RuntimeError("Error code: 404 - model_not_found"),
}

print("CA 1: Groq khoẻ -> không đụng Gemini")
moi(groq="kq groq", gemini="kq gemini")
ok(llm.complete_text("p") == "kq groq" and nha() == ["groq"], "Groq chạy thì Gemini 0 lượt", str(nha()))
ok(llm.so_luot_du_phong() == 0, "bộ đếm dự phòng = 0")
moi(groq='{"a":1}', gemini='{"b":2}')
ok(llm.complete_json("p") == {"a": 1} and "gemini" not in nha(), "JSON Groq đúng -> giữ Groq")

print("CA 2: mọi kiểu Groq chết -> chuyển Gemini, cùng prompt")
for ten, loi in LOI.items():
    moi(groq=loi, gemini="kq gemini")
    r = llm.complete_text("PROMPT Y HỆT", system="HỆ THỐNG")
    gem = [g for g in GOI if g[0] == "gemini"]
    ok(r == "kq gemini" and gem and gem[0][2] == "PROMPT Y HỆT" and gem[0][3] == "HỆ THỐNG",
       f"{ten} -> Gemini, giữ nguyên prompt + system", str(nha()[:4]))
    ok(gem and gem[0][4] == settings.GEMINI_DU_PHONG_MODEL, f"{ten}: dùng model dự phòng", gem[0][4] if gem else "")
    ok(llm.so_luot_du_phong() == 1, f"{ten}: đếm 1 lượt dự phòng")
moi(groq=LOI["Groq khoá tổ chức"], gemini="kq")
for k in settings.groq_keys():
    key_health.record("groq", k, "chat", "restricted", "organization_restricted")
ok(llm.complete_text("p") == "kq" and nha() == ["gemini"], "mọi key đã ghi sổ bị khoá -> sang thẳng Gemini", str(nha()))

print("CA 3: JSON Groq rỗng / bị cắt / hỏng cũng sang Gemini")
moi(groq="", gemini='{"ok":1}')
ok(llm.complete_json("p") == {"ok": 1}, "Groq trả RỖNG 3 lượt -> Gemini", str(nha()))
moi(groq="không phải json", gemini='{"ok":2}')
ok(llm.complete_json("p") == {"ok": 2}, "Groq trả JSON hỏng 3 lượt -> Gemini", str(nha()))

print("CA 4: nhớ Groq đang nghỉ, hết nghỉ thì quay lại")
moi(groq=LOI["mất mạng/503"], gemini="g")
llm.complete_text("p")
GOI.clear()
llm.complete_text("p2")
ok(nha() == ["gemini"], "lượt sau KHÔNG đi lại hết key Groq chết", str(nha()))
llm._DP_GROQ_NGHI_TOI = 0.0
llm._KEY_STATE.clear()
CFG.GROQ_API_KEYS = "gk_hoi_a,gk_hoi_b"
KICH["groq"] = "groq hồi"
GOI.clear()
ok(llm.complete_text("p3") == "groq hồi" and nha() == ["groq"], "hết nghỉ -> Groq chạy chính lại")
moi(groq=RuntimeError("Error code: 413 - Request too large on tokens per minute"), gemini="g")
ok(llm.complete_text("p") == "g", "413 Groq -> Gemini làm hộ")
ok(llm._DP_GROQ_NGHI_TOI == 0.0, "413 là lỗi của yêu cầu đó, KHÔNG cho Groq nghỉ")
moi(groq="groq khoẻ", gemini=RuntimeError("Error code: 503 - unavailable"))
llm._DP_GROQ_NGHI_TOI = llm.time.monotonic() + 100
ok(llm.complete_text("p") == "groq khoẻ", "đang nghỉ mà Gemini lỗi -> thử lại Groq", str(nha()))

print("CA 5: không được chuyển khi không nên")
huy = CanceledError("huỷ")
moi(groq=huy, gemini="g")
try:
    llm.complete_text("p")
    ok(False, "Huỷ phải nổi lên")
except CanceledError:
    ok("gemini" not in nha(), "bấm Huỷ -> dừng, KHÔNG gọi Gemini")
moi(groq=llm.LLMError("AI phản hồi quá lâu; đã giữ phần phân tích"), gemini="g")
try:
    llm.complete_text("p")
    ok(False, "hết ngân sách job phải nổi lên")
except llm.LLMError:
    ok("gemini" not in nha(), "hết ngân sách thời gian job -> không đổi nhà cung cấp")
moi(groq=LOI["429 hết lượt"], gem_key=False)
try:
    llm.complete_text("p")
    ok(False, "không có key Gemini phải báo lỗi cũ")
except llm.LLMError as e:
    ok("gemini" not in nha() and "dự phòng" not in str(e), "chưa có key Gemini -> y hệt bản cũ")
moi(groq=LOI["429 hết lượt"], gemini="g")
CFG.GEMINI_DU_PHONG = False
try:
    llm.complete_text("p")
    ok(False, "tắt dự phòng phải báo lỗi cũ")
except llm.LLMError:
    ok("gemini" not in nha(), "GEMINI_DU_PHONG=0 -> không chuyển")
moi(groq="g", gemini="kq gemini", provider="gemini")
ok(llm.complete_text("p") == "kq gemini" and GOI[0][4] == "", "user chọn hẳn Gemini -> dùng GEMINI_MODEL, không ép dự phòng")
moi(groq=LOI["429 hết lượt"], gemini="g")
try:
    llm.complete_text("p", provider="groq")
    ok(False, "provider tường minh phải giữ nguyên")
except llm.LLMError:
    ok("gemini" not in nha(), "gọi tường minh provider='groq' -> không chuyển")

print("CA 6: Gemini cũng trục trặc")
dem = [0]


def het_phut(key):
    dem[0] += 1
    if dem[0] == 1:
        return RuntimeError("Error code: 429 - quota exceeded. Please retry in 51s")
    return "qua phút"


moi(groq=LOI["Groq khoá tổ chức"], gemini=het_phut)
ok(llm.complete_text("p") == "qua phút", "Gemini 429 theo phút -> đợi rồi thử lại", f"{dem[0]} lượt")
moi(groq=LOI["429 hết lượt"], gemini=RuntimeError("Error code: 429 - quota exceeded for generate_content_free_tier_requests per day. Please retry in 16h1m0.5s."))
try:
    llm.complete_text("p")
    ok(False, "cả hai hết lượt phải báo lỗi")
except llm.LLMError as e:
    ok(llm.is_rate_limit_error(str(e)) and "Gemini dự phòng cũng lỗi" in str(e),
       "cả hai hết lượt -> lỗi kiểu hết lượt, để tầng trên ĐỢI (không cắt cơ bản)", str(e)[:70])
vong = [k for k in GOI if k[0] == "gemini"]
ok(len(vong) <= 2, "hết lượt NGÀY thì không đợi 16 tiếng", f"{len(vong)} lượt Gemini")


def tien(key):
    return RuntimeError("Gemini Error code: 402 - Your prepayment credits are depleted.") if key.endswith("a") else "key b còn tiền"


moi(groq=LOI["429 hết lượt"], gemini=tien)
CFG.GEMINI_API_KEY = f"mk{SO_CASE[0]}a,mk{SO_CASE[0]}b"
ok(llm.complete_text("p") == "key b còn tiền", "key Gemini hết tiền -> xoay key khác", str(nha()[-2:]))
moi(groq=LOI["429 hết lượt"], gemini=llm.LLMContentBlocked("block_reason=SAFETY"))
try:
    llm.complete_text("p")
    ok(False, "chặn nội dung phải nổi lên")
except llm.LLMContentBlocked:
    ok(True, "Gemini chặn nội dung -> báo đúng LLMContentBlocked")
moi(groq=LOI["429 hết lượt"], gemini=RuntimeError("Gemini Error code: 404 - This model models/x is no longer available to new users"))
try:
    llm.complete_text("p")
    ok(False, "model Gemini bị gỡ phải báo lỗi")
except llm.LLMError as e:
    ok("Gemini dự phòng cũng lỗi" in str(e) and "no longer available" in str(e), "model dự phòng bị gỡ -> báo rõ", str(e)[-70:])
ok(llm._is_model_missing_error("models/x is no longer available to new users"), "404 'no longer available' nhận đúng là model bị gỡ")
moi(groq=LOI["429 hết lượt"], gemini="g")
llm.complete_text("p")
ok(getattr(llm._LAN, "gemini_model", "") == "", "model dự phòng không rò sang lượt sau trong thread")
log = list(Path(TMP, "logs").glob("du_phong_*.log"))
txt = log[0].read_text(encoding="utf-8") if log else ""
ok(log and "chuyển Gemini" in txt, "có nhật ký chuyển nhà cung cấp")
ok("gk1a" not in txt and "mk1a" not in txt, "nhật ký không lộ key")

print("CA 7: nhiều làn cùng lúc")
moi(groq=LOI["429 hết lượt"], gemini=lambda key: "g:" + getattr(llm._LAN, "gemini_model", ""))
kq = []


def lan():
    kq.append(llm.complete_text("p"))


ts = [threading.Thread(target=lan) for _ in range(8)]
[t.start() for t in ts]
[t.join() for t in ts]
ok(len(kq) == 8 and all(x == "g:" + settings.GEMINI_DU_PHONG_MODEL for x in kq), "8 làn đều ra Gemini đúng model", str(set(kq)))

print("CA 8: Gemini đi đúng đường REST với model dự phòng")
llm._call_once = _GOC
CFG.GEMINI_MODEL = "gemini-2.5-flash"


class R:
    ok = True
    status_code = 200

    def json(self):
        return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "x"}]}}], "usageMetadata": {}}


URL = []
requests.post = lambda url, **k: (URL.append((url, k["json"])), R())[1]
llm._LAN.gemini_model = "gemini-3.5-flash-lite"
llm._call_once("gemini", "k", "p", "", .2, json_mode=True)
llm._LAN.gemini_model = ""
ok("gemini-3.5-flash-lite:" in URL[-1][0], "URL là model dự phòng, không phải GEMINI_MODEL", URL[-1][0][-50:])
ok("thinkingConfig" not in URL[-1][1]["generationConfig"], "dòng 3.x không ép thinkingBudget")
llm._call_once = gia_call

print("CA 9: giữ đúng yêu cầu cắt ghép khi dùng Gemini")
g = M1._gon_so_doan
s11 = [[i * 20.0, i * 20.0 + 15] for i in range(11)]
r = g(s11)
ok(len(r) <= 6, "11 đoạn -> tối đa 6", f"{len(r)} đoạn")
ok(all(r[i][0] < r[i + 1][0] for i in range(len(r) - 1)), "vẫn đúng thứ tự thời gian")
ok(r[0][0] == 0 and r[-1][1] >= s11[-1][1] - 15, "không cụt đầu/cuối")
s_xa = [[i * 100.0, i * 100.0 + 5 + i] for i in range(8)]
r = g(s_xa)
ok(len(r) == 6 and [0.0, 5.0] in r and [100.0, 106.0] not in r, "khe xa -> giữ đoạn đầu, bỏ đoạn ngắn nhất, không nối đoạn xa", str(r[:2]))
s_ng = [[300.0, 320.0], [10.0, 30.0], [40.0, 60.0], [70.0, 90.0], [100.0, 120.0], [130.0, 150.0], [160.0, 180.0], [190.0, 210.0]]
r = g(s_ng)
ok(len(r) <= 6 and r[0][0] == 300.0, "hook đặt trước (ngược thời gian) vẫn giữ ở đầu", str(r[0]))
s6 = [[i * 20.0, i * 20.0 + 15] for i in range(6)]
ok(g(s6) == s6, "đủ 6 đoạn thì KHÔNG đổi gì")
ok(g([]) == [], "rỗng -> rỗng")


def tr(dur=600.0):
    cau = "So today we are going to show you how the whole thing works and why it matters"
    segs, words, t = [], [], 0.0
    while t < dur - 6:
        segs.append({"start": t, "end": t + 6, "text": cau})
        for k, w in enumerate(cau.split()):
            words.append({"word": w, "start": t + k * .3, "end": t + k * .3 + .25})
        t += 6
    return {"language": "en", "duration": dur, "segments": segs, "words": words, "text": cau}


seg_vun = [[i * 21.0, i * 21.0 + 15.0] for i in range(11)]   # khe 6 s, không bị bước làm mượt nối sẵn
JS = json.dumps({"clips": [{"title": "Tiêu đề", "title_en": "T", "hook": "h", "score": 90, "segments": seg_vun}]})
PROMPT = {}


def lay_prompt(nha_nao):
    def f(key):
        PROMPT[nha_nao] = GOI[-1][2:4]
        return JS
    return f


D = {"min_len": 100.0, "max_len": 180.0, "count": 3, "purpose": "highlight", "style": "drama"}
M1_refine = M1._refine_clip
M1._refine_clip = lambda c, *a, **k: c
moi(groq=lay_prompt("groq"), gemini=lay_prompt("gemini"))
cg, _ = M1._llm_select_clips(tr(), 600.0, None, {}, D, digest=[], nghe_xem="", audit={})
n_groq = max(len(c["segments"]) for c in cg) if cg else 0
moi(groq=LOI["Groq khoá tổ chức"], gemini=lay_prompt("gemini"))
ck, _ = M1._llm_select_clips(tr(), 600.0, None, {}, D, digest=[], nghe_xem="", audit={})
n_gem = max(len(c["segments"]) for c in ck) if ck else 0
ok(PROMPT.get("groq") and PROMPT["groq"] == PROMPT.get("gemini"), "Gemini nhận Y HỆT prompt + system chọn đoạn của Groq")
ok(ck and n_gem <= 6, "Gemini ghép vụn -> vẫn <= 6 đoạn", f"{n_gem} đoạn")
ok(n_groq == 11, "Groq không bị áp bước gọn (kết quả cũ không đổi)", f"Groq {n_groq} đoạn")
M1._refine_clip = M1_refine

print("CA 10: cả video chạy qua generate_highlights khi Groq chết")
from app.core.analysis import _set  # noqa: E402
from app.database import db  # noqa: E402

pid = db.execute("INSERT INTO projects(name,assets_dir) VALUES('k','x')").lastrowid
vid = db.execute("INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)", (pid, os.path.join(TMP, "v.mp4"), 600.0)).lastrowid
_set(vid, "transcript", "done", tr())


class Ctx:
    def progress(self, p, m=""):
        pass

    def check_canceled(self):
        pass

    def __getattr__(self, n):
        return lambda *a, **k: None


JS2 = json.dumps({"clips": [{"title": "Tiêu đề A", "title_en": "Title A", "hook": "h", "score": 90, "segments": [[0, 60], [100, 170]]},
                            {"title": "Tiêu đề B", "title_en": "Title B", "hook": "h", "score": 88, "segments": [[200, 330]]}]})
CFG.AI_MULTIPASS = False
import app.ai.continuity_cut as CC  # noqa: E402
CC.review = lambda segs, *a, **k: (segs, {"status": "reviewed", "changed": False})
moi(groq=LOI["429 hết lượt"], gemini=JS2)
res = M1.generate_highlights({"video_id": vid, "preset": D}, Ctx())
rows = db.query("SELECT signals FROM clips WHERE video_id=?", (vid,))
sigs = [db.loads(r["signals"]) for r in rows]
ok(sigs and all(s.get("llm_used") for s in sigs), "Part đi đường AI, KHÔNG rơi cắt cơ bản", f"{len(sigs)} Part")
ok(sigs and all(s.get("ai_du_phong") == "gemini" for s in sigs), "Part ghi rõ đã dùng Gemini dự phòng")
ok(any("Gemini dự phòng" in str(w) for w in (res or {}).get("warnings", [])) or any("Gemini dự phòng" in json.dumps(res, ensure_ascii=False, default=str) for _ in [0]), "kết quả job báo đã dùng dự phòng")

print(f"\nCỔNG 114: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
