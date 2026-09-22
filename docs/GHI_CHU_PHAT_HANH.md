# BQ Hung Video v2.50.5 — tiến trình hàng loạt rõ hơn, dọn gốc an toàn hơn

- Mỗi việc hiện tên kênh/video và bước đang thực hiện ngay trên hai dòng. Các việc xuất có số Part, số đã xuất/tổng Part của video và kết quả dọn gốc khi Dây chuyền đã ghi nhận.
- Tách số việc AI/xử lý và số Part đang chờ, đã xong hôm nay. Phần trăm thuộc từng công việc; dấu `~` là ước tính. Chỉ báo 100% khi việc hoàn tất, hiện riêng bước hoàn thiện hashtag. Phân tích xong không đồng nghĩa đã xuất xong video.
- Thay thông báo tự xuất dễ bị hiểu là trạng thái hiện tại bằng thông báo rõ về lượt vừa xếp hàng. Nhãn video phân biệt số clip được tạo với số Part đã xuất. Thử lại lỗi không giữ lại thao tác mở thông báo lỗi cũ.
- Trước khi dọn gốc, đối chiếu đường dẫn và dấu nhận dạng file lúc nhận, kiểm tra đủ file Part và kết quả xuất. Giữ lại video mới nếu file cùng tên bị thay thế; không dọn nhầm file ở thư mục nguồn mới.
- Khi thử dọn lại gốc từng bị Windows giữ, kiểm tra lại danh sách Part và file đầu ra. Giữ gốc nếu Part thiếu/rỗng/đã đổi hoặc việc xuất chưa thành công.
- Khi mở lại app, tôn trọng lệnh hủy của từng Part. Lần xuất lại chủ động mới và clip của lần phân tích mới không bị chặn bởi lịch sử hủy cũ.
- Giữ các sửa lỗi xoay key Groq và mở cửa sổ sau cập nhật từ v2.50.4.

Phát hành được chặn bởi 29 chương trình kiểm thử: gồm 67 ca hồi quy trong bốn bộ unittest, xuất FFmpeg thật hai kênh/bốn Part, kiểm tra hủy/hồi phục và hiệu năng danh sách hàng loạt. EXE phải qua tự kiểm tra tài nguyên, FFmpeg và ba tình huống mở cửa sổ thật trước khi phát hành. Kiểm thử AI của bản sửa tiến trình dùng kết quả mẫu cách ly; không gọi API bằng key của người dùng.
