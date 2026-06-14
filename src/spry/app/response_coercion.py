from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any, Protocol, runtime_checkable

from spry.http import Response, StreamingResponse
from spry.results import ActionResult


@runtime_checkable
class _HasToWsgi(Protocol):
    def to_wsgi(self, start_response: Any) -> Any: ...


def coerce_response(result: ActionResult) -> Response:
    if isinstance(result, Response):
        return result
    if isinstance(result, StreamingResponse):
        return result
    if isinstance(result, _HasToWsgi):
        # Wrapping preserves the duck-typed protocol without forcing a base class.
        return _WSGIAdapter(result)
    if result is None:
        return Response.empty(204)
    if isinstance(result, (dict, list)) or is_dataclass(result):
        return Response.json(result)
    if isinstance(result, bytes):
        return Response(result)
    return Response.text(str(result))


class _WSGIAdapter(Response):
    def __init__(self, inner: _HasToWsgi) -> None:
        super().__init__(body=b"", status_code=200, headers={})
        self._inner = inner

    def to_wsgi(self, start_response: Any) -> Any:
        return self._inner.to_wsgi(start_response)
