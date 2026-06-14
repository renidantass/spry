# Spry

`Spry` e um framework Python opinado para quem quer sair do boilerplate rapido sem cair em muita magia.

Ele pega algumas ideias de ASP.NET Core e adapta para um fluxo mais pythonic:

- `AppBuilder` para bootstrap, configuracao e DI
- descoberta automatica de controllers no pacote da aplicacao
- `ControllerBase` para API e `Controller` para MVC
- `DbContext` e `DbSet` inspirados no EF Core
- middleware por pipeline
- validacao de payload com resposta `422`
- suporte WSGI e ASGI no mesmo app
- scaffold de projeto com templates `api` e `mvc`
- CLI para `new`, `run`, `watch`, `migrate` e `seed`

## Para Quem E

`Spry` faz mais sentido se voce quer:

- uma base pequena e legivel
- controle explicito sobre o que acontece no request
- uma stack unificada para API ou MVC server-side
- um caminho inicial rapido para projetos pequenos e medios

Hoje ele ainda esta em `v0.x`, entao a API esta evoluindo, mas a proposta ja e clara: produtividade com leitura simples de codigo.

## Requisitos

- Python `3.11+`
- `pip`

## Instalacao Local

Na raiz de `spry/`:

```bash
pip install -e .
```

Isso disponibiliza:

- o modulo `spry`
- o comando `spry`
- atualizacao imediata quando voce edita os arquivos locais

Verificacao rapida:

```bash
spry --help
python -c "import spry; print('ok')"
```

## Quick Start Em 5 Minutos

Criando uma API:

```bash
spry new taskboard
cd taskboard
spry run --app taskboard.app:create_app
```

Criando um projeto MVC server-side:

```bash
spry new backoffice --template mvc
cd backoffice
spry run --app backoffice.app:create_app
```

## Primeiro App Manual

Esse e o menor exemplo util com `Spry` hoje:

```python
from dataclasses import dataclass

from spry import AppBuilder, ControllerBase, DbContext, controller, dbset, get, key, post


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

Ponto importante: voce nao precisa registrar controllers manualmente. O `AppBuilder` descobre automaticamente classes decoradas com `@controller` no pacote da aplicacao.

## Criando Um Projeto

Template de API:

```bash
spry new taskboard
```

Template MVC server-side com UI inspirada no `shadcn`:

```bash
spry new taskboard_web --template mvc
```

Escolhendo pasta de destino:

```bash
spry new inventory --template api --output C:\dev\inventory
```

## Estrutura Do Projeto Gerado

Template `api`:

- `main.py`: entrypoint simples para desenvolvimento
- `appsettings.json`: host, porta e configuracao de banco
- `src/<app>/app.py`: composicao do `AppBuilder`
- `src/<app>/controllers.py`: controllers HTTP
- `src/<app>/data.py`: entidades e `DbContext`
- `src/<app>/seed.py`: carga inicial de dados

Template `mvc`:

- tudo do template `api`
- `views/`: layouts, paginas e partials
- `static/site.css`: estilos da interface

## Como Rodar

Dentro do projeto gerado:

```bash
spry run --app taskboard.app:create_app
```

Ou com o modulo Python:

```bash
python -m spry.cli run --app taskboard.app:create_app
```

Padroes:

- host: `127.0.0.1`
- porta: `8000`

Customizando:

```bash
spry run --app taskboard.app:create_app --host 0.0.0.0 --port 8080
```

## Hot Reload

```bash
spry watch --app taskboard.app:create_app
```

Incluindo pastas extras no watch:

```bash
spry watch --app taskboard.app:create_app --path . --path shared
```

## Banco, Migracoes E Seed

Gerar SQL inicial a partir do `DbContext`:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
```

Aplicar migracoes:

```bash
spry migrate apply --database taskboard.db
```

Executar seed:

```bash
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
```

Fluxo comum local:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
spry migrate apply --database taskboard.db
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
spry run --app taskboard.app:create_app
```

## API Vs MVC

Use `ControllerBase` quando:

- o retorno principal e JSON
- o app e uma API
- voce quer helpers como `self.created()`, `self.not_found()` e `self.no_content()`

Use `Controller` quando:

- o app serve HTML
- voce quer `self.view(...)`, `self.partial_view(...)` e `self.redirect(...)`
- o projeto segue MVC server-side

## Convenções Que O Framework Assume

- controllers sao classes decoradas com `@controller`
- a descoberta automatica olha para o pacote da aplicacao
- `DbContext` e tipicamente registrado com `builder.add_db_context(...)`
- para MVC, views ficam fora do Python, em arquivos dentro de `views/`
- middlewares devem ser pequenos e focados em preocupacoes transversais

## Producao

### Servidor WSGI (recomendado para producao)

O `Application` do Spry e um callable WSGI compativel com qualquer servidor WSGI.

```bash
# Gunicorn
pip install gunicorn
gunicorn taskboard.app:create_app -w 4 -b 0.0.0.0:8000

# Waitress (Windows-friendly)
pip install waitress
waitress-serve taskboard.app:create_app
```

### Servidor ASGI

Para ambientes que requerem async, Spry tambem e um callable ASGI valido:

```bash
# Uvicorn
pip install uvicorn
uvicorn taskboard.app:create_app --host 0.0.0.0 --port 8000 --workers 4

# Hypercorn
pip install hypercorn
hypercorn taskboard.app:create_app --bind 0.0.0.0:8000 --workers 4
```

### Health Check

Toda aplicacao Spry expoe automaticamente `GET /health`:

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

### Seguranca

**Secret key:** A configuracao `auth.secret_key` e obrigatoria em
producao. Nao use o valor padrao:

```json
{
  "auth": {
    "secret_key": "substitua-por-uma-chave-forte-aqui",
    "cookie_name": "meuapp_auth"
  }
}
```

**Limite de corpo de requisicao:** O padrao e 10MB. Ajuste conforme
necessario:

```python
builder.set_max_body_size(50 * 1024 * 1024)  # 50MB
```

**Modo debug:** Em producao, desative o debug para nao vazar
stack traces:

```json
{ "server": { "debug": false } }
```

Ou programaticamente:

```python
builder.set_debug(False)
```

### Configuracao por ambiente

O Spry carrega `appsettings.json` e sobrescreve com variaveis de
ambiente prefixadas com `APP__`:

```bash
APP__database__url=postgresql://user:pass@host/db spry run --app app:create_app
```

## Troubleshooting

### `ModuleNotFoundError` ao rodar um projeto gerado

Normalmente acontece por um destes motivos:

- voce esta rodando fora da pasta do projeto e o `PYTHONPATH` nao inclui o `src` correto
- o `--app` nao bate com o nome do pacote gerado

Exemplo correto:

```bash
spry run --app taskboard.app:create_app
```

Se estiver trabalhando com o framework e o app lado a lado:

```powershell
$env:PYTHONPATH="$PSScriptRoot\..\src;$PSScriptRoot\taskboard\src"
python -m spry.cli run --app taskboard.app:create_app
```

### Controller nao responde rota

Checklist:

- a classe tem `@controller("/prefixo")`
- o metodo tem `@get`, `@post`, `@put`, `@patch` ou `@delete`
- o controller esta dentro do pacote da aplicacao
- a rota chamada bate com o prefixo + metodo

### Payload retorna `422`

Isso significa que o binding do payload para a `dataclass` falhou.

Cheque:

- campos obrigatorios ausentes
- tipos invalidos
- nomes de propriedades divergentes do DTO esperado

### MVC nao encontra view

Cheque:

- se `builder.add_views(...)` foi chamado
- se os arquivos existem dentro da pasta `views/`
- se o nome passado em `self.view("home/index")` bate com `views/home/index.html`

### Import de controller com `from __future__ import annotations`

O framework ja resolve `type hints` adiados em controllers e servicos DI. Se ainda houver erro, normalmente o problema e o modulo nao estar no `sys.path`.

## Rodando Os Exemplos Deste Repositorio

### Exemplo de API

```bash
pip install -e .
cd examples/taskboard
spry run --app taskboard.app:create_app
```

### Site de Documentacao

```bash
pip install -e .
cd docs
spry run --app spry_docs.app:create_app --host 127.0.0.1 --port 8010
```

## Desenvolvimento Local Sem Instalar Globalmente

Voce sempre pode usar:

```bash
python -m spry.cli --help
```

Se estiver trabalhando fora do ambiente instalado, garanta que o `PYTHONPATH` inclua o `src` do framework e o `src` do projeto.

Exemplo no PowerShell:

```powershell
$env:PYTHONPATH="$PSScriptRoot\src;C:\meu-projeto\src"
python -m spry.cli run --app meu_projeto.app:create_app
```

## Comandos Principais

```bash
spry new <nome> [--template api|mvc] [--output <pasta>]
spry run --app modulo:factory [--host 127.0.0.1] [--port 8000]
spry watch --app modulo:factory [--path extra]
spry migrate add <nome> --context modulo:DbContext [--output migrations]
spry migrate apply --database app.db [--input migrations]
spry seed --entry modulo:funcao [--context modulo:DbContext] [--database app.db]
```

## Estrutura Deste Repositorio

- `src/spry`: nucleo do framework
- `src/spry/templates/api`: template de API
- `src/spry/templates/mvc`: template MVC server-side
- `examples/taskboard`: exemplo de API usando o framework
- `docs`: site de documentacao do framework

## Documentacao Web

O site de docs fica em `docs/` e cobre guias mais visuais e organizados por assunto.

```bash
cd docs
spry run --app spry_docs.app:create_app --host 127.0.0.1 --port 8010
```
