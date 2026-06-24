---
title: Authentification et Sécurité
order: 5
description: CORS, CSRF, JWT, rate limiting, en-têtes de sécurité
tags: auth, sécurité, cors, jwt, csrf
---

## CORS

```python
builder.add_cors(origins=["https://monapp.com"])
```

Pour le développement :

```python
builder.add_cors(origins=["*"], credentials=False)
```

## Authentification par Cookie

```python
builder.add_auth(secret_key=os.getenv("AUTH_SECRET"))
```

Protégez les routes avec `@authorize` :

```python
from spry.auth import authorize

@get("/admin")
@authorize(roles=["admin"])
def admin_panel(self):
    return {"secret": "data"}
```

## Authentification JWT

```python
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"))
# ou avec algorithme et TTL personnalisés :
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"), algorithm="HS384", ttl=3600)
```

Algorithmes supportés : `HS256`, `HS384`, `HS512` (HMAC-SHA de la suite OpenAPI). `RS256` et `ES256` nécessitent l'option `cryptography` et ne sont pas encore intégrés.

Les clients envoient le token dans l'en-tête :

```
Authorization: Bearer <token>
```

`add_jwt_auth` enregistre automatiquement un `BearerAuth` (http/bearer/JWT) dans les `securitySchemes` de l'OpenAPI à `/openapi.json`, donc l'interface Swagger à `/docs` affiche déjà le bouton "Authorize".

## Schemes de sécurité OpenAPI

La spécification OpenAPI expose les schemes enregistrés pour que le client puisse tester l'Authorization dans Swagger UI. Les schemes par défaut sont créés par `add_auth` (`apiKey` en cookie) et `add_jwt_auth` (`http` Bearer). Pour enregistrer des schemes personnalisés :

```python
builder.add_security_scheme("ApiKeyAuth", {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
})
```

Les routes décorées avec `@authorize` reçoivent automatiquement le champ `security` dans l'OpenAPI.

## CSRF

```python
builder.add_csrf()
```

Spry valide le CSRF via cookie + en-tête `X-CSRF-Token` ou champ de formulaire `__csrf`.

## Rate Limiting

```python
builder.add_rate_limiter(max_requests=100, window=60)
```

En-têtes de réponse :

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
Retry-After: 42
```

## En-têtes de Sécurité

```python
builder.add_security_headers(
    csp={"default-src": ["'self'"]},
    hsts=True,
    xfo="DENY",
)
```

## Mode Debug

```python
builder.set_debug(False)  # En production : cache les stack traces
```

Ou via `appsettings.json` :

```json
{ "server": { "debug": false } }
```

## Limite de Body

```python
builder.set_max_body_size(10 * 1024 * 1024)  # 10 Mo
```

## Sessions

```python
builder.add_session()
```

```python
# Dans le contrôleur
request.items["session"]["user_id"] = user.id
```

## Bonnes pratiques

- N'utilisez jamais la clé secrète par défaut (`spry-dev-secret`) en production
- Configurez CORS avec des origines spécifiques, pas `*`
- Activez HSTS en production
- Désactivez toujours le debug en production
- Utilisez des variables d'environnement pour les secrets (`APP__auth__secret_key=...`)
