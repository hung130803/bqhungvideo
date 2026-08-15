# -*- coding: utf-8 -*-
"""BỘ BẢN DỊCH HỎNG CÓ CHỦ Ý + BỘ TỐT — để TỰ KIỂM THƯỚC `app/ai/cham_dich.py`.

Đây là phần quan trọng nhất của việc làm thước: **thước phải tự chứng minh nó
bắt được lỗi TRƯỚC KHI ai đó tin điểm nó chấm.** Repo này vừa dính đúng bẫy
"phép đo cấp chứng chỉ cho thứ vẫn hỏng" (thước dịch-ngược cho 7,85-7,97/10
trên bản dịch có `新片 -> "phim về chip"`).

Câu GỐC lấy nguyên văn từ video THẬT của anh Hùng (`_do_dich_cache.json`,
`近期热播的7部新片推荐`). Bản dịch TỐT và bản dịch HỎNG do người viết tay, mỗi
bản hỏng gắn ĐÚNG MỘT loại lỗi để đọc được thước bắt/sót loại nào.

HAI CHIỀU, THIẾU CHIỀU NÀO CŨNG VÔ DỤNG:
  · bản HỎNG -> thước phải chấm THẤP (bắt được)
  · bản TỐT  -> thước phải chấm CAO (không chỉ biết chê)

`nguoc_tai` và `may_moc` CỐ Ý giữ ĐÚNG NGHĨA — chúng chỉ sai ở chỗ không ai nói
tiếng Việt như vậy. Đó là loại lỗi thước cũ hoàn toàn mù, và cũng là loại khó
nhất cho thước mới.
"""
from __future__ import annotations

#: (mã_lỗi, câu gốc, bản dịch)
#: Mã lỗi: thuat_ngu · nguoc_tai · cut · gop · chu_han · may_moc
HONG: list[tuple[str, str, str]] = [
    # ---- SAI THUẬT NGỮ (lỗi thật của anh Hùng + cùng họ) ----
    ("thuat_ngu", "近期热播的七部新片推荐",
     "Bảy bộ phim về chip đang hot gần đây"),
    ("thuat_ngu", "主要讲述落魄拳手踏入非法决斗场",
     "Phim kể về một tay đầu bếp sa cơ bước vào sàn đấu phi pháp"),
    ("thuat_ngu", "十二位使者被迫集结与恶灵展开了一场关乎人类存亡的生死对战",
     "Hai mươi vị sứ giả buộc phải tập hợp, mở ra trận sinh tử với ác linh, "
     "quyết định sự tồn vong của loài người"),
    ("thuat_ngu", "讲述2042年一场神秘太阳风暴引发全球性灾难",
     "Kể về năm 2024, một cơn bão tuyết bí ẩn gây ra thảm hoạ toàn cầu"),
    ("thuat_ngu", "新娘在婚礼后再次陷入致命游戏",
     "Sau đám cưới, chú rể lại rơi vào một trò chơi chết người"),
    ("thuat_ngu", "影片采用阿凡达顶级班底操刀特效",
     "Phim mời ê-kíp hàng đầu của Avatar về làm nhạc phim"),

    # ---- NGƯỢC TAI (nghĩa gần đúng, nhưng không ai nói vậy) ----
    ("nguoc_tai", "主要讲述落魄拳手踏入非法决斗场",
     "Chủ yếu kể lại một võ sĩ xuống cấp giẫm vào trường quyết đấu phi pháp"),
    ("nguoc_tai", "在无规则厮杀中绝境求生",
     "Trong sự chém giết không quy tắc mà cầu sinh nơi tuyệt cảnh"),
    ("nguoc_tai", "打戏部分拳拳到肉",
     "Bộ phận hí đánh thì quyền quyền đến thịt"),
    ("nguoc_tai", "每一秒都让人心跳加速",
     "Mỗi một giây đều làm cho người ta tim đập gia tốc"),
    ("nguoc_tai", "场面真是震撼",
     "Trường diện thật là chấn động"),
    ("nguoc_tai", "她必须在绝境中求生",
     "Cô ấy tất phải ở trong tuyệt cảnh mà cầu lấy sự sinh tồn"),

    # ---- CỤT (cụt lủn như ghi chú, mất ý chính) ----
    ("cut", "主要讲述落魄拳手踏入非法决斗场", "Võ sĩ."),
    ("cut", "十二位使者被迫集结与恶灵展开了一场关乎人类存亡的生死对战",
     "Mười hai sứ giả."),
    ("cut", "影片延续了拳霸等泰式动作片的黄金传统", "Phim Thái."),
    ("cut", "讲述2042年一场神秘太阳风暴引发全球性灾难", "Bão mặt trời."),
    ("cut", "此次讲述幸存者踏上千亿新家园的艰险旅程", "Hành trình."),

    # ---- GỘP (nuốt luôn câu kế) ----
    ("gop", "场面真是震撼",
     "Cảnh phim thật sự chấn động. Tuyệt đối đáng thức đêm để xem."),
    ("gop", "喜欢看动作片的小伙伴",
     "Các bạn thích xem phim hành động. Đừng bỏ lỡ bộ phim này."),
    ("gop", "途中遭遇极端天灾",
     "Trên đường gặp phải thiên tai khắc nghiệt. Đường chạy trốn từng bước "
     "nghẹt thở."),
    ("gop", "他们不仅要解开古老预言",
     "Họ không chỉ phải giải mã lời tiên tri cổ xưa. Mà còn phải đối đầu với "
     "thế lực tà ác mạnh hơn nhiều."),

    # ---- CÒN CHỮ HÁN ----
    ("chu_han", "近期热播的七部新片推荐", "Bảy bộ 新片 đang hot gần đây"),
    ("chu_han", "第一部地下决斗室", "Phần một: 地下决斗室"),
    ("chu_han", "影片融合科幻与惊悚元素", "Phim pha trộn 科幻 với yếu tố kinh dị"),
    ("chu_han", "故事设定在未来世界", "故事设定在未来世界"),

    # ---- DỊCH MÁY WORD-BY-WORD ----
    ("may_moc", "近期热播的七部新片推荐",
     "Cận kỳ nhiệt bá đích thất bộ tân phiến thôi tiến"),
    ("may_moc", "主要讲述落魄拳手踏入非法决斗场",
     "Chủ yếu giảng thuật lạc phách quyền thủ đạp nhập phi pháp quyết đấu trường"),
    ("may_moc", "影片延续了拳霸等泰式动作片的黄金传统",
     "Ảnh phiến duyên tục liễu quyền bá đẳng thái thức động tác phiến đích "
     "hoàng kim truyền thống"),
    ("may_moc", "以未知的恐怖力量展开殊死搏斗",
     "Lấy vị tri đích khủng bố lực lượng triển khai thù tử bác đấu"),
    ("may_moc", "新娘在婚礼后再次陷入致命游戏",
     "Tân nương tại hôn lễ hậu tái thứ hãm nhập trí mệnh du hí"),
]

#: Bản dịch TỐT — người viết, văn nói, đúng nghĩa. Thước phải cho điểm CAO.
TOT: list[tuple[str, str]] = [
    ("近期热播的七部新片推荐", "Bảy bộ phim mới đang hot gần đây"),
    ("每部都是声猛劲爆", "Phim nào cũng nghẹt thở, cháy màn hình"),
    ("第一部地下决斗室", "Phim đầu tiên: Sàn Đấu Ngầm"),
    ("主要讲述落魄拳手踏入非法决斗场",
     "Phim kể về một võ sĩ sa cơ lỡ vận bước chân vào sàn đấu phi pháp"),
    ("在无规则厮杀中绝境求生",
     "Giành giật sự sống giữa những trận hỗn chiến không luật lệ"),
    ("打戏部分拳拳到肉", "Cảnh đánh nhau thì đấm phát nào ra phát nấy"),
    ("喜欢看动作片的小伙伴", "Ai mê phim hành động"),
    ("千万不要错过这部电影", "Thì đừng bỏ lỡ bộ phim này nhé"),
    ("主要讲述恶灵军团试图打开地狱之门",
     "Phim kể về đạo quân ác linh tìm cách mở cánh cổng địa ngục"),
    ("十二位使者被迫集结与恶灵展开了一场关乎人类存亡的生死对战",
     "Mười hai vị sứ giả buộc phải tập hợp, mở ra trận sinh tử với ác linh, "
     "quyết định sự tồn vong của loài người"),
    ("场面真是震撼", "Cảnh phim đúng là chấn động"),
    ("绝对值得熬夜看看", "Thức đêm xem cũng đáng"),
    ("非常值得一看", "Rất đáng để xem"),
    ("战斗场面激烈震撼", "Cảnh chiến đấu vừa dữ dội vừa mãn nhãn"),
    ("新娘在婚礼后再次陷入致命游戏",
     "Sau đám cưới, cô dâu lại rơi vào một trò chơi chết người"),
    ("她必须在绝境中求生", "Cô phải tìm đường sống giữa đường cùng"),
    ("每一秒都让人心跳加速", "Từng giây đều khiến tim đập thình thịch"),
    ("喜欢惊悚片的千万不要错过", "Ai mê phim kinh dị thì đừng bỏ lỡ nhé"),
    ("讲述2042年一场神秘太阳风暴引发全球性灾难",
     "Kể về năm 2042, một cơn bão mặt trời bí ẩn gây ra thảm hoạ toàn cầu"),
    ("影片融合科幻与惊悚元素", "Phim pha trộn giữa khoa học viễn tưởng và kinh dị"),
]

LOAI = ("thuat_ngu", "nguoc_tai", "cut", "gop", "chu_han", "may_moc")
