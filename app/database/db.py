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
        """Mở/ tạo DB. PHẢI luôn thành công để app mở được — nếu file DB hỏng
        hoặc ổ lỗi thì lần lượt: dọn file hỏng -> đổi sang tên file MỚI ->
        cuối cùng DB tạm trong RAM (app vẫn mở, chỉ không lưu qua phiên)."""
        try:
            self._apply_schema()
            return
        except Exception as e:  # noqa: BLE001 - malformed / I/O error / notadb...
            if not self._is_corrupt_err(e):
                raise      # lỗi lạ (vd thiếu quyền ghi cả thư mục) -> ném thật

        # (1) Dọn sạch file hỏng TẠI CHỖ rồi thử lại VÀI LẦN (đợi chút giữa các
        # lần): 'disk I/O'/khóa file thường do wal/shm mồ côi hoặc AV/OneDrive
        # giữ handle tạm — chờ 1 nhịp là mở lại được. Giữ NGUYÊN studio.db là
        # đáng tin nhất (subprocess luôn tìm đúng file), nên cố ở đây trước khi
        # nhảy sang path mới.
        for attempt in range(4):
            self._wipe_db_files(self.path)
            try:
                self._reset_conn()
                self._apply_schema()
                return
            except Exception:  # noqa: BLE001
                if attempt < 3:
                    time.sleep(0.3 * (attempt + 1))

        # (2) Cùng chỗ vẫn lỗi (file khóa/ổ lỗi/OneDrive) -> DÙNG TÊN FILE MỚI.
        # publish_path() sẽ set BQ_DB_PATH = file mới -> subprocess mở đúng file.
        newp = str(Path(self.path).with_name(f"studio_{int(time.time())}.db"))
        try:
            self._wipe_db_files(newp)
            self.path = newp
            self._reset_conn()
            self._apply_schema()
            return
        except Exception:  # noqa: BLE001
            pass

        # (3) Bó tay với đĩa -> DB trong RAM: app VẪN mở, chạy được trong phiên
        # (kênh/clip phiên này không lưu lại sau khi tắt — nhưng còn hơn crash).
        # CẢNH BÁO: tiến trình con (phân tích) KHÔNG chia sẻ được RAM-DB -> sẽ
        # không thấy video. UI đọc self.in_memory để báo user rõ.
        self.path = ":memory:"
        self.in_memory = True
        self._reset_conn()
        self._apply_schema()

    @staticmethod
    def _is_corrupt_err(e: Exception) -> bool:
        m = str(e).lower()
        return isinstance(e, sqlite3.Error) and any(
            s in m for s in ("malformed", "not a database", "disk i/o",
                             "disk image", "file is encrypted", "corrupt"))

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
