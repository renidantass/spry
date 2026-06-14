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
  +-- build() ? Application
```

## Request Pipeline

```
Request ? Middleware 1 ? Middleware 2 ? ... ? Controller
                                                    ¦
Response ? Middleware 1 ? Middleware 2 ? ... ? Response
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

## Template Engine

```
TemplateEngine (ABC)
  +-- SpryTemplateEngine (default, for/if/include/filters)
  +-- Jinja2TemplateEngine (optional, spry[jinja2])
```
