"""
Lớp truy cập SQLite dùng chung, thread-safe.

Queue chạy nhiều worker (thread) => mỗi thread mở connection riêng
(SQLite không cho dùng chung 1 connection giữa nhiều thread). WAL mode
cho phép nhiều reader + 1 writer cùng lúc.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Optional

from config import DB_PATH

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = str(path)
        self._local = threading.local()
        self.init_schema()

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
        try:
            self._apply_schema()
        except sqlite3.DatabaseError as e:
            # FILE DB HỎNG ("database disk image is malformed" — do tắt máy/
            # mất điện lúc đang ghi, ổ lỗi...) -> app crash ngay khi mở, KHÔNG
            # vào được. Cứu: đóng connection, ĐỔI TÊN file hỏng thành .corrupt
            # (giữ lại phòng khi cứu tay được) rồi tạo DB MỚI trống -> app mở
            # lại bình thường (mất lịch sử/kênh cũ, nhưng còn hơn không mở nổi).
            if "malformed" not in str(e).lower() and "not a database" \
                    not in str(e).lower():
                raise
            self._quarantine_corrupt()
            self._apply_schema()

    def _apply_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn().executescript(sql)
        self.conn().commit()
        self._migrate()

    def _quarantine_corrupt(self) -> None:
        """Đóng connection + đổi tên mọi file DB hỏng (db + -wal + -shm) sang
        .corrupt để tạo lại DB mới sạch."""
        import time as _t
        try:
            c = getattr(self._local, "conn", None)
            if c is not None:
                c.close()
        except Exception:  # noqa: BLE001
            pass
        self._local = threading.local()
        stamp = int(_t.time())
        for suffix in ("", "-wal", "-shm"):
            f = Path(self.path + suffix)
            if f.exists():
                try:
                    f.rename(f.with_name(f.name + f".corrupt{stamp}"))
                except OSError:
                    try:
                        f.unlink()          # đổi tên không được -> xóa để mở lại
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
