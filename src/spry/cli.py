from __future__ import annotations

import argparse
import importlib
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from spry.app import Application
from spry.orm import DatabaseMigrator
from spry.scaffold import scaffold_project

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("spry.cli")


def _print_version_and_exit() -> None:
    from spry import __version__
    print(f"Spry {__version__}")
    sys.exit(0)


def main() -> None:
    if "--version" in sys.argv:
        _print_version_and_exit()

    parser = argparse.ArgumentParser(prog="spry", description="Spry framework utilities")
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Create a new Spry project")
    new_parser.add_argument("name", help="Project name")
    new_parser.add_argument("--output", help="Output directory")
    new_parser.add_argument("--template", default="api", choices=["api", "mvc"], help="Project template")
    new_parser.add_argument("--orm", default="sqlite", choices=["sqlite", "postgres", "mysql", "mssql"], help="Database ORM")
    new_parser.add_argument("--auth", default="none", choices=["none", "cookie", "jwt"], help="Authentication method")
    new_parser.add_argument("--deploy", action="store_true", help="Generate Dockerfile, docker-compose and CI workflow")

    run_parser = subparsers.add_parser("run", help="Run a Spry application")
    run_parser.add_argument("--app", required=True, help="App factory path in module:callable format")
    run_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    run_parser.add_argument("--port", type=int, default=8000, help="Bind port")
    run_parser.add_argument("--server", default="wsgiref", choices=["wsgiref", "gunicorn", "waitress", "uvicorn"], help="Production server")

    watch_parser = subparsers.add_parser("watch", help="Restart app on Python file changes")
    watch_parser.add_argument("--app", required=True, help="App factory path in module:callable format")
    watch_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    watch_parser.add_argument("--port", type=int, default=8000, help="Bind port")
    watch_parser.add_argument("--path", action="append", dest="paths", help="Additional paths to watch")

    seed_parser = subparsers.add_parser("seed", help="Run a database seed entrypoint")
    seed_parser.add_argument("--entry", required=True, help="Seed callable in module:callable format")
    seed_parser.add_argument("--context", help="DbContext import path in module:Class format")
    seed_parser.add_argument("--database", help="SQLite database path")

    migrate_parser = subparsers.add_parser("migrate", help="Manage SQL migrations")
    migrate_subparsers = migrate_parser.add_subparsers(dest="migrate_command", required=True)

    migrate_add = migrate_subparsers.add_parser("add", help="Generate a SQL migration")
    migrate_add.add_argument("name", help="Migration name")
    migrate_add.add_argument("--context", required=True, help="Import path in module:Class format")
    migrate_add.add_argument("--output", default="migrations", help="Migration output directory")

    migrate_apply = migrate_subparsers.add_parser("apply", help="Apply SQL migrations")
    migrate_apply.add_argument("--database", required=True, help="SQLite database path")
    migrate_apply.add_argument("--input", default="migrations", help="Migration directory")

    migrate_rollback = migrate_subparsers.add_parser("rollback", help="Rollback the last migration")
    migrate_rollback.add_argument("--database", required=True, help="Database path or connection string")
    migrate_rollback.add_argument("--input", default="migrations", help="Migration directory")

    routes_parser = subparsers.add_parser("routes", help="List all registered routes")
    routes_parser.add_argument("--app", required=True, help="App factory path in module:callable format")

    doctor_parser = subparsers.add_parser("doctor", help="Check project setup and dependencies")

    db_parser = subparsers.add_parser("db", help="Database operations")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)
    db_shell = db_subparsers.add_parser("shell", help="Open a database shell")
    db_shell.add_argument("--database", default="app.db", help="Database path or connection string")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "new":
        output = Path(args.output) if args.output else Path.cwd() / args.name
        destination = scaffold_project(args.name, output, template_name=args.template, orm=args.orm, auth=args.auth)
        logger.info("Created project at %s", destination)
        return

    if args.command == "run":
        _prepare_import_paths(args.app)
        app = _load_application(args.app)
        if args.server == "wsgiref":
            app.run(host=args.host, port=args.port)
        elif args.server == "gunicorn":
            import gunicorn.app.base
            class GunicornApp(gunicorn.app.base.BaseApplication):
                def __init__(self, app, host, port):
                    self._app = app
                    self._host = host
                    self._port = port
                    super().__init__()
                def load_config(self):
                    self.cfg.set("bind", f"{self._host}:{self._port}")
                    self.cfg.set("workers", 4)
                def load(self):
                    return self._app
            GunicornApp(app, args.host, args.port).run()
        elif args.server == "waitress":
            from waitress import serve
            serve(app, host=args.host, port=args.port)
        elif args.server == "uvicorn":
            import uvicorn
            uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.command == "watch":
        _watch_application(args.app, args.host, args.port, args.paths or [])
        return

    if args.command == "seed":
        _prepare_import_paths(args.entry)
        if args.context:
            _prepare_import_paths(args.context)
        _run_seed(args.entry, args.context, args.database)
        return

    if args.command == "migrate" and args.migrate_command == "add":
        _prepare_import_paths(args.context)
        context_type = _load_symbol(args.context)
        file_path = DatabaseMigrator.create_migration(context_type, args.name, args.output)
        logger.info("Created migration %s", file_path)
        return

    if args.command == "doctor":
        _run_doctor()
        return

    if args.command == "migrate" and args.migrate_command == "apply":
        executed = DatabaseMigrator.apply_migrations(args.database, args.input)
        if executed:
            logger.info("Applied %d migration(s)", len(executed))
            for item in executed:
                logger.info(" - %s", item)
        else:
            logger.info("No pending migrations")

    if args.command == "migrate" and args.migrate_command == "rollback":
        rolled = DatabaseMigrator.rollback_migration(args.database, args.input)
        if rolled:
            logger.info("Rolled back: %s", rolled[0])
        else:
            logger.info("No migrations to rollback")

    if args.command == "routes":
        _prepare_import_paths(args.app)
        app = _load_application(args.app)
        print(f"{'Method':<8} {'Path':<40} {'Handler'}")
        print("-" * 80)
        for route in app.routes:
            handler = route.function_handler
            if route.controller_type and route.handler_name:
                handler_name = f"{route.controller_type.__name__}.{route.handler_name}"
            elif handler:
                handler_name = getattr(handler, "__name__", str(handler))
            else:
                handler_name = "?"
            print(f"{route.method:<8} {route.path:<40} {handler_name}")

    if args.command == "db" and args.db_command == "shell":
        _open_db_shell(args.database)


def _prepare_import_paths(import_path: str | None = None) -> None:
    cwd = Path.cwd()
    candidates = [cwd, cwd / "src", *_discover_project_paths(cwd, import_path)]
    for candidate in candidates:
        path = str(candidate)
        if path not in sys.path:
            sys.path.insert(0, path)


def _load_symbol(import_path: str) -> Any:
    module_name, separator, symbol_name = import_path.partition(":")
    if not separator:
        raise ValueError("Context path must use module:Class format")
    module = importlib.import_module(module_name)
    return getattr(module, symbol_name)


def _load_application(import_path: str) -> Application:
    loaded = _load_symbol(import_path)
    app = loaded() if callable(loaded) else loaded
    if not isinstance(app, Application):
        raise TypeError("App factory must return an Application")
    return app


def _watch_application(app_path: str, host: str, port: int, extra_paths: list[str]) -> None:
    _prepare_import_paths(app_path)
    watched_paths = [
        Path.cwd(),
        Path.cwd() / "src",
        *_discover_project_watch_paths(Path.cwd(), app_path),
        *(Path(item) for item in extra_paths),
    ]
    process = _spawn_run_process(app_path, host, port)
    fingerprints = _collect_mtimes(watched_paths)

    try:
        while True:
            time.sleep(1)
            current = _collect_mtimes(watched_paths)
            if current == fingerprints:
                if process.poll() is None:
                    continue
                process = _spawn_run_process(app_path, host, port)
                fingerprints = current
                continue

            logger.info("Change detected. Restarting...")
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            process = _spawn_run_process(app_path, host, port)
            fingerprints = current
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()


def _spawn_run_process(app_path: str, host: str, port: int) -> subprocess.Popen[Any]:
    env = os.environ.copy()
    paths = [
        str(Path.cwd()),
        str(Path.cwd() / "src"),
        *(str(path) for path in _discover_project_paths(Path.cwd(), app_path)),
    ]
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(paths + ([current] if current else []))
    return subprocess.Popen(
        [sys.executable, "-m", "spry.cli", "run", "--app", app_path, "--host", host, "--port", str(port)],
        env=env,
    )


def _collect_mtimes(paths: list[Path]) -> dict[str, float]:
    fingerprints: dict[str, float] = {}
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            fingerprints[str(path)] = path.stat().st_mtime
            continue
        for file_path in path.rglob("*.py"):
            fingerprints[str(file_path)] = file_path.stat().st_mtime
        appsettings = path / "appsettings.json"
        if appsettings.exists():
            fingerprints[str(appsettings)] = appsettings.stat().st_mtime
    return fingerprints


def _discover_project_paths(cwd: Path, import_path: str | None) -> list[Path]:
    if not import_path:
        return []

    module_name, _, _ = import_path.partition(":")
    if not module_name:
        return []

    root_name = module_name.split(".", 1)[0]
    project_root = cwd / root_name
    candidates = [project_root / "src", project_root]
    return [candidate for candidate in candidates if candidate.exists()]


def _discover_project_watch_paths(cwd: Path, import_path: str | None) -> list[Path]:
    if not import_path:
        return []

    module_name, _, _ = import_path.partition(":")
    if not module_name:
        return []

    root_name = module_name.split(".", 1)[0]
    project_root = cwd / root_name
    candidates = [project_root, project_root / "src"]
    return [candidate for candidate in candidates if candidate.exists()]


def _run_seed(entry_path: str, context_path: str | None, database: str | None) -> None:
    entrypoint = _load_symbol(entry_path)
    if context_path is None:
        entrypoint()
        logger.info("Seed executed")
        return

    context_type = _load_symbol(context_path)
    db = context_type(database or "app.db")
    try:
        db.ensure_created()
        entrypoint(db)
        db.save_changes()
    finally:
        db.close()
    logger.info("Seed executed")


def _run_doctor() -> None:
    logger.info("Spry Doctor - Checking project setup")
    issues = []

    from spry import __version__
    logger.info("  Version: %s", __version__)

    try:
        import sys
        logger.info("  Python: %s", sys.version.split()[0])
        if sys.version_info < (3, 11):
            issues.append("Python 3.11+ is required")
    except Exception:
        issues.append("Could not determine Python version")

    try:
        import spry
        logger.info("  Spry import: OK")
    except ImportError as e:
        issues.append(f"Spry import failed: {e}")

    try:
        from spry.db.backends import get_backend
        from spry.db.url import parse_database_url
        for scheme in ("sqlite",):  # postgresql, mysql require drivers
            try:
                url = parse_database_url(f"{scheme}:///test")
                b = get_backend(url)
                logger.info("  Backend %s: available", scheme)
            except (ImportError, ValueError):
                issues.append(f"  Backend {scheme}: not available")
    except Exception as e:
        issues.append(f"Backend check failed: {e}")

    try:
        import jinja2
        logger.info("  Jinja2: available")
    except ImportError:
        logger.info("  Jinja2: not installed (optional)")

    app_dir = Path.cwd() / "src" / "app"
    if app_dir.exists():
        logger.info("  App package: found at src/app")
    else:
        app_dir = Path.cwd() / "src"
        if (app_dir / "app.py").exists():
            logger.info("  App package: found at src")
        else:
            logger.info("  App package: not found (run 'spry new' first)")

    if issues:
        logger.warning("Issues found:")
        for issue in issues:
            logger.warning("  - %s", issue)
    else:
        logger.info("All checks passed")


def _open_db_shell(database: str) -> None:
    import shutil

    if database.endswith(".db") or database.startswith("sqlite"):
        db_path = database.replace("sqlite:///", "").replace("sqlite://", "")
        if shutil.which("sqlite3"):
            subprocess.run(["sqlite3", db_path])
        else:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            logger.info("SQLite shell (type .exit to quit, .tables for list)")
            while True:
                try:
                    line = input("sqlite> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not line:
                    continue
                if line == ".exit":
                    break
                if line == ".tables":
                    tables = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                    for t in tables:
                        print(t["name"])
                    continue
                try:
                    cursor = conn.execute(line)
                    if line.upper().startswith("SELECT") or line.upper().startswith("PRAGMA"):
                        rows = cursor.fetchall()
                        if rows:
                            keys = rows[0].keys()
                            print(" | ".join(keys))
                            print("-" * (len(keys) * 20))
                            for row in rows:
                                print(" | ".join(str(row[k]) for k in keys))
                        print(f"({len(rows)} rows)")
                    else:
                        conn.commit()
                        print(f"({cursor.rowcount} rows affected)")
                except Exception as e:
                    print(f"Error: {e}")
            conn.close()
    elif database.startswith("postgresql"):
        subprocess.run(["psql", database])
    elif database.startswith("mysql"):
        subprocess.run(["mysql", database])
    else:
        logger.error("Unsupported database: %s", database)


if __name__ == "__main__":
    main()
