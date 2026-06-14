---
title: Ferramentas e CLI
order: 6
description: Comandos do CLI, scaffolding e migrações
tags: cli, ferramentas, scaffolding, migrações
---

## Comandos

| Comando | Descrição |
|---|---|
| `spry new <nome>` | Cria um novo projeto |
| `spry run --app ...` | Executa o servidor de desenvolvimento |
| `spry watch --app ...` | Executa com hot reload |
| `spry routes --app ...` | Lista todas as rotas registradas |
| `spry seed --entry ...` | Executa o seed de dados |
| `spry migrate add <nome>` | Cria uma migration |
| `spry migrate apply` | Aplica migrations pendentes |
| `spry migrate rollback` | Reverte a última migration |
| `spry db shell` | Abre shell interativo do banco |

## Scaffolding

```bash
# Projeto API
spry new taskboard

# Projeto MVC
spry new backoffice --template mvc

# Com banco de dados específico
spry new app --orm postgres

# Com autenticação JWT
spry new app --auth jwt

# Em diretório específico
spry new inventory --output C:/dev/inventory
```

## Estrutura Gerada

```
main.py              → Entrypoint
appsettings.json     → Configuração
src/
  app/
    app.py           → AppBuilder
    controllers.py   → Controllers
    data.py          → DbContext e entidades
    seed.py          → Dados iniciais
```

## Migrações

```bash
# Criar
spry migrate add initial --context app.data:AppDbContext

# Aplicar
spry migrate apply --database app.db

# Rollback
spry migrate rollback --database app.db
```

## Hot Reload

```bash
spry watch --app app:create_app

# Com pastas adicionais
spry watch --app app:create_app --path shared --path lib
```
