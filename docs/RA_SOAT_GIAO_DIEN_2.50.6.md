# Rà soát giao diện v2.50.6

## Phạm vi và phát hiện

Đọc các thành phần cửa sổ chính, nguồn video/clip, tiến trình, Dây chuyền, nhóm/kênh, quản lý video, kho rác, cookie, AI, chỉnh mẫu, thuyết minh, thay giọng, đăng nhập và cập nhật. Dựng ảnh từ widget Qt thật với dữ liệu tạm; không chạy trên cơ sở dữ liệu hoặc video thật của người dùng.

- Cửa sổ chính cũ yêu cầu tối thiểu khoảng 1.732 × 783 khi có đủ nút. Hàng nguồn và hàng tác vụ ép rộng màn hình. Sau gom nút và bổ sung thanh điều hướng, mức đo còn 1.080 × 645; đã kiểm tra ở 1.280 × 720 và 1.366 × 768.
- Hàng đợi theo công việc khó đối chiếu với kết quả từng video. Bổ sung trang Hàng loạt, giữ riêng số Part, lỗi công việc và trạng thái dọn gốc. Không suy đoán rằng đã xóa gốc chỉ từ việc xuất xong.
- Cửa sổ Thay giọng cũ cao hơn 900 px, phần cấu hình dài đẩy bảng và nút xuống ngoài màn hình. Nay cuộn cấu hình riêng, bảng và nút thao tác giữ ở vùng dưới. Các combo mô tả dài có tooltip đầy đủ.
- AI/Chỉnh mẫu có nhiều nhóm, cần cuộn tìm; thêm Đi tới. Thuyết minh cuộn riêng, giữ Lưu/Hủy. Đổi kích thước/nhảy nhóm không đổi mẫu xuất.
- Ghi chú cập nhật bị cắt 800 ký tự. Nay hiển thị đầy đủ bằng văn bản thuần trong vùng cuộn.
- Bảng xen kẽ kế thừa màu trắng trên một số nền tối; đặt rõ màu nền, chữ và dòng chọn. Nhãn giọng dài được giữ phần chi phí/tải bộ ở màn hẹp.

Nhóm/kênh, kho rác, cookie, đăng nhập và các hộp phụ đã được kiểm tra bố cục hiện tại; không đổi chức năng chỉ để thay hình thức.

## Giới hạn và cách kiểm tra

`tests/test_workspace_ui.py` kiểm tra cả trạng thái trong DB và widget thực: giữ đúng video khi thứ tự thay đổi, tìm tiếng Việt không dấu, không ghi DB khi lọc, thử lại/hủy đúng phạm vi, tránh xuất clip cũ khi phân tích lại, timer Dây chuyền tiếp tục khi đổi màn, giữ nguyên mẫu xuất/cài đặt sau khi cuộn, giới hạn số dòng và độ trễ.

`tools/validate_repairs.py` chạy lại các kiểm tra đường phân tích/xuất, dữ liệu, hủy/hồi phục, tiến trình và hiệu năng trước phát hành. Tự kiểm tra EXE và `tools/check_startup.py` xác minh tài nguyên, FFmpeg và mở cửa sổ thường/mở từ updater/mở lần hai.

Bảng đọc trạng thái đã ghi, không xác minh sự tồn tại của mọi file đầu ra. Việc xác minh Part trước dọn gốc vẫn do Dây chuyền thực hiện. Các ca UI không xác nhận chất lượng từng video, dịch vụ AI/TTS trực tuyến hoặc mọi mức DPI trên mọi máy. Không thay cấu hình AI/mẫu xuất mặc định và không sửa cơ sở dữ liệu, media thật trong quá trình kiểm tra.
