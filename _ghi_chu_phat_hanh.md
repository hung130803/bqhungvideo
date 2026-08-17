# BQ Hung Video v2.32.0

## Sửa được gì

### 1. Adam (ElevenLabs) — nay CHỌN ĐƯỢC trong hộp "Thay giọng nói"

Anh Hùng chụp màn hình hộp Thay giọng, Ngôn ngữ đích **Tiếng Anh**, combo
Giọng đọc chỉ có edge-tts, và hỏi *"đâu Adam đâu"*.

Adam vốn **có** trong app (hộp Lồng tiếng) nhưng bị lọc khỏi hộp này, với lý
do ghi thẳng trong mã: *"`doc_ban_dich` gọi thẳng `dubbing._synth_all` — hàm
này CHỈ biết edge-tts. Đưa id `el:` vào là câu nào cũng hỏng mà UI vẫn khoe có
chọn."* Bộ lọc **thành thật và đúng** — chỉ là chưa ai nối tiếp.

Nay đã nối, và nối ở **CỬA CHUNG** (`_synth_all` / `_synth_all_words`) chứ
không vá từng chỗ gọi. Nhờ vậy phủ luôn cả **3 chỗ gọi** của đường thay giọng
lẫn 3 chỗ của đường lồng tiếng — **không phải sửa một chỗ gọi nào**. Sót một
chỗ là video **lẫn hai giọng** mà app vẫn báo thành công.

Combo nay có **33 giọng ElevenLabs**, Adam đứng đầu nhóm.

### 2. Mốc chữ của Adam — ĐO RA TỐT NGANG edge-tts, không giống Piper

Việc này vốn được giao với giả định *"ElevenLabs không trả mốc, phải suy ra
như Piper, chắc sẽ tệ hơn edge-tts nhiều"*. **Đo xong thì giả định đó SAI ở
cả hai vế**, và đây là phần đáng giá nhất của lượt này.

**Vế một: ElevenLabs CÓ trả mốc thật.** Endpoint `/with-timestamps` trả mốc
từng ký tự theo audio gốc. Không phải suy ra, không tốn một lượt Groq nào.

**Vế hai: chất lượng mốc ngang edge-tts.** Đo bằng đúng thước đã đo Piper
(Groq chép ngược chính file tiếng), 2 bộ câu tiếng Anh THẬT, arm đối chứng
edge-tts chạy **đan xen trong cùng lượt**:

| | bộ 1 (462 mốc) | bộ 2 held-out (270 mốc) |
|---|---|---|
| **RUNG — Adam** | **47,2 ms** | **34,0 ms** |
| **RUNG — edge-tts** | **46,0 ms** | **35,0 ms** |
| **tỉ lệ Adam/edge** | **1,03×** | **0,97×** |

> **RUNG là con số quan trọng nhất** — đó là phần KHÔNG chữa được bằng một
> hằng số. Piper đo được **59,1 ms (1,53×)**; Adam **ngang edge-tts**.
> Adam KHÔNG cùng họ với Piper.

**Số thô thì trông xấu, và suýt nữa tôi tin nó.** Số thô: Adam 70,1 ms vs
edge 54,9 ms, và **57,7% số chữ hiện MUỘN hơn tiếng**. Nguyên nhân là một
**lệch HỆ THỐNG +58,0 ms** (bộ 2: +61,5 ms) trong khi edge là −35,0 (bộ 2:
−33,5). Lệch hệ thống thì trừ một hằng số là xong — nên tôi đã **định trừ
94 ms**.

**Thước thứ ba chặn lại đúng lúc.** Đo mốc chữ đầu so với lúc THẬT SỰ phát ra
tiếng (`silencedetect`, không dùng Groq):

| | mốc chữ đầu so với tiếng thật |
|---|---|
| edge-tts | −47,0 ms |
| **Adam** | **−37,9 ms** |

Hai máy đọc chỉ lệch nhau **~9 ms**, không phải 94 ms. Tức **cái lệch +58 ms
kia là của THƯỚC GROQ, không phải của ElevenLabs** — Groq đánh dấu đầu từ
khác nhau tuỳ chất giọng. Trừ 94 ms đi thì đã tự tay làm mốc sai thêm 94 ms
rồi khoe là đã chữa.

*(Giả định "độ trễ Groq không phụ thuộc giọng" đã được ghi là CHƯA CHỨNG MINH
từ lượt đo Piper. Nay đo được: nó **phụ thuộc giọng thật**. Mọi kết luận cũ
dựa trên lệch hệ thống của thước Groq cần đọc lại với lưu ý này.)*

### 3. Cảnh báo chi phí TRƯỚC khi chạy — tiền của anh Hùng

Thay giọng chạy **cả thư mục**. Gói free là **10.000 ký tự/tháng/tài khoản**,
đang xoay 5 tài khoản ≈ 50.000 — vài video là cạn.

Chọn giọng ElevenLabs rồi bấm Chạy thì hộp hiện: **ước lượng số ký tự cả mẻ**
(đo mẫu độ dài rồi nhân, theo số đo thật **1.273 ký tự/phút phim**) và **hạn
mức còn lại thật** trên mọi key. Nút mặc định là **"Không chạy"** — bấm Enter
theo phản xạ thì không tiêu tiền.

Bốn ca đều nói thẳng, không ca nào im lặng:
- đủ hạn mức → nói đủ
- **thiếu** → nói thiếu bao nhiêu, và nói rõ app sẽ **tự lùi edge-tts** cho
  các video còn lại (video vẫn ra, chỉ khác giọng) + ghi vào nhật ký
- **không đọc được hạn mức** → nói thẳng *"chạy tiếp là chạy mò"*, không coi
  như còn nhiều
- **không đo được độ dài** → nói không ước lượng được, **không hiện số 0** như
  thể miễn phí

Con số ghi rõ là **"ÍT NHẤT"**: các câu tràn khung phải đọc lại, mỗi lượt đọc
lại là một lượt tính tiền nữa mà ước lượng này chưa đếm.

### 4. Dòng tiến trình đã có tên video

Anh Hùng chụp hai dòng ghi `thay_giong — — thay_giong`: lặp tên loại việc, mà
chỗ tên video thì **trống**. Chạy cả thư mục thì không biết dòng nào là video
nào.

Gốc: job thay giọng chạy trên FILE trong thư mục anh Hùng chọn, không gắn với
bảng video trong máy, nên chỗ lấy tên bị rỗng và app lấp bằng mã loại việc.

Nay đọc tên từ chính việc đó: **`Thay giọng · kenh 21 · Chuyen la co that`**.
Payload rỗng/hỏng thì chỉ mất cái tên, **không làm sập bảng hàng đợi**.

### 5. Một lỗi NỔ được tìm ra khi làm việc này

Đường lùi edge-tts của ElevenLabs gọi `asyncio.run(...)` từ bên trong một
vòng lặp sự kiện đang chạy → **`RuntimeError` làm nổ cả lượt thay giọng**.

Chỗ nguy hiểm: nó **chỉ nổ ở nhánh LÙI**, tức đúng lúc ElevenLabs hết hạn mức
giữa chừng. Chạy thử vài video đầu thì êm ru; tới giữa mẻ 300 video mới chết.
Cổng 67 CA 4 bắt được ngay khi vừa nối xong.

---

## NÓI THẬT — những chỗ CHƯA được

**1. Giọng Gemini VẪN bị chặn, và đây là lý do bằng số chứ không phải quên.**
Gemini TTS **không trả mốc từng chữ**. Đường thay giọng dựng chữ THEO mốc
từng chữ ("nói đến đâu chữ hiện đến đó"), nhận Gemini vào là chữ quay lại
kiểu đổ cả cụm — đúng cái anh Hùng đã kêu. Ngoài ra nó có thể **tự đổi cả
track sang edge-tts** khi hết hạn mức mà không hỏi ai. Muốn mở Gemini thì
phải giải hai chuyện đó trước.

**2. ElevenLabs KHÔNG có tham số tốc độ đọc — bước "đọc nhanh cho vừa khung"
không chạy được với Adam.** v2.27.0 chữa được lỗi *"nói không mượt"* nhờ bảo
edge-tts **đọc nhanh hơn** thay vì ép `atempo` cắt-dán (đo được `tempo_max`
xuống **1,017–1,027** và chồng lấn **0 ms, 6/6 lượt**). ElevenLabs không nhận
tham số đó, nên câu tràn khung sẽ phải quay lại nhờ `atempo` như trước —
tức có thể chạm lại trần 1,5 và nghe kém mượt hơn edge-tts.
**Tôi CHƯA ĐO con số này với Adam** (một lượt đo là ~2.275 ký tự hạn mức của
anh Hùng cho đúng một video). Nói ra cơ chế, không bịa con số.
Bù lại, app **không bao giờ trộn hai giọng**: hai bước đọc lại được khoá
đường lùi, hết hạn mức thì **giữ nguyên bản Adam cũ** chứ không chèn câu
edge-tts vào giữa clip.

**3. Ước lượng chi phí là ƯỚC LƯỢNG.** Đo độ dài tối đa 12 video rồi nhân cho
cả mẻ (đo hết 300 video là bắt anh Hùng chờ hàng chục giây ngay lúc vừa bấm
Chạy). Video nói dày/thưa lệch nhau nhiều.

**4. Hạn mức đã tiêu cho lượt đo này: 1.924 ký tự** (47.833 → 45.909 trên 5
tài khoản). Cổng 67 chạy trong hồi quy **không gọi mạng**, không tốn thêm ký
tự nào.

**5. Chưa ai NGHE Adam đọc trên video thật.** Mọi số ở trên là đo máy.
File nghe thử để anh Hùng tự nghe: bấm nút **Nghe thử** trong hộp Thay giọng
sau khi chọn Adam.

**6. Giấy phép — CHỜ ANH HÙNG QUYẾT, tôi không tự ý gỡ.** `edge-tts` là
LGPLv3 kèm nguyên văn câu của tác giả *"It shouldn't be used for commercial
reasons"*. ElevenLabs đang **xoay vòng 5 tài khoản miễn phí**. Cả hai đều
đang dùng hằng ngày.
