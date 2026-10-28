from collections.abc import AsyncGenerator
from contextlib import aclosing

from src.data_extraction import extract_emails, extract_title, transform_emails
from src.http_client import iter_fetch_results

PageResult = dict[str, str | bool | list[str] | None]


def build_page_result(url: str, html: str | None) -> PageResult:
    """Turn one fetched page into the result structure saved as JSON."""
    if html is None:
        return {
            "url": url,
            "success": False,
            "title": None,
            "emails": [],
        }

    return {
        "url": url,
        "success": True,
        "title": extract_title(html),
        "emails": transform_emails(extract_emails(html)),
    }


async def iter_page_results(
    urls: list[str],
    timeout: float = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    max_concurrency: int = 10,
    min_request_interval: float = 0.0,
) -> AsyncGenerator[tuple[int, PageResult], None]:
    """Yield ``(index, result)`` for each page as soon as it is fetched and processed.

    Pages arrive in completion order; ``index`` is the page's position in
    ``urls`` so callers can rebuild the original order.
    """
    async with aclosing(
        iter_fetch_results(
            urls,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            max_concurrency=max_concurrency,
            min_request_interval=min_request_interval,
        )
    ) as fetched:
        async for page in fetched:
            yield page.index, build_page_result(page.url, page.html)
