from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Any

from spry.http import Request, Response
from spry.token_signer import TokenSigner

logger = logging.getLogger("spry.session")


class SessionStore:
    def __init__(self, ttl: int = 3600, idle_timeout: int | None = None) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._expires: dict[str, float] = {}
        self._last_access: dict[str, float] = {}
        self._ttl = ttl
        self._idle_timeout = idle_timeout
        self._lock = threading.Lock()

    def get(self, sid: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            if sid in self._expires and now > self._expires[sid]:
                self._delete_unlocked(sid)
                return None
            if sid in self._last_access and self._idle_timeout is not None:
                if now - self._last_access[sid] > self._idle_timeout:
                    logger.info("Session expired due to idle timeout: %s", sid[:8])
                    self._delete_unlocked(sid)
                    return None
            return self._data.get(sid)

    def set(self, sid: str, data: dict[str, Any]) -> None:
        now = time.time()
        with self._lock:
            self._data[sid] = data
            self._expires[sid] = now + self._ttl
            self._last_access[sid] = now

    def delete(self, sid: str) -> None:
        with self._lock:
            self._delete_unlocked(sid)

    def _delete_unlocked(self, sid: str) -> None:
        self._data.pop(sid, None)
        self._expires.pop(sid, None)
        self._last_access.pop(sid, None)

    def touch(self, sid: str) -> None:
        now = time.time()
        with self._lock:
            if sid in self._data:
                self._last_access[sid] = now

    def exists(self, sid: str) -> bool:
        with self._lock:
            return sid in self._data


class SignedSessionStore(SessionStore):
    def __init__(self, secret_key: str, ttl: int = 3600, idle_timeout: int | None = None) -> None:
        super().__init__(ttl=ttl, idle_timeout=idle_timeout)
        self._signer = TokenSigner(secret_key)

    def _sign(self, sid: str) -> str:
        return self._signer.sign(sid)

    def _verify(self, token: str) -> str | None:
        return self._signer.unsign(token)


class SessionMiddleware:
    def __init__(
        self,
        store: SessionStore | None = None,
        cookie_name: str = "spry_session",
        ttl: int = 3600,
        idle_timeout: int | None = 1800,
        secret_key: str | None = None,
    ) -> None:
        if secret_key:
            self._store: SessionStore = SignedSessionStore(secret_key, ttl=ttl, idle_timeout=idle_timeout)
        else:
            self._store = store or SessionStore(ttl=ttl, idle_timeout=idle_timeout)
        self._cookie_name = cookie_name
        self._use_signing = secret_key is not None

    def __call__(self, context: Any, next_handler: Any) -> Response:
        request: Request = context.request
        raw_sid = request.cookies.get(self._cookie_name)

        sid: str | None = None
        if raw_sid:
            if self._use_signing:
                sid = self._store._verify(raw_sid) if hasattr(self._store, "_verify") else raw_sid
            else:
                sid = raw_sid

        if sid is None or not self._store.exists(sid):
            sid = secrets.token_urlsafe(32)
            self._store.set(sid, {})

        session_data = self._store.get(sid) or {}

        request.items["session"] = session_data
        request.items["session_id"] = sid

        response = next_handler()

        self._store.set(sid, session_data)
        cookie_value = self._store._sign(sid) if self._use_signing and hasattr(self._store, "_sign") else sid
        response.set_cookie(self._cookie_name, cookie_value, path="/", http_only=True, same_site="Strict", max_age=self._store._ttl)
        return response

    @property
    def store(self) -> SessionStore:
        return self._store
