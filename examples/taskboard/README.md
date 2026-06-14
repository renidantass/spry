# Taskboard

Exemplo de API usando `Spry`.

## Requisitos

- Python `3.11+`
- `pip`

## Instalacao Local

Na raiz de `spry/`, instale o framework em modo editavel:

```bash
pip install -e .
```

Se voce estiver dentro de `examples/taskboard`, pode usar:

```bash
pip install -e ../../
```

## Estrutura

- `main.py`: entrypoint simples
- `appsettings.json`: configuracao de servidor e banco
- `src/taskboard/app.py`: bootstrap do app
- `src/taskboard/controllers.py`: controller de `Todo`
- `src/taskboard/data.py`: entidade `Todo` e `AppDbContext`
- `src/taskboard/seed.py`: carga inicial do banco

## Rodando

### Usando a CLI instalada

```bash
spry run --app taskboard.app:create_app
```

### Usando o modulo Python

```bash
python -m spry.cli run --app taskboard.app:create_app
```

Por padrao:

- host: `127.0.0.1`
- porta: `8000`

Para alterar:

```bash
spry run --app taskboard.app:create_app --host 0.0.0.0 --port 8080
```

## Hot Reload

```bash
spry watch --app taskboard.app:create_app
```

## Banco E Migracoes

Gerar migracao inicial:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
```

Aplicar migracoes:

```bash
spry migrate apply --database taskboard.db
```

## Seed

```bash
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
```

## Fluxo Rapido Local

```bash
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
spry run --app taskboard.app:create_app
```

## Endpoints

- `GET /todos`
- `GET /todos/{id}`
- `POST /todos`
- `PUT /todos/{id}`
- `DELETE /todos/{id}`

## Exemplo De Payload

Criando um todo:

```json
{
  "title": "Subir primeira API com Spry"
}
```

## Desenvolvimento

Compile o exemplo para uma verificacao rapida:

```bash
python -m compileall "src"
```
