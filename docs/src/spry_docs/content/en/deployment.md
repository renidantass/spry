---
title: Deployment
order: 8
description: Production, Docker, CI/CD and environment configuration
tags: deploy, production, docker, gunicorn
---

## WSGI Server

Spry's `Application` is a WSGI callable compatible with any WSGI server:

```bash
# Gunicorn (Linux/Mac)
pip install gunicorn
gunicorn app:create_app -w 4 -b 0.0.0.0:8000

# Waitress (Windows)
pip install waitress
waitress-serve app:create_app
```

## ASGI Server

```bash
# Uvicorn
pip install uvicorn
uvicorn app:create_app --host 0.0.0.0 --port 8000

# Hypercorn
pip install hypercorn
hypercorn app:create_app --bind 0.0.0.0:8000
```

## CLI `spry run --server`

```bash
# Use the specified server
spry run --app app:create_app --server gunicorn --host 0.0.0.0 --port 8000
```

## Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install spry-core
EXPOSE 8000
CMD ["gunicorn", "app:create_app", "-w", "4", "-b", "0.0.0.0:8000"]
```

## Environment Configuration

```json
// appsettings.json (base)
{ "database": { "url": "dev.db" } }

// appsettings.Production.json (overrides)
{ "database": { "url": "postgresql://user:pass@host/db" } }
```

```bash
APP_ENVIRONMENT=Production spry run --app app:create_app
```

Environment variables with `APP__` prefix override any configuration:

```bash
APP__database__url=postgresql://user:pass@host/prod_db spry run --app app:create_app
```

## Health Check

Every Spry application automatically exposes:

```
GET /health ? {"status": "ok", "version": "0.2.5", "uptime_seconds": 1234}
```

## Logging

```python
builder.add_request_logging()
```

## Best Practices

- Disable debug in production: `builder.set_debug(False)`
- Configure CORS with specific origins
- Use strong secrets for auth and CSRF
- Enable security headers: `builder.add_security_headers()`
- Use rate limiting: `builder.add_rate_limiter(max_requests=100)`
- Configure body size limit: `builder.set_max_body_size(10 * 1024 * 1024)`
