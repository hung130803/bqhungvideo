"""
Lớp truy cập SQLite dùng chung, thread-safe.

Queue chạy nhiều worker (thread) => mỗi thread mở connection riêng
(SQLite không cho dùng chung 1 connection giữa nhiều thread). WAL mode
cho phép nhiều reader + 1 writer cùng lúc.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Optional

from config import DB_PATH

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = str(path)
        self._local = threading.local()
        # True nếu phải rơi vào DB tạm trong RAM (không lưu qua phiên + TIẾN TRÌNH
        # CON không chia sẻ được -> phân tích sẽ fail). UI dùng cờ này để cảnh báo.
        self.in_memory = False
        self.init_schema()
        # Chốt path THỰC vào biến môi trường để MỌI tiến trình con (phân tích)
        # spawn sau (jobs.py truyền env=dict(os.environ)) mở ĐÚNG file này —
        # kể cả khi recovery vừa đổi path sang studio_<ts>.db.
        self._publish_path()

    def _publish_path(self) -> None:
        """Đăng path thực ra BQ_DB_PATH cho subprocess kế thừa (trừ khi RAM)."""
        if self.path and self.path != ":memory:":
            os.environ["BQ_DB_PATH"] = self.path
        else:                     # RAM: KHÔNG chia sẻ được -> xoá để subprocess
            os.environ.pop("BQ_DB_PATH", None)  # không mở nhầm file rỗng

    # ---- connection mỗi-thread ----
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            try:
                c.row_factory = sqlite3.Row
                c.execute("PRAGMA journal_mode = WAL;")
                c.execute("PRAGMA foreign_keys = ON;")
                c.execute("PRAGMA busy_timeout = 30000;")
            except Exception:      # DB hỏng -> ĐÓNG ngay (nhả file để quarantine
                c.close()          # đổi tên/xóa được), rồi ném lên cho init_schema
                raise
            self._local.conn = c
        return c

    def init_schema(self) -> None:
        """Mở/ tạo DB. PHẢI luôn thành công để app mở được, NHƯNG TUYỆT ĐỐI
        không được hủy dữ liệu người dùng vì một lỗi TẠM THỜI.

        Phân loại lỗi rất quan trọng (đây là nguyên nhân MẤT KÊNH/MẪU sau mỗi
        lần cập nhật của bản cũ):
          - HỎNG THẬT (malformed / not a database / encrypted / image is
            malformed): file thực sự không đọc được -> mới được phép cách ly.
            Nhưng KHÔNG xóa: SAO LƯU (copy) studio.db -> studio_backup_<ts>.db
            trước, rồi tạo DB mới. Dữ liệu cũ vẫn cứu tay được.
          - TẠM THỜI (disk I/O error / database is locked / unable to open /
            timeout...): ngay sau cập nhật thường do AV/OneDrive đang quét file
            vừa swap, wal/shm mồ côi, hoặc tiến trình app cũ chưa nhả handle.
            KHÔNG xóa gì cả -> RETRY (đóng connection, đợi tăng dần). Nếu retry
            hết vẫn lỗi -> GIỮ NGUYÊN studio.db, rơi vào DB RAM cho phiên này
            (lần mở sau đĩa rảnh sẽ đọc lại được data). Không bao giờ wipe.
        """
        try:
            self._apply_schema()
            return
        except Exception as e:  # noqa: BLE001
            first_err = e
            if self._is_true_corrupt(e):
                self._recover_true_corrupt()
                return
            if not self._is_transient_err(e):
                raise      # lỗi lạ (vd thiếu quyền ghi cả thư mục) -> ném thật

        # ---- LỖI TẠM THỜI: RETRY, KHÔNG ĐỘNG VÀO FILE ----
        # Đợi tăng dần tới ~vài giây tổng cộng (0.3+0.6+...+1.8 ≈ 6.3s) cho
        # AV/OneDrive/tiến trình cũ nhả file. Chỉ đóng connection, KHÔNG xóa.
        for attempt in range(6):
            time.sleep(0.3 * (attempt + 1))
            try:
                self._reset_conn()
                self._apply_schema()
                return
            except Exception as e:  # noqa: BLE001
                first_err = e
                if self._is_true_corrupt(e):   # hoá ra hỏng thật -> sao lưu + tạo mới
                    self._recover_true_corrupt()
                    return
                if not self._is_transient_err(e):
                    raise

        # ---- Retry hết vẫn lỗi tạm thời: GIỮ NGUYÊN studio.db ----
        # KHÔNG wipe, KHÔNG đổi tên file. Rơi vào DB RAM để app mở được phiên
        # này; lần khởi động sau khi đĩa rảnh, studio.db (còn nguyên data) sẽ
        # đọc lại được. UI đọc self.in_memory để cảnh báo user.
        self._fallback_memory()

    def _recover_true_corrupt(self) -> None:
        """File studio.db HỎNG THẬT: sao lưu (COPY) rồi tạo DB mới TẠI CHỖ.
        Không bao giờ xóa vĩnh viễn — bản backup để user/mình cứu tay."""
        self._backup_db_file(self.path)
        # Sau khi đã có backup an toàn, dọn file hỏng tại chỗ để tạo mới.
        # (backup là COPY nên xóa bản gốc hỏng ở đây không mất dữ liệu.)
        self._wipe_db_files(self.path)
        try:
            self._reset_conn()
            self._apply_schema()
            return
        except Exception:  # noqa: BLE001
            pass
        # Cùng chỗ tạo mới vẫn lỗi (đĩa/khoá) -> DB RAM cho phiên này.
        self._fallback_memory()

    def _fallback_memory(self) -> None:
        """DB trong RAM: app VẪN mở, chạy được trong phiên (không lưu qua phiên).
        CẢNH BÁO: tiến trình con (phân tích) KHÔNG chia sẻ được RAM-DB."""
        self.path = ":memory:"
        self.in_memory = True
        self._reset_conn()
        self._apply_schema()

    def _backup_db_file(self, path: str) -> Optional[str]:
        """COPY studio.db -> studio_backup_<ts>.db (không move/delete). Trả path
        backup, hoặc None nếu không có gì để sao lưu / copy thất bại."""
        import shutil as _sh
        src = Path(path)
        if not src.exists() or src.stat().st_size == 0:
            return None
        dst = src.with_name(f"studio_backup_{int(time.time())}.db")
        try:
            self._reset_conn()          # nhả handle trước khi copy
            _sh.copy2(src, dst)
        except OSError:
            return None
        # GIỚI HẠN: giữ 3 bản backup mới nhất (mỗi bản = cả cỡ studio.db;
        # DB hỏng lặp lại nhiều lần sẽ phình đĩa vô hạn nếu không chặn).
        try:
            baks = sorted(src.parent.glob("studio_backup_*.db"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            for f in baks[3:]:
                f.unlink()
        except OSError:
            pass
        return str(dst)

    @staticmethod
    def _is_true_corrupt(e: Exception) -> bool:
        """CHỈ những lỗi cho thấy nội dung file thật sự hỏng — mới được cách ly.
        KHÔNG gồm 'disk i/o error' / 'locked' / 'unable to open' (tạm thời)."""
        m = str(e).lower()
        return isinstance(e, sqlite3.Error) and any(
            s in m for s in ("malformed", "not a database",
                             "file is encrypted", "image is malformed"))

    @staticmethod
    def _is_transient_err(e: Exception) -> bool:
        """Lỗi có thể TỰ HẾT khi thử lại — TUYỆT ĐỐI không xóa dữ liệu."""
        m = str(e).lower()
        if not isinstance(e, sqlite3.Error):
            return False
        return any(s in m for s in (
            "disk i/o", "database is locked", "unable to open",
            "locked", "busy", "timeout", "readonly", "read-only",
            "cannot open", "permission"))

    def _reset_conn(self) -> None:
        try:
            c = getattr(self._local, "conn", None)
            if c is not None:
                c.close()
        except Exception:  # noqa: BLE001
            pass
        self._local = threading.local()

    def _apply_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn().executescript(sql)
        self.conn().commit()
        self._migrate()

    def _wipe_db_files(self, path: str) -> None:
        """Đóng connection + XÓA (đổi tên nếu xóa không được) db + wal + shm ở
        `path`. Xóa hẳn chắc chắn hơn đổi tên khi mở lại (không còn wal/shm
        mồ côi gây 'disk I/O error')."""
        import time as _t
        self._reset_conn()
        stamp = int(_t.time())
        for suffix in ("-wal", "-shm", ""):        # xóa wal/shm TRƯỚC, db sau
            f = Path(path + suffix)
            if not f.exists():
                continue
            try:
                f.unlink()
            except OSError:
                try:                               # khóa -> đổi tên né sang bên
                    f.rename(f.with_name(f.name + f".corrupt{stamp}"))
                except OSError:
                    pass

    def _migrate(self) -> None:
        """Thêm cột mới cho DB cũ (không làm mất dữ liệu)."""
        try:
            cols = [r[1] for r in
                    self.conn().execute("PRAGMA table_info(projects)").fetchall()]
            if "export_dir" not in cols:   # thư mục lưu clip của kênh (user chọn)
                self.conn().execute("ALTER TABLE projects ADD COLUMN export_dir TEXT")
                self.conn().commit()
            if "grp" not in cols:   # NHÓM kênh (quốc gia...); '' = chưa phân nhóm
                self.conn().execute(
                    "ALTER TABLE projects ADD COLUMN grp TEXT NOT NULL DEFAULT ''")
                self.conn().commit()
            # HOẠT ĐỘNG GẦN NHẤT ghi thẳng vào kênh/video (KHÔNG suy ra từ bảng
            # jobs nữa) — 'Xóa lịch sử' xoá job done thì thời điểm 'xong gần
            # nhất' vẫn còn, không bị reset sang ngày hôm sau.
            vcols = [r[1] for r in
                     self.conn().execute("PRAGMA table_info(videos)").fetchall()]
            need_backfill = False
            for tbl, tcols in (("projects", cols), ("videos", vcols)):
                if "last_done_at" not in tcols:
                    self.conn().execute(
                        f"ALTER TABLE {tbl} ADD COLUMN last_done_at TEXT")
                    self.conn().execute(
                        f"ALTER TABLE {tbl} ADD COLUMN last_done_type TEXT")
                    self.conn().commit()
                    need_backfill = True
            if need_backfill:      # 1 LẦN: điền từ job done sẵn có (giữ lịch sử)
                self.conn().execute(
                    "UPDATE videos SET "
                    "last_done_at=(SELECT MAX(finished_at) FROM jobs j "
                    "  WHERE j.video_id=videos.id AND j.status='done' "
                    "  AND j.finished_at IS NOT NULL), "
                    "last_done_type=(SELECT j.type FROM jobs j "
                    "  WHERE j.video_id=videos.id AND j.status='done' "
                    "  AND j.finished_at IS NOT NULL "
                    "  ORDER BY j.finished_at DESC LIMIT 1) "
                    "WHERE EXISTS (SELECT 1 FROM jobs j WHERE j.video_id=videos.id "
                    "  AND j.status='done' AND j.finished_at IS NOT NULL)")
                self.conn().execute(
                    "UPDATE projects SET "
                    "last_done_at=(SELECT MAX(finished_at) FROM jobs j "
                    "  WHERE j.project_id=projects.id AND j.status='done' "
                    "  AND j.finished_at IS NOT NULL), "
                    "last_done_type=(SELECT j.type FROM jobs j "
                    "  WHERE j.project_id=projects.id AND j.status='done' "
                    "  AND j.finished_at IS NOT NULL "
                    "  ORDER BY j.finished_at DESC LIMIT 1) "
                    "WHERE EXISTS (SELECT 1 FROM jobs j "
                    "  WHERE j.project_id=projects.id AND j.status='done' "
                    "  AND j.finished_at IS NOT NULL)")
                self.conn().commit()
        except Exception:  # noqa: BLE001
            pass

    # ---- helper cơ bản ----
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn().execute(sql, tuple(params))
        self.conn().commit()
        return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self.conn().execute(sql, tuple(params)).fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        return self.conn().execute(sql, tuple(params)).fetchone()

    def insert(self, sql: str, params: Iterable[Any] = ()) -> int:
        cur = self.execute(sql, params)
        return int(cur.lastrowid)

    # ---- tiện ích JSON ----
    @staticmethod
    def dumps(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def loads(text: Optional[str], default: Any = None) -> Any:
        if not text:
            return default
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return default


# Instance dùng chung toàn app
db = Database()
