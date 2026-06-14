---
title: Arquitetura
order: 9
description: Visão interna do framework, pipeline e componentes
tags: arquitetura, framework, design
---

## Bootstrap

```
AppBuilder
  ├── Carrega appsettings.json
  ├── Registra serviços no ServiceCollection
  ├── Descobre controllers automaticamente
  ├── Constrói middleware pipeline
  └── build() → Application
```

## Pipeline por Request

```
Request → Middleware 1 → Middleware 2 → ... → Controller
                                                    │
Response ← Middleware 1 ← Middleware 2 ← ... ← Response
```

Cada middleware pode:
- Modificar o request (autenticação, logging)
- Modificar a resposta (headers, compressão)
- Interromper o pipeline (autorização, rate limiting)

## DI Container

O Spry possui um container de injeção de dependência com três lifetimes:

| Lifetime | Comportamento |
|---|---|
| **Singleton** | Uma única instância para toda a aplicação |
| **Scoped** | Uma instância por request |
| **Transient** | Uma nova instância a cada resolução |

```python
builder.add_singleton(MeuServico)
builder.add_scoped(DbContext)
builder.add_transient(Helper)
```

## Controllers

```
ControllerBase (API)
  └── Controller (MVC + views)
       └── AuthenticatedController (MVC + auth)
```

## ORM

```
DbContext
  ├── Connection pooling
  ├── Schema generation
  ├── Migrations
  └── DbSet[T]
       ├── CRUD (add, update, remove)
       ├── Queries (all, where, first, find)
       ├── OrderBy, Pagination
       ├── Aggregations (sum, avg, min, max)
       ├── Include (eager loading)
       └── Raw SQL (from_sql)
```

## Backends de Banco

```
DatabaseBackend (ABC)
  ├── SqliteBackend   (stdlib, sem dependências)
  ├── PostgresBackend (psycopg2)
  ├── MySqlBackend    (pymysql)
  ├── MariaDBBackend  (pymysql)
  └── SqlServerBackend (pyodbc)
```

## Template Engine

```
TemplateEngine (ABC)
  ├── SpryTemplateEngine (padrão, for/if/include/filters)
  └── Jinja2TemplateEngine (opcional, spry[jinja2])
```
