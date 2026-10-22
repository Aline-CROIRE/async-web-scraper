import asyncio
import json

import pytest
from aiohttp import web

from src.benchmark import benchmark_fetching


@pytest.mark.asyncio
async def test_benchmark_reports_all_three_methods(aiohttp_server):
    async def handler(request):
        await asyncio.sleep(0.02)
        return web.Response(text="benchmark response")

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    urls = [
        str(server.make_url("/one")),
        str(server.make_url("/two")),
        str(server.make_url("/three")),
    ]

    results = await benchmark_fetching(urls)

    assert set(results) == {"sequential", "threaded", "async"}
    for method in results.values():
        assert method["elapsed_seconds"] >= 0
        assert method["successful_requests"] == 3


@pytest.mark.asyncio
async def test_benchmark_handles_empty_url_list():
    results = await benchmark_fetching([])

    assert set(results) == {"sequential", "threaded", "async"}
    for method in results.values():
        assert method["elapsed_seconds"] >= 0
        assert method["successful_requests"] == 0


@pytest.mark.asyncio
async def test_benchmark_results_can_be_serialized():
    results = await benchmark_fetching([])

    # Benchmark results should be suitable for JSON output.
    serialized = json.dumps(results)
    assert json.loads(serialized) == results
