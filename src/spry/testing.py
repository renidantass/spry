from __future__ import annotations

import io
import json
import urllib.parse
from http.cookies import SimpleCookie
from typing import Any

from spry.http import Response, StreamingResponse


class TestResponse:
    def __init__(self, response: Response) -> None:
        self.status_code = response.status_code
        self.headers = dict(response.headers)
        self.body = response.body
        self._extra_headers = list(response._extra_headers)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def cookies(self) -> dict[str, str]:
        cookie = SimpleCookie()
        for name, value in self._extra_headers:
            if name.lower() == "set-cookie":
                cookie.load(value)
        return {key: morsel.value for key, morsel in cookie.items()}


class TestClient:
    def __init__(self, app: Any) -> None:
        self.app = app
        self._base_headers: dict[str, str] = {}
        self._base_cookies: dict[str, str] = {}

    def _build_environ(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        merged_headers = {**self._base_headers, **(headers or {})}
        merged_cookies = {**self._base_cookies, **(cookies or {})}

        body_bytes = b""
        content_type = merged_headers.get("Content-Type", "")

        if json_body is not None:
            body_bytes = json.dumps(json_body).encode("utf-8")
            content_type = "application/json"
        elif files:
            boundary = "----SpryTestBoundary" + str(hash(str(files)))
            body_bytes = self._build_multipart(data or {}, files, boundary)
            content_type = f"multipart/form-data; boundary={boundary}"
        elif data:
            body_bytes = urllib.parse.urlencode(data).encode("utf-8")
            content_type = "application/x-www-form-urlencoded"

        merged_headers["Content-Type"] = content_type

        cookie_header = "; ".join(f"{k}={v}" for k, v in merged_cookies.items())
        if cookie_header:
            merged_headers["Cookie"] = cookie_header

        prefix = merged_headers.get("Host", "localhost")
        http_headers = {f"HTTP_{k.upper().replace('-', '_')}": v for k, v in merged_headers.items()}

        return {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "CONTENT_LENGTH": str(len(body_bytes)),
            "CONTENT_TYPE": content_type,
            "wsgi.input": io.BytesIO(body_bytes),
            "wsgi.url_scheme": "http",
            "HTTP_HOST": prefix,
            **http_headers,
        }

    def _build_multipart(
        self,
        data: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
        boundary: str,
    ) -> bytes:
        parts: list[bytes] = []
        for name, value in data.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            parts.append(value.encode() + b"\r\n")
        for name, (filename, content, content_type) in files.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            )
            parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
            parts.append(content + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return b"".join(parts)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> TestResponse:
        captured_status: list[str] = []
        captured_headers: list[tuple[str, str]] = []

        def start_response(status: str, response_headers: list[tuple[str, str]]) -> None:
            captured_status.append(status)
            captured_headers.extend(response_headers)

        environ = self._build_environ(
            method=method,
            path=path,
            json_body=json,
            data=data,
            files=files,
            headers=headers,
            cookies=cookies,
        )
        result = self.app(environ, start_response)
        body = b"".join(result or [])
        status_code = int(captured_status[0].split()[0]) if captured_status else 200

        resp_headers: dict[str, str] = {}
        extra_headers: list[tuple[str, str]] = []
        for key, value in captured_headers:
            if key.lower().startswith("set-cookie"):
                extra_headers.append(("Set-Cookie", value))
            else:
                resp_headers[key] = value

        response = Response(body=body, status_code=status_code, headers=resp_headers)
        response._extra_headers = extra_headers
        return TestResponse(response)

    def _call_wsgi_streaming(self, environ: dict[str, Any], start_response: Any) -> "Response | StreamingResponse":
        """Variant that preserves StreamingResponse for tests that need it."""
        result = self.app(environ, start_response)
        # The framework's static handler returns either a Response or a
        # StreamingResponse. The standard _request path flattens both to
        # Response. This helper is for tests that need the streaming object.
        raise NotImplementedError("Use request() for both Response and StreamingResponse")

    def get(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> TestResponse:
        return self.request("DELETE", path, **kwargs)
