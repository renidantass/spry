---
title: Tests
order: 7
description: TestClient, tests d'intégration et bonnes pratiques
tags: tests, testclient, testing
---

## TestClient

Le `TestClient` permet de tester votre application sans avoir besoin d'un serveur HTTP :

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

## Méthodes du TestClient

| Méthode | Description |
|---|---|
| `client.get(path, ...)` | Requête GET |
| `client.post(path, ...)` | Requête POST |
| `client.put(path, ...)` | Requête PUT |
| `client.patch(path, ...)` | Requête PATCH |
| `client.delete(path, ...)` | Requête DELETE |

## Paramètres

```python
# JSON body
resp = client.post("/api", json={"key": "value"})

# Form data
resp = client.post("/login", data={"user": "admin", "pass": "123"})

# File upload
resp = client.post("/upload", files={
    "file": ("photo.jpg", image_bytes, "image/jpeg")
})

# En-têtes et Cookies
resp = client.get("/secure", headers={"Authorization": "Bearer token"},
                   cookies={"session": "abc123"})
```

## TestResponse

```python
resp = client.get("/todos")
resp.status_code   # 200
resp.json()        # [{"id": 1, ...}]
resp.text          # '[{"id": 1, ...}]'
resp.headers       # {"Content-Type": "application/json"}
resp.cookies       # {"session_id": "abc123"}
```

## Bonnes pratiques

- Créez un `conftest.py` avec une fixture du `TestClient`
- Utilisez des bases de données en mémoire pour les tests (`:memory:`)
- Testez les scénarios d'erreur (400, 404, 422, 500)
- Testez l'authentification et l'autorisation séparément
