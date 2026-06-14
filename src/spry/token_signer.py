from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


_ALG_DIGEST_MAP: dict[str, str] = {
    "HS256": "sha256",
    "HS384": "sha384",
    "HS512": "sha512",
}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _hmac(secret: bytes, message: bytes, algorithm: str = "HS256") -> bytes:
    digest = _ALG_DIGEST_MAP.get(algorithm, "sha256")
    return hmac.new(secret, message, digest).digest()


class TokenSigner:
    DEFAULT_ALGORITHM = "HS256"

    def __init__(self, secret_key: str, algorithm: str = DEFAULT_ALGORITHM) -> None:
        if algorithm not in _ALG_DIGEST_MAP:
            raise NotImplementedError(
                f"Algorithm '{algorithm}' is not supported. "
                f"Supported: {sorted(_ALG_DIGEST_MAP)}"
            )
        self._secret = secret_key.encode("utf-8")
        self.algorithm = algorithm

    def sign(self, payload: str) -> str:
        sig = hmac.new(self._secret, payload.encode("utf-8"), _ALG_DIGEST_MAP[self.algorithm]).hexdigest()
        return f"{payload}.{sig}"

    def unsign(self, token: str, max_age: float | None = None) -> str | None:
        try:
            payload, sig = token.rsplit(".", 1)
            expected = hmac.new(self._secret, payload.encode("utf-8"), _ALG_DIGEST_MAP[self.algorithm]).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            return payload
        except (ValueError, AttributeError):
            return None

    def sign_b64(self, data: dict[str, Any]) -> str:
        b64 = _b64url_encode(json.dumps(data, separators=(",", ":")).encode("utf-8"))
        sig = _b64url_encode(_hmac(self._secret, b64.encode("utf-8"), self.algorithm))
        return f"{b64}.{sig}"

    def unsign_b64(self, token: str, max_age: float | None = None) -> dict[str, Any] | None:
        try:
            b64, sig = token.rsplit(".", 1)
            expected = _b64url_encode(_hmac(self._secret, b64.encode("utf-8"), self.algorithm))
            if not hmac.compare_digest(sig, expected):
                return None
            data = json.loads(_b64url_decode(b64).decode("utf-8"))
            if max_age is not None:
                iat = data.get("iat", 0)
                if time.time() > iat + max_age:
                    return None
            return data
        except (ValueError, json.JSONDecodeError, AttributeError):
            return None

    def sign_jwt(self, payload: dict[str, Any]) -> str:
        header_b64 = _b64url_encode(json.dumps({"alg": self.algorithm, "typ": "JWT"}, separators=(",", ":")).encode())
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = _b64url_encode(_hmac(self._secret, f"{header_b64}.{payload_b64}".encode(), self.algorithm))
        return f"{header_b64}.{payload_b64}.{signature}"

    def unsign_jwt(self, token: str) -> dict[str, Any] | None:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, _ = parts
            expected = _b64url_encode(_hmac(self._secret, f"{header_b64}.{payload_b64}".encode(), self.algorithm))
            if not hmac.compare_digest(parts[2], expected):
                return None
            return json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, AttributeError):
            return None
