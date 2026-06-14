from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path
from typing import Any

from spry_docs.components import CodeBlock


API_MODULES = [
    ("spry", "app", "Application e AppBuilder"),
    ("spry", "http", "Request e Response"),
    ("spry", "orm", "DbContext, DbSet, DatabaseMigrator"),
    ("spry", "routing", "Rotas e RouteDefinition"),
    ("spry", "di", "ServiceCollection, ServiceProvider"),
    ("spry", "auth", "CookieAuthService, JwtAuthService"),
    ("spry", "validation", "ValidationError, bind_payload"),
    ("spry", "views", "ViewRenderer, template engine"),
    ("spry", "testing", "TestClient, TestResponse"),
    ("spry", "session", "SessionMiddleware, SessionStore"),
    ("spry", "events", "EventDispatcher"),
    ("spry", "tasks", "BackgroundWorker, BackgroundTask"),
    ("spry", "cors", "CorsConfig"),
    ("spry", "i18n", "I18nService"),
]

_MODULE_CACHE: dict[str, str] = {}


def load_api_index() -> list[tuple[str, str]]:
    return [(m[1], m[2]) for m in API_MODULES]


def generate_api_page(module_path: str) -> str | None:
    if module_path in _MODULE_CACHE:
        return _MODULE_CACHE[module_path]

    for pkg, mod, desc in API_MODULES:
        if mod == module_path or f"{pkg}.{mod}" == module_path:
            page = _generate_for_module(pkg, mod)
            _MODULE_CACHE[module_path] = page
            return page

    parts = module_path.split(".")
    if len(parts) == 2:
        return generate_api_page(parts[1])

    return None


def _generate_for_module(pkg: str, mod: str) -> str:
    try:
        module = importlib.import_module(f"{pkg}.{mod}")
    except ImportError:
        return f"<h1>{mod}</h1><p>Module not found.</p>"

    sections: list[str] = [
        f'<nav class="bc">'
        f'<span class="bc-item"><a href="/">Spry</a></span>'
        f'<span class="bc-sep">/</span>'
        f'<span class="bc-item"><a href="/api/">API</a></span>'
        f'<span class="bc-sep">/</span>'
        f'<span class="bc-item">{mod}</span></nav>'
        f"<h1>{pkg}.{mod}</h1>"
    ]

    module_doc = (module.__doc__ or "").strip()
    if module_doc:
        sections.append(f"<p>{_doc_to_html(module_doc)}</p>")

    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        if inspect.isclass(obj):
            sections.append(_render_class(obj, name))
        elif inspect.isfunction(obj):
            sections.append(_render_function(obj, name))

    return "".join(sections)


def _render_class(cls: type, name: str) -> str:
    parts: list[str] = [f'<h2 id="{name}">{name}</h2>']
    doc = (cls.__doc__ or "").strip()
    if doc:
        parts.append(f"<p>{_doc_to_html(doc)}</p>")

    bases = [b.__name__ for b in cls.__bases__ if b.__name__ != "object"]
    if bases:
        parts.append(f"<p><strong>Base classes:</strong> {', '.join(bases)}</p>")

    methods = [
        m for m in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not m[0].startswith("_")
    ]
    if methods:
        parts.append("<h3>Methods</h3>")
        for method_name, method in methods:
            sig = _format_signature(method)
            doc = (method.__doc__ or "").strip()
            desc = f"<p>{_doc_to_html(doc)}</p>" if doc else ""
            parts.append(
                f'<div class="api-method">'
                f'<div class="api-sig">{name}.{method_name}{sig}</div>'
                f"{desc}</div>"
            )

    return "".join(parts)


def _render_function(func: object, name: str) -> str:
    sig = _format_signature(func)
    doc = ""
    if hasattr(func, "__doc__") and func.__doc__:
        doc = _doc_to_html(func.__doc__)
    return (
        f'<h2 id="{name}">{name}</h2>'
        f'<div class="api-sig">{name}{sig}</div>'
        f"<p>{doc}</p>"
    )


def _format_signature(func: object) -> str:
    try:
        sig = inspect.signature(func)
        params: list[str] = []
        for p_name, p in sig.parameters.items():
            if p_name == "self":
                continue
            param_str = p_name
            if p.annotation is not inspect.Parameter.empty:
                ann = _format_annotation(p.annotation)
                param_str += f": {ann}"
            if p.default is not inspect.Parameter.empty:
                default = repr(p.default)
                if len(default) > 30:
                    default = default[:30] + "..."
                param_str += f" = {default}"
            params.append(param_str)
        return f"({', '.join(params)})"
    except (ValueError, TypeError):
        return "(...)"


def _format_annotation(annotation: Any) -> str:
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())
    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin))
        arg_strs = [_format_annotation(a) for a in args]
        return f"{origin_name}[{', '.join(arg_strs)}]"
    return str(annotation)


def _doc_to_html(doc: str) -> str:
    doc = doc.strip()
    doc = re.sub(r"`(.+?)`", r"<code>\1</code>", doc)
    doc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", doc)
    lines = doc.split("\n")
    if len(lines) > 1:
        return "<br/>".join(lines)
    return doc
