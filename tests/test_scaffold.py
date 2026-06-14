from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from spry.scaffold import scaffold_project


class ScaffoldTests(unittest.TestCase):
    def test_can_scaffold_mvc_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "backoffice"
            scaffold_project("backoffice", destination, template_name="mvc")

            self.assertTrue((destination / "static" / "site.css").exists())
            self.assertTrue((destination / "views" / "shared" / "_layout.html").exists())
            self.assertTrue((destination / "views" / "home" / "index.html").exists())
            self.assertIn("inspirada no `shadcn`", (destination / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
