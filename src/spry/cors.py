from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from spry.http import Response

logger = logging.getLogger("spry.cors")


@dataclass
class CorsConfig:
    origins: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    headers: list[str] = field(default_factory=lambda: ["Content-Type", "Authorization", "X-CSRF-Token", "X-XSRF-Token"])
    credentials: bool = False
    max_age: int = 3600


def cors_middleware_factory(config: CorsConfig) -> Any:

    if not config.origins:
        logger.warning(
            "CORS is enabled but no origins configured. "
            "Use builder.add_cors(origins=[...]) to allow specific origins. "
            "Requests from browsers will be blocked until configured."
        )

    def cors_middleware(context: Any, next_handler: Any) -> Response:
        request = context.request
        response = next_handler()

        origin = request.headers.get("Origin", "")
        if not origin or not config.origins:
            return response

        if "*" in config.origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin in config.origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            return response

        if config.credentials and "*" not in config.origins:
            response.headers["Access-Control-Allow-Credentials"] = "true"

        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Methods"] = ", ".join(config.methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(config.headers)
            response.headers["Access-Control-Max-Age"] = str(config.max_age)
            response.status_code = 204
            response.body = b""

        return response

    return cors_middleware
