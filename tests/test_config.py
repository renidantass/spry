from __future__ import annotations

import json
import tempfile
import unittest
import os
from pathlib import Path
from spry.config import Configuration


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self._old_environ = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_environ)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_empty(self):
        cfg = Configuration.load(self.temp_dir, file_name="missing.json")
        self.assertEqual(cfg.as_dict(), {})

    def test_load_json(self):
        cfg = Configuration.load(self.temp_dir, file_name="appsettings.test_notfound.json")
        (self.temp_dir / "appsettings.test.json").write_text(
            json.dumps({"server": {"host": "0.0.0.0", "port": 8080}})
        )
        cfg = Configuration.load(self.temp_dir, file_name="appsettings.test.json")
        self.assertEqual(cfg.get("server", "host"), "0.0.0.0")
        self.assertEqual(cfg.get("server", "port"), 8080)

    def test_get_case_insensitive(self):
        (self.temp_dir / "appsettings.json").write_text(
            json.dumps({"Server": {"Host": "127.0.0.1"}})
        )
        cfg = Configuration.load(self.temp_dir)
        self.assertEqual(cfg.get("server", "host"), "127.0.0.1")

    def test_section(self):
        (self.temp_dir / "appsettings.json").write_text(
            json.dumps({"database": {"url": "test.db"}})
        )
        cfg = Configuration.load(self.temp_dir)
        section = cfg.section("database")
        self.assertEqual(section.get("url"), "test.db")

    def test_env_override(self):
        import os
        os.environ["APP__DATABASE__URL"] = "env.db"
        (self.temp_dir / "appsettings.json").write_text(
            json.dumps({"database": {"url": "file.db"}})
        )
        cfg = Configuration.load(self.temp_dir)
        self.assertEqual(cfg.get("database", "url"), "env.db")
        del os.environ["APP__DATABASE__URL"]

    def test_env_file(self):
        (self.temp_dir / ".env").write_text(
            "APP_ENV=test\nAPP__SERVER__PORT=9000\n"
        )
        cfg = Configuration.load(self.temp_dir)
        self.assertEqual(os.environ.get("APP_ENV"), "test")

    def test_environment_specific_json(self):
        cfg_file = "appsettings.test_env.json"
        prod_file = "appsettings.test_env.Production.json"
        (self.temp_dir / cfg_file).write_text(
            json.dumps({"server": {"host": "127.0.0.1", "port": 8000}})
        )
        (self.temp_dir / prod_file).write_text(
            json.dumps({"server": {"port": 80}})
        )
        os.environ["APP_ENVIRONMENT"] = "Production"
        os.environ.pop("APP__SERVER__PORT", None)
        cfg = Configuration.load(self.temp_dir, file_name=cfg_file)
        self.assertEqual(cfg.get("server", "host"), "127.0.0.1")
        self.assertEqual(cfg.get("server", "port"), 80)
        del os.environ["APP_ENVIRONMENT"]
