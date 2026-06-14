from __future__ import annotations

from dataclasses import MISSING, field, fields, is_dataclass
from types import UnionType
from typing import Any, Union, get_args, get_origin


class ValidationError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        detail = "; ".join(f"{e.get('field','?')}: {e.get('message','?')}" for e in errors[:3])
        super().__init__(f"Validation failed: {detail}")


def _make_error(field: str, message: str, code: str = "validation", actual: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"field": field, "message": message, "code": code}
    if actual is not None:
        error["actual"] = actual
    return error


def bind_value(expected_type: Any, raw: Any, *, path: str) -> Any:
    try:
        return _bind_value(expected_type, raw, path=path)
    except ValidationError:
        raise
    except (TypeError, ValueError) as error:
        raise ValidationError([{"field": path, "message": str(error), "code": "type_error", "actual": raw}]) from error


def bind_payload(model_type: type[Any], raw: Any) -> Any:
    if not is_dataclass(model_type):
        raise TypeError(f"{model_type.__name__} must be a dataclass")
    return _bind_dataclass(model_type, raw, path="$")


def _bind_value(expected_type: Any, raw: Any, *, path: str) -> Any:
    if expected_type is Any:
        return raw

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if expected_type is None or expected_type is type(None):
        if raw is not None:
            raise TypeError("Expected null")
        return None

    if origin in {UnionType, Union}:
        if type(None) in args and raw is None:
            return None
        last_error: ValidationError | None = None
        for candidate in args:
            if candidate is type(None):
                continue
            try:
                return _bind_value(candidate, raw, path=path)
            except ValidationError as error:
                last_error = error
        if last_error is not None:
            raise last_error
        raise TypeError("Value does not match any allowed type")

    if is_dataclass(expected_type):
        return _bind_dataclass(expected_type, raw, path=path)

    if origin is list:
        if not isinstance(raw, list):
            raise TypeError("Expected a list")
        item_type = args[0] if args else Any
        return [_bind_value(item_type, item, path=f"{path}[{index}]") for index, item in enumerate(raw)]

    if origin is dict:
        if not isinstance(raw, dict):
            raise TypeError("Expected an object")
        return raw

    if expected_type is bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        raise TypeError("Expected a boolean")

    if expected_type is int:
        if raw is None:
            raise TypeError("Expected an integer, got null")
        if isinstance(raw, bool):
            raise TypeError("Expected an integer")
        return int(raw)

    if expected_type is float:
        if raw is None:
            raise TypeError("Expected a number, got null")
        return float(raw)

    if expected_type is str:
        if raw is None:
            raise TypeError("Expected a string")
        return str(raw)

    return raw


def _bind_dataclass(model_type: type[Any], raw: Any, *, path: str) -> Any:
    if not isinstance(raw, dict):
        raise ValidationError([{"field": path, "message": "Expected an object"}])

    lowered = {key.lower(): value for key, value in raw.items()}
    kwargs: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    for item in fields(model_type):
        field_path = f"{path}.{item.name}" if path != "$" else item.name
        key = item.name.lower()
        if key not in lowered:
            if item.default is MISSING and item.default_factory is MISSING:
                errors.append(_make_error(field_path, "Field is required", "required"))
            continue
        try:
            kwargs[item.name] = _bind_value(item.type, lowered[key], path=field_path)
        except ValidationError as error:
            errors.extend(error.errors)

    if errors:
        raise ValidationError(errors)

    instance = model_type(**kwargs)

    for item in fields(model_type):
        validators = item.metadata.get("validate", []) if hasattr(item, "metadata") else []
        if not validators:
            continue
        field_path = f"{path}.{item.name}" if path != "$" else item.name
        for validator in validators:
            msg = validator.validate(kwargs.get(item.name), item.name)
            if msg:
                errors.append(_make_error(field_path, msg, type(validator).__name__.lower(), kwargs.get(item.name)))

    if errors:
        raise ValidationError(errors)
    return instance


def validate(*validators: Any, default: Any = MISSING, default_factory: Any = MISSING) -> Any:
    """Pythonic helper to create a dataclass field with validators.

    Examples:
        title: str = validate(Required(), MinLength(3))
        email: str = validate(Email(), default="")
        tags: list[str] = validate(default_factory=list)
    """
    metadata = {"validate": list(validators)} if validators else {}
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("Use either default or default_factory, not both")
    if default is not MISSING:
        return field(default=default, metadata=metadata)
    if default_factory is not MISSING:
        return field(default_factory=default_factory, metadata=metadata)
    return field(metadata=metadata)
