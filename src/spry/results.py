from __future__ import annotations

from typing import Any, TypeAlias

from spry.http import Response


ActionResult: TypeAlias = "Response | dict | list | None | bytes | str"


def ok(value: Any | None = None) -> Response:
    return Response.empty(200) if value is None else Response.json(value, 200)


def created(location: str, value: Any | None = None) -> Response:
    headers = {"Location": location}
    return Response.empty(201, headers=headers) if value is None else Response.json(value, 201, headers=headers)


def no_content() -> Response:
    return Response.empty(204)


def not_found(message: str = "Not found") -> Response:
    return Response.json({"error": message}, 404)


def bad_request(message: str = "Bad request") -> Response:
    return Response.json({"error": message}, 400)
