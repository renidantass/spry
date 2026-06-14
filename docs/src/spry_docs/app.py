from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from spry import AppBuilder, Request, Response
from spry.routing import create_function_route

from spry_docs.components import Layout
from spry_docs.render.parser import parse_markdown, slugify
from spry_docs.render.blocks import render_block

logger = logging.getLogger("spry.docs")

DOCS_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = DOCS_DIR / "src" / "spry_docs" / "assets"
CONTENT_DIR = DOCS_DIR / "src" / "spry_docs" / "content"
API_DIR = DOCS_DIR / "src" / "spry_docs" / "api"
VERSION: str | None = None
VERSIONS: list[str] = []


def _get_version() -> str:
    global VERSION, VERSIONS
    if VERSION is not None:
        return VERSION
    try:
        import tomllib
        pyproject = tomllib.load(open(DOCS_DIR.parent / "pyproject.toml", "rb"))
        VERSION = pyproject["project"]["version"]
        VERSIONS = [VERSION]
    except Exception:
        VERSION = "0.1.0"
        VERSIONS = ["0.1.0"]
    return VERSION


_get_version()

_locale_cache: dict[str, list[dict[str, Any]]] = {}

PAGE_ORDER = [
    "getting-started",
    "api-development",
    "mvc-development",
    "orm-data",
    "auth-security",
    "tooling-cli",
    "testing",
    "deployment",
    "architecture",
    "troubleshooting",
]

DOC_TITLES = {
    "getting-started": {"pt": "Começando", "en": "Getting Started"},
    "api-development": {"pt": "Desenvolvimento de API", "en": "API Development"},
    "mvc-development": {"pt": "Desenvolvimento MVC", "en": "MVC Development"},
    "orm-data": {"pt": "ORM e Dados", "en": "ORM and Data"},
    "auth-security": {"pt": "Autenticação e Segurança", "en": "Auth and Security"},
    "tooling-cli": {"pt": "Ferramentas e CLI", "en": "Tools and CLI"},
    "testing": {"pt": "Testes", "en": "Testing"},
    "deployment": {"pt": "Deploy", "en": "Deployment"},
    "architecture": {"pt": "Arquitetura", "en": "Architecture"},
    "troubleshooting": {"pt": "Solução de Problemas", "en": "Troubleshooting"},
}

DOC_DESCRIPTIONS = {
    "getting-started": {"pt": "Instalação e primeiro projeto", "en": "Installation and first project"},
    "api-development": {"pt": "Controllers, middleware e validação", "en": "Controllers, middleware and validation"},
    "mvc-development": {"pt": "Views, layouts e HTML server-side", "en": "Views, layouts and server-side HTML"},
    "orm-data": {"pt": "DbContext, migrações e relacionamentos", "en": "DbContext, migrations and relationships"},
    "auth-security": {"pt": "Auth, CORS, CSRF e rate limiting", "en": "Auth, CORS, CSRF and rate limiting"},
    "tooling-cli": {"pt": "CLI, scaffolding e ferramentas", "en": "CLI, scaffolding and tools"},
    "testing": {"pt": "TestClient e testes de integração", "en": "TestClient and integration tests"},
    "deployment": {"pt": "Produção, Docker e deploy", "en": "Production, Docker and deployment"},
    "architecture": {"pt": "Visão interna do framework", "en": "Framework internals"},
    "troubleshooting": {"pt": "Erros comuns e soluções", "en": "Common errors and solutions"},
}


def _detect_locale(request: Request) -> str:
    cookie_locale = request.cookies.get("spry_locale")
    if cookie_locale in ("pt", "en"):
        return cookie_locale
    accept = request.headers.get("Accept-Language", "")
    if accept.startswith("en"):
        return "en"
    return "pt"


def _load_pages(locale: str) -> list[dict[str, Any]]:
    key = f"pages_{locale}"
    if key in _locale_cache:
        return _locale_cache[key]

    pages: list[dict[str, Any]] = []
    for slug in PAGE_ORDER:
        md_path = CONTENT_DIR / locale / f"{slug}.md"
        if not md_path.exists():
            md_path = CONTENT_DIR / "pt" / f"{slug}.md"
        if md_path.exists():
            title = DOC_TITLES.get(slug, {}).get(locale, slug)
            desc = DOC_DESCRIPTIONS.get(slug, {}).get(locale, "")
            pages.append({"slug": slug, "title": title, "description": desc})

    _locale_cache[key] = pages
    return pages


def _build_search_index(locale: str) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for slug in PAGE_ORDER:
        md_path = CONTENT_DIR / locale / f"{slug}.md"
        if not md_path.exists():
            continue
        title = DOC_TITLES.get(slug, {}).get(locale, slug)
        content = md_path.read_text("utf-8")
        text = content.split("---", 2)[-1] if content.startswith("---") else content
        import re
        plain = re.sub(r"[#*`\[\]()>|-]", "", re.sub(r"```.*?```", "", text, flags=re.DOTALL)).strip()
        tags_match = re.search(r"tags:\s*(.*)", content)
        tags = [t.strip() for t in tags_match.group(1).split(",")] if tags_match else []
        index.append({
            "slug": f"/docs/{slug}",
            "title": title,
            "snippet": plain[:300],
            "tags": tags,
        })
    return index


def create_app() -> Any:
    base_url = os.environ.get("SPRY_DOCS_BASE_URL", "")
    builder = AppBuilder(base_path=DOCS_DIR)

    def security_headers(context: Any, next_handler: Any) -> Response:
        response = next_handler()
        response.headers.setdefault("X-Powered-By", "Spry Docs")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    builder.use(security_headers)

    def landing_page(request: Request) -> Response:
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        md_path = CONTENT_DIR / locale / "index.md"
        if not md_path.exists():
            md_path = CONTENT_DIR / "pt" / "index.md"
        fm, blocks = parse_markdown(md_path.read_text("utf-8") if md_path.exists() else "")

        feat_grid = (
            '<div class="feat-grid">'
            + "".join(
                f'<div class="feat-card"><div class="feat-ico">{i}</div><div class="feat-tl">{t}</div><div class="feat-desc">{d}</div></div>'
                for i, t, d in [
                    ("⚡", "Rápido", "Crie APIs completas em 5 minutos"),
                    ("🧩", "Modular", "DI container, middleware pipeline, ORM próprio"),
                    ("📖", "Legível", "Código explícito sem magia"),
                    ("🔒", "Seguro", "CORS, CSRF, JWT, rate limiting inclusos"),
                    ("📝", "OpenAPI", "Swagger UI automático"),
                    ("🗄️", "Multi-DB", "SQLite, PostgreSQL, MySQL, SQL Server"),
                ]
            )
            + "</div>"
        )

        body = (
            '<div class="hero">'
            '<h1>Spry Framework</h1>'
            '<p>Framework Python opinado para APIs e web apps. '
            "Zero boilerplate, controle total, pronto para produção.</p>"
            '<div class="hero-actions">'
            '<a href="/docs/getting-started" class="btn btn-primary">Começar</a>'
            '<a href="/playground" class="btn btn-secondary">Playground</a>'
            '<a href="https://github.com/renidantass/spry" class="btn btn-secondary">GitHub</a>'
            "</div>"
            '<div class="term">'
            '<div class="term-hd"><span class="term-dot"></span><span class="term-dot"></span><span class="term-dot"></span></div>'
            '<div class="term-bd">'
            '<span style="color:var(--ac)">$</span> spry new myapp<br/>'
            '<span style="color:var(--ac)">$</span> cd myapp<br/>'
            '<span style="color:var(--ac)">$</span> spry run<br/>'
            '<br/>'
            '<span style="color:var(--tx3)"># Spry listening on http://127.0.0.1:8000</span>'
            '</div></div>'
            "</div>"
            f'{feat_grid}'
            '<div class="path-grid">'
            + "".join(
                f'<a href="/docs/{p["slug"]}" class="card">'
                f'<div class="card-tl">{p["title"]}</div>'
                f'<div class="card-desc">{p.get("description", "")}</div>'
                f"</a>"
                for p in pages[:6]
            )
            + "</div>"
        )

        html = Layout(base_url=base_url,
            title="Spry Framework",
            description="Framework Python opinado para APIs e web apps",
            body=body,
            active_slug="",
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
            canonical=base_url or "/",
        ).render()
        return Response.html(html)

    def docs_page(slug: str, request: Request) -> Response:
        locale = _detect_locale(request)
        pages = _load_pages(locale)

        if slug not in PAGE_ORDER:
            body = (
                f'<h1>Página não encontrada</h1>'
                f'<p>A documentação para <code>{slug}</code> não foi encontrada.</p>'
                f'<a href="/docs/getting-started" class="btn btn-primary">Ver documentação</a>'
            )
            html = Layout(base_url=base_url,
                title="404 — Spry",
                description="Page not found",
                body=body,
                active_slug="",
                pages=pages,
                locale=locale,
                version=VERSION,
                versions=VERSIONS,
            ).render()
            return Response.html(html, status_code=404)

        md_path = CONTENT_DIR / locale / f"{slug}.md"
        if not md_path.exists():
            md_path = CONTENT_DIR / "pt" / f"{slug}.md"
        if not md_path.exists():
            return Response.html("<h1>Not found</h1>", status_code=404)

        fm, blocks = parse_markdown(md_path.read_text("utf-8"))
        title = DOC_TITLES.get(slug, {}).get(locale, fm.title or slug)
        desc = DOC_DESCRIPTIONS.get(slug, {}).get(locale, "")

        toc_items = "".join(
            f'<a href="#{slugify(b.content)}" class="sb-item sb-toc">{b.content}</a>'
            for b in blocks if b.type == "heading" and b.level == 2
        )

        sections_html = "".join(render_block(b) for b in blocks)

        body = (
            f'<nav class="bc">'
            f'<span class="bc-item"><a href="/">Spry</a></span>'
            f'<span class="bc-sep">/</span>'
            f'<span class="bc-item">{title}</span>'
            f'</nav>'
            f'<h1>{title}</h1>'
            f'<p class="page-desc">{desc}</p>'
            f'<div class="toc">{toc_items}</div>'
            f'{sections_html}'
        )

        html = Layout(base_url=base_url,
            title=f"{title} — Spry",
            description=desc or fm.description,
            body=body,
            active_slug=slug,
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
            canonical=f"{base_url}/docs/{slug}",
        ).render()
        return Response.html(html)

    def search_index(request: Request) -> Response:
        locale = _detect_locale(request)
        index = _build_search_index(locale)
        return Response.json(index)

    def api_page(path: str, request: Request) -> Response:
        from spry_docs.apigen import generate_api_page, load_api_index
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        api_index = load_api_index()

        if not path:
            body = (
                '<h1>API Reference</h1>'
                '<p>Navegue pelos módulos do Spry:</p>'
                + "".join(
                    f'<a href="/api/{m}" class="card">'
                    f'<div class="card-tl">{m}</div>'
                    f'<div class="card-desc">{d}</div></a>'
                    for m, d in api_index
                )
            )
        else:
            page = generate_api_page(path)
            if page is None:
                body = f"<h1>Módulo não encontrado</h1><p>{path}</p>"
            else:
                body = page

        html = Layout(base_url=base_url,
            title=f"API — Spry",
            description="API Reference",
            body=body,
            active_slug="",
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
        ).render()
        return Response.html(html)

    def asset(name: str) -> Response:
        from spry.controllers import serve_static_file
        return serve_static_file(ASSETS_DIR, name, {
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        })

    def change_log(request: Request) -> Response:
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        changelog_path = DOCS_DIR.parent / "CHANGELOG.md"
        if not changelog_path.exists():
            body = "<h1>Changelog</h1><p>Em breve.</p>"
        else:
            from spry_docs.render.parser import parse_markdown
            _, blocks = parse_markdown(changelog_path.read_text("utf-8"))
            body = "<h1>Changelog</h1>" + "".join(render_block(b) for b in blocks)

        html = Layout(base_url=base_url,
            title="Changelog — Spry",
            description="Histórico de versões",
            body=body,
            active_slug="",
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
        ).render()
        return Response.html(html)

    def playground(request: Request) -> Response:
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        body = (
            '<h1>Playground</h1>'
            '<p>Teste código Spry diretamente no navegador.</p>'
            '<div class="pg">'
            '<div class="pg-hd"><span class="pg-lang">python</span>'
            '<button class="pg-run" onclick="runPlayground(this)">Run ▶</button></div>'
            '<textarea class="pg-ed" id="pgCode" rows="14">'
            'from spry import AppBuilder, ControllerBase, controller, get\n\n'
            '@controller("/hello")\n'
            'class HelloController(ControllerBase):\n'
            '    @get("/")\n'
            '    def say_hello(self):\n'
            '        return {"message": "Hello World!"}\n\n'
            'builder = AppBuilder()\n'
            'builder.add_controller(HelloController)\n'
            'app = builder.build()\n\n'
            'from spry.testing import TestClient\n'
            'client = TestClient(app)\n'
            'resp = client.get("/hello")\n'
            'print(resp.json())\n'
            '</textarea>'
            '<pre class="pg-out" id="pgOutput">Click "Run" to execute</pre>'
            '</div>'
        )
        html = Layout(base_url=base_url,
            title="Playground — Spry",
            description="Teste Spry no navegador",
            body=body,
            active_slug="",
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
        ).render()
        return Response.html(html)

    def run_code(request: Request) -> Response:
        data = request.json()
        code = data.get("code", "")
        import tempfile, subprocess, sys, os as os_mod
        import_paths = os_mod.pathsep.join(
            [str(Path(__file__).resolve().parents[3] / "src"),
             str(Path(__file__).resolve().parents[2] / "src")]
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(f"import sys\nsys.path.insert(0, '{str(Path(__file__).resolve().parents[3]/'src').replace(chr(92), '/')}')\n")
            f.write(code)
            f.flush()
        try:
            result = subprocess.run(
                [sys.executable, f.name],
                capture_output=True, text=True, timeout=10,
                env={**os_mod.environ, "PYTHONPATH": import_paths},
            )
            return Response.json({
                "output": result.stdout,
                "error": result.stderr,
            })
        except subprocess.TimeoutExpired:
            return Response.json({"error": "Execution timed out"}, 408)
        except Exception as e:
            return Response.json({"error": str(e)}, 500)
        finally:
            Path(f.name).unlink(missing_ok=True)

    builder.map_get(base_url or "/", landing_page)
    def docs_page_locale(locale: str, slug: str, request: Request) -> Response:
        # Set locale cookie and redirect to the standard path
        import json
        from spry.http import Response as R
        resp = docs_page(slug, request)
        resp.set_cookie("spry_locale", locale, path="/")
        return resp

    builder.map_get(f"{base_url}/docs/{{slug}}", docs_page)
    builder.map_get(f"{base_url}/docs/{{locale}}/{{slug}}", docs_page_locale)
    builder.map_get(f"{base_url}/search-index.json", search_index)
    builder.map_get(f"{base_url}/api/{{path:path}}", api_page)
    builder.map_get(f"{base_url}/assets/{{name}}", asset)
    builder.map_get(f"{base_url}/changelog", change_log)
    def favicon() -> Response:
        return Response.empty(204)

    builder.map_get(f"{base_url}/playground", playground)
    builder.map_post(f"{base_url}/api/run", run_code)
    builder.map_get(f"{base_url}/favicon.ico", favicon)

    return builder.build()
