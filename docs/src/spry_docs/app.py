from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from spry.app import AppBuilder
from spry.http import Request, Response
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
        try:
            from spry import __version__
            VERSION = __version__
        except Exception:
            VERSION = "0.1.0"
        VERSIONS = [VERSION]
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
    "getting-started": {"pt": "Começando", "en": "Getting Started", "fr": "Pour commencer"},
    "api-development": {"pt": "Desenvolvimento de API", "en": "API Development", "fr": "Développement d'API"},
    "mvc-development": {"pt": "Desenvolvimento MVC", "en": "MVC Development", "fr": "Développement MVC"},
    "orm-data": {"pt": "ORM e Dados", "en": "ORM and Data", "fr": "ORM et Données"},
    "auth-security": {"pt": "Autenticação e Segurança", "en": "Auth and Security", "fr": "Authentification et Sécurité"},
    "tooling-cli": {"pt": "Ferramentas e CLI", "en": "Tools and CLI", "fr": "Outils et CLI"},
    "testing": {"pt": "Testes", "en": "Testing", "fr": "Tests"},
    "deployment": {"pt": "Deploy", "en": "Deployment", "fr": "Déploiement"},
    "architecture": {"pt": "Arquitetura", "en": "Architecture", "fr": "Architecture"},
    "troubleshooting": {"pt": "Solução de Problemas", "en": "Troubleshooting", "fr": "Dépannage"},
}

DOC_DESCRIPTIONS = {
    "getting-started": {"pt": "Instalação e primeiro projeto", "en": "Installation and first project", "fr": "Installation et premier projet"},
    "api-development": {"pt": "Controllers, middleware e validação", "en": "Controllers, middleware and validation", "fr": "Contrôleurs, middleware et validation"},
    "mvc-development": {"pt": "Views, layouts e HTML server-side", "en": "Views, layouts and server-side HTML", "fr": "Vues, layouts et HTML côté serveur"},
    "orm-data": {"pt": "DbContext, migrações e relacionamentos", "en": "DbContext, migrations and relationships", "fr": "DbContext, migrations et relations"},
    "auth-security": {"pt": "Auth, CORS, CSRF e rate limiting", "en": "Auth, CORS, CSRF and rate limiting", "fr": "Auth, CORS, CSRF et rate limiting"},
    "tooling-cli": {"pt": "CLI, scaffolding e ferramentas", "en": "CLI, scaffolding and tools", "fr": "CLI, scaffolding et outils"},
    "testing": {"pt": "TestClient e testes de integração", "en": "TestClient and integration tests", "fr": "TestClient et tests d'intégration"},
    "deployment": {"pt": "Produção, Docker e deploy", "en": "Production, Docker and deployment", "fr": "Production, Docker et déploiement"},
    "architecture": {"pt": "Visão interna do framework", "en": "Framework internals", "fr": "Vue interne du framework"},
    "troubleshooting": {"pt": "Erros comuns e soluções", "en": "Common errors and solutions", "fr": "Erreurs courantes et solutions"},
}


LANG_MAP = {
    "pt": "PT",
    "en": "EN",
    "fr": "FR",
}

FLAG_MAP = {
    "pt": "br",
    "en": "us",
    "fr": "fr",
}

UI_STRINGS: dict[str, dict[str, str]] = {
    "hero_title": {"pt": "Spry Framework", "en": "Spry Framework", "fr": "Spry Framework"},
    "hero_subtitle": {
        "pt": "Framework Python opinado para APIs e web apps. Zero boilerplate, controle total, pronto para produção.",
        "en": "Opinionated Python web framework for APIs and web apps. Zero boilerplate, full control, production-ready.",
        "fr": "Framework Python opiné pour APIs et applications web. Zéro boilerplate, contrôle total, prêt pour la production.",
    },
    "hero_cta": {"pt": "Começar", "en": "Get Started", "fr": "Commencer"},
    "meta_description": {
        "pt": "Framework Python opinado para APIs e web apps",
        "en": "Opinionated Python web framework for APIs and web apps",
        "fr": "Framework Python opiné pour APIs et applications web",
    },
    "page_not_found": {"pt": "Página não encontrada", "en": "Page not found", "fr": "Page non trouvée"},
    "docs_not_found": {
        "pt": "A documentação para <code>{slug}</code> não foi encontrada.",
        "en": "Documentation for <code>{slug}</code> was not found.",
        "fr": "La documentation pour <code>{slug}</code> n'a pas été trouvée.",
    },
    "view_docs": {"pt": "Ver documentação", "en": "View documentation", "fr": "Voir la documentation"},
    "browse_modules": {
        "pt": "Navegue pelos módulos do Spry:",
        "en": "Browse Spry modules:",
        "fr": "Parcourez les modules Spry :",
    },
    "module_not_found": {"pt": "Módulo não encontrado", "en": "Module not found", "fr": "Module non trouvé"},
    "soon": {"pt": "Em breve.", "en": "Coming soon.", "fr": "Bientôt."},
    "version_history": {"pt": "Histórico de versões", "en": "Version history", "fr": "Historique des versions"},
    "playground_desc": {
        "pt": "Teste código Spry diretamente no navegador.",
        "en": "Test Spry code directly in the browser.",
        "fr": "Testez le code Spry directement dans le navigateur.",
    },
    "back_to_home": {"pt": "Voltar ao início", "en": "Back to home", "fr": "Retour à l'accueil"},
    "page_moved": {
        "pt": "A página que você procura não existe ou foi movida.",
        "en": "The page you are looking for does not exist or has been moved.",
        "fr": "La page que vous cherchez n'existe pas ou a été déplacée.",
    },
    "go_back": {"pt": "Voltar ao início", "en": "Back to home", "fr": "Retour à l'accueil"},
    "api_ref_title": {"pt": "API Reference", "en": "API Reference", "fr": "API Reference"},
    "changelog_title": {"pt": "Changelog", "en": "Changelog", "fr": "Changelog"},
    "playground_title": {"pt": "Playground", "en": "Playground", "fr": "Playground"},
}

FEATURE_CARDS = {
    "pt": [
        ("⚡", "Rápido", "Crie APIs completas em 5 minutos"),
        ("🧩", "Modular", "DI container, middleware pipeline, ORM próprio"),
        ("📖", "Legível", "Código explícito sem magia"),
        ("🔒", "Seguro", "CORS, CSRF, JWT, rate limiting inclusos"),
        ("📝", "OpenAPI", "Swagger UI automático"),
        ("🗄️", "Multi-DB", "SQLite, PostgreSQL, MySQL, SQL Server"),
    ],
    "en": [
        ("⚡", "Fast", "Build complete APIs in 5 minutes"),
        ("🧩", "Modular", "DI container, middleware pipeline, own ORM"),
        ("📖", "Readable", "Explicit code without magic"),
        ("🔒", "Secure", "CORS, CSRF, JWT, rate limiting included"),
        ("📝", "OpenAPI", "Automatic Swagger UI"),
        ("🗄️", "Multi-DB", "SQLite, PostgreSQL, MySQL, SQL Server"),
    ],
    "fr": [
        ("⚡", "Rapide", "Créez des API complètes en 5 minutes"),
        ("🧩", "Modulaire", "Conteneur DI, pipeline middleware, ORM intégré"),
        ("📖", "Lisible", "Code explicite sans magie"),
        ("🔒", "Sécurisé", "CORS, CSRF, JWT, rate limiting inclus"),
        ("📝", "OpenAPI", "Swagger UI automatique"),
        ("🗄️", "Multi-DB", "SQLite, PostgreSQL, MySQL, SQL Server"),
    ],
}


def _ui(locale: str, key: str, **kwargs: str) -> str:
    val = UI_STRINGS.get(key, {}).get(locale, UI_STRINGS.get(key, {}).get("en", key))
    return val.format(**kwargs) if kwargs else val


def _detect_locale(request: Request) -> str:
    cookie_locale = request.cookies.get("spry_locale")
    if cookie_locale in ("pt", "en", "fr"):
        return cookie_locale
    accept = request.headers.get("Accept-Language", "")
    if accept.startswith("fr"):
        return "fr"
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


def _build_search_index(locale: str, base_url: str = "") -> list[dict[str, Any]]:
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
            "slug": f"{base_url}/{locale}/docs/{slug}",
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
                for i, t, d in FEATURE_CARDS.get(locale, FEATURE_CARDS["en"])
            )
            + "</div>"
        )

        body = (
            '<div class="hero">'
            f'<h1>Spry Framework</h1>'
            f'<p>{_ui(locale, "hero_subtitle")}</p>'
            '<div class="hero-actions">'
            f'<a href="{base_url}/{locale}/docs/getting-started" class="btn btn-primary">{_ui(locale, "hero_cta")}</a>'
            f'<a href="{base_url}/playground" class="btn btn-secondary">Playground</a>'
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
                f'<a href="{base_url}/{locale}/docs/{p["slug"]}" class="card">'
                f'<div class="card-tl">{p["title"]}</div>'
                f'<div class="card-desc">{p.get("description", "")}</div>'
                f"</a>"
                for p in pages[:6]
            )
            + "</div>"
        )

        html = Layout(base_url=base_url,
            title="Spry Framework",
            description=_ui(locale, "meta_description"),
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
                f'<h1>{_ui(locale, "page_not_found")}</h1>'
                f'<p>{_ui(locale, "docs_not_found", slug=slug)}</p>'
                f'<a href="{base_url}/{locale}/docs/getting-started" class="btn btn-primary">{_ui(locale, "view_docs")}</a>'
            )
            html = Layout(base_url=base_url,
                title="404",
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
            f'<span class="bc-item"><a href="{base_url or "/"}">Spry</a></span>'
            f'<span class="bc-sep">/</span>'
            f'<span class="bc-item">{title}</span>'
            f'</nav>'
            f'<h1>{title}</h1>'
            f'<p class="page-desc">{desc}</p>'
            f'<div class="toc">{toc_items}</div>'
            f'{sections_html}'
        )

        html = Layout(base_url=base_url,
            title=title,
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

    def search_index(request: Request, locale: str = "") -> Response:
        if locale not in ("pt", "en", "fr"):
            locale = _detect_locale(request)
        index = _build_search_index(locale, base_url)
        return Response.json(index)

    def api_page(path: str, request: Request) -> Response:
        from spry_docs.apigen import generate_api_page, load_api_index
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        api_index = load_api_index()

        if not path:
            body = (
                f'<h1>{_ui(locale, "api_ref_title")}</h1>'
                f'<p>{_ui(locale, "browse_modules")}</p>'
                + "".join(
                    f'<a href="{base_url}/api/{m}" class="card">'
                    f'<div class="card-tl">{m}</div>'
                    f'<div class="card-desc">{d}</div></a>'
                    for m, d in api_index
                )
            )
        else:
            page = generate_api_page(path, base_url)
            body = f"<h1>{_ui(locale, 'module_not_found')}</h1><p>{path}</p>" if page is None else page

        html = Layout(base_url=base_url,
            title="API",
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
            body = f"<h1>{_ui(locale, 'changelog_title')}</h1><p>{_ui(locale, 'soon')}</p>"
        else:
            from spry_docs.render.parser import parse_markdown
            _, blocks = parse_markdown(changelog_path.read_text("utf-8"))
            body = f"<h1>{_ui(locale, 'changelog_title')}</h1>" + "".join(render_block(b) for b in blocks)

        html = Layout(base_url=base_url,
            title=_ui(locale, "changelog_title"),
            description=_ui(locale, "version_history"),
            body=body,
            active_slug="",
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
        ).render()
        return Response.html(html)

    def playground(request: Request) -> Response:
        from spry_docs.components import Playground as PlaygroundComponent
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        code = (
            'from spry.app import AppBuilder\n'
            'from spry.controllers import ControllerBase\n'
            'from spry.routing import controller, get\n\n'
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
        )
        body = (
            f'<h1>{_ui(locale, "playground_title")}</h1>'
            f'<p>{_ui(locale, "playground_desc")}</p>'
            + PlaygroundComponent(code, rows=14).render()
        )
        html = Layout(base_url=base_url,
            title=_ui(locale, "playground_title"),
            description=_ui(locale, "playground_desc"),
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
        # Force the given locale regardless of cookie/headers
        if locale not in ("pt", "en", "fr"):
            locale = "pt"
        forced_pages = _load_pages(locale)
        if slug not in PAGE_ORDER:
            body = (
                f'<h1>{_ui(locale, "page_not_found")}</h1>'
                f'<p>{_ui(locale, "docs_not_found", slug=slug)}</p>'
                f'<a href="{base_url}/{locale}/docs/getting-started" class="btn btn-primary">{_ui(locale, "view_docs")}</a>'
            )
            html = Layout(base_url=base_url,
                title="404",
                description="Page not found",
                body=body,
                active_slug="",
                pages=forced_pages,
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
            f'<span class="bc-item"><a href="{base_url or "/"}">Spry</a></span>'
            f'<span class="bc-sep">/</span>'
            f'<span class="bc-item">{title}</span>'
            f'</nav>'
            f'<h1>{title}</h1>'
            f'<p class="page-desc">{desc}</p>'
            f'<div class="toc">{toc_items}</div>'
            f'{sections_html}'
        )
        html = Layout(base_url=base_url,
            title=title,
            description=desc or fm.description,
            body=body,
            active_slug=slug,
            pages=forced_pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
            canonical=f"{base_url}/{locale}/docs/{slug}",
        ).render()
        resp = Response.html(html)
        resp.set_cookie("spry_locale", locale, path="/")
        return resp

    builder.map_get(f"{base_url}/docs/{{slug}}", docs_page)
    builder.map_get(f"{base_url}/docs/{{locale}}/{{slug}}", docs_page_locale)
    builder.map_get(f"{base_url}/{{locale}}/docs/{{slug}}", docs_page_locale)
    builder.map_get(f"{base_url}/search-index.json", search_index)
    builder.map_get(f"{base_url}/{{locale}}/search-index.json", search_index)
    builder.map_get(f"{base_url}/api", lambda request: api_page("", request))
    builder.map_get(f"{base_url}/api/", lambda request: api_page("", request))
    builder.map_post(f"{base_url}/api/run", run_code)
    builder.map_get(f"{base_url}/api/{{path:path}}", api_page)
    builder.map_get(f"{base_url}/assets/{{name}}", asset)
    builder.map_get(f"{base_url}/changelog", change_log)
    def favicon() -> Response:
        return Response.empty(204)

    builder.map_get(f"{base_url}/playground", playground)
    builder.map_get(f"{base_url}/favicon.ico", favicon)

    def not_found(request: Request) -> Response:
        locale = _detect_locale(request)
        pages = _load_pages(locale)
        body = (
            '<div style="text-align:center;padding:80px 0">'
            '<h1>404</h1>'
            f'<p style="font-size:18px;margin-bottom:8px">{_ui(locale, "page_not_found")}</p>'
            f'<p style="color:var(--tx3);margin-bottom:32px">{_ui(locale, "page_moved")}</p>'
            f'<a href="{base_url or "/"}" class="btn btn-primary">{_ui(locale, "go_back")}</a>'
            '</div>'
        )
        html = Layout(base_url=base_url,
            title="404",
            description="Page not found",
            body=body,
            active_slug="",
            pages=pages,
            locale=locale,
            version=VERSION,
            versions=VERSIONS,
        ).render()
        return Response.html(html, status_code=404)

    builder.map_get(f"{base_url}/{{rest:path}}", not_found)

    return builder.build()
