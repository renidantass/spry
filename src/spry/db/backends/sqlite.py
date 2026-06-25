from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from spry.db.backend import DatabaseBackend
from spry.db.column_type import ColumnType


class SqliteBackend(DatabaseBackend):

    def connect(self, database_url: Any) -> sqlite3.Connection:
        conn = sqlite3.connect(database_url.database)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def set_foreign_keys(self, connection: sqlite3.Connection, enabled: bool) -> None:
        connection.execute(f"PRAGMA foreign_keys = {'ON' if enabled else 'OFF'}")

    def quote_identifier(self, name: str) -> str:
        return name

    def map_type(self, python_type: Any) -> ColumnType:
        if python_type in {int, bool}:
            return ColumnType("INTEGER", auto_increment_keyword="AUTOINCREMENT")
        if python_type is float:
            return ColumnType("REAL")
        if python_type is datetime:
            return ColumnType("TEXT")
        if python_type is date:
            return ColumnType("TEXT")
        return ColumnType("TEXT")

    def create_migration_table_ddl(self, history_table: str) -> str:
        return (
            f"CREATE TABLE IF NOT EXISTS {history_table} "
            f"(id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )

    @property
    def supports_returning(self) -> bool:
        return False

    def get_identity_keyword(self) -> str:
        return "AUTOINCREMENT"

    def batch_execute(self, connection: sqlite3.Connection, statements: list[str]) -> None:
        script = ";\n".join(statements)
        if script.strip():
            connection.executescript(script)

    def row_to_dict(self, row: sqlite3.Row, field_names: list[str]) -> dict[str, Any]:
        return dict(row)

    def fetchall_dicts(self, cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
        return [dict(row) for row in cursor.fetchall()]

    def fetchone_dict(self, cursor: sqlite3.Cursor) -> dict[str, Any] | None:
        row = cursor.fetchone()
        return None if row is None else dict(row)
