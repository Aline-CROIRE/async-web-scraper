import pytest

from src.scraper import scrape_urls


@pytest.mark.asyncio
async def test_scrape_urls_extracts_titles_and_emails(monkeypatch):
    async def fake_fetch_urls(urls, **kwargs):
        return [
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

    monkeypatch.setattr("src.scraper.fetch_urls", fake_fetch_urls)

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
    async def fake_fetch_urls(urls, **kwargs):
        return [None]

    monkeypatch.setattr("src.scraper.fetch_urls", fake_fetch_urls)

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
    async def fake_fetch_urls(urls, **kwargs):
        return []

    monkeypatch.setattr("src.scraper.fetch_urls", fake_fetch_urls)

    assert await scrape_urls([]) == []
