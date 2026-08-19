# -*- coding: utf-8 -*-
"""TỰ DỌN RÁC ĐĨA khi mở app — đo thật trên máy anh Hùng 31/07/2026 (ổ C còn
5,7 GB / 926 GB):

    %TEMP%\\_MEI*        4,69 GB / 339 thư mục  ← yt-dlp (bản đóng gói
                                                 PyInstaller) giải nén ~22 MB
                                                 mỗi lần chạy; bị tắt giữa
                                                 đường là BỎ LẠI nguyên khối.
    %TEMP%\\_seg_*.mkv   1,71 GB / 100 file     ← mảnh ghép đoạn của app; dọn
                                                 trong finally nhưng app tắt
                                                 bằng os._exit thì finally
                                                 KHÔNG chạy.
    DATA_DIR\\studio_*.db   12 file             ← bản app cũ để lại.
    DATA_DIR\\logs\\pipeline_*.log               ← không giới hạn ngày.

Ổ đầy là nguyên nhân gốc của cả DB vỡ (ghi dở dang) lẫn job lỗi, nên dọn rác
KHÔNG phải việc phụ.

BẤT BIẾN AN TOÀN (đừng nới lỏng):
  * CHỈ xoá trong %TEMP% và DATA_DIR, CHỈ những tên khớp danh sách dưới.
  * BỎ QUA mọi thứ vừa đổi trong `gio` giờ -> không đụng việc đang chạy.
  * BỎ QUA thư mục _MEI của CHÍNH tiến trình này (sys._MEIPASS).
  * File/thư mục đang bị khoá -> bỏ qua im lặng (đừng cố xoá).
  * TUYỆT ĐỐI không đụng: projects/, KhoVideo/, studio.db đang dùng, .env,
    cookie, models/, _potoken/, _cache/tts (có LRU riêng).
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

# --- rác trong %TEMP% ---
# (mẫu tên, có phải thư mục, giờ tuổi tối thiểu, ghi chú)
RAC_TEMP: tuple[tuple[str, bool, float, str], ...] = (
    ("_MEI*", True, 2.0, "yt-dlp giải nén rồi bị tắt giữa đường"),
    ("_seg_*", None, 2.0, "mảnh ghép đoạn của app"),
    ("gq_*", True, 2.0, "gói audio gửi Groq"),
    ("recap_*", True, 2.0, "giọng đọc reup"),
    ("dub_*", True, 2.0, "giọng thuyết minh"),
    ("bqvid_*", None, 2.0, "file tạm xuất clip"),
    # Ảnh lớp chữ (tiêu đề + huy hiệu Part) do Qt vẽ sẵn. Lượt xuất bị ngắt mà
    # job không bao giờ chạy lại thì file này nằm lại (~15-35 KB/lượt). Chờ đủ
    # 2 giờ mới dọn: job xếp hàng vẫn cần đúng file này để dựng lại lớp chữ.
    ("_ovl_*", None, 2.0, "ảnh lớp chữ tiêu đề/Part"),
    ("bq_dbcopy*", True, 2.0, "bản sao DB để kiểm tra"),
    # Hộp cát của nhóm cổng THAY GIỌNG. Chúng chứa wav PCM **không nén** +
    # bản tách Demucs nên là loại rác NẶNG NHẤT: 15/08/2026 một lượt bị
    # `timeout` giết bỏ lại **80-131 GB**, `%TEMP%` phình 420 GB và ổ C đầy
    # 100%. Máy dev CHÍNH LÀ máy anh Hùng, nên bộ dọn của app phải biết mặt
    # chúng — đừng trông chờ mỗi cổng tự dọn (cái làm đầy ổ chính là lượt
    # KHÔNG dọn được).
    ("tg_gate_*", True, 2.0, "hộp cát cổng 53 thay giọng"),
    ("tgui_*", True, 2.0, "hộp cát cổng 55 thay giọng UI"),
    ("tgbang_*", True, 2.0, "hộp cát cổng 57 bảng tiến độ"),
)

_GIU_BAN_DB = 3          # giữ 3 bản studio_*.db / .corrupt mới nhất
_GIU_NGAY_LOG = 14       # giữ log 14 ngày
_TRAN_ERROR_LOG = 2 * 1024 * 1024   # error.log > 2 MB thì cắt còn nửa cuối


def _co(p: Path) -> int:
    """Dung lượng (byte) của file/thư mục — lỗi thì coi như 0."""
    try:
        if p.is_dir():
            return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return p.stat().st_size
    except OSError:
        return 0


def _xoa(p: Path) -> int:
    """Xoá 1 mục, trả số byte giải phóng (0 nếu bị khoá/lỗi/BỊ CẤM).

    Chốt `ly_do_cam` thêm 19/08/2026 (cổng 80): mọi nơi gọi hiện thời đều
    truyền CON của `glob`/`iterdir` nên an toàn DO XÂY DỰNG — nhưng hàm này
    là `rmtree(..., ignore_errors=False)` TRẦN, tức `_xoa(Path("."))` xoá
    sạch thư mục đang làm việc rồi `except OSError` nuốt im lặng và trả 0.
    Một mẫu tên mới vô ý (`"*"`) hay một nơi gọi mới là đủ. Chốt rẻ (chỉ
    `resolve()`), đặt vào đây thì cả 4 nơi gọi được che một lượt.
    """
    from app.core.xoa_an_toan import ly_do_cam
    if ly_do_cam(p):
        return 0
    n = _co(p)
    try:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=False)
        else:
            p.unlink()
        return n
    except OSError:
        return 0            # đang bị khoá (tiến trình khác dùng) -> để yên


def _cua_minh() -> set:
    """Thư mục _MEI của CHÍNH tiến trình này — không được xoá."""
    ra = set()
    mp = getattr(sys, "_MEIPASS", "")
    if mp:
        ra.add(str(Path(mp).resolve()).lower())
    return ra


def quet_temp(gio_min: float = 1.0) -> tuple[int, int]:
    """Dọn %TEMP%. Trả (số mục, số byte). `gio_min` nhân với tuổi từng mẫu."""
    goc = Path(os.environ.get("TEMP") or "/tmp")
    tru = _cua_minh()
    n = byte = 0
    for mau, la_dir, gio, _gc in RAC_TEMP:
        han = time.time() - max(gio, gio_min) * 3600
        try:
            ds = list(goc.glob(mau))
        except OSError:
            continue
        for p in ds:
            try:
                if la_dir is True and not p.is_dir():
                    continue
                if la_dir is False and p.is_dir():
                    continue
                if str(p.resolve()).lower() in tru:
                    continue
                if p.stat().st_mtime > han:      # còn mới -> có thể đang dùng
                    continue
            except OSError:
                continue
            b = _xoa(p)
            if b or not p.exists():
                n += 1
                byte += b
    return (n, byte)


def quet_data_dir(data_dir: Path) -> tuple[int, int]:
    """Dọn trong thư mục dữ liệu app: bản DB cũ + log quá hạn."""
    n = byte = 0
    # 1) bản DB do các lần cứu-hộ trước để lại: giữ 3 mới nhất
    try:
        cu = [p for p in data_dir.glob("studio_*.db")]
        cu += [p for p in data_dir.glob("studio.db.corrupt*")
               if not p.name.endswith(("-wal", "-shm"))]
        cu.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for p in cu[_GIU_BAN_DB:]:
            for hau in ("", "-wal", "-shm"):     # xoá kèm wal/shm mồ côi
                q = p.with_name(p.name + hau)
                if q.exists():
                    b = _xoa(q)
                    if b or not q.exists():
                        n += 1
                        byte += b
    except OSError:
        pass
    # 2) log cũ hơn 14 ngày
    han = time.time() - _GIU_NGAY_LOG * 86400
    try:
        for p in (data_dir / "logs").glob("pipeline_*.log"):
            if p.stat().st_mtime < han:
                b = _xoa(p)
                if b or not p.exists():
                    n += 1
                    byte += b
    except OSError:
        pass
    # 3) error.log phình -> giữ nửa cuối (vẫn đọc được lỗi gần đây)
    try:
        el = data_dir / "logs" / "error.log"
        if el.exists() and el.stat().st_size > _TRAN_ERROR_LOG:
            cu_size = el.stat().st_size
            noi_dung = el.read_bytes()[-_TRAN_ERROR_LOG // 2:]
            el.write_bytes(b"[... da cat bot phan cu ...]\n" + noi_dung)
            byte += cu_size - el.stat().st_size
            n += 1
    except OSError:
        pass
    return (n, byte)


def quet_tat(data_dir: Path | None = None, gio_min: float = 1.0) -> tuple[int, float]:
    """Dọn hết. Trả (số mục, số MB). KHÔNG bao giờ ném lỗi ra ngoài."""
    n = byte = 0
    # MẢNH `_seg_*` MỒ CÔI của lần chạy TRƯỚC — dọn NGAY, không đợi đủ 2 giờ.
    # Luật 2 giờ dưới đây là để tránh đụng lượt xuất ĐANG chạy; nay tên mảnh có
    # đóng dấu PID nên biết chắc chủ nó đã chết hay chưa (`don_seg_mo_coi`).
    # Máy anh Hùng tự cập nhật + tắt app giữa chừng liên tục, `os._exit` khiến
    # `finally` không chạy -> đợi 2 giờ là để rác nằm lại cả buổi.
    try:
        from app.core.ffmpeg_utils import don_seg_mo_coi
        a, b = don_seg_mo_coi()
        n += a
        byte += b
    except Exception:  # noqa: BLE001 - dọn rác không được làm app chết
        pass
    try:
        a, b = quet_temp(gio_min)
        n += a
        byte += b
    except Exception:  # noqa: BLE001 - dọn rác không được làm app chết
        pass
    if data_dir is not None:
        try:
            a, b = quet_data_dir(Path(data_dir))
            n += a
            byte += b
        except Exception:  # noqa: BLE001
            pass
    return (n, byte / 1048576.0)


def temp_rieng_cho_ytdlp(data_dir: Path) -> str:
    """Thư mục tạm RIÊNG cho yt-dlp con.

    yt-dlp bản đóng gói tự giải nén vào %TEMP%\\_MEIxxxx theo biến TEMP của
    TIẾN TRÌNH CON. Trỏ nó vào thư mục của mình -> rác nằm gọn 1 chỗ, lần mở
    sau xoá cả cây là sạch, không phải đoán tên _MEI của ai."""
    d = Path(data_dir) / "_ytdlp_temp"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ""
    return str(d)


def don_temp_ytdlp(data_dir: Path, gio: float = 2.0) -> tuple[int, int]:
    """Xoá cây tạm riêng của yt-dlp (mọi thứ cũ hơn `gio` giờ)."""
    d = Path(data_dir) / "_ytdlp_temp"
    if not d.is_dir():
        return (0, 0)
    han = time.time() - gio * 3600
    n = byte = 0
    try:
        for p in d.iterdir():
            try:
                if p.stat().st_mtime > han:
                    continue
            except OSError:
                continue
            b = _xoa(p)
            if b or not p.exists():
                n += 1
                byte += b
    except OSError:
        pass
    return (n, byte)
