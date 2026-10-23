from src.data_extraction import extract_emails, extract_title, transform_emails
from src.http_client import fetch_urls


async def scrape_urls(
    urls: list[str],
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    max_concurrency: int = 10,
    min_request_interval: float = 0.0,
) -> list[dict[str, str | bool | list[str] | None]]:
    """Fetch URLs concurrently and extract useful information from each page."""
    html_pages = await fetch_urls(
        urls,
        timeout=timeout,
        retries=retries,
        retry_delay=retry_delay,
        max_concurrency=max_concurrency,
        min_request_interval=min_request_interval,
    )

    results: list[dict[str, str | bool | list[str] | None]] = []

    for url, html in zip(urls, html_pages, strict=True):
        if html is None:
            results.append(
                {
                    "url": url,
                    "success": False,
                    "title": None,
                    "emails": [],
                }
            )
            continue

        emails = transform_emails(extract_emails(html))

        results.append(
            {
                "url": url,
                "success": True,
                "title": extract_title(html),
                "emails": emails,
            }
        )

    return results
