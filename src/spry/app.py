from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import pkgutil
import signal
import sys
from dataclasses import is_dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, get_type_hints
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from spry.auth import CookieAuthService, forbidden_response, unauthorized_response
from spry.config import Configuration
from spry.cors import CorsConfig, cors_middleware_factory
from spry.csrf import CsrfService, csrf_error_response
from spry.di import ServiceCollection, ServiceProvider, ServiceScope
from spry.http import MAX_BODY, ProblemDetail, Request, Response
from spry.middleware import HttpContext, Middleware
from spry.openapi import OpenApiBuilder, make_openapi_response, make_swagger_ui_response
from spry.results import ActionResult
from spry.routing import RouteDefinition, create_function_route, extract_controller_routes
from spry.validation import ValidationError, bind_payload, bind_value
from spry.views import ViewRenderer

logger = logging.getLogger("spry")

_VERSION = "0.1.0"
_START_TIME: float = 0.0


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

    def create_scope(self) -> ServiceScope:
        return self.services.create_scope()

    def run(self, host: str | None = None, port: int | None = None) -> None:
        server_settings = self.configuration.section("server")
        bind_host = host or server_settings.get("host", "127.0.0.1")
        bind_port = int(port or server_settings.get("port", 8000))

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        with make_server(bind_host, bind_port, self) as server:
            logger.info("Spry listening on http://%s:%s", bind_host, bind_port)
            server.serve_forever()

    def __call__(self, environ: dict[str, Any], start_response: Any) -> list[bytes]:
        request = Request.from_environ(environ)
        response = self._handle_sync(request)
        response._request_scheme = request.scheme
        return response.to_wsgi(start_response)

    def _handle_error(self, status: int, request: Request, error: Exception) -> Response | None:
        handler = self._error_handlers.get(status)
        if handler:
            return handler(request)
        return None

    def _handle_sync(self, request: Request) -> Response:
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
                return self._execute_pipeline(context)
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
        except ValueError as error:
            logger.warning("Bad request: %s", error)
            custom = self._handle_error(400, request, error)
            if custom:
                return custom
            return ProblemDetail(
                type="/errors/bad-request",
                title="Bad Request",
                status=400,
                detail=str(error),
            ).to_response()
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

    async def handle_request_async(self, request: Request) -> Response:
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
            response = self._handle_sync(request)
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
        for route in self.routes:
            values = route.match(method, path)
            if values is not None:
                return route, values
        return None, None

    def _invoke_route(
        self,
        route: RouteDefinition,
        scope: ServiceScope,
        request: Request,
        route_values: dict[str, str],
    ) -> Any:
        target = route.function_handler
        if route.controller_type is not None:
            controller = scope.resolve(route.controller_type)
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

        return _invoke_callable(target, scope, request, route_values)

    def _execute_pipeline(self, context: HttpContext) -> Response:
        def endpoint() -> Response:
            if context.route is None:
                return Response.json({"error": "Route not found"}, 404)
            result = self._invoke_route(
                context.route, context.services, context.request, context.route_values
            )
            return _coerce_response(result)

        next_handler = endpoint
        for middleware in reversed(self.middlewares):
            previous = next_handler
            if inspect.iscoroutinefunction(middleware):
                raise RuntimeError(
                    "Async middleware is not supported in the sync pipeline. "
                    "Use sync middleware or run via ASGI with async handlers."
                )
            def current_handler(m: Middleware = middleware, p: Any = previous) -> Response:
                return _coerce_response(m(context, p))
            next_handler = current_handler
        return next_handler()


class AppBuilder:
    def __init__(self, base_path: str | Path | None = None) -> None:
        self.base_path = Path(base_path or Path.cwd())
        self.configuration = Configuration.load(self.base_path)
        self.services = ServiceCollection()
        self._routes: list[RouteDefinition] = []
        self._middlewares: list[Middleware] = []
        self._registered_controllers: set[type[Any]] = set()
        self._default_controller_target = _infer_default_controller_target()
        self._auto_discovery_ran = False
        self._openapi_enabled = True
        self._openapi_title = "Spry API"
        self._openapi_version = "0.1.0"
        self._openapi_description = ""
        self._debug: bool | None = None
        self._max_body_size: int | None = None
        self._error_handlers: dict[int, Any] = {}
        self._server_header_added = False

    def enable_openapi(self, title: str = "Spry API", version: str = "0.1.0", description: str = "") -> None:
        self._openapi_enabled = True
        self._openapi_title = title
        self._openapi_version = version
        self._openapi_description = description

    def disable_openapi(self) -> None:
        self._openapi_enabled = False

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def add_error_handler(self, status_code: int, handler: Any) -> None:
        self._error_handlers[status_code] = handler

    def set_max_body_size(self, size: int) -> None:
        self._max_body_size = size

    def add_settings(self, settings_type: type[Any], section: str | None = None) -> Any:
        settings = self.configuration.bind(settings_type, section)
        self.services.add_singleton(settings_type, instance=settings)
        return settings

    def add_singleton(
        self,
        service_type: type[Any],
        implementation: type[Any] | None = None,
        *,
        instance: Any | None = None,
        factory: Any | None = None,
    ) -> None:
        self.services.add_singleton(service_type, implementation, instance=instance, factory=factory)

    def add_scoped(self, service_type: type[Any], implementation: type[Any] | None = None, *, factory: Any | None = None) -> None:
        self.services.add_scoped(service_type, implementation, factory=factory)

    def add_transient(self, service_type: type[Any], implementation: type[Any] | None = None) -> None:
        self.services.add_transient(service_type, implementation)

    def add_views(self, *, root_path: str | Path | None = None, views_dir: str = "views", layout: str | None = "shared/_layout", engine: str = "spry", i18n: Any = None) -> None:
        resolved_root = Path(root_path or self.base_path)
        self.services.add_singleton(
            ViewRenderer,
            factory=lambda _: ViewRenderer(resolved_root, views_dir=views_dir, default_layout=layout, engine=engine, i18n_service=i18n),
        )

    def add_server_header(self, header: str = "X-Powered-By", value: str = "Spry") -> None:
        if self._server_header_added:
            return
        self._server_header_added = True
        def server_header_middleware(context: Any, next_handler: Any) -> Response:
            response = next_handler()
            response.headers.setdefault(header, value)
            return response
        self.use(server_header_middleware)

    def add_cors(self, *, origins: list[str] | None = None, methods: list[str] | None = None, headers: list[str] | None = None, credentials: bool = False, max_age: int = 3600) -> None:
        config = CorsConfig(
            origins=origins or [],
            methods=methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            headers=headers or ["Content-Type", "Authorization", "X-CSRF-Token", "X-XSRF-Token"],
            credentials=credentials,
            max_age=max_age,
        )
        self.use(cors_middleware_factory(config))

    def add_security_headers(self, *, csp: dict[str, Any] | None = None, hsts: bool = True, xfo: str = "DENY", ct: bool = True, referrer: str = "strict-origin-when-cross-origin", nonce: bool = False) -> None:
        config = {
            "csp": csp or {"default-src": ["'self'"]},
            "hsts": hsts,
            "xfo": xfo,
            "ct": ct,
            "referrer": referrer,
            "nonce": nonce,
        }

        def security_middleware(context: Any, next_handler: Any) -> Response:
            import secrets as _secrets
            nonce_val = _secrets.token_urlsafe(16) if config["nonce"] else None
            if nonce_val is not None:
                context.request.items["csp_nonce"] = nonce_val
            response = next_handler()
            csp_directives = dict(config.get("csp", {}))
            if nonce_val:
                existing = csp_directives.get("script-src", ["'self'"])
                csp_directives["script-src"] = existing + [f"'nonce-{nonce_val}'"]
            if csp_directives:
                csp_str = "; ".join(f"{k} {' '.join(v)}" for k, v in csp_directives.items())
                response.headers["Content-Security-Policy"] = csp_str
            if config["hsts"]:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["X-Frame-Options"] = config["xfo"]
            if config["ct"]:
                response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = config["referrer"]
            return response

        self.use(security_middleware)

    def add_request_logging(self, fmt: str = "combined") -> None:
        def logging_middleware(context: Any, next_handler: Any) -> Response:
            import time as ttime
            start = ttime.time()
            request = context.request
            response = next_handler()
            duration = ttime.time() - start
            if fmt == "json":
                import json as _json
                entry = {
                    "timestamp": ttime.strftime("%Y-%m-%dT%H:%M:%S", ttime.gmtime()),
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": int(duration * 1000),
                    "ip": request.headers.get("X-Forwarded-For", request.host),
                }
                logger.info(_json.dumps(entry))
            else:
                logger.info("%s %s %s %dms", request.method, request.path, response.status_code, int(duration * 1000))
            return response
        self.use(logging_middleware)

    def add_default_deny(self, *, login_path: str = "/login", exempt_paths: list[str] | None = None) -> None:
        exempt = set(exempt_paths or [])
        exempt.add("/health")
        exempt.add("/docs")
        exempt.add("/openapi.json")

        def deny_middleware(context: Any, next_handler: Any) -> Response:
            request = context.request
            if request.user is not None:
                return next_handler()
            if request.path in exempt or request.path.startswith("/assets/"):
                return next_handler()
            if request.path.startswith(("/docs/", "/api/", "/changelog", "/playground", "/search-index.json")):
                return next_handler()
            return unauthorized_response(request, login_path)

        self.use(deny_middleware)

    def add_auth_logging(self) -> None:
        from spry.auth import LoginTracker
        tracker = LoginTracker()

        def auth_log_middleware(context: Any, next_handler: Any) -> Response:
            response = next_handler()
            if context.request.user:
                logger.info("Authenticated request: %s %s (user=%s)", context.request.method, context.request.path, context.request.user.user_id)
            return response

        self.use(auth_log_middleware)

    def add_compression(self, min_size: int = 1024) -> None:
        import gzip as gz

        def compression_middleware(context: Any, next_handler: Any) -> Response:
            response = next_handler()
            accept = context.request.headers.get("Accept-Encoding", "")
            body = response.body
            if len(body) < min_size:
                return response
            if "gzip" in accept:
                response.body = gz.compress(body)
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(response.body))
            return response

        self.use(compression_middleware)

    def add_static_files(self, url_prefix: str, directory: str | Path) -> None:
        resolved = Path(directory).resolve()

        def static_handler(path: str) -> Response:
            file_path = (resolved / path).resolve()
            if not str(file_path).startswith(str(resolved)):
                return Response.text("Not found", 404)
            if not file_path.exists() or not file_path.is_file():
                return Response.text("Not found", 404)
            import mimetypes
            content_type, _ = mimetypes.guess_type(str(file_path))
            body = file_path.read_bytes()
            import hashlib
            etag = hashlib.md5(body).hexdigest()
            resp = Response(body, headers={"Content-Type": content_type or "application/octet-stream", "ETag": f'"{etag}"', "Cache-Control": "public, max-age=3600"})
            return resp

        cleaned_prefix = url_prefix.rstrip("/")
        self._routes.append(create_function_route(
            "GET", f"{cleaned_prefix}/{{path:path}}", static_handler
        ))

    def add_rate_limiter(self, max_requests: int = 100, window: float = 60.0) -> None:
        from spry.throttling import TokenBucket, rate_limit_middleware_factory
        bucket = TokenBucket(max_requests=max_requests, window=window)
        self.use(rate_limit_middleware_factory(bucket))

    def add_session(self, cookie_name: str = "spry_session", ttl: int = 3600, idle_timeout: int = 1800, secret_key: str | None = None) -> None:
        from spry.session import SessionMiddleware
        self.use(SessionMiddleware(cookie_name=cookie_name, ttl=ttl, idle_timeout=idle_timeout, secret_key=secret_key))

    def add_jwt_auth(self, secret_key: str, algorithm: str = "HS256", ttl: int = 3600) -> None:
        from spry.auth import JwtAuthService
        service = JwtAuthService(secret_key, algorithm=algorithm, ttl=ttl)
        self.services.add_singleton(JwtAuthService, instance=service)

        def jwt_middleware(context: Any, next_handler: Any) -> Response:
            user = service.authenticate(context.request)
            context.request.user = user
            return next_handler()

        self.use(jwt_middleware)

    def add_auth(
        self,
        *,
        secret_key: str | None = None,
        cookie_name: str = "spry_auth",
    ) -> CookieAuthService:
        auth_settings = self.configuration.section("auth")
        resolved_secret = secret_key or auth_settings.get("secret_key") or "spry-dev-secret"
        resolved_cookie = auth_settings.get("cookie_name") or cookie_name
        service = CookieAuthService(str(resolved_secret), cookie_name=str(resolved_cookie))
        self.services.add_singleton(CookieAuthService, instance=service)

        def auth_middleware(context: HttpContext, next_handler: Any) -> Response:
            auth = context.services.resolve(CookieAuthService)
            context.request.user = auth.authenticate(context.request)
            return next_handler()

        self.use(auth_middleware)
        return service

    def add_csrf(
        self,
        *,
        cookie_name: str = "spry_csrf",
        field_name: str = "__csrf",
    ) -> CsrfService:
        service = CsrfService(cookie_name=cookie_name, field_name=field_name)
        self.services.add_singleton(CsrfService, instance=service)

        def csrf_middleware(context: HttpContext, next_handler: Any) -> Response:
            csrf = context.services.resolve(CsrfService)
            token, should_set_cookie = csrf.get_or_create_token(context.request)
            context.request.items["csrf_token"] = token
            context.request.items["csrf_field_name"] = csrf.field_name

            if not csrf.validate_request(context.request):
                return csrf_error_response(context.request)

            response = next_handler()
            if should_set_cookie:
                csrf.attach_cookie(response, token)
            return response

        self.use(csrf_middleware)
        return service

    def use(self, middleware: Middleware) -> None:
        self._middlewares.append(middleware)

    def add_db_context(self, context_type: type[Any], *, connection_string: str | None = None, section: str = "database") -> None:
        database_settings = self.configuration.section(section)
        resolved_connection = connection_string or database_settings.get("url") or database_settings.get("connection_string") or "app.db"
        self.services.add_scoped(context_type, factory=lambda _: context_type(resolved_connection))

    def add_controller(self, controller_type: type[Any]) -> None:
        if controller_type in self._registered_controllers:
            return
        self._registered_controllers.add(controller_type)
        self.services.add_transient(controller_type)
        self._routes.extend(extract_controller_routes(controller_type))

    def discover_controllers(self, package_name: str) -> None:
        package = importlib.import_module(package_name)
        self._register_controllers_from_module(package)
        if hasattr(package, "__path__"):
            for _, module_name, _ in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
                module = importlib.import_module(module_name)
                self._register_controllers_from_module(module)

    def map_get(self, path: str, handler: Any) -> None:
        self._routes.append(create_function_route("GET", path, handler))

    def map_post(self, path: str, handler: Any) -> None:
        self._routes.append(create_function_route("POST", path, handler))

    def map_put(self, path: str, handler: Any) -> None:
        self._routes.append(create_function_route("PUT", path, handler))

    def map_delete(self, path: str, handler: Any) -> None:
        self._routes.append(create_function_route("DELETE", path, handler))

    def map_patch(self, path: str, handler: Any) -> None:
        self._routes.append(create_function_route("PATCH", path, handler))

    def add_route_group(self, prefix: str, middlewares: list[Any] | None = None) -> "RouteGroupBuilder":
        return RouteGroupBuilder(self, prefix, middlewares or [])

    def build(self) -> Application:
        if not self._server_header_added:
            self.add_server_header()
        self._auto_discover_controllers()
        final_routes = list(self._routes)

        server_section = self.configuration.section("server")
        debug = self._debug if self._debug is not None else server_section.get("debug", False)
        max_body = self._max_body_size or MAX_BODY
        Request.set_max_body_size(max_body)

        openapi_spec = None
        if self._openapi_enabled:
            openapi = OpenApiBuilder(
                title=self._openapi_title,
                version=self._openapi_version,
                description=self._openapi_description,
            )
            if final_routes:
                openapi.add_routes(final_routes)
            openapi_spec = openapi.build()

            def openapi_json_handler():
                return Response.json(openapi_spec)

            def swagger_ui_handler():
                return make_swagger_ui_response()

            final_routes.append(create_function_route("GET", "/openapi.json", openapi_json_handler))
            final_routes.append(create_function_route("GET", "/docs", swagger_ui_handler))

        def health_handler():
            import time
            uptime = time.time() - _START_TIME
            return Response.json({
                "status": "ok",
                "version": _VERSION,
                "uptime_seconds": int(uptime),
            })

        final_routes.append(create_function_route("GET", "/health", health_handler))

        provider = self.services.build_provider()
        app = Application(self.configuration, provider, final_routes, self._middlewares, debug=debug, error_handlers=self._error_handlers)
        if openapi_spec is not None:
            app._openapi_spec = openapi_spec
        return app

    def _register_controllers_from_module(self, module: ModuleType) -> None:
        for attribute in vars(module).values():
            if inspect.isclass(attribute) and getattr(attribute, "__spry_prefix__", None) is not None:
                self.add_controller(attribute)

    def _auto_discover_controllers(self) -> None:
        if self._auto_discovery_ran:
            return
        self._auto_discovery_ran = True

        target = self._default_controller_target
        if not target:
            return

        spec = importlib.util.find_spec(target)
        if spec is None:
            return

        if spec.submodule_search_locations:
            self.discover_controllers(target)
            return

        module = importlib.import_module(target)
        self._register_controllers_from_module(module)


class RouteGroupBuilder:
    def __init__(self, builder: AppBuilder, prefix: str, middlewares: list[Any]) -> None:
        self._builder = builder
        self._prefix = prefix.rstrip("/")
        self._middlewares = list(middlewares)

        for m in middlewares:
            builder.use(m)

    def add_controller(self, controller_type: type[Any]) -> None:
        original_prefix = getattr(controller_type, "__spry_prefix__", "/")
        new_prefix = original_prefix
        if self._prefix:
            if new_prefix == "/":
                new_prefix = self._prefix
            else:
                new_prefix = f"{self._prefix}{new_prefix}"
        setattr(controller_type, "__spry_prefix__", new_prefix)
        self._builder.add_controller(controller_type)

    def map_get(self, path: str, handler: Any) -> None:
        full_path = f"{self._prefix}{path}" if path != "/" else self._prefix
        self._builder.map_get(full_path, handler)

    def map_post(self, path: str, handler: Any) -> None:
        full_path = f"{self._prefix}{path}" if path != "/" else self._prefix
        self._builder.map_post(full_path, handler)


def _invoke_callable(handler: Any, scope: ServiceScope, request: Request, route_values: dict[str, str]) -> Any:
    signature = inspect.signature(handler)
    type_hints = get_type_hints(handler)
    kwargs: dict[str, Any] = {}
    payload = None

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
                payload = request.json() if payload is None else payload
                kwargs[name] = bind_payload(annotation, payload)
                continue
            if scope.registered(annotation):
                kwargs[name] = scope.resolve(annotation)
                continue

        if parameter.default is inspect._empty:
            raise ValueError(f"Missing value for parameter '{name}'")

    result = handler(**kwargs)
    if inspect.iscoroutine(result):
        result = asyncio.run(result)
    return result


def _coerce_response(result: ActionResult) -> Response:
    if isinstance(result, Response):
        return result
    if result is None:
        return Response.empty(204)
    if isinstance(result, (dict, list)) or is_dataclass(result):
        return Response.json(result)
    if isinstance(result, bytes):
        return Response(result)
    return Response.text(str(result))


import warnings as _warnings


def deprecated(message: str = "") -> Any:
    """Decorator to mark functions as deprecated."""
    def decorator(func: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _warnings.warn(
                f"{func.__name__} is deprecated. {message}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def _infer_default_controller_target() -> str | None:
    for frame_info in inspect.stack()[2:]:
        module_name = frame_info.frame.f_globals.get("__name__")
        if not module_name or module_name.startswith("spry."):
            continue
        if module_name in {"__main__", "builtins"}:
            continue
        return module_name.partition(".")[0] or module_name
    return None


def _handle_signal(signum: int, frame: Any) -> None:
    logger.info("Received signal %s, shutting down gracefully...", signum)
    sys.exit(0)
