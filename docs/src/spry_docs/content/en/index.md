---
title: Spry Framework
order: 0
description: Opinionated Python web framework for APIs and web apps
---

Spry is an opinionated Python web framework for those who want to skip boilerplate without falling into too much magic.

It takes ideas from ASP.NET Core and adapts them to a more *pythonic* workflow:

- **AppBuilder** for bootstrap, configuration and DI
- **Automatic discovery** of controllers in the application package
- **ControllerBase** for API and **Controller** for MVC
- **DbContext** and **DbSet** inspired by EF Core
- **Middleware pipeline**
- **Payload validation** with 422 response
- **WSGI and ASGI support** in the same app
- **OpenAPI/Swagger** auto-generation

## Who is it for

Spry makes sense if you want:

- A small, readable codebase
- Explicit control over what happens in the request
- A unified stack for API or server-side MVC
- A quick starting path for small and medium projects

{% note type="tip" %}
Spry is at v0.x — the API is evolving, but the proposal is already clear: productivity with simple, readable code.
{% endnote %}
