# -*- coding: utf-8 -*-
"""THƯỚC CHẤM BẢN DỊCH — luật máy + HỘI ĐỒNG nhiều model + soát thuật ngữ.

VÌ SAO CÓ FILE NÀY. Thước cũ (`thay_giong._dich_nguoc_cham`) chỉ hỏi MỘT model
MỘT câu hỏi: *"bản dịch có GIỐNG NGHĨA câu gốc không?"*. Nó cho **7,85-7,97/10**
trên chính bản dịch đã dịch `新片` (phim mới) thành **"phim về chip"** — tức nó
phát chứng chỉ cho thứ vẫn hỏng. Ba chỗ hổng của cách hỏi đó:

1. **GỘP 4 THỨ VÀO 1 SỐ.** "Giống nghĩa" không phân biệt được câu SAI NGHĨA với
   câu đúng nghĩa mà NGƯỢC TAI. Nay chấm **4 tiêu chí TÁCH BẠCH** và lấy điểm
   chốt = **THẤP NHẤT** trong 4 (bản dịch chỉ tốt bằng trục tệ nhất của nó).
2. **MỘT MODEL LÀ MỘT Ý KIẾN.** Một model dễ dãi là cả phép đo dễ dãi. Nay
   **HỘI ĐỒNG 3 model khác họ**, lấy **TRUNG VỊ** — muốn qua cửa thì phải lừa
   được ít nhất 2/3, khó hơn hẳn.
3. **THUẬT NGỮ SAI CHÌM TRONG CÂU ĐÚNG.** Câu 11 chữ dịch sai 1 từ khoá vẫn
   "giống nghĩa ~80%". Nay có **lượt soát thuật ngữ RIÊNG** chỉ hỏi đúng một
   việc: *liệt kê từ nào bị dịch sai*. Đây là cửa bắt `新片 -> "phim về chip"`.

Thêm **LUẬT MÁY** (`loi_may`) chạy TRƯỚC, không tốn một lượt LLM nào và TIỀN
ĐỊNH: câu rỗng · còn chữ gốc · chép nguyên câu gốc · cụt · gộp. Luật máy là
SÀN — LLM có khen mấy thì câu dính luật máy vẫn TRƯỢT. Không có sàn này thì
cả phép đo phụ thuộc hoàn toàn vào tâm trạng của model.

BẤT BIẾN: hàm ở đây **CHỈ ĐỌC**, không sửa bản dịch. Chấm và sửa phải tách
nhau — bộ chấm mà tự sửa thì nó chấm chính bài của nó.

==========================================================================
THƯỚC NÀY ĐÃ TỰ KIỂM — SỐ CỦA CHÍNH NÓ (16/08/2026, `_do_thuoc_dich.py`)
==========================================================================
Bộ đối chứng `_do_bo_hong.py`: **30 bản dịch HỎNG CÓ CHỦ Ý** (6 loại lỗi,
câu gốc lấy nguyên văn video thật của anh Hùng) + **20 bản dịch TỐT**, TRỘN
LẪN rồi xáo tiền định trước khi gửi — đưa nguyên khối toàn-hỏng là mồi cho
model chấm gắt, con số ra sẽ là của cách xếp bài chứ không phải của thước.

**BẮT ĐÚNG: 30/30 = 100,0% — CẢ 4 LƯỢT, cả 6/6 loại lỗi.**
(LLM không tiền định nên chạy 1 lượt rồi báo số là tự lừa mình — CLAUDE.md đã
đo 0% vs 39,1% trên cùng một mã. Đây là 4 lượt, 2 lần gọi khác nhau.)
Trong đó có ĐÚNG ca đã đẻ ra file này: `新片 -> "phim về chip"` (thước cũ cho
7,85-7,97/10) và `落魄拳手 -> "võ sĩ xuống cấp"`.

**KÊU OAN CỦA v1: đây là mặt YẾU, và nó là lý do có v2.** Bản TỐT được cho ĐẠT
chỉ **11/20 · 17/20 · 14/20 · 12/20 = 67,5% trung bình**; đo lại bằng
`_do_dich_luat.py` trên 200 quan sát ra **38,8%** kêu oan (bộ kiểm 150 quan
sát: **25,0%**). Tức cứ 3 câu dịch tốt thì 1 câu bị đem đi dịch lại.

**HẠ NGƯỠNG KHÔNG CHỮA ĐƯỢC — ĐÃ ĐO, ĐỪNG THỬ LẠI.** `diem` (=MIN 4 trục) hai
nhóm CHỒNG NHAU: HỎNG 0,0..6,0 · TỐT 5,0..9,0. Chỉ hạ ngưỡng v1 từ 7,0 xuống
6,0 ra **99,2% bắt / 30,0% oan** (kiểm 95,6% / 20,0%) — vẫn không dùng được.

==========================================================================
v2 (16/08/2026) — NGƯỠNG RIÊNG TỪNG TRỤC. **ĐÍCH ĐẠT: bắt >= 90% · oan <= 10%**
==========================================================================
**GỐC BỆNH KHÔNG PHẢI CON SỐ NGƯỠNG MÀ LÀ PHÉP `MIN`.** Cả 4 trục đều tách
được hai nhóm (AUC: tron 0,941 · nghia 0,931 · xuoi 0,920 · noi 0,917), nhưng
một bản dịch TỐT thường bị hội đồng chê ĐÚNG MỘT trục (hay là văn phong) —
`MIN` biến một lá phiếu lạc thành một bản án. Nên v2 cho **mỗi trục một
ngưỡng riêng**, trục nào không chấm được thì BỎ QUA.

**CỬA THUẬT NGỮ LÀ NGUỒN KÊU OAN LỚN NHẤT** (đo từng cửa MỘT MÌNH, 200 quan sát):

    cửa                    | bắt hỏng | kêu oan
    luật máy               |   43,3%  |   0,0%
    thuật ngữ 1/3 model    |   93,3%  |  58,8%
    thuật ngữ 2/3 model    |   75,0%  |  18,8%   <- v1 dùng mức này
    thuật ngữ 3/3 model    |   25,0%  |   1,2%
    nghia >= 5 · 6 · 7     | 69,2/72,5/82,5% | 3,8/10,0/13,8%
    xuoi  >= 5 · 6 · 7     | 66,7/80,0/85,0% | 1,2/ 5,0/15,0%
    noi   >= 5 · 6 · 7     | 65,8/80,0/85,8% | 1,2/ 5,0/16,2%
    tron  >= 5 · 6 · 7     | 55,8/59,2/70,0% | 2,5/ 2,5/ 3,8%

**SỐ CỦA v2** (`NGUONG_TRUC` + `TN_CAN`=3 + `TN_NGUONG_NGHIA`=6,0). Mỗi bộ là
một lượt gọi LLM RIÊNG, xáo bài khác nhau — 700 quan sát tất cả:

    bộ (50 câu × số lượt)         |  v1 bắt/oan   |  **v2 bắt/oan**
    HIỆU CHUẨN (200 = 4 lượt)     | 100,0% / 38,8% |  97,5% / 10,0%
    KIỂM CHÉO  (150 = 3 lượt)     |  98,9% / 25,0% |  93,3% /  6,7%
    XÁC NHẬN   (150 = 3 lượt)     | 100,0% / 43,3% |  97,8% / 10,0%
    **GỘP NGOÀI MẪU (300)**       |  99,4% / 34,2% | **95,6% / 8,3%**

**ĐÍCH ĐẠT trên bộ NGOÀI MẪU: bắt 95,6% (>= 90%) · kêu oan 8,3% (<= 10%).**
Tức kêu oan hạ **34,2% -> 8,3%**, đổi lấy 3,8 điểm khả năng bắt.

BA ĐIỀU CHỐNG TỰ LỪA, đừng bỏ khi đo lại:
1. Luật chọn từ một DANH SÁCH NGẮN số tròn viết ra TRƯỚC, **không** lấy luật
   thắng lưới quét (~46.000 luật/200 quan sát). Luật thắng lưới đo 97,5%/6,2%
   trên bộ hiệu chuẩn nhưng chỉ **87,8%** trên bộ kiểm = học thuộc bài.
2. Bộ XÁC NHẬN được gọi SAU KHI luật đã chốt, không tham gia việc chọn.
3. Số của chính v1 nhấp nháy **25,0 .. 43,3%** giữa 3 bộ — một lượt đo không
   đủ để nói gì về thước này, đây là 10 lượt.

**MẶT YẾU CÒN LẠI, GHI THẲNG:** loại `nguoc_tai` (đúng nghĩa nhưng không ai
nói tiếng Việt như vậy) chỉ bắt **28/36 = 77,8%** ngoài mẫu (bộ hiệu chuẩn
87,5%). Đây là loại lỗi NHẤP NHÁY nhất vì nó phụ thuộc hoàn toàn vào khẩu vị
văn phong của hội đồng. **5 loại còn lại đều 100% ngoài mẫu**: thuat_ngu 36/36
· cut 30/30 · gop 24/24 · chu_han 24/24 · may_moc 30/30.

**THỬ PHÁ (gỡ từng chốt, 300 quan sát ngoài mẫu) — cổng này không phải con dấu:**
    nguyên vẹn                        95,6% bắt / 8,3% oan
    gỡ HẾT 4 trục                     52,8%   (**−42,8 điểm**)
    gỡ luật máy                       85,6%   (−10,0)
    gỡ ngưỡng `nghia`                 92,2%   (−3,3)
    gỡ ngưỡng `noi`                   92,8%   (−2,8)
    gỡ ngưỡng `xuoi`                  95,0%   (−0,6)
    gỡ ngưỡng `tron`                  95,6%   (±0,0 — luật máy đã bắt trọn)
    gỡ cửa thuật ngữ                  95,6%   (**±0,0 — cửa này KHÔNG gánh gì**)
**Cửa thuật ngữ ở mức 3/3 KHÔNG bắt thêm câu nào trên corpus này** — 4 trục đã
bắt trọn 18/18 ca `thuat_ngu` (kể cả `新片 -> "phim về chip"`). GIỮ nó lại làm
lưới an toàn cho video khác (giá đo được: 1,2% kêu oan khi đứng một mình), chứ
KHÔNG được kể nó vào công trạng của con số ở trên.

**BA CỬA GÁNH VIỆC KHÁC HẲN NHAU:**
  · **luật máy** (`loi_may`, TIỀN ĐỊNH, 0 lượt LLM): kêu oan **0,0%**, bắt
    TRỌN 3 loại lỗi HÌNH THỨC (cụt · gộp · còn chữ Hán) và **0** lỗi NGHĨA.
    Chính xác tuyệt đối, nhưng mù nghĩa.
  · **hội đồng 3 model**: cửa duy nhất với tới lỗi NGHĨA. Gỡ hết 4 trục là tụt
    93,3% -> 52,2%.
  · **soát thuật ngữ**: xem khối THỬ PHÁ ở trên.
"""
from __future__ import annotations

import re
import statistics
from typing import Iterable

# --------------------------------------------------------------------------
# HỘI ĐỒNG — 3 model KHÁC HỌ. Cùng một họ (vd oss-120b + oss-20b) thì chúng sai
# giống nhau, hội đồng chỉ còn là một model đắt tiền hơn.
# KHÔNG dùng model SUY LUẬN (qwen3.6): CLAUDE.md đã đo — nó tiêu hết max_tokens
# cho khối <think> rồi trả rỗng (0/3 lượt ở khâu chấm).
# --------------------------------------------------------------------------
MODEL_HOI_DONG = (
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
)

#: 4 trục chấm TÁCH BẠCH. Đổi tên khoá là đổi cả prompt — sửa cả hai chỗ.
TIEU_CHI = ("nghia", "xuoi", "noi", "tron")
TEN_TIEU_CHI = {
    "nghia": "đúng nghĩa",
    "xuoi": "xuôi tiếng Việt",
    "noi": "đúng văn nói",
    "tron": "không cụt / không gộp",
}

#: NGƯỠNG CŨ (v1) — MIN 4 trục >= 7,0. GIỮ LẠI để `_do_thuoc_dich.py` còn so
#: được với mốc; ĐƯỜNG CHẤM MẶC ĐỊNH KHÔNG CÒN DÙNG NÓ (xem `NGUONG_TRUC`).
NGUONG_DAT = 7.0

# --------------------------------------------------------------------------
# v2 — NGƯỠNG RIÊNG TỪNG TRỤC (hiệu chuẩn `_do_dich_luat.py`, 16/08/2026)
# --------------------------------------------------------------------------
# **VÌ SAO BỎ "MIN 4 TRỤC >= 7,0".** MIN bắt bản dịch phải tốt ĐỀU cả 4 trục
# ở cùng một mức, trong khi hai nhóm KHÔNG hề trải giống nhau. Đo AUC (xác
# suất một câu TỐT được chấm cao hơn một câu HỎNG) trên 200 quan sát:
#     tron 0,941 · nghia 0,931 · xuoi 0,920 · noi 0,917
# — bốn trục đều tách được, nhưng câu TỐT thường có ĐÚNG MỘT trục tụt (hội
# đồng chê văn phong), và MIN biến một lá phiếu lạc thành một bản án. Đó là
# toàn bộ 30-39% kêu oan của v1, và **hạ ngưỡng KHÔNG chữa được**: đo riêng
# "chỉ hạ v1 về 6,0" ra 99,2% bắt / **30,0%** oan (kiểm chéo 95,6% / 20,0%).
#
# **CỬA THUẬT NGỮ LÀ NGUỒN KÊU OAN LỚN NHẤT.** Đo từng cửa một mình:
#     thuật ngữ 1/3 model: bắt 93,3% · **kêu oan 58,8%**
#     thuật ngữ 2/3 model: bắt 75,0% · **kêu oan 18,8%**   <- v1 dùng mức này
#     thuật ngữ 3/3 model: bắt 25,0% · kêu oan  1,2%
# Nên v2 đòi **CẢ 3 model** cùng kêu, và chỉ cho nó phủ quyết khi trục
# `nghia` cũng dưới `TN_NGUONG_NGHIA` — một lỗi thuật ngữ THẬT thì kéo cả
# `nghia` xuống; kêu một mình trong khi `nghia` vẫn 9 là lượt soát đang bịa.
#
# SỐ ĐO CỦA CHÍNH LUẬT NÀY — xem docstring đầu file.
#: Ngưỡng RIÊNG từng trục. Câu ĐẠT khi MỌI trục đo được đều >= ngưỡng của nó.
NGUONG_TRUC = {"nghia": 5.0, "xuoi": 6.0, "noi": 6.0, "tron": 6.0}
#: Số model phải CÙNG kêu một khoá lỗi thì cửa thuật ngữ mới tính là lỗi.
TN_CAN = 3
#: Cửa thuật ngữ chỉ được phủ quyết khi `nghia` cũng dưới mức này.
#: `None` = phủ quyết vô điều kiện (hành vi v1).
TN_NGUONG_NGHIA = 6.0

#: Số câu mỗi lượt gọi. Groq trả 413 "Request too large" khi gói to — đó là lỗi
#: CỦA YÊU CẦU, phải THU NHỎ, KHÔNG được phạt key (bug cũ đã đốt sạch 38 key).
CO_MOI_LUOT = 12

# --------------------------------------------------------------------------
# LUẬT MÁY — hiệu chuẩn bằng `_do_nguong_dich.py` trên corpus THẬT, đừng chỉnh mò
# --------------------------------------------------------------------------
#: Tỉ lệ ÂM TIẾT TIẾNG VIỆT trên mỗi CHỮ HÁN của câu gốc. Dưới sàn = CỤT.
TY_LE_CUT = 0.45
#: Trên trần = GỘP (nuốt luôn câu kế) — hoặc câu có nhiều dấu kết câu.
TY_LE_GOP = 2.20
#: Câu gốc ngắn hơn ngần này chữ thì KHÔNG áp luật tỉ lệ (mẫu số quá nhỏ,
#: lệch 1 âm tiết đã đủ lật kết luận).
GOC_TOI_THIEU = 5

_KET_CAU = re.compile(r"[.!?…。！？]+")
_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def _so_chu_han(t: str) -> int:
    return len(_HAN.findall(t or ""))


def am_tiet_viet(t: str) -> int:
    """Đếm ÂM TIẾT tiếng Việt = cụm chữ cái ngăn bởi khoảng trắng/dấu câu.

    Tiếng Việt viết rời từng âm tiết nên đây cũng là đơn vị đọc — dùng chung
    cho cả phép đo ngân sách thời gian (`dich_theo_gio`).
    """
    return len([x for x in re.split(r"[^0-9A-Za-zÀ-ỹ]+", t or "") if x])


def _con_chu_goc(text: str, dich_sang: str) -> bool:
    """Bản dịch còn chữ của tiếng gốc (chữ Hán) mà đích KHÔNG dùng chữ đó."""
    from app.core.thay_giong import con_chu_goc
    return bool(con_chu_goc(text, dich_sang))


def loi_may(goc: str, dich: str, dich_sang: str = "vi") -> list[str]:
    """LUẬT MÁY: trả danh sách MÃ LỖI dò được mà KHÔNG cần LLM (tiền định).

    Mã: `rong` · `con_chu_goc` · `chep_goc` · `cut` · `gop`.
    Rỗng = máy không bắt được gì (KHÔNG có nghĩa là câu tốt — còn hội đồng).
    """
    g, d = (goc or "").strip(), (dich or "").strip()
    ra: list[str] = []
    if not d:
        return ["rong"]
    if _con_chu_goc(d, dich_sang):
        ra.append("con_chu_goc")
    # chép nguyên câu gốc (bỏ khoảng trắng để không bị lừa bởi cách ngắt)
    if re.sub(r"\s+", "", d) == re.sub(r"\s+", "", g):
        ra.append("chep_goc")

    n_goc = _so_chu_han(g) or am_tiet_viet(g)
    if n_goc >= GOC_TOI_THIEU:
        n_dich = am_tiet_viet(d)
        ty = n_dich / float(n_goc)
        if ty < TY_LE_CUT:
            ra.append("cut")
        elif ty > TY_LE_GOP:
            ra.append("gop")
    # Dấu kết câu nằm GIỮA câu = hai câu bị nhập một. Bỏ dấu ở cuối trước khi
    # đếm, và bỏ dấu ba chấm (nó là ngắt giọng, không phải hết câu).
    than = _KET_CAU.sub(
        lambda m: "" if m.end() >= len(d.rstrip()) else m.group(0),
        d.replace("...", " ").replace("…", " "))
    if "gop" not in ra and len(_KET_CAU.findall(than)) >= 1 and n_goc >= GOC_TOI_THIEU:
        ra.append("gop")
    return ra


# --------------------------------------------------------------------------
# HỘI ĐỒNG
# --------------------------------------------------------------------------
def _ten_nn(ma: str) -> str:
    from app.core.thay_giong import _ten_nn as t
    return t(ma)


def _theo_nhan(data, chi_so: list[int], khoa: str) -> dict:
    from app.core.thay_giong import _theo_nhan as f
    return f(data, chi_so, khoa)


def _chia_co(n: int, co: int = CO_MOI_LUOT):
    for i in range(0, n, co):
        yield list(range(i, min(i + co, n)))


def _chay_song_song(viec: list, khi_loi):
    """Chạy các lá phiếu của hội đồng SONG SONG (mỗi model một luồng).

    Model này KHÔNG phụ thuộc model kia nên chạy tuần tự chỉ là ngồi đợi mạng
    3 lần. Lỗi của một model KHÔNG được kéo cả hội đồng xuống — trả `khi_loi`
    cho riêng lá phiếu đó, đúng luật "thiếu 1 ý kiến, hội đồng vẫn chạy".
    """
    if len(viec) <= 1:
        return [f() for f in viec]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(viec)) as ex:
        fs = [ex.submit(f) for f in viec]
        ra = []
        for f in fs:
            try:
                ra.append(f.result())
            except Exception:                    # noqa: BLE001
                ra.append(khi_loi() if callable(khi_loi) else khi_loi)
        return ra


def _cham_mot_model(goc: list[str], dich: list[str], goc_ma: str, dich_ma: str,
                    model: str) -> dict[int, dict]:
    """MỘT model chấm 4 tiêu chí cho mọi câu. Trả {i: {tiêu chí: điểm}}.

    Lỗi/không đòi được -> câu đó KHÔNG có mặt trong kết quả (caller tự biết là
    thiếu ý kiến, đừng bịa điểm 10 như thước cũ — bịa 10 là tự phát chứng chỉ).
    """
    from app.ai import llm

    ra: dict[int, dict] = {}
    for nhom in _chia_co(len(goc)):
        items = []
        for i in nhom:
            items.append(f'#{i}\n  GỐC ({_ten_nn(goc_ma)}): "{goc[i][:300]}"\n'
                         f'  BẢN DỊCH ({_ten_nn(dich_ma)}): "{dich[i][:300]}"')
        system = ("Bạn là biên tập viên LỒNG TIẾNG khó tính, soát bản dịch "
                  "trước khi thu âm. CHỈ trả JSON thuần.")
        prompt = (
            "Chấm từng bản dịch dưới đây theo 4 TIÊU CHÍ TÁCH BẠCH.\n"
            f"{chr(10).join(items)}\n\n"
            "MỖI TIÊU CHÍ THANG 0-10, **CÀNG CAO CÀNG TỐT**:\n"
            '- "nghia" = ĐÚNG NGHĨA câu gốc. 10 = đúng trọn ý. '
            "**Dịch sai dù chỉ MỘT từ khoá (tên riêng, con số, sự vật chính) "
            "thì chấm <= 3** — sai một từ là người xem hiểu sai cả câu.\n"
            '- "xuoi" = ĐỌC LÊN CÓ XUÔI TAI người Việt không. 10 = như người '
            "Việt viết. **Đúng nghĩa nhưng lủng củng, dịch sát từng chữ, "
            "dùng từ không ai nói thì chấm <= 4** dù nghĩa đúng.\n"
            '- "noi" = ĐÚNG VĂN NÓI. 10 = như người thật đang nói trong video. '
            "Văn viết/sách vở/trang trọng quá mức thì chấm thấp.\n"
            '- "tron" = TRỌN CÂU, không CỤT không GỘP. 10 = đủ ý câu gốc, '
            "không thiếu vế, không nuốt ý, và KHÔNG gộp hai câu làm một.\n"
            "ĐỪNG rộng lượng: đây là bản sắp đưa vào video cho hàng nghìn "
            "người xem. Câu tầm thường chấm 5-6, chỉ câu THẬT SỰ tốt mới 9-10.\n"
            f"Trả MẢNG JSON {len(nhom)} đối tượng "
            '{"i": <đúng số sau dấu #>, "nghia": <0-10>, "xuoi": <0-10>, '
            '"noi": <0-10>, "tron": <0-10>}. BẮT BUỘC đủ MỌI số #.'
        )
        try:
            data = llm.complete_json(prompt, system=system, model=model)
        except Exception:                        # noqa: BLE001
            continue                             # thiếu 1 ý kiến, hội đồng vẫn chạy
        for khoa in TIEU_CHI:
            for i, v in _theo_nhan(data, nhom, khoa).items():
                try:
                    ra.setdefault(i, {})[khoa] = max(0.0, min(10.0, float(v)))
                except (TypeError, ValueError):
                    pass
    return ra


def cham_hoi_dong(goc: list[str], dich: list[str], goc_ma: str = "zh",
                  dich_ma: str = "vi",
                  models: Iterable[str] = MODEL_HOI_DONG) -> list[dict]:
    """HỘI ĐỒNG chấm: mỗi model một lá phiếu, lấy TRUNG VỊ từng tiêu chí.

    Trả list cùng độ dài `goc`, mỗi phần tử:
      {nghia, xuoi, noi, tron, diem, so_phieu}
    `diem` = **THẤP NHẤT** trong 4 trung vị (bản dịch chỉ tốt bằng trục tệ nhất).
    Không model nào chấm được -> `so_phieu` = 0 và `diem` = None (KHÔNG bịa 10:
    không có căn cứ thì phải nói là không có căn cứ).
    """
    phieu = _chay_song_song(
        [(lambda m=m: _cham_mot_model(goc, dich, goc_ma, dich_ma, m))
         for m in models], {})
    ra: list[dict] = []
    for i in range(len(goc)):
        gom: dict[str, list[float]] = {k: [] for k in TIEU_CHI}
        n = 0
        for p in phieu:
            if i in p and p[i]:
                n += 1
                for k in TIEU_CHI:
                    if k in p[i]:
                        gom[k].append(p[i][k])
        d: dict = {"so_phieu": n}
        tv = []
        for k in TIEU_CHI:
            d[k] = round(statistics.median(gom[k]), 2) if gom[k] else None
            if d[k] is not None:
                tv.append(d[k])
        d["diem"] = round(min(tv), 2) if tv else None
        d["diem_tb"] = round(sum(tv) / len(tv), 2) if tv else None
        ra.append(d)
    return ra


# --------------------------------------------------------------------------
# SOÁT THUẬT NGỮ — cửa RIÊNG bắt `新片 -> "phim về chip"`
# --------------------------------------------------------------------------
def _soat_mot_model(goc: list[str], dich: list[str], goc_ma: str, dich_ma: str,
                    model: str) -> list[list[str]]:
    """MỘT model liệt kê từ bị dịch sai. Trả list cùng độ dài `goc`, mỗi phần
    tử là danh sách KHOÁ LỖI đã chuẩn hoá (`_khoa_loi`) của riêng model đó.

    Tách hàm ra để phép đo lấy được PHIẾU THÔ từng model — có phiếu thô thì
    thử luật gộp khác (2/2 · 2/3 · 3/3) là việc TÍNH TOÁN, không phải gọi
    lại LLM; và mọi luật được so trên CÙNG một bộ phiếu nên hiệu số không
    lẫn nhiễu của LLM.
    """
    from app.ai import llm

    ra: list[list[str]] = [[] for _ in goc]
    for nhom in _chia_co(len(goc)):
        items = []
        for i in nhom:
            items.append(f'#{i}\n  GỐC ({_ten_nn(goc_ma)}): "{goc[i][:300]}"\n'
                         f'  BẢN DỊCH ({_ten_nn(dich_ma)}): "{dich[i][:300]}"')
        system = ("Bạn là người soát THUẬT NGỮ trong bản dịch. "
                  "CHỈ trả JSON thuần.")
        prompt = (
            "Với mỗi cặp, tìm những TỪ/CỤM TỪ trong câu GỐC bị dịch SAI "
            "NGHĨA trong bản dịch.\n"
            f"{chr(10).join(items)}\n\n"
            "CHỈ kể lỗi SAI NGHĨA THẬT SỰ:\n"
            "- Dịch ra một sự vật KHÁC HẲN (ví dụ chữ nghĩa là 'phim mới' "
            "mà dịch thành 'con chip').\n"
            "- Hiểu nhầm mặt chữ, đoán bừa theo âm, bịa thêm thứ không có "
            "trong câu gốc.\n"
            "- Tên riêng / con số bị đổi.\n"
            "KHÔNG kể: cách diễn đạt khác nhưng cùng nghĩa · từ đồng nghĩa "
            "· thêm/bớt từ đệm · thay đổi trật tự · rút gọn cho gọn câu. "
            "Những cái đó là dịch BÌNH THƯỜNG, không phải lỗi.\n"
            "Không thấy lỗi nào thì trả mảng rỗng — ĐỪNG cố tìm cho có.\n"
            f"Trả MẢNG JSON {len(nhom)} đối tượng "
            '{"i": <đúng số sau dấu #>, '
            '"sai": ["<từ gốc> -> <bản dịch sai> (đúng: <nghĩa đúng>)", ...]}.'
        )
        try:
            data = llm.complete_json(prompt, system=system, model=model)
        except Exception:                        # noqa: BLE001
            continue
        for i, v in _theo_nhan(data, nhom, "sai").items():
            if not isinstance(v, list):
                continue
            for x in v:
                khoa = _khoa_loi(str(x))
                if khoa and khoa not in ra[i]:
                    ra[i].append(khoa)
    return ra


def gop_thuat_ngu(phieu: list[list[list[str]]], can: int = 2) -> list[list[str]]:
    """Gộp phiếu thô của nhiều model: khoá lỗi nào được >= `can` model cùng
    kêu thì mới tính. HÀM THUẦN (không gọi LLM) — dùng chung cho đường chạy
    thật và cho phép đo quét luật.
    """
    n = len(phieu[0]) if phieu else 0
    can = max(1, min(can, len(phieu)))
    ra: list[list[str]] = []
    for i in range(n):
        dem: dict[str, int] = {}
        for p in phieu:
            for k in p[i]:
                dem[k] = dem.get(k, 0) + 1
        ra.append(sorted(k for k, v in dem.items() if v >= can))
    return ra


def soat_thuat_ngu(goc: list[str], dich: list[str], goc_ma: str = "zh",
                   dich_ma: str = "vi",
                   models: Iterable[str] = MODEL_HOI_DONG[:2],
                   can: int = 0) -> list[list[str]]:
    """Hỏi ĐÚNG MỘT VIỆC: từ/cụm nào trong câu gốc bị dịch SAI?

    Tách khỏi lượt chấm điểm là CỐ Ý: hỏi "chấm điểm" thì model nhìn tổng thể
    và một từ sai chìm trong câu đúng; hỏi "liệt kê từ sai" thì nó phải soi
    từng từ. Trả list cùng độ dài `goc`, mỗi phần tử là danh sách mô tả lỗi
    (rỗng = không thấy lỗi).

    Lấy **GIAO** của các model (từ nào >= `can` model cùng kêu mới tính) — một
    mình lượt này rất hay bịa lỗi trên câu dịch đúng (đo được: 1 model kêu oan
    nhiều gấp mấy lần 2 model cùng kêu). `can=0` = mặc định `TN_CAN`.
    """
    ds = list(models)
    if not ds:
        return [[] for _ in goc]
    phieu = _chay_song_song(
        [(lambda m=m: _soat_mot_model(goc, dich, goc_ma, dich_ma, m))
         for m in ds], lambda: [[] for _ in goc])
    return gop_thuat_ngu(phieu, can or TN_CAN)


def _khoa_loi(s: str) -> str:
    """Chuẩn hoá mô tả lỗi để 2 model diễn đạt khác nhau vẫn gộp được.

    Lấy phần TRƯỚC dấu `->` (chính là từ GỐC bị dịch sai) — đó là thứ hai model
    chắc chắn viết giống nhau, còn lời giải thích thì mỗi model một kiểu.
    """
    s = (s or "").strip()
    if not s:
        return ""
    dau = re.split(r"->|→|:", s, maxsplit=1)[0]
    return re.sub(r"\s+", "", dau).strip('"\'' + " ")[:40] or s[:40]


# --------------------------------------------------------------------------
# CỬA CHỐT
# --------------------------------------------------------------------------
def dat_cau(c: dict, nguong_truc: dict | None = None,
            tn_nguong_nghia: float | None = TN_NGUONG_NGHIA) -> bool:
    """Một câu đã chấm có ĐẠT không. HÀM THUẦN — cổng và phép đo gọi thẳng.

    `c` cần có: `loi` (luật máy) · `thuat_ngu` · 4 trục. Trục nào KHÔNG chấm
    được thì BỎ QUA (không có căn cứ thì không kết tội); không một trục nào
    chấm được thì TRƯỢT (cũng không có căn cứ để tha).
    """
    ng = nguong_truc or NGUONG_TRUC
    if c.get("loi"):
        return False                     # LUẬT MÁY LÀ SÀN, tiền định, 0 kêu oan
    if c.get("thuat_ngu"):
        if tn_nguong_nghia is None:
            return False
        n = c.get("nghia")
        if n is None or n < tn_nguong_nghia:
            return False
    co = 0
    for k, v in ng.items():
        x = c.get(k)
        if x is None:
            continue
        co += 1
        if x < v:
            return False
    return co > 0


def cham_ban_dich(goc: list[str], dich: list[str], goc_ma: str = "zh",
                  dich_ma: str = "vi", nguong_truc: dict | None = None,
                  models: Iterable[str] = MODEL_HOI_DONG,
                  soat_tn: bool = True,
                  tn_nguong_nghia: float | None = TN_NGUONG_NGHIA) -> dict:
    """Chấm cả loạt: luật máy + hội đồng + soát thuật ngữ. CHỈ ĐỌC, không sửa.

    Trả {cau: [...], dat, tong, ty_le_dat, diem_tb, ...} — `cau[i]` gồm
    `diem` (MIN 4 trục, giữ để ĐỌC/so mốc) · 4 tiêu chí · `loi` (mã lỗi máy)
    · `thuat_ngu` (list) · `dat` (theo NGƯỠNG RIÊNG TỪNG TRỤC).
    """
    n = len(goc)
    if not n:
        hd, tn = [], []
    else:
        # CẢ 3 model ở cửa thuật ngữ (v1 chỉ hỏi 2): cửa này nay đòi TOÀN BỘ
        # đồng ý nên phải có đủ 3 phiếu — hỏi 2 mà đòi 3 là tắt cửa mà không
        # nói ra. Hai lượt (chấm điểm · soát thuật ngữ) độc lập nhau nên chạy
        # SONG SONG luôn.
        viec = [lambda: cham_hoi_dong(goc, dich, goc_ma, dich_ma, models)]
        if soat_tn:
            viec.append(lambda: soat_thuat_ngu(goc, dich, goc_ma, dich_ma,
                                               list(models), TN_CAN))
        kq = _chay_song_song(viec, lambda: [])
        hd = kq[0]
        tn = kq[1] if soat_tn and len(kq) > 1 else [[] for _ in range(n)]
        if len(tn) != n:
            tn = [[] for _ in range(n)]

    cau = []
    for i in range(n):
        lm = loi_may(goc[i], dich[i], dich_ma)
        d = dict(hd[i]) if i < len(hd) else {"diem": None, "so_phieu": 0}
        d["loi"] = lm
        d["thuat_ngu"] = tn[i] if i < len(tn) else []
        d["dat"] = dat_cau(d, nguong_truc, tn_nguong_nghia)
        cau.append(d)

    co_diem = [c["diem"] for c in cau if c.get("diem") is not None]
    dat = sum(1 for c in cau if c["dat"])
    return {
        "cau": cau,
        "tong": n,
        "dat": dat,
        "ty_le_dat": round(100.0 * dat / max(1, n), 1),
        "diem_tb": round(sum(co_diem) / len(co_diem), 2) if co_diem else None,
        "diem_min": round(min(co_diem), 2) if co_diem else None,
        "so_loi_may": sum(1 for c in cau if c["loi"]),
        "so_thuat_ngu": sum(1 for c in cau if c["thuat_ngu"]),
        "khong_cham_duoc": sum(1 for c in cau if c.get("diem") is None),
    }
