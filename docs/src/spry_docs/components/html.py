from __future__ import annotations

import json
import re
from html import escape
from typing import Any


def _escape_and_tag(code: str) -> str:
    """Escape HTML in code, then tag the injected markup markers."""
    return escape(code)


def _apply_tags(text: str, tag_map: list[tuple[re.Pattern, str]]) -> str:
    for pattern, template in tag_map:
        text = pattern.sub(template, text)
    return text


_PY_RULES = [
    (re.compile(r"\b(def|class|return|if|elif|else|for|while|import|from|as|async|await|with|try|except|finally|raise|pass|None|True|False|in|not|and|or|is|lambda|yield|self|super|print|len|range|type|dict|list|set|str|int|float|bool|tuple|Any|Optional|Union)\b"), r'<span class=tk-kw>\1</span>'),
    (re.compile(r"""(?<!=)'([^']*?)'"""), r"<span class=tk-str>'\1'</span>"),
    (re.compile(r'\x22([^\x22]*?)\x22'), r'<span class=tk-str>"\1"</span>'),
    (re.compile(r"(#.*?)$", re.MULTILINE), r'<span class=tk-cm>\1</span>'),
    (re.compile(r"@(\w+)"), r'<span class=tk-dc>@\1</span>'),
    (re.compile(r"\b(\d+)\b"), r'<span class=tk-num>\1</span>'),
]

_BASH_RULES = [
    (re.compile(r"(spry|python|pip|cd|mkdir|gunicorn|uvicorn|waitress)"), r'<span class=tk-cmd>\1</span>'),
    (re.compile(r"(--[\w-]+)"), r'<span class=tk-fl>\1</span>'),
    (re.compile(r"(\$[\w{}]+)"), r'<span class=tk-ev>\1</span>'),
]

_JSON_RULES = [
    (re.compile(r'("(?:[^"\\]|\\.)*")\s*:'), r'<span class=tk-key>\1</span>:'),
    (re.compile(r':\s*("(?:[^"\\]|\\.)*")'), r': <span class=tk-str>\1</span>'),
    (re.compile(r":\s*(\d+\.?\d*)"), r': <span class=tk-num>\1</span>'),
    (re.compile(r":\s*(true|false|null)", re.IGNORECASE), r': <span class=tk-kw>\1</span>'),
]

_HTML_RULES = [
    (re.compile(r"(&lt;/?)(\w+)"), r'\1<span class=tk-tag>\2</span>'),
    (re.compile(r'(\w+)="(.*?)"'), r'<span class=tk-attr>\1</span>="<span class=tk-str>\2</span>"'),
]


def _highlight_python(code: str) -> str:
    code = escape(code)
    return _apply_tags(code, _PY_RULES)


def _highlight_bash(code: str) -> str:
    code = escape(code)
    return _apply_tags(code, _BASH_RULES)


def _highlight_json(code: str) -> str:
    code = escape(code)
    return _apply_tags(code, _JSON_RULES)


def _highlight_html(code: str) -> str:
    code = escape(code)
    return _apply_tags(code, _HTML_RULES)


def highlight(code: str, language: str) -> str:
    if language == "python":
        return _highlight_python(code)
    if language in {"bash", "sh", "shell", "powershell"}:
        return _highlight_bash(code)
    if language == "json":
        return _highlight_json(code)
    if language in {"html", "xml"}:
        return _highlight_html(code)
    return escape(code)


class CodeBlock:
    def __init__(self, code: str, language: str = "") -> None:
        self.code = code
        self.language = language

    def render(self) -> str:
        highlighted = highlight(self.code, self.language)
        label = f'<span class="cl-lang">{self.language}</span>' if self.language else ""
        return (
            f'<div class="cl-block">'
            f'<div class="cl-hd">{label}<button class="cl-copy" onclick="copyCode(this)">Copy</button></div>'
            f'<pre class="cl-bd language-{self.language}"><code>{highlighted}</code></pre>'
            f'</div>'
        )


class Note:
    def __init__(self, content: str, note_type: str = "info") -> None:
        self.content = content
        self.note_type = note_type

    def render(self) -> str:
        icons = {"tip": "💡", "warning": "⚠️", "danger": "🚫", "info": "ℹ️"}
        icon = icons.get(self.note_type, "ℹ️")
        return (
            f'<div class="note note-{self.note_type}">'
            f'<div class="note-ico">{icon}</div>'
            f'<div class="note-bd">{self.content}</div>'
            f'</div>'
        )


class Tabs:
    def __init__(self, tabs: list[dict[str, str]]) -> None:
        self.tabs = tabs

    def render(self) -> str:
        items = "".join(
            f'<button class="tb-btn{" is-active" if i == 0 else ""}" '
            f'onclick="switchTab(this, `tb-{i}`)" data-tab="tb-{i}">'
            f'{t.get("language", "code")}</button>'
            for i, t in enumerate(self.tabs)
        )
        panels = "".join(
            f'<div class="tb-pnl{" is-active" if i == 0 else ""}" id="tb-{i}">'
            f'{CodeBlock(t["code"], t.get("language", "")).render()}'
            f'</div>'
            for i, t in enumerate(self.tabs)
        )
        return f'<div class="tabs"><div class="tb-hd">{items}</div>{panels}</div>'


class Table:
    def __init__(self, headers: list[str], rows: list[list[str]]) -> None:
        self.headers = headers
        self.rows = rows

    def render(self) -> str:
        hd = "".join(f"<th>{escape(h)}</th>" for h in self.headers)
        rws = "".join(
            "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>"
            for row in self.rows
        )
        return f'<div class="tbl-wrp"><table class="tbl"><thead><tr>{hd}</tr></thead><tbody>{rws}</tbody></table></div>'


class Card:
    def __init__(self, title: str, description: str, link: str, icon: str = "→") -> None:
        self.title = title
        self.description = description
        self.link = link
        self.icon = icon

    def render(self) -> str:
        return (
            f'<a href="{self.link}" class="card">'
            f'<div class="card-ico">{self.icon}</div>'
            f'<div class="card-tl">{escape(self.title)}</div>'
            f'<div class="card-desc">{escape(self.description)}</div>'
            f'</a>'
        )


class SearchBar:
    def render(self) -> str:
        return (
            '<div class="srch">'
            '<input type="text" class="srch-inp" placeholder="Search docs..." '
            'oninput="searchDocs(this.value)" id="searchInput" />'
            '<div class="srch-ico">🔍</div>'
            '<div class="srch-rs" id="searchResults"></div>'
            '</div>'
        )


class Sidebar:
    def __init__(self, pages: list[dict[str, Any]], active_slug: str = "") -> None:
        self.pages = pages
        self.active_slug = active_slug

    def render(self) -> str:
        items = "".join(
            f'<a href="/docs/{p["slug"]}" class="sb-item{" is-active" if p["slug"] == self.active_slug else ""}">'
            f'{escape(p.get("title", p["slug"]))}</a>'
            for p in self.pages
        )
        return f'<nav class="sb">{items}</nav>'


class Breadcrumb:
    def __init__(self, path: list[tuple[str, str]]) -> None:
        self.path = path

    def render(self) -> str:
        items = "".join(
            f'<span class="bc-item"><a href="{link}">{escape(label)}</a></span>'
            f'{"<span class=\"bc-sep\">/</span>" if i < len(self.path) - 1 else ""}'
            for i, (label, link) in enumerate(self.path)
        )
        return f'<nav class="bc">{items}</nav>'


class VersionSelector:
    def __init__(self, versions: list[str], current: str = "") -> None:
        self.versions = versions
        self.current = current

    def render(self) -> str:
        opts = "".join(
            f'<option value="{v}"{" selected" if v == self.current else ""}>{v}</option>'
            for v in self.versions
        )
        return f'<select class="vs" onchange="switchVersion(this.value)">{opts}</select>'


class Diagram:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def render(self) -> str:
        diagram_type = self.data.get("type", "flow")
        label = self.data.get("label", "")
        if diagram_type == "flow":
            return self._render_flow()
        if diagram_type == "box":
            return self._render_box()
        if diagram_type == "relation":
            return self._render_relation()
        return f'<div class="dgm">{escape(label)}</div>'

    def _render_flow(self) -> str:
        steps = self.data.get("steps", [])
        items = "".join(
            f'<div class="flw-step"><div class="flw-n">{i+1}</div><div class="flw-l">{escape(s)}</div></div>'
            for i, s in enumerate(steps)
        )
        return f'<div class="dgm dgm-flw">{items}</div>'

    def _render_box(self) -> str:
        title = self.data.get("title", "")
        items = self.data.get("items", [])
        inner = "".join(f'<div class="bx-item">{escape(i)}</div>' for i in items)
        return f'<div class="dgm dgm-bx"><div class="bx-tl">{escape(title)}</div>{inner}</div>'

    def _render_relation(self) -> str:
        entities = self.data.get("entities", [])
        items = "".join(
            f'<div class="rel-ent">{escape(e.get("name", ""))}'
            f'<div class="rel-flds">'
            + "".join(f'<span class="rel-fld">{escape(f)}</span>' for f in e.get("fields", []))
            + f'</div></div>'
            for e in entities
        )
        conn = self.data.get("connection", "→")
        return f'<div class="dgm dgm-rel">{items}<div class="rel-conn">{escape(conn)}</div></div>'


class Playground:
    def __init__(self, code: str, language: str = "python") -> None:
        self.code = code
        self.language = language

    def render(self) -> str:
        code_escaped = escape(self.code)
        return (
            f'<div class="pg">'
            f'<div class="pg-hd">'
            f'<span class="pg-lang">{self.language}</span>'
            f'<button class="pg-run" onclick="runPlayground(this)">Run ▶</button>'
            f'</div>'
            f'<textarea class="pg-ed" data-lang="{self.language}" rows="8">{code_escaped}</textarea>'
            f'<pre class="pg-out" id="pgOutput"></pre>'
            f'</div>'
        )


class Layout:
    def __init__(
        self,
        title: str,
        description: str,
        body: str,
        active_slug: str = "",
        pages: list[dict[str, Any]] | None = None,
        locale: str = "pt",
        version: str = "0.1.0",
        versions: list[str] | None = None,
        canonical: str = "",
        csp_nonce: str = "",
    ) -> None:
        self.title = title
        self.description = description
        self.body = body
        self.active_slug = active_slug
        self.pages = pages or []
        self.locale = locale
        self.version = version
        self.versions = versions or ["0.1.0"]
        self.canonical = canonical
        self.csp_nonce = csp_nonce

    def render(self) -> str:
        sidebar = Sidebar(self.pages, self.active_slug).render()
        search = SearchBar().render()
        vs = VersionSelector(self.versions, self.version).render()
        alt_locale = "en" if self.locale == "pt" else "pt"
        alt_label = "🇺🇸 EN" if self.locale == "pt" else "🇧🇷 PT"
        canonical_tag = f'<link rel="canonical" href="{self.canonical}"/>' if self.canonical else ""

        return f"""<!DOCTYPE html>
<html lang="{self.locale}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="description" content="{escape(self.description)}"/>
<title>{escape(self.title)} — Spry</title>
{canonical_tag}
<meta property="og:title" content="{escape(self.title)}"/>
<meta property="og:description" content="{escape(self.description)}"/>
<meta property="og:type" content="website"/>
<meta name="twitter:card" content="summary"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/assets/site.css"/>
</head>
<body>
<div class="topbar">
  <a href="/" class="tb-brand">spry</a>
  <div class="tb-nav">
    <a href="/docs/getting-started" class="tb-link">Docs</a>
    <a href="/api/spry/app" class="tb-link">API</a>
    <a href="/playground" class="tb-link">Playground</a>
  </div>
  <div class="tb-right">
    {vs}
    <a href="#" onclick="event.preventDefault();document.cookie='spry_locale={alt_locale};path=/';window.location.href='/docs/getting-started'" class="tb-locale">{alt_label}</a>
    <button class="tb-menu" onclick="toggleMobileMenu()">☰</button>
  </div>
</div>

<div class="mobile-nav" id="mobileNav" onclick="closeMobileMenu(event)">
  <div class="mn-inner">
    <a href="/" class="mn-link">Home</a>
    <a href="/docs/getting-started" class="mn-link">Docs</a>
    <a href="/api/spry/app" class="mn-link">API</a>
    <a href="/playground" class="mn-link">Playground</a>
    {search}
  </div>
</div>

<div class="layout">
  <aside class="layout-sb">
    {search}
    {sidebar}
  </aside>
  <main class="layout-main">
    {self.body}
  </main>
</div>

<footer class="ftr">
  <p>Spry {self.version} — MIT License</p>
  <p><a href="https://github.com/anomalyco/spry">GitHub</a></p>
</footer>

<script>
const SEARCH_INDEX_URL = '/search-index.json';
let searchIndex = null;

async function loadSearchIndex() {{
  if (!searchIndex) {{
    const res = await fetch(SEARCH_INDEX_URL);
    searchIndex = await res.json();
  }}
  return searchIndex;
}}

async function searchDocs(query) {{
  const results = document.getElementById('searchResults');
  if (!query || query.length < 2) {{ results.innerHTML = ''; results.style.display = 'none'; return; }}
  const q = query.toLowerCase();
  const index = await loadSearchIndex();
  const hits = index
    .map(entry => ({{
      ...entry,
      score: (entry.title.toLowerCase().includes(q) ? 10 : 0) +
             (entry.snippet.toLowerCase().includes(q) ? 5 : 0) +
             entry.tags.filter(t => t.toLowerCase().includes(q)).length * 3
    }}))
    .filter(e => e.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
  if (hits.length === 0) {{
    results.innerHTML = '<div class="srch-nr">No results</div>';
  }} else {{
    results.innerHTML = hits.map(h =>
      `<a href="${{h.slug}}" class="srch-r"><span class="srch-t">${{h.title}}</span><span class="srch-s">${{h.snippet.slice(0, 100)}}</span></a>`
    ).join('');
  }}
  results.style.display = 'block';
}}

document.addEventListener('click', function(e) {{
  const rs = document.getElementById('searchResults');
  if (rs && !e.target.closest('.srch')) {{
    rs.style.display = 'none';
  }}
}});

function switchTab(btn, tabId) {{
  const parent = btn.closest('.tabs');
  parent.querySelectorAll('.tb-btn').forEach(b => b.classList.remove('is-active'));
  parent.querySelectorAll('.tb-pnl').forEach(p => p.classList.remove('is-active'));
  btn.classList.add('is-active');
  document.getElementById(tabId).classList.add('is-active');
}}

function copyCode(btn) {{
  const code = btn.closest('.cl-block').querySelector('code');
  navigator.clipboard.writeText(code.textContent);
  btn.textContent = 'Copied!';
  setTimeout(() => btn.textContent = 'Copy', 2000);
}}

function toggleMobileMenu() {{
  document.getElementById('mobileNav').classList.toggle('is-open');
}}

function closeMobileMenu(e) {{
  if (e.target === e.currentTarget) {{
    e.currentTarget.classList.remove('is-open');
  }}
}}

function switchVersion(version) {{
  window.location.href = window.location.pathname + '?v=' + version;
}}

async function runPlayground(btn) {{
  const pg = btn.closest('.pg');
  const code = pg.querySelector('.pg-ed').value;
  const output = pg.querySelector('.pg-out');
  output.textContent = 'Running...';
  try {{
    const res = await fetch('/api/run', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ code: code }})
    }});
    const data = await res.json();
    if (data.error) {{
      output.textContent = 'Error:\\n' + data.error;
    }} else {{
      output.textContent = data.output || '(no output)';
      if (data.output && data.error) {{
        output.textContent += '\\n\\nStderr:\\n' + data.error;
      }}
    }}
  }} catch (e) {{
    output.textContent = 'Request failed: ' + e.message;
  }}
}}
</script>
</body>
</html>"""
