"""Compare sequential, threaded and async fetching under equivalent conditions."""

import asyncio
import math
import statistics
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from aiohttp import web
from aiohttp.http import SERVER_SOFTWARE

from src.http_client import fetch_urls

METHODS = ("sequential", "threaded", "async")

# aiohttp's default User-Agent; the blocking client sends it too so that
# servers treat every method the same way.
USER_AGENT = SERVER_SOFTWARE

# Ignore proxy environment variables, as aiohttp does by default.
_OPENER = build_opener(ProxyHandler({}))

RunResult = dict[str, float | int]
MethodResult = dict[str, float | int | list[RunResult]]


def _fetch_sync(url: str, timeout: float = 10) -> str | None:
    """Fetch one URL using blocking standard-library HTTP."""
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        # The error holds the open response; close it to avoid a resource leak.
        error.close()
        return None
    except (URLError, HTTPException, TimeoutError, OSError, ValueError):
        return None


def _fetch_sequentially(urls: list[str], timeout: float) -> list[str | None]:
    """Fetch URLs one after another."""
    return [_fetch_sync(url, timeout) for url in urls]


def _fetch_with_threads(
    urls: list[str],
    timeout: float,
    concurrency: int,
) -> list[str | None]:
    """Fetch URLs with at most ``concurrency`` worker threads."""
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        return list(executor.map(lambda url: _fetch_sync(url, timeout), urls))


async def _time_method(
    method: str,
    urls: list[str],
    timeout: float,
    concurrency: int,
) -> RunResult:
    """Run one method once and measure its elapsed time and successes."""
    start = time.perf_counter()

    if method == "sequential":
        pages = await asyncio.to_thread(_fetch_sequentially, urls, timeout)
    elif method == "threaded":
        pages = await asyncio.to_thread(_fetch_with_threads, urls, timeout, concurrency)
    else:
        # The real scraper path: one shared session and bounded workers.
        pages = await fetch_urls(
            urls,
            timeout=timeout,
            retries=1,
            max_concurrency=concurrency,
        )

    elapsed = time.perf_counter() - start

    return {
        "elapsed_seconds": round(elapsed, 6),
        "successful_requests": sum(page is not None for page in pages),
    }


def method_order(repetition: int) -> list[str]:
    """Rotate the running order so no method always benefits from warm caches."""
    shift = repetition % len(METHODS)
    return [*METHODS[shift:], *METHODS[:shift]]


def _summarize(runs: list[RunResult]) -> MethodResult:
    """Reduce repeated runs to a median time, range and worst success count."""
    times = [run["elapsed_seconds"] for run in runs]

    return {
        "elapsed_seconds": round(statistics.median(times), 6),
        "min_seconds": min(times),
        "max_seconds": max(times),
        "successful_requests": min(run["successful_requests"] for run in runs),
        "runs": runs,
    }


def _validate_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be at least 1")


async def benchmark_fetching(
    urls: list[str],
    *,
    repetitions: int = 1,
    concurrency: int = 10,
    timeout: float = 10.0,
) -> dict[str, MethodResult]:
    """Time sequential, threaded and async fetching of the same URLs.

    Every method uses the same timeout, no retries and the same User-Agent,
    and counts only 2xx responses as successful. Threaded and async fetching
    both allow ``concurrency`` requests at once.

    For each method, ``elapsed_seconds`` is the median of ``repetitions``
    runs, and ``successful_requests`` is the lowest count seen in any run.
    """
    _validate_positive_int("repetitions", repetitions)
    _validate_positive_int("concurrency", concurrency)

    runs: dict[str, list[RunResult]] = {method: [] for method in METHODS}

    for repetition in range(repetitions):
        for method in method_order(repetition):
            runs[method].append(await _time_method(method, urls, timeout, concurrency))

    return {method: _summarize(runs[method]) for method in METHODS}


@contextmanager
def local_benchmark_server(
    page_count: int = 25,
    latency: float = 0.1,
) -> Iterator[list[str]]:
    """Serve ``page_count`` local pages that each respond after ``latency`` seconds.

    The server runs on its own event loop in a background thread, so it
    never competes with the client being measured. Yields the page URLs.
    """
    _validate_positive_int("page_count", page_count)
    if isinstance(latency, bool) or not isinstance(latency, (int, float)):
        raise TypeError("latency must be a number")
    if not math.isfinite(latency) or latency < 0:
        raise ValueError("latency must be finite and non-negative")

    async def handle_page(request: web.Request) -> web.Response:
        await asyncio.sleep(latency)
        page = request.match_info["page"]
        return web.Response(
            text=f"<title>Benchmark page {page}</title>",
            content_type="text/html",
        )

    async def start() -> tuple[web.AppRunner, int]:
        app = web.Application()
        app.router.add_get("/pages/{page}", handle_page)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", 0).start()
        return runner, runner.addresses[0][1]

    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=loop.run_forever,
        name="benchmark-server",
        daemon=True,
    )
    thread.start()

    try:
        runner, port = asyncio.run_coroutine_threadsafe(start(), loop).result(10)

        try:
            yield [
                f"http://127.0.0.1:{port}/pages/{page}" for page in range(page_count)
            ]
        finally:
            asyncio.run_coroutine_threadsafe(runner.cleanup(), loop).result(10)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(10)
        loop.close()
