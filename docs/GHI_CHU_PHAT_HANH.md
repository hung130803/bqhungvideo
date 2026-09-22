# BQ Hung Video v2.50.3 — sửa mở ứng dụng và kiểm tra Groq

## Mở ứng dụng sau cập nhật

- Sửa lỗi cập nhật xong ứng dụng chạy nhưng cửa sổ đăng nhập bị ẩn. Bản mới tự hiện cửa sổ cả khi bộ cập nhật cũ khởi chạy ở chế độ ẩn.
- Khi bấm mở lần nữa, ứng dụng đưa cửa sổ đang chạy lên, thay vì chỉ báo “đã mở”. Không tạo thêm hàng đợi xử lý video.

## Key Groq và kiểm tra kết nối

- Nút “Kiểm tra kết nối” thử riêng AI chat và Whisper chép lời bằng âm thanh mẫu ngắn. Chat thành công không còn được hiểu là chép lời cũng hoạt động.
- Kết quả ghi rõ key được kiểm tra: mỗi dịch vụ kiểm một key đầu danh sách, không xác nhận tất cả key. Với chép lời local, hiển thị rõ chưa thử model local.
- Bỏ cơ chế lấy lỗi một key để chặn cả danh sách. Lưu trạng thái đúng key và đúng dịch vụ, chia sẻ được giữa tiến trình phân tích và giao diện.
- Key chưa từng kiểm tra hiển thị “CHƯA KIỂM TRA”. Lỗi hạn chế tổ chức được phân biệt với key sai, không đưa nhầm vào danh sách key cần xóa.
- Kiểm tra chat không xóa lỗi hạn chế của Whisper. Chỉ khi chính key/dịch vụ đó kiểm tra thành công mới gỡ trạng thái chặn đã lưu.
- Không cộng hạn mức các key thành tổng gây hiểu nhầm: nhiều key cùng tổ chức có thể dùng chung hạn mức.

## Kiểm tra bản phát hành

Quy trình phát hành chạy 27 chương trình kiểm thử, gồm 36 ca hồi quy cho dữ liệu, dây chuyền, cập nhật và trạng thái key. Sau đóng gói, EXE còn phải vượt qua kiểm tra giao diện, tài nguyên và ba tình huống cửa sổ thật: mở thường, mở từ bộ cập nhật ẩn, mở lần hai khi cửa sổ cũ bị ẩn.

Các sửa lỗi dây chuyền và bảo vệ dữ liệu của v2.50.2 vẫn được giữ. Bản này không tự gỡ hạn chế do Groq áp dụng cho tài khoản; nếu dịch vụ tiếp tục trả `organization_restricted`, video gốc được giữ và cần xử lý tài khoản với Groq.
