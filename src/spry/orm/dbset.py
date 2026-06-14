from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Generic, TypeVar, overload

from spry.orm.metadata import (
    DbSetDefinition,
    ModelMetadata,
    from_db_value,
    resolve_target_type,
    to_db_value,
)

TEntity = TypeVar("TEntity")


def dbset(entity_type: type) -> "DbSetDefinition[TEntity]":
    return DbSetDefinition(entity_type)


class _SkipTakeQuery(Generic[TEntity]):
    def __init__(self, dbset: "DbSet[TEntity]", skip: int) -> None:
        self._dbset = dbset
        self._skip = skip
        self._limit: int | None = None

    def take(self, count: int) -> list[TEntity]:
        b = self._dbset.context.backend
        sql = f"SELECT * FROM {self._dbset._qt()} LIMIT ? OFFSET ?"
        sql = self._dbset._p(sql)
        cursor = self._dbset.context.connection.execute(sql, (count, self._skip))
        return [self._dbset._hydrate(row) for row in b.fetchall_dicts(cursor)]


class DbSet(Generic[TEntity]):
    def __init__(self, context: Any, model: ModelMetadata) -> None:
        self.context = context
        self.model = model

    def _q(self, name: str) -> str:
        return self.context.backend.quote_identifier(name)

    def _qt(self) -> str:
        return self._q(self.model.table_name)

    def _p(self, sql: str) -> str:
        style = self.context.backend.param_style
        return sql.replace("?", style) if style != "?" else sql

    def _valid_fields(self) -> set[str]:
        return {f.name for f in self.model.fields}

    def _validate_fields(self, *names: str) -> None:
        valid = self._valid_fields()
        for name in names:
            clean = name.lstrip("-")
            if clean not in valid:
                raise ValueError(
                    f"'{clean}' is not a valid field on {self.model.entity_type.__name__}. "
                    f"Valid fields: {', '.join(sorted(valid))}"
                )

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
        full_sql = b.compile_limit(f"SELECT * FROM {self._qt()}{sql}", 1)
        cursor = self.context.connection.execute(full_sql, values)
        row = b.fetchone_dict(cursor)
        return None if row is None else self._hydrate(row)

    def find(self, key_value: Any) -> TEntity | None:
        primary_key = self.model.primary_key
        if primary_key is None:
            raise TypeError(f"{self.model.entity_type.__name__} does not define a primary key")
        return self.first(**{primary_key.name: key_value})

    def include(self, entity_or_entities: Any, *relations: str) -> Any:
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
            values.append(to_db_value(val))

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
            values.append(to_db_value(getattr(entity, item.name)))
        values.append(key_value)

        sql = self._p(f"UPDATE {self._qt()} SET {', '.join(assignments)} WHERE {self._q(primary_key.name)} = ?")
        self.context.connection.execute(sql, values)
        return entity

    def remove(self, entity_or_key: Any) -> None:
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
        self._validate_fields(*fields)
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

    def skip(self, count: int) -> _SkipTakeQuery[TEntity]:
        return _SkipTakeQuery(self, count)

    def paginate(self, page: int = 1, per_page: int = 20) -> Any:
        from spry.orm.metadata import ModelMetadata
        from spry.orm.page import Page
        total = self.count()
        items = self._execute_with_limit_offset(per_page, (page - 1) * per_page)
        return Page(items=items, total=total, page=page, per_page=per_page)

    def _execute_with_limit_offset(self, limit: int, offset: int) -> list[TEntity]:
        b = self.context.backend
        sql = self._p(f"SELECT * FROM {self._qt()} LIMIT ? OFFSET ?")
        cursor = self.context.connection.execute(sql, (limit, offset))
        return [self._hydrate(row) for row in b.fetchall_dicts(cursor)]

    def sum(self, field: str) -> Any:
        self._validate_fields(field)
        return self._aggregate(f"SUM({self._q(field)})")

    def avg(self, field: str) -> Any:
        self._validate_fields(field)
        return self._aggregate(f"AVG({self._q(field)})")

    def min(self, field: str) -> Any:
        self._validate_fields(field)
        return self._aggregate(f"MIN({self._q(field)})")

    def max(self, field: str) -> Any:
        self._validate_fields(field)
        return self._aggregate(f"MAX({self._q(field)})")

    def _aggregate(self, expr: str) -> Any:
        b = self.context.backend
        sql = self._p(f"SELECT {expr} AS result FROM {self._qt()}")
        cursor = self.context.connection.execute(sql)
        row = b.fetchone_dict(cursor)
        return row["result"] if row else None

    @staticmethod
    def from_sql(context: Any, model_type: type, sql: str, params: list[Any] | None = None) -> list[TEntity]:
        b = context.backend
        cursor = context.connection.execute(sql, params or [])
        model = context._models.get(model_type)
        if model is None:
            raise KeyError(f"{model_type.__name__} is not registered in this context")
        return [DbSet._hydrate_static(row, model) for row in b.fetchall_dicts(cursor)]

    @staticmethod
    def _hydrate_static(row: dict[str, Any], model: ModelMetadata) -> Any:
        kwargs: dict[str, Any] = {
            item.name: from_db_value(row.get(item.name), item.python_type)
            for item in model.fields
        }
        return model.entity_type(**kwargs)

    def _build_where(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        self._validate_fields(*filters.keys())
        clauses = [f"{self._q(name)} = ?" for name in filters]
        values = [to_db_value(value) for value in filters.values()]
        where_clause = f" WHERE {' AND '.join(clauses)}"
        return self._p(where_clause), values

    def _hydrate(self, row: dict[str, Any]) -> TEntity:
        kwargs: dict[str, Any] = {
            item.name: from_db_value(row.get(item.name), item.python_type)
            for item in self.model.fields
        }
        return self.model.entity_type(**kwargs)

    def _load_relation(self, entity: TEntity, relation_name: str) -> None:
        relation = self.model.relations.get(relation_name)
        if relation is None:
            raise KeyError(f"Relation {relation_name} is not defined on {self.model.entity_type.__name__}")

        target_type = resolve_target_type(relation.target_type)
        target_set = self.context.set(target_type)
        if relation.many:
            local_value = getattr(entity, relation.local_key)
            setattr(entity, relation.name, target_set.where(**{relation.foreign_key: local_value}))
            return

        foreign_key_value = getattr(entity, relation.foreign_key)
        related = None if foreign_key_value is None else target_set.first(**{relation.reference_key: foreign_key_value})
        setattr(entity, relation.name, related)
