from __future__ import annotations

from datetime import date, datetime
from typing import Any

from spry.db.backend import DatabaseBackend, InsertResult
from spry.db.column_type import ColumnType


class PostgresBackend(DatabaseBackend):

    def connect(self, database_url: Any) -> Any:
        import psycopg2

        params = {
            "host": database_url.host or "localhost",
            "port": database_url.port or 5432,
            "dbname": database_url.database,
        }
        if database_url.username:
            params["user"] = database_url.username
        if database_url.password:
            params["password"] = database_url.password
        return psycopg2.connect(**params)

    def set_foreign_keys(self, connection: Any, enabled: bool) -> None:
        with connection.cursor() as cur:
            cur.execute("SET session_replication_role = 'replica';" if not enabled else "SET session_replication_role = 'origin';")
        connection.commit()

    def quote_identifier(self, name: str) -> str:
        return f'"{name}"'

    def map_type(self, python_type: Any) -> ColumnType:
        if python_type is int:
            return ColumnType("INTEGER")
        if python_type is bool:
            return ColumnType("BOOLEAN")
        if python_type is float:
            return ColumnType("DOUBLE PRECISION")
        if python_type is datetime:
            return ColumnType("TIMESTAMP")
        if python_type is date:
            return ColumnType("DATE")
        return ColumnType("TEXT")

    def compile_insert(
        self, table: str, columns: list[str], pk_field: Any | None = None
    ) -> InsertResult:
        quoted_cols = [self.quote_identifier(c) for c in columns]
        placeholders = self._placeholders(len(columns))
        sql = f"INSERT INTO {self.quote_identifier(table)} ({', '.join(quoted_cols)}) VALUES ({', '.join(placeholders)})"
        if pk_field is not None:
            sql += f" RETURNING {self.quote_identifier(pk_field.name)}"
            return InsertResult(sql=sql, params=placeholders, use_returning=True)
        return InsertResult(sql=sql, params=placeholders, use_returning=False)

    def get_last_insert_id(self, cursor: Any, pk_field: Any) -> Any:
        return cursor.fetchone()[0]

    def compile_limit(self, sql: str, limit: int) -> str:
        return f"{sql} LIMIT {limit}"

    def create_migration_table_ddl(self, history_table: str) -> str:
        return (
            f"CREATE TABLE IF NOT EXISTS {self.quote_identifier(history_table)} "
            f"(id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )

    @property
    def param_style(self) -> str:
        return "%s"

    @property
    def supports_returning(self) -> bool:
        return True

    def _placeholders(self, count: int) -> list[str]:
        return ["%s"] * count

    def batch_execute(self, connection: Any, statements: list[str]) -> None:
        with connection.cursor() as cur:
            for stmt in statements:
                if stmt.strip():
                    cur.execute(stmt)
        connection.commit()
