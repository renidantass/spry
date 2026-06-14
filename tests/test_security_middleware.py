from __future__ import annotations

import unittest
from spry import AppBuilder
from spry.http import Request
from spry.testing import TestClient


class CorsTests(unittest.TestCase):
    def test_cors_no_origins(self):
        builder = AppBuilder()
        builder.add_cors(origins=[])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/test", headers={"Origin": "https://evil.com"})
        self.assertIsNone(resp.headers.get("Access-Control-Allow-Origin"))

    def test_cors_specific_origin(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/test", headers={"Origin": "https://app.com"})
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "https://app.com")

    def test_cors_unknown_origin_blocked(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/test", headers={"Origin": "https://evil.com"})
        self.assertIsNone(resp.headers.get("Access-Control-Allow-Origin"))

    def test_cors_wildcard(self):
        builder = AppBuilder()
        builder.add_cors(origins=["*"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/test", headers={"Origin": "https://any.com"})
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_cors_options_preflight(self):
        builder = AppBuilder()
        builder.add_cors(origins=["https://app.com"])
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.request("OPTIONS", "/test", headers={"Origin": "https://app.com"})
        self.assertEqual(resp.status_code, 204)
        self.assertIn("Access-Control-Allow-Methods", resp.headers)


class CsrfTests(unittest.TestCase):
    def test_csrf_validate_form_token(self):
        builder = AppBuilder()
        builder.add_csrf()
        builder.map_get("/page", lambda: {"ok": True})
        builder.map_post("/submit", lambda request: {"ok": True})
        app = builder.build()

        client = TestClient(app)

        resp = client.get("/page")
        csrf_cookie = resp.cookies.get("spry_csrf", "")

        resp = client.post("/submit", data={"__csrf": csrf_cookie}, cookies={"spry_csrf": csrf_cookie})
        self.assertEqual(resp.status_code, 200)

    def test_csrf_rejects_wrong_token(self):
        builder = AppBuilder()
        builder.add_csrf()
        builder.map_post("/submit", lambda request: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.post("/submit", data={"__csrf": "wrong"}, cookies={"spry_csrf": "real"})
        self.assertEqual(resp.status_code, 400)

    def test_csrf_accepts_header_token(self):
        builder = AppBuilder()
        builder.add_csrf()
        builder.map_get("/page", lambda: {"ok": True})
        builder.map_post("/submit", lambda request: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/page")
        csrf_cookie = resp.cookies.get("spry_csrf", "")

        resp = client.post("/submit", headers={"X-CSRF-Token": csrf_cookie}, cookies={"spry_csrf": csrf_cookie})
        self.assertEqual(resp.status_code, 200)

    def test_csrf_safe_methods_skipped(self):
        builder = AppBuilder()
        builder.add_csrf()
        builder.map_get("/data", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/data")
        self.assertEqual(resp.status_code, 200)


class SessionTests(unittest.TestCase):
    def test_session_creates_new(self):
        from spry.session import SessionMiddleware, SessionStore
        builder = AppBuilder()
        builder.use(SessionMiddleware(store=SessionStore()))
        builder.map_get("/", lambda request: {"sid": request.items.get("session_id", "")})
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/")
        self.assertIn("spry_session", resp.cookies)

    def test_session_persists_data(self):
        from spry.session import SessionMiddleware, SessionStore

        def handler(request):
            session = request.items.get("session", {})
            count = session.get("count", 0) + 1
            session["count"] = count
            return {"count": count}

        builder = AppBuilder()
        builder.use(SessionMiddleware(store=SessionStore()))
        builder.map_get("/", handler)
        app = builder.build()
        client = TestClient(app)
        resp = client.get("/")
        self.assertEqual(resp.json()["count"], 1)

    def test_session_idle_timeout(self):
        from spry.session import SessionStore
        import time
        store = SessionStore(ttl=3600, idle_timeout=1)
        store.set("test", {"user": "admin"})
        time.sleep(1.5)
        self.assertIsNone(store.get("test"))

    def test_signed_session(self):
        from spry.session import SignedSessionStore
        store = SignedSessionStore("mysecret", ttl=3600)
        store.set("sid1", {"role": "admin"})
        token = store._sign("sid1")
        self.assertEqual(store._verify(token), "sid1")
        self.assertIsNone(store._verify(token + "tampered"))
