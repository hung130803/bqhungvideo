# BQ Hung Video v2.50.8 — quản lý Hàng loạt theo nhóm và kênh

- Bỏ Tất cả nhóm trong Hàng loạt. Chỉ hiển thị các nhóm đã lưu, kể cả nhóm trống; Chưa phân nhóm chỉ xuất hiện khi có kênh chưa được gán nhóm.
- Bên trái có danh sách kênh theo STT, sắp số tự nhiên (2 trước 10), số video và dấu hiệu đang chạy/chờ. Có tìm kênh không dấu, thêm kênh, sửa tên/nhóm, quản lý nhóm và nhớ lựa chọn khi mở lại.
- Hiển thị riêng nơi lưu Part và nguồn video Dây chuyền. Mở/chép thư mục kênh ngay cả khi chưa có video; thêm/đổi đường dẫn hoặc về mặc định trong cùng cửa sổ. File đã có giữ tại vị trí cũ.
- Kiểm tra đường dẫn tồn tại, chặn cấu hình cũ ghi đè cấu hình mới; chặn đổi khi kênh còn việc chạy/chờ hoặc Dây chuyền chưa hoàn tất video. Hủy cửa sổ không lưu thay đổi.
- Bảng bên phải theo đúng kênh đã chọn, có STT video, tìm kiếm và lọc trạng thái. Không còn bỏ sót video cũ do giới hạn 2.000 video toàn ứng dụng; mỗi trang hiển thị tối đa 100 dòng.
- Cấu hình Dây chuyền mở theo nhóm đang xem. Các bước phân tích, xuất Part và xử lý gốc vẫn hiển thị riêng.

Kiểm thử dùng cơ sở dữ liệu và file mẫu cách ly. Bao gồm kênh hơn 2.000 video, chuyển nhóm, nhóm/kênh trống, bảo vệ đường dẫn và màn hình 1280×720. Giữ các cổng hồi quy tiến trình, Dây chuyền, xoay key, đóng gói và khởi động Windows.
