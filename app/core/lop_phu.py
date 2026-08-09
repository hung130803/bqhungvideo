# -*- coding: utf-8 -*-
"""CHỌN LỚP PHỦ HẠT **THEO NỘI DUNG CẢNH** — không khớp thì KHÔNG THÊM.

VÌ SAO CÓ FILE NÀY (nguyên văn anh Hùng 09/08/2026): *"tôi muốn làm đa dạng
nhiều kiểu ấy… kiểu hiệu ứng tuyết rơi, trái tim bay, với rất nhiều kiểu khác
thêm vào — **nhưng phải hợp lý, tuỳ cảnh mới chọn chứ không chọn bừa bãi**"*.

Kho hiệu ứng cũ (27 kiểu, `hieu_ung.py`) chọn theo SỐ ĐO: giây nào tiếng vọt
lên / hình động mạnh thì nhấn ở đó. Cách ấy ĐÚNG cho zoom/rung/glitch — chúng
không mang nghĩa. Lớp phủ thì MANG NGHĨA: **tuyết rơi trên video nấu ăn là
hỏng**, dù giây đó tiếng có vọt lên tới đâu. Vì vậy nhóm lớp phủ **KHÔNG hề có
mặt trong `hieu_ung._UV_THEO_LOAI`** — đường chọn theo số đo không bao giờ với
tới được nó. Cửa duy nhất là file này.

=== 3 BẤT BIẾN, ĐỪNG NỚI ===
1. **KHÔNG KHỚP THÌ KHÔNG THÊM.** Thà clip trần còn hơn tuyết rơi trong bếp.
   Mọi đường ra đều trả `([], lý do)` — lý do được ghi nhật ký để tra sau.
2. **KHÔNG GỌI THÊM LLM.** Chỉ đọc 2 thứ CÓ SẴN: `vision_digest` (đã cache
   trong bảng `analysis`) và BẢN CHÉP LỜI của chính đoạn đó. Không digest ->
   BỎ QUA NHÓM NÀY, tuyệt đối không bật vision chỉ để chọn hiệu ứng: đo thật
   06/08/2026 là **219 giây/video**, nhân 300 kênh thì không dùng được.
3. **MỖI CLIP TỐI ĐA 1 LỚP PHỦ** và nó vẫn ăn chung ngân sách 10% thời lượng +
   trần độ đậm `DAM_MAX` của nhóm cũ. Lớp phủ là thứ mắt thấy rõ nhất trong cả
   kho (đo 9-27% điểm ảnh đổi) — 2 cái một lúc là loè.

=== VÌ SAO CHẤM ĐIỂM KIỂU NÀY (không phải "có từ khoá là bật") ===
Một mốc digest lẻ nhắc tới "ice" thì có thể chỉ là ly nước đá trong quán. Nên:
  * bằng chứng phải LẶP LẠI (đếm theo SỐ MỐC digest, không phải số lần chữ);
  * từ khoá PHỤ (bối cảnh: "cold", "winter") một mình KHÔNG BAO GIỜ đủ điểm —
    trần của riêng chúng đã nằm dưới ngưỡng, cố ý;
  * mỗi kiểu có danh sách **CẤM**: thấy là loại thẳng, không cộng trừ gì.
    Đây là cái chặn "tuyết rơi trên video nấu ăn" — "kitchen/cooking/chef" cấm
    tuyết, "fight/blood/match" cấm trái tim;
  * hai kiểu khác HỌ mà điểm sát nhau = nội dung PHA TẠP -> KHÔNG THÊM GÌ.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

#: Điểm tự tin tối thiểu (0..1) mới được đặt lớp phủ. Xem `_diem` để biết thang
#: điểm; 0,55 nghĩa là phải có **2 mốc digest mạnh**, hoặc **1 mốc digest mạnh +
#: 1 từ mạnh trong lời**. Một mình một mốc digest thì KHÔNG đủ (đo: 2,0/6,0 =
#: 0,33) — đúng chủ ý: một khung hình lướt qua không phải là chủ đề của clip.
NGUONG_TIN = 0.55
#: Kiểu nhất phải hơn kiểu nhì bấy nhiêu (khi hai kiểu KHÁC HỌ) mới dám chọn.
#: Sát nhau = nội dung pha tạp (vừa tiệc vừa khóc) -> không đoán.
CACH_BIET = 0.12
#: Trần số lớp phủ mỗi clip.
LOP_PHU_MAX = 1
#: Thang chuẩn hoá điểm thô -> 0..1.
_THANG = 6.0

#: lý do của lượt chọn gần nhất (chỉ để đọc/ghi nhật ký, không ai được dựa vào
#: nó để quyết định — 3 làn xuất song song thì nó là của lượt nào xong sau cùng,
#: đúng bài học `_SFX_LAST_PICK`). Đường xuất lấy lý do qua GIÁ TRỊ TRẢ VỀ.
LY_DO_CUOI = ""


@dataclass
class Luat:
    """1 luật khớp cảnh -> 1 kiểu lớp phủ.

    `ho`: HỌ cảnh. Hai kiểu cùng họ (lấp lánh / confetti đều là "vui") điểm sát
    nhau thì cứ chọn cái cao hơn — chúng nói cùng một chuyện. Khác họ mà sát
    nhau thì nội dung đang pha tạp -> bỏ.
    """
    khoa: str
    ho: str
    manh: tuple = ()
    phu: tuple = ()
    cam: tuple = ()
    #: BIẾN THỂ NHÌN của CÙNG MỘT CẢNH — `((khoá_hiệu_ứng, (gợi ý…)), …)`.
    #: Anh Hùng 09/08/2026: *"càng nhiều kiểu càng tốt, 100 kiểu cũng được,
    #: nhưng đảm bảo AI hiểu ngữ cảnh, thêm vào hợp lý, không thêm bừa bãi"*.
    #: Cách mở rộng ĐÚNG là thêm BIẾN THỂ trong cùng ngữ cảnh (tuyết bụi bay
    #: ngang · bông rơi chậm · bão tuyết dày), KHÔNG bịa thêm ngữ cảnh không
    #: nhận ra được — vì mỗi ngữ cảnh mới là một cơ hội nhận NHẦM, còn biến thể
    #: thì dùng LẠI đúng bằng chứng đã đủ mạnh của cảnh đó.
    #: Rỗng -> `((khoa, ()),)`, tức hành xử Y HỆT bản 10 kiểu.
    bien: tuple = ()
    _re_manh: list = field(default_factory=list, repr=False)
    _re_phu: list = field(default_factory=list, repr=False)
    _re_cam: list = field(default_factory=list, repr=False)
    _re_bien: list = field(default_factory=list, repr=False)


def _khong_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường: 'Tuyết Rơi' -> 'tuyet roi'.

    Bản chép lời của anh Hùng có dấu, còn bảng từ khoá viết KHÔNG dấu cho gọn và
    để khớp được cả khi Groq trả thiếu dấu. `đ` không phải chữ có dấu tổ hợp nên
    phải thay tay.
    """
    s = str(s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _bien(tu: str) -> re.Pattern:
    """Từ khoá -> mẫu dò có RÀNG BUỘC BIÊN TỪ.

    Bắt buộc, không phải cho đẹp: dò chuỗi con thì `ice` khớp "pol**ice**",
    "serv**ice**", "n**ice**" -> tuyết rơi trên video cảnh sát. Đã thử trên
    chính bảng dưới đây: bỏ biên từ là 3/6 ca nội dung khớp SAI.
    """
    return re.compile(r"(?<![a-z0-9])" + re.escape(_khong_dau(tu))
                      + r"(?![a-z0-9])")


def _dk(l: Luat) -> Luat:
    l._re_manh = [_bien(t) for t in l.manh]
    l._re_phu = [_bien(t) for t in l.phu]
    l._re_cam = [_bien(t) for t in l.cam]
    l._re_bien = [(k, [_bien(t) for t in (goi or ())])
                  for k, goi in (l.bien or ((l.khoa, ()),))]
    LUAT[l.khoa] = l
    return l


def moi_kieu() -> set:
    """MỌI khoá hiệu ứng mà bảng luật có thể chọn ra (gồm cả biến thể).

    Cổng 46 canh `hieu_ung.LOP_PHU <= moi_kieu()`: kiểu nằm trong kho mà không
    luật nào với tới được là **kiểu chết** — nó vào bản .exe, ăn chỗ, mà không
    bao giờ hiện ra clip nào. Đó đúng là bệnh 6 shader "nằm trong .exe mà không
    một dòng mã nào gọi tới" đã ghi ở cổng 41.
    """
    return {k for l in LUAT.values() for k, _g in l._re_bien}


LUAT: dict = {}

# ---------------------------------------------------------------- BẢNG LUẬT
# Mô tả digest là TIẾNG ANH (prompt `vision_digest._VISION_PROMPT` yêu cầu vậy),
# còn chép lời là tiếng của video. Nên mỗi hàng có CẢ HAI: từ tiếng Anh cho
# hình, từ tiếng Việt (không dấu) cho lời. GHI THẲNG GIỚI HẠN: video tiếng
# Nhật/Hàn/Trung thì phần LỜI gần như không khớp được (không có từ khoá của các
# thứ tiếng đó ở đây) — với chúng, bằng chứng đến từ DIGEST là chính, và vì
# ngưỡng cần 2 mốc digest mạnh nên vẫn an toàn, chỉ ít khi bật hơn.
_dk(Luat(
    "tuyet_roi", "lanh",
    manh=("snow", "snowy", "snowing", "snowfall", "snowman", "snowflake",
          "snowflakes", "blizzard", "ski", "skiing", "snowboard", "icicle",
          "frozen lake", "tuyet roi", "bong tuyet", "tuyet trang",
          "phu tuyet", "bang tuyet", "truot tuyet"),
    phu=("winter", "cold", "icy", "frost", "frosty", "freezing", "chilly",
         "scarf", "gloves", "mountain", "mua dong", "lanh", "gia ret", "ret",
         "khan quang", "gang tay", "nui tuyet", "troi lanh"),
    cam=("kitchen", "cooking", "cook", "chef", "frying", "pan", "stove",
         "oven", "recipe", "grill", "barbecue", "beach", "desert", "summer",
         "pool", "sand", "sweating", "nau an", "can bep", "dau bep",
         "chao ran", "lo nuong", "cong thuc", "bai bien", "be boi",
         "sa mac"),
    bien=(("tuyet_roi", ("snowfall", "snowflake", "snowflakes", "snowman",
                         "bong tuyet", "tuyet roi")),
          ("tuyet_bui", ("wind", "windy", "gust", "breeze", "gio thoi",
                         "gio lanh")),
          ("tuyet_bao", ("blizzard", "storm", "heavy snow", "ski", "skiing",
                         "snowboard", "bao tuyet", "truot tuyet")),
          ("tuyet_tinh_the", ("icicle", "frozen lake", "crystal", "frost",
                              "frosty", "bang tuyet", "pha le")))))
_dk(Luat(
    "trai_tim", "tinh_cam",
    manh=("wedding", "bride", "groom", "marriage", "kiss", "kissing", "hug",
          "hugging", "couple", "romantic", "baby", "newborn", "toddler",
          "infant", "puppy", "kitten", "proposal", "engagement", "valentine",
          "dam cuoi", "co dau", "chu re", "hon nhau", "om nhau", "cap doi",
          "em be", "tre so sinh", "cun con", "meo con", "cau hon", "tinh yeu"),
    phu=("love", "smile", "smiling", "laughing", "family", "mother", "father",
         "together", "gift", "flowers", "heart", "cuddle", "tender",
         "gia dinh", "cha me", "me con", "bo me", "cung nhau", "qua tang",
         "bo hoa", "yeu thuong"),
    cam=("fight", "fighting", "punch", "blood", "weapon", "gun", "accident",
         "crash", "funeral", "angry", "shouting", "war", "police", "arrest",
         "match", "race", "goal", "referee", "workout", "gym", "danh nhau",
         "chay mau", "vet mau", "sung dan", "tai nan", "dam tang",
         "chien tranh", "canh sat",
         "thi dau", "ban thang", "trong tai", "tap gym"),
    bien=(("trai_tim", ("couple", "romantic", "love", "cuddle", "tender",
                        "cap doi", "tinh yeu", "yeu thuong")),
          ("trai_tim_nho", ("baby", "newborn", "toddler", "infant", "puppy",
                            "kitten", "em be", "tre so sinh", "cun con",
                            "meo con")),
          # tim VỠ chỉ bật khi có bằng chứng "tan vỡ" — không thì cảnh cưới lại
          # ra tim vỡ. Đây là biến thể có gợi ý riêng chặt nhất bảng.
          ("trai_tim_vo", ("breakup", "heartbroken", "crying", "tears",
                           "goodbye", "farewell", "chia tay", "tan vo",
                           "nuoc mat", "tam biet")),
          ("canh_hoa", ("wedding", "bride", "groom", "marriage", "proposal",
                        "engagement", "flowers", "dam cuoi", "co dau",
                        "chu re", "cau hon", "bo hoa")))))
_dk(Luat(
    "lap_lanh", "vui",
    manh=("sparkle", "sparkling", "glitter", "jewelry", "diamond", "ring",
          "makeup", "magic", "magical", "transformation", "princess",
          "crystal", "lap lanh", "kim cuong", "trang suc", "nhan cuoi",
          "trang diem", "phep thuat", "long lay", "pha le"),
    phu=("beautiful", "elegant", "gold", "silver", "shiny", "glowing",
         "stars", "surprise", "wow", "sang trong", "ngoi sao", "bat ngo",
         "lung linh"),
    cam=("fight", "blood", "accident", "funeral", "war", "mud", "garbage",
         "crash", "danh nhau", "chay mau", "tai nan", "dam tang",
         "chien tranh", "bun dat", "bai rac"),
    bien=(("lap_lanh", ("magic", "magical", "transformation", "surprise",
                        "phep thuat", "bat ngo")),
          ("lap_lanh_bui", ("makeup", "glitter", "sparkling", "trang diem",
                            "lap lanh")),
          ("lap_lanh_sao", ("princess", "stars", "crystal", "wow", "shiny",
                            "ngoi sao", "pha le", "lung linh")),
          ("lap_lanh_vang", ("jewelry", "diamond", "ring", "gold", "silver",
                             "kim cuong", "trang suc", "nhan cuoi",
                             "sang trong")))))
_dk(Luat(
    "confetti", "vui",
    manh=("birthday", "cake", "candles", "party", "celebration",
          "celebrating", "confetti", "graduation", "trophy", "champion",
          "winner", "victory", "award", "prize", "new year", "anniversary",
          "sinh nhat", "banh kem", "tiec", "an mung", "tot nghiep",
          "vo dich", "chien thang", "giai thuong", "nam moi", "khai truong"),
    phu=("happy", "clapping", "applause", "dancing", "crowd", "balloons",
         "cheers", "toast", "vui", "vo tay", "nhay mua", "dam dong",
         "bong bay", "chuc mung"),
    cam=("funeral", "crying", "sad", "accident", "hospital", "war",
         "protest", "fight", "blood", "dam tang", "khoc", "tai nan",
         "benh vien", "chien tranh", "bieu tinh", "danh nhau",
         "chay mau"),
    bien=(("confetti", ("confetti", "party", "celebration", "celebrating",
                        "tiec", "an mung")),
          ("confetti_dai", ("graduation", "award", "prize", "anniversary",
                            "tot nghiep", "giai thuong", "khai truong")),
          ("confetti_no", ("trophy", "champion", "winner", "victory",
                           "vo dich", "chien thang")),
          ("bong_bay", ("birthday", "cake", "candles", "balloons", "new year",
                        "sinh nhat", "banh kem", "bong bay", "nam moi")))))
_dk(Luat(
    "mua_roi", "buon",
    manh=("rain", "raining", "rainy", "downpour", "umbrella", "storm",
          "thunderstorm", "drizzle", "monsoon", "crying", "tears", "breakup",
          "heartbroken", "farewell", "funeral", "grave", "troi mua",
          "con mua", "mua rao", "duoi mua", "cay du", "con bao", "khoc",
          "nuoc mat", "chia tay", "tan vo", "dam tang", "nam mo"),
    phu=("sad", "alone", "lonely", "grey sky", "dark clouds", "goodbye",
         "empty", "window", "noi buon", "mot minh", "co don", "may den",
         "tam biet", "trong vang"),
    cam=("birthday", "party", "celebration", "confetti", "wedding",
         "comedy", "desert", "kitchen", "cooking", "sinh nhat", "tiec",
         "an mung", "dam cuoi", "hai huoc", "sa mac", "nau an", "bep"),
    bien=(("mua_roi", ("rain", "raining", "rainy", "troi mua", "con mua",
                       "duoi mua")),
          ("mua_rao", ("downpour", "storm", "thunderstorm", "monsoon",
                       "mua rao", "con bao")),
          ("mua_bui", ("drizzle", "sad", "alone", "lonely", "noi buon",
                       "co don", "mot minh")),
          ("giot_kinh", ("window", "umbrella", "grey sky", "dark clouds",
                         "cua so", "cay du", "may den")))))
_dk(Luat(
    "dom_bokeh", "dem",
    manh=("night", "nighttime", "city lights", "neon", "streetlights",
          "bokeh", "concert", "stage lights", "nightclub", "fireworks",
          "lantern", "candlelight", "christmas lights", "ban dem",
          "den neon", "den duong", "hoa nhac", "san khau", "phao hoa",
          "den long", "anh nen", "den giang sinh"),
    phu=("dark", "evening", "glowing", "skyline", "blurred lights",
         "troi toi", "buoi toi", "len den", "duong chan troi"),
    cam=("daylight", "midday", "noon", "sunny", "beach", "ban ngay",
         "giua trua", "nang gat", "bai bien"),
    bien=(("dom_bokeh", ("bokeh", "blurred lights", "city lights", "skyline",
                         "den duong", "duong chan troi")),
          ("bokeh_nho", ("nightclub", "concert", "stage lights", "hoa nhac",
                         "san khau")),
          ("den_nhap_nhay", ("christmas lights", "lantern", "candlelight",
                             "neon", "den giang sinh", "den long", "anh nen",
                             "den neon")),
          ("phao_hoa", ("fireworks", "phao hoa")))))
_dk(Luat(
    "tan_lua", "lua",
    manh=("fire", "flames", "burning", "bonfire", "campfire", "explosion",
          "blast", "fireplace", "forge", "welding", "torch", "volcano",
          "embers", "ngon lua", "dam chay", "lua trai", "dot lua",
          "lua chay", "vu no", "lo suoi", "han xi", "nui lua", "than hong"),
    phu=("smoke", "heat", "sparks", "ash", "dragon", "khoi lua",
         "tia lua", "tro tan", "rong lua"),
    cam=("snow", "ice", "rain", "underwater", "swimming", "winter",
         "hospital", "baby", "tuyet roi", "bong tuyet", "troi mua",
         "con mua", "duoi nuoc", "boi loi", "mua dong", "benh vien",
         "em be"),
    bien=(("tan_lua", ("embers", "campfire", "bonfire", "torch", "lua trai",
                       "than hong", "dot lua")),
          ("tan_lua_day", ("explosion", "blast", "volcano", "forge",
                           "welding", "vu no", "nui lua", "han xi",
                           "dam chay")),
          ("khoi_bay", ("smoke", "ash", "heat", "fireplace", "khoi lua",
                        "tro tan", "lo suoi")))))
_dk(Luat(
    "tia_sang", "hoai_niem",
    manh=("sunset", "sunrise", "golden hour", "lens flare", "flashback",
          "vintage", "retro", "nostalgic", "film camera", "old photo",
          "hoang hon", "binh minh", "nang chieu", "hoi tuong", "ngay xua",
          "co dien", "may anh phim", "anh cu"),
    phu=("memories", "warm light", "silhouette", "dreamy", "soft light",
         "summer evening", "ky niem", "anh sang am", "nguoc sang",
         "mo mang"),
    cam=("screen recording", "spreadsheet", "chart", "horror", "dark room",
         "quay man hinh", "bang tinh", "bieu do", "kinh di", "phong toi"),
    bien=(("tia_sang", ("lens flare", "flashback", "nostalgic", "hoi tuong",
                        "ngay xua")),
          ("tia_sang_doc", ("vintage", "retro", "film camera", "old photo",
                            "co dien", "may anh phim", "anh cu")),
          ("nang_xuyen", ("sunset", "sunrise", "golden hour", "summer evening",
                          "soft light", "hoang hon", "binh minh",
                          "nang chieu")))))
_dk(Luat(
    "bui_phim", "hoai_niem",
    manh=("black and white", "archive footage", "vintage film", "old movie",
          "grainy", "historical", "museum", "ancestor", "war archive",
          "den trang", "tu lieu", "phim cu", "lich su", "bao tang",
          "to tien", "ky uc"),
    phu=("old", "past", "grandmother", "grandfather", "letter", "diary",
         "dusty", "cu ky", "qua khu", "ba noi", "ong noi", "la thu",
         "nhat ky", "bui bam", "ngay truoc"),
    cam=("modern", "futuristic", "gaming", "smartphone screen", "unboxing",
         "neon", "hien dai", "tuong lai", "khui hop"),
    bien=(("bui_phim", ("grainy", "old movie", "archive footage",
                        "vintage film", "phim cu", "tu lieu")),
          ("xuoc_phim", ("black and white", "historical", "war archive",
                         "den trang", "lich su")),
          ("bui_bay", ("museum", "ancestor", "letter", "diary", "dusty",
                       "bao tang", "to tien", "la thu", "nhat ky",
                       "bui bam")))))
_dk(Luat(
    "la_roi", "thien_nhien",
    manh=("autumn", "fall leaves", "falling leaves", "maple", "foliage",
          "forest", "orchard", "countryside", "hiking trail", "mua thu",
          "la roi", "la vang", "rung cay", "vuon cay", "nong thon",
          "duong rung"),
    phu=("nature", "outdoor", "wind", "trees", "park", "peaceful", "birds",
         "thien nhien", "ngoai troi", "gio thoi", "cay coi", "cong vien",
         "yen binh", "chim hot"),
    bien=(("la_roi", ("autumn", "fall leaves", "falling leaves", "maple",
                      "mua thu", "la roi", "la vang")),
          ("la_bay", ("wind", "hiking trail", "countryside", "gio thoi",
                      "duong rung", "nong thon")),
          ("la_kim_tuyen", ("foliage", "orchard", "forest", "park",
                            "rung cay", "vuon cay", "cong vien")))))

# ---- 4 CẢNH MỚI (09/08/2026). Điều kiện để được thêm một CẢNH mới (không phải
# biến thể): từ khoá phải ĐẶC TRƯNG tới mức khó nhầm sang cảnh khác, và phải có
# danh sách CẤM đủ mạnh. Cảnh nào chỉ nhận ra được bằng từ chung chung
# ("food", "travel", "sport") thì KHÔNG thêm — thà không có còn hơn thêm bừa.
_dk(Luat(
    "duoi_nuoc", "nuoc",
    manh=("underwater", "diving", "scuba", "snorkeling", "aquarium",
          "fish tank", "swimming pool", "swimming", "waterfall",
          "coral reef", "duoi nuoc", "lan bien", "be ca", "be boi",
          "boi loi", "thac nuoc", "san ho"),
    phu=("water", "sea", "ocean", "wave", "waves", "bubbles", "boat",
         "nuoc bien", "song bien", "bot nuoc", "dai duong", "con thuyen"),
    cam=("desert", "fire", "flames", "kitchen", "cooking", "snow",
         "sa mac", "lua chay", "nau an", "can bep", "tuyet roi"),
    bien=(("bong_bong", ("bubbles", "aquarium", "fish tank", "be ca",
                         "bot khi")),
          ("bot_nuoc", ("waterfall", "wave", "waves", "diving", "scuba",
                        "thac nuoc", "song bien", "lan bien")),
          ("song_nuoc", ("swimming pool", "swimming", "coral reef",
                         "be boi", "mat nuoc", "boi loi")))))
_dk(Luat(
    "ma_quai", "bi_an",
    manh=("halloween", "ghost", "haunted", "horror", "scary", "spooky",
          "pumpkin", "graveyard", "cemetery", "zombie", "witch", "creepy",
          "ma quy", "kinh di", "ghe ron", "nghia trang", "ma am"),
    phu=("dark", "fog", "mist", "midnight", "abandoned", "mystery",
         "toi tam", "suong mu", "nua dem", "hoang tan", "bo hoang"),
    cam=("birthday", "wedding", "baby", "comedy", "cooking", "kitchen",
         "beach", "sinh nhat", "dam cuoi", "em be", "hai huoc", "nau an",
         "can bep", "bai bien"),
    bien=(("suong_mo", ("fog", "mist", "forest", "abandoned", "suong mu",
                        "bo hoang")),
          ("dom_ma", ("ghost", "haunted", "witch", "ma am", "linh hon")),
          ("tan_tro", ("zombie", "ruins", "burned", "graveyard", "tro tan",
                       "tan the", "hoang tan")))))
_dk(Luat(
    "tien_bac", "tien",
    # "to tien" KHÔNG được dùng ở đây: bỏ dấu thì `tờ tiền` và `tổ tiên` ra
    # CÙNG một chuỗi — đúng cái bẫy `tuyết`/`tuyệt vời` đã ghi.
    manh=("money", "cash", "banknote", "dollar", "dollars", "wallet",
          "jackpot", "lottery", "payday", "gold bar", "treasure",
          "millionaire", "tien mat", "tien giay", "vi tien", "trung so",
          "xo so", "luong thang", "vang mieng", "kho bau", "ty phu"),
    phu=("shopping", "price", "expensive", "business", "bank", "invest",
         "luxury", "mua sam", "gia tien", "dat tien", "kinh doanh",
         "ngan hang", "dau tu", "giam gia"),
    cam=("funeral", "hospital", "war", "accident", "protest", "dam tang",
         "benh vien", "chien tranh", "tai nan", "bieu tinh"),
    bien=(("tien_roi", ("cash", "banknote", "dollar", "dollars", "lottery",
                        "jackpot", "tien mat", "tien giay", "trung so")),
          ("xu_vang", ("coin", "coins", "treasure", "gold bar", "dong xu",
                       "kho bau", "vang mieng")),
          ("lap_lanh_vang", ("luxury", "millionaire", "expensive",
                             "giau co", "sang trong", "ty phu")))))
_dk(Luat(
    "cong_nghe", "so",
    manh=("computer", "laptop", "coding", "programming", "software",
          "robot", "robotics", "artificial intelligence", "hologram",
          "circuit board", "server room", "video game", "screen recording",
          "may tinh", "lap trinh", "phan mem", "tri tue nhan tao",
          "man hinh may tinh", "choi game"),
    phu=("screen", "keyboard", "data", "digital", "technology", "futuristic",
         "man hinh", "ban phim", "du lieu", "cong nghe", "tuong lai"),
    cam=("nature", "forest", "beach", "cooking", "kitchen", "baby",
         "wedding", "snow", "thien nhien", "rung cay", "bai bien",
         "nau an", "can bep", "em be", "dam cuoi"),
    bien=(("hat_so", ("artificial intelligence", "data", "hologram",
                      "server room", "robot", "tri tue nhan tao",
                      "du lieu")),
          ("luoi_so", ("screen recording", "video game", "circuit board",
                       "man hinh", "choi game")))),
)


# -------------------------------------------------------------- CHẤM ĐIỂM
def _dem_moc(digest: list, mau: list) -> tuple[int, list]:
    """Đếm SỐ MỐC digest có ít nhất 1 từ khoá khớp -> (số mốc, [mốc đã khớp]).

    Đếm theo MỐC chứ không theo số lần chữ xuất hiện: một mô tả nhắc "snow"
    ba lần vẫn chỉ là MỘT khung hình, không phải bằng chứng mạnh gấp ba.
    """
    ra = []
    for d in digest or []:
        t = _khong_dau(d.get("desc", ""))
        if any(r.search(t) for r in mau):
            ra.append(d)
    return len(ra), ra


def _dem_tu(loi: str, mau: list) -> int:
    """Số từ khoá KHÁC NHAU khớp trong lời (không phải tổng số lần)."""
    return sum(1 for r in mau if r.search(loi))


def _diem(l: Luat, digest: list, loi: str) -> Optional[dict]:
    """Điểm thô + bằng chứng của 1 luật. `None` = BỊ CẤM (thấy từ khoá cấm).

    Thang: mốc digest MẠNH 2,0 (trần 2 mốc) · mốc digest PHỤ 0,7 (trần 3) ·
    từ MẠNH trong lời 1,5 (trần 2) · từ PHỤ trong lời 0,5 (trần 2).
    Trần riêng của nhóm PHỤ = 0,7*3 + 0,5*2 = 3,1 điểm thô = 0,52 < NGUONG_TIN
    -> **bối cảnh một mình KHÔNG BAO GIỜ đủ**, đúng chủ ý.
    """
    if any(r.search(loi) for r in l._re_cam):
        return None
    n_cam_hinh, _ = _dem_moc(digest, l._re_cam)
    if n_cam_hinh:
        return None
    dm, moc_manh = _dem_moc(digest, l._re_manh)
    dp, moc_phu = _dem_moc(digest, l._re_phu)
    tm = _dem_tu(loi, l._re_manh)
    tp = _dem_tu(loi, l._re_phu)
    tho = 2.0 * min(2, dm) + 0.7 * min(3, dp) + 1.5 * min(2, tm) \
        + 0.5 * min(2, tp)
    return {"khoa": l.khoa, "ho": l.ho, "tho": tho,
            "tin": max(0.0, min(1.0, tho / _THANG)),
            "dm": dm, "dp": dp, "tm": tm, "tp": tp,
            "moc": moc_manh or moc_phu}


def _so(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def _van(s: str) -> int:
    """Số nguyên ỔN ĐỊNH từ một chuỗi — **KHÔNG dùng `hash()`**.

    `hash()` của Python băm chuỗi kèm `PYTHONHASHSEED` NGẪU NHIÊN mỗi tiến
    trình, nên cùng một clip xuất lại (hoặc xuất ở làn khác) sẽ ra biến thể
    KHÁC. Với 3 làn xuất song song thì đó là "mỗi Part một kiểu ngẫu nhiên",
    không tra lại được — đúng loại lỗi `_SFX_LAST_PICK`. `crc32` là hàm thuần,
    cùng chuỗi luôn ra cùng số, ở mọi máy.
    """
    import zlib
    return int(zlib.crc32(str(s).encode("utf-8", "replace")))


def _chon_bien(l: Luat, digest: list, loi: str, dung: set,
               kho: dict) -> tuple:
    """Cảnh đã khớp -> chọn 1 BIẾN THỂ NHÌN. Trả `(khoá, lý do)`.

    Hai đường, theo đúng thứ tự:
      1. **GỢI Ý RIÊNG** — biến thể nào có từ khoá riêng khớp thì lấy nó
         ("blizzard" -> bão tuyết dày, chứ không phải bông rơi lững lờ). Mốc
         digest tính 2, từ trong lời tính 1: hình là bằng chứng chắc hơn lời.
      2. **RẢI ĐỀU TIỀN ĐỊNH** — không biến thể nào được gợi ý riêng thì chia
         theo `crc32` của CHÍNH bằng chứng (mô tả digest + lời). Cùng một clip
         luôn ra cùng biến thể (xuất lại không đổi), nhưng clip khác nội dung
         thì ra biến thể khác -> 3 Part của một video không giống hệt nhau,
         mà vẫn KHÔNG hề "chọn bừa": cảnh đã được chấm đạt ngưỡng ở trên rồi,
         đây chỉ là chọn CÁCH VẼ trong cùng một cảnh.

    Biến thể không có trong kho / bị máy nhân viên loại (`dung`) thì bỏ qua —
    cùng lối lùi êm của nhóm shader.
    """
    ung = [(k, ps) for k, ps in l._re_bien if k in dung and k in kho]
    if not ung:
        return "", "không biến thể nào của cảnh này dùng được trên máy này"
    diem = []
    for k, ps in ung:
        n = (2 * _dem_moc(digest, ps)[0] + _dem_tu(loi, ps)) if ps else 0
        diem.append((n, k))
    cao = max(n for n, _k in diem)
    dau = sorted(k for n, k in diem if n == cao)
    if cao > 0 and len(dau) == 1:
        return dau[0], f"biến thể theo gợi ý riêng ({cao} bằng chứng)"
    if len(dau) == 1:
        return dau[0], "cảnh chỉ có 1 biến thể"
    van = _van(" ".join(str(d.get("desc", "")) for d in digest or []) + "|"
               + str(loi))
    return (dau[van % len(dau)],
            f"biến thể rải đều theo nội dung ({len(dau)} kiểu cùng cảnh)")


def chon_lop_phu(digest: list, loi: str, tong_giay: float,
                 muc: str = "vua", co_the_dung: Optional[list] = None,
                 tranh: Optional[list] = None,
                 ngan_sach: Optional[float] = None) -> tuple[list, str]:
    """KHỚP CẢNH -> tối đa 1 lớp phủ. Hàm THUẦN (không ffmpeg, không DB, không LLM).

    Trả `([{bat,het,khoa,dam,loai,vi_sao}], lý do)`. Danh sách RỖNG là kết quả
    HỢP LỆ và hay gặp nhất — lý do luôn nói được vì sao (ghi nhật ký).

      digest : [{'t': giây trên timeline ĐẦU RA, 'desc': mô tả, 'act': 0-10}]
               Caller (`ffmpeg_utils`) đã lọc bỏ mốc rơi ngoài các đoạn được
               cắt và đã đổi `t` sang timeline đầu ra — file này không biết gì
               về chuyện cắt ghép.
      loi    : bản chép lời CỦA CHÍNH ĐOẠN NÀY (không phải cả video).
      tranh  : các giây ĐÃ có hiệu ứng khác (giữ khoảng cách `CACH_MIN`).
      ngan_sach : số giây còn lại trong trần 10% (None = tự tính).
    """
    global LY_DO_CUOI
    from app.core import hieu_ung as HU
    LY_DO_CUOI = ""
    m = str(muc or "").strip().lower()
    if m not in HU.MUC_DAM:
        return [], "mức hiệu ứng Tắt -> không xét lớp phủ"
    if float(tong_giay or 0) < 2.0:
        return [], "clip quá ngắn (<2s)"
    if not digest:
        # ĐÂY LÀ ĐƯỜNG RA HAY GẶP NHẤT và nó ĐÚNG: `VISION_CUT` mặc định TẮT
        # (3,7 phút/video là quá đắt cho 300 kênh), nên phần lớn clip không có
        # digest. Luật đã chốt: KHÔNG bật vision chỉ để chọn hiệu ứng.
        return [], ("không có vision_digest cho clip này -> bỏ qua nhóm lớp phủ "
                    "(không bật AI xem hình chỉ để chọn hiệu ứng)")
    dung = set(co_the_dung if co_the_dung is not None else HU.dung_duoc())
    loi_n = _khong_dau(loi or "")
    bang = []
    for _k, l in LUAT.items():
        # LUẬT LÀ CẢNH, không phải kiểu: chỉ cần MỘT biến thể còn dùng được thì
        # cảnh đó vẫn xét. Lọc theo chính khoá luật là sai từ lúc có biến thể —
        # tên cảnh có thể không còn là tên một kiểu trong kho.
        if not any(k2 in dung and k2 in HU.KHO for k2, _g in l._re_bien):
            continue
        d = _diem(l, digest, loi_n)
        if d is not None:
            bang.append(d)
    if not bang:
        return [], "mọi kiểu lớp phủ đều bị từ khoá CẤM loại (nội dung trái cảnh)"
    bang.sort(key=lambda d: -d["tho"])
    nhat = bang[0]
    if nhat["tho"] <= 0.0:
        # Ca HAY GẶP và cũng là ca AN TOÀN NHẤT: nội dung không dính tới cảnh
        # nào trong bảng (phỏng vấn, mở hộp, giảng bài…). Nói thẳng ra thế, đừng
        # in "kiểu hợp nhất là tuyet_roi 0,00" — đọc lên tưởng app suýt bật
        # tuyết cho video phỏng vấn.
        return [], ("không mốc hình nào và không từ nào trong lời khớp bảng "
                    "cảnh -> KHÔNG thêm lớp phủ")
    if nhat["tin"] < NGUONG_TIN:
        return [], (f"kiểu hợp nhất là {nhat['khoa']} nhưng độ tự tin chỉ "
                    f"{_so(nhat['tin'])} < ngưỡng {_so(NGUONG_TIN)} "
                    f"({nhat['dm']} mốc hình mạnh · {nhat['dp']} mốc phụ · "
                    f"{nhat['tm']} từ mạnh trong lời) -> KHÔNG thêm gì")
    nhi = next((d for d in bang[1:] if d["ho"] != nhat["ho"]), None)
    if nhi and nhi["tin"] >= NGUONG_TIN \
            and (nhat["tin"] - nhi["tin"]) < CACH_BIET:
        return [], (f"nội dung PHA TẠP: {nhat['khoa']} {_so(nhat['tin'])} và "
                    f"{nhi['khoa']} {_so(nhi['tin'])} sát nhau (cách "
                    f"{_so(nhat['tin'] - nhi['tin'])} < {_so(CACH_BIET)}) "
                    f"-> KHÔNG đoán, không thêm gì")
    kieu, ly_do_bien = _chon_bien(LUAT[nhat["khoa"]], digest, loi_n, dung,
                                  HU.KHO)
    if not kieu:
        return [], (f"{nhat['khoa']} khớp cảnh ({_so(nhat['tin'])}) nhưng "
                    f"{ly_do_bien}")
    h = HU.KHO[kieu]
    dai = max(HU.DAI_MIN, min(HU.DAI_MAX, h.dai))
    con = float(tong_giay) * HU.TY_LE_MAX if ngan_sach is None \
        else float(ngan_sach)
    if dai > con + 1e-6:
        return [], (f"{nhat['khoa']} khớp cảnh ({_so(nhat['tin'])}) nhưng ngân "
                    f"sách còn {_so(con)}s < {_so(dai)}s -> nhường hiệu ứng "
                    f"điểm nhấn")
    # ĐẶT ĐÚNG CHỖ CÓ BẰNG CHỨNG: giây của mốc digest đã kích hoạt luật (mốc
    # `act` cao nhất). Đặt bừa giữa clip thì tuyết rơi đúng lúc cảnh trong nhà.
    moc = sorted(nhat["moc"], key=lambda d: -int(d.get("act", 0) or 0))
    bat = float(moc[0]["t"]) if moc else max(0.0, float(tong_giay) * 0.3)
    bat = max(0.0, min(float(tong_giay) - dai - 0.05, bat))
    if bat < 0:
        return [], "clip ngắn hơn thời lượng lớp phủ"
    for g in (tranh or []):
        if abs(bat - float(g)) < HU.CACH_MIN:
            return [], (f"{nhat['khoa']} khớp cảnh nhưng giây {_so(bat, 1)} "
                        f"nằm sát điểm nhấn đã có ({_so(float(g), 1)}s, cách "
                        f"< {_so(HU.CACH_MIN, 1)}s) -> không chồng")
    vi_sao = (f"giây {_so(bat, 1)} · {h.ten} · cảnh «{nhat['khoa']}» · "
              f"{ly_do_bien} · KHỚP NỘI DUNG — tự tin "
              f"{_so(nhat['tin'])}/1,00 (ngưỡng {_so(NGUONG_TIN)}): "
              f"{nhat['dm']} mốc hình khớp mạnh, {nhat['dp']} mốc phụ, "
              f"{nhat['tm']} từ mạnh trong lời"
              + (f'; cảnh: "{str(moc[0].get("desc", ""))[:60]}"' if moc else ""))
    LY_DO_CUOI = vi_sao
    return ([{"bat": round(bat, 3), "het": round(bat + dai, 3),
              "khoa": kieu, "canh": nhat["khoa"], "dam": HU.MUC_DAM[m],
              "loai": "lop_phu", "vi_sao": vi_sao}], vi_sao)


def ghi_nhat_ky(ly_do: str, ten_clip: str = "") -> None:
    """1 dòng vào `logs/lop_phu_<ngày>.log`. KHÔNG BAO GIỜ ném lỗi.

    Vì sao phải ghi cả lúc KHÔNG thêm gì: nhóm này im lặng theo thiết kế, nên
    nếu không ghi thì "sao clip của tôi không có tuyết" là câu không tra được —
    đúng cái bẫy đã che chuyện model vision bị Groq gỡ suốt mấy ngày.
    """
    try:
        from datetime import datetime

        from config import DATA_DIR
        d = DATA_DIR / "logs"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"lop_phu_{datetime.now():%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] {ten_clip} — {ly_do}\n")
    except Exception:  # noqa: BLE001 — nhật ký không bao giờ được chặn việc
        pass


def loi_theo_doan(transcript: dict, segs: list, tran: int = 4000) -> str:
    """Chép lời CỦA RIÊNG các đoạn được cắt (không phải cả video). Hàm THUẦN.

    Lấy cả video là sai kiểu khác: video 20 phút nói về đám cưới ở phút 15 thì
    clip cắt ở phút 2 cũng được gán trái tim. Chỉ câu nào GIAO với đoạn cắt mới
    tính. Không có mốc câu -> trả "" (thà không có bằng chứng lời còn hơn bằng
    chứng của chỗ khác).
    """
    ss = [(float(s), float(e)) for s, e in (segs or []) if float(e) > float(s)]
    if not ss:
        return ""
    ra = []
    for c in (transcript or {}).get("segments") or []:
        try:
            a, b = float(c.get("start")), float(c.get("end"))
        except (TypeError, ValueError):
            continue
        if any(b > s and a < e for s, e in ss):
            t = str(c.get("text") or "").strip()
            if t:
                ra.append(t)
        if sum(len(x) for x in ra) > tran:
            break
    return " ".join(ra)[:tran]


def loc_digest_theo_doan(digest: list, segs: list, vspeed: float = 1.0) -> list:
    """Mốc digest (giây NGUỒN) -> giây trên timeline ĐẦU RA; bỏ mốc bị cắt đi.

    Hàm THUẦN, để `ffmpeg_utils` gọi. Vì sao phải có: digest được xây cho CẢ
    video, còn clip chỉ lấy 2-4 đoạn. Không lọc thì một mốc "snowy mountain" ở
    phút 12 vẫn bật tuyết cho clip cắt ở phút 2 — đúng loại "chọn bừa" phải
    tránh. Thứ tự đoạn có thể NGƯỢC THỜI GIAN (hook-first) nên phải cộng dồn
    theo ĐÚNG thứ tự danh sách, không sắp xếp lại.
    """
    ra = []
    for d in digest or []:
        try:
            t = float(d.get("t"))
        except (TypeError, ValueError):
            continue
        acc = 0.0
        for s, e in segs or []:
            s, e = float(s), float(e)
            if e <= s:
                continue
            if s <= t <= e:
                ra.append({"t": round((acc + (t - s)) / max(0.01, vspeed), 3),
                           "desc": str(d.get("desc") or ""),
                           "act": int(d.get("act", 0) or 0)})
                break
            acc += (e - s)
    ra.sort(key=lambda d: d["t"])
    return ra
