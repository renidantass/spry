---
title: ORM e Dados
order: 4
description: DbContext, DbSet, migrações, relacionamentos e consultas
tags: orm, dados, migrações, database
---

## DbContext e DbSet

O ORM do Spry é inspirado no Entity Framework Core:

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

## Bancos de Dados Suportados

Spry suporta múltiplos bancos via URL de conexão:

```python
# SQLite (padrão, sem dependências)
db = StoreDbContext("sqlite:///store.db")

# PostgreSQL (pip install spry-core[postgres])
db = StoreDbContext("postgresql://usuario:senha@localhost:5432/store")

# MySQL (pip install spry-core[mysql])
db = StoreDbContext("mysql://usuario:senha@localhost:3306/store")

# SQL Server (pip install spry-core[sqlserver])
db = StoreDbContext("mssql://sa:CHANGE_ME@localhost:1433/store")
```

### Connection Pooling

Para produção com PostgreSQL/MySQL, ative o pool:

```python
db = StoreDbContext("postgresql://...", pool_size=10)
```

## Consultas

```python
# Todos os registros
all_products = db.products.all()

# Filtro por campos
cheap = db.products.where(price=10.0)

# Primeiro registro
product = db.products.first(name="Tablet")

# Busca por chave primária
product = db.products.find(1)

# Ordenação
ordered = db.products.order_by("name")
ordered_desc = db.products.order_by("-price")

# Paginação
page = db.products.paginate(page=1, per_page=20)
# page.items, page.total, page.has_next, page.has_prev

# Skip / Take
results = db.products.skip(10).take(5)

# Agregações
total = db.products.sum("price")
media = db.products.avg("price")
menor = db.products.min("price")
maior = db.products.max("price")

# SQL Raw
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

## Relacionamentos

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

Carregue relacionamentos com `include`:

```python
author = db.authors.find(1)
db.authors.include(author, "posts")
```

## Migrações

```bash
# Criar migration
spry migrate add initial --context app.data:AppDbContext

# Aplicar
spry migrate apply --database app.db

# Rollback (desfaz última migration)
spry migrate rollback --database app.db
```

## Transaction

```python
with db.transaction():
    db.products.add(product1)
    db.products.add(product2)
    # commit automático no final do bloco
    # rollback automático em caso de erro
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

## Boas práticas

- Sempre use `save_changes()` após `add()`, `update()`, `remove()`
- Prefira `transaction()` para operações que envolvem múltiplas entidades
- Use `pool_size` em produção para evitar criar conexões por request
- Configure a URL do banco via `appsettings.json` ou variável de ambiente `APP__database__url`
