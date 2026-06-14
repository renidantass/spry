# Spry

Spry é um framework Python opinado para quem quer sair do boilerplate rápido sem cair em muita magia.

Ele pega algumas ideias do ASP.NET Core e adapta para um fluxo mais pythonic:

- `AppBuilder` para bootstrap, configuração e DI
- Descoberta automática de controllers no pacote da aplicação
- `ControllerBase` para API e `Controller` para MVC
- `DbContext` e `DbSet` inspirados no EF Core
- Middleware por pipeline
- Validação de payload com resposta `422`
- Suporte WSGI e ASGI no mesmo app
- Scaffold de projeto com templates `api` e `mvc`
- CLI para `new`, `run`, `watch`, `migrate` e `seed`

## Requirements

- Python `3.11+`
- `pip`

## Quick start

Instale o framework via PyPI:

```bash
pip install spry-core
```

Crie uma API:

```bash
spry new taskboard
cd taskboard
spry run --app taskboard.app:create_app
```

Crie um projeto MVC:

```bash
spry new backoffice --template mvc
cd backoffice
spry run --app backoffice.app:create_app
```

### Hot reload

```bash
spry watch --app taskboard.app:create_app
```

## First manual app

O menor exemplo útil com Spry hoje:

```python
from dataclasses import dataclass

from spry.app import AppBuilder
from spry.controllers import ControllerBase
from spry.orm import DbContext, dbset, key
from spry.routing import controller, get, post


@dataclass(slots=True)
class Todo:
    id: int | None = key()
    title: str = ""
    done: bool = False


class AppDbContext(DbContext):
    todos = dbset(Todo)


@controller("/todos")
class TodosController(ControllerBase):
    def __init__(self, db: AppDbContext) -> None:
        self.db = db

    @get("/")
    def list(self):
        return self.db.todos.all()

    @post("/")
    def create(self, todo: Todo):
        self.db.todos.add(todo)
        self.db.save_changes()
        return self.created(f"/todos/{todo.id}", todo)


builder = AppBuilder()
builder.add_db_context(AppDbContext)
app = builder.build()
app.run()
```

Você não precisa registrar controllers manualmente. O `AppBuilder` descobre automaticamente classes decoradas com `@controller` no pacote da aplicação.

## API vs MVC

Use `ControllerBase` quando:

- O retorno principal é JSON
- O app é uma API
- Você quer helpers como `self.created()`, `self.not_found()` e `self.no_content()`

Use `Controller` quando:

- O app serve HTML
- Você quer `self.view(...)`, `self.partial_view(...)` e `self.redirect(...)`
- O projeto segue MVC server-side

## Creating a project

### Templates

```
spry new taskboard               # template api (padrão)
spry new backoffice --template mvc
spry new inventory --output ./projetos
```

Template `api`:

- `main.py` — entrypoint para desenvolvimento
- `appsettings.json` — host, porta e configuração de banco
- `src/<app>/app.py` — composição do `AppBuilder`
- `src/<app>/controllers.py` — controllers HTTP
- `src/<app>/data.py` — entidades e `DbContext`
- `src/<app>/seed.py` — carga inicial de dados

Template `mvc`:

- Tudo do template `api`
- `views/` — layouts, páginas e partials
- `static/site.css` — estilos da interface

### Conventions the framework assumes

- Controllers são classes decoradas com `@controller`
- A descoberta automática olha para o pacote da aplicação
- `DbContext` é tipicamente registrado com `builder.add_db_context(...)`
- Para MVC, views ficam em arquivos dentro de `views/`
- Middlewares devem ser pequenos e focados em preocupações transversais

## CLI reference

```
spry new <nome> [--template api|mvc] [--output <pasta>]
spry run --app modulo:factory [--host 127.0.0.1] [--port 8000]
spry watch --app modulo:factory [--path extra]
spry migrate add <nome> --context modulo:DbContext [--output migrations]
spry migrate apply --database app.db [--input migrations]
spry seed --entry modulo:funcao [--context modulo:DbContext] [--database app.db]
```

## Database, migrations and seed

Gerar SQL inicial a partir do `DbContext`:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
```

Aplicar migrações:

```bash
spry migrate apply --database taskboard.db
```

Executar seed:

```bash
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
```

Fluxo completo local:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
spry migrate apply --database taskboard.db
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
spry run --app taskboard.app:create_app
```

## Production

### WSGI server (recommended)

A `Application` do Spry é um callable WSGI compatível com qualquer servidor WSGI.

```bash
# Gunicorn
pip install gunicorn
gunicorn taskboard.app:create_app -w 4 -b 0.0.0.0:8000

# Waitress (Windows-friendly)
pip install waitress
waitress-serve taskboard.app:create_app
```

### ASGI server

Para ambientes que requerem async, Spry também é um callable ASGI válido.

```bash
# Uvicorn
pip install uvicorn
uvicorn taskboard.app:create_app --host 0.0.0.0 --port 8000 --workers 4

# Hypercorn
pip install hypercorn
hypercorn taskboard.app:create_app --bind 0.0.0.0:8000 --workers 4
```

### Health check

Toda aplicação Spry expõe automaticamente `GET /health`:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0","uptime_seconds":42}
```

### CORS

Para consumir a API de um browser SPA, configure CORS:

```python
builder.add_cors(origins=["https://meuapp.com"])
# ou para desenvolvimento:
builder.add_cors(origins=["*"], credentials=False)
```

### Security

**Secret key:** A configuração `auth.secret_key` é obrigatória em produção. Não use o valor padrão:

```json
{
  "auth": {
    "secret_key": "substitua-por-uma-chave-forte-aqui",
    "cookie_name": "meuapp_auth"
  }
}
```

**Request body limit:** O padrão é 10 MB. Ajuste conforme necessário:

```python
builder.set_max_body_size(50 * 1024 * 1024)  # 50 MB
```

**Debug mode:** Em produção, desative o debug para não vazar stack traces:

```json
{ "server": { "debug": false } }
```

Ou programaticamente:

```python
builder.set_debug(False)
```

### Environment config

O Spry carrega `appsettings.json` e sobrescreve com variáveis de ambiente prefixadas com `APP__`:

```bash
APP__database__url=postgresql://usuario:senha@host/db spry run --app app:create_app
```

## Troubleshooting

### ModuleNotFoundError ao rodar um projeto gerado

Normalmente acontece por um destes motivos:

- Você está rodando fora da pasta do projeto e o `PYTHONPATH` não inclui o `src` correto
- O `--app` não bate com o nome do pacote gerado

Exemplo correto:

```bash
spry run --app taskboard.app:create_app
```

Se estiver trabalhando com o framework e o app lado a lado:

```powershell
$env:PYTHONPATH="$PSScriptRoot\..\src;$PSScriptRoot\taskboard\src"
python -m spry.cli run --app taskboard.app:create_app
```

### Controller não responde rota

Checklist:

- A classe tem `@controller("/prefixo")`
- O método tem `@get`, `@post`, `@put`, `@patch` ou `@delete`
- O controller está dentro do pacote da aplicação
- A rota chamada bate com o prefixo + método

### Payload retorna 422

Isso significa que o binding do payload para a dataclass falhou.

Cheque:

- Campos obrigatórios ausentes
- Tipos inválidos
- Nomes de propriedades divergentes do DTO esperado

### MVC não encontra view

Cheque:

- Se `builder.add_views(...)` foi chamado
- Se os arquivos existem dentro da pasta `views/`
- Se o nome passado em `self.view("home/index")` bate com `views/home/index.html`

## Contributing and branch strategy

Contribuições são bem-vindas! Leia o [`CONTRIBUTING.md`](CONTRIBUTING.md) para setup, estilo de código e processo de PR.

### Branch naming

| Branch | Base | Merge para | Descrição |
|--------|------|------------|-----------|
| `feat/*` | `main` | `main` via PR | Nova funcionalidade |
| `fix/*` | `main` | `main` via PR | Correção de bug |
| `docs/*` | `main` | `main` via PR | Documentação |
| `chore/*` | `main` | `main` via PR | Manutenção (CI, dependências) |

### Release flow

O release é totalmente automatizado via CI/CD:

1. Faça commits seguindo [Conventional Commits](https://www.conventionalcommits.org/) — a versão é calculada automaticamente
2. O merge para `main` dispara: testes → bump de versão → tag → GitHub Release → PyPI

### CI

O workflow de CI roda em todos os PRs para `main` com Python 3.11, 3.12 e 3.13 em Linux, Windows e macOS.

## Repository structure

- `src/spry` — núcleo do framework
- `src/spry/templates/api` — template de API
- `src/spry/templates/mvc` — template MVC server-side
- `examples/taskboard` — exemplo de API usando o framework
- `docs` — site de documentação do framework
- `tests` — suite de testes

## Documentation site

O site de documentação fica em `docs/` e cobre guias mais visuais e organizados por assunto.
