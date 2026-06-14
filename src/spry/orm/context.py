from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any

from spry.db import get_backend, parse_database_url
from spry.db.backend import ConnectionPool
from spry.db.url import DatabaseUrl
from spry.orm.dbset import DbSet
from spry.orm.metadata import DbSetDefinition, ModelMetadata, discover_models, to_table_name

logger = logging.getLogger("spry.orm")

_POOL_REGISTRY: dict[tuple[str, int], ConnectionPool] = {}
_POOL_LOCK = threading.Lock()


def dispose_all_pools() -> None:
    with _POOL_LOCK:
        for pool in _POOL_REGISTRY.values():
            try:
                pool.close_all()
            except Exception:
                logger.debug("Error closing pool", exc_info=True)
        _POOL_REGISTRY.clear()


def _get_or_create_pool(backend: Any, parsed: DatabaseUrl, pool_size: int) -> ConnectionPool:
    key = (parsed.database or "", pool_size)
    with _POOL_LOCK:
        pool = _POOL_REGISTRY.get(key)
        if pool is None:
            pool = ConnectionPool(backend, parsed, min_size=min(pool_size, 2), max_size=pool_size * 2)
            _POOL_REGISTRY[key] = pool
        return pool


class DbContext:
    models: list[type[Any]] | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        model_list = getattr(cls, "models", None)
        if model_list is not None:
            for entity_type in model_list:
                name = to_table_name(entity_type.__name__)
                if name not in vars(cls):
                    definition = DbSetDefinition(entity_type)
                    definition.__set_name__(cls, name)
                    setattr(cls, name, definition)

    def __init__(self, database_url: str = "app.db", *, pool_size: int | None = None) -> None:
        self.database_url = database_url
        parsed = parse_database_url(database_url)
        self._backend = get_backend(database_url)
        if pool_size is None and parsed.protocol != "sqlite":
            pool_size = 5
        if pool_size:
            self._pool = _get_or_create_pool(self._backend, parsed, pool_size)
            self.connection = self._pool.acquire()
        else:
            self._pool = None
            self.connection = self._backend.connect(parsed)
        self._dbsets: dict[str, DbSet[Any]] = {}
        self._models: dict[type, ModelMetadata] = discover_models(type(self))

    @property
    def backend(self):
        return self._backend

    def _get_dbset(self, name: str, entity_type: type) -> DbSet:
        if name not in self._dbsets:
            self._dbsets[name] = DbSet(self, self._models[entity_type])
        return self._dbsets[name]

    def set(self, entity_type: type) -> DbSet:
        model = self._models.get(entity_type)
        if model is None:
            raise KeyError(f"{entity_type.__name__} is not registered in this context")
        return DbSet(self, model)

    def ensure_created(self) -> None:
        for statement in self.schema_sql():
            self.connection.execute(statement)
        self.connection.commit()

    def schema_sql(self) -> list[str]:
        b = self._backend
        statements: list[str] = []
        for model in self._models.values():
            columns: list[str] = []
            constraints: list[str] = []
            for item in model.fields:
                definition = f"{b.quote_identifier(item.name)} {item.column_type}"
                if item.primary_key:
                    definition += " PRIMARY KEY"
                    if item.auto_increment:
                        kw = b.get_identity_keyword()
                        if kw:
                            definition += f" {kw}"
                if not item.nullable and not item.primary_key:
                    definition += " NOT NULL"
                if item.unique:
                    definition += " UNIQUE"
                columns.append(definition)
                if item.references is not None:
                    constraints.append(
                        f"FOREIGN KEY ({b.quote_identifier(item.name)}) "
                        f"REFERENCES {b.quote_identifier(item.references[0])} "
                        f"({b.quote_identifier(item.references[1])}) "
                        f"ON DELETE {item.on_delete or 'NO ACTION'}"
                    )
            statement = f"CREATE TABLE IF NOT EXISTS {b.quote_identifier(model.table_name)} ({', '.join(columns + constraints)})"
            statements.append(statement)
        return statements

    @contextmanager
    def transaction(self) -> Any:
        try:
            yield self
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def save(self) -> None:
        self.connection.commit()

    def save_changes(self) -> None:
        """Backward-compatible alias for :meth:`save`."""
        self.save()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.release(self.connection)
        else:
            self.connection.close()
