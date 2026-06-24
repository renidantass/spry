---
title: Outils et CLI
order: 6
description: Commandes CLI, scaffolding et migrations
tags: cli, outils, scaffolding, migrations
---

## Commandes

| Commande | Description |
|---|---|
| `spry new <nom>` | Crée un nouveau projet |
| `spry run --app ...` | Exécute le serveur de développement |
| `spry watch --app ...` | Exécute avec hot reload |
| `spry routes --app ...` | Liste toutes les routes enregistrées |
| `spry seed --entry ...` | Exécute le seed de données |
| `spry migrate add <nom>` | Crée une migration |
| `spry migrate apply` | Applique les migrations en attente |
| `spry migrate rollback` | Annule la dernière migration |
| `spry db shell` | Ouvre un shell interactif de la base de données |

## Scaffolding

```bash
# Projet API
spry new taskboard

# Projet MVC
spry new backoffice --template mvc

# Avec base de données spécifique
spry new app --orm postgres

# Avec authentification JWT
spry new app --auth jwt

# Dans un répertoire spécifique
spry new inventory --output C:/dev/inventory
```

## Structure Générée

```
main.py              → Point d'entrée
appsettings.json     → Configuration
src/
  app/
    app.py           → AppBuilder
    controllers.py   → Contrôleurs
    data.py          → DbContext et entités
    seed.py          → Données initiales
```

## Migrations

```bash
# Créer
spry migrate add initial --context app.data:AppDbContext

# Appliquer
spry migrate apply --database app.db

# Rollback
spry migrate rollback --database app.db
```

## Hot Reload

```bash
spry watch --app app:create_app

# Avec des dossiers supplémentaires
spry watch --app app:create_app --path shared --path lib
```
