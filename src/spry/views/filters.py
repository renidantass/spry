from __future__ import annotations

import re
from typing import Any, Mapping

FILTERS: dict[str, "FilterFn"] = {}

FilterFn = Any


def register_filter(name: str, func: Any) -> None:
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
    register_filter("safe", lambda v, *a: _html_safe(str(v)))
    register_filter("default", lambda v, d, *a: v if v is not None and v != "" else d)


def _html_safe(value: str) -> "HtmlString":
    from spry.views.html import HtmlString
    return HtmlString(value)
