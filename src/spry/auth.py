from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from spry.http import Request, Response
from spry.token_signer import TokenSigner

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
_DEV_SECRET_LOCK = threading.Lock()


def _warn_dev_secret() -> None:
    global _DEV_SECRET_WARNED
    with _DEV_SECRET_LOCK:
        if _DEV_SECRET_WARNED:
            return
        _DEV_SECRET_WARNED = True
    logger.warning(
        "Using default auth secret 'spry-dev-secret'. "
        "Set a strong secret via 'auth.secret_key' in appsettings.json "
        "or pass it explicitly to add_auth()."
    )


class LoginTracker:
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_minutes * 60
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, identifier: str, cutoff: float) -> None:
        if identifier not in self._attempts:
            return
        remaining = [t for t in self._attempts[identifier] if t > cutoff]
        if remaining:
            self._attempts[identifier] = remaining
        else:
            del self._attempts[identifier]

    def record_failure(self, identifier: str) -> int:
        now = time.time()
        cutoff = now - self.lockout_seconds
        with self._lock:
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
        with self._lock:
            self._prune(identifier, cutoff)
            attempts = len(self._attempts.get(identifier, []))
            return attempts >= self.max_attempts

    def remaining_attempts(self, identifier: str) -> int:
        now = time.time()
        cutoff = now - self.lockout_seconds
        with self._lock:
            self._prune(identifier, cutoff)
            attempts = len(self._attempts.get(identifier, []))
        return max(0, self.max_attempts - attempts)

    def lockout_remaining_seconds(self, identifier: str) -> int:
        now = time.time()
        cutoff = now - self.lockout_seconds
        with self._lock:
            self._prune(identifier, cutoff)
            entries = self._attempts.get(identifier, [])
            if len(entries) < self.max_attempts:
                return 0
            earliest = entries[0]
        remaining = int(self.lockout_seconds - (now - earliest))
        return max(0, remaining)

    def reset(self, identifier: str) -> None:
        with self._lock:
            self._attempts.pop(identifier, None)


class CookieAuthService:
    def __init__(self, secret_key: str, *, cookie_name: str = "spry_auth", max_age: int = 86400) -> None:
        if not secret_key or secret_key == "spry-dev-secret":
            _warn_dev_secret()
        self._signer = TokenSigner(secret_key or "spry-dev-secret")
        self.cookie_name = cookie_name
        self._max_age = max_age

    def issue(self, user_id: str, name: str, claims: dict[str, Any] | None = None) -> str:
        return self._signer.sign_b64({
            "sub": user_id,
            "name": name,
            "iat": int(time.time()),
            "claims": claims or {},
        })

    def authenticate(self, request: Request) -> UserPrincipal | None:
        token = request.cookies.get(self.cookie_name)
        if not token:
            return None
        payload = self._signer.unsign_b64(token, max_age=self._max_age)
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


class JwtAuthService:
    SUPPORTED_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})

    def __init__(self, secret_key: str, algorithm: str = "HS256", ttl: int = 3600) -> None:
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise NotImplementedError(
                f"Algorithm '{algorithm}' is not supported. "
                f"Currently supported: {sorted(self.SUPPORTED_ALGORITHMS)}. "
                "Asymmetric algorithms (RS256, ES256) require the optional 'cryptography' extra."
            )
        if not secret_key:
            raise ValueError("JwtAuthService requires a non-empty secret_key")
        self._signer = TokenSigner(secret_key, algorithm=algorithm)
        self.algorithm = algorithm
        self.ttl = ttl

    def issue(self, user_id: str, name: str, claims: dict[str, Any] | None = None) -> str:
        payload = {
            "sub": user_id,
            "name": name,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.ttl,
            "claims": claims or {},
        }
        return self._signer.sign_jwt(payload)

    def authenticate(self, request: Request) -> UserPrincipal | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        payload = self._signer.unsign_jwt(token)
        if payload is None:
            return None
        exp = payload.get("exp", 0)
        if time.time() > exp:
            return None
        return UserPrincipal(
            user_id=str(payload.get("sub", "")),
            name=str(payload.get("name", "")),
            claims=dict(payload.get("claims", {})),
        )

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
