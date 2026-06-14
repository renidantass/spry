from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import pkgutil
import signal
from dataclasses import is_dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from spry import __version__ as _VERSION
from spry.config import Configuration
from spry.cors import CorsConfig, cors_middleware_factory
from spry.csrf import CsrfService, csrf_error_response
from spry.db.url import DatabaseUrl
from spry.di import ServiceCollection, ServiceProvider, ServiceScope
from spry.http import MAX_BODY, ProblemDetail, Request, Response
from spry.middleware import HttpContext, Middleware
from spry.openapi import OpenApiBuilder, make_swagger_ui_response
from spry.results import ActionResult
from spry.routing import (
    RouteDefinition,
    create_function_route,
    extract_controller_routes,
)
from spry.validation import ValidationError, bind_value
from spry.views import ViewRenderer

logger = logging.getLogger("spry")


def _handle_signal_factory(server: Any):
    def handler(signum: int, frame: Any) -> None:
        logger.info("Received signal %s, shutting down gracefully...", signum)
        try:
            server.shutdown()
        except Exception:
            pass
    return handler


class Application:
    def __init__(
        self,
        configuration: Configuration,
        services: ServiceProvider,
        routes: list[RouteDefinition],
        middlewares: list[Middleware],
        debug: bool = False,
        error_handlers: dict[int, Any] | None = None,
    ) -> None:
        self.configuration = configuration
        self.services = services
        self.routes = routes
        self.middlewares = middlewares
        self.debug = debug
        self._error_handlers = error_handlers or {}
        self._openapi_spec: dict[str, Any] | None = None
        self._route_index: dict[str, list[RouteDefinition]] = {}
        for route in routes:
            self._route_index.setdefault(route.method, []).append(route)

    @property
    def openapi_spec(self) -> dict[str, Any] | None:
        return self._openapi_spec

    def create_scope(self) -> ServiceScope:
        return self.services.create_scope()

    def run(self, host: str | None = None, port: int | None = None) -> None:
        server_settings = self.configuration.section("server")
        bind_host = host or server_settings.get("host", "127.0.0.1")
        bind_port = int(port or server_settings.get("port", 8000))

        with make_server(bind_host, bind_port, self) as server:
            previous_term = signal.getsignal(signal.SIGTERM)
            previous_int = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGTERM, _handle_signal_factory(server))
            signal.signal(signal.SIGINT, _handle_signal_factory(server))
            try:
                logger.info("Spry listening on http://%s:%s", bind_host, bind_port)
                server.serve_forever()
            finally:
                signal.signal(signal.SIGTERM, previous_term)
                signal.signal(signal.SIGINT, previous_int)
        self._shutdown()

    def __call__(self, environ: dict[str, Any], start_response: Any) -> list[bytes]:
        request = Request.from_environ(environ)
        response = self._handle_sync(request)
        return response.to_wsgi(start_response)

    def _handle_error(self, status: int, request: Request, error: Exception) -> Response | None:
        handler = self._error_handlers.get(status)
        if handler:
            return handler(request)
        return None

    def _handle_sync(self, request: Request) -> Response:
        from spry.errors import BadRequestError, SpryError
        try:
            scope = self.services.create_scope()
            try:
                route, route_values = self._resolve_route(request.method, request.path)
                context = HttpContext(
                    request=request,
                    services=scope,
                    route=route,
                    route_values=route_values or {},
                )
                response = self._execute_pipeline(context)
                self._finalize_response(response, request)
                return response
            finally:
                scope.dispose()
        except ValidationError as error:
            logger.debug("Validation error: %s", error.errors)
            custom = self._handle_error(422, request, error)
            if custom:
                return custom
            return ProblemDetail(
                type="/errors/validation",
                title="Validation Failed",
                status=422,
                detail="One or more fields failed validation",
                errors=error.errors,
            ).to_response()
        except json.JSONDecodeError as error:
            logger.debug("Invalid JSON: %s", error.msg)
            custom = self._handle_error(400, request, error)
            if custom:
                return custom
            return ProblemDetail(
                type="/errors/json",
                title="Invalid JSON",
                status=400,
                detail=f"Invalid JSON payload: {error.msg}",
            ).to_response()
        except SpryError as error:
            custom = self._handle_error(error.meta.status_code, request, error)
            if custom:
                return custom
            return error.to_response()
        except ValueError as error:
            logger.warning("Bad request: %s", error)
            custom = self._handle_error(400, request, error)
            if custom:
                return custom
            return BadRequestError(str(error)).to_response()
        except Exception as error:
            logger.exception("Unhandled error handling request %s %s", request.method, request.path)
            custom = self._handle_error(500, request, error)
            if custom:
                return custom
            if self.debug:
                from spry.debug import render_debug_page
                html = render_debug_page(error, request)
                return Response.html(html, 500)
            return ProblemDetail(
                type="/errors/internal",
                title="Internal Server Error",
                status=500,
                detail="An unexpected error occurred",
            ).to_response()

    def handle_request(self, request: Request) -> Response:
        return self._handle_sync(request)

    async def asgi(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            raise RuntimeError("Spry ASGI support only handles HTTP scopes")

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break

        if len(body) > MAX_BODY:
            response = Response.json({"error": f"Request body exceeds maximum size of {MAX_BODY} bytes"}, 413)
        else:
            headers = {
                key.decode("latin-1").replace("_", "-").title(): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            raw_query = parse_qs(scope.get("query_string", b"").decode("utf-8"), keep_blank_values=True)
            request = Request(
                method=scope.get("method", "GET"),
                path=scope.get("path", "/") or "/",
                query={key: values[-1] for key, values in raw_query.items()},
                headers=headers,
                body=bytes(body),
                scheme=scope.get("scheme", "http"),
                host=headers.get("Host", "localhost"),
            )
            # Run the sync pipeline off the event loop. This also lets async
            # handlers work because asyncio.run is usable from the worker thread.
            response = await asyncio.to_thread(self._handle_sync, request)
            response._request_scheme = request.scheme

        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": [(key.lower().encode("latin-1"), str(value).encode("latin-1")) for key, value in response.header_items()],
            }
        )
        await send({"type": "http.response.body", "body": response.body})

    def _resolve_route(self, method: str, path: str) -> tuple[RouteDefinition | None, dict[str, str] | None]:
        for route in self._route_index.get(method, ()):
            values = route.match(method, path)
            if values is not None:
                return route, values
        return None, None

    def _finalize_response(self, response: Response, request: Request) -> None:
        """Apply request-scoped metadata that handlers couldn't know at write time.

        Currently ensures Set-Cookie headers carry the Secure flag when the
        request came in over HTTPS (handlers run before the scheme is known).
        """
        response._request_scheme = request.scheme
        if request.scheme != "https":
            return
        patched: list[tuple[str, str]] = []
        for name, value in response._extra_headers:
            if name.lower() == "set-cookie" and "secure" not in value.lower():
                patched.append((name, f"{value}; Secure"))
            else:
                patched.append((name, value))
        response._extra_headers = patched

    def _invoke_route(
        self,
        route: RouteDefinition,
        scope: ServiceScope,
        request: Request,
        route_values: dict[str, str],
    ) -> Any:
        from spry.app.invocation import invoke_callable
        from spry.auth import forbidden_response, unauthorized_response
        target = route.function_handler
        if route.controller_type is not None:
            controller = scope.resolve(route.controller_type)
            controller.request = request
            target = getattr(controller, route.handler_name or "")
        if target is None:
            raise RuntimeError("Route handler not found")

        authorize_settings = getattr(target, "__spry_authorize__", None)
        if authorize_settings is None and getattr(target, "__func__", None) is not None:
            authorize_settings = getattr(target.__func__, "__spry_authorize__", None)
        if authorize_settings is not None and request.user is None:
            return unauthorized_response(request, authorize_settings.get("login_path", "/login"))
        if authorize_settings is not None:
            required_roles = authorize_settings.get("roles", [])
            if required_roles and request.user is not None and not any(request.user.is_in_role(role) for role in required_roles):
                return forbidden_response(request, authorize_settings.get("access_denied_path", "/access-denied"))

        return invoke_callable(target, scope, request, route_values)

    def _execute_pipeline(self, context: HttpContext) -> Response:
        from spry.app.response_coercion import coerce_response

        def endpoint() -> Response:
            if context.route is None:
                return Response.json({"error": "Route not found"}, 404)
            result = self._invoke_route(
                context.route, context.services, context.request, context.route_values
            )
            return coerce_response(result)

        next_handler = endpoint
        for middleware in reversed(self.middlewares):
            previous = next_handler
            def current_handler(m: Middleware = middleware, p: Any = previous) -> Response:
                return coerce_response(m(context, p))
            next_handler = current_handler
        return next_handler()

    def _shutdown(self) -> None:
        from spry.orm import dispose_all_pools
        dispose_all_pools()
