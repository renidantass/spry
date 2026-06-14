from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from spry.http import Request, Response

logger = logging.getLogger("spry.auth")


@dataclass(slots=True)
class UserPrincipal:
    user_id: str
    name: str
    claims: dict[str, Any]

    @property
    def roles(self) -> list[str]:
        raw = self.claims.get("roles", [])
        if isinstance(raw, str):
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(raw, list):
            return [str(item) for item in raw]
        return []

    def is_in_role(self, role: str) -> bool:
        return role in self.roles


class PasswordHasher:
    def __init__(self, *, iterations: int = 600_000) -> None:
        self.iterations = iterations

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
        return f"pbkdf2_sha256${self.iterations}${salt.hex()}${digest.hex()}"

    def verify(self, password: str, hashed_password: str) -> bool:
        try:
            algorithm, iterations_text, salt_hex, digest_hex = hashed_password.split("$", 3)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations)
        return hmac.compare_digest(digest.hex(), digest_hex)


_DEV_SECRET_WARNED = False


def _warn_dev_secret() -> None:
    global _DEV_SECRET_WARNED
    if not _DEV_SECRET_WARNED:
        import logging
        logging.getLogger("spry").warning(
            "Using default auth secret 'spry-dev-secret'. "
            "Set a strong secret via 'auth.secret_key' in appsettings.json "
            "or pass it explicitly to add_auth()."
        )
        _DEV_SECRET_WARNED = True


class LoginTracker:
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_minutes * 60
        self._attempts: dict[str, list[float]] = {}

    def record_failure(self, identifier: str) -> int:
        now = time.time()
        cutoff = now - self.lockout_seconds
        if identifier not in self._attempts:
            self._attempts[identifier] = []
        self._attempts[identifier] = [t for t in self._attempts[identifier] if t > cutoff]
        self._attempts[identifier].append(now)
        attempts = len(self._attempts[identifier])
        if attempts >= self.max_attempts:
            logger.warning("Account locked due to failed attempts: %s (%d/%d)", identifier, attempts, self.max_attempts)
        return attempts

    def is_locked(self, identifier: str) -> bool:
        now = time.time()
        cutoff = now - self.lockout_seconds
        attempts = [t for t in self._attempts.get(identifier, []) if t > cutoff]
        return len(attempts) >= self.max_attempts

    def remaining_attempts(self, identifier: str) -> int:
        now = time.time()
        cutoff = now - self.lockout_seconds
        attempts = len([t for t in self._attempts.get(identifier, []) if t > cutoff])
        return max(0, self.max_attempts - attempts)

    def lockout_remaining_seconds(self, identifier: str) -> int:
        now = time.time()
        cutoff = now - self.lockout_seconds
        attempts = [t for t in self._attempts.get(identifier, []) if t > cutoff]
        if len(attempts) < self.max_attempts:
            return 0
        earliest = attempts[0]
        remaining = int(self.lockout_seconds - (now - earliest))
        return max(0, remaining)

    def reset(self, identifier: str) -> None:
        self._attempts.pop(identifier, None)


class CookieAuthService:
    def __init__(self, secret_key: str, *, cookie_name: str = "spry_auth") -> None:
        if not secret_key or secret_key == "spry-dev-secret":
            _warn_dev_secret()
        self.secret_key = (secret_key or "spry-dev-secret").encode("utf-8")
        self.cookie_name = cookie_name

    def issue(self, user_id: str, name: str, claims: dict[str, Any] | None = None) -> str:
        payload = {
            "sub": user_id,
            "name": name,
            "claims": claims or {},
        }
        payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_token = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
        signature = hmac.new(self.secret_key, payload_token.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_token}.{signature}"

    def authenticate(self, request: Request) -> UserPrincipal | None:
        token = request.cookies.get(self.cookie_name)
        if not token:
            return None
        payload = self._read_payload(token)
        if payload is None:
            return None
        return UserPrincipal(
            user_id=str(payload.get("sub", "")),
            name=str(payload.get("name", "")),
            claims=dict(payload.get("claims", {})),
        )

    def sign_in(self, response: Response, user_id: str, name: str, claims: dict[str, Any] | None = None) -> None:
        response.set_cookie(self.cookie_name, self.issue(user_id, name, claims), path="/")

    def sign_out(self, response: Response) -> None:
        response.delete_cookie(self.cookie_name, path="/")

    def _read_payload(self, token: str) -> dict[str, Any] | None:
        try:
            payload_token, signature = token.rsplit(".", 1)
        except ValueError:
            return None

        expected_signature = hmac.new(self.secret_key, payload_token.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        padding = "=" * (-len(payload_token) % 4)
        try:
            payload_json = base64.urlsafe_b64decode(payload_token + padding)
            return json.loads(payload_json.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return None


class JwtAuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256", ttl: int = 3600) -> None:
        self.secret_key = secret_key.encode("utf-8")
        self.algorithm = algorithm
        self.ttl = ttl

    def issue(self, user_id: str, name: str, claims: dict[str, Any] | None = None) -> str:
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()).rstrip(b"=").decode()
        payload_data = {
            "sub": user_id,
            "name": name,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.ttl,
            "claims": claims or {},
        }
        payload = base64.urlsafe_b64encode(json.dumps(payload_data, separators=(",", ":")).encode()).rstrip(b"=").decode()
        signature_input = f"{header}.{payload}".encode()
        signature = base64.urlsafe_b64encode(hmac.new(self.secret_key, signature_input, hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{header}.{payload}.{signature}"

    def authenticate(self, request: Request) -> UserPrincipal | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        payload = self._read_payload(token)
        if payload is None:
            return None
        return UserPrincipal(
            user_id=str(payload.get("sub", "")),
            name=str(payload.get("name", "")),
            claims=dict(payload.get("claims", {})),
        )

    def _read_payload(self, token: str) -> dict[str, Any] | None:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_str, payload_str, _ = parts

            expected_sig = base64.urlsafe_b64encode(
                hmac.new(self.secret_key, f"{header_str}.{payload_str}".encode(), hashlib.sha256).digest()
            ).rstrip(b"=").decode()
            if not hmac.compare_digest(parts[2], expected_sig):
                return None

            padding = "=" * (-len(payload_str) % 4)
            payload_data = json.loads(base64.urlsafe_b64decode(payload_str + padding).decode("utf-8"))

            exp = payload_data.get("exp", 0)
            if time.time() > exp:
                return None
            return payload_data
        except (ValueError, json.JSONDecodeError, Exception):
            return None

    def sign_in(self, response: Response, user_id: str, name: str, claims: dict[str, Any] | None = None) -> str:
        token = self.issue(user_id, name, claims)
        response.headers["Authorization"] = f"Bearer {token}"
        return token


def authorize(
    login_path: str = "/login",
    *,
    roles: str | Iterable[str] | None = None,
    access_denied_path: str = "/access-denied",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
        resolved_roles = [roles] if isinstance(roles, str) else list(roles or [])
        handler.__spry_authorize__ = {
            "login_path": login_path,
            "roles": resolved_roles,
            "access_denied_path": access_denied_path,
        }
        return handler

    return decorator


def unauthorized_response(request: Request, login_path: str = "/login") -> Response:
    accepts_html = "text/html" in request.headers.get("Accept", "") or request.headers.get("Accept", "") in {"", "*/*"}
    if accepts_html and request.method == "GET":
        return Response.empty(302, headers={"Location": login_path})
    return Response.json({"error": "Unauthorized"}, 401)


def forbidden_response(request: Request, access_denied_path: str = "/access-denied") -> Response:
    accepts_html = "text/html" in request.headers.get("Accept", "") or request.headers.get("Accept", "") in {"", "*/*"}
    if accepts_html and request.method == "GET":
        return Response.empty(302, headers={"Location": access_denied_path})
    return Response.json({"error": "Forbidden"}, 403)
