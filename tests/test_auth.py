from __future__ import annotations

import io
import json
import unittest

from spry import AppBuilder, CookieAuthService, ControllerBase, Request, authorize, controller, get


@controller("/secure")
class SecureController(ControllerBase):
    @get("/")
    @authorize("/login")
    def index(self):
        return {"status": "secure"}


class AuthTests(unittest.TestCase):
    def test_authorize_redirects_html_requests_without_user(self) -> None:
        builder = AppBuilder(base_path=".")
        builder.add_auth(secret_key="test-secret")
        builder.add_controller(SecureController)
        app = builder.build()

        captured: dict[str, object] = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(
            app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/secure",
                    "QUERY_STRING": "",
                    "CONTENT_LENGTH": "0",
                    "HTTP_ACCEPT": "text/html",
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "http",
                    "HTTP_HOST": "localhost",
                },
                start_response,
            )
        )

        self.assertEqual(captured["status"], "302 Found")
        self.assertEqual(captured["headers"]["Location"], "/login")
        self.assertEqual(body, b"")

    def test_authorize_allows_authenticated_request(self) -> None:
        builder = AppBuilder(base_path=".")
        auth = builder.add_auth(secret_key="test-secret")
        builder.add_controller(SecureController)
        app = builder.build()

        token = auth.issue("1", "Ada")
        response = app.handle_request(
            Request(
                "GET",
                "/secure",
                {},
                {"Cookie": f"{auth.cookie_name}={token}", "Accept": "application/json"},
                b"",
                "http",
                "localhost",
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body), {"status": "secure"})
