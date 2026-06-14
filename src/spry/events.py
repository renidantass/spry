from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable


class EventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable[..., Any] | None = None) -> None:
        if handler is None:
            self._handlers.pop(event, None)
        else:
            self._handlers[event] = [h for h in self._handlers[event] if h is not handler]

    def dispatch(self, event: str, **kwargs: Any) -> list[Any]:
        results: list[Any] = []
        for handler in self._handlers.get(event, []):
            result = handler(**kwargs)
            if inspect.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import threading
                        future = asyncio.run_coroutine_threadsafe(result, loop)
                        results.append(future.result())
                    else:
                        results.append(asyncio.run(result))
                except RuntimeError:
                    results.append(asyncio.run(result))
            else:
                results.append(result)
        return results

    async def dispatch_async(self, event: str, **kwargs: Any) -> list[Any]:
        results: list[Any] = []
        for handler in self._handlers.get(event, []):
            result = handler(**kwargs)
            if inspect.iscoroutine(result):
                result = await result
            results.append(result)
        return results
