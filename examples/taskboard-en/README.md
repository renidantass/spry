# Taskboard

Example API built with Spry.

## Requirements

- Python 3.11+
- pip

## Local Setup

At the root of `spry/`, install the framework in editable mode:

```bash
pip install -e .
```

If you are inside `examples/taskboard-en`, you can use:

```bash
pip install -e ../../
```

## Structure

- `main.py`: simple entrypoint
- `appsettings.json`: server and database configuration
- `src/taskboard/app.py`: app bootstrap
- `src/taskboard/controllers.py`: Todo controller
- `src/taskboard/data.py`: Todo entity and AppDbContext
- `src/taskboard/seed.py`: initial database seed

## Running

### Using the installed CLI

```bash
spry run --app taskboard.app:create_app
```

### Using the Python module

```bash
python -m spry.cli run --app taskboard.app:create_app
```

Default configuration:

- host: `127.0.0.1`
- port: `8000`

To change:

```bash
spry run --app taskboard.app:create_app --host 0.0.0.0 --port 8080
```

## Hot Reload

```bash
spry watch --app taskboard.app:create_app
```

## Database and Migrations

Generate initial migration:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
```

Apply migrations:

```bash
spry migrate apply --database taskboard.db
```

## Seed

```bash
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
```

## Quick Local Workflow

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

## Example Payload

Creating a todo:

```json
{
  "title": "Build my first Spry API"
}
```

## Development

Quick verification:

```bash
python -m compileall "src"
```
