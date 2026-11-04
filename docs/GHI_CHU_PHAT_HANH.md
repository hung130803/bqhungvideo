## 2.50.26 — Giọng kể Gemini và bố cục dựng chuyện

- Gemini nhận cách nhấn từng cảnh; nhịp nhanh/chậm được áp dụng bằng audio giữ cao độ (nhanh +12%, chậm -5%) vì chỉ dẫn tốc độ AI không ổn định; bỏ chỉ dẫn ngắt nghỉ kịch tính dùng chung. Nghe thử dùng cùng nhịp/cảm xúc đã chọn. Không kéo chậm lời để lấp cảnh.
- Kịch bản Việt ưu tiên từ Việt dễ nói, giữ đúng tên riêng; yêu cầu hook có căn cứ và góc kể riêng cho mỗi Part. TTS nhận chỉ dẫn đọc tên ngoại ngữ trong câu Việt; vẫn cần nghe duyệt, không bảo đảm phát âm mọi tên.
- Thêm bố cục giấy ấm, xanh đêm, xanh ngọc; chọn nền riêng, khung video cao 20–44%, nhãn cuối tối đa 48 ký tự. Giữ nguyên tỉ lệ nguồn. Sửa tại Kịch bản → Dựng hình & âm thanh; chọn Theo mẫu xuất hiện tại để dùng Chỉnh mẫu.
- Không tự viết lại kịch bản đã duyệt. Muốn nội dung mới cần chỉnh/duyệt hoặc phân tích lại; mẫu mới có thể áp dụng vào Part hiện có.

# BQ Hung Video v2.50.25

- Sửa báo lỗi giả khi lời chỉ dài hơn cảnh dưới 2%: áp mức điều chỉnh nhịp nhỏ được cho phép, không bỏ qua rồi chặn xuất.
- Giọng Gemini quá dài được thu lại một lần bằng đúng lời và giọng đã duyệt, kèm thời lượng cảnh; không đổi kịch bản, cắt câu hay tự đổi giọng. Nếu vẫn quá dài, báo rõ số cảnh, mốc nguồn và câu cần sửa.
- Lỗi lời dài hơn cảnh không tự chạy lại toàn việc xuất 3 lần. Bảng duyệt đánh số cảnh và hiển thị độ dài chữ ước tính; phân biệt duyệt nội dung với đo thời lượng giọng thật.

# BQ Hung Video v2.50.24

- Gemini dùng ngân sách đầu vào riêng cho dựng chuyện, không còn chịu ngưỡng nhỏ 5.800 token của nhánh Groq. Vẫn chặn yêu cầu quá lớn; không cắt bỏ căn cứ để lách kiểm tra.
- Lập bản đồ Gemini gộp nhóm lớn hơn có giới hạn, giữ đủ từng cảnh để giảm số lượt gọi. Không hạ mật độ xem hình hay bỏ kiểm tra lời kể.
- Cảnh AI cắt ngắn sẽ dùng lời kể nếu mép cắt không bảo toàn lời gốc; sửa sai số làm tròn ở mép cảnh nguyên vẹn, tránh thử chọn lại chỉ vì lệch vài phần nghìn giây.
- Lưu bản đồ tình tiết, mạch chuyện, đối chiếu cảnh và từng Part hoàn tất; thử lại tiếp tục phần còn thiếu. Đổi nguồn, cài đặt hoặc model sẽ bỏ bộ nhớ đệm không còn phù hợp.
- Lỗi vượt ngân sách của app không tự chạy lại toàn bộ 3 lượt. Hiển thị bước/yêu cầu đang chạy và ghi thời gian xử lý từng yêu cầu, không ghi key hoặc nội dung lời thoại vào log thời gian.
- Chờ SDK Gemini có kiểm tra hủy và thời hạn; tắt vòng thử lại ngầm để tránh chờ nhiều tầng. Chất lượng kịch bản vẫn cần người dùng xem và duyệt.
- Dựng chuyện chỉ nhận JSON object đầy đủ; không lấy nhầm danh sách hook bên trong phản hồi bị cắt làm kịch bản. Với Gemini 2.5 Flash/Pro, các yêu cầu JSON có thời hạn giữ ngân sách suy luận 4.096 và trần đầu ra 12.288 token qua API chính thức, dành chỗ cho câu trả lời; vẫn kiểm tra từng cảnh và duyệt kịch bản.

# BQ Hung Video v2.50.23

- Sửa Gemini đọc hình: yêu cầu JSON theo cấu trúc mô tả cảnh, từ chối nội dung bị cắt dở. Cảnh trả sai định dạng được thử lại một lần với cùng ảnh; không lấy lời thoại thay cho căn cứ hình ảnh.
- Phần hình ảnh Gemini dùng danh sách key và trạng thái chờ, xoay khi 429/key sai; không đánh dấu key hỏng vì lỗi định dạng, quyền truy cập hay nội dung bị chặn.
- Áp dụng thời hạn gọi và kiểm tra hủy trong lúc chờ Gemini. Thông báo lỗi ghi vị trí cảnh; vẫn giữ kết quả các cảnh đã kiểm tra để tiếp tục.
- Các key cùng project Google vẫn dùng chung hạn mức; bản sửa không tăng quota và không tự chuyển sang dịch vụ tính phí khác.

# BQ Hung Video v2.50.22

- Chia cài đặt dựng chuyện thành ba thẻ: Ngôn ngữ/giọng, Kịch bản/Part, Hình/âm thanh. Hiện rõ BẬT/TẮT; giữ cấu hình đã lưu và nút Lưu luôn nhìn thấy. Ẩn số lượt viết lại không áp dụng cho chế độ dựng chuyện kỹ.
- Sửa Groq vision gọi lại key còn cooldown; đọc Retry-After của dịch vụ, giữ hạn mức hình ảnh khi chat thành công. Tiếp tục tôn trọng key/dịch vụ bị hạn chế và giới hạn thời gian thử.
- Không coi lỗi 403 chung là bằng chứng key sai hoặc đề xuất xóa key. Nhận diện hạn chế tổ chức bằng thông báo cụ thể.
- Cài đặt AI cho chọn key để kiểm tra lại chat, chép lời và hình ảnh. Mẫu kiểm tra là âm thanh/ảnh màu tạo sẵn, không gửi video người dùng. Thành công ở dịch vụ nào chỉ mở lại trạng thái dịch vụ đó.
- Sửa phụ đề cụm vượt khoảng im lặng, bị gom lại qua chỗ ngắt, hoặc kéo dài quá cuối lời đọc. Xuất lại Part để áp dụng; không cần phân tích lại chỉ để sửa thời gian chữ.
- Bản này không tăng hạn mức Groq, không tự mở khóa tài khoản và không cam kết chất lượng kịch bản/giọng đọc như người dựng chuyên nghiệp.

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
