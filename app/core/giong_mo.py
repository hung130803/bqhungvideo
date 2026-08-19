# -*- coding: utf-8 -*-
"""MỞ KHOÁ GIỌNG edge-tts — luật mở là **ĐÃ ĐO THÌ MỞ**, không phải danh sách tay.

**VÌ SAO CÓ FILE NÀY.** ``dubbing.GIONG_MO_HET = ("en-",)`` mở danh sách gọn
cho đúng một tiền tố ngôn ngữ, và ghi chú ngay tại đó nói rõ lý do không mở
thêm: *"KHÔNG mở các tiếng khác — không phải vì chúng kém mà vì CHƯA ĐO"*.
Nay 109 giọng của 14 thứ tiếng còn lại **đã đo xong** bằng đúng thước cổng 76,
nên điều kiện đó không còn.

**LUẬT MỞ (một câu):** giọng có mặt trong ``nhan_nha.BANG`` thì mở, không có
thì không. Không có bảng tay thứ hai để ai đó quên cập nhật.

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

**137 GIỌNG CÒN LẠI (60 thứ tiếng) CỐ Ý KHÔNG ĐO, KHÔNG MỞ** — không phải quên:
``_do_nhan_nha_bang.CAU`` chỉ có bộ câu cho 15 thứ tiếng, và ``cau_cho()`` lùi
về **câu tiếng Anh** cho mọi thứ tiếng khác. Bắt giọng Thổ / Ba Lan / Hà Lan
đọc câu tiếng Anh rồi ghi số vào bảng là đo một thứ khác hẳn — chính bẫy đã
làm ``piper:vais1000`` ra 1,88 (thấp nhất toàn bảng) ở lượt trước. Muốn mở
thêm tiếng nào thì **viết bộ 4 câu đúng tiếng đó trước**, rồi chạy
``_do_nhan_nha_het.py``; file này tự nhận.
"""
from __future__ import annotations

from app.core import nhan_nha

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


def nen_mo(ma: str) -> bool:
    """Giọng edge-tts này có được hiện trong DANH SÁCH GỌN không.

    Thay cho ``dubbing._la_giong_mo_them``. Nhận **mã giọng** (chuỗi) chứ
    không nhận dict — nơi gọi có dict thì truyền ``v["ShortName"]``; ép nơi
    gọi bóc khoá ra là để hàm này dùng được cả ở chỗ chỉ có mã (bảng cấu hình
    kênh, payload job, cổng test).
    """
    return la_ma_edge(ma) and nhan_nha.muc(ma) is not None


def loc_mo(ds):
    """Lọc một danh sách dict giọng edge-tts (``[{"ShortName": ...}]``)."""
    return [v for v in (ds or []) if nen_mo(str(v.get("ShortName") or ""))]


def tieng_da_mo() -> list[str]:
    """Mã ngôn ngữ (``en`` · ``es`` · ...) đã có ít nhất một giọng được mở.

    Dùng cho nhãn/báo cáo: nói được *"đang mở 14 thứ tiếng"* mà không phải
    giữ một con số viết tay sẽ lạc hậu ngay lượt đo sau.
    """
    ra = {ma.split("-")[0] for ma in nhan_nha.BANG if la_ma_edge(ma)}
    return sorted(ra)


def dem_theo_tieng() -> dict[str, int]:
    """{mã ngôn ngữ: số giọng edge-tts đã mở}. Chỉ để báo cáo/nhãn."""
    ra: dict[str, int] = {}
    for ma in nhan_nha.BANG:
        if la_ma_edge(ma):
            ra[ma.split("-")[0]] = ra.get(ma.split("-")[0], 0) + 1
    return ra


def so_giong_mo() -> int:
    """Tổng số giọng edge-tts đang được mở."""
    return sum(1 for ma in nhan_nha.BANG if la_ma_edge(ma))
