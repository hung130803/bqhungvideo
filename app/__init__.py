"""AI Content Studio - package gốc."""
__version__ = "0.1.0"


def _bo_dem_ma_nguon_song() -> None:
    """Bản .exe chạy THẲNG mã nguồn (`_nguon_song`) KHÔNG ghi bộ đệm .pyc, nên
    mỗi lần mở app và MỖI tiến trình phân tích con dịch lại toàn bộ mã.

    Đo 31/10/2026 (máy anh Hùng, ổ D: là ổ cứng cơ): nạp mã giao diện 9,0 giây
    khi không có bộ đệm, 0,95 giây khi có. Bộ đệm đặt ở thư mục dữ liệu (ổ SSD),
    không rải vào thư mục dự án; Python tự bỏ bộ đệm cũ khi file nguồn đổi
    (so mtime + cỡ) nên sửa mã xong mở lại app vẫn chạy bản mới.

    Đặt ở ĐÂY (không chỉ trong `_nguon_song`) vì `_nguon_song.py` nằm trong gói
    .exe: sửa nó phải đóng gói lại, còn file này đi theo nguồn sống ngay."""
    import os
    import sys
    if not getattr(sys, "frozen", False):
        return
    ns = sys.modules.get("_nguon_song")
    if ns is None or not getattr(ns, "dang_bat", lambda: False)():
        return
    try:
        base = os.environ.get("BQ_DATA_DIR") or os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.dirname(sys.executable)), "BQHungVideo")
        d = os.path.join(base, "_pyc_nguon")
        os.makedirs(d, exist_ok=True)
        sys.pycache_prefix = d
        sys.dont_write_bytecode = False
    except OSError:
        pass


_bo_dem_ma_nguon_song()
