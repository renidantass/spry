---
title: Architecture
order: 9
description: Framework internals, pipeline and components
tags: architecture, framework, design
---

## Bootstrap

```
AppBuilder
  +-- Loads appsettings.json
  +-- Registers services in ServiceCollection
  +-- Discovers controllers automatically
  +-- Builds middleware pipeline
  +-- build() → Application
```

## Request Pipeline

```
Request → Middleware 1 → Middleware 2 → ... → Controller
                                                    │
Response ← Middleware 1 ← Middleware 2 ← ... ← Response
```

Each middleware can:
- Modify the request (authentication, logging)
- Modify the response (headers, compression)
- Interrupt the pipeline (authorization, rate limiting)

## DI Container

Spry has a dependency injection container with three lifetimes:

| Lifetime | Behavior |
|---|---|
| **Singleton** | Single instance for the entire application |
| **Scoped** | One instance per request |
| **Transient** | A new instance on every resolution |

```python
builder.add_singleton(MyService)
builder.add_scoped(DbContext)
builder.add_transient(Helper)
```

## Controllers

```
ControllerBase (API)
  +-- Controller (MVC + views)
       +-- AuthenticatedController (MVC + auth)
```

## ORM

```
DbContext
  +-- Connection pooling
  +-- Schema generation
  +-- Migrations
  +-- DbSet[T]
       +-- CRUD (add, update, remove)
       +-- Queries (all, where, first, find)
       +-- OrderBy, Pagination
       +-- Aggregations (sum, avg, min, max)
       +-- Include (eager loading)
       +-- Raw SQL (from_sql)
```

## Database Backends

```
DatabaseBackend (ABC)
  +-- SqliteBackend   (stdlib, no dependencies)
  +-- PostgresBackend (psycopg2)
  +-- MySqlBackend    (pymysql)
  +-- MariaDBBackend  (pymysql)
  +-- SqlServerBackend (pyodbc)
```

## AppBuilder Methods

The `AppBuilder` is the main entry point for configuring a Spry application:

| Method | Description |
|--------|-------------|
| `add_controller(cls)` | Registers a controller class |
| `add_db_context(cls)` | Registers a DbContext class |
| `add_cors(origins, ...)` | Enables CORS with the given origins |
| `add_auth(secret_key, ...)` | Enables cookie-based authentication |
| `add_jwt_auth(secret_key, ...)` | Enables JWT-based authentication |
| `add_csrf()` | Enables CSRF protection |
| `add_session()` | Enables session middleware |
| `add_rate_limiter(max_requests, window)` | Enables rate limiting |
| `add_security_headers(csp, hsts, xfo)` | Sets security headers |
| `add_request_logging()` | Logs all incoming requests |
| `add_compression(min_size)` | Enables response compression |
| `add_views(engine, views_dir)` | Configures the template engine |
| `add_error_handler(status_code)` | Registers a custom error handler |
| `add_settings(settings_cls)` | Adds typed configuration settings |
| `add_server_header(value)` | Sets the Server response header |
| `add_default_deny()` | Deny all routes by default (whitelist approach) |
| `add_auth_logging()` | Logs authentication events |
| `add_static_files(prefix, directory)` | Serves static files from a directory |
| `add_route_group(prefix)` | Groups routes under a common prefix |
| `set_debug(bool)` | Enables/disables debug mode |
| `set_max_body_size(bytes)` | Sets the maximum request body size |
| `use(middleware)` | Adds a middleware function to the pipeline |
| `map_get(path, handler)` | Registers a GET route |
| `map_post(path, handler)` | Registers a POST route |
| `map_put(path, handler)` | Registers a PUT route |
| `map_patch(path, handler)` | Registers a PATCH route |
| `map_delete(path, handler)` | Registers a DELETE route |
| `build()` | Builds and returns the Application |

## Template Engine

```
TemplateEngine (ABC)
  +-- SpryTemplateEngine (default, for/if/include/filters)
  +-- Jinja2TemplateEngine (optional, spry[jinja2])
```
