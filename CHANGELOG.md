# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-14

### Added

- Core framework: AppBuilder, DI container, middleware pipeline, routing
- ORM: DbContext, DbSet, migrations, connection pooling
- Controllers: ControllerBase (API), Controller (MVC), AuthenticatedController
- Template engine: SpryTemplateEngine (for/if/include/filters) + Jinja2 support
- Authentication: Cookie-based (HMAC) + JWT (HS256) + role-based authorization
- Security: CORS, CSRF, rate limiting, security headers, session management
- Validation: Dataclass binding, custom validators (Email, MinLength, Regex, etc.)
- OpenAPI: Auto-generated spec + Swagger UI
- CLI: new, run, watch, migrate (add/apply/rollback), seed, routes, db shell
- Multi-database: SQLite, PostgreSQL, MySQL, MariaDB, SQL Server
- Testing: TestClient with JSON, form data, file upload support
- i18n: I18nService with .po/.mo loader, {% trans %} template tag
- Background tasks, event dispatcher
- Health check endpoint (/health)
- Config: .env support, multi-environment appsettings

### Changed

- Initial release

[0.1.0]: https://github.com/anomalyco/spry/releases/tag/v0.1.0
