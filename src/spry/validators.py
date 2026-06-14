from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class Validator(ABC):
    @abstractmethod
    def validate(self, value: Any, field: str) -> str | None:
        ...


class Required(Validator):
    def validate(self, value: Any, field: str) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"Field '{field}' is required"
        return None


class MinLength(Validator):
    def __init__(self, min_len: int) -> None:
        self.min_len = min_len

    def validate(self, value: Any, field: str) -> str | None:
        if value is not None and len(str(value)) < self.min_len:
            return f"Field '{field}' must have at least {self.min_len} characters"
        return None


class MaxLength(Validator):
    def __init__(self, max_len: int) -> None:
        self.max_len = max_len

    def validate(self, value: Any, field: str) -> str | None:
        if value is not None and len(str(value)) > self.max_len:
            return f"Field '{field}' must have at most {self.max_len} characters"
        return None


class Regex(Validator):
    def __init__(self, pattern: str, message: str | None = None) -> None:
        self._pattern = re.compile(pattern)
        self._message = message

    def validate(self, value: Any, field: str) -> str | None:
        if value is not None:
            s = str(value)
            if len(s) > 10_000:
                return f"Field '{field}' value is too long for pattern matching"
            if not self._pattern.match(s):
                return self._message or f"Field '{field}' does not match required pattern"
        return None


class Email(Validator):
    _pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def validate(self, value: Any, field: str) -> str | None:
        if value is not None and not self._pattern.match(str(value)):
            return f"Field '{field}' must be a valid email address"
        return None


class Range(Validator):
    def __init__(self, min_val: float | None = None, max_val: float | None = None) -> None:
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any, field: str) -> str | None:
        if value is not None:
            try:
                num = float(value)
                if self.min_val is not None and num < self.min_val:
                    return f"Field '{field}' must be at least {self.min_val}"
                if self.max_val is not None and num > self.max_val:
                    return f"Field '{field}' must be at most {self.max_val}"
            except (TypeError, ValueError):
                return f"Field '{field}' must be a number"
        return None


def required() -> Required:
    """Factory: Required()"""
    return Required()


def min_length(min_len: int) -> MinLength:
    """Factory: MinLength(min_len)"""
    return MinLength(min_len)


def max_length(max_len: int) -> MaxLength:
    """Factory: MaxLength(max_len)"""
    return MaxLength(max_len)


def email() -> Email:
    """Factory: Email()"""
    return Email()


def regex(pattern: str, message: str | None = None) -> Regex:
    """Factory: Regex(pattern, message)"""
    return Regex(pattern, message)


def range_validator(min_val: float | None = None, max_val: float | None = None) -> Range:
    """Factory: Range(min_val, max_val)"""
    return Range(min_val, max_val)


def validate_model(model: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    from dataclasses import fields

    for field in fields(model):
        validators = field.metadata.get("validate", [])
        if not validators:
            continue
        value = getattr(model, field.name)
        for validator in validators:
            msg = validator.validate(value, field.name)
            if msg:
                errors.append({"field": field.name, "message": msg, "code": type(validator).__name__.lower()})
    return errors
