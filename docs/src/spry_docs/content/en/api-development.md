---
title: API Development
order: 2
description: Controllers, handlers, middleware, validation and responses
tags: api, controllers, middleware, validation
---

## Controllers

Controllers are classes that group related routes:

```python
from spry.controllers import ControllerBase
from spry.routing import controller, get, post

@controller("/products")
class ProductsController(ControllerBase):
    @get("/")
    def list(self):
        return {"items": ["product1", "product2"]}

    @post("/")
    def create(self, product: CreateProduct):
        # product is automatically validated from JSON body
        return self.created("/products/1", product)
```

### Typed Routes

Spry supports route parameters with types:

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

Available types: `int`, `float`, `slug`, `uuid`, `path`, `str`.

## ControllerBase — Response Helpers

| Method | Status | Usage |
|---|---|---|
| `ok(value)` | 200 | Successful JSON response |
| `created(location, value)` | 201 | Resource created |
| `bad_request(message)` | 400 | Client error |
| `not_found(message)` | 404 | Resource not found |
| `no_content()` | 204 | Success without content |
| `unauthorized(message)` | 401 | Not authenticated |
| `forbidden(message)` | 403 | No permission |
| `redirect(location)` | 302 | Redirect |
| `json(value, status)` | 200 | Custom JSON |

## Standalone handlers

For simple routes without a controller:

```python
builder.map_get("/health", lambda: {"status": "ok"})
builder.map_post("/webhook", webhook_handler)
```

## Middleware

Middleware are functions that wrap the request/response pipeline:

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

### Built-in Middleware

```python
builder.add_cors(origins=["https://myapp.com"])
builder.add_security_headers()
builder.add_rate_limiter(max_requests=100, window=60)
builder.add_request_logging()
builder.add_compression(min_size=1024)
```

## Validation

Payload validation is automatic for dataclass parameters:

```python
from dataclasses import dataclass
from spry.validators import Email, MinLength

@dataclass
class CreateUser:
    name: str = field(metadata={"validate": [Required(), MinLength(3)]})
    email: str = field(metadata={"validate": [Email()]})
```

Validation errors return `422 Validation failed` with details.

## Typed exceptions (ProblemDetail)

The pipeline converts exceptions from `spry.errors` into `ProblemDetail` (RFC 9457) responses automatically. Raise the appropriate exception in any handler:

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

| Exception | Status | Typical use |
| --- | --- | --- |
| `BadRequestError` | 400 | Malformed input outside validation |
| `UnauthorizedError` | 401 | Missing or invalid credential |
| `ForbiddenError` | 403 | Authenticated without permission |
| `NotFoundError` | 404 | Resource does not exist |
| `ConflictError` | 409 | Duplicate or invariant violation |
| `UnprocessableEntityError` | 422 | Semantic validation (auto-binding uses the same status with `errors[]`) |

Unhandled exceptions become `500 Internal Server Error` in production, or the debug page when `set_debug(True)`.

## OpenAPI and security schemes

Calling `add_auth` (cookie) or `add_jwt_auth` (Bearer) registers the matching `securitySchemes` entry in the OpenAPI spec at `/openapi.json` and automatically tags every route guarded with `@authorize`. For custom schemes:

```python
builder.add_security_scheme("ApiKeyAuth", {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
})
```

The Swagger UI at `/docs` shows the "Authorize" button automatically when at least one scheme is registered.

## Async handlers and streaming

Handlers can be `async def`. The pipeline itself stays sync, but the ASGI entry point dispatches each request to a worker thread via `asyncio.to_thread`, so coroutines work without the usual "asyncio.run() in a running loop" error:

```python
@get("/async")
async def list_async():
    return await some_async_io()
```

For large responses use `StreamingResponse`, which sends the body in chunks without loading it entirely into memory:

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

`builder.add_static_files` uses streaming automatically for files above 256 KB and honors `If-None-Match`, returning `304` when the ETag matches.

## JWT with HS256 / HS384 / HS512

`JwtAuthService` accepts any HMAC-SHA:

```python
builder.add_jwt_auth(secret_key=SECRET, algorithm="HS384", ttl=3600)
```

Currently supported: `HS256`, `HS384`, `HS512`. Asymmetric algorithms (`RS256`, `ES256`) are not yet wired up.

## Authentication Middleware

### Cookie Auth

```python
builder.add_auth(secret_key=os.getenv("AUTH_SECRET"))
```

### JWT Auth

```python
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"))
```

Use `@authorize` to protect routes:

```python
from spry.auth import authorize

@get("/admin")
@authorize(roles=["admin"])
def admin_panel(self):
    return {"secret": "data"}
```

## Testing

Use `TestClient` to test your API without a server:

```python
from spry.testing import TestClient

def test_list_todos():
    client = TestClient(app)
    resp = client.get("/todos")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_create_todo():
    client = TestClient(app)
    resp = client.post("/todos", json={"title": "New todo"})
    assert resp.status_code == 201
```

{% note type="tip" %}
TestClient supports `json=`, `data=`, `files=`, `headers=`, and `cookies=`.
{% endnote %}
