"""MỨC NHẤN NHÁ CỦA TỪNG GIỌNG — để anh Hùng CHỌN ĐÚNG giọng.

Anh Hùng 18/08/2026: *"giọng chả có hồn gì, không có cảm xúc, rất là trơ"* —
anh ấy đang dùng `ov:nam_tre`. Vấn đề là **anh ấy không có cách nào biết giọng
nào sinh động hơn**: combo chỉ hiện tên. Đó là lỗi TRÌNH BÀY, và module này
chữa đúng chỗ đó — hiện SỐ ĐO cạnh mỗi giọng + gợi ý giọng nhấn nhá cao nhất.

**KHÔNG HỨA LÀM GIỌNG OmniVoice SINH ĐỘNG HƠN** — không đổi được, đó là bản
chất model. Chỉ giúp chọn đúng giọng.

═══════════════════════════════════════════════════════════════════════════
THƯỚC: độ lệch chuẩn CAO ĐỘ (F0) tính bằng NỬA CUNG
═══════════════════════════════════════════════════════════════════════════
F0 theo khung 40 ms bằng tự tương quan (chỉ khung CÓ TIẾNG, dải 70-400 Hz),
đổi sang nửa cung rồi lấy độ lệch chuẩn. Càng lớn = lên xuống càng nhiều =
nghe càng có cảm xúc. Giọng đọc đều một giọng ra số thấp.
Đo bằng `_do_nhan_nha.py`, đi qua CỬA CHUNG `thay_giong.doc_ban_dich` (đúng
bước 4 của lượt xuất thật).

═══════════════════════════════════════════════════════════════════════════
HAI CÁI BẪY ĐÃ SẬP KHI LÀM VIỆC NÀY — ĐỌC TRƯỚC KHI THÊM SỐ VÀO BẢNG
═══════════════════════════════════════════════════════════════════════════
**BẪY 1 — `2,16` KHÔNG PHẢI NHẤN NHÁ CỦA `ov:nam_tre`.** Con số đó đang bị
nhắc tới như "nhấn nhá OmniVoice", nhưng `docs/GIONG_LUOT_7.md` ghi nguyên
văn: *"nhấn nhá 11 giọng thiết kế: 1,48..3,64 = **TRẢI** 2,16"* — tức nó là
**KHOẢNG TRẢI (3,64 − 1,48) CỦA 11 GIỌNG**, không phải giá trị của một giọng
nào. Đem nó so với giá trị TỪNG GIỌNG (Aria 5,89) là so hai đơn vị khác nhau
rồi kết luận "giọng anh ấy nằm dưới đáy thang" — kết luận đó **CHƯA CÓ CĂN
CỨ** cho tới khi đo giá trị của chính `ov:nam_tre`.

**BẪY 2 — SỐ ĐO TRÊN CORPUS KHÁC NGÔN NGỮ KHÔNG SO ĐƯỢC VỚI NHAU.** Bảng cũ
ghi Aria **5,89** · Jenny **5,54** (đo trên câu TIẾNG ANH) rồi đặt cạnh
NamMinh 3,96 (câu TIẾNG VIỆT). Đo lại CẢ BỐN trên CÙNG corpus tiếng Việt:
Aria ra **2,72**, Jenny **2,62** — tức thấp hơn cả hai giọng Việt, ngược hẳn
bảng cũ. Lý do đơn giản: giọng Anh đọc chữ Việt thì ngữ điệu vỡ.
=> **CHỈ ĐƯỢC so các giọng đọc CÙNG MỘT ngôn ngữ, đo trên CÙNG một corpus.**
Vì vậy bảng dưới đây CHỈ chứa số đo trên corpus TIẾNG VIỆT, và
`goi_y_giong()` chỉ gợi ý trong nhóm giọng của đúng ngôn ngữ đang chọn.

**GIỌNG CHƯA ĐO THÌ KHÔNG HIỆN SỐ** — bịa một con số cạnh tên giọng còn tệ
hơn không hiện gì, vì user sẽ tin nó mà chọn.
"""
from __future__ import annotations

#: Corpus dùng để đo bảng này — ghi ra để lần sau đo lại đúng chỗ.
CORPUS = ("6 câu tiếng Việt (bản dịch thật của video anh Hùng đang làm), "
          "có câu hỏi và câu cảm thán")

#: Ngôn ngữ của corpus. Bảng CHỈ dùng được cho giọng đọc ngôn ngữ này.
CORPUS_NGON_NGU = "vi"

#: {mã giọng: mức nhấn nhá (nửa cung)} — SỐ ĐO, corpus tiếng Việt, cùng lượt.
#: Cột "trong câu" (nhấn nhá TRUNG BÌNH từng câu) đi kèm trong
#: `bq_do_nhan_nha/ket_qua.json`; ở đây lấy cột CẢ BỘ vì nó gồm cả phần lên
#: xuống GIỮA các câu — thứ tai nghe ra là "đọc có nhấn hay đọc đều đều".
BANG_VI: dict[str, float] = {
    "vi-VN-NamMinhNeural": 3.80,
    "vi-VN-HoaiMyNeural": 3.09,
}

#: Ngưỡng chia mức để nói bằng CHỮ, không chỉ bằng số. Lấy từ chính dải đo
#: được trên corpus này (2,3 .. 3,8): dưới 2,6 là nhóm đọc đều nhất, trên 3,4
#: là nhóm lên xuống nhiều nhất.
NGUONG_TRO = 2.60
NGUONG_SINH_DONG = 3.40


def muc(voice: str, ngon_ngu: str = "vi") -> float | None:
    """Mức nhấn nhá của `voice`, hoặc None nếu CHƯA ĐO.

    `ngon_ngu` khác corpus -> trả None: số của corpus tiếng Việt không nói
    được gì về giọng đọc tiếng khác (BẪY 2 ở đầu file).
    """
    if str(ngon_ngu or "").lower().split("-")[0] != CORPUS_NGON_NGU:
        return None
    return BANG_VI.get(str(voice or "").strip())


def xep_loai(m: float) -> str:
    """Mức nhấn nhá -> một chữ người đọc hiểu ngay."""
    if m >= NGUONG_SINH_DONG:
        return "nhiều cảm xúc"
    if m < NGUONG_TRO:
        return "đọc đều, hơi trơ"
    return "vừa"


def nhan_kem(voice: str, ngon_ngu: str = "vi") -> str:
    """Đuôi nhãn để GẮN VÀO combo chọn giọng. Rỗng = chưa đo, KHÔNG bịa."""
    m = muc(voice, ngon_ngu)
    if m is None:
        return ""
    return f"  ·  nhấn nhá {m:.2f} ({xep_loai(m)})".replace(".", ",")


def goi_y_giong(ngon_ngu: str = "vi") -> tuple[str, float] | None:
    """(mã giọng, mức) có nhấn nhá CAO NHẤT trong số giọng ĐÃ ĐO.

    None nếu ngôn ngữ đó chưa có bảng — thà không gợi ý gì còn hơn gợi ý một
    giọng chưa ai đo.
    """
    if str(ngon_ngu or "").lower().split("-")[0] != CORPUS_NGON_NGU:
        return None
    if not BANG_VI:
        return None
    ma = max(BANG_VI, key=lambda k: BANG_VI[k])
    return (ma, BANG_VI[ma])


def cau_goi_y(ngon_ngu: str = "vi", ten_giong=None) -> str:
    """Câu gợi ý hiện dưới combo. Rỗng nếu chưa đo được gì cho ngôn ngữ đó."""
    g = goi_y_giong(ngon_ngu)
    if not g:
        return ""
    ma, m = g
    ten = ten_giong(ma) if callable(ten_giong) else ma
    so = f"{m:.2f}".replace(".", ",")
    return (f"Giọng nhiều cảm xúc nhất đã đo cho tiếng Việt: {ten} "
            f"(nhấn nhá {so} nửa cung). Số càng lớn thì giọng lên xuống càng "
            f"nhiều; giọng đọc đều nghe ra là trơ.")
