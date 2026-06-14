---
title: Testing
order: 7
description: TestClient, integration tests and best practices
tags: testing, testclient, tests
---

## TestClient

`TestClient` allows you to test your application without needing an HTTP server:

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

## TestClient Methods

| Method | Description |
|---|---|
| `client.get(path, ...)` | GET request |
| `client.post(path, ...)` | POST request |
| `client.put(path, ...)` | PUT request |
| `client.patch(path, ...)` | PATCH request |
| `client.delete(path, ...)` | DELETE request |

## Parameters

```python
# JSON body
resp = client.post("/api", json={"key": "value"})

# Form data
resp = client.post("/login", data={"user": "admin", "pass": "123"})

# File upload
resp = client.post("/upload", files={
    "file": ("photo.jpg", image_bytes, "image/jpeg")
})

# Headers and Cookies
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

## Best Practices

- Create a `conftest.py` with a `TestClient` fixture
- Use in-memory databases for tests (`:memory:`)
- Test error scenarios (400, 404, 422, 500)
- Test authentication and authorization separately
