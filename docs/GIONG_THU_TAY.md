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

Giọng trải rộng nhất: `en-US-Andrew` **5,35** · hẹp nhất `en-US-Ana` **2,20**.

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

## 5. BỘ ĐO CUỐI — **THỨ ANH HÙNG XIN, ANH ĐANG CÓ SẴN NHIỀU HƠN ANH TƯỞNG**

Sau 4 bộ trên, câu trả lời "có bộ mới nào hơn không" là KHÔNG. Nên tôi quay thước
vào **chính thứ app đang chạy** — chỗ duy nhất hôm nay đo ra được con số VƯỢT MỐC.

### 5a. Anh Hùng đang có bao nhiêu giọng edge-tts (đếm bằng API, không đoán)

`edge_tts.list_voices()` trả **322 giọng**, trong đó:

| | số giọng |
|---|---|
| **tiếng Việt `vi-VN`** | **2** (HoaiMy nữ · NamMinh nam) — đúng như đã biết |
| **tiếng Anh** | **47 giọng / 14 vùng** — en-US 17 · en-GB 5 · en-IN 3 · và 11 vùng khác 2 giọng mỗi vùng (AU · CA · HK · IE · KE · NZ · NG · PH · SG · ZA · TZ) |

### 5b. **47 GIỌNG ANH TRẢI 3,53 — RỘNG HƠN MỐC 3,31.** Đây là số duy nhất hôm nay vượt mốc.

Đo nhấn nhá cả 47 giọng trên **cùng một câu tiếng Anh** (cùng thước, cùng lượt):

| | trải nhấn nhá |
|---|---|
| Chatterbox (núm cảm xúc) | 1,84 |
| OmniVoice (11 giọng thiết kế) | 2,16 |
| **Kani-TTS-Vie (5 mục)** | **2,26** |
| 17 giọng en-US — mốc cũ lượt 5 | 3,31 |
| 17 giọng en-US — đo lại hôm nay | 3,15 |
| **CẢ 47 giọng tiếng Anh của edge-tts** | **3,53** |

Trải nhất: `en-US-Andrew` **5,35** · `en-US-AndrewMultilingual` 5,25 ·
`en-US-Emma` 4,96 · `en-GB-Ryan` **4,85** · đều đều nhất `en-PH-Rosa` **1,82**.

→ **Chỉ cần mở ô chọn giọng cho đủ 47 giọng thay vì 17 giọng en-US là dải cảm xúc
rộng thêm 0,38 nửa cung, 0 đồng, 0 dòng mã model mới.** `en-GB-Ryan` 4,85 nằm
NGOÀI nhóm 17 giọng đang liệt kê, mà nó đứng thứ 5 toàn bảng.

### 5c. Núm `pitch` — **có tạo ra GIỌNG KHÁC, đo được**, và KHÔNG làm đọc sai

Đo bằng đúng thước ECAPA đã dùng cho Kani (mốc: hai giọng en-US khác nhau ≤ 0,314):

| | cao độ trung vị | cặp giống nhau THẤP NHẤT |
|---|---|---|
| HoaiMy `-50Hz` → `+50Hz` | 141,6 → 272,0 Hz | **0,059** |
| NamMinh `-50Hz` → `+50Hz` | 86,7 → 174,9 Hz | **0,013** |

Chọn ra bộ mà **mọi cặp** đều dưới 0,314 (tức đôi một khác nhau như hai giọng
en-US khác nhau):

* **NamMinh: `-50Hz` · `+0Hz` · `+50Hz` = 3 giọng** (0,147 · 0,013 · 0,175)
* **HoaiMy: `-50Hz` · `+0Hz` = 2 giọng** (0,139) — thêm `+50Hz` thì cặp
  `+0/+50` lên 0,461, quá mức, nên chỉ được 2

→ **2 giọng Việt của edge-tts đo ra 5 người nói đôi một khác nhau.**

**VÀ NÓ KHÔNG PHÁ TIẾNG VIỆT** — đây là phép kiểm bắt buộc vì tiếng Việt CÓ
THANH ĐIỆU, dịch cao độ là chỗ dễ làm sai dấu. Cho Groq chép ngược cả 10 file
(2 giọng × 5 mức): **sai từ 0,0% và bịa chữ 0,0% ở CẢ 10/10**, câu chép ra đúng
nguyên văn từng chữ ở mọi mức.

> ⚠ **PHẢI NÓI RÕ GIỚI HẠN CỦA SỐ NÀY, ĐỪNG ĐỌC QUÁ:** ECAPA **rất nhạy với cao
> độ**. Nó nói "hai vector người nói khác nhau" — điều đó đúng và đo được, nhưng
> tai người có thể nghe ra *"vẫn một người, nói cao/thấp hơn"* chứ không phải
> *"một người khác"*. **Tôi không có tai, nên chỗ này anh Hùng phải nghe rồi
> chốt.** File để nghe: `L10_pit_*.wav`. App **đã có sẵn** đường này (cổng 65 —
> nút Nghe thử đã liệt kê "edge-tts + biến thể cao độ"), nên thử là 0 công.

### 5d. Núm `pitch` cho thêm GIỌNG, **không** cho thêm CẢM XÚC

Đo nhấn nhá của NamMinh qua 5 mức pitch: **3,73 – 3,85 = trải 0,12**. Tức nó dịch
cả giọng lên/xuống chứ không làm giọng lên xuống nhiều hơn. Muốn thêm cảm xúc thì
phải **đổi GIỌNG** (mục 5b), không phải xoay núm.

### 5e. Ba giọng Việt đang có: **là 3 giọng khác nhau thật, nhưng 2 giọng nữ hơi giống**

| cặp | giống nhau |
|---|---|
| edge HoaiMy vs edge NamMinh | **0,189** — khác rõ |
| edge NamMinh vs Piper vais1000 | **0,259** — khác rõ |
| **edge HoaiMy vs Piper vais1000** | **0,544** — khác (dưới mức "cùng người" 0,70) nhưng **GẦN NHAU**, cùng nữ |

Hai giọng Piper còn lại trong kho chính thức **không dùng được**: `vivos`
CC-BY-NC (cấm thương mại) · `25hours_single` giấy phép **"Unknown"**.

---

## 6. BẢNG TỔNG — ĐỦ 7 CỘT ANH HÙNG ĐẶT

| bộ | giọng **THẬT** | nhấn nhá TRẢI | sai từ Việt | sai từ Anh | **bịa chữ** | mốc từng chữ | giấy phép |
|---|---|---|---|---|---|---|---|
| **edge-tts** *(ĐANG CHẠY)* | **2 Việt** (→ **5** nếu tính biến thể cao độ) · **47 Anh** | **3,53** (47 giọng Anh) · 3,15 (17 en-US) | **5,2%** | **0,0%** | **0,0%** | **CÓ — rung 15,7 ms** | LGPLv3; rủi ro ở điều khoản Microsoft (đã khai `LICENSES.txt`) |
| **Piper `vais1000`** *(đã nối)* | 1 Việt | 3,24 *(lượt 1)* | *(chưa đo lượt này)* | — | *(chưa đo)* | SUY RA, rung 57,7 ms | MIT + dữ liệu CC BY 4.0 — **bán được** |
| **Kani-TTS-Vie** | **2** (1 nam · 1 nữ) — 18 cái TÊN nhưng 2 người nói; **giọng KHÔNG đứng yên** | **2,26** | **7,1%** | **0,0%** | **0,0%** | KHÔNG → cần `giong_hang.py` | 3 tầng: apache-2.0 (thẻ) / **LFM1.0** (nền) / **NVIDIA Open Model** (bộ giải mã) — **cả 3 CHO thương mại** |
| **LEMAS-TTS** | **0 giọng dựng sẵn** (zero-shot nhân bản) | không đo được | không đo được | không đo được | không đo được | KHÔNG | thẻ CC-BY-4.0, nhưng dữ liệu 150k giờ **giấu nguồn** + dấu vết Emilia (NC) |
| **MeloTTS-Vietnamese** | **1** (`spk2id` = `{"VI-default":0}`) | chưa đo | chưa đo | — | chưa đo | KHÔNG | **MIT + InfoRe CC-BY-4.0 — sạch nhất cả 2 tầng** |
| **VITS-OpenBible-Vietnamese** | **2** (`speakers.pth`) | chưa đo | chưa đo | — | chưa đo | KHÔNG | CC-BY-SA-4.0 — bán được nhưng **buộc chia sẻ lại** |
| **EveryVoice-OpenBible-VN** | không khai | chưa đo | chưa đo | — | chưa đo | KHÔNG | CC-BY-SA-4.0 |
| **Viet-SpeechT5** | — | — | — | — | — | — | **tên repo lượt 9 ghi là 401 = KHÔNG TỒN TẠI** |
| *(nhóm CC-BY-NC: v-tts 5 giọng · ZipVoice-VN · VibeVoice-VN · Dia-VN · Voxtral-4B · Parler-TTS-VN · CapSpeech-VN · omnivoice-VN)* | — | — | — | — | — | — | **CẤM thương mại → không thử, đúng đề bài** |
| *(nhóm giọng đi mượn Vbee: Kokoro-VI 14 giọng · VieNeu-lora-ngoc-huyen)* | — | — | — | — | — | — | **LOẠI vì đạo đức, không thử** |

## 7. TRẢ LỜI THẲNG BA CÂU HỎI

### 7.1 Có bộ nào ĐÁNG THÊM VÀO APP không? — **KHÔNG.**

| mốc anh Hùng đặt | ai vượt? |
|---|---|
| nhiều hơn **2 giọng Việt** | **KHÔNG BỘ MỚI NÀO.** Kani đo ra **2** · MeloTTS 1 · VITS-OpenBible 2 · LEMAS **0**. Bộ duy nhất có nhiều hơn 2 là Kokoro-VI (14) và v-tts (5) — một cái giọng đi mượn Vbee, một cái cấm thương mại. |
| nhấn nhá trải hơn **3,31** | **KHÔNG BỘ MỚI NÀO.** Kani 2,26. **Thứ duy nhất vượt là 47 giọng Anh của chính edge-tts: 3,53.** |
| sai từ không tệ hơn edge-tts | Kani: tiếng Anh **BẰNG** (0,0% = 0,0%), tiếng Việt **TỆ HƠN** (7,1% vs 5,2%). Các bộ khác chưa đo được. |
| **0% bịa chữ** | Kani **ĐẠT** (0,0% cả Việt lẫn Anh) — công bằng mà nói, nó qua được án tử. |

**Kani-TTS-Vie đạt 1/4 mốc.** Cộng thêm giá: **1,2 GB** tải về (448 MB thư viện
NeMo + 723 MB trọng số), bộ thư viện KHÔNG có trong `.exe`, không có mốc từng
chữ, đọc chậm hơn edge ~40% ở câu dài, và **giọng trôi giữa các lượt xuất**.

### 7.2 Anh Hùng có bao nhiêu giọng miễn phí HỢP PHÁP?

| | số giọng | nguồn |
|---|---|---|
| **Tiếng Việt** | **3** dùng ngay · **6** nếu bật biến thể cao độ | edge-tts HoaiMy + NamMinh (2) · Piper `vais1000` (1) · biến thể cao độ đo ra thêm 3 người nói khác (HoaiMy ×2, NamMinh ×3) |
| **Tiếng Anh** | **47** | edge-tts, 14 vùng — hiện app chỉ liệt kê 17 giọng en-US, **còn 30 giọng chưa mở** |

Cộng lại: **50 giọng dùng được ngay (3 Việt + 47 Anh)**, lên **53** nếu bật biến
thể cao độ. **KHÔNG tính** 5 giọng OmniVoice trong app — trọng số CC-BY-NC, nhà
phát hành CẤM thương mại (app đã dán cảnh báo đúng ở `giong_ngoai.CANH_BAO_GP_OV`).

### 7.3 Việc nên làm — theo thứ tự rẻ trước

1. **Mở ô chọn giọng tiếng Anh từ 17 lên 47.** Số đo: dải cảm xúc **3,15 → 3,53**.
   0 đồng, 0 model mới, không tải gì. Đây là việc duy nhất hôm nay có số chứng minh.
2. **Nghe thử 10 file `L10_pit_*.wav` rồi tự chốt** biến thể cao độ có ra "người
   khác" hay chỉ là "cùng người nói cao hơn". Đo đã xong: sai từ 0,0%, đôi một
   khác nhau theo máy. Chỉ còn thiếu cái tai của anh.
3. **KHÔNG thêm Kani-TTS-Vie.** 1/4 mốc, +1,2 GB.
4. **Nhớ MeloTTS-Vietnamese** như phương án cuối nếu ngày nào Microsoft đóng cửa
   edge-tts: 1 giọng, nhưng **sạch phép nhất cả hai tầng** (mã MIT + dữ liệu
   InfoRe CC-BY-4.0). Chưa đo chất lượng — cần dựng môi trường Python thứ hai.

---

## 8. NHỮNG GÌ CHƯA LÀM ĐƯỢC — GHI THẲNG

1. **Không đo được chất lượng của 4 bộ**: MeloTTS-Vietnamese · VITS-OpenBible ·
   EveryVoice-OpenBible · Viet-SpeechT5. Lý do thật: mỗi bộ đòi một bộ thư viện
   riêng xung đột với máy này (MeloTTS ghim `transformers==4.27.4` + `numpy==1.26.4`;
   VITS cần coqui-tts; EveryVoice cần `everyvoice`), **và cả 4 đều chỉ có 1-2
   giọng nên đã trượt mốc đếm giọng trước khi chạy**. Tôi đọc số giọng từ chính
   file cấu hình của model và ghi rõ cột chất lượng là "chưa đo" — **không bịa số**.
2. **LEMAS-TTS không chạy**: nó là zero-shot nhân bản, không có giọng dựng sẵn,
   nên chạy nó chỉ đo được "nó sao chép giọng tôi đưa vào tốt tới đâu" — không
   trả lời được câu hỏi của anh Hùng. Vẫn đọc được giao diện thật để chốt "0 giọng".
3. **Piper `vais1000` lượt này KHÔNG đo lại** sai từ / bịa chữ. Số 3,24 trong
   bảng là của lượt 1, **thước khác câu** — đừng so thẳng với 3,53.
4. **Tôi không có tai.** Mọi con số ở đây là số đo máy. Cụ thể ba chỗ CHỈ có tai
   anh Hùng chốt được: (a) biến thể cao độ có ra người khác không · (b) `en-GB-Ryan`
   4,85 nghe có hay hơn `en-US-Andrew` 5,35 không · (c) giọng Kani nghe thế nào.
5. **ECAPA nhạy cao độ** — đã ghi ở mục 5c. Con số "5 giọng Việt" là số MÁY;
   con số CHẮC CHẮN là **3**.
6. **Kani đo ở nhiệt độ mặc định của Space** (`temperature=0.7`, `do_sample=True`).
   Hạ nhiệt độ có thể làm giọng đứng yên hơn — **chưa thử**, và cũng không cứu
   được mốc đếm giọng (2) hay nhấn nhá (2,26).

---

## 9. XÁC NHẬN CÁCH LÀM

- **KHÔNG đẻ một luồng con nào** — tự làm hết.
- **KHÔNG sửa một file nào trong `app/`.** Lượt này ghi đúng một file:
  `docs/GIONG_THU_TAY.md`. Mọi script đo nằm NGOÀI repo (`D:\claude\_l10\`).
- **Không tăng version, không tag, không push.** Commit sau MỖI bộ đo xong (5 lần).
- **KHÔNG dùng tài khoản Hugging Face của anh Hùng** — không đăng nhập, không
  token. Space chặn thì chuyển sang chạy tại máy, không đi tìm chìa khoá.
- **Không đụng `_lib/`, `_giong_hang/`, `_giong_ngoai/`.** Dùng python của
  `_giong_ngoai/venv` (đọc thôi), gói phụ cài vào thư mục RIÊNG
  `D:\claude\_l10\pk` bằng `pip --target` nên **không thêm/xoá một gói nào** trong
  môi trường app đang chạy sản xuất.
- **GPU xin theo ĐỢT NGẮN**: 6 đợt, mỗi đợt 30 giây – 2 phút, nghỉ 20 giây giữa
  các đợt. Đỉnh VRAM 2,8/12 GB — luồng phát hành v2.37.0 chạy song song suốt.
- **Model tải về DỌN SẠCH** (xem mục 10). Ổ C: **372 GB trống** lúc bắt đầu và
  lúc xong, chưa bao giờ xuống gần 50 GB.
- **File nghe thử GIỮ LẠI** ở `%TEMP%\bq_tts_thu\nghe_thu\` — 135 file cũ
  **không xoá cái nào**, lượt này thêm ~110 file mang tiền tố `L10_`.

### FILE ĐỂ ANH HÙNG TỰ NGHE — `_NGHE_THU_ANH_HUNG\`

Tôi không có tai, nên ba thư mục này là chỗ anh chốt bằng tai mình:

| thư mục | nghe để làm gì |
|---|---|
| `luot10_cao_do\` (10 file) | **Quan trọng nhất.** `HoaiMy_-50Hz` … `p50Hz` và `NamMinh_-50Hz` … `p50Hz`. Máy nói đây là **những người nói khác nhau**; anh nghe xem có đúng là "người khác" hay chỉ là "cùng người nói cao/thấp hơn". Đây là câu hỏi 3 giọng Việt hay 5-6 giọng Việt. |
| `luot10_kani\` (7 file) | 5 mục giọng của Kani-TTS-Vie. Nghe `1_Khoa` · `2_Hung` · `4_David` cạnh nhau — máy đo ra **cùng một người**. Và `1b`/`1c` là **cùng mục "Khoa" chạy lượt khác** — nghe xem giọng có trôi không. |
| `luot10_giong_anh_moi\` (8 file) | 8 giọng tiếng Anh, trong đó **6 giọng app chưa mở** (`en-GB-Ryan` trải 4,85 · `en-GB-Sonia` · `en-IE-Connor` · `en-AU-Natasha` · `en-IN-Prabhat` · `en-NG-Ezinne` · `en-ZA-Luke`), kèm `en-US-Andrew` (5,35) để so. |

## 10. SỐ ĐO TÓM TẮT ĐỂ TRA LẠI SAU

```
BO CAU: 8 cau Viet + 8 cau Anh (4 cau dau moi thu tieng lay tu
        _bo_cau_thu_doc.py loai cau_thuong; 4 cau sau viet them)
THUOC:  sai tu/bia chu = Groq whisper-large-v3 chep nguoc + SequenceMatcher
        nhan nha       = f0_std (nua cung quanh trung vi), librosa.pyin
        so giong THAT  = ECAPA-TDNN (speechbrain/spkrec-ecapa-voxceleb)

TU KIEM BO DO ECAPA (bat buoc, chay tren edge-tts):
   TRONG-giong HoaiMy  0.704-0.848   (4 CAU KHAC NHAU = dieu kien KHO HON)
   TRONG-giong NamMinh 0.739-0.807
   HoaiMy vs NamMinh   0.209         -> khac giong, dung
   4 giong en-US, cao nhat 0.314     -> nguong doc so: >=0.70 cung nguoi

ARM DOI CHUNG edge-tts (chinh bo cau nay):
   sai tu vi 5.2%  bia 0.0%  8/8 cau
   sai tu en 0.0%  bia 0.0%  8/8 cau
   nhan nha 17 giong en-US  2.20-5.35 = TRAI 3.15  (moc luot 5: 3.31)
   nhan nha 47 giong en     1.82-5.35 = TRAI 3.53  <<< DUY NHAT VUOT MOC
   nhan nha 2 giong vi      3.38-3.74 = TRAI 0.36

KANI-TTS-VIE (chay TAI MAY, RTX 3060, nap model 5.9s, 2.0-3.9s/cau):
   so giong THAT = 2   (Khoa=Hung=David | Trinh=Katie=mac dinh)
   13 giong "cross-lingual" the model ke: 13/13 KHONG THAT (gom lai 3 cum,
      trung voi 2 giong tren; nur~mac dinh 0.764, jenny 0.710, seulgi 0.694)
   TRONG-giong 0.404-0.849 (TB tung muc 0.572-0.729) << edge 0.782
      -> GIONG KHONG DUNG YEN giua cac luot
   sai tu vi 7.1%  bia 0.0%  8/8   (edge 5.2%)
   sai tu en 0.0%  bia 0.0%  8/8   (edge 0.0%)
   nhan nha 5 muc 2.86-5.12 = TRAI 2.26   (edge 47 giong 3.53)
   cau Anh dai: Kani 9.1-11.5s vs edge ~7s -> doc cham hon ~40%
   GIAY PHEP 3 TANG: the apache-2.0 | nen lfm1.0 | codec NVIDIA Open Model
      ca 3 CHO thuong mai; codec ghi ro "ready for commercial use"

LEMAS-TTS: 0 giong dung san (gr.Audio "Reference Audio" = phai nap tieng mau)
   du lieu 150.000 gio dan cc-by-4.0 nhung KHONG NEU MOT NGUON NAO
   + file demo zh_emilia_*.mp3 (Emilia = CAM thuong mai)

SO GIONG doc tu CHINH FILE CAU HINH (khong chay model):
   MeloTTS-Vietnamese  spk2id {"VI-default":0}          = 1
   VITS-OpenBible      speakers.pth 2 muc               = 2
   Viet-SpeechT5 (ten luot 9 ghi)  HTTP 401             = KHONG TON TAI

EDGE-TTS KIEM KE (edge_tts.list_voices): 322 giong tong
   vi-VN 2 | tieng Anh 47 giong / 14 vung (en-US 17, en-GB 5, en-IN 3, 11 vung x2)

NUM PITCH (do bang ECAPA + Groq):
   HoaiMy  141.6 -> 272.0 Hz | cap thap nhat 0.059 | bo doi-mot-khac: -50,+0 = 2
   NamMinh  86.7 -> 174.9 Hz | cap thap nhat 0.013 | bo doi-mot-khac: -50,+0,+50 = 3
   SAI TU 0.0% + BIA 0.0% o CA 10/10 file -> khong pha thanh dieu tieng Viet
   nhan nha qua 5 muc pitch 3.73-3.85 = TRAI 0.12 -> them GIONG, khong them CAM XUC
   >> CANH BAO: ECAPA RAT NHAY CAO DO. So chac chan la 3 giong Viet, khong phai 5.

3 GIONG VIET DANG CO (ECAPA):
   HoaiMy vs NamMinh      0.189  khac ro
   NamMinh vs vais1000    0.259  khac ro
   HoaiMy vs vais1000     0.544  khac, nhung GAN NHAU (cung nu)
   (Piper vivos = CC-BY-NC | 25hours_single = "Unknown" -> khong dung duoc)

GIAY PHEP BAT SAI LUOT NAY (cong don 15 -> 16):
   danhtran2mind/Vi-SpeechT5-TTS  luot 9 ghi "MIT" | THAT: repo 401, khong ton tai
   (repo that la danhtran2mind/Viet-SpeechT5-TTS-finetuning)
   + bo sung TANG 3 cua Kani ma luot 9 khong kiem: NVIDIA Open Model License

CHUA DO: chat luong cua MeloTTS / VITS-OpenBible / EveryVoice / Viet-SpeechT5
   (moi bo doi mot bo thu vien xung dot, va ca 4 chi co 1-2 giong nen da truot
    moc dem giong truoc khi chay) — KHONG BIA SO

script do: D:\claude\_l10\  (ngoai repo, khong dung app/)
file nghe thu: %TEMP%\bq_tts_thu\nghe_thu\L10_*   (~110 file, giu 135 file cu)
```

---

*Đo ngày 18/08/2026. Lượt 10. **Không đẻ luồng con nào** — tự làm hết.
**Không sửa file nào trong `app/`.** Không tăng version, không tag, không push.
Ổ C 372 GB trống trước và sau. Model tải về đã dọn.*
