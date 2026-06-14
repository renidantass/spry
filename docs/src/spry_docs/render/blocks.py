from spry_docs.components import CodeBlock, Note, Tabs, Table, Diagram, Playground
from spry_docs.render.parser import Block


def render_block(block: Block) -> str:
    if block.type == "heading":
        tag = f"h{block.level}"
        anchor = _slugify_text(block.content)
        return f'<{tag} id="{anchor}">{block.content}</{tag}>'

    if block.type == "paragraph":
        return f"<p>{block.content}</p>"

    if block.type == "code":
        return CodeBlock(block.content, block.language).render()

    if block.type == "note":
        return Note(block.content, block.meta.get("type", "info")).render()

    if block.type == "code-tabs":
        return Tabs(block.items).render()

    if block.type == "table":
        return Table(block.meta.get("headers", []), block.items).render()

    if block.type == "list":
        items = "".join(f"<li>{item}</li>" for item in block.items)
        return f"<ul>{items}</ul>"

    if block.type == "diagram":
        return Diagram(block.meta).render()

    if block.type == "playground":
        return Playground(block.content, block.language).render()

    return ""


def _slugify_text(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text
