from __future__ import annotations

from typing import Any

from spry.views.nodes import (
    BlockTranslateNode,
    ForNode,
    IfNode,
    IncludeNode,
    Node,
    TextNode,
    TransNode,
    VarNode,
)
from spry.views.tokenizer import T_BLOCK, T_COMMENT, T_TEXT, T_VAR


def parse(tokens: list[tuple[str, str]], engine: Any) -> list[Node]:
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
            i = _parse_block(content, tokens, i, nodes, engine)
        else:
            i += 1
    return nodes


def _parse_single_node(tok_type: str, content: str, engine: Any) -> Node:
    if tok_type == T_TEXT:
        return TextNode(content)
    if tok_type == T_VAR:
        return VarNode(content)
    if tok_type == T_COMMENT:
        return TextNode("")
    raise RuntimeError(f"Unexpected block token: {content}")


def _parse_block(block: str, tokens: list[tuple[str, str]], i: int, target: list[Node], engine: Any) -> int:
    if block.startswith("for ") and " in " in block:
        rest = block[len("for "):]
        item_name, _, iter_expr = rest.partition(" in ")
        item_name = item_name.strip()
        iter_expr = iter_expr.strip()
        body, else_body, end = _parse_block_body(tokens, i + 1, "endfor", "else", engine)
        target.append(ForNode(item_name, iter_expr, body, else_body))
        return end

    if block.startswith("if "):
        condition = block[len("if "):].strip()
        body, elifs, else_body, end = _parse_if_block(tokens, i + 1, engine)
        target.append(IfNode(condition, body, elifs, else_body))
        return end

    if block.startswith("trans "):
        message = block[len("trans "):].strip().strip('"').strip("'")
        target.append(TransNode(message))
        return i + 1

    if block == "blocktranslate" or block.startswith("blocktranslate "):
        rest = block[len("blocktranslate"):].strip() if block.startswith("blocktranslate ") else ""
        count_expr: str | None = None
        plural: str | None = None
        if "plural" in rest:
            head, _, tail = rest.partition("plural")
            count_expr = head.strip().removeprefix("count ").strip() or None
            plural = tail.strip().strip('"').strip("'") or None
        body_nodes, end = _parse_block_translate(tokens, i + 1, engine)
        singular = "".join(n.text for n in body_nodes if isinstance(n, TextNode))
        target.append(BlockTranslateNode(body_nodes, singular, plural, count_expr))
        return end

    if block.startswith("include "):
        parts = block[len("include "):].strip().split()
        template = parts[0].strip('"').strip("'")
        without_context = (
            len(parts) > 2 and parts[1] == "without" and parts[2] == "context"
        )
        target.append(IncludeNode(template, not without_context, engine))
        return i + 1

    raise RuntimeError(f"Unknown block tag: {block}")


def _parse_block_body(
    tokens: list[tuple[str, str]], start: int, end_tag: str, else_tag: str | None, engine: Any
) -> tuple[list[Node], list[Node], int]:
    body: list[Node] = []
    else_body: list[Node] = []
    i = start
    target = body
    has_else = else_tag is not None

    while i < len(tokens):
        tok_type, content = tokens[i]
        if tok_type == T_BLOCK:
            block = content
            if block.startswith("for ") or block.startswith("if ") or block == "blocktranslate" or block.startswith("blocktranslate ") or block.startswith("include ") or block.startswith("trans "):
                i = _parse_block(block, tokens, i, target, engine)
                continue
            if block == end_tag:
                return body, else_body, i + 1
            if has_else and block == else_tag and target is body:
                target = else_body
                i += 1
                continue
        target.append(_parse_single_node(tok_type, content, engine))
        i += 1

    raise RuntimeError(f"Unclosed block: expected {end_tag}")


def _parse_if_block(
    tokens: list[tuple[str, str]], start: int, engine: Any
) -> tuple[list[Node], list[tuple[str, list[Node]]], list[Node], int]:
    branches: list[dict[str, Any]] = [{"kind": "if", "body": []}]
    i = start

    while i < len(tokens):
        tok_type, content = tokens[i]
        if tok_type == T_BLOCK:
            block = content
            if block.startswith("for ") or block.startswith("if ") or block == "blocktranslate" or block.startswith("blocktranslate ") or block.startswith("include ") or block.startswith("trans "):
                i = _parse_block(block, tokens, i, branches[-1]["body"], engine)
                continue
            if block.startswith("elif "):
                branches.append({"kind": "elif", "cond": block[len("elif "):].strip(), "body": []})
                i += 1
                continue
            if block == "else":
                branches.append({"kind": "else", "body": []})
                i += 1
                continue
            if block == "endif":
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
    tokens: list[tuple[str, str]], start: int, engine: Any
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
