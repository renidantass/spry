---
title: Deploy
order: 8
description: Produção, Docker, CI/CD e configuração por ambiente
tags: deploy, produção, docker, gunicorn
---

## Servidor WSGI

O `Application` do Spry é um callable WSGI compatível com qualquer servidor WSGI:

```bash
# Gunicorn (Linux/Mac)
pip install gunicorn
gunicorn app:create_app -w 4 -b 0.0.0.0:8000

# Waitress (Windows)
pip install waitress
waitress-serve app:create_app
```

## Servidor ASGI

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
# Usa o servidor especificado
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

## Configuração por ambiente

```json
// appsettings.json (base)
{ "database": { "url": "dev.db" } }

// appsettings.Production.json (sobrescreve)
{ "database": { "url": "postgresql://user:pass@host/db" } }
```

```bash
APP_ENVIRONMENT=Production spry run --app app:create_app
```

Variáveis de ambiente com prefixo `APP__` sobrescrevem qualquer configuração:

```bash
APP__database__url=postgresql://user:pass@host/prod_db spry run --app app:create_app
```

## Health Check

Toda aplicação Spry expõe automaticamente:

```
GET /health → {"status": "ok", "version": "0.2.5", "uptime_seconds": 1234}
```

## Logging

```python
builder.add_request_logging()
```

## Boas práticas

- Desative o debug em produção: `builder.set_debug(False)`
- Configure CORS com origins específicas
- Use secrets fortes para auth e CSRF
- Ative security headers: `builder.add_security_headers()`
- Use rate limiting: `builder.add_rate_limiter(max_requests=100)`
- Configure o limite de body: `builder.set_max_body_size(10 * 1024 * 1024)`
