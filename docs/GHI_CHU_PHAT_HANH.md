# BQ Hung Video v2.38.0 — có gì mới

*Viết cho người dùng, không phải cho lập trình viên. Cái nào anh bấm thấy được
thì mới ghi ở đây.*

---

## 1. DANH SÁCH GIỌNG ĐỌC — SẮP XẾP LẠI HẲN

Anh Hùng nói: *"phần chọn giọng nó không phân gì cả, rất lung tung, không biết
chọn sao"*. Bản này sửa đúng chỗ đó.

**Danh sách nay chia thành các nhóm có tiêu đề**, tiêu đề màu vàng không bấm
được:

- **KHUYÊN DÙNG cho \<tiếng đang chọn\>** — 5 giọng tốt nhất, miễn phí, chạy
  được ngay, không phải tải gì. Không biết chọn gì thì lấy đại một cái ở đây.
- **MIỄN PHÍ — giọng đúng thứ tiếng đang làm**
- **MIỄN PHÍ — giọng đọc được MỌI thứ tiếng**
- **TRÊN MÁY — miễn phí nhưng phải tải model về trước**
- **TRẢ TIỀN — tốn hạn mức hoặc tốn tiền**
- **MIỄN PHÍ — các tiếng khác** (đẩy xuống đáy)

**Ba thứ đổi theo:**

1. **Chọn Tiếng Việt thì giọng Việt lên đầu tiên.** Trước đây nó nằm lẫn giữa
   mấy chục giọng tiếng Anh.
2. **Mỗi dòng tự nói ra tiền.** Đọc hết một dòng là biết: giọng này miễn phí
   hay tốn tiền, có phải tải gì không, đọc truyền cảm tới mức nào.
3. **Rê chuột lên một dòng** thì hiện thêm phần chữ dài: giấy phép, điểm yếu
   đã đo được, phải tải bao nhiêu.

**Vài giọng cố ý hiện HAI LẦN.** Nhóm "KHUYÊN DÙNG" là lối tắt nên nó chép lại
giọng của nhóm dưới; dòng lối tắt ghi rõ **"[lối tắt — cùng giọng ở nhóm
dưới]"** nên không nhầm được.

> **Giọng na ná nhau giữa các nguồn thì giữ hết, không gộp** — đúng như anh
> dặn: *"chỗ free chỗ mất tiền ấy, cứ thêm"*.

**Sửa hai lỗi hiển thị:** trước đây mỗi dòng in **hai lần** cùng một mức nhấn
nhá (*"nhấn nhá 4,7 rất truyền cảm - nhấn nhá 4,7 rất truyền cảm"*); và nhóm
"khuyên dùng" hiện **Nam Minh hai lần** nên chỉ còn 3 giọng thay vì 5. Nay
đúng 5 giọng, mỗi dòng một số.

---

## 2. THÊM 20 GIỌNG VIỆT MỚI (VieNeu) — CHẠY TRÊN MÁY

Nằm trong nhóm **"TRÊN MÁY"**, mỗi dòng ghi thẳng **"cần tải 250 MB"**.

Đủ giọng nam/nữ, giọng Bắc – Trung – Nam, kiểu đọc tin tức / kể chuyện / đọc
truyện / tự nhiên. Ngoài ra còn **nhân bản giọng từ file mẫu của anh**.

- **Máy chưa tải model thì vẫn thấy chúng**, dòng mở đầu bằng **"CHƯA TẢI
  (250 MB)"**. Chọn lúc chưa tải thì app đọc bằng giọng thường và ghi lại là
  nó đã lùi — không im lặng.
- Giọng tên **"Adam"** có ghi kèm **NGỜ NGUỒN**: tên nó trùng một giọng bán
  tiền của hãng khác mà không kiểm được nguồn gốc. Cân nhắc trước khi đăng
  kênh.
- **Chưa dùng để kiếm tiền vô tư được:** bảng giọng của bộ này **không khai
  giấy phép**. Chi tiết ở `docs/DANH_SACH_GIONG.md` mục 6.

---

## 3. BIẾT GIỌNG NÀO TRUYỀN CẢM, KHÔNG PHẢI DÒ MÒ

Mỗi giọng nay có **mức nhấn nhá** ghi ngay cạnh tên — số đo thật, cộng một
chữ dễ hiểu: *rất truyền cảm · truyền cảm · vừa · đều đều*. Trong mỗi nhóm,
giọng truyền cảm hơn được xếp lên trên.

**Mở khoá thêm rất nhiều giọng:** bảng đo từ 82 lên **191 giọng**, phủ thêm
14 thứ tiếng; riêng tiếng Anh mở từ 15 lên **47 giọng**.

> Số này chỉ đo **độ lên xuống của giọng**, không nói giọng hay hay dở. Kể
> chuyện thì cần cao; đọc tin tức thì giọng đều lại dễ nghe hơn. Và **chỉ so
> được trong cùng một thứ tiếng**.

---

## 4. SỬA LỖI CHỌN GIỌNG NÀY RA GIỌNG KHÁC

- **Giọng "Nữ trung niên ấm" (OmniVoice)** chọn vào lại ra giọng khác — đã
  sửa.
- **20 giọng VieNeu** suýt dính đúng lỗi đó: module giọng đã viết xong nhưng
  chưa nối vào chỗ đọc, nên chọn "Minh Đức" sẽ nghe ra giọng khác. Đã nối và
  có phép kiểm tự động canh.

---

## 5. TIẾNG VÀ HÌNH

- **Hết mất tiếng ở những đoạn không được đọc lại.** Trước đây có đoạn bị câm;
  nay giữ nguyên giọng gốc ở đó và chỉnh cho mức tiếng khớp với giọng mới, để
  không có chỗ nhô to bất thường.
- **Thêm cách "chỉnh video theo giọng".** Trước đây chỉ có một chiều là ép
  giọng đọc nhanh lên cho vừa khung hình, nghe méo. Nay có thể nhích video
  chậm lại một chút (nhiều nhất 1,25 lần) để giọng đọc tự nhiên.
- **Chữa tiếng "bị bè"** bằng cách bù lại dải cao theo chính video gốc.

---

## 6. HỘP THAY GIỌNG BỚT RỐI

- **9 ô chỉnh chữ gom vào MỘT nút "Chỉnh chữ..."** — hộp thoáng hẳn.
- **Sửa thanh tiến độ chạy ngược** và bảng tiến độ bị bóp còn 2 điểm ảnh.
- **Sửa lỗi mở hộp Thay giọng là app văng** (bản trước mọi việc thay giọng
  đều báo lỗi).

---

## 7. AN TOÀN

- **Sửa một lỗi nguy hiểm: app có thể xoá nhầm cả thư mục đang làm việc.**
  Khi đường dẫn bị rỗng, lệnh dọn rác hiểu thành "thư mục hiện tại" rồi xoá
  sạch. Đã bịt, và bịt thêm 5 chỗ khác cùng kiểu.
- **Không chỗ nào in key API ra file nữa.** Trước đây một phép kiểm ghi nguyên
  văn key Groq ra file log.

---

## 8. VBEE

Thêm **ô dán key Vbee** trong Cài đặt AI — dán vào là dùng được ngay. Chưa dán
thì giọng Vbee không hiện, nên không bấm nhầm vào chỗ mất tiền.

---

## CÁI CHƯA LÀM ĐƯỢC — NÓI THẲNG

- **20 giọng VieNeu chưa có mức nhấn nhá.** Cột đó để trống vì chưa đo. Bịa
  một con số cạnh tên giọng thì anh sẽ tin mà chọn.
- **Chưa ai nghe bằng tai người.** Mọi con số trong tài liệu là máy đo. File
  tiếng để anh tự nghe nằm ở `_NGHE_THU_ANH_HUNG\`.
- **Giấy phép bộ giọng VieNeu chưa rõ** — xem mục 2.
