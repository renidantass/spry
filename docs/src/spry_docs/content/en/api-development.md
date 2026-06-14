---
title: API Development
order: 2
description: Controllers, handlers, middleware, validation and responses
tags: api, controllers, middleware, validation
---

## Controllers

Controllers are classes that group related routes:

```python
from spry import ControllerBase, controller, get, post

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
from spry import authorize

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
