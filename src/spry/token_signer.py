from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class TokenSigner:
    def __init__(self, secret_key: str) -> None:
        self._secret = secret_key.encode("utf-8")

    def sign(self, payload: str) -> str:
        sig = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}.{sig}"

    def unsign(self, token: str, max_age: float | None = None) -> str | None:
        try:
            payload, sig = token.rsplit(".", 1)
            expected = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            return payload
        except (ValueError, AttributeError):
            return None

    def sign_b64(self, data: dict[str, Any]) -> str:
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
        b64 = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
        sig = hmac.new(self._secret, b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64}.{sig}"

    def unsign_b64(self, token: str, max_age: float | None = None) -> dict[str, Any] | None:
        try:
            b64, sig = token.rsplit(".", 1)
            expected = hmac.new(self._secret, b64.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            padding = "=" * (-len(b64) % 4)
            data = json.loads(base64.urlsafe_b64decode(b64 + padding).decode("utf-8"))
            if max_age is not None:
                iat = data.get("iat", 0)
                if time.time() > iat + max_age:
                    return None
            return data
        except (ValueError, json.JSONDecodeError, AttributeError):
            return None

    def sign_jwt(self, payload: dict[str, Any]) -> str:
        header_b64 = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
        signature = base64.urlsafe_b64encode(
            hmac.new(self._secret, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        return f"{header_b64}.{payload_b64}.{signature}"

    def unsign_jwt(self, token: str) -> dict[str, Any] | None:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, _ = parts
            expected = base64.urlsafe_b64encode(
                hmac.new(self._secret, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
            ).rstrip(b"=").decode()
            if not hmac.compare_digest(parts[2], expected):
                return None
            padding = "=" * (-len(payload_b64) % 4)
            return json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, AttributeError):
            return None
