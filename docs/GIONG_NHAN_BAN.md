# LƯỢT 9 — NHÂN BẢN GIỌNG: anh Hùng có nhiều giọng Việt MIỄN PHÍ được không?

*Ngày 18/08/2026. Đây là hy vọng cuối cho hướng miễn phí, sau khi 8 lượt trước
đã chốt: 3 giọng Vbee anh muốn **chỉ có đường mua** (điều khoản Vbee cấm cấp
phép lại).*

**Không sửa một file nào trong `app/`. Không đẻ một luồng con nào. Không tăng
version, không tag, không push.**

> **Cách đọc tài liệu này:** phần A là câu trả lời. Phần B, C, D là số đo để
> chứng minh. Nếu chỉ có 2 phút, đọc phần A.

---

# PHẦN A — TRẢ LỜI NGẮN

*(điền ở cuối, sau khi đủ 3 ý — xem phần B, C, D)*

---

# PHẦN B — Ý 1: NHÂN BẢN CÓ RA GIỌNG KHÁC NHAU KHÔNG?

## B0. Câu hỏi này là gì, nói cho dễ hiểu

"Nhân bản giọng" = đưa cho máy nghe **5 giây** giọng một người, rồi máy đọc bất
kỳ câu nào **bằng giọng người đó**.

Nếu nó chạy thật: đưa 8 người khác nhau → được **8 giọng khác nhau**. Anh Hùng
có 8 giọng cho 8 kênh, miễn phí.

Nếu nó không chạy: đưa 8 người → máy vẫn đọc bằng **1 giọng mặc định** của nó,
chỉ là mình tưởng bở. **Lượt 4 đã sập đúng cái bẫy này** — truyền đường dẫn vào
một tham số tên `use_ref_codes`, nhưng tham số đó chỉ là cờ bật/tắt, nên đưa
đường dẫn vào chỉ làm nó thành "bật", **giọng ra vẫn y hệt giọng mặc định**.

Nên lần này tôi đo có **đối chứng âm**: chạy thêm một lượt **không đưa mẫu nào**
để biết "giọng mặc định" cao bao nhiêu. Nếu 8 bản sao đều bằng giọng mặc định →
nhân bản KHÔNG chạy.

## B1. Nguyên liệu — và chúng có hợp pháp không

Tôi kiểm giấy phép **từ máy chủ gốc**, không đọc bài giới thiệu:

| Thứ dùng | Nguồn thật | Giấy phép | Bị khoá không |
|---|---|---|---|
| **Mẫu giọng người thật** | `fsicoli/common_voice_17_0` (Mozilla Common Voice 17) | **CC0-1.0** | không |
| **Máy đọc** | `pnnbao-ump/VieNeu-TTS-v3-Turbo` | **Apache 2.0** | không |
| **Bộ mã tiếng** kèm theo | `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | **Apache 2.0** | không |

**CC0 nghĩa là gì:** người thu âm đã **hiến giọng vào phạm vi công cộng**, từ bỏ
mọi quyền. Đây là giấy phép rộng nhất có thể có — rộng hơn cả CC-BY (CC-BY còn
bắt ghi tên, CC0 thì không bắt gì cả). Trang gốc của bộ dữ liệu ghi thẳng
`license: cc0-1.0`.

**Apache 2.0 nghĩa là gì:** dùng thương mại thoải mái, không phải trả tiền,
không phải mở mã của mình.

> **Tôi KHÔNG đụng vào giọng Vbee / FPT / Zalo / ElevenLabs.** Anh Hùng có hỏi,
> tôi đã từ chối ở lượt trước và vẫn từ chối. Toàn bộ 8 giọng dưới đây là người
> đã **tự nguyện hiến giọng** cho Mozilla.

Tôi chọn **8 người đọc khác nhau** trong bộ Common Voice, cố ý chọn trải từ
giọng trầm nhất tới giọng cao nhất (mỗi người 1 mẫu, dài 4–7 giây).

## B2. KẾT QUẢ — bảng cao độ giọng

Thước đo là **cao độ (F0)** — số đo "giọng trầm hay bổng", tính bằng Hz. Giọng
nam thường 85–180 Hz, giọng nữ thường 165–255 Hz. Mỗi ô là **trung vị của 6 câu**.

| | **MẪU** (người thật) | **BẢN SAO** (máy đọc) | lệch | giới tính (theo hồ sơ) |
|---|---|---|---|---|
| M0 | 102,6 Hz | **98,2 Hz** | −4,4 | ? |
| M1 | 115,5 Hz | **106,4 Hz** | −9,2 | ? |
| M2 | 118,5 Hz | **115,6 Hz** | −3,0 | nam |
| M3 | 129,0 Hz | **130,1 Hz** | +1,1 | nam |
| M4 | 140,4 Hz | **143,2 Hz** | +2,8 | nam |
| M5 | 150,9 Hz | **168,4 Hz** | +17,5 | ? |
| M6 | 197,5 Hz | **217,0 Hz** | +19,4 | nữ |
| M7 | 296,3 Hz | **273,5 Hz** | −22,8 | ? |
| **MD** | *(không đưa mẫu nào)* | **160,9 Hz** | — | ← **ĐỐI CHỨNG ÂM** |

## B3. Đọc bảng trên: NHÂN BẢN CHẠY THẬT

**1. Bản sao bám theo mẫu, không trượt phát nào.**
- Thứ tự trầm→bổng của 8 bản sao **trùng khít** thứ tự của 8 mẫu:
  **28/28 cặp giữ đúng thứ tự** (Spearman = **1,0000** — tức khớp tuyệt đối).
- Độ khớp theo trị số: Pearson **0,9765**.
- Bản sao lệch khỏi mẫu trung bình chỉ **10,0 Hz** (gần nhất 1,1 · xa nhất 22,8).

**2. Đối chứng âm sạch — không dính bẫy lượt 4.**
Giọng mặc định (không đưa mẫu) là **160,9 Hz**. Nếu nhân bản không chạy, cả 8
bản sao phải **xúm quanh 160,9 Hz** và độ tản mát phải ≈ 0.

| Nếu nhân bản KHÔNG chạy | Số đo THẬT |
|---|---|
| 8 bản sao đều ≈ 160,9 Hz | trải từ **98,2 → 273,5 Hz** |
| độ tản mát ≈ 0 Hz | **60,9 Hz** |
| cách giọng mặc định ≈ 0 Hz | trung bình **48,4 Hz**, xa nhất **112,6 Hz** |
| — | **6/8** bản sao cách mặc định hơn 20 Hz |

→ **Nhân bản CHẠY. Không phải dương tính giả.**

**3. Ra được bao nhiêu giọng thật sự khác nhau?**
Khoảng cách đôi một giữa 8 bản sao: trung bình **69,7 Hz**, gần nhất **8,2 Hz**,
xa nhất **175,4 Hz**.

Để dễ hình dung: **mốc lượt 4** là 2 mẫu cách 93,0 Hz → 2 bản sao cách 98,5 Hz.
Giờ với 8 mẫu, cặp xa nhất cách **175,4 Hz** — tức trải rộng gấp gần 2 lần, phủ
từ **giọng nam trầm (98 Hz)** tới **giọng nữ cao (273 Hz)**.

Cặp gần nhất chỉ cách 8,2 Hz (M1 106,4 vs M2 115,6) — 2 giọng này nghe sẽ hao
hao nhau. Nhưng đó là vì tôi cố ý chọn 2 mẫu gốc sát nhau (115,5 và 118,5 Hz).
**Chọn mẫu tách xa ra thì bản sao cũng tách xa ra** — đó chính là điều bảng trên
chứng minh.

> **CHỐT Ý 1: nhân bản ra giọng KHÁC NHAU thật, và số lượng giọng là do anh
> Hùng chọn bao nhiêu mẫu — không bị máy giới hạn.** Bộ Common Voice tiếng Việt
> có hàng nghìn người đọc CC0 để chọn.

---

# PHẦN C — Ý 2: GHÉP GIÓNG HÀNG THÌ KHỚP BAO NHIÊU?

## C0. Vì sao ý này từng là cửa tử

Lượt 4 đã loại VieNeu **chỉ vì một lý do**: không ra lệnh cho nó đọc đúng số
giây được. Video cần tiếng khớp hình; giọng đọc không chỉnh được thời gian thì
vô dụng.

**Chặn đó nay đã hết.** `app/core/giong_hang.py` (v2.35.0) không cần máy đọc tự
báo giờ nữa — nó **nghe lại file tiếng và tự dò ra từng chữ rơi vào giây nào**
(bằng `torchaudio.functional.forced_align`). Nghĩa là **bất kỳ máy đọc nào** cũng
lấy được mốc từng chữ, kể cả máy không hỗ trợ.

## C1. Thước đo — và vì sao tôi không dùng máy nghe

Thước là **`silencedetect` của ffmpeg** (ngưỡng −40 dB, 0,05 giây): nó chỉ ra
**giây thật sự bắt đầu có tiếng** trong file. So mốc chữ đầu tiên mà gióng hàng
đoán với giây có tiếng thật → ra sai số.

Đây là **thước duy nhất không thiên vị** (nó không biết gì về máy đọc nào). Trong
phiên này nó đã **chặn 2 phép đo sai**. Máy nghe (Whisper) thì tự nó cũng sai
giờ, lấy nó làm chuẩn là lấy thước cong đo thước cong.

**Bắt buộc tách 2 con số** — số thô là số lừa, đã sập 3 lần:
- **LỆCH HỆ THỐNG** = sai đều một hướng. **Vô hại**, trừ đi một phát là hết.
- **RUNG** = sai lung tung mỗi câu một kiểu. **Đây mới là cái hại**, không trừ được.

Và tôi **chạy lại arm đối chứng edge-tts trên ĐÚNG 6 câu đó**, cùng lúc, cùng
thước — chứ không so với con số cũ đo ở corpus khác.

## C2. KẾT QUẢ

| Máy đọc | PHỦ | LỆCH HỆ THỐNG | **RUNG** | chữ muộn >50 ms |
|---|---|---|---|---|
| **VieNeu — 8 bản sao** (48 file) | 95,4% | −11,9 ms | **25,4 ms** | 4,2% |
| VieNeu — giọng mặc định (6 file) | 95,4% | +1,5 ms | **21,7 ms** | 0% |
| **edge-tts — đối chứng** (12 file) | 95,4% | −14,9 ms | **16,7 ms** | 0% |
| *edge-tts — mốc do CHÍNH NÓ tự báo* | *100%* | *−107,8 ms* | *51,5 ms* | *0%* |

**Thước đã được hiệu chuẩn đúng:** arm edge-tts ra **16,7 ms**, khớp với mốc
**15,7 ms** đo ở lượt trước. Nên các số còn lại trong bảng tin được.

## C3. Đọc bảng trên

**1. PHỦ 95,4% không phải lỗi giọng — là do CHỮ SỐ.**
Cả 4 arm đều đúng 95,4%, không xê dịch. Tôi truy ra: 6 câu có **65 chữ**, gióng
hàng trả **62 mốc**, thiếu **đúng 3**. Và corpus có **đúng 3 chữ số**: "Nhà **5**
tầng", "Tầng hầm bi **2**", "có **3** cái". Bộ gióng hàng không đọc được số thô.
→ **Với chữ đã viết ra lời (app vẫn làm vậy khi đọc), phủ ≈ 100%.** Không phải
điểm trừ của nhân bản.

**2. RUNG 25,4 ms — đạt, nhưng thua edge-tts 1,5 lần.**

So với các mốc đã đo trong phiên:

| | RUNG |
|---|---|
| edge-tts (đối chứng, cùng corpus) | **16,7 ms** |
| VieNeu giọng mặc định | 21,7 ms |
| **VieNeu bản sao (nhân bản)** | **25,4 ms** |
| Piper | 29,5 ms |
| OmniVoice + gióng hàng | 90–119 ms |

**25,4 ms là dùng được** — tốt hơn Piper, và tốt hơn OmniVoice 4 lần. Ở mức
25 ms thì tai người không nhận ra tiếng lệch hình.

**3. Nhưng con số 25,4 bị 2 bản sao hỏng kéo xuống.** Xem từng bản sao:

| bản sao | RUNG | | bản sao | RUNG |
|---|---|---|---|---|
| M4 | **7,3 ms** | | M6 | 16,5 ms |
| M1 | **8,4 ms** | | M0 | 18,8 ms |
| M7 | 11,7 ms | | **M5** | **51,5 ms** ← hỏng |
| M2 | 14,8 ms | | **M3** | **58,4 ms** ← hỏng |

**6/8 bản sao rung 7,3–18,8 ms — trung bình 12,9 ms, tức NGANG HOẶC HƠN
edge-tts (16,7 ms).** Chỉ 2 bản sao (M3, M5) bị rung 51–58 ms kéo trung bình lên.

→ **Cách xử lý thực tế: nhân bản xong thì ĐO, bản nào rung cao thì bỏ, chọn mẫu
khác.** Mẫu miễn phí có hàng nghìn, loại 2 trong 8 không mất gì.

**4. Phát hiện phụ có giá trị: đừng tin giờ do máy đọc tự báo.**
Dòng cuối bảng C2: mốc **edge-tts tự khai** lệch hệ thống **−107,8 ms** và rung
**51,5 ms** — **tệ hơn 3 lần** so với để `giong_hang` tự dò lại (16,7 ms). Tức
`app/core/giong_hang.py` đang **chính xác hơn cả đồng hồ của chính máy đọc**.

## C4. Tôi bắt được thước của chính mình bị sai — và đã sửa

Khi đo thêm 6 giọng nữa (phần E), có 6 giọng bỗng ra rung **93–250 ms**, tệ gấp
10 lần. Trước khi tin con số đó, tôi soi lại 9 file tệ nhất: đo độ to của đoạn
âm thanh **nằm trước chữ đầu tiên**.

| | kết quả |
|---|---|
| đoạn trước chữ đầu **nhỏ hơn** câu chính | **−25,1 dB** (trung vị) |
| số file nhỏ hơn −12 dB (= hơi thở/tiếng nền) | **9/9** |
| số file to ngang câu chính (= nghi bịa tiếng) | **0/9** |

→ Đó là **hơi thở**, không phải máy bịa tiếng. Thước `silencedetect` đặt ở
**−40 dB** quá nhạy: nó tưởng tiếng hít vào là "bắt đầu nói", nên chấm gióng hàng
bị coi là **trễ oan**. **Lỗi của thước, không phải lỗi của giọng.**

Tôi hạ độ nhạy xuống **−30 dB** và **đo lại TOÀN BỘ các arm y như nhau** — kể cả
arm đối chứng edge-tts. Đây là **sửa thước, không phải nới thước**, và có cổng
kiểm chứng: *nếu edge-tts không còn ra ~15 ms thì thước mới cũng sai và tôi vứt*.

| arm | thước cũ (−40 dB) | **thước sửa (−30 dB)** |
|---|---|---|
| **edge-tts (cổng hiệu chuẩn)** | 14,5 ms | **13,5 ms** ← vẫn đúng mốc, thước tin được |
| VieNeu giọng mặc định | 9,9 ms | **8,5 ms** |
| bản sao từ mẫu Common Voice | 13,1 ms | **14,6 ms** |
| bản sao từ mẫu FLEURS | *119,7 ms* | **15,4 ms** |

## C5. Con số Ý 2 CUỐI CÙNG

| | RUNG |
|---|---|
| VieNeu giọng mặc định | **8,5 ms** |
| **edge-tts (đối chứng)** | **13,5 ms** |
| **bản sao — mẫu Common Voice** | **14,6 ms** |
| **bản sao — mẫu FLEURS** | **15,4 ms** |
| Piper (mốc cũ) | 29,5 ms |
| OmniVoice + gióng hàng (mốc cũ) | 90–119 ms |

**Cả 14 giọng nhân bản đều rung ≤ 22,5 ms.** Không một giọng nào bị loại vì
khớp thời gian.

> **CHỐT Ý 2: gióng hàng ĐẠT HOÀN TOÀN. Giọng nhân bản khớp thời gian NGANG
> edge-tts (14,6–15,4 ms so với 13,5 ms). Cửa tử của lượt 4 đã mở hẳn —
> khâu thời gian không còn là vấn đề nữa.**

---

# PHẦN D — Ý 3: ĐỌC CÓ SAI CHỮ / BỊA CHỮ KHÔNG?

Đây là ý quyết định. Giọng hay mấy mà **đọc sai chữ** hoặc **tự bịa thêm chữ**
thì video đăng lên là hỏng — và anh Hùng không ngồi nghe lại 200 kênh được.

## D1. Cách đo và bằng chứng là thước ĐÚNG

Cho máy nghe (Groq `whisper-large-v3`) **chép ngược** file tiếng ra chữ, rồi so
với chữ gốc. **Mỗi file chép 3 lượt, lấy trung vị** để bớt nhiễu của máy nghe.

**Thước này có đáng tin không?** Có, và đây là bằng chứng: arm đối chứng
**edge-tts ra 6,2%**, trong khi mốc đã biết của edge-tts là **6,8%**. Thước tái
lập đúng số đã biết → **các số còn lại tin được**.

## D2. KẾT QUẢ — và nó là tin XẤU

| Máy đọc | **sai từ** | thừa chữ (bịa) |
|---|---|---|
| edge-tts (đối chứng) | **6,2%** | −1,5% |
| VieNeu **giọng mặc định** (không nhân bản) | **7,7%** | −1,5% |
| **VieNeu — 8 bản sao nhân bản** | **21,2%** | +0,8% |

Từng bản sao:

| bản sao | sai từ | | bản sao | sai từ |
|---|---|---|---|---|
| M0 | 10,8% | | M7 | 21,5% |
| M1 | 10,8% | | M3 | 24,6% |
| M2 | 16,9% | | M4 | 26,2% |
| | | | M5 | 27,7% |
| | | | M6 | **30,8%** |

**Nhân bản làm sai từ tăng từ 7,7% lên 21,2% — gấp 2,75 lần.** Bản tệ nhất sai
gần **1/3 số chữ**. Đây là mức **không dùng được** cho video đăng kênh.

## D3. Tôi đã truy ra NGUYÊN NHÂN — và nó không sửa được bằng lọc âm

Giả thuyết tự nhiên: mẫu Common Voice là **người dân tự thu bằng điện thoại**,
có ồn, có vọng phòng. Vậy **lọc sạch mẫu rồi nhân bản lại** thì có đỡ không?

Tôi làm **thí nghiệm ghép cặp** — cùng người đọc, cùng 6 câu, **chỉ khác** mẫu
đã lọc sạch hay chưa (lọc: cắt ù dưới 70 Hz + khử nhiễu + chuẩn độ to):

| người đọc | mẫu **còn bẩn** | mẫu **đã lọc sạch** | đổi được |
|---|---|---|---|
| M4 | 26,2% | 33,8% | **+7,7** (tệ đi) |
| M5 | 27,7% | 27,7% | 0,0 |
| M6 | 30,8% | 26,2% | −4,6 (đỡ chút) |
| **gộp 3 người** | **28,2%** | **29,2%** | **+1,0 → KHÔNG ĂN THUA** |

→ **Lọc âm không cứu được.** Vấn đề không nằm ở tiếng ồn.

**Vậy nó nằm ở đâu?** Tôi chạy thêm một arm quyết định: nhân bản từ **mẫu sạch
tuyệt đối** — lấy chính đầu ra của giọng mặc định VieNeu làm mẫu (`STN`):

| | sai từ |
|---|---|
| VieNeu giọng mặc định (không nhân bản gì) | **7,7%** |
| **VieNeu nhân bản từ mẫu SẠCH TUYỆT ĐỐI** | **7,7%** |
| | **giá của việc nhân bản = 0,0 điểm** |

> **Đây là phát hiện quan trọng nhất của lượt này.**
> **Bản thân cơ chế nhân bản KHÔNG làm hỏng chữ — giá của nó bằng 0.**
> Toàn bộ 21,2% là do **CHẤT LƯỢNG MẪU GIỌNG**, và là loại hỏng mà **khử nhiễu
> không chữa được** (giọng nghiệp dư, giọng vùng miền, cách nói, chất mic).

Nói cho dễ hiểu: máy nhân bản **không có lỗi**. Nó bắt chước rất trung thành —
trung thành cả **cái dở** của người thu mẫu. Mẫu miễn phí trên Common Voice là
dân tự thu, nên bản sao cũng đọc "nghiệp dư" y như vậy.

## D4. Có bịa chữ không? — KHÔNG, đây là điểm SÁNG

Nhắc lại vì sao ý này quan trọng: **viXTTS** đưa 29 chữ Trung đọc ra **40 chữ**,
**Chatterbox** cũng bịa. **Bịa là loại thẳng**, vì video sẽ nói thứ anh không viết.

| | thừa chữ |
|---|---|
| VieNeu 8 bản sao (48 file) | **+0,8%** |
| VieNeu mặc định | −1,5% |
| edge-tts | −1,5% |

**Chỉ 1/66 file** chép ra dài hơn gốc quá 15%. Đó là file `M1 c0` — máy **đọc
lặp lại** nửa câu đầu:

> gốc: «Tôi mới tộ căn nhà dị hợm bị người ta chê»
> chép: «Tôi mới tổ căn nhà dị hợm Bị người ta chê **Tôi mới tổ căn nhà dị hợm**»

Đây là lỗi **lặp**, không phải bịa nội dung mới. Tỷ lệ **1/48 file bản sao
(2,1%)**.

> **CHỐT Ý 3: KHÔNG bịa chữ (+0,8% — sạch). NHƯNG sai từ 21,2% là KHÔNG ĐẠT.**
> Và nguyên nhân đã truy ra: **lỗi của MẪU miễn phí, không phải lỗi của máy.**
