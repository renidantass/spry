"""Fix imports: convert 'from spry import X, Y' to specific submodule imports."""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

IMPORT_MAP = {
    "AppBuilder": "spry.app",
    "Application": "spry.app",
    "deprecated": "spry.app",
    "ControllerBase": "spry.controllers",
    "Controller": "spry.controllers",
    "AuthenticatedController": "spry.controllers",
    "serve_static_file": "spry.controllers",
    "controller": "spry.routing",
    "get": "spry.routing",
    "post": "spry.routing",
    "put": "spry.routing",
    "patch": "spry.routing",
    "delete": "spry.routing",
    "ok": "spry.results",
    "created": "spry.results",
    "bad_request": "spry.results",
    "not_found": "spry.results",
    "no_content": "spry.results",
    "ActionResult": "spry.results",
    "DbContext": "spry.orm",
    "DbSet": "spry.orm",
    "dbset": "spry.orm",
    "key": "spry.orm",
    "column": "spry.orm",
    "foreign_key": "spry.orm",
    "navigation": "spry.orm",
    "navigation_many": "spry.orm",
    "Page": "spry.orm",
    "DatabaseMigrator": "spry.orm",
    "DatabaseBackend": "spry.orm",
    "get_backend": "spry.orm",
    "parse_database_url": "spry.orm",
    "ConnectionPool": "spry.orm",
    "Request": "spry.http",
    "Response": "spry.http",
    "UploadedFile": "spry.http",
    "HttpContext": "spry.http",
    "ProblemDetail": "spry.http",
    "PasswordHasher": "spry.auth",
    "CookieAuthService": "spry.auth",
    "JwtAuthService": "spry.auth",
    "authorize": "spry.auth",
    "UserPrincipal": "spry.auth",
    "CorsConfig": "spry.cors",
    "CsrfService": "spry.csrf",
    "SessionMiddleware": "spry.session",
    "SessionStore": "spry.session",
    "TokenBucket": "spry.throttling",
    "validate": "spry.validation",
    "ValidationError": "spry.validation",
    "bind_payload": "spry.validation",
    "bind_value": "spry.validation",
    "Required": "spry.validators",
    "MinLength": "spry.validators",
    "MaxLength": "spry.validators",
    "Email": "spry.validators",
    "Range": "spry.validators",
    "Regex": "spry.validators",
    "validate_model": "spry.validators",
    "ViewRenderer": "spry.views",
    "HtmlString": "spry.views",
    "SpryTemplateEngine": "spry.views",
    "TemplateEngine": "spry.views",
    "TestClient": "spry.testing",
    "TestResponse": "spry.testing",
    "ServiceCollection": "spry.di",
    "ServiceProvider": "spry.di",
    "Configuration": "spry.config",
    "EventDispatcher": "spry.events",
    "BackgroundTask": "spry.tasks",
    "BackgroundWorker": "spry.tasks",
    "I18nService": "spry.i18n",
    "RouteDefinition": "spry.routing",
    "create_function_route": "spry.routing",
    "OpenApiBuilder": "spry.openapi",
    "make_openapi_response": "spry.openapi",
    "make_swagger_ui_response": "spry.openapi",
    "Middleware": "spry.middleware",
}

FILES = [
    "README.md",
    "README_EN.md",
    "examples/taskboard/src/taskboard/app.py",
    "examples/taskboard/src/taskboard/data/__init__.py",
    "examples/taskboard/src/taskboard/models/todo.py",
    "examples/taskboard/src/taskboard/controllers/todos.py",
    "examples/taskboard-en/src/taskboard/app.py",
    "examples/taskboard-en/src/taskboard/data/__init__.py",
    "examples/taskboard-en/src/taskboard/models/todo.py",
    "examples/taskboard-en/src/taskboard/controllers/todos.py",
    "examples/taskboard-en/src/taskboard/seeders/todo_seeder.py",
    "examples/auth-api/src/auth_api/app.py",
    "examples/auth-api/src/auth_api/data/__init__.py",
    "examples/auth-api/src/auth_api/models/user.py",
    "examples/auth-api/src/auth_api/controllers/auth.py",
    "examples/auth-api/src/auth_api/controllers/admin.py",
    "examples/auth-api/src/auth_api/seeders/user_seeder.py",
    "src/spry/templates/api/src/__PACKAGE_NAME__/app.py.tmpl",
    "src/spry/templates/api/src/__PACKAGE_NAME__/data/__init__.py.tmpl",
    "src/spry/templates/api/src/__PACKAGE_NAME__/models/todo.py.tmpl",
    "src/spry/templates/api/src/__PACKAGE_NAME__/controllers/todos.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/app.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/data/__init__.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/models/todo.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/models/user.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/controllers/home.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/controllers/account.py.tmpl",
    "src/spry/templates/mvc/src/__PACKAGE_NAME__/seeders/user_seeder.py.tmpl",
    "docs/src/spry_docs/content/en/getting-started.md",
    "docs/src/spry_docs/content/pt/getting-started.md",
    "docs/src/spry_docs/content/en/api-development.md",
    "docs/src/spry_docs/content/pt/api-development.md",
    "docs/src/spry_docs/content/en/orm-data.md",
    "docs/src/spry_docs/content/pt/orm-data.md",
    "docs/src/spry_docs/content/en/mvc-development.md",
    "docs/src/spry_docs/content/pt/mvc-development.md",
    "docs/src/spry_docs/content/en/auth-security.md",
    "docs/src/spry_docs/content/pt/auth-security.md",
    "docs/src/spry_docs/content/en/tooling-cli.md",
    "docs/src/spry_docs/content/pt/tooling-cli.md",
    "docs/src/spry_docs/content/en/testing.md",
    "docs/src/spry_docs/content/pt/testing.md",
    "docs/src/spry_docs/content/en/deployment.md",
    "docs/src/spry_docs/content/pt/deployment.md",
    "docs/src/spry_docs/content/en/architecture.md",
    "docs/src/spry_docs/content/pt/architecture.md",
    "docs/src/spry_docs/content/en/troubleshooting.md",
    "docs/src/spry_docs/content/pt/troubleshooting.md",
]


def rewrite_imports(text: str) -> str:
    lines = text.split("\n")
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(from spry import )(.*)", line.strip())
        if m:
            symbols = [s.strip() for s in m.group(2).split(",")]
            groups: dict[str, list[str]] = {}
            for sym in symbols:
                mod = IMPORT_MAP.get(sym)
                if mod:
                    groups.setdefault(mod, []).append(sym)
                else:
                    groups.setdefault("__UNKNOWN__", []).append(sym)
            indent = line[: len(line) - len(line.lstrip())]
            if "__UNKNOWN__" in groups:
                new_lines.append(
                    f"{indent}from spry import {', '.join(groups['__UNKNOWN__'])}"
                )
            for mod in sorted(groups):
                if mod == "__UNKNOWN__":
                    continue
                syms = sorted(groups[mod])
                new_lines.append(f"{indent}from {mod} import {', '.join(syms)}")
        else:
            new_lines.append(line)
        i += 1
    return "\n".join(new_lines)


def main() -> None:
    for rel_path in FILES:
        path = BASE / rel_path
        if not path.exists():
            print(f"  SKIP {rel_path}")
            continue
        original = path.read_text("utf-8")
        if "from spry import" not in original:
            print(f"  SKIP (no import) {rel_path}")
            continue
        result = rewrite_imports(original)
        if result != original:
            path.write_text(result, encoding="utf-8")
            print(f"  UPDATED {rel_path}")
        else:
            print(f"  NO CHANGE {rel_path}")

    # Special: fix playground inline code in app.py
    pg_path = BASE / "docs/src/spry_docs/app.py"
    pg_text = pg_path.read_text("utf-8")
    # The playground has inline Python code as a string
    old_pg_import = (
        "from spry import AppBuilder, ControllerBase, controller, get"
    )
    if old_pg_import in pg_text:
        pg_text = pg_text.replace(
            old_pg_import,
            "from spry.app import AppBuilder\n"
            "from spry.controllers import ControllerBase\n"
            "from spry.routing import controller, get",
        )
        pg_path.write_text(pg_text, encoding="utf-8")
        print("  UPDATED playground inline code")
    else:
        print("  NO CHANGE (playground)")

    old_pg_testing = "from spry.testing import TestClient"
    if old_pg_testing not in pg_text:
        # Check if it still uses from spry import TestClient
        if "from spry.testing import TestClient" not in pg_text:
            # Already updated
            pass

    print("\nDone!")


if __name__ == "__main__":
    main()
