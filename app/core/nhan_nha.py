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

═══════════════════════════════════════════════════════════════════════════
BẢNG 82 -> 191 GIỌNG (19/08/2026) — VÀ THƯỚC ĐÃ PHẢI DỰNG LẠI
═══════════════════════════════════════════════════════════════════════════
**ĐỌC CÁI NÀY TRƯỚC KHI TIN 109 SỐ MỚI.** Docstring trên trỏ về
``_do_nhan_nha.f0_nua_cung`` "của lượt 10", nhưng file đó **CHƯA BAO GIỜ ĐƯỢC
COMMIT** — ``git log --all -- _do_nhan_nha.py`` ra rỗng. Tức 82 số cũ được
sinh ra bởi một đoạn mã **không còn trên đĩa**, và ai muốn đo thêm một giọng
đều đâm vào ``ImportError``. Thước đã được **dựng lại** từ mô tả trong chính
docstring này cộng với ``_do_bien_the_giong.f0_trung_vi`` (hàm F0 cùng tác
giả, cùng cách, vẫn còn trong repo).

**BẢN DỰNG LẠI KHÔNG ĐƯỢC TIN CHO TỚI KHI TÁI LẬP ĐƯỢC BẢNG CŨ** — trộn số
của hai cái thước vào cùng MỘT CỘT là lỗi không ai nhìn ra được.
``_do_kiem_thuoc.py`` đo lại **8 giọng đã có trong bảng, trải từ đáy tới
đỉnh** (2,26 -> 5,86):

    ar-SA-Hamed 5,86 -> 5,86 (+0,00)   ·  en-GB-Ryan  5,38 -> 5,38 (+0,00)
    en-US-Andrew 4,49 -> 4,39 (-0,10)  ·  vi-VN-NamMinh 4,04 -> 4,10 (+0,06)
    en-US-Aria  3,33 -> 3,33 (+0,00)   ·  vi-VN-HoaiMy 3,18 -> 3,18 (+0,00)
    en-US-Jenny 3,06 -> 3,06 (+0,00)   ·  es-ES-Elvira 2,26 -> 2,27 (+0,01)

**5/8 giọng lệch ĐÚNG 0,00 · lệch lớn nhất 0,10 · TB 0,021** — nằm gọn trong
dải nhiễu mà chính mục "SỐ NÀY TIỀN ĐỊNH" ở trên đã đo (0,00..0,12). Thước
dựng lại là ĐÚNG THƯỚC CŨ.

**109 GIỌNG MỚI** (``_do_nhan_nha_het.py``, 207 giây, **109/109 đo được, 0
lỗi**): toàn bộ giọng còn lại của 14 thứ tiếng ĐÃ CÓ BỘ CÂU RIÊNG —
es 43 · ar 30 · zh 11 · fr 11 · de 8 · pt 3 · it 2 · ko 1.
Trải **1,91 – 6,66**, rộng hơn hẳn bảng cũ (2,26 – 5,86).

**ĐỈNH BẢNG ĐỔI CHỦ, VÀ ĐÓ LÀ CHUYỆN ĐÁNG NÓI:** ``zh-CN-Yunyang`` **6,66**
vượt ``ar-SA-Hamed`` (5,86) — nhưng nhớ giới hạn số 1 ở trên: **so CHÉO tiếng
chỉ là tham khảo**. Con số dùng để chọn giọng là con số TRONG CÙNG một tiếng.

**137 GIỌNG CÒN LẠI (60 thứ tiếng) CỐ Ý ĐỂ TRỐNG.** ``_do_nhan_nha_bang.CAU``
chỉ có bộ câu cho 15 thứ tiếng, còn ``cau_cho()`` lùi về **câu tiếng Anh** cho
mọi tiếng khác — bắt giọng Thổ/Ba Lan/Hà Lan đọc câu tiếng Anh rồi ghi số vào
bảng chính là bẫy đã làm ``piper:vais1000`` ra 1,88 (thấp nhất toàn bảng).
Ô trống ở đây nghĩa là CHƯA ĐO, và ``nhan()`` trả chuỗi rỗng cho chúng — đúng
luật "bịa một con số cạnh tên giọng là người dùng sẽ tin mà chọn".
"""
from __future__ import annotations

from app.core import giong_doc

#: Đuôi nhãn cho giọng **ĐỌC ĐƯỢC nhưng CHƯA ĐO nhấn nhá** — trạng thái THỨ BA,
#: thêm 19/08/2026 cùng lượt mở 133 giọng của 59 thứ tiếng.
#:
#: **VÌ SAO PHẢI CÓ TRẠNG THÁI THỨ BA.** Trước lượt này chỉ có hai: có số, hoặc
#: không có mặt trong combo. Nên muốn mở một giọng thì buộc phải có số cho nó,
#: mà có số thì phải có bộ 4 câu đúng tiếng — và đó chính là chỗ 137 giọng của
#: 60 thứ tiếng bị kẹt. Hai đường thoát sai đều đã bị loại:
#:
#: * **bịa số** (chấm bằng câu tiếng Anh) -> người dùng thấy con số cạnh tên
#:   giọng thì họ TIN mà chọn. Đây là bẫy đã làm ``piper:vais1000`` ra 1,88.
#: * **để trống hẳn** -> ``duoi_nhan_nha`` trả rỗng, dòng combo không có đuôi,
#:   nhìn y hệt một lỗi hiển thị. Người đọc không phân biệt được "chưa đo" với
#:   "app quên".
#:
#: Nói thẳng "chưa đo" giải được cả hai: không có số nào để tin nhầm, mà cũng
#: không ai tưởng là hỏng. **KHÔNG EMOJI** (máy anh Hùng thiếu glyph -> ô đen).
CHUA_DO = " - chưa đo nhấn nhá"

#: Ngưỡng chia mức, lấy từ **TỨ PHÂN VỊ CỦA CHÍNH BẢNG ĐO** chứ không đặt mò.
#: Đổi bảng thì phải chạy lại tứ phân vị, đừng giữ số cũ — và lượt 19/08/2026
#: đã chạy lại thật khi bảng lên 191 giọng:
#:
#:      82 giọng  ->  25% = 3,07 · 50% = 3,61 · 75% = 4,16
#:     191 giọng  ->  25% = 3,10 · 50% = 3,54 · 75% = 4,14
#:
#: Làm tròn 1 chữ số (đúng số hiện ra trên nhãn) thì chỉ ``CAO`` đổi:
#: **3,6 -> 3,5**. Đổi ngưỡng là đổi NHÃN của giọng cũ, nên phải đếm: **đúng
#: 2 giọng** trong 82 giọng cũ đổi nhãn (``en-SG-Wayne`` 3,53 và
#: ``en-TZ-Elimu`` 3,48, cả hai "vừa" -> "truyền cảm"). Phân bố trên bảng mới:
#: 52 rất truyền cảm · 50 truyền cảm · 47 vừa · 42 đều đều — bốn nhóm cân
#: nhau, đúng ý nghĩa của tứ phân vị.
#:
#: **KHÔNG đổi mấy số này để cho cổng xanh.** Chúng chỉ được đổi khi BẢNG đổi,
#: và phải đổi bằng cách chạy lại tứ phân vị.
RAT_CAO = 4.1
CAO = 3.5
VUA = 3.1

#: voice_id -> nhấn nhá (nửa cung). Gồm cả giọng KHÔNG PHẢI edge-tts
#: (``ov:`` OmniVoice · ``piper:``) — chúng đọc **CÙNG BỘ CÂU TIẾNG VIỆT** với
#: ``vi-VN-*`` nên so với nhau là hợp lệ, và đó đúng là phép so anh Hùng cần.
#: **SINH RA TỪ PHÉP ĐO, ĐỪNG SỬA TAY** — chạy ``_do_nhan_nha_bang.py``
#: (danh sách gọn) rồi ``_do_nhan_nha_het.py`` (phần còn lại).
BANG: dict[str, float] = {
    "zh-CN-YunyangNeural": 6.66,
    "ar-MA-JamalNeural": 6.03,
    "ar-DZ-IsmaelNeural": 6.01,
    "ar-AE-HamdanNeural": 5.99,
    "ar-KW-FahedNeural": 5.87,
    "ar-SA-HamedNeural": 5.86,
    "ar-LB-RamiNeural": 5.75,
    "pt-BR-AntonioNeural": 5.74,
    "ar-IQ-BasselNeural": 5.47,
    "ar-QA-MoazNeural": 5.45,
    "en-GB-RyanNeural": 5.38,
    "ar-BH-AliNeural": 5.20,
    "ru-RU-DmitryNeural": 5.20,
    "hi-IN-MadhurNeural": 5.18,
    "ar-JO-TaimNeural": 5.12,
    "ar-LY-OmarNeural": 5.12,
    "ar-YE-SalehNeural": 5.04,
    "fr-CA-AntoineNeural": 5.03,
    "en-CA-LiamNeural": 5.01,
    "fr-CA-ThierryNeural": 5.00,
    "zh-CN-YunjianNeural": 5.00,
    "de-DE-ConradNeural": 4.94,
    "ov:ong_gia": 4.93,
    "fr-CA-JeanNeural": 4.83,
    "en-AU-WilliamMultilingualNeural": 4.73,
    "ar-EG-ShakirNeural": 4.71,
    "ja-JP-KeitaNeural": 4.69,
    "es-ES-AlvaroNeural": 4.68,
    "en-US-EmmaMultilingualNeural": 4.66,
    "en-US-EmmaNeural": 4.66,
    "de-DE-KillianNeural": 4.56,
    "en-IN-PrabhatNeural": 4.56,
    "zh-TW-YunJheNeural": 4.55,
    "en-US-AndrewNeural": 4.49,
    "de-AT-IngridNeural": 4.48,
    "ko-KR-InJoonNeural": 4.48,
    "fr-FR-RemyMultilingualNeural": 4.40,
    "th-TH-NiwatNeural": 4.35,
    "de-CH-JanNeural": 4.25,
    "ov:nam_tre": 4.24,
    "en-NZ-MollyNeural": 4.22,
    "es-CU-ManuelNeural": 4.18,
    "en-IE-ConnorNeural": 4.16,
    "de-DE-FlorianMultilingualNeural": 4.15,
    "fr-CH-FabriceNeural": 4.15,
    "en-AU-NatashaNeural": 4.14,
    "es-HN-CarlosNeural": 4.14,
    "hi-IN-SwaraNeural": 4.14,
    "zh-HK-HiuGaaiNeural": 4.10,
    "de-AT-JonasNeural": 4.09,
    "es-ES-XimenaNeural": 4.07,
    "ov:nam_tram": 4.06,
    "en-HK-SamNeural": 4.05,
    "vi-VN-NamMinhNeural": 4.04,
    "it-IT-DiegoNeural": 4.03,
    "en-GB-LibbyNeural": 4.02,
    "en-IN-NeerjaExpressiveNeural": 4.01,
    "en-US-GuyNeural": 4.01,
    "es-DO-EmilioNeural": 4.01,
    "es-NI-FedericoNeural": 4.00,
    "es-CL-LorenzoNeural": 3.99,
    "en-US-RogerNeural": 3.96,
    "es-GQ-JavierNeural": 3.95,
    "es-GT-AndresNeural": 3.95,
    "ja-JP-NanamiNeural": 3.95,
    "en-IE-EmilyNeural": 3.91,
    "es-PE-AlexNeural": 3.87,
    "es-EC-LuisNeural": 3.81,
    "en-NZ-MitchellNeural": 3.80,
    "en-US-AndrewMultilingualNeural": 3.79,
    "ko-KR-SunHiNeural": 3.77,
    "de-CH-LeniNeural": 3.76,
    "es-MX-JorgeNeural": 3.76,
    "es-US-AlonsoNeural": 3.75,
    "es-PA-RobertoNeural": 3.74,
    "zh-CN-XiaoxiaoNeural": 3.74,
    "es-PR-VictorNeural": 3.70,
    "es-CR-JuanNeural": 3.69,
    "es-CO-GonzaloNeural": 3.67,
    "zh-CN-YunxiNeural": 3.67,
    "pt-PT-DuarteNeural": 3.66,
    "zh-CN-shaanxi-XiaoniNeural": 3.65,
    "en-IN-NeerjaNeural": 3.62,
    "ov:nu_tre": 3.62,
    "en-GB-SoniaNeural": 3.61,
    "es-BO-MarceloNeural": 3.61,
    "pt-BR-ThalitaMultilingualNeural": 3.61,
    "th-TH-PremwadeeNeural": 3.61,
    "en-CA-ClaraNeural": 3.60,
    "fr-FR-HenriNeural": 3.60,
    "zh-HK-WanLungNeural": 3.59,
    "es-DO-RamonaNeural": 3.57,
    "es-VE-SebastianNeural": 3.56,
    "es-EC-AndreaNeural": 3.55,
    "zh-CN-YunxiaNeural": 3.55,
    "es-CR-MariaNeural": 3.54,
    "es-SV-LorenaNeural": 3.54,
    "es-SV-RodrigoNeural": 3.54,
    "en-SG-WayneNeural": 3.53,
    "es-PR-KarinaNeural": 3.53,
    "en-TZ-ElimuNeural": 3.48,
    "es-US-PalomaNeural": 3.48,
    "en-US-AvaMultilingualNeural": 3.44,
    "de-DE-KatjaNeural": 3.43,
    "es-GT-MartaNeural": 3.43,
    "es-PA-MargaritaNeural": 3.43,
    "ko-KR-HyunsuMultilingualNeural": 3.43,
    "es-PE-CamilaNeural": 3.40,
    "ov:nu_am": 3.40,
    "ar-EG-SalmaNeural": 3.38,
    "en-GB-ThomasNeural": 3.36,
    "es-MX-DaliaNeural": 3.36,
    "it-IT-GiuseppeMultilingualNeural": 3.36,
    "en-US-AriaNeural": 3.33,
    "es-NI-YolandaNeural": 3.33,
    "es-PY-MarioNeural": 3.32,
    "en-US-EricNeural": 3.31,
    "ar-LY-ImanNeural": 3.30,
    "ar-QA-AmalNeural": 3.30,
    "zh-CN-XiaoyiNeural": 3.30,
    "zh-HK-HiuMaanNeural": 3.30,
    "ar-YE-MaryamNeural": 3.29,
    "en-US-ChristopherNeural": 3.29,
    "es-CL-CatalinaNeural": 3.27,
    "fr-BE-GerardNeural": 3.26,
    "ar-TN-HediNeural": 3.23,
    "ar-IQ-RanaNeural": 3.22,
    "es-HN-KarlaNeural": 3.22,
    "es-VE-PaolaNeural": 3.22,
    "id-ID-ArdiNeural": 3.21,
    "ar-JO-SanaNeural": 3.20,
    "de-DE-SeraphinaMultilingualNeural": 3.20,
    "es-BO-SofiaNeural": 3.20,
    "ar-OM-AbdullahNeural": 3.19,
    "en-HK-YanNeural": 3.19,
    "id-ID-GadisNeural": 3.19,
    "pt-PT-RaquelNeural": 3.19,
    "zh-TW-HsiaoChenNeural": 3.19,
    "it-IT-ElsaNeural": 3.18,
    "vi-VN-HoaiMyNeural": 3.18,
    "ar-BH-LailaNeural": 3.16,
    # Khoá phải là mã ĐẦY ĐỦ `piper_tts.MA_GIONG`. Bản đầu ghi
    # `piper:vais1000` (tên tôi gõ lúc đo) -> `muc()` trả None, số đo đúng mà
    # tra không ra. `_piper_hay_khong` nhận MỌI id bắt đầu bằng `piper:` nên
    # phép đo vẫn chạy và vẫn ra tiếng — sai khoá KHÔNG hề lộ ra lúc đo.
    "piper:vi_VN-vais1000-medium": 3.11,
    "zh-CN-liaoning-XiaobeiNeural": 3.11,
    "ar-TN-ReemNeural": 3.10,
    "en-PH-JamesNeural": 3.08,
    "en-ZA-LukeNeural": 3.08,
    "de-DE-AmalaNeural": 3.07,
    "en-NG-AbeoNeural": 3.07,
    "en-US-JennyNeural": 3.06,
    "es-AR-TomasNeural": 3.05,
    "ar-SY-LaithNeural": 3.03,
    "es-UY-MateoNeural": 3.03,
    "ru-RU-SvetlanaNeural": 3.00,
    "ar-AE-FatimaNeural": 2.99,
    "ar-DZ-AminaNeural": 2.99,
    "ar-KW-NouraNeural": 2.98,
    "ar-MA-MounaNeural": 2.97,
    "en-SG-LunaNeural": 2.96,
    "en-US-AvaNeural": 2.95,
    "ar-SA-ZariyahNeural": 2.93,
    "es-AR-ElenaNeural": 2.92,
    "es-UY-ValentinaNeural": 2.92,
    "fr-CA-SylvieNeural": 2.91,
    "pt-BR-FranciscaNeural": 2.89,
    "ar-LB-LaylaNeural": 2.88,
    "ar-OM-AyshaNeural": 2.85,
    "en-US-MichelleNeural": 2.81,
    "zh-TW-HsiaoYuNeural": 2.79,
    "ar-SY-AmanyNeural": 2.78,
    "en-US-SteffanNeural": 2.77,
    "en-GB-MaisieNeural": 2.72,
    "fr-FR-EloiseNeural": 2.72,
    "en-US-BrianNeural": 2.71,
    "en-US-BrianMultilingualNeural": 2.70,
    "en-KE-ChilembaNeural": 2.69,
    "en-TZ-ImaniNeural": 2.69,
    "fr-CH-ArianeNeural": 2.66,
    "fr-BE-CharlineNeural": 2.64,
    "en-ZA-LeahNeural": 2.62,
    "en-KE-AsiliaNeural": 2.60,
    "en-US-AnaNeural": 2.38,
    "en-NG-EzinneNeural": 2.37,
    "en-PH-RosaNeural": 2.35,
    "fr-FR-DeniseNeural": 2.33,
    "es-CU-BelkysNeural": 2.30,
    "es-GQ-TeresaNeural": 2.30,
    "it-IT-IsabellaNeural": 2.30,
    "es-ES-ElviraNeural": 2.26,
    "fr-FR-VivienneMultilingualNeural": 2.12,
    "es-PY-TaniaNeural": 1.92,
    "es-CO-SalomeNeural": 1.91,
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
    """Đuôi nhãn cho combo — **BA TRẠNG THÁI, đừng rút về hai**::

        đã đo             ->  " - nhấn nhá 5,4 rất truyền cảm"
        ĐỌC ĐƯỢC, chưa đo ->  " - chưa đo nhấn nhá"        (xem ``CHUA_DO``)
        không biết gì cả  ->  ""

    Trạng thái thứ ba giữ nguyên nghĩa cũ: **bịa một con số cho giọng chưa đo
    là đúng loại "phép đo phát chứng nhận" mà cả repo này đang chống**. Trạng
    thái thứ hai là mới, và nó chỉ áp cho giọng ĐÃ CÓ BẰNG CHỨNG ĐỌC THẬT
    (``giong_doc.BANG``) — tức nhãn "chưa đo" không bao giờ rơi vào một mã
    giọng bâng quơ, nó luôn nói về một giọng app dám mở.

    KHÔNG EMOJI (máy anh Hùng thiếu glyph -> nhãn ra ô đen).

    **CHỮ TÍNH TỪ SỐ ĐÃ LÀM TRÒN, KHÔNG PHẢI SỐ THÔ.** Jenny đo 3,06: chấm
    ngưỡng trên số thô ra *"3,1 đều đều"* — người đọc thấy 3,1 >= ngưỡng 3,1
    mà chữ lại nói ngược. Cái hiện ra phải TỰ NHẤT QUÁN, kể cả khi phải lệch
    khỏi giá trị thô một chút.

    **BẤT BIẾN CỔNG 83 CHẤM:** với **mọi** mã đã có trong ``BANG``, chuỗi trả
    ra phải giống bản mốc **TỪNG KÝ TỰ**. Nhánh mới chỉ được chạm mã KHÔNG có
    trong ``BANG`` — nếu không thì 191 dòng combo anh Hùng đang nhìn tự đổi
    chữ sau một lượt vá chẳng liên quan.
    """
    v = muc(voice)
    if v is None:
        return CHUA_DO if giong_doc.da_doc(voice) else ""
    lam_tron = round(v, 1)
    return f" - nhấn nhá {lam_tron:.1f} {chu(lam_tron)}".replace(".", ",")


def khoa_sap(voice: str) -> tuple[int, float]:
    """Khoá sắp xếp: nhấn nhá CAO lên trước, giọng CHƯA ĐO xuống cuối.

    Dùng với ``sorted(...)`` -> (0, -nhấn_nhá) cho giọng đã đo, (1, 0.0) cho
    giọng chưa đo.
    """
    v = muc(voice)
    return (1, 0.0) if v is None else (0, -v)
