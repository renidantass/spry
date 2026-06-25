from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any

from spry.views.filters import FILTERS
from spry.views.html import HtmlString
from spry.views.tokenizer import _lookup_value, eval_expression


class Node:
    def render(self, context: dict[str, Any]) -> str:
        raise NotImplementedError


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
        items_list = list(items) if hasattr(items, "__iter__") and not isinstance(items, (str, bytes, Mapping)) else []
        if not items_list:
            return "".join(n.render(context) for n in self.else_body)
        return "".join(
            "".join(n.render({**context, self.item_name: item}) for n in self.body)
            for item in items_list
        )


class IfNode(Node):
    def __init__(self, condition: str, body: list[Node], elifs: list[tuple[str, list[Node]]], else_body: list[Node]) -> None:
        self.condition = condition
        self.body = body
        self.elifs = elifs
        self.else_body = else_body

    def render(self, context: dict[str, Any]) -> str:
        if eval_expression(self.condition, context):
            return "".join(n.render(context) for n in self.body)
        for cond, body in self.elifs:
            if eval_expression(cond, context):
                return "".join(n.render(context) for n in body)
        return "".join(n.render(context) for n in self.else_body)


class IncludeNode(Node):
    def __init__(self, template_name: str, pass_context: bool, engine: Any) -> None:
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
        result = template
        for n in self.body:
            rendered = n.render(context)
            result = result.replace("{}", rendered, 1) if isinstance(n, VarNode) else result
        return result
