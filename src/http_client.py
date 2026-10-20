
import aiohttp


async def fetch_url(url: str, timeout: int = 10) -> str:
    """Fetch a URL asynchronously and return its response body."""
    request_timeout = aiohttp.ClientTimeout(total=timeout)

    async with aiohttp.ClientSession(timeout=request_timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
