# -*- coding: utf-8 -*-
"""BẢNG **ĐỌC THẬT ĐƯỢC** — giọng edge-tts nào đã CHỨNG MINH ra tiếng thật.

**FILE NÀY RA ĐỜI ĐỂ TÁCH HAI VIỆC ĐANG BỊ GỘP.** Tới trước lượt này, tấm vé
vào combo được cấp bởi ``nhan_nha.BANG`` — tức bởi phép đo **NHẤN NHÁ**. Nhấn
nhá cần bộ 4 câu ĐÚNG TIẾNG, mà ``_do_nhan_nha_bang.CAU`` chỉ có bộ câu cho 15
thứ tiếng. Hậu quả đo được: **137 giọng của 60 thứ tiếng bị khoá** không phải
vì chúng kém, cũng không phải vì ai đó nghi ngờ chúng, mà vì **thiếu bộ câu để
CHẤM** chúng. Một giọng Ba Lan không được vào combo vì tôi chưa viết được bốn
câu tiếng Ba Lan — đó là lý do không liên quan gì tới giọng đó.

Nay hai câu hỏi đi hai đường:

* **ĐỌC ĐƯỢC KHÔNG** (rẻ, BẮT BUỘC) -> bảng này. Một câu đúng tiếng là đủ.
* **NHẤN NHÁ BAO NHIÊU** (đắt, TUỲ CHỌN) -> ``nhan_nha.BANG``. Chưa có bộ câu
  thì **để TRỐNG**, nhãn ghi *"chưa đo"*. Cấm chấm bằng câu tiếng Anh rồi ghi
  số vào bảng — đó đúng cái bẫy đã làm ``piper:vais1000`` ra 1,88.

**SỐ TRONG BẢNG LÀ SỐ ĐO, SINH BẰNG MÁY — ĐỪNG GÕ TAY.** Chạy
``_do_doc_that.py``: mỗi giọng đọc **1 câu ĐÚNG TIẾNG CỦA NÓ** (bộ câu ở
``_cau_doc_thu.py``) qua **CỬA CHUNG** ``dubbing._synth_all`` — đúng cửa lượt
xuất thật đi — rồi đo trên file máy đọc trả về. Giá trị là
``(độ dài giây, RMS dBFS)``.

**VÌ SAO PHẢI LƯU CẢ HAI SỐ chứ không lưu một tập tên:** một tập tên thì ai
cũng gõ thêm được một dòng, và không ai phân biệt được "đã đo" với "đã tin".
Có số thì cổng đọc được, và cổng ĐÒI mọi giọng đang mở phải có số nằm trên
ngưỡng. Nói cách khác: bảng này là **BIÊN BẢN**, không phải danh sách ước muốn.

**NGƯỠNG ĐẠT (cả ba, xem ``_do_doc_that``):** ``_synth_all`` trả ok=True và có
file (chốt "không phải 0 byte") · độ dài >= 0,80 giây · RMS >= -60 dBFS. Hai
ngưỡng sau bắt đúng hai kiểu hỏng ÂM THẦM: máy đọc trả mảnh cụt, và máy đọc trả
file đủ dài mà toàn im lặng. **Tự kiểm bộ dò đã chạy thật**: file im lặng 3
giây đo ra -99,0 dBFS (bị bắt) · file có tiếng nhưng cụt 0,26 giây (bị bắt) ·
file 0 byte (bị bắt).

**SỐ ĐO CỦA LƯỢT NÀY (19/08/2026):** 137 giọng còn khoá -> lượt đầu **ĐẠT 133 ·
HỎNG 4** (415 giây); sau khi vá nguyên nhân của 4 ca hỏng -> **ĐẠT 137/137 ·
HỎNG 0**. Cộng 185 giọng đã có bằng chứng từ lượt đo nhấn nhá, **cả 322 giọng /
75 thứ tiếng của edge-tts nay đều có biên bản đọc thật**.

Độ dài **2,59-4,34 giây** (trung vị 3,41) · RMS **-25,7..-17,2 dBFS**. Không
giọng nào **gần** ngưỡng: ca sát sàn nhất vẫn dài gấp **3,2 lần** sàn độ dài và
cao hơn sàn RMS **34 dB**. Phép kiểm không đứng ở chỗ chông chênh, nên một lượt
nhiễu mạng không lật được kết luận.

═══════════════════════════════════════════════════════════════════════════
4 CA HỎNG BAN ĐẦU — TRUY TẬN GỐC RỒI CHỮA, KHÔNG BỎ QUA
═══════════════════════════════════════════════════════════════════════════
Cả bốn là Inuktitut (``iu-Cans-CA-Siqiniq`` · ``iu-Cans-CA-Taqqiq`` ·
``iu-Latn-CA-Siqiniq`` · ``iu-Latn-CA-Taqqiq``). **KHÔNG phải Microsoft gỡ
giọng, cũng KHÔNG phải câu thử của tôi sai** — hai nguyên nhân đó được TÁCH
BẰNG PHÉP ĐO chứ không bằng lập luận: cho chính hai giọng đó đọc **câu tiếng
Anh**, **một từ Latin** và **dãy số đếm** thì cả bốn phép đều hỏng y hệt. Câu
Inuktitut của tôi mà sai thì câu tiếng Anh đã phải chạy. Nó không chạy.

Thủ phạm là **thư viện khách ``edge_tts``**:
``data_classes.TTSConfig.__post_init__`` bóc tên giọng bằng
``^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$``, mà mẫu đó đòi phần vùng có **>= 2
CHỮ HOA liền nhau**. Locale Inuktitut có **4 đoạn** và đoạn thứ hai là
``Cans``/``Latn`` (một chữ hoa) -> không khớp -> tên giữ nguyên -> phép kiểm
thứ hai ném ``ValueError: Invalid voice``. **Nó chết TRƯỚC KHI chạm mạng**, nên
``_synth_all`` thử lại 4 lần cũng vô ích — và vì ``_synth_all`` nuốt ngoại lệ,
triệu chứng duy nhất ở ngoài là *"giọng này không đọc được"*. Không một dòng
nào chỉ ra thủ phạm.

**CHỮA:** ``giong_mo.chuan_ten_edge`` đổi sang dạng tên đầy đủ
``Microsoft Server Speech Text to Speech Voice (iu-Cans-CA, SiqiniqNeural)``,
nối vào ``dubbing._ten_edge`` tại đúng 3 chỗ gọi ``edge_tts.Communicate``. Đo
lại **QUA ĐÚNG CỬA** ``_synth_all``: **4/4 ĐẠT**, 4,22 / 4,01 / 4,22 / 4,01
giây, -20,3..-20,4 dBFS.

**MD5 của 4 file KHÁC NHAU cả 4** — chốt này có mặt vì hai locale
``Cans``/``Latn`` ra CÙNG độ dài và CÙNG RMS (là đúng: cùng một giọng đọc cùng
nội dung ở hai hệ chữ), nhìn cột số rất dễ tưởng bốn dòng đang dùng chung một
file. Cột số không phân biệt được thì phải hỏi thước khác.

**Bản vá chỉ chạm ca thư viện BÓ TAY**: ``chuan_ten_edge`` trả **nguyên văn**
cho mọi mã thư viện tự bóc được, nên **318/322 giọng không đổi một ký tự nào**.
Đó là điều kiện để một bản vá cho 4 giọng không thành canh bạc với 318 giọng
đang chạy sản xuất.
"""
from __future__ import annotations

#: Mã giọng -> (độ dài giây, RMS dBFS) của câu thử. SINH BẰNG
#: _do_doc_that.py --in-bang, đừng gõ tay.
BANG: dict[str, tuple[float, float]] = {
    "af-ZA-AdriNeural": (3.07, -22.4),
    "af-ZA-WillemNeural": (2.93, -23.3),
    "am-ET-AmehaNeural": (2.86, -24.7),
    "am-ET-MekdesNeural": (2.86, -23.7),
    "az-AZ-BabekNeural": (3.07, -25.7),
    "az-AZ-BanuNeural": (3.10, -23.6),
    "bg-BG-BorislavNeural": (3.41, -21.2),
    "bg-BG-KalinaNeural": (3.62, -22.6),
    "bn-BD-NabanitaNeural": (3.19, -22.3),
    "bn-BD-PradeepNeural": (3.14, -23.9),
    "bn-IN-BashkarNeural": (3.48, -22.8),
    "bn-IN-TanishaaNeural": (3.48, -22.5),
    "bs-BA-GoranNeural": (3.41, -23.9),
    "bs-BA-VesnaNeural": (3.41, -23.4),
    "ca-ES-EnricNeural": (3.34, -22.4),
    "ca-ES-JoanaNeural": (3.41, -21.0),
    "cs-CZ-AntoninNeural": (3.41, -19.5),
    "cs-CZ-VlastaNeural": (4.13, -17.2),
    "cy-GB-AledNeural": (3.38, -21.3),
    "cy-GB-NiaNeural": (3.74, -20.8),
    "da-DK-ChristelNeural": (3.05, -21.0),
    "da-DK-JeppeNeural": (3.10, -21.8),
    "el-GR-AthinaNeural": (3.31, -19.0),
    "el-GR-NestorasNeural": (3.38, -21.4),
    "et-EE-AnuNeural": (2.74, -23.1),
    "et-EE-KertNeural": (2.76, -22.7),
    "fa-IR-DilaraNeural": (2.88, -23.7),
    "fa-IR-FaridNeural": (3.07, -25.1),
    "fi-FI-HarriNeural": (3.79, -23.3),
    "fi-FI-NooraNeural": (3.22, -20.0),
    "fil-PH-AngeloNeural": (3.17, -20.1),
    "fil-PH-BlessicaNeural": (3.29, -23.3),
    "ga-IE-ColmNeural": (3.34, -24.2),
    "ga-IE-OrlaNeural": (3.22, -22.4),
    "gl-ES-RoiNeural": (2.64, -24.3),
    "gl-ES-SabelaNeural": (2.71, -23.7),
    "gu-IN-DhwaniNeural": (4.30, -20.9),
    "gu-IN-NiranjanNeural": (4.34, -17.5),
    "he-IL-AvriNeural": (3.79, -20.7),
    "he-IL-HilaNeural": (3.72, -21.7),
    "hr-HR-GabrijelaNeural": (3.46, -20.6),
    "hr-HR-SreckoNeural": (3.24, -21.5),
    "hu-HU-NoemiNeural": (3.48, -17.7),
    "hu-HU-TamasNeural": (2.93, -21.7),
    "is-IS-GudrunNeural": (2.88, -22.6),
    "is-IS-GunnarNeural": (2.71, -23.4),
    "iu-Cans-CA-SiqiniqNeural": (4.22, -20.3),
    "iu-Cans-CA-TaqqiqNeural": (4.01, -20.4),
    "iu-Latn-CA-SiqiniqNeural": (4.22, -20.3),
    "iu-Latn-CA-TaqqiqNeural": (4.01, -20.4),
    "jv-ID-DimasNeural": (3.58, -18.5),
    "jv-ID-SitiNeural": (3.79, -21.7),
    "ka-GE-EkaNeural": (3.48, -24.5),
    "ka-GE-GiorgiNeural": (3.48, -23.4),
    "kk-KZ-AigulNeural": (3.62, -22.0),
    "kk-KZ-DauletNeural": (3.36, -22.7),
    "km-KH-PisethNeural": (3.00, -23.3),
    "km-KH-SreymomNeural": (3.05, -22.9),
    "kn-IN-GaganNeural": (3.46, -21.6),
    "kn-IN-SapnaNeural": (3.60, -22.5),
    "lo-LA-ChanthavongNeural": (3.19, -21.9),
    "lo-LA-KeomanyNeural": (3.53, -21.1),
    "lt-LT-LeonasNeural": (3.29, -23.9),
    "lt-LT-OnaNeural": (3.67, -21.4),
    "lv-LV-EveritaNeural": (3.36, -24.6),
    "lv-LV-NilsNeural": (3.00, -21.6),
    "mk-MK-AleksandarNeural": (3.10, -22.8),
    "mk-MK-MarijaNeural": (3.10, -22.4),
    "ml-IN-MidhunNeural": (3.48, -23.5),
    "ml-IN-SobhanaNeural": (3.79, -21.9),
    "mn-MN-BataaNeural": (3.41, -25.1),
    "mn-MN-YesuiNeural": (3.41, -24.0),
    "mr-IN-AarohiNeural": (4.06, -21.1),
    "mr-IN-ManoharNeural": (3.91, -19.3),
    "ms-MY-OsmanNeural": (3.43, -21.8),
    "ms-MY-YasminNeural": (4.06, -20.6),
    "mt-MT-GraceNeural": (3.17, -24.8),
    "mt-MT-JosephNeural": (3.22, -24.6),
    "my-MM-NilarNeural": (3.84, -22.4),
    "my-MM-ThihaNeural": (3.26, -22.4),
    "nb-NO-FinnNeural": (3.14, -23.2),
    "nb-NO-PernilleNeural": (3.05, -23.4),
    "ne-NP-HemkalaNeural": (3.12, -19.3),
    "ne-NP-SagarNeural": (3.12, -22.9),
    "nl-BE-ArnaudNeural": (3.22, -21.3),
    "nl-BE-DenaNeural": (3.26, -17.9),
    "nl-NL-ColetteNeural": (3.43, -21.1),
    "nl-NL-FennaNeural": (3.55, -19.1),
    "nl-NL-MaartenNeural": (3.26, -19.9),
    "pl-PL-MarekNeural": (3.50, -20.2),
    "pl-PL-ZofiaNeural": (3.53, -21.4),
    "ps-AF-GulNawazNeural": (2.59, -22.0),
    "ps-AF-LatifaNeural": (2.62, -21.2),
    "ro-RO-AlinaNeural": (4.13, -21.3),
    "ro-RO-EmilNeural": (4.01, -18.6),
    "si-LK-SameeraNeural": (2.98, -20.9),
    "si-LK-ThiliniNeural": (2.90, -22.3),
    "sk-SK-LukasNeural": (3.41, -20.3),
    "sk-SK-ViktoriaNeural": (3.79, -18.2),
    "sl-SI-PetraNeural": (3.36, -18.3),
    "sl-SI-RokNeural": (3.77, -20.8),
    "so-SO-MuuseNeural": (3.58, -24.1),
    "so-SO-UbaxNeural": (3.77, -23.0),
    "sq-AL-AnilaNeural": (3.36, -21.7),
    "sq-AL-IlirNeural": (3.41, -24.6),
    "sr-RS-NicholasNeural": (3.24, -23.3),
    "sr-RS-SophieNeural": (3.29, -20.9),
    "su-ID-JajangNeural": (3.86, -23.3),
    "su-ID-TutiNeural": (4.10, -20.7),
    "sv-SE-MattiasNeural": (3.86, -23.1),
    "sv-SE-SofieNeural": (3.53, -20.0),
    "sw-KE-RafikiNeural": (3.36, -19.6),
    "sw-KE-ZuriNeural": (3.60, -21.2),
    "sw-TZ-DaudiNeural": (3.53, -19.6),
    "sw-TZ-RehemaNeural": (3.79, -21.2),
    "ta-IN-PallaviNeural": (3.72, -20.6),
    "ta-IN-ValluvarNeural": (3.82, -22.1),
    "ta-LK-KumarNeural": (4.01, -22.1),
    "ta-LK-SaranyaNeural": (3.91, -20.6),
    "ta-MY-KaniNeural": (3.53, -20.6),
    "ta-MY-SuryaNeural": (4.01, -22.1),
    "ta-SG-AnbuNeural": (3.62, -22.1),
    "ta-SG-VenbaNeural": (3.53, -20.6),
    "te-IN-MohanNeural": (3.60, -18.6),
    "te-IN-ShrutiNeural": (3.62, -21.0),
    "tr-TR-AhmetNeural": (3.43, -18.6),
    "tr-TR-EmelNeural": (3.05, -19.9),
    "uk-UA-OstapNeural": (3.74, -22.1),
    "uk-UA-PolinaNeural": (3.53, -21.3),
    "ur-IN-GulNeural": (4.03, -21.2),
    "ur-IN-SalmanNeural": (4.03, -20.3),
    "ur-PK-AsadNeural": (3.50, -23.2),
    "ur-PK-UzmaNeural": (3.26, -22.6),
    "uz-UZ-MadinaNeural": (2.83, -21.6),
    "uz-UZ-SardorNeural": (2.71, -23.0),
    "zu-ZA-ThandoNeural": (4.15, -21.9),
    "zu-ZA-ThembaNeural": (3.98, -21.9),
}


def da_doc(ma: str) -> bool:
    """Giọng này đã CHỨNG MINH đọc ra tiếng thật (qua _synth_all) chưa."""
    return str(ma or "") in BANG


def so_do(ma: str) -> tuple[float, float] | None:
    """(độ dài, RMS) đo được; None = chưa kiểm."""
    return BANG.get(str(ma or ""))
