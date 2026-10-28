from collections.abc import Callable
from contextlib import aclosing

from src.async_generators import PageResult, iter_page_results


async def scrape_urls(
    urls: list[str],
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    max_concurrency: int = 10,
    min_request_interval: float = 0.0,
    on_result: Callable[[PageResult], None] | None = None,
) -> list[PageResult]:
    """Fetch URLs concurrently and extract useful information from each page.

    Results are consumed from an async generator as each page finishes;
    ``on_result`` (for example, a progress printer) is called in that
    completion order. The returned list is in the same order as ``urls``.
    """
    results: dict[int, PageResult] = {}

    async with aclosing(
        iter_page_results(
            urls,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            max_concurrency=max_concurrency,
            min_request_interval=min_request_interval,
        )
    ) as page_results:
        async for index, result in page_results:
            results[index] = result
            if on_result is not None:
                on_result(result)

    return [results[index] for index in range(len(urls))]
