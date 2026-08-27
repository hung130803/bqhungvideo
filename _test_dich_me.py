# -*- coding: utf-8 -*-
"""CỔNG 93 — DỊCH PHẢI CHIA MẺ THEO NGÂN SÁCH TOKEN, VÀ CỔNG CHẤM PHẢI CHẠY.

Số **93** lấy bằng cách ĐỌC `_chay_hoi_quy.CONG` (max đang là 92), không đếm
theo trí nhớ — trùng số là hai cổng ghi đè `_kq93.txt` của nhau (bài học 70 vs
69, 85 vs 81).

**HAI BỆNH CỔNG NÀY CANH, cả hai đều "app vẫn chạy, mọi cổng vẫn xanh":**

(a) **LỆCH BẬC.** `_dich_loat` bản cũ gửi CẢ LOẠT câu trong MỘT lượt. Groq
    trần **8.000 token/phút** và tính CẢ `max_tokens` vào cỡ yêu cầu, nên
    video 167 câu ra prompt 4.064 token + chỗ trả lời 3.436 — trong khi bản
    dịch cần ~3.340. Chật tới mức model **GỘP/BỎ vài câu rồi ĐÁNH SỐ TIẾP**,
    tức mọi câu phía sau mang bản dịch của câu KHÁC. `_theo_nhan` chỉ hỏi
    *"nhãn #i có về không"* — nhãn VỀ ĐỦ, nên **không phép kiểm nào của app
    với tới**. Đo trên video THẬT 396 s (bộ dò dịch-ngược + chrF):
        đường app `dich_hau_kiem` -> **LỆCH BẬC 29,3% / 6,0%** (2 lượt)
        `_dich_loat` một mình     -> **6,6% / 31,7%**  · Trung->Anh **25,1%**
        video 65 câu (lọt MỘT lượt) -> **0,0%**  <- đối chứng
        SAU KHI CHIA MẺ + ngữ cảnh -> **0,6% / 1,2%**

(b) **CỔNG CHẤM TỰ PASS OAN.** `_dich_nguoc_cham` bản cũ nhét cả (gốc + dịch)
    của MỌI câu vào một prompt: 167 câu ra **9.712 token**, vượt trần TPM
    TRƯỚC KHI cộng chỗ trả lời -> **413 mọi lượt** -> `except` nuốt -> trả
    `[10.0] * n`. App báo *"điểm TB 10,0 · 0 câu phải dịch lại"* cho bản dịch
    có ~30% câu lệch bậc. Đúng họ bẫy "phép đo hỏng phát chứng nhận"
    (`astats` cổng 53 · `startswith` cổng 44).

CỔNG NÀY **KHÔNG GỌI MẠNG**: `llm.complete_json` bị thay bằng hàm GIÁN ĐIỆP
ghi lại từng prompt rồi trả JSON đúng nhãn. Nhờ vậy nó đọc HÀNH VI THẬT (gọi
mấy lượt, mỗi lượt mấy câu, prompt bao nhiêu token) chứ không quét chuỗi —
quét chuỗi thì luôn có phép phá giữ nguyên mặt chữ mà đổi ý nghĩa (bài học
cổng 56d).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

DAT = 0
HONG = 0


def ok(dieu: bool, mo_ta: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print("  ĐẠT  %s%s" % (mo_ta, (" — " + chi_tiet) if chi_tiet else ""))
    else:
        HONG += 1
        print("  HỎNG %s%s" % (mo_ta, (" — " + chi_tiet) if chi_tiet else ""))


def cau_gia(n: int, ky_tu: int = 12) -> list[dict]:
    """Bộ câu giả CÓ HÌNH DẠNG THẬT: 12 chữ Hán/câu, khung 2,35 s — đúng số đo
    trên video của anh Hùng (167 câu · 12,2 ký tự · 2,35 s)."""
    return [{"start": round(i * 2.35, 3), "end": round(i * 2.35 + 2.2, 3),
             "text": "".join(chr(0x4E00 + (i * 7 + k) % 2000)
                             for k in range(ky_tu))}
            for i in range(n)]


class GianDiep:
    """Thay `llm.complete_json` — ghi sổ prompt rồi trả ĐÚNG nhãn được hỏi."""

    def __init__(self, khoa: str = "t", hong_me: int = -1, gia_tri=None):
        self.muc: list[dict] = []
        self.khoa = khoa
        self.hong_me = hong_me          # mẻ thứ mấy thì NÉM (mô phỏng lỗi)
        self.gia_tri = gia_tri
        self._cu = None

    def bat(self):
        from app.ai import llm
        self._cu = llm.complete_json
        import re

        def bao(prompt, system="", provider=None, model=None):
            nhan = [int(x) for x in re.findall(r"^#(\d+)[ \[\n]", prompt,
                                               re.M)]
            mt = llm.max_tokens_groq(prompt, system)
            self.muc.append({
                "nhan": nhan, "so_muc": len(nhan),
                "prompt": prompt,
                "tok": llm._uoc_token(prompt) + llm._uoc_token(system),
                "max_tokens": mt})
            if len(self.muc) - 1 == self.hong_me:
                raise llm.LLMError("mẻ hỏng (mô phỏng)")
            gt = self.gia_tri
            return [{"i": i, self.khoa: (gt if gt is not None
                                         else "dich_%d" % i)} for i in nhan]
        llm.complete_json = bao
        return self

    def tat(self):
        if self._cu is not None:
            from app.ai import llm
            llm.complete_json = self._cu
            self._cu = None

    def __enter__(self):
        return self.bat()

    def __exit__(self, *a):
        self.tat()


# ==========================================================================
def ca1_chia_me_thuan() -> None:
    """CA 1 — `chia_me_dich` là hàm THUẦN, ca biên không nổ."""
    from app.core import thay_giong as TG
    print("\nCA 1 — chia_me_dich (hàm thuần, không mạng)")
    ok(TG.chia_me_dich([], []) == [], "rỗng -> []")
    c1 = cau_gia(1)
    ok(TG.chia_me_dich(c1, [0]) == [[0]], "1 câu -> 1 mẻ 1 câu")
    c = cau_gia(167)
    me = TG.chia_me_dich(c, list(range(167)))
    ok(sum(len(m) for m in me) == 167 and
       [i for m in me for i in m] == list(range(167)),
       "phủ ĐỦ và ĐÚNG THỨ TỰ 167 nhãn",
       "%d mẻ · cỡ %s" % (len(me), [len(m) for m in me]))
    ok(all(len(m) <= TG.ME_TOI_DA for m in me),
       "không mẻ nào vượt trần ME_TOI_DA=%d" % TG.ME_TOI_DA)
    # câu DÀI BẤT THƯỜNG (400 ký tự) vẫn phải chia được, không lặp vô hạn
    dai = cau_gia(20, ky_tu=400)
    md = TG.chia_me_dich(dai, list(range(20)))
    ok(sum(len(m) for m in md) == 20, "câu 400 ký tự vẫn chia đủ",
       "cỡ %s" % [len(m) for m in md])


def ca2_ngan_sach() -> None:
    """CA 2 — MỆNH ĐỀ TRUNG TÂM: mọi lượt gọi THẬT phải còn chỗ trả lời rộng
    gấp `ME_HE_SO_ROI` lần mức cần, và không lượt nào chạm trần TPM."""
    from app.ai import llm
    from app.core import thay_giong as TG
    print("\nCA 2 — ngân sách token của TỪNG lượt gọi THẬT (167 câu)")
    c = cau_gia(167)
    with GianDiep() as g:
        TG._dich_loat(c, "vi", "zh")
    ok(len(g.muc) >= 5, "chia thành nhiều mẻ, KHÔNG dồn 1 lượt",
       "%d lượt · cỡ %s" % (len(g.muc), [m["so_muc"] for m in g.muc]))
    xau = [(m["tok"], m["max_tokens"], m["so_muc"]) for m in g.muc
           if m["tok"] + m["max_tokens"] > llm.GROQ_TPM_TRAN]
    ok(not xau, "không lượt nào vượt trần TPM %d" % llm.GROQ_TPM_TRAN,
       str(xau[:3]))
    # **SÀN GHI CỨNG, KHÔNG ĐỌC `TG.ME_HE_SO_ROI`.** Đo bằng chính hằng số
    # đang canh thì hạ hằng số là hai vế cùng tụt và mục này TỰ ĐẠT — lượt
    # thử phá đầu đã LỌT đúng phép đó (`ME_HE_SO_ROI = 4.0 -> 1.0`).
    SAN_ROI, SAN_TOK = 4.0, 20
    hep = [(m["so_muc"], m["max_tokens"]) for m in g.muc
           if m["max_tokens"] < SAN_TOK * m["so_muc"] * SAN_ROI]
    ok(not hep, "mọi mẻ còn chỗ trả lời >= %.0f lần mức cần (sàn GHI CỨNG)"
       % SAN_ROI, str(hep[:3]))
    ok(TG.ME_HE_SO_ROI >= SAN_ROI and TG.ME_TOKEN_RA_MOI_CAU >= SAN_TOK,
       "hằng số trong mã không bị hạ dưới sàn đã đo",
       "ME_HE_SO_ROI=%s · ME_TOKEN_RA_MOI_CAU=%s"
       % (TG.ME_HE_SO_ROI, TG.ME_TOKEN_RA_MOI_CAU))
    # BỆNH (b): cổng chấm cũng phải chia mẻ
    g2 = GianDiep(khoa="d", gia_tri=9).bat()
    try:
        diem = TG._dich_nguoc_cham([x["text"] for x in c],
                                   ["ban dich rat dai " * 4] * 167,
                                   "zh", "vi")
    finally:
        g2.tat()
    ok(len(g2.muc) >= 5, "cổng CHẤM cũng chia mẻ",
       "%d lượt · cỡ %s" % (len(g2.muc), [m["so_muc"] for m in g2.muc]))
    qua = [m["tok"] for m in g2.muc
           if m["tok"] + m["max_tokens"] > llm.GROQ_TPM_TRAN]
    ok(not qua, "cổng CHẤM không lượt nào vượt trần TPM", str(qua[:3]))
    ok(len(diem) == 167 and all(d == 9.0 for d in diem),
       "cổng CHẤM trả ĐÚNG điểm cho đủ 167 câu (không rơi fail-safe 10,0)",
       "điểm[0]=%s · điểm[-1]=%s" % (diem[0], diem[-1]))


def ca3_ngu_canh() -> None:
    """CA 3 — mỗi mẻ mang NGỮ CẢNH hai bên, và ngữ cảnh KHÔNG được mang nhãn
    (mang nhãn là model dịch luôn phần ngữ cảnh -> đẻ ra câu thừa)."""
    from app.core import thay_giong as TG
    print("\nCA 3 — ngữ cảnh trước/sau + bối cảnh cả bài")
    c = cau_gia(167)
    with GianDiep() as g:
        TG._dich_loat(c, "vi", "zh")
    p1 = g.muc[1]["prompt"]
    ok("ĐOẠN NGAY TRƯỚC" in p1 and "ĐOẠN NGAY SAU" in p1,
       "mẻ giữa có CẢ HAI phía ngữ cảnh")
    ok("BỐI CẢNH CẢ VIDEO" in p1, "có bối cảnh cả bài")
    truoc_that = c[g.muc[1]["nhan"][0] - 1]["text"]
    ok(truoc_that in p1, "ngữ cảnh TRƯỚC là câu gốc THẬT ngay trước mẻ")
    ok(set(g.muc[1]["nhan"]).isdisjoint({g.muc[0]["nhan"][-1]}),
       "câu ngữ cảnh KHÔNG mang nhãn # (không bị dịch lại)")
    p0 = g.muc[0]["prompt"]
    ok("(đầu bài)" in p0, "mẻ ĐẦU ghi rõ là đầu bài")
    ok("(cuối bài)" in g.muc[len(g.muc) - 1]["prompt"],
       "mẻ CUỐI ghi rõ là cuối bài")


def ca4_video_ngan() -> None:
    """CA 4 — BẤT BIẾN: video ngắn vẫn ĐI MỘT LƯỢT, không đẻ thêm lượt gọi."""
    from app.core import thay_giong as TG
    print("\nCA 4 — video NGẮN không bị chia vụn (bất biến giá)")
    for n in (5, 20, 30):
        c = cau_gia(n)
        with GianDiep() as g:
            TG._dich_loat(c, "vi", "zh")
        ok(len(g.muc) == 1, "%d câu -> ĐÚNG 1 lượt gọi" % n,
           "%d lượt" % len(g.muc))


def ca5_me_hong() -> None:
    """CA 5 — MỘT MẺ HỎNG KHÔNG ĐƯỢC GIẾT CẢ VIDEO (chống all-or-nothing)."""
    from app.core import thay_giong as TG
    print("\nCA 5 — một mẻ hỏng thì mẻ khác vẫn ra chữ")
    c = cau_gia(167)
    g = GianDiep(hong_me=0).bat()
    # **PHẢI BẮT NGOẠI LỆ Ở ĐÂY.** Bản hỏng (một mẻ lỗi -> bỏ cả loạt) sẽ NÉM;
    # để nó nổi lên là cổng CHẾT GIỮA CHỪNG, mất luôn dòng tổng kết và đọc ra
    # không phân biệt được với "chưa chạy tới chốt" (bài học cổng 74 lỗi b).
    bd, nem = [], ""
    try:
        bd = TG._dich_loat(c, "vi", "zh")
    except Exception as e:                                    # noqa: BLE001
        nem = "%s: %s" % (type(e).__name__, e)
    finally:
        g.tat()
    dich_duoc = sum(1 for i, t in enumerate(bd) if t != c[i]["text"])
    ok(not nem and dich_duoc > 100,
       "mẻ 1 ném lỗi -> vẫn dịch được phần lớn",
       nem or "%d/167 câu có bản dịch" % dich_duoc)
    ok(len(bd) == 167, "trả ĐÚNG 167 phần tử, không nuốt câu nào")
    # mọi mẻ hỏng -> phải NÉM (không im lặng trả toàn câu gốc)
    from app.ai import llm

    class MoiMeHong(GianDiep):
        def bat(self):
            super().bat()
            cu = llm.complete_json

            def bao(prompt, system="", provider=None, model=None):
                cu(prompt, system=system)
                raise llm.LLMError("hỏng hết (mô phỏng)")
            llm.complete_json = bao
            return self
    g2 = MoiMeHong().bat()
    try:
        TG._dich_loat(c, "vi", "zh")
        nem = False
    except Exception:                                         # noqa: BLE001
        nem = True
    finally:
        g2.tat()
    ok(nem, "MỌI mẻ hỏng -> NÉM, không im lặng trả nguyên câu gốc")


def ca6_tu_kiem() -> None:
    """CA 6 — TỰ KIỂM BỘ DÒ: dựng lại HÀNH VI CŨ (một lượt cho cả loạt) thì
    CA 2 phải KÊU. Không có mục này thì cổng chỉ là con dấu."""
    from app.ai import llm
    from app.core import thay_giong as TG
    print("\nCA 6 — TỰ KIỂM BỘ DÒ (dựng lại bản CŨ, cổng phải kêu)")
    c = cau_gia(167)
    cu = TG.chia_me_dich
    TG.chia_me_dich = lambda cau, chi_so, **kw: [list(chi_so)]  # bản CŨ
    try:
        with GianDiep() as g:
            TG._dich_loat(c, "vi", "zh")
        mot_luot = (len(g.muc) == 1)
        hep = any(m["max_tokens"] < TG.ME_TOKEN_RA_MOI_CAU * m["so_muc"]
                  * TG.ME_HE_SO_ROI for m in g.muc)
        g2 = GianDiep(khoa="d", gia_tri=9).bat()
        try:
            diem = TG._dich_nguoc_cham([x["text"] for x in c],
                                       ["ban dich rat dai " * 4] * 167,
                                       "zh", "vi")
        finally:
            g2.tat()
        qua = any(m["tok"] + m["max_tokens"] > llm.GROQ_TPM_TRAN
                  for m in g2.muc)
    finally:
        TG.chia_me_dich = cu
    ok(mot_luot and hep,
       "bản CŨ: 1 lượt cho 167 câu VÀ chỗ trả lời CHẬT -> CA 2 kêu đúng")
    ok(qua, "bản CŨ: cổng chấm VƯỢT TRẦN TPM -> CA 2 kêu đúng",
       "prompt %d tok + max_tokens %d > %d"
       % (g2.muc[0]["tok"], g2.muc[0]["max_tokens"], llm.GROQ_TPM_TRAN))
    ok(len(diem) == 167, "bản cũ vẫn trả đủ 167 điểm (do gián điệp không 413)")


def main() -> int:
    print("=" * 70)
    print("CỔNG 93 — DỊCH CHIA MẺ THEO NGÂN SÁCH TOKEN")
    print("=" * 70)
    ca1_chia_me_thuan()
    ca2_ngan_sach()
    ca3_ngu_canh()
    ca4_video_ngan()
    ca5_me_hong()
    ca6_tu_kiem()
    print("\n" + "=" * 70)
    print("KETQUA: ĐẠT %d · HỎNG %d" % (DAT, HONG))
    print("=" * 70)
    Path(REPO / "_kq93.txt").write_text(
        json.dumps({"dat": DAT, "hong": HONG}, ensure_ascii=False),
        encoding="utf-8")
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
