import asyncio

import aiohttp


async def fetch_url(url: str, timeout: int = 10) -> str:
    """Fetch a URL asynchronously and return its response body."""
    request_timeout = aiohttp.ClientTimeout(total=timeout)

    async with (
        aiohttp.ClientSession(timeout=request_timeout) as session,
        session.get(url) as response,
    ):
        response.raise_for_status()
        return await response.text()


async def fetch_url_safely(url: str, timeout: int = 10) -> str | None:
    """Fetch a URL, returning None for common request failures."""
    try:
        return await fetch_url(url, timeout)
    except (aiohttp.ClientError, TimeoutError):
        return None


async def fetch_urls(
    urls: list[str],
    timeout: int = 10,
) -> list[str | None]:
    """Fetch multiple URLs concurrently, preserving their input order."""
    tasks = [fetch_url_safely(url, timeout) for url in urls]
    return await asyncio.gather(*tasks)
