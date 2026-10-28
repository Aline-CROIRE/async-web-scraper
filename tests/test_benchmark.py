import asyncio
import json
import time

import pytest
from aiohttp import web

from src.benchmark import (
    METHODS,
    USER_AGENT,
    _fetch_sync,
    benchmark_fetching,
    local_benchmark_server,
    method_order,
)


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


@pytest.mark.asyncio
async def test_concurrent_methods_respect_the_same_limit_and_user_agent(
    aiohttp_server,
):
    active = 0
    max_active = 0
    user_agents = set()

    async def handler(request):
        nonlocal active, max_active
        user_agents.add(request.headers.get("User-Agent"))
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)
    urls = [str(server.make_url(f"/{page}")) for page in range(8)]

    results = await benchmark_fetching(urls, concurrency=3)

    assert all(method["successful_requests"] == 8 for method in results.values())
    assert max_active == 3
    assert user_agents == {USER_AGENT}


@pytest.mark.asyncio
async def test_benchmark_counts_http_errors_as_failures_for_every_method(
    aiohttp_server,
):
    async def handler(request):
        if request.match_info["page"] == "missing":
            raise web.HTTPNotFound()
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)
    urls = [str(server.make_url("/found")), str(server.make_url("/missing"))]

    results = await benchmark_fetching(urls)

    assert {name: m["successful_requests"] for name, m in results.items()} == {
        "sequential": 1,
        "threaded": 1,
        "async": 1,
    }


@pytest.mark.asyncio
async def test_benchmark_records_every_repetition_and_summarizes_them():
    results = await benchmark_fetching([], repetitions=3)

    for method in results.values():
        assert len(method["runs"]) == 3
        assert method["min_seconds"] <= method["elapsed_seconds"]
        assert method["elapsed_seconds"] <= method["max_seconds"]


def test_method_order_rotates_so_each_method_runs_first():
    assert [method_order(repetition)[0] for repetition in range(3)] == [
        "sequential",
        "threaded",
        "async",
    ]
    assert all(sorted(method_order(i)) == sorted(METHODS) for i in range(6))


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"repetitions": 0}, ValueError),
        ({"concurrency": 0}, ValueError),
        ({"repetitions": 1.5}, TypeError),
        ({"concurrency": True}, TypeError),
    ],
)
@pytest.mark.asyncio
async def test_benchmark_rejects_invalid_options(options, error):
    with pytest.raises(error):
        await benchmark_fetching([], **options)


def test_local_server_serves_pages_with_configured_latency():
    with local_benchmark_server(page_count=3, latency=0.05) as urls:
        assert len(urls) == 3
        start = time.perf_counter()
        page = _fetch_sync(urls[1])
        elapsed = time.perf_counter() - start

    assert page == "<title>Benchmark page 1</title>"
    assert elapsed >= 0.045
    # The server is shut down after the with block.
    assert _fetch_sync(urls[1], timeout=1) is None


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"page_count": 0}, ValueError),
        ({"latency": -1}, ValueError),
        ({"latency": float("inf")}, ValueError),
        ({"latency": "fast"}, TypeError),
    ],
)
def test_local_server_rejects_invalid_options(options, error):
    with pytest.raises(error), local_benchmark_server(**options):
        pass


@pytest.mark.asyncio
async def test_local_benchmark_shows_async_and_threads_beating_sequential():
    with local_benchmark_server(page_count=20, latency=0.05) as urls:
        results = await benchmark_fetching(urls, concurrency=10)

    for method in results.values():
        assert method["successful_requests"] == 20

    sequential = results["sequential"]["elapsed_seconds"]
    # 20 pages x 50 ms is at least 1 s one at a time; 10 at once needs ~0.1 s.
    assert sequential >= 1.0
    assert results["threaded"]["elapsed_seconds"] < sequential / 2
    assert results["async"]["elapsed_seconds"] < sequential / 2
