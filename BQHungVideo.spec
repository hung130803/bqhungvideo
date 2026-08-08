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
datas = [('app/database/schema.sql', 'app/database'), ('app/assets/fonts', 'app/assets/fonts'), ('app/assets/sfx', 'app/assets/sfx'), ('app/assets/hieu_ung', 'app/assets/hieu_ung'), ('app/core/potoken_plugins', 'app/core/potoken_plugins'), ('.env.example', '.')]
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
