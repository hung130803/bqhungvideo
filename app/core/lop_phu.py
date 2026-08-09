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
    #: bản dò trên text CÒN DẤU — dùng cho LỜI THOẠI (xem `_DAU_VN`).
    _rd_manh: list = field(default_factory=list, repr=False)
    _rd_phu: list = field(default_factory=list, repr=False)
    _rd_cam: list = field(default_factory=list, repr=False)
    _rd_bien: list = field(default_factory=list, repr=False)


def _khong_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường: 'Tuyết Rơi' -> 'tuyet roi'.

    DÙNG CHO **MÔ TẢ DIGEST** (đường XEM HÌNH). Mô tả digest là tiếng Anh do
    model sinh ra nên bỏ dấu ở đây gần như chỉ là hạ chữ thường. `đ` không phải
    chữ có dấu tổ hợp nên phải thay tay.

    **KHÔNG DÙNG CHO LỜI THOẠI** — xem `_ha` và `_DAU_VN` để biết vì sao.
    """
    s = str(s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _ha(s: str) -> str:
    """Hạ chữ thường nhưng **GIỮ NGUYÊN DẤU** — dùng cho LỜI THOẠI."""
    return str(s or "").lower()


#: Lớp chữ "trong một từ" của tiếng Việt CÓ DẤU. `[a-z0-9]` không đủ: chữ có
#: dấu nằm ngoài a-z nên `(?![a-z0-9])` coi ngay sau `lạ` là hết từ và `lạnh`
#: khớp được cả trong `lạnh`… — thực ra vẫn đúng ở đây, nhưng để biên từ có
#: nghĩa với tiếng Việt thì phải kể cả chữ có dấu vào lớp.
_CHU = ("a-z0-9àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩị"
        "òóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ")

#: ========================= BẢNG DẤU (bẫy đã ĐO ĐƯỢC) =========================
#: Bảng luật bên dưới viết từ khoá tiếng Việt **KHÔNG DẤU** — đúng cho đường XEM
#: HÌNH (mô tả digest là tiếng Anh). Nhưng đường LỜI THOẠI đọc CHỮ THẬT của
#: video, mà bỏ dấu tiếng Việt thì hai từ khác nghĩa hẳn nhập làm một.
#: **ĐO THẬT 09/08/2026 (`_do_lop_phu_loi.py`) — 9 bẫy, tất cả là từ khoá MẠNH
#: (chỉ cần 2 cái là đủ bật lớp phủ):**
#:     "thế là **rồi**"  -> `la roi`  (lá rơi)  -> lá rụng mùa thu
#:     "rất **tiếc**"    -> `tiec`    (tiệc)    -> confetti ăn mừng
#:     "**anh cứ** làm"  -> `anh cu`  (ảnh cũ)  -> tia sáng hoài niệm
#:     "**anh nên** đi"  -> `anh nen` (ánh nến) -> đốm bokeh đêm
#:     "**nằm mơ** thấy" -> `nam mo`  (nấm mồ)  -> mưa rơi
#:     "**có đâu** mà lo"-> `co dau`  (cô dâu)  -> trái tim
#:     "**lịch sự** lắm" -> `lich su` (lịch sử) -> bụi phim
#:     "mà **ấm** áp"    -> `ma am`   (ma ám)   -> ma quái
#:     "**có điện** rồi" -> `co dien` (cổ điển) -> tia sáng
#: (3 bẫy anh Hùng nêu đích danh — `tuyết`/`tuyệt vời`, `mưa`/`mùa đông`,
#: `máu`/`màu sắc` — đo ra là ĐÃ SẠCH SẴN vì từ khoá là CỤM 2 CHỮ; cổng vẫn giữ
#: đủ 3 ca đó để lần sau ai thêm từ khoá 1 chữ `tuyet`/`mua`/`mau` là biết ngay.)
#:
#: CÁCH CHỮA: đường LỜI dò dạng **CÓ DẤU**. Khoá = dạng không dấu trong bảng
#: luật, giá trị = các cách viết CÓ DẤU chấp nhận được (nhiều cách vì chính tả
#: tiếng Việt có biến thể: "hòa nhạc"/"hoà nhạc", "kỷ niệm"/"kỉ niệm").
#: Từ khoá KHÔNG có trong bảng này (tiếng Anh, tiếng Nhật, tiếng Hàn) được dò
#: NGUYÊN VĂN — tiếng Anh không có dấu nên không đổi gì.
#: **GIỚI HẠN GHI THẲNG:** nếu Groq trả bản chép lời tiếng Việt **mất hết dấu**
#: thì không cách nào phân biệt `lá rơi` với `là rồi` — lúc đó đường lời mất tác
#: dụng (từ khoá có dấu không khớp text không dấu). Đó là hướng AN TOÀN: thà
#: không thêm còn hơn thêm bừa.
_DAU_VN: dict = {
    "an mung": ("ăn mừng",), "anh cu": ("ảnh cũ",), "anh nen": ("ánh nến",),
    "anh sang am": ("ánh sáng ấm",), "ba noi": ("bà nội",),
    "bai bien": ("bãi biển",), "bai rac": ("bãi rác",), "ban dem": ("ban đêm",),
    "ban ngay": ("ban ngày",), "ban phim": ("bàn phím",),
    "ban thang": ("bàn thắng",), "bang tinh": ("bảng tính",),
    "bang tuyet": ("băng tuyết",), "banh kem": ("bánh kem",),
    "bao tang": ("bảo tàng",), "bao tuyet": ("bão tuyết",),
    "bat ngo": ("bất ngờ",), "be boi": ("bể bơi",), "be ca": ("bể cá",),
    "benh vien": ("bệnh viện",), "bep": ("bếp",), "bieu do": ("biểu đồ",),
    "bieu tinh": ("biểu tình",), "binh minh": ("bình minh",),
    "bo hoa": ("bó hoa",), "bo hoang": ("bỏ hoang",), "bo me": ("bố mẹ",),
    "boi loi": ("bơi lội",), "bong bay": ("bóng bay",),
    "bong tuyet": ("bông tuyết",), "bot khi": ("bọt khí",),
    "bot nuoc": ("bọt nước",), "bui bam": ("bụi bặm",), "bun dat": ("bùn đất",),
    "buoi toi": ("buổi tối",), "can bep": ("căn bếp",),
    "canh sat": ("cảnh sát",), "cap doi": ("cặp đôi",), "cau hon": ("cầu hôn",),
    "cay coi": ("cây cối",), "cay du": ("cây dù",), "cha me": ("cha mẹ",),
    "chao ran": ("chảo rán",), "chay mau": ("chảy máu",),
    "chia tay": ("chia tay",), "chien thang": ("chiến thắng",),
    "chien tranh": ("chiến tranh",), "chim hot": ("chim hót",),
    "choi game": ("chơi game",), "chu re": ("chú rể",),
    "chuc mung": ("chúc mừng",), "co dau": ("cô dâu",), "co dien": ("cổ điển",),
    "co don": ("cô đơn",), "con bao": ("cơn bão",), "con mua": ("cơn mưa",),
    "con thuyen": ("con thuyền",), "cong nghe": ("công nghệ",),
    "cong thuc": ("công thức",), "cong vien": ("công viên",),
    "cu ky": ("cũ kỹ",), "cua so": ("cửa sổ",), "cun con": ("cún con",),
    "cung nhau": ("cùng nhau",), "dai duong": ("đại dương",),
    "dam chay": ("đám cháy",), "dam cuoi": ("đám cưới",),
    "dam dong": ("đám đông",), "dam tang": ("đám tang",),
    "danh nhau": ("đánh nhau",), "dat tien": ("đắt tiền",),
    "dau bep": ("đầu bếp",), "dau tu": ("đầu tư",), "den duong": ("đèn đường",),
    "den giang sinh": ("đèn giáng sinh",), "den long": ("đèn lồng",),
    "den neon": ("đèn neon",), "den trang": ("đen trắng",),
    "dong xu": ("đồng xu",), "dot lua": ("đốt lửa",), "du lieu": ("dữ liệu",),
    "duoi mua": ("dưới mưa",), "duoi nuoc": ("dưới nước",),
    "duong chan troi": ("đường chân trời",), "duong rung": ("đường rừng",),
    "em be": ("em bé",), "gang tay": ("găng tay",), "ghe ron": ("ghê rợn",),
    "gia dinh": ("gia đình",), "gia ret": ("giá rét",), "gia tien": ("giá tiền",),
    "giai thuong": ("giải thưởng",), "giam gia": ("giảm giá",),
    "giau co": ("giàu có",), "gio lanh": ("gió lạnh",), "gio thoi": ("gió thổi",),
    "giua trua": ("giữa trưa",), "hai huoc": ("hài hước",), "han xi": ("hàn xì",),
    "hien dai": ("hiện đại",), "hoa nhac": ("hòa nhạc", "hoà nhạc"),
    "hoang hon": ("hoàng hôn",), "hoang tan": ("hoang tàn",),
    "hoi tuong": ("hồi tưởng",), "hon nhau": ("hôn nhau",),
    "khai truong": ("khai trương",), "khan quang": ("khăn quàng",),
    "kho bau": ("kho báu",), "khoc": ("khóc",), "khoi lua": ("khói lửa",),
    "khui hop": ("khui hộp",), "kim cuong": ("kim cương",),
    "kinh di": ("kinh dị",), "kinh doanh": ("kinh doanh",),
    "ky niem": ("kỷ niệm",), "ky uc": ("ký ức",),
    "la roi": ("lá rơi",), "la thu": ("lá thư",), "la vang": ("lá vàng",),
    "lan bien": ("lặn biển",), "lanh": ("lạnh",), "lantern": ("lantern",),
    "lap lanh": ("lấp lánh",), "lap trinh": ("lập trình",),
    "len den": ("lên đèn",), "lich su": ("lịch sử",), "linh hon": ("linh hồn",),
    "lo nuong": ("lò nướng",), "lo suoi": ("lò sưởi",),
    "long lay": ("lộng lẫy",), "lua chay": ("lửa cháy",),
    "lua trai": ("lửa trại",), "lung linh": ("lung linh",),
    "luong thang": ("lương tháng",), "ma am": ("ma ám",),
    "ma quy": ("ma quỷ",), "man hinh": ("màn hình",),
    "man hinh may tinh": ("màn hình máy tính",), "mat nuoc": ("mặt nước",),
    "may anh phim": ("máy ảnh phim",), "may den": ("mây đen",),
    "may tinh": ("máy tính",), "me con": ("mẹ con",), "meo con": ("mèo con",),
    "mo mang": ("mơ màng",), "mot minh": ("một mình",), "mua dong": ("mùa đông",),
    "mua rao": ("mưa rào",), "mua sam": ("mua sắm",), "mua thu": ("mùa thu",),
    "nam mo": ("nấm mồ",), "nam moi": ("năm mới",), "nang chieu": ("nắng chiều",),
    "nang gat": ("nắng gắt",), "nau an": ("nấu ăn",), "ngan hang": ("ngân hàng",),
    "ngay truoc": ("ngày trước",), "ngay xua": ("ngày xưa",),
    "nghia trang": ("nghĩa trang",), "ngoai troi": ("ngoài trời",),
    "ngoi sao": ("ngôi sao",), "ngon lua": ("ngọn lửa",),
    "nguoc sang": ("ngược sáng",), "nhan cuoi": ("nhẫn cưới",),
    "nhat ky": ("nhật ký",), "nhay mua": ("nhảy múa",),
    "noi buon": ("nỗi buồn",), "nong thon": ("nông thôn",),
    "nua dem": ("nửa đêm",), "nui lua": ("núi lửa",), "nui tuyet": ("núi tuyết",),
    "nuoc bien": ("nước biển",), "nuoc mat": ("nước mắt",),
    "om nhau": ("ôm nhau",), "ong noi": ("ông nội",), "pha le": ("pha lê",),
    "phan mem": ("phần mềm",), "phao hoa": ("pháo hoa",),
    "phep thuat": ("phép thuật",), "phim cu": ("phim cũ",),
    "phong toi": ("phòng tối",), "phu tuyet": ("phủ tuyết",),
    "qua khu": ("quá khứ",), "qua tang": ("quà tặng",),
    "quay man hinh": ("quay màn hình",), "ret": ("rét",),
    "rong lua": ("rồng lửa",), "rung cay": ("rừng cây",), "sa mac": ("sa mạc",),
    "san ho": ("san hô",), "san khau": ("sân khấu",), "sang trong": ("sang trọng",),
    "sinh nhat": ("sinh nhật",), "song bien": ("sóng biển",),
    "sung dan": ("súng đạn",), "suong mu": ("sương mù",), "tai nan": ("tai nạn",),
    "tam biet": ("tạm biệt",), "tan the": ("tận thế",), "tan vo": ("tan vỡ",),
    "tap gym": ("tập gym",), "thac nuoc": ("thác nước",),
    "than hong": ("than hồng",), "thi dau": ("thi đấu",),
    "thien nhien": ("thiên nhiên",), "tia lua": ("tia lửa",), "tiec": ("tiệc",),
    "tien giay": ("tiền giấy",), "tien mat": ("tiền mặt",),
    "tinh yeu": ("tình yêu",), "to tien": ("tổ tiên",), "toi tam": ("tối tăm",),
    "tot nghiep": ("tốt nghiệp",), "trang diem": ("trang điểm",),
    "trang suc": ("trang sức",), "tre so sinh": ("trẻ sơ sinh",),
    "tri tue nhan tao": ("trí tuệ nhân tạo",), "tro tan": ("tro tàn",),
    "troi lanh": ("trời lạnh",), "troi mua": ("trời mưa",),
    "troi toi": ("trời tối",), "trong tai": ("trọng tài",),
    "trong vang": ("trống vắng",), "trung so": ("trúng số",),
    "truot tuyet": ("trượt tuyết",), "tu lieu": ("tư liệu",),
    "tuong lai": ("tương lai",), "tuyet roi": ("tuyết rơi",),
    "tuyet trang": ("tuyết trắng",), "ty phu": ("tỷ phú",),
    "vang mieng": ("vàng miếng",), "vet mau": ("vết máu",),
    "vi tien": ("ví tiền",), "vo dich": ("vô địch",), "vo tay": ("vỗ tay",),
    "vu no": ("vụ nổ",), "vui": ("vui",), "vuon cay": ("vườn cây",),
    "xo so": ("xổ số",), "yen binh": ("yên bình",), "yeu thuong": ("yêu thương",),
}

def _bien(tu: str) -> re.Pattern:
    """Từ khoá -> mẫu dò có RÀNG BUỘC BIÊN TỪ, trên text **ĐÃ BỎ DẤU**.

    Bắt buộc, không phải cho đẹp: dò chuỗi con thì `ice` khớp "pol**ice**",
    "serv**ice**", "n**ice**" -> tuyết rơi trên video cảnh sát. Đã thử trên
    chính bảng dưới đây: bỏ biên từ là 3/6 ca nội dung khớp SAI.
    """
    return re.compile(r"(?<![a-z0-9])" + re.escape(_khong_dau(tu))
                      + r"(?![a-z0-9])")


def _bien_dau(tu: str) -> list:
    """Từ khoá -> các mẫu dò trên text **CÒN NGUYÊN DẤU** (đường LỜI THOẠI).

    Từ khoá tiếng Việt lấy dạng có dấu ở `_DAU_VN`; từ khoá tiếng Anh/Nhật/Hàn
    dò nguyên văn. Biên từ tính theo `_CHU` (kể cả chữ Việt có dấu) — CJK không
    nằm trong lớp đó nên "雪" vẫn khớp giữa "大雪が", đúng ý (tiếng Nhật/Hàn
    không có dấu cách giữa từ).
    """
    return [re.compile(f"(?<![{_CHU}])" + re.escape(x) + f"(?![{_CHU}])")
            for x in _DAU_VN.get(_khong_dau(tu), (_ha(tu),))]


def _dk(l: Luat) -> Luat:
    l._re_manh = [_bien(t) for t in l.manh]
    l._re_phu = [_bien(t) for t in l.phu]
    l._re_cam = [_bien(t) for t in l.cam]
    l._re_bien = [(k, [_bien(t) for t in (goi or ())])
                  for k, goi in (l.bien or ((l.khoa, ()),))]
    l._rd_manh = [_bien_dau(t) for t in l.manh]
    l._rd_phu = [_bien_dau(t) for t in l.phu]
    l._rd_cam = [_bien_dau(t) for t in l.cam]
    l._rd_bien = [(k, [_bien_dau(t) for t in (goi or ())])
                  for k, goi in (l.bien or ((l.khoa, ()),))]
    LUAT[l.khoa] = l
    return l


def _co(t: str, mau: list) -> bool:
    """`mau` = danh sách MẪU (mỗi từ khoá 1 mẫu) HOẶC danh sách NHÓM mẫu (mỗi
    từ khoá nhiều cách viết có dấu). Khớp bất kỳ = True."""
    for r in mau:
        if isinstance(r, list):
            if any(x.search(t) for x in r):
                return True
        elif r.search(t):
            return True
    return False


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

# ================== TỪ KHOÁ TIẾNG NHẬT / TIẾNG HÀN ==================
# Chỉ có tác dụng ở **đường LỜI THOẠI** (mô tả digest luôn là tiếng Anh). Anh
# Hùng chạy cả kênh Nhật lẫn kênh Hàn, mà bảng trên chỉ có Anh + Việt — với
# video Nhật/Hàn thì đường lời KHÔNG có lấy một bằng chứng nào.
#
# **LUẬT SẮT CỦA NHÓM NÀY — CJK KHÔNG CÓ DẤU CÁCH:** biên từ `(?<![a-z0-9…])`
# không chặn được gì giữa chữ Hán/Kana/Hangul, nên từ khoá NGẮN khớp BÊN TRONG
# từ dài. Cùng họ với bẫy bỏ dấu tiếng Việt, chỉ khác cơ chế:
#     `火`  khớp trong **火曜日** (thứ Ba)        -> lửa cháy trên video lịch
#     `不`/`불` khớp trong **불편/불가능** (bất tiện) -> lửa cháy trên video than phiền
#     `눈`  tiếng Hàn vừa là **tuyết** vừa là **mắt** -> KHÔNG dùng; chỉ dùng
#           `눈사람`(người tuyết) · `눈보라`(bão tuyết) · `함박눈`(tuyết bông)
#     `비`  vừa là **mưa** vừa là tiền tố so sánh -> chỉ dùng `비가 오` · `소나기`
# Vì vậy: **tối thiểu 2 ký tự và phải là từ khó nhầm**. Cảnh nào không tìm được
# từ đủ chắc thì để trống — thà không có còn hơn thêm bừa.
_CJK: dict = {
    "tuyet_roi": {
        "manh": ("雪が降", "大雪", "吹雪", "雪だるま", "雪景色", "スキー場",
                 "スノーボード", "눈사람", "눈보라", "함박눈", "폭설", "스키장",
                 "스노보드"),
        "phu": ("寒い", "真冬", "マフラー", "手袋", "추워", "겨울철", "목도리",
                "장갑"),
        "cam": ("料理", "キッチン", "台所", "オーブン", "レシピ", "フライパン",
                "砂漠", "海水浴", "プール", "요리", "주방", "부엌", "오븐",
                "레시피", "프라이팬", "사막", "해변", "수영장")},
    "trai_tim": {
        "manh": ("結婚式", "花嫁", "新郎", "キス", "抱きしめ", "カップル",
                 "赤ちゃん", "新生児", "子犬", "子猫", "プロポーズ", "婚約",
                 "결혼식", "신부", "신랑", "키스", "커플", "아기", "신생아",
                 "강아지", "고양이", "프러포즈", "약혼"),
        "phu": ("家族", "お母さん", "お父さん", "プレゼント", "花束", "가족",
                "엄마", "아빠", "선물", "꽃다발"),
        "cam": ("喧嘩", "殴っ", "出血", "拳銃", "事故", "葬式", "戦争", "警察",
                "試合", "審判", "ゴール", "싸움", "사고", "장례식", "전쟁",
                "경찰", "경기", "심판", "골키퍼")},
    "confetti": {
        "manh": ("誕生日", "ケーキ", "パーティー", "お祝い", "卒業", "優勝",
                 "表彰", "記念日", "생일", "케이크", "파티", "축하", "졸업",
                 "우승", "챔피언", "시상", "새해"),
        "phu": ("拍手", "風船", "乾杯", "박수", "풍선", "건배"),
        "cam": ("葬式", "事故", "病院", "戦争", "デモ", "喧嘩", "출혈",
                "장례식", "사고", "병원", "전쟁", "시위", "싸움")},
    "mua_roi": {
        "manh": ("雨が降", "大雨", "土砂降り", "傘を", "台風", "梅雨", "涙が",
                 "お別れ", "お墓", "비가 오", "소나기", "우산", "태풍", "장맛비",
                 "눈물", "이별", "무덤"),
        "phu": ("寂しい", "ひとりぼっち", "曇り空", "외로", "쓸쓸"),
        "cam": ("誕生日", "パーティー", "結婚式", "砂漠", "料理", "생일",
                "파티", "결혼식", "사막", "요리")},
    "dom_bokeh": {
        "manh": ("夜景", "ネオン", "街灯", "コンサート", "ステージ", "花火",
                 "提灯", "ろうそく", "イルミネーション", "야경", "네온",
                 "가로등", "콘서트", "무대 조명", "불꽃놀이", "등불", "촛불"),
        "phu": ("真夜中", "夕暮れ", "한밤중", "저녁 무렵"),
        "cam": ("真昼", "日中", "海水浴", "한낮", "대낮", "해변")},
    "tan_lua": {
        "manh": ("炎が", "火事", "焚き火", "キャンプファイヤー", "爆発", "暖炉",
                 "溶接", "火山", "たき火", "화염", "화재", "모닥불", "폭발",
                 "벽난로", "용접", "화산"),
        "phu": ("煙が", "火の粉", "연기가", "불똥"),
        "cam": ("大雪", "雨が降", "水中", "病院", "赤ちゃん", "폭설", "수중",
                "병원", "아기")},
    "la_roi": {
        "manh": ("紅葉", "落ち葉", "秋の", "もみじ", "단풍", "낙엽", "가을"),
        "phu": ("自然", "屋外", "公園", "자연", "야외", "공원")},
    "duoi_nuoc": {
        "manh": ("水中", "ダイビング", "シュノーケリング", "水族館", "熱帯魚",
                 "プールで", "滝が", "サンゴ", "수중", "다이빙", "스노클링",
                 "수족관", "열대어", "폭포", "산호"),
        "phu": ("海の中", "波が", "泡が", "바닷속", "파도", "물거품"),
        "cam": ("砂漠", "火事", "料理", "大雪", "사막", "화재", "요리", "폭설")},
    "ma_quai": {
        "manh": ("ハロウィン", "幽霊", "心霊", "ホラー", "怖すぎ", "お化け",
                 "かぼちゃ", "墓地", "ゾンビ", "魔女", "핼러윈", "유령", "심령",
                 "공포", "무서워", "귀신", "묘지", "좀비", "마녀"),
        "phu": ("霧が", "真夜中", "廃墟", "안개", "한밤중", "폐허"),
        "cam": ("誕生日", "結婚式", "赤ちゃん", "料理", "海水浴", "생일",
                "결혼식", "아기", "요리", "해변")},
    "tien_bac": {
        "manh": ("現金", "お札", "財布", "宝くじ", "給料日", "金塊", "宝物",
                 "億万長者", "현금", "지폐", "지갑", "복권", "월급날", "금괴",
                 "보물", "억만장자"),
        "phu": ("買い物", "値段", "銀行", "投資", "쇼핑", "가격", "은행",
                "투자"),
        "cam": ("葬式", "病院", "戦争", "事故", "장례식", "병원", "전쟁",
                "사고")},
    "cong_nghe": {
        "manh": ("パソコン", "ノートパソコン", "プログラミング", "ソフトウェア",
                 "ロボット", "人工知能", "ホログラム", "サーバー", "テレビゲーム",
                 "컴퓨터", "노트북", "프로그래밍", "소프트웨어", "로봇",
                 "인공지능", "홀로그램", "서버실", "비디오 게임"),
        "phu": ("キーボード", "データ", "技術", "키보드", "데이터", "기술"),
        "cam": ("自然", "森の中", "海水浴", "料理", "赤ちゃん", "結婚式",
                "자연", "숲속", "해변", "요리", "아기", "결혼식")},
    "lap_lanh": {
        "manh": ("キラキラ", "ダイヤモンド", "アクセサリー", "指輪", "メイク",
                 "魔法", "変身", "お姫様", "반짝반짝", "다이아몬드", "액세서리",
                 "반지", "메이크업", "마법", "변신", "공주"),
        "phu": ("豪華", "びっくり", "화려", "깜짝"),
        "cam": ("喧嘩", "出血", "事故", "葬式", "戦争", "싸움", "사고",
                "장례식", "전쟁")},
    "bui_phim": {
        "manh": ("白黒", "記録映像", "昔の映画", "歴史的", "博物館", "ご先祖",
                 "흑백", "기록 영상", "옛날 영화", "역사적", "박물관", "조상"),
        "phu": ("おばあちゃん", "おじいちゃん", "手紙", "日記", "할머니",
                "할아버지", "편지", "일기"),
        "cam": ("最新", "未来的", "ゲーム実況", "開封", "최신", "미래적",
                "게임 방송", "언박싱")},
    "tia_sang": {
        "manh": ("夕焼け", "朝焼け", "日の出", "日の入り", "回想", "レトロ",
                 "フィルムカメラ", "昔の写真", "노을", "일출", "일몰", "회상",
                 "레트로", "필름 카메라", "옛날 사진"),
        "phu": ("思い出", "逆光", "추억", "역광"),
        "cam": ("画面録画", "表計算", "ホラー", "화면 녹화", "스프레드시트",
                "공포")},
}
for _k, _b in _CJK.items():
    _l = LUAT[_k]
    _l.manh = tuple(_l.manh) + tuple(_b.get("manh", ()))
    _l.phu = tuple(_l.phu) + tuple(_b.get("phu", ()))
    _l.cam = tuple(_l.cam) + tuple(_b.get("cam", ()))
    _dk(_l)      # dựng lại CẢ HAI bộ mẫu (bỏ dấu + có dấu)


# -------------------------------------------------------------- CHẤM ĐIỂM
def _dem_moc(digest: list, mau: list, mau_dau: list) -> tuple[int, list]:
    """Đếm SỐ MỐC digest có ít nhất 1 từ khoá khớp -> (số mốc, [mốc đã khớp]).

    Đếm theo MỐC chứ không theo số lần chữ xuất hiện: một mô tả nhắc "snow"
    ba lần vẫn chỉ là MỘT khung hình, không phải bằng chứng mạnh gấp ba.

    Mốc gắn cờ `loi=True` (do `digest_tu_loi` sinh, `desc` là CÂU NÓI THẬT) thì
    dò bằng bộ mẫu **CÓ DẤU**; mốc xem hình (`desc` là mô tả tiếng Anh của model)
    dò bằng bộ mẫu bỏ dấu như cũ. Nhờ vậy một danh sách TRỘN cả hai nguồn vẫn
    chấm đúng từng mốc theo đúng thứ tiếng của nó.
    """
    ra = []
    for d in digest or []:
        if d.get("loi"):
            t, m = _ha(d.get("desc", "")), mau_dau
        else:
            t, m = _khong_dau(d.get("desc", "")), mau
        if _co(t, m):
            ra.append(d)
    return len(ra), ra


def _dem_tu(loi: str, mau: list) -> int:
    """Số từ khoá KHÁC NHAU khớp trong lời (không phải tổng số lần).

    `loi` LUÔN là text CÒN DẤU và `mau` LUÔN là bộ mẫu có dấu — lời thoại là
    chữ thật của video, bỏ dấu ở đây là mở đúng 9 cái bẫy đã đo (xem `_DAU_VN`).
    """
    return sum(1 for r in mau if any(x.search(loi) for x in r))


def _diem(l: Luat, digest: list, loi: str) -> Optional[dict]:
    """Điểm thô + bằng chứng của 1 luật. `None` = BỊ CẤM (thấy từ khoá cấm).

    Thang: mốc digest MẠNH 2,0 (trần 2 mốc) · mốc digest PHỤ 0,7 (trần 3) ·
    từ MẠNH trong lời 1,5 (trần 2) · từ PHỤ trong lời 0,5 (trần 2).
    Trần riêng của nhóm PHỤ = 0,7*3 + 0,5*2 = 3,1 điểm thô = 0,52 < NGUONG_TIN
    -> **bối cảnh một mình KHÔNG BAO GIỜ đủ**, đúng chủ ý.

    `loi` là text CÒN DẤU (xem `_ha`).
    """
    if _dem_tu(loi, l._rd_cam):
        return None
    n_cam_hinh, _ = _dem_moc(digest, l._re_cam, l._rd_cam)
    if n_cam_hinh:
        return None
    dm, moc_manh = _dem_moc(digest, l._re_manh, l._rd_manh)
    dp, moc_phu = _dem_moc(digest, l._re_phu, l._rd_phu)
    tm = _dem_tu(loi, l._rd_manh)
    tp = _dem_tu(loi, l._rd_phu)
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
    _pd = dict(l._rd_bien)
    ung = [(k, ps, _pd.get(k) or []) for k, ps in l._re_bien
           if k in dung and k in kho]
    if not ung:
        return "", "không biến thể nào của cảnh này dùng được trên máy này"
    diem = []
    for k, ps, pd in ung:
        n = (2 * _dem_moc(digest, ps, pd)[0] + _dem_tu(loi, pd)) if ps else 0
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
        # Không CÒN là đường ra hay gặp nhất: từ v2.21.0 caller tự dựng mốc từ
        # LỜI THOẠI khi không có vision_digest (xem `digest_tu_loi`). Tới đây
        # nghĩa là không có CẢ HAI — video không lời và không xem hình.
        return [], ("không có vision_digest và cũng không có lời thoại nào cho "
                    "clip này -> bỏ qua nhóm lớp phủ (không bật AI xem hình "
                    "chỉ để chọn hiệu ứng)")
    dung = set(co_the_dung if co_the_dung is not None else HU.dung_duoc())
    loi_n = _ha(loi or "")
    # NGUỒN của các mốc, chỉ để VIẾT NHẬT KÝ cho đúng chữ: đọc "2 mốc hình mạnh"
    # trong khi thật ra là 2 CÂU NÓI thì lần sau không ai tra lại được.
    _n_loi = sum(1 for d in digest or [] if d.get("loi"))
    _mn = "mốc lời" if _n_loi and _n_loi == len(digest) else "mốc hình"
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
        return [], (f"không {_mn} nào và không từ nào trong lời khớp bảng "
                    "cảnh -> KHÔNG thêm lớp phủ")
    if nhat["tin"] < NGUONG_TIN:
        return [], (f"kiểu hợp nhất là {nhat['khoa']} nhưng độ tự tin chỉ "
                    f"{_so(nhat['tin'])} < ngưỡng {_so(NGUONG_TIN)} "
                    f"({nhat['dm']} {_mn} mạnh · {nhat['dp']} mốc phụ · "
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
              f"nguồn {'LỜI THOẠI' if _mn == 'mốc lời' else 'XEM HÌNH'} · "
              f"{ly_do_bien} · KHỚP NỘI DUNG — tự tin "
              f"{_so(nhat['tin'])}/1,00 (ngưỡng {_so(NGUONG_TIN)}): "
              f"{nhat['dm']} {_mn} khớp mạnh, {nhat['dp']} mốc phụ, "
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
                x = {"t": round((acc + (t - s)) / max(0.01, vspeed), 3),
                     "desc": str(d.get("desc") or ""),
                     "act": int(d.get("act", 0) or 0)}
                if d.get("loi"):
                    # cờ NGUỒN phải đi theo mốc: `_dem_moc` chọn bộ mẫu CÓ DẤU
                    # hay bỏ dấu theo đúng cờ này. Rơi cờ ở đây là lời thoại
                    # tiếng Việt bị dò bằng bảng bỏ dấu -> mở lại 9 cái bẫy.
                    x["loi"] = True
                ra.append(x)
                break
            acc += (e - s)
    ra.sort(key=lambda d: d["t"])
    return ra


def digest_tu_loi(transcript: dict, segs: list, vspeed: float = 1.0,
                  tran: int = 400) -> list:
    """ĐOÁN CẢNH BẰNG **LỜI THOẠI** — mỗi CÂU chép lời thành 1 mốc. Hàm THUẦN.

    VÌ SAO CÓ (anh Hùng 09/08/2026): anh cắt clip trên v2.20.0 và **không thấy
    tuyết/trái tim nào**. Nhật ký `lop_phu_*.log` ghi *"không có vision_digest
    cho clip này -> bỏ qua nhóm lớp phủ"*. Đúng thiết kế, nhưng `VISION_CUT` mặc
    định TẮT nên **46 kiểu lớp phủ gần như không bao giờ xuất hiện**.

    Bản chép lời thì LÚC NÀO CŨNG CÓ SẴN (mọi video đều qua bước chép lời để
    đốt phụ đề) -> đường này **không tốn thêm một giây nào, không thêm một lượt
    LLM nào**. Xem hình vẫn ƯU TIÊN khi có: caller chỉ gọi hàm này khi
    `vision_digest` rỗng.

    Trả ĐÚNG cấu trúc mốc digest `[{'t', 'desc', 'act', 'loi': True}]` trên
    timeline **ĐẦU RA** — nhờ vậy `chon_lop_phu` không phải biết gì về nguồn,
    và mọi chốt chặn (`NGUONG_TIN` 0,55 · nhóm PHỤ trần 0,52 · danh sách CẤM ·
    hai họ sát nhau = bỏ) áp Y NGUYÊN.

    Cờ `loi=True` là thứ bắt `_dem_moc` dò bằng bộ mẫu **CÓ DẤU** — bắt buộc,
    xem `_DAU_VN` (9 bẫy đã đo).

    `act` để 5 ở MỌI mốc, cố ý: `act` chỉ dùng để chọn CHỖ ĐẶT lớp phủ, và
    `sorted` của Python ổn định -> đặt vào mốc khớp SỚM NHẤT. Bịa ra "độ sôi
    động" từ chữ là đoán bừa, mà đoán bừa là thứ nhóm này tồn tại để tránh.
    """
    ss = [(float(s), float(e)) for s, e in (segs or []) if float(e) > float(s)]
    if not ss:
        return []
    tho = []
    for c in (transcript or {}).get("segments") or []:
        try:
            a = float(c.get("start"))
        except (TypeError, ValueError):
            continue          # câu KHÔNG MỐC -> bỏ (không biết rơi vào đoạn nào)
        t = str(c.get("text") or "").strip()
        if t:
            tho.append({"t": a, "desc": t, "act": 5, "loi": True})
        if len(tho) >= tran:
            break
    return loc_digest_theo_doan(tho, ss, vspeed)
