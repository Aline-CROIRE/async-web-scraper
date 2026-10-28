"""asyncio fundamentals: functions vs coroutines, asyncio.run and asyncio.gather.

Run ``python -m src.async_basics`` to see the demonstration.
"""

import asyncio
import inspect
import time

DEMO_DELAYS = {"page-a": 0.3, "page-b": 0.1, "page-c": 0.2}


def greet_sync(name: str) -> str:
    """A normal function: calling it runs the body and returns the value."""
    return f"Hello, {name}!"


async def greet_async(name: str) -> str:
    """A coroutine function: calling it returns a coroutine object instead.

    The body only runs when the coroutine object is awaited or scheduled
    on an event loop.
    """
    return f"Hello, {name}!"


async def say_hello() -> None:
    """Print a greeting from an asynchronous coroutine."""
    print("Hello from asyncio!")


def describe_callables() -> dict[str, bool]:
    """Use inspect to show how functions, coroutine functions and coroutines differ."""
    coroutine = greet_async("inspect")

    try:
        return {
            "greet_sync is a coroutine function": inspect.iscoroutinefunction(
                greet_sync
            ),
            "greet_async is a coroutine function": inspect.iscoroutinefunction(
                greet_async
            ),
            "greet_sync() returns a coroutine object": inspect.iscoroutine(
                greet_sync("inspect")
            ),
            "greet_async() returns a coroutine object": inspect.iscoroutine(coroutine),
        }
    finally:
        # Never awaited on purpose; closing it avoids a "never awaited" warning.
        coroutine.close()


async def simulated_request(name: str, delay: float) -> str:
    """Wait like a network request would, without blocking the event loop."""
    await asyncio.sleep(delay)
    return name


async def run_sequentially(delays: dict[str, float]) -> tuple[list[str], float]:
    """Await each request in turn: total time is roughly the sum of the delays."""
    start = time.perf_counter()
    results = [await simulated_request(name, delay) for name, delay in delays.items()]
    return results, time.perf_counter() - start


async def run_concurrently(delays: dict[str, float]) -> tuple[list[str], float]:
    """Run requests together with gather: total time is roughly the longest delay."""
    start = time.perf_counter()
    results = await asyncio.gather(
        *(simulated_request(name, delay) for name, delay in delays.items())
    )
    return results, time.perf_counter() - start


async def main() -> None:
    """Print a short tour of the asyncio fundamentals used by the scraper."""
    await say_hello()

    print("\n1. Functions, coroutine functions and coroutine objects")
    for description, value in describe_callables().items():
        print(f"   {description}: {value}")

    print("\n2. Awaiting one at a time vs asyncio.gather")
    sequential_results, sequential_time = await run_sequentially(DEMO_DELAYS)
    concurrent_results, concurrent_time = await run_concurrently(DEMO_DELAYS)
    print(f"   sequential: {sequential_time:.2f}s -> {sequential_results}")
    print(f"   gather:     {concurrent_time:.2f}s -> {concurrent_results}")
    print("   gather returns results in argument order, not completion order.")


if __name__ == "__main__":
    # asyncio.run creates the event loop, runs main() to completion, then closes it.
    asyncio.run(main())
