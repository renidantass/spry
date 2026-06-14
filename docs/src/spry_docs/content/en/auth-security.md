---
title: Auth and Security
order: 5
description: CORS, CSRF, JWT, rate limiting, security headers
tags: auth, security, cors, jwt, csrf
---

## CORS

```python
builder.add_cors(origins=["https://myapp.com"])
```

For development:

```python
builder.add_cors(origins=["*"], credentials=False)
```

## Cookie Authentication

```python
builder.add_auth(secret_key=os.getenv("AUTH_SECRET"))
```

Protect routes with `@authorize`:

```python
from spry import authorize

@get("/admin")
@authorize(roles=["admin"])
def admin_panel(self):
    return {"secret": "data"}
```

## JWT Authentication

```python
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"))
```

Clients send the token in the header:

```
Authorization: Bearer <token>
```

## CSRF

```python
builder.add_csrf()
```

Spry validates CSRF via cookie + `X-CSRF-Token` header or `__csrf` form field.

## Rate Limiting

```python
builder.add_rate_limiter(max_requests=100, window=60)
```

Response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
Retry-After: 42
```

## Security Headers

```python
builder.add_security_headers(
    csp={"default-src": ["'self'"]},
    hsts=True,
    xfo="DENY",
)
```

## Debug Mode

```python
builder.set_debug(False)  # In production: hide stack traces
```

Or via `appsettings.json`:

```json
{ "server": { "debug": false } }
```

## Request Body Limit

```python
builder.set_max_body_size(10 * 1024 * 1024)  # 10MB
```

## Sessions

```python
builder.add_session()
```

```python
# In controller
request.items["session"]["user_id"] = user.id
```

## Best Practices

- Never use the default secret key (`spry-dev-secret`) in production
- Configure CORS with specific origins, not `*`
- Enable HSTS in production
- Always disable debug in production
- Use environment variables for secrets (`APP__auth__secret_key=...`)
