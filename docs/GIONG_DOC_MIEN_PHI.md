# Tìm bộ giọng đọc miễn phí thay ElevenLabs — kết quả tra cứu + thử thật

*Ngày làm: 15/08/2026 · Việc TRA CỨU + THỬ, không sửa một dòng nào trong `app/`*

## Câu hỏi của anh Hùng

> *"phần giọng đọc xem kỹ có hỗ trợ nhiều giọng khác không, mà kiểu giọng có hiệu
> ứng nhấn nhá nhưng phải điều chỉnh khớp kỹ nhé, mà không mất phí như ElevenLabs"*

Ba đòi hỏi: **miễn phí** · **nhiều giọng + nhấn nhá** · **khớp thời gian kỹ**.

---

## TRẢ LỜI NGẮN — ĐỌC ĐOẠN NÀY LÀ ĐỦ

**Không có bộ nào đủ cả ba. Tôi nói thẳng thay vì đề xuất thứ dùng hai hôm rồi bỏ.**

Đã tra 24 bộ, cài thử thật 2 bộ đứng đầu, đo trên máy này. Kết quả:

| Điều anh cần | Bộ làm được | Bộ đó hỏng ở đâu |
|---|---|---|
| Khớp thời gian kỹ | **Piper** (mốc từng chữ THẬT — đã đo 300 mốc) | Chỉ có **1 giọng** dùng được, và **nhấn nhá KÉM hơn cái đang dùng** |
| Nhiều giọng + nhấn nhá | **VieNeu-TTS** (nhân bản giọng từ 3-5 giây mẫu) | **Không có một cách nào chỉnh thời gian** — sẽ phá hỏng bản vá v2.27.0 |
| Miễn phí | cả hai | — |

**Điều bất ngờ nhất, và là lý do tôi khuyên ĐỪNG đổi vội:** tôi đo độ nhấn nhá của
edge-tts (thứ app đang dùng, anh chê "đọc đều đều") thì nó **3,96** — còn Piper chỉ
**3,24**. Tức đổi sang Piper là giọng **đều hơn** chứ không sinh động hơn. VieNeu
được **4,43**, tốt hơn edge-tts nhưng chỉ hơn **12%** — bỏ ra hàng tuần công sức để
đổi lấy 12% là không đáng.

**Vấn đề thật của anh không phải "giọng đều" mà là "ít giọng quá".** edge-tts chỉ có
**đúng 2 giọng Việt** (HoaiMy nữ, NamMinh nam) — tôi đã hỏi máy chủ Microsoft và
đếm. Ba trăm kênh dùng chung 2 giọng thì kênh nào cũng giống kênh nào.

**Đề xuất: xem mục "Nên làm gì" ở cuối.**

---

## PHẦN A — BẢNG TRA CỨU

Cột quan trọng nhất là cột 2. App phải nhét giọng đọc vào đúng khung thời gian câu
gốc; bộ nào chỉ trả một file "đọc xong rồi đấy" mà không nói chữ nào ở giây nào,
cũng không cho chỉnh tốc độ, thì **không dùng được** dù giọng hay tới đâu.

### Nhóm 1 — CÓ tiếng Việt VÀ được phép kiếm tiền

| Bộ | 1. Tiếng Việt | 2. Mốc từng chữ / chỉnh độ dài | 3. Nhấn nhá | 4. Giấy phép — bán được không | 5. Máy cần gì | 6. Nhân bản giọng |
|---|---|---|---|---|---|---|
| **Piper** `vi_VN-vais1000` | **CÓ**, giọng riêng cho tiếng Việt | **CÓ MỐC TỪNG ÂM** (đã đo thật: 300 mốc → ghép ra 48 từ / 47 từ) + `length_scale` chỉnh tốc độ | Không chỉnh được. Đọc sao nghe vậy | **ĐƯỢC** — giọng CC BY 4.0 (phải ghi công). ⚠ Mã nguồn `piper-tts 1.6.1` là **GPL-3.0** | **63 MB**, CPU, **không cần torch**, đo được **25,8× nhanh hơn thời gian thật** | KHÔNG (phải huấn luyện lại) |
| **VieNeu-TTS** v3 Turbo | **CÓ**, tiếng Việt gốc, 48 kHz | **KHÔNG CÓ GÌ.** Đã thử 6 tên tham số, tất cả bị **nuốt im lặng** | Thẻ `[cười]` `[thở dài]` (thử nghiệm) | **ĐƯỢC** — Apache 2.0 cả mã lẫn model | **286 MB**, CPU, **không cần torch**, đo được **2,99×** | **CÓ** — 3-5 giây mẫu |
| **MOSS-TTS v1.5** | CÓ (1 trong 31 thứ tiếng) | Có đặt số token ≈ giây (1s ≈ 12,5 token) | Có | **ĐƯỢC** — Apache 2.0 | **4B–8B tham số**, cần GPU + torch, tải hàng GB | CÓ |
| `zalopay/vietnamese-tts` | CÓ | Chỉ `speed` | Qua giọng mẫu | ⚠ Ghi CC-BY-4.0 **nhưng dùng kiến trúc F5-TTS vốn cấm thương mại** — nguồn gốc đáng ngờ, chưa dám khuyên | Cần GPU + torch | CÓ |
| Piper `vi_VN-25hours_single` | CÓ | **0 mốc** (đo thật) | Không | ⚠ **"License: Unknown"** — không rõ, rủi ro | 63 MB, CPU | KHÔNG |

### Nhóm 2 — CÓ tiếng Việt nhưng **CẤM KIẾM TIỀN** (loại thẳng)

Anh kiếm tiền từ video nên cột giấy phép mà sai là hại anh. Những bộ dưới đây đều
**cấm dùng thương mại**, dù giọng hay tới đâu cũng không được đụng:

| Bộ | Vì sao bị loại |
|---|---|
| **F5-TTS** + mọi bản Việt hoá (`hynt`, `yukiakai`, `danhtran2mind`…) | Model gốc `SWivid/F5-TTS` là **CC-BY-NC** → mọi bản con thừa hưởng lệnh cấm. Tiếc, vì đây là bộ **duy nhất khoá cứng được tổng thời lượng** (`fix_duration`) |
| **viXTTS / XTTS-v2** (Coqui) | Model theo giấy phép CPML: *"chỉ dùng phi thương mại"*. Nặng hơn: công ty Coqui **đã đóng cửa 01/2024**, không còn ai để mua giấy phép. Dữ liệu viVoice cũng NC → **chặn kép** |
| **Fish-Speech / OpenAudio** | Đổi sang "Fish Audio Research License": *"No commercial rights are granted"* — cấm cả mã lẫn model |
| **ChatTTS** | Model CC BY-NC 4.0, ghi rõ cấm thương mại |
| **Higgs Audio v3** | "Research and Non-Commercial License". (Lưu ý: rất nhiều bài blog chép sai rằng nó Apache 2.0 — **sai**) |
| **VietTTS** (dangvansam) | Model CC-BY-NC |
| **viterbox** (bản Việt của Chatterbox) | CC-BY-NC 4.0, ghi thẳng tiếng Việt *"KHÔNG được sử dụng cho mục đích thương mại"* |
| **Spark-TTS** | Model CC-BY-NC-SA |
| **valtec-tts** | CC BY-NC 4.0 ("commercial use requires written permission") |
| **Piper** `vi_VN-vivos` | CC BY-NC-SA 4.0 |

### Nhóm 3 — KHÔNG có tiếng Việt (loại, dù nổi tiếng)

**Kokoro** (Apache 2.0, giấy phép đẹp nhất nhưng chỉ 9 thứ tiếng, không có Việt —
có bản cộng đồng `contextboxai/Kokoro-Vietnamese` nhưng không chính thức) ·
**IndexTTS2** (zh/en/ja/es/ar; hơn nữa tính năng khoá thời lượng mà nó quảng cáo thì
README ghi *"chưa bật trong bản này"*) · **Orpheus** · **Chatterbox** (MIT, nhưng
23 thứ tiếng không có `vi`) · **Kyutai TTS** (bộ **duy nhất** trả mốc từng từ đúng
nghĩa — tiếc là chỉ Anh/Pháp) · **VoiceStar** (có `--target_duration` thật, chỉ tiếng
Anh) · **MAGIC-TTS** · **Step-Audio-EditX**.

---

## PHẦN B — THỬ THẬT TRÊN MÁY NÀY

Cài trong môi trường ảo riêng ở `%TEMP%\bq_tts_thu`, **không đụng `.venv` của app**,
không cài vào Python hệ thống. Ổ C trước khi làm còn 414 GB (an toàn). Đọc cùng một
đoạn tiếng Việt 208 ký tự / 47 từ.

### B1. Piper — mốc từng chữ CÓ THẬT

Đây là điều tôi tưởng đã hỏng rồi lại hoá ra chạy được, nên ghi kỹ:

**Lần đo đầu ra 0 mốc.** Suýt kết luận oan là "Piper không có mốc". Tra ra hai chỗ
bẫy: mốc cần gói phụ `onnx` (cài bằng `pip install piper-tts[alignment]`) **và phải
bật lúc NẠP model**, không phải lúc đọc. Bật đúng thì:

| Đo | Kết quả |
|---|---|
| Số mốc âm thu được | **300 mốc** |
| Ghép thành mốc từng từ | **48 khối** (bài có 47 từ chính tả) → gần như một-đối-một |
| Mốc cuối so với độ dài tiếng | 10,252s / 10,252s — **khớp tuyệt đối** |
| Tốc độ (sau khi nạp model) | **25,8× nhanh hơn thời gian thật** |
| Nạp model | 2,21 giây (một lần) |

Mốc trả về là **từng ÂM** (`s` `ˈ` `i` `n`…), không phải từng TỪ — phải tự viết lớp
ghép âm thành từ. Tôi đã viết thử, ghép ra 48/47 nên việc này không khó.

### B2. Piper — ép vừa khung: được tới một mức rồi **DỪNG HẲN**

Câu thử đọc tự nhiên hết 4,8 giây. Ép về các khung nhỏ hơn bằng cách lặp:

| Khung đích | Số vòng | Kết quả | Lệch |
|---|---|---|---|
| 5,0 s | 4 | 5,050 s | **1,0 %** ✔ |
| 4,0 s | 6 | 4,040 s | **1,0 %** ✔ |
| 3,5 s | 6 | 3,780 s | 8,0 % ✘ |
| 3,0 s | 6 | 3,550 s | **18,3 %** ✘ |

**`length_scale` bão hoà.** Hạ xuống 0,45 vẫn ra 3,55 giây — không nén thêm được
nữa. Trần nén thật của Piper là khoảng **0,74 lần** độ dài tự nhiên.

Để so sánh cho công bằng: edge-tts đang dùng cũng bão hoà tương tự (`+50%` chỉ ra
1,455× theo số đã ghi trong CLAUDE.md, tức nén về ~0,69 lần). **Hai bên xấp xỉ
nhau**, Piper hẹp hơn một chút. Nghĩa là kiến trúc 4 bước hiện tại của app (cắt lề
im → rút gọn chữ → đọc nhanh → mượn khoảng lặng → `atempo`) vẫn dùng được nguyên xi
với Piper.

### B3. Piper — chỉ **1 trong 3** giọng Việt dùng được

| Giọng | Mốc từng âm | Chất lượng | Giấy phép | Kết luận |
|---|---|---|---|---|
| `vais1000-medium` (63 MB, 22 kHz) | **300 mốc** | tốt nhất | **CC BY 4.0** — bán được | **DÙNG ĐƯỢC** |
| `25hours_single-low` (63 MB, 16 kHz) | **0 mốc** | kém hơn | **Không rõ** | loại |
| `vivos-x_low` (28 MB, 16 kHz, 65 người) | **0 mốc** | kém nhất | CC BY-NC-SA — **cấm** | loại |

Giọng `vivos` còn có lỗi nặng: khi chạy nó in ra hàng loạt cảnh báo
`Missing phoneme from id map: 2 / 4 / 5 / 6` — đó chính là **các dấu thanh tiếng
Việt**. Bảng âm của nó thiếu dấu, mà tiếng Việt mất dấu là sai nghĩa. May là giọng
này đã bị loại vì giấy phép rồi.

**Nên: Piper cho anh đúng MỘT giọng Việt.** Anh đang có 2 giọng (edge-tts). Đổi sang
Piper là **ít giọng đi**.

### B4. VieNeu-TTS — giọng hay, nhưng không điều khiển được thời gian

Điểm cộng thật: **không kéo theo torch** (chỉ dùng `onnxruntime`), nên **không dính
bẫy access violation** khi chạy chung với Qt. 48 kHz. Có nhân bản giọng từ 3-5 giây
mẫu — tức anh muốn bao nhiêu giọng cũng được, kể cả giọng chính anh.

Nhưng cột quyết định thì trượt sạch:

| Đo | Kết quả |
|---|---|
| Mốc từng chữ | **KHÔNG có** |
| Chỉnh tốc độ / độ dài | **KHÔNG có** |
| Thử `speed` `length_scale` `duration` `target_duration` `rate` `tempo` | **cả 6 đều CHẠY BÌNH THƯỜNG nhưng KHÔNG ĐỔI GÌ** |
| Đọc cùng 1 câu 3 lượt | 5,920s · 5,920s · **6,160s** → lệch **240 ms (4,1%)** |
| Tốc độ | **2,99×** (chậm hơn Piper **8,6 lần**) |

**Dòng in đậm ở trên là chỗ nguy hiểm nhất của cả việc này.** Gọi
`infer(speed=0.7)` không báo lỗi, vẫn trả về file âm thanh nghe bình thường — nhưng
tốc độ không hề đổi. Đây đúng loại bẫy "chạy được, không một dòng báo, chỉ số đo tố
giác" mà cả repo này đang chống (cùng họ với `astats` cổng 53, `startswith` cổng 44,
`blend` cổng 41). Ai nối VieNeu vào app mà tin vào tên tham số sẽ tưởng mình đang
khớp thời gian trong khi không có gì xảy ra.

Thêm nữa: độ dài **không tiền định**. Cùng một câu, cùng một tham số, ra 3 độ dài
khác nhau. App cần nhét câu vào khung cố định thì đây là vấn đề thật.

### B5. "Nghe thử" — tôi đo, không nghe

**Nói thẳng: tôi không có tai, không thể mở file ra nghe.** Thay vì bịa ra cảm nhận,
tôi đo bằng cách kiểm chứng được: **cho máy chép lời NGƯỢC lại** (Groq
whisper-large-v3, tiếng Việt) rồi so với chữ gốc. Đọc ngọng hay sai dấu sẽ lộ ra
thành sai từ.

| Bộ đọc | Sai từ | Máy nghe nhầm thành gì |
|---|---|---|
| **Piper `vais1000-medium`** | **2,1 %** | chỉ khác "ba phút" → "3 phút" (whisper tự đổi số, **không phải lỗi đọc**) |
| **VieNeu v3turbo** | 4,3 % | cũng chỉ khác dấu câu + "3 phút" — **không phải lỗi đọc** |
| Piper ép về khung 5,0s | 4,5 % | không lỗi thật |
| Piper ép về khung 3,0s | **4,5 %** | **nén mạnh vẫn không ngọng thêm** |
| Piper `25hours_single-low` | 8,5 % | *"câu chuyện"* → **"công chuyên"**, *"mỗi ngày"* → **"mỗi night"** |
| Piper `vivos-x_low` | 10,6 % | *"chia sẻ"* → **"chỉ xe"**, *"câu chuyện"* → **"câu truyền"** |

**Điều này đọc được:** hai giọng đứng đầu (Piper vais1000 và VieNeu) phát âm tiếng
Việt **đúng, rõ, không ngọng** — mọi khác biệt còn lại chỉ là whisper viết số và dấu
câu khác đi. Hai giọng Piper còn lại **ngọng thật**, sai cả từ, và đúng như dự đoán
từ chuyện thiếu dấu thanh.

Điểm đáng giá riêng: Piper **ép về khung 3,0 giây (nén mạnh nhất) vẫn 4,5% y như
lúc đọc thường** — tức nén không làm méo tiếng. Khác hẳn `atempo` (cắt-dán sóng),
thứ đã đo được **6,765 dB méo phổ ở mức 1,50**.

### B6. Nhấn nhá — **đây là số làm tôi đổi ý**

Đo trên cùng một đoạn chữ. Thước: giọng lên xuống bao nhiêu (độ lệch chuẩn cao độ,
tính bằng nửa cung). Người thật kể chuyện thường 2,5-4.

| Bộ đọc | Nhấn nhá | Dải cao độ |
|---|---|---|
| **VieNeu v3turbo** | **4,43** | 13,86 |
| **edge-tts NamMinh — ĐANG DÙNG** | **3,96** | 13,30 |
| **edge-tts HoaiMy — ĐANG DÙNG** | **3,40** | 11,30 |
| Piper `vais1000-medium` | **3,24** | 10,53 |
| Piper `vivos-x_low` | 3,13 | 9,60 |
| Piper `25hours_single-low` | 2,54 | 8,37 |

**Kết luận ngược hẳn với điều tôi tưởng lúc đầu:**

- **edge-tts của anh KHÔNG hề "đều đều như máy"** — nó 3,40-3,96, nằm trong khoảng
  người thật kể chuyện. Cảm giác "đều đều" nhiều khả năng đến từ chỗ **chỉ có 2
  giọng nghe mãi**, chứ không phải giọng thiếu biểu cảm.
- **Piper KÉM HƠN edge-tts 0,72 nửa cung.** Đổi sang Piper là đi lùi ở đúng cái anh
  đang chê.
- **VieNeu hơn edge-tts 0,47 nửa cung (~12%).** Có hơn, nhưng ít.

*Lưu ý trung thực về phép đo:* tiếng Việt là tiếng có dấu, nên một phần dao động cao
độ là do **dấu thanh** chứ không phải cảm xúc. Nhưng cả 6 bộ đọc **cùng một đoạn
chữ**, phần do dấu thanh là như nhau ở mọi bộ, nên so sánh giữa các cột vẫn công
bằng.

---

## PHẦN C — CÔNG SỨC NỐI VÀO APP

App gọi giọng đọc qua 2 cửa trong `app/core/dubbing.py`:
`_synth_all()` (chỉ ra file) và `_synth_all_words()` (ra file **+ mốc từng từ** dạng
`[[đầu, cuối, từ], …]`). `app/core/thay_giong.py` dùng thêm `rate` để đọc nhanh lại.

**Tin tốt: app đã có sẵn đường lùi cho bộ không có mốc.** `dubbing.py` dòng 2899
chép lời lại bằng STT rồi ghép mốc — đang dùng thật cho ElevenLabs và Gemini. Nên bộ
thiếu mốc không chết hẳn, chỉ tốn thêm một lượt Groq mỗi câu.

### Nếu chọn Piper

| Việc | Ước lượng |
|---|---|
| Bọc Piper thành hàm giống `_synth_all` / `_synth_all_words` | 1-2 ngày |
| Viết lớp **ghép mốc ÂM → mốc TỪ** (Piper trả từng âm) | 1 ngày (đã thử được 48/47) |
| Đổi `rate="+20%"` → `length_scale` (nghịch đảo, phải lặp 4-6 vòng) | 1 ngày |
| Thêm ô chọn bộ đọc trong giao diện | 0,5 ngày |
| Cổng test mới (theo chuẩn repo: đo thật, thử phá) | 2-3 ngày |
| **Tổng** | **6-8 ngày** |

**Chỉ nên THÊM LỰA CHỌN, tuyệt đối không thay edge-tts.** Lý do: Piper nhấn nhá kém
hơn, chỉ 1 giọng, và 200-300 kênh đang chạy sản xuất bằng edge-tts.

Ba điều phải ghi vào thiết kế:
1. **Không cần tiến trình riêng** — Piper dùng `onnxruntime`, **không có torch**,
   nên không dính bẫy access violation như Demucs. Đây là ưu điểm lớn.
2. **Model 63 MB — có thể nhét thẳng vào `.exe`** (đang 155 MB → ~220 MB). Không
   phải làm cơ chế tải rời như torch/Demucs. Máy nhân viên không GPU vẫn chạy tốt
   (25,8× là đo trên CPU).
3. ⚠ **Giấy phép phải hỏi luật sư trước khi bán:** gói `piper-tts 1.6.1` là
   **GPL-3.0-or-later**. Nhúng thẳng vào app đóng gói có thể buộc **cả app phải mở mã
   nguồn**. Cách né thông thường là gọi Piper bằng **tiến trình con** (chạy file
   `.exe` riêng) thay vì import thư viện — nhưng đây là chuyện pháp lý, tôi không đủ
   thẩm quyền kết luận. Giọng `vais1000` thì sạch (CC BY 4.0, chỉ cần ghi công).

### Nếu chọn VieNeu

**Tôi không khuyên, và đây là lý do bằng số:** bản vá **v2.27.0** vừa chữa đúng bệnh
*"giọng lồng tiếng không mượt"* bằng cách **bỏ ép `atempo`, chuyển sang dùng `rate`
của edge-tts** — kết quả câu chạm trần từ 26,8% xuống **0,0%**, chồng lấn từ 574 ms
xuống **0 ms**. VieNeu **không có `rate`**, cũng không có bất cứ cách chỉnh tốc độ
nào. Nối VieNeu vào là **mọi việc khớp thời gian rơi hết trở lại lên `atempo`** —
tức đi lùi về đúng cái vừa chữa xong. Cộng thêm độ dài không tiền định 240 ms mỗi
lượt.

Nếu vẫn muốn dùng VieNeu, phải chấp nhận: chậm hơn Piper 8,6 lần · mỗi câu tốn thêm
một lượt Groq để lấy mốc · và **phải đo lại toàn bộ bảng lệch chữ-tiếng** trước khi
cho chạy sản xuất.

---

## NÊN LÀM GÌ — đề xuất theo thứ tự

**1. Việc rẻ nhất, làm được ngay: dùng hết giọng edge-tts đang có.**
Anh mới dùng 2 giọng Việt, nhưng edge-tts có **hàng trăm giọng** ở các thứ tiếng
khác, và app đã có sẵn `rate`/`pitch`. Đổi `pitch` (`+10Hz`/`-10Hz`) trên 2 giọng
Việt là ra thêm vài biến thể nghe khác hẳn, **0 ngày công, 0 rủi ro**. Nếu cái anh
thật sự cần là "kênh nào nghe khác kênh đó" thì việc này giải quyết được phần lớn.

**2. Nếu vẫn thiếu giọng: thêm Piper làm LỰA CHỌN THỨ HAI (6-8 ngày).**
Được thêm 1 giọng Việt nữa, mốc từng chữ tốt hơn cả edge-tts, chạy offline (không
cần mạng, không sợ Microsoft chặn), miễn phí vĩnh viễn. Đổi lại giọng đó nhấn nhá
kém hơn. **Phải hỏi luật sư về GPL trước.**

**3. Đừng đổi hẳn sang bộ nào cả.** edge-tts hiện tại đang làm tốt hơn tôi tưởng:
nhấn nhá 3,96 (cao hơn Piper), có mốc từng từ thật, có `rate`, và miễn phí. Ba trăm
kênh đang chạy ổn định bằng nó.

**4. Nếu sau này thật sự cần nhiều giọng riêng (nhân bản giọng của anh):** theo dõi
**VieNeu-TTS** (Apache 2.0, tiếng Việt gốc, đang phát triển nhanh) và **MOSS-TTS
v1.5**. Chờ tới khi chúng có cách chỉnh tốc độ rồi hãy nối vào.

---

## Những gì tôi CHƯA làm được — ghi thẳng

- **Chưa ai nghe bằng tai.** Tôi đo bằng máy chép lời ngược và bằng cao độ. Số nói
  Piper `vais1000` và VieNeu phát âm đúng, nhưng *"nghe có hay không, có hợp kênh
  không"* thì **phải anh nghe**. Tôi đã dọn hết model thử (1,4 GB) nhưng **giữ lại
  8 file tiếng ở `%TEMP%\bq_tts_thu\nghe_thu\`** (3,3 MB) — cùng một đoạn chữ đọc
  bằng 6 bộ khác nhau, mở lần lượt là so được ngay:
  `vn2.wav` (Piper vais1000) · `vieneu_thuong.wav` (VieNeu) ·
  `edge_vi-VN-HoaiMyNeural.mp3` + `edge_vi-VN-NamMinhNeural.mp3` (2 giọng đang
  dùng) · `giong_vivos.wav` + `giong_25hours_single.wav` (2 giọng Piper ngọng —
  nghe để thấy vì sao bị loại) · `ep_3.0_5.wav` (Piper nén mạnh nhất, nghe xem có
  méo tiếng không) · `vieneu_cuoi.wav` (thẻ cảm xúc `[cười]`).
- **Chưa thử MOSS-TTS v1.5** — bộ duy nhất còn lại có đủ tiếng Việt + Apache 2.0 +
  chỉnh được thời lượng. Bỏ qua vì nó 4B-8B tham số, cần GPU + torch + tải hàng GB,
  mà torch thì máy nhân viên không có. Nếu anh muốn, đây là việc tiếp theo đáng làm.
- **Chưa thử nhân bản giọng của VieNeu** (mới thử giọng mặc định).
- **Chất lượng tiếng Việt của MOSS-TTS và Higgs v3 là do nhà sản xuất tự nói** —
  tôi không tìm được đánh giá độc lập nào.
- **Giấy phép GPL của Piper tôi chỉ nêu ra, không kết luận** — chuyện pháp lý.

---

## Số đo tóm tắt để tra lại sau

| | edge-tts (đang dùng) | Piper vais1000 | VieNeu v3turbo |
|---|---|---|---|
| Giọng Việt có sẵn | **2** | **1** | không hạn chế (nhân bản) |
| Mốc từng chữ | CÓ (WordBoundary) | **CÓ** (300 mốc âm → 48 từ) | **KHÔNG** |
| Chỉnh tốc độ | `rate`, nén ~0,69× | `length_scale`, nén ~0,74× | **KHÔNG** |
| Nhấn nhá (nửa cung) | **3,40 / 3,96** | 3,24 | **4,43** |
| Sai từ khi chép ngược | *(chưa đo)* | **2,1 %** | 4,3 % |
| Nhanh hơn thời gian thật | (chạy trên mạng) | **25,8×** | 2,99× |
| Cần mạng | **CÓ** | không | không |
| Cần torch | không | **không** | **không** |
| Dung lượng | 0 | **63 MB** | 286 MB |
| Bán được không | được | được (⚠ GPL mã nguồn) | được (Apache 2.0) |

*Môi trường đo: Windows 10, RTX 3060 12 GB (không dùng tới — cả hai bộ chạy CPU),
Python 3.12 trong môi trường ảo riêng ở `%TEMP%`. Ổ C còn 413 GB sau khi làm.*

---
---

# LƯỢT 2 — "Có giọng Adam như ElevenLabs mà không mất phí không?"

*Ngày làm: 15/08/2026 · Tra cứu + thử thật · Không sửa một dòng nào trong `app/`*

## Câu hỏi của anh Hùng

> *"kiếm kỹ xem có cái giọng Adam như ElevenLabs không, tôi thấy nhiều bên họ
> làm sao có mà không mất phí gì"*

---

## TRẢ LỜI NGẮN — ĐỌC ĐOẠN NÀY LÀ ĐỦ

**Ba câu, mỗi câu là một tin anh cần biết:**

**1. Phần lớn "nhiều bên" đó KHÔNG dùng ElevenLabs.** Họ dùng giọng **Azure của
Microsoft** bọc lại rồi gọi là "TTS miễn phí". Đã có bằng chứng kỹ thuật, không
phải đoán.

**2. App của anh ĐANG CÓ SẴN giọng Adam của ElevenLabs, và đang xoay 5 tài
khoản miễn phí — việc này vi phạm điều khoản, khoá là khoá vĩnh viễn.** Nặng
hơn: gói miễn phí của ElevenLabs **cấm dùng để kiếm tiền**, nên kể cả xoay 1
tài khoản hay 100 tài khoản thì video có bật kiếm tiền vẫn là dùng sai. Đây là
phần nguy hiểm nhất của cả báo cáo, mời anh đọc kỹ mục 2.

**3. Nhân bản giọng CHẠY ĐƯỢC và giống rất tốt — tôi đã thử thật hôm nay —
nhưng nó vẫn không giải quyết được chuyện khớp thời gian.** Vẫn **chưa có** bộ
nào đủ cả năm điều: miễn phí + hay + khớp giờ + tiếng Việt + được bán.

---

## MỤC 1 — "SAO HỌ CÓ MÀ KHÔNG MẤT PHÍ"

Có đúng **bốn** con đường. Xếp theo mức phổ biến thật ngoài đời:

### Đường 1 (phổ biến nhất): họ không dùng ElevenLabs, họ dùng Azure

Các web "TTS miễn phí" mà anh thấy phần lớn là **vỏ bọc của Microsoft Azure**.
Bằng chứng cứng, không phải suy đoán:

| Trang | Bằng chứng chạy bằng gì | Cho kiếm tiền? |
|---|---|---|
| **ttsfree.com** | API bắt khai `voiceService` = `servicebin` (Bing/Microsoft) hoặc `servicegoo` (Google); danh sách giọng trả về `en-US-JennyNeural` — **đúng tên giọng Azure** | Có, ghi trong điều khoản |
| **luvvoice.com** | **Tự khai thẳng**: *"through Microsoft Azure AI Speech… Google Cloud Text-to-Speech"* | **KHÔNG** ở gói Free |
| **speechma.com** | Giọng mẫu duy nhất trong tài liệu là "Adri" = `af-ZA-AdriNeural` của Azure | Có |
| **ttsmaker.com** | Không tra ra được | Có |

**Điều này giải thích gọn câu hỏi của anh:** giọng nghe "hay như ElevenLabs" mà
miễn phí thường **không phải ElevenLabs**, mà là Azure — cùng họ với `edge-tts`
**app anh đang dùng sẵn**. Nói cách khác, một phần cái người ta khoe thì anh đã
có rồi.

⚠️ **Bẫy khi dùng mấy trang này:** chính TTSMaker viết trong điều khoản rằng họ
**không chịu trách nhiệm** nếu *"YouTube từ chối bật kiếm tiền cho video giọng
tổng hợp"*. Tức "miễn phí thương mại" chỉ nghĩa là **họ** không đòi tiền anh,
không có nghĩa YouTube chấp nhận.

### Đường 2: dùng đúng gói miễn phí — nhưng CẤM kiếm tiền

- **10.000 credits/tháng** cho mỗi tài khoản (trang giá chính thức).
- **Không được dùng thương mại.** Điều khoản §1(c) ghi nguyên văn: *"if you
  access or use our Services free of charge … you may only use the Services for
  **non-commercial purposes**"*. Trang hỗ trợ nói thẳng hơn: *"The free plan
  does **not** include a commercial license and **cannot be used for any
  commercial purpose**."*
- **Chính sách đã ĐỔI.** Trước đây ghi công "elevenlabs.io" thì được dùng
  thương mại. **Nay không còn.** Ghi công vẫn bắt buộc, nhưng ghi công **không**
  mở ra quyền kiếm tiền nữa. Ai nhớ luật cũ là đang nhớ nhầm.
- Giấy phép thương mại chỉ có từ gói **Starter 6 đô/tháng** trở lên.

### Đường 3: cày nhiều tài khoản — đây là chỗ app anh đang đứng

Xem mục 2 ngay dưới.

### Đường 4: key lậu / bên bán lại — có thật, và phần lớn là của ăn cắp

Nêu ra để anh hiểu vì sao "nhiều bên có", **không phải để làm theo**:

- Nghiên cứu bảo mật của **Sysdig** (2024) và **Cloud Security Alliance**
  (03/2026) mô tả một kiểu tấn công tên **"LLMjacking"**: kẻ gian ăn cắp API key
  rồi bán lại quyền dùng. Danh sách nền tảng bị nhắm có **ElevenLabs** — và có
  cả **Groq**.
- **Wiz** khảo sát 50 công ty AI hàng đầu (Forbes AI 50): **65%** bị lộ key,
  trong đó có một key ElevenLabs hạng doanh nghiệp nằm trần trong file cấu hình.
- Giá bán lại rẻ hơn 40-60% so với giá gốc — vì **vốn là của ăn cắp**.

**Vì sao anh tuyệt đối không nên đụng:** ElevenLabs là đối tác quét bí mật của
GitHub, key lộ ra là bị **tự động vô hiệu hoá**. Mua phải key ăn cắp thì tiền
mất, việc đang chạy đứt giữa chừng, và anh đứng về phía sai của pháp luật.

### Một tin riêng về giọng Adam

Giọng Adam **vẫn còn**, nhưng **đang bị khai tử**:

- Nhóm giọng mặc định cũ (có Adam) sẽ **hết hạn ngày 31/12/2026**.
- **Chỉ tài khoản mở TRƯỚC tháng 3/2026 mới còn dùng được** nhóm giọng đó.

Nghĩa là kể cả đi đường sạch, **xây kênh dựa trên giọng Adam là xây trên cát** —
sang năm nó biến mất. Đây là lý do độc lập với chuyện tiền nong để không bám vào
giọng này.

---

## MỤC 2 — APP ĐANG XOAY KEY: CÓ BỊ KHOÁ KHÔNG?

**Nói thẳng: CÓ RỦI RO THẬT, và app đang làm đúng cái điều khoản cấm.**

### Tôi tìm thấy gì trong máy anh

Đếm trong file cấu hình thật (`.env`) — tôi **không** in key ra, chỉ đếm:

| | Số key đang xoay |
|---|---|
| Groq | **41** |
| **ElevenLabs** | **5** |

Và trong mã nguồn `app/core/dubbing.py`, ghi chú do chính người viết app để lại
nói rõ mục đích:

> *"Nhiều key mỗi dòng/dấu phẩy (**tự xoay vòng khi hết hạn mức free 10k ký
> tự/tháng**)"*

Cùng file còn có bảng giọng nổi tiếng với **Adam đứng đầu danh sách**. Tức là:
**anh đã có sẵn giọng Adam trong app, chạy bằng 5 tài khoản miễn phí xoay
vòng.**

### Vì sao đây là vi phạm

**Ba điều khoản, cả ba đều bị chạm:**

1. **Cày nhiều tài khoản** — Prohibited Use Policy mục 9(t) của ElevenLabs cấm
   nguyên văn: *"**creating multiple accounts to exploit our free plans**"* (tạo
   nhiều tài khoản để khai thác gói miễn phí). Đây đúng là việc app đang làm.
2. **Một tài khoản miễn phí một người** — trang hỗ trợ ghi: *"We only allow
   **one free account per user and IP**."* Anh đang có 5.
3. **Gói miễn phí cấm thương mại** — §1(c) đã trích ở mục 1. **Đây là điều nặng
   nhất**: dù anh bỏ hết chỉ giữ 1 key, thì video có bật kiếm tiền vẫn là dùng
   sai mục đích.

### Bị khoá là mất hẳn, không xin lại được

Trang hỗ trợ của chính ElevenLabs, về lỗi "phát hiện hoạt động bất thường":

> *"This is regrettably a limitation we've needed to impose on the free tier to
> **avoid people creating multiple accounts**."*
> *"We are sorry about the inconvenience but **there is nothing we can do once
> the account has been flagged**."*

Đọc được hai điều: (a) hệ thống chặn này **sinh ra đúng để bắt việc cày nhiều
tài khoản** — không phải anh né được bằng khéo léo; (b) **khoá rồi là hết, không
có cửa kêu**.

### Còn 41 key Groq thì sao?

**Cũng có điều khoản cấm, nhưng nhẹ hơn nhiều về hậu quả thực tế.** Groq để điều
này ở "Acceptable Use Policy" (không nằm trong Terms nên dễ bỏ sót), cấm dùng
dịch vụ vượt hạn mức *"including by **registering multiple accounts**"*.

Hai điểm cần phân biệt cho đúng:

- Nếu 41 key đó là **41 tài khoản khác nhau** → chạm đúng câu cấm trên.
- Nếu là **nhiều key trong CÙNG một tài khoản** → **không vi phạm**, nhưng cũng
  **vô ích**: Groq ghi rõ *"Rate limits apply at the **organization** level, not
  individual users"* — hạn mức tính theo tổ chức, tạo thêm key trong cùng tài
  khoản không tăng thêm lượt nào.

### Tôi khuyên gì

| Việc | Vì sao |
|---|---|
| **1. Gỡ 5 key ElevenLabs miễn phí ra khỏi app** | Đang vi phạm 3 điều khoản cùng lúc, mà khoá là vĩnh viễn |
| **2. Nếu thật sự cần ElevenLabs: mua Starter 6 đô/tháng** | Rẻ hơn rủi ro rất nhiều, và **có giấy phép thương mại** — thứ gói miễn phí không bao giờ có |
| **3. Đừng xây kênh dựa vào giọng Adam** | Nó hết hạn 31/12/2026 |
| **4. Kiểm lại 41 key Groq là 41 tài khoản hay 1 tài khoản** | Nếu là 41 tài khoản thì nên gom lại; nếu 1 tài khoản thì đang không được lợi gì, chỉ tốn công quản |

---

## MỤC 3 — NHÂN BẢN GIỌNG CÓ PHẢI LỐI RA KHÔNG?

Luồng trước chốt: **VieNeu-TTS** giấy phép sạch (Apache 2.0), phát âm tốt, nhân
bản từ 3-5 giây mẫu — **nhưng không có bất kỳ cách chỉnh thời gian nào**. Việc
của lượt này là đi tiếp: **nhân bản có ra hồn không**, và **có đường vòng nào ép
được thời gian không**.

### 3.1 — Nhân bản CHẠY THẬT, và giống rất tốt

Tôi thử thật hôm nay. **Giọng mẫu do chính máy sinh ra bằng edge-tts, không lấy
giọng người thật của ai.**

Cách đo: nếu nhân bản có tác dụng thật thì bản sao phải **bám theo mẫu**. Tôi
đưa hai mẫu khác hẳn nhau (một nữ cao, một nam trầm) rồi xem hai bản sao có tách
ra đúng hướng không.

| | Giọng MẪU | Bản SAO | Lệch |
|---|---|---|---|
| Mẫu nữ (edge HoaiMy) | 228,6 Hz | **235,3 Hz** | **6,7 Hz** |
| Mẫu nam (edge NamMinh) | 135,6 Hz | **136,8 Hz** | **1,2 Hz** |
| *Đối chứng:* giọng mặc định VieNeu | — | 166,7 Hz | *61,9 Hz* |

**Hai mẫu cách nhau 93,0 Hz → hai bản sao cách nhau 98,5 Hz.** Bản sao bám mẫu
gần như tuyệt đối, trong khi giọng mặc định lệch tới 61,9 Hz. Màu âm cũng gần
lại: **6,89 → 3,50 dB**.

Phát âm **không xấu đi**: chấm bằng cách cho Groq chép lời ngược (3 lượt/bản),
cả giọng mặc định lẫn hai bản sao đều **2,1% sai từ** — mà chỗ "sai" duy nhất là
whisper viết "ba" thành "3", không phải đọc ngọng.

**Kết luận nhỏ: nhân bản giọng là thật, dùng được, và anh muốn bao nhiêu giọng
cũng được — kể cả giọng của chính anh.**

### 3.2 — NHƯNG: nhân bản CẦN `torch`, và đó là bẫy đã biết

**Đây là phát hiện quan trọng nhất của mục này, và nó SỬA LẠI kết luận của lượt
trước.** Lượt trước ghi *"VieNeu không kéo theo torch → không dính bẫy access
violation"*. Điều đó **chỉ đúng với giọng MẶC ĐỊNH**. Vừa gọi nhân bản là:

```
infer(ref_audio=...) -> ModuleNotFoundError: No module named 'torch'
```

Cài torch xong lại đòi tiếp `torchaudio`. Mà `import torch` sau khi Qt đã nạp =
**ACCESS VIOLATION**, `try/except` không chặn được — bẫy này repo đã đo và đã
phải chữa một lần cho Demucs (phải chạy tiến trình riêng).

Nghĩa là muốn dùng nhân bản thì phải **chạy tiến trình riêng**, cộng thêm tải
torch (~154 MB tải, ~700 MB trên đĩa), cộng máy nhân viên không có Python. Đúng
y bài toán đau đầu của Demucs.

> **Ghi lại một cái bẫy tôi đã sập, để người sau khỏi sập:** khi `ref_audio` báo
> lỗi thiếu torch, tôi thử sang tham số `use_ref_codes` và **nó chạy, không báo
> lỗi gì**. Phép đo đầu của tôi ra *"NHÂN BẢN CÓ TÁC DỤNG"*. **Sai.**
> `use_ref_codes` là **cờ bật/tắt**, truyền đường dẫn file vào chỉ làm nó thành
> "bật", giọng ra vẫn là giọng mặc định. Con số lúc đó (61,7 so với 63,5 Hz) gần
> như bằng nhau và **cả hai đều cách xa mẫu**, vậy mà tôi suýt kết luận là thành
> công. Đây đúng loại *"phép đo phát chứng nhận cho thứ vẫn hỏng"*. Bản đo sau
> tôi thêm **đối chứng âm**: bản sao phải gần mẫu **hơn hẳn** giọng mặc định thì
> mới tính là thật.

### 3.3 — Ép thời gian bằng ffmpeg: méo tới đâu?

Anh hỏi đúng câu cần hỏi. VieNeu không chỉnh được tốc độ, nên đường vòng duy
nhất là **sinh xong rồi kéo giãn**. Tôi đo hai cách ở đúng bốn mức anh nêu.

**Trước hết, đọc lại lý do app bỏ `atempo` ở v2.27.0** (đúng như anh dặn): gốc
rễ không phải tại `atempo` xấu, mà tại **edge-tts chèn ~0,20 giây im ở đầu và
~0,87 giây im ở cuối MỖI CÂU**. App cũ đo độ dài **kể cả lề im** rồi ép cho lọt
khung — tức **ép méo tiếng nói thật chỉ để nén khoảng im**. Chữa bằng cắt lề im
+ rút gọn chữ + dùng `rate` của edge-tts, kết quả câu chạm trần từ 26,8% xuống
**0,0%**.

#### Kết quả đo — phần bất ngờ nhất

Tôi đo bằng cách ép đi rồi ép về, so từng khung 32 mili-giây với bản gốc. **Đối
chứng bắt buộc** (chép file không lọc gì) ra **đúng 0,000 dB**, chứng tỏ chuỗi
đo không tự sinh lỗi.

| Phép | Méo (dB) | Đọc là |
|---|---|---|
| chép file, không lọc — **đối chứng** | **0,000** | chuỗi đo chuẩn |
| `rubberband` mức **1.0** (không ép gì) | **0,061** | trong suốt, đúng như phải thế |
| **`atempo` mức 1.0 (không ép gì)** | **5,982** | ⚠️ **phá tiếng dù không ép gì cả** |

**Dòng in đậm cuối là phát hiện đáng giá nhất của cả lượt này.** `atempo=1.0`
nghĩa là "giữ nguyên tốc độ" — đáng lẽ không được đụng vào một mẫu âm nào. Thực
tế nó **vẫn cắt-dán lại toàn bộ sóng** và làm lệch 5,982 dB, còn đẩy tiếng trễ
đi 180 mẫu. Trong khi `rubberband` ở cùng mức chỉ 0,061 dB.

Ép ở mức thật thì cả hai đều nặng tay như nhau (6,3-9,6 dB), **nhưng**:

| | `atempo` | `rubberband` |
|---|---|---|
| Ép **đúng** khung tới đâu | sai 0,02-0,28% | **sai 0,00%** |
| Có phá tiếng khi **không** ép gì | **CÓ (5,982 dB)** | không (0,061 dB) |
| Đổi cao độ (giọng the/trầm đi) | không (≤0,26 nửa cung) | không (≤0,09 nửa cung) |
| Tốn máy (file 13 giây) | 0,03-0,07 giây | 0,08-0,34 giây |
| **Có sẵn trong `bin/ffmpeg.exe` của app không** | có | **CÓ** — tôi đã kiểm |

#### Ép mạnh có làm ngọng không? — KHÔNG

Tôi cho Groq chép lời ngược, 3 lượt mỗi bản:

| Bản | Sai từ | Máy nghe nhầm thành gì |
|---|---|---|
| GỐC (không ép) | 4,3% | "ba"→"3", "nhé"→"nha" |
| atempo 0,8× / 1,25× / 1,5× | **4,3% · 4,3% · 4,3%** | y hệt bản gốc |
| rubberband 0,8× / 1,25× | **2,1% · 2,1%** | chỉ "ba"→"3" |
| rubberband 1,5× | 4,3% | y hệt bản gốc |

**Ép tới 1,5× vẫn không ngọng thêm một chữ nào.** Con số không hề xấu đi so với
bản gốc.

#### Nhưng đừng đọc bảng trên thành "vậy ép thoải mái"

**Phải nói thẳng chỗ này.** Máy chép lời đo **có ra chữ không**, nó **không** đo
**có êm tai không**. Bằng chứng: chính anh nghe bản v2.26.0 rồi báo *"giọng lồng
tiếng cảm giác không khớp, không mượt"* — lúc đó mọi con số máy đều đẹp. **Tai
anh mới là trọng tài.** Tôi đã để sẵn file để anh tự nghe (xem cuối báo cáo).

**Việc nên làm ngay, rẻ và không rủi ro:** ở những chỗ app **buộc phải** ép thời
gian, **đổi `atempo` sang `rubberband`**. Lý do bằng số: cùng ép đúng khung hơn
(0,00% so với 0,28%), giữ cao độ tốt hơn, và **không phá tiếng khi không cần
ép** — trong khi `atempo` phá 5,982 dB ngay cả lúc rảnh tay. `rubberband` **đã
có sẵn** trong ffmpeg app đang dùng, không phải tải thêm gì.

### 3.4 — Hai tin tốt bất ngờ cho VieNeu

**(a) VieNeu chèn lề im ÍT HƠN HẲN edge-tts.** Đây là số đo đi thẳng vào gốc rễ
bệnh "không mượt":

| | Lề im chiếm bao nhiêu file | Im ở cuối mỗi câu |
|---|---|---|
| edge-tts (đang dùng) | **33,9%** | 0,85-1,06 giây |
| **VieNeu nhân bản** | **7,6%** | **0,12-0,15 giây** |

Nghĩa là với VieNeu, phần "phải ép" **ít hơn nhiều** ngay từ đầu — vì không phải
ép để nén khoảng im ảo.

**(b) Mốc từng từ lấy được, và lấy rất chuẩn.** VieNeu không trả mốc, nhưng app
**đã có sẵn đường vòng** (chép lời lại bằng Groq — đang dùng thật cho ElevenLabs
và Gemini). Tôi đo thử trên chính giọng nhân bản:

| | Số mốc thu được | Chồng lấn | Mốc cuối so độ dài file |
|---|---|---|---|
| Bản sao nữ | **47/47 từ** | **0** | lệch 140 ms |
| Bản sao nam | **47/47 từ** | **0** | lệch 200 ms |

**Khớp một-đối-một với 47 từ của bài, không một mốc nào chồng lấn.** Cột "không
có mốc từng từ" của VieNeu vì vậy **không còn là cửa tử** — chỉ tốn thêm một
lượt Groq mỗi câu.

### 3.5 — Nhưng bức tường vẫn còn nguyên

Tôi thử lại **cả 6 tham số** trên giọng **đã nhân bản**:

| Tham số thử | Kết quả |
|---|---|
| `speed` · `length_scale` · `duration` · `target_duration` · `rate` · `tempo` | **cả 6 CHẠY BÌNH THƯỜNG, KHÔNG ĐỔI GÌ** |

Và độ dài **vẫn không tiền định**: cùng một câu, cùng tham số, đọc 3 lượt ra
5,280 / 5,120 / 5,120 giây — **lệch 160 ms (3,1%)**.

Cộng thêm: nhân bản **chậm hơn** giọng mặc định — chỉ **1,06-1,90×** thời gian
thật (giọng mặc định 2,99×).

---

## MỤC 4 — CÓ BỘ NÀO KHÁC KHÔNG? (tra tiếp ngoài 24 bộ cũ)

Tra thêm hơn 20 bộ nữa. **Bài học lớn nhất: đừng đi tìm "mốc từng từ" trong bộ
đọc nữa** — gần như không bộ hiện đại nào trả mốc thật, kể cả bộ quảng cáo là
có (chúng chạy chép lời ngược hậu kỳ, **đúng cách app anh đã làm sẵn**).

### Ứng viên mới đáng chú ý nhất: VoxCPM2

Giấy phép **Apache 2.0 cả mã lẫn trọng số** (đã đối chiếu 2 nguồn gốc), tiếng
Việt **chính thức**, nhân bản giọng, lại quảng cáo có cờ mốc từng từ. Nghe như
đúng thứ cần tìm.

**Tôi kiểm thẳng mã nguồn của nó (không tải trọng số vài GB) và kết quả là:
KHÔNG có tham số độ dài nào cả.** Hàm sinh tiếng của nó nhận:

```
text · prompt_wav_path · prompt_text · reference_wav_path ·
cfg_value · inference_timesteps · min_len · max_len · normalize · denoise
```

`min_len`/`max_len` là **trần cắt token** (chống sinh lỗi), không phải ép thời
lượng; `cfg_value`/`inference_timesteps` là núm chất lượng. **Cùng bức tường với
VieNeu.** Cộng thêm nó chạy CPU **chậm 4,5-9,5 lần thời gian thật** — với 300
kênh là không dùng được.

### Bảng những bộ CÓ đúng tính năng cần — và vì sao vẫn không dùng được

| Bộ | Có gì hay | Vì sao loại |
|---|---|---|
| **OmniVoice** | `duration` — **ép cứng bằng GIÂY**, tiếng Việt 8.481 giờ | 🔴 Trọng số **CC-BY-NC** — cấm thương mại |
| **F5-TTS** | `fix_duration` | 🔴 Trọng số **CC-BY-NC** |
| **MaskGCT** | `target_len` bằng giây | 🔴 **CC-BY-NC** |
| **ViiTorVoice-NAR** | Ép độ dài chính xác ±0,5 giây, Apache 2.0 thật | Không có tiếng Việt |
| **Supertonic 3** | `--speed`, 99 MB, CPU rất nhanh, có tiếng Việt | Không nhân bản được; trọng số **OpenRAIL-M** (nhiều blog chép nhầm là MIT) |
| **`facebook/mms-tts-vie`** | `speaking_rate` | 🔴 **CC-BY-NC** |
| **Confucius4-TTS** | Apache 2.0 sạch, nhân bản 3 giây, tiếng Việt | Không chỉnh được thời gian; bắt buộc CUDA |

**Một quy luật đáng nhớ:** hầu hết bộ có `duration` thật đều dính CC-BY-NC, vì
chúng huấn luyện trên bộ dữ liệu **Emilia** vốn cấm thương mại. Mã nguồn Apache
nhưng **trọng số** thì NC — đây đúng cái bẫy mà Higgs v3 đã sập.

⚠️ **Cảnh báo riêng về `zalopay/vietnamese-tts`** (lượt trước đã nghi ngờ, nay rõ
hơn): thẻ model khai `cc-by-4.0` (cho thương mại) **nhưng** khai luôn
`base_model: SWivid/F5-TTS` — tức **fine-tune từ trọng số CC-BY-NC**. Bản phái
sinh của thứ cấm thương mại **không tự tuyên bố lại thành cho phép** được. Đây
là bộ duy nhất có khả năng vừa `fix_duration` vừa tiếng Việt vừa sạch phép, nên
**đáng bỏ một email hỏi thẳng ZaloPay** xem họ huấn luyện từ đầu hay fine-tune.

### Tin tốt: đường lấy mốc từng từ có bản SẠCH PHÉP cho tiếng Việt

**MFA (Montreal Forced Aligner)**: mã **MIT**, mô hình tiếng Việt + từ điển Hà
Nội + G2P **đều CC BY 4.0** — sạch cả ba. Sai số **19,93 ms** (tốt nhất trong
các bộ đo được), chạy CPU, **không cần torch**.

⚠️ **Cạm bẫy phải tránh**: **WhisperX** mặc định tải mô hình tiếng Việt
`nguyenvulebinh/wav2vec2-base-vi-vlsp2020` = **CC-BY-NC**. Chạy
`whisperx --language vi` là **tự động kéo về một mô hình cấm thương mại** mà
không hề báo. Danh sách đen cùng loại:
`nguyenvulebinh/wav2vec2-base-vietnamese-250h`,
`khanhld/wav2vec2-base-vietnamese-160h` — nhiều blog ghi nhầm là Apache.

---

## MỤC 5 — KẾT LUẬN THẲNG: **CHƯA CÓ**

**Vẫn chưa có bộ nào đủ cả năm: miễn phí + hay như ElevenLabs + khớp thời gian +
tiếng Việt + được phép bán.** Tôi nói thẳng thay vì đẩy anh vào thứ dùng hai hôm
rồi bỏ.

Cái đã đổi so với lượt trước: **nhân bản giọng nay đã chứng minh là chạy tốt
thật**, và **hai cột từng tưởng là cửa tử của VieNeu đã có lối đi** (mốc từng từ
lấy được 47/47 qua Groq; lề im ít hơn edge-tts 4,5 lần). Cột **duy nhất** còn
chặn là **ép thời gian** — và cột đó **không có bộ nào giải được** trong phạm vi
miễn phí + thương mại + tiếng Việt.

### Bảng đánh đổi để anh tự chọn

| Đường đi | Được gì | Mất gì | Tiền | Rủi ro pháp lý |
|---|---|---|---|---|
| **A. Giữ nguyên edge-tts** *(đang chạy)* | Ổn định, 2 giọng, có mốc từng từ, có `rate` — 300 kênh đang chạy tốt | Chỉ 2 giọng, kênh nào cũng giống kênh nào | 0 | **Không** |
| **B. edge-tts + đổi `atempo`→`rubberband`** | Như A, cộng ép khung chuẩn hơn và bớt méo. **Rẻ nhất, làm được ngay** | Gần như không mất gì; ffmpeg đã có sẵn | 0 | **Không** |
| **C. Mua ElevenLabs Starter** | Giọng hay nhất, có Adam *(tới 31/12/2026)*, **có giấy phép thương mại** | Vẫn không có mốc từng từ; phụ thuộc mạng và nhà cung cấp | **6 đô/tháng** | **Không** |
| **D. VieNeu nhân bản** | Bao nhiêu giọng cũng được, kể cả giọng anh; Apache 2.0; lề im ít | **Cần torch → phải tiến trình riêng**; không ép được thời gian; chậm hơn; độ dài lệch 160 ms mỗi lượt | 0 | **Không** *(nếu dùng giọng của chính anh)* |
| **E. Xoay tài khoản ElevenLabs miễn phí** *(đang làm)* | Không tốn tiền | — | 0 | 🔴 **CAO — vi phạm 3 điều khoản, khoá vĩnh viễn** |
| **F. Mua key bán lại / key lậu** | — | — | rẻ | 🔴 **RẤT CAO — phần lớn là của ăn cắp** |

### Tôi khuyên theo thứ tự

1. **Làm ngay, 0 đồng, 0 rủi ro: gỡ 5 key ElevenLabs miễn phí ra.** Đây là việc
   gấp nhất trong cả báo cáo. Đang vi phạm mà lợi ích thu về chỉ là 10k ký
   tự/tháng mỗi tài khoản.
2. **Rẻ và đáng làm: đổi `atempo` sang `rubberband`** ở những chỗ buộc phải ép
   thời gian. Có sẵn trong ffmpeg của app, số đo tốt hơn ở mọi cột.
3. **Nếu thật sự cần giọng cao cấp: mua Starter 6 đô/tháng.** So với rủi ro mất
   sạch tài khoản thì đây là món rẻ. Nhưng **đừng xây kênh quanh giọng Adam** —
   nó hết hạn cuối 2026.
4. **Nếu cái anh cần là "nhiều giọng khác nhau cho 300 kênh": VieNeu nhân bản là
   đường đúng** — miễn phí vĩnh viễn, Apache 2.0, muốn bao nhiêu giọng cũng
   được. Nhưng phải chấp nhận làm cơ chế tiến trình riêng cho torch (giống
   Demucs), và chấp nhận khớp thời gian bằng `rubberband`.
5. **Việc đáng làm mà chưa ai làm: hỏi thẳng ZaloPay** về nguồn gốc trọng số
   `vietnamese-tts`. Nếu họ train từ đầu thật thì đó là bộ **duy nhất** có cả
   `fix_duration` + tiếng Việt + giấy phép thương mại.

---

## ĐẠO ĐỨC + PHÁP LÝ — PHẦN KHÔNG ĐƯỢC BỎ QUA

**1. Nhân bản giọng người thật mà không xin phép là SAI.** Nếu anh dùng đường
VieNeu nhân bản, chỉ được lấy:

- **giọng của chính anh**, hoặc
- giọng có **giấy phép cho phép rõ ràng**, hoặc
- giọng **do máy sinh ra** (như cách tôi làm trong lượt thử này).

Nhân bản giọng người khác — kể cả người nổi tiếng, kể cả "chỉ để thử" — là xâm
phạm quyền nhân thân về giọng nói, và nhiều nước đã có luật riêng cho việc này.

**2. KHÔNG nhân bản giọng Adam hay bất kỳ giọng riêng nào của ElevenLabs.** Đó
là tài sản của họ (và của diễn viên lồng tiếng đã cho họ mượn giọng). Trong lúc
tra, tôi **có** thấy hướng dẫn kiểu "tải giọng Adam về rồi clone lại bằng bộ mã
nguồn mở". **Việc đó tồn tại nhưng anh KHÔNG nên làm**, vì ba lý do: nó vi phạm
điều khoản ElevenLabs; nó xâm phạm quyền của diễn viên gốc; và nó biến toàn bộ
kho video 300 kênh của anh thành tài sản có tì vết pháp lý — thứ có thể bị gỡ
hàng loạt bất cứ lúc nào. **Tôi không ghi cách làm ở đây.**

**3. Giấy phép thương mại là cột dễ hại anh nhất.** Lượt này tra tận giấy phép
gốc trên GitHub/HuggingFace (không tin bài blog) và bắt thêm được **4 chỗ blog
ghi sai**:

| Bộ | Blog nói | Sự thật (đọc từ file LICENSE gốc) |
|---|---|---|
| **Supertonic 3** | MIT | Mã MIT, **trọng số OpenRAIL-M** |
| **Maya1** | có nhân bản giọng | **Không** — chỉ tả giọng bằng chữ |
| `dangtr0408/StyleTTS2-lite-vi` | `mit` *(ghi ở đầu thẻ)* | Thân bài ghi **CC-BY-NC-SA** |
| Họ **Emilia** (F5-TTS, OmniVoice, ZipVoice, MaskGCT) | Apache | Mã Apache, **trọng số CC-BY-NC** |

Cộng với **Higgs v3** đã bắt được ở lượt trước. **Quy luật: luôn tách "giấy phép
MÃ NGUỒN" và "giấy phép TRỌNG SỐ" — chúng thường khác nhau, và cái hại anh là
cái thứ hai.**

---

## FILE ĐỂ ANH TỰ NGHE

**Tôi không có tai** — mọi con số trên là đo bằng máy. Phần "nghe có hay không,
có hợp kênh không" thì **phải anh nghe**. Để sẵn ở `%TEMP%\bq_tts_thu\nghe_thu\`
(đã dọn hết model, chỉ còn 12 MB):

**Nhóm NHÂN BẢN — nghe theo đúng thứ tự 1→5 là thấy ngay nó bám mẫu tới đâu:**

- `NB_1_mau_nu.wav` · `NB_2_mau_nam.wav` — hai giọng **mẫu** đưa vào
- `NB_3_vieneu_macdinh.wav` — giọng **mặc định** của VieNeu *(đối chứng)*
- `NB_4_ban_sao_nu.wav` · `NB_5_ban_sao_nam.wav` — hai **bản sao**

**Nhóm ÉP THỜI GIAN — nghe để tự quyết có chấp nhận được không:**

- `EP_atempo_1.0x_khongepgi.wav` — **nghe cái này trước**: đây là bản *"không ép
  gì cả"* mà vẫn bị `atempo` phá 5,982 dB
- `EP_atempo_1.25x.wav` so với `EP_rubberband_1.25x.wav` — cùng một mức
- `EP_atempo_1.5x.wav` so với `EP_rubberband_1.5x.wav` — mức nặng nhất

*(8 file của lượt trước vẫn còn nguyên: `vn2.wav`, `vieneu_thuong.wav`,
`edge_*.mp3`, `giong_vivos.wav`, `giong_25hours_single.wav`, `ep_3.0_5.wav`,
`vieneu_cuoi.wav`.)*

---

## NHỮNG GÌ TÔI CHƯA LÀM ĐƯỢC — GHI THẲNG

- **Chưa chạy VoxCPM2 thật.** Tôi chỉ đọc mã nguồn của nó để xác nhận **không
  có tham số độ dài** — điều đó đủ để loại nó khỏi vai "lối ra", và tiết kiệm
  vài GB tải về. Nhưng **chất giọng tiếng Việt của nó thì tôi chưa nghe**. Nếu
  sau này anh cần thêm giọng và chấp nhận chậm, đây là bộ đáng thử đầu tiên.
- **Chưa đo trên máy nhân viên thật** (máy không GPU, không Python). Mọi số ở
  trên đo trên máy anh.
- **Chưa thử nối VieNeu nhân bản vào app.** Mới chứng minh từng mảnh chạy được
  (nhân bản tốt · mốc từng từ 47/47 · `rubberband` ép chuẩn), **chưa** ghép
  thành một dây chuyền chạy thật.
- **Chưa hỏi ZaloPay** về nguồn gốc trọng số — cần anh hoặc người có tài khoản
  đứng ra hỏi.
- **Số "méo tiếng" của tôi đo bằng phép ép-đi-rồi-ép-về**, nên nó nặng tay hơn
  thực tế (ép một chiều thì thiệt hại ít hơn). Điều **chắc chắn đúng** là phần
  **so sánh giữa hai cách** và phần **đối chứng ở mức 1.0** — vì cả hai đo bằng
  đúng một thước, và thước đó đã tự chứng minh ra 0,000 dB khi không có gì để đo.
- **Giấy phép GPL của Piper** (nêu ở lượt trước) vẫn chưa ai kết luận — chuyện
  pháp lý, cần luật sư.

---

## SỐ ĐO TÓM TẮT ĐỂ TRA LẠI SAU

| | edge-tts *(đang dùng)* | VieNeu **nhân bản** | VoxCPM2 |
|---|---|---|---|
| Số giọng Việt | 2 | **không hạn chế** | không hạn chế |
| Nhân bản giọng | không | **có** (mẫu 3-8 giây) | có (mẫu 5-30 giây) |
| Bám mẫu tới đâu | — | **lệch 1,2-6,7 Hz** | chưa đo |
| Mốc từng từ | có sẵn | **47/47 qua Groq**, 0 chồng lấn | hậu kỳ, như nhau |
| **Ép được thời gian** | **có (`rate`)** | **KHÔNG** | **KHÔNG** |
| Độ dài có tiền định | có | **không — lệch 160 ms (3,1%)** | chưa đo |
| Lề im chiếm | 33,9% | **7,6%** | chưa đo |
| Sai từ khi chép ngược | — | **2,1%** | chưa đo |
| Nhanh hơn thời gian thật | *(chạy trên mạng)* | 1,06-1,90× | 0,1-0,2× *(rất chậm)* |
| Cần torch | không | **CÓ** ⚠️ | **CÓ** |
| Bán được không | được | **được** (Apache 2.0) | được (Apache 2.0) |

**Ép thời gian — `atempo` so với `rubberband`** *(cùng một thước, đối chứng chép
file = 0,000 dB)*:

| | `atempo` | `rubberband` |
|---|---|---|
| Mức 1.0 — **không ép gì** | **5,982 dB** ⚠️ | **0,061 dB** |
| Ép đúng khung | sai 0,02-0,28% | **sai 0,00%** |
| Đổi cao độ | ≤0,26 nửa cung | **≤0,09 nửa cung** |
| Sai từ ở 1,5× | 4,3% *(= bản gốc)* | 4,3% *(= bản gốc)* |
| Tốn máy *(file 13 giây)* | 0,03-0,07 s | 0,08-0,34 s |

*Môi trường đo: Windows 10, máy anh Hùng, Python 3.12 trong môi trường ảo riêng
ở `%TEMP%` (đã xoá sạch sau khi đo). Groq whisper-large-v3 thật, 3 lượt mỗi
phép. ffmpeg của chính app (`bin/ffmpeg.exe`). Ổ C: 414 GB trống trước và sau
khi làm — đã dọn hết model và torch, chỉ giữ 12 MB file nghe thử.*
