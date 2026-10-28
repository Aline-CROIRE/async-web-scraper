import asyncio
from contextlib import aclosing

import pytest
from aiohttp import web

from src.async_generators import build_page_result, iter_page_results


@pytest.mark.asyncio
async def test_generator_yields_pages_as_they_complete_with_their_index(
    aiohttp_server,
):
    async def handler(request):
        page = request.match_info["page"]
        if page == "slow":
            await asyncio.sleep(0.2)
        return web.Response(text=f"<title>{page}</title>", content_type="text/html")

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    urls = [
        str(server.make_url("/slow")),
        str(server.make_url("/fast-a")),
        str(server.make_url("/fast-b")),
    ]

    yielded = [item async for item in iter_page_results(urls, max_concurrency=3)]

    # The slow first page finishes last, so it is yielded last.
    assert [index for index, _ in yielded][-1] == 0
    assert sorted(index for index, _ in yielded) == [0, 1, 2]
    for index, result in yielded:
        assert result["url"] == urls[index]
        assert result["success"] is True
    assert {result["title"] for _, result in yielded} == {"slow", "fast-a", "fast-b"}


@pytest.mark.asyncio
async def test_generator_yields_failed_result_for_a_failed_request(aiohttp_server):
    async def handler(request):
        raise web.HTTPNotFound()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)
    url = str(server.make_url("/"))

    results = [
        item async for item in iter_page_results([url], retries=1, retry_delay=0)
    ]

    assert results == [
        (0, {"url": url, "success": False, "title": None, "emails": []}),
    ]


@pytest.mark.asyncio
async def test_generator_handles_empty_url_list():
    results = [item async for item in iter_page_results([])]

    assert results == []


@pytest.mark.asyncio
async def test_generator_extracts_title_and_normalized_emails(aiohttp_server):
    async def handler(request):
        return web.Response(
            text=(
                "<title> Contact Page </title>"
                "<p>INFO@Example.com, sales@example.org, info@example.com</p>"
            ),
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)
    url = str(server.make_url("/"))

    results = [item async for item in iter_page_results([url])]

    assert results == [
        (
            0,
            {
                "url": url,
                "success": True,
                "title": "Contact Page",
                "emails": ["info@example.com", "sales@example.org"],
            },
        ),
    ]


@pytest.mark.asyncio
async def test_stopping_generator_early_cancels_workers_and_closes_session(
    monkeypatch,
):
    blocked_tasks = []
    sessions = []

    async def fake_fetch_once(url, timeout, session):
        sessions.append(session)
        if url == "fast":
            return "<title>Fast</title>"
        blocked_tasks.append(asyncio.current_task())
        await asyncio.Event().wait()

    monkeypatch.setattr("src.http_client._fetch_url_once", fake_fetch_once)

    async with aclosing(
        iter_page_results(["fast", "blocked-1", "blocked-2"], max_concurrency=3)
    ) as results:
        async for index, result in results:
            assert (index, result["title"]) == (0, "Fast")
            break

    # Both still-running requests were cancelled when the consumer stopped.
    assert len(blocked_tasks) == 2
    assert all(task.cancelled() for task in blocked_tasks)
    assert len({id(session) for session in sessions}) == 1
    assert sessions[0].closed


def test_build_page_result_for_failed_fetch():
    assert build_page_result("https://example.com", None) == {
        "url": "https://example.com",
        "success": False,
        "title": None,
        "emails": [],
    }
