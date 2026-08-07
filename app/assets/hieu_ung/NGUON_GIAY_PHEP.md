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

### Plugin ĐANG kèm (13 file, 253 KB)
`distort0r` · `filmgrain` · `gateweave` · `glitch0r` · `glow` · `lenscorrection`
· `letterb0xed` · `nosync0r` · `ntsc` · `scanline0r` · `softglow` · `squareblur`
· `vertigo`

Gói MSYS2 có **159 file .dll**; ffmpeg nạp được **87** trong số đó với tư cách
filter 1 đầu vào (số ĐO THẬT, xem `_do_frei0r_quet.py` → `_ket_frei0r.json`).
Repo chỉ kèm 13 cái ĐANG DÙNG để không phình dung lượng — muốn thêm thì chép
thêm .dll vào `frei0r/` rồi khai báo trong `app/core/hieu_ung.py`.

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

## 2. gl-transitions — CHƯA kèm file nào
Kho kernel chuyển cảnh https://github.com/gl-transitions/gl-transitions, giấy
phép **MIT**. Nếu sau này chuyển kernel sang `xfade_opencl` thì **phải chép kèm
đoạn giấy phép MIT + tên tác giả từng kernel** vào đây.

## 3. KHÔNG DÙNG — 6 file trong `D:\hieu-ung-demo\overlays`
AV1, tải từ đâu về **không rõ nguồn** → **cấm ship**. Anh Hùng cho phép dùng
không tạo ra quyền nếu file là của người khác. Một khiếu nại là dính cả cụm kênh.

## 4. Tài sản TỰ SINH
Mọi hiệu ứng thuần ffmpeg trong `hieu_ung.py` (`zoompan`, `crop`, `eq`, `noise`,
`pixelize`, `vignette`, `gblur`, `unsharp`, `lagfun`, `edgedetect`,
`shufflepixels`, `rgbashift`, `drawtext`) là **công thức toán**, 0 file tải về,
0 rủi ro bản quyền, 0 phình dung lượng.
