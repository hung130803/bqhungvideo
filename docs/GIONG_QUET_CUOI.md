# LƯỢT QUÉT CUỐI — có bộ giọng Việt miễn phí nào tôi đã bỏ sót không?

*Ngày 18/08/2026. Lượt thứ 9. Anh Hùng đã hỏi 7 lần về giọng Việt hay miễn phí
trên GitHub, nên lượt này tôi quét cho **thật hết**, rồi chốt.*

**THUẦN TRA CỨU — không sửa một file nào trong `app/`. Không tăng version, không
tag, không push. Không đẻ một luồng con nào.**

---

## TRẢ LỜI NGẮN — ĐỌC ĐOẠN NÀY LÀ ĐỦ

### 1. Tôi tìm được **18 bộ MỚI** chưa từng đo. Không bộ nào đáng thay edge-tts.

Nhưng lượt này **khác 8 lượt trước**: tôi không chỉ nói "không có". Tôi tìm được
**đúng cái tên anh hỏi** — và tìm ra **vì sao nó miễn phí**.

### 2. Có model miễn phí mang **đúng tên "Ngọc Huyền"** — và nó là bản sao giọng Vbee. **KHÔNG NÊN DÙNG.**

Đây là phát hiện lớn nhất lượt này. Trên Hugging Face có
`pnnbao-ump/VieNeu-TTS-0.3B-lora-ngoc-huyen`. Thẻ model **tự viết bằng tiếng
Việt, nguyên văn**:

> *"LoRA adapter được fine-tune từ base model VieNeu-TTS-0.3B để huấn luyện
> giọng đọc **Ngọc Huyền (Vbee)**."*

Chính tác giả ghi chữ **(Vbee)** vào. Và đáng chú ý: **mọi model khác của anh ấy
đều `apache-2.0`, riêng cái này anh ấy dán `cc-by-nc-4.0` = CẤM KIẾM TIỀN.** Tức
người làm ra nó **biết** cái này khác, và tự đánh dấu là không được bán.

→ **Có thật, tải được, miễn phí. Nhưng nó là giọng đi mượn của Vbee, và cấm
thương mại.** Anh Hùng bán app / dùng app kiếm tiền nên đây là cửa đóng. Tôi ghi
ra để anh biết nó tồn tại (anh sẽ tự tìm thấy), **không phải để khuyên dùng.**

### 3. Bộ 14 giọng "sạch phép" hấp dẫn nhất — hoá ra cũng là bảng giọng Vbee.

`contextboxai/Kokoro-Vietnamese` (**37.804 lượt tải**) dán nhãn **apache-2.0**,
có **14 giọng Việt đặt tên sẵn**. Nhìn bảng nhãn là ra vấn đề:

`ngoc_huyen` (Ngọc Huyền) · `manh_dung` (Mạnh Dũng) · `thuc_trinh` (Thục Trinh)
· `mai_linh` · `mai_loan` · `diem_trinh` · `my_yen` · `phat_tai` · `thanh_dat` ·
`hung_thinh` · `tuan_ngoc` · `duc_an` · `duc_duy` · `storyvert`

**Ba cái đầu tôi đối chiếu được thẳng với bảng giọng thương mại của Vbee**:
Ngọc Huyền (giọng nữ Bắc được dùng nhiều nhất của Vbee), Mạnh Dũng (giọng nam
Bắc chuyên TVC), Thục Trinh (Vbee vừa ra bản nâng cấp cho đúng 3 giọng Mạnh Dũng
· Thục Trinh · Minh Hoàng). Và kho GitHub của nó **cố ý không công bố nguồn dữ
liệu** — `TRAINING.md` ghi thẳng *"Datasets … are intentionally ignored"*.

**Dán chữ `apache-2.0` lên một giọng đi sao chép thì không tự sinh ra quyền.**
Cái này còn nguy hơn bản LoRA ở mục 2, vì bản kia ít ra còn ghi thật là NC.

### 4. Bộ MỚI sạch phép tốt nhất: **Kani-TTS-Vie** — 3 giọng Việt. Vẫn ít hơn cái anh cần.

Apache trên giấy tờ là **SAI** (xem mục 5 bên dưới), giấy phép thật là **LFM1.0
của Liquid AI: CHO kiếm tiền tới doanh thu 10 triệu USD/năm** — anh còn rất xa
ngưỡng đó, nên **anh dùng được**. Nó có **3 giọng đặt tên** (Khoa – nam Bắc ·
Hùng – nam Nam · Trinh – nữ Nam), huấn luyện trên 500 giờ đa vùng miền.

**3 giọng so với 2 giọng edge-tts đang chạy = hơn đúng 1 giọng**, đổi lại phải
cài thêm model, mất mốc từng chữ, và chưa đo được chất lượng. Không đáng.

### 5. Bắt thêm **4 chỗ ghi sai giấy phép** (6 lượt trước đã bắt 11 chỗ, nay là 15).

Lần này có cái sai nằm ngay trong **README của chính model**, không phải blog:

| Chỗ ghi sai | Ghi là | Sự thật |
|---|---|---|
| `nineninesix/kani-tts-370m` (huy hiệu trong README) | huy hiệu **Apache-2.0** | trường `license:` ghi **`other` / `lfm1.0`** — giấy phép Liquid AI, có trần doanh thu 10 triệu USD |
| `thangquang09/parler-tts-vietnamese` (thẻ HF) | **apache-2.0** | GitHub gốc **của chính tác giả** ghi **CC BY-NC 4.0** |
| `thangquang09/capspeech-nar-vietnamese` (thẻ HF) | **mit** | cùng GitHub đó, cũng **CC BY-NC 4.0** |
| `splendor1811/omnivoice-vietnamese` (2.496 lượt tải) | **apache-2.0** | trọng số gốc OmniVoice là **CC-BY-NC** (đã chốt ở lượt 7) |

### 6. Một điều trong đề bài **SAI**, phải nói thẳng: **VietBud500 KHÔNG mở.**

Đề bài ghi *"VLSP · VietBud500 · InfoRe · Common Voice — các kho này giấy phép
mở"*. Tôi tra thẳng thẻ dataset:

| Kho dữ liệu | Giấy phép THẬT | Dùng bán được? |
|---|---|---|
| `doof-ferb/infore1_25hours` (InfoRe) | **CC-BY-4.0** | **ĐƯỢC** |
| Common Voice | CC0 | ĐƯỢC (nhưng **không có** model TTS tiếng Việt nào dùng nó) |
| `linhtran92/viet_bud500` (VietBud500) | **CC-BY-NC-SA-4.0** | **KHÔNG** |
| `capleaf/viVoice` | **CC-BY-NC-SA-4.0** | **KHÔNG** |
| `thivux/phoaudiobook` | **không khai giấy phép** | không rõ = không nên |

→ Trong 4 kho đề bài nêu, **chỉ InfoRe là thật sự mở**. Đây là lý do gốc khiến
gần như mọi model tiếng Việt hay đều dính NC: **kho dữ liệu tốt của tiếng Việt
phần lớn là NC**, model huấn luyện trên đó thì thừa hưởng lệnh cấm.

### 7. Kho giọng Piper CHÍNH THỨC: **vẫn đúng 3 giọng Việt, không thêm cái nào.**

Tôi liệt kê thẳng danh sách file của `rhasspy/piper-voices` chứ không đọc bài
giới thiệu: chỉ có `vais1000` · `25hours_single` · `vivos` — **y hệt lượt 1**.
Có 2 giọng Piper Việt MỚI nằm **ngoài** kho chính thức
(`vongocanhthi/acut-piper-vietnamese`) nhưng giấy phép ghi `other` = **không nói
rõ**, và im lặng không phải là cho phép.

---

## BẢNG ĐẦY ĐỦ — 18 BỘ MỚI TÌM ĐƯỢC

Cột giấy phép là **giấy phép TRỌNG SỐ** (đọc thẻ model + LICENSE gốc, không đọc
blog). Cột "mốc từng chữ": app đã có `giong_hang.py` (gióng hàng cưỡng bức, đo
được phủ 98,5%) nên **không có mốc KHÔNG còn là án tử như các lượt trước**.

### Nhóm A — giấy phép DÙNG BÁN ĐƯỢC

| Bộ | Giấy phép trọng số | Giọng Việt | Mốc từng chữ | Nghe thử |
|---|---|---|---|---|
| **Kani-TTS-Vie** `pnnbao-ump/kani-tts-370m-vie` | **LFM1.0** (Liquid AI) — cho thương mại **dưới 10 triệu USD/năm**. Thẻ ghi apache-2.0 là **SAI** | **3** có tên: Khoa (nam Bắc) · Hùng (nam Nam) · Trinh (nữ Nam) | KHÔNG → `giong_hang.py` lo | [Spaces](https://huggingface.co/spaces/pnnbao-ump/Kani-TTS-Vie) (sống) |
| **LEMAS-TTS** | **CC-BY-4.0** cả model lẫn dataset | zero-shot; `vi` là 1 trong 10 tiếng; **không công bố số giọng dựng sẵn** | KHÔNG | [Spaces](https://huggingface.co/spaces/LEMAS-Project/LEMAS-TTS) (sống) |
| **MeloTTS-Vietnamese** `nmcuong` | **MIT** (nền MeloTTS MIT) + dữ liệu **InfoRe CC-BY-4.0** — sạch cả hai tầng | **1** | KHÔNG | 3 file `samples/*.wav` trong kho |
| **Viet-SpeechT5** `danhtran2mind` | **MIT** (nền `microsoft/speecht5_tts` MIT) | **1** | KHÔNG | — |
| **VITS-OpenBible-Vietnamese** | **CC-BY-SA-4.0** (bán được, nhưng **buộc chia sẻ lại**) | **2** (đọc Kinh Thánh) | KHÔNG | — |
| **EveryVoice-OpenBible-Vietnamese** | CC-BY-SA-4.0 | ít, giọng đọc Kinh Thánh | KHÔNG | — |
| **index-tts-2-vietnamese** `dinhthuan` | thẻ ghi apache-2.0; nền IndexTTS-2 = **giấy phép bilibili** (vẫn **cho** thương mại) | nhân bản | KHÔNG | — |

### Nhóm B — CẤM KIẾM TIỀN (loại thẳng)

| Bộ | Giấy phép | Ghi chú |
|---|---|---|
| **v-tts** `tronghieuit` (**367 sao**, to nhất nhóm mới) | **CC BY-NC 4.0** — *"Commercial use requires written permission"* | Tiếc nhất: **5 giọng** dựng sẵn (NF · SF · NM1 · SM · NM2 = nữ/nam Bắc/Nam), chạy CPU, có nhân bản zero-shot. Demo trả 401 |
| **ZipVoice-Vietnamese-2500h** `hynt` | CC-BY-NC-SA-4.0 | 2.500 giờ, 34 lượt thích |
| **VibeVoice-Vietnamese-LoRA** `nmcuong` | CC-BY-NC-4.0 | nền Microsoft VibeVoice |
| **Dia-Vietnamese** `duyluandethuong` | CC-BY-NC-SA-4.0 | dữ liệu viVoice (cũng NC) — chặn kép |
| **Voxtral-4B-TTS** `viethang` | CC-BY-NC-4.0 | có sẵn nhiều vector giọng |
| **Parler-TTS Vietnamese** `thangquang09` | thẻ HF ghi apache-2.0 nhưng **GitHub tác giả ghi CC BY-NC 4.0** | Tiếc: **tả giọng bằng câu tiếng Việt** (*"Giọng nữ trẻ miền Bắc, nói chậm rãi"*) = số giọng gần như vô hạn |
| **CapSpeech-NAR Vietnamese** `thangquang09` | thẻ ghi mit, cùng GitHub **CC BY-NC 4.0**; thượng nguồn CapSpeech = **NOASSERTION** | có `duration_predictor` (ép thời lượng) |
| **omnivoice-vietnamese** `splendor1811` | thẻ ghi apache-2.0, **trọng số gốc CC-BY-NC** | 2.496 lượt tải — nhiều người đang dùng nhầm |

### Nhóm C — CÓ NHƯNG KHÔNG NÊN (giọng đi mượn của Vbee)

| Bộ | Vấn đề |
|---|---|
| **VieNeu-TTS-0.3B-lora-ngoc-huyen** + `-ngoc-huyen` + `-ngoc-huyen-gguf-Q4_0` | Thẻ model **tự ghi** *"giọng đọc **Ngọc Huyền (Vbee)**"*. Tác giả dán **cc-by-nc-4.0** trong khi mọi model khác của anh ấy là apache-2.0 |
| **Kokoro-Vietnamese** `contextboxai` (37.804 lượt tải) | 14 giọng, **3 tên đối chiếu trùng bảng giọng thương mại Vbee**; kho **cố ý không công bố nguồn dữ liệu**; vẫn dán **apache-2.0** |
| **acut-piper-vietnamese** `vongocanhthi` | 2 giọng Piper Việt mới, giấy phép **`other` = không nói rõ** |

---

## MỤC RIÊNG — VÌ SAO TÔI KHÔNG KHUYÊN DÙNG NHÓM C

Anh Hùng đã hỏi 7 lần, nên tôi trả lời thẳng chỗ này thay vì nói vòng.

**Câu hỏi thật của anh là: "sao người ta có giọng Ngọc Huyền miễn phí mà tôi
không có?"** Nay tôi trả lời được: **họ không có giấy phép của Vbee. Họ sao chép
giọng đó bằng model nhân bản, rồi đăng lên GitHub/Hugging Face.**

Vì sao anh **không nên** đi đường đó, ba lý do xếp theo mức nặng:

1. **Anh là người BÁN app, không phải người dùng ẩn danh.** Người đăng model lên
   HF ở nước ngoài thì khó truy; còn anh có tên, có khách hàng, có 200-300 kênh
   chạy sản xuất. Rủi ro dồn hết về phía anh, không về phía người đăng model.
2. **Chính tác giả đã đánh dấu là cấm thương mại.** Bản LoRA ghi `cc-by-nc-4.0`.
   Dùng nó để kiếm tiền là vi phạm ngay cả điều kiện của **người sao chép**, chưa
   nói tới Vbee.
3. **Nhãn `apache-2.0` của bản Kokoro không cứu được ai.** Người ta không thể cấp
   cho anh cái quyền mà chính họ không có. Điều khoản 4.2 của `policy.vbee.vn`
   cấm cấp phép lại — tôi đã chốt điều này ở lượt trước và nó vẫn đúng.

**Nói gọn: đường đi tới đúng 3 giọng anh muốn (HN-Ngọc Huyền · HN-Anh Khôi ·
HN-Minh Quân) là MUA của Vbee, hoặc không có.** Sau 9 lượt quét, kết luận này
không đổi — nhưng nay tôi biết chính xác *vì sao* trên mạng lại có bản miễn phí,
và đó là câu trả lời cho điều anh thắc mắc bấy lâu.

---

## CÓ BỘ NÀO HAY HƠN edge-tts VÀ NHIỀU GIỌNG HƠN KHÔNG?

**KHÔNG.**

Chấm theo đúng 2 điều kiện anh đặt ra:

| Điều kiện | Ai vượt? |
|---|---|
| Sai từ tiếng Việt < **6,8%** (mốc edge-tts) | **Không bộ nào đo được là hơn.** Chưa bộ mới nào có số công bố; bộ tôi thử được thì không hơn (xem dưới) |
| **Nhiều giọng Việt hơn 2** (edge-tts: HoaiMy + NamMinh) | **Chỉ 3 bộ có nhiều hơn 2 giọng, và cả 3 đều vướng:** v-tts 5 giọng (**NC**) · Kokoro-VI 14 giọng (**giọng Vbee**) · Kani-TTS-Vie 3 giọng (**sạch, nhưng chỉ hơn 1 giọng**) |

Nói cách khác: **bộ nào nhiều giọng thì bẩn phép, bộ nào sạch phép thì ít giọng.**
Đó là hình dạng của cả thị trường tiếng Việt lúc này, không phải tôi tìm chưa kỹ.

---

## KẾT LUẬN THẲNG SAU 9 LƯỢT

**Giọng Việt miễn phí hợp pháp tốt nhất cho anh vẫn là `edge-tts` — 2 giọng
(HoaiMy nữ · NamMinh nam), đang chạy sẵn trong app, sai từ 6,8%, có mốc từng chữ
thật.**

Xếp hạng cuối:

1. **`edge-tts` (đang dùng) — giữ nguyên.** Là bộ duy nhất trả **mốc từng chữ
   thật**; rung 15,7 ms, không bộ nào lượt này tới gần. 0 đồng, 0 công sửa.
2. **`Piper vais1000`** — đã nối sẵn vào app, chạy hẳn trên máy, không cần mạng.
   Giữ làm lựa chọn thứ hai như hiện tại.
3. **`Kani-TTS-Vie`** — *chỉ nếu anh thật sự cần thêm giọng nam/nữ miền Nam.*
   Được phép bán (dưới 10 triệu USD/năm). 3 giọng. Cần cài thêm, chưa đo chất lượng.
4. **`MeloTTS-Vietnamese`** — bộ **sạch phép nhất** cả hai tầng (mã MIT + dữ liệu
   InfoRe CC-BY-4.0), nhưng chỉ 1 giọng. Đáng nhớ nếu sau này cần một giọng
   không vướng gì tuyệt đối.

**Việc nên làm ngay: không làm gì cả.** Đây là lượt thứ 4 liên tiếp (6, 7, 8, 9)
ra cùng một kết luận. Thứ đang chạy vẫn là thứ tốt nhất trong tầm với.

---

## NHỮNG GÌ TÔI CHƯA LÀM ĐƯỢC — GHI THẲNG

1. **Tôi KHÔNG thử tay được bộ nào lượt này.** Lý do có thật, không phải lười:
   máy đang có **2 luồng khác chạy** (phát hành v2.37.0 và đo VieNeu nhân bản) và
   việc này bị dặn **không được chiếm CPU/GPU**. Thử thật một bộ = tải 1-4 GB
   trọng số + chiếm GPU vài phút. Tôi **chủ động dừng** ở mức tra cứu thay vì
   giành máy với luồng đang phát hành.
   → Vì vậy **mọi số "sai từ / bịa chữ" của 18 bộ mới đều CHƯA ĐO**. Tôi không
   bịa số. Bảng trên chỉ có thứ đọc được từ thẻ model, LICENSE và danh sách file.
2. **Số giọng của LEMAS-TTS chưa xác định.** Nó khai `vi` trong 10 thứ tiếng và
   là zero-shot, nhưng không công bố số giọng dựng sẵn. Đây là bộ **CC-BY-4.0
   sạch nhất** trong nhóm mới nên nếu anh muốn tôi đào tiếp thì đây là chỗ đáng đào.
3. **Nghi ngờ về Kokoro-Vietnamese là SUY LUẬN TỪ BẰNG CHỨNG, không phải bản án.**
   Bằng chứng: 3 tên giọng trùng bảng Vbee + kho cố ý giấu nguồn dữ liệu + một
   dự án khác công khai thừa nhận sao chép đúng giọng đó. Tôi **không** tải trọng
   số về so sóng âm với giọng Vbee thật — muốn chắc 100% thì phải làm phép đó.
   Nhưng với người **bán app**, mức nghi ngờ này đã quá đủ để tránh.
4. **`LEMAS-Dataset` có thể dính Emilia.** Trong kho có file demo tên
   `zh_emilia_zh_0008385782.mp3`. Emilia là kho cấm thương mại (đã ghi ở lượt 2).
   Thẻ dataset khai CC-BY-4.0, nhưng tôi **chưa đối chiếu được** hai điều này.
   Ai định dùng LEMAS thì phải làm rõ chỗ đó trước.
5. **VLSP: không tra ra model TTS tiếng Việt nào dùng nó.** Truy vấn thẳng API
   Hugging Face lọc theo `text-to-speech` + `vlsp` ra **0 kết quả**.
6. **Tôi không nghe được.** Mọi kết luận ở đây là đọc giấy phép và metadata, chứ
   không phải chấm giọng hay dở. Tai anh mới là người chấm cuối.

---

## XÁC NHẬN CÁCH LÀM

- **KHÔNG đẻ một luồng con nào** — tôi tự làm hết.
- **KHÔNG sửa một file nào trong `app/`.** Việc này chỉ ghi đúng một file:
  `docs/GIONG_QUET_CUOI.md`.
- **Không tăng version, không tag, không push.**
- **Không tải một bộ trọng số nào** — chỉ đọc thẻ model, LICENSE, `config.json`
  và danh sách file (tổng tải về vài trăm KB).
- **Không chiếm CPU/GPU** để nhường 2 luồng đang chạy.
- Ổ C: **374 GB trống**, không đổi so với lúc bắt đầu.
- **Không đi tìm cách lấy giọng Vbee/FPT/Zalo/ElevenLabs**, không tìm key lậu,
  không tìm bản crack. Chỗ nào gặp thì ghi một dòng "có nhưng KHÔNG nên" rồi thôi
  (Nhóm C ở trên).

---

## SỐ ĐO TÓM TẮT ĐỂ TRA LẠI SAU

```
QUÉT: HF API (pipeline_tag=text-to-speech, lọc vi + search vietnam/viet)
      + GitHub API (pushed:>2025-08-01, 3 truy vấn) + kho rhasspy/piper-voices
KẾT QUẢ: 18 bộ MỚI ngoài 21 bộ đã đo 8 lượt trước

PIPER CHÍNH THỨC (đếm file, không đọc blog):
  vi/vi_VN/ -> vais1000 · 25hours_single · vivos = ĐÚNG 3, KHÔNG THÊM
  (ngoài kho: vongocanhthi/acut-piper-vietnamese = 2 giọng, giấy phép "other")

GIẤY PHÉP BẮT SAI LƯỢT NÀY (cộng dồn 6 lượt trước 11 -> nay 15):
  nineninesix/kani-tts-370m   huy hiệu README "Apache-2.0" | THẬT: other/lfm1.0
                              (LFM Open License, trần doanh thu 10 triệu USD/năm)
  thangquang09/parler-tts-vietnamese   thẻ apache-2.0 | GitHub tác giả: CC BY-NC 4.0
  thangquang09/capspeech-nar-vietnamese thẻ mit       | GitHub tác giả: CC BY-NC 4.0
  splendor1811/omnivoice-vietnamese    thẻ apache-2.0 | trọng số gốc CC-BY-NC

KHO DỮ LIỆU (đề bài ghi cả 4 là "mở" -> SAI 1):
  doof-ferb/infore1_25hours   CC-BY-4.0        MỞ THẬT
  Common Voice                CC0              mở, nhưng 0 model TTS vi dùng
  linhtran92/viet_bud500      CC-BY-NC-SA-4.0  KHÔNG MỞ
  capleaf/viVoice             CC-BY-NC-SA-4.0  KHÔNG MỞ
  thivux/phoaudiobook         không khai       không rõ
  VLSP                        0 model TTS vi tra ra được

SỐ GIỌNG VIỆT (bộ mới, nhiều nhất trước):
  Kokoro-Vietnamese  14  <- tên trùng bảng Vbee, KHÔNG NÊN
  v-tts               5  <- CC BY-NC 4.0, LOẠI
  Kani-TTS-Vie        3  <- SẠCH (LFM1.0), tốt nhất nhóm mới
  VITS-OpenBible      2  <- CC-BY-SA-4.0
  MeloTTS-vi          1  <- MIT + InfoRe CC-BY-4.0 = sạch nhất cả 2 tầng
  Viet-SpeechT5       1  <- MIT
  [đang dùng] edge-tts 2 giọng, sai từ 6,8%, CÓ mốc từng chữ thật (rung 15,7 ms)

GIỌNG "NGỌC HUYỀN" MIỄN PHÍ: CÓ THẬT, và là bản sao Vbee
  pnnbao-ump/VieNeu-TTS-0.3B-lora-ngoc-huyen
    thẻ model nguyên văn: "huấn luyện giọng đọc Ngọc Huyền (Vbee)"
    giấy phép cc-by-nc-4.0  <- tác giả TỰ đánh dấu cấm thương mại
    (mọi model khác cùng tác giả: apache-2.0)
  -> CÓ NHƯNG KHÔNG NÊN

CHƯA ĐO: sai từ · bịa chữ · số giọng thật của cả 18 bộ mới
  (nhường CPU/GPU cho 2 luồng đang chạy — không bịa số)
```

---

*Tra cứu ngày 18/08/2026. Lượt 9. **Không đẻ luồng con nào** — tự làm hết.
**Không sửa file nào trong `app/`.** Không tăng version, không tag, không push.
Không tải trọng số. Ổ C 374 GB trống, không đổi.*
