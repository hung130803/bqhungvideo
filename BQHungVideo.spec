# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

# LƯU Ý (lỗi thật tìm ra 08/08/2026 khi tổng rà soát): thiếu 1 dòng ở đây là
# TÍNH NĂNG BIẾN MẤT LẶNG LẼ trên máy nhân viên — app vẫn chạy, không một dòng
# lỗi, chỉ ÍT hiệu ứng đi. `app/assets/hieu_ung` từng bị bỏ sót: bản .exe mất
# 25 hiệu ứng frei0r (kho co còn 14), mất 21 chuyển cảnh GPU (thiếu
# `gl_transitions.cl`), mất 6 shader, và mất luôn `NGUON_GIAY_PHEP.md` — file
# GHI NGUỒN + GIẤY PHÉP GPL/LGPL của frei0r, thứ BẮT BUỘC phải kèm khi phát
# hành. Cổng `_test_dong_goi.py` nay quét MỌI thư mục app/assets/* mà mã có đọc
# và bắt lỗi nếu spec chưa khai.
# `LICENSES.txt` KHÔNG phải cho đẹp: `bin/ffmpeg.exe` kèm theo là bản
# `--enable-gpl --enable-version3` (GPL-3.0-or-later, có librubberband
# GPL-2.0) và GPL BUỘC phải kèm văn bản giấy phép + chỉ chỗ lấy mã nguồn. Bộ
# cài trước 16/08/2026 THIẾU hẳn file này. Để cạnh .exe ('.') cho người dùng
# thấy ngay, không chôn trong `_internal`.
#
# GIÓNG HÀNG (`app/core/giong_hang.py`) và GIỌNG NGOÀI (`giong_ngoai.py`):
# **CỐ Ý KHÔNG khai gì thêm ở đây — đã kiểm, không phải bỏ sót.** Ghi ra để
# người sau đừng "sửa" bằng cách nhét vài GB vào bộ cài:
#   · Hai module Python đã VÀO bản .exe sẵn qua `collect_submodules('app')`
#     (kiểm thật: `app.core.giong_hang` và `app.core.giong_ngoai` đều có
#     trong danh sách 69 module).
#   · Chúng KHÔNG đọc file tài nguyên nào. Script chạy ở tiến trình con được
#     GHI RA từ chuỗi nhúng trong mã (`giong_hang._MA_GIONG` ·
#     `giong_ngoai._MA_DOC`) chứ không phải file `.py` nằm cạnh — chính vì
#     vậy bản `.exe` (không có cây mã nguồn) mới chạy được y máy dev.
#   · Phần NẶNG là đồ TẢI RỜI LÚC CHẠY, giống hệt ràng buộc Demucs/Piper:
#     torch dùng chung `_lib` (~4,3 GB bản CUDA) · model gióng hàng MMS_FA
#     1,18 GB · trọng số OmniVoice 6,1 GB. Gói vào `.exe` là bộ cài phình từ
#     240 MB lên hơn 11 GB cho tính năng phần lớn người dùng không bật.
#     Tất cả nằm trong `DATA_DIR`, **KHÔNG cạnh `.exe`**: lượt tự cập nhật
#     `ren _internal -> _internal.old` rồi `rmdir /S /Q` sẽ xoá sạch (cổng 58
#     CA5 — đã xảy ra thật với `_lib`).
#   · Nút tải nằm trong hộp Thay giọng (`giong_hang.cai_giong_hang`).
datas = [('app/database/schema.sql', 'app/database'), ('app/assets/fonts', 'app/assets/fonts'), ('app/assets/sfx', 'app/assets/sfx'), ('app/assets/hieu_ung', 'app/assets/hieu_ung'), ('app/core/potoken_plugins', 'app/core/potoken_plugins'), ('.env.example', '.'), ('LICENSES.txt', '.')]
binaries = [('bin/ffmpeg.exe', '.'), ('bin/ffprobe.exe', '.'), ('bin/yt-dlp.exe', '.')]
hiddenimports = ['openai', 'requests', 'psutil', 'dotenv']
hiddenimports += collect_submodules('app')
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('google.generativeai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BQHungVideo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BQHungVideo',
)
