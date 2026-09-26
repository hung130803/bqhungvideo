# BQ Hung Video v2.50.20

- Sửa lỗi xuất Part khi mẫu Phóng sự/Giải thích kế thừa tùy chọn cắt viền đen: tự giữ trọn nguồn, đồng nhất với bản xem thử và tọa độ mũi tên/zoom.
- Bỏ lượt dò viền không cần thiết cho hai bố cục này. Mẫu thường và bố cục dựng hình đã tắt vẫn giữ cách cắt viền cũ.
- Có thể xuất lại các Part đã duyệt, không cần phân tích AI lại vì lỗi này. Không thay đổi kịch bản, cấu hình mẫu đã lưu hay video gốc.

# BQ Hung Video v2.50.19

- Sửa khâu kiểm tra mạch chuyện: dùng thêm bối cảnh hình, ngày ghi, địa điểm và nhân vật; không chỉ dựa vào vài câu thoại khi nối các đoạn xa nhau. Nguồn tổng hợp nhiều vụ việc phải được xem là nhiều câu chuyện riêng.
- Có kiểm tra cục bộ để cảnh báo khi các cảnh có ngày ghi khác nhau, kể cả kịch bản cũ. Đây là tín hiệu từ mô tả AI, cần xem nguồn để xác nhận, không phải chứng cứ sự kiện.
- Phát hiện câu nguồn tiếng Anh bị chép nguyên vào lời kể tiếng Việt; yêu cầu AI viết lại đúng ngôn ngữ trước khi công nhận kiểm tra đạt. Không tự sửa kịch bản đã được người dùng duyệt.
- Giữ toàn bộ mẫu phóng sự, keyframe, kho nhạc/SFX và nhịp đọc từng cảnh của v2.50.18. Các thay đổi không biến giọng TTS thành người diễn xuất, không đảm bảo mọi kịch bản đều hấp dẫn.

Cách dùng: **AI dựng chuyện kỹ → ngôn ngữ tiếng Việt → Bố cục: Phóng sự**. Trong **Kịch bản → Dựng hình & âm thanh**, chỉnh tiêu đề, ảnh dừng, zoom và mũi tên; xem thử trước khi lưu/duyệt. Kịch bản cũ muốn AI viết lại phải phân tích lại; cập nhật ứng dụng không tự sửa các Part đã lưu.
