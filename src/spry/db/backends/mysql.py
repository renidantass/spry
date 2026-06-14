from __future__ import annotations

from datetime import date, datetime
from typing import Any

from spry.db.backend import DatabaseBackend, InsertResult
from spry.db.column_type import ColumnType


class MySqlBackend(DatabaseBackend):

    def connect(self, database_url: Any) -> Any:
        import pymysql

        params = {
            "host": database_url.host or "localhost",
            "port": database_url.port or 3306,
            "database": database_url.database,
        }
        if database_url.username:
            params["user"] = database_url.username
        if database_url.password:
            params["password"] = database_url.password
        return pymysql.connect(**params)

    def set_foreign_keys(self, connection: Any, enabled: bool) -> None:
        with connection.cursor() as cur:
            cur.execute(f"SET foreign_key_checks = {1 if enabled else 0}")

    def quote_identifier(self, name: str) -> str:
        return f"`{name}`"

    def map_type(self, python_type: Any) -> ColumnType:
        if python_type is int:
            return ColumnType("INT", auto_increment_keyword="AUTO_INCREMENT")
        if python_type is bool:
            return ColumnType("TINYINT(1)")
        if python_type is float:
            return ColumnType("DOUBLE")
        if python_type is datetime:
            return ColumnType("DATETIME(6)")
        if python_type is date:
            return ColumnType("DATE")
        return ColumnType("VARCHAR(255)")

    def create_migration_table_ddl(self, history_table: str) -> str:
        return (
            f"CREATE TABLE IF NOT EXISTS {self.quote_identifier(history_table)} "
            f"(id VARCHAR(255) PRIMARY KEY, applied_at TEXT NOT NULL)"
        )

    @property
    def param_style(self) -> str:
        return "%s"

    def _placeholders(self, count: int) -> list[str]:
        return ["%s"] * count

    def compile_insert(
        self, table: str, columns: list[str], pk_field: Any | None = None
    ) -> InsertResult:
        quoted_cols = [self.quote_identifier(c) for c in columns]
        ph = self._placeholders(len(columns))
        sql = f"INSERT INTO {self.quote_identifier(table)} ({', '.join(quoted_cols)}) VALUES ({', '.join(ph)})"
        return InsertResult(sql=sql, params=ph, use_returning=False)

    def batch_execute(self, connection: Any, statements: list[str]) -> None:
        with connection.cursor() as cur:
            for stmt in statements:
                if stmt.strip():
                    cur.execute(stmt)
        connection.commit()
