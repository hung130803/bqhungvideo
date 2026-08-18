"""NHẤN NHÁ TỪNG GIỌNG — số ĐO ĐƯỢC, để hiện cạnh mỗi giọng trong combo.

**VÌ SAO CÓ FILE NÀY:** anh Hùng đang dùng một giọng nằm ở ĐÁY thang nhấn nhá
mà **không có cách nào biết** — combo chỉ ghi tên giọng. Trước lượt này app đã
liệt kê đủ 47 giọng tiếng Anh nhưng vẫn không nói giọng nào lên xuống nhiều,
giọng nào đọc đều đều như máy đọc văn bản.

**THƯỚC:** độ lệch chuẩn cao độ F0 tính bằng **NỬA CUNG** (khung 40 ms, tự
tương quan) — đúng thước ``_do_nhan_nha.f0_nua_cung`` của lượt 10, không viết
thước thứ hai. Càng cao = giọng lên xuống càng nhiều = nghe càng có cảm xúc;
càng thấp = càng đều đều.

**ĐO NHƯ THẾ NÀO:** ``_do_nhan_nha_bang.py`` cho mỗi giọng đọc **4 câu ĐÚNG
TIẾNG CỦA NÓ** (kể · hỏi · cảm thán · kể dài) qua **CỬA CHUNG**
``dubbing._synth_all``, tức đúng cửa lượt xuất thật đi.

**SỐ NÀY TIỀN ĐỊNH — ĐÃ KIỂM, không phải tin lời:** đo lại lượt 2 trên 6
giọng, 5 giọng đủ 4 câu lệch **0,00 · 0,00 · 0,00 · +0,01 · +0,09**. Giọng
DUY NHẤT lệch nhiều (``vi-VN-HoaiMy`` +0,12) chính là giọng lượt 1 **thiếu 1
câu** (383 khung so với 499) — tức đó là lỗ hổng dữ liệu, KHÔNG phải nhiễu của
máy đọc. Bảng dưới chỉ nhận giọng ĐỦ 4 CÂU. Vì còn lệch tới 0,09 nên UI hiện
**1 chữ số thập phân**; hiện 2 chữ số là chính xác giả.

**ĐỌC SỐ NÀY CHO ĐÚNG — 2 GIỚI HẠN, ĐỪNG BỎ QUA:**

1. **So trong CÙNG một tiếng thì chắc; so CHÉO tiếng chỉ là tham khảo.** Mỗi
   ngôn ngữ đọc một bộ câu khác nhau, mà bản thân ngôn ngữ cũng có nhịp điệu
   riêng. ``ar-SA-Hamed`` 5,86 đứng trên ``en-GB-Ryan`` 5,38 **không** có
   nghĩa giọng Ả Rập giàu cảm xúc hơn.
2. **Số này KHÔNG nói giọng HAY hay DỞ.** Nó đo ĐỘ LÊN XUỐNG của cao độ.
   Giọng lên xuống nhiều hợp kể chuyện/giật gân; đọc tin tức hay hướng dẫn thì
   giọng đều lại dễ nghe hơn. **Tôi không có tai — anh Hùng nghe rồi chốt**,
   số chỉ để khỏi phải dò mò 76 giọng.

**ĐÍNH CHÍNH QUAN TRỌNG NHẤT CỦA LƯỢT NÀY — ``ov:nam_tre`` KHÔNG Ở ĐÁY THANG.**
Việc này được giao với mệnh đề *"anh Hùng đang dùng ``ov:nam_tre``, nhấn nhá
**2,16**, đáy thang"*. **Đo ra 4,24** — nằm **TRÊN tứ phân vị 75% (4,16)**,
tức thuộc nhóm ĐỈNH của cả 82 giọng, và **cao hơn cả hai giọng Việt của
edge-tts** (NamMinh 4,04 · HoaiMy 3,18).

Con số 2,16 là **TRẢI (range) của 11 giọng OmniVoice** ở lượt 7
(``docs/GIONG_LUOT_7.md``: *"nhấn nhá 11 giọng thiết kế: 1,48..3,64 = TRẢI
2,16"*, tức 3,64 − 1,48), **không phải giá trị của riêng một giọng**. Đem một
con số TRẢI so với giá trị TỪNG GIỌNG là so hai đơn vị khác nhau —
``_do_nhan_nha.py`` đã cảnh báo đúng chỗ này từ lượt 10 mà nó vẫn được chép
tiếp. **Vậy nếu muốn khuyên anh Hùng bỏ OmniVoice thì phải lấy lý do KHÁC**
(trọng số CC-BY-NC cấm thương mại · đọc sai chữ Việt 16,9% so với 6,8% · mốc
chữ rung 90-119 ms so với 16 ms) — **lý do "nhấn nhá thấp" là SAI, số không
đỡ được**.

**SỐ CŨ TRONG ``docs/GIONG_THU_TAY.md`` KHÁC BẢNG NÀY, VÀ ĐÓ LÀ BÌNH THƯỜNG:**
tài liệu ghi Andrew 5,35 · Ryan 4,85 · Rosa 1,82; bảng này ra 4,49 · 5,38 ·
2,35. Khác vì **khác bộ câu đọc** (F0 std phụ thuộc câu). Thứ hạng vẫn cùng
chiều: Ryan ở nhóm đỉnh, Rosa ở đáy. **Đừng trộn hai bảng** — muốn so thì phải
cùng một lượt đo, và bảng dùng cho UI là bảng dưới đây.
"""
from __future__ import annotations

#: Ngưỡng chia mức, lấy từ **TỨ PHÂN VỊ CỦA CHÍNH BẢNG ĐO** (82 giọng:
#: 25% = 3,07 · 50% = 3,61 · 75% = 4,16) chứ không đặt mò. Đổi bảng thì phải
#: chạy lại tứ phân vị, đừng giữ số cũ.
RAT_CAO = 4.1
CAO = 3.6
VUA = 3.1

#: voice_id -> nhấn nhá (nửa cung). Gồm cả giọng KHÔNG PHẢI edge-tts
#: (``ov:`` OmniVoice · ``piper:``) — chúng đọc **CÙNG BỘ CÂU TIẾNG VIỆT** với
#: ``vi-VN-*`` nên so với nhau là hợp lệ, và đó đúng là phép so anh Hùng cần.
#: **SINH RA TỪ PHÉP ĐO, ĐỪNG SỬA TAY** — chạy ``_do_nhan_nha_bang.py``.
BANG: dict[str, float] = {
    "ar-SA-HamedNeural": 5.86,
    "pt-BR-AntonioNeural": 5.74,
    "en-GB-RyanNeural": 5.38,
    "ru-RU-DmitryNeural": 5.20,
    "hi-IN-MadhurNeural": 5.18,
    "en-CA-LiamNeural": 5.01,
    "zh-CN-YunjianNeural": 5.00,
    "de-DE-ConradNeural": 4.94,
    "ov:ong_gia": 4.93,
    "en-AU-WilliamMultilingualNeural": 4.73,
    "ja-JP-KeitaNeural": 4.69,
    "es-ES-AlvaroNeural": 4.68,
    "en-US-EmmaMultilingualNeural": 4.66,
    "en-US-EmmaNeural": 4.66,
    "en-IN-PrabhatNeural": 4.56,
    "en-US-AndrewNeural": 4.49,
    "ko-KR-InJoonNeural": 4.48,
    "th-TH-NiwatNeural": 4.35,
    "ov:nam_tre": 4.24,
    "en-NZ-MollyNeural": 4.22,
    "en-IE-ConnorNeural": 4.16,
    "en-AU-NatashaNeural": 4.14,
    "hi-IN-SwaraNeural": 4.14,
    "ov:nam_tram": 4.06,
    "en-HK-SamNeural": 4.05,
    "vi-VN-NamMinhNeural": 4.04,
    "it-IT-DiegoNeural": 4.03,
    "en-GB-LibbyNeural": 4.02,
    "en-IN-NeerjaExpressiveNeural": 4.01,
    "en-US-GuyNeural": 4.01,
    "en-US-RogerNeural": 3.96,
    "ja-JP-NanamiNeural": 3.95,
    "en-IE-EmilyNeural": 3.91,
    "en-NZ-MitchellNeural": 3.80,
    "en-US-AndrewMultilingualNeural": 3.79,
    "ko-KR-SunHiNeural": 3.77,
    "zh-CN-XiaoxiaoNeural": 3.74,
    "zh-CN-YunxiNeural": 3.67,
    "en-IN-NeerjaNeural": 3.62,
    "ov:nu_tre": 3.62,
    "en-GB-SoniaNeural": 3.61,
    "th-TH-PremwadeeNeural": 3.61,
    "en-CA-ClaraNeural": 3.60,
    "fr-FR-HenriNeural": 3.60,
    "en-SG-WayneNeural": 3.53,
    "en-TZ-ElimuNeural": 3.48,
    "en-US-AvaMultilingualNeural": 3.44,
    "de-DE-KatjaNeural": 3.43,
    "ov:nu_am": 3.40,
    "en-GB-ThomasNeural": 3.36,
    "en-US-AriaNeural": 3.33,
    "en-US-EricNeural": 3.31,
    "en-US-ChristopherNeural": 3.29,
    "id-ID-ArdiNeural": 3.21,
    "en-HK-YanNeural": 3.19,
    "id-ID-GadisNeural": 3.19,
    "it-IT-ElsaNeural": 3.18,
    "vi-VN-HoaiMyNeural": 3.18,
    "piper:vais1000": 3.11,
    "en-PH-JamesNeural": 3.08,
    "en-ZA-LukeNeural": 3.08,
    "en-NG-AbeoNeural": 3.07,
    "en-US-JennyNeural": 3.06,
    "ru-RU-SvetlanaNeural": 3.00,
    "en-SG-LunaNeural": 2.96,
    "en-US-AvaNeural": 2.95,
    "ar-SA-ZariyahNeural": 2.93,
    "pt-BR-FranciscaNeural": 2.89,
    "en-US-MichelleNeural": 2.81,
    "en-US-SteffanNeural": 2.77,
    "en-GB-MaisieNeural": 2.72,
    "en-US-BrianNeural": 2.71,
    "en-US-BrianMultilingualNeural": 2.70,
    "en-KE-ChilembaNeural": 2.69,
    "en-TZ-ImaniNeural": 2.69,
    "en-ZA-LeahNeural": 2.62,
    "en-KE-AsiliaNeural": 2.60,
    "en-US-AnaNeural": 2.38,
    "en-NG-EzinneNeural": 2.37,
    "en-PH-RosaNeural": 2.35,
    "fr-FR-DeniseNeural": 2.33,
    "es-ES-ElviraNeural": 2.26,
}


def muc(voice: str) -> float | None:
    """Nhấn nhá của giọng; None = CHƯA ĐO (đừng đoán bừa một con số)."""
    return BANG.get(str(voice or ""))


def chu(v: float) -> str:
    """Chữ mô tả kèm số — anh Hùng không phải tự dịch '5,4' ra nghĩa gì."""
    if v >= RAT_CAO:
        return "rất truyền cảm"
    if v >= CAO:
        return "truyền cảm"
    if v >= VUA:
        return "vừa"
    return "đều đều"


def nhan(voice: str) -> str:
    """Đuôi nhãn cho combo: ' - nhấn nhá 5,4 rất truyền cảm'.

    CHƯA ĐO -> trả chuỗi RỖNG. Cố ý: bịa một con số cho giọng chưa đo là đúng
    loại "phép đo phát chứng nhận" mà cả repo này đang chống.
    KHÔNG EMOJI (máy anh Hùng thiếu glyph -> nhãn ra ô đen).

    **CHỮ TÍNH TỪ SỐ ĐÃ LÀM TRÒN, KHÔNG PHẢI SỐ THÔ.** Jenny đo 3,06: chấm
    ngưỡng trên số thô ra *"3,1 đều đều"* — người đọc thấy 3,1 >= ngưỡng 3,1
    mà chữ lại nói ngược. Cái hiện ra phải TỰ NHẤT QUÁN, kể cả khi phải lệch
    khỏi giá trị thô một chút.
    """
    v = muc(voice)
    if v is None:
        return ""
    lam_tron = round(v, 1)
    return f" - nhấn nhá {lam_tron:.1f} {chu(lam_tron)}".replace(".", ",")


def khoa_sap(voice: str) -> tuple[int, float]:
    """Khoá sắp xếp: nhấn nhá CAO lên trước, giọng CHƯA ĐO xuống cuối.

    Dùng với ``sorted(...)`` -> (0, -nhấn_nhá) cho giọng đã đo, (1, 0.0) cho
    giọng chưa đo.
    """
    v = muc(voice)
    return (1, 0.0) if v is None else (0, -v)
