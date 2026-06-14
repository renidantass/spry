# Spry Docs Site

Site de documentacao do framework `Spry`, construido com o proprio framework.

## Requisitos

- Python `3.11+`
- `pip`

## Instalacao Local

Na raiz de `spry/`, instale o framework em modo editavel:

```bash
pip install -e .
```

Isso disponibiliza o modulo `spry` e a CLI `spry` localmente.

## Estrutura

- `docs/main.py`: entrypoint simples
- `docs/appsettings.json`: host e porta padrao
- `docs/src/spry_docs/app.py`: composicao do app de documentacao
- `docs/src/spry_docs/content.py`: conteudo estruturado das paginas
- `docs/src/spry_docs/render.py`: renderer HTML
- `docs/src/spry_docs/assets/`: CSS e JS do site

## Rodando Localmente

### Opcao 1: usando a CLI instalada

Na pasta `docs/`:

```bash
spry run --app spry_docs.app:create_app --host 127.0.0.1 --port 8010
```

### Opcao 2: usando o modulo Python

```bash
python -m spry.cli run --app spry_docs.app:create_app --host 127.0.0.1 --port 8010
```

## Configurando PYTHONPATH

Se voce estiver rodando a partir de `docs/`, o Python precisa enxergar:

- o framework em `../src`
- o app de docs em `src`

### PowerShell

```powershell
$env:PYTHONPATH="..\src;src"
spry run --app spry_docs.app:create_app --host 127.0.0.1 --port 8010
```

### CMD

```cmd
set PYTHONPATH=..\src;src
spry run --app spry_docs.app:create_app --host 127.0.0.1 --port 8010
```

## Hot Reload

Reinicia o processo quando arquivos Python ou `appsettings.json` mudam.

```bash
spry watch --app spry_docs.app:create_app --path .
```

## Paginas Principais

- `/`: home da documentacao
- `/docs/getting-started`
- `/docs/http-and-routing`
- `/docs/orm-and-data`
- `/docs/tooling-and-cli`
- `/docs/architecture`
- `/health`: health check simples

## Assets

Os assets sao servidos pelo proprio app:

- `/assets/site.css`
- `/assets/site.js`

## Desenvolvimento

Compile os fontes do site para uma validacao rapida:

```bash
python -m compileall "src"
```

Se estiver na raiz de `spry/`:

```bash
python -m compileall "docs/src"
```
