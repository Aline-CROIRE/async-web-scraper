import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


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
        lock = asyncio.Lock()
        last_call_time: float | None = None

        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal last_call_time

            async with lock:
                now = time.monotonic()

                if last_call_time is not None:
                    elapsed = now - last_call_time
                    remaining = min_interval - elapsed

                    if remaining > 0:
                        await asyncio.sleep(remaining)

                last_call_time = time.monotonic()

            return await function(*args, **kwargs)

        return wrapper

    return decorator
