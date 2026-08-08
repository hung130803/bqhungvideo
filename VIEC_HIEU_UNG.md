# VIỆC: chuyển cảnh ở chỗ ghép đoạn + chữa quá tải luồng

---

## 🌏 ĐA QUỐC GIA — anh Hùng chốt 08/08/2026, CỔNG BẮT BUỘC
Nguyên văn: *"đảm bảo test đủ kiểu nhé, AI phải hiểu hết các loại nội dung đa
quốc gia nhé, k đc lỗi, thêm hiệu ứng âm thanh hợp lý bất chấp mọi nội dung quốc
gia, test kỹ đó nhé"*.

### VÌ SAO ĐÂY LÀ CHỖ NGUY HIỂM NHẤT — 2 lỗi thật đã xảy ra
1. **v2.11.1 (hồi quy tôi gây ra)**: khoá ngôn ngữ truyền **TÊN** ngôn ngữ
   ("English") vào tham số chỉ nhận **MÃ ISO** → `400 unsupported language` →
   chép lời chết → **MỌI video > 10 phút thành "Cắt cơ bản"**. Đã chữa bằng
   `_ma_iso()`.
2. **CJK không có dấu cách**: mọi chỗ dùng `.split()` để đếm từ đều **đếm sai
   gần hết** với tiếng Nhật/Trung. Đã phải làm `_word_tokens` + `_has_cjk`
   (việc #124-128). **Bẫy này còn sống**: bất cứ mã mới nào đếm từ bằng
   `.split()` là tái phát.

### PHẢI TEST — tối thiểu 6 nhóm ngôn ngữ, VIDEO THẬT
Kho video thật ở `C:\Users\Admin\Downloads\thùng rác` (kênh anh Hùng đang chạy).
Nếu thiếu nhóm nào thì **ghi rõ là thiếu**, đừng bịa.

| Nhóm | Đặc thù phải canh |
|---|---|
| **Nhật** (chính) | CJK không dấu cách · dọc/ngang · chữ cỡ lớn |
| **Trung** | CJK · phồn/giản thể |
| **Hàn** | Hangul · khoảng cách khác Nhật/Trung |
| **Anh** | mốc từng-từ đầy đủ (ca dễ nhất — dùng làm đối chứng) |
| **Việt** | dấu thanh chồng — dễ **cắt đáy khung** khi cỡ chữ lớn |
| **Ả Rập / Do Thái** (nếu có) | **viết PHẢI→TRÁI** — `libass` phải bật `fribidi` (build đã có `--enable-libfribidi`), kiểm thứ tự chữ trên khung THẬT |
| **Thái** | không dấu cách + dấu chồng tầng |
| **KHÔNG LỜI** | phải đi đường XEM HÌNH (v2.15.0), không rơi cắt cơ bản |

### 5 điều phải chứng minh cho TỪNG nhóm (đo, không đoán)
1. **Chép lời ra chữ đúng ngôn ngữ** — `language` trả về khớp, số câu > 0.
2. **AI chọn đoạn CHẠY** — ra clip có `llm_used=True`, **không** rơi "Cắt cơ bản".
   Rơi thì phải **ghi lý do** (v2.13.4 đã có).
3. **Phụ đề vẽ ĐÚNG** — render khung THẬT + **đếm pixel**, không tin `rc=0`.
   Ca Việt phải kiểm **không cắt đáy khung** (bài học `ny ≤ 0,80`).
4. **HIỆU ỨNG ÂM THANH hợp lý bất chấp quốc gia** — anh Hùng nhấn riêng ý này.
   `_loai_theo_khoang_nhay` chọn tiếng động theo **NỘI DUNG CHỖ NỐI** (nhảy
   ngược thời gian / gần liền mạch / câu chốt), **KHÔNG theo ngôn ngữ** → về lý
   thuyết là trung lập. **Phải CHỨNG MINH bằng số**: với mỗi nhóm, xuất ≥3 Part
   và kiểm **không phải Part nào cũng cùng một tiếng** (đúng lỗi cũ: mọi Part
   đều "ding"). Đo mức to nhỏ tiếng động so với tiếng gốc — **không được át
   lời** ở ngôn ngữ nào (đo RMS trước/sau).
5. **Hiệu ứng HÌNH cũng phải trung lập** — luật chọn dựa trên `nang_luong` +
   `chuyen_dong`, **không** dựa vào chữ. Kiểm: cùng một video, đổi nhãn ngôn ngữ
   → **kết quả chọn hiệu ứng phải Y HỆT**.

### QUÉT TĨNH bắt buộc
`grep` toàn repo tìm `.split()` dùng để **đếm từ / đo mật độ chữ** trong mã mới
(hiệu ứng, chuyển cảnh, bảng mẫu). Có là **FAIL** — phải dùng `_word_tokens`.
Cũng tìm chỗ nào so sánh **tên ngôn ngữ** thay vì **mã ISO**.

---

## 🔴 4 VIỆC CÒN SÓT — anh Hùng bắt được 08/08/2026
Nguyên văn: *"bạn bảo mấy cái này chưa làm đc thì cho vào tiến trình chạy chưa"*.
Anh soi lại danh sách "CHƯA làm được" 7 mục và phát hiện **tôi chỉ giao 3/7**
(máy nhân viên · build .exe · tổng rà soát). **4 mục dưới đây CHƯA ai làm:**

### A. 6 shader `libplacebo` CHƯA nối vào app
Kẹt vì `libplacebo` **không có timeline `enable`** → áp là áp **TOÀN clip**, trái
luật chống loè (hiệu ứng chỉ 0,3-0,8s ở điểm nhấn). **Cách chữa đã nhìn thấy:**
cắt mảnh riêng rồi concat — **y hệt đường `xfade_opencl` đã làm được** (kiến trúc
2n−1 mảnh). Xong phải đo: lệch độ dài **0 ms** · U/V **< 3** · render khung thật
+ đếm pixel.

### B. `export_vertical_clip` không có hiệu ứng/chuyển cảnh
Vì mẫu thiếu `video_rect`. **Là tình trạng CŨ, không phải hồi quy** — nhưng nghĩa
là kênh nào đi đường này thì **không có hiệu ứng gì cả**, mà app **im lặng**.
Phải: (1) đếm có bao nhiêu kênh/clip THẬT đi đường này (đọc DB thật, **CHỈ ĐỌC**)
· (2) nếu có kênh dùng thì nối hiệu ứng vào, hoặc **ít nhất báo rõ trong UI /
nhật ký** để anh Hùng biết mẫu đó không có hiệu ứng — **đừng im lặng**.

### C. Tối ưu giá **1,87× wall**
Bật hiệu ứng làm xuất chậm 1,87× (5,56s → 10,38s cho clip 24s). Với 200-300 kênh
đây là chi phí lớn. **Hướng rẻ hơn ĐÃ ĐO ĐƯỢC:** mức `manh` dùng GPU chỉ **1,60×**
vì không phải encode lại toàn clip. Áp cùng kiến trúc đó cho `nhe`/`vua`.
**Mốc: ≤ 1,4×** (ngân sách đã chốt từ đầu). Không đạt thì **báo số, đừng lờ**.

### D. `_test_pipe_integ.py` đang FAIL
Fail vì thiếu file nguồn đặt tay ở `%TEMP%`. **Lỗi có sẵn**, không nằm trong danh
sách cổng chặn `CLAUDE.md`. Nhưng để nguyên thì lần sau ai chạy cũng tưởng hỏng
thật. Sửa: tự sinh nguồn bằng `lavfi` (như cổng 37 làm), **hoặc** skip có in dòng
lý do rõ ràng. **Đừng để FAIL trơ.**

---

## ⭐ BƯỚC CUỐI BẮT BUỘC — TỔNG RÀ SOÁT (anh Hùng chốt 08/08/2026)

Nguyên văn: *"khi nào xong tất cả mọi thứ tôi yêu cầu, bạn kiểm tra rà soát lại
hết các phần đã làm tích hợp xem chạy đã mượt mà chưa, chạy nhiều kênh nhiều
luồng đã được chưa, xử lý AI đã oke chưa, có bị nghẽn hay bị lỗi gì k nhé. Chậm
mà chắc nhé. Bạn có thể tự chạy nhé, nào xong tự chạy."*

**Làm SAU KHI xong mọi việc khác. TỰ CHẠY, không cần hỏi lại anh Hùng.**
Đây là lượt chạy **CẢ HỆ THỐNG như thật**, không phải chạy lại từng cổng lẻ.

### 5 câu hỏi phải trả lời BẰNG SỐ
| # | Câu hỏi của anh Hùng | Cách chứng minh |
|---|---|---|
| 1 | **Tích hợp có chạy không?** | Chạy **e2e THẬT** qua app: quét nguồn → nhập → phân tích AI → cắt → xuất → xoá gốc. Ít nhất **5 video Nhật thật**, đủ cả ca có lời / không lời / hook-first / VFR. Đếm: bao nhiêu ra clip tốt, bao nhiêu lỗi. Mốc: **0 lỗi**. |
| 2 | **Chạy mượt chưa?** | Đo **trễ vòng lặp UI** liên tục ≥120 giây trong lúc dây chuyền chạy: trung vị **<30ms**, đỉnh **<150ms**. Kèm CPU + RAM đỉnh. |
| 3 | **Nhiều kênh nhiều luồng được chưa?** | **≥50 kênh** trong hàng chờ + **10 làn**. Đo: tổng luồng ffmpeg **≤2× nhân**, RAM đỉnh, có kênh nào bị **bỏ đói** không (làn cắt vs làn phân tích — bài học cổng 5 `_test_lane_starve`). |
| 4 | **Xử lý AI oke chưa?** | Trên ≥5 video: **bao nhiêu video ra clip AI, bao nhiêu rơi "Cắt cơ bản"** và **VÌ SAO** (đọc lý do trong nhật ký — v2.13.4 đã ghi). Kiểm luôn: video **không lời** phải ra clip bằng XEM HÌNH (v2.15.0), không rơi cơ bản. Đếm lượt Groq + số key còn sống. |
| 5 | **Có nghẽn không?** | Tìm **điểm nghẽn**: hàng chờ có job nào đợi > 10 phút? Làn nào đói? DB có bị khoá? `%TEMP%` có phình? ffmpeg mồ côi? WAL có gấp không? |

### Phải kiểm thêm (chỗ đã từng hỏng, đừng bỏ)
- **Hồi phục sau khi tắt app giữa chừng**: đang chạy 20 job → tắt app → mở lại → **không được tự chạy lại job đã HUỶ**, và sổ dây chuyền phải dựng lại được (cổng 7 + `_test_pipe_overlap`).
- **DB**: `studio.db` có gấp WAL khi thoát không? Dung lượng DB tăng bao nhiêu sau 5 video?
- **Đĩa**: đo `%TEMP%` + thư mục xuất **trước/sau**. Rác `_seg_*` / `_MEI*` = **0**.
- **Máy nhân viên**: chạy lại toàn bộ trên venv khách (`requirements-build.txt`), giả lập thiếu NVENC + frei0r + OpenCL.
- **Bản đóng gói**: build `.exe` bằng `.venv-build` (KHÔNG dùng `.venv`) rồi **kiểm ngày sửa .exe + đếm file trong `_internal/app/assets/`** — bẫy 06/08: `dist/` còn bản cũ mà tưởng đã build.

### Kết luận báo cáo phải có
Một bảng **"Câu hỏi của anh Hùng → Số đo → ĐẠT/KHÔNG"**, và nếu có mục KHÔNG
ĐẠT thì **nói thẳng, đừng che, đừng gộp vào chỗ khác cho đẹp bảng**.

---


> Hồ sơ việc cho nhánh `hieu-ung-video`. **Đọc file này TRƯỚC khi làm.**
> Mọi số đo dưới đây đã đo THẬT ngày 07/08/2026 — **đừng đo lại**, dùng luôn.
> Đọc `CLAUDE.md` để biết 35 cổng chặn + quy tắc sắt của repo.

## 2 QUYẾT ĐỊNH ANH HÙNG ĐÃ CHỐT

### 1. "10 luồng cắt" = TỰ ĐIỀU CHỈNH THEO MÁY
App tự đo số nhân + có NVENC hay không rồi **tự chọn SỐ TIẾN TRÌNH ffmpeg chạy
đồng thời** (semaphore), **độc lập với "số làn" user đặt**.
- User đặt 10 làn → hàng chờ vẫn nhận 10 việc song song, nhưng **chỉ N lệnh
  ffmpeg chạy cùng lúc**, số còn lại đợi tới lượt.
- Máy anh Hùng 24 nhân + RTX 3060 → N nên ra **3-4**. Máy nhân viên yếu → **1-2**.
- Tôn trọng `ECO_MODE` ("Tiết kiệm máy") → N thấp hơn nữa.
- **Vì sao phải làm thế (đã đo):** một tiến trình ffmpeg + NVENC có **SÀN ~36
  luồng**, siết núm không xuống thấp hơn được. 10 tiến trình song song dù siết
  hết vẫn ~100-160 luồng = 4-6× số nhân. **Chỉ giảm SỐ TIẾN TRÌNH mới đạt.**
- **Mốc nghiệm thu MỚI** (thay mốc "≤1,5× số nhân" cũ vì bất khả thi):
  với 10 làn, **tổng luồng ffmpeg ≤ 2× số nhân** và **độ trễ vòng lặp UI < 30ms**.
  Không đạt thì BÁO LẠI kèm số, **đừng ship**.

### 2. Hiệu ứng: CHUYỂN CẢNH Ở CHỖ GHÉP ĐOẠN TRƯỚC
Chỉ làm **58 kiểu `xfade`**. **KHÔNG** làm hiệu ứng filter (flicker/zoom/glitch/
film…) trong lượt này — để lượt sau. Lý do anh chọn: 0 tải về, 0 rủi ro bản
quyền, **KHÔNG sửa màu nên không thể loè**, và chữa luôn chỗ hiện đang **cắt cụt
khô khốc** giữa 2 đoạn.

### 3. Kho hiệu ứng phủ: **TỰ SINH BẰNG ffmpeg**, không tải về
Anh Hùng nói "tôi cấp giấy phép cho bạn". Đã giải thích lại: giấy phép thuộc về
**người làm ra file**, anh cho phép không tạo ra quyền nếu file là của người
khác. 6 file trong `D:\hieu-ung-demo\overlays` là **AV1, tải từ đâu về, KHÔNG rõ
nguồn** → **KHÔNG ship**. Anh chạy 200-300 kênh kiếm tiền; một khiếu nại bản
quyền là dính cả cụm kênh.

**Đường đã chọn: TỰ SINH tài sản phủ bằng ffmpeg** (`lavfi`) — 100% của anh, 0
tải về, 0 rủi ro, và **không phình dung lượng** (công thức toán, không phải file).
Sinh được: mưa · tuyết · bụi bay · tia sáng / light leak · quầng sáng · bokeh ·
đốm lấp lánh. **Chưa sinh được** (cần file, để sau, chỉ khi anh Hùng có pack đã
mua): lửa cháy thật, khói thật.

**BẮT BUỘC khi sinh**: kiểm U/V trung bình ≈ **128 (lệch < 3)** ngay lúc sinh —
đó là chỗ `tim.mp4` sai (V=142,1 → tím cả khung). Sinh xong phải chạy thước đo,
file nào lệch màu thì **bỏ, sinh lại**, đừng ship.

Việc này là **GIAI ĐOẠN SAU** — vẫn làm xong chuyển cảnh (quyết định 2) trước.

## ĐÍNH CHÍNH LỚN 07/08/2026 — ffmpeg MẠNH HƠN tôi tưởng
Tôi từng viết "`gltransition` KHÔNG CÓ, cần biên dịch ffmpeg riêng, ĐỪNG hứa".
**SAI.** Kiểm `bin/ffmpeg.exe -filters` và `-version`:

| Khả năng | Trạng thái THẬT |
|---|---|
| `frei0r` (filter + `frei0r_src`) | **CÓ** — build có `--enable-frei0r`. Nhưng **plugin chưa cài**: thử `frei0r=filter_name=glow` → `Could not find module 'glow'`. Tải plugin frei0r (GPL/LGPL, mã nguồn mở, ~100+ hiệu ứng — chính thứ Kdenlive/Shotcut dùng) là chạy. |
| `xfade_opencl` | **CÓ** — nhận **kernel OpenCL tự viết** → **chuyển được 80 hiệu ứng `gl-transitions`** (MIT) sang, KHÔNG cần build lại ffmpeg |
| `xfade_vulkan` | **CÓ** |
| `libplacebo` | **CÓ** — chạy **shader GLSL tự viết** (`custom_shader_path`); mở cửa vào kho shader mã nguồn mở (mpv `.hook`) |

Build có sẵn: `--enable-gpl --enable-version3 --enable-frei0r --enable-opencl
--enable-vulkan --enable-libshaderc --enable-libplacebo --enable-libass`.

**VIỆC CẦN LÀM (giai đoạn sau chuyển cảnh):**
1. Tải **plugin frei0r** cho Windows, kiểm từng hiệu ứng bằng cổng render thật +
   đo U/V (đừng tin tên hiệu ứng, phải xem khung ra sao). Kiểm **giấy phép**:
   frei0r là GPL/LGPL — ffmpeg trong repo đã `--enable-gpl` nên dùng được, nhưng
   phải ghi rõ nguồn + giấy phép vào repo.
2. Thử `xfade_opencl` với 2-3 kernel `gl-transitions` (MIT — giấy phép thoáng)
   để **đo chi phí GPU/CPU** trước khi hứa với anh Hùng. Nếu chạy trên GPU thì
   đây là đường **KHÔNG ăn CPU** — đúng chỗ máy anh Hùng đang thiếu (CPU 96,7%,
   GPU chỉ 11,3%).
3. **ĐỪNG hứa số lượng trước khi đo.** Bẫy đã sập 2 lần: hiệu ứng "zoom nhồi"
   báo 0,03 CPU-giây (thực ra lỗi filter); `tim.mp4` lệch màu làm tím cả khung.

## ĐIỀU KIỆN ANH HÙNG CHỐT — KHÔNG ĐẠT THÌ KHÔNG SHIP
Nguyên văn 07/08/2026: *"thêm vào cho tôi, kiểm tra kỹ đó nhé, k đc lỗi, đảm bảo
chạy nhiều dây chuyền k vấn đề gì cả, xuất k sao đó nhé, đảm bảo máy k đc đơ giật
lag đó, AI phải thông minh nhất"*.

Dịch thành 5 mốc ĐO ĐƯỢC. **Thiếu một mốc là KHÔNG ship, báo lại kèm số:**

| # | Mốc | Cách đo |
|---|---|---|
| 1 | **Máy KHÔNG đơ/giật** | Trong lúc 10 làn đang xuất, đo **độ trễ vòng lặp UI** liên tục 60 giây: **trung vị < 30ms VÀ đỉnh < 150ms**. Đây là mốc anh Hùng cảm nhận được, quan trọng hơn số luồng. |
| 2 | Tổng luồng ffmpeg ở 10 làn | **≤ 2× số nhân** (24 nhân → ≤ 48). Cơ sở hiện tại: **592 luồng = 24,7×**. |
| 3 | **Xuất không sao** | 10 làn × ≥ 2 lượt: **0 clip lỗi, 0 clip 0-byte, 0 clip mất tiếng/lệch phụ đề**. Đo lệch tiếng-hình **< 80ms**. Kiểm cả **hook-first (ngược thời gian)** + **nguồn VFR**. |
| 4 | **Không lỗi hồi quy** | preset CŨ / hiệu ứng TẮT ra file **GIỐNG HỆT** `main` (md5 hoặc PSNR ≥ 50 dB). Cộng đủ cửa chặn `CLAUDE.md`. |
| 5 | **AI chọn thông minh nhất** | Trên ≥ 3 video Nhật thật: mỗi chỗ nối phải có **lý do ghi ra được** (theo `_loai_theo_khoang_nhay`), **không** lặp một kiểu ở mọi chỗ nối, và **không** đặt hiệu ứng động vào cảnh TĨNH. Ghi bảng "chỗ nối → kiểu chọn → vì sao" vào báo cáo cho anh Hùng đọc. |

**GIẤY PHÉP: anh Hùng đã duyệt** dùng nguồn mã nguồn mở — `frei0r` (GPL/LGPL) và
`gl-transitions` (MIT). Vẫn phải: ghi rõ nguồn + giấy phép vào repo, và **kiểm
từng hiệu ứng** bằng cổng render thật + đo U/V (đừng tin tên). **KHÔNG** dùng 6
file trong `D:\hieu-ung-demo\overlays` (không rõ nguồn).

**ƯU TIÊN GPU:** máy anh Hùng CPU 96,7% mà GPU chỉ 11,3%. `xfade_opencl` /
`xfade_vulkan` / `libplacebo` chạy trên **GPU** → ưu tiên nhóm này, nó dùng đúng
phần máy đang bỏ không. Nhưng **phải ĐO** chi phí thật trước khi hứa (bẫy đã sập
2 lần: hiệu ứng báo 0,03 CPU-giây thực ra lỗi filter).

## ANH HÙNG CHỐT THÊM 07/08/2026 (cuối phiên)

### A. BỎ Mixed-Cut
Nguyên văn: *"cái mixed-cut bỏ đi tôi thấy k cần thiết ở tool của tôi"*.
- Bỏ **lối vào UI** (nút "Mixed-Cut" ở `studio_page.py`) — đây là việc an toàn nhất.
- **TRƯỚC KHI XOÁ MÃ**: kiểm xem có kênh nào đang dùng không
  (`SELECT ... FROM projects/clips` có cấu hình mixed-cut / `export_stitched_clip`).
  **Nếu CÓ kênh đang dùng thì CHỈ ẩn nút, ĐỪNG xoá mã** — anh Hùng chạy 200-300
  kênh sản xuất, xoá đường xuất mà có kênh đang dùng là clip cũ "Xuất lại" sẽ nổ.
- Nhờ bỏ Mixed-Cut mà **việc "chuyển cảnh cho Mixed-Cut" trong danh sách CHƯA
  LÀM được GẠCH BỎ** — không cần làm nữa.
- Cổng test liên quan phải cập nhật, không để FAIL oan.

### B. Làm nốt các nguồn hiệu ứng còn lại
Nguyên văn: *"hiệu ứng tôi thấy bạn bảo lấy bn cái ở đâu nx mà, làm hết chưa,
làm đi"*. Anh nhắc 3 nguồn tôi đã hứa — phải làm **hết**, mỗi nguồn **đếm ra số
THẬT** rồi báo:
1. **frei0r** — đã cài 13 plugin, chốt 25 hiệu ứng. **XONG.**
2. **`xfade_opencl` + kernel `gl-transitions`** (MIT, ~80 kiểu) — **CHƯA LÀM.**
   Chạy trên **GPU** → đúng chỗ máy anh Hùng bỏ không (CPU 96,7% / GPU 11,3%).
3. **`libplacebo` + shader GLSL** — **CHƯA LÀM.** Cũng GPU.
Cả 2 nhóm GPU phải: đo chi phí thật · fallback ÊM khi máy không có OpenCL/Vulkan
(máy nhân viên) · ghi nguồn + giấy phép vào `app/assets/hieu_ung/NGUON_GIAY_PHEP.md`.

**Bảng mẫu `D:\hieu-ung-demo-v3\00_BANG_MAU_TAT_CA_HIEU_UNG.mp4` là ưu tiên số 1** —
anh Hùng đã hỏi 5 lần, và anh không xem được số đo, chỉ xem được clip.

## LỖI ANH HÙNG BÁO Ở BẢNG MẪU v3 — SỬA NGAY (07/08/2026)
Anh gửi ảnh `00_BANG_MAU_TAT_CA_HIEU_UNG.mp4` đang phát, nguyên văn: *"nó bị
phóng to à, với tuỳ cái, cái nào cần thì hiện thôi hiểu k, với AI chọn sao phù
hợp nhé"*.

### Lỗi 1 — CHỮ NHÃN BỊ CẮT MẤT HAI ĐẦU
Ảnh cho thấy nhãn `...ỐC – KHÔNG HIỆU ỨNG (ô để so sá...` — **mất chữ đầu và
chữ cuối**. Nhãn dài hơn bề rộng khung 1080 nên tràn ra ngoài.
**SỬA**: `drawtext` phải TỰ CO cỡ chữ theo độ dài nhãn, hoặc xuống 2 dòng, hoặc
cắt ngắn tên. **Cấm để tràn.** Cách kiểm: render khung có nhãn rồi **đếm pixel
chữ ở cột 0-8 và cột (w-8)-w** — có chữ sát mép = FAIL. Đây đúng bài học "nút
cụt chữ Hav/Nha" (cổng 31): **số px cứng KHÔNG BAO GIỜ đúng**, phải đo
`fontMetrics`/`textfile` lúc chạy.

### Lỗi 2 — HÌNH BỊ PHÓNG TO
Nội dung trong khung bị blow-up, mất khung cảnh. Nghi: dựng bảng mẫu bằng
`scale`+`crop` kiểu `force_original_aspect_ratio=increase` (cắt để lấp đầy) trên
nguồn 16:9 → phóng to cắt mất hai bên. **SỬA**: bảng mẫu phải cho thấy **TOÀN
khung** (`decrease` + `pad`), vì mục đích là để anh Hùng ĐÁNH GIÁ hiệu ứng, không
phải clip thành phẩm. Ghi rõ trong ghi chú là "khung xem, không phải khung xuất".

### Lỗi 3 (yêu cầu, không phải bug) — CHỈ HIỆN KHI CẦN
*"tuỳ cái, cái nào cần thì hiện thôi"* — khẳng định lại **4 luật chống loè** đã
chốt, và phải **CHỨNG MINH bằng số** trong báo cáo:
- Hiệu ứng chỉ **0,3–0,8s** ở ĐIỂM NHẤN, tuyệt đối **KHÔNG phủ toàn clip**
- Mỗi clip **tối đa 2-3 điểm**
- **Cảnh TĨNH → KHÔNG đụng gì** (đo `chuyen_dong` thấp thì bỏ qua)
- Đoạn không có cao trào (`nang_luong` phẳng) → **KHÔNG thêm gì**
Trong `_ghi_chu.txt` phải ghi rõ: clip dài bao nhiêu giây, **tổng số giây CÓ hiệu
ứng** là bao nhiêu, tỉ lệ %. Nếu tỉ lệ > 10% thời lượng clip là **SAI thiết kế**,
phải giảm.

### Lỗi 3.5 — TÔI TỰ TÌM RA khi soi lại bản vừa xuất (08/08/2026): `%` NUỐT CẢ DÒNG
Sửa xong 2 lỗi trên, tôi trích khung bản v3 vừa render ra XEM lại thì thấy **cả
25 ô mất hẳn dòng nhãn thứ 2** (`14/25 · CapCut: Film Radiance · đổi 100% khung
hình`), chỉ ô GỐC (nhãn `0/25`, không có `%`) là còn.

**Nguyên nhân**: `drawtext` mặc định chạy `expansion=normal`, coi `%` là mở đầu
hàm `%{...}`; gặp `%` trơ nó **bỏ SẠCH chuỗi và VẪN trả rc=0**. Đo thật cùng một
chuỗi: mặc định **0 px** vs `expansion=none` **11.744 px**; riêng `'100%'` 0 px
vs 1.512 px. **Chữa: `expansion=none`.**

**Cổng cũ PASS OAN** vì nó chỉ đếm pixel TỔNG của cả khối nhãn — dòng 1 còn nên
tổng > 0 nên báo "26/26 ĐẠT". Nay `_canh_nhan` đếm pixel **TỪNG DÒNG**, dòng nào
0 px là FAIL. Đây đúng loại lỗi "app vẫn chạy, test vẫn xanh, chỉ số đo tố giác".

**App THẬT không dính**: `ffmpeg_utils._esc_drawtext` đã escape `%` -> `\%` từ
trước; hiệu ứng `dem_nguoc` chỉ vẽ chữ số. Lỗi khu trú trong script bảng mẫu.

### Lỗi 4 (yêu cầu) — AI CHỌN PHẢI PHÙ HỢP
*"AI chọn sao phù hợp nhé"*. Bảng "giây thứ mấy → hiệu ứng gì → VÌ SAO" trong
`_ghi_chu.txt` là bằng chứng duy nhất anh Hùng đọc được. Mỗi dòng phải nêu **CĂN
CỨ SỐ**, ví dụ: `giây 41,2 · zoom nhồi · vì RMS đạt đỉnh 0,82 (nền 0,31) +
chuyển động 7,4/10`. **Không được ghi lý do chung chung** kiểu "cảnh hay".

## SỐ ĐO CƠ SỞ (máy rảnh 10-14%)
Xuất thật · video Nhật thật · 2 đoạn hook-first · nền mờ · đốt .ass · 1080×1920 ·
h264_nvenc · 24 nhân. Nguồn: `「実録」不倫ハシゴ中に現場突撃！不倫相手全員集合！.mp4`

| lượt song song | wall (trung vị) | CPU-giây | đỉnh luồng | quá tải/24 nhân | RSS đỉnh |
|---|---|---|---|---|---|
| 1 (lặp 3) | 7,04 s | 22,33 | 61 | 2,54× | 0,97–1,14 GB |
| 10 (lặp 2) | 49,07 s | 263,85 | **592** | **24,7×** | 5,0–5,9 GB |

10 lượt tốn 263,85 CPU-giây; song song hoàn hảo chỉ cần 10 × 22,33 = 223,3
→ **+18% CPU đốt vô ích vì giành luồng**.

## CHỖ HỞ: luồng GIẢI MÃ chưa ai bịt
- `_global_enc_opts()` (~dòng 495 `app/core/ffmpeg_utils.py`): chỉ có
  `-filter_complex_threads`, **thiếu `-filter_threads`**.
- `_enc_args()` (~dòng 477): chỉ đặt `-threads` cho **libx264**; nhánh **nvenc
  không có núm nào**.
- **KHÔNG chỗ nào đặt `-threads` TRƯỚC `-i`** → giải mã mặc định `-threads 0`
  ≈ **17 luồng/lệnh**, dư 12-14 luồng mỗi lệnh.
- `_build_seg` (pha 1, ~dòng 1325): nhánh nvenc trắng trơn.

### Bảng soi từng núm ở PHA 2 (concat + blur + overlay + đốt .ass + nvenc)
| ca | wall | CPU-giây | đỉnh luồng |
|---|---|---|---|
| bỏ hết giới hạn (đối chứng) | 2,51 | 11,53 | 106 |
| **HIỆN TẠI** (`fct=7`) | 2,59 | 8,97 | **70** |
| `fct=7` + giải mã 4 | 2,57 | 10,03 | 58 |
| `fct=4` + giải mã 4 | 2,53 | 8,55 | 47 |
| **`fct=2` + giải mã 2** | 2,68 | **7,44** | **36** |
| `fct=7` + giải mã 4 + nvenc `-threads 4` | 2,60 | 9,70 | 46 |

**Wall-time cả 8 ca chênh < 7%** → nút cổ chai là **NVENC/GPU**, siết luồng
**KHÔNG làm chậm** (ở 1 lượt, máy có NVENC).

## ĐÍNH CHÍNH QUAN TRỌNG
Kết luận cũ *"chặn luồng làm chậm 3,4 lần (61,2s → 208,3s)"* là **NHIỄU, KHÔNG
THẬT**. Mốc 61,2s đo khi app anh Hùng chạy 96,7% CPU; đo lại **đúng cấu hình đó
trên máy rảnh = 7,04s** (phồng ~9 lần). Nên **cứ dùng núm luồng**, nhưng vẫn phải
đo lại sau khi sửa.

## CÒN THIẾU 1 SỐ ĐO QUYẾT ĐỊNH — LÀM TRƯỚC KHI SỬA
Pha 1 (`_build_seg`) là bước **duy nhất không có filter** → **decode-bound** →
là chỗ duy nhất siết luồng giải mã **có thể** làm chậm thật, và đúng là chỗ lần
trước thất bại. Script `_do_pha1_tach_doan.py` (9 ca, nvenc + libx264, lặp 3 lấy
trung vị) **đã viết sẵn, chưa chạy được** vì máy bận. **CHẠY NÓ TRƯỚC.**

## ENCODER THỰC — đã khoanh đúng nguyên nhân, ĐỪNG sửa regex
Kiểm bằng log ffmpeg thật (build `N-121186-g03c054d43c-20250923`):

| dạng lệnh | dòng mapping thật | regex `->\s*h264\s*\(` | regex `encoder:\s*Lavc` |
|---|---|---|---|
| pha 1 (không filter, .mkv) | `Stream #0:0 -> #0:0 (h264 (native) -> h264 (h264_nvenc))` | KHỚP | KHỚP |
| pha 2 (`-filter_complex`, .mp4) | `setsar:default -> Stream #0:0 (h264_nvenc)` | **không khớp** | KHỚP |

Cả 2 dạng đều ra `h264_nvenc` → **chẩn đoán "regex chưa khớp" là SAI**. Nguyên
nhân cột `?` nằm ở 2 chỗ khác:
1. `_do_pha_xuat.py:81` và `_do_uu_tien.py:142` đổ **stderr vào
   `subprocess.DEVNULL`** → không bao giờ có log để đọc. Cột enc do 2 cửa đó
   nuôi thì `?` là **tất yếu về cấu trúc**, sửa regex bao nhiêu cũng vô ích.
2. Lệnh **thất bại** (rc≠0) thoát trước khi in khối `Stream mapping` → không có
   encoder → `?` là đúng.

### BẪY PHẢI GHI VÀO CODE KẺO SẬP
File `.mkv` mezzanine mang tag `ENCODER : Lavc62.15.100 h264_nvenc` **CHỮ HOA ở
phần INPUT** (Matroska hoa, MP4 thường). Ai "chữa" bằng `re.IGNORECASE` sẽ đọc
tag của **INPUT** và **luôn** báo `h264_nvenc` → **PASS oan, che đúng cái
tụt-nvenc-về-CPU đang đi tìm**.

Tin tốt: đường xuất của app **không** chặn log (`-loglevel error` chỉ có ở
`ffmpeg_utils.py:344` `_nvenc_works()` và `:1228` trích khung) → đọc encoder thật
trên đường xuất là làm được. App cũng có sẵn nhánh tự lùi encoder ở
`ffmpeg_utils.py:1050–1066` (`_looks_nvenc_failure`) → nvenc rớt về CPU là
chuyện **có thật**, không phải lo hão.

## CHỌN KIỂU CHUYỂN CẢNH — KHÔNG RANDOM
Dùng lại **đúng khuôn `m1_highlight._loai_theo_khoang_nhay`** (thuần, đang chạy
tốt cho TIẾNG ĐỘNG): suy theo **NỘI DUNG chỗ nối** — nhảy NGƯỢC thời gian
(hook-first) → impact; gần liền mạch ≤1,2s → pop; đoạn kế <2,5s (câu chốt) →
impact; còn lại → transition; reveal CHỈ khi ≥2 điểm nối.

Trước khi có hàm đó, luật cũ làm **MỌI Part đều một tiếng "ding"** — đúng cái
anh Hùng sợ: *"thêm ngẫu nhiên k hợp cảnh k hợp logic gì cả"*.

Ánh xạ sang xfade theo cùng nguyên tắc (tự thẩm định lại):
- chỗ nối **nhảy ngược thời gian** → dứt khoát: `fadeblack` / `wipeleft`, 0,25s
- chỗ nối **gần liền mạch** ≤1,2s → mềm: `dissolve` / `smoothleft`, 0,3s
- **câu chốt** (đoạn kế rất ngắn) → `fadewhite` / `circleclose`, 0,35s
- còn lại → `fade`, 0,3s

Cùng một video **KHÔNG lặp một kiểu ở mọi chỗ nối** (đa dạng nhưng có lý do).
Thời lượng 0,25–0,4s, mặc định 0,3s.

## RỦI RO LỚN NHẤT CỦA VIỆC NÀY
Đường ghép đoạn là **2 PHA**: `_extract_segments_to_temp` tách từng đoạn ra
`.mkv` (mezzanine, CFR, PCM) rồi **concat demuxer** nối theo THỨ TỰ DANH SÁCH.
Đọc kỹ docstring hàm đó — có **2 lỗi thật đã học**: (a) 1 lệnh trim+concat làm
RAM phình **19,6 GB**; (b) 1 nhánh `select` làm **hình một đằng tiếng một đằng**
vì hook-first xếp đoạn NGƯỢC thời gian.

`xfade` cần 2 luồng vào và **ĂN BỚT thời lượng** ở chỗ nối → phải:
- KHÔNG phá thứ tự hook-first
- KHÔNG phá đồng bộ tiếng-hình (cân nhắc `acrossfade` tương ứng cho tiếng)
- **Tính lại tổng thời lượng clip** — xfade làm clip NGẮN đi mỗi chỗ nối; không
  tính lại thì **phụ đề `.ass` và tiếng động sẽ LỆCH**. Phải test riêng.
- Giữ RAM phẳng (đừng quay lại kiểu 1-lệnh-tất-cả)

## NGHIỆM THU
1. **Cổng render THẬT**: xuất clip 2 đoạn + 3 đoạn có xfade, trích khung ở đúng
   mốc chỗ nối, **đếm pixel** để chứng minh chuyển cảnh CÓ xảy ra (không phải cắt
   khô). Kiểu nào lỗi filter phải **FAIL**, không im lặng.
2. **Cổng ĐỒNG BỘ**: đo lệch tiếng-hình và lệch phụ đề sau khi có xfade — phải
   **< 80ms**. Test cả **thứ tự hook-first (ngược thời gian)** và **nguồn VFR**.
3. **Cổng TẢI NẶNG**: 10 làn, đo tổng luồng ffmpeg + CPU-giây + độ trễ UI.
   Mốc: **≤ 2× số nhân**, UI **< 30ms**.
4. **BẤT BIẾN SỐNG CÒN**: preset CŨ / chuyển cảnh TẮT phải ra file **GIỐNG HỆT**
   `main`. Kiểm: xuất 1 clip ở `main`, rồi ở nhánh này với chuyển cảnh TẮT, so
   md5 hoặc **PSNR ≥ 50 dB**.
5. **Máy nhân viên**: kiểm bằng `requirements-build.txt` (venv khách). **KHÔNG
   thêm thư viện Python mới.**
6. **Cửa chặn `CLAUDE.md`**: `pyflakes app config.py main.py` không được còn
   "undefined name"; `_test_app_smoke.py`; `_test_pipe_dialogs.py`; cộng cổng 24
   `_test_chon_doan`, 25 `_test_tieng_va_mau`, 28 `_test_lien_thong`, 34
   `_test_moc_ngoai_phim`, 35 `_test_va_lo_sub`.
7. **UI**: thêm chọn chuyển cảnh vào Chỉnh mẫu (`app/ui/editor.py`) — có mục
   **TẮT**, mặc định BẬT ở mức nhẹ. Nhãn **không dùng emoji dễ thiếu font** (máy
   anh Hùng từng ra Ô ĐEN với 📋/✕).

## QUY TẮC SẮT
- Test bằng **THÀNH PHẦN THẬT**: ffmpeg thật, video Nhật thật trong
  `C:\Users\Admin\Downloads\thùng rác` (tên có ký tự tiếng Nhật). Groq thật nếu
  cần (key ở `%LOCALAPPDATA%\BQHungVideo\.env`, truyền qua **BIẾN MÔI TRƯỜNG**,
  **KHÔNG ghi ra file**).
- **Đo bằng CPU-GIÂY** (`psutil.Process.cpu_times()`). Kiểm máy rảnh
  (`cpu_percent < 20%` trong 5 giây, không có `BQHungVideo.exe`/`ffmpeg.exe` lạ)
  TRƯỚC khi đo; máy bận thì **DỪNG và báo**. Lặp ≥ 3 lần lấy trung vị.
- `git diff | grep gsk_` trước mỗi commit — phải ra **0**.
- Test **KHÔNG ghi vào QSettings thật**, **không mở Explorer/player** — mọi test
  dựng UI phải `import _test_guard`. Sandbox: `BQ_DB_PATH` + `BQ_DATA_DIR` sang
  thư mục tạm.
- **KHÔNG bump version / tag / push / merge vào `main`.** Commit vào nhánh
  `hieu-ung-video` thì được.

## THỨ TỰ LÀM (anh Hùng: "cứ làm chậm nhưng đảm bảo")
1. Chạy `_do_pha1_tach_doan.py` → số đo pha 1.
2. Bịt chỗ đọc **encoder THỰC** (xem mục trên — sửa `DEVNULL`, **đừng** sửa
   regex, **đừng** dùng `IGNORECASE`) → xác nhận nvenc không rớt về CPU.
3. Sửa quá tải: núm luồng (giải mã + `filter_threads`) **+ semaphore
   tự-điều-chỉnh-theo-máy** cho số ffmpeg đồng thời. Đo lại 1 lượt và 10 lượt.
4. Làm chuyển cảnh xfade + chọn theo chỗ nối. Xuất **demo ra
   `D:\hieu-ung-demo-v2\`** (≥ 3 clip: 2 đoạn, 3 đoạn, hook-first) để anh Hùng
   xem TRƯỚC khi coi là xong.
5. Cổng test + cửa chặn.
6. **Báo cáo** (tiếng Việt): bảng số đo trước/sau, kết quả 10 làn, danh sách kiểu
   chuyển cảnh + luật chọn, và **nói rõ cái gì CHƯA làm được**. Đừng che.

## LƯU Ý VỀ CÁC FILE ĐO ĐANG CÓ TRONG THƯ MỤC
Nhiều file `_do_*.py` do các lượt trước để lại, **untracked**, và **không tách
bạch**: `_do_quet_luong.py` `import` từ `_do_pha_xuat`, `_do_uu_tien`,
`_do_vaxuat`. Trước khi xoá bất cứ file nào, kiểm `import` chéo. File cần dùng:
`_do_pha1_tach_doan.py` (soi pha 1), `_do_nut_luong.py` (soi núm pha 2),
`_do_luong_ffmpeg.py` (máy đo chính: `--luot 1 --lap 3` / `--luot 10 --lap 2`).

---
---
# ĐÃ LÀM XONG — lượt 07/08/2026 (tối), nhánh `hieu-ung-video`
Commit: `46b5f6c` (núm luồng + chuyển cảnh) · `adf43eb` (cửa chờ + cổng 36).
**Bước 1→5 của "THỨ TỰ LÀM" đã xong.** Dưới đây là những gì phiên sau CẦN BIẾT.

## ⚠ 2 BÀI HỌC VỀ CÁCH LÀM — ĐỌC TRƯỚC KHI SỬA GÌ

**1. CÓ SESSION KHÁC ĐANG SỬA CÙNG FILE — ĐÃ MẤT VIỆC 1 LẦN.**
Đang làm thì `app/core/ffmpeg_utils.py` bị ghi đè: **cả khối cửa chờ ffmpeg biến
mất khỏi `_run`**, và `_uu_tien_co()` của lượt khác cũng bị revert (dấu vết:
`_va_uu_tien_hwdec.patch` 21:00, `_DO_UU_TIEN_VA_GPU.md` 21:01). `VIEC_HIEU_UNG.md`
cũng bị sửa song song (+70 dòng về frei0r/GPU). App vẫn chạy, pyflakes vẫn xanh,
**chỉ SỐ ĐO tố giác** (10 lượt vẫn ra 397 luồng thay vì 44). Vì vậy:
- **COMMIT SỚM, COMMIT NHIỀU** vào nhánh — mất là `git checkout` lấy lại.
- Sau MỖI lần sửa khối lớn, `grep` lại tên hàm vừa thêm để chắc nó còn đó.
- Cổng 36 đã có ca **QUÉT TĨNH**: `_run` phải chứa `_xin_cho_ffmpeg`. Thiếu là
  FAIL — đó là cái phanh cho đúng lỗi này.

**2. Máy "rảnh" có thể bận lại giữa lượt đo.** Lượt đo đầu ra 6,2 → 28,1 → 77,6s
(phồng 12 lần) vì 6 ffmpeg của python KHÁC chen vào; đo lại trên máy sạch:
6,17 / 6,61 / 6,13s. **Dãy số phồng dần theo lần lặp = có kẻ khác trên máy, KHÔNG
phải code chậm.** Luôn đọc lại dòng `[máy]` và cột "N tiến trình".

## SỐ ĐO PHA 1 (`_build_seg`) — ĐÃ CHẠY, ĐỪNG CHẠY LẠI
Nguồn Nhật thật, lặp 3 lấy trung vị, máy 24 nhân rảnh 6,6%. Cột `enc THỰC` đọc
từ log: **cả 9 ca đều h264_nvenc / libx264 đúng như đặt — nvenc KHÔNG rớt về CPU.**

| ca | wall | CPU-giây | đỉnh luồng | so wall |
|---|---|---|---|---|
| nvenc, không giới hạn | 0,76 | 1,89 | 61 | — |
| nvenc + giải mã 4 | 0,75 | 1,67 | 49 | **0,99x** |
| nvenc + giải mã 2 | 0,78 | 1,50 | 47 | 1,03x |
| nvenc + giải mã 1 | 0,99 | 1,17 | 45 | **1,30x** |
| nvenc + `-threads 4` SAU `-i` | 0,76 | 1,92 | **37** | 1,00x |
| libx264 hiện tại (`-threads 7`) | 0,78 | 4,97 | 48 | — |
| libx264 giải mã+enc 4 | 0,84 | 4,34 | 27 | 1,08x |
| libx264 giải mã+enc 2 | 1,16 | 3,23 | 19 | 1,49x |
| libx264 giải mã+enc 1 | 1,99 | 2,64 | 12 | **2,55x** |

**Chốt: giải mã = 4 (ECO = 2). ĐỪNG hạ về 1** dù cột luồng đẹp hơn.

## SỐ ĐO TRƯỚC/SAU (24 nhân, RTX 3060, máy rảnh)
1 lượt xuất (2 đoạn hook-first, nền mờ, đốt .ass, 1080×1920):

| | wall | CPU-giây | đỉnh luồng | quá tải | RSS |
|---|---|---|---|---|---|
| TRƯỚC (`main`) | 7,04 | 22,33 | 61 | 2,54x | 0,97–1,14 GB |
| SAU (ECO mặc định) | 6,17 | 20,17 | 40 | 1,67x | 0,69–0,72 GB |
| SAU (ECO=0) | 5,35 | 19,91 | 43 | 1,79x | 0,68–0,74 GB |

10 lượt song song, ECO=0, lặp 2 lấy trung vị — **quét từng mức cửa chờ**:

| cửa chờ N | wall | CPU-giây | đỉnh luồng | quá tải | tiến trình |
|---|---|---|---|---|---|
| TRƯỚC (`main`) | 49,07 | 263,85 | 592 | 24,70x | 10 |
| chỉ núm luồng, CHƯA có cửa chờ | 40,44 | 251,65 | 397 | 16,54x | 10 |
| **N=1 (tự đo ra trên máy này)** | 58,25 | **209,48** | **44** | **1,83x** ✅ | 1 |
| N=2 | 45,54 | 237,49 | 86,5 | 3,60x | 2 |
| N=3 | **37,71** | 226,20 | 128,5 | 5,36x | 3 |
| N=4 | 37,85 | 253,67 | 169,5 | 7,06x | 4 |

**3 điều rút ra:**
1. Chỉ **N=1** đạt mốc ≤ 2× số nhân. Kỳ vọng "N nên ra 3-4" là **KHÔNG đạt được**
   cùng lúc với mốc đó — sàn ~40 luồng/tiến trình quyết định như vậy.
2. **N=4 KHÔNG nhanh hơn N=3** (37,85 vs 37,71) mà +32% luồng, +12% CPU-giây →
   nút cổ chai là **NVENC/GPU**. Trần 4 trong code là đủ, đừng nới.
3. N=1 đổi **+19% wall** lấy **−21% CPU-giây** và **−93% luồng**. Muốn thông
   lượng thì `BQ_FFMPEG_SLOTS=3` (−23% wall so `main`, nhưng 5,36× nhân).

**CẢNH BÁO VỀ CỘT RSS của `_do_luong_ffmpeg.py`:** nó **CỘNG RSS theo pid** trong
cả lượt (`self._rss[pid] = ...` giữ cả pid đã chết) → N=1 sinh 30 pid tuần tự nên
"RSS 7,63 GB" là **TỔNG CỘNG DỒN, không phải RSS đồng thời**. RSS đồng thời thật
= ~0,7 GB (đo ở lượt 1-luồng). **Đừng so cột RSS giữa các mức N.**

## CHUYỂN CẢNH — CHỐT THIẾT KẾ (chỗ dễ sập nhất, đọc kỹ)
`xfade` **ĂN BỚT `d` giây** mỗi chỗ nối (`out = dài(A)+dài(B)-d`). Phụ đề `.ass`
và mốc tiếng động dựng theo timeline "nối THẲNG" → không bù là **lệch (n−1)×d**
(clip 4 đoạn = 0,9 s). Đúng loại lỗi v1.87 "hình một đằng tiếng một đằng".

**CÁCH CHỮA ĐÃ CHỌN (`_bu_xfade`): LẤY THÊM đúng `d` giây phim ở CUỐI đoạn trước,
rồi đặt `offset = độ_dài_GỐC(A)`.** Khi đó khung của B rơi ĐÚNG mốc cũ, tổng =
a+b → **timeline BẤT BIẾN, không phải sửa `.ass` một dòng nào**. Đo thật: lệch độ
dài **0 ms**, lệch hình **−33 ms** (= 1 khung, đúng độ phân giải phép đo), lệch
tiếng **0,0 ms**, phụ đề ở cùng mốc đếm được 75.006 px (bật) vs 75.045 px (tắt).
- Hết phim thì thu ngắn `d`; dưới 0,08 s thì chỗ nối đó **cắt thẳng** (thà cụt 1
  chỗ hơn lệch cả clip). **KHÔNG lùi đầu đoạn B để bù** — đó là dịch nội dung B.

**KIẾN TRÚC: thêm PHA 1.5, KHÔNG sửa graph pha 2.** Pha 1 tách n mezzanine như cũ
→ pha 1.5 nối chúng thành **1 mezzanine duy nhất** bằng `xfade` + `acrossfade` →
file danh sách concat chỉ còn 1 dòng nên **pha 2 (nền mờ + overlay + đốt .ass +
fade + tiếng động) không phải sửa gì**, và chuyển cảnh TẮT thì đường cũ y nguyên.
Giá phải trả: **+2,5–2,9 s/clip** cho 1 lượt encode mezzanine nữa. Chấp nhận vì
gộp xfade vào graph pha 2 phải đánh số lại toàn bộ input (nền màu/overlay/nhạc/
dub) trong hàm 400 dòng đang gánh sản xuất 200-300 kênh.

**LỖI THẬT cổng 36 bắt được ngay lượt đầu:** `noi = temps` là **tham chiếu**, nên
`temps.append(gop)` sửa luôn `noi` → file GỘP (chưa tồn tại) bị đưa vào làm INPUT
thứ n+1 → `No such file or directory`. Phải `noi = list(temps)`.

**58 kiểu xfade đã đối chiếu với `bin/ffmpeg.exe`**: `transition` nhận 0..57
(cộng `custom=-1` cần biểu thức riêng nên bỏ) → khớp đúng 58, không thiếu kiểu
nào. Cổng 36 có ca so danh sách này với `ffmpeg -h filter=xfade`.

**4 mức trong Chỉnh mẫu** (`app/ui/editor.py`, combo `xfade_cb`, nhãn KHÔNG emoji):
`tat` (= đường cũ y nguyên) · **`nhe` = MẶC ĐỊNH** · `vua` · `manh`.
Khoá mẫu: `chuyen_canh`. Mẫu CŨ chưa có khoá → app dùng `nhe`, tức **200-300 kênh
đang chạy sẽ CÓ chuyển cảnh ngay** — nếu anh Hùng không muốn thì đổi mặc định về
`tat` ở 3 chỗ: `editor.py` (`setCurrentIndex`), `studio_page.py`, `m1_highlight.py`.

**Luật chọn kiểu — TIỀN ĐỊNH, KHÔNG bốc thăm** (`chon_chuyen_canh`, khuôn
`_loai_theo_khoang_nhay`); chọn trong 2 kiểu theo `i % 2` nên cùng 1 video không
lặp một kiểu ở mọi chỗ nối:

| chỗ nối | nhận biết | nhẹ | vừa | mạnh |
|---|---|---|---|---|
| `nguoc` nhảy NGƯỢC thời gian (hook-first) | `bat − het < −0,05` | fadeblack/fade 0,25s | fadeblack/wipeleft 0,25s | slideleft/wipeleft 0,30s |
| `lien` gần liền mạch | nhảy ≤ 1,2s | dissolve/fade 0,30s | dissolve/smoothleft 0,30s | smoothleft/smoothright 0,35s |
| `chot` câu chốt | đoạn kế < 2,5s | fadewhite/fade 0,30s | fadewhite/circleclose 0,35s | circleclose/squeezev 0,40s |
| `xa` đổi bối cảnh | còn lại | fade/dissolve 0,25s | fade/smoothright 0,30s | slideup/horzclose 0,35s |

## CỔNG 36 `_test_chuyen_canh.py` — 53 ca, 0 FAIL
Ca đáng chú ý + số đo: chuyển cảnh CÓ xảy ra (82,8% / 57,7% pixel khác bản cắt
thẳng) · `fadeblack` làm tối thật (18,5 vs 81,8) · độ dài lệch 0 ms · lệch hình
−33 ms · lệch tiếng 0,0 ms · phụ đề không lệch · **nguồn VFR** (dựng bằng
`select` + `-fps_mode passthrough`) đều đạt · kiểu lạ **ném lỗi** và không để lại
file · **BẤT BIẾN: chuyển cảnh TẮT so với `main` ra PSNR 99 dB ở cả 5 mốc** (nạp
`git show main:app/core/ffmpeg_utils.py` thành module riêng rồi xuất song song).

**2 BẪY ĐO ĐÃ SẬP khi viết cổng này, đừng lặp:**
- **Mốc cắt phải ở CẢNH SÁNG.** Nguồn Nhật ở giây 20 sáng TB chỉ **3,3/255** (gần
  đen) → ca "đếm pixel ở chỗ nối" ra 0,69% và **FAIL OAN** vì cả 2 bản đều đen.
  Đổi sang mốc 100/200/300s (71–90/255) thì ra 57–83%.
- **Ngưỡng đếm pixel phải THEO TỈ LỆ.** Khung phim đã có vùng gần trắng nên khung
  KHÔNG có chữ vẫn đếm 4.634 px → ngưỡng cứng 1.500 px FAIL OAN. Đúng: chữ phải
  làm số px trắng **gấp > 4 lần**, và bản BẬT phải khớp bản TẮT ở CÙNG mốc.

## RÒ RÁC ĐĨA — TÌM RA VÀ ĐÃ SỬA (có từ bản `main`, không phải lỗi mới)
Xuất LỖI GIỮA PHA 1 thì mảnh `.mkv` đã tách **nằm lại vĩnh viễn**: caller bọc
`try/except` rồi gọi `_cleanup_paths(_seg_temps)`, nhưng khi
`_extract_segments_to_temp` NÉM LỖI thì phép gán `_seg_list, _seg_temps = ...`
**chưa chạy** nên `_seg_temps` vẫn RỖNG → dọn 0 file. Chuyển cảnh làm nó nặng
thêm vì pha 1.5 là chỗ ném lỗi MỚI.
- **Đo thật:** sau các lượt đo/test hôm nay `%TEMP%` còn **48 file `_seg_*` /
  0,53 GB**. Đúng loại rác **1,71 GB** phải dọn tay hôm 31/07 khi ổ C đầy 100%.
- **Sửa:** `_extract_segments_to_temp(..., temps_out=<list của caller>)` —
  append từng mảnh vào list của caller NGAY khi tạo, nên lỗi ở bất kỳ đoạn nào
  vẫn dọn được hết. Cổng 36 có ca canh: xuất LỖI xong `%TEMP%` phải sạch.

## NÚM MỚI CHO NGƯỜI DÙNG / GỠ RỐI
- `BQ_FFMPEG_SLOTS=<N>` — ép số lệnh ffmpeg chạy cùng lúc (1..16). Dùng để đo và
  để chữa máy user mà không phải phát hành bản mới.
- `so_ffmpeg_song_song()` / `dang_chay_ffmpeg()` / `decode_threads()` — đọc được
  từ test.

## CÒN THIẾU (chưa làm trong lượt này)
1. **Cửa chặn `CLAUDE.md`**: xem mục cuối báo cáo — chạy tới đâu ghi tới đó.
2. **Chuyển cảnh chưa vào đường `export_stitched_clip`** (Mixed-Cut KHÔNG có mẫu)
   và `export_vertical_clip` — chỉ `export_canvas_clip` có. Mixed-Cut ghép bằng
   filter `concat` trong 1 lệnh, muốn xfade phải làm riêng.
3. **Hiệu ứng filter (frei0r / `xfade_opencl` / `libplacebo`)** — đúng như đã
   chốt, để lượt sau. Mục "ƯU TIÊN GPU" ở trên còn nguyên giá trị.
4. **Chưa đo trên máy nhân viên yếu thật** (chỉ mô phỏng bằng công thức + ca test
   ECO_MODE). `requirements-build.txt` KHÔNG thêm thư viện nào — cổng 36 chỉ dùng
   `numpy`/`cv2` đã có sẵn.

---
---
# LƯỢT 08/08/2026 — sửa bảng mẫu · 2 nguồn GPU · RÀ SOÁT LỖI
Commit: `589b57f` (bảng mẫu) · `9033421` (GPU) · `34c15c9` (cổng 37) · lượt này.

## 1. BẢNG MẪU v3 — 3 lỗi đã sửa (2 anh Hùng báo + 1 tôi tự tìm)
Xem mục "LỖI ANH HÙNG BÁO Ở BẢNG MẪU v3" ở trên. Lỗi thứ 3 (`%` nuốt cả dòng)
đáng nhớ nhất: **cổng kiểm đếm pixel TỔNG nên PASS OAN 26/26 trong khi 25 ô mất
hẳn dòng nhãn 2.** Nay đếm pixel TỪNG DÒNG.

## 2. NHÓM GPU — 21 chuyển cảnh + 6 shader, và 2 bẫy suýt ship
Chi tiết ở docstring `app/core/hieu_ung_gpu.py` và `CLAUDE.md`. Tóm tắt số:
`xfade_opencl` **21/21 ĐẠT** · `libplacebo` **6/6 ĐẠT** · **CPU-giây 1,03× so
CPU** (GPU KHÔNG rẻ hơn ở quy mô 0,3-0,5s; giá trị nằm ở 21 kiểu MỚI).
Tai nạn đáng nhớ: chữa PTS rác bằng `fps=` làm ffmpeg **sinh khung vô tận, 19,1
GB RSS + 364 CPU-giây trong 9 phút**, phải giết tay.

## 3. LỖI THẬT ĐANG CHẠY TRONG SẢN XUẤT — ĐÃ SỬA
**`_bu_xfade` không kẹp `d` theo độ dài ĐOẠN KẾ.** `xfade` (hình) và
`acrossfade` (tiếng) xử lý ca "đoạn B ngắn hơn `d`" KHÁC NHAU:

| B dài | d | hình ra | tiếng ra | lệch |
|---|---|---|---|---|
| 0,20 | 0,40 | 2,200 | 2,400 | **200 ms** |
| 0,20 | 0,30 | 2,200 | 2,300 | **100 ms** |
| 0,30 | 0,40 | 2,300 | 2,400 | **100 ms** |
| 0,30 | 0,30 | 2,300 | 2,300 | 0 ms |

Mốc cho phép 80 ms. App **TỰ ĐẨY MÌNH VÀO**: `_loai_cho_noi` gọi chỗ nối là
`'chot'` đúng khi đoạn kế < 2,5s, mà `'chot'` có `d` DÀI NHẤT (vua 0,35 · manh
0,40); `_cat_theo_do_dai_that` cho đoạn ngắn tới 0,30s (Part cuối kẹp vào mép
phim). Mức mặc định `'nhe'` vừa đúng 0,30 nên thoát — **`'vua'`/`'manh'` thì
KHÔNG**. Sửa: `d = min(d, độ_dài_đoạn_kế)`. Đo lại: lệch **23 ms**. Cổng 37 ca 6.

**Rò tiến trình ffmpeg mồ côi:** `do_nhip` và `_thu_module` trong `hieu_ung.py`
gọi thẳng `subprocess.run`, KHÔNG qua `register_proc` -> `terminate_all_children()`
lúc đóng app không giết nổi. `do_nhip` giải mã CẢ clip (tới 2 lệnh khi video
không tiếng), `dung_duoc()` thử 11 module frei0r. Nay cả 2 đi qua `_chay_ffmpeg`
(vào sổ tiến trình). **Cố ý KHÔNG qua cửa chờ** — lệnh ĐO mà xin chỗ sẽ tự khoá
lẫn với lệnh xuất đang giữ chỗ.

## 4. HIỆU ỨNG ĐIỂM NHẤN CHƯA NỐI VÀO APP — và 5 lỗi phải sửa TRƯỚC KHI nối
`export_canvas_clip` CÓ tham số `hieu_ung` (mặc định `""` = đường cũ y nguyên),
nhưng **không có núm trong Chỉnh mẫu, không có khoá mẫu, `m1_highlight` không
truyền, `services.enqueue_export` không có** -> anh Hùng **KHÔNG bấm tới được**.
Đúng thiết kế cho tới khi anh xem bảng mẫu và duyệt. **Trước khi nối phải sửa 5
lỗi sau (đã rà ra, CHƯA sửa vì chưa ai chạm tới được):**
1. **`zoompan` nhận `fps` SAI khi nền Đen/Trắng.** Nền `color=…:r=30` là đầu vào
   CHÍNH của `overlay` nên luồng vào `zoompan` chạy 30 fps, trong khi app truyền
   fps NGUỒN. Nguồn 25 fps -> clip 2,00s ra **2,40s** (hình dài hơn tiếng 20%).
2. **`vien_net` (`edgedetect=mode=colormix`) đổi màu TOÀN CLIP.** Filter chỉ nhận
   GBRP nên ffmpeg chèn `auto_scale` cho MỌI khung, kể cả khung `enable` đang
   TẮT: đo dU 1,27 / dV 1,56 ở khung NGOÀI cửa sổ (24 hiệu ứng kia = 0,00).
3. **`_hu_t` nhân `vspeed` SAI CHIỀU.** Mốc sinh trên timeline TRƯỚC tốc độ, phải
   **CHIA** `vspeed` (như `whoosh_offsets` đang làm) chứ không nhân. `speed=1,25`,
   clip 60s: điểm ở giây 48 thành `enable='between(t,60.0,60.6)'` -> KHÔNG BAO
   GIỜ CHẠY.
4. **`dem_nguoc` gắn cứng mốc 0,30/0,60** trong khi cửa sổ co theo `vspeed` ->
   `vspeed=0,7` thì số "1" không bao giờ hiện.
5. **`hieu_ung_log` ghi hiệu ứng mà `chuoi_filter` sẽ VỨT** khi máy thiếu font
   (`chon_hieu_ung` gọi `dung_duoc()` với `co_font=True` mặc định) -> nhật ký
   khoe hiệu ứng không tồn tại, mất 1 suất trong tối đa 3 điểm nhấn.

## 5. SỐ ĐO NGHIỆM THU LƯỢT NÀY (máy 24 nhân, RTX 3060, rảnh 13,8%)
| mốc | yêu cầu | ĐO ĐƯỢC | |
|---|---|---|---|
| trễ vòng lặp UI, 10 làn 60s | trung vị < 30ms | **16,2 ms** (p95 20,6) | ĐẠT |
| đỉnh trễ UI | < 150ms | **28,0 ms** | ĐẠT |
| tổng luồng ffmpeg 10 làn | ≤ 2× nhân (48) | **44 (1,83×)** | ĐẠT |
| clip lỗi trong 20 lượt | 0 | **0** | ĐẠT |
| chuyển cảnh TẮT vs `main` | PSNR ≥ 50 dB | **99 dB** ở 5/5 mốc | ĐẠT |
| lệch tiếng-hình | < 80 ms | 0,0 ms (thường) · 23 ms (đoạn kế 0,31s) | ĐẠT |
| rác `_seg_*` sau toàn bộ test | 0 | **0 file** | ĐẠT |
| ffmpeg mồ côi sau huỷ | 0 | **0** | ĐẠT |

## 6. CỬA CHẶN ĐÃ CHẠY LƯỢT NÀY (tất cả 0 FAIL)
`pyflakes app config.py main.py` 0 "undefined name" · `_test_app_smoke.py` ·
`_test_pipe_dialogs.py` · cổng 14 · 19 · 21 · 23 · 24 · 25 · 26 · 28 · 34 · 35 ·
36 (61 OK) · **37 MỚI** (31 OK).

---
---
# LƯỢT 08/08/2026 (chiều) — SỬA 5 LỖI · NỐI VÀO APP · AI CHỌN THÔNG MINH
Commit: `534c442` (5 lỗi + cổng 38) · `9cb687f` (nối vào app) · `60e312f`
(21 chuyển cảnh GPU) · `1a5465c` (demo v4 + đo giá).
Anh Hùng chốt: *"kệ nó đi, k bỏ vậy, nhưng làm xem đầy đủ các phần tôi bảo, với
AI lựa chọn hiệu ứng thông minh phù hợp cho tôi nhé"*.

## 1. 5 LỖI — 4 CÓ THẬT, 1 KHÔNG TÁI HIỆN ĐƯỢC
| # | lỗi | TRƯỚC | SAU |
|---|---|---|---|
| 1 | `zoompan` nhận fps sai khi nền Đen/Trắng | clip **2,400s** (đáng ra 2,000) | 2,000s ở cả 4 kiểu nền |
| 2 | `vien_net` đổi màu TOÀN CLIP | ghi là dU 1,27 / dV 1,56 | **KHÔNG tái hiện** — xem dưới |
| 3 | nhân `vspeed` sai chiều | điểm ở giây 9,00-9,70 của clip **8,03s** = không bao giờ chạy | mọi điểm nằm trong clip, đổi 12,4% -> **63,2%** pixel ở đúng mốc |
| 4 | `dem_nguoc` mất số "1" | `between(t,0.60,0.56)` = rỗng | 23.019 / 22.298 / **12.560 px** (render thật) |
| 5 | nhật ký khoe hiệu ứng không tồn tại | có | log = đúng cái vào file |

**LỖI 2 — ĐÍNH CHÍNH, ĐỪNG TIN CON SỐ CŨ.** Đo lại bằng **rawvideo (KHÔNG qua
encoder)** trên đúng khuôn graph thật: `vien_net` ra **|dU| 0,022 · |dV| 0,054 ·
0,07% pixel Y** ở khung NGOÀI cửa sổ — **Y HỆT `quang_sang`(glow) và mọi hiệu ứng
frei0r khác**, vì đó là nhiễu đổi hệ màu yuv<->rgb chung, không phải rò hiệu ứng.
Con số 1,27/1,56 cũ đo qua mp4/nvenc nên dính nhiễu rate-control. **GIỮ hiệu ứng**
(anh Hùng: không bỏ cái nào) và thay bằng ca canh CẢ 25 KIỂU.
Đối chứng để biết ngưỡng: lỗi rò CÓ THẬT (`rung_lac` bản `crop`+`scale`) từng đo
**18,7%** pixel. Trần cổng đặt ở 1,0 (U/V) và 3% — nằm giữa 0,05 và 18,7.
Nếu muốn tuyệt đối 0,000: `sobel=planes=1` / `edgedetect=mode=canny:planes=y`
chạy thẳng trong YUV (đo 0,000/0,000/0,00%) nhưng đổi tới **99% pixel** trong cửa
sổ = xoá mất khung cảnh, nên KHÔNG dùng.

## 2. ĐÃ NỐI VÀO APP — anh Hùng bấm tới được rồi
`editor.py` (ô "Hiệu ứng điểm nhấn", 4 mức, **nhãn không emoji**) -> khoá mẫu
`hieu_ung` -> `studio_page` (qua `self.layout_tpl` mà **`_export_video` cửa duy
nhất** đặt vào — cổng 19) -> `services.enqueue_export` (payload **+ sig dedup**)
-> `m1_highlight` -> `export_canvas_clip` + `hieu_ung_log` -> nhật ký dây chuyền.

**MẶC ĐỊNH `nhe` CHO MẪU CŨ** => **200-300 kênh sẽ CÓ hiệu ứng điểm nhấn NGAY
khi cập nhật.** Muốn tắt hết thì đổi 3 chỗ: `editor._apply_layout`,
`studio_page._export_video_inner`, `m1_highlight`.

## 3. GIÁ PHẢI TRẢ (3 đoạn = 24s · 1080x1920 · nvenc · máy rảnh 9,5% · lặp 3)
| ca | wall | CPU-giây | so TẮT |
|---|---|---|---|
| TẮT hết (đường cũ) | 5,56s | 20,56 | — |
| chỉ chuyển cảnh 'nhe' | 8,51s | 36,69 | 1,53x |
| chỉ điểm nhấn 'nhe' | 7,44s | 29,25 | 1,34x |
| chỉ điểm nhấn 'vua' | 7,96s | 33,52 | 1,43x |
| chỉ điểm nhấn 'manh' | 7,89s | 34,62 | 1,42x |
| **MẶC ĐỊNH MỚI (nhe+nhe)** | **10,38s** | **47,36** | **1,87x** |
| manh+manh (GPU) | 8,92s | 33,16 | 1,60x |

**PHÁT HIỆN:** mức 'manh' + GPU **RẺ HƠN** mức mặc định (1,60x vs 1,87x wall) vì
đường GPU cắt 2n-1 mảnh rồi concat, **KHÔNG encode lại TOÀN CLIP** ở pha 1.5 như
đường `xfade` CPU. Muốn hạ giá mặc định thì hướng đi là đó.

## 4. NHÓM GPU — ĐÃ NỐI (21 chuyển cảnh), SHADER THÌ CHƯA
Mức 'manh' + máy có OpenCL -> dùng kernel gl-transitions. `nhe`/`vua` giữ CPU
nên 200-300 kênh không đổi hành vi. Kiến trúc: **2n-1 mảnh + concat demuxer**
(`_tach_va_noi_gpu`) vì `xfade_opencl` KHÔNG nối cả clip được (bẫy 2 `hwupload`).
Fallback 3 lớp: thiếu OpenCL -> `GPU_LUI_VE` đổi sang kiểu CPU · GPU hỏng giữa
chừng -> dọn mảnh rồi làm lại bằng CPU · **HUỶ thì ném tiếp, không lùi**.

**LỖI THẬT tìm được khi làm:** đếm bằng GIÂY thì mỗi mảnh làm tròn LÊN trọn khung
mà concat demuxer CỘNG DỒN -> clip 3 đoạn ra **17,067s thay vì 17,000s**; 4 đoạn
sẽ +7 khung = 0,117s = **vượt mốc lệch 80 ms**. Chữa: chốt SỐ KHUNG từng mảnh
(`-frames:v` + `-t` đầu ra). Đo lại 2/3/4 đoạn đều lệch **0 ms**.

**6 SHADER libplacebo: CHƯA NỐI.** Lý do kỹ thuật, không phải quên: `libplacebo`
**không có timeline `enable`** và cần `hwupload`/`hwdownload` -> áp là áp **TOÀN
CLIP**, trái luật chống loè số 1 (hiệu ứng chỉ 0,3-0,8s ở điểm nhấn). Muốn dùng
phải cắt clip ở điểm nhấn thành mảnh riêng như đường GPU — làm được, nhưng là
việc riêng.

## 5. BẪY MỚI (đừng lặp)
- `QApplication.instance() or QApplication([])` **đứng trơ, không giữ biến** ->
  Python thu hồi QApplication -> chết **0xC0000409** lúc dựng QDialog, KHÔNG
  traceback, `faulthandler` cũng không bắt được, `*>` của PowerShell mất SẠCH
  output nên rất dễ tưởng "test treo".
- Dựng Qt trong CÙNG tiến trình đã chạy ffmpeg-OpenCL cũng chết 0xC0000409 ->
  phần UI của cổng 38 chạy ở **tiến trình riêng**.
- Đo chuyển cảnh phải đo ở **[a, a+d]** (phép bù lấy thêm phim ở CUỐI đoạn A),
  KHÔNG phải [a-d, a] -> đo trước mốc ra 0,0% và FAIL OAN.
- Hiệu ứng dao động (`nhay_sang`, sin 4,5 lần/giây) phải đo **ĐỈNH trên mọi
  khung** trong cửa sổ; đo 1 khung có thể rơi đúng chỗ sin=0 -> 0,0% FAIL OAN.
- `zoompan` đóng dấu lại mốc thời gian theo `fps` truyền vào -> khi ĐO phải ép
  `fps=` ở đầu graph cho khớp, không thì khung cùng chỉ số là nội dung KHÁC.

## 6. NGHIỆM THU LƯỢT NÀY
Demo: **`D:\hieu-ung-demo-v4\`** — 10 mp4 (5 ca × BẬT/TẮT) + `_ghi_chu.txt`.

| mốc | yêu cầu | ĐO ĐƯỢC | |
|---|---|---|---|
| trễ vòng lặp UI, 10 làn 60s, MẶC ĐỊNH MỚI | trung vị < 30ms | **15,9 ms** (p95 21,3) | ĐẠT |
| đỉnh trễ UI | < 150ms | **37,2 ms** | ĐẠT |
| tổng luồng ffmpeg 10 làn, mặc định mới | ≤ 2× nhân (48) | đỉnh 47-66 · **TB 33** | xem ghi chú |
| clip lỗi trong 10 làn × 4 cấu hình | 0 | **0** | ĐẠT |
| chuyển cảnh + hiệu ứng TẮT vs `main` | PSNR ≥ 50 dB | **99 dB** ở 5/5 mốc | ĐẠT |
| lệch tiếng-hình | < 80 ms | 0,0 ms · hình −33,3 ms | ĐẠT |
| độ dài clip GPU 2/3/4 đoạn | lệch < 40 ms | **0 ms** cả 3 | ĐẠT |
| tỉ lệ giây có hiệu ứng (5 clip demo) | ≤ 10% | **3,2–4,9%** | ĐẠT |
| tỉ lệ giây có hiệu ứng (9 clip cổng 38) | ≤ 10% | **2,2–6,2%** (trung vị 3,6) | ĐẠT |
| rác `_seg_*` / `_MEI*` / `_nhip_*` | 0 | **0** | ĐẠT |
| ffmpeg mồ côi | 0 | **0** | ĐẠT |
| thư viện Python thêm mới | 0 | **0** | ĐẠT |

**GHI CHÚ VỀ CỘT LUỒNG:** đỉnh 47-66 đo được có **2 tiến trình**, nhưng cửa chờ
chỉ cho **1** lệnh chạy — tiến trình thứ 2 là tiến trình ĐANG THOÁT mà `psutil`
vẫn đếm. Luồng TRUNG BÌNH 33 (1,37× nhân). Đường cũ đo cùng cách ra đỉnh 44-45.
**MỌI SỐ ĐO Ở TRÊN LẤY KHI `BQHungVideo.exe` CỦA ANH HÙNG ĐANG CHẠY** (không tắt
được app đang sản xuất) -> đây là **CẬN TRÊN**, máy rảnh chỉ tốt hơn.

### Cửa chặn đã chạy (tất cả 0 FAIL)
pyflakes 0 "undefined name" · `_test_app_smoke` · `_test_pipe_dialogs` ·
`_test_pipe_overlap` · `_test_lane_starve` · `_test_shutdown_safety` ·
`_test_cancel_persist` · `_test_ai_gate` · `_test_chan_search` ·
`_test_reanalyze_clean` · `_test_clip_count_len` · `_test_no_popup` ·
`_test_don_rac` · `_test_guard` · `_test_db_maint` · `_test_chon_kenh_mau` ·
`_test_hoc_gu` · `_test_pipe_e2e` (PASS, có ghi dòng điểm nhấn vào nhật ký) ·
cổng 14 · 19 · 21 · 23 · 24 · 25 · 26 · 28 · 34 · 35 · **36 (64 OK)** ·
**37 (31 OK)** · **38 MỚI (46 OK)**.

## 7. CHƯA LÀM ĐƯỢC (nói thẳng)
1. **6 shader libplacebo CHƯA nối** — `libplacebo` không có timeline `enable`
   nên áp là áp TOÀN CLIP, trái luật chống loè số 1. Muốn dùng phải cắt clip ở
   điểm nhấn thành mảnh riêng như đường GPU.
2. **`export_vertical_clip` KHÔNG có hiệu ứng/chuyển cảnh** — đó là đường cho
   mẫu THIẾU khung video (`video_rect`). Giống hệt tình trạng của `chuyen_canh`
   từ lượt trước, không phải hồi quy. Mixed-Cut đã bỏ nên không tính.
3. **Chưa đo trên máy nhân viên yếu THẬT** — chỉ mô phỏng bằng cổng 37 (tắt
   NVENC + frei0r + OpenCL bằng monkeypatch).
4. **Chưa build `.exe`** để kiểm bản đóng gói (mục "Bản đóng gói" của TỔNG RÀ
   SOÁT) — chưa bump version nên chưa phát hành, và anh Hùng đang chạy app.
5. **Giá phải trả 1,87× wall** cho mặc định mới — đã đo, đã ghi ở mục 3, nhưng
   CHƯA tối ưu. Hướng rẻ hơn đã nhìn thấy: đường GPU (1,60×).
6. **Chưa chạy TỔNG RÀ SOÁT quy mô 50 kênh** (mục anh Hùng thêm cuối phiên):
   e2e 1 kênh/2 video đã PASS, 10 làn đã đo, nhưng **chưa chạy ≥50 kênh cùng
   lúc** vì máy anh Hùng đang chạy sản xuất.

---
---
# LƯỢT 08/08/2026 (tối) — ⭐ TỔNG RÀ SOÁT: 3 LỖI THẬT LÒI RA

> Đây là lượt "chạy CẢ HỆ THỐNG như thật" ở đầu file. Bộ công cụ mới:
> `_ra_e2e.py` · `_ra_50kenh.py` · `_ra_may_nhanvien.py` · `_ra_cong.py` ·
> `_ra_luong_phan_tich.py` · `_ra_ab_chuyen_dong.py` · `_ra_key_groq.py`.
> Mọi script đều sandbox `BQ_DB_PATH`+`BQ_DATA_DIR`+`BQ_QSETTINGS_INI` và
> `import _test_guard` → KHÔNG đụng DB / cài đặt / Explorer của anh Hùng.

## ĐIỀU KIỆN ĐO
Máy 24 nhân · RTX 3060 · CPU nền 10-14% · 0 ffmpeg lạ · ổ C còn 342 GB.
`BQHungVideo.exe` của anh Hùng ĐANG MỞ nhưng **đo được 0,05% CPU và 0 tiến
trình ffmpeg con** → coi là máy rảnh; đã ghi rõ vì `_may_ranh()` vẫn cảnh báo.
Nguồn: **7 video Nhật THẬT** (`C:\Users\Admin\Downloads\thùng rác`), soi trước
bằng `_ra_probe.py` để phủ đủ ca: **VFR ×2 · CFR 25/29,97/59,94 fps · 2–14
phút · 1 ca KHÔNG LỜI** (hình Nhật thật, tiếng thay bằng im lặng). Mỗi video 1
KÊNH riêng → 7 kênh chạy cùng lúc.

## ⚠ 3 LỖI THẬT TÌM ĐƯỢC (đã sửa, mỗi lỗi có ca canh)

### LỖI 1 — Bản PHÁT HÀNH quên `app/assets/hieu_ung` (nặng nhất)
`.github/workflows/release.yml` (**chính là bản máy nhân viên tự cập nhật**)
khai `--add-data` cho `fonts` + `sfx` nhưng **bỏ sót `hieu_ung`**.
`BQHungVideo.spec` sót y hệt, và nó bị `.gitignore` nên **sửa mỗi spec là
KHÔNG cứu được máy nhân viên**. Hậu quả trên `.exe`, app **không báo một dòng
lỗi nào** (mọi đường đều "lùi êm"):
- `hieu_ung/frei0r/` mất → kho hiệu ứng **25 → 14**
- `gl_transitions.cl` mất → **21 chuyển cảnh GPU biến mất** (mức `manh` lặng
  lẽ lùi về CPU)
- `shaders/` mất → 6 shader không dùng được
- **`NGUON_GIAY_PHEP.md` mất → không kèm giấy phép GPL/LGPL của frei0r**
Máy anh Hùng chạy từ NGUỒN nên đủ hiệu ứng → không ai phát hiện ra.
**Cổng 39 `_test_dong_goi.py`** (mới): CA A quét tĩnh **cả 2 cửa** đóng gói ·
CA B đếm file thật trong `dist/_internal/app/assets` + so ngày sửa `.exe` với
mã nguồn (đúng bẫy 06/08 "dist/ còn bản cũ mà tưởng đã build").

### LỖI 2 — Lệnh ĐO của pha phân tích không siết luồng: 1 lệnh ăn 70 luồng
Lượt e2e đo tổng **203 luồng ffmpeg = 8,46× số nhân**, phá mốc "≤ 2× nhân".
Mốc cũ 44 luồng (1,83×) chỉ đo đường **XUẤT**; lượt này đo **cả pha PHÂN TÍCH**
nên lỗi mới lộ. Truy ra: `chon_doan.chuyen_dong` gọi `subprocess.run` TRẦN,
**một mình 70 luồng (2,92× nhân)**, ngốn ~13,5 nhân → cướp CPU của làn XUẤT.
3 lệnh đo **cố ý đứng ngoài cửa chờ** (lệnh đo mà xin chỗ sẽ tự khoá lẫn với
lệnh xuất đang giữ chỗ) nên cửa chờ không cứu được — phải siết núm tại chỗ.

A/B **đan xen** 3 vòng (nguồn Nhật 653s/60fps/263 MB; dãy số khít, không nhiễu):

| cấu hình | wall | CPU-giây | đỉnh luồng | |
|---|---|---|---|---|
| HIỆN TẠI (không núm) | 17,06s | **229,3** | **70 (2,92×)** | ❌ |
| **giải mã 4** | 28,60s | **102,2** | **22 (0,92×)** | ✅ chọn |
| giải mã 2 | 47,83s | 89,3 | 14 (0,58×) | ✅ nhưng chậm 2,8× |
| giải mã 1 | 80,71s | 83,4 | 9 (0,38×) | ✅ nhưng chậm 4,7× |
| GPU `cuda` + giải mã 4 | 52,92s | **30,0** | 25 (1,04×) | chưa dùng |
| GPU `d3d11va` + giải mã 4 | 146,70s | 158,4 | 41 | **tệ hơn bản gốc** |

Chọn mức **theo SỐ NHÂN, trần 4** (24 nhân→4 · 4 nhân→2 · 2 nhân→1), **KHÔNG**
dùng thẳng `decode_threads()` vì nó hạ về 2 khi `ECO_MODE` bật (mặc định BẬT)
mà mức 2 làm `chuyen_dong` **82,4s → 198,1s (2,4×)** đổi lấy phần luồng không
đáng. Đo lại: **70 → 22 luồng**, `chuyen_dong` +37%. CPU-giây giảm ~56% — ở quy
mô 300 video/ngày là **19 giờ-nhân/ngày → 8,4 giờ-nhân/ngày** chỉ riêng bước đo
chuyển động. **Cổng 37 thêm CA 7**: quét tĩnh (lệnh có `-f null` mà thiếu
`-threads` = FAIL) + đo thật đỉnh luồng ≤ 2× nhân.

### LỖI 3 — Cột `analysis.engine` NÓI DỐI (suýt làm tôi kết luận sai)
`analysis._run_one` đóng cứng `f"faster-whisper:{model}"` cho MỌI lượt chép
lời. Nhưng `transcribe()` **tự lùi về whisper MÁY khi Groq lỗi, không báo một
dòng nào** (CLAUDE.md cổng 22: "chậm hơn hàng chục lần"), và cột này là chỗ
DUY NHẤT nhìn ra được. Đo thật: cả 7 video ghi `faster-whisper:large-v3` trong
khi **38/38 key Groq còn sống** và gọi thẳng `_transcribe_groq` ra 35 đoạn bình
thường → **tôi mất một lượt điều tra vì cột này**. Nay mỗi đường tự khai
`engine` (`groq:whisper-large-v3` / `stable-ts:<model>` /
`faster-whisper:<model>`). Đo lại: báo đúng `groq:whisper-large-v3` → **xác
nhận lượt e2e THỰC SỰ chạy Groq, không hề tụt về whisper máy.**

## KHÔNG PHẢI LỖI — 1 ca suýt báo oan, ghi lại để đừng lặp
Trích khung 8 Part vừa xuất thấy **hộp tiêu đề ra Ô VUÔNG TRẮNG (tofu)** ở
**cả 8/8** — giống hệt lỗi "ô đen" máy anh Hùng từng gặp. Đo phân định bằng
`_ra_tieu_de.py`: cùng hàm `editor.render_overlay_png`, cùng chữ, cùng font
Montserrat →
- nền tảng Qt `windows` (**như app thật**): chữ Nhật + Latin render **ĐÚNG**
- nền tảng `offscreen` (**như test**): chữ Nhật ra **TOFU**

→ **tạo tác của bộ test**, không phải lỗi app: `QT_QPA_PLATFORM=offscreen`
thiếu đường lùi font CJK của Windows. **Hệ quả phải nhớ: mọi test headless
KHÔNG bao giờ soi được chữ trên clip xuất ra** — muốn canh chữ tiêu đề phải
render ở nền tảng `windows`.
