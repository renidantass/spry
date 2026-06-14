---
title: Solução de Problemas
order: 10
description: Erros comuns e como resolvê-los
tags: troubleshooting, erros, debug
---

## ModuleNotFoundError

```bash
ModuleNotFoundError: No module named 'taskboard'
```

**Causa:** O PYTHONPATH não inclui o diretório `src/` do projeto.

**Solução:**

```bash
# PowerShell
$env:PYTHONPATH="C:\meu-projeto\src"
spry run --app taskboard.app:create_app
```

## Rota retorna 404

**Checklist:**
- A classe tem `@controller("/prefixo")`
- O método tem `@get`, `@post`, `@put`, `@patch` ou `@delete`
- O controller está dentro do pacote da aplicação
- A rota chamada corresponde ao prefixo + path do método

## Payload retorna 422

Isso significa que o binding do payload para a dataclass falhou.

**Causas comuns:**
- Campos obrigatórios ausentes
- Tipos inválidos (enviar string onde espera int)
- Nomes de campos divergentes do DTO

## MVC não encontra view

- Verifique se `builder.add_views(...)` foi chamado
- Verifique se os arquivos existem dentro de `views/`
- O nome passado em `self.view("home/index")` deve bater com `views/home/index.html`

## Async handler não funciona

**Causa:** Async handlers usam `asyncio.run()` internamente. Se você estiver rodando em um ambiente com event loop ativo (como ASGI), pode ocorrer erro.

**Solução:** Use handlers síncronos ou garanta que o middleware também seja async.

## Erro de conexão com banco

- Verifique se o driver do banco está instalado (`spry[postgres]`, `spry[mysql]`, etc.)
- Verifique a URL de conexão no `appsettings.json`
- Para produção, configure `pool_size` para evitar criar conexões por request
