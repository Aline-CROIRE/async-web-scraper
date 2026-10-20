import aiohttp
import pytest
from aiohttp import web

from src.http_client import fetch_url, fetch_url_safely

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
        return web.Response(status=404, text="Not found")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    with pytest.raises(aiohttp.ClientResponseError):
        await fetch_url(str(server.make_url("/")))


@pytest.mark.asyncio
async def test_fetch_url_safely_returns_none_for_http_error(aiohttp_server):
    async def handler(request):
        return web.Response(status=500, text="Server error")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url_safely(str(server.make_url("/")))

    assert result is None
