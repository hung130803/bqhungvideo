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
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode = WAL;")
            c.execute("PRAGMA foreign_keys = ON;")
            c.execute("PRAGMA busy_timeout = 30000;")
            self._local.conn = c
        return c

    def init_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn().executescript(sql)
        self.conn().commit()
        self._migrate()

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
