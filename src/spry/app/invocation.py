from __future__ import annotations

import asyncio
import inspect
from dataclasses import is_dataclass
from typing import Any, get_type_hints

from spry.di import ServiceScope
from spry.http import Request
from spry.validation import bind_payload, bind_value

_HANDLER_INSPECTION_CACHE: dict[Any, tuple[inspect.Signature, dict[str, Any]]] = {}


def _inspect_handler(handler: Any) -> tuple[inspect.Signature, dict[str, Any]]:
    cached = _HANDLER_INSPECTION_CACHE.get(handler)
    if cached is not None:
        return cached
    try:
        hints = get_type_hints(handler)
    except Exception:
        hints = {}
    signature = inspect.signature(handler)
    result = (signature, hints)
    _HANDLER_INSPECTION_CACHE[handler] = result
    return result


def invoke_callable(handler: Any, scope: ServiceScope, request: Request, route_values: dict[str, str]) -> Any:
    signature, type_hints = _inspect_handler(handler)
    kwargs: dict[str, Any] = {}
    payload: Any = None

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        annotation = type_hints.get(name, parameter.annotation)

        if annotation is Request or name == "request":
            kwargs[name] = request
            continue

        if name in route_values:
            kwargs[name] = bind_value(annotation, route_values[name], path=name)
            continue

        if name in request.query:
            kwargs[name] = bind_value(annotation, request.query[name], path=name)
            continue

        if annotation is not inspect._empty:
            if is_dataclass(annotation):
                if payload is None:
                    payload = request.json()
                kwargs[name] = bind_payload(annotation, payload)
                continue
            if scope.registered(annotation):
                kwargs[name] = scope.resolve(annotation)
                continue

        if parameter.default is inspect._empty:
            raise ValueError(f"Missing value for parameter '{name}'")

    result = handler(**kwargs)
    if inspect.iscoroutine(result):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            result = asyncio.run(result)
        else:
            raise RuntimeError(
                "Cannot await coroutine handler in a running event loop. "
                "Spry's WSGI pipeline is synchronous; use the ASGI interface "
                "or define a sync handler."
            )
    return result
