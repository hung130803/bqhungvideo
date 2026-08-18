# LƯỢT 8 — CHỐT CHUYỆN GIỌNG: giá mua thật + đường miễn phí cuối cùng

*Ngày 18/08/2026. Đây là lượt thứ 8 anh Hùng hỏi về giọng. Tôi ghi số đo và số
tiền, không nới thước, không đoán giá.*

**Không sửa một file nào trong `app/`. Không đẻ một luồng con nào. Không tăng
version, không tag, không push.**

---

# PHẦN A — GIÁ MUA GIỌNG (Vbee · FPT.AI · Zalo AI · Viettel AI · Azure)

## A0. TRẢ LỜI NGẮN — ĐỌC ĐOẠN NÀY LÀ ĐỦ

### 1. Ba giọng anh đòi đích danh CÓ THẬT, và tôi đã tra ra tận mã giọng của Vbee

Tôi gọi thẳng vào máy chủ Vbee (`https://vbee.vn/api/v1/voices` — dữ liệu của
chính họ, không phải bài giới thiệu):

| Giọng anh nêu | Mã giọng thật trong hệ thống Vbee | Bậc | Hệ số tính tiền |
|---|---|---|---|
| **HN - Ngọc Huyền** | `hn_female_ngochuyen_full_48k-fhg` | BASIC | **1** |
| **HN - Anh Khôi** | `hn_male_phuthang_stor80dt_48k-fhg` *(kể truyện)*<br>`hn_male_phuthang_news65dt_44k-fhg` *(đọc tin)* | BASIC | **1** |
| **HN - Minh Quân** | `hn_male_minhquan_yt-stable` | BASIC | **1** |

*(Để ý: "Anh Khôi" là **tên sân khấu** — mã máy của Vbee ghi người thu âm là
`phuthang`. Tức giọng đó là giọng của một người thật tên khác, và Vbee đứng ra
lo phần quyền cho người đó. Chi tiết này chính là lý do ở mục A8.)*

Vbee có **462 giọng**, trong đó **25 giọng tiếng Việt**. Có cả bản "2.0/Pro"
mới hơn (`Ngọc Huyền 2.0`, `Minh Quân Pro`) nhưng chúng ăn **hệ số 3** — tức
đọc cùng một chữ mà bị trừ tiền gấp 3 lần.

### 2. GÓI MIỄN PHÍ CÓ — nhưng nhỏ tới mức không dùng được cho 200 kênh

Đây là ý anh nói *"nhiều bên public"*. Có thật, và đây là con số thật:

| Bên | Gói miễn phí | Đổi ra phút tiếng | Phủ được **bao nhiêu %** nhu cầu của anh |
|---|---|---|---|
| **Vbee** | **3.000 ký tự/NGÀY** (≈ 90.000/tháng) | 70,7 phút/tháng | **0,118%** |
| **FPT.AI** | **100.000 ký tự/THÁNG** | 78,6 phút/tháng | **0,131%** |
| **Azure** | **500.000 ký tự/THÁNG** (gói F0) | 392,8 phút/tháng | **0,655%** |
| **Viettel AI** | 1.000.000 ký tự **dùng thử 1 lần** | 785,5 phút *(một lần)* | 1,309% *(rồi hết)* |
| **Zalo AI** | web miễn phí, **500 ký tự/lần** | — | không đo được (xem A6) |

**Anh cần 76.380.000 ký tự/tháng** (= 60.000 phút tiếng = **1.000 giờ**).
Cộng cả 4 gói miễn phí lại được **1,69 triệu ký tự = 2,2%**. Còn thiếu 97,8%.

Và gói miễn phí còn bị bóp thêm: Vbee miễn phí chỉ **1 thiết bị đồng thời** và
tài liệu của họ ghi *"Thêm watermark vào audio miễn phí"*; FPT miễn phí ghi
thẳng *"Tốc độ chuyển đổi thấp · Giới hạn số lượng yêu cầu mỗi ngày · Phản hồi
kết quả chậm · Không hỗ trợ kỹ thuật"*.

→ **Không có đường miễn phí hợp pháp nào để chạy 200 kênh bằng giọng Vbee.**

### 3. RẺ NHẤT ĐỂ CÓ ĐÚNG THỨ ANH MUỐN: **15 triệu đồng/tháng (FPT.AI)**

Nhưng phải nói ngay: **FPT.AI KHÔNG có 3 giọng anh nêu** — 3 giọng đó là của
Vbee, chỉ Vbee bán. Muốn đúng **HN-Ngọc Huyền / HN-Anh Khôi / HN-Minh Quân** thì
rẻ nhất là **Vbee ≈ 24,4 triệu/tháng** (giá gói năm) hoặc **45,8 triệu/tháng**
(giá trả theo dùng niêm yết 0,599 đ/ký tự).

### 4. TIN QUAN TRỌNG NHẤT — và nó là tin XẤU cho ý "mua Azure là gọn nhất"

Anh đoán đúng một nửa: **2 giọng Việt `edge-tts` app đang dùng ĐÚNG là của
Azure** (`vi-VN-HoaiMyNeural` · `vi-VN-NamMinhNeural` — tôi liệt kê từ chính
`edge-tts` trên máy và đối chiếu với danh sách gốc của Microsoft).

**Nhưng Azure chỉ có 3 giọng tiếng Việt, không hơn.** Đọc từ file gốc của
Microsoft (`azure-ai-docs` trên GitHub, không đọc blog):

```
vi-VN-HoaiMyNeural            (Nữ)
vi-VN-NamMinhNeural           (Nam)
vi-VN-Linh:MAI-Voice-2-Flash  (Nữ) — bản xem trước (public preview)
```

**Nghĩa là trả tiền cho Azure, anh được thêm ĐÚNG 1 GIỌNG VIỆT** (giọng Linh,
mà nó còn đang là bản xem trước). **Không phải đáp án cho câu "tôi muốn nhiều
giọng Việt hay".** Cái Azure trả tiền cho anh là **hợp pháp** + **mốc từng chữ
có bảo đảm hợp đồng** — không phải thêm giọng.

### 5. MỐC TỪNG CHỮ: chỉ Azure có. Bốn bên Việt Nam đều KHÔNG có.

| Bên | Trả mốc từng chữ? | Bằng chứng |
|---|---|---|
| **Azure** | **CÓ — `WordBoundary` thật** | Tài liệu Microsoft: sự kiện trả `AudioOffset` · `Duration` · `Text` · `TextOffset` · `WordLength` cho **từng từ**, kèm cả dấu câu và câu |
| **FPT.AI** | **KHÔNG** | API chỉ trả `error` · `async` (link file) · `request_id` · `message` |
| **Vbee** | **KHÔNG tìm thấy** | Không có mục nào trong tài liệu công khai nói tới mốc/timestamp/mark |
| **Viettel AI** | **KHÔNG tìm thấy** | như trên |
| **Zalo AI** | **không đọc được** | trang tài liệu chạy bằng JavaScript, không lấy được nội dung |

**Ý nghĩa cho anh:** mua FPT / Vbee / Viettel thì **bắt buộc** phải chạy thêm
`app/core/giong_hang.py` (gióng hàng cưỡng bức) để tự dò mốc. May là app **đã
có sẵn** bộ đó và nó **đã đo được: phủ 98,6% · rung 90-119 ms**. Nên chuyện
"không có mốc" nay chỉ là *tốn thêm 6,3 giây/mẻ 12 câu*, **không còn là cửa tử**
như 4 lượt trước.

Nhưng cũng phải nói thẳng: mốc gióng hàng **rung 90-119 ms**, còn mốc thật của
`WordBoundary` (edge-tts/Azure) **rung 15,7 ms**. Đó là **kém hơn 6-7 lần**.

### 6. ĐIỀU KHOẢN — cả 5 bên đều CHO LÀM VIDEO KIẾM TIỀN

Tôi đọc **văn bản gốc**, không đọc bài giới thiệu (6 lượt trước đã bắt 11 chỗ
bài viết ghi sai giấy phép).

**Vbee** — nguyên văn Điều 4.2 Điều khoản sử dụng:

> *"Vbee AITalk cam kết về bản quyền và **quyền thương mại hóa** các giọng nói
> tiếng Việt và giọng nói tiếng nước ngoài mà Vbee AITalk cung cấp… Vbee AITalk
> **khẳng định và cam kết** rằng Dữ liệu đầu ra mà khách hàng tạo ra… **không vi
> phạm quyền sở hữu trí tuệ và bản quyền tác giả liên quan đến giọng nói của bất
> cứ bên thứ ba nào khác.**"*

Và Điều 3.1.5: *"**Dữ liệu đầu ra thuộc quyền sở hữu của khách hàng**"*.

**Đây chính là thứ anh KHÔNG THỂ có bằng cách bóc giọng.** Anh trả tiền không
chỉ để lấy file tiếng — anh trả tiền để Vbee **đứng ra bảo đảm** rằng người thu
âm giọng đó đã đồng ý cho anh kiếm tiền. Bóc giọng thì cái bảo đảm đó không tồn
tại, và người đi kiện là chính người thu âm — không phải Vbee.

**Ba chỗ phải để ý trong điều khoản Vbee** (tôi không phải luật sư, nhưng đây là
chữ trong văn bản):
1. Giấy phép là *"không độc quyền, không thể chuyển nhượng, không thể cấp phép
   lại và **có thể thu hồi**"* → anh **không được bán lại** quyền dùng giọng cho
   nhân viên/khách của anh như một tính năng của app.
2. Điều 3.1.2: *"Dịch vụ chỉ được cung cấp và sử dụng trên website vbee.vn
   và/hoặc ứng dụng Vbee AIVoice"* → muốn gọi từ app của anh thì phải mua **gói
   API**, không phải gói Studio.
3. Điều 6.1: Vbee được *"thay đổi… bất kỳ điều khoản nào vào bất kỳ thời điểm
   nào… **mà không cần thông báo trước**"*.

---

## A1. BẢNG MUA — TẤT CẢ CÁC CỘT ANH HỎI

| | **Vbee** | **FPT.AI** | **Viettel AI** | **Azure Speech** | **Zalo AI** |
|---|---|---|---|---|---|
| **Gói miễn phí** | 3.000 ký tự/**ngày** (1 thiết bị, có watermark) | 100.000 ký tự/**tháng** (tốc độ thấp, giới hạn/ngày) | 1 triệu ký tự **dùng thử 1 lần** | **500.000 ký tự/tháng** (F0) | web 500 ký tự/lần |
| **Giá rẻ nhất/ký tự** | 0,319 đ *(gói năm)* | **0,185 đ** | 0,280 đ *(chưa VAT)* | 0,317 đ *(cam kết 80M)* | ? |
| **Giá trả-theo-dùng** | 0,599 đ | — | 0,320 đ | 0,396 đ *(15 USD/1M)* | ? |
| **TIỀN/THÁNG cho 200 kênh** | **24,4 – 45,8 triệu** | **15,0 triệu** | **24,6 triệu** *(có VAT)* | **25,3 triệu** | ? |
| **Mốc từng chữ** | KHÔNG | **KHÔNG** | KHÔNG | **CÓ (`WordBoundary`)** | ? |
| **Cho kiếm tiền** | **CÓ** *(Đ4.2, có cam kết bảo đảm)* | CÓ | CÓ | CÓ | ? |
| **Có 3 giọng anh nêu** | **CÓ — cả 3** | KHÔNG | KHÔNG | KHÔNG | KHÔNG |
| **Số giọng Việt** | **25** | 7 | ~10 *(chưa đếm được chắc)* | **3** | 4 |

**Cách tính:** app đo **1.273 ký tự = 1 phút tiếng**. Video 10 phút = **12.730
ký tự**. 200 kênh × 1 video/ngày × 30 ngày = 6.000 video = **76.380.000 ký
tự/tháng** = 60.000 phút = **1.000 giờ tiếng/tháng**. Tỷ giá **26.400 đ/USD**
(giá bán ngân hàng thương mại tháng 8/2026).

## A2. BẢNG GIÁ ĐẦY ĐỦ — SẮP THEO RẺ DẦN

| Gói | đ/ký tự | Tiền/tháng cho 76,38 triệu ký tự |
|---|---|---|
| **FPT.AI Enterprise** 5.000.000đ/27 triệu ký tự | **0,1852** | **14,14 triệu** *(mua 3 gói = 15,00 triệu cho 81 triệu ký tự)* |
| FPT.AI Professional 2.000.000đ/10 triệu | 0,2000 | 15,28 triệu |
| FPT.AI Standard 1.000.000đ/4 triệu | 0,2500 | 19,09 triệu |
| Viettel gói lớn (15 triệu/50M + 280k/1M thêm) | 0,2800 | 22,39 triệu chưa VAT → **24,63 triệu có VAT** |
| **Azure cam kết 80M/tháng — 960 USD** | 0,3168 | **25,34 triệu** *(trần 80M ≥ 76,38M → vừa đủ)* |
| **Vbee API gói năm** 7.650.000đ/24 triệu | 0,3187 | **24,35 triệu** *(phải mua ~38 gói/năm)* |
| Viettel trả theo dùng 320.000đ/1M | 0,3200 | 24,44 triệu chưa VAT → 26,89 triệu có VAT |
| FPT.AI Premium 500.000đ/1,5 triệu | 0,3333 | 25,46 triệu |
| Azure S1 trả theo dùng — 15 USD/1M | 0,3960 | 30,25 triệu |
| Vbee API-BASIC gói năm 2.388.000đ/6 triệu | 0,3980 | 30,40 triệu |
| Vbee API-ADV tháng 799.000đ/1,5 triệu | 0,5327 | 40,69 triệu |
| **Vbee trả theo dùng (niêm yết)** | **0,5990** | **45,75 triệu** |

**Nguồn từng số — đều là dữ liệu GỐC của nhà cung cấp, không phải bài viết:**
- Vbee: `GET https://vbee.vn/api/v1/packages` (124 gói) và
  `GET https://vbee.vn/api/v1/voices` (462 giọng) — đọc hôm nay.
- FPT.AI: `docs.fpt.ai/docs/vi/speech/documentation/tts-pricing/`
- Viettel AI: bảng giá Viettel IDC (320.000đ/1M · 3,2 triệu/10M · 15 triệu/50M,
  **chưa VAT 10%**).
- Azure: **API giá bán lẻ chính thức của Microsoft**
  `https://prices.azure.com/api/retail/prices` → `S1 Neural Text To Speech
  Characters = 15,00 USD/1M` (cả `eastus` lẫn `southeastasia`), bậc cam kết
  `80M Unit = 960 USD/tháng`, `400M = 3.900 USD`, `2000M = 15.000 USD`.
  *(Ghi chú: nhiều bài trên mạng ghi 16 USD — số thật trong bảng giá của
  Microsoft hôm nay là **15 USD**. Neural HD = 22 USD/1M.)*

## A3. VBEE — CHI TIẾT GÓI (đọc từ API của chính họ)

| Mã gói | Tên | Giá | Ký tự | Luồng đồng thời |
|---|---|---|---|---|
| `STUDIO-BASIC` | **Miễn phí** | 0 | **3.000/ngày** | 1 |
| `STUDIO-TRIAL` | Miễn phí 3 ngày | 0 | 3.000/ngày | 5 |
| `STUDIO-ADV-MONTH` | Nâng cao | 149.000đ | 650.000/tháng | 5 |
| `STUDIO-PRO-MONTH` | Cao cấp | 249.000đ | 600.000/tháng | 10 |
| `STUDIO-ENTERPRISE-MONTH` | Đặc biệt | 799.000đ | 1.300.000/tháng | 100 |
| `API-BASIC-MONTH` | API Tiêu chuẩn | 249.000đ | 500.000/tháng | 5 |
| `API-ADV-MONTH` | API Nâng cao | 799.000đ | 1.500.000/tháng | 20 |
| `API-ADV-YEAR` | API Nâng cao (năm) | 7.650.000đ | 24.000.000/năm | 20 |
| `API-PAYG` | **API trả theo dùng** | **0,599đ/ký tự** | không giới hạn | không giới hạn |

**Một cái bẫy phải biết:** gói miễn phí `STUDIO-BASIC` mở quyền
`premium-vietnam-voice` (tức các bản *Ngọc Huyền 2.0* · *Minh Quân Pro*) nhưng
**KHÔNG** mở `basic-vietnam-voice` — đúng cái quyền mà **HN-Ngọc Huyền**,
**HN-Anh Khôi**, **HN-Minh Quân** đòi. Mà bản 2.0/Pro thì **hệ số tiền = 3**.
Nghĩa là gói miễn phí không cho anh chính 3 giọng anh nêu; nó cho anh bản mới
hơn nhưng đốt điểm gấp 3.

**Một số hay:** Vbee tự khai giọng của họ đọc **18 ký tự/giây** = 1.080 ký
tự/phút. App đo được **1.273 ký tự/phút**. Hai số cùng độ lớn → phép quy đổi của
tôi ở trên **không phải bịa**, lệch khoảng 18%. Nếu tính theo số của Vbee thì
tiền còn **thấp hơn** bảng trên ~15%.

## A4. FPT.AI — CHI TIẾT (bảng giá gốc)

| Gói | Giá | Ký tự |
|---|---|---|
| **Miễn phí** | 0 | **100.000/tháng** (phiên bản 5 — giọng tốt nhất) |
| Cao cấp | 500.000đ | +1.500.000 |
| — | 1.000.000đ | +4.000.000 |
| — | 2.000.000đ | +10.000.000 |
| — | 5.000.000đ | **+27.000.000** ← rẻ nhất/ký tự |
| Doanh nghiệp cao cấp | liên hệ | tuỳ |

7 giọng Việt: `banmai` · `thuminh` (nữ Bắc) · `lannhi` · `linhsan` (nữ Nam) ·
`leminh` (nam Bắc) · `myan` (nữ Trung) · `giahuy` (nam Trung).
Trần **5.000 ký tự/yêu cầu**. API **không trả mốc**.

## A5. AZURE — CHI TIẾT

- **Miễn phí (F0): 500.000 ký tự/tháng** cho giọng neural. Đây là **gói miễn phí
  lớn nhất trong 5 bên**, và nó **lặp lại hằng tháng**.
- Trả theo dùng: **15 USD/1 triệu ký tự** (≈ 396 đ/ký tự).
- Cam kết 80 triệu ký tự/tháng: **960 USD/tháng** (≈ 25,34 triệu đ) — vừa đúng
  khung 76,38 triệu của anh.
- **Chỉ 3 giọng Việt** (2 giọng anh đang dùng miễn phí + 1 bản xem trước).
- **`WordBoundary` là mốc THẬT**, trả `AudioOffset` + `Duration` + `Text` +
  `TextOffset` + `WordLength` cho từng từ.
  ⚠ **Nhưng nó là tính năng của SDK, không phải của REST API** — tài liệu
  Microsoft không nói REST trả mốc. Muốn có mốc thì phải dùng Speech SDK.

**Chỗ phải nói thẳng nhất của cả phần A:** hôm nay app đang lấy **đúng 2 giọng
Việt đó, đúng mốc `WordBoundary` đó, 0 đồng** qua `edge-tts`. Trả 25-30 triệu
đồng/tháng cho Azure thì **về mặt kỹ thuật anh gần như không được thêm gì** —
được thêm 1 giọng xem trước, và được **hết rủi ro điều khoản** (`edge-tts` gọi
vào cửa "Đọc to" của trình duyệt Edge, không phải cửa API có hợp đồng; chính tác
giả `edge-tts` viết *"It shouldn't be used for commercial reasons"*, và
`LICENSES.txt` của app đã ghi nguyên văn câu đó).

## A6. ZALO AI — CHƯA ĐO ĐƯỢC, GHI THẲNG

- Dịch vụ **còn sống**: `zalo.ai` chuyển sang `ai.zalo.solutions`, trả HTTP 200.
- Trang tài liệu API **chạy hoàn toàn bằng JavaScript** nên tôi **không lấy được
  giá, không lấy được hạn mức, không lấy được danh sách giọng**.
- Thông tin chỉ ở mức bài viết bên thứ ba (web miễn phí 500 ký tự/lần, API ~2000
  từ/lần, 4 giọng Việt: 2 Bắc + 2 Nam). **Tôi không lấy con số này làm căn cứ.**
- **Zalo AI cũng không có 3 giọng anh nêu**, nên nó không giải được bài toán
  chính. Cần biết giá thì phải mở trình duyệt vào trang đó bằng tay.

## A7. NẾU ANH MUỐN MUA — 3 ĐƯỜNG, THEO ĐÚNG THỨ TỰ TIỀN

**Đường 1 — đúng 3 giọng anh đòi: Vbee, ~24,4 triệu đồng/tháng.**
Mua gói **API** (không phải Studio — Studio bị Điều 3.1.2 giới hạn "chỉ dùng
trên website/app Vbee"). Phải nói với Vbee mức 76 triệu ký tự/tháng để họ báo
giá doanh nghiệp; giá niêm yết trả-theo-dùng 0,599đ ra **45,8 triệu**, gần gấp
đôi. **Phải tự dò mốc bằng `giong_hang.py`.**

**Đường 2 — rẻ nhất, chấp nhận đổi giọng: FPT.AI, ~15 triệu đồng/tháng.**
3 gói Enterprise = 81 triệu ký tự. Được 7 giọng Việt (đủ Bắc/Trung/Nam). Rẻ hơn
Vbee **~9,4 triệu/tháng = 113 triệu/năm**. **Cũng phải tự dò mốc.**

**Đường 3 — êm nhất về kỹ thuật: Azure cam kết, ~25,3 triệu đồng/tháng.**
Không phải sửa gì trong app về mốc (mốc thật, rung 15,7 ms). Nhưng **chỉ được 3
giọng Việt**, tức **không giải được câu "tôi muốn nhiều giọng"**.

**Đường 0 — giữ nguyên: 0 đồng.** Đây vẫn là thứ tôi khuyên (xem Phần B trước
khi quyết).

## A8. TÔI TỪ CHỐI VIỆC GÌ, VÀ TẠI SAO

Anh yêu cầu bóc/nhân bản 3 giọng Vbee. **Tôi không làm, và cũng không lách.**
Không phải vì "sợ rủi ro chung chung" mà vì **hai chủ thể cụ thể**:

1. **Vbee** — sản phẩm họ bán chính là 3 giọng đó. Điều 4.2 nói rõ khách hàng
   *"không được quyền sở hữu các giọng nói… chỉ được cấp phép sử dụng"*.
2. **Người thu âm** — HN-Ngọc Huyền, HN-Anh Khôi, HN-Minh Quân là **giọng người
   thật**. Vbee cam kết đã lo phần quyền của họ. Bóc giọng là bỏ qua đúng cái
   cam kết đó, và người bị hại là người thu âm, không phải Vbee.

Tra cứu có gặp hướng dẫn kiểu "dùng cửa hậu / key lậu / gọi API không qua thanh
toán": **có nhưng KHÔNG nên** — một dòng, hết. Lượt 2 đã đo: bị khoá là **mất
hẳn, không xin lại được**.

---
