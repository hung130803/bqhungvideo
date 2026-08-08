# Hướng dẫn dùng bản lớn v2.16.0

Gộp 45 commit từ nhánh `hieu-ung-video`. Bản này thêm **hiệu ứng điểm nhấn do AI
tự chọn theo cảnh**, sửa nghẽn khi chạy nhiều luồng, và vá phần phụ đề sót.

---

## 1. Anh phải làm gì? — Gần như KHÔNG

Hiệu ứng **đã bật sẵn ở mức "Nhẹ"** cho mọi mẫu, kể cả mẫu cũ. Cứ cắt như thường,
AI tự chọn. Không cần chỉnh gì nếu anh thấy ổn.

Chỉ khi muốn đổi thì mới vào: **Chỉnh mẫu → ô "Hiệu ứng điểm nhấn"**

| Mức | Số điểm nhấn / clip | Độ đậm | Dùng khi |
|---|---|---|---|
| **Tắt** | 0 | — | Kênh cần y hệt bản cũ |
| **Nhẹ** ← *mặc định* | 1–2 | 12% | Hầu hết kênh. Kín, không ai để ý là có hiệu ứng |
| **Vừa** | 3 | 18% | Kênh giải trí, muốn nhìn thấy rõ hơn |
| **Mạnh** | 3 | 25% | Kênh drama/gaming. 25% là **trần cứng**, không thể loè hơn |

> Mức "Mạnh" vẫn bị chặn ở 25% — đây là trần trong code, không phải khuyến nghị.
> Đo trên clip thật: hiệu ứng chỉ chiếm **3,2–4,9% thời lượng clip**. Không có
> chuyện phủ màu cả clip như mấy video tím anh chê.

---

## 2. AI chọn hiệu ứng kiểu gì?

Không phải random. Với mỗi clip AI chấm từng giây theo **tiếng** (RMS) và
**hình** (độ động), rồi chỉ đặt hiệu ứng vào chỗ vượt hẳn mức nền:

- Cảnh động mạnh → hiệu ứng nhóm "xáo động / giật"
- Cao trào tiếng → nhóm "nháy sáng / tăng tương phản"
- Cảnh tĩnh, người nói → **không đặt gì** (đây là chỗ hay bị lạm dụng nhất)

Anh xem được **lý do kèm số** trong nhật ký dây chuyền, mỗi dòng dạng:

```
giây 14,0 · Xáo dòng ngang · cảnh động mạnh — RMS 0,05 = 3,2x nền; động 10,0/10
```

Nếu clip **không có tiếng** (hoặc im lặng quá nửa), dòng này ghi `nền ~0` thay vì
một con số vô nghĩa — đây là lỗi vừa bắt được ở lượt kiểm cuối, cũ nó in ra
`49.274.701x`.

**Anh không phải làm gì để "dạy" nó.** Nếu thấy nó chọn dở ở clip nào, gửi tôi
dòng nhật ký của clip đó — có số nên tôi truy được ngay.

---

## 3. Ghép đoạn: chuyển cảnh mượt, phụ đề KHÔNG lệch

58 kiểu chuyển cảnh `xfade` ở chỗ nối các đoạn. Cái bẫy ở đây: `xfade` **ăn bớt**
thời lượng mỗi mối nối → tiếng và phụ đề trôi dần. Đã bù bằng cách lấy dư đúng
phần bị ăn từ đoạn trước.

**Đo:** lệch **0 ms** trên toàn timeline. Và khi để "Tắt", file xuất ra giống hệt
bản cũ — **PSNR 99 dB ở cả 5 mốc kiểm** (so với bản trước khi gộp). Nghĩa là 200–300
kênh đang chạy preset cũ **không bị đổi hình một chút nào**.

---

## 4. Chạy hàng loạt — cái này quan trọng nhất với anh

Trước đây 10 luồng cắt là app đơ. Nguyên nhân đo được: mỗi tiến trình ffmpeg
NVENC tự đẻ ~36–40 luồng, 10 job = **592 luồng** giành nhau CPU.

Đã chặn bằng hàng đợi slot ffmpeg. Đo lại:

| | Trước | Sau |
|---|---|---|
| Số luồng | 592 | **44** |
| Độ trễ UI | đơ | **13,7 ms/nhịp** |
| 50 kênh / 10 làn | 18,1 phút | **7,1 phút** |
| CPU-giây tiêu tốn | — | **+1,3%** (gần như không đổi) |

Nghĩa là bật hiệu ứng **không làm máy nặng thêm đáng kể** — chỉ đổi cách xếp việc.

Máy yếu (nhân viên): bật **"Tiết kiệm máy"** ở thanh bên, mỗi làn khoá về 1 job.

---

## 5. Phụ đề — vá đoạn nói mà không có chữ

Chỗ anh chê so với CapCut. Giờ sau khi chép lời xong, app tự dò các khoảng
**≥ 2 giây không có phụ đề**, kiểm bằng lọc dải giọng người xem có tiếng nói thật
không, rồi **chép lại riêng khoảng đó** và ghép vào.

Lọc 3 tầng (highpass 300Hz ×2 + lowpass 3400Hz) nên tiếng máy nổ / nhạc nền
không bị nhận nhầm là người nói — đo: giọng nói −27dB, ù 80Hz −67dB, nhạc 9kHz −73dB,
ngưỡng cắt −55dB.

Có lỗi gì ở bước này thì **giữ nguyên bản chép lời cũ**, thà thiếu chứ không hỏng.

---

## 6. Đa quốc gia

Đã test Nhật / Hàn / Anh / Việt — **0 lỗi**. Riêng tiếng Nhật trước đây bị đếm
sai (cả câu tính là 1 từ) làm hỏng 183 video ngắn, đã sửa bằng bộ tách từ CJK.

**Chưa test được:** Trung, Thái, Ả-Rập — quét cả ổ D: và C: **không có video thật
nào** của mấy thứ tiếng đó. Tôi không bịa số. Anh có video mẫu thì đưa tôi test.

---

## 7. Những thứ khác trong bản này

- **Bỏ Mixed-Cut** theo yêu cầu của anh
- **prodown**: bỏ qua video đang live / chờ live, không tự tải, không coi là video mới nhất
- Video **không có lời** vẫn được AI chọn đoạn bằng **hình**, không rơi về "cắt cơ bản"
- Tên clip lấy theo tên file gốc khi không có thoại
- Lỗi ffmpeg giờ hiện **đúng dòng nguyên nhân**, không chỉ 6 dòng cuối
- Chặn được ca ffmpeg trả "thành công" nhưng file ra **0 khung hình**

---

## 8. Cập nhật cho máy nhân viên

Máy nhân viên mở app sẽ tự thấy thông báo có bản mới → bấm cập nhật.

Bản `.exe` **đã đóng gói kèm** `app/assets/hieu_ung` (25 hiệu ứng frei0r + shader
+ 142 tiếng động). Trước đây thư mục này từng bị bỏ sót khỏi bản build, nhân viên
cài xong là mất sạch hiệu ứng mà app vẫn chạy bình thường nên không ai biết.

---

## 9. Chưa làm được — nói thẳng

1. ~~**6 shader libplacebo** chưa nối vào~~ — **ĐÃ NỐI** (08/08/2026). Kho hiệu
   ứng lên **31 kiểu**, trong đó "Nét gắt (GPU)" là kiểu hoàn toàn mới. Chúng
   chạy trên **card màn hình** nên gần như không ăn thêm CPU (đo **1,01×
   CPU-giây**; thời gian xuất +16% và chỉ ở clip THẬT SỰ dùng shader). Máy nhân
   viên không có card thì app **tự bỏ nhóm này**, không báo lỗi, không chậm đi.
2. **Chi phí hiệu ứng 1,98× thời gian thực**, mục tiêu đặt ra là 1,4× — chậm hơn dự tính
3. **Số luồng 2,67× số nhân**, mục tiêu 2× — chưa đạt trần mong muốn
4. **Chưa test trên máy nhân viên thật**, mới chỉ giả lập máy 2–4 nhân
5. **Chưa có video Trung / Thái / Ả-Rập** để test (mục 6)

Ba cái đầu là *chưa tối ưu hết*, không phải lỗi — app chạy đúng, chỉ là tôi đặt
mục tiêu cao hơn mức đạt được.
