# -*- coding: utf-8 -*-
"""MỞ KHOÁ GIỌNG edge-tts — luật mở là **ĐÃ ĐO THÌ MỞ**, không phải danh sách tay.

**VÌ SAO CÓ FILE NÀY.** ``dubbing.GIONG_MO_HET = ("en-",)`` mở danh sách gọn
cho đúng một tiền tố ngôn ngữ, và ghi chú ngay tại đó nói rõ lý do không mở
thêm: *"KHÔNG mở các tiếng khác — không phải vì chúng kém mà vì CHƯA ĐO"*.
Nay 109 giọng của 14 thứ tiếng còn lại **đã đo xong** bằng đúng thước cổng 76,
nên điều kiện đó không còn.

**LUẬT MỞ (một câu):** giọng **ĐÃ CHỨNG MINH ĐỌC ĐƯỢC** thì mở, không thì
không. Không có bảng tay thứ hai để ai đó quên cập nhật.

**LUẬT ĐÓ VỪA ĐƯỢC TÁCH LÀM ĐÔI (19/08/2026) — ĐỌC KỸ, ĐÂY LÀ THAY ĐỔI LỚN
NHẤT CỦA FILE NÀY.** Bản đầu viết luật là *"có trong ``nhan_nha.BANG`` thì
mở"*, và ba lý do bên dưới vẫn đúng nguyên — nhưng nó gộp **hai câu hỏi khác
hẳn nhau** vào một tấm vé:

* **ĐỌC ĐƯỢC KHÔNG?** — rẻ, BẮT BUỘC. Một câu đúng tiếng qua đúng cửa là xong.
* **NHẤN NHÁ BAO NHIÊU?** — đắt, TUỲ CHỌN. Cần bộ 4 câu ĐÚNG TIẾNG.

Gộp lại thì tấm vé bị cấp bởi câu hỏi ĐẮT, và hậu quả đo được là **137 giọng
của 60 thứ tiếng bị khoá vì một lý do chẳng liên quan gì tới chúng**:
``_do_nhan_nha_bang.CAU`` chỉ có bộ câu cho 15 thứ tiếng. Không ai nghi ngờ
giọng Ba Lan; chỉ là chưa ai viết được bốn câu tiếng Ba Lan để chấm nó.

Nay: mở = ``giong_doc.da_doc(ma)`` **hoặc** ``nhan_nha.muc(ma) is not None``.
Vế thứ hai KHÔNG phải nhân nhượng — 185 giọng đang mở đều đã đọc thật **4 câu**
qua ``dubbing._synth_all`` trong lượt đo nhấn nhá, tức chúng có bằng chứng đọc
được **mạnh hơn** bằng chứng 1 câu của bảng mới. Giữ vế đó lại là để **không
giọng nào đang chạy bị rơi khỏi combo** vì một lượt dọn dẹp.

**BA TRẠNG THÁI, NHÃN PHẢI PHÂN BIỆT ĐƯỢC** (``nhan_nha.nhan`` lo phần chữ):

    có điểm nhấn nhá   ->  " - nhấn nhá 4,1 rất truyền cảm"
    ĐỌC ĐƯỢC, chưa đo  ->  " - chưa đo nhấn nhá"       <- MỚI
    không đọc được     ->  KHÔNG hiện dòng nào (``nen_mo`` trả False)

Trạng thái giữa là chỗ đắt giá nhất: nó cho phép mở một giọng **mà không phải
bịa một con số cạnh tên nó**. Bịa số là người dùng sẽ tin mà chọn.

Ba lý do chọn luật này thay vì viết thêm một tuple tiền tố:

1. **Tự đồng bộ.** Đo thêm giọng -> nó tự vào danh sách. Bỏ một giọng khỏi
   bảng -> nó tự biến mất. Bảng tay ``_HOT_VOICES`` đã chứng minh chuyện
   ngược lại: 32 giọng ``en-`` bị khoá suốt nhiều tháng **không vì lý do nào
   ngoài việc chưa ai thêm tay vào bảng**.
2. **Không bao giờ hiện một dòng trống số.** Combo hiện đuôi *"- nhấn nhá 4,1
   rất truyền cảm"* lấy từ chính bảng đó (``nhan_nha.nhan`` trả chuỗi RỖNG khi
   chưa đo). Mở theo tiền tố thì mở luôn cả giọng chưa đo -> anh Hùng thấy một
   danh sách nửa có số nửa không, và **phần không có số lại chính là phần rủi
   ro nhất**.
3. **Mở tới đâu là chịu trách nhiệm tới đó.** Mọi giọng lọt qua cửa này đều đã
   đọc thật 4 câu **đúng tiếng của nó** qua **đúng cửa lượt xuất đi**
   (``dubbing._synth_all``) — tức nó đã chứng minh là đọc được, không phải chỉ
   có tên trong danh mục của Microsoft.

**CÁI FILE NÀY CỐ Ý KHÔNG LÀM:**

* **KHÔNG sửa ``dubbing.py``** (luồng khác đang giữ file đó). Nó chỉ cung cấp
  hàm; luồng lắp giao diện gọi ``nen_mo`` thay cho ``_la_giong_mo_them``.
* **KHÔNG mọc thêm ⭐.** Dấu sao đọc từ ``_HOT_VOICES``; nhồi 109 tên vào đó là
  mọi giọng đều hot và dấu sao mất nghĩa (đúng lý lẽ đã ghi ở ``GIONG_MO_HET``).
* **KHÔNG đụng thứ tự.** Sắp xếp vẫn là ``nhan_nha.khoa_sap``.

**SỐ ĐO CỦA LƯỢT MỞ NÀY** (xem ``_kq_nn_het.txt`` + ``_do_nhan_nha_het.py``):
edge-tts có **322 giọng / 75 thứ tiếng**. Trước lượt này bảng có **82 giọng**
(47 ``en-`` + 30 giọng ⭐ của 14 tiếng + 5 OmniVoice + 1 Piper). Lượt này đo
thêm **109 giọng** của 14 thứ tiếng ĐÃ CÓ BỘ CÂU RIÊNG.

**137 GIỌNG CÒN LẠI: NAY ĐÃ KIỂM ĐỌC THẬT, MỞ HẾT 137/137**
(``_do_doc_that.py``, 19/08/2026). Cộng 185 giọng cũ -> **322/322 giọng, 75/75
thứ tiếng của edge-tts đều có biên bản đọc thật**. Không đo nhấn nhá cho 137
giọng mới — ``cau_cho()`` lùi về **câu tiếng Anh** cho tiếng không có bảng, mà
bắt giọng Thổ / Ba Lan / Hà Lan đọc câu tiếng Anh rồi ghi số vào bảng là đo một
thứ khác hẳn (bẫy đã làm ``piper:vais1000`` ra 1,88). Nên nhấn nhá của chúng
**để TRỐNG**, nhãn ghi *"chưa đo"*. Muốn có số thì **viết bộ 4 câu đúng tiếng
đó trước**, chạy ``_do_nhan_nha_het.py``; file này tự nhận, không sửa gì ở đây.

**LƯỢT ĐẦU CÓ 4 GIỌNG HỎNG, VÀ CHÚNG ĐÃ ĐƯỢC CHỮA CHỨ KHÔNG BỎ QUA** — bốn
giọng Inuktitut chết vì mẫu regex của **thư viện khách ``edge_tts``** không bóc
nổi locale 4 đoạn, chết **trước khi chạm mạng**. ``chuan_ten_edge`` ngay dưới
đây là bản vá; ``dubbing._ten_edge`` là chỗ nối. Xem ``giong_doc`` mục cuối cho
đủ đường truy nguyên nhân (gồm cả phép TÁCH "câu thử sai" khỏi "giọng chết").
"""
from __future__ import annotations

import re

from app.core import giong_doc, nhan_nha

#: Tiền tố mã giọng KHÔNG phải edge-tts. Chúng có đường vào combo riêng
#: (`giong_ngoai.danh_sach_giong`, `piper_tts`, `giong_vieneu`...) nên cửa này
#: phải trả False, nếu không một mã `ov:` lọt vào nhánh lọc giọng edge-tts.
#: Quy ước "mã edge-tts KHÔNG BAO GIỜ chứa dấu hai chấm" đã chốt ở
#: `giong_bang._TIEN_TO` — dùng lại, đừng đặt quy ước thứ hai.
_KHONG_EDGE = ":"


def la_ma_edge(ma: str) -> bool:
    """Mã này có phải giọng edge-tts không (`vi-VN-HoaiMyNeural`)."""
    s = str(ma or "")
    return bool(s) and _KHONG_EDGE not in s


def da_kiem_doc(ma: str) -> bool:
    """Giọng này ĐÃ CHỨNG MINH đọc ra tiếng thật qua ``dubbing._synth_all``.

    Hai nguồn bằng chứng, **đều là phép đo, không phải danh sách tay**:

    * ``giong_doc.BANG`` — lượt kiểm ĐỌC THẬT: 1 câu đúng tiếng, lưu kèm
      ``(độ dài, RMS)`` nên cổng đọc lại được;
    * ``nhan_nha.BANG`` — lượt đo NHẤN NHÁ: 4 câu đúng tiếng. Bằng chứng này
      **mạnh hơn**, nên nó tính luôn là đã kiểm đọc; không cần đo lại 185 giọng
      đang chạy chỉ để chép tên sang bảng mới.

    Tách khỏi ``nen_mo`` để cổng chấm được riêng "có bằng chứng đọc không" với
    "có phải mã edge-tts không" — gộp một hàm thì không biết nó trả False vì lý
    do nào.
    """
    s = str(ma or "")
    return giong_doc.da_doc(s) or nhan_nha.muc(s) is not None


def nen_mo(ma: str) -> bool:
    """Giọng edge-tts này có được hiện trong DANH SÁCH GỌN không.

    Thay cho ``dubbing._la_giong_mo_them``. Nhận **mã giọng** (chuỗi) chứ
    không nhận dict — nơi gọi có dict thì truyền ``v["ShortName"]``; ép nơi
    gọi bóc khoá ra là để hàm này dùng được cả ở chỗ chỉ có mã (bảng cấu hình
    kênh, payload job, cổng test).

    **KHÔNG BAO GIỜ mở theo TIỀN TỐ NGÔN NGỮ.** Đó là cách
    ``dubbing.GIONG_MO_HET = ("en-",)`` đang làm, và nó mở luôn cả giọng chưa
    ai thử đọc bao giờ. Giọng lọt qua cửa này đều có **biên bản** kèm số đo.
    """
    return la_ma_edge(ma) and da_kiem_doc(ma)


def loc_mo(ds):
    """Lọc một danh sách dict giọng edge-tts (``[{"ShortName": ...}]``)."""
    return [v for v in (ds or []) if nen_mo(str(v.get("ShortName") or ""))]


def moi_giong_mo() -> list[str]:
    """MỌI mã edge-tts đang được mở — hợp của hai bảng bằng chứng.

    **CỬA DUY NHẤT để đếm.** Ba hàm báo cáo bên dưới đều đi qua đây, nên không
    thể xảy ra chuyện ``so_giong_mo()`` nói một số mà ``dem_theo_tieng()`` cộng
    lại ra số khác — lỗi đó im lặng và chỉ lộ ra khi có người cộng tay.
    """
    ra = {ma for ma in nhan_nha.BANG if la_ma_edge(ma)}
    ra |= {ma for ma in giong_doc.BANG if la_ma_edge(ma)}
    return sorted(ra)


def tieng_da_mo() -> list[str]:
    """Mã ngôn ngữ (``en`` · ``es`` · ...) đã có ít nhất một giọng được mở.

    Dùng cho nhãn/báo cáo: nói được *"đang mở 74 thứ tiếng"* mà không phải
    giữ một con số viết tay sẽ lạc hậu ngay lượt đo sau.
    """
    return sorted({ma.split("-")[0] for ma in moi_giong_mo()})


def dem_theo_tieng() -> dict[str, int]:
    """{mã ngôn ngữ: số giọng edge-tts đã mở}. Chỉ để báo cáo/nhãn."""
    ra: dict[str, int] = {}
    for ma in moi_giong_mo():
        g = ma.split("-")[0]
        ra[g] = ra.get(g, 0) + 1
    return ra


def so_giong_mo() -> int:
    """Tổng số giọng edge-tts đang được mở."""
    return len(moi_giong_mo())


# ---------------------------------------------------------------------------
# TÊN GIỌNG CHO `edge_tts` — locale 4 ĐOẠN
# ---------------------------------------------------------------------------
#: Mẫu mà `edge_tts.data_classes.TTSConfig.__post_init__` dùng để bóc tên giọng.
#: Chép lại ở đây để `chuan_ten_edge` chỉ đụng vào ca thư viện KHÔNG bóc được —
#: ca bóc được thì trả nguyên văn, tức hành vi của 318/322 giọng **không đổi một
#: ký tự nào**. Đó là điều kiện để bản vá này không phải một canh bạc.
_EDGE_BOC_DUOC = re.compile(r"^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$")

#: Dạng tên đầy đủ mà máy chủ Microsoft nhận. `edge_tts` tự dựng chuỗi này khi
#: bóc được; ta dựng hộ khi nó bó tay.
_EDGE_TEN_DAY = ("Microsoft Server Speech Text to Speech Voice "
                 "({loc}, {ten})")


def chuan_ten_edge(ma: str) -> str:
    """Đổi mã giọng sang dạng ``edge_tts`` chắc chắn nhận. Không cần -> nguyên.

    **VÌ SAO CÓ HÀM NÀY — LỖI THẬT, ĐÃ ĐO** (xem ``giong_doc`` mục cuối).
    ``edge_tts`` bóc tên bằng ``^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$``, tức nó
    ngầm giả định locale có **đúng 3 đoạn** và đoạn vùng có **>= 2 chữ HOA**.
    Bốn giọng Inuktitut có locale **4 đoạn** (``iu-Cans-CA``, ``iu-Latn-CA``)
    nên trượt mẫu -> thư viện ném ``ValueError: Invalid voice`` **trước khi
    chạm mạng**. ``_synth_all`` nuốt ngoại lệ rồi thử lại 4 lần, nên triệu
    chứng ở ngoài chỉ là *"giọng này không đọc được"* — không một dòng nào chỉ
    ra thủ phạm là thư viện khách.

    Đo thật: gọi bằng tên đầy đủ thì **ra tiếng thật** (4,22 s / -20,3 dBFS và
    4,01 s / -20,4 dBFS).

    **CHỈ ĐỤNG CA THƯ VIỆN BÓ TAY.** Mã bóc được -> trả **nguyên văn**, nên
    318/322 giọng đi đúng đường cũ. Mã không phải edge-tts (có ``:``) hoặc
    không có đuôi ``Neural`` -> cũng trả nguyên văn: đoán mò một dạng tên khác
    còn tệ hơn để thư viện tự báo lỗi.
    """
    s = str(ma or "")
    if not la_ma_edge(s) or not s.endswith("Neural"):
        return s
    if _EDGE_BOC_DUOC.match(s):
        return s                        # thư viện tự lo được -> ĐỪNG ĐỤNG
    phan = s.rsplit("-", 1)
    if len(phan) != 2 or not phan[0]:
        return s
    return _EDGE_TEN_DAY.format(loc=phan[0], ten=phan[1])
