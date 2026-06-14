from __future__ import annotations

import inspect
import logging
import pkgutil
import time
from pathlib import Path
from types import ModuleType
from typing import Any, TYPE_CHECKING

from spry import __version__ as _VERSION
from spry.config import Configuration
from spry.cors import CorsConfig, cors_middleware_factory
from spry.csrf import CsrfService
from spry.di import ServiceCollection
from spry.http import MAX_BODY, Request, Response
from spry.middleware import HttpContext
from spry.openapi import OpenApiBuilder, make_swagger_ui_response
from spry.routing import create_function_route, extract_controller_routes
from spry.views import ViewRenderer

if TYPE_CHECKING:
    from spry.app.application import Application


class RouteGroupBuilder:
    def __init__(self, builder: "AppBuilder", prefix: str, middlewares: list[Any]) -> None:
        self._builder = builder
        self._prefix = prefix.rstrip("/")
        self._middleware = list(middlewares)
        for m in middlewares:
            builder.use(m)

    def add_controller(self, controller_type: type) -> None:
        original_prefix = getattr(controller_type, "__spry_prefix__", "/")
        if self._prefix:
            new_prefix = self._prefix if original_prefix == "/" else f"{self._prefix}{original_prefix}"
        else:
            new_prefix = original_prefix
        self._builder.add_controller(controller_type, prefix_override=new_prefix)

    def map_get(self, path: str, handler: Any) -> None:
        full_path = f"{self._prefix}{path}" if path != "/" else self._prefix
        self._builder.map_get(full_path, handler)

    def map_post(self, path: str, handler: Any) -> None:
        full_path = f"{self._prefix}{path}" if path != "/" else self._prefix
        self._builder.map_post(full_path, handler)


class AppBuilder:
    def __init__(self, base_path: str | Path | None = None) -> None:
        self.base_path = Path(base_path or Path.cwd())
        self.configuration = Configuration.load(self.base_path)
        self.services = ServiceCollection()
        self._routes: list = []
        self._middleware: list = []
        self._registered_controllers: set[type] = set()
        self._discovery_done = False
        self._openapi_enabled = True
        self._openapi_title = "Spry API"
        self._openapi_version = _VERSION
        self._openapi_description = ""
        self._openapi_security_schemes: dict[str, dict[str, Any]] = {}
        self._debug: bool | None = None
        self._max_body_size: int | None = None
        self._error_handlers: dict[int, Any] = {}
        self._server_header_added = False

    def enable_openapi(self, title: str = "Spry API", version: str = "", description: str = "") -> None:
        if not version:
            version = _VERSION
        self._openapi_enabled = True
        self._openapi_title = title
        self._openapi_version = version
        self._openapi_description = description

    def disable_openapi(self) -> None:
        self._openapi_enabled = False

    def add_security_scheme(self, name: str, scheme: dict[str, Any]) -> None:
        self._openapi_security_schemes[name] = scheme

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def add_error_handler(self, status_code: int, handler: Any) -> None:
        self._error_handlers[status_code] = handler

    def set_max_body_size(self, size: int) -> None:
        self._max_body_size = size

    def add_settings(self, settings_type: type, section: str | None = None) -> Any:
        settings = self.configuration.bind(settings_type, section)
        self.services.add_singleton(settings_type, instance=settings)
        return settings

    def add_singleton(
        self,
        service_type: type,
        implementation: type | None = None,
        *,
        instance: Any | None = None,
        factory: Any | None = None,
    ) -> None:
        self.services.add_singleton(service_type, implementation, instance=instance, factory=factory)

    def add_scoped(self, service_type: type, implementation: type | None = None, *, factory: Any | None = None) -> None:
        self.services.add_scoped(service_type, implementation, factory=factory)

    def add_transient(self, service_type: type, implementation: type | None = None) -> None:
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

    def add_security_headers(self, *, csp: dict | None = None, hsts: bool = True, xfo: str = "DENY", ct: bool = True, referrer: str = "strict-origin-when-cross-origin", nonce: bool = False) -> None:
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

        def static_handler(path: str, request: "Request"):
            from spry.http import StreamingResponse
            file_path = (resolved / path).resolve()
            if not str(file_path).startswith(str(resolved)):
                return Response.text("Not found", 404)
            if not file_path.exists() or not file_path.is_file():
                return Response.text("Not found", 404)
            import mimetypes
            content_type, _ = mimetypes.guess_type(str(file_path))
            import hashlib
            file_size = file_path.stat().st_size

            # ETag uses size + mtime; cheap and unique enough for static assets.
            mtime = int(file_path.stat().st_mtime)
            etag_src = f"{file_size}-{mtime}".encode("utf-8")
            etag = hashlib.sha1(etag_src).hexdigest()  # noqa: S324

            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match.strip() == f'"{etag}"':
                return Response.empty(304, headers={"ETag": f'"{etag}"'})

            base_headers = {
                "Content-Type": content_type or "application/octet-stream",
                "ETag": f'"{etag}"',
                "Cache-Control": "public, max-age=3600",
            }

            # Small files: load into memory (faster, WSGI friendly).
            # Large files: stream in chunks (constant memory).
            if file_size <= 256 * 1024:
                return Response(file_path.read_bytes(), headers=base_headers)

            def chunker(block_size: int):
                with file_path.open("rb") as fp:
                    while True:
                        block = fp.read(block_size)
                        if not block:
                            return
                        yield block

            base_headers["Content-Length"] = str(file_size)
            return StreamingResponse(chunker, headers=base_headers)

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
        self.add_security_scheme("BearerAuth", {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        })

        def jwt_middleware(context: Any, next_handler: Any) -> Response:
            user = service.authenticate(context.request)
            context.request.user = user
            return next_handler()

        self.use(jwt_middleware)

    def add_auth(self, *, secret_key: str | None = None, cookie_name: str = "spry_auth") -> Any:
        from spry.auth import CookieAuthService
        auth_settings = self.configuration.section("auth")
        resolved_secret = secret_key or auth_settings.get("secret_key") or "spry-dev-secret"
        resolved_cookie = auth_settings.get("cookie_name") or cookie_name
        service = CookieAuthService(str(resolved_secret), cookie_name=str(resolved_cookie))
        self.services.add_singleton(CookieAuthService, instance=service)
        self.add_security_scheme("CookieAuth", {
            "type": "apiKey",
            "in": "cookie",
            "name": str(resolved_cookie),
        })

        def auth_middleware(context: HttpContext, next_handler: Any) -> Response:
            auth = context.services.resolve(CookieAuthService)
            context.request.user = auth.authenticate(context.request)
            return next_handler()

        self.use(auth_middleware)
        return service

    def add_csrf(self, *, cookie_name: str = "spry_csrf", field_name: str = "__csrf") -> CsrfService:
        from spry.csrf import csrf_error_response
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
        if inspect.iscoroutinefunction(middleware):
            raise TypeError(
                "Async middleware is not supported. Use sync middleware or run via ASGI."
            )
        self._middleware.append(middleware)

    def add_db_context(self, context_type: type, *, connection_string: str | None = None, section: str = "database") -> None:
        database_settings = self.configuration.section(section)
        resolved_connection = connection_string or database_settings.get("url") or database_settings.get("connection_string") or "app.db"
        self.services.add_scoped(context_type, factory=lambda _: context_type(resolved_connection))

    def add_controller(self, controller_type: type, prefix_override: str | None = None) -> None:
        if controller_type in self._registered_controllers:
            return
        self._registered_controllers.add(controller_type)
        self.services.add_transient(controller_type)
        self._routes.extend(extract_controller_routes(controller_type, prefix_override))

    def discover_controllers(self, package_name: str) -> None:
        import importlib
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

    def add_route_group(self, prefix: str, middlewares: list | None = None) -> RouteGroupBuilder:
        return RouteGroupBuilder(self, prefix, middlewares or [])

    def build(self) -> "Application":
        from spry.app.application import Application
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
                security_schemes=self._openapi_security_schemes or None,
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

        # Pre-create the Application so the /health handler can read its
        # _started_at timestamp, then mutate the route list before index
        # construction by passing the additional route into a small wrapper
        # that recomputes the index after the fact.
        provider = self.services.build_provider()
        app = Application(self.configuration, provider, final_routes, self._middleware, debug=debug, error_handlers=self._error_handlers)
        if openapi_spec is not None:
            app._openapi_spec = openapi_spec

        started_at = app._started_at

        def health_handler():
            return Response.json({
                "status": "ok",
                "version": _VERSION,
                "uptime_seconds": time.time() - started_at,
            })

        health_route = create_function_route("GET", "/health", health_handler)
        app._route_index.setdefault(health_route.method, []).append(health_route)
        app.routes.append(health_route)
        return app

    def _register_controllers_from_module(self, module: "ModuleType") -> None:
        for attribute in vars(module).values():
            if inspect.isclass(attribute) and getattr(attribute, "__spry_prefix__", None) is not None:
                self.add_controller(attribute)

    def _auto_discover_controllers(self) -> None:
        return


logger = logging.getLogger("spry.builder")
