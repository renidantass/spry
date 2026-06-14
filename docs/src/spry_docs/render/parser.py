from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Frontmatter:
    title: str = ""
    order: int = 99
    description: str = ""
    tags: list[str] = field(default_factory=list)
    min_version: str = ""


@dataclass
class Block:
    type: str  # heading, paragraph, code, note, tabs, list, table, diagram
    level: int = 0
    content: Any = ""
    language: str = ""
    items: list[Any] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


SHORTCODE_RE = re.compile(
    r"\{%\s*(note|code-tabs|diagram|table|playground)"
    r"(.*?)\%\}(.*?)\{%\s*end\1\s*%\}",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
LIST_RE = re.compile(r"^(\s*[-*]\s+.+)$", re.MULTILINE)
TABLE_RE = re.compile(r"^\|.+\|\n\|[-| :]+\|\n(\|.+\|\n?)*", re.MULTILINE)


def parse_markdown(source: str) -> tuple[Frontmatter, list[Block]]:
    fm = Frontmatter()
    fm_match = FRONTMATTER_RE.match(source)
    if fm_match:
        try:
            fm_data = {}
            for line in fm_match.group(1).strip().split("\n"):
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm_data[k.strip()] = v.strip().strip('"').strip("'")
            fm = Frontmatter(
                title=fm_data.get("title", ""),
                order=int(fm_data.get("order", 99)),
                description=fm_data.get("description", ""),
                tags=[t.strip() for t in fm_data.get("tags", "").split(",") if t.strip()],
                min_version=fm_data.get("min_version", ""),
            )
        except Exception:
            pass
        source = source[fm_match.end():]

    body = source.strip()
    blocks = _parse_blocks(body)
    return fm, blocks


def _parse_blocks(source: str) -> list[Block]:
    blocks: list[Block] = []
    i = 0
    while i < len(source):
        shortcode_match = SHORTCODE_RE.search(source, i)
        if shortcode_match and shortcode_match.start() == i:
            blocks.append(_parse_shortcode(shortcode_match))
            i = shortcode_match.end()
            continue

        code_match = CODE_BLOCK_RE.search(source, i)
        if code_match and code_match.start() == i:
            blocks.append(Block(
                type="code",
                language=code_match.group(1) or "",
                content=code_match.group(2).strip(),
            ))
            i = code_match.end()
            continue

        table_match = TABLE_RE.match(source, i)
        if table_match:
            blocks.append(_parse_table(table_match.group()))
            i = table_match.end()
            continue

        heading_match = HEADING_RE.match(source, i)
        if heading_match and heading_match.start() == i:
            level = len(heading_match.group(1))
            text = _parse_inline(heading_match.group(2).strip())
            blocks.append(Block(type="heading", level=level, content=text))
            i = heading_match.end()
            continue

        list_match = LIST_RE.match(source, i)
        if list_match and list_match.start() == i:
            list_end = _find_list_end(source, i)
            raw = source[i:list_end]
            items = [line.strip().lstrip("-* ").strip() for line in raw.split("\n") if line.strip()]
            blocks.append(Block(type="list", items=[_parse_inline(it) for it in items]))
            i = list_end
            continue

        para_end = source.find("\n\n", i)
        if para_end == -1:
            para_end = len(source)
        para = source[i:para_end].strip()
        if para:
            blocks.append(Block(type="paragraph", content=_parse_inline(para)))
        i = para_end + 2 if para_end < len(source) else len(source)

    return blocks


def _parse_shortcode(match: re.Match) -> Block:
    tag = match.group(1)
    params_str = match.group(2).strip()
    inner = match.group(3).strip()

    params: dict[str, str] = {}
    if params_str:
        for p in re.findall(r'(\w+)\s*=\s*"([^"]*)"', params_str):
            params[p[0]] = p[1]

    if tag == "note":
        return Block(type="note", meta={"type": params.get("type", "info")}, content=_parse_inline(inner))
    elif tag == "code-tabs":
        tabs = re.findall(r'```(\w+)\n(.*?)```', inner, re.DOTALL)
        return Block(
            type="code-tabs",
            items=[{"language": t[0], "code": t[1].strip()} for t in tabs],
        )
    elif tag == "diagram":
        try:
            data = json.loads(inner)
        except json.JSONDecodeError:
            data = {"type": "flow", "label": inner}
        return Block(type="diagram", meta=data)
    elif tag == "playground":
        code_match = re.search(r"```(\w*)\n(.*?)```", inner, re.DOTALL)
        return Block(
            type="playground",
            language=code_match.group(1) if code_match else "python",
            content=code_match.group(2).strip() if code_match else inner,
        )
    return Block(type="paragraph", content=inner)


def _parse_table(source: str) -> Block:
    lines = source.strip().split("\n")
    if len(lines) < 2:
        return Block(type="paragraph", content=source)
    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    rows: list[list[str]] = []
    for line in lines[2:]:
        row = [c.strip() for c in line.strip("|").split("|")]
        rows.append(row)
    return Block(type="table", meta={"headers": headers}, items=rows)


def _parse_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


def _find_list_end(source: str, start: int) -> int:
    i = start
    while i < len(source):
        nl = source.find("\n", i)
        if nl == -1:
            return len(source)
        rest = source[nl + 1:].lstrip()
        if not rest or not rest.startswith(("- ", "* ")):
            return nl + 1
        i = nl + 1
    return len(source)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text
