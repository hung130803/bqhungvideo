# BQ Hung Video v2.50.6 — bố cục gọn hơn, theo dõi hàng loạt theo từng video

- Thanh bên có Video & clip, Hàng loạt, Thay giọng, Cài đặt AI và Hướng dẫn. Các nút phụ được gom vào Quản lý, Tạo nhiều, Công cụ và Xuất thêm; vẫn giữ các chức năng cũ.
- Trang Hàng loạt hiển thị kênh/video, bước đang làm, số Part đã xuất/tổng Part và trạng thái video gốc riêng biệt. Tìm không dấu, lọc nhóm/trạng thái, mở đúng video, xem lỗi, thử lại hoặc hủy việc của video đang chọn. Đổi màn không dừng Dây chuyền.
- Không coi việc phân tích đã xong là đã xuất đủ Part. Việc xuất lỗi hoặc đã hủy vẫn được hiện rõ, kể cả khi còn đường dẫn file xuất cũ. Thử lại phân tích không đồng thời xếp xuất những Part có thể sắp được thay thế.
- Màn chính vừa bố cục 1.280 × 720 và 1.366 × 768 ở mức hiển thị tiêu chuẩn. Thanh bên có thể cuộn; thông tin máy thu gọn khi không cần.
- Cài đặt AI và Chỉnh mẫu có ô Đi tới để đến nhanh nhóm cần chỉnh. Thuyết minh có vùng cuộn riêng, nút Lưu/Hủy ở cuối cửa sổ. Thay giọng giữ bảng tiến trình và nút Chạy/Dừng ở ngoài vùng cuộn, có vạch kéo đổi tỷ lệ hai vùng.
- Sửa màu bảng tối để các dòng đều đọc được. Giữ thông tin chi phí/tải bộ giọng trên nhãn khi màn hình hẹp. Ghi chú cập nhật có vùng cuộn, không bị cắt ở 800 ký tự.
- Giữ các sửa lỗi tiến trình, dọn gốc an toàn, xoay key và mở app sau cập nhật của các bản trước. Không thay cấu hình AI, mẫu xuất, thư mục đầu ra hoặc quy tắc dọn gốc khi đổi bố cục.

Bản phát hành phải qua 30 chương trình kiểm thử, trong đó có 15 ca mới về bố cục, thao tác đúng video và giữ cấu hình. Có kiểm tra xuất FFmpeg thật, tài nguyên EXE và ba tình huống mở cửa sổ Windows. Phần AI của các kiểm tra này dùng dữ liệu mẫu cách ly; không gọi API bằng key người dùng. Bảng hàng loạt đọc trạng thái đã lưu, tối đa 2.000 video ưu tiên đang chạy/gần nhất, 100 dòng mỗi trang; không quét lại toàn bộ file trên ổ đĩa.
