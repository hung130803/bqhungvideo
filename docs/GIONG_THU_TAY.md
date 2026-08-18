# LƯỢT 10 — THỬ TAY NỐT 18 BỘ CỦA LƯỢT 9

*Ngày 18/08/2026. Lượt thứ 10. Lượt 9 (`GIONG_QUET_CUOI.md`) tìm được 18 bộ
mới nhưng **17/18 chưa thử tay** vì máy chủ dùng thử ZeroGPU của Hugging Face
chặn sau 2 câu. Lượt này **không đi tìm bộ mới** — chỉ đo nốt.*

**KHÔNG sửa một file nào trong `app/`. Không tăng version, không tag, không
push. Không đẻ một luồng con nào.**

---

## 0. ĐƯỜNG SPACE ĐÃ ĐÓNG HẲN — ĐO LẠI ĐỂ CHẮC

Việc đầu tiên là thử lại đúng cái cửa lượt 9 bị chặn. Máy chủ trả nguyên văn:

> `❌ Lỗi khi suy luận: 'You have exceeded your ZeroGPU runs limit.
> Authenticate with a Hugging Face token for more quota'`

Space **vẫn sống** (hỏi được bảng tham số, thấy đủ 6 mục trong ô chọn giọng),
chỉ là **hết hạn mức tính toán**. Muốn chạy tiếp phải đăng nhập bằng tài khoản
Hugging Face của anh Hùng — **tôi không đi tìm/dùng chìa khoá của anh**.

→ Nên toàn bộ lượt này **chạy TẠI MÁY** (tải trọng số về, RTX 3060), đúng như
đề bài dặn.

**Một điều lượt 9 ghi thiếu, đọc bảng tham số của Space mới thấy:** ô chọn
giọng của Kani-TTS-Vie có **6 mục** chứ không phải 3 —
`Khoa – Nam miền Bắc` · `Hùng – Nam miền Nam` · `Trinh – Nữ miền Nam` ·
**`David – English (British)`** · **`Katie – English (Irish)`** ·
`Không chỉ định`. Tức nó có **giọng tiếng Anh riêng**, đúng thứ anh Hùng hỏi
("cho cả tiếng Anh với tiếng Việt"). Thẻ model còn kể thêm một danh sách giọng
"cross-lingual" (Puck, Kore, Andrew, Seulgi, Maria, Mei…) — **phải đo xem có
thật không**, không đọc quảng cáo rồi chép vào bảng.

---

## 1. ARM ĐỐI CHỨNG edge-tts — CHẠY LẠI TRÊN CHÍNH BỘ CÂU LƯỢT NÀY

**Không chép số cũ.** Lượt 9 đã chứng minh thước đổi theo bộ câu (6,8% cũ đo
trên bản chép tự động có lỗi sẵn; bộ câu sạch cho edge-tts 0,0%). Bộ câu lượt
này: **8 câu tiếng Việt + 8 câu tiếng Anh** — 4 câu đầu mỗi thứ tiếng lấy
nguyên từ `_bo_cau_thu_doc.py` (loại `cau_thuong`, đã dùng ở việc "đọc sai chữ
nước ngoài"), 4 câu sau viết thêm cho đủ dài, kiểu câu kể chuyện.

### 1a. Sai từ / bịa chữ — mốc PHẢI VƯỢT

| edge-tts (ĐANG CHẠY) | sai từ | bịa chữ | số câu |
|---|---|---|---|
| **tiếng Việt** (HoaiMy + NamMinh) | **5,2%** | **0,0%** | 8/8 |
| **tiếng Anh** (Aria + Andrew) | **0,0%** | **0,0%** | 8/8 |

Hai lỗi đọc thật của tiếng Việt, ghi ra để biết thước còn răng:
*"cô gái **mỉm** cười"* → máy nghe ra *"**miễn** cười"* (8,3%) ·
*"Tiếng **chuông** vang lên giữa đêm **khuya làm cả xóm** thức giấc"* →
*"Tiếng **chung** vang lên giữa đêm **khuy lầm cả sóng** thức giấc"* (33,3%).

> ⚠ **ĐỪNG so 5,2% này với "0,0%" của lượt 9.** Lượt 9 chỉ dùng 4 câu ngắn;
> lượt này thêm 4 câu dài hơn nên thước khó hơn. Cách đọc đúng là so **trong
> cùng bảng** — mọi bộ ở dưới đều chạy trên ĐÚNG 8 câu này.

### 1b. Nhấn nhá — dựng lại mốc "trải 3,31" trên chính câu lượt này

| | số giọng | f0_std thấp nhất – cao nhất | **TRẢI** |
|---|---|---|---|
| **edge-tts en-US** | **17** | 2,20 – 5,35 | **3,15** |
| edge-tts vi | 2 | 3,38 – 3,74 | 0,36 |

Mốc lượt 5 ghi **3,31** (2,38–5,69) trên một câu tiếng Anh KHÁC. Đo lại hôm
nay ra **3,15** — **hai phép đo độc lập gặp nhau trong 0,16 nửa cung**, tức
thước đứng vững và mốc dùng được. Từ đây lấy **3,15** làm mốc so (cùng câu,
cùng lượt), và ghi kèm 3,31 để nối với lượt cũ.

Giọng trải rộng nhất: `en-US-Andrew` **5,35** · hẹp nhất `en-US-Ana` **2,20`.

---

## 2. KANI-TTS-VIE — CHẠY TẠI MÁY ĐƯỢC, VÀ **KHÔNG CÓ 3 GIỌNG VIỆT**

Đây là phát hiện lớn nhất lượt này, và nó **lật một con số lượt 9 đã ghi**.

### 2a. Chạy được tại máy — không cần Space nữa

Dựng lại đúng đường của Space (`kani_vie/tts_core.py` + `utils/normalize_text.py`
tải thẳng từ Space, bỏ lớp gradio). Chạy trên RTX 3060:
**nạp model 5,9 giây · mỗi câu 2,6 – 4,3 giây** (Space đo 9,5–10,3 giây vì có
hàng đợi). Tức cửa "ZeroGPU chặn" **không còn là rào** — nhưng phải trả giá
bằng bộ thư viện: Kani cần **NVIDIA NeMo** để giải mã tiếng, và NeMo kéo theo
**448 MB gói phụ** (lightning · hydra · lhotse · pyannote · tensorboard…) cộng
**723 MB trọng số**.

### 2b. **CÓ BA TẦNG GIẤY PHÉP, KHÔNG PHẢI MỘT** — lượt 9 ghi thiếu tầng thứ ba

| tầng | thứ gì | giấy phép THẬT | bán được? |
|---|---|---|---|
| 1. thẻ model `pnnbao-ump/kani-tts-370m-vie` | bản tinh chỉnh Việt | ghi **apache-2.0** | — |
| 2. model NỀN `nineninesix/kani-tts-370m` | LFM2 của Liquid AI | trường `license:` = **`other` / `lfm1.0`** (trần doanh thu 10 triệu USD/năm) | ĐƯỢC |
| 3. **bộ GIẢI MÃ TIẾNG** `nvidia/nemo-nano-codec-22khz-0.6kbps-12.5fps` | NanoCodec — **thiếu nó thì KHÔNG RA MỘT TIẾNG NÀO** | **NVIDIA Open Model License** | **ĐƯỢC** — thẻ model ghi nguyên văn *"This model is ready for commercial/non-commercial use."* |

Tin tốt: **cả ba tầng đều cho kiếm tiền.** Nhưng phải ghi ra cho đủ — lượt 9 chỉ
kiểm tầng 1-2, mà tầng 3 mới là thứ biến số thành âm thanh. Nếu NVIDIA đổi điều
khoản thì bộ này chết, không phải tác giả người Việt quyết.

### 2c. **SỐ GIỌNG THẬT: 2, KHÔNG PHẢI 3 (và cũng không phải 5)**

Ô chọn giọng có **6 mục** (Khoa · Hùng · Trinh · David · Katie · Không chỉ định).
Câu hỏi đúng không phải "có mấy cái tên" mà là **"có mấy NGƯỜI NÓI khác nhau"**.

**Hai thước đầu tôi dùng đều HỎNG — ghi ra để đừng ai đi lại:**

* **MFCC trung bình** (thước lượt trước hay dùng): Kani sinh ngẫu nhiên
  (`do_sample=True`) nên **nhiễu TRONG-giọng còn LỚN HƠN khoảng cách
  GIỮA-giọng** — `nam-mien-bac` tự nó lệch **97,7** trong khi
  `nam-mien-bac` vs `nam-mien-nam` chỉ **48,4**. Thước này gom cả 6 mục làm 1
  giọng, tức nó không nói được gì.
* **Cao độ trung vị (F0)**: chỉ tách được nam/nữ. `nam-mien-bac` đo 81,8 và
  110,5 Hz, `nam-mien-nam` đo 90,3 và 94,0 Hz — **hai dải CHỒNG LÊN NHAU**.

**Thước ĐÚNG là bộ nhận dạng người nói ECAPA-TDNN** (VoxCeleb) — thứ dùng để
mở khoá bằng giọng, học đúng cái "ai đang nói" và bỏ qua nội dung. Mỗi mục chạy
**4 LƯỢT** (4 seed) trên cùng một câu.

**TỰ KIỂM BỘ DÒ TRƯỚC (bắt buộc — không có mục này thì mọi số dưới là vô nghĩa):**
chạy chính thước đó trên edge-tts, nơi biết chắc là giọng khác nhau. Và cố ý
cho edge điều kiện **KHÓ HƠN** (TRONG-giọng đo trên 4 CÂU KHÁC NHAU, trong khi
Kani đo trên CÙNG MỘT CÂU):

| edge-tts | giống nhau |
|---|---|
| TRONG-giọng HoaiMy (4 câu khác nhau) | 0,704 – 0,848 |
| TRONG-giọng NamMinh (4 câu khác nhau) | 0,739 – 0,807 |
| **HoaiMy vs NamMinh** | **0,209** |
| 4 giọng en-US khác nhau, cao nhất | **0,314** |

→ Thước đứng vững: **cùng giọng ≈ 0,78 · khác giọng ≤ 0,31.**

**KANI, cùng thước:**

| | giống nhau |
|---|---|
| TRONG-giọng (cùng mục, 4 lượt, **CÙNG một câu**) | 0,404 – 0,849 · TB từng mục **0,572 – 0,729** |
| `Trinh` vs `Katie` | **0,693** |
| `Trinh` vs `Không chỉ định` | **0,743** |
| `Katie` vs `Không chỉ định` | **0,678** |
| `Khoa` vs `Hùng` | **0,562** |
| `Hùng` vs `David` | **0,512** |
| `Khoa` vs `David` | **0,460** |
| mọi cặp nam–nữ | 0,240 – 0,291 |

**Đọc bảng này:** ba mục `Trinh` · `Katie` · `Không chỉ định` giống nhau
**0,68–0,74** — tức **cao hơn cả mức "cùng một giọng" của chính chúng**
(0,572–0,729). Ba mục `Khoa` · `Hùng` · `David` cũng vậy (0,46–0,56, nằm gọn
trong dải TRONG-giọng). Chỉ có ranh giới **nam/nữ** là thật (0,24–0,29).

> **SỐ GIỌNG THẬT = 2** (một nam · một nữ), không phải 3 giọng Việt như lượt 9
> ghi, và cũng không phải 5 như ô chọn giọng gợi ý. `Khoa`/`Hùng`/`David` là
> **một giọng**; `Trinh`/`Katie`/mặc-định là **một giọng**.

**Và giọng KHÔNG ĐỨNG YÊN.** Đây là con số thứ hai đáng lo: cùng một mục, cùng
một câu, hai lượt chạy khác nhau chỉ giống nhau **0,572–0,729** — trong khi
edge-tts ở điều kiện KHÓ HƠN (khác câu) vẫn giữ **0,782**. Nghĩa là mỗi lần
bấm xuất, "Khoa" có thể ra một người hơi khác. Với 200-300 kênh chạy sản xuất,
đó là giọng kênh **trôi giữa các tập** mà không ai chỉnh được.

---

*(còn tiếp — các bộ đo tiếp theo ghi bên dưới, mỗi bộ xong là commit)*
