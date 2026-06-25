from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Handler = Callable[..., Any]


def controller(prefix: str = "") -> Callable[[type[Any]], type[Any]]:
    def decorator(controller_type: type[Any]) -> type[Any]:
        controller_type.__spry_prefix__ = _normalize_path(prefix)
        return controller_type

    return decorator


def get(path: str = "") -> Callable[[Handler], Handler]:
    return _route("GET", path)


def post(path: str = "") -> Callable[[Handler], Handler]:
    return _route("POST", path)


def put(path: str = "") -> Callable[[Handler], Handler]:
    return _route("PUT", path)


def patch(path: str = "") -> Callable[[Handler], Handler]:
    return _route("PATCH", path)


def delete(path: str = "") -> Callable[[Handler], Handler]:
    return _route("DELETE", path)


def _route(method: str, path: str) -> Callable[[Handler], Handler]:
    normalized = _normalize_path(path)

    def decorator(handler: Handler) -> Handler:
        routes = getattr(handler, "__spry_routes__", [])
        routes.append((method, normalized))
        handler.__spry_routes__ = routes
        return handler

    return decorator


@dataclass(slots=True)
class RouteDefinition:
    method: str
    path: str
    handler_name: str | None
    controller_type: type[Any] | None
    function_handler: Handler | None
    pattern: re.Pattern[str]
    parameter_names: tuple[str, ...]

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if self.method != method.upper():
            return None
        match = self.pattern.fullmatch(path)
        if not match:
            return None
        return match.groupdict()


def extract_controller_routes(
    controller_type: type[Any],
    prefix_override: str | None = None,
) -> list[RouteDefinition]:
    prefix = prefix_override if prefix_override is not None else getattr(controller_type, "__spry_prefix__", None)
    if prefix is None:
        raise TypeError(f"{controller_type.__name__} is not decorated with @controller")

    definitions: list[RouteDefinition] = []
    for attribute_name in dir(controller_type):
        attribute = getattr(controller_type, attribute_name)
        routes = getattr(attribute, "__spry_routes__", None)
        if not routes:
            continue
        for method, path in routes:
            full_path = _combine_paths(prefix, path)
            pattern, names = _compile_path(full_path)
            definitions.append(
                RouteDefinition(
                    method=method,
                    path=full_path,
                    handler_name=attribute_name,
                    controller_type=controller_type,
                    function_handler=None,
                    pattern=pattern,
                    parameter_names=names,
                )
            )
    return definitions


def create_function_route(method: str, path: str, handler: Handler) -> RouteDefinition:
    normalized = _normalize_path(path)
    pattern, names = _compile_path(normalized)
    return RouteDefinition(
        method=method.upper(),
        path=normalized,
        handler_name=None,
        controller_type=None,
        function_handler=handler,
        pattern=pattern,
        parameter_names=names,
    )


def _normalize_path(path: str) -> str:
    if not path or path == "/":
        return "/"
    cleaned = "/".join(part for part in path.split("/") if part)
    return f"/{cleaned}"


def _combine_paths(prefix: str, path: str) -> str:
    if prefix == "/":
        return _normalize_path(path)
    if path == "/":
        return prefix
    return _normalize_path(f"{prefix}/{path}")


_PARAM_PATTERNS: dict[str, str] = {
    "int": r"\d+",
    "float": r"\d+\.?\d*",
    "slug": r"[a-z0-9-]+",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "path": r".+",
}


def _compile_path(path: str) -> tuple[re.Pattern[str], tuple[str, ...]]:
    def _replace_param(match: re.Match[str]) -> str:
        content = match.group(1)
        if ":" in content:
            name, param_type = content.split(":", 1)
            pattern = _PARAM_PATTERNS.get(param_type.strip(), r"[^/]+")
            return f"(?P<{name}>{pattern})"
        return f"(?P<{content}>[^/]+)"

    raw_params = re.findall(r"\{([^{}]+)\}", path)
    names = tuple(p.split(":")[0].strip() for p in raw_params)
    escaped = re.sub(r"\{([^{}]+)\}", _replace_param, path)
    return re.compile(escaped), names
