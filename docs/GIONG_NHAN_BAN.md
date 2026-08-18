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

*(còn Ý 2 — ghép gióng hàng khớp bao nhiêu; và Ý 3 — đọc có sai/bịa chữ không.
Hai ý đó quyết định giọng này có DÙNG ĐƯỢC không, xem phần C và D.)*
