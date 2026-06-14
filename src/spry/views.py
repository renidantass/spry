from __future__ import annotations

import re
from abc import ABC, abstractmethod
from html import escape
from pathlib import Path
from typing import Any, Callable, Mapping


class HtmlString(str):
    def __html__(self) -> str:
        return str(self)


FILTERS: dict[str, Callable[..., str]] = {}


def register_filter(name: str, func: Callable[..., str]) -> None:
    FILTERS[name] = func


def _init_filters() -> None:
    if FILTERS:
        return
    register_filter("upper", lambda v, *a: str(v).upper())
    register_filter("lower", lambda v, *a: str(v).lower())
    register_filter("capitalize", lambda v, *a: str(v).capitalize())
    register_filter("title", lambda v, *a: str(v).title())
    register_filter("trim", lambda v, *a: str(v).strip())
    register_filter("length", lambda v, *a: str(len(v)) if v is not None else "0")
    register_filter("reverse", lambda v, *a: str(v)[::-1])
    register_filter("safe", lambda v, *a: HtmlString(str(v)))
    register_filter("default", lambda v, d, *a: v if v is not None and v != "" else d)


_init_filters()


T_TEXT = "TEXT"
T_VAR = "VAR"
T_BLOCK = "BLOCK"
T_COMMENT = "COMMENT"

_token_pattern = re.compile(
    r"\{\{\s*([\s\S]*?)\s*\}\}"  # {{ var|filter }}
    r"|\{%\s*([\s\S]*?)\s*%\}"  # {% statement %}
    r"|\{#\s*([\s\S]*?)\s*#\}"  # {# comment #}
)


def tokenize(source: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    for match in _token_pattern.finditer(source):
        start = match.start()
        if start > pos:
            tokens.append((T_TEXT, source[pos:start]))
        var_content = match.group(1)
        block_content = match.group(2)
        comment_content = match.group(3)
        if var_content is not None:
            tokens.append((T_VAR, var_content.strip()))
        elif block_content is not None:
            tokens.append((T_BLOCK, block_content.strip()))
        elif comment_content is not None:
            tokens.append((T_COMMENT, comment_content))
        pos = match.end()
    if pos < len(source):
        tokens.append((T_TEXT, source[pos:]))
    return tokens


class Node(ABC):
    @abstractmethod
    def render(self, context: dict[str, Any]) -> str:
        ...


class TextNode(Node):
    def __init__(self, text: str) -> None:
        self.text = text

    def render(self, context: dict[str, Any]) -> str:
        return self.text


class VarNode(Node):
    def __init__(self, expression: str) -> None:
        parts = [p.strip() for p in expression.split("|")]
        self.variable = parts[0]
        self.filters: list[tuple[str, list[str]]] = []
        for f in parts[1:]:
            f_parts = [p.strip() for p in f.split("(")]
            name = f_parts[0]
            args: list[str] = []
            if len(f_parts) > 1:
                raw = f_parts[1].rstrip(")")
                args = [a.strip().strip('"').strip("'") for a in raw.split(",") if a.strip()]
            self.filters.append((name, args))

    def render(self, context: dict[str, Any]) -> str:
        value = _lookup_value(context, self.variable)
        for name, args in self.filters:
            func = FILTERS.get(name)
            if func is not None:
                value = func(value, *args)
            else:
                raise RuntimeError(f"Unknown filter: {name}")
        if value is None:
            return ""
        if isinstance(value, HtmlString):
            return str(value)
        return escape(str(value))


class ForNode(Node):
    def __init__(self, item_name: str, iterable_expr: str, body: list[Node], else_body: list[Node]) -> None:
        self.item_name = item_name
        self.iterable_expr = iterable_expr
        self.body = body
        self.else_body = else_body

    def render(self, context: dict[str, Any]) -> str:
        items = _lookup_value(context, self.iterable_expr)
        if items is None:
            items = []
        items_list = list(items) if hasattr(items, "__iter__") else []
        if not items_list:
            return "".join(n.render(context) for n in self.else_body)
        results: list[str] = []
        for item in items_list:
            ctx = dict(context)
            ctx[self.item_name] = item
            results.append("".join(n.render(ctx) for n in self.body))
        return "".join(results)


class IfNode(Node):
    def __init__(self, condition: str, body: list[Node], elifs: list[tuple[str, list[Node]]], else_body: list[Node]) -> None:
        self.condition = condition
        self.body = body
        self.elifs = elifs
        self.else_body = else_body

    def render(self, context: dict[str, Any]) -> str:
        if _eval_expression(self.condition, context):
            return "".join(n.render(context) for n in self.body)
        for cond, body in self.elifs:
            if _eval_expression(cond, context):
                return "".join(n.render(context) for n in body)
        return "".join(n.render(context) for n in self.else_body)


class IncludeNode(Node):
    def __init__(self, template_name: str, pass_context: bool, engine: SpryTemplateEngine) -> None:
        self.template_name = template_name
        self.pass_context = pass_context
        self.engine = engine

    def render(self, context: dict[str, Any]) -> str:
        ctx = context if self.pass_context else {}
        return self.engine._render_template(self.template_name, ctx)


class TransNode(Node):
    def __init__(self, message: str) -> None:
        self.message = message

    def render(self, context: dict[str, Any]) -> str:
        i18n = context.get("_i18n")
        if i18n and hasattr(i18n, "translate"):
            return i18n.translate(self.message)
        return self.message


class BlockTranslateNode(Node):
    def __init__(self, body: list[Node], singular: str, plural: str | None, count_expr: str | None) -> None:
        self.body = body
        self.singular = singular
        self.plural = plural
        self.count_expr = count_expr

    def render(self, context: dict[str, Any]) -> str:
        i18n = context.get("_i18n")
        if self.count_expr is not None and i18n and hasattr(i18n, "ngettext"):
            count = _lookup_value(context, self.count_expr)
            count = int(count) if count is not None else 1
            template = i18n.ngettext(self.singular, self.plural or self.singular, count)
        elif i18n and hasattr(i18n, "translate"):
            template = i18n.translate(self.singular)
        else:
            template = self.singular
        ctx = dict(context)
        result = template
        for n in self.body:
            rendered = n.render(ctx)
            result = result.replace("{}", rendered, 1) if isinstance(n, VarNode) else result
        return result


def _eval_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return bool(value)
    if hasattr(value, "__len__"):
        return len(value) > 0
    return bool(value)


def _eval_expression(expr: str, context: dict[str, Any]) -> Any:
    expr = expr.strip()
    if expr.startswith("not "):
        return not _eval_truthy(_lookup_value(context, expr[4:].strip()))
    if "==" in expr:
        left, right = expr.split("==", 1)
        left = _lookup_value(context, left.strip())
        right = _resolve_literal(right.strip(), context)
        return left == right
    if "!=" in expr:
        left, right = expr.split("!=", 1)
        left = _lookup_value(context, left.strip())
        right = _resolve_literal(right.strip(), context)
        return left != right
    if ">" in expr:
        left, right = expr.split(">", 1)
        left = _lookup_value(context, left.strip())
        right = _resolve_literal(right.strip(), context)
        try:
            return float(left) > float(right)
        except (TypeError, ValueError):
            return False
    if "<" in expr:
        left, right = expr.split("<", 1)
        left = _lookup_value(context, left.strip())
        right = _resolve_literal(right.strip(), context)
        try:
            return float(left) < float(right)
        except (TypeError, ValueError):
            return False
    if ">=" in expr:
        left, right = expr.split(">=", 1)
        left = _lookup_value(context, left.strip())
        right = _resolve_literal(right.strip(), context)
        try:
            return float(left) >= float(right)
        except (TypeError, ValueError):
            return False
    if "<=" in expr:
        left, right = expr.split("<=", 1)
        left = _lookup_value(context, left.strip())
        right = _resolve_literal(right.strip(), context)
        try:
            return float(left) <= float(right)
        except (TypeError, ValueError):
            return False
    return _eval_truthy(_lookup_value(context, expr))


def _resolve_literal(token: str, context: dict[str, Any]) -> Any:
    token = token.strip()
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    if token in {"True", "true"}:
        return True
    if token in {"False", "false"}:
        return False
    if token in {"None", "none", "null"}:
        return None
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        pass
    return _lookup_value(context, token)


def parse(tokens: list[tuple[str, str]], engine: SpryTemplateEngine) -> list[Node]:
    nodes: list[Node] = []
    i = 0
    while i < len(tokens):
        tok_type, content = tokens[i]
        if tok_type == T_TEXT:
            nodes.append(TextNode(content))
            i += 1
        elif tok_type == T_VAR:
            nodes.append(VarNode(content))
            i += 1
        elif tok_type == T_COMMENT:
            i += 1
        elif tok_type == T_BLOCK:
            block = content
            if block.startswith("for ") and " in " in block:
                i = _parse_nested_block(block, tokens, i, nodes, engine)
            elif block.startswith("if "):
                i = _parse_nested_block(block, tokens, i, nodes, engine)
            elif block.startswith("trans "):
                message = block[5:].strip().strip('"').strip("'")
                nodes.append(TransNode(message))
                i += 1
            elif block == "blocktranslate" or block.startswith("blocktranslate "):
                rest = block[13:].strip() if block.startswith("blocktranslate ") else ""
                count_expr = None
                plural = None
                if "plural " in rest or "plural" in rest:
                    parts2 = rest.split("plural", 1)
                    count_expr = parts2[0].strip().removeprefix("count ").strip() or None
                    plural = parts2[1].strip().strip('"').strip("'") if len(parts2) > 1 else None
                body_nodes, end = _parse_block_translate(tokens, i + 1, engine)
                nodes.append(BlockTranslateNode(body_nodes, "", plural, count_expr))
                singular = ""
                for n in body_nodes:
                    if isinstance(n, TextNode):
                        singular += n.text
                nodes[-1] = BlockTranslateNode(body_nodes, singular, plural, count_expr)
                i = end
            elif block.startswith("include "):
                parts = block[8:].strip().split()
                template = parts[0].strip('"').strip("'")
                without_context = (
                    len(parts) > 1 and parts[1] == "without"
                    and len(parts) > 2 and parts[2] == "context"
                )
                nodes.append(IncludeNode(template, not without_context, engine))
                i += 1
            else:
                raise RuntimeError(f"Unknown block tag: {block}")
        else:
            i += 1
    return nodes


def _parse_block_body(
    tokens: list[tuple[str, str]], start: int, end_tag: str, else_tag: str | None, engine: SpryTemplateEngine
) -> tuple[list[Node], list[Node], int]:
    body: list[Node] = []
    else_body: list[Node] = []
    i = start
    target = body
    has_else_tag = else_tag is not None

    while i < len(tokens):
        tok_type, content = tokens[i]
        if tok_type == T_BLOCK:
            block = content
            if block.startswith("for ") or block.startswith("if "):
                i = _parse_nested_block(block, tokens, i, target, engine)
                continue
            elif block == end_tag:
                return body, else_body, i + 1
            elif has_else_tag and block == else_tag and target is body:
                target = else_body
                i += 1
                continue
        target.append(_parse_single_node(tok_type, content, engine))
        i += 1

    raise RuntimeError(f"Unclosed block: expected {end_tag}")


def _parse_nested_block(
    block: str, tokens: list[tuple[str, str]], i: int, target: list[Node], engine: SpryTemplateEngine
) -> int:
    if block.startswith("for "):
        rest = block[4:]
        item_name, _, iter_expr = rest.partition(" in ")
        item_name = item_name.strip()
        iter_expr = iter_expr.strip()
        inner_body, inner_else, end = _parse_block_body(tokens, i + 1, "endfor", "else", engine)
        target.append(ForNode(item_name, iter_expr, inner_body, inner_else))
        return end
    if block.startswith("if "):
        condition = block[3:].strip()
        inner_body, elifs, inner_else, end = _parse_if_block(tokens, i + 1, engine)
        target.append(IfNode(condition, inner_body, elifs, inner_else))
        return end
    return i + 1


def _parse_if_block(
    tokens: list[tuple[str, str]], start: int, engine: SpryTemplateEngine
) -> tuple[list[Node], list[tuple[str, list[Node]]], list[Node], int]:
    branches: list[dict[str, Any]] = [{"kind": "if", "body": []}]
    i = start

    while i < len(tokens):
        tok_type, content = tokens[i]
        if tok_type == T_BLOCK:
            block = content
            if block.startswith("for ") or block.startswith("if "):
                i = _parse_nested_block(block, tokens, i, branches[-1]["body"], engine)
                continue
            elif block.startswith("elif "):
                branches.append({"kind": "elif", "cond": block[4:].strip(), "body": []})
                i += 1
                continue
            elif block == "else":
                branches.append({"kind": "else", "body": []})
                i += 1
                continue
            elif block == "endif":
                break
        branches[-1]["body"].append(_parse_single_node(tok_type, content, engine))
        i += 1

    body: list[Node] = []
    elifs: list[tuple[str, list[Node]]] = []
    else_body: list[Node] = []

    for branch in branches:
        if branch["kind"] == "if":
            body = branch["body"]
        elif branch["kind"] == "elif":
            elifs.append((branch["cond"], branch["body"]))
        elif branch["kind"] == "else":
            else_body = branch["body"]

    return body, elifs, else_body, i + 1


def _parse_block_translate(
    tokens: list[tuple[str, str]], start: int, engine: SpryTemplateEngine
) -> tuple[list[Node], int]:
    body: list[Node] = []
    i = start
    while i < len(tokens):
        tok_type, content = tokens[i]
        if tok_type == T_BLOCK and content == "endblocktranslate":
            return body, i + 1
        body.append(_parse_single_node(tok_type, content, engine))
        i += 1
    raise RuntimeError("Unclosed block: expected endblocktranslate")


def _parse_single_node(tok_type: str, content: str, engine: SpryTemplateEngine) -> Node:
    if tok_type == T_TEXT:
        return TextNode(content)
    if tok_type == T_VAR:
        return VarNode(content)
    if tok_type == T_COMMENT:
        return TextNode("")
    raise RuntimeError(f"Unexpected block token: {content}")


class TemplateEngine(ABC):
    @abstractmethod
    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def render_string(self, source: str, context: dict[str, Any]) -> str:
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class SpryTemplateEngine(TemplateEngine):
    def __init__(self, views_dir: Path) -> None:
        self.views_dir = views_dir
        self._cache: dict[str, list[Node]] = {}

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        if template_name not in self._cache:
            source = self._load_template(template_name)
            tokens = tokenize(source)
            ast = parse(tokens, self)
            self._cache[template_name] = ast
        ast = self._cache[template_name]
        return "".join(n.render(context) for n in ast)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        tokens = tokenize(source)
        ast = parse(tokens, self)
        return "".join(n.render(context) for n in ast)

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        return self.render_template(template_name, context)

    def _load_template(self, template_name: str) -> str:
        normalized = template_name.replace("\\", "/").lstrip("/")
        file_name = normalized if normalized.endswith(".html") else f"{normalized}.html"
        file_path = (self.views_dir / file_name).resolve()
        if self.views_dir.resolve() not in file_path.parents and file_path != self.views_dir.resolve():
            raise FileNotFoundError(f"View '{template_name}' is outside the views directory")
        return file_path.read_text(encoding="utf-8")


class Jinja2TemplateEngine(TemplateEngine):
    def __init__(self, views_dir: Path) -> None:
        import jinja2

        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(views_dir)),
            autoescape=jinja2.select_autoescape(),
            undefined=jinja2.DebugUndefined,
        )

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        template = self._env.get_template(template_name)
        return template.render(**context)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        return self._env.from_string(source).render(**context)

    @property
    def name(self) -> str:
        return "Jinja2"


class ViewRenderer:
    def __init__(
        self,
        base_path: str | Path,
        *,
        views_dir: str = "views",
        default_layout: str | None = "shared/_layout",
        engine: TemplateEngine | str = "spry",
        i18n_service: Any = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.views_dir_path = self.base_path / views_dir
        self.default_layout = default_layout
        self._engine = self._resolve_engine(engine)
        self._i18n = i18n_service

    def _resolve_engine(self, engine: TemplateEngine | str) -> TemplateEngine:
        if isinstance(engine, TemplateEngine):
            return engine
        if engine == "jinja2":
            return Jinja2TemplateEngine(self.views_dir_path)
        return SpryTemplateEngine(self.views_dir_path)

    @property
    def engine(self) -> TemplateEngine:
        return self._engine

    def _with_i18n(self, context: dict[str, Any]) -> dict[str, Any]:
        if self._i18n is not None and "_i18n" not in context:
            context = dict(context)
            context["_i18n"] = self._i18n
        return context

    def render(
        self,
        view_name: str,
        model: Mapping[str, Any] | None = None,
        *,
        layout: str | None = None,
    ) -> str:
        context = self._with_i18n(dict(model or {}))
        content = self._engine.render_template(view_name, context)
        layout_name = self.default_layout if layout is None else layout
        if not layout_name:
            return content

        layout_context = self._with_i18n(dict(context))
        layout_context.setdefault("body", HtmlString(content))
        layout_context.setdefault("page_title", context.get("page_title", "Spry"))
        return self._engine.render_template(layout_name, layout_context)

    def render_partial(self, view_name: str, model: Mapping[str, Any] | None = None) -> HtmlString:
        context = self._with_i18n(dict(model or {}))
        return HtmlString(self._engine.render_template(view_name, context))


def _lookup_value(context: dict[str, Any], token: str) -> Any:
    current: Any = context
    for part in token.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        current = getattr(current, part, None)
    return current
