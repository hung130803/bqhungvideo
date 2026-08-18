# -*- coding: utf-8 -*-
"""CỔNG 69 — **GROQ GỠ MODEL THÌ APP PHẢI SỐNG, VÀ KHÔNG ĐƯỢC ĐỔ OAN CHO KEY**
(17/08/2026).

VÌ SAO CÓ CỔNG NÀY — LỖI THẬT, ĐÃ RA TỚI MÁY ANH HÙNG:
Groq khai tử `llama-3.3-70b-versatile`. App ghi CỨNG tên đó ở **cả**
`GROQ_LLM_MODEL` **lẫn** `GROQ_LLM_FALLBACK`, mà lưới rơi-về-dự-phòng trong
`llm._call_once` lại có điều kiện `model != fb` -> **lưới không bao giờ chạy**.
Mọi lượt gọi ra 404, cắt/thay giọng/reup chết cả dây chuyền. Tệ hơn: lời lỗi
`LLMError: Gọi groq thất bại: Error code: 404 ...` khiến anh Hùng đọc xong
tưởng **hết hạn mức 41 key** ("key groq tôi bao nhiêu mà sao hết được").

Cổng phủ đúng 5 mệnh đề, và MỆNH ĐỀ 3 là quan trọng nhất:
  1. Model trong cấu hình phải CÒN SỐNG (hỏi thẳng `/models`, không tin tên
     ghi trong mã — Groq đổi model theo tháng).
  2. Model chính và model dự phòng phải **KHÁC NHAU** (đúng lỗi kiến trúc trên).
  3. 404 -> **SANG MODEL KẾ, TUYỆT ĐỐI KHÔNG KHOÁ KEY**. Đây là cùng lớp bệnh
     với 413 đã đốt sạch 38 key (xem `llm.is_too_large_error`): lỗi CỦA YÊU CẦU
     / CỦA APP bị đọc nhầm thành lỗi CỦA KEY.
  4. Mỗi mã lỗi một đường: 429 xoay key · 413 thu nhỏ · 404 đổi model. Không
     được trộn.
  5. Lời báo 404 phải KHÁC HẲN lời báo hết hạn mức (đúng chỗ đã làm anh Hùng
     hiểu sai), và không còn tên model chết ghi cứng ở đâu.

CÁCH DỰNG — ĐI ĐƯỜNG THẬT, KHÔNG DỰNG DỮ LIỆU GIẢ VÒNG QUA:
Các ca hỏng vá `openai.OpenAI` (đúng RANH GIỚI MẠNG) rồi gọi
`llm.complete_text` THẬT — tức toàn bộ `_call_once` + dây chuyền model + vòng
xoay key + bảng phân loại lỗi đều là mã thật. Vá ở tầng cao hơn (vá
`_call_once`) là tự bỏ qua đúng thứ đang test. Kèm 2 ca gọi Groq THẬT để chứng
minh bảng phân loại khớp với thân lỗi Groq ĐANG trả về hôm nay, không phải
thân lỗi tôi tưởng tượng.

TỰ KIỂM (mục 8): gỡ chốt ra thì cổng PHẢI đỏ — bộ dò quét tĩnh phải bắt được
tên model chết cấy vào, và bộ so lời báo phải từ chối lời báo sai. Không có
mục này thì cổng chỉ là con dấu (bài học cổng 56d/64).

  .venv\\Scripts\\python -u _test_groq_model.py
  BQ_BO_MANG=1 .venv\\Scripts\\python -u _test_groq_model.py   # bỏ ca gọi thật
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent          # KHÔNG ghi cứng đường repo
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:                                        # in tiếng Việt khi ghi ra file
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                           # noqa: BLE001
        pass

BO_MANG = os.environ.get("BQ_BO_MANG", "") == "1"

DAT = HONG = 0
_HONG: list = []


def ok(dieu: str, tot: bool, chi_tiet: str = "") -> bool:
    global DAT, HONG
    if tot:
        DAT += 1
        print(f"  [ĐẠT ] {dieu}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        _HONG.append(dieu)
        print(f"  [HỎNG] {dieu}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return tot


# ══════════════════════════════════════════════════════════════════════════
# BỘ GIẢ LẬP RANH GIỚI MẠNG — thay đúng `openai.OpenAI`, giữ nguyên mã app
# ══════════════════════════════════════════════════════════════════════════
class _Msg:
    def __init__(self, c): self.content = c


class _Choice:
    def __init__(self, c): self.message = _Msg(c)


class _Resp:
    def __init__(self, c): self.choices = [_Choice(c)]


class _Completions:
    def __init__(self, cl): self._cl = cl

    def create(self, model=None, messages=None, temperature=None,
               extra_body=None, **kw):
        _StubOpenAI.NHAT_KY.append((self._cl.api_key, model))
        return _Resp(_StubOpenAI.HOOK(self._cl.api_key, model))


class _Chat:
    def __init__(self, cl): self.completions = _Completions(cl)


class _StubOpenAI:
    """Thay `openai.OpenAI`. `HOOK(key, model)` trả CHUỖI nội dung, hoặc ném."""
    HOOK = staticmethod(lambda k, m: "OK")
    NHAT_KY: list = []

    def __init__(self, api_key=None, base_url=None, timeout=None,
                 max_retries=None, **kw):
        self.api_key = api_key
        self.chat = _Chat(self)


#: thân lỗi ĐÚNG như Groq trả về (chép từ lượt gọi thật 17/08/2026)
L404 = ("Error code: 404 - {'error': {'message': 'The model "
        "`llama-3.3-70b-versatile` does not exist or you do not have access "
        "to it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}")
L429 = ("Error code: 429 - {'error': {'message': 'Rate limit reached for "
        "model `x` in organization `org_1` service tier `on_demand` on tokens "
        "per minute (TPM): Limit 8000, Used 8000. Please try again in 2.5s.', "
        "'type': 'tokens', 'code': 'rate_limit_exceeded'}}")
L413 = ("Error code: 413 - {'error': {'message': 'Request too large for model "
        "`x` on tokens per minute (TPM): Limit 8000, Requested 12000, please "
        "reduce your message size and try again.', 'code': "
        "'rate_limit_exceeded'}}")

KEY_GIA = ["gsk_test_A", "gsk_test_B", "gsk_test_C"]

#: model Groq ĐÃ CHẾT — không dòng mã sống nào được ghi cứng mấy tên này.
CHET = ("llama-3.3-70b-versatile", "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192",
        "mixtral-8x7b-32768", "gemma2-9b-it", "gemma-7b-it",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct")


#: thư mục KHÔNG phải mã của repo này (bản sao của luồng khác, thư viện, bản build)
BO_QUA_DIR = {"__pycache__", ".git", ".venv", ".venv-build", ".claude",
              "dist", "build", "_lib", "_piper", "node_modules"}


def _chuoi_gia_tri(p: Path) -> list:
    """Mọi hằng chuỗi **MANG GIÁ TRỊ** trong file — BỎ comment VÀ docstring.

    Đây là chỗ phải cân đúng giữa hai bẫy ngược nhau của repo này:
      · quét thô `"x" in text` -> **ĐỎ OAN VĨNH VIỄN**, vì ghi chú/docstring ở
        đây CỐ Ý nhắc đích danh tên model đã chết để cảnh báo người sau (đã sập
        ở cổng 47/51/53/54 — và sập lại đúng ở bản đầu của cổng này: docstring
        của `LLMModelMissing` bị kể là vi phạm).
      · bỏ luôn mọi token STRING (cách cổng 55/58 làm) -> **PASS OAN**, vì thứ
        đang truy CHÍNH LÀ hằng chuỗi tên model (bài học cổng 56d).
    Nên dùng AST: giữ `ast.Constant` chuỗi, nhưng loại docstring của
    module/class/hàm và mọi câu lệnh chỉ-có-một-chuỗi (doc-comment trá hình).
    """
    import ast
    try:
        cay = ast.parse(p.read_text(encoding="utf-8", errors="replace"),
                        filename=str(p))
    except Exception as e:                                  # noqa: BLE001
        return [f"<<LỖI ĐỌC {e}>>"]
    bo = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.ClassDef, ast.FunctionDef,
                            ast.AsyncFunctionDef)):
            than = getattr(nut, "body", None) or []
            if than and isinstance(than[0], ast.Expr) \
                    and isinstance(than[0].value, ast.Constant) \
                    and isinstance(than[0].value.value, str):
                bo.add(id(than[0].value))
        # chuỗi đứng một mình làm câu lệnh = ghi chú, không phải giá trị
        if isinstance(nut, ast.Expr) and isinstance(nut.value, ast.Constant) \
                and isinstance(nut.value.value, str):
            bo.add(id(nut.value))
    return [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in bo]


def quet_model_chet(goc: Path, bo_bo_do: bool = True) -> list:
    """Trả về [(file, tên model chết)] tìm thấy trong HẰNG GIÁ TRỊ của mã sống.

    `bo_bo_do=False`: quét MỌI file .py (dùng cho mục TỰ KIỂM 8b — file cấy vào
    mang tiền tố của bộ đo nên nếu vẫn lọc thì bộ dò tự bỏ qua chính phép thử,
    và mục tự kiểm hoá ra lại là một con dấu nữa)."""
    thay = []
    for p in sorted(goc.rglob("*.py")):
        if BO_QUA_DIR & set(p.parts):
            continue
        if bo_bo_do and p.name.startswith(("_test_", "_do_", "_pha_")):
            continue
        for s in _chuoi_gia_tri(p):
            for md in CHET:
                if md in s:
                    thay.append((str(p.relative_to(REPO)), md))
    return thay


# ══════════════════════════════════════════════════════════════════════════
def main() -> int:
    from config import settings
    from app.ai import llm

    # key GIẢ phải gán lên LỚP: `groq_keys` là @classmethod đọc `cls.…`,
    # gán lên instance thì nó không thấy (bẫy đã sập ở cổng 67).
    settings_cls = type(settings)
    goc_keys = settings_cls.GROQ_API_KEYS
    goc_file = settings_cls.GROQ_KEYS_FILE
    goc_model = settings_cls.GROQ_LLM_MODEL
    goc_fb = settings_cls.GROQ_LLM_FALLBACK
    goc_chain = getattr(settings_cls, "GROQ_LLM_CHAIN", "")
    goc_openai = None

    def dat_key_gia():
        settings_cls.GROQ_API_KEYS = "\n".join(KEY_GIA)
        settings_cls.GROQ_KEYS_FILE = ""

    def khoi_phuc():
        settings_cls.GROQ_API_KEYS = goc_keys
        settings_cls.GROQ_KEYS_FILE = goc_file
        settings_cls.GROQ_LLM_MODEL = goc_model
        settings_cls.GROQ_LLM_FALLBACK = goc_fb
        settings_cls.GROQ_LLM_CHAIN = goc_chain

    goc_do = llm.models_groq_con_song

    def reset(models="M_CHET,M_SONG,M_SONG2"):
        """Dọn sạch sổ key + sổ model chết + ép dây chuyền model tường minh."""
        llm._KEY_STATE.clear()
        llm._GROQ_DEAD_MODELS.clear()
        _StubOpenAI.NHAT_KY = []
        ms = [m.strip() for m in models.split(",")]
        settings_cls.GROQ_LLM_MODEL = ms[0]
        settings_cls.GROQ_LLM_FALLBACK = ms[1] if len(ms) > 1 else ""
        settings_cls.GROQ_LLM_CHAIN = ",".join(ms[2:])
        # TẮT HẲN bộ tự-dò ở các ca giả lập: phải ép lượt gọi đi qua ĐÚNG đường
        # 404, chứ không để nó loại model chết TRƯỚC khi gọi.
        # BẪY ĐÃ SẬP Ở BẢN ĐẦU CỦA CỔNG NÀY: chỉ đặt `_GROQ_SONG["models"]`
        # rỗng là KHÔNG đủ — rỗng nghĩa là "chưa biết" nên hàm đi đọc CACHE ĐĨA
        # (`groq_models.json`) rồi lấy được danh sách THẬT, lọc sạch model bịa
        # rồi trả về model thật. Cổng khi đó đo model `openai/gpt-oss-120b`
        # trong khi tưởng đang đo `M_CHET` -> hỏng 3 mục vì lý do NGƯỢC HẲN.
        llm.models_groq_con_song = lambda *a, **k: frozenset()

    def phat_key():
        return {k[1]: v.get("state") for k, v in llm._KEY_STATE.items()
                if v.get("state") in ("limited", "invalid")}

    try:
        import openai
        goc_openai = openai.OpenAI

        # ───────────────────────────────────────────────────────────────
        print("\n=== 1. MODEL TRONG CẤU HÌNH PHẢI CÒN SỐNG (hỏi /models thật)")
        if BO_MANG:
            print("  (bỏ qua: BQ_BO_MANG=1)")
        else:
            khoi_phuc()
            llm._GROQ_SONG["models"] = frozenset()
            llm._GROQ_SONG["ts"] = 0.0
            song = llm.models_groq_con_song(force=True)
            ok("hỏi được danh sách model của Groq", bool(song),
               f"{len(song)} model")
            if song:
                for ten, gt in (("model CHÍNH", settings.GROQ_LLM_MODEL),
                                ("model DỰ PHÒNG", settings.GROQ_LLM_FALLBACK)):
                    ok(f"{ten} còn sống", gt in song, f"«{gt}»")
                for gt in [s.strip() for s in
                           str(getattr(settings, "GROQ_LLM_CHAIN", "") or "")
                           .split(",") if s.strip()]:
                    ok(f"model dây chuyền «{gt}» còn sống", gt in song)
                from app.ai import cham_dich
                for gt in cham_dich.MODEL_HOI_DONG:
                    ok(f"hội đồng chấm dịch «{gt}» còn sống", gt in song)
                gv = str(getattr(settings, "GROQ_VISION_MODEL", "") or "")
                if gv:
                    ok(f"model XEM HÌNH «{gv}» còn sống", gv in song)
                gw = str(getattr(settings, "GROQ_WHISPER_MODEL", "") or "")
                if gw:
                    ok(f"model CHÉP LỜI «{gw}» còn sống", gw in song)

        # ───────────────────────────────────────────────────────────────
        print("\n=== 2. CHÍNH ≠ DỰ PHÒNG (đúng lỗi kiến trúc làm app chết)")
        khoi_phuc()
        ok("model chính KHÁC model dự phòng",
           settings.GROQ_LLM_MODEL != settings.GROQ_LLM_FALLBACK,
           f"«{settings.GROQ_LLM_MODEL}» vs «{settings.GROQ_LLM_FALLBACK}»")
        ok("dây chuyền có ÍT NHẤT 2 model",
           len(llm.chuoi_model_groq()) >= 2, str(llm.chuoi_model_groq()))

        # ───────────────────────────────────────────────────────────────
        print("\n=== 3. 404 -> SANG MODEL KẾ, KHÔNG KHOÁ KEY (mệnh đề trung tâm)")
        openai.OpenAI = _StubOpenAI
        dat_key_gia()
        reset()

        def hook_404(key, model):
            if model == "M_CHET":
                raise RuntimeError(L404)
            return "TRA LOI TU MODEL KE"
        _StubOpenAI.HOOK = staticmethod(hook_404)
        out = llm.complete_text("x")
        ok("vẫn ra kết quả dù model đầu 404", out == "TRA LOI TU MODEL KE",
           repr(out))
        ok("KHÔNG khoá/phạt MỘT key nào", phat_key() == {}, str(phat_key()))
        ok("đã đánh dấu model chết để lượt sau khỏi gọi lại",
           "M_CHET" in llm._GROQ_DEAD_MODELS, str(llm._GROQ_DEAD_MODELS))
        ok("chỉ tốn ĐÚNG 1 key (không xoay key vô ích)",
           len({k for k, _ in _StubOpenAI.NHAT_KY}) == 1,
           str(_StubOpenAI.NHAT_KY))
        # lượt SAU phải đi thẳng model kế, không gọi lại model chết
        _StubOpenAI.NHAT_KY = []
        llm.complete_text("x")
        ok("lượt sau KHÔNG gọi lại model đã chết",
           all(m != "M_CHET" for _, m in _StubOpenAI.NHAT_KY),
           str(_StubOpenAI.NHAT_KY))

        print("\n--- 3b. MỌI model đều 404 -> lỗi RIÊNG, vẫn không phạt key")
        reset()
        _StubOpenAI.HOOK = staticmethod(
            lambda k, m: (_ for _ in ()).throw(RuntimeError(L404)))
        loi404 = None
        try:
            llm.complete_text("x")
        except Exception as e:                              # noqa: BLE001
            loi404 = e
        ok("ném đúng lớp LLMModelMissing",
           isinstance(loi404, llm.LLMModelMissing), type(loi404).__name__)
        ok("mọi model chết mà VẪN không phạt key", phat_key() == {},
           str(phat_key()))

        # ───────────────────────────────────────────────────────────────
        print("\n=== 4. 429 -> XOAY KEY (không được đổi model)")
        reset("M_SONG,M_SONG2")
        goi = {"n": 0}

        def hook_429(key, model):
            if key == KEY_GIA[0]:
                raise RuntimeError(L429)
            goi["n"] += 1
            return "OK_KEY_2"
        _StubOpenAI.HOOK = staticmethod(hook_429)
        out = llm.complete_text("x")
        ok("429 -> sang KEY kế, vẫn ra kết quả", out == "OK_KEY_2", repr(out))
        ok("ĐÚNG key 429 bị đánh dấu limited",
           phat_key().get(KEY_GIA[0]) == "limited", str(phat_key()))
        ok("key lành KHÔNG bị phạt lây",
           KEY_GIA[1] not in phat_key(), str(phat_key()))
        ok("429 KHÔNG làm app đổi model",
           all(m == "M_SONG" for _, m in _StubOpenAI.NHAT_KY),
           str(_StubOpenAI.NHAT_KY))

        # ───────────────────────────────────────────────────────────────
        print("\n=== 5. 413 -> THU NHỎ, KHÔNG PHẠT KEY (vết xe đã đốt 38 key)")
        reset("M_SONG")            # dây chuyền 1 model -> phải nổi lên caller
        _StubOpenAI.HOOK = staticmethod(
            lambda k, m: (_ for _ in ()).throw(RuntimeError(L413)))
        loi413 = None
        try:
            llm.complete_text("x")
        except Exception as e:                              # noqa: BLE001
            loi413 = e
        ok("413 ném LLMTooLarge (caller tự thu nhỏ)",
           isinstance(loi413, llm.LLMTooLarge), type(loi413).__name__)
        ok("413 KHÔNG phạt key nào", phat_key() == {}, str(phat_key()))
        ok("413 KHÔNG bị lớp 404 nuốt nhầm",
           not isinstance(loi413, llm.LLMModelMissing))

        print("\n--- 5b. 413 khi CÒN model kế -> đổi model, vẫn không phạt key")
        reset("M_YEU,M_SONG")
        _StubOpenAI.HOOK = staticmethod(
            lambda k, m: (_ for _ in ()).throw(RuntimeError(L413))
            if m == "M_YEU" else "OK_MODEL_KE")
        ok("413 -> sang model kế", llm.complete_text("x") == "OK_MODEL_KE")
        ok("vẫn không phạt key", phat_key() == {}, str(phat_key()))
        ok("413 KHÔNG bị nhớ là model chết (prompt ngắn vẫn dùng lại được)",
           "M_YEU" not in llm._GROQ_DEAD_MODELS, str(llm._GROQ_DEAD_MODELS))

        # ───────────────────────────────────────────────────────────────
        print("\n=== 6. CONTENT RỖNG -> sang model kế (bẫy model suy luận)")
        reset("M_RONG,M_SONG")
        _StubOpenAI.HOOK = staticmethod(
            lambda k, m: "" if m == "M_RONG" else "OK_SAU_RONG")
        ok("model trả rỗng -> lấy model kế",
           llm.complete_text("x") == "OK_SAU_RONG")
        ok("không phạt key vì model trả rỗng", phat_key() == {})

        # ───────────────────────────────────────────────────────────────
        print("\n=== 7. LỜI BÁO 404 PHẢI KHÁC HẲN LỜI BÁO HẾT HẠN MỨC")
        reset("M_CHET2")
        _StubOpenAI.HOOK = staticmethod(
            lambda k, m: (_ for _ in ()).throw(RuntimeError(L404)))
        try:
            llm.complete_text("x")
            tin404 = ""
        except Exception as e:                              # noqa: BLE001
            tin404 = str(e)
        reset("M_SONG")
        _StubOpenAI.HOOK = staticmethod(
            lambda k, m: (_ for _ in ()).throw(RuntimeError(L429)))
        try:
            llm.complete_text("x")
            tinql = ""
        except Exception as e:                              # noqa: BLE001
            tinql = str(e)
        print(f"    404  : {tin404[:150]}")
        print(f"    429  : {tinql[:150]}")

        def _bao_404_dung(t: str) -> bool:
            """Lời báo 404 phải NÓI RA 2 điều: app cần cập nhật, VÀ đây không
            phải chuyện hạn mức. Chỉ hỏi 'có khác lời kia không' là chưa đủ."""
            tl = (t or "").lower()
            return ("cập nhật" in tl
                    and "không phải hết hạn mức" in tl
                    and "bỏ model" in tl)
        ok("lời báo 404 nói RÕ 'app cần cập nhật' + 'KHÔNG phải hết hạn mức'",
           _bao_404_dung(tin404))
        ok("lời báo hết hạn mức KHÔNG đội lốt lỗi model",
           "cập nhật" not in tinql.lower() and bool(tinql), tinql[:80])
        ok("hai lời báo KHÁC HẲN nhau", tin404 != tinql and bool(tin404))

        openai.OpenAI = goc_openai
        khoi_phuc()

        # ───────────────────────────────────────────────────────────────
        print("\n=== 8. QUÉT TĨNH: không còn tên model CHẾT ghi cứng")
        thay = quet_model_chet(REPO / "app")
        for p in (REPO / "config.py", REPO / "main.py"):
            for s in _chuoi_gia_tri(p):
                for md in CHET:
                    if md in s:
                        thay.append((p.name, md))
        ok("mã sống (app/, config.py, main.py) sạch tên model chết",
           not thay, str(thay[:6]))
        env_mau = (REPO / ".env.example").read_text(encoding="utf-8")
        con = [md for md in CHET
               if any(l.strip().startswith(("GROQ_", "SELECT_", "JUDGE_"))
                      and md in l for l in env_mau.splitlines())]
        ok(".env.example không còn trỏ vào model chết", not con, str(con))

        print("\n--- 8b. TỰ KIỂM BỘ DÒ (không có mục này thì cổng là con dấu)")
        import shutil
        san = REPO / f"_bq_thu_model_{os.getpid()}"
        try:
            san.mkdir(exist_ok=True)
            (san / "co_loi.py").write_text(
                'X = "llama-3.3-70b-versatile"\n', encoding="utf-8")
            (san / "trong_sach.py").write_text(
                '"""Docstring nhắc `mixtral-8x7b-32768` để cảnh báo."""\n'
                '# ghi chú: llama3-70b-8192 nằm trong COMMENT\n'
                '"gemma2-9b-it đứng một mình = doc-comment"\n'
                'Y = "openai/gpt-oss-120b"\n', encoding="utf-8")
            bat = quet_model_chet(san, bo_bo_do=False)
            ten = {Path(f).name for f, _ in bat}
            ok("bộ dò BẮT được tên model chết ở hằng GIÁ TRỊ",
               "co_loi.py" in ten, str(sorted(ten)))
            ok("bộ dò BỎ QUA comment + docstring + doc-comment (không đỏ oan)",
               "trong_sach.py" not in ten,
               str([(f, m) for f, m in bat if "trong_sach" in f]))
        finally:
            shutil.rmtree(san, ignore_errors=True)
        ok("bộ so lời báo TỪ CHỐI lời báo kiểu cũ",
           not _bao_404_dung("Gọi groq thất bại: Error code: 404 - ..."))
        ok("bộ so lời báo TỪ CHỐI lời báo nửa vời",
           not _bao_404_dung("Groq đã bỏ model này, app cần cập nhật"))

        # ───────────────────────────────────────────────────────────────
        print("\n=== 9. GỌI GROQ THẬT: bảng phân loại khớp lỗi Groq HÔM NAY")
        if BO_MANG:
            print("  (bỏ qua: BQ_BO_MANG=1)")
        else:
            # model CHẾT THẬT đứng đầu, model thật đứng sau. Giữ bộ tự-dò TẮT
            # (reset đã tắt) để lượt gọi buộc phải ăn 404 THẬT của Groq — đó
            # chính là thứ ca này muốn chứng minh.
            reset("llama-3.3-70b-versatile," + goc_model)
            settings_cls.GROQ_API_KEYS = goc_keys
            settings_cls.GROQ_KEYS_FILE = goc_file
            llm._KEY_STATE.clear()
            llm._GROQ_DEAD_MODELS.clear()
            if not settings.groq_keys():
                print("  (bỏ qua: máy này chưa cấu hình key Groq)")
            else:
                out = llm.complete_text(
                    "Tra loi dung 1 tu, khong giai thich: thu do Viet Nam?")
                ok("404 THẬT của Groq -> app vẫn ra kết quả",
                   bool(out.strip()), repr(out[:60]))
                ok("404 THẬT KHÔNG khoá key nào (41 key còn nguyên)",
                   phat_key() == {}, str(phat_key()))
                ok("nhận đúng model chết THẬT",
                   "llama-3.3-70b-versatile" in llm._GROQ_DEAD_MODELS,
                   str(llm._GROQ_DEAD_MODELS))
    finally:
        try:
            if goc_openai is not None:
                import openai
                openai.OpenAI = goc_openai
        except Exception:                                   # noqa: BLE001
            pass
        khoi_phuc()
        try:
            from app.ai import llm as _l
            _l.models_groq_con_song = goc_do
            _l._KEY_STATE.clear()
            _l._GROQ_DEAD_MODELS.clear()
            _l._GROQ_SONG["models"] = frozenset()
            _l._GROQ_SONG["ts"] = 0.0
        except Exception:                                   # noqa: BLE001
            pass

    print("\n" + "=" * 68)
    print(f"CỔNG 69 — ĐẠT {DAT} · HỎNG {HONG}")
    if _HONG:
        for d in _HONG:
            print(f"   HỎNG: {d}")
    print("=" * 68)
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
