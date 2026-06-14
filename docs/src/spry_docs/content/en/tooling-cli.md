---
title: Tools and CLI
order: 6
description: CLI commands, scaffolding and migrations
tags: cli, tools, scaffolding, migrations
---

## Commands

| Command | Description |
|---|---|
| `spry new <name>` | Creates a new project |
| `spry run --app ...` | Runs the development server |
| `spry watch --app ...` | Runs with hot reload |
| `spry routes --app ...` | Lists all registered routes |
| `spry seed --entry ...` | Runs the data seed |
| `spry migrate add <name>` | Creates a migration |
| `spry migrate apply` | Applies pending migrations |
| `spry migrate rollback` | Reverts the last migration |
| `spry db shell` | Opens an interactive database shell |

## Scaffolding

```bash
# API project
spry new taskboard

# MVC project
spry new backoffice --template mvc

# With specific database
spry new app --orm postgres

# With JWT authentication
spry new app --auth jwt

# In a specific directory
spry new inventory --output C:/dev/inventory
```

## Generated Structure

```
main.py              ? Entrypoint
appsettings.json     ? Configuration
src/
  app/
    app.py           ? AppBuilder
    controllers.py   ? Controllers
    data.py          ? DbContext and entities
    seed.py          ? Initial data
```

## Migrations

```bash
# Create
spry migrate add initial --context app.data:AppDbContext

# Apply
spry migrate apply --database app.db

# Rollback
spry migrate rollback --database app.db
```

## Hot Reload

```bash
spry watch --app app:create_app

# With additional paths
spry watch --app app:create_app --path shared --path lib
```
