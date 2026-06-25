from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from spry import AppBuilder
from spry.auth import JwtAuthService
from spry.db.url import parse_database_url
from spry.http import StreamingResponse
from spry.testing import TestClient
from spry.token_signer import TokenSigner


class OpenApiSecuritySchemesTests(unittest.TestCase):
    def test_jwt_auth_registers_bearer_scheme(self) -> None:
        builder = AppBuilder(base_path=".")
        builder.add_jwt_auth(secret_key="x" * 32)
        builder.map_get("/ping", lambda: {"ok": True})
        app = builder.build()
        spec = app.openapi_spec
        self.assertIsNotNone(spec)
        schemes = spec["components"].get("securitySchemes", {})
        self.assertIn("BearerAuth", schemes)
        self.assertEqual(schemes["BearerAuth"]["type"], "http")
        self.assertEqual(schemes["BearerAuth"]["scheme"], "bearer")

    def test_cookie_auth_registers_api_key_scheme(self) -> None:
        builder = AppBuilder(base_path=".")
        builder.add_auth(secret_key="x" * 32, cookie_name="my_auth")
        builder.map_get("/ping", lambda: {"ok": True})
        app = builder.build()
        spec = app.openapi_spec
        schemes = spec["components"].get("securitySchemes", {})
        self.assertIn("CookieAuth", schemes)
        self.assertEqual(schemes["CookieAuth"]["type"], "apiKey")
        self.assertEqual(schemes["CookieAuth"]["in"], "cookie")
        self.assertEqual(schemes["CookieAuth"]["name"], "my_auth")


class AsgiAsyncHandlerTests(unittest.TestCase):
    def test_async_handler_via_asgi(self) -> None:
        async def async_handler():
            return {"async": True}

        builder = AppBuilder(base_path=".")
        builder.map_get("/async", async_handler)
        app = builder.build()

        async def runner() -> tuple[int, bytes]:
            messages: list = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await app.asgi(
                {"type": "http", "method": "GET", "path": "/async", "query_string": b"", "headers": [(b"host", b"t")], "scheme": "http"},
                receive,
                send,
            )
            return messages[0]["status"], messages[1]["body"]

        status, body = asyncio.run(runner())
        self.assertEqual(status, 200)
        import json
        self.assertEqual(json.loads(body), {"async": True})


class TokenSignerAlgorithmsTests(unittest.TestCase):
    def test_hs384_roundtrip(self) -> None:
        signer = TokenSigner("x" * 32, algorithm="HS384")
        token = signer.sign_jwt({"sub": "1"})
        self.assertEqual(signer.unsign_jwt(token), {"sub": "1"})

    def test_hs512_roundtrip(self) -> None:
        signer = TokenSigner("x" * 32, algorithm="HS512")
        token = signer.sign_jwt({"sub": "1"})
        self.assertEqual(signer.unsign_jwt(token), {"sub": "1"})

    def test_jwt_auth_accepts_hs512(self) -> None:
        service = JwtAuthService("x" * 32, algorithm="HS512", ttl=60)
        token = service.issue("1", "Ada")
        from spry.http import Request
        req = Request("GET", "/", {}, {"Authorization": f"Bearer {token}"}, b"", "http", "localhost")
        user = service.authenticate(req)
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "1")

    def test_unsupported_algorithm_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            TokenSigner("x" * 32, algorithm="RS256")


class SqliteAbsolutePathTests(unittest.TestCase):
    def test_sqlite_absolute_path(self) -> None:
        url = parse_database_url("sqlite:////tmp/spry.db")
        self.assertEqual(url.protocol, "sqlite")
        self.assertEqual(url.database, "/tmp/spry.db")

    def test_sqlite_relative_path(self) -> None:
        url = parse_database_url("sqlite:///spry.db")
        self.assertEqual(url.protocol, "sqlite")
        self.assertEqual(url.database, "spry.db")

    def test_sqlite_in_memory(self) -> None:
        url = parse_database_url("sqlite:///:memory:")
        self.assertEqual(url.protocol, "sqlite")
        self.assertEqual(url.database, ":memory:")


class StreamingResponseTests(unittest.TestCase):
    def test_streaming_via_wsgi(self) -> None:
        chunks = [b"hello ", b"world"]

        def start_response(status, headers):
            self.assertIn("200", status)

        captured: list[bytes] = []

        class FakeIterable:
            def __iter__(self):
                return iter(chunks)

        resp = StreamingResponse(FakeIterable())
        body_iter = resp.to_wsgi(start_response)
        captured.extend(body_iter)
        self.assertEqual(b"".join(captured), b"hello world")

    def test_callable_chunker(self) -> None:
        data = b"abcdefghij" * 100

        def chunker(block_size: int):
            for i in range(0, len(data), block_size):
                yield data[i : i + block_size]

        resp = StreamingResponse(chunker)
        result = b"".join(resp._iter_chunks())
        self.assertEqual(result, data)

    def test_static_files_stream_large(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            big = Path(d) / "big.bin"
            big.write_bytes(b"x" * (512 * 1024))
            builder = AppBuilder(base_path=".")
            builder.add_static_files("/static", d)
            app = builder.build()
            client = TestClient(app)
            resp = client.get("/static/big.bin")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.body), 512 * 1024)
            self.assertIn("Content-Length", resp.headers)
            self.assertEqual(resp.headers["Content-Length"], str(512 * 1024))

    def test_static_files_small_uses_response(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            small = Path(d) / "small.txt"
            small.write_text("hello")
            builder = AppBuilder(base_path=".")
            builder.add_static_files("/static", d)
            app = builder.build()
            client = TestClient(app)
            resp = client.get("/static/small.txt")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.body, b"hello")


if __name__ == "__main__":
    unittest.main()
