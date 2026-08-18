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

### 2d. 13 giọng "cross-lingual" thẻ model kể ra — **KHÔNG CÓ CÁI NÀO LÀ THẬT**

Thẻ model liệt kê thêm: *Puck · Kore · Andrew · Jenny · Simon · Seulgi · Bert ·
Thorsten · Maria · Mei · Ming · Karim · Nur*. Nghe thì tưởng bộ này có gần 20
giọng. Sinh đủ 13 file rồi đo bằng chính thước ECAPA:

**13/13 đều rơi vào một trong các giọng đã có.** `nur` giống mục "Không chỉ
định" **0,764** · `jenny` **0,710** · `seulgi` giống `Trinh` **0,694** ·
`maria` giống `Hùng` **0,661**. Gom cụm 13 tên đó với nhau chỉ ra **3 cụm**, mà
3 cụm đó lại trùng với 2 giọng đã đếm được ở mục 2c.

→ **Tên giọng có 18. Người nói có 2.** Đây đúng là cái bẫy đề bài dặn: đừng đọc
tên tham số, phải đo âm.

### 2e. Sai từ · bịa chữ · nhấn nhá — trên ĐÚNG bộ câu của arm đối chứng

| | **Kani-TTS-Vie** | **edge-tts** (mốc) |
|---|---|---|
| sai từ **tiếng Việt** | **7,1%** | **5,2%** |
| sai từ **tiếng Anh** | **0,0%** | **0,0%** |
| **bịa chữ** (cả 2 thứ tiếng) | **0,0%** | **0,0%** |
| số câu đo được | 8/8 và 8/8 | 8/8 và 8/8 |
| **nhấn nhá — TRẢI** | **2,26** (5 mục: 2,86 – 5,12) | **3,15** (17 giọng: 2,20 – 5,35) |
| tốc độ | 2,0 – 3,9 s/câu (RTX 3060) | 0,9 – 5,1 s/câu (qua mạng) |

Lỗi đọc thật của Kani: *"đi dạo **nhé**"* → *"đi dạo **né**"* ·
*"Bà cụ **ngồi** bên hiên nhà, **lặng lẽ**"* → *"Bà cụ **vội** bên hiên nhà,
**lạnh lẽ**"* · *"**Tiếng chuông vang** lên … cả **xóm**"* → *"**Tiến chung
văn** lên … cả **sống**"*.

**Ba điều đọc ra từ bảng này:**

1. **QUA được án tử: bịa chữ 0,0%.** Đây là chỗ viXTTS và Chatterbox chết. Kani
   sạch — nói cho công bằng.
2. **Tiếng Anh NGANG edge-tts (0,0% cả hai).** Đúng thứ anh Hùng hỏi, và Kani
   làm được. Nhưng "ngang" thì không có lý do gì để đổi.
3. **Tiếng Việt TỆ HƠN edge-tts** (7,1% so với 5,2%), và **nhấn nhá HẸP HƠN**
   (2,26 so với 3,15). Hai mốc quan trọng nhất đều thua.

> Ghi thêm một số đáng ngờ: câu tiếng Anh dài Kani đọc mất **11,5 s** (David) và
> **9,1 s** (Katie) trong khi edge-tts đọc cùng câu hết ~7 s — tức nó đọc **CHẬM
> HƠN ~40%**. Với clip ngắn phải nhét lời vào khung hình thì đó là chỗ phải ép
> tốc độ, mà ép là méo tiếng (bài học `atempo` v2.27.0).

### 2f. CHẤM KANI THEO 4 MỐC ANH HÙNG ĐẶT

| mốc phải vượt | Kani-TTS-Vie | đạt? |
|---|---|---|
| nhiều hơn **2 giọng Việt** | **2 giọng thật** (1 nam · 1 nữ), và cả 2 đều KHÔNG đứng yên giữa các lượt | **KHÔNG** |
| nhấn nhá trải hơn **3,15** | **2,26** | **KHÔNG** |
| sai từ không tệ hơn edge-tts | Việt **7,1%** vs 5,2% · Anh 0,0% vs 0,0% | **KHÔNG** (Việt tệ hơn) |
| **0% bịa chữ** | **0,0%** | **ĐẠT** |

**1/4. KHÔNG ĐÁNG THÊM VÀO APP.** Và nó còn đòi thêm **1,2 GB** (448 MB thư viện
NeMo + 723 MB trọng số) cùng một bộ thư viện nặng không nằm trong `.exe`.

**Bộ này CẦN `giong_hang.py`** — nó không trả mốc từng chữ.

---

## 3. LEMAS-TTS — **0 GIỌNG DỰNG SẴN**, đây là bộ NHÂN BẢN

Lượt 9 để ngỏ *"chưa biết bao nhiêu giọng — nếu anh muốn tôi đào tiếp thì đây là
chỗ đáng đào"*. Đào rồi, và câu trả lời **không cần chạy model** mới biết:

Đọc giao diện thật của Space (`inference_gradio.py`): ô đầu vào là
`ref_audio = gr.Audio(label="Reference Audio")` — **bắt buộc phải NẠP một đoạn
tiếng mẫu**. Không có một ô chọn giọng nào, không một giọng đặt tên nào. Thẻ
model cũng ghi thẳng: *"multilingual **zero-shot** text-to-speech"*, kiến trúc
flow-matching (họ F5-TTS).

→ **Số giọng dựng sẵn: 0.** Nó không cho anh Hùng giọng nào; nó **sao chép**
giọng từ đoạn tiếng anh đưa vào. Muốn có giọng Việt thì hoặc anh **tự thu giọng
mình**, hoặc lấy giọng người khác — mà cái sau đúng là đường lượt 9 đã kết luận
KHÔNG NÊN. Nên bộ "sạch phép nhất trong nhóm mới" này **không giải được bài toán
của anh**, dù giấy phép có sạch.

**Và giấy phép của nó cũng không sạch như thẻ ghi.** Thẻ dataset
`LEMAS-Dataset-train` khai `cc-by-4.0` cho **150.000 giờ / hơn 6.400 giờ tiếng
Việt**. Nhưng phần "Methods" chỉ nói *"filtered … depending on the **source
dataset**"* mà **KHÔNG NÊU MỘT CÁI TÊN NÀO**. Cùng dấu hiệu với
`Kokoro-Vietnamese` (`TRAINING.md` ghi *"Datasets … are intentionally ignored"*).
Cộng với bằng chứng lượt 9 đã bắt: trong kho có file demo
`zh_emilia_zh_0008385782.mp3` — **Emilia là kho CẤM thương mại**. Một kho 150 nghìn
giờ dán CC-BY-4.0 mà không dám kể nguồn thì với người **bán app** là cửa đóng.

## 4. BỐN BỘ CÒN LẠI TRONG NHÓM SẠCH PHÉP — ĐO ĐƯỢC ĐẾN ĐÂU, NÓI THẲNG

| bộ | số giọng — đo từ ĐÂU | có chạy end-to-end không |
|---|---|---|
| **MeloTTS-Vietnamese** `nmcuong` | **1** — đọc `spk2id` trong chính `pretrain/config.json`: `{"VI-default": 0}` | **KHÔNG** — xem lý do dưới |
| **VITS-OpenBible-Vietnamese** | **2** — đọc `speakers.pth`: `SPEAKER_00_Vietnamese`, `SPEAKER_01_Vietnamese` | KHÔNG |
| **EveryVoice-OpenBible-Vietnamese** | không khai; kho chỉ có `feature_prediction.ckpt` + `vocoder.ckpt` | KHÔNG |
| **Viet-SpeechT5** | tên repo lượt 9 ghi (`danhtran2mind/Vi-SpeechT5-TTS`) trả **HTTP 401 = KHÔNG TỒN TẠI**. Repo thật là `danhtran2mind/Viet-SpeechT5-TTS-finetuning` (10 lượt tải) | KHÔNG |

**VÌ SAO KHÔNG CHẠY MELOTTS — lý do kỹ thuật thật, không phải bỏ dở:**
bản Việt phải dùng nhánh riêng `manhcuong02/MeloTTS_Vietnamese`, mà
`requirements.txt` của nhánh đó ghim **`transformers==4.27.4`** và
**`numpy==1.26.4`** — máy này đang có transformers 5.15.0 / numpy 2.5.2. Tức phải
dựng một môi trường Python THỨ HAI với bộ ghim cũ (thêm ~2 GB torch nữa). **Và
dựng xong cũng không đổi kết luận: 1 giọng thì không thể vượt mốc "nhiều hơn 2
giọng Việt".** Nên tôi dừng ở chỗ đọc được số giọng từ chính file cấu hình của
model, và ghi rõ là CHƯA đo chất lượng.

Ba bộ còn lại cùng lý do: **1-2 giọng thì đã trượt mốc đếm giọng ngay từ đầu**,
mỗi bộ lại đòi một bộ thư viện riêng (coqui-tts · everyvoice · transformers cũ).
**Tôi không bịa số cho chúng.**

**Thêm một chỗ ghi sai của lượt 9 (cộng dồn: 15 → 16):** `Viet-SpeechT5
danhtran2mind` — tên repo đó **không tồn tại**. Bảng lượt 9 ghi "MIT" cho một
đường dẫn 401. Cái có thật là `Viet-SpeechT5-TTS-finetuning`.

---

*(còn tiếp — bộ đo cuối: lấy thêm giọng từ thứ ĐANG CÓ)*
