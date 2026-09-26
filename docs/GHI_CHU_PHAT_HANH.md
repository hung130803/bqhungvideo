# BQ Hung Video v2.50.21

- Sửa chữ trong khung phóng sự còn hiện sau khi đọc: dùng mốc giọng thực tế, ẩn trong khoảng ngắt và khi đọc xong; vẫn khớp khi đổi tốc độ xuất.
- Căn cụm phụ đề bằng mốc từng từ của dịch vụ giọng khi có, thay vì chia đều toàn câu. Ghép các thẻ chữ vào một luồng ảnh để tránh mở nhiều bộ giải mã cùng lúc.
- Chọn cảnh có thêm mép vào/ra bên trong từng khúc nguồn; yêu cầu AI bỏ khoảng thừa, chọn nhịp cảnh khác nhau và giữ câu trọn vẹn khi dùng tiếng gốc. Part vẫn phải 61–119 giây.
- Hướng dẫn viết lời kể thành mạch chuyện, giảm lối liệt kê hình ảnh. Giao diện dùng tên trung tính “đoạn nguồn”, không tự khẳng định các đoạn đều hay.
- Xuất lại Part cũ để áp dụng sửa thời gian chữ. Muốn AI chọn cảnh/viết lời theo chỉ dẫn mới cần tạo lượt phân tích mới và duyệt lại. Giọng không đổi sang dịch vụ trả phí; thay đổi này không bảo đảm diễn cảm như người thật.

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
