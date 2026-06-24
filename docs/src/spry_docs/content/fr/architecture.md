---
title: Architecture
order: 9
description: Vue interne du framework, pipeline et composants
tags: architecture, framework, conception
---

## Bootstrap

```
AppBuilder
  ├── Charge appsettings.json
  ├── Enregistre les services dans ServiceCollection
  ├── Découvre les contrôleurs automatiquement
  ├── Construit le pipeline middleware
  └── build() → Application
```

## Pipeline par Requête

```
Requête → Middleware 1 → Middleware 2 → ... → Contrôleur
                                                     │
Réponse ← Middleware 1 ← Middleware 2 ← ... ← Réponse
```

Chaque middleware peut :
- Modifier la requête (authentification, logging)
- Modifier la réponse (en-têtes, compression)
- Interrompre le pipeline (autorisation, rate limiting)

## Conteneur DI

Spry possède un conteneur d'injection de dépendances avec trois durées de vie :

| Durée de vie | Comportement |
|---|---|
| **Singleton** | Une seule instance pour toute l'application |
| **Scoped** | Une instance par requête |
| **Transient** | Une nouvelle instance à chaque résolution |

```python
builder.add_singleton(MonService)
builder.add_scoped(DbContext)
builder.add_transient(Helper)
```

## Contrôleurs

```
ControllerBase (API)
  └── Controller (MVC + vues)
       └── AuthenticatedController (MVC + auth)
```

## ORM

```
DbContext
  ├── Connection pooling
  ├── Génération de schéma
  ├── Migrations
  └── DbSet[T]
       ├── CRUD (add, update, remove)
       ├── Requêtes (all, where, first, find)
       ├── OrderBy, Pagination
       ├── Agrégations (sum, avg, min, max)
       ├── Include (eager loading)
       └── SQL brut (from_sql)
```

## Backends de Base de Données

```
DatabaseBackend (ABC)
  ├── SqliteBackend   (stdlib, sans dépendances)
  ├── PostgresBackend (psycopg2)
  ├── MySqlBackend    (pymysql)
  ├── MariaDBBackend  (pymysql)
  └── SqlServerBackend (pyodbc)
```

## Méthodes d'AppBuilder

`AppBuilder` est le point d'entrée principal pour configurer une application Spry :

| Méthode | Description |
|--------|-----------|
| `add_controller(cls)` | Enregistre une classe de contrôleur |
| `add_db_context(cls)` | Enregistre une classe DbContext |
| `add_cors(origins, ...)` | Active CORS avec les origines fournies |
| `add_auth(secret_key, ...)` | Active l'authentification par cookie |
| `add_jwt_auth(secret_key, ...)` | Active l'authentification JWT |
| `add_csrf()` | Active la protection CSRF |
| `add_session()` | Active le middleware de session |
| `add_rate_limiter(max, window)` | Active le rate limiting |
| `add_security_headers(csp, hsts, xfo)` | Définit les en-têtes de sécurité |
| `add_request_logging()` | Enregistre toutes les requêtes reçues |
| `add_compression(min_size)` | Active la compression des réponses |
| `add_views(engine, views_dir)` | Configure le moteur de templates |
| `add_error_handler(status_code)` | Enregistre un gestionnaire d'erreur personnalisé |
| `add_settings(settings_cls)` | Ajoute une configuration typée |
| `add_server_header(value)` | Définit l'en-tête Server dans la réponse |
| `add_default_deny()` | Refuse toutes les routes par défaut (whitelist) |
| `add_auth_logging()` | Enregistre les événements d'authentification |
| `add_static_files(prefix, dir)` | Sert des fichiers statiques |
| `add_route_group(prefix)` | Groupe les routes sous un préfixe commun |
| `set_debug(bool)` | Active/désactive le mode debug |
| `set_max_body_size(bytes)` | Définit la taille maximale du corps |
| `use(middleware)` | Ajoute un middleware au pipeline |
| `map_get(path, handler)` | Enregistre une route GET |
| `map_post(path, handler)` | Enregistre une route POST |
| `map_put(path, handler)` | Enregistre une route PUT |
| `map_patch(path, handler)` | Enregistre une route PATCH |
| `map_delete(path, handler)` | Enregistre une route DELETE |
| `build()` | Construit et retourne l'Application |

## Moteur de Template

```
TemplateEngine (ABC)
  ├── SpryTemplateEngine (par défaut, for/if/include/filters)
  └── Jinja2TemplateEngine (optionnel, spry[jinja2])
```
