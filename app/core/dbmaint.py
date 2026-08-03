# -*- coding: utf-8 -*-
"""BẢO DƯỠNG DB: dọn BẢN CHÉP LỜI cũ + nén file, KHÔNG làm mất việc của user.

VÌ SAO (đo thật 02/08/2026 trên DB máy anh Hùng):
    analysis.data  = 378 KB / video  ← 99% chỗ trong DB, và GIỮ MÃI MÃI
    clips.signals  = 0,4 KB / dòng
    jobs           = 1,0 KB / dòng
    pipeline_files = 0,1 KB / dòng
Với ~100 video/ngày: +37 MB/ngày -> ~1,1 GB/tháng -> ~13 GB/năm. DB càng phình
thì mọi truy vấn càng chậm, và đây đúng loại rủi ro làm studio.db VỠ khi ổ đầy.

BẢN CHÉP LỜI DÙNG LÀM GÌ (đọc code trước khi xoá — bài học 02/08):
    m1_highlight.py:2820  tr = get_analysis(video_id, "transcript")
                          words = tr["words"]        ← VẼ PHỤ ĐỀ lúc XUẤT clip
Nên xoá bừa = bấm "Xuất lại" clip cũ sẽ ra clip KHÔNG CÓ PHỤ ĐỀ.

=> ĐIỀU KIỆN AN TOÀN (đừng nới lỏng): chỉ dọn video mà
      (1) FILE GỐC KHÔNG CÒN trên đĩa  -> vốn đã KHÔNG thể xuất lại được nữa,
      (2) mọi clip của nó đã xuất/cất kho (không còn 'suggested' đang chờ), và
      (3) clip mới nhất đã quá `ngay` ngày.
   Video còn gốc, hoặc vừa làm, hoặc còn clip đang chờ -> GIỮ NGUYÊN.

KHÔNG BAO GIỜ chạm: projects (kênh/nhóm/mẫu-theo-kênh) · presets (mẫu) ·
clips (tiêu đề/đường dẫn file đã xuất) · pipeline_files (sổ chống trùng) ·
file .env (key) · clip .mp4 trên đĩa.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from app.database.db import db

#: Chỉ dọn loại nặng. 'scenes'/'faces'/'audio'/'hashtags' đều < 1 KB -> giữ,
#: vì chúng còn dùng để hiện thông tin video và không đáng để xoá.
_LOAI_NANG = ("transcript",)


def _thoi_diem(v) -> float | None:
    """Đổi giá trị `created_at` thành mốc thời gian. **None = KHÔNG ĐỌC ĐƯỢC.**

    LỖI THẬT bắt được ở cổng 20: cột `clips.created_at` khai kiểu TEXT, nên số
    ghi vào bị lưu thành chuỗi ('1785000000.0'); bản đầu của hàm này trả 0.0 khi
    không parse được, và `if t and t > han` coi 0.0 là "chưa biết" rồi ĐI XOÁ —
    tức không đọc được ngày là xoá luôn video vừa làm. Nay tách rõ: không đọc
    được -> None -> caller GIỮ LẠI."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v) or None
    s = str(v).strip()
    try:                                  # số ghi dưới dạng chuỗi
        return float(s) or None
    except ValueError:
        pass
    try:                                  # ISO '2026-08-02 10:00:00'
        import datetime as _dt
        return _dt.datetime.fromisoformat(s.replace("Z", "")).timestamp()
    except ValueError:
        return None


def _co_the_don(ngay: float) -> list:
    """Danh sách (video_id, byte) đủ điều kiện AN TOÀN để dọn chép lời."""
    han = time.time() - ngay * 86400
    try:
        rows = db.query(
            "SELECT v.id AS vid, v.src_path AS src, "
            "       SUM(LENGTH(COALESCE(a.data,''))) AS b, "
            "       MAX(COALESCE(c.created_at,0)) AS moi_nhat, "
            "       SUM(CASE WHEN c.status='suggested' THEN 1 ELSE 0 END) AS cho "
            "FROM videos v "
            "JOIN analysis a ON a.video_id = v.id AND a.kind IN "
            f"      ({','.join('?' * len(_LOAI_NANG))}) "
            "LEFT JOIN clips c ON c.video_id = v.id "
            "GROUP BY v.id", tuple(_LOAI_NANG))
    except Exception:  # noqa: BLE001 - DB vỡ/thiếu bảng -> bỏ qua, không chặn app
        return []
    ra = []
    for r in rows:
        try:
            if int(r["cho"] or 0) > 0:
                continue                      # còn clip CHỜ xuất -> giữ
            src = (r["src"] or "").strip()
            if src and os.path.exists(src):
                continue                      # CÒN GỐC -> xuất lại được -> giữ
            t = _thoi_diem(r["moi_nhat"])
            if t is None:
                continue     # KHÔNG ĐỌC ĐƯỢC NGÀY -> GIỮ (an toàn)
            if t > han:
                continue     # vừa làm -> giữ
            ra.append((int(r["vid"]), int(r["b"] or 0)))
        except Exception:  # noqa: BLE001
            continue
    return ra


def sao_luu_db() -> str:
    """COPY studio.db -> studio_backup_truoc_don_<ts>.db (đường lùi). '' nếu lỗi."""
    p = str(getattr(db, "path", "") or "")
    if not p or p == ":memory:" or not os.path.exists(p):
        return ""
    dst = Path(p).with_name(f"studio_backup_truoc_don_{int(time.time())}.db")
    try:
        db.gap_wal()                     # gấp WAL trước để bản sao TỰ ĐỦ
        shutil.copy2(p, dst)
        return str(dst)
    except OSError:
        return ""


def don_chep_loi_cu(ngay: float = 30.0, sao_luu: bool = True) -> tuple[int, float]:
    """Dọn bản chép lời của video ĐÃ MẤT GỐC + xong quá `ngay` ngày.
    Trả (số video, số MB). KHÔNG BAO GIỜ ném lỗi ra ngoài."""
    try:
        ds = _co_the_don(ngay)
        if not ds:
            return (0, 0.0)
        if sao_luu:
            sao_luu_db()                 # có đường lùi trước khi xoá lần đầu
        n = byte = 0
        for vid, b in ds:
            try:
                db.execute(
                    "DELETE FROM analysis WHERE video_id=? AND kind IN "
                    f"({','.join('?' * len(_LOAI_NANG))})",
                    (vid, *_LOAI_NANG))
                n += 1
                byte += b
            except Exception:  # noqa: BLE001 - 1 video lỗi không chặn cả loạt
                continue
        return (n, byte / 1048576.0)
    except Exception:  # noqa: BLE001
        return (0, 0.0)


def nen_db() -> float:
    """VACUUM: dồn chỗ trống trả lại ổ đĩa. Trả số MB giảm được (0 nếu lỗi).

    An toàn: VACUUM không đổi dữ liệu. Cần chỗ trống tạm ~bằng cỡ DB, và không
    chạy được khi đang có giao dịch dở -> lỗi thì bỏ qua, lần sau làm."""
    p = str(getattr(db, "path", "") or "")
    if not p or p == ":memory:" or not os.path.exists(p):
        return 0.0
    try:
        truoc = os.path.getsize(p)
        db.gap_wal()
        db.conn().execute("VACUUM")
        return max(0.0, (truoc - os.path.getsize(p)) / 1048576.0)
    except Exception:  # noqa: BLE001
        return 0.0


def bao_duong(ngay: float = 30.0) -> str:
    """Chạy 1 lượt bảo dưỡng (gọi ở luồng nền lúc mở app). Trả 1 dòng để log."""
    n, mb = don_chep_loi_cu(ngay)
    gon = nen_db() if n else 0.0
    if not n and not gon:
        return ""
    return (f"[bảo dưỡng DB] dọn chép lời {n} video ({mb:.0f} MB) · "
            f"nén DB giảm {gon:.0f} MB")
