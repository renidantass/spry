---
title: Getting Started
order: 1
description: Installation, first project, and first steps with Spry
tags: installation, quickstart, tutorial
---

## Requirements

- Python **3.11+**
- pip

## Installation

```bash
pip install spry-core
```

With database support:

```bash
pip install spry-core[postgres]
pip install spry-core[mysql]
pip install spry-core[sqlserver]
pip install spry-core[all]
```

## Quick Start

```bash
spry new taskboard
cd taskboard
spry run --app taskboard.app:create_app
```

Visit `http://127.0.0.1:8000/todos` — your API is running.

## Your First App

```python
from dataclasses import dataclass
from spry import AppBuilder, ControllerBase, DbContext, controller, dbset, get, key, post

@dataclass(slots=True)
class Todo:
    id: int | None = key()
    title: str = ""
    done: bool = False

class AppDbContext(DbContext):
    todos = dbset(Todo)

@controller("/todos")
class TodosController(ControllerBase):
    def __init__(self, db: AppDbContext):
        self.db = db

    @get("/")
    def list(self):
        return self.db.todos.all()

    @post("/")
    def create(self, todo: Todo):
        self.db.todos.add(todo)
        self.db.save_changes()
        return self.created(f"/todos/{todo.id}", todo)

builder = AppBuilder()
builder.add_db_context(AppDbContext)
app = builder.build()
```

## Project Structure

```
main.py              → Entrypoint
appsettings.json     → Configuration (host, port, database)
src/
  taskboard/
    app.py           → AppBuilder
    controllers.py   → Controllers
    data.py          → Entities and DbContext
    seed.py          → Seed data
```

## Next Steps

- [API Development](/docs/api-development) — Controllers, handlers, middleware
- [ORM and Data](/docs/orm-data) — DbContext, migrations, relationships
- [Auth and Security](/docs/auth-security) — CORS, JWT, CSRF, rate limiting
