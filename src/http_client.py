import asyncio

import aiohttp

from src.retry import retry


def _is_retryable_http_error(error: Exception) -> bool:
    """Return whether an HTTP response error represents a server failure."""
    return isinstance(error, aiohttp.ClientResponseError) and error.status >= 500


def _should_retry(error: Exception) -> bool:
    """Retry network failures and HTTP server errors, but not client errors."""
    if isinstance(error, aiohttp.ClientResponseError):
        return _is_retryable_http_error(error)

    return True


async def _fetch_url_once(url: str, timeout: int = 10) -> str:
    """Make one HTTP request and return its response body."""
    request_timeout = aiohttp.ClientTimeout(total=timeout)

    async with (
        aiohttp.ClientSession(timeout=request_timeout) as session,
        session.get(url) as response,
    ):
        response.raise_for_status()
        return await response.text()


async def fetch_url(
    url: str,
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> str:
    """Fetch a URL, retrying temporary network and server failures."""
    if retries < 1:
        raise ValueError("retries must be at least 1")

    if retry_delay < 0:
        raise ValueError("retry_delay cannot be negative")

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
        return await _fetch_url_once(url, timeout)

    return await fetch_with_retries()


async def fetch_url_safely(
    url: str,
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> str | None:
    """Fetch a URL, returning None for common request failures."""
    try:
        return await fetch_url(url, timeout, retries, retry_delay)
    except (aiohttp.ClientError, TimeoutError, ConnectionError):
        return None


async def fetch_urls(
    urls: list[str],
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> list[str | None]:
    """Fetch multiple URLs concurrently, preserving their input order."""
    tasks = [fetch_url_safely(url, timeout, retries, retry_delay) for url in urls]
    return await asyncio.gather(*tasks)
