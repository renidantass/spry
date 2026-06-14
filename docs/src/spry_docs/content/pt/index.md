---
title: Spry Framework
order: 0
description: Framework Python opinado para APIs e web apps
---

Spry é um framework Python opinado para quem quer sair do boilerplate rápido sem cair em muita magia.

Ele pega ideias do ASP.NET Core e adapta para um fluxo mais *pythonic*:

- **AppBuilder** para bootstrap, configuração e DI
- **Descoberta automática** de controllers no pacote da aplicação
- **ControllerBase** para API e **Controller** para MVC
- **DbContext** e **DbSet** inspirados no EF Core
- **Middleware por pipeline**
- **Validação de payload** com resposta 422
- **Suporte WSGI e ASGI** no mesmo app
- **OpenAPI/Swagger** automático com security schemes
- **Exceções tipadas** traduzidas em `ProblemDetail` (RFC 9457)
- **StreamingResponse** para servir arquivos grandes sem carregar tudo em memória
- **JWT** com HS256 / HS384 / HS512
- **Handlers async** funcionam via ASGI (`asyncio.to_thread`)

## Para quem é

Spry faz sentido se você quer:

- Uma base pequena e legível
- Controle explícito sobre o que acontece no request
- Uma stack unificada para API ou MVC server-side
- Um caminho inicial rápido para projetos pequenos e médios

{% note type="tip" %}
Spry está em v0.x — a API está evoluindo, mas a proposta já é clara: produtividade com leitura simples de código.
{% endnote %}
