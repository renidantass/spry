from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from spry.views import SpryTemplateEngine, tokenize, parse, HtmlString


class TokenizerTests(unittest.TestCase):
    def test_tokenize_text_only(self):
        tokens = tokenize("Hello World")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0][0], "TEXT")

    def test_tokenize_variable(self):
        tokens = tokenize("Hello {{ name }}!")
        types = [t for t, _ in tokens]
        self.assertIn("VAR", types)

    def test_tokenize_block(self):
        tokens = tokenize("{% if x %}y{% endif %}")
        types = [t for t, _ in tokens]
        self.assertIn("BLOCK", types)

    def test_tokenize_comment(self):
        tokens = tokenize("before{# comment #}after")
        types = [t for t, _ in tokens]
        self.assertIn("TEXT", types)
        self.assertIn("COMMENT", types)

    def test_tokenize_all(self):
        source = "a{{ b }}c{% d %}e{# f #}g"
        tokens = tokenize(source)
        types = [t for t, _ in tokens]
        self.assertIn("TEXT", types)
        self.assertIn("VAR", types)
        self.assertIn("BLOCK", types)

    def test_nested_template(self):
        source = "{% if show %}{% for x in items %}{{ x }}{% endfor %}{% endif %}"
        tokens = tokenize(source)
        self.assertGreater(len(tokens), 0)


class SpryEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.views_dir = self.temp_dir / "views"
        self.views_dir.mkdir()
        self.engine = SpryTemplateEngine(self.views_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write(self, name: str, content: str):
        (self.views_dir / name).write_text(content)

    def test_render_variable(self):
        result = self.engine.render_string("{{ name }}", {"name": "World"})
        self.assertEqual(result, "World")

    def test_render_escape(self):
        result = self.engine.render_string("{{ name }}", {"name": "<script>"})
        self.assertIn("&lt;", result)

    def test_render_safe(self):
        result = self.engine.render_string("{{ content|safe }}", {"content": "<b>bold</b>"})
        self.assertEqual(result, "<b>bold</b>")

    def test_render_html_string(self):
        result = self.engine.render_string("{{ content }}", {"content": HtmlString("<p>safe</p>")})
        self.assertEqual(result, "<p>safe</p>")

    def test_for_loop(self):
        result = self.engine.render_string(
            "{% for item in items %}{{ item }} {% endfor %}",
            {"items": ["a", "b", "c"]},
        )
        self.assertEqual(result.strip(), "a b c")

    def test_for_loop_empty(self):
        result = self.engine.render_string(
            "{% for item in items %}{{ item }}{% else %}empty{% endfor %}",
            {"items": []},
        )
        self.assertEqual(result, "empty")

    def test_if_condition(self):
        result = self.engine.render_string(
            "{% if show %}yes{% else %}no{% endif %}",
            {"show": True},
        )
        self.assertEqual(result, "yes")

    def test_if_elif(self):
        result = self.engine.render_string(
            "{% if x == 1 %}one{% elif x == 2 %}two{% else %}other{% endif %}",
            {"x": 2},
        )
        self.assertEqual(result, "two")

    def test_if_not(self):
        result = self.engine.render_string(
            "{% if not done %}pending{% endif %}",
            {"done": False},
        )
        self.assertEqual(result, "pending")

    def test_nested_for_in_if(self):
        result = self.engine.render_string(
            "{% if items %}{% for i in items %}{{ i }}{% endfor %}{% endif %}",
            {"items": ["x", "y"]},
        )
        self.assertEqual(result, "xy")

    def test_nested_if_in_for(self):
        result = self.engine.render_string(
            "{% for i in items %}{% if i == 1 %}one{% else %}{{ i }}{% endif %}{% endfor %}",
            {"items": [1, 2, 3]},
        )
        self.assertEqual(result, "one23")

    def test_include(self):
        self._write("child.html", "|{{ msg }}|")
        result = self.engine.render_template("child", {"msg": "inc"})
        self.assertEqual(result, "|inc|")

    def test_include_from_template(self):
        self._write("parent.html", "A {% include child %} B")
        self._write("child.html", "{{ val }}")
        result = self.engine.render_template("parent", {"val": "x"})
        self.assertEqual(result, "A x B")

    def test_filter_upper(self):
        result = self.engine.render_string("{{ name|upper }}", {"name": "hello"})
        self.assertEqual(result, "HELLO")

    def test_filter_default(self):
        result = self.engine.render_string("{{ missing|default('fallback') }}", {})
        self.assertEqual(result, "fallback")

    def test_filter_length(self):
        result = self.engine.render_string("{{ items|length }}", {"items": [1, 2, 3]})
        self.assertEqual(result, "3")

    def test_template_caching(self):
        self._write("cache_test.html", "{{ val }}")
        r1 = self.engine.render_template("cache_test", {"val": "first"})
        r2 = self.engine.render_template("cache_test", {"val": "second"})
        self.assertEqual(r1, "first")
        self.assertEqual(r2, "second")

    def test_missing_variable_returns_empty(self):
        result = self.engine.render_string("{{ missing }}", {})
        self.assertEqual(result, "")

    def test_dot_notation_dict(self):
        result = self.engine.render_string("{{ a.b }}", {"a": {"b": "nested"}})
        self.assertEqual(result, "nested")

    def test_dot_notation_object(self):
        class Obj:
            b = "attr_val"
        result = self.engine.render_string("{{ a.b }}", {"a": Obj()})
        self.assertEqual(result, "attr_val")

    def test_directory_traversal_protection(self):
        with self.assertRaises(FileNotFoundError):
            self.engine.render_template("../outside", {})
