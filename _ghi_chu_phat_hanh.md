# BQ Hung Video v2.35.0

## Sửa được gì

### 1. Chữ chạy theo lời của giọng ngoài: từ "một phần ba số chữ không có mốc" lên gần đủ

Bản trước, giọng ngoài (OmniVoice) lấy mốc từng chữ bằng cách **cho máy nghe
chép ngược** chính file tiếng vừa đọc rồi đoán xem nó nói gì. Chữ nào máy nghe
nghe sai thì chữ đó **không có mốc nào** — chỗ đó chữ không chạy theo tiếng
được.

Nay app dùng **gióng hàng cưỡng bức**: nó **không đoán chữ, nó đã biết chữ**,
chỉ còn đi tìm mỗi chữ nằm ở giây nào. Đo trên 4 thứ tiếng (Việt · Anh · Trung
· Nhật), 12 câu mỗi thứ, 2 lượt đan xen, **thước là `silencedetect` chứ không
phải máy nghe nào**:

| | cách cũ | **cách mới** |
|---|---|---|
| Số chữ CÓ mốc | 52,5% | **98,6%** |
| · tiếng Việt | 37,6% | **98,9%** |
| · tiếng Anh | 79,0% | **100,0%** |
| · tiếng Trung | 67,5% | **96,8%** |
| · tiếng Nhật | 25,7% | **98,7%** |
| Chữ lệch tiếng (rung) | 711,9 ms | **90,4 ms** |
| Thời gian lấy mốc cho 12 câu | 32,5 giây | **6,3 giây** |
| Lượt Groq tiêu tốn | mỗi câu 1 lượt | **0** |

Đo lại trên một mẻ tiếng khác cũng ra **98,5%** — tức con số này là tính chất
của cách làm, không phải may.

**Nói thẳng phần chưa được:** chữ vẫn bám lời kém hơn giọng thường (edge-tts).
Rung còn **90-119 ms** so với **15,7 ms** của edge-tts, nặng nhất ở tiếng Anh.
Cần chữ bám sát lời nhất thì vẫn dùng giọng thường.

Giọng **Piper** cũng hưởng cùng bản này: máy có bộ gióng hàng thì Piper lệch
**29,5 ms** thay vì 51,8 ms (giọng thường đo cùng lượt: 38,6 ms).

### 2. Một chữ có dấu gạch nối làm mất mốc CẢ CÂU — đã sửa

Lỗi thật, nhật ký ghi thẳng. Bảng chữ cái của bộ gióng hàng coi dấu `-` là ký
tự đặc biệt, mà công cụ chép âm thì giữ nguyên dấu gạch nối. Kết quả: một câu
có chữ như **`COVID-19`** thì **cả câu mất sạch mốc** — chữ trong câu đó không
chạy theo tiếng nữa, và app không báo một dòng nào.

Đo lại sau khi sửa: câu *"Dịch COVID-19 đã làm thay đổi cả thế giới..."* ra
**13/13 mốc** (trước: rỗng).

### 3. Nút tải bộ gióng hàng ngay trong app

Trước đây muốn dùng gióng hàng phải **tự đặt file 1,18 GB vào đúng thư mục** —
tức tính năng coi như không tồn tại với người không đọc mã.

Hộp **Thay giọng nói** nay có thêm một hàng: *Tải bộ gióng hàng (khoảng
1,2 GB)*, cùng kiểu với nút tải bộ tách giọng và nút tải giọng Piper.

- Dùng **chung** torch với bộ tách giọng nên **không tải thêm 2,5 GB** trùng.
  Chưa tải bộ tách giọng thì nút nói thẳng là bấm nút kia trước, chứ không
  lặng lẽ kéo về bản torch thứ hai.
- Chưa tải thì app **vẫn chạy bình thường**, chỉ là mốc chữ lấy theo cách cũ.

### 4. Nhãn chọn giọng nay nói đúng theo máy của bạn

Nhãn giọng ngoài trước đây ghi cố định *"chỉ có mốc cho 30-56% số chữ"*. Con số
đó nay sai, nên nhãn tự đổi theo máy:

- Máy **đã có** bộ gióng hàng: ghi số mới (phủ 98,5%, rung 90-119 ms).
- Máy **chưa có**: vẫn cảnh báo, nhưng ghi đúng dải đo được là **38-99% tuỳ
  lượt** kèm chỉ đường sang nút tải.

Phần cảnh báo **giấy phép giữ nguyên**: trọng số OmniVoice là CC-BY-NC, nhà
phát hành cấm dùng cho mục đích thương mại.

### 5. Môi trường giọng ngoài không còn nằm trong thư mục tạm

Môi trường 7,74 GB của giọng ngoài trước đây nằm trong `%TEMP%`. Một lượt dọn
đĩa của Windows — hoặc chính lúc ổ C đầy phải dọn — là **mất sạch**, và triệu
chứng không phải một dòng lỗi mà là **giọng tự nhiên biến khỏi danh sách**.
Đúng cái đã xảy ra một lần với bộ tách giọng.

Nay nó nằm cạnh app (bản đóng gói: trong thư mục dữ liệu, **không** nằm cạnh
`.exe` để lượt tự cập nhật không xoá mất). Máy nào còn bản cũ vẫn chạy được,
nhưng app ghi cảnh báo vào nhật ký mỗi lượt.

## Đo bằng gì

Thước duy nhất dùng để chấm là `silencedetect` — so mốc chữ đầu với lúc file
**thật sự phát ra tiếng**. Cố ý không dùng máy nghe: mốc của cách cũ vốn do máy
nghe sinh ra, nên đem máy nghe đi chấm là để nó tự chấm cho chính nó (đo thử ra
đúng 0,0 ms trên 1.587 mốc — một bảng điểm hoàn hảo cho thứ chưa hề được kiểm).

## Còn nợ, ghi thẳng

- Rung mốc của gióng hàng ở **tiếng Anh** còn cao (lệch đều +104..+121 ms).
  Chưa truy ra nguyên nhân, và cố ý **không trừ đi bằng một hằng số** — làm vậy
  là tự tay làm sai thêm rồi khoe đã chữa.
- Giọng ngoài **chưa có nút tải** (trọng số 6,1 GB + môi trường riêng); máy nào
  chưa dựng sẵn thì app lùi êm về giọng thường.
- Bản `.exe` vẫn **không gói** torch/model: máy nhân viên phải có Python 3 và
  bấm nút tải. Gói vào là bộ cài phình từ 240 MB lên hơn 11 GB.
