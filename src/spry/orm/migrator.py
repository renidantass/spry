from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spry.db import get_backend, parse_database_url
from spry.db.backend import DatabaseBackend
from spry.orm.context import DbContext
from spry.orm.metadata import slugify, to_table_name

logger = logging.getLogger("spry.orm")


def _in_transaction(connection: Any, statements: list[str]) -> None:
    """Run statements + caller-provided follow-ups as a single transaction.
    The caller is expected to append history-table writes to `statements`.
    """
    connection.execute("BEGIN")
    try:
        for stmt in statements:
            if stmt.strip():
                connection.execute(stmt)
        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            logger.debug("Rollback failed", exc_info=True)
        raise


class DatabaseMigrator:
    HISTORY_TABLE = "__spry_migrations"

    @classmethod
    def create_migration(cls, context_type: type[DbContext], name: str, output_dir: str | Path) -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        context = context_type(":memory:")
        try:
            sql = ";\n\n".join(context.schema_sql()) + ";\n"
        finally:
            context.close()

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        file_name = f"{stamp}_{slugify(name)}.sql"
        destination = output_path / file_name
        destination.write_text(sql, encoding="utf-8")

        down_sql = cls._generate_down_sql(context_type)
        if down_sql:
            down_file_name = f"{stamp}_{slugify(name)}_down.sql"
            down_destination = output_path / down_file_name
            down_destination.write_text(down_sql, encoding="utf-8")
        return destination

    @classmethod
    def _generate_down_sql(cls, context_type: type[DbContext]) -> str:
        context = context_type(":memory:")
        try:
            statements = [f"DROP TABLE IF EXISTS {model.table_name};" for model in context._models.values()]
            return "\n".join(statements) + "\n"
        finally:
            context.close()

    @classmethod
    def rollback_migration(cls, database_url: str, migrations_dir: str | Path, name: str | None = None) -> list[str]:
        directory = Path(migrations_dir)
        parsed = parse_database_url(database_url)
        backend = get_backend(database_url)
        connection = backend.connect(parsed)
        try:
            ddl = backend.create_migration_table_ddl(cls.HISTORY_TABLE)
            connection.execute(ddl)

            cursor = connection.execute(
                f"SELECT id FROM {backend.quote_identifier(cls.HISTORY_TABLE)} ORDER BY id DESC LIMIT 1"
            )
            row = backend.fetchone_dict(cursor)
            if row is None:
                logger.info("No migrations to rollback")
                return []

            last_applied = row["id"]
            down_file = directory / last_applied.replace(".sql", "_down.sql")
            if not down_file.exists():
                raise FileNotFoundError(f"Rollback file not found: {down_file}")

            script = down_file.read_text(encoding="utf-8")
            down_statements = [s.strip() for s in script.replace("\r\n", "\n").split(";") if s.strip()]
            ph = backend.param_style
            delete_history = (
                f"DELETE FROM {backend.quote_identifier(cls.HISTORY_TABLE)} WHERE id = {ph}"
            )

            def _run_with_history() -> None:
                DatabaseBackend.batch_execute(connection, down_statements)
                connection.execute(delete_history, (last_applied,))

            # Use the base class batch_execute path (no per-call commit) and
            # wrap everything in a single transaction for atomicity.
            try:
                connection.execute("BEGIN")
                _run_with_history()
                connection.execute("COMMIT")
            except Exception:
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    logger.debug("Rollback failed", exc_info=True)
                raise

            logger.info("Rolled back migration: %s", last_applied)
            return [last_applied]
        finally:
            connection.close()

    @classmethod
    def apply_migrations(cls, database_url: str, migrations_dir: str | Path) -> list[str]:
        directory = Path(migrations_dir)
        directory.mkdir(parents=True, exist_ok=True)

        parsed = parse_database_url(database_url)
        backend = get_backend(database_url)
        connection = backend.connect(parsed)
        try:
            ddl = backend.create_migration_table_ddl(cls.HISTORY_TABLE)
            connection.execute(ddl)
            connection.commit()

            cursor = connection.execute(
                f"SELECT id FROM {backend.quote_identifier(cls.HISTORY_TABLE)}"
            )
            rows = backend.fetchall_dicts(cursor)
            applied = {row["id"] for row in rows}

            executed: list[str] = []
            ph = backend.param_style
            history_insert = (
                f"INSERT INTO {backend.quote_identifier(cls.HISTORY_TABLE)} (id, applied_at) "
                f"VALUES ({ph}, {ph})"
            )

            for file_path in sorted(directory.glob("*.sql")):
                if file_path.name in applied:
                    continue
                script = file_path.read_text(encoding="utf-8")
                statements = [s.strip() for s in script.replace("\r\n", "\n").split(";") if s.strip()]
                now = datetime.now(timezone.utc).isoformat()

                # Use the base class batch_execute (no per-call commit) and
                # run history insert + statements atomically.
                try:
                    connection.execute("BEGIN")
                    DatabaseBackend.batch_execute(connection, statements)
                    connection.execute(history_insert, (file_path.name, now))
                    connection.execute("COMMIT")
                except Exception:
                    try:
                        connection.execute("ROLLBACK")
                    except Exception:
                        logger.debug("Rollback failed", exc_info=True)
                    raise

                executed.append(file_path.name)

            return executed
        finally:
            connection.close()
