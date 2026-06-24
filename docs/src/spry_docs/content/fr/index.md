---
title: Spry Framework
order: 0
description: Framework Python opiné pour APIs et applications web
---

Spry est un framework Python opiné pour ceux qui veulent sortir du boilerplate rapidement sans tomber dans trop de magie.

Il reprend des idées d'ASP.NET Core et les adapte à un flux plus *pythonic* :

- **AppBuilder** pour le bootstrap, la configuration et l'ID
- **Découverte automatique** des contrôleurs dans le paquet de l'application
- **ControllerBase** pour l'API et **Controller** pour le MVC
- **DbContext** et **DbSet** inspirés d'EF Core
- **Middleware par pipeline**
- **Validation des charges utiles** avec réponse 422
- **Support WSGI et ASGI** dans la même application
- **OpenAPI/Swagger** automatique avec security schemes
- **Exceptions typées** traduites en `ProblemDetail` (RFC 9457)
- **StreamingResponse** pour servir des fichiers volumineux sans tout charger en mémoire
- **JWT** avec HS256 / HS384 / HS512
- **Gestionnaires async** fonctionnent via ASGI (`asyncio.to_thread`)

## Pour qui

Spry a du sens si vous voulez :

- Une base petite et lisible
- Un contrôle explicite sur ce qui se passe dans la requête
- Une pile unifiée pour l'API ou le MVC côté serveur
- Un chemin de démarrage rapide pour les petits et moyens projets

{% note type="tip" %}
Spry est en v0.x — l'API évolue, mais la proposition est déjà claire : productivité avec un code simple et lisible.
{% endnote %}
