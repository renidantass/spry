---
title: Autenticação e Segurança
order: 5
description: CORS, CSRF, JWT, rate limiting, security headers
tags: auth, segurança, cors, jwt, csrf
---

## CORS

```python
builder.add_cors(origins=["https://meuapp.com"])
```

Para desenvolvimento:

```python
builder.add_cors(origins=["*"], credentials=False)
```

## Autenticação via Cookie

```python
builder.add_auth(secret_key=os.getenv("AUTH_SECRET"))
```

Proteja rotas com `@authorize`:

```python
from spry.auth import authorize

@get("/admin")
@authorize(roles=["admin"])
def admin_panel(self):
    return {"secret": "data"}
```

## Autenticação JWT

```python
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"))
# ou com algoritmo e TTL customizados:
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"), algorithm="HS384", ttl=3600)
```

Algoritmos suportados: `HS256`, `HS384`, `HS512` (HMAC-SHA do OpenAPI suite). `RS256` e `ES256` exigem a extra opcional `cryptography` e ainda não foram integrados.

Clientes enviam o token no header:

```
Authorization: Bearer <token>
```

O `add_jwt_auth` registra automaticamente um `BearerAuth` (http/bearer/JWT) nos `securitySchemes` do OpenAPI em `/openapi.json`, então o Swagger UI em `/docs` já mostra o botão "Authorize".

## OpenAPI security schemes

O spec OpenAPI expõe os schemes registrados para o cliente testar Authorization no Swagger UI. Os schemes default são criados por `add_auth` (`apiKey` em cookie) e `add_jwt_auth` (`http` Bearer). Para registrar schemes customizados:

```python
builder.add_security_scheme("ApiKeyAuth", {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
})
```

Rotas decoradas com `@authorize` recebem automaticamente o campo `security` no OpenAPI.

## CSRF

```python
builder.add_csrf()
```

O Spry valida CSRF via cookie + header `X-CSRF-Token` ou campo de formulário `__csrf`.

## Rate Limiting

```python
builder.add_rate_limiter(max_requests=100, window=60)
```

Headers de resposta:

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
builder.set_debug(False)  # Em produção: esconde stack traces
```

Ou via `appsettings.json`:

```json
{ "server": { "debug": false } }
```

## Limite de Body

```python
builder.set_max_body_size(10 * 1024 * 1024)  # 10MB
```

## Sessões

```python
builder.add_session()
```

```python
# No controller
request.items["session"]["user_id"] = user.id
```

## Boas práticas

- Nunca use a secret key padrão (`spry-dev-secret`) em produção
- Configure CORS com origins específicas, não `*`
- Habilite HSTS em produção
- Sempre desative o debug em produção
- Use variáveis de ambiente para secrets (`APP__auth__secret_key=...`)
