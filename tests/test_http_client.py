import asyncio

import aiohttp
import pytest
from aiohttp import web

from src.http_client import fetch_url, fetch_url_safely, fetch_urls


@pytest.mark.asyncio
async def test_fetch_url_returns_response_body(aiohttp_server):
    async def handler(request):
        return web.Response(text="Hello from the test server!")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url(str(server.make_url("/")))

    assert result == "Hello from the test server!"


@pytest.mark.asyncio
async def test_fetch_url_raises_for_http_error(aiohttp_server):
    async def handler(request):
        raise web.HTTPInternalServerError()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    with pytest.raises(aiohttp.ClientResponseError):
        await fetch_url(
            str(server.make_url("/")),
            retries=1,
            retry_delay=0,
        )


@pytest.mark.asyncio
async def test_fetch_url_safely_returns_none_for_http_error(aiohttp_server):
    async def handler(request):
        raise web.HTTPInternalServerError()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url_safely(
        str(server.make_url("/")),
        retries=1,
        retry_delay=0,
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_urls_returns_multiple_response_bodies(aiohttp_server):
    async def handler(request):
        page = request.match_info["page"]
        return web.Response(text=f"Content for {page}")

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    urls = [
        str(server.make_url("/first")),
        str(server.make_url("/second")),
        str(server.make_url("/third")),
    ]

    results = await fetch_urls(urls)

    assert results == [
        "Content for first",
        "Content for second",
        "Content for third",
    ]


@pytest.mark.asyncio
async def test_fetch_urls_keeps_successful_results_when_one_url_fails(
    aiohttp_server,
):
    async def handler(request):
        page = request.match_info["page"]
        if page == "failure":
            raise web.HTTPInternalServerError()
        return web.Response(text=f"Content for {page}")

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    urls = [
        str(server.make_url("/first")),
        str(server.make_url("/failure")),
        str(server.make_url("/third")),
    ]

    results = await fetch_urls(urls)

    assert results == [
        "Content for first",
        None,
        "Content for third",
    ]


@pytest.mark.asyncio
async def test_fetch_url_safely_returns_none_on_timeout(aiohttp_server):
    async def handler(request):
        await asyncio.sleep(0.2)
        return web.Response(text="Too late")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url_safely(
        str(server.make_url("/")),
        timeout=0.05,
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_url_retries_temporary_server_error(aiohttp_server):
    attempts = 0

    async def handler(request):
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise web.HTTPServiceUnavailable()

        return web.Response(text="Recovered")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url(
        str(server.make_url("/")),
        retries=3,
        retry_delay=0,
    )

    assert result == "Recovered"
    assert attempts == 3


@pytest.mark.asyncio
async def test_fetch_url_does_not_retry_not_found(aiohttp_server):
    attempts = 0

    async def handler(request):
        nonlocal attempts
        attempts += 1
        raise web.HTTPNotFound()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    with pytest.raises(aiohttp.ClientResponseError) as error:
        await fetch_url(
            str(server.make_url("/")),
            retries=3,
            retry_delay=0,
        )

    assert error.value.status == 404
    assert attempts == 1


@pytest.mark.asyncio
async def test_fetch_url_rejects_invalid_retries():
    with pytest.raises(ValueError, match="retries must be at least 1"):
        await fetch_url("https://example.com", retries=0)


@pytest.mark.asyncio
async def test_fetch_url_rejects_negative_retry_delay():
    with pytest.raises(ValueError, match="retry_delay cannot be negative"):
        await fetch_url("https://example.com", retry_delay=-0.1)
