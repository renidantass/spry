---
title: Testes
order: 7
description: TestClient, testes de integração e boas práticas
tags: testes, testclient, testing
---

## TestClient

O `TestClient` permite testar sua aplicação sem precisar de um servidor HTTP:

```python
from spry.testing import TestClient

def test_list_todos():
    client = TestClient(app)
    resp = client.get("/todos")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_create_todo():
    client = TestClient(app)
    resp = client.post("/todos", json={"title": "Novo"})
    assert resp.status_code == 201
```

## Métodos do TestClient

| Método | Descrição |
|---|---|
| `client.get(path, ...)` | Requisição GET |
| `client.post(path, ...)` | Requisição POST |
| `client.put(path, ...)` | Requisição PUT |
| `client.patch(path, ...)` | Requisição PATCH |
| `client.delete(path, ...)` | Requisição DELETE |

## Parâmetros

```python
# JSON body
resp = client.post("/api", json={"key": "value"})

# Form data
resp = client.post("/login", data={"user": "admin", "pass": "123"})

# File upload
resp = client.post("/upload", files={
    "file": ("foto.jpg", image_bytes, "image/jpeg")
})

# Headers e Cookies
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

## Boas práticas

- Crie um `conftest.py` com uma fixture do `TestClient`
- Use bancos de dados em memória para testes (`:memory:`)
- Teste cenários de erro (400, 404, 422, 500)
- Teste autenticação e autorização separadamente
