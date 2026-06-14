from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from spry.http import Response


class TokenBucket:
    def __init__(self, max_requests: int, window: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window = window
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup(self, key: str) -> None:
        now = time.time()
        cutoff = now - self.window
        remaining = [t for t in self._buckets[key] if t > cutoff]
        if remaining:
            self._buckets[key] = remaining
        else:
            self._buckets.pop(key, None)

    def is_allowed(self, key: str) -> bool:
        with self._lock:
            self._cleanup(key)
            if len(self._buckets[key]) >= self.max_requests:
                return False
            self._buckets[key].append(time.time())
            return True

    def remaining(self, key: str) -> int:
        with self._lock:
            self._cleanup(key)
            return max(0, self.max_requests - len(self._buckets[key]))

    def reset_time(self, key: str) -> float:
        with self._lock:
            self._cleanup(key)
            if self._buckets[key]:
                return self._buckets[key][0] + self.window
            return time.time() + self.window


# Backward-compatible alias. Older code paths referred to the in-memory rate
# limiter as InMemoryStore; TokenBucket has always been that implementation.
InMemoryStore = TokenBucket


def rate_limit_middleware_factory(
    bucket: TokenBucket,
    key_func: Any = None,
    status_code: int = 429,
    message: str = "Too many requests",
) -> Any:
    def get_key(context: Any) -> str:
        if key_func:
            return key_func(context)
        return context.request.headers.get("X-Forwarded-For", context.request.host)

    def middleware(context: Any, next_handler: Any) -> Response:
        key = get_key(context)
        if not bucket.is_allowed(key):
            resp = Response.json({"error": message, "retry_after": int(bucket.window)}, status_code)
            resp.headers["Retry-After"] = str(int(bucket.window))
            resp.headers["X-RateLimit-Limit"] = str(bucket.max_requests)
            resp.headers["X-RateLimit-Remaining"] = str(bucket.remaining(key))
            return resp
        response = next_handler()
        response.headers["X-RateLimit-Limit"] = str(bucket.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(bucket.remaining(key))
        return response

    return middleware
