from __future__ import annotations

import queue
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from spry.db.column_type import ColumnType
from spry.db.url import DatabaseUrl


@dataclass(slots=True)
class InsertResult:
    sql: str
    params: list[str]
    use_returning: bool = False


class DatabaseBackend(ABC):

    @abstractmethod
    def connect(self, database_url: DatabaseUrl) -> Any:
        ...

    def set_foreign_keys(self, connection: Any, enabled: bool) -> None:
        pass

    @abstractmethod
    def quote_identifier(self, name: str) -> str:
        ...

    def get_last_insert_id(self, cursor: Any, pk_field: Any) -> Any:
        return cursor.lastrowid

    def compile_insert(
        self, table: str, columns: list[str], pk_field: Any | None = None
    ) -> InsertResult:
        quoted_cols = [self.quote_identifier(c) for c in columns]
        placeholders = self._placeholders(len(columns))
        sql = f"INSERT INTO {self.quote_identifier(table)} ({', '.join(quoted_cols)}) VALUES ({', '.join(placeholders)})"
        return InsertResult(sql=sql, params=placeholders, use_returning=False)

    def compile_limit(self, sql: str, limit: int) -> str:
        return f"{sql} LIMIT {limit}"

    def quote_table(self, table: str) -> str:
        return self.quote_identifier(table)

    @abstractmethod
    def map_type(self, python_type: Any) -> ColumnType:
        ...

    def batch_execute(self, connection: Any, statements: list[str]) -> None:
        for stmt in statements:
            if stmt.strip():
                connection.execute(stmt)

    @abstractmethod
    def create_migration_table_ddl(self, history_table: str) -> str:
        ...

    @property
    def param_style(self) -> str:
        return "?"

    @property
    def supports_returning(self) -> bool:
        return False

    def _placeholders(self, count: int) -> list[str]:
        return ["?"] * count

    def get_identity_keyword(self) -> str:
        return ""

    def row_to_dict(self, row: Any, field_names: list[str]) -> dict[str, Any]:
        return {name: row[name] for name in field_names}

    def fetchall_dicts(self, cursor: Any) -> list[dict[str, Any]]:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def fetchone_dict(self, cursor: Any) -> dict[str, Any] | None:
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(zip(columns, row))


class ConnectionPool:
    def __init__(self, backend: DatabaseBackend, database_url: DatabaseUrl, min_size: int = 1, max_size: int = 10, timeout: float = 5.0) -> None:
        self._backend = backend
        self._database_url = database_url
        self._max_size = max_size
        self._timeout = timeout
        self._pool: queue.Queue[Any] = queue.Queue()
        self._size = 0
        self._lock = threading.Lock()
        for _ in range(min_size):
            self._pool.put(self._create_connection())
            self._size += 1

    def _create_connection(self) -> Any:
        conn = self._backend.connect(self._database_url)
        self._backend.set_foreign_keys(conn, True)
        return conn

    def acquire(self) -> Any:
        try:
            return self._pool.get(block=True, timeout=self._timeout)
        except queue.Empty:
            with self._lock:
                if self._size < self._max_size:
                    self._size += 1
                    return self._create_connection()
            raise RuntimeError(f"Connection pool exhausted (max={self._max_size})")

    def release(self, conn: Any) -> None:
        self._pool.put(conn)

    def close_all(self) -> None:
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            try:
                conn.close()
            except Exception:
                pass
