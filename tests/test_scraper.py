import pytest

from src.http_client import FetchResult
from src.scraper import scrape_urls


def fake_fetch_results(pages):
    """Build a fake iter_fetch_results that yields pages in reverse order."""

    async def fake_iter_fetch_results(urls, **kwargs):
        # Completing in reverse proves scrape_urls restores input order.
        for index in reversed(range(len(urls))):
            yield FetchResult(index, urls[index], pages[index])

    return fake_iter_fetch_results


@pytest.mark.asyncio
async def test_scrape_urls_extracts_titles_and_emails(monkeypatch):
    pages = [
        """
        <html>
            <title> Example Page </title>
            <p>Contact us at INFO@example.com</p>
            <p>Another contact: hello@example.org</p>
            <p>Duplicate: info@example.com</p>
        </html>
        """,
        "<html><title>Second Page</title></html>",
    ]

    monkeypatch.setattr(
        "src.async_generators.iter_fetch_results",
        fake_fetch_results(pages),
    )

    urls = ["https://example.com", "https://example.org"]
    results = await scrape_urls(urls)

    assert len(results) == 2
    assert results[0] == {
        "url": "https://example.com",
        "success": True,
        "title": "Example Page",
        "emails": ["info@example.com", "hello@example.org"],
    }
    assert results[1] == {
        "url": "https://example.org",
        "success": True,
        "title": "Second Page",
        "emails": [],
    }


@pytest.mark.asyncio
async def test_scrape_urls_records_failed_fetch(monkeypatch):
    monkeypatch.setattr(
        "src.async_generators.iter_fetch_results",
        fake_fetch_results([None]),
    )

    results = await scrape_urls(["https://unavailable.example"])

    assert results == [
        {
            "url": "https://unavailable.example",
            "success": False,
            "title": None,
            "emails": [],
        }
    ]


@pytest.mark.asyncio
async def test_scrape_urls_handles_empty_list(monkeypatch):
    monkeypatch.setattr(
        "src.async_generators.iter_fetch_results",
        fake_fetch_results([]),
    )

    assert await scrape_urls([]) == []


@pytest.mark.asyncio
async def test_scrape_urls_reports_each_result_as_it_completes(monkeypatch):
    pages = ["<title>A</title>", None, "<title>C</title>"]
    monkeypatch.setattr(
        "src.async_generators.iter_fetch_results",
        fake_fetch_results(pages),
    )
    urls = ["https://a.example", "https://b.example", "https://c.example"]
    reported = []

    results = await scrape_urls(urls, on_result=reported.append)

    # Callback sees completion order; the returned list keeps input order.
    assert [result["url"] for result in reported] == list(reversed(urls))
    assert [result["url"] for result in results] == urls
    assert [result["success"] for result in results] == [True, False, True]
