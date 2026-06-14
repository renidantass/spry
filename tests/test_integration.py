from __future__ import annotations

import unittest
from dataclasses import dataclass

from spry import AppBuilder, ControllerBase, controller, post
from spry.testing import TestClient


@dataclass(slots=True)
class _Item:
    name: str


class SmokeTests(unittest.TestCase):
    def test_app_imports_and_creates(self):
        from spry import AppBuilder, Application
        builder = AppBuilder()
        builder.map_get("/ping", lambda: {"ok": True})
        app = builder.build()
        self.assertIsInstance(app, Application)

    def test_basic_request_response_cycle(self):
        builder = AppBuilder()
        builder.map_get("/ping", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/ping")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})

    def test_404_for_unknown_route(self):
        builder = AppBuilder()
        builder.map_get("/known", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/unknown")
        self.assertEqual(resp.status_code, 404)

    def test_health_endpoint(self):
        builder = AppBuilder()
        builder.map_get("/ping", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)
        self.assertIn("uptime_seconds", data)


class IntegrationTests(unittest.TestCase):
    def test_full_pipeline_with_all_middlewares(self):
        builder = AppBuilder()
        builder.map_get("/", lambda: {"ok": True})
        builder.map_post("/data", lambda request: {"received": request.json()})
        builder.add_cors(origins=["*"])
        builder.add_security_headers()
        builder.add_session(secret_key="test-secret-key")
        builder.add_csrf(cookie_name="test_csrf")
        builder.add_rate_limiter(max_requests=100, window=60)
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/", headers={"Origin": "https://app.com"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)
        self.assertIn("Content-Security-Policy", resp.headers)

        resp = client.post("/data", json={"hello": "world"}, headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"received": {"hello": "world"}})

    def test_session_and_csrf_together(self):
        builder = AppBuilder()
        builder.map_get("/", lambda request: {"session": request.items.get("session", {})})
        builder.map_post("/submit", lambda request: {"ok": True})
        builder.add_session(secret_key="integration-secret")
        builder.add_csrf(cookie_name="int_csrf")
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        session_cookie = resp.cookies.get("spry_session", "")

        csrf_cookie = resp.cookies.get("int_csrf", "")
        resp = client.post("/submit", data={"__csrf": csrf_cookie}, cookies={"spry_session": session_cookie, "int_csrf": csrf_cookie})
        self.assertEqual(resp.status_code, 200)

    def test_error_handling_pipeline(self):
        def failing_handler():
            raise RuntimeError("Something went wrong")

        builder = AppBuilder()
        builder.map_get("/fail", failing_handler)
        builder.set_debug(False)
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/fail")
        self.assertEqual(resp.status_code, 500)

    def test_validation_error_returns_422(self):
        @controller("/items")
        class Ctrl(ControllerBase):
            @post("/")
            def create(self, item: _Item):
                return {"created": item.name}

        builder = AppBuilder()
        builder.add_controller(Ctrl)
        app = builder.build()
        client = TestClient(app)

        resp = client.post("/items", json={})
        self.assertEqual(resp.status_code, 422)

        resp = client.post("/items", json={"name": "test"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"created": "test"})
