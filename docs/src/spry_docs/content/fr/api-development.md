---
title: Développement d'API
order: 2
description: Contrôleurs, handlers, middleware, validation et réponses
tags: api, contrôleurs, middleware, validation
---

## Contrôleurs

Les contrôleurs sont des classes qui regroupent des routes associées :

```python
from spry.controllers import ControllerBase
from spry.routing import controller, get, post

@controller("/products")
class ProductsController(ControllerBase):
    @get("/")
    def list(self):
        return {"items": ["produit1", "produit2"]}

    @post("/")
    def create(self, product: CreateProduct):
        # product est automatiquement validé à partir du body JSON
        return self.created("/products/1", product)
```

### Routes typées

Spry supporte les paramètres de route avec types :

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

Types disponibles : `int`, `float`, `slug`, `uuid`, `path`, `str`.

## ControllerBase — Helpers de réponse

| Méthode | Statut | Usage |
|---|---|---|
| `ok(value)` | 200 | Réponse JSON de succès |
| `created(location, value)` | 201 | Ressource créée |
| `bad_request(message)` | 400 | Erreur du client |
| `not_found(message)` | 404 | Ressource non trouvée |
| `no_content()` | 204 | Succès sans contenu |
| `unauthorized(message)` | 401 | Non authentifié |
| `forbidden(message)` | 403 | Sans permission |
| `redirect(location)` | 302 | Redirection |
| `json(value, status)` | — | JSON personnalisé |

## Handlers autonomes

Pour des routes simples sans contrôleur :

```python
builder.map_get("/health", lambda: {"status": "ok"})
builder.map_post("/webhook", webhook_handler)
```

## Middleware

Les middleware sont des fonctions qui enveloppent le pipeline de requête/réponse :

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

### Middleware intégrés

```python
builder.add_cors(origins=["https://monapp.com"])
builder.add_security_headers()
builder.add_rate_limiter(max_requests=100, window=60)
builder.add_request_logging()
builder.add_compression(min_size=1024)
```

## Validation

La validation de la charge utile est automatique pour les paramètres de type dataclass :

```python
from dataclasses import dataclass
from spry.validators import Email, MinLength

@dataclass
class CreateUser:
    name: str = field(metadata={"validate": [Required(), MinLength(3)]})
    email: str = field(metadata={"validate": [Email()]})
```

Les erreurs de validation retournent `422 Validation failed` avec les détails.

## Exceptions typées (ProblemDetail)

Le pipeline convertit les exceptions du module `spry.errors` en réponses `ProblemDetail` (RFC 9457) automatiquement. Levez l'exception appropriée dans n'importe quel handler :

```python
from spry import NotFoundError, ConflictError, ForbiddenError, UnauthorizedError, BadRequestError

@controller("/users")
class UsersController(ControllerBase):
    @get("/{id:int}")
    def show(self, id: int):
        user = self.db.users.find(id)
        if user is None:
            raise NotFoundError(f"utilisateur {id} non trouvé")
        return user

    @post("/")
    def create(self, payload: CreateUser):
        if self.db.users.first(email=payload.email) is not None:
            raise ConflictError("email déjà enregistré")
        return self.db.users.add(payload)
```

| Exception | Statut | Usage typique |
| --- | --- | --- |
| `BadRequestError` | 400 | Entrée malformée hors validation |
| `UnauthorizedError` | 401 | Identifiant absent ou invalide |
| `ForbiddenError` | 403 | Authentifié mais sans permission |
| `NotFoundError` | 404 | Ressource inexistante |
| `ConflictError` | 409 | Doublon ou invariant violé |
| `UnprocessableEntityError` | 422 | Validation sémantique (binding utilise le même statut avec `errors[]`) |

Toutes les exceptions non gérées deviennent `500 Internal Server Error` en production, ou la page de débogage quand `set_debug(True)`.

## OpenAPI et security schemes

Appeler `add_auth` (cookie) ou `add_jwt_auth` (Bearer) enregistre les `securitySchemes` correspondants dans la spécification OpenAPI à `/openapi.json` et marque automatiquement les routes avec `@authorize` comme protégées. Pour des schemes personnalisés :

```python
builder.add_security_scheme("ApiKeyAuth", {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
})
```

L'interface Swagger à `/docs` affiche le bouton "Authorize" automatiquement quand au moins un scheme est enregistré.

## Handlers async et streaming

Les handlers peuvent être `async def`. Le pipeline reste synchrone, mais l'adaptateur ASGI envoie chaque requête à un thread de travail via `asyncio.to_thread`, donc les coroutines fonctionnent sans erreur de boucle d'événements :

```python
@get("/async")
async def list_async():
    return await some_async_io()
```

Pour les réponses volumineuses, utilisez `StreamingResponse`, qui envoie le body en morceaux sans tout charger en mémoire :

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

`builder.add_static_files` utilise le streaming automatiquement pour les fichiers de plus de 256 Ko et honore `If-None-Match` en retournant `304` quand l'ETag correspond.

## JWT avec HS256 / HS384 / HS512

`JwtAuthService` accepte n'importe quel HMAC-SHA :

```python
builder.add_jwt_auth(secret_key=SECRET, algorithm="HS384", ttl=3600)
```

Algorithmes supportés : `HS256`, `HS384`, `HS512`. Les signatures asymétriques (`RS256`, `ES256`) ne sont pas encore intégrées.

## Middleware d'authentification

### Cookie Auth

```python
builder.add_auth(secret_key=os.getenv("AUTH_SECRET"))
```

### JWT Auth

```python
builder.add_jwt_auth(secret_key=os.getenv("JWT_SECRET"))
```

Utilisez `@authorize` pour protéger les routes :

```python
from spry.auth import authorize

@get("/admin")
@authorize(roles=["admin"])
def admin_panel(self):
    return {"secret": "data"}
```

## Tests

Utilisez le `TestClient` pour tester votre API sans serveur :

```python
from spry.testing import TestClient

def test_list_todos():
    client = TestClient(app)
    resp = client.get("/todos")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_create_todo():
    client = TestClient(app)
    resp = client.post("/todos", json={"title": "Nouveau"})
    assert resp.status_code == 201
```

{% note type="tip" %}
TestClient supporte `json=`, `data=`, `files=`, `headers=` et `cookies=`.
{% endnote %}
