# -*- coding: utf-8 -*-
"""CÂU THỬ ĐỌC — mỗi thứ tiếng MỘT câu, viết BẰNG CHÍNH TIẾNG ĐÓ.

**FILE NÀY CHỈ PHỤC VỤ PHÉP KIỂM "ĐỌC ĐƯỢC KHÔNG", KHÔNG PHẢI ĐO NHẤN NHÁ.**
Hai việc đó đã bị gộp làm một suốt từ lượt mở 185 giọng, và chính chỗ gộp ấy
là lý do 137 giọng của 60 thứ tiếng bị khoá: `_do_nhan_nha_bang.CAU` chỉ có bộ
4 câu cho 15 thứ tiếng, nên "chưa có bộ câu để CHẤM" bị hiểu thành "không được
MỞ". Tách ra rồi thì câu hỏi rẻ (đọc được không) trả lời được cho cả 60 tiếng,
còn câu hỏi đắt (nhấn nhá bao nhiêu) cứ để trống cho tới khi có bộ câu chuẩn.

**VÌ SAO KHÔNG DÙNG LẠI `_do_nhan_nha_bang.CAU`:** `cau_cho()` của file đó lùi
về **câu TIẾNG ANH** cho mọi tiếng không có bảng. Bắt giọng Thổ / Ba Lan / Miến
đọc câu tiếng Anh thì máy đọc vẫn ra tiếng (nên phép kiểm "có đọc được không"
vẫn XANH) — nhưng nó chứng nhận sai thứ: nó chứng nhận "giọng này đọc được chữ
Latin", không phải "giọng này đọc được tiếng của nó". Ca `piper:vais1000` ra
1,88 vì đúng cái lùi này.

**NÓI THẲNG CÂU NÀY Ở ĐÂU RA:** tôi tự viết, mỗi tiếng một câu chào + một nhận
xét về thời tiết — cấu trúc giống nhau để so được, và cố ý dùng câu ĐỜI THƯỜNG
nhất có thể. **Tôi KHÔNG đọc được 60 thứ tiếng này**, nên câu chữ ở đây không
được coi là bản dịch chuẩn. Cái đỡ cho nó là một phép kiểm ĐỘC LẬP:
`_do_doc_that.py` cho Groq whisper **chép ngược chính file tiếng vừa đọc** rồi
so **NHÃN NGÔN NGỮ** máy nghe đoán ra với mã ngôn ngữ của giọng. Nhãn khớp =
câu đúng tiếng đó (hoặc chí ít máy đọc đã đọc nó bằng đúng bộ vần ấy); nhãn
lệch thì ghi ra, không giấu.

**TIẾNG TÔI ÍT CHẮC NHẤT, GHI RA TRƯỚC KHI ĐO** (đừng để phép đo tự phong):
`iu` (Inuktitut, cả hai hệ chữ) · `su` (Sunda) · `jv` (Java) · `ps` (Pashto) ·
`so` (Somali) · `mt` (Malta). Sáu tiếng này nếu nhãn ngôn ngữ lệch thì nghi
CÂU trước, đừng vội kết luận giọng hỏng.

**KHOÁ LÀ `Locale` ĐẦY ĐỦ KHI CÓ, KHÔNG THÌ MÃ NGÔN NGỮ.** `iu-Cans-CA` và
`iu-Latn-CA` là **hai hệ chữ khác nhau** của cùng một tiếng — đưa chữ âm tiết
cho giọng bản Latin (hoặc ngược lại) là bắt máy đọc đọc thứ nó không có bảng
vần, tức lại đúng cái bẫy vừa mô tả ở trên.
"""
from __future__ import annotations

#: Locale ĐẦY ĐỦ -> câu. Chỉ dùng khi hai locale của cùng một tiếng phải khác
#: nhau THẬT (khác hệ chữ). Tra bảng này TRƯỚC `CAU_TIENG`.
CAU_LOCALE: dict[str, str] = {
    # Inuktitut chữ âm tiết (Canadian Aboriginal Syllabics)
    "iu-Cans-CA": "ᐊᐃᓐᖓᐃ. ᐅᓪᓗᒥ ᓯᓚ ᐱᐅᔪᖅ.",
    # Inuktitut chữ Latin — CÙNG nội dung, khác hệ chữ
    "iu-Latn-CA": "Ainngai. Ullumi sila piujuq.",
}

#: Mã ngôn ngữ 2-3 ký tự -> câu thử. Một câu là đủ: phép kiểm này hỏi "có ra
#: tiếng thật không", không hỏi "lên xuống bao nhiêu".
CAU_TIENG: dict[str, str] = {
    "af": "Hallo, vandag is die weer baie mooi.",
    "am": "ሰላም፣ ዛሬ አየሩ በጣም ጥሩ ነው።",
    "az": "Salam, bu gün hava çox gözəldir.",
    "bg": "Здравейте, днес времето е много хубаво.",
    "bn": "নমস্কার, আজ আবহাওয়া খুব সুন্দর।",
    "bs": "Zdravo, danas je vrijeme veoma lijepo.",
    "ca": "Hola, avui fa molt bon temps.",
    "cs": "Dobrý den, dnes je velmi hezké počasí.",
    "cy": "Helo, mae'r tywydd yn braf iawn heddiw.",
    "da": "Hej, vejret er meget flot i dag.",
    "el": "Γεια σας, σήμερα ο καιρός είναι πολύ ωραίος.",
    "et": "Tere, täna on ilm väga ilus.",
    "fa": "سلام، امروز هوا خیلی خوب است.",
    "fi": "Hei, tänään on todella kaunis sää.",
    "fil": "Kumusta, napakaganda ng panahon ngayon.",
    "ga": "Dia duit, tá an aimsir go hálainn inniu.",
    "gl": "Ola, hoxe fai moi bo tempo.",
    "gu": "નમસ્તે, આજે હવામાન ખૂબ સરસ છે.",
    "he": "שלום, מזג האוויר היום יפה מאוד.",
    "hr": "Bok, danas je vrijeme vrlo lijepo.",
    "hu": "Jó napot, ma nagyon szép az idő.",
    "is": "Halló, veðrið er mjög gott í dag.",
    "jv": "Sugeng enjing, dina iki hawane apik banget.",
    "ka": "გამარჯობა, დღეს ამინდი ძალიან კარგია.",
    "kk": "Сәлеметсіз бе, бүгін ауа райы өте жақсы.",
    "km": "សួស្តី ថ្ងៃនេះ អាកាសធាតុល្អណាស់។",
    "kn": "ನಮಸ್ಕಾರ, ಇಂದು ಹವಾಮಾನ ತುಂಬಾ ಚೆನ್ನಾಗಿದೆ.",
    "lo": "ສະບາຍດີ, ມື້ນີ້ອາກາດດີຫຼາຍ.",
    "lt": "Sveiki, šiandien oras labai gražus.",
    "lv": "Sveiki, šodien laiks ir ļoti jauks.",
    "mk": "Здраво, денес времето е многу убаво.",
    "ml": "നമസ്കാരം, ഇന്ന് കാലാവസ്ഥ വളരെ നല്ലതാണ്.",
    "mn": "Сайн байна уу, өнөөдөр цаг агаар маш сайхан байна.",
    "mr": "नमस्कार, आज हवामान खूप छान आहे.",
    "ms": "Helo, hari ini cuaca sangat cantik.",
    "mt": "Bonġu, illum it-temp huwa sabiħ ħafna.",
    "my": "မင်္ဂလာပါ၊ ဒီနေ့ ရာသီဥတု အရမ်းကောင်းပါတယ်။",
    "nb": "Hei, været er veldig fint i dag.",
    "ne": "नमस्ते, आज मौसम धेरै राम्रो छ।",
    "nl": "Hallo, het weer is vandaag heel mooi.",
    "pl": "Dzień dobry, dziś jest bardzo ładna pogoda.",
    "ps": "سلام، نن ورځ هوا ډېره ښه ده.",
    "ro": "Bună ziua, astăzi vremea este foarte frumoasă.",
    "si": "ආයුබෝවන්, අද කාලගුණය ඉතා හොඳයි.",
    "sk": "Dobrý deň, dnes je veľmi pekné počasie.",
    "sl": "Pozdravljeni, danes je zelo lepo vreme.",
    "so": "Salaan, maanta cimiladu aad bay u fiican tahay.",
    "sq": "Përshëndetje, sot moti është shumë i bukur.",
    "sr": "Здраво, данас је време веома лепо.",
    "su": "Wilujeng énjing, dinten ieu cuacana saé pisan.",
    "sv": "Hej, vädret är väldigt fint idag.",
    "sw": "Habari, leo hali ya hewa ni nzuri sana.",
    "ta": "வணக்கம், இன்று வானிலை மிகவும் நன்றாக உள்ளது.",
    "te": "నమస్కారం, ఈరోజు వాతావరణం చాలా బాగుంది.",
    "tr": "Merhaba, bugün hava çok güzel.",
    "uk": "Вітаю, сьогодні дуже гарна погода.",
    "ur": "السلام علیکم، آج موسم بہت اچھا ہے۔",
    "uz": "Salom, bugun havo juda yaxshi.",
    "zu": "Sawubona, isimo sezulu sihle kakhulu namuhla.",
}

#: Sáu tiếng tôi ít chắc nhất — xem docstring. Để MÁY đọc được danh sách này
#: (báo cáo tự gắn dấu) thay vì bắt người đọc nhớ.
IT_CHAC: frozenset[str] = frozenset({"iu", "su", "jv", "ps", "so", "mt"})


def cau_cho_locale(locale: str) -> str:
    """Câu thử cho một ``Locale`` của edge-tts (``pl-PL`` · ``iu-Cans-CA``).

    KHÔNG có câu -> trả chuỗi RỖNG. **Cố ý không lùi về tiếng Anh**: lùi là
    dựng lại đúng cái bẫy `cau_cho()` đã sập (xem docstring module). Nơi gọi
    thấy rỗng thì phải ghi "chưa có câu thử", đừng đo bừa rồi ghi số.
    """
    loc = str(locale or "")
    if loc in CAU_LOCALE:
        return CAU_LOCALE[loc]
    return CAU_TIENG.get(loc.split("-")[0].lower(), "")


def ma_tieng(locale: str) -> str:
    """``pl-PL`` -> ``pl`` · ``iu-Cans-CA`` -> ``iu``."""
    return str(locale or "").split("-")[0].lower()
