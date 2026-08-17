# BQ Hung Video v2.31.0

## Sửa được gì

### 1. Hết "ít tiếng quá" — clip nay to đúng chuẩn nền tảng

Anh Hùng: *"tool cắt sao phần giọng nói ít tiếng quá nghe không hay"*.

Đo ra **hai lỗi**, cả hai đều thật, và lỗi thứ hai nặng hơn lỗi anh Hùng kêu.

**(a) Đường THAY TIẾNG chưa từng có bước chuẩn hoá độ to.** Bản anh Hùng xuất
ngày 16/08 đo được **−16,00 LUFS**. Vì sao đó đúng là *"ít tiếng"*:
YouTube/TikTok chỉ chuẩn hoá **XUỐNG**, không nâng lên — clip −16 phát ra nhỏ
hơn hẳn mọi clip khác trong cùng luồng vì chúng đều bị kéo về ~−14.

| | I (LUFS) | TP (dBTP) | LRA |
|---|---|---|---|
| GỐC Douyin | −5,07 | +6,16 | 3,30 |
| bản anh Hùng xuất 16/08 | **−16,00** | −2,26 | 2,10 |
| **sau khi sửa** | **−14,01** | **−1,44** | **2,10** |

**(b) Đường CẮT THƯỜNG và GHÉP ĐOẠN: 3/8 bản xuất VỠ TIẾNG.** Đường cắt chép
tiếng gốc nên không ai chặn đỉnh. Đo ffmpeg thật, 4 video thật, 8 bản xuất:

| đường | I trước | TP trước | LRA trước | I sau | TP sau | LRA sau |
|---|---|---|---|---|---|---|
| cắt thường (Douyin) | −6,50 | **+3,90** | 3,10 | −14,00 | −3,80 | 3,10 |
| ghép 2 đoạn (Douyin) | −5,90 | **+0,70** | 1,70 | −14,00 | −5,30 | 1,70 |
| cắt thường | −21,90 | **+0,90** | 7,00 | −21,40 | −1,20 | 7,10 |
| ghép 2 đoạn | −19,70 | −3,00 | 10,90 | −15,50 | −1,30 | 10,70 |
| cắt thường | −15,50 | −2,00 | 8,10 | −14,10 | −1,40 | 8,10 |
| ghép 2 đoạn | −15,40 | −2,50 | 3,00 | −14,00 | −1,20 | 3,00 |
| cắt thường | −10,20 | −1,60 | 18,20 | −14,00 | −3,30 | 18,20 |
| ghép 2 đoạn | −9,90 | −1,90 | 14,30 | −14,10 | −5,60 | 14,30 |

> **Đỉnh vượt 0 dBTP (vỡ tiếng): 3/8 → 0/8.**
> **Trải độ to giữa các clip: 15,75 LU → 7,40 LU.**

Nay mọi đường xuất đi qua **một cửa chuẩn hoá duy nhất** — cắt thường · ghép ·
recap · Mixed-Cut · clip đơn đều qua đó, không đường nào sót.

**Ba chốt an toàn:**
- Clip **gần câm** (dưới −45 LUFS) thì **BỎ QUA** — nâng lên là nâng nền nhiễu.
- Clip **đã đúng độ to** thì không mã hoá lại một byte nào (không thêm đời AAC).
- Chuẩn hoá **hỏng** thì giữ nguyên clip cũ, không mất video.

Hình **giống từng byte** (`-c:v copy`), độ dài không đổi, lệch tiếng-hình
**0 mẫu**.

**Cách áp là "nâng thuần + hạn đỉnh", KHÔNG dùng `loudnorm`.** Đã đo cả 3 cách:
`loudnorm` một lượt là bộ nén **ĐỘNG** (độ lệch chuẩn hệ số 0,277 dB — nó bóp
méo tỉ lệ giọng/nhạc); `loudnorm linear=true` **tự tụt về động mà mã thoát vẫn
0** khi thiếu chỗ trống (LRA 2,10 → 1,90 = nén dập, không một dòng cảnh báo).
Cách đang dùng có hệ số **hằng số 0,0055 dB** nên tỉ lệ giọng-nhạc không đổi
một ly. Trần đỉnh phải trừ **hai lần**: `alimiter` vọt +0,06 dB rồi **AAC vọt
thêm +0,19 dB**.

### 2. Nút "Nghe thử" trong hộp Thay giọng nói

Anh Hùng: *"với không có phần nghe thử à"*. Nay có.

Nút đi qua **đúng bước 4 của lượt xuất thật**, không phải một đường đọc riêng —
nghe thử thế nào thì xuất ra thế đó. Không chặn giao diện (**0 ms**); bấm lại
cùng câu/giọng thì lấy từ cache (**652 ms → 1 ms**).

**Nói ra NGUỒN THẬT, không nói cái bạn chọn:** chọn Piper mà máy chưa tải bộ đọc
thì app lùi về edge-tts và **ghi rõ là đang nghe edge-tts** — không để bạn tưởng
đang nghe Piper.

---

## NÓI THẬT — những chỗ CHƯA được

**1. Còn MỘT clip trong 8 bản xuất chưa tới đích −14 (dừng ở −21,40).** Đây là
lựa chọn CỐ Ý chứ không phải sót: clip đó có dải động rộng (LRA 7,0) và đỉnh đã
ở +0,90 dBTP, ép cho đủ to thì phải gọt quá ngân sách 6 dB = **nén dập tiếng**.
App thà để clip nhỏ hơn còn hơn làm hỏng dải động. Vì vậy trải độ to còn
**7,40 LU** chứ không về 0.

**2. Đường DỊCH: đã đóng, KHÔNG có lời giải.** Đã đo end-to-end và **bác cả hai**
hướng còn lại, bằng số, mỗi hướng 3 lượt đan xen trên video thật:

| | đang dùng | thước chấm | ngân sách giờ |
|---|---|---|---|
| ĐẠT theo thước % | 82,67 | 78,0 | **69,33** |
| câu cụt (mất nghĩa) | 1,33 | 3,00 | **5,67** |
| lượt Groq / video | **5,0** | **54,7** | **12,3** |

Hướng "thước chấm" tốn **10,9 lần** lượt Groq mà chất lượng nằm trong nhiễu của
chính cái thước. Hướng "ngân sách giờ" tốn 2,46 lần lượt mà **tụt 13,3 điểm** và
đẻ ra **4,3 lần câu cụt**. Cả hai đều đi giải trước một bài toán mà bước sau
(rút gọn + đọc nhanh) đã giải xong. **Muốn dịch tốt hơn phải tìm chỗ khác —
đừng đo lại hai hướng này.**

**3. Mốc chữ của giọng Piper vẫn kém edge-tts, và bản vá lần này KHÔNG kể là
chữa.** Đo bằng Groq chép ngược chính file tiếng, 413-426 mốc từ:

| | edge-tts | Piper |
|---|---|---|
| **rung** (đã trừ lệch hệ thống) | **38,6 ms** | **59,1 ms (1,53×)** |
| đuôi 90% | 81 ms | **138 ms (1,70×)** |
| **chữ hiện MUỘN hơn tiếng** | **0,5%** | **42%** |

Số thô (60,4 vs 65,1 ms) là **số lừa** — hai lỗi ngược dấu triệt tiêu nhau, phải
tách ra mới thấy. Bản vá cho chữ nhảy qua chỗ máy đang im, đo ghép cặp ra
**27 mốc tốt lên · 32 mốc TỆ ĐI · 354 y nguyên**, vì câu thật gần như không có
chỗ nghỉ (0,53 s trên 90,64 s = 0,6%). Giữ bản vá vì nó đúng, **nhưng không kể
là thành tích**. Hộp chọn giọng nay ghi thẳng đánh đổi đó.

**4. Chưa ai NGHE giọng Piper.** Mọi số ở trên là đo máy — tôi không có tai.

**5. Piper tốn 3,62× thời gian thật, 212 MB, và cần máy có Python 3.**

**6. Che chữ "quét cả khung" vẫn MẶC ĐỊNH TẮT.** Nguồn quay camera cố định thì
nó bôi hỏng khung hình. Đã đo cách tự phát hiện nhưng cả bộ đối chứng chỉ có
**1** video che oan — biên vỏn vẹn 2,3%, không đủ đặt ngưỡng. Và cách che hiện
tại vẫn **bỏ sót 9,1%** (4/44 cửa sổ có chữ mà không dò ra).

**7. Giấy phép giọng đọc — CHỜ ANH HÙNG QUYẾT, tôi không tự ý gỡ.**
`edge-tts` là LGPLv3 và kèm đúng câu của tác giả *"It shouldn't be used for
commercial reasons"* (đó không phải điều khoản LGPL — rủi ro thật nằm ở điều
khoản dịch vụ Microsoft). ElevenLabs thì đang xoay vòng **5 tài khoản miễn phí**.
Cả hai đều đang dùng hằng ngày, nên anh Hùng cần biết để quyết.
