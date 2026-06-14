from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger("spry.tasks")


def _run_sync(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    try:
        result = fn(*args, **kwargs)
        if inspect.iscoroutine(result):
            asyncio.run(result)
    except Exception as exc:
        logger.error("Background task %s failed: %s", getattr(fn, "__name__", repr(fn)), exc)


class BackgroundTask:
    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self._executor = executor
        self._future = None
        self._error: Exception | None = None

    @property
    def is_done(self) -> bool:
        return self._future is not None and self._future.done()

    @property
    def error(self) -> Exception | None:
        if self._future is not None and self._future.done():
            try:
                self._future.result()
            except Exception as exc:
                return exc
        return self._error

    def _run(self, fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        try:
            self._future = self._executor.submit(_run_sync, fn, *args, **kwargs)
        except RuntimeError:
            logger.warning("Executor is closed; task was not submitted")


class BackgroundWorker:
    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="spry-bg")

    def enqueue(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> BackgroundTask:
        task = BackgroundTask(self._executor)
        task._run(fn, args, kwargs)
        return task

    @staticmethod
    def delay(seconds: float, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> BackgroundTask:
        def delayed() -> None:
            time.sleep(seconds)
            _run_sync(fn, *args, **kwargs)

        worker = BackgroundWorker(max_workers=1)
        task = BackgroundTask(worker._executor)
        task._run(delayed, (), {})
        return task

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
