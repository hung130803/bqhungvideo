# BQ Hung Video v2.39.0 — có gì mới

*Viết cho người dùng, không phải cho lập trình viên. Cái nào anh bấm thấy được
thì mới ghi ở đây.*

> **Máy anh đang chạy v2.37.0**, nên bản này gộp cả phần của v2.38.0 (chưa từng
> phát hành ra máy nào) lẫn phần mới của v2.39.0. Đọc hết một lượt là đủ.

---

## 0. NGẮN GỌN: DANH SÁCH GIỌNG TỪ 76 LÊN 455 DÒNG

Trước đây hộp **Thay giọng nói** chỉ cho chọn trong **76 giọng**. Bản này:

| | trước | **nay** |
|---|---|---|
| giọng edge-tts (miễn phí, cần mạng) | 76 | **322** |
| thứ tiếng | ~15 | **75** |
| giọng Việt chạy trên máy (VieNeu) | 0 | **20** |
| giọng Việt Piper | 1 | 1 |
| giọng OmniVoice (4 thứ tiếng) | 5 | 5 |
| giọng ElevenLabs (có key của anh) | 0 | **33** |
| giọng Vbee (trả tiền) | 0 | **3** |
| biến thể cao độ giọng Việt | 0 | **8** |
| **tổng chọn được trong hộp** | **76** | **392** |

Đếm cả dòng tiêu đề nhóm và dòng lối tắt thì danh sách dài **455 dòng**.
Cộng thêm **nhân bản giọng** (Chatterbox / VieNeu) là số giọng thực tế không
còn giới hạn — mỗi file mẫu anh đưa vào là một giọng mới.

**Mọi giọng trong danh sách đều đã được bắt đọc thử một câu thật rồi mới cho
hiện.** Giọng nào không ra tiếng thì không có mặt — đo lại lúc dựng bản này:
**0 giọng câm lọt vào danh sách**.

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
- Giọng tên **"Adam"** nay ghi kèm **TIẾNG ANH** (trước ghi *NGỜ NGUỒN*, đã
  bỏ). Hai chuyện, đừng lẫn:
  - **Nghi ngờ về nguồn: ĐÃ ĐO XONG, và đã loại.** Tên nó trùng một giọng bán
    tiền của ElevenLabs, nên đã lấy giọng đó về so bằng máy đo giọng
    (ECAPA‑TDNN, một hệ thứ ba). Kết quả: **hai người khác nhau** — độ giống
    **0,115–0,346**, trong khi cùng-một-người đo ra **0,756–0,931**. Đến hai
    giọng VieNeu khác nhau còn giống nhau hơn thế. Nên **không còn cảnh báo
    nguồn nữa**; giữ lại một cảnh báo đã chứng minh là vô căn cứ chỉ làm anh
    quen bỏ qua mọi cảnh báo.
  - **Cái phải nhớ khi dùng:** đây là **giọng tiếng Anh DUY NHẤT** trong 20
    giọng, 19 giọng kia đều là giọng Việt. Chọn nhầm cho video tiếng Việt là
    hỏng cả loạt. Vì thế nó đã bị **đẩy xuống cuối danh sách** (trước đây nó
    đứng đầu, chỉ vì xếp theo chữ cái mà "A" đứng trước).
  - File tiếng để anh **tự nghe** cả hai nguồn: `_NGHE_THU_ANH_HUNG\adam\`.
- **Chưa dùng để kiếm tiền vô tư được:** bảng giọng của bộ này **không khai
  giấy phép**. Chi tiết ở `docs/DANH_SACH_GIONG.md` mục 6.

---

## 3. BIẾT GIỌNG NÀO TRUYỀN CẢM, KHÔNG PHẢI DÒ MÒ

Mỗi giọng nay có **mức nhấn nhá** ghi ngay cạnh tên — số đo thật, cộng một
chữ dễ hiểu: *rất truyền cảm · truyền cảm · vừa · đều đều*. Trong mỗi nhóm,
giọng truyền cảm hơn được xếp lên trên.

**Mở khoá thêm rất nhiều giọng, theo hai bước:** bảng chấm nhấn nhá từ 82 lên
**191 giọng** (thêm 14 thứ tiếng; riêng tiếng Anh từ 15 lên **47 giọng**), rồi
**tách hẳn hai câu hỏi khác nhau ra**:

- *"giọng này có đọc ra tiếng không?"* — rẻ, chỉ cần một câu, **bắt buộc**;
- *"giọng này nhấn nhá bao nhiêu?"* — đắt, cần bộ 4 câu đúng tiếng, **tuỳ chọn**.

Gộp hai câu đó làm một chính là lý do **137 giọng của 60 thứ tiếng bị khoá vì
một lý do chẳng liên quan gì tới chúng**: không ai nghi ngờ giọng Ba Lan, chỉ là
chưa ai viết được bốn câu tiếng Ba Lan để chấm nó. Nay đã bắt cả 137 giọng đó
đọc thử thật, **322/322 giọng của 75/75 thứ tiếng đều có biên bản đọc được**, và
chúng vào danh sách với dòng ghi *"chưa đo nhấn nhá"* thay vì bị bịa một con số.

> Trong lượt kiểm đó có **4 giọng Inuktitut không đọc được** — truy ra không
> phải Microsoft gỡ giọng mà là thư viện app dùng không đọc nổi dạng tên của
> chúng. Đã chữa; cả 4 nay đọc ra tiếng thật.

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

Thêm **ô dán key Vbee** trong Cài đặt AI — dán vào là dùng được ngay.

**Đổi so với dự tính ban đầu: 3 giọng Vbee nay LUÔN hiện, kể cả khi chưa dán
key**, và dòng của chúng tự ghi **"cần key Vbee, xem vbee.vn"**. Lý do: giấu đi
thì anh không bao giờ biết có đường đó để mua. Chọn lúc chưa có key thì app đọc
bằng giọng thường và **ghi lại là nó đã lùi** — không im lặng.

---

## 9. NHÂN BẢN GIỌNG — ĐƯA FILE MẪU, APP ĐỌC BẰNG GIỌNG ĐÓ

Hai đường, dùng chung một chỗ nhập:

- **Chatterbox** — **23 thứ tiếng**, giấy phép MIT (bán được). Cần **GPU
  NVIDIA**: RTX 3060 đọc nhanh 1,53 lần thời gian thật, còn chạy bằng CPU chỉ
  0,25 lần (1 phút tiếng tốn 4 phút máy). Tải khoảng 5,5 GB.
- **VieNeu** — nhân bản giọng Việt từ file mẫu, tải 250 MB.

**Ba điều phải biết trước khi dùng Chatterbox** (đã ghi thẳng trên dòng chọn
giọng, không bắt anh nhớ):

1. **KHÔNG có tiếng Việt.** Ép nó đọc tiếng Việt thì nó **không báo lỗi và
   không câm** — nó đọc ra một chuỗi vô nghĩa rồi báo thành công. Vì thế app
   chặn sẵn: mã giọng nào ghi tiếng Việt sẽ tự lùi về giọng thường.
2. **Mọi file nó tạo đều bị đóng dấu chìm**, không tắt được (nhà làm ra bộ này
   ép như vậy).
3. Chữ bám lời kém hơn giọng thường một chút (lệch 76 ms so với 44 ms).

**Mẫu xấu thì app nói ngay, không để anh phát hiện sau vài chục video** — có
bước kiểm file mẫu trước khi nhận.

---

## 10. MỖI KÊNH MỘT GIỌNG RIÊNG (+ XOAY VÒNG)

Gán giọng riêng cho từng kênh, giống như mẫu-theo-kênh đang có. Có cả chế độ
**xoay vòng** để các video của cùng một kênh không đọc mãi một giọng.

**Chốt an toàn quan trọng nhất: KÊNH B KHÔNG BAO GIỜ RA GIỌNG CỦA KÊNH A.**
Trước đây cách xoay vòng dùng một phép băm ngẫu nhiên theo từng tiến trình, nên
**3 làn xuất song song có thể ra 3 giọng khác nhau cho CÙNG MỘT video** và sau
đó không tra lại được đã dùng giọng nào. Nay xoay vòng là **tiền định** — cùng
một video thì lượt nào cũng ra đúng một giọng, và phép kiểm tự động chạy ở một
tiến trình khác để chứng minh điều đó.

---

## 11. SỬA TIẾP LỖI "CHỌN GIỌNG NÀY RA GIỌNG KHÁC"

Đây là lỗi duy nhất anh coi là lỗi thật trong đợt sắp xếp giọng, nên nó được
kiểm bằng cách **gọi thật đường đọc rồi xem giọng đi vào đâu**, không phải bằng
cách đọc mã.

- **Giọng nhân bản (Chatterbox) hết chết âm thầm.** Mã giọng của nó chưa được
  khai báo ở cửa đọc chung, nên chọn giọng nhân bản của kênh mình lại nghe ra
  Hoài My. Đã nối.
- **3 giọng Vbee** cũng vậy — module đã viết xong mà chưa nối vào cửa đọc.
- Đo lại lúc dựng bản này: **6 trên 7 nguồn giọng đi đúng nguồn mình chọn**.
  Nguồn thứ 7 là **Vbee** — máy anh chưa có key Vbee nên nó lùi về giọng
  thường, đúng như dòng chọn giọng đã báo trước.
- **Chọn giọng · Lưu · mở lại vẫn là giọng đó** — trước đây có ca mở hộp rồi
  Lưu ngay là ghi đè mất giọng đã chọn.
- **Giọng "Adam" (VieNeu) được mở lại.** Nó từng bị chặn chỉ vì trùng tên với
  một giọng bán tiền của ElevenLabs; đã đem hai giọng đi so bằng máy đo giọng
  và kết luận **hai người khác nhau**, nên bỏ chặn. Vẫn giữ ghi chú là đây là
  **giọng tiếng Anh duy nhất** trong 20 giọng VieNeu.

---

## 12. SỬA LỖI MẤT MỐC CHỮ KHI CHẠY NHIỀU VIỆC CÙNG LÚC

Bộ **gióng hàng** (thứ lấy mốc từng chữ cho các giọng chạy trên máy) dùng chung
một thư mục làm việc, nên **hai việc chạy cùng lúc ghi đè file của nhau và mất
sạch mốc của cả một mẻ** — hậu quả là chữ không bám lời. Đã tách thư mục riêng
cho từng việc.

---

## CÁI CHƯA LÀM ĐƯỢC — NÓI THẲNG

- **20 giọng VieNeu chưa có mức nhấn nhá.** Cột đó để trống vì chưa đo. Bịa
  một con số cạnh tên giọng thì anh sẽ tin mà chọn. Cũng vậy với phần lớn trong
  137 giọng mới mở của các thứ tiếng ít gặp: chúng **đã chứng minh đọc được**
  nhưng chưa có bộ câu đúng tiếng để chấm nhấn nhá, nên dòng ghi *"chưa đo"*.
- **Chưa ai nghe bằng tai người.** Mọi con số trong tài liệu là máy đo. File
  tiếng để anh tự nghe nằm ở `_NGHE_THU_ANH_HUNG\`.
- **Giấy phép bộ giọng VieNeu chưa rõ** — xem mục 2.
- **MẤT TIẾNG CHƯA HẾT HẲN — đây là con số thật, không giấu.** Đo trên 4 video
  Trung dài tổng 20 phút: vẫn còn **45,6 giây / 3,8% thời lượng** có tiếng nói ở
  bản gốc mà bản thay tiếng bị im. Không rải đều: 2 video **0,0% và 0,1%** (coi
  như sạch), 2 video còn lại **6,5% và 5,4%**. Đang truy tiếp nguyên nhân.
- **Chatterbox và VieNeu phải tự tải model, và máy phải có Python 3.** Bộ cài
  không kèm sẵn (kèm thì bộ cài phồng từ 240 MB lên hơn 11 GB). Chatterbox còn
  cần GPU NVIDIA mới dùng được thật.
- **Giọng ElevenLabs chỉ hiện khi máy có key.** 33 giọng đếm được là của key
  đang có trên máy anh; máy nhân viên chưa dán key thì nhóm đó không hiện.
- **Chưa ai bấm thử bản này trên máy nhân viên thật.**
