import asyncio
import inspect
import logging
import math
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (
        TimeoutError,
        ConnectionError,
    ),
    retry_if: Callable[[Exception], bool] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Retry an async function when a selected exception is retryable.

    Only ``Exception`` subclasses can be retried, so cancellation
    (``asyncio.CancelledError``) always stops the function immediately.
    """
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise TypeError("max_attempts must be an integer")

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if isinstance(delay, bool) or not isinstance(delay, (int, float)):
        raise TypeError("delay must be a number")

    if not math.isfinite(delay):
        raise ValueError("delay must be finite")

    if delay < 0:
        raise ValueError("delay cannot be negative")

    if not isinstance(exceptions, tuple):
        raise TypeError("exceptions must be a tuple of exception classes")

    if not exceptions or not all(
        isinstance(exception, type) and issubclass(exception, Exception)
        for exception in exceptions
    ):
        raise ValueError("exceptions must contain exception classes")

    if retry_if is not None and not callable(retry_if):
        raise TypeError("retry_if must be callable")

    def decorator(
        function: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        if not inspect.iscoroutinefunction(function):
            raise TypeError("retry can only decorate an async function")

        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, max_attempts + 1):
                try:
                    return await function(*args, **kwargs)
                except exceptions as error:
                    if retry_if is not None and not retry_if(error):
                        raise

                    if attempt == max_attempts:
                        logger.error(
                            "Function %s failed after %d attempts (%s)",
                            function.__name__,
                            attempt,
                            type(error).__name__,
                        )
                        raise

                    logger.warning(
                        "Function %s failed on attempt %d of %d; retrying",
                        function.__name__,
                        attempt,
                        max_attempts,
                    )
                    await asyncio.sleep(delay)

            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator
