import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import URLError
from urllib.request import urlopen

from src.http_client import fetch_url_safely


def _fetch_sync(url: str, timeout: float = 10) -> str | None:
    """Fetch one URL using blocking standard-library HTTP."""
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError, OSError, ValueError):
        return None


def _benchmark_sequential(urls: list[str]) -> dict[str, float | int]:
    """Fetch URLs one after another and measure elapsed time."""
    start = time.perf_counter()
    results = [_fetch_sync(url) for url in urls]
    elapsed = time.perf_counter() - start

    return {
        "elapsed_seconds": round(elapsed, 6),
        "successful_requests": sum(result is not None for result in results),
    }


def _benchmark_threaded(urls: list[str]) -> dict[str, float | int]:
    """Fetch URLs concurrently using a thread pool."""
    start = time.perf_counter()

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(_fetch_sync, urls))

    elapsed = time.perf_counter() - start

    return {
        "elapsed_seconds": round(elapsed, 6),
        "successful_requests": sum(result is not None for result in results),
    }


async def _benchmark_async(urls: list[str]) -> dict[str, float | int]:
    """Fetch URLs concurrently using asyncio and aiohttp."""
    start = time.perf_counter()
    results = await asyncio.gather(*(fetch_url_safely(url, retries=1) for url in urls))
    elapsed = time.perf_counter() - start

    return {
        "elapsed_seconds": round(elapsed, 6),
        "successful_requests": sum(result is not None for result in results),
    }


async def benchmark_fetching(
    urls: list[str],
) -> dict[str, dict[str, float | int]]:
    """Compare sequential, threaded and async fetching."""
    sequential = await asyncio.to_thread(_benchmark_sequential, urls)
    threaded = await asyncio.to_thread(_benchmark_threaded, urls)
    asynchronous = await _benchmark_async(urls)

    return {
        "sequential": sequential,
        "threaded": threaded,
        "async": asynchronous,
    }
