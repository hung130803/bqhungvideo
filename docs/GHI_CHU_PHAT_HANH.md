# BQ Hung Video v2.50.12 — AI dựng chuyện kỹ theo cảnh nguồn

- Thêm **Video & clip → Công cụ → AI dựng chuyện kỹ · nhiều Part**. App lấy mẫu hình xuyên suốt video, đối chiếu với lời gốc, lập mạch chuyện, viết hook và kiểm tra từng câu theo cảnh được chọn. Có thể tạo nhiều Part theo thứ tự nguồn, không lặp lại đoạn đã dùng.
- Trong **Cài đặt Reup thuyết minh**, chọn giọng, phong cách, số Part và thời lượng. Bật **AI dựng chuyện kỹ** để dùng cùng chế độ Reup của Dây chuyền. Đây là lựa chọn riêng, mặc định tắt; cách cắt thường giữ nguyên.
- **Mỗi Part dựng chuyện bắt buộc trên 60 giây**, mặc định **61–120 giây**. Cấu hình riêng cho chế độ mới; kiểm tra cả thời lượng sau tăng tốc và file xuất thật. Nguồn không đủ sẽ báo giảm số Part/chọn video dài hơn, không lặp cảnh để kéo dài.
- Mỗi Part mới **CHỜ DUYỆT**: mở **Kịch bản…**, xem video nguồn theo mốc, nhấp đúp lời kể để sửa, rồi **Lưu & duyệt**. Đóng cửa sổ không duyệt. Dây chuyền/tự xuất chờ duyệt đủ các Part, kể cả sau khi khởi động lại app. Không cần thêm AI cục bộ.
- Giữ nguyên lời đã duyệt. Nếu thu âm dài hơn cảnh, app báo để bạn viết ngắn và duyệt lại; không cắt cụt câu, tự đổi lời hoặc mượn hình của cảnh kế tiếp. Giữ đúng giọng đã chọn; thu âm thiếu sẽ báo lỗi để thử lại.
- Chặn xuất khi kịch bản chưa duyệt, cảnh hoặc nguồn thay đổi. Sửa kịch bản đã xuất sẽ yêu cầu xuất lại, không dùng kết quả cũ để dọn video gốc.
- Nhạc nền, hiệu ứng, chuyển cảnh và phụ đề dùng theo mẫu xuất hiện có. Sửa trường hợp thiếu mẫu khung làm chế độ mới bỏ qua ghép đoạn/thuyết minh. Kiểm tra thời lượng và âm thanh của Part trước khi ghi nhận thành công.
- Lưu kết quả xem hình để tiếp tục khi thử lại. Lỗi máy chủ quá tải được chờ và thử lại có giới hạn. Chuyển model xem hình Groq mặc định đã ngừng hỗ trợ sang `qwen/qwen3.8-27b`; giữ cấu hình model khác do người dùng chọn.

Chế độ này cần AI xem hình và tốn thời gian hơn cắt thường. App lấy mẫu hình, không đọc từng khung hình; Groq vẫn có thể nhận sai đối tượng hoặc tình tiết. Bạn cần xem nguồn khi duyệt và xem Part trước khi đăng. Nếu các lượt kiểm tra AI chưa thống nhất, bản nháp hiện cảnh báo cụ thể để bạn sửa; vẫn bị chặn xuất tới khi bạn duyệt. Mốc cảnh không hợp lệ hoặc không đủ cảnh cho số Part đã chọn sẽ dừng và báo lý do.

Tạo kịch bản không tự xóa nguồn. Dây chuyền chỉ dọn nguồn theo cấu hình hiện có sau khi các Part cần xuất đã thành công.
