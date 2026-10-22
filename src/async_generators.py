from collections.abc import AsyncGenerator

from src.http_client import fetch_url_safely


async def fetch_urls_as_generator(
    urls: list[str],
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> AsyncGenerator[str | None, None]:
    """Fetch URLs sequentially and yield each result asynchronously."""
    for url in urls:
        result = await fetch_url_safely(
            url,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
        )
        yield result
