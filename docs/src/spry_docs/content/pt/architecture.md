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

## Métodos do AppBuilder

O `AppBuilder` é o ponto de entrada principal para configurar uma aplicação Spry:

| Método | Descrição |
|--------|-----------|
| `add_controller(cls)` | Registra uma classe de controller |
| `add_db_context(cls)` | Registra uma classe DbContext |
| `add_cors(origins, ...)` | Habilita CORS com as origens fornecidas |
| `add_auth(secret_key, ...)` | Habilita autenticação baseada em cookie |
| `add_jwt_auth(secret_key, ...)` | Habilita autenticação JWT |
| `add_csrf()` | Habilita proteção CSRF |
| `add_session()` | Habilita middleware de sessão |
| `add_rate_limiter(max, window)` | Habilita rate limiting |
| `add_security_headers(csp, hsts, xfo)` | Define headers de segurança |
| `add_request_logging()` | Loga todas as requisições recebidas |
| `add_compression(min_size)` | Habilita compressão de resposta |
| `add_views(engine, views_dir)` | Configura o motor de templates |
| `add_error_handler(status_code)` | Registra um handler de erro customizado |
| `add_settings(settings_cls)` | Adiciona configuração tipada |
| `add_server_header(value)` | Define o header Server na resposta |
| `add_default_deny()` | Nega todas as rotas por padrão (whitelist) |
| `add_auth_logging()` | Loga eventos de autenticação |
| `add_static_files(prefix, dir)` | Serve arquivos estáticos |
| `add_route_group(prefix)` | Agrupa rotas sob um prefixo comum |
| `set_debug(bool)` | Habilita/desabilita modo debug |
| `set_max_body_size(bytes)` | Define o tamanho máximo do corpo |
| `use(middleware)` | Adiciona um middleware ao pipeline |
| `map_get(path, handler)` | Registra uma rota GET |
| `map_post(path, handler)` | Registra uma rota POST |
| `map_put(path, handler)` | Registra uma rota PUT |
| `map_patch(path, handler)` | Registra uma rota PATCH |
| `map_delete(path, handler)` | Registra uma rota DELETE |
| `build()` | Constrói e retorna a Application |

## Template Engine

```
TemplateEngine (ABC)
  ├── SpryTemplateEngine (padrão, for/if/include/filters)
  └── Jinja2TemplateEngine (opcional, spry[jinja2])
```
