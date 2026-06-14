# Spry

Spry is an opinionated Python web framework for those who want to skip boilerplate without falling into too much magic.

It takes some ideas from ASP.NET Core and adapts them to a more pythonic workflow:

- AppBuilder for bootstrap, configuration and DI
- Automatic controller discovery in the application package
- ControllerBase for API and Controller for MVC
- DbContext and DbSet inspired by EF Core
- Middleware pipeline
- Payload validation with 422 response
- WSGI and ASGI support in the same app
- Project scaffolding with api and mvc templates
- CLI for new, run, watch, migrate, and seed

## Requirements

- Python 3.11+
- pip

## Quick start

Install the framework:

```bash
pip install spry-core
```

With database support:

```bash
pip install spry-core[postgres]
pip install spry-core[mysql]
pip install spry-core[sqlserver]
pip install spry-core[all]
```

Create an API:

```bash
spry new taskboard
cd taskboard
spry run --app taskboard.app:create_app
```

Create an MVC project:

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

The smallest useful example with Spry today:

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

You don't need to register controllers manually. AppBuilder automatically discovers classes decorated with @controller in the application package.

## API vs MVC

Use ControllerBase when:

- The main return type is JSON
- The app is an API
- You want helpers like self.created(), self.not_found(), and self.no_content()

Use Controller when:

- The app serves HTML
- You want self.view(...), self.partial_view(...) and self.redirect(...)
- The project follows server-side MVC

## Creating a project

### Templates

```
spry new taskboard               # api template (default)
spry new backoffice --template mvc
spry new inventory --output ./projects
```

Template pi:

- main.py - development entrypoint
- ppsettings.json - host, port and database configuration
- src/<app>/app.py - AppBuilder composition
- src/<app>/controllers.py - HTTP controllers
- src/<app>/data.py - entities and DbContext
- src/<app>/seed.py - initial data seed

Template mvc:

- Everything from the api template
- iews/ - layouts, pages and partials
- static/site.css - interface styles

### Conventions the framework assumes

- Controllers are classes decorated with @controller
- Automatic discovery looks at the application package
- DbContext is typically registered with uilder.add_db_context(...)
- For MVC, views live in files inside iews/
- Middlewares should be small and focused on cross-cutting concerns

## CLI reference

```
spry new <name> [--template api|mvc] [--output <directory>]
spry run --app module:factory [--host 127.0.0.1] [--port 8000]
spry watch --app module:factory [--path extra]
spry migrate add <name> --context module:DbContext [--output migrations]
spry migrate apply --database app.db [--input migrations]
spry seed --entry module:function [--context module:DbContext] [--database app.db]
```

## Database, migrations and seed

Generate initial SQL from the DbContext:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
```

Apply migrations:

```bash
spry migrate apply --database taskboard.db
```

Run seed:

```bash
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
```

Complete local workflow:

```bash
spry migrate add initial --context taskboard.data:AppDbContext
spry migrate apply --database taskboard.db
spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db
spry run --app taskboard.app:create_app
```

## Production

### WSGI server (recommended)

Spry's Application is a WSGI callable compatible with any WSGI server.

```bash
# Gunicorn
pip install gunicorn
gunicorn taskboard.app:create_app -w 4 -b 0.0.0.0:8000

# Waitress (Windows-friendly)
pip install waitress
waitress-serve taskboard.app:create_app
```

### ASGI server

For environments that require async, Spry is also a valid ASGI callable.

```bash
# Uvicorn
pip install uvicorn
uvicorn taskboard.app:create_app --host 0.0.0.0 --port 8000 --workers 4

# Hypercorn
pip install hypercorn
hypercorn taskboard.app:create_app --bind 0.0.0.0:8000 --workers 4
```

### Health check

Every Spry application automatically exposes GET /health:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0","uptime_seconds":42}
```

### CORS

To consume the API from a browser SPA, configure CORS:

```python
builder.add_cors(origins=["https://myapp.com"])
# or for development:
builder.add_cors(origins=["*"], credentials=False)
```

### Security

**Secret key:** The uth.secret_key config is required in production. Don't use the default value:

```json
{
  "auth": {
    "secret_key": "replace-with-a-strong-key-here",
    "cookie_name": "myapp_auth"
  }
}
```

**Request body limit:** The default is 10 MB. Adjust as needed:

```python
builder.set_max_body_size(50 * 1024 * 1024)  # 50 MB
```

**Debug mode:** In production, disable debug to avoid leaking stack traces:

```json
{ "server": { "debug": false } }
```

Or programmatically:

```python
builder.set_debug(False)
```

### Environment config

Spry loads ppsettings.json and overrides with environment variables prefixed with APP__:

```bash
APP__database__url=postgresql://user:password@host/db spry run --app app:create_app
```

## Troubleshooting

### ModuleNotFoundError when running a generated project

This usually happens because:

- You're running outside the project folder and PYTHONPATH doesn't include the correct src
- The --app doesn't match the generated package name

Correct example:

```bash
spry run --app taskboard.app:create_app
```

If working with the framework and the app side by side:

```powershell
="\..\src;\taskboard\src"
python -m spry.cli run --app taskboard.app:create_app
```

### Controller doesn't respond to route

Checklist:

- The class has @controller("/prefix")
- The method has @get, @post, @put, @patch or @delete
- The controller is inside the application package
- The called route matches the prefix + method path

### Payload returns 422

This means the payload binding to the dataclass failed.

Check:

- Missing required fields
- Invalid types
- Property names diverging from the expected DTO

### MVC doesn't find view

Check:

- If uilder.add_views(...) was called
- If the files exist inside the iews/ folder
- If the name passed in self.view("home/index") matches iews/home/index.html

## Contributing and branch strategy

Contributions are welcome! Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, code style, and PR process.

### Branch naming

| Branch | Base | Merge to | Description |
|--------|------|----------|-------------|
| eat/* | main | main via PR | New feature |
| ix/* | main | main via PR | Bug fix |
| docs/* | main | main via PR | Documentation |
| chore/* | main | main via PR | Maintenance (CI, deps) |
### Release flow

The release is fully automated via CI/CD:

1. Make commits following [Conventional Commits](https://www.conventionalcommits.org/) — the version is calculated automatically
2. Merging to `main` triggers: tests → version bump → tag → GitHub Release → PyPI

### CI

The CI workflow runs on all PRs to main with Python 3.11, 3.12, and 3.13 on Linux, Windows, and macOS.

## Repository structure

- src/spry - framework core
- src/spry/templates/api - API template
- src/spry/templates/mvc - MVC server-side template
- examples/taskboard - API example using the framework
- docs - framework documentation site
- tests - test suite

## Documentation site

The documentation site is in docs/ and covers more visual and organized guides by topic.
