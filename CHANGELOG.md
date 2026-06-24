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

## v0.8.8 (2026-06-24)

### Fix

- move OPENCODE_GO_API_KEY to job-level env for proper inheritance

## v0.8.7 (2026-06-24)

### Fix

- restore opencode-go/deepseek-v4-flash as requested

## v0.8.6 (2026-06-24)

### Fix

- correct model name to deepseek-v4-flash-free

## v0.8.5 (2026-06-24)

### Fix

- try opencode/ provider instead of opencode-go/

## v0.8.4 (2026-06-24)

### Fix

- use correct secret OPENCODE_GO_API_KEY
- restore model opencode-go/deepseek-v4-flash with ANTHROPIC_API_KEY secret

## v0.8.3 (2026-06-24)

### Fix

- use correct secret name OPENCODE_GO_API_KEY for model

## v0.8.2 (2026-06-24)

### Fix

- correct model name from opencode-go/deepseek-v4-flash to deepseek-v4-flash

## v0.8.1 (2026-06-24)

### Fix

- configure git credentials for branch push in issue workflow

## v0.8.0 (2026-06-24)

### Feat

- automated issue-to-PR pipeline with quality gates and auto-merge

## v0.7.0 (2026-06-16)

### Feat

- implement opencode-review workflow, update save_changes to save in various files

## v0.6.0 (2026-06-14)

### Feat

- typed exceptions, OpenAPI security, streaming, async ASGI, HS384/HS512

### Fix

- CI failures, add uptime_seconds, InMemoryStore, save_changes aliases

### Refactor

- split monolithic app.py, orm.py, views.py into subpackages

## v0.5.2 (2026-06-14)

### Refactor

- replace flat 'from spry import X' with explicit submodule imports

## v0.5.1 (2026-06-14)

### Fix

- remove hardcoded versions, fix example bugs

## v0.5.0 (2026-06-14)

### Feat

- flag SVGs, API page styling, playground 405 fix

## v0.4.1 (2026-06-14)

### Fix

- docs site — favicon, sidebar locale, search index, playground error handling

## v0.4.0 (2026-06-14)

### Feat

- docs site overhaul — i18n, contenteditable playground, Ctrl+K, content refresh

## v0.3.0 (2026-06-14)

### Feat

- docs site polish — playground syntax highlight, 404 page, broken link fixes

## v0.2.5 (2026-06-14)

### Fix

- Swagger UI blank page + DX overhaul — auto-discovery, CLI defaults, scaffold fixes

## v0.2.4 (2026-06-14)

### Fix

- Phase 3 resilience — memory leaks, i18n crash, cookie expiration, ReDoS, LOW items

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
