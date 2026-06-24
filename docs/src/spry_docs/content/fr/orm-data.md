---
title: ORM et Données
order: 4
description: DbContext, DbSet, migrations, relations et requêtes
tags: orm, données, migrations, base de données
---

## DbContext et DbSet

L'ORM de Spry est inspiré d'Entity Framework Core :

```python
from spry.orm import DbContext, dbset, key
from dataclasses import dataclass

@dataclass(slots=True)
class Product:
    id: int | None = key()
    name: str = ""
    price: float = 0.0

class StoreDbContext(DbContext):
    products = dbset(Product)
```

## Bases de Données Supportées

Spry supporte plusieurs bases de données via l'URL de connexion :

```python
# SQLite (par défaut, sans dépendances)
db = StoreDbContext("sqlite:///store.db")

# PostgreSQL (pip install spry-core[postgres])
db = StoreDbContext("postgresql://utilisateur:motdepasse@localhost:5432/store")

# MySQL (pip install spry-core[mysql])
db = StoreDbContext("mysql://utilisateur:motdepasse@localhost:3306/store")

# SQL Server (pip install spry-core[sqlserver])
db = StoreDbContext("mssql://sa:CHANGE_ME@localhost:1433/store")
```

### Connection Pooling

Pour la production avec PostgreSQL/MySQL, activez le pool :

```python
db = StoreDbContext("postgresql://...", pool_size=10)
```

## Requêtes

```python
# Tous les enregistrements
all_products = db.products.all()

# Filtre par champs
cheap = db.products.where(price=10.0)

# Premier enregistrement
product = db.products.first(name="Tablette")

# Recherche par clé primaire
product = db.products.find(1)

# Tri
ordered = db.products.order_by("name")
ordered_desc = db.products.order_by("-price")

# Pagination
page = db.products.paginate(page=1, per_page=20)
# page.items, page.total, page.has_next, page.has_prev

# Skip / Take
results = db.products.skip(10).take(5)

# Agrégations
total = db.products.sum("price")
moyenne = db.products.avg("price")
minimum = db.products.min("price")
maximum = db.products.max("price")

# SQL Brut
from spry.orm import DbSet
results = DbSet.from_sql(db, Product, "SELECT * FROM products WHERE price > ?", [50])
```

## CRUD

```python
# Create
product = Product(name="Ordinateur", price=2999.0)
db.products.add(product)
db.save()

# Read
product = db.products.find(product.id)

# Update
product.price = 2499.0
db.products.update(product)
db.save()

# Delete
db.products.remove(product.id)
db.save()
```

## Relations

```python
from spry.orm import foreign_key, navigation, navigation_many

@dataclass
class Author:
    id: int | None = key()
    name: str = ""
    posts: list = navigation_many("Post", foreign_key="author_id")

@dataclass
class Post:
    id: int | None = key()
    title: str = ""
    author_id: int = foreign_key("Author")
    author: Author | None = navigation("Author", foreign_key="author_id")

class BlogDb(DbContext):
    authors = dbset(Author)
    posts = dbset(Post)
```

Chargez les relations avec `include` :

```python
author = db.authors.find(1)
db.authors.include(author, "posts")
```

## Migrations

```bash
# Créer une migration
spry migrate add initial --context app.data:AppDbContext

# Appliquer
spry migrate apply --database app.db

# Rollback (annule la dernière migration)
spry migrate rollback --database app.db
```

## Transaction

```python
with db.transaction():
    db.products.add(product1)
    db.products.add(product2)
    # commit automatique à la fin du bloc
    # rollback automatique en cas d'erreur
```

## Enum

```python
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

@dataclass
class User:
    id: int | None = key()
    status: Status = Status.ACTIVE
```

## Bonnes pratiques

- Utilisez toujours `save()` après `add()`, `update()`, `remove()`
- Préférez `transaction()` pour les opérations impliquant plusieurs entités
- Utilisez `pool_size` en production pour éviter de créer des connexions par requête
- Configurez l'URL de la base de données via `appsettings.json` ou la variable d'environnement `APP__database__url`
