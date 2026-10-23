import asyncio
from itertools import pairwise

import aiohttp
import pytest
from aiohttp import web

from src.http_client import (
    _read_response,
    fetch_url,
    fetch_url_safely,
    fetch_urls,
)


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
async def test_safe_fetch_logs_sanitized_http_failure(aiohttp_server, caplog):
    async def handler(request):
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/missing", handler)
    server = await aiohttp_server(app)
    url = f"{server.make_url('/missing')}?token=private"

    result = await fetch_url_safely(url, retries=1, retry_delay=0)

    assert result is None
    assert "HTTP 404" in caplog.text
    assert str(server.make_url("/")).rstrip("/") in caplog.text
    assert "private" not in caplog.text


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
        retries=1,
        retry_delay=0,
    )

    assert result is None


@pytest.mark.asyncio
async def test_safe_fetch_logs_timeout_and_closes_session(
    aiohttp_server,
    caplog,
    monkeypatch,
):
    async def handler(request):
        await asyncio.sleep(0.2)
        return web.Response(text="Too late")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)
    sessions = []

    async def tracking_read_response(session, url):
        sessions.append(session)
        return await _read_response(session, url)

    monkeypatch.setattr(
        "src.http_client._read_response",
        tracking_read_response,
    )

    result = await fetch_url_safely(
        str(server.make_url("/")),
        timeout=0.03,
        retries=1,
        retry_delay=0,
    )

    assert result is None
    assert "TimeoutError" in caplog.text
    assert str(server.make_url("/")).rstrip("/") in caplog.text
    assert len(sessions) == 1
    assert all(session.closed for session in sessions)


@pytest.mark.asyncio
async def test_fetch_url_retries_after_wait_for_timeout(aiohttp_server):
    attempts = 0

    async def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            await asyncio.sleep(0.1)
        return web.Response(text="Recovered")

    app = web.Application()
    app.router.add_get("/", handler)
    server = await aiohttp_server(app)

    result = await fetch_url(
        str(server.make_url("/")),
        timeout=0.03,
        retries=2,
        retry_delay=0,
    )

    assert result == "Recovered"
    assert attempts == 2


@pytest.mark.asyncio
async def test_fetch_urls_uses_one_session_and_closes_it(monkeypatch):
    sessions = []

    async def fake_fetch_once(url, timeout, session):
        sessions.append(session)
        return url

    monkeypatch.setattr("src.http_client._fetch_url_once", fake_fetch_once)

    assert await fetch_urls(["first", "second"], max_concurrency=2) == [
        "first",
        "second",
    ]

    assert len({id(session) for session in sessions}) == 1
    assert sessions[0].closed


@pytest.mark.asyncio
async def test_fetch_urls_bounds_workers_for_twenty_urls(aiohttp_server):
    active_requests = 0
    maximum_active_requests = 0

    async def handler(request):
        nonlocal active_requests, maximum_active_requests
        page = int(request.match_info["page"])
        active_requests += 1
        maximum_active_requests = max(maximum_active_requests, active_requests)
        await asyncio.sleep((page % 4) * 0.005)
        active_requests -= 1
        if page == 7:
            raise web.HTTPInternalServerError()
        return web.Response(text=str(page))

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)
    urls = [str(server.make_url(f"/{page}")) for page in range(24)]

    results = await fetch_urls(urls, max_concurrency=4, retries=1)

    assert results == [None if page == 7 else str(page) for page in range(24)]
    assert 1 < maximum_active_requests <= 4


@pytest.mark.asyncio
async def test_fetch_urls_rate_limits_requests_retries_and_failures(
    aiohttp_server,
    caplog,
):
    attempts = {}
    request_times = []

    async def handler(request):
        page = request.match_info["page"]
        attempts[page] = attempts.get(page, 0) + 1
        request_times.append(asyncio.get_running_loop().time())
        if page == "retry" and attempts[page] == 1:
            raise web.HTTPServiceUnavailable()
        if page == "fail":
            raise web.HTTPServiceUnavailable()
        return web.Response(text=page)

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    results = await fetch_urls(
        [
            str(server.make_url("/first")),
            str(server.make_url("/retry")),
            str(server.make_url("/third")),
            f"{server.make_url('/fail')}?token=private",
        ],
        max_concurrency=3,
        retries=2,
        retry_delay=0,
        min_request_interval=0.04,
    )

    assert results == ["first", "retry", "third", None]
    assert attempts["fail"] == 2
    assert len(request_times) == 6
    assert all(later - earlier >= 0.03 for earlier, later in pairwise(request_times))
    assert "HTTP 503" in caplog.text
    assert "private" not in caplog.text


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


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
@pytest.mark.asyncio
async def test_fetch_url_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError, match="timeout must be finite"):
        await fetch_url("https://example.com", timeout=timeout)


@pytest.mark.parametrize("timeout", [True, "10"])
@pytest.mark.asyncio
async def test_fetch_url_rejects_non_numeric_timeout(timeout):
    with pytest.raises(TypeError, match="timeout must be a number"):
        await fetch_url("https://example.com", timeout=timeout)


@pytest.mark.parametrize("retries", [True, 1.5, "3"])
@pytest.mark.asyncio
async def test_fetch_url_rejects_non_integer_retries(retries):
    with pytest.raises(TypeError, match="retries must be an integer"):
        await fetch_url("https://example.com", retries=retries)


@pytest.mark.parametrize("retry_delay", [float("inf"), float("nan")])
@pytest.mark.asyncio
async def test_fetch_url_rejects_non_finite_retry_delay(retry_delay):
    with pytest.raises(ValueError, match="retry_delay must be finite"):
        await fetch_url("https://example.com", retry_delay=retry_delay)


@pytest.mark.parametrize("retry_delay", [True, "1"])
@pytest.mark.asyncio
async def test_fetch_url_rejects_non_numeric_retry_delay(retry_delay):
    with pytest.raises(TypeError, match="retry_delay must be a number"):
        await fetch_url("https://example.com", retry_delay=retry_delay)


@pytest.mark.asyncio
async def test_fetch_urls_creates_named_tasks(aiohttp_server, monkeypatch):
    created_tasks = []
    original_create_task = asyncio.create_task

    async def handler(request):
        return web.Response(text=request.match_info["page"])

    app = web.Application()
    app.router.add_get("/{page}", handler)
    server = await aiohttp_server(app)

    def tracking_create_task(coro, **kwargs):
        task = original_create_task(coro, **kwargs)

        if task.get_name().startswith("fetch-worker-"):
            created_tasks.append(task)

        return task

    monkeypatch.setattr(asyncio, "create_task", tracking_create_task)

    urls = [
        str(server.make_url("/first")),
        str(server.make_url("/second")),
    ]

    results = await fetch_urls(urls)

    assert results == ["first", "second"]
    assert [task.get_name() for task in created_tasks] == [
        "fetch-worker-1",
        "fetch-worker-2",
    ]
    assert all(task.done() for task in created_tasks)


@pytest.mark.asyncio
async def test_fetch_urls_returns_empty_list_for_no_urls():
    results = await fetch_urls([])

    assert results == []


@pytest.mark.asyncio
async def test_fetch_urls_cancels_child_tasks_when_cancelled(monkeypatch):
    started = asyncio.Event()
    child_tasks = []
    sessions = []

    async def blocked_fetch(url, timeout, session):
        child_tasks.append(asyncio.current_task())
        sessions.append(session)

        if len(child_tasks) == 2:
            started.set()

        await asyncio.Event().wait()

    monkeypatch.setattr(
        "src.http_client._fetch_url_once",
        blocked_fetch,
    )

    parent_task = asyncio.create_task(
        fetch_urls(["first", "second"], max_concurrency=2)
    )

    await asyncio.wait_for(started.wait(), timeout=1)

    parent_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await parent_task

    assert len(child_tasks) == 2
    assert all(task.cancelled() for task in child_tasks)
    assert len({id(session) for session in sessions}) == 1
    assert sessions[0].closed
