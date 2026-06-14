---
title: ORM and Data
order: 4
description: DbContext, DbSet, migrations, relationships and queries
tags: orm, data, migrations, database
---

## DbContext and DbSet

Spry's ORM is inspired by Entity Framework Core:

```python
from spry import DbContext, dbset, key
from dataclasses import dataclass

@dataclass(slots=True)
class Product:
    id: int | None = key()
    name: str = ""
    price: float = 0.0

class StoreDbContext(DbContext):
    products = dbset(Product)
```

## Supported Databases

Spry supports multiple databases via connection URL:

```python
# SQLite (default, no dependencies)
db = StoreDbContext("sqlite:///store.db")

# PostgreSQL (pip install spry-core[postgres])
db = StoreDbContext("postgresql://user:password@localhost:5432/store")

# MySQL (pip install spry-core[mysql])
db = StoreDbContext("mysql://user:password@localhost:3306/store")

# SQL Server (pip install spry-core[sqlserver])
db = StoreDbContext("mssql://sa:CHANGE_ME@localhost:1433/store")
```

### Connection Pooling

For production with PostgreSQL/MySQL, enable pooling:

```python
db = StoreDbContext("postgresql://...", pool_size=10)
```

## Queries

```python
# All records
all_products = db.products.all()

# Filter by fields
cheap = db.products.where(price=10.0)

# First record
product = db.products.first(name="Tablet")

# Find by primary key
product = db.products.find(1)

# Ordering
ordered = db.products.order_by("name")
ordered_desc = db.products.order_by("-price")

# Pagination
page = db.products.paginate(page=1, per_page=20)
# page.items, page.total, page.has_next, page.has_prev

# Skip / Take
results = db.products.skip(10).take(5)

# Aggregations
total = db.products.sum("price")
average = db.products.avg("price")
minimum = db.products.min("price")
maximum = db.products.max("price")

# Raw SQL
from spry.orm import DbSet
results = DbSet.from_sql(db, Product, "SELECT * FROM products WHERE price > ?", [50])
```

## CRUD

```python
# Create
product = Product(name="Notebook", price=2999.0)
db.products.add(product)
db.save_changes()

# Read
product = db.products.find(product.id)

# Update
product.price = 2499.0
db.products.update(product)
db.save_changes()

# Delete
db.products.remove(product.id)
db.save_changes()
```

## Relationships

```python
from spry import foreign_key, navigation, navigation_many

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

Load relationships with `include`:

```python
author = db.authors.find(1)
db.authors.include(author, "posts")
```

## Migrations

```bash
# Create migration
spry migrate add initial --context app.data:AppDbContext

# Apply
spry migrate apply --database app.db

# Rollback (undoes last migration)
spry migrate rollback --database app.db
```

## Transaction

```python
with db.transaction():
    db.products.add(product1)
    db.products.add(product2)
    # automatic commit at the end of the block
    # automatic rollback on error
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

## Best Practices

- Always use `save_changes()` after `add()`, `update()`, `remove()`
- Prefer `transaction()` for operations involving multiple entities
- Use `pool_size` in production to avoid creating connections per request
- Configure the database URL via `appsettings.json` or environment variable `APP__database__url`
