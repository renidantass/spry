from __future__ import annotations

from datetime import date, datetime
from typing import Any

from spry.db.backend import DatabaseBackend, InsertResult
from spry.db.column_type import ColumnType


class SqlServerBackend(DatabaseBackend):

    def connect(self, database_url: Any) -> Any:
        import pyodbc

        host = database_url.host or "localhost"
        port = database_url.port or 1433
        server = f"{host},{port}"
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database_url.database};"
        )
        if database_url.username:
            conn_str += f"UID={database_url.username};"
        if database_url.password:
            conn_str += f"PWD={database_url.password};"
        else:
            conn_str += "Trusted_Connection=yes;"
        return pyodbc.connect(conn_str)

    def set_foreign_keys(self, connection: Any, enabled: bool) -> None:
        with connection.cursor() as cur:
            state = "CHECK" if enabled else "NOCHECK"
            cur.execute(f"ALTER TABLE ALL {state} CONSTRAINT ALL")

    def quote_identifier(self, name: str) -> str:
        return f"[{name}]"

    def map_type(self, python_type: Any) -> ColumnType:
        if python_type is int:
            return ColumnType("INT", auto_increment_keyword="IDENTITY(1,1)")
        if python_type is bool:
            return ColumnType("BIT")
        if python_type is float:
            return ColumnType("FLOAT")
        if python_type is datetime:
            return ColumnType("DATETIME2")
        if python_type is date:
            return ColumnType("DATE")
        return ColumnType("NVARCHAR(MAX)")

    def compile_insert(
        self, table: str, columns: list[str], pk_field: Any | None = None
    ) -> InsertResult:
        quoted_cols = [self.quote_identifier(c) for c in columns]
        placeholders = self._placeholders(len(columns))
        sql = f"INSERT INTO {self.quote_identifier(table)} ({', '.join(quoted_cols)}) OUTPUT INSERTED.{self.quote_identifier(pk_field.name) if pk_field else ''} VALUES ({', '.join(placeholders)})"
        if pk_field:
            return InsertResult(sql=sql, params=placeholders, use_returning=True)
        return InsertResult(
            sql=f"INSERT INTO {self.quote_identifier(table)} ({', '.join(quoted_cols)}) VALUES ({', '.join(placeholders)})",
            params=placeholders,
            use_returning=False,
        )

    def get_last_insert_id(self, cursor: Any, pk_field: Any) -> Any:
        row = cursor.fetchone()
        return row[0] if row else None

    def compile_limit(self, sql: str, limit: int) -> str:
        order_match = __import__("re").search(r"ORDER\s+BY\s+.+", sql, __import__("re").IGNORECASE)
        if order_match:
            return f"{sql} OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        return f"{sql} ORDER BY (SELECT NULL) OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"

    def create_migration_table_ddl(self, history_table: str) -> str:
        return (
            f"CREATE TABLE {self.quote_identifier(history_table)} "
            f"(id NVARCHAR(255) PRIMARY KEY, applied_at NVARCHAR(50) NOT NULL)"
        )

    @property
    def param_style(self) -> str:
        return "?"

    def batch_execute(self, connection: Any, statements: list[str]) -> None:
        with connection.cursor() as cur:
            for stmt in statements:
                if stmt.strip():
                    cur.execute(stmt)
        connection.commit()
