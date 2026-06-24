---
title: Déploiement
order: 8
description: Production, Docker, CI/CD et configuration par environnement
tags: déploiement, production, docker, gunicorn
---

## Serveur WSGI

Le `Application` de Spry est un callable WSGI compatible avec n'importe quel serveur WSGI :

```bash
# Gunicorn (Linux/Mac)
pip install gunicorn
gunicorn app:create_app -w 4 -b 0.0.0.0:8000

# Waitress (Windows)
pip install waitress
waitress-serve app:create_app
```

## Serveur ASGI

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
# Utilise le serveur spécifié
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

## Configuration par environnement

```json
// appsettings.json (base)
{ "database": { "url": "dev.db" } }

// appsettings.Production.json (surcharge)
{ "database": { "url": "postgresql://user:pass@host/db" } }
```

```bash
APP_ENVIRONMENT=Production spry run --app app:create_app
```

Les variables d'environnement avec le préfixe `APP__` surchargent toute configuration :

```bash
APP__database__url=postgresql://user:pass@host/prod_db spry run --app app:create_app
```

## Health Check

Toute application Spry expose automatiquement :

```
GET /health → {"status": "ok", "version": "0.2.5", "uptime_seconds": 1234}
```

## Logging

```python
builder.add_request_logging()
```

## Bonnes pratiques

- Désactivez le debug en production : `builder.set_debug(False)`
- Configurez CORS avec des origines spécifiques
- Utilisez des secrets forts pour l'auth et le CSRF
- Activez les en-têtes de sécurité : `builder.add_security_headers()`
- Utilisez le rate limiting : `builder.add_rate_limiter(max_requests=100)`
- Configurez la limite de body : `builder.set_max_body_size(10 * 1024 * 1024)`
