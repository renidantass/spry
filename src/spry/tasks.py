from __future__ import annotations

import inspect
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger("spry.tasks")


class BackgroundTask:
    def __init__(self, fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self._thread: threading.Thread | None = None
        self._done = False
        self._error: Exception | None = None

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            if inspect.iscoroutine(result):
                import asyncio
                asyncio.run(result)
        except Exception as e:
            self._error = e
            logger.error("Background task %s failed: %s", self.fn.__name__, e)
        finally:
            self._done = True

    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def is_done(self) -> bool:
        return self._done

    def error(self) -> Exception | None:
        return self._error


class BackgroundWorker:
    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers

    def enqueue(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> BackgroundTask:
        task = BackgroundTask(fn, args, kwargs)
        task.start()
        return task

    @staticmethod
    def delay(seconds: float, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> BackgroundTask:
        def delayed() -> None:
            time.sleep(seconds)
            result = fn(*args, **kwargs)
            if inspect.iscoroutine(result):
                import asyncio
                asyncio.run(result)
        task = BackgroundTask(delayed, (), {})
        task.start()
        return task
