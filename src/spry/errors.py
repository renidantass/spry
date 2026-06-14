from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spry.http import ProblemDetail, Response


@dataclass(slots=True)
class ErrorMeta:
    status_code: int
    title: str
    error_type: str


class SpryError(Exception):
    """Base exception that the pipeline translates to an HTTP response."""

    meta = ErrorMeta(status_code=500, title="Internal Server Error", error_type="/errors/internal")

    def __init__(self, detail: str = "", **extras: Any) -> None:
        self.detail = detail or self.meta.title
        self.extras: dict[str, Any] = extras
        super().__init__(self.detail)

    def to_response(self) -> Response:
        return ProblemDetail(
            type=self.meta.error_type,
            title=self.meta.title,
            status=self.meta.status_code,
            detail=self.detail,
        ).to_response()


class BadRequestError(SpryError):
    meta = ErrorMeta(status_code=400, title="Bad Request", error_type="/errors/bad-request")


class UnauthorizedError(SpryError):
    meta = ErrorMeta(status_code=401, title="Unauthorized", error_type="/errors/unauthorized")


class ForbiddenError(SpryError):
    meta = ErrorMeta(status_code=403, title="Forbidden", error_type="/errors/forbidden")


class NotFoundError(SpryError):
    meta = ErrorMeta(status_code=404, title="Not Found", error_type="/errors/not-found")


class ConflictError(SpryError):
    meta = ErrorMeta(status_code=409, title="Conflict", error_type="/errors/conflict")


class UnprocessableEntityError(SpryError):
    meta = ErrorMeta(status_code=422, title="Unprocessable Entity", error_type="/errors/unprocessable-entity")
