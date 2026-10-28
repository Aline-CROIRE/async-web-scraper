import asyncio
import logging
import math
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit

import aiohttp

from src.rate_limit import rate_limit
from src.retry import retry

logger = logging.getLogger(__name__)

RequestAttempt = Callable[
    [str, float, aiohttp.ClientSession | None],
    Awaitable[str],
]


def _validate_request_options(
    timeout: float,
    retries: int,
    retry_delay: float,
) -> None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise TypeError("timeout must be a number")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and greater than zero")
    if isinstance(retries, bool) or not isinstance(retries, int):
        raise TypeError("retries must be an integer")
    if retries < 1:
        raise ValueError("retries must be at least 1")
    if isinstance(retry_delay, bool) or not isinstance(retry_delay, (int, float)):
        raise TypeError("retry_delay must be a number")
    if not math.isfinite(retry_delay):
        raise ValueError("retry_delay must be finite")
    if retry_delay < 0:
        raise ValueError("retry_delay cannot be negative")


def _is_retryable_http_error(error: Exception) -> bool:
    """Return whether an HTTP response error represents a server failure."""
    return isinstance(error, aiohttp.ClientResponseError) and error.status >= 500


def _should_retry(error: Exception) -> bool:
    """Retry network failures and HTTP server errors, but not client errors."""
    if isinstance(error, aiohttp.ClientResponseError):
        return _is_retryable_http_error(error)

    return True


def _safe_url_for_logging(url: str) -> str:
    """Return the URL origin without credentials, paths, queries, or fragments."""
    try:
        parsed_url = urlsplit(url)
        if parsed_url.scheme and parsed_url.hostname:
            hostname = parsed_url.hostname
            if ":" in hostname:
                hostname = f"[{hostname}]"
            if parsed_url.port is not None:
                hostname = f"{hostname}:{parsed_url.port}"
            return urlunsplit((parsed_url.scheme, hostname, "", "", ""))
    except ValueError:
        pass

    return "<invalid URL>"


async def _read_response(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=None),
    ) as response:
        response.raise_for_status()
        # Real pages often contain bytes that do not match their declared
        # charset; replace them so one malformed page cannot fail a batch.
        return await response.text(errors="replace")


async def _fetch_url_once(
    url: str,
    timeout: float = 10,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Fetch one response, with asyncio.wait_for bounding the full operation."""
    if session is None:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=None),
        ) as owned_session:
            return await asyncio.wait_for(
                _read_response(owned_session, url),
                timeout=timeout,
            )

    return await asyncio.wait_for(
        _read_response(session, url),
        timeout=timeout,
    )


async def _fetch_with_retries(
    url: str,
    timeout: float,
    retries: int,
    retry_delay: float,
    session: aiohttp.ClientSession | None,
    request_attempt: RequestAttempt,
) -> str:
    """Apply the existing retry policy to a shared or standalone request attempt."""
    _validate_request_options(timeout, retries, retry_delay)

    retryable_exceptions = (
        TimeoutError,
        aiohttp.ClientConnectionError,
        aiohttp.ClientResponseError,
    )

    @retry(
        max_attempts=retries,
        delay=retry_delay,
        exceptions=retryable_exceptions,
        retry_if=_should_retry,
    )
    async def fetch_with_retries() -> str:
        return await request_attempt(url, timeout, session)

    return await fetch_with_retries()


async def _fetch_safely(
    url: str,
    timeout: float,
    retries: int,
    retry_delay: float,
    session: aiohttp.ClientSession | None,
    request_attempt: RequestAttempt,
) -> str | None:
    try:
        return await _fetch_with_retries(
            url,
            timeout,
            retries,
            retry_delay,
            session,
            request_attempt,
        )
    except (aiohttp.ClientError, TimeoutError, ConnectionError) as error:
        safe_url = _safe_url_for_logging(url)
        if isinstance(error, aiohttp.ClientResponseError):
            failure = f"HTTP {error.status}"
        elif isinstance(error, TimeoutError):
            failure = "TimeoutError"
        else:
            failure = type(error).__name__
        logger.warning("Request to %s failed after retries: %s", safe_url, failure)
        return None


async def fetch_url(
    url: str,
    timeout: float = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    *,
    min_request_interval: float = 0.0,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Fetch a URL with retries and optional pacing between request attempts."""
    request_attempt = rate_limit(min_request_interval)(_fetch_url_once)
    return await _fetch_with_retries(
        url,
        timeout,
        retries,
        retry_delay,
        session,
        request_attempt,
    )


async def fetch_url_safely(
    url: str,
    timeout: float = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    *,
    min_request_interval: float = 0.0,
    session: aiohttp.ClientSession | None = None,
) -> str | None:
    """Fetch a URL, returning None and logging common request failures."""
    request_attempt = rate_limit(min_request_interval)(_fetch_url_once)
    return await _fetch_safely(
        url,
        timeout,
        retries,
        retry_delay,
        session,
        request_attempt,
    )


async def fetch_urls(
    urls: list[str],
    timeout: float = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    max_concurrency: int = 10,
    min_request_interval: float = 0.0,
) -> list[str | None]:
    """Fetch URLs with bounded workers, preserving input order."""
    _validate_request_options(timeout, retries, retry_delay)
    if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int):
        raise TypeError("max_concurrency must be an integer")
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")

    request_attempt = rate_limit(min_request_interval)(_fetch_url_once)
    if not urls:
        return []

    results: list[str | None] = [None] * len(urls)
    url_iterator = iter(enumerate(urls))
    worker_count = min(max_concurrency, len(urls))

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=None),
        connector=aiohttp.TCPConnector(limit=max_concurrency),
    ) as session:

        async def worker() -> None:
            while item := next(url_iterator, None):
                index, url = item
                results[index] = await _fetch_safely(
                    url,
                    timeout,
                    retries,
                    retry_delay,
                    session,
                    request_attempt,
                )

        tasks = [
            asyncio.create_task(worker(), name=f"fetch-worker-{index}")
            for index in range(1, worker_count + 1)
        ]

        try:
            await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    return results
