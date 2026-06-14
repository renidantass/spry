from __future__ import annotations

import secrets
from pathlib import Path


def scaffold_project(
    project_name: str,
    output_dir: str | Path,
    template_name: str = "api",
    orm: str = "sqlite",
    auth: str = "none",
) -> Path:
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Destination '{destination}' is not empty")

    package_name = _package_name(project_name)
    db_extras = {"postgres": "spry[postgres]", "mysql": "spry[mysql]", "mssql": "spry[sqlserver]"}
    db_dep = db_extras.get(orm, "")
    db_url_map = {
        "sqlite": f"{package_name}.db",
        "postgres": f"postgresql://CHANGE_ME:CHANGE_ME@localhost:5432/{package_name}",
        "mysql": f"mysql://CHANGE_ME:CHANGE_ME@localhost:3306/{package_name}",
        "mssql": f"mssql://CHANGE_ME:CHANGE_ME@localhost:1433/{package_name}",
    }
    default_password = secrets.token_urlsafe(8)
    replacements = {
        "__PROJECT_NAME__": project_name,
        "__PACKAGE_NAME__": package_name,
        "__PROJECT_SLUG__": package_name.replace("_", "-"),
        "__DEFAULT_PASSWORD__": default_password,
        "__DB_URL__": db_url_map.get(orm, f"{package_name}.db"),
        "__DB_EXTRA__": db_dep,
        "__AUTH__": auth,
    }

    template_root = Path(__file__).resolve().parent / "templates" / template_name
    if not template_root.exists():
        raise FileNotFoundError(f"Template '{template_name}' does not exist")

    for file_path in template_root.rglob("*"):
        relative = file_path.relative_to(template_root)
        rendered_relative = Path(_render_text(str(relative), replacements))
        if rendered_relative.suffix == ".tmpl":
            rendered_relative = rendered_relative.with_suffix("")

        target_path = destination / rendered_relative
        if file_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = file_path.read_text(encoding="utf-8")
        target_path.write_text(_render_text(content, replacements), encoding="utf-8")

    return destination


def _package_name(project_name: str) -> str:
    cleaned = [char.lower() if char.isalnum() else "_" for char in project_name]
    package_name = "".join(cleaned).strip("_")
    while "__" in package_name:
        package_name = package_name.replace("__", "_")
    return package_name or "app"


def _render_text(content: str, replacements: dict[str, str]) -> str:
    rendered = content
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered
