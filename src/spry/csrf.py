from __future__ import annotations

import hmac
import secrets

from spry.http import Request, Response


class CsrfService:
    def __init__(self, *, cookie_name: str = "spry_csrf", field_name: str = "__csrf") -> None:
        self.cookie_name = cookie_name
        self.field_name = field_name

    def get_or_create_token(self, request: Request) -> tuple[str, bool]:
        existing = request.cookies.get(self.cookie_name)
        if existing:
            return existing, False
        return secrets.token_urlsafe(32), True

    def attach_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(self.cookie_name, token, path="/", http_only=True, same_site="Lax")

    def _get_header(self, request: Request, name: str) -> str | None:
        for key in (name, name.lower(), name.title(), name.upper()):
            value = request.headers.get(key)
            if value:
                return value
        return None

    def validate_request(self, request: Request) -> bool:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        cookie_token = request.cookies.get(self.cookie_name)
        if not cookie_token:
            return False
        form_token = request.form().get(self.field_name)
        header_token = self._get_header(request, "X-CSRF-Token") or self._get_header(request, "X-XSRF-Token")
        token = form_token or header_token
        return bool(token) and hmac.compare_digest(cookie_token, token)


def csrf_error_response(request: Request) -> Response:
    accepts_html = "text/html" in request.headers.get("Accept", "") or request.headers.get("Accept", "") in {"", "*/*"}
    if accepts_html:
        return Response.html("<h1>Bad Request</h1><p>Invalid CSRF token.</p>", 400)
    return Response.json({"error": "Invalid CSRF token"}, 400)
