from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from dataclasses import MISSING, asdict, dataclass, field, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar, overload, get_args, get_origin, get_type_hints

logger = logging.getLogger("spry.orm")

from spry.db import get_backend, parse_database_url
from spry.db.column_type import ColumnType


TEntity = TypeVar("TEntity")


@dataclass(slots=True)
class Page:
    items: list[Any]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.per_page))

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


def key(default: Any = None) -> Any:
    return field(default=default, metadata={"primary_key": True, "nullable": default is None})


def column(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    nullable: bool = False,
    unique: bool = False,
) -> Any:
    metadata = {"nullable": nullable, "unique": unique}
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("Use either default or default_factory, not both")
    if default is not MISSING:
        return field(default=default, metadata=metadata)
    if default_factory is not MISSING:
        return field(default_factory=default_factory, metadata=metadata)
    return field(metadata=metadata)


def foreign_key(
    target_type: type[Any] | Callable[[], type[Any]],
    *,
    default: Any = MISSING,
    nullable: bool = False,
    reference_key: str = "id",
    on_delete: str = "NO ACTION",
) -> Any:
    metadata = {
        "nullable": nullable,
        "references": target_type,
        "reference_key": reference_key,
        "on_delete": on_delete,
    }
    if default is not MISSING:
        return field(default=default, metadata=metadata)
    return field(metadata=metadata)


def navigation(
    target_type: type[Any] | Callable[[], type[Any]],
    *,
    foreign_key: str,
    reference_key: str = "id",
    default: Any = None,
) -> Any:
    return field(
        default=default,
        repr=False,
        compare=False,
        metadata={
            "relation": True,
            "many": False,
            "target_type": target_type,
            "foreign_key": foreign_key,
            "reference_key": reference_key,
        },
    )


def navigation_many(
    target_type: type[Any] | Callable[[], type[Any]],
    *,
    foreign_key: str,
    local_key: str = "id",
) -> Any:
    return field(
        default_factory=list,
        repr=False,
        compare=False,
        metadata={
            "relation": True,
            "many": True,
            "target_type": target_type,
            "foreign_key": foreign_key,
            "local_key": local_key,
        },
    )


class DbSetDefinition(Generic[TEntity]):
    def __init__(self, entity_type: type[TEntity]) -> None:
        self.entity_type = entity_type
        self.name = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.name = name

    @overload
    def __get__(self, instance: None, owner: type[Any]) -> "DbSetDefinition[TEntity]": ...
    @overload
    def __get__(self, instance: object, owner: type[Any]) -> "DbSet[TEntity]": ...
    def __get__(self, instance: Any, owner: type[Any]) -> "DbSet[TEntity] | DbSetDefinition[TEntity]":
        if instance is None:
            return self
        return instance._get_dbset(self.name, self.entity_type)


def dbset(entity_type: type[TEntity]) -> DbSetDefinition[TEntity]:
    return DbSetDefinition(entity_type)


@dataclass(slots=True)
class ModelField:
    name: str
    python_type: Any
    column_type: str
    primary_key: bool
    nullable: bool
    unique: bool
    references: tuple[str, str] | None = None
    on_delete: str | None = None
    auto_increment: bool = False


@dataclass(slots=True)
class RelationField:
    name: str
    target_type: type[Any] | Callable[[], type[Any]]
    foreign_key: str
    many: bool
    reference_key: str = "id"
    local_key: str = "id"


@dataclass(slots=True)
class ModelMetadata(Generic[TEntity]):
    entity_type: type[TEntity]
    table_name: str
    fields: list[ModelField]
    primary_key: ModelField | None
    relations: dict[str, RelationField]


class DbContext:
    def __init__(self, database_url: str = "app.db", *, pool_size: int | None = None) -> None:
        self.database_url = database_url
        parsed = parse_database_url(database_url)
        self._backend = get_backend(database_url)
        if pool_size is None and parsed.protocol != "sqlite":
            pool_size = 5
        if pool_size:
            from spry.db.backend import ConnectionPool
            self._pool = ConnectionPool(self._backend, parsed, min_size=min(pool_size, 2), max_size=pool_size * 2)
            self.connection = self._pool.acquire()
        else:
            self._pool = None
            self.connection = self._backend.connect(parsed)
        self._dbsets: dict[str, DbSet[Any]] = {}
        self._models = _discover_models(type(self))

    @property
    def backend(self):
        return self._backend

    def _get_dbset(self, name: str, entity_type: type[TEntity]) -> "DbSet[TEntity]":
        if name not in self._dbsets:
            self._dbsets[name] = DbSet(self, self._models[entity_type])
        return self._dbsets[name]

    def set(self, entity_type: type[TEntity]) -> "DbSet[TEntity]":
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

    def save_changes(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        if self._pool:
            self._pool.release(self.connection)
        else:
            self.connection.close()


class DbSet(Generic[TEntity]):
    def __init__(self, context: DbContext, model: ModelMetadata[TEntity]) -> None:
        self.context = context
        self.model = model

    def _q(self, name: str) -> str:
        return self.context.backend.quote_identifier(name)

    def _qt(self) -> str:
        return self._q(self.model.table_name)

    def _p(self, sql: str) -> str:
        style = self.context.backend.param_style
        return sql.replace("?", style) if style != "?" else sql

    def all(self) -> list[TEntity]:
        b = self.context.backend
        cursor = self.context.connection.execute(f"SELECT * FROM {self._qt()}")
        return [self._hydrate(row) for row in b.fetchall_dicts(cursor)]

    def count(self) -> int:
        cursor = self.context.connection.execute(f"SELECT COUNT(*) AS total FROM {self._qt()}")
        row = self.context.backend.fetchone_dict(cursor)
        return int(row["total"])

    def where(self, **filters: Any) -> list[TEntity]:
        b = self.context.backend
        sql, values = self._build_where(filters)
        cursor = self.context.connection.execute(
            f"SELECT * FROM {self._qt()}{sql}",
            values,
        )
        return [self._hydrate(row) for row in b.fetchall_dicts(cursor)]

    def first(self, **filters: Any) -> TEntity | None:
        b = self.context.backend
        sql, values = self._build_where(filters)
        full_sql = f"SELECT * FROM {self._qt()}{sql}"
        full_sql = b.compile_limit(full_sql, 1)
        cursor = self.context.connection.execute(full_sql, values)
        row = b.fetchone_dict(cursor)
        return None if row is None else self._hydrate(row)

    def find(self, key_value: Any) -> TEntity | None:
        primary_key = self.model.primary_key
        if primary_key is None:
            raise TypeError(f"{self.model.entity_type.__name__} does not define a primary key")
        return self.first(**{primary_key.name: key_value})

    def include(self, entity_or_entities: TEntity | list[TEntity], *relations: str) -> TEntity | list[TEntity]:
        entities = entity_or_entities if isinstance(entity_or_entities, list) else [entity_or_entities]
        for entity in entities:
            for relation_name in relations:
                self._load_relation(entity, relation_name)
        return entity_or_entities

    def add(self, entity: TEntity) -> TEntity:
        b = self.context.backend
        payload = asdict(entity) if is_dataclass(entity) else entity.__dict__.copy()
        columns: list[str] = []
        values: list[Any] = []

        for item in self.model.fields:
            val = payload.get(item.name)
            if item.primary_key and val is None:
                continue
            columns.append(item.name)
            values.append(_to_db_value(val))

        primary_key = self.model.primary_key
        insert = b.compile_insert(self.model.table_name, columns, pk_field=primary_key)
        cursor = self.context.connection.execute(insert.sql, values)

        if primary_key is not None and getattr(entity, primary_key.name, None) is None:
            pk_value = b.get_last_insert_id(cursor, primary_key)
            if pk_value is not None:
                setattr(entity, primary_key.name, pk_value)
        return entity

    def update(self, entity: TEntity) -> TEntity:
        primary_key = self.model.primary_key
        if primary_key is None:
            raise TypeError(f"{self.model.entity_type.__name__} does not define a primary key")

        key_value = getattr(entity, primary_key.name)
        if key_value is None:
            raise ValueError("Cannot update an entity without a primary key value")

        assignments: list[str] = []
        values: list[Any] = []
        for item in self.model.fields:
            if item.primary_key:
                continue
            assignments.append(f"{self._q(item.name)} = ?")
            values.append(_to_db_value(getattr(entity, item.name)))
        values.append(key_value)

        sql = self._p(f"UPDATE {self._qt()} SET {', '.join(assignments)} WHERE {self._q(primary_key.name)} = ?")
        self.context.connection.execute(sql, values)
        return entity

    def remove(self, entity_or_key: TEntity | Any) -> None:
        primary_key = self.model.primary_key
        if primary_key is None:
            raise TypeError(f"{self.model.entity_type.__name__} does not define a primary key")

        key_value = entity_or_key
        if isinstance(entity_or_key, self.model.entity_type):
            key_value = getattr(entity_or_key, primary_key.name)

        sql = self._p(f"DELETE FROM {self._qt()} WHERE {self._q(primary_key.name)} = ?")
        self.context.connection.execute(sql, (key_value,))

    def order_by(self, *fields: str) -> list[TEntity]:
        if not fields:
            return self.all()
        clauses: list[str] = []
        for f in fields:
            f = f.strip()
            if f.startswith("-"):
                clauses.append(f"{self._q(f[1:])} DESC")
            else:
                clauses.append(f"{self._q(f)} ASC")
        sql = f"SELECT * FROM {self._qt()} ORDER BY {', '.join(clauses)}"
        cursor = self.context.connection.execute(self._p(sql))
        return [self._hydrate(row) for row in self.context.backend.fetchall_dicts(cursor)]

    def skip(self, count: int) -> "_SkipTakeQuery[TEntity]":
        return _SkipTakeQuery(self, count)

    def paginate(self, page: int = 1, per_page: int = 20) -> Page:
        count = self.count()
        items = self._execute_with_limit_offset(per_page, (page - 1) * per_page)
        return Page(items=items, total=count, page=page, per_page=per_page)

    def _execute_with_limit_offset(self, limit: int, offset: int) -> list[TEntity]:
        b = self.context.backend
        sql = f"SELECT * FROM {self._qt()} LIMIT ? OFFSET ?"
        sql = self._p(sql)
        cursor = self.context.connection.execute(sql, (limit, offset))
        return [self._hydrate(row) for row in b.fetchall_dicts(cursor)]

    def sum(self, field: str) -> int | float | None:
        return self._aggregate(f"SUM({self._q(field)})")

    def avg(self, field: str) -> float | None:
        return self._aggregate(f"AVG({self._q(field)})")

    def min(self, field: str) -> Any:
        return self._aggregate(f"MIN({self._q(field)})")

    def max(self, field: str) -> Any:
        return self._aggregate(f"MAX({self._q(field)})")

    def _aggregate(self, expr: str) -> Any:
        b = self.context.backend
        sql = self._p(f"SELECT {expr} AS result FROM {self._qt()}")
        cursor = self.context.connection.execute(sql)
        row = b.fetchone_dict(cursor)
        return row["result"] if row else None

    @staticmethod
    def from_sql(context: DbContext, model_type: type[TEntity], sql: str, params: list[Any] | None = None) -> list[TEntity]:
        b = context.backend
        cursor = context.connection.execute(sql, params or [])
        model = context._models.get(model_type)
        if model is None:
            raise KeyError(f"{model_type.__name__} is not registered in this context")
        return [DbSet._hydrate_static(row, model) for row in b.fetchall_dicts(cursor)]

    @staticmethod
    def _hydrate_static(row: dict[str, Any], model: ModelMetadata) -> Any:
        kwargs: dict[str, Any] = {}
        for item in model.fields:
            kwargs[item.name] = _from_db_value(row.get(item.name), item.python_type)
        return model.entity_type(**kwargs)

    def _build_where(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        clauses = [f"{self._q(name)} = ?" for name in filters]
        values = [_to_db_value(value) for value in filters.values()]
        where_clause = f" WHERE {' AND '.join(clauses)}"
        return self._p(where_clause), values

    def _hydrate(self, row: dict[str, Any]) -> TEntity:
        kwargs: dict[str, Any] = {}
        for item in self.model.fields:
            kwargs[item.name] = _from_db_value(row.get(item.name), item.python_type)
        return self.model.entity_type(**kwargs)

    def _load_relation(self, entity: TEntity, relation_name: str) -> None:
        relation = self.model.relations.get(relation_name)
        if relation is None:
            raise KeyError(f"Relation {relation_name} is not defined on {self.model.entity_type.__name__}")

        target_type = _resolve_target_type(relation.target_type)
        target_set = self.context.set(target_type)
        if relation.many:
            local_value = getattr(entity, relation.local_key)
            items = target_set.where(**{relation.foreign_key: local_value})
            setattr(entity, relation.name, items)
            return

        foreign_key_value = getattr(entity, relation.foreign_key)
        related = None if foreign_key_value is None else target_set.first(**{relation.reference_key: foreign_key_value})
        setattr(entity, relation.name, related)


class _SkipTakeQuery(Generic[TEntity]):
    def __init__(self, dbset: DbSet[TEntity], skip: int) -> None:
        self._dbset = dbset
        self._skip = skip
        self._limit: int | None = None

    def take(self, count: int) -> list[TEntity]:
        b = self._dbset.context.backend
        sql = f"SELECT * FROM {self._dbset._qt()} LIMIT ? OFFSET ?"
        sql = self._dbset._p(sql)
        cursor = self._dbset.context.connection.execute(sql, (count, self._skip))
        rows = b.fetchall_dicts(cursor)
        return [self._dbset._hydrate(row) for row in rows]


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

        file_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{_slugify(name)}.sql"
        destination = output_path / file_name
        destination.write_text(sql, encoding="utf-8")

        down_sql = cls._generate_down_sql(context_type)
        if down_sql:
            down_file_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{_slugify(name)}_down.sql"
            down_destination = output_path / down_file_name
            down_destination.write_text(down_sql, encoding="utf-8")
        return destination

    @classmethod
    def _generate_down_sql(cls, context_type: type[DbContext]) -> str:
        context = context_type(":memory:")
        try:
            statements: list[str] = []
            for model in context._models.values():
                statements.append(f"DROP TABLE IF EXISTS {model.table_name};")
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
            statements = [s.strip() for s in script.replace("\r\n", "\n").split(";") if s.strip()]
            backend.batch_execute(connection, statements)

            ph = backend.param_style
            connection.execute(
                f"DELETE FROM {backend.quote_identifier(cls.HISTORY_TABLE)} WHERE id = {ph}",
                (last_applied,),
            )
            connection.commit()
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

            cursor = connection.execute(
                f"SELECT id FROM {backend.quote_identifier(cls.HISTORY_TABLE)}"
            )
            rows = backend.fetchall_dicts(cursor)
            applied = {row["id"] for row in rows}

            executed: list[str] = []
            for file_path in sorted(directory.glob("*.sql")):
                if file_path.name in applied:
                    continue
                script = file_path.read_text(encoding="utf-8")
                statements = [s.strip() for s in script.replace("\r\n", "\n").split(";") if s.strip()]
                backend.batch_execute(connection, statements)

                now = datetime.utcnow().isoformat()
                pk = file_path.name
                ph = backend.param_style
                connection.execute(
                    f"INSERT INTO {backend.quote_identifier(cls.HISTORY_TABLE)} (id, applied_at) VALUES ({ph}, {ph})",
                    (pk, now),
                )
                executed.append(file_path.name)

            connection.commit()
            return executed
        finally:
            connection.close()


def _discover_models(context_type: type[DbContext]) -> dict[type[Any], ModelMetadata[Any]]:
    models: dict[type[Any], ModelMetadata[Any]] = {}
    for attribute in vars(context_type).values():
        if not isinstance(attribute, DbSetDefinition):
            continue
        entity_type = attribute.entity_type
        if not is_dataclass(entity_type):
            raise TypeError(f"{entity_type.__name__} must be a dataclass to be used with dbset")
        models[entity_type] = _build_model(entity_type)
    return models


def _build_model(entity_type: type[TEntity]) -> ModelMetadata[TEntity]:
    model_fields: list[ModelField] = []
    primary_key: ModelField | None = None
    relations: dict[str, RelationField] = {}
    type_hints = get_type_hints(entity_type)

    for item in fields(entity_type):
        metadata = item.metadata or {}
        if metadata.get("relation"):
            relations[item.name] = RelationField(
                name=item.name,
                target_type=metadata["target_type"],
                foreign_key=metadata["foreign_key"],
                many=bool(metadata.get("many", False)),
                reference_key=metadata.get("reference_key", "id"),
                local_key=metadata.get("local_key", "id"),
            )
            continue

        python_type, nullable = _unwrap_type(type_hints.get(item.name, item.type))
        is_primary_key = bool(metadata.get("primary_key")) or item.name == "id"
        reference = metadata.get("references")

        col_type = ColumnType("TEXT")
        if python_type is int:
            col_type = ColumnType("INTEGER", auto_increment_keyword="AUTOINCREMENT")
        elif python_type is float:
            col_type = ColumnType("REAL")
        elif python_type is date:
            col_type = ColumnType("TEXT")
        elif python_type is datetime:
            col_type = ColumnType("TEXT")
        elif python_type is bool:
            col_type = ColumnType("INTEGER")
        elif isinstance(python_type, type) and issubclass(python_type, Enum):
            col_type = ColumnType("TEXT")

        model_field = ModelField(
            name=item.name,
            python_type=python_type,
            column_type=col_type.sql_type,
            primary_key=is_primary_key,
            nullable=bool(metadata.get("nullable", nullable)),
            unique=bool(metadata.get("unique", False)),
            references=None if reference is None else (_to_table_name(_resolve_target_type(reference).__name__), metadata.get("reference_key", "id")),
            on_delete=metadata.get("on_delete"),
            auto_increment=is_primary_key and (python_type is int),
        )
        if is_primary_key:
            primary_key = model_field
        model_fields.append(model_field)

    table_name = getattr(entity_type, "__table_name__", _to_table_name(entity_type.__name__))
    return ModelMetadata(
        entity_type=entity_type,
        table_name=table_name,
        fields=model_fields,
        primary_key=primary_key,
        relations=relations,
    )


def _unwrap_type(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is None:
        return annotation, False
    if origin in {list, tuple, dict}:
        return str, False
    if type(None) in args:
        inner = next(arg for arg in args if arg is not type(None))
        return inner, True
    return annotation, False


def _to_db_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _from_db_value(value: Any, python_type: Any) -> Any:
    if value is None:
        return None
    if python_type is bool:
        return bool(value)
    if python_type is int:
        return int(value)
    if python_type is float:
        return float(value)
    if python_type is datetime:
        return datetime.fromisoformat(value)
    if python_type is date:
        return date.fromisoformat(value)
    if isinstance(python_type, type) and issubclass(python_type, Enum):
        try:
            return python_type(value)
        except (ValueError, TypeError):
            return value
    return value


def _to_table_name(class_name: str) -> str:
    name = []
    for index, char in enumerate(class_name):
        if char.isupper() and index > 0:
            name.append("_")
        name.append(char.lower())
    base = "".join(name)
    return base if base.endswith("s") else f"{base}s"


def _slugify(value: str) -> str:
    return "_".join(part for part in value.lower().replace("-", " ").split() if part)


def _resolve_target_type(target: type[Any] | Callable[[], type[Any]]) -> type[Any]:
    if callable(target) and not isinstance(target, type):
        return target()
    return target
