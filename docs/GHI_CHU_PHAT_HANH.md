# BQ Hung Video v2.50.4 — sửa xoay key khi chép lời

- Sửa lỗi một key Groq báo `organization_restricted` làm cả video thất bại dù các key khác vẫn chép lời được.
- Đánh dấu key lỗi theo dịch vụ, bỏ qua key đó và tiếp tục xử lý chính đoạn âm thanh bằng key tiếp theo trong danh sách đã cấu hình. Khi tới cuối danh sách có thể quay về key còn dùng được ở đầu.
- Áp dụng cách xử lý này cho chép lời, AI chat và phân tích hình ảnh. Các worker kiểm tra lại trạng thái trước khi gọi, tránh gọi key vừa bị worker khác đánh dấu chặn.
- Khi không xử lý được bằng danh sách key, thông báo nêu tổng số key, số bị hạn chế và số sai key; không kết luận tất cả bị khóa chỉ từ một lỗi. Giữ video gốc nếu xử lý chưa hoàn tất.
- Giữ nguyên các sửa lỗi mở cửa sổ sau cập nhật và kiểm tra riêng chat/Whisper của v2.50.3. Bản này không gỡ hạn chế trên tài khoản Groq đã bị chặn.

Quy trình phát hành chạy 27 chương trình kiểm thử, gồm 45 ca hồi quy. Bổ sung đối chứng key thứ 9 lỗi rồi chuyển key, nhiều key bị chặn, trạng thái thay đổi giữa các worker và video chín đoạn vẫn ghép đủ nội dung đúng mốc thời gian. EXE phải vượt kiểm tra tài nguyên, xuất FFmpeg và ba tình huống mở cửa sổ thật trước khi phát hành.
