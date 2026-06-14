from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, get_args, get_origin


class Configuration:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

    @classmethod
    def load(cls, base_path: str | Path | None = None, file_name: str = "appsettings.json") -> "Configuration":
        base_dir = Path(base_path or Path.cwd())
        data: dict[str, Any] = {}

        _try_load_dotenv(base_dir)

        env_name = os.environ.get("APP_ENVIRONMENT", "")
        env_files = [file_name]
        if env_name:
            env_specific = file_name.replace(".json", f".{env_name}.json")
            env_files.append(env_specific)

        for fname in env_files:
            file_path = base_dir / fname
            if file_path.exists():
                with file_path.open("r", encoding="utf-8") as handle:
                    _deep_merge(data, json.load(handle))

        env_data = _env_to_dict("APP__")
        _deep_merge(data, env_data)
        return cls(data)

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self._data)

    def get(self, *path: str, default: Any = None) -> Any:
        current: Any = self._data
        for part in path:
            if not isinstance(current, dict):
                return default
            if part not in current:
                lowered = {key.lower(): value for key, value in current.items()}
                current = lowered.get(part.lower(), default)
            else:
                current = current[part]
            if current is default:
                return default
        return current

    def section(self, name: str) -> dict[str, Any]:
        section = self.get(name, default={})
        return section if isinstance(section, dict) else {}

    def bind(self, model_type: type[Any], section: str | None = None, *, strict: bool = False) -> Any:
        source = self.section(section) if section else self.as_dict()
        if strict and section:
            extra = [k for k in self._data.get(section, {}) if k.lower() not in {f.name.lower() for f in fields(model_type)}]
            if extra:
                import logging
                logging.getLogger("spry.config").warning("Extra config keys in section '%s': %s", section, extra)
        return _bind_model(model_type, source)


def _try_load_dotenv(base_dir: Path) -> None:
    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return
    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def _env_to_dict(prefix: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        cursor = result
        parts = [part.lower() for part in key[len(prefix) :].split("__") if part]
        if not parts:
            continue

        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = _parse_scalar(value)
    return result


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _deep_merge(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key, value in incoming.items():
        lowered_key = next((current for current in target if current.lower() == key.lower()), key)
        if isinstance(value, dict) and isinstance(target.get(lowered_key), dict):
            _deep_merge(target[lowered_key], value)
            continue
        target[lowered_key] = value


def _bind_model(model_type: type[Any], source: dict[str, Any]) -> Any:
    if not is_dataclass(model_type):
        raise TypeError(f"{model_type.__name__} must be a dataclass to use configuration binding")

    values: dict[str, Any] = {}
    lowered = {key.lower(): value for key, value in source.items()}

    for field in fields(model_type):
        raw = lowered.get(field.name.lower())
        if raw is None:
            continue
        values[field.name] = _coerce_value(field.type, raw)
    return model_type(**values)


def _coerce_value(expected_type: Any, raw: Any) -> Any:
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if origin is None:
        if is_dataclass(expected_type) and isinstance(raw, dict):
            return _bind_model(expected_type, raw)
        if expected_type in {str, int, float, bool}:
            return expected_type(raw)
        return raw

    if origin in {list, tuple} and args and isinstance(raw, list):
        return [_coerce_value(args[0], item) for item in raw]

    if origin is dict:
        return raw

    if origin is not None and type(None) in args:
        inner = next(arg for arg in args if arg is not type(None))
        return None if raw is None else _coerce_value(inner, raw)

    return raw
