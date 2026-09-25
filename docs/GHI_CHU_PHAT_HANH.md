# BQ Hung Video v2.50.14 — Sửa lỗi chọn tình tiết khi dựng chuyện

- Sửa lỗi dừng với thông báo **“Chưa chọn được các tình tiết có căn cứ”** ở bước thu gọn ghi chú cảnh. Đây có thể là phản hồi sai định dạng của AI, không phải video không có nội dung.
- Rút ngắn ghi chú trước khi loại ứng viên, giữ toàn bộ mã cảnh đối với nguồn vừa giới hạn. Khi cần thu gọn nguồn dài, nhận đúng mã dạng số/chuỗi số, gộp mã trùng và yêu cầu sửa mã không hợp lệ tối đa một lần. Nếu vẫn sai, giữ nhóm cảnh gốc để lập kế hoạch thay vì bỏ toàn bộ lượt phân tích.
- Giữ kiểm tra cảnh thật, thời lượng 61–119 giây, không lặp cảnh giữa Part và duyệt kịch bản trước khi xuất. Không tự thay bằng các cảnh ngẫu nhiên để che lỗi.
- Bấm **Thử lại** ở việc lỗi để dùng lại phần chép lời/xem hình đã lưu khi nguồn và cấu hình AI không thay đổi. Bản vá không tự chạy lại việc cũ hoặc tự duyệt kịch bản.

## Lịch sử v2.50.13 — Chọn cảnh toàn nguồn, chọn giọng và phối nhạc

- **Video & clip → Công cụ → AI dựng chuyện kỹ · nhiều Part** mở cấu hình trước khi chạy: giọng/nghe thử, ngôn ngữ kịch bản, phong cách, số Part, nhạc nền và tiếng động.
- Tìm tình tiết trên toàn nguồn rồi chọn các cảnh có liên hệ để ghép thành câu chuyện. Không chia đều video thành chương. Mỗi cảnh có vai trò và lý do chọn; các Part không lặp cảnh. Một hành động cần giữ liền phải có giải thích, không cố ghép cảnh không liên quan.
- Tạo ba gợi ý mở đầu; kiểm tra hook, căn cứ từng câu và mạch kể. Giới hạn lời theo thời lượng cảnh. Kịch bản chưa được AI kiểm tra thống nhất hiện rõ cảnh báo để người dùng sửa.
- Trong **Kịch bản…**, xem góc kể, căn cứ, vai trò và lý do chọn cảnh. **Xem cảnh đang chọn** phát đúng khoảng nguồn để đối chiếu lời kể. **Chọn giọng / nghe thử** đổi giọng riêng cho Part, không cần phân tích lại; bấm **Lưu & duyệt**, sau đó xuất lại. Giọng khác ngôn ngữ kịch bản được báo rõ.
- Căn cứ lời gốc lấy theo mốc từng từ trong khoảng cắt, không mang phần cuối câu ở cảnh sau sang cảnh trước. Tiến trình giữ phần trăm khi AI phải sửa lại và hiện bước đang thực hiện.
- Giảm lượt xem hình: khảo sát một hình mỗi khoảng nguồn tối đa 12 giây, sau đó đối chiếu thêm trong đúng khúc được chọn. Hai lượt xem hình có thể chạy đồng thời trong một video; có giới hạn chung. Lưu căn cứ để tiếp tục khi thử lại, gom lượt lập bản đồ và kiểm tra lời thay vì gọi riêng từng câu.
- Giới hạn thời gian một lượt gọi AI qua các key/model; lỗi hạn mức phút được chờ và thử lại hữu hạn. Không coi nhiều key là hạn mức vô hạn. Tốc độ thực tế phụ thuộc video, số Part và Groq.
- Chọn file nhạc riêng hoặc nhạc của mẫu. Nhạc vào/ra êm và hạ dưới lời kể; có thể bật/tắt. AI chọn tối đa ba điểm nhấn tình tiết từ 11 nhóm tiếng động có sẵn; hiệu ứng hình/chuyển cảnh vẫn theo mẫu. Giữ đúng nhật ký hiệu ứng đã xuất.
- **Mỗi Part bắt buộc 61–119 giây**, kiểm tra cả tốc độ mẫu và file thật. Giữ nguyên lời đã duyệt; lời quá dài cần sửa rồi duyệt lại, không tự cắt cụt hoặc đổi nội dung.

Groq vẫn có thể nhận sai hình hoặc viết sai tình tiết. App lấy mẫu hình, không xem từng khung hình như người; nhanh hơn không đồng nghĩa chính xác tuyệt đối. Mỗi Part vẫn bắt buộc xem/sửa và duyệt trước khi xuất. Tạo kịch bản không xóa nguồn; Dây chuyền chỉ dọn nguồn theo cấu hình sau khi mọi Part cần xuất đã thành công và qua kiểm tra an toàn.

## Lịch sử v2.50.12

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
