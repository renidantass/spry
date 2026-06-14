from __future__ import annotations

import importlib
import io
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class AutoDiscoveryTests(unittest.TestCase):
    def test_build_discovers_controllers_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_dir = root / "autosite"
            package_dir.mkdir()

            (package_dir / "__init__.py").write_text("", encoding="utf-8")
            (package_dir / "controllers.py").write_text(
                textwrap.dedent(
                    '''
                    from spry import ControllerBase, controller, get


                    @controller("/ping")
                    class PingController(ControllerBase):
                        @get("/")
                        def index(self):
                            return {"status": "ok"}
                    '''
                ),
                encoding="utf-8",
            )
            (package_dir / "app.py").write_text(
                textwrap.dedent(
                    '''
                    from spry import AppBuilder


                    def create_app():
                        builder = AppBuilder()
                        builder.discover_controllers("autosite")
                        return builder.build()
                    '''
                ),
                encoding="utf-8",
            )

            sys.path.insert(0, str(root))
            try:
                module = importlib.import_module("autosite.app")
                app = module.create_app()

                captured: dict[str, object] = {}

                def start_response(status, headers):
                    captured["status"] = status
                    captured["headers"] = dict(headers)

                body = b"".join(
                    app(
                        {
                            "REQUEST_METHOD": "GET",
                            "PATH_INFO": "/ping",
                            "QUERY_STRING": "",
                            "CONTENT_LENGTH": "0",
                            "wsgi.input": io.BytesIO(b""),
                            "wsgi.url_scheme": "http",
                            "HTTP_HOST": "localhost",
                        },
                        start_response,
                    )
                )

                self.assertEqual(captured["status"], "200 OK")
                self.assertEqual(json.loads(body), {"status": "ok"})
            finally:
                sys.path.remove(str(root))
                for module_name in list(sys.modules):
                    if module_name == "autosite" or module_name.startswith("autosite."):
                        sys.modules.pop(module_name, None)


if __name__ == "__main__":
    unittest.main()
