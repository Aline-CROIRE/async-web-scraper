import asyncio
import logging
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
    """Retry an async function when a selected exception is retryable."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if delay < 0:
        raise ValueError("delay cannot be negative")

    if not exceptions or not all(
        isinstance(exception, type) and issubclass(exception, Exception)
        for exception in exceptions
    ):
        raise ValueError("exceptions must contain exception classes")

    def decorator(
        function: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
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
