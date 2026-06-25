from __future__ import annotations

import json
import unittest

from spry.http import Request, Response, UploadedFile


class HttpTests(unittest.TestCase):
    def test_request_from_environ(self):
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/data",
            "QUERY_STRING": "page=1&limit=10",
            "CONTENT_LENGTH": "15",
            "CONTENT_TYPE": "application/json",
            "HTTP_HOST": "example.com",
            "HTTP_X_CUSTOM": "test-value",
            "wsgi.url_scheme": "https",
            "wsgi.input": __import__("io").BytesIO(b'{"key": "val"}'),
        }
        req = Request.from_environ(environ)
        self.assertEqual(req.method, "POST")
        self.assertEqual(req.path, "/api/data")
        self.assertEqual(req.query, {"page": "1", "limit": "10"})
        self.assertEqual(req.headers.get("Host"), "example.com")
        self.assertEqual(req.headers.get("X-Custom"), "test-value")
        self.assertEqual(req.scheme, "https")
        self.assertEqual(req.json(), {"key": "val"})

    def test_request_json_empty_body(self):
        req = Request("GET", "/", {}, {}, b"", "http", "localhost")
        self.assertEqual(req.json(), {})

    def test_request_form_urlencoded(self):
        body = b"name=John&age=30"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        req = Request("POST", "/", {}, headers, body, "http", "localhost")
        self.assertEqual(req.form(), {"name": "John", "age": "30"})

    def test_request_cookies(self):
        req = Request("GET", "/", {}, {"Cookie": "session=abc123; theme=dark"}, b"", "http", "localhost")
        self.assertEqual(req.cookies, {"session": "abc123", "theme": "dark"})

    def test_request_user_property(self):
        req = Request("GET", "/", {}, {}, b"", "http", "localhost")
        self.assertIsNone(req.user)
        req.user = "admin"
        self.assertEqual(req.user, "admin")
        req.user = None
        self.assertIsNone(req.user)

    def test_request_url(self):
        req = Request("GET", "/path", {}, {}, b"", "https", "example.com")
        self.assertEqual(req.url, "https://example.com/path")

    def test_response_text(self):
        resp = Response.text("Hello", 200)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Hello", resp.body)
        self.assertIn("text/plain", resp.headers.get("Content-Type", ""))

    def test_response_html(self):
        resp = Response.html("<h1>Title</h1>")
        self.assertIn(b"<h1>Title</h1>", resp.body)
        self.assertIn("text/html", resp.headers.get("Content-Type", ""))

    def test_response_json(self):
        resp = Response.json({"key": "value"})
        data = json.loads(resp.body)
        self.assertEqual(data, {"key": "value"})
        self.assertIn("application/json", resp.headers.get("Content-Type", ""))

    def test_response_empty(self):
        resp = Response.empty(204)
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.body, b"")

    def test_response_cookie(self):
        resp = Response.text("ok")
        resp.set_cookie("session", "abc123", path="/app")
        header_str = " ".join(k + "=" + v for k, v in resp._extra_headers)
        self.assertIn("session=abc123", header_str)
        self.assertIn("Path=/app", header_str)

    def test_response_delete_cookie(self):
        resp = Response.text("ok")
        resp.delete_cookie("session")
        header_str = " ".join(k + "=" + v for k, v in resp._extra_headers)
        self.assertIn("Max-Age=0", header_str)

    def test_response_etag(self):
        resp = Response.json({"a": 1}).with_etag()
        self.assertIn("ETag", resp.headers)
        self.assertTrue(resp.headers["ETag"].startswith('"'))

    def test_response_cache_control(self):
        resp = Response.json({"a": 1}).with_cache_control(max_age=300)
        self.assertIn("max-age=300", resp.headers["Cache-Control"])

    def test_max_body_size_enforced(self):
        Request.set_max_body_size(10)
        with self.assertRaises(ValueError):
            environ = {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/",
                "QUERY_STRING": "",
                "CONTENT_LENGTH": "100",
                "wsgi.input": __import__("io").BytesIO(b"x" * 100),
                "HTTP_HOST": "localhost",
                "wsgi.url_scheme": "http",
            }
            Request.from_environ(environ)
        Request.set_max_body_size(10 * 1024 * 1024)

    def test_accepts_and_best_match(self):
        req = Request("GET", "/", {}, {"Accept": "application/json"}, b"", "http", "localhost")
        self.assertTrue(req.accepts("application/json"))
        self.assertFalse(req.accepts("text/html"))
        self.assertEqual(req.best_match(["application/json", "text/html"]), "application/json")

    def test_multipart_upload(self):
        body = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="title"\r\n\r\n'
            b'Hello\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
            b'Content-Type: text/plain\r\n\r\n'
            b'File content\r\n'
            b'--boundary--\r\n'
        )
        req = Request("POST", "/", {}, {"Content-Type": "multipart/form-data; boundary=boundary"}, body, "http", "localhost")
        self.assertEqual(req.form().get("title"), "Hello")
        self.assertIn("file", req.files())
        f = req.files()["file"]
        self.assertIsInstance(f, UploadedFile)
        self.assertEqual(f.filename, "test.txt")
        self.assertIn(b"File content", f.read())
