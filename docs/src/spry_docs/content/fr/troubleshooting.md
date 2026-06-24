---
title: Dépannage
order: 10
description: Erreurs courantes et comment les résoudre
tags: dépannage, erreurs, debug
---

## ModuleNotFoundError

```bash
ModuleNotFoundError: No module named 'taskboard'
```

**Cause :** Le PYTHONPATH n'inclut pas le répertoire `src/` du projet.

**Solution :**

```bash
# PowerShell
$env:PYTHONPATH="C:\mon-projet\src"
spry run --app taskboard.app:create_app
```

## La route retourne 404

**Checklist :**
- La classe a `@controller("/prefixe")`
- La méthode a `@get`, `@post`, `@put`, `@patch` ou `@delete`
- Le contrôleur est dans le paquet de l'application
- La route appelée correspond au préfixe + chemin de la méthode

## La charge utile retourne 422

Cela signifie que la liaison de la charge utile vers la dataclass a échoué.

**Causes courantes :**
- Champs obligatoires manquants
- Types invalides (envoi d'une chaîne là où un entier est attendu)
- Noms de champs divergents du DTO

## MVC ne trouve pas la vue

- Vérifiez que `builder.add_views(...)` a été appelé
- Vérifiez que les fichiers existent dans `views/`
- Le nom passé dans `self.view("home/index")` doit correspondre à `views/home/index.html`

## Le handler async ne fonctionne pas

**Cause :** Les handlers async utilisent `asyncio.run()` en interne. Si vous êtes dans un environnement avec une boucle d'événements active (comme ASGI), une erreur peut survenir.

**Solution :** Utilisez des handlers synchrones ou assurez-vous que le middleware est également async.

## Erreur de connexion à la base de données

- Vérifiez que le pilote de base de données est installé (`spry[postgres]`, `spry[mysql]`, etc.)
- Vérifiez l'URL de connexion dans `appsettings.json`
- Pour la production, configurez `pool_size` pour éviter de créer des connexions par requête
