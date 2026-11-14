# -*- coding: utf-8 -*-
"""CỔNG 115 — HẬU KIỂM MẠCH CHUYỆN ĐÃ CÓ QUYẾT ĐỊNH THÌ KHÔNG ĐƯỢC BỊ COI LÀ
"CHƯA KIỂM XONG" (13/11/2026).

Đo trước khi sửa (studio.db đọc immutable + logs tháng 11):
  * 187/229 cảnh báo "chưa kiểm tra xong chất lượng" là do một lý do:
    "Đề xuất sai mốc hoặc sai thời lượng; giữ bản chọn" — AI đề xuất id không
    hợp lệ, app GIỮ bản chọn. Đó là quyết định đã xong, nhưng mang trạng thái
    'unreviewed' -> `continuity_incomplete=True`.
  * `m1._cut_vi_het_luot` gặp kết quả "chưa đủ" mà lời lỗi không nói rõ
    nguyên nhân thì hỏi `soonest_ready_wait`: còn key nào đang hồi (gần như
    LUÔN có) -> coi là HẾT LƯỢT -> đợi rồi phân tích lại. Câu trả lời của AI
    đã được lưu (`local_step`) nên lượt sau ra Y HỆT -> lặp tới trần 12 vòng.
  * 161 job tháng 11 mang lý do đó: lượt chạy cuối trung vị 0,1 phút (= phát
    lại kết quả đã lưu), từ lúc xếp -> xong trung vị 56,5 phút (job khác 35,3).
  * Ngoài ra `studio_page._pipe_nhan_lai_vang` NHẬN LẠI video có
    `continuity_incomplete` lúc mở app.
Cùng bệnh: "vượt ngân sách hậu kiểm" (prompt dựng lại y hệt mỗi lượt) và
"đoạn nối chứa lời quảng cáo" (nhánh ở m1).

GIỮ NGUYÊN: lỗi MẠNG / hết lượt / kiểm chứng sai định dạng VẪN là chưa kiểm
(chạy lại có thể khác) — cổng 94 CA 4 cũng canh điều đó.

KHÔNG MẠNG · KHÔNG GROQ · tiền định.
Chạy:  .venv\\Scripts\\python -u _test_hau_kiem_xong.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from app.ai import continuity_cut as cc  # noqa: E402

DAT = HONG = 0
XONG = ("reviewed", "skipped")


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}")
    else:
        HONG += 1
        print(f"  HỎNG {ten}  {chi_tiet}")


TR = {"segments": [{"start": float(i), "end": float(i + 5), "text": f"cau {i // 5}"}
                   for i in range(0, 120, 5)]}
DUR = 120.0
G = [[10.0, 30.0], [40.0, 60.0]]


def gia(tra):
    so = {"goi": 0}

    def cj(prompt, **_kw):
        so["goi"] += 1
        return tra(prompt)
    return cj, so


print("CA 1 — AI đề xuất id SAI -> giữ bản chọn và là quyết định ĐÃ XONG")
for ten, ids in (("thiếu slot", [0]), ("id ngoài phạm vi", [9999, 9999]),
                 ("không phải list", "abc"), ("sai thứ tự slot", None)):
    def tra(p, ids=ids):
        if ids is None:      # đảo slot: chọn id của slot 1 cho vị trí 0
            import json
            o = json.loads(p[p.index('{"options"'):])["options"]
            return {"ids": [next(x["id"] for x in o if x["slot"] == 1),
                            next(x["id"] for x in o if x["slot"] == 0)]}
        return {"ids": ids}
    cj, so = gia(tra)
    cut, au = cc.review(G, TR, DUR, 20, 80, cj)
    ok(cut == G and au.get("status") == "reviewed" and au.get("changed") is False,
       f"1 {ten}: giữ gốc + reviewed", au)
    ok(so["goi"] == 1, f"1 {ten}: chỉ 1 lượt LLM", so["goi"])

print("CA 2 — đề xuất làm tổng VƯỢT Max -> vẫn là quyết định đã xong")
def tra2(p):
    import json
    o = json.loads(p[p.index('{"options"'):])["options"]
    return {"ids": [max((x for x in o if x["slot"] == s), key=lambda x: x["end"] - x["start"])["id"]
                    for s in (0, 1)]}
cj, so = gia(tra2)
cut, au = cc.review(G, TR, DUR, 20, 40.5, cj)
ok(cut == G and au.get("status") == "reviewed", "2a sai thời lượng -> reviewed", au)

print("CA 3 — ngữ cảnh vượt ngân sách -> 'skipped', 0 lượt LLM")
TR_DAI = {"segments": [{"start": float(i), "end": float(i + 5), "text": "x" * 4000}
                       for i in range(0, 120, 5)]}
cj, so = gia(lambda p: {"ids": []})
cut, au = cc.review(G, TR_DAI, DUR, 20, 80, cj)
ok(cut == G and au.get("status") == "skipped", "3a status skipped", au)
ok(so["goi"] == 0, "3b không gọi LLM", so["goi"])
ok("vượt ngân sách" in au.get("reason", ""), "3c lý do vẫn được ghi", au)

print("CA 4 — lỗi THẬT vẫn là chưa kiểm (không sửa quá tay)")
def nem(p, **_k):
    raise RuntimeError("429 rate_limit")
cut, au = cc.review(G, TR, DUR, 20, 80, nem)
ok(cut == G and au.get("status") not in XONG, "4a lỗi mạng/hết lượt -> chưa kiểm", au)
cj, so = gia(lambda p: {"ids": list(range(0))} if '"options"' in p else {"khong": 1})
def tra4(p):
    if '"options"' in p:
        import json
        o = json.loads(p[p.index('{"options"'):])["options"]
        return {"ids": [next(x["id"] for x in o if x["slot"] == 0 and x["start"] == 10.0 and x["end"] == 30.0),
                        max((x for x in o if x["slot"] == 1 and x["start"] == 40.0), key=lambda x: x["end"])["id"]]}
    return {"khong_dung": 1}
cj, so = gia(tra4)
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(cut == G and au.get("status") not in XONG, "4b kiểm chứng sai định dạng -> chưa kiểm", au)
cut, au = cc.review(G, {"segments": []}, DUR, 20, 80, cj)
ok(au.get("status") not in XONG, "4c không có lời thoại -> giữ như cũ (không đổi hành vi)", au)

print("CA 5 — m1_highlight: nhánh quảng cáo + điều kiện 'chưa kiểm' (đọc AST)")
src = (GOC / "app" / "modules" / "m1_highlight.py").read_text(encoding="utf-8")


def kiem_m1(ma: str):
    """-> (nhánh quảng cáo trả reviewed?, điều kiện chưa-kiểm chấp nhận skipped?)"""
    cay = ast.parse(ma)
    qc = dk = False
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            kv = {k.value: v for k, v in zip(n.keys, n.values)
                  if isinstance(k, ast.Constant)}
            r = kv.get("reason")
            if isinstance(r, ast.Constant) and "quảng cáo" in str(r.value):
                st = kv.get("status")
                qc = isinstance(st, ast.Constant) and st.value == "reviewed"
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.NotIn):
            l = n.left
            if (isinstance(l, ast.Subscript) and isinstance(l.value, ast.Name)
                    and l.value.id == "continuity" and isinstance(n.comparators[0], ast.Tuple)):
                vals = {e.value for e in n.comparators[0].elts if isinstance(e, ast.Constant)}
                dk = vals == set(XONG)
    return qc, dk


qc, dk = kiem_m1(src)
ok(qc, "5a nhánh 'đoạn nối chứa quảng cáo' mang status reviewed")
ok(dk, "5b continuity_incomplete chỉ khi status KHÔNG thuộc (reviewed, skipped)")
# TỰ KIỂM BỘ DÒ: dựng lại đúng mã CŨ -> bộ dò phải kêu.
cu = src.replace('continuity = {"status": "reviewed", "changed": False,\n'
                 '                                  "reason": "Đoạn nối chứa lời quảng cáo',
                 'continuity = {"status": "needs_review", "changed": False,\n'
                 '                                  "reason": "Đoạn nối chứa lời quảng cáo')
cu = cu.replace('if continuity["status"] not in ("reviewed", "skipped"):',
                'if continuity["status"] != "reviewed":')
ok(cu != src, "5c tự kiểm: dựng được bản mã cũ (chuỗi neo còn khớp)")
ok(kiem_m1(cu) == (False, False), "5d tự kiểm: bộ dò BẮT được mã cũ", kiem_m1(cu))

print("CA 6 — bản mở rộng KHÔNG thêm lời thoại -> giữ bản chọn, KHÔNG gọi lượt kiểm chứng")
TR6 = {"segments": [{"start": 8.0, "end": 12.0, "text": "mot"},
                    {"start": 12.0, "end": 30.0, "text": "hai"},
                    {"start": 40.0, "end": 60.0, "text": "ba"}]}


def _chon(p, a0):
    import json
    o = json.loads(p[p.index('{"options"'):])["options"]
    return {"ids": [next(x["id"] for x in o if x["slot"] == 0 and x["start"] == a0 and x["end"] == 30.0),
                    next(x["id"] for x in o if x["slot"] == 1 and x["start"] == 40.0 and x["end"] == 60.0)]}


cj, so = gia(lambda p: _chon(p, 8.0) if '"options"' in p else {"chon": "ban_goc", "ly_do": "x"})
cut, au = cc.review(G, TR6, DUR, 20, 80, cj)
ok(cut == G and au.get("status") == "reviewed" and au.get("changed") is False,
   "6a giữ bản chọn + reviewed", au)
ok(so["goi"] == 1, "6b chỉ 1 lượt LLM (bỏ lượt kiểm chứng)", so["goi"])
# Đối chứng: bản mở rộng CÓ thêm lời -> vẫn phải hỏi lượt kiểm chứng.
TR6b = {"segments": [{"start": 6.0, "end": 10.0, "text": "them"},
                     {"start": 10.0, "end": 30.0, "text": "hai"},
                     {"start": 40.0, "end": 60.0, "text": "ba"}]}
cj, so = gia(lambda p: _chon(p, 6.0) if '"options"' in p else {"chon": "ban_goc", "ly_do": "x"})
cut, au = cc.review(G, TR6b, DUR, 20, 80, cj)
ok(so["goi"] == 2, "6c đối chứng: thêm lời thoại -> vẫn hỏi kiểm chứng (2 lượt)", (so["goi"], au))

print("CA 7 — llm ghi cached_tokens của Groq ra nhật ký (mục 6)")
import glob, os, shutil, tempfile  # noqa: E401,E402
from types import SimpleNamespace as NS  # noqa: E402
import config  # noqa: E402
from app.ai import llm  # noqa: E402
_d = tempfile.mkdtemp(prefix="bq_test_hk_")
_cu = config.DATA_DIR
config.DATA_DIR = _d
try:
    u = NS(prompt_tokens=1000, completion_tokens=5, prompt_tokens_details=NS(cached_tokens=640))
    llm._ghi_chan_doan("openai/gpt-oss-120b", NS(usage=u, choices=[NS(finish_reason="stop")]), "{}")
    fs = glob.glob(os.path.join(_d, "logs", "groq_cache_*.log"))
    txt = open(fs[0], encoding="utf-8").read() if fs else ""
    ok("vao=1000 ra=5 cache=640" in txt, "7a nhật ký có token vào + token cache", txt)
    ok(llm._cached_tokens(NS(prompt_tokens=3)) == 0, "7b thiếu prompt_tokens_details -> 0, không ném")
    ok(llm._cached_tokens({"prompt_tokens_details": {"cached_tokens": 7}}) == 7, "7c dạng dict cũng đọc được")
finally:
    config.DATA_DIR = _cu
    shutil.rmtree(_d, ignore_errors=True)

print(f"\nKETQUA cổng 115: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
