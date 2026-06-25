from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from spry.di import ServiceScope
from spry.http import Request, Response
from spry.routing import RouteDefinition

NextHandler = Callable[[], Awaitable[Response] | Response]
Middleware = Callable[["HttpContext", NextHandler], Awaitable[Any] | Any]


@dataclass(slots=True)
class HttpContext:
    request: Request
    services: ServiceScope
    route: RouteDefinition | None
    route_values: dict[str, str]
    items: dict[str, Any] = field(default_factory=dict)
