# -*- coding: utf-8 -*-
"""BỘ CÂU THỬ cho phép đo "MÁY ĐỌC SAI CHỮ NƯỚC NGOÀI / TÊN RIÊNG".

Anh Hùng 17/08/2026: *"ví dụ như chọn tiếng Việt, mấy chữ tiếng Anh hay tên
riêng hay tên gì đó nó đọc toàn bị lỗi ở cái đó, với mấy cái kiểu khác nữa nó
bị lỗi đọc, bạn kiểm tra xem mấy phần tiếng khác có bị lỗi thế không"*.

Để RIÊNG một file vì cả phép ĐO (`_do_doc_sai.py`) lẫn CỔNG hồi quy đều phải
dùng **CÙNG MỘT bộ câu** — chép corpus sang hai nơi là hai nơi trôi khác nhau
rồi so số của hai bộ khác nhau.

CẤU TRÚC: `CORPUS[mã_ngôn_ngữ] = [(loại, câu, [token phải đọc ra được]), ...]`

`token` là thứ NGƯỜI NGHE phải nhận ra. Chấm theo TOKEN chứ không theo cả câu:
cả câu sai một chữ thì tỉ lệ ra 100% sai, không chỉ được chỗ nào hỏng.

LOẠI (đúng 6 loại anh Hùng nêu, cộng 1 loại ĐỐI CHỨNG):
  * `cau_thuong`  — câu bản ngữ TRƠN, không có gì lạ. **ĐỐI CHỨNG BẮT BUỘC**:
    phép đo này chép ngược bằng máy nghe, mà máy nghe cũng sai. Không có SÀN
    này thì mọi con số ở dưới là "lỗi của máy đọc CỘNG lỗi của máy nghe" và
    không tách ra được. Bài học `_do_dich_soat` (cột đối chứng "câu KHÔNG bị
    đổi chữ").
  * `ten_rieng`   — tên riêng nước ngoài trong câu
  * `viet_tat`    — từ viết tắt
  * `so_ngay`     — số và ngày
  * `don_vi`      — đơn vị / ký hiệu
  * `ban_dia`     — tên riêng BẢN ĐỊA (tiếng Việt có dấu · địa danh Trung/Nhật)
"""
from __future__ import annotations

#: Nhãn tiếng Việt của từng loại — dùng chung cho bảng kết quả.
NHAN_LOAI = {
    "cau_thuong": "Câu thường (đối chứng)",
    "ten_rieng": "Tên riêng nước ngoài",
    "viet_tat": "Từ viết tắt",
    "so_ngay": "Số và ngày",
    "don_vi": "Đơn vị / ký hiệu",
    "ban_dia": "Tên riêng bản địa",
}
THU_TU_LOAI = ("cau_thuong", "ten_rieng", "viet_tat", "so_ngay", "don_vi",
               "ban_dia")

NHAN_NN = {"vi": "Việt", "en": "Anh", "zh": "Trung", "ja": "Nhật"}

CORPUS: dict[str, list[tuple[str, str, list[str]]]] = {
    # ================================================================
    "vi": [
        ("cau_thuong", "Hôm nay trời rất đẹp, chúng ta cùng đi dạo nhé.",
         ["trời rất đẹp", "đi dạo"]),
        ("cau_thuong", "Anh ấy mở cửa rồi bước vào trong căn phòng tối.",
         ["mở cửa", "căn phòng tối"]),
        ("cau_thuong", "Cô gái mỉm cười và quay lưng bỏ đi không nói gì.",
         ["mỉm cười", "quay lưng"]),
        ("cau_thuong", "Chúng tôi đã chờ ở đó suốt cả buổi chiều hôm qua.",
         ["chờ ở đó", "buổi chiều"]),

        ("ten_rieng", "Bộ phim này đang đứng đầu bảng xếp hạng Netflix.",
         ["Netflix"]),
        ("ten_rieng", "Marvel vừa công bố phần phim mới nhất của họ.",
         ["Marvel"]),
        ("ten_rieng", "Cô ấy quay video này bằng chiếc iPhone đời cũ.",
         ["iPhone"]),
        ("ten_rieng", "Elon Musk lại gây tranh cãi trên mạng xã hội.",
         ["Elon Musk"]),
        ("ten_rieng", "Đoạn clip đó nổi rần rần trên TikTok tuần trước.",
         ["TikTok"]),
        ("ten_rieng", "Kênh YouTube của anh ấy có hơn một triệu người theo dõi.",
         ["YouTube"]),

        ("viet_tat", "Công nghệ AI đang thay đổi cách chúng ta làm việc.",
         ["AI"]),
        ("viet_tat", "Vị CEO này mới nhậm chức được đúng ba tháng.", ["CEO"]),
        ("viet_tat", "GDP của cả nước năm nay tăng khá mạnh.", ["GDP"]),
        ("viet_tat", "MV mới của cô ấy đạt triệu view chỉ sau một ngày.",
         ["MV", "view"]),
        ("viet_tat", "Bài OST của phim này rất hay, ai nghe cũng thích.",
         ["OST"]),
        ("viet_tat", "Anh nhớ cắm cái USB vào máy giúp tôi nhé.", ["USB"]),

        ("so_ngay", "Đến năm 2026 thì mọi chuyện đã khác hẳn rồi.", ["2026"]),
        ("so_ngay", "Bộ phim thu về 1.500.000 đô la ngay tuần đầu.",
         ["1.500.000"]),
        ("so_ngay", "Chúng tôi hẹn gặp nhau vào ngày 15/08 năm ngoái.",
         ["15/08"]),
        ("so_ngay", "Thị trường này được định giá khoảng 3,5 tỷ đồng.",
         ["3,5 tỷ"]),
        ("so_ngay", "Có tới 90% khán giả cho điểm rất cao.", ["90%"]),
        ("so_ngay", "Chuyện đó xảy ra từ năm 1999, lâu lắm rồi.", ["1999"]),

        ("don_vi", "Chiếc xe này chạy tới 250 km/h trên đường cao tốc.",
         ["250 km/h"]),
        ("don_vi", "Nhiệt độ ngoài trời lúc đó là 38°C, nóng kinh khủng.",
         ["38°C"]),
        ("don_vi", "Anh ấy trả 500$ cho một buổi chụp hình.", ["500$"]),
        ("don_vi", "Con cá nặng gần 12 kg, to hơn cả cái bàn.", ["12 kg"]),
        ("don_vi", "Căn hộ rộng 85 m2 nằm ngay trung tâm thành phố.",
         ["85 m2"]),
        ("don_vi", "Chỉ 30% số người được hỏi đồng ý với ý kiến đó.",
         ["30%"]),

        ("ban_dia", "Vua Nguyễn Huệ đã đánh tan quân giặc chỉ trong năm ngày.",
         ["Nguyễn Huệ"]),
        ("ban_dia", "Gia đình anh ấy chuyển lên Đắk Lắk sống từ lâu rồi.",
         ["Đắk Lắk"]),
        ("ban_dia", "Chị Quỳnh Như vừa mở một quán cà phê nhỏ ở Huế.",
         ["Quỳnh Như", "Huế"]),
        ("ban_dia", "Chuyến tàu đi Quy Nhơn khởi hành lúc sáng sớm.",
         ["Quy Nhơn"]),
        ("ban_dia", "Ông Trần Hưng Đạo được cả nước kính trọng.",
         ["Trần Hưng Đạo"]),
        ("ban_dia", "Món bún bò Huế ở Nghệ An cũng ngon không kém.",
         ["Nghệ An"]),
    ],
    # ================================================================
    "en": [
        ("cau_thuong", "The weather is beautiful today, let us go for a walk.",
         ["beautiful today", "for a walk"]),
        ("cau_thuong", "He opened the door and stepped into the dark room.",
         ["opened the door", "dark room"]),
        ("cau_thuong", "She smiled at him and then walked away without a word.",
         ["smiled at him", "without a word"]),
        ("cau_thuong", "We had been waiting there for the entire afternoon.",
         ["waiting there", "entire afternoon"]),

        ("ten_rieng", "This movie is topping the charts on Netflix right now.",
         ["Netflix"]),
        ("ten_rieng", "Marvel just announced their newest film in the series.",
         ["Marvel"]),
        ("ten_rieng", "She shot this whole video on an old iPhone.",
         ["iPhone"]),
        ("ten_rieng", "Elon Musk stirred up another argument online.",
         ["Elon Musk"]),
        ("ten_rieng", "That clip went completely viral on TikTok last week.",
         ["TikTok"]),
        ("ten_rieng", "His YouTube channel has over a million subscribers.",
         ["YouTube"]),

        ("viet_tat", "AI technology is changing the way we all work.", ["AI"]),
        ("viet_tat", "The new CEO has only been in charge for three months.",
         ["CEO"]),
        ("viet_tat", "The GDP of the whole country grew quite strongly.",
         ["GDP"]),
        ("viet_tat", "Her new MV hit a million views in a single day.",
         ["MV"]),
        ("viet_tat", "The OST of this film is wonderful, everyone loves it.",
         ["OST"]),
        ("viet_tat", "Please plug the USB into the machine for me.", ["USB"]),

        ("so_ngay", "By the year 2026 everything had completely changed.",
         ["2026"]),
        ("so_ngay", "The film pulled in 1,500,000 dollars in its first week.",
         ["1,500,000"]),
        ("so_ngay", "We agreed to meet on August 15th of last year.",
         ["August 15"]),
        ("so_ngay", "This market is valued at around 3.5 billion dollars.",
         ["3.5 billion"]),
        ("so_ngay", "As many as 90% of the audience rated it very highly.",
         ["90%"]),
        ("so_ngay", "That happened back in 1999, such a long time ago.",
         ["1999"]),

        ("don_vi", "This car goes up to 250 km/h on the highway.",
         ["250 km/h"]),
        ("don_vi", "The temperature outside was 38°C, absolutely boiling.",
         ["38°C"]),
        ("don_vi", "He paid 500$ for a single photo session.", ["500$"]),
        ("don_vi", "The fish weighed almost 12 kg, bigger than the table.",
         ["12 kg"]),
        ("don_vi", "The apartment is 85 m2 and sits right downtown.",
         ["85 m2"]),
        ("don_vi", "Only 30% of the people asked agreed with that opinion.",
         ["30%"]),

        ("ban_dia", "The team from Massachusetts won the final round.",
         ["Massachusetts"]),
        ("ban_dia", "He grew up in Worcester before moving to the city.",
         ["Worcester"]),
        ("ban_dia", "Siobhan and Xavier arrived together that evening.",
         ["Siobhan", "Xavier"]),
        ("ban_dia", "They drove all the way through Albuquerque overnight.",
         ["Albuquerque"]),
        ("ban_dia", "Doctor Nguyen presented the findings at the conference.",
         ["Nguyen"]),
        ("ban_dia", "The old house stood in Edinburgh for two hundred years.",
         ["Edinburgh"]),
    ],
    # ================================================================
    "zh": [
        ("cau_thuong", "今天天气很好，我们一起出去走走吧。", ["天气很好", "出去走走"]),
        ("cau_thuong", "他打开门，走进了那间黑暗的房间。", ["打开门", "黑暗的房间"]),
        ("cau_thuong", "她对他笑了笑，然后一句话也没说就走了。", ["笑了笑", "走了"]),
        ("cau_thuong", "我们在那里等了整整一个下午。", ["等了", "一个下午"]),

        ("ten_rieng", "这部电影现在在 Netflix 排行榜上排第一。", ["Netflix"]),
        ("ten_rieng", "Marvel 刚刚公布了他们最新的一部电影。", ["Marvel"]),
        ("ten_rieng", "她这个视频是用一台旧的 iPhone 拍的。", ["iPhone"]),
        ("ten_rieng", "Elon Musk 又在网上引起了争议。", ["Elon Musk"]),
        ("ten_rieng", "那段视频上周在 TikTok 上火遍全网。", ["TikTok"]),
        ("ten_rieng", "他的 YouTube 频道有超过一百万订阅者。", ["YouTube"]),

        ("viet_tat", "AI 技术正在改变我们的工作方式。", ["AI"]),
        ("viet_tat", "这位新的 CEO 才上任三个月。", ["CEO"]),
        ("viet_tat", "全国的 GDP 今年增长得相当强劲。", ["GDP"]),
        ("viet_tat", "她的新 MV 一天就有了一百万播放量。", ["MV"]),
        ("viet_tat", "这部电影的 OST 非常好听，大家都喜欢。", ["OST"]),
        ("viet_tat", "请帮我把 USB 插到机器上。", ["USB"]),

        ("so_ngay", "到了 2026 年，一切都完全不一样了。", ["2026"]),
        ("so_ngay", "这部电影第一周就赚了 1,500,000 美元。", ["1,500,000"]),
        ("so_ngay", "我们约好去年 8月15日 见面。", ["8月15日"]),
        ("so_ngay", "这个市场估值大约 35 亿元。", ["35 亿"]),
        ("so_ngay", "多达 90% 的观众给了很高的评分。", ["90%"]),
        ("so_ngay", "那件事发生在 1999 年，已经很久了。", ["1999"]),

        ("don_vi", "这辆车在高速公路上能开到 250 km/h。", ["250 km/h"]),
        ("don_vi", "当时外面的气温是 38°C，热得不行。", ["38°C"]),
        ("don_vi", "他为一次拍摄付了 500$。", ["500$"]),
        ("don_vi", "这条鱼将近 12 kg，比桌子还大。", ["12 kg"]),
        ("don_vi", "这套公寓有 85 m2，就在市中心。", ["85 m2"]),
        ("don_vi", "只有 30% 的受访者同意那个观点。", ["30%"]),

        ("ban_dia", "李小龙 是很多人心目中的英雄。", ["李小龙"]),
        ("ban_dia", "他们全家搬到 乌鲁木齐 已经很多年了。", ["乌鲁木齐"]),
        ("ban_dia", "从 北京 到 上海 的高铁只要几个小时。", ["北京", "上海"]),
        ("ban_dia", "重庆 的火锅是全国最有名的。", ["重庆"]),
        ("ban_dia", "诸葛亮 的故事流传了上千年。", ["诸葛亮"]),
        ("ban_dia", "她出生在 黑龙江 的一个小村子里。", ["黑龙江"]),
    ],
    # ================================================================
    "ja": [
        ("cau_thuong", "今日はとてもいい天気なので、一緒に散歩しましょう。",
         ["いい天気", "散歩"]),
        ("cau_thuong", "彼はドアを開けて、暗い部屋の中に入りました。",
         ["ドアを開けて", "暗い部屋"]),
        ("cau_thuong", "彼女は微笑んで、何も言わずに立ち去りました。",
         ["微笑んで", "立ち去り"]),
        ("cau_thuong", "私たちはそこで午後ずっと待っていました。",
         ["そこで", "待っていました"]),

        ("ten_rieng", "この映画は今 Netflix のランキングで一位です。",
         ["Netflix"]),
        ("ten_rieng", "Marvel が最新の映画を発表したばかりです。", ["Marvel"]),
        ("ten_rieng", "彼女はこの動画を古い iPhone で撮影しました。",
         ["iPhone"]),
        ("ten_rieng", "Elon Musk がまたネットで議論を起こしました。",
         ["Elon Musk"]),
        ("ten_rieng", "あの動画は先週 TikTok で大流行しました。", ["TikTok"]),
        ("ten_rieng", "彼の YouTube チャンネルは登録者が百万人を超えています。",
         ["YouTube"]),

        ("viet_tat", "AI の技術は私たちの働き方を変えています。", ["AI"]),
        ("viet_tat", "この新しい CEO は就任してまだ三か月です。", ["CEO"]),
        ("viet_tat", "今年の国全体の GDP はかなり伸びました。", ["GDP"]),
        ("viet_tat", "彼女の新しい MV は一日で百万再生を記録しました。",
         ["MV"]),
        ("viet_tat", "この映画の OST はとても良くて、みんな好きです。",
         ["OST"]),
        ("viet_tat", "その USB を機械に挿しておいてください。", ["USB"]),

        ("so_ngay", "2026年 には、すべてがすっかり変わっていました。",
         ["2026年"]),
        ("so_ngay", "この映画は初週で 1,500,000 ドルを稼ぎました。",
         ["1,500,000"]),
        ("so_ngay", "私たちは去年の 8月15日 に会う約束をしました。",
         ["8月15日"]),
        ("so_ngay", "この市場はおよそ 35億 と評価されています。", ["35億"]),
        ("so_ngay", "観客の 90% がとても高い評価をつけました。", ["90%"]),
        ("so_ngay", "それは 1999年 の出来事で、もうずいぶん昔です。",
         ["1999年"]),

        ("don_vi", "この車は高速道路で 250 km/h まで出ます。", ["250 km/h"]),
        ("don_vi", "その時の外の気温は 38°C で、とても暑かったです。",
         ["38°C"]),
        ("don_vi", "彼は一回の撮影に 500$ 払いました。", ["500$"]),
        ("don_vi", "その魚は 12 kg 近くあって、机より大きかったです。",
         ["12 kg"]),
        ("don_vi", "そのアパートは 85 m2 で、街の中心にあります。",
         ["85 m2"]),
        ("don_vi", "質問された人のうち 30% だけが同意しました。", ["30%"]),

        ("ban_dia", "宮崎駿 の映画は世界中で愛されています。", ["宮崎駿"]),
        ("ban_dia", "彼らの家族は 名古屋 に引っ越して長いです。", ["名古屋"]),
        ("ban_dia", "東京 から 大阪 まで新幹線で数時間です。", ["東京", "大阪"]),
        ("ban_dia", "北海道 の冬はとても寒いことで有名です。", ["北海道"]),
        ("ban_dia", "織田信長 の物語は何百年も語り継がれています。",
         ["織田信長"]),
        ("ban_dia", "彼女は 鹿児島 の小さな村で生まれました。", ["鹿児島"]),
    ],
}


def dem() -> dict:
    """Số câu · số token theo ngôn ngữ — để báo cáo khỏi đếm tay."""
    ra = {}
    for nn, ds in CORPUS.items():
        ra[nn] = {"cau": len(ds), "token": sum(len(t) for _, _, t in ds)}
    return ra
