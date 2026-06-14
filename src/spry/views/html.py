from __future__ import annotations


class HtmlString(str):
    def __html__(self) -> str:
        return str(self)
