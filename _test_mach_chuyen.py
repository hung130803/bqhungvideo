# -*- coding: utf-8 -*-
"""CỔNG 94 — HẬU KIỂM MẠCH CHUYỆN (`app/ai/continuity_cut.py`) KHÔNG ĐƯỢC
TRƯỢT OAN MỌI CLIP, VÀ KHÔNG ĐƯỢC PHÁ HOOK-FIRST KHI ĐÃ CHỊU NHẬN ĐỀ XUẤT.

Anh Hùng (27/10/2026): xem lại "bộ kiểm mạch chuyện". Đo trên máy thật:
nhật ký dây chuyền 26/10 có **295/296** lượt chọn clip mang cảnh báo
"Mạch chuyện: ..." (tiếng Anh); chạy lại bước kiểm chứng bằng Groq THẬT trên
**10 clip đã xuất** -> **10/10 TRƯỢT, trượt cả 4 tiêu chí cùng lúc**. Lý do
model đưa ra đều là "thiếu bối cảnh / không có hỏi-đáp / không có kết" — một
đoạn trích 1-2 phút của video dài KHÔNG BAO GIỜ thoả được, nhất là khi prompt
còn dặn "không đủ bằng chứng phải trả false".

4 LỖI, mỗi lỗi một ca canh:
 (a) giữ nguyên bản ghép vẫn bị bắt qua kiểm chứng tuyệt đối -> trượt -> cảnh
     báo trên MỌI video + tốn thêm 1 lượt LLM (đo được tới 115 s/lượt).
 (b) chặn "cắt giữa câu" tính cả mốc CỦA BẢN GỐC (mốc gốc khớp từng chữ, còn
     dòng chép lời rất thô) -> gần như mọi đề xuất bị loại.
 (c) kiểm chứng TUYỆT ĐỐI thay vì SO SÁNH gốc với đề xuất.
 (d) LỖI ẨN: `validate` SẮP LẠI các đoạn theo thời gian -> clip hook-first
     (ngược thời gian) mất hook ngay khi một đề xuất được nhận. Chưa từng nổ
     CHỈ VÌ (c) chưa bao giờ nhận đề xuất nào — vá (c) mà sót (d) là nổ ngay.

KHÔNG MẠNG · KHÔNG GROQ: `complete_json` là hàm giả trả lời theo kịch bản và
GHI SỔ từng lượt gọi, nên cổng TIỀN ĐỊNH.

Chạy:  .venv\\Scripts\\python -u _test_mach_chuyen.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from app.ai import continuity_cut as cc  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}")
    else:
        HONG += 1
        print(f"  HỎNG {ten}  {chi_tiet}")


# Lời thoại giả: mỗi câu 5 giây, 0..120 s.
TR = {"segments": [{"start": float(i), "end": float(i + 5), "text": f"cau {i // 5}"}
                   for i in range(0, 120, 5)]}
DUR = 120.0


def gia(de_xuat=None, chon="de_xuat", loi_kiem=False):
    """complete_json giả. de_xuat(options, goc_ids) -> list id; None = giữ gốc."""
    so = {"goi": 0, "prompt": []}

    def cj(prompt, **_kw):
        so["goi"] += 1
        so["prompt"].append(prompt)
        if '"options"' in prompt:
            data = json.loads(prompt[prompt.index('{"options"'):])
            opts = data["options"]
            goc = [next(o["id"] for o in opts if o["slot"] == s and o["start"] == G[s][0]
                        and o["end"] == G[s][1]) for s in sorted({o["slot"] for o in opts})]
            ids = goc if de_xuat is None else de_xuat(opts, goc)
            return {"ids": ids, "reason": "x"}
        if loi_kiem:
            return {"khong_dung": 1}
        return {"chon": chon, "ly_do": "dễ theo dõi hơn"}
    return cj, so


def mo_rong_cuoi(slot):
    """Đề xuất: slot `slot` lấy phương án có ĐUÔI dài nhất, slot khác giữ gốc."""
    def f(opts, goc):
        ids = list(goc)
        cung = [o for o in opts if o["slot"] == slot and o["start"] == G[slot][0]]
        ids[slot] = max(cung, key=lambda o: o["end"])["id"]
        return ids
    return f


print("CA 1 — giữ nguyên bản ghép: 1 lượt gọi, KHÔNG cảnh báo")
G = [[10.0, 30.0], [40.0, 60.0]]
cj, so = gia(None)
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(au["status"] == "reviewed" and au["changed"] is False, "1a status reviewed, changed False", au)
ok(so["goi"] == 1, "1b chỉ 1 lượt LLM (không kiểm chứng thừa)", so["goi"])
ok(cut == G, "1c giữ nguyên mốc", cut)

print("CA 2 — đề xuất tốt hơn được NHẬN (trước 27/10: không bao giờ)")
cj, so = gia(mo_rong_cuoi(1), chon="de_xuat")
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(au["status"] == "reviewed" and au["changed"] is True, "2a nhận đề xuất", au)
ok(cut[1][1] > 60.0 and cut[0] == [10.0, 30.0], "2b chỉ đuôi slot 1 dài ra", cut)
ok(so["goi"] == 2, "2c đúng 2 lượt LLM", so["goi"])
p = so["prompt"][1]
ok('"ban_goc"' in p and '"de_xuat"' in p, "2d kiểm chứng là SO SÁNH gốc với đề xuất")
ok("phải trả false" not in p, "2e bỏ câu ép trượt 'không đủ bằng chứng phải trả false'")
ok("tiếng Việt" in p, "2f lý do đòi tiếng Việt")

print("CA 3 — kiểm chứng chọn bản gốc: giữ gốc, vẫn là quyết định HỢP LỆ")
cj, so = gia(mo_rong_cuoi(1), chon="ban_goc")
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(cut == G and au["status"] == "reviewed" and au["changed"] is False, "3a giữ gốc, không cảnh báo", au)

print("CA 4 — kiểm chứng lỗi/sai định dạng: giữ gốc VÀ không chứng nhận")
cj, so = gia(mo_rong_cuoi(1), loi_kiem=True)
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(cut == G and au["status"] != "reviewed", "4a sai định dạng -> chưa kiểm (giữ cảnh báo)", au)

def nem(prompt, **_kw):
    raise RuntimeError("mạng chết")
cut, au = cc.review(G, TR, DUR, 20, 80, nem)
ok(cut == G and au["status"] != "reviewed", "4b lỗi mạng -> giữ gốc, chưa kiểm", au)

print("CA 5 — HOOK-FIRST (ngược thời gian) giữ nguyên thứ tự khi nhận đề xuất")
G = [[70.0, 80.0], [20.0, 40.0]]
cj, so = gia(mo_rong_cuoi(1), chon="de_xuat")
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(au["changed"] is True, "5a đề xuất được nhận", au)
ok(cut[0] == [70.0, 80.0] and cut[1][0] == 20.0, "5b hook (đoạn 70-80s) VẪN đứng đầu", cut)
# TỰ KIỂM BỘ DÒ: cách gộp CŨ (sắp theo thời gian) phải làm 5b vỡ.
cu = sorted([list(x) for x in cut])
ok(cu[0][0] != 70.0, "5c tự kiểm: gộp-sắp-xếp kiểu cũ làm mất hook (ca 5b có răng)", cu)

print("CA 6 — validate")
ok(cc._merge_in_order([[10, 20], [18, 30]]) == [[10, 30]], "6a nối tiếp xuôi thì gộp")
ok(cc._merge_in_order([[50, 60], [10, 20]]) == [[50, 60], [10, 20]], "6b ngược thời gian giữ thứ tự")
ok(cc._merge_in_order([[50, 60], [55, 58], [10, 20]]) == [[50, 60], [10, 20]], "6c đoạn nằm trong đoạn trước thì gộp")
ok(cc._merge_in_order([[50, 60], [10, 20], [15, 25]]) == [[50, 60], [10, 25]], "6d gộp kề sau hook")
ok(cc._merge_in_order([[50, 60], [10, 55]]) is None, "6e chồng lấn chạy lại cảnh -> loại")

print("CA 7 — chặn cắt giữa câu CHỈ ở mốc bị DỜI")
# Gốc cắt giữa câu (12,5 nằm trong câu 10-15) — mốc gốc KHÔNG được làm đề xuất trượt.
G = [[12.5, 30.0], [40.0, 60.0]]
cj, so = gia(mo_rong_cuoi(1), chon="de_xuat")
cut, au = cc.review(G, TR, DUR, 20, 80, cj)
ok(au["changed"] is True and cut[0][0] == 12.5, "7a mốc gốc giữa câu vẫn cho nhận đề xuất", au)
# Đề xuất DỜI mốc vào giữa câu -> loại, giữ gốc.
TR2 = {"segments": TR["segments"] + [{"start": 58.0, "end": 66.0, "text": "cau chen"}]}
G = [[10.0, 30.0], [40.0, 55.0]]
def doi_giua(opts, goc):
    ids = list(goc)
    cho = [o for o in opts if o["slot"] == 1 and o["start"] == 40.0 and 55.0 < o["end"] < 66.0]
    ids[1] = cho[0]["id"]
    return ids
opts = cc.candidates(G, TR2, DUR)
co_ca = [o["end"] for o in opts if o["slot"] == 1 and 55.0 < o["end"] < 66.0
         and cc._mid_sentence(o["end"], TR2)]
ok(bool(co_ca), "7b0 dữ liệu giả CÓ phương án dời mốc vào giữa câu", co_ca)
cj, so = gia(doi_giua, chon="de_xuat")
cut, au = cc.review(G, TR2, DUR, 20, 80, cj)
ok(cut == G and au["changed"] is False and so["goi"] == 1,
   "7b mốc mới rơi giữa câu -> giữ gốc, không gọi kiểm chứng", (cut, au, so["goi"]))

print()
print(f"KẾT QUẢ: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
