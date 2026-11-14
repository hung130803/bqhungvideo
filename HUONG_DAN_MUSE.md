# Dùng agent Muse (Meta) để chọn đoạn — hướng dẫn cho anh Hùng

App gửi bản nhẹ của video (480p, 2 khung/giây) + lời thoại app đã chép cho agent
Muse chọn Part. Muse lỗi, quá giờ hoặc trả sai thì app **tự chuyển Groq** (rồi
Gemini dự phòng) như bình thường. Bật/tắt trong **Cài đặt AI → thẻ "Muse (Meta)"**.

## 1. Cài (một lần)

Nháy đúp **`CAI_MUSE.bat`** trong thư mục app. Nó cài MuseAI-API vào
`D:\MuseAI-API` (môi trường riêng, không đụng app), hỏi email + mã OTP rồi kiểm
`ping`. Thấy `HTTP 200` là xong.

Bản ở `D:\MuseAI-API` đã được soát mã và vá 2 lỗi của tác giả (file dính số dòng;
tải lên báo sai cỡ). `CAI_MUSE.bat` **không tự cập nhật** từ GitHub để giữ đúng
bản đã soát.

## 2. Thêm tài khoản (tuỳ chọn)

Nháy đúp **`THEM_TK_MUSE.bat`**, đặt tên ngắn (vd `tk2`), nhập email + OTP. Tài
khoản lưu ở `D:\MuseAI-API\.muse-state-tk2`; **app tự nhận khi mở lại**, không
phải sửa cài đặt. App chia mỗi video cho tài khoản đang ít việc nhất; một video
dùng đúng một tài khoản từ lúc tải lên tới lúc đọc kết quả. Tài khoản nào hết
đăng nhập thì app tạm bỏ qua 10 phút và làm lại video đó trên tài khoản khác.

## 3. Cài đặt (đã bật sẵn trên máy anh)

Trong `%LOCALAPPDATA%\BQHungVideo\.env`:

```
MUSE_CHON_DOAN=1
MUSE_LUI_GROQ=1
MUSE_AI_CLI=D:\MuseAI-API\.venv\Scripts\muse-ai.exe
MUSE_STATE_DIR=D:\MuseAI-API\.muse-state
```

Tuỳ chọn: `MUSE_SONG_SONG=10` (số video gửi Muse cùng lúc) ·
`MUSE_TIMEOUT_MAX=3600` (giây đợi tối đa / video) · `MUSE_LUI_GROQ=0` (Muse lỗi
thì đợi 1 phút rồi thử Muse lại, tối đa 12 lần/video, sau đó vẫn chuyển Groq).

Nhật ký từng lượt: `%LOCALAPPDATA%\BQHungVideo\logs\muse_<ngày>.log`.

## 4. Số đo thật (13/11/2026, 1 tài khoản)

- Video 19 phút: Muse trả lời sau 54-79 giây · cả bước phân tích 247 giây.
- Video 56 phút: bản nhẹ 22,9 MB · Muse trả lời 88 giây.
- 6 video cùng lúc: 6/6 trong 123 giây · 15 cùng lúc: 15/15 trong 147 giây,
  45/45 Part đúng độ dài anh đặt.

## 5. Rủi ro — đọc trước

- MuseAI-API là bản **không chính thức**, **không có giấy phép**. Meta đổi web là
  nó hỏng; khi đó app tự chuyển Groq.
- Dùng công cụ tự động có thể **vi phạm điều khoản** muse.ai → có thể **khoá tài
  khoản**.
- Muse trả lời trong ~1 phút cho video 20-60 phút, tức nó **chủ yếu đọc lời
  thoại**, không xem hết từng khung hình.
- Chỉ bước **chọn đoạn** dùng Muse. Chép lời, cắt gọn, chấm, tiêu đề, hậu kiểm
  vẫn dùng Groq/Gemini.
- CLI **không có lệnh xoá file**, nên thư mục `workspace/bq/...` (vài chục MB mỗi
  video) nằm lại trên Muse. Thỉnh thoảng nhờ Muse xoá `workspace/bq` trong chat.
- Phiên đăng nhập (`D:\MuseAI-API\.muse-state*`) là cookie dạng chữ thường —
  **không gửi cho ai**.

## Muse làm hết (mới, 13/11/2026)

Cài đặt AI → thẻ Muse có ô **"Muse làm luôn tiêu đề + chấm điểm + ghép mạch"** (mặc định bật).
Bật thì sau khi Muse chọn Part, app dùng luôn tiêu đề, điểm, mốc hook và hashtag Muse trả về,
không gọi Groq cho các bước đó nữa. Groq chỉ còn: chép lời (bắt buộc — Muse chậm và không có mốc
từng chữ cho phụ đề), và làm dự phòng khi Muse hỏng.

Video không có lời nói (nhạc, ASMR): Muse tự xem video để chọn, thay cho bước Groq xem hình 3-4 phút.

Đo thật: chọn 3 Part của 1 video còn ~85 giây và 0 lượt Groq (trước 158-201 giây).
