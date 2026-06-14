from __future__ import annotations

import re
from typing import Any, Callable

T_TEXT = "TEXT"
T_VAR = "VAR"
T_BLOCK = "BLOCK"
T_COMMENT = "COMMENT"

_token_pattern = re.compile(
    r"\{\{\s*([\s\S]*?)\s*\}\}"
    r"|\{%\s*([\s\S]*?)\s*%\}"
    r"|\{#\s*([\s\S]*?)\s*#\}"
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


def _lookup_value(context: dict[str, Any], token: str) -> Any:
    current: Any = context
    for part in token.split("."):
        if isinstance(current, dict):
            current = current.get(part)
            continue
        current = getattr(current, part, None)
    return current


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


def eval_expression(expr: str, context: dict[str, Any]) -> Any:
    expr = expr.strip()
    if expr.startswith("not "):
        return not _eval_truthy(_lookup_value(context, expr[4:].strip()))
    if "==" in expr:
        left, right = expr.split("==", 1)
        return _lookup_value(context, left.strip()) == _resolve_literal(right.strip(), context)
    if "!=" in expr:
        left, right = expr.split("!=", 1)
        return _lookup_value(context, left.strip()) != _resolve_literal(right.strip(), context)
    if ">=" in expr:
        left, right = expr.split(">=", 1)
        try:
            return float(_lookup_value(context, left.strip())) >= float(_resolve_literal(right.strip(), context))
        except (TypeError, ValueError):
            return False
    if "<=" in expr:
        left, right = expr.split("<=", 1)
        try:
            return float(_lookup_value(context, left.strip())) <= float(_resolve_literal(right.strip(), context))
        except (TypeError, ValueError):
            return False
    if ">" in expr:
        left, right = expr.split(">", 1)
        try:
            return float(_lookup_value(context, left.strip())) > float(_resolve_literal(right.strip(), context))
        except (TypeError, ValueError):
            return False
    if "<" in expr:
        left, right = expr.split("<", 1)
        try:
            return float(_lookup_value(context, left.strip())) < float(_resolve_literal(right.strip(), context))
        except (TypeError, ValueError):
            return False
    return _eval_truthy(_lookup_value(context, expr))
