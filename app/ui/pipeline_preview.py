"""Read-only source preview. Missing/unreadable directories are never 'empty'."""
import os
from pathlib import Path
import stat


def source_preview(path, scan):
    if not path:
        return dict(label='Chưa đặt', error='Chưa đặt thư mục nguồn', ready=0, busy=0)
    try:
        folder=Path(path)
        if not folder.is_absolute():
            return dict(label='Sai đường dẫn',error='Cần đường dẫn đầy đủ',ready=0,busy=0)
        if not stat.S_ISDIR(folder.stat().st_mode):
            return dict(label='Không phải thư mục',error='Đường dẫn nguồn không phải thư mục',ready=0,busy=0)
        # Check directory access even when the scanner has a recent cached count.
        with os.scandir(folder) as entries:
            next(entries,None)
        ready,busy=scan(folder)
        label=str(len(ready))+(f' (+{len(busy)} đang ghi)' if busy else '')
        return dict(label=label,error='',ready=len(ready),busy=len(busy))
    except FileNotFoundError:
        return dict(label='Không thấy',error='Không tìm thấy thư mục nguồn hoặc ổ đĩa chưa kết nối',ready=0,busy=0)
    except (OSError,ValueError):
        return dict(label='Không đọc được',error='Không truy cập được thư mục nguồn; kiểm tra quyền và kết nối ổ đĩa',ready=0,busy=0)
