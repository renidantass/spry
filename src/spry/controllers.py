from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from spry.auth import CookieAuthService
from spry.http import Response
from spry.results import bad_request, created, no_content, not_found, ok
from spry.views import HtmlString, ViewRenderer


class ControllerBase:
    def ok(self, value: Any | None = None) -> Response:
        return ok(value)

    def created(self, location: str, value: Any | None = None) -> Response:
        return created(location, value)

    def bad_request(self, message: str = "Bad request") -> Response:
        return bad_request(message)

    def not_found(self, message: str = "Not found") -> Response:
        return not_found(message)

    def no_content(self) -> Response:
        return no_content()

    def unauthorized(self, message: str = "Unauthorized") -> Response:
        return Response.json({"error": message}, 401)

    def forbidden(self, message: str = "Forbidden") -> Response:
        return Response.json({"error": message}, 403)

    def json(self, value: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> Response:
        return Response.json(value, status_code=status_code, headers=headers)

    def text(self, value: str, status_code: int = 200, headers: dict[str, str] | None = None) -> Response:
        return Response.text(value, status_code=status_code, headers=headers)

    def html(self, markup: str, status_code: int = 200, headers: dict[str, str] | None = None) -> Response:
        return Response.html(markup, status_code=status_code, headers=headers)

    def redirect(self, location: str, status_code: int = 302) -> Response:
        return Response.empty(status_code, headers={"Location": location})

    def file_bytes(self, content: bytes, content_type: str, status_code: int = 200) -> Response:
        return Response(content, status_code=status_code, headers={"Content-Type": content_type})


class Controller(ControllerBase):
    def __init__(self, view_renderer: ViewRenderer) -> None:
        self._view_renderer = view_renderer

    def view(
        self,
        view_name: str,
        model: Mapping[str, Any] | None = None,
        *,
        layout: str | None = None,
        status_code: int = 200,
    ) -> Response:
        full_model = dict(model or {})
        if "csrf_input" not in full_model and hasattr(self, 'request'):
            token = self.request.items.get("csrf_token", "")
            field_name = self.request.items.get("csrf_field_name", "__csrf")
            if token:
                full_model["csrf_input"] = HtmlString(f'<input type="hidden" name="{field_name}" value="{token}" />')
        markup = self._view_renderer.render(view_name, full_model, layout=layout)
        return self.html(markup, status_code=status_code)

    def partial_view(self, view_name: str, model: Mapping[str, Any] | None = None) -> HtmlString:
        return self._view_renderer.render_partial(view_name, model)


class AuthenticatedController(Controller):
    def __init__(self, view_renderer: ViewRenderer, auth: CookieAuthService) -> None:
        super().__init__(view_renderer)
        self.auth = auth

    def sign_in(self, response: Response, user_id: str, name: str, claims: dict[str, Any] | None = None) -> Response:
        self.auth.sign_in(response, user_id, name, claims)
        return response

    def sign_out(self, response: Response) -> Response:
        self.auth.sign_out(response)
        return response

    def csrf_input(self, request: Any) -> HtmlString:
        token = request.items.get("csrf_token", "")
        field_name = request.items.get("csrf_field_name", "__csrf")
        return HtmlString(f'<input type="hidden" name="{field_name}" value="{token}" />')


def serve_static_file(static_dir: str | Path, relative_name: str, content_types: Mapping[str, str]) -> Response:
    base_dir = Path(static_dir).resolve()
    file_path = (base_dir / relative_name).resolve()
    if file_path.parent != base_dir or not file_path.exists():
        return Response.text("Not found", 404)

    content_type = content_types.get(file_path.suffix)
    if content_type is None:
        return Response.text("Unsupported asset", 404)
    return Response(file_path.read_bytes(), headers={"Content-Type": content_type})
