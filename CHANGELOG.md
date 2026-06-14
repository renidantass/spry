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

### Documentation

- Added English README (README_EN.md)
- Added English documentation pages: index, getting-started, architecture, api-development, mvc-development, orm-data, auth-security, testing, tooling-cli, deployment, troubleshooting
- Added English taskboard example (examples/taskboard-en)
- Added auth-api example with JWT authentication (examples/auth-api)
- Updated pyproject.toml with PyPI metadata (license, authors, classifiers, keywords, urls)
- Added GitHub Actions workflow for PyPI publishing

### Changed

- Initial release

[0.1.0]: https://github.com/renidantass/spry/releases/tag/v0.1.0

## v0.2.3 (2026-06-14)

### Fix

- Phase 2 resilience — JSON safety, multipart limits, CORS Vary, CSRF edge cases, cookie attributes
- critical resilience fixes — SQL injection prevention, threading locks, CSRF fix, concurrency tests

## v0.2.2 (2026-06-14)

### Refactor

- extract TokenSigner, remove stack frame magic and CLI REPL, add tests

## v0.2.1 (2026-06-14)

### Fix

- remove paths filter from deploy-docs workflow to trigger on every push

## v0.2.0 (2026-06-14)

### Feat

- automate CI/CD, versioning, docs deployment, and agent instructions

### Fix

- configure git before cz bump so commit/tag creation works
- add version field to commitizen and fix version_files regex
- add version to commitizen config and handle no-bump in publish workflow
- remove backslash from f-string expression in Breadcrumb.render

## v0.1.3 (2026-06-14)

## v0.1.2 (2026-06-14)

### Feat

- auto-discover dbset from __models__, organize seeders/ dir

### Fix

- csrf in partial views, password verification in login

### Refactor

- split controllers, models, data into separate packages

## v0.1.1 (2026-06-14)

## v0.1.0 (2026-06-14)

### Fix

- remove invalid Framework classifier for PyPI
