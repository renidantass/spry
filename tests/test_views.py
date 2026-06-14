from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from spry.controllers import Controller
from spry.views import HtmlString, ViewRenderer


class DummyController(Controller):
    pass


class ViewRendererTests(unittest.TestCase):
    def test_render_uses_layout_and_escapes_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "views" / "shared").mkdir(parents=True)
            (base / "views" / "home").mkdir(parents=True)
            (base / "views" / "shared" / "_layout.html").write_text("<html><body>{{ body }}</body></html>", encoding="utf-8")
            (base / "views" / "home" / "index.html").write_text("<h1>{{ title }}</h1>{{ content }}", encoding="utf-8")

            renderer = ViewRenderer(base)
            controller = DummyController(renderer)
            response = controller.view("home/index", {"title": "<unsafe>", "content": HtmlString("<p>safe</p>")})

            markup = response.body.decode("utf-8")
            self.assertIn("&lt;unsafe&gt;", markup)
            self.assertIn("<p>safe</p>", markup)
            self.assertIn("<html><body>", markup)

    def test_partial_view_returns_html_string(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "views" / "home").mkdir(parents=True)
            (base / "views" / "home" / "card.html").write_text("<div>{{ title }}</div>", encoding="utf-8")

            renderer = ViewRenderer(base, default_layout=None)
            controller = DummyController(renderer)
            content = controller.partial_view("home/card", {"title": "Hello"})

            self.assertIsInstance(content, HtmlString)
            self.assertEqual(str(content), "<div>Hello</div>")
