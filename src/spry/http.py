from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, is_dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs

MAX_BODY: int = 10 * 1024 * 1024


class UploadedFile:
    def __init__(self, filename: str, content_type: str, body: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.body = body

    def read(self) -> bytes:
        return self.body

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(self.body)


class Request:
    _max_body_size: int = MAX_BODY

    @classmethod
    def set_max_body_size(cls, size: int) -> None:
        cls._max_body_size = size

    def __init__(
        self,
        method: str,
        path: str,
        query: dict[str, str],
        headers: dict[str, str],
        body: bytes,
        scheme: str,
        host: str,
    ) -> None:
        self.method = method.upper()
        self.path = path
        self.query = query
        self.headers = headers
        self.body = body
        self.scheme = scheme
        self.host = host
        self._json_cache: Any | None = None
        self._form_cache: dict[str, str] | None = None
        self._files_cache: dict[str, UploadedFile] | None = None
        self._cookies_cache: dict[str, str] | None = None
        self.items: dict[str, Any] = {}

    @classmethod
    def from_environ(cls, environ: dict[str, Any]) -> Request:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        if content_length > cls._max_body_size:
            raise ValueError(f"Request body exceeds maximum size of {cls._max_body_size} bytes")
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
        raw_query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        query = {key: values[-1] for key, values in raw_query.items()}
        headers = {
            key[5:].replace("_", "-").title(): value
            for key, value in environ.items()
            if key.startswith("HTTP_")
        }
        if "CONTENT_TYPE" in environ:
            headers["Content-Type"] = environ["CONTENT_TYPE"]

        return cls(
            method=environ.get("REQUEST_METHOD", "GET"),
            path=environ.get("PATH_INFO", "/") or "/",
            query=query,
            headers=headers,
            body=body,
            scheme=environ.get("wsgi.url_scheme", "http"),
            host=environ.get("HTTP_HOST", "localhost"),
        )

    def json(self) -> Any:
        if self._json_cache is None:
            if not self.body:
                self._json_cache = {}
            else:
                try:
                    self._json_cache = json.loads(self.body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise ValueError(f"Invalid JSON body: {exc}") from exc
        return self._json_cache

    def text(self) -> str:
        return self.body.decode("utf-8")

    def form(self) -> dict[str, str]:
        if self._form_cache is None:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type and self.body:
                fields, _ = _parse_multipart(self.body, content_type)
                self._form_cache = fields
            elif "application/x-www-form-urlencoded" in content_type or not self.body:
                parsed = parse_qs(self.body.decode("utf-8"), keep_blank_values=True) if self.body else {}
                self._form_cache = {key: values[-1] for key, values in parsed.items()}
            else:
                self._form_cache = {}
        return self._form_cache

    def files(self) -> dict[str, UploadedFile]:
        if self._files_cache is None:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type and self.body:
                _, self._files_cache = _parse_multipart(self.body, content_type)
            else:
                self._files_cache = {}
        return self._files_cache

    @property
    def cookies(self) -> dict[str, str]:
        if self._cookies_cache is None:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            self._cookies_cache = {key: morsel.value for key, morsel in cookie.items()}
        return self._cookies_cache

    @property
    def user(self) -> Any | None:
        return self.items.get("user")

    @user.setter
    def user(self, value: Any | None) -> None:
        if value is None:
            self.items.pop("user", None)
            return
        self.items["user"] = value

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.host}{self.path}"

    def accepts(self, media_type: str) -> bool:
        accept = self.headers.get("Accept", "*/*")
        return media_type in accept or accept == "*/*" or accept == ""

    def best_match(self, options: list[str]) -> str | None:
        accept = self.headers.get("Accept", "*/*")
        if accept == "*/*" or not accept:
            return options[0] if options else None
        for option in options:
            if option in accept:
                return option
        return options[0] if options else None


class Response:
    def __init__(
        self,
        body: bytes = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        *,
        scheme: str = "http",
    ) -> None:
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self._extra_headers: list[tuple[str, str]] = []
        self._request_scheme = scheme

    @classmethod
    def text(cls, text: str, status_code: int = 200, headers: dict[str, str] | None = None) -> Response:
        payload = text.encode("utf-8")
        merged = {"Content-Type": "text/plain; charset=utf-8", **(headers or {})}
        return cls(body=payload, status_code=status_code, headers=merged)

    @classmethod
    def html(cls, markup: str, status_code: int = 200, headers: dict[str, str] | None = None) -> Response:
        payload = markup.encode("utf-8")
        merged = {"Content-Type": "text/html; charset=utf-8", **(headers or {})}
        return cls(body=payload, status_code=status_code, headers=merged)

    @classmethod
    def json(cls, value: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> Response:
        payload = json.dumps(value, default=_json_default).encode("utf-8")
        merged = {"Content-Type": "application/json; charset=utf-8", **(headers or {})}
        return cls(body=payload, status_code=status_code, headers=merged)

    @classmethod
    def empty(cls, status_code: int = 204, headers: dict[str, str] | None = None) -> Response:
        return cls(body=b"", status_code=status_code, headers=headers or {})

    def to_wsgi(self, start_response: Any) -> list[bytes]:
        headers = {**self.headers}
        headers.setdefault("Content-Length", str(len(self.body)))
        start_response(f"{self.status_code} {HTTPStatus(self.status_code).phrase}", self.header_items(headers))
        return [self.body]

    def header_items(self, base_headers: dict[str, str] | None = None) -> list[tuple[str, str]]:
        headers = dict(base_headers or self.headers)
        return list(headers.items()) + list(self._extra_headers)

    def set_cookie(
        self,
        name: str,
        value: str,
        *,
        path: str = "/",
        http_only: bool = True,
        same_site: str = "Lax",
        max_age: int | None = None,
        secure: bool | None = None,
    ) -> None:
        cookie = SimpleCookie()
        cookie[name] = value
        cookie[name]["path"] = path
        if http_only:
            cookie[name]["httponly"] = True
        if same_site:
            cookie[name]["samesite"] = same_site
        if max_age is not None:
            cookie[name]["max-age"] = str(max_age)
        if secure is True or (secure is None and self._request_scheme == "https"):
            cookie[name]["secure"] = True
        self._extra_headers.append(("Set-Cookie", cookie.output(header="").strip()))

    def delete_cookie(self, name: str, *, path: str = "/") -> None:
        cookie = SimpleCookie()
        cookie[name] = ""
        cookie[name]["path"] = path
        cookie[name]["max-age"] = "0"
        cookie[name]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        self._extra_headers.append(("Set-Cookie", cookie.output(header="").strip()))

    def with_etag(self) -> Response:
        import hashlib
        etag = hashlib.md5(self.body).hexdigest()
        self.headers["ETag"] = f'"{etag}"'
        return self

    def with_cache_control(self, *, max_age: int = 3600, public: bool = True) -> Response:
        parts = ["public" if public else "private", f"max-age={max_age}"]
        self.headers["Cache-Control"] = ", ".join(parts)
        return self


class StreamingResponse:
    """Response whose body is produced lazily by an iterable of bytes.

    Useful for serving large files without loading them entirely into memory.
    Content-Length is omitted so the server can use chunked transfer encoding.
    """

    def __init__(
        self,
        chunks: Iterable[bytes] | Callable[[int], Iterable[bytes]],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunk_size: int = 64 * 1024,
    ) -> None:
        self._chunks = chunks
        self._chunker: Callable[[int], Iterable[bytes]] | None = None
        if callable(chunks):
            self._chunker = chunks
        self.status_code = status_code
        self.headers = headers or {}
        self._extra_headers: list[tuple[str, str]] = []
        self._request_scheme = "http"
        self.chunk_size = chunk_size

    def header_items(self, base_headers: dict[str, str] | None = None) -> list[tuple[str, str]]:
        headers = dict(base_headers or self.headers)
        return list(headers.items()) + list(self._extra_headers)

    def to_wsgi(self, start_response: Any) -> list[bytes]:
        # WSGI expects an iterable of bytes. Transfer-Encoding: chunked is the
        # server's responsibility once we omit Content-Length.
        self.headers.setdefault("Transfer-Encoding", "chunked")
        start_response(
            f"{self.status_code} {HTTPStatus(self.status_code).phrase}",
            self.header_items(),
        )
        return list(self._iter_chunks())

    def _iter_chunks(self) -> Iterable[bytes]:
        if self._chunker is not None:
            yield from self._chunker(self.chunk_size)
            return
        for chunk in self._chunks:  # type: ignore[union-attr]
            if chunk:
                yield chunk

    def set_cookie(self, *args: Any, **kwargs: Any) -> None:
        from http.cookies import SimpleCookie
        name = args[0] if args else kwargs.get("name", "")
        value = args[1] if len(args) > 1 else kwargs.get("value", "")
        path = kwargs.get("path", "/")
        http_only = kwargs.get("http_only", True)
        same_site = kwargs.get("same_site", "Lax")
        max_age = kwargs.get("max_age")
        secure = kwargs.get("secure")
        cookie = SimpleCookie()
        cookie[name] = value
        cookie[name]["path"] = path
        if http_only:
            cookie[name]["httponly"] = True
        if same_site:
            cookie[name]["samesite"] = same_site
        if max_age is not None:
            cookie[name]["max-age"] = str(max_age)
        if secure is True or (secure is None and self._request_scheme == "https"):
            cookie[name]["secure"] = True
        self._extra_headers.append(("Set-Cookie", cookie.output(header="").strip()))

    def delete_cookie(self, name: str, *, path: str = "/") -> None:
        from http.cookies import SimpleCookie
        cookie = SimpleCookie()
        cookie[name] = ""
        cookie[name]["path"] = path
        cookie[name]["max-age"] = "0"
        cookie[name]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        self._extra_headers.append(("Set-Cookie", cookie.output(header="").strip()))


@dataclass(slots=True)
class ProblemDetail:
    type: str = "about:blank"
    title: str = ""
    status: int = 400
    detail: str = ""
    instance: str = ""
    errors: list[dict[str, Any]] | None = None

    def to_response(self) -> Response:
        body: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.instance:
            body["instance"] = self.instance
        if self.errors:
            body["errors"] = self.errors
        return Response.json(body, self.status, headers={"Content-Type": "application/problem+json"})


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _parse_multipart(body: bytes, content_type: str, max_parts: int = 100) -> tuple[dict[str, str], dict[str, UploadedFile]]:
    boundary_match = re.search(r"boundary=([^;]+)", content_type)
    if not boundary_match:
        return {}, {}
    boundary = boundary_match.group(1).strip().strip('"').strip("'")
    if not boundary:
        return {}, {}

    delimiter = f"--{boundary}".encode()
    parts = body.split(delimiter)
    if len(parts) > max_parts:
        raise ValueError(f"Multipart body exceeds maximum of {max_parts} parts")
    fields: dict[str, str] = {}
    files: dict[str, UploadedFile] = {}

    for part in parts:
        if not part.strip() or part.strip() == b"--":
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        raw_headers = part[:header_end].decode("utf-8", errors="replace")
        raw_body = part[header_end + 4:]
        if raw_body.endswith(b"\r\n"):
            raw_body = raw_body[:-2]

        name_match = re.search(r'name="([^"]*)"', raw_headers)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', raw_headers)
        if filename_match:
            ct_match = re.search(r"Content-Type:\s*(\S+)", raw_headers, re.IGNORECASE)
            ct = ct_match.group(1) if ct_match else "application/octet-stream"
            files[name] = UploadedFile(filename=filename_match.group(1), content_type=ct, body=raw_body)
        else:
            fields[name] = raw_body.decode("utf-8", errors="replace")

    return fields, files
