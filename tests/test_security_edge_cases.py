from __future__ import annotations

import unittest

from spry import AppBuilder
from spry.http import Request
from spry.testing import TestClient


class MalformedJsonTests(unittest.TestCase):
    def _req(self, body: bytes) -> Request:
        return Request("POST", "/", {}, {"Content-Type": "application/json"}, body, "http", "localhost")

    def test_malformed_json_raises(self):
        with self.assertRaises(ValueError):
            self._req(b"{malformed").json()

    def test_truncated_json_raises(self):
        with self.assertRaises(ValueError):
            self._req(b'{"key": "val').json()

    def test_binary_body_raises(self):
        with self.assertRaises(ValueError):
            self._req(b"\x80\x81\x82").json()

    def test_empty_body_returns_empty(self):
        self.assertEqual(self._req(b"").json(), {})


def _get_set_cookie(resp) -> list[str]:
    headers = getattr(resp, "_extra_headers", [])
    return [v for k, v in headers if k.lower() == "set-cookie"]


class SessionCookieAttributesTests(unittest.TestCase):
    def test_session_cookie_has_http_only_and_same_site(self):
        from spry.session import SessionMiddleware, SessionStore

        builder = AppBuilder()
        builder.use(SessionMiddleware(store=SessionStore()))
        builder.map_get("/", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/")
        cookies = _get_set_cookie(resp)
        session_cookie = next((c for c in cookies if c.startswith("spry_session")), None)
        self.assertIsNotNone(session_cookie)
        self.assertIn("HttpOnly", session_cookie)
        self.assertIn("SameSite=Strict", session_cookie)
        self.assertIn("Path=/", session_cookie)

    def test_signed_session_cookie_attributes(self):
        from spry.session import SessionMiddleware

        builder = AppBuilder()
        builder.use(SessionMiddleware(secret_key="test-secret"))
        builder.map_get("/", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/")
        cookies = _get_set_cookie(resp)
        session_cookie = next((c for c in cookies if c.startswith("spry_session")), None)
        self.assertIsNotNone(session_cookie)
        self.assertIn("HttpOnly", session_cookie)
        self.assertIn("SameSite=Strict", session_cookie)

    def test_csrf_cookie_attributes(self):
        builder = AppBuilder()
        builder.add_csrf()
        builder.map_get("/", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/")
        cookies = _get_set_cookie(resp)
        csrf_cookie = next((c for c in cookies if c.startswith("spry_csrf")), None)
        self.assertIsNotNone(csrf_cookie)
        self.assertIn("HttpOnly", csrf_cookie)


class CorsEdgeCaseTests(unittest.TestCase):
    def test_origin_with_port_matches(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com:8080"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test", headers={"Origin": "https://app.com:8080"})
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "https://app.com:8080")

    def test_origin_with_port_rejected_if_not_in_list(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test", headers={"Origin": "https://app.com:8080"})
        self.assertIsNone(resp.headers.get("Access-Control-Allow-Origin"))

    def test_null_origin_rejected(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test", headers={"Origin": "null"})
        self.assertIsNone(resp.headers.get("Access-Control-Allow-Origin"))

    def test_vary_origin_header_set_for_specific_origin(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test", headers={"Origin": "https://app.com"})
        self.assertIn("Vary", resp.headers)
        self.assertIn("Origin", resp.headers["Vary"])

    def test_no_vary_for_wildcard(self):
        builder = AppBuilder()
        builder.add_cors(origins=["*"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test", headers={"Origin": "https://any.com"})
        if "Vary" in resp.headers:
            self.assertNotIn("Origin", resp.headers["Vary"])

    def test_credentials_with_wildcard_does_not_set_credential_header(self):
        builder = AppBuilder()
        builder.add_cors(origins=["*"], credentials=True)
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test", headers={"Origin": "https://app.com"})
        self.assertIsNone(resp.headers.get("Access-Control-Allow-Credentials"))

    def test_preflight_max_age_header(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"], max_age=7200)
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.request("OPTIONS", "/test", headers={"Origin": "https://app.com"})
        self.assertEqual(resp.headers.get("Access-Control-Max-Age"), "7200")


class CsrfEdgeCaseTests(unittest.TestCase):
    def test_missing_cookie_on_post_rejected(self):
        builder = AppBuilder()
        builder.add_csrf(cookie_name="csrf_c")
        builder.map_post("/submit", lambda request: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.post("/submit", data={})
        self.assertEqual(resp.status_code, 400)

    def test_header_token_accepted(self):
        builder = AppBuilder()
        builder.add_csrf(cookie_name="csrf_h")
        builder.map_get("/", lambda: {"ok": True})
        builder.map_post("/submit", lambda request: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/")
        token = resp.cookies.get("csrf_h", "")
        resp = client.post("/submit", headers={"X-CSRF-Token": token}, cookies={"csrf_h": token})
        self.assertEqual(resp.status_code, 200)

    def test_x_xsrf_token_header_accepted(self):
        builder = AppBuilder()
        builder.add_csrf(cookie_name="csrf_x")
        builder.map_get("/", lambda: {"ok": True})
        builder.map_post("/submit", lambda request: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/")
        token = resp.cookies.get("csrf_x", "")
        resp = client.post("/submit", headers={"X-XSRF-Token": token}, cookies={"csrf_x": token})
        self.assertEqual(resp.status_code, 200)

    def test_safe_methods_always_allowed(self):
        builder = AppBuilder()
        builder.add_csrf()
        builder.map_get("/data", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        self.assertEqual(client.get("/data").status_code, 200)
        self.assertEqual(client.request("HEAD", "/data").status_code, 404)
        self.assertEqual(client.request("OPTIONS", "/data").status_code, 404)
