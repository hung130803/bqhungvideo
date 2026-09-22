# BQ Hung Video v2.50.2 — sửa dây chuyền và bảo vệ dữ liệu

Bản này tập trung sửa lỗi vận hành, giữ nguyên cách sử dụng và cấu hình hiện có.

Đây là bản phát hành lại sau khi sửa lỗi môi trường kiểm thử và lưu log trên GitHub; lượt đóng gói v2.50.1 trước đó thất bại và chưa công bố bộ cài.

## Dây chuyền cắt video

- Sửa lỗi không dọn được video gốc khi tên kênh chứa ký tự đặc biệt như `|`, `:` hoặc `/`.
- Chỉ dọn nguồn sau khi đủ các Part đã xuất; nếu thiếu Part hoặc xuất lỗi thì giữ nguồn và ghi rõ lý do.
- Nút cứu video kẹt xử lý được cả gốc đã xuất nhưng còn mắc lại. Gốc được chuyển vào Thùng rác của ứng dụng để có thể khôi phục.
- Chờ file tải ổn định trước khi nhận; theo dõi đúng từng video khi nhiều kênh chạy cùng lúc.
- Sửa một số trường hợp huỷ rồi mở lại vẫn chạy tiếp, hoặc nhiều lượt cùng xếp trùng một công việc.

## Phân tích AI và thay giọng

- Khi Groq báo tài khoản bị hạn chế, ứng dụng báo đúng nguyên nhân, dừng gọi lặp và giữ video gốc. Người dùng cần xử lý tài khoản với Groq, sau đó vào Cài đặt để kiểm tra lại kết nối.
- Lỗi tài khoản hoặc cấu hình AI không còn bị coi là video hỏng.
- Sửa lựa chọn nhà cung cấp AI khi lưu cài đặt và xử lý một số kết quả JSON có dấu phẩy thừa.
- Chế độ đè giọng không bắt buộc cài Demucs; nút bỏ qua có gửi lệnh huỷ. Bổ sung thời hạn dừng tiến trình bị treo ở một số bước xử lý giọng và OCR.

## Dữ liệu và cập nhật

- Sao lưu bao gồm dữ liệu SQLite chưa ghi hết vào file chính; không dọn dữ liệu nếu sao lưu thất bại.
- Khi database hỏng, giữ bộ dữ liệu để khôi phục và báo lỗi rõ; không âm thầm mở một database rỗng.
- Hạn chế dọn file tạm vào vùng ứng dụng sở hữu; không lưu mật khẩu dạng base64 khi Windows không mã hoá được.
- Cập nhật có kiểm tra mã SHA256 và giữ bản cũ để quay lui nếu thay EXE hoặc thư viện thất bại.

## Kiểm tra trước phát hành

Đã chạy đạt 25 chương trình kiểm thử, gồm 26 ca hồi quy mới; có thử xuất video với hình và âm thanh bằng FFmpeg thật. Quy trình phát hành tiếp tục kiểm tra tự động và chạy thử chính EXE đã đóng gói trước khi công bố file tải.

Kết quả này không bảo đảm mọi video, model hoặc dịch vụ bên ngoài đều không còn lỗi. Bản sửa không tự gỡ hạn chế tài khoản Groq. Nếu công cụ đăng đã lấy mất Part trước lúc kiểm tra, ứng dụng giữ nguồn để tránh mất dữ liệu.
