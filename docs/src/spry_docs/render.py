from __future__ import annotations

import re
from html import escape

from spry_docs.content import PAGE_MAP, PAGES, Page, Section


def render_home() -> str:
    page_links = "\n".join(
        f'<a class="path-card" href="/docs/{page.slug}"><span class="path-card__eyebrow">{escape(page.eyebrow)}</span><strong>{escape(page.title)}</strong><p>{escape(page.summary)}</p></a>'
        for page in PAGES
    )
    features = "\n".join(
        f"<li>{feature}</li>"
        for feature in [
            "Bootstrap enxuto com `AppBuilder`.",
            "Controllers descobertos automaticamente e handlers avulsos quando necessario.",
            "ORM leve com `DbContext`, `DbSet` e relacoes simples.",
            "CLI para scaffold, run, watch, migrate, seed e troubleshooting mais previsivel.",
        ]
    )
    body = f'''
    <section class="hero">
      <div class="hero__copy">
        <span class="eyebrow">Spry v0.2</span>
        <h1>Documentacao para um framework Python opinado, pragmatico e direto.</h1>
        <p class="hero__lede">Spry junta o feeling de ASP.NET Core com uma ergonomia mais pythonic: `dataclasses`, DI leve, descoberta automatica de controllers, MVC com views em arquivo e um ORM voltado ao caminho feliz.</p>
        <div class="hero__actions">
          <a class="button button--primary" href="/docs/getting-started">Comecar agora</a>
          <a class="button button--ghost" href="/docs/troubleshooting">Resolver problemas comuns</a>
        </div>
      </div>
      <div class="hero__preview">
        <div class="hero__terminal">
          <div class="terminal-bar">
            <span></span><span></span><span></span>
          </div>
          <pre><code>spry new taskboard\nspry run --app taskboard.app:create_app\nspry migrate add initial --context taskboard.data:AppDbContext\nspry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db</code></pre>
        </div>
        {render_visual("home-preview")}
      </div>
    </section>

    <section class="overview-grid">
      <article class="panel panel--accent">
        <span class="panel__eyebrow">Porque Spry</span>
        <h2>Reduza boilerplate sem cair em uma API magica demais.</h2>
        <ul class="feature-list">{features}</ul>
      </article>
      <article class="panel">
        <span class="panel__eyebrow">Fluxo sugerido</span>
        <ol class="steps">
          <li>Gere um projeto com `spry new`.</li>
          <li>Modele suas entidades com `dataclasses`.</li>
          <li>Registre `DbContext`, middleware e views quando precisar.</li>
          <li>Suba localmente com `spry run` ou `spry watch`.</li>
        </ol>
      </article>
    </section>

    <section class="paths">
      <div class="section-heading">
        <span class="eyebrow">Mapeamento rapido</span>
        <h2>Escolha uma trilha</h2>
      </div>
      <div class="path-grid">
        {page_links}
      </div>
    </section>
    '''
    return render_layout(
        title="Spry Docs",
        description="Site oficial de documentacao do framework Spry.",
        body=body,
        active_slug=None,
    )


def render_docs_page(page: Page) -> str:
    toc = "\n".join(
        f'<li><a href="#{slugify(section.title)}">{escape(section.title)}</a></li>'
        for section in page.sections
    )
    sections = "\n".join(render_section(section) for section in page.sections)
    highlights = "\n".join(f"<li>{highlight}</li>" for highlight in page.highlights)
    body = f'''
    <div class="docs-shell">
      <aside class="docs-sidebar" data-sidebar>
        <div class="sidebar-card">
          <span class="eyebrow">Documentacao</span>
          <h2>Spry</h2>
          <p>Framework Python opinado com runtime HTTP, ORM e tooling para projetos pequenos e medios.</p>
        </div>
        <nav class="sidebar-nav">
          {render_sidebar(active_slug=page.slug)}
        </nav>
      </aside>
      <main class="docs-main">
        <header class="page-header">
          <span class="eyebrow">{escape(page.eyebrow)}</span>
          <h1>{escape(page.title)}</h1>
          <p class="page-header__summary">{escape(page.summary)}</p>
          <ul class="highlight-list">{highlights}</ul>
          <nav class="docs-jump">{render_page_jump(page)}</nav>
        </header>
        <div class="docs-content">
          <div class="docs-article">{sections}</div>
          <aside class="docs-toc">
            <div class="toc-card">
              <span class="eyebrow">Nesta pagina</span>
              <ul>{toc}</ul>
            </div>
          </aside>
        </div>
      </main>
    </div>
    '''
    return render_layout(
        title=f"{page.title} | Spry Docs",
        description=page.summary,
        body=body,
        active_slug=page.slug,
    )


def render_not_found() -> str:
    body = '''
    <section class="not-found panel panel--centered">
      <span class="eyebrow">404</span>
      <h1>Pagina nao encontrada</h1>
      <p>O endereco pedido nao existe no site de documentacao do Spry.</p>
      <a class="button button--primary" href="/">Voltar para a home</a>
    </section>
    '''
    return render_layout("404 | Spry Docs", "Pagina nao encontrada.", body, active_slug=None)


def render_layout(title: str, description: str, body: str, active_slug: str | None) -> str:
    sidebar = render_sidebar(active_slug)
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/assets/site.css" />
  </head>
  <body>
    <div class="site-shell">
      <header class="topbar">
        <a class="brand" href="/">
          <span class="brand__badge">S</span>
          <span>
            <strong>Spry</strong>
            <small>Python framework docs</small>
          </span>
        </a>
        <nav class="topbar__nav">
          <a href="/docs/getting-started">Getting Started</a>
          <a href="/docs/api-development">API</a>
          <a href="/docs/mvc-development">MVC</a>
          <a href="/docs/orm-and-data">ORM</a>
          <a href="/docs/tooling-and-cli">CLI</a>
          <a href="/docs/troubleshooting">Troubleshooting</a>
        </nav>
        <button class="menu-button" type="button" data-menu-button aria-label="Abrir navegacao">Menu</button>
      </header>
      <div class="mobile-nav" data-mobile-nav>
        <div class="mobile-nav__panel">
          <div class="mobile-nav__header">
            <strong>Navegacao</strong>
            <button class="menu-button menu-button--small" type="button" data-menu-close aria-label="Fechar navegacao">Fechar</button>
          </div>
          {sidebar}
        </div>
      </div>
      {body}
      <footer class="footer">
        <p>Spry e um framework experimental focado em reduzir boilerplate sem perder legibilidade.</p>
        <a href="/docs/architecture">Entender a arquitetura</a>
      </footer>
    </div>
    <script src="/assets/site.js"></script>
  </body>
</html>
'''


def render_sidebar(active_slug: str | None) -> str:
    items = ['<a class="sidebar-link {classes}" href="/">Overview</a>'.format(classes="is-active" if active_slug is None else "")]
    for page in PAGES:
        classes = "is-active" if page.slug == active_slug else ""
        items.append(f'<a class="sidebar-link {classes}" href="/docs/{page.slug}">{escape(page.title)}</a>')
    return "".join(items)


def render_section(section: Section) -> str:
    paragraphs = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in section.body)
    bullets = ""
    if section.bullets:
        bullet_items = "".join(f"<li>{escape(item)}</li>" for item in section.bullets)
        bullets = f"<ul class=\"section-list\">{bullet_items}</ul>"
    code = ""
    if section.code:
        code = render_code_block(section.code, section.code_language)
    visual = render_visual(section.visual) if section.visual else ""
    example_block = ""
    if code or visual:
        example_block = f'<div class="example-split">{visual}{code}</div>'
    note = f'<aside class="callout">{escape(section.note)}</aside>' if section.note else ""
    return f'''
    <section class="doc-section" id="{slugify(section.title)}">
      <div class="section-heading">
        <h2>{escape(section.title)}</h2>
      </div>
      {paragraphs}
      {bullets}
      {example_block}
      {note}
    </section>
    '''


def slugify(value: str) -> str:
    return "-".join(value.lower().replace("&", "and").split())


def render_page_jump(page: Page) -> str:
    return "".join(
        f'<a class="jump-chip" href="#{slugify(section.title)}">{escape(section.title)}</a>'
        for section in page.sections
    )


def render_visual(name: str | None) -> str:
    if not name:
        return ""
    visuals = {
        "home-preview": '''
        <div class="visual-demo visual-demo--home">
          <div class="mini-browser">
            <div class="mini-browser__bar"><span></span><span></span><span></span></div>
            <div class="mini-browser__body">
              <div class="mini-stat"><strong>5</strong><small>Rotas ativas</small></div>
              <div class="mini-stat"><strong>3</strong><small>Middlewares</small></div>
              <div class="mini-stat"><strong>1</strong><small>DbContext</small></div>
            </div>
          </div>
          <div class="stack-card stack-card--accent">
            <strong>AppBuilder</strong>
            <p>Config, DI, routes e pipeline em um ponto so.</p>
          </div>
          <div class="stack-card"><strong>Controllers</strong><p>Decorators legiveis para o fluxo web.</p></div>
        </div>
        ''',
        "todo-flow": '''
        <div class="visual-demo visual-demo--todo">
          <div class="demo-window">
            <div class="demo-window__header">
              <span class="demo-pill">POST /todos</span>
              <span class="demo-status">201 Created</span>
            </div>
            <div class="todo-board">
              <div class="todo-card"><span class="todo-badge todo-badge--done"></span><strong>Scaffold project</strong><small>persistido em SQLite</small></div>
              <div class="todo-card"><span class="todo-badge"></span><strong>Add middleware</strong><small>injetado por request</small></div>
              <div class="todo-card"><span class="todo-badge"></span><strong>Write docs</strong><small>payload validado</small></div>
            </div>
          </div>
        </div>
        ''',
        "routing-flow": '''
        <div class="visual-demo visual-demo--route">
          <div class="flow-row">
            <div class="flow-node"><strong>Request</strong><small>GET /todos/42</small></div>
            <div class="flow-arrow"></div>
            <div class="flow-node"><strong>Middleware</strong><small>headers, auth, logging</small></div>
            <div class="flow-arrow"></div>
            <div class="flow-node"><strong>Controller</strong><small>`get_by_id(id: int)`</small></div>
          </div>
        </div>
        ''',
        "orm-relations": '''
        <div class="visual-demo visual-demo--orm">
          <div class="relation-card">
            <span class="relation-card__label">Author</span>
            <strong>Ada Lovelace</strong>
            <small>id = 1</small>
          </div>
          <div class="relation-link"></div>
          <div class="relation-column">
            <div class="relation-card relation-card--child"><span class="relation-card__label">Post</span><strong>Hello Spry</strong><small>author_id = 1</small></div>
            <div class="relation-card relation-card--child"><span class="relation-card__label">Post</span><strong>SQLite Notes</strong><small>author_id = 1</small></div>
          </div>
        </div>
        ''',
        "cli-loop": '''
        <div class="visual-demo visual-demo--cli">
          <div class="command-steps">
            <div class="command-step"><span>1</span><strong>new</strong><small>gera a base</small></div>
            <div class="command-step"><span>2</span><strong>run</strong><small>sobe o app</small></div>
            <div class="command-step"><span>3</span><strong>watch</strong><small>reinicia ao salvar</small></div>
            <div class="command-step"><span>4</span><strong>migrate</strong><small>versiona schema</small></div>
          </div>
        </div>
        ''',
        "architecture-map": '''
        <div class="visual-demo visual-demo--architecture">
          <div class="arch-center">Application</div>
          <div class="arch-grid">
            <div class="arch-box"><strong>AppBuilder</strong><small>config + DI + routes</small></div>
            <div class="arch-box"><strong>Middleware</strong><small>pipeline por request</small></div>
            <div class="arch-box"><strong>Controllers</strong><small>handlers tipados</small></div>
            <div class="arch-box"><strong>DbContext</strong><small>persistencia e schema</small></div>
          </div>
        </div>
        ''',
    }
    html = visuals.get(name)
    return "" if html is None else html


def render_code_block(code: str, language: str | None) -> str:
    highlighted = highlight_code(code, language or infer_language(code))
    data_language = escape(language or infer_language(code))
    return f'<pre class="code-block" data-language="{data_language}"><code>{highlighted}</code></pre>'


def infer_language(code: str) -> str:
    stripped = code.lstrip()
    if stripped.startswith("{"):
        return "json"
    if stripped.startswith("<"):
        return "html"
    if stripped.startswith("pip ") or stripped.startswith("spry ") or stripped.startswith("python -m") or stripped.startswith("# PowerShell") or "$env:" in code:
        return "bash"
    return "python"


def highlight_code(code: str, language: str) -> str:
    if language == "python":
        return _highlight_python(code)
    if language == "bash":
        return _highlight_bash(code)
    if language == "json":
        return _highlight_json(code)
    if language == "html":
        return _highlight_html(code)
    return escape(code)


def _highlight_python(code: str) -> str:
    keywords = {
        "class", "def", "return", "from", "import", "if", "else", "for", "in", "with",
        "try", "finally", "raise", "None", "True", "False"
    }
    builtins = {"str", "int", "bool", "list", "dict"}
    lines: list[str] = []
    token_pattern = re.compile(r'(#[^\n]*|"[^"]*"|\'[^\']*\'|@[A-Za-z_][\w.]*|\b[A-Za-z_][A-Za-z0-9_]*\b)')

    for raw_line in code.splitlines():
        parts: list[str] = []
        last = 0
        for match in token_pattern.finditer(raw_line):
            parts.append(escape(raw_line[last:match.start()]))
            token = match.group(0)
            if token.startswith("#"):
                parts.append(f'<span class="tok-comment">{escape(token)}</span>')
            elif token.startswith("@"):
                parts.append(f'<span class="tok-decorator">{escape(token)}</span>')
            elif token.startswith(('"', "'")):
                parts.append(f'<span class="tok-string">{escape(token)}</span>')
            elif token in keywords:
                parts.append(f'<span class="tok-keyword">{escape(token)}</span>')
            elif token in builtins:
                parts.append(f'<span class="tok-type">{escape(token)}</span>')
            else:
                parts.append(f'<span class="tok-name">{escape(token)}</span>')
            last = match.end()
        parts.append(escape(raw_line[last:]))
        lines.append("".join(parts))
    return "\n".join(lines)


def _highlight_bash(code: str) -> str:
    commands = {"spry", "python", "pip", "cd", "set"}
    flags = re.compile(r'(?<![\w-])--?[A-Za-z0-9._-]+')
    lines: list[str] = []

    for raw_line in code.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("#"):
            lines.append(f'<span class="tok-comment">{escape(raw_line)}</span>')
            continue

        escaped_line = escape(raw_line)
        for match in flags.finditer(raw_line):
            escaped_line = escaped_line.replace(escape(match.group(0)), f'<span class="tok-flag">{escape(match.group(0))}</span>', 1)
        for command in commands:
            escaped_line = re.sub(rf'\b{re.escape(command)}\b', f'<span class="tok-command">{command}</span>', escaped_line, count=1)
        escaped_line = re.sub(r'(\$env:[A-Za-z_][A-Za-z0-9_]*)', r'<span class="tok-var">\1</span>', escaped_line)
        escaped_line = re.sub(r'("[^"]*")', r'<span class="tok-string">\1</span>', escaped_line)
        lines.append(escaped_line)
    return "\n".join(lines)


def _highlight_json(code: str) -> str:
    escaped = escape(code)
    escaped = re.sub(r'("[^"]+")(?=\s*:)', r'<span class="tok-key">\1</span>', escaped)
    escaped = re.sub(r':\s*("[^"]*")', r': <span class="tok-string">\1</span>', escaped)
    escaped = re.sub(r':\s*(-?\d+(?:\.\d+)?)', r': <span class="tok-number">\1</span>', escaped)
    escaped = re.sub(r'\b(true|false|null)\b', r'<span class="tok-keyword">\1</span>', escaped)
    return escaped


def _highlight_html(code: str) -> str:
    escaped = escape(code)
    escaped = re.sub(r'(&lt;/?)([A-Za-z0-9_-]+)', r'\1<span class="tok-tag">\2</span>', escaped)
    escaped = re.sub(r'\b([A-Za-z_:][-A-Za-z0-9_:]*)(=)', r'<span class="tok-attr">\1</span>\2', escaped)
    escaped = re.sub(r'("[^"]*")', r'<span class="tok-string">\1</span>', escaped)
    return escaped


__all__ = ["PAGE_MAP", "PAGES", "render_docs_page", "render_home", "render_not_found"]
