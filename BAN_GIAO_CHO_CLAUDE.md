# Bàn giao cho phiên Claude chạy trên máy (27/10/2026)

Phiên cloud trước đã sửa xong và ghi vào thư mục này. Việc còn lại cần CHẠY LỆNH trên máy:

1. **Cập nhật app 1 lần cuối** (bật chế độ chạy thẳng mã nguồn):
   tắt BQHungVideo.exe rồi chạy `CAP_NHAT_APP.bat`, chọn `1`
   (= `powershell -File tools\dong_goi_cap_nhat.ps1 1`). Sau đó sửa mã chỉ cần mở lại app.
2. **Dọn video trong `D:\video ssmatool\video mỹ`** theo yêu cầu anh Hùng: xoá file Part
   + video gốc dài > 3 phút, GIỮ video shorts (≤ 3 phút), không kể ngày.
   Dùng `tools\don_video_kenh.py` (tắt app trước): chọn 1 → kiểm tra danh sách → Y.
   File được CHUYỂN vào `D:\_RAC_VIDEO\<giờ>` (hoàn tác: chọn 2; xoá hẳn: chọn 3 + gõ XOA).
   Không xoá video đang chạy dây chuyền / file vừa ghi < 10 phút.
3. Sau ~1 ngày chạy: đọc `%LOCALAPPDATA%\BQHungVideo\studio.db` + `logs\pipeline_*.log`
   để đo thời gian xuất mỗi Part (mốc cũ 468 s) và soát video bị sót/kẹt gốc.

Đã làm (đừng làm lại): bố cục gọn + Dây chuyền 2 thẻ; trần bitrate 8/12/20 Mbps
(`EXPORT_MAX_MBPS`) + NVENC nén hiệu quả (tự dò); ảnh bìa `_Bia` + bỏ fade-in đầu;
giải mã NVDEC tự dò; "Hủy tất cả" bỏ lượt dựng đang xếp; toast thay hộp OK ngắn;
bỏ lệnh xuất trùng chặn dọn gốc (`export_recovery.bo_xuat_trung_da_xong`);
AI lỗi tạm thời tự thử lại 3 lần; báo file gốc tên "Part…" bị bỏ qua;
chạy thẳng mã nguồn (`_nguon_song.py` + `nguon_ma.txt` cạnh .exe).
Không đẩy GitHub release khi chưa hỏi anh Hùng (ảnh hưởng máy nhân viên).
