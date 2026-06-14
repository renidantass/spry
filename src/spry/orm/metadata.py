from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any, Generic, TypeVar, overload, get_args, get_origin, get_type_hints

from dataclasses import MISSING, dataclass, field, fields, is_dataclass

from spry.db.column_type import ColumnType

TEntity = TypeVar("TEntity")


def to_db_value(value: Any) -> Any:
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


def from_db_value(value: Any, python_type: Any) -> Any:
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


def unwrap_type(annotation: Any) -> tuple[Any, bool]:
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


def to_table_name(class_name: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(class_name):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    base = "".join(chars)
    return base if base.endswith("s") else f"{base}s"


def slugify(value: str) -> str:
    return "_".join(part for part in value.lower().replace("-", " ").split() if part)


def resolve_target_type(target: Any) -> type:
    if callable(target) and not isinstance(target, type):
        return target()
    return target


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
    target_type: Any
    foreign_key: str
    many: bool
    reference_key: str = "id"
    local_key: str = "id"


@dataclass(slots=True)
class ModelMetadata:
    entity_type: type
    table_name: str
    fields: list[ModelField]
    primary_key: ModelField | None
    relations: dict[str, RelationField]


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
    target_type: Any,
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
    target_type: Any,
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
    target_type: Any,
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


def build_model(entity_type: type) -> ModelMetadata:
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

        python_type, nullable = unwrap_type(type_hints.get(item.name, item.type))
        is_primary_key = bool(metadata.get("primary_key")) or item.name == "id"
        reference = metadata.get("references")

        col_type = _python_to_column_type(python_type)

        model_field = ModelField(
            name=item.name,
            python_type=python_type,
            column_type=col_type.sql_type,
            primary_key=is_primary_key,
            nullable=bool(metadata.get("nullable", nullable)),
            unique=bool(metadata.get("unique", False)),
            references=None if reference is None else (to_table_name(resolve_target_type(reference).__name__), metadata.get("reference_key", "id")),
            on_delete=metadata.get("on_delete"),
            auto_increment=is_primary_key and (python_type is int),
        )
        if is_primary_key:
            primary_key = model_field
        model_fields.append(model_field)

    table_name = getattr(entity_type, "__table_name__", to_table_name(entity_type.__name__))
    return ModelMetadata(
        entity_type=entity_type,
        table_name=table_name,
        fields=model_fields,
        primary_key=primary_key,
        relations=relations,
    )


def _python_to_column_type(python_type: Any) -> ColumnType:
    if python_type is int:
        return ColumnType("INTEGER", auto_increment_keyword="AUTOINCREMENT")
    if python_type is float:
        return ColumnType("REAL")
    if python_type is datetime:
        return ColumnType("TEXT")
    if python_type is date:
        return ColumnType("TEXT")
    if python_type is bool:
        return ColumnType("INTEGER")
    if isinstance(python_type, type) and issubclass(python_type, Enum):
        return ColumnType("TEXT")
    return ColumnType("TEXT")


def discover_models(context_type: type) -> dict[type, ModelMetadata]:
    models: dict[type, ModelMetadata] = {}
    for attribute in vars(context_type).values():
        if not isinstance(attribute, DbSetDefinition):
            continue
        entity_type = attribute.entity_type
        if not is_dataclass(entity_type):
            raise TypeError(f"{entity_type.__name__} must be a dataclass to be used with dbset")
        models[entity_type] = build_model(entity_type)
    return models


class DbSetDefinition(Generic[TEntity]):
    def __init__(self, entity_type: type) -> None:
        self.entity_type = entity_type
        self.name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, instance: None, owner: type) -> "DbSetDefinition[TEntity]": ...
    @overload
    def __get__(self, instance: object, owner: type) -> Any: ...
    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        return instance._get_dbset(self.name, self.entity_type)
