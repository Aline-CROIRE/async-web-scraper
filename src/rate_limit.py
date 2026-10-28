import asyncio
import inspect
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import ParamSpec, TypeVar
from weakref import WeakKeyDictionary

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class _LoopState:
    """Pacing state for one event loop; an asyncio.Lock cannot cross loops."""

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_call_time: float | None = None


def rate_limit(
    min_interval: float,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Limit how frequently calls to an async function can start."""
    if isinstance(min_interval, bool) or not isinstance(min_interval, (int, float)):
        raise TypeError("min_interval must be a number")

    if not math.isfinite(min_interval) or min_interval < 0:
        raise ValueError("min_interval must be finite and non-negative")

    def decorator(
        function: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        if not inspect.iscoroutinefunction(function):
            raise TypeError("rate_limit can only decorate an async function")

        if min_interval == 0:

            @wraps(function)
            async def unthrottled_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return await function(*args, **kwargs)

            return unthrottled_wrapper

        # Weak keys let finished event loops be garbage collected.
        states: WeakKeyDictionary[asyncio.AbstractEventLoop, _LoopState] = (
            WeakKeyDictionary()
        )

        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            loop = asyncio.get_running_loop()
            state = states.get(loop)
            if state is None:
                state = states[loop] = _LoopState()

            async with state.lock:
                now = time.monotonic()

                if state.last_call_time is not None:
                    elapsed = now - state.last_call_time
                    remaining = min_interval - elapsed

                    if remaining > 0:
                        await asyncio.sleep(remaining)

                state.last_call_time = time.monotonic()

            return await function(*args, **kwargs)

        return wrapper

    return decorator
