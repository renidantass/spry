---
title: Desenvolvimento de API
order: 2
description: Controllers, handlers, middleware, validação e respostas
tags: api, controllers, middleware, validation
---

## Controllers

Controllers são classes que agrupam rotas relacionadas:

```python
from spry import ControllerBase, controller, get, post

@controller("/products")
class ProductsController(ControllerBase):
    @get("/")
    def list(self):
        return {"items": ["produto1", "produto2"]}

    @post("/")
    def create(self, product: CreateProduct):
        # product é automaticamente validado do body JSON
        return self.created("/products/1", product)
```

### Rotas tipadas

Spry suporta parâmetros de rota com tipos:

```python
@get("/{id:int}")
def by_id(self):
    return {"handler": "by_id"}

@get("/{uuid:uuid}")
def by_uuid(self):
    return {"handler": "by_uuid"}

@get("/{slug}")
def by_slug(self):
    return {"handler": "by_slug"}
```

Tipos disponíveis: `int`, `float`, `slug`, `uuid`, `path`, `str`.

## ControllerBase — Helpers de resposta

| Método | Status | Uso |
|---|---|---|
| `ok(value)` | 200 | Resposta JSON de sucesso |
| `created(location, value)` | 201 | Recurso criado |
| `bad_request(message)` | 400 | Erro do cliente |
| `not_found(message)` | 404 | Recurso não encontrado |
| `no_content()` | 204 | Sucesso sem conteúdo |
| `unauthorized(message)` | 401 | Não autenticado |
| `forbidden(message)` | 403 | Sem permissão |
| `redirect(location)` | 302 | Redirecionamento |
| `json(value, status)` | — | JSON customizado |

## Standalone handlers

Para rotas simples sem controller:

```python
builder.map_get("/health", lambda: {"status": "ok"})
builder.map_post("/webhook", webhook_handler)
```

## Middleware

Middleware são funções que envolvem o pipeline de request/response:

```python
def timing_middleware(context, next_handler):
    import time
    start = time.time()
    response = next_handler()
    duration = time.time() - start
    response.headers["X-Duration-Ms"] = str(int(duration * 1000))
    return response

builder.use(timing_middleware)
```

### Middleware embutidos

```python
builder.add_cors(origins=["https://meuapp.com"])
builder.add_security_headers()
builder.add_rate_limiter(max_requests=100, window=60)
builder.add_request_logging()
builder.add_compression(min_size=1024)
```

## Validação

A validação de payload é automática para parâmetros do tipo dataclass:

```python
from dataclasses import dataclass
from spry.validators import Email, MinLength

@dataclass
class CreateUser:
    name: str = field(metadata={"validate": [Required(), MinLength(3)]})
    email: str = field(metadata={"validate": [Email()]})
```

Erros de validação retornam `422 Validation failed` com detalhes.

## Middleware de autenticação

### Cookie Auth

```python
builder.add_auth(secret_key=os.getenv("AUTH_SECRET"))
```

### JWT Auth

```python
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"))
```

Use `@authorize` para proteger rotas:

```python
from spry import authorize

@get("/admin")
@authorize(roles=["admin"])
def admin_panel(self):
    return {"secret": "data"}
```

## Testes

Use o `TestClient` para testar sua API sem servidor:

```python
from spry.testing import TestClient

def test_list_todos():
    client = TestClient(app)
    resp = client.get("/todos")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_create_todo():
    client = TestClient(app)
    resp = client.post("/todos", json={"title": "Novo"})
    assert resp.status_code == 201
```

{% note type="tip" %}
TestClient suporta `json=`, `data=`, `files=`, `headers=`, e `cookies=`.
{% endnote %}
