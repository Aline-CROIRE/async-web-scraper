
import pytest
from aiohttp import web

from src.http_client import fetch_url


@pytest.mark.asyncio
async def test_fetch_url_returns_response_body(aiohttp_server):
    async def handler(request):
        return web.Response(text="Hello from the test server!")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url(str(server.make_url("/")))

    assert result == "Hello from the test server!"
