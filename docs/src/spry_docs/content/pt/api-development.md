---
title: Desenvolvimento de API
order: 2
description: Controllers, handlers, middleware, validação e respostas
tags: api, controllers, middleware, validation
---

## Controllers

Controllers são classes que agrupam rotas relacionadas:

```python
from spry.controllers import ControllerBase
from spry.routing import controller, get, post

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

## Exceções tipadas (ProblemDetail)

A pipeline converte exceções do módulo `spry.errors` em respostas `ProblemDetail` (RFC 9457) automaticamente. Levante a exceção apropriada em qualquer handler:

```python
from spry import NotFoundError, ConflictError, ForbiddenError, UnauthorizedError, BadRequestError

@controller("/users")
class UsersController(ControllerBase):
    @get("/{id:int}")
    def show(self, id: int):
        user = self.db.users.find(id)
        if user is None:
            raise NotFoundError(f"user {id} not found")
        return user

    @post("/")
    def create(self, payload: CreateUser):
        if self.db.users.first(email=payload.email) is not None:
            raise ConflictError("email already registered")
        return self.db.users.add(payload)
```

| Exceção | Status | Uso típico |
| --- | --- | --- |
| `BadRequestError` | 400 | Entrada malformada fora de validação |
| `UnauthorizedError` | 401 | Credencial ausente ou inválida |
| `ForbiddenError` | 403 | Autenticado mas sem permissão |
| `NotFoundError` | 404 | Recurso inexistente |
| `ConflictError` | 409 | Duplicidade ou invariante violada |
| `UnprocessableEntityError` | 422 | Validação semântica (binding usa o mesmo status com `errors[]`) |

Todas as exceções não tratadas viram `500 Internal Server Error` em produção, ou a página de debug quando `set_debug(True)`.

## OpenAPI e security schemes

Chamar `add_auth` (cookie) ou `add_jwt_auth` (Bearer) registra o `securitySchemes` correspondente no spec OpenAPI em `/openapi.json` e marca automaticamente as rotas com `@authorize` como protegidas. Para schemes customizados:

```python
builder.add_security_scheme("ApiKeyAuth", {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
})
```

A UI Swagger em `/docs` passa a exibir o botão "Authorize" automaticamente quando há ao menos um scheme registrado.

## Handlers async e streaming

Handlers podem ser `async def`. O pipeline continua síncrono, mas o adapter ASGI despacha cada request para uma thread de trabalho via `asyncio.to_thread`, então coroutines funcionam sem erro de event loop:

```python
@get("/async")
async def list_async():
    return await some_async_io()
```

Para respostas grandes use `StreamingResponse`, que envia o body em chunks sem carregar tudo em memória:

```python
from spry import StreamingResponse

@get("/export.csv")
def export():
    def chunks(block_size: int = 64 * 1024):
        with open("big.csv", "rb") as fp:
            while True:
                buf = fp.read(block_size)
                if not buf:
                    return
                yield buf
    return StreamingResponse(chunks, headers={"Content-Type": "text/csv"})
```

`builder.add_static_files` usa streaming automaticamente para arquivos acima de 256 KB e honra `If-None-Match` retornando `304` quando o ETag bate.

## JWT com HS256 / HS384 / HS512

`JwtAuthService` aceita qualquer HMAC-SHA:

```python
builder.add_jwt_auth(secret_key=SECRET, algorithm="HS384", ttl=3600)
```

Algoritmos suportados: `HS256`, `HS384`, `HS512`. Assinaturas assimétricas (`RS256`, `ES256`) ainda não foram integradas.

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
from spry.auth import authorize

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
