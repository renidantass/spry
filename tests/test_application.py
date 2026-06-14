from __future__ import annotations

import asyncio
import io
import json
import unittest
from dataclasses import dataclass

from spry import AppBuilder, Request, controller, get, post


@dataclass(slots=True)
class CreateMessage:
    text: str


@controller("/messages")
class MessageController:
    @get("/")
    def list(self):
        return {"items": ["ok"]}

    @post("/")
    def create(self, payload: CreateMessage):
        return {"message": payload.text}


class ApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        builder = AppBuilder(base_path=".")

        def powered_by(context, next_handler):
            context.items["trace"] = "set"
            response = next_handler()
            response.headers["X-Test"] = "middleware"
            return response

        builder.use(powered_by)
        builder.add_controller(MessageController)
        self.app = builder.build()

    def test_wsgi_middleware_and_route(self) -> None:
        response = self._call_wsgi("GET", "/messages")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(response["headers"]["X-Test"], "middleware")
        self.assertEqual(json.loads(response["body"]), {"items": ["ok"]})

    def test_validation_returns_422(self) -> None:
        response = self._call_wsgi("POST", "/messages", {"wrong": "value"})
        self.assertTrue(str(response["status"]).startswith("422 "))
        payload = json.loads(response["body"])
        self.assertEqual(payload["title"], "Validation Failed")
        self.assertEqual(payload["errors"][0]["field"], "text")

    def test_asgi_support(self) -> None:
        async def run_test() -> tuple[int, bytes]:
            messages: list[dict[str, object]] = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await self.app.asgi(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/messages",
                    "query_string": b"",
                    "headers": [(b"host", b"testserver")],
                    "scheme": "http",
                },
                receive,
                send,
            )
            start = messages[0]
            body = messages[1]
            return start["status"], body["body"]

        status, body = asyncio.run(run_test())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"items": ["ok"]})

    def _call_wsgi(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(body),
            "wsgi.url_scheme": "http",
            "HTTP_HOST": "testserver",
        }
        captured: dict[str, object] = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        chunks = self.app(environ, start_response)
        captured["body"] = b"".join(chunks)
        return captured


if __name__ == "__main__":
    unittest.main()
