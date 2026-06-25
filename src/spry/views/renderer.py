from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from spry.views.engine import Jinja2TemplateEngine, SpryTemplateEngine, TemplateEngine
from spry.views.filters import _init_filters
from spry.views.html import HtmlString

_init_filters()


class ViewRenderer:
    def __init__(
        self,
        base_path: str | Path,
        *,
        views_dir: str = "views",
        default_layout: str | None = "shared/_layout",
        engine: TemplateEngine | str = "spry",
        i18n_service: Any = None,
        debug: bool = False,
    ) -> None:
        self.base_path = Path(base_path)
        self.views_dir_path = self.base_path / views_dir
        self.default_layout = default_layout
        self._engine = self._resolve_engine(engine, debug=debug)
        self._i18n = i18n_service

    def _resolve_engine(self, engine: TemplateEngine | str, *, debug: bool) -> TemplateEngine:
        if isinstance(engine, TemplateEngine):
            return engine
        if engine == "jinja2":
            return Jinja2TemplateEngine(self.views_dir_path, debug=debug)
        return SpryTemplateEngine(self.views_dir_path)

    @property
    def engine(self) -> TemplateEngine:
        return self._engine

    def _with_i18n(self, context: dict[str, Any]) -> dict[str, Any]:
        if self._i18n is not None and "_i18n" not in context:
            context = {**context, "_i18n": self._i18n}
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
