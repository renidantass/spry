from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from spry.views.parser import parse
from spry.views.tokenizer import tokenize


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
        self._cache: dict[str, list] = {}

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        ast = self._cache.get(template_name)
        if ast is None:
            ast = parse(tokenize(self._load_template(template_name)), self)
            self._cache[template_name] = ast
        return "".join(n.render(context) for n in ast)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        ast = parse(tokenize(source), self)
        return "".join(n.render(context) for n in ast)

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        return self.render_template(template_name, context)

    def _load_template(self, template_name: str) -> str:
        if "\0" in template_name:
            raise FileNotFoundError(f"Invalid view name: {template_name}")
        normalized = template_name.replace("\\", "/").lstrip("/")
        file_name = normalized if normalized.endswith(".html") else f"{normalized}.html"
        file_path = (self.views_dir / file_name).resolve()
        if self.views_dir.resolve() not in file_path.parents and file_path != self.views_dir.resolve():
            raise FileNotFoundError(f"View '{template_name}' is outside the views directory")
        return file_path.read_text(encoding="utf-8")


class Jinja2TemplateEngine(TemplateEngine):
    def __init__(self, views_dir: Path, *, debug: bool = False) -> None:
        import jinja2

        if debug:
            undefined_cls: type = jinja2.DebugUndefined
        else:
            undefined_cls = jinja2.ChainableUndefined
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(views_dir)),
            autoescape=jinja2.select_autoescape(),
            undefined=undefined_cls,
        )

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        return self._env.get_template(template_name).render(**context)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        return self._env.from_string(source).render(**context)

    @property
    def name(self) -> str:
        return "Jinja2"
