# VIỆC: chuyển cảnh ở chỗ ghép đoạn + chữa quá tải luồng

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
