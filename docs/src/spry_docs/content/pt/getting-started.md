---
title: Começando
order: 1
description: Instalação, primeiro projeto, e primeiros passos com Spry
tags: instalação, quickstart, tutorial
---

## Requisitos

- Python **3.11+**
- pip

## Instalação

```bash
pip install spry-core
```

Para instalar com suporte a banco de dados adicional:

```bash
pip install spry-core[postgres]   # PostgreSQL
pip install spry-core[mysql]      # MySQL/MariaDB
pip install spry-core[sqlserver]  # SQL Server
pip install spry-core[jinja2]     # Jinja2 templates
pip install spry-core[all]        # Tudo
```

## Primeiro projeto em 5 minutos

```bash
spry new taskboard
cd taskboard
spry run --app taskboard.app:create_app
```

Acesse `http://127.0.0.1:8000/todos` — sua API já está no ar.

## Primeiro app manual

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
    def __init__(self, db: AppDbContext) -> None:
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

{% note type="tip" %}
Você não precisa registrar controllers manualmente. O `AppBuilder` descobre automaticamente classes com `@controller`.
{% endnote %}

## Estrutura do projeto

```
main.py              → Entrypoint
appsettings.json     → Configuração (host, porta, banco)
src/
  taskboard/
    app.py           → AppBuilder
    controllers.py   → Controllers HTTP
    data.py          → Entidades e DbContext
    seed.py          → Dados iniciais
```

## Hot reload

```bash
spry watch --app taskboard.app:create_app
```

## Próximos passos

- [Guia de API](/docs/api-development) — Controllers, handlers, middleware
- [Guia MVC](/docs/mvc-development) — Views, layouts, HTML server-side
- [ORM e Dados](/docs/orm-data) — DbContext, migrações, relacionamentos
