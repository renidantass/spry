try:
    import tomllib
    from pathlib import Path
    _pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    __version__ = tomllib.load(_pyproject.open("rb")).get("project", {}).get("version", "0.1.0")
except Exception:
    try:
        from importlib.metadata import version as _v
        __version__ = _v("spry-core")
    except Exception:
        __version__ = "0.1.0"

from spry.app import AppBuilder, Application

# Infrastructure — DI, config, events, i18n, testing, tasks, token_signer
from spry.config import Configuration

# Data / ORM — DbContext, DbSet, database backends
from spry.data import (
    DatabaseBackend,
    DatabaseMigrator,
    DbContext,
    DbSet,
    Page,
    column,
    dbset,
    foreign_key,
    get_backend,
    key,
    navigation,
    navigation_many,
    parse_database_url,
)

# Data Annotations — validation, validators
from spry.data_annotations import (
    Email,
    MaxLength,
    MinLength,
    Range,
    Regex,
    Required,
    ValidationError,
    email,
    max_length,
    min_length,
    range_validator,
    regex,
    required,
    validate,
    validate_model,
)
from spry.di import ServiceCollection, ServiceProvider
from spry.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    SpryError,
    UnauthorizedError,
    UnprocessableEntityError,
)
from spry.events import EventDispatcher
from spry.i18n import I18nService

# Security — auth, cors, csrf, sessions, throttling
from spry.security import (
    CookieAuthService,
    CorsConfig,
    CsrfService,
    JwtAuthService,
    PasswordHasher,
    SessionMiddleware,
    SessionStore,
    TokenBucket,
    UserPrincipal,
    authorize,
)
from spry.tasks import BackgroundTask, BackgroundWorker
from spry.testing import TestClient, TestResponse
from spry.token_signer import TokenSigner

# Web layer — http, controllers, routing, results, middleware, views, openapi
from spry.web import (
    ActionResult,
    AuthenticatedController,
    Controller,
    ControllerBase,
    HtmlString,
    HttpContext,
    OpenApiBuilder,
    Request,
    Response,
    SpryTemplateEngine,
    TemplateEngine,
    UploadedFile,
    ViewRenderer,
    bad_request,
    controller,
    created,
    delete,
    get,
    no_content,
    not_found,
    ok,
    patch,
    post,
    put,
    serve_static_file,
)

__all__ = [
    "AppBuilder",
    "Application",
    "AuthenticatedController",
    "BackgroundTask",
    "BackgroundWorker",
    "BadRequestError",
    "Configuration",
    "ConflictError",
    "Controller",
    "ControllerBase",
    "CookieAuthService",
    "CorsConfig",
    "CsrfService",
    "DatabaseBackend",
    "DatabaseMigrator",
    "DbContext",
    "DbSet",
    "Email",
    "EventDispatcher",
    "ForbiddenError",
    "HtmlString",
    "HttpContext",
    "I18nService",
    "JwtAuthService",
    "MaxLength",
    "MinLength",
    "NotFoundError",
    "OpenApiBuilder",
    "Page",
    "PasswordHasher",
    "Range",
    "Regex",
    "Request",
    "Required",
    "Response",
    "StreamingResponse",
    "ServiceCollection",
    "ServiceProvider",
    "SessionMiddleware",
    "SessionStore",
    "SpryError",
    "SpryTemplateEngine",
    "TemplateEngine",
    "TestClient",
    "TestResponse",
    "TokenBucket",
    "UnauthorizedError",
    "UnprocessableEntityError",
    "UploadedFile",
    "UserPrincipal",
    "ValidationError",
    "ViewRenderer",
    "ActionResult",
    "authorize",
    "bad_request",
    "column",
    "controller",
    "created",
    "dbset",
    "delete",
    "email",
    "foreign_key",
    "get",
    "get_backend",
    "key",
    "max_length",
    "min_length",
    "navigation",
    "navigation_many",
    "no_content",
    "not_found",
    "ok",
    "parse_database_url",
    "patch",
    "post",
    "put",
    "range_validator",
    "regex",
    "required",
    "serve_static_file",
    "validate",
    "validate_model",
]
