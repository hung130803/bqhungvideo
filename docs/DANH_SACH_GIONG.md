# DANH SÁCH GIỌNG ĐỌC — MỞ RA LÀ BIẾT CHỌN GIỌNG NÀO

*Viết cho anh Hùng, ngày 19/08/2026. Anh nói: "phần chọn giọng nó không phân
gì cả, rất lung tung, không biết chọn sao" và "ghi riêng chi tiết ra".*

> **Nếu chỉ có 1 phút:** đọc mục **1** (chọn nhanh) rồi thôi.
> Mục 2–3 là bảng đầy đủ. Mục 4–6 là số đo để chứng minh.

---

## 0. BA CÂU TRẢ LỜI NGẮN

**Giọng nào cũng MIỄN PHÍ trừ hai loại:** ElevenLabs và Vbee. Hai loại đó
chỉ hiện ra khi anh đã dán key vào Cài đặt AI — chưa dán thì chúng không có
trong danh sách, nên **không thể bấm nhầm vào chỗ mất tiền**.

**Giọng phải tải model chỉ có hai họ:** Piper (212 MB) và OmniVoice (6,1 GB).
Danh sách ghi thẳng số MB/GB ngay cạnh tên. Chưa tải mà chọn thì app tự đọc
bằng giọng thường và **nói ra là nó đã lùi** — không im lặng.

**Giọng đang dùng hằng ngày là edge-tts, và nó đang là loại tốt nhất trong
nhà** về khoản chữ chạy khớp lời (15,7 ms — xem mục 4). Đừng đổi hẳn sang
loại khác chỉ vì nó "chạy trên máy".

---

## 1. CHỌN NHANH — CHỈ CẦN NHỚ BẢNG NÀY

| Anh muốn | Chọn | Vì sao |
|---|---|---|
| **Video tiếng Việt, nam** | **Nam Minh** | giọng Việt nam duy nhất của edge-tts, nhấn nhá **4,0** |
| **Video tiếng Việt, nữ** | **Hoài My** | giọng Việt nữ duy nhất của edge-tts, nhấn nhá **3,2** |
| **Muốn giọng Việt KHÁC đi** | Nam Minh / Hoài My **— trầm · hơi trầm · hơi cao · cao** | vẫn 2 người đọc đó nhưng đổi cao độ, nghe ra là người khác |
| **Video tiếng Anh, kể chuyện** | **Ryan** (Anh Quốc) | nhấn nhá **5,4** — cao nhất trong 42 giọng Anh |
| **Video tiếng Anh, nam trầm ấm** | **Andrew — bản tiếng Anh** | nhấn nhá **4,5** |
| **Một giọng đọc được MỌI thứ tiếng** | **William** hoặc **Emma** (bản đa ngôn ngữ) | nhấn nhá **4,7** |
| **Không muốn phụ thuộc mạng** | **Piper** (tải 212 MB) | chạy hẳn trên máy — nhưng chữ bám lời kém hơn (29,5 ms) |

**Hai cái tên hay gây nhầm — Andrew và Brian có HAI bản, và chúng là HAI
GIỌNG KHÁC NHAU thật:**

| | nhấn nhá | đọc được tiếng gì |
|---|---|---|
| **Andrew — bản tiếng Anh** (`en-US-AndrewNeural`) | **4,5** rất truyền cảm | chỉ tiếng Anh |
| **Andrew — bản đa ngôn ngữ** (`en-US-AndrewMultilingualNeural`) | **3,8** truyền cảm | mọi thứ tiếng |
| **Brian — bản tiếng Anh** (`en-US-BrianNeural`) | **2,7** đều đều | chỉ tiếng Anh |
| **Brian — bản đa ngôn ngữ** (`en-US-BrianMultilingualNeural`) | **2,7** đều đều | mọi thứ tiếng |

Danh sách trong app nay ghi thẳng **[bản tiếng Anh]** / **[bản đa ngôn ngữ]**
vào cuối dòng, nên nhìn dòng đang chọn là biết ngay đang dùng bản nào.

---

## 2. SO SÁNH 6 NGUỒN GIỌNG — TIỀN, TẢI, CHẤT LƯỢNG

Đây là bảng quan trọng nhất. Mọi con số đều là **số đo**, chỗ nào chưa đo thì
ghi thẳng "chưa đo" chứ không đoán.

| Nguồn | Số giọng trong app | Tiền | Phải tải | Chữ chạy lệch lời | Đọc sai chữ (tiếng Việt) | Bán video được không |
|---|---|---|---|---|---|---|
| **edge-tts** *(đang dùng)* | **84** | **miễn phí** | không | **15,7 ms** — tốt nhất | **6,2 %** | được; rủi ro nằm ở điều khoản Microsoft (đã khai `LICENSES.txt` mục 5) |
| **Piper** | 1 (Việt) | miễn phí | **212 MB** | 29,5 ms | chưa đo | **được** — MIT + dữ liệu CC BY 4.0 |
| **OmniVoice** | 5 | miễn phí | **6,1 GB** | 90–119 ms | **16,9 %** | **KHÔNG** — trọng số CC-BY-NC cấm thương mại |
| **VieNeu** *(đang thêm)* | 20 dựng sẵn | miễn phí | 286 MB | 14,6–15,4 ms | 7,7 % (giọng mặc định) | **CHƯA RÕ** — xem mục 5 |
| **ElevenLabs** | tuỳ tài khoản | **tốn hạn mức** | không | ngang edge-tts | chưa đo | được (theo gói đã mua) |
| **Vbee** | 3 | **tốn tiền theo ký tự** | không | 90–119 ms | chưa đo | được (theo gói đã mua) |

**Đọc bảng này thế nào:**

- **"Chữ chạy lệch lời"** = phụ đề hiện sớm/muộn hơn tiếng bao nhiêu. Dưới
  ~25 ms thì tai người không nhận ra. **90–119 ms là nhìn ra được.**
- **"Đọc sai chữ"** = trong 100 chữ thì máy đọc sai mấy chữ. edge-tts 6,2 % là
  mốc; OmniVoice **16,9 % là gần gấp 3**.
- **OmniVoice là chỗ duy nhất có rào pháp lý cứng.** Nhà phát hành ghi rõ cấm
  dùng kiếm tiền. App vẫn cho chọn (anh đã quyết) nhưng **nhãn luôn nói ra**.

---

## 3. BẢNG ĐẦY ĐỦ — 90 GIỌNG

Cột **"Mã giọng"** là thứ ghi vào mẫu; anh không cần dùng tới, để đây để lúc
cần đối chiếu.

Cột **"Nhấn nhá"** là giọng lên xuống nhiều hay đọc đều đều:
**từ 4,1 trở lên = rất truyền cảm · 3,6–4,0 = truyền cảm · 3,1–3,5 = vừa ·
dưới 3,1 = đều đều.**

> **HAI ĐIỀU PHẢI BIẾT KHI ĐỌC CỘT NHẤN NHÁ** (nếu không sẽ chọn sai):
>
> 1. **Chỉ so được TRONG CÙNG MỘT TIẾNG.** Mỗi giọng được đo bằng câu đúng
>    tiếng của nó, mà mỗi ngôn ngữ có nhịp điệu riêng. `Hamed` tiếng Ả Rập
>    **5,9** đứng trên `Ryan` tiếng Anh **5,4** **không** có nghĩa giọng Ả Rập
>    hay hơn. So Ryan với Andrew thì chắc; so Ryan với Nam Minh thì không.
> 2. **Số cao KHÔNG có nghĩa là HAY HƠN.** Nó chỉ đo độ lên xuống. Kể chuyện /
>    giật gân thì cần cao; đọc tin tức, hướng dẫn thì giọng đều lại dễ nghe
>    hơn. **Tôi không có tai — anh nghe rồi chốt**, số chỉ để anh khỏi phải dò
>    tay 90 giọng.

### edge-tts — Tiếng Việt (10 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Nam Minh — Nam chuẩn | Nam | `vi-VN-NamMinhNeural` | **4,0** | truyền cảm |
| Nam Minh — trầm | Nam | `vi-VN-NamMinhNeural|-20Hz` | **4,0 *(số của giọng gốc)*** | truyền cảm |
| Nam Minh — hơi trầm | Nam | `vi-VN-NamMinhNeural|-10Hz` | **4,0 *(số của giọng gốc)*** | truyền cảm |
| Nam Minh — hơi cao | Nam | `vi-VN-NamMinhNeural|+10Hz` | **4,0 *(số của giọng gốc)*** | truyền cảm |
| Nam Minh — cao | Nam | `vi-VN-NamMinhNeural|+20Hz` | **4,0 *(số của giọng gốc)*** | truyền cảm |
| Hoài My — Nữ nhẹ nhàng | Nữ | `vi-VN-HoaiMyNeural` | **3,2** | vừa |
| Hoài My — trầm | Nữ | `vi-VN-HoaiMyNeural|-20Hz` | **3,2 *(số của giọng gốc)*** | vừa |
| Hoài My — hơi trầm | Nữ | `vi-VN-HoaiMyNeural|-10Hz` | **3,2 *(số của giọng gốc)*** | vừa |
| Hoài My — hơi cao | Nữ | `vi-VN-HoaiMyNeural|+10Hz` | **3,2 *(số của giọng gốc)*** | vừa |
| Hoài My — cao | Nữ | `vi-VN-HoaiMyNeural|+20Hz` | **3,2 *(số của giọng gốc)*** | vừa |

### edge-tts — ĐA NGÔN NGỮ (5 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| William | Nam | `en-AU-WilliamMultilingualNeural` | **4,7** | rất truyền cảm |
| Emma | Nữ | `en-US-EmmaMultilingualNeural` | **4,7** | rất truyền cảm |
| Andrew | Nam | `en-US-AndrewMultilingualNeural` | **3,8** | truyền cảm |
| Ava | Nữ | `en-US-AvaMultilingualNeural` | **3,4** | vừa |
| Brian | Nam | `en-US-BrianMultilingualNeural` | **2,7** | đều đều |

### edge-tts — Tiếng Anh (42 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Ryan | Nam | `en-GB-RyanNeural` | **5,4** | rất truyền cảm |
| Liam | Nam | `en-CA-LiamNeural` | **5,0** | rất truyền cảm |
| Emma | Nữ | `en-US-EmmaNeural` | **4,7** | rất truyền cảm |
| Prabhat | Nam | `en-IN-PrabhatNeural` | **4,6** | rất truyền cảm |
| Andrew | Nam | `en-US-AndrewNeural` | **4,5** | rất truyền cảm |
| Molly | Nữ | `en-NZ-MollyNeural` | **4,2** | rất truyền cảm |
| Connor | Nam | `en-IE-ConnorNeural` | **4,2** | rất truyền cảm |
| Natasha | Nữ | `en-AU-NatashaNeural` | **4,1** | rất truyền cảm |
| Sam | Nam | `en-HK-SamNeural` | **4,0** | truyền cảm |
| Libby | Nữ | `en-GB-LibbyNeural` | **4,0** | truyền cảm |
| Guy | Nam | `en-US-GuyNeural` | **4,0** | truyền cảm |
| NeerjaExpressive | Nữ | `en-IN-NeerjaExpressiveNeural` | **4,0** | truyền cảm |
| Roger | Nam | `en-US-RogerNeural` | **4,0** | truyền cảm |
| Emily | Nữ | `en-IE-EmilyNeural` | **3,9** | truyền cảm |
| Mitchell | Nam | `en-NZ-MitchellNeural` | **3,8** | truyền cảm |
| Neerja | Nữ | `en-IN-NeerjaNeural` | **3,6** | truyền cảm |
| Sonia | Nữ | `en-GB-SoniaNeural` | **3,6** | truyền cảm |
| Clara | Nữ | `en-CA-ClaraNeural` | **3,6** | truyền cảm |
| Wayne | Nam | `en-SG-WayneNeural` | **3,5** | vừa |
| Elimu | Nam | `en-TZ-ElimuNeural` | **3,5** | vừa |
| Thomas | Nam | `en-GB-ThomasNeural` | **3,4** | vừa |
| Aria | Nữ | `en-US-AriaNeural` | **3,3** | vừa |
| Eric | Nam | `en-US-EricNeural` | **3,3** | vừa |
| Christopher | Nam | `en-US-ChristopherNeural` | **3,3** | vừa |
| Yan | Nữ | `en-HK-YanNeural` | **3,2** | vừa |
| James | Nam | `en-PH-JamesNeural` | **3,1** | đều đều |
| Luke | Nam | `en-ZA-LukeNeural` | **3,1** | đều đều |
| Abeo | Nam | `en-NG-AbeoNeural` | **3,1** | đều đều |
| Jenny | Nữ | `en-US-JennyNeural` | **3,1** | đều đều |
| Luna | Nữ | `en-SG-LunaNeural` | **3,0** | đều đều |
| Ava | Nữ | `en-US-AvaNeural` | **3,0** | đều đều |
| Michelle | Nữ | `en-US-MichelleNeural` | **2,8** | đều đều |
| Steffan | Nam | `en-US-SteffanNeural` | **2,8** | đều đều |
| Maisie | Nữ | `en-GB-MaisieNeural` | **2,7** | đều đều |
| Brian | Nam | `en-US-BrianNeural` | **2,7** | đều đều |
| Chilemba | Nam | `en-KE-ChilembaNeural` | **2,7** | đều đều |
| Imani | Nữ | `en-TZ-ImaniNeural` | **2,7** | đều đều |
| Leah | Nữ | `en-ZA-LeahNeural` | **2,6** | đều đều |
| Asilia | Nữ | `en-KE-AsiliaNeural` | **2,6** | đều đều |
| Ana | Nữ | `en-US-AnaNeural` | **2,4** | đều đều |
| Ezinne | Nữ | `en-NG-EzinneNeural` | **2,4** | đều đều |
| Rosa | Nữ | `en-PH-RosaNeural` | **2,4** | đều đều |

### edge-tts — Tiếng Ả Rập (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Hamed | Nam | `ar-SA-HamedNeural` | **5,9** | rất truyền cảm |
| Zariyah | Nữ | `ar-SA-ZariyahNeural` | **2,9** | đều đều |

### edge-tts — Tiếng Đức (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Conrad | Nam | `de-DE-ConradNeural` | **4,9** | rất truyền cảm |
| Katja | Nữ | `de-DE-KatjaNeural` | **3,4** | vừa |

### edge-tts — Tiếng Tây Ban Nha (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Alvaro | Nam | `es-ES-AlvaroNeural` | **4,7** | rất truyền cảm |
| Elvira | Nữ | `es-ES-ElviraNeural` | **2,3** | đều đều |

### edge-tts — Tiếng Pháp (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Henri | Nam | `fr-FR-HenriNeural` | **3,6** | truyền cảm |
| Denise | Nữ | `fr-FR-DeniseNeural` | **2,3** | đều đều |

### edge-tts — Tiếng Hindi (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Madhur | Nam | `hi-IN-MadhurNeural` | **5,2** | rất truyền cảm |
| Swara | Nữ | `hi-IN-SwaraNeural` | **4,1** | rất truyền cảm |

### edge-tts — Tiếng Indonesia (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Ardi | Nam | `id-ID-ArdiNeural` | **3,2** | vừa |
| Gadis | Nữ | `id-ID-GadisNeural` | **3,2** | vừa |

### edge-tts — Tiếng Ý (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Diego | Nam | `it-IT-DiegoNeural` | **4,0** | truyền cảm |
| Elsa | Nữ | `it-IT-ElsaNeural` | **3,2** | vừa |

### edge-tts — Tiếng Nhật (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Keita | Nam | `ja-JP-KeitaNeural` | **4,7** | rất truyền cảm |
| Nanami | Nữ | `ja-JP-NanamiNeural` | **4,0** | truyền cảm |

### edge-tts — Tiếng Hàn (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| InJoon | Nam | `ko-KR-InJoonNeural` | **4,5** | rất truyền cảm |
| SunHi | Nữ | `ko-KR-SunHiNeural` | **3,8** | truyền cảm |

### edge-tts — Tiếng Bồ Đào Nha (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Antonio | Nam | `pt-BR-AntonioNeural` | **5,7** | rất truyền cảm |
| Francisca | Nữ | `pt-BR-FranciscaNeural` | **2,9** | đều đều |

### edge-tts — Tiếng Nga (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Dmitry | Nam | `ru-RU-DmitryNeural` | **5,2** | rất truyền cảm |
| Svetlana | Nữ | `ru-RU-SvetlanaNeural` | **3,0** | đều đều |

### edge-tts — Tiếng Thái (2 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Niwat | Nam | `th-TH-NiwatNeural` | **4,3** | rất truyền cảm |
| Premwadee | Nữ | `th-TH-PremwadeeNeural` | **3,6** | truyền cảm |

### edge-tts — Tiếng Trung (3 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Yunjian | Nam | `zh-CN-YunjianNeural` | **5,0** | rất truyền cảm |
| Xiaoxiao | Nữ | `zh-CN-XiaoxiaoNeural` | **3,7** | truyền cảm |
| Yunxi | Nam | `zh-CN-YunxiNeural` | **3,7** | truyền cảm |

### OmniVoice — chạy hẳn trên máy (5 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Nam cao tuổi rất trầm | Nam | `ov:ong_gia` | **4,9** | rất truyền cảm |
| Nam trẻ | Nam | `ov:nam_tre` | **4,2** | rất truyền cảm |
| Nam trung niên trầm | Nam | `ov:nam_tram` | **4,1** | truyền cảm |
| Nữ trẻ | Nữ | `ov:nu_tre` | **3,6** | truyền cảm |
| Nữ trung niên ấm | Nữ | `ov:nu_am` | **3,4** | vừa |

### Piper — chạy hẳn trên máy (1 giọng)

| Tên | Giới | Mã giọng (dán vào mẫu) | Nhấn nhá | Nghe ra sao |
|---|---|---|---|---|
| Giọng Việt chạy trên máy (`vais1000`) | Nữ | `piper:vi_VN-vais1000-medium` | **3,1** | vừa |

---

## 4. SỐ ĐO — LẤY Ở ĐÂU RA

Không con số nào trong tài liệu này là ước lượng. Nguồn từng cột:

| Cột | Đo bằng cách nào | Ghi ở đâu |
|---|---|---|
| **Nhấn nhá** | mỗi giọng đọc **4 câu đúng tiếng của nó** (kể · hỏi · cảm thán · kể dài) qua **đúng cửa lượt xuất thật** đi, rồi đo độ lệch chuẩn cao độ theo nửa cung | `app/core/nhan_nha.py` — bảng 82 giọng |
| **Chữ chạy lệch lời** | dò lúc thật sự bắt đầu phát tiếng (`silencedetect`) rồi so với mốc chữ | `docs/GIONG_NHAN_BAN.md` mục C5 |
| **Đọc sai chữ** | cho máy nghe chép ngược file tiếng ra chữ rồi đếm chữ lệch | `docs/GIONG_THU_TAY.md`, `docs/GIONG_LUOT_7.md` |
| **Dung lượng phải tải** | chạy thật lệnh tải vào thư mục rỗng rồi đo | `piper_tts` 212,4 MB · `giong_ngoai` 6,1 GB |
| **Giá tiền** | đọc bảng giá niêm yết của nhà cung cấp | `docs/GIONG_CHOT.md` |

**Bảng nhấn nhá tiền định — đã kiểm, không phải tin lời.** Đo lại lượt hai
trên 6 giọng: 5 giọng lệch **0,00 · 0,00 · 0,00 · +0,01 · +0,09**. Vì còn lệch
tới 0,09 nên app chỉ hiện **1 chữ số thập phân** — hiện 2 chữ số là chính xác
giả.

**Một con số bị truyền sai, đính chính ở đây:** có chỗ ghi *"OmniVoice nhấn nhá
2,16, đáy thang"*. **Sai.** 2,16 là **khoảng TRẢI của 11 giọng** OmniVoice
(3,64 − 1,48), không phải giá trị của một giọng. Đo từng giọng thì
`ov:nam_tre` ra **4,2** — cao hơn cả Nam Minh (4,0) lẫn Hoài My (3,2). **Lý do
nên cân nhắc bỏ OmniVoice là GIẤY PHÉP và ĐỌC SAI CHỮ (16,9 %), không phải
nhấn nhá.**

---

## 5. VieNeu — 20 GIỌNG VIỆT ĐANG ĐƯỢC THÊM VÀO

Một luồng khác đang nối bộ này vào app. Khi xong, 20 giọng sẽ nằm trong nhóm
**"TRÊN MÁY"** của danh sách (chỗ đã chừa sẵn).

**Cái tốt, đo được:** chữ bám lời **14,6–15,4 ms — ngang edge-tts**, tốt hơn
Piper (29,5 ms) và hơn OmniVoice (90–119 ms) rất xa. Đọc sai chữ **7,7 %**,
chỉ hơn edge-tts 1,5 điểm. Chỉ phải tải **286 MB**, chạy CPU.

**Cái phải hỏi trước khi dùng để kiếm tiền — nói thẳng:** mã và trọng số là
Apache-2.0 (sạch), **nhưng bảng giọng thì không**. Bộ 6 giọng cũ ghi rõ
`CC BY-NC 4.0` = **cấm thương mại**, còn **bộ 20 giọng mới KHÔNG khai giấy
phép gì cả**. Theo đúng lệ đã chốt trong repo này (giọng Piper `25hours_single`
ghi *"Unknown"* → **im lặng không phải là cho phép**), chỗ trống đó **không
được đọc thành "được dùng thoải mái"**. Chi tiết ở `docs/GIONG_VIENEU_V3.md`.

---

## 6. NHỮNG GÌ TÀI LIỆU NÀY CHƯA TRẢ LỜI ĐƯỢC

Ghi thẳng, để anh không tưởng là đã đủ:

- **Chưa ai nghe bằng tai người.** Toàn bộ bảng trên là số máy đo. File tiếng
  để anh tự nghe nằm ở `_NGHE_THU_ANH_HUNG\`.
- **"Đọc sai chữ" mới đo cho edge-tts · OmniVoice · VieNeu.** Piper,
  ElevenLabs và Vbee **chưa đo** — cột đó ghi "chưa đo" chứ không để trống cho
  đẹp bảng.
- **Cột "chữ chạy lệch lời" của ElevenLabs không đặt cạnh các số khác được.**
  Nó có mốc thật và đo ra ngang edge-tts, nhưng đo bằng **thước khác**; đặt
  chung một cột là so hai đơn vị.
- **"Tính cách" của từng giọng chỉ có với ~12 giọng** đã được mô tả tay
  (Andrew *nam trầm ấm*, Aria *nữ rõ ràng biểu cảm*...). 78 giọng còn lại chỉ
  có **tên · giới tính · nhấn nhá** — mô tả tính cách cho chúng là bịa.
- **Số giọng thay đổi theo máy.** Bảng này đếm trên máy dev (**90 giọng**).
  Máy chưa tải Piper/OmniVoice sẽ thấy ít hơn; máy có dán key ElevenLabs/Vbee
  sẽ thấy nhiều hơn.
