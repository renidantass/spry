---
title: Pour commencer
order: 1
description: Installation, premier projet et premiers pas avec Spry
tags: installation, démarrage, tutoriel
---

## Prérequis

- Python **3.11+**
- pip

## Installation

```bash
pip install spry-core
```

Pour installer avec le support de base de données supplémentaire :

```bash
pip install spry-core[postgres]   # PostgreSQL
pip install spry-core[mysql]      # MySQL/MariaDB
pip install spry-core[sqlserver]  # SQL Server
pip install spry-core[jinja2]     # Templates Jinja2
pip install spry-core[all]        # Tout
```

## Premier projet en 5 minutes

```bash
spry new taskboard
cd taskboard
spry run --app taskboard.app:create_app
```

Accédez à `http://127.0.0.1:8000/todos` — votre API est déjà en ligne.

## Première application manuelle

```python
from dataclasses import dataclass
from spry.app import AppBuilder
from spry.controllers import ControllerBase
from spry.orm import DbContext, dbset, key
from spry.routing import controller, get, post

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
        self.db.save()
        return self.created(f"/todos/{todo.id}", todo)

builder = AppBuilder()
builder.add_db_context(AppDbContext)
app = builder.build()
```

{% note type="tip" %}
Vous n'avez pas besoin d'enregistrer les contrôleurs manuellement. Le `AppBuilder` découvre automatiquement les classes avec `@controller`.
{% endnote %}

## Structure du projet

```
main.py              → Point d'entrée
appsettings.json     → Configuration (hôte, port, base de données)
src/
  taskboard/
    app.py           → AppBuilder
    controllers.py   → Contrôleurs HTTP
    data.py          → Entités et DbContext
    seed.py          → Données initiales
```

## Hot reload

```bash
spry watch --app taskboard.app:create_app
```

## Prochaines étapes

- [Guide API](/docs/api-development) — Contrôleurs, handlers, middleware
- [Guide MVC](/docs/mvc-development) — Vues, layouts, HTML côté serveur
- [ORM et Données](/docs/orm-data) — DbContext, migrations, relations
