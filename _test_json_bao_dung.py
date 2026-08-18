# -*- coding: utf-8 -*-
"""CỔNG 74 — **JSON CỦA LLM: ĐỨT/BỌC/THỪA CHỮ THÌ VẪN PHẢI SỐNG** (18/08/2026).

Canh bản sửa CHẶN SẢN XUẤT: anh Hùng chạy v2.34.0, đường Thay giọng, 2 video
ra "1 xong · 1 LỖI" với `LLMError: LLM trả về không phải JSON hợp lệ:
Expecting value: line 1 column 1838 (char 1837)`.

GỐC RỄ ĐO ĐƯỢC (`_do_json_dut.py`, 6/6 lượt, Groq THẬT): app KHÔNG đặt
`max_tokens` — nhưng **không đặt KHÔNG phải là không giới hạn**, Groq tự áp
trần MẶC ĐỊNH `completion_tokens` = **3072** (gpt-oss-120b) / **2048**
(gpt-oss-20b). Bản dịch cần ~3.100 token nên mảng JSON đứt giữa chừng.
`finish_reason` = **`length` 6/6 lượt**. Hụt ÍT nên bệnh CHẬP CHỜN.

CỔNG NÀY PHỦ 7 MỆNH ĐỀ (mỗi cái là một cách app đã/sẽ chết):
  1. JSON ĐỨT CUỐI  -> vớt được phần hoàn chỉnh, KHÔNG mất trắng
  2. BỌC MARKDOWN (kể cả khối mở mà chưa đóng vì bị cắt)
  3. CHỮ DẪN THỪA trước/sau · DẤU PHẨY THỪA
  4. `finish_reason=length` -> báo ĐÚNG BỆNH ("quá dài bị cắt"), không phải
     "không phải JSON hợp lệ" (lời cũ chỉ đúng phần NGỌN)
  5. THỬ LẠI rồi mới báo lỗi; 2 lượt đầu parse NGHIÊM, lượt cuối mới vớt
  6. **KHÔNG PHẠT KEY** — JSON hỏng là lỗi ĐỊNH DẠNG, mọi key như nhau
  7. `max_tokens` phải xin TRƯỚC và `prompt + max_tokens <= 8000` (TPM)

CHỐNG "CON DẤU": mọi mệnh đề đều chạy lại trên **BẢN MỐC `v2.34.0`** (nạp
bằng `git show`) và ĐÒI bản mốc phải HỎNG. Cổng nào cũng xanh ở cả hai bản
thì nó không canh gì cả. Kèm chốt "bản mốc phải KHÁC bản đang test" (bài học
cổng 36/51/52/56 — gộp vào main rồi lấy main làm mốc là PASS OAN vĩnh viễn).

Chạy: .venv\\Scripts\\python.exe -u _test_json_bao_dung.py
      BQ_BO_MANG=1 để bỏ ca gọi Groq THẬT.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from app.ai import llm            # noqa: E402

#: MỐC = bản phát hành NGAY TRƯỚC tính năng này (luật CLAUDE.md, cổng 56).
#: **KHÔNG BAO GIỜ dùng `main`/`HEAD`** — gộp xong thì mốc chính là bản đang
#: test, cổng đối chứng tự ĐẠT OAN vĩnh viễn (cổng 36/51/52 đã sập).
#: Đo 18/08/2026: `git diff v2.34.0 v2.35.0 -- app/ai/llm.py …` **RỖNG**, tức
#: anh Hùng gặp lỗi ở v2.34.0 và v2.35.0 mang y nguyên bệnh đó.
MOC_REF = os.environ.get("BQ_MOC_JSON", "v2.35.0")
DAT, HONG = 0, 0
LOI: list[str] = []


def ok(ten: str, dieu: bool, ghi: str = "") -> bool:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  [OK ] {ten}" + (f" — {ghi}" if ghi else ""))
    else:
        HONG += 1
        LOI.append(ten)
        print(f"  [HỎNG] {ten}" + (f" — {ghi}" if ghi else ""))
    return dieu


# --------------------------------------------------------------------------
# MẪU HỎNG — lấy đúng hình dạng model trả về trong lượt đo thật
# --------------------------------------------------------------------------
#: mảng bị CẮT NGANG giữa phần tử thứ 4 (đúng kiểu `_do_json_dut_mau.txt`)
DUT_MANG = ('[\n  {"i":0,"t":"Gần đây có bảy bộ phim mới"},\n'
            '  {"i":1,"t":"Mỗi phim một âm thanh bùng nổ"},\n'
            '  {"i":2,"t":"Các bạn mê phim chắc sẽ thích"},\n'
            '  {"i":3,"t":"Phần đầu tiên: Phòng đấu ng')
#: object có mảng bên trong bị cắt — hình dạng của recap {"title","parts":[…]}
DUT_OBJ = ('{"title":"Bảy bộ phim mới","parts":[{"start":0,"end":5.5},'
           '{"start":6.0,"end":11.2},{"start":12.0,"end":')
BOC_MD = '```json\n[{"i":0,"t":"xin chào"}]\n```'
BOC_MD_HO = '```json\n[{"i":0,"t":"xin chào"},{"i":1,"t":"tạm biệt"}]'
#: khối markdown MỞ **và** JSON đứt — bản mốc chết ở đây, `BOC_MD_HO` thì
#: không (bước "ứng viên" của bản mốc vẫn bắt được mảng ĐÃ ĐÓNG). Phải tách
#: hai mẫu ra thì mục TỰ KIỂM mới nói đúng cái mình canh.
BOC_MD_DUT = '```json\n[{"i":0,"t":"xin chào"},{"i":1,"t":"tạm bi'
CHU_THUA = 'Đây là kết quả của bạn:\n[{"i":0,"t":"xin chào"}]\nHy vọng giúp ích!'
PHAY_THUA = '[{"i":0,"t":"a"},{"i":1,"t":"b"},]'
HOP_LE = ('[{"i":0,"t":"a"},{"i":1,"t":"b"}]', '{"title":"x","parts":[1,2]}',
          '  \n[]  ', '{"a":{"b":[1,2,{"c":3}]}}', '[1,2,3]', '"chuoi"',
          '{"vi_sao":"có dấu , ] trong chuỗi","d":7}',
          '```json\n{"ok":true}\n```',
          'Đây là:\n[{"index":0,"score":88,"vi_sao":"hay"}]')


def nap_moc():
    """Nạp `app/ai/llm.py` của BẢN MỐC thành module RIÊNG (không đụng bản
    đang chạy). Trả (module, lý do bỏ qua)."""
    try:
        r = subprocess.run(["git", "show", f"{MOC_REF}:app/ai/llm.py"],
                           cwd=str(REPO), capture_output=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        return None, f"không chạy được git: {e}"
    if r.returncode != 0:
        return None, (r.stderr or b"").decode("utf-8", "replace")[:120]
    ma = r.stdout.decode("utf-8", "replace")
    if ma == (REPO / "app" / "ai" / "llm.py").read_text(encoding="utf-8"):
        return None, ("BẢN MỐC TRÙNG BẢN ĐANG TEST — mốc sai, mọi phép so "
                      "sẽ tự ĐẠT OAN")
    d = Path(tempfile.mkdtemp(prefix="bq_moc_json_"))
    f = d / "llm_moc.py"
    f.write_text(ma, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("llm_moc_v74", f)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)                    # type: ignore[union-attr]
    except Exception as e:  # noqa: BLE001
        return None, f"nạp mốc lỗi: {e}"
    return mod, ""


def boc(mod, s: str, cho_vot: bool = True):
    """Gọi bộ bóc của module `mod`; bản mốc không có tham số `cho_vot`."""
    try:
        return mod._extract_json(s, cho_vot=cho_vot)
    except TypeError:
        return mod._extract_json(s)


# ==========================================================================
print("== CA 1. BẤT BIẾN: JSON HỢP LỆ ra kết quả Y HỆT bản mốc ==")
MOC, vi_sao = nap_moc()
if MOC is None:
    ok(f"nạp bản mốc {MOC_REF}", False, vi_sao)
else:
    ok(f"nạp bản mốc {MOC_REF}", True, "khác bản đang test")
    lech = []
    for s in HOP_LE:
        try:
            a = json.dumps(llm._extract_json(s), ensure_ascii=False,
                           sort_keys=True)
        except Exception as e:  # noqa: BLE001
            a = f"NÉM:{type(e).__name__}"
        try:
            b = json.dumps(boc(MOC, s), ensure_ascii=False, sort_keys=True)
        except Exception as e:  # noqa: BLE001
            b = f"NÉM:{type(e).__name__}"
        if a != b:
            lech.append(f"{s[:40]!r}: nay={a[:60]} mốc={b[:60]}")
    ok(f"{len(HOP_LE)} mẫu JSON HỢP LỆ giống mốc từng ký tự",
       not lech, "; ".join(lech)[:200] or "0 lệch")

# ==========================================================================
print("\n== CA 2. JSON ĐỨT CUỐI -> VỚT được, KHÔNG mất trắng ==")
d = llm._extract_json(DUT_MANG)
ok("mảng đứt -> ra list", isinstance(d, list), f"{type(d).__name__}")
ok("vớt đúng 3 phần tử HOÀN CHỈNH (bỏ cái dở)",
   isinstance(d, list) and len(d) == 3, f"{len(d) if isinstance(d, list) else '?'}")
ok("phần tử vớt đúng nội dung",
   isinstance(d, list) and d and d[0] == {"i": 0, "t": "Gần đây có bảy bộ phim mới"},
   str(d[:1])[:90])
ok("KHÔNG bịa phần model chưa viết",
   isinstance(d, list) and all(isinstance(x, dict) and "t" in x for x in d))

do = llm._extract_json(DUT_OBJ)
ok("object đứt -> ra dict", isinstance(do, dict), f"{type(do).__name__}")
ok("giữ được khoá đã hoàn chỉnh (title)",
   isinstance(do, dict) and do.get("title") == "Bảy bộ phim mới")
ok("vớt được mảng lồng bên trong (2 part đủ)",
   isinstance(do, dict) and isinstance(do.get("parts"), list)
   and len(do["parts"]) == 2, str(do.get("parts"))[:80])

if MOC is not None:
    b1 = b2 = "?"
    try:
        b1 = str(boc(MOC, DUT_MANG))[:40]
    except Exception as e:  # noqa: BLE001
        b1 = f"NÉM:{type(e).__name__}"
    try:
        b2 = str(boc(MOC, DUT_OBJ))[:40]
    except Exception as e:  # noqa: BLE001
        b2 = f"NÉM:{type(e).__name__}"
    ok("TỰ KIỂM: bản mốc PHẢI chết với cả 2 mẫu đứt",
       b1.startswith("NÉM") and b2.startswith("NÉM"), f"{b1} · {b2}")

# ==========================================================================
print("\n== CA 3. bọc markdown · chữ dẫn thừa · dấu phẩy thừa ==")
ok("khối ```json đóng đủ", llm._extract_json(BOC_MD) == [{"i": 0, "t": "xin chào"}])
ok("khối ```json MỞ mà chưa đóng (JSON vẫn đủ)",
   llm._extract_json(BOC_MD_HO) == [{"i": 0, "t": "xin chào"},
                                    {"i": 1, "t": "tạm biệt"}])
ok("khối ```json MỞ **và** JSON đứt",
   llm._extract_json(BOC_MD_DUT) == [{"i": 0, "t": "xin chào"}],
   str(llm._extract_json(BOC_MD_DUT))[:70])
ok("chữ dẫn thừa trước/sau", llm._extract_json(CHU_THUA) == [{"i": 0, "t": "xin chào"}])
ok("dấu phẩy thừa trước ]",
   llm._extract_json(PHAY_THUA) == [{"i": 0, "t": "a"}, {"i": 1, "t": "b"}])
ok("_bo_phay_thua KHÔNG đụng dấu phẩy giữa chuỗi",
   json.loads(llm._bo_phay_thua('{"a":"x, y","b":1}'))["a"] == "x, y")
if MOC is not None:
    # BẢN MỐC SAI KIỂU NÀO CŨNG ĐƯỢC TÍNH LÀ SAI — và một trong hai kiểu còn
    # NGUY HIỂM HƠN ném lỗi: với `md hở + đứt`, bản mốc **KHÔNG ném** mà trả về
    # `{"i":0,"t":"xin chào"}` — tức một DICT thay cho MẢNG (nó bắt phải mảnh
    # LỒNG BÊN TRONG). Caller nhận sai ruột mà không có cách nào biết. Đây đúng
    # là lý do bước "vớt cấu trúc ngoài cùng" phải chạy TRƯỚC bước ứng viên.
    r = []
    for ten, s, dung in (("md hở + đứt", BOC_MD_DUT, [{"i": 0, "t": "xin chào"}]),
                         ("phẩy thừa", PHAY_THUA,
                          [{"i": 0, "t": "a"}, {"i": 1, "t": "b"}])):
        try:
            got = boc(MOC, s)
        except Exception:  # noqa: BLE001
            continue                     # ném = sai, đúng như mong đợi
        if got == dung:
            r.append(f"{ten} (mốc ra ĐÚNG)")
        else:
            print(f"       (mốc {ten}: KHÔNG ném nhưng trả SAI -> {got!r})")
    ok("TỰ KIỂM: bản mốc PHẢI SAI với 'md hở + đứt' và 'phẩy thừa' "
       "(ném HOẶC sai hình dạng)", not r, f"mốc lại ra đúng: {r}")
    # `BOC_MD_HO` (md hở nhưng JSON ĐỦ) bản mốc VẪN QUA — ghi ra để không ai
    # tưởng mục trên là tính năng mới; nó là chốt CHỐNG HỒI QUY.
    try:
        boc(MOC, BOC_MD_HO)
        _md_ho_moc = True
    except Exception:  # noqa: BLE001
        _md_ho_moc = False
    ok("ghi nhận: 'md hở + JSON đủ' vốn ĐÃ chạy ở bản mốc (chốt hồi quy)",
       _md_ho_moc)

# ==========================================================================
print("\n== CA 4. finish_reason=length -> BÁO ĐÚNG BỆNH ==")
_goc_ct = llm.complete_text
_dem = {"n": 0, "sys": []}


def _ct_cut(prompt, system="", temperature=0.4, provider=None, model=None,
            json_mode=False):
    _dem["n"] += 1
    _dem["sys"].append(system)
    llm._LAN.ket_thuc = "length"
    return DUT_MANG


try:
    llm.complete_text = _ct_cut
    try:
        llm.complete_json("dịch giúp")
        ok("phải ném khi không vớt nổi", True, "vớt được -> đi nhánh vớt")
    except llm.LLMError as e:
        ok("không tới đây", False, str(e)[:80])
    ok("VỚT được nên KHÔNG ném (3 lượt đều cắt)", True,
       f"gọi {_dem['n']} lần")
    ok("gọi ĐÚNG 3 lượt rồi mới thôi", _dem["n"] == 3, str(_dem["n"]))
    ok("lượt 2 có nhắc CHỈ trả JSON", "CHỈ trả về" in _dem["sys"][1])
    ok("lượt 2 có nhắc VIẾT NGẮN vì bị cắt", "bị cắt" in _dem["sys"][1],
       _dem["sys"][1][-70:])
    # không vớt nổi -> phải ném LLMCatCut chứ KHÔNG phải "không phải JSON"
    _dem["n"] = 0

    def _ct_cut_rac(prompt, system="", temperature=0.4, provider=None,
                    model=None, json_mode=False):
        _dem["n"] += 1
        llm._LAN.ket_thuc = "length"
        return "Tôi đang nghĩ về việc này và"

    llm.complete_text = _ct_cut_rac
    try:
        llm.complete_json("dịch giúp")
        ok("phải ném LLMCatCut", False, "không ném")
    except llm.LLMCatCut as e:
        ok("ném ĐÚNG lớp LLMCatCut", True)
        ok("lời lỗi nói 'quá dài' + 'bị CẮT'",
           "quá dài" in str(e) and "CẮT" in str(e), str(e)[:90])
        ok("lời lỗi KHÔNG đổ oan cho hạn mức key",
           "KHÔNG phải hết hạn mức key" in str(e))
        ok("LLMCatCut vẫn là LLMError (caller cũ không vỡ)",
           isinstance(e, llm.LLMError))
    except llm.LLMError as e:
        ok("ném ĐÚNG lớp LLMCatCut", False, f"ném {type(e).__name__}")
    # JSON hỏng mà KHÔNG bị cắt -> giữ nguyên lời cũ
    _dem["n"] = 0

    def _ct_rac(prompt, system="", temperature=0.4, provider=None,
                model=None, json_mode=False):
        _dem["n"] += 1
        llm._LAN.ket_thuc = "stop"
        return "xin lỗi tôi không hiểu"

    llm.complete_text = _ct_rac
    try:
        llm.complete_json("x")
        ok("phải ném", False)
    except llm.LLMCatCut as e:
        ok("KHÔNG được đổ nhầm sang 'bị cắt' khi finish=stop", False, str(e)[:80])
    except llm.LLMError as e:
        ok("finish=stop + rác -> vẫn lời cũ 'không phải JSON hợp lệ'",
           "không phải JSON hợp lệ" in str(e), str(e)[:80])
    ok("rác thì cũng thử đủ 3 lượt", _dem["n"] == 3, str(_dem["n"]))
finally:
    llm.complete_text = _goc_ct
    llm._LAN.ket_thuc = ""

# ==========================================================================
print("\n== CA 5. 2 lượt đầu parse NGHIÊM, lượt CUỐI mới vớt ==")
_goc_ct = llm.complete_text
_v = {"n": 0}


def _ct_dut_roi_du(prompt, system="", temperature=0.4, provider=None,
                   model=None, json_mode=False):
    _v["n"] += 1
    llm._LAN.ket_thuc = "length" if _v["n"] == 1 else "stop"
    return DUT_MANG if _v["n"] == 1 else '[{"i":0,"t":"ĐỦ"}]'


try:
    llm.complete_text = _ct_dut_roi_du
    d = llm.complete_json("x")
    ok("lượt 1 đứt -> KHÔNG nhận vội, gọi lại", _v["n"] == 2, f"gọi {_v['n']}")
    ok("nhận bản ĐỦ của lượt 2", d == [{"i": 0, "t": "ĐỦ"}], str(d)[:60])
finally:
    llm.complete_text = _goc_ct
    llm._LAN.ket_thuc = ""

try:
    llm._extract_json(DUT_MANG, cho_vot=False)
    ok("cho_vot=False phải NÉM (để caller còn đòi bản đủ)", False,
       "lại parse được")
except (ValueError, json.JSONDecodeError):
    ok("cho_vot=False phải NÉM (để caller còn đòi bản đủ)", True)

# ==========================================================================
print("\n== CA 6. KHÔNG PHẠT KEY khi JSON hỏng / bị cắt ==")
from config import settings                       # noqa: E402

_goc_keys = settings.llm_keys_for
_goc_call = llm._call_once
_goc_ml = llm.mark_limited
_goc_mi = llm.mark_invalid
_phat = {"limited": 0, "invalid": 0}


def _dem_ml(p, k, t=""):
    _phat["limited"] += 1
    return 0.0


def _dem_mi(p, k):
    _phat["invalid"] += 1


def _call_cut(provider, key, prompt, system, temperature, model=None,
              json_mode=False):
    llm._LAN.ket_thuc = "length"
    return DUT_MANG[:60]


try:
    settings.llm_keys_for = lambda p: ["k1", "k2", "k3"]
    llm.mark_limited, llm.mark_invalid = _dem_ml, _dem_mi
    llm._call_once = _call_cut
    try:
        llm.complete_json("x", provider="groq")
    except llm.LLMError:
        pass
    ok("0 key bị mark_limited", _phat["limited"] == 0, str(_phat))
    ok("0 key bị mark_invalid", _phat["invalid"] == 0, str(_phat))
finally:
    settings.llm_keys_for = _goc_keys
    llm._call_once = _goc_call
    llm.mark_limited, llm.mark_invalid = _goc_ml, _goc_mi
    llm._LAN.ket_thuc = ""

# ==========================================================================
print("\n== CA 7. max_tokens: xin TRƯỚC + không đụng trần TPM 8000 ==")
ok("hằng số trần TPM = 8000 (đọc từ chính lời lỗi 413)",
   llm.GROQ_TPM_TRAN == 8000, str(llm.GROQ_TPM_TRAN))
# ước lượng token KHÔNG được HỤT so với 3 mốc ĐO THẬT của Groq
try:
    from _do_json_dut import dung_prompt, nap_cau
    _cau, _goc = nap_cau()
    hut = []
    for n, that in ((10, 551), (25, 874), (50, 1413)):
        p, s = dung_prompt(_cau[:n], "vi", _goc)
        u = llm._uoc_token(p) + llm._uoc_token(s)
        if u < that:
            hut.append(f"{n} câu: ước {u} < thật {that}")
    ok("ước token KHÔNG hụt ở 3 mốc đo thật (551/874/1413)",
       not hut, "; ".join(hut) or "0 hụt")
    for n in (10, 25, 50):
        p, s = dung_prompt(_cau[:n], "vi", _goc)
        tong = llm._uoc_token(p) + llm._uoc_token(s) + llm.max_tokens_groq(p, s)
        ok(f"prompt {n} câu + max_tokens <= 8000", tong <= 8000, str(tong))
except Exception as e:  # noqa: BLE001
    ok("dựng được prompt thật để đo", False, str(e)[:120])
ok("prompt KHỔNG LỒ vẫn còn sàn xin việc",
   llm.max_tokens_groq("鿿" * 20000) == llm.GROQ_OUT_TOI_THIEU,
   str(llm.max_tokens_groq("鿿" * 20000)))
ok("prompt ngắn bị chặn ở trần trên (không xin 8000 -> 413)",
   llm.max_tokens_groq("hi") == llm.GROQ_OUT_TOI_DA <= 6144,
   str(llm.max_tokens_groq("hi")))

# `_call_once` phải THẬT SỰ truyền tham số xuống — chặn bằng STUB, không quét
# chuỗi (bài học cổng 56d: quét chuỗi thì phép phá giữ mặt chữ mà đổi ý nghĩa).
_bat: dict = {}


class _Comp:
    def __init__(self, cl):
        self._cl = cl

    def create(self, model=None, messages=None, temperature=None,
               extra_body=None, **kw):
        _bat.update({"model": model, **kw})

        class _M:
            content = '[{"i":0,"t":"ok"}]'

        class _C:
            message = _M()
            finish_reason = "stop"

        class _R:
            choices = [_C()]
        return _R()


class _Chat:
    def __init__(self, cl):
        self.completions = _Comp(cl)


class _Stub:
    def __init__(self, api_key=None, base_url=None, timeout=None,
                 max_retries=None, **kw):
        self.api_key = api_key
        self.chat = _Chat(self)


import openai                                     # noqa: E402

_goc_openai = openai.OpenAI
_goc_chuoi = llm.chuoi_model_groq
try:
    openai.OpenAI = _Stub
    llm.chuoi_model_groq = lambda m=None: ["openai/gpt-oss-120b"]
    llm._call_once("groq", "k", "prompt ngắn", "sys", 0.3, json_mode=True)
    ok("_call_once CÓ truyền max_tokens", "max_tokens" in _bat, str(sorted(_bat)))
    ok("max_tokens là SỐ TÍNH RA, không phải hằng bịa",
       _bat.get("max_tokens") == llm.max_tokens_groq("prompt ngắn", "sys"),
       str(_bat.get("max_tokens")))
    ok("CÓ bật response_format json_object khi json_mode=True",
       _bat.get("response_format") == {"type": "json_object"},
       str(_bat.get("response_format")))
    ok("CÓ đặt reasoning_effort=low cho gpt-oss",
       _bat.get("reasoning_effort") == "low", str(_bat.get("reasoning_effort")))
    _bat.clear()
    llm._call_once("groq", "k", "p", "s", 0.3, json_mode=False)
    ok("json_mode=False thì KHÔNG bật response_format",
       "response_format" not in _bat, str(sorted(_bat)))
    _bat.clear()
    llm.chuoi_model_groq = lambda m=None: ["groq/compound"]
    llm._call_once("groq", "k", "p", "s", 0.3, json_mode=True)
    ok("model KHÔNG hỗ trợ -> không ép json_object/reasoning",
       "response_format" not in _bat and "reasoning_effort" not in _bat,
       str(sorted(_bat)))

    # model TỪ CHỐI tham số (400) -> phải gọi lại kiểu trần, KHÔNG chết
    _lan = {"n": 0}

    class _CompTuChoi(_Comp):
        def create(self, model=None, messages=None, temperature=None,
                   extra_body=None, **kw):
            _lan["n"] += 1
            if "reasoning_effort" in kw:
                raise RuntimeError(
                    "Error code: 400 - {'error': {'message': "
                    "'`reasoning_effort` must be one of `low`...'}}")
            return super().create(model=model, messages=messages,
                                  temperature=temperature,
                                  extra_body=extra_body, **kw)

    class _ChatTC:
        def __init__(self, cl):
            self.completions = _CompTuChoi(cl)

    class _StubTC(_Stub):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.chat = _ChatTC(self)

    openai.OpenAI = _StubTC
    llm.chuoi_model_groq = lambda m=None: ["openai/gpt-oss-120b"]
    out = llm._call_once("groq", "k", "p", "s", 0.3, json_mode=True)
    ok("400 vì tham số -> LÙI ÊM, vẫn ra kết quả", out.startswith("[{"), out[:40])
    ok("lùi êm = gọi lại đúng 1 lần", _lan["n"] == 2, str(_lan["n"]))
finally:
    openai.OpenAI = _goc_openai
    llm.chuoi_model_groq = _goc_chuoi
    llm._LAN.ket_thuc = ""

if MOC is not None:
    ok("TỰ KIỂM: bản mốc KHÔNG có max_tokens_groq (nên mới dính lỗi)",
       not hasattr(MOC, "max_tokens_groq"))
    ok("TỰ KIỂM: bản mốc KHÔNG có LLMCatCut",
       not hasattr(MOC, "LLMCatCut"))
    ok("TỰ KIỂM: bản mốc KHÔNG có ly_do_ket_thuc",
       not hasattr(MOC, "ly_do_ket_thuc"))

# ==========================================================================
print("\n== CA 8. VIỆC 3 — mọi chỗ bóc JSON của LLM đều qua bộ bao dung ==")


def _ma_that(p: Path) -> str:
    """Mã THẬT (bỏ COMMENT + STRING) — bài học cổng 47/51/53/54: quét bằng
    chuỗi thì chính dòng ghi chú giải thích bản vá bị kể là vi phạm."""
    import io
    import tokenize
    ra = []
    with io.open(p, "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(tok.string)
    return " ".join(ra)


def _co_goi(p: Path, ten: str) -> bool:
    """Có lời gọi hàm tên `ten` THẬT SỰ trong mã không (đọc bằng AST, không
    tìm chuỗi — quét chuỗi là để lọt phép phá giữ nguyên mặt chữ)."""
    cay = ast.parse(p.read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Call):
            f = nut.func
            n = (f.id if isinstance(f, ast.Name) else
                 f.attr if isinstance(f, ast.Attribute) else "")
            if n == ten:
                return True
        if isinstance(nut, ast.ImportFrom):
            for a in nut.names:
                if a.name == ten:
                    return True
    return False


for ten, rel in (("chon_doan", "app/ai/chon_doan.py"),
                 ("mach_lac", "app/ai/mach_lac.py"),
                 ("recap", "app/ai/recap.py")):
    ok(f"{ten}: có nối vào boc_json", _co_goi(REPO / rel, "boc_json"))

ok("boc_json là ĐÚNG bộ bao dung (không phải bản sao)",
   llm.boc_json is llm._extract_json)

from app.ai import chon_doan as CD                # noqa: E402
from app.ai import mach_lac as ML                 # noqa: E402
from app.ai import recap as RC                    # noqa: E402

# chon_doan: bảng chấm bị cắt -> vẫn lấy được điểm đã chấm xong
CD_DUT = ('[{"index":0,"score":88,"vi_sao":"hook mạnh"},'
          '{"index":1,"score":71,"vi_sao":"ổn"},{"index":2,"sco')
_clips = [{"start": 0, "end": 5}, {"start": 5, "end": 10},
          {"start": 10, "end": 15}]
_tr = {"segments": [], "words": []}
r = CD.cham_mu(_clips, _tr, lambda p, model=None: CD_DUT)
ok("chon_doan: bảng chấm ĐỨT -> vẫn lấy được 2 điểm đã xong",
   len(r) == 2 and abs(r[0]["score"] - 88.0) < 0.01, str(r)[:110])

# mach_lac: JSON hậu kiểm bị cắt đuôi
ML_DUT = '{"mach_lac":8,"thu_tu":[1,0,2],"bo":null,"vi_sao":"đảo cho x'
r2 = ML.doc_ket(ML_DUT, 3)
ok("mach_lac: JSON hậu kiểm ĐỨT -> vẫn đọc được mach_lac",
   isinstance(r2, dict) and r2.get("mach_lac") == 8.0, str(r2)[:110])

# recap: model trả JSON-TRONG-CHUỖI mà chuỗi đó bọc markdown / đứt cuối
_RC_PART = ('{"start":0,"end":30,"mode":"narrate",'
            '"text":"Bảy bộ phim mới đang gây sốt khắp nơi"}')
RC_MD = ('```json\n{"title":"Bảy phim","windows":[[0,30]],'
         f'"parts":[{_RC_PART}]}}\n```')
RC_DUT = ('{"title":"Bảy phim","windows":[[0,30]],'
          f'"parts":[{_RC_PART}],"ghi_chu":"còn d')
_LOI_CU = "không phải JSON object — trả JSON THUẦN"
for _nhan, _s in (("bọc markdown", RC_MD), ("đứt cuối", RC_DUT)):
    try:
        _d, _e = RC._director_from_data(_s, [], 60.0, 5.0, 50.0)
        ok(f"recap: chuỗi {_nhan} KHÔNG còn bị chối ngay",
           _LOI_CU not in (_e or ""), f"lỗi trả về: {str(_e)[:70]!r}")
        ok(f"recap: chuỗi {_nhan} -> lấy được title",
           isinstance(_d, dict) and _d.get("title") == "Bảy phim",
           str(_d)[:80] if _d else str(_e)[:80])
    except Exception as e:  # noqa: BLE001
        ok(f"recap: gọi được _director_from_data ({_nhan})", False, str(e)[:120])
# TỰ KIỂM: đúng 2 chuỗi đó phải làm `json.loads` trần CHẾT
for _nhan, _s in (("bọc markdown", RC_MD), ("đứt cuối", RC_DUT)):
    try:
        json.loads(_s)
        ok(f"TỰ KIỂM: json.loads trần PHẢI chết với '{_nhan}'", False)
    except ValueError:
        ok(f"TỰ KIỂM: json.loads trần PHẢI chết với '{_nhan}'", True)

# TỰ KIỂM BỘ DÒ: dựng lại ĐÚNG cách bóc CŨ của 2 chỗ trên (regex đòi dấu
# đóng) và bắt nó phải TRƯỢT — nếu cách cũ cũng qua được thì 2 mục trên chỉ
# là con dấu.
import re as _re                                  # noqa: E402

_cu_cd = _re.search(r"\[.*\]", CD_DUT, _re.S)
_cu_ml = _re.search(r"\{.*\}", ML_DUT, _re.S)
ok("TỰ KIỂM: cách bóc CŨ của chon_doan PHẢI trượt mẫu đứt", _cu_cd is None)
ok("TỰ KIỂM: cách bóc CŨ của mach_lac PHẢI trượt mẫu đứt", _cu_ml is None)

# ==========================================================================
print("\n== CA 9. GROQ THẬT: complete_json ra JSON dùng được ==")
if os.environ.get("BQ_BO_MANG") == "1":
    print("  [BỎ QUA] BQ_BO_MANG=1")
elif not settings.llm_keys_for("groq"):
    print("  [BỎ QUA] không có key groq trong .env")
else:
    try:
        from _do_json_dut import dung_prompt, nap_cau     # noqa: F811
        _cau, _goc = nap_cau()
        p, s = dung_prompt(_cau[:30], "vi", _goc)
        d = llm.complete_json(p, system=s)
        xs = d if isinstance(d, list) else []
        ok("Groq THẬT: 30 câu -> mảng JSON parse được", isinstance(d, list),
           f"{type(d).__name__} · {len(xs)} phần tử")
        ok("Groq THẬT: đủ ÍT NHẤT 25/30 nhãn", len(xs) >= 25, f"{len(xs)}/30")
        ok("Groq THẬT: finish_reason KHÔNG phải length",
           llm.ly_do_ket_thuc() != "length", llm.ly_do_ket_thuc())
    except llm.LLMError as e:
        ok("Groq THẬT", False, str(e)[:150])

# ==========================================================================
print()
print(f"KẾT QUẢ CỔNG 74: ĐẠT {DAT} · HỎNG {HONG}")
if LOI:
    print("HỎNG: " + " | ".join(LOI))
sys.exit(1 if HONG else 0)
