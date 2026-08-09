# NGUỒN + GIẤY PHÉP của tài sản hiệu ứng

> Anh Hùng đã duyệt dùng **nguồn mã nguồn mở** (07/08/2026). File này ghi rõ
> lấy từ đâu, giấy phép gì, để không bao giờ dính khiếu nại bản quyền trên
> 200-300 kênh. **Không thêm file nào vào đây mà không ghi nguồn.**

## 1. frei0r-plugins — thư mục `frei0r/`

| | |
|---|---|
| Dự án | **frei0r** — kho hiệu ứng video mã nguồn mở, chính thứ Kdenlive / Shotcut / MLT / Cinelerra dùng |
| Trang chủ | https://frei0r.dyne.org/ · mã nguồn https://github.com/dyne/frei0r |
| Bản dùng | **2.5.0** |
| Bản dựng sẵn cho Windows lấy từ | MSYS2 (mingw64), gói `mingw-w64-x86_64-frei0r-plugins-2.5.0-1-any.pkg.tar.zst` — https://repo.msys2.org/mingw/mingw64/ |
| Giấy phép | **GPL-2.0-or-later** cho phần lớn plugin; một số plugin LGPL. Xem `frei0r/COPYING` |
| Vì sao dùng được | `bin/ffmpeg.exe` (bản BtbN `ffmpeg-master-latest-win64-gpl`) đã build với `--enable-gpl --enable-version3 --enable-frei0r`, tức bản ffmpeg này **đã là GPL**. App gọi ffmpeg qua **tiến trình riêng** (`subprocess`), không liên kết thư viện vào mã Python |

### Plugin ĐANG kèm (12 file, 239 KB)
`distort0r` · `filmgrain` · `glitch0r` · `glow` · `lenscorrection`
· `letterb0xed` · `nosync0r` · `ntsc` · `pixs0r` · `scanline0r` · `softglow`
· `squareblur`

`pixs0r` là file THÊM 09/08/2026 (**19.408 byte**), cùng gói MSYS2 2.5.0, cùng
giấy phép GPL-2.0-or-later. Nó là plugin C thuần, KHÔNG cần thêm DLL runtime
nào ngoài 3 cái đã có. Dùng cho hiệu ứng `xe_dong` ("Xé dòng ngang") — xem
NHÓM 6 trong `app/core/hieu_ung.py`.

Gói MSYS2 có **159 file .dll**; ffmpeg nạp được **87** trong số đó với tư cách
filter 1 đầu vào (số ĐO THẬT, xem `_do_frei0r_quet.py` → `_ket_frei0r.json`).
Repo chỉ kèm 12 cái ĐANG DÙNG để không phình dung lượng — muốn thêm thì chép
thêm .dll vào `frei0r/` rồi khai báo trong `app/core/hieu_ung.py`.

**KIỂU THAM SỐ phải DÒ, không đoán** (`_do_f0r_thamso.py`): `frei0r=
filter_params=` nhận 4 mã hoá khác nhau — `0.85` (double) · `y`/`n` (bool) ·
`0.1/0.2/0.3` (màu) · `0.25/0.75` (vị trí). Đưa sai kiểu là ffmpeg **chết cả
lệnh** chứ không bỏ qua. ffmpeg KHÔNG in bảng tham số ra ở bất kỳ mức log nào,
nên phải dò bằng cách "đầu độc" từng chỉ số rồi đọc tên trong lời lỗi.
Đã dò được 09/08/2026: `pixs0r` = `<double>|<double>|<double>|<double>` ·
`flippo` = `y|n` · `pixeliz0r` = `<d>|<d>|n` · `c0rners` = 8 double + bool ở
chỉ số 8 và 12 · `defish0r` = bool ở chỉ số 1 và 8 · `normaliz0r` = 2 MÀU rồi
3 double · `perspective` = 4 VỊ TRÍ · `IIRblur` = `<d>|<d>|n`.

Vì sao 159 → 87: **26** plugin kiểu `mixer2` (chế độ hoà 2 lớp: `addition`,
`multiply`, `screen`…) và **16** plugin `sleid0r_*` (chuyển cảnh 2 đầu vào) —
filter `frei0r` của ffmpeg **chỉ nhận 1 đầu vào** nên không dùng được; **9**
plugin kiểu `source` (`plasma`, `test_pat_*`…) sinh hình chứ không sửa hình;
**11** plugin cần thêm `libcairo` / `libgavl` / `libopencv` (không kèm).

### `frei0r/runtime/` — 3 DLL runtime của mingw-w64 (2,79 MB)
`libstdc++-6.dll` · `libgcc_s_seh-1.dll` · `libwinpthread-1.dll`
Nguồn: MSYS2 `mingw-w64-x86_64-gcc-libs-16.1.0-6` và
`mingw-w64-x86_64-libwinpthread-git-12.0.0.r747.g1a99f8514-1`.
Giấy phép: **GPL-3.0 + GCC Runtime Library Exception** (libstdc++/libgcc) ·
**MIT/BSD** (libwinpthread) — cả 2 cho phép phát hành kèm.

**PHẢI nằm CẠNH `ffmpeg.exe`, không phải cạnh plugin.** ffmpeg nạp plugin bằng
`LoadLibraryExA(..., LOAD_LIBRARY_SEARCH_APPLICATION_DIR|SYSTEM32|USER_DIRS)`
nên Windows **không** tìm phụ thuộc theo `PATH` và **không** tìm cạnh DLL vừa
nạp. Đo thật 07/08/2026: để cạnh plugin → **63/159** nạp được; để cạnh
`ffmpeg.exe` → **87/159**. `hieu_ung.bao_dam_runtime()` tự chép; chép không được
thì app **tự tắt** 2 hiệu ứng cần chúng (`nosync0r`, `scanline0r`), KHÔNG nổ lỗi.

## 2. gl-transitions — thư mục gốc, file `gl_transitions.cl`

| | |
|---|---|
| Dự án | **gl-transitions** — kho chuyển cảnh GLSL mã nguồn mở |
| Nguồn | https://github.com/gl-transitions/gl-transitions |
| Giấy phép | **MIT** (xem nguyên văn bên dưới) |
| Cách dùng | Công thức GLSL được **viết lại tay sang OpenCL C** cho filter `xfade_opencl` của ffmpeg (`transition=custom:source=…:kernel=…`). Không chép nhị phân, không tải file lúc chạy |
| Chạy ở đâu | **GPU** (OpenCL). Máy không có OpenCL -> `hieu_ung_gpu.dung_duoc()` trả `[]`, app dùng `xfade` CPU như cũ, KHÔNG một dòng lỗi |

### 21 kernel ĐANG DÙNG + tác giả gốc (số ĐO THẬT, không phải đếm tên)
Đã render bằng GPU thật, đếm pixel từng khung, đo U/V — xem `_do_gpu_chuyen_canh.py`
→ `_ket_gpu.json`. **21/21 ĐẠT.**

`crosswarp` (Eke Péter) · `directional` ×2 (gre) · `directionalwarp` (pschroen)
· `wind` (gre) · `ripple` (gre) · `pixelize` (gre) · `squareswire` (gre)
· `radial` (Xaychru) · `crosshatch` (pthrasher) · `crossblur` · `rotate`
· `morph` · `verticalstripes` · `randomsquares` · `waterdrop` · `angular`
· `radialblur` · `pinwheel` · `swap` · `glitchmemories` (Gunnar Roth)

**3 kernel viết rồi nhưng KHÔNG đưa vào kho** (mã còn trong `.cl` để đối chiếu):
`polka dots curtain` — khung giữa đã giống đoạn sau 94,4%, nhìn ra là cắt khô;
`simplezoom` — lệch màu U+3,3 V−3,6 (trần U/V < 3); `fadecolor` — lệch màu
U−21,7 V−43,3. **Không ship cái không đo được.**

### Nguyên văn giấy phép MIT của gl-transitions
```
The MIT License (MIT)

Copyright (c) 2017 Gaetan Renaudeau (gre) and gl-transitions contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2b. Shader GLSL cho `libplacebo` — thư mục `shaders/`
**TỰ VIẾT 100%**, không lấy từ đâu: 6 file `.hook` (`hat_phim` · `mo_net` ·
`net_hon` · `quang_sang` · `toi_vien` · `tuong_phan`) là công thức toán đặt
trong khuôn `//!HOOK` của mpv — 0 file tải về, 0 rủi ro bản quyền, tổng **3,7 KB**.
Chạy trên **GPU** qua Vulkan. Máy không có Vulkan -> `shader_co()` trả `[]`,
app bỏ qua, KHÔNG nổ lỗi. Đo thật: **6/6 ĐẠT**, 30/30 khung, lệch U/V < 0,5.

## 3. KHÔNG DÙNG — 6 file trong `D:\hieu-ung-demo\overlays`
AV1, tải từ đâu về **không rõ nguồn** → **cấm ship**. Anh Hùng cho phép dùng
không tạo ra quyền nếu file là của người khác. Một khiếu nại là dính cả cụm kênh.

## 3b. NHÓM LỚP PHỦ HẠT (tuyết · trái tim · confetti…) — **0 BYTE tài nguyên**

Thêm 09/08/2026. Anh Hùng yêu cầu *"tuyết rơi, trái tim bay, với rất nhiều kiểu
khác"* nhưng đã chốt trước đó *"không được làm app quá nhiều dung lượng"* (gói
đang 228 MB), và mục 3 ngay trên đây đã cấm 6 file overlay không rõ nguồn.

**Nên 10 kiểu lớp phủ được SINH BẰNG ffmpeg, không một file nào:**
`color` (nền màu hạt) + `geq` (biểu thức toán vẽ mặt nạ hạt) + `alphamerge` +
`scale` + `overlay`, cắt đúng cửa sổ bằng `trim`/`concat`. Riêng confetti lấy
màu từ `gradients` (nguồn dựng sẵn của ffmpeg, `seed` cố định).

| | |
|---|---|
| Dung lượng thêm vào gói | **0 byte** — đo bằng `git diff --stat`: chỉ có file `.py` |
| `.spec` / `release.yml` | **KHÔNG phải sửa** — nhóm này không đọc `app/assets/*` |
| Rủi ro bản quyền | **0** — công thức toán tự viết, không tải, không chép của ai |
| Máy thiếu GPU/frei0r | vẫn chạy: toàn filter lõi của ffmpeg, không Vulkan, không OpenCL, không plugin ngoài |

Kỹ thuật "băm bằng `mod(sin(x)*43758.5453,1)`" và "lưới ô — mỗi ô một hạt" là
**thủ pháp phổ thông của giới shader**, không phải mã của một dự án cụ thể nào;
ở đây viết lại bằng cú pháp biểu thức của ffmpeg. Số đo từng kiểu: xem cổng 46
(`_test_lop_phu.py`) và `_do_lop_phu.py`.

## 4. Tài sản TỰ SINH
Mọi hiệu ứng thuần ffmpeg trong `hieu_ung.py` (`zoompan`, `crop`, `eq`, `noise`,
`pixelize`, `vignette`, `gblur`, `unsharp`, `lagfun`, `edgedetect`,
`shufflepixels`, `rgbashift`, `drawtext`) là **công thức toán**, 0 file tải về,
0 rủi ro bản quyền, 0 phình dung lượng.

MỞ RỘNG KHO 09/08/2026 thêm **15 kiểu nữa cùng loại này** — cũng chỉ là công
thức, cũng 0 byte tài nguyên: `shear` · `perspective` · `rotate` ·
`lenscorrection` (bản THUẦN của ffmpeg, khác plugin frei0r cùng tên) ·
`shufflepixels` (chế độ `block` và `vertical`) · `swaprect` · `scroll` ·
`lutyuv` · `dblur` · `boxblur`, cộng 4 quỹ đạo `zoompan` mới (kéo lùi, lướt
ngang, lướt dọc, và zoom+`rotate` ghép đôi).
Đây là chỗ ĐÁNG GIÁ NHẤT của cả lượt: chúng chạy trên **MÁY NHÂN VIÊN** (không
frei0r · không Vulkan · không OpenCL) mà không thêm một byte nào vào gói cài.
