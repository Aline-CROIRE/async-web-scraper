import pytest
from aiohttp import web

from src.async_generators import fetch_urls_as_generator


@pytest.mark.asyncio
async def test_generator_yields_each_response_in_input_order(aiohttp_server):
    async def handler(request):
        return web.Response(text=request.match_info["page"])

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    urls = [
        str(server.make_url("/first")),
        str(server.make_url("/second")),
        str(server.make_url("/third")),
    ]

    results = []

    async for result in fetch_urls_as_generator(urls):
        results.append(result)

    assert results == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_generator_yields_none_for_a_failed_request(aiohttp_server):
    async def handler(request):
        raise web.HTTPNotFound()

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    results = []

    async for result in fetch_urls_as_generator(
        [str(server.make_url("/"))],
        retries=1,
        retry_delay=0,
    ):
        results.append(result)

    assert results == [None]


@pytest.mark.asyncio
async def test_generator_handles_empty_url_list():
    results = []

    async for result in fetch_urls_as_generator([]):
        results.append(result)

    assert results == []
