import asyncio
import time
from itertools import pairwise

import pytest

from src.rate_limit import rate_limit


@pytest.mark.asyncio
async def test_rate_limit_preserves_function_result():
    @rate_limit(min_interval=0)
    async def get_value():
        return "success"

    assert await get_value() == "success"


@pytest.mark.asyncio
async def test_rate_limit_delays_calls():
    call_times = []

    @rate_limit(min_interval=0.05)
    async def record_call():
        call_times.append(time.monotonic())

    await record_call()
    await record_call()

    assert len(call_times) == 2
    assert call_times[1] - call_times[0] >= 0.04


@pytest.mark.asyncio
async def test_rate_limit_rejects_negative_interval():
    with pytest.raises(ValueError, match="min_interval"):
        rate_limit(min_interval=-1)


@pytest.mark.asyncio
async def test_rate_limit_rejects_non_numeric_interval():
    with pytest.raises(TypeError, match="min_interval"):
        rate_limit(min_interval="fast")


@pytest.mark.asyncio
async def test_rate_limit_spaces_out_concurrent_callers():
    start_times = []

    @rate_limit(min_interval=0.03)
    async def record_call(index):
        start_times.append(time.monotonic())
        return index

    results = await asyncio.gather(*(record_call(index) for index in range(5)))

    assert results == [0, 1, 2, 3, 4]
    assert all(later - earlier >= 0.025 for earlier, later in pairwise(start_times))


@pytest.mark.asyncio
async def test_rate_limit_recovers_after_waiting_caller_is_cancelled():
    @rate_limit(min_interval=0.05)
    async def get_value():
        return "success"

    await get_value()
    waiting = asyncio.create_task(get_value())
    await asyncio.sleep(0.01)  # The task is now waiting for its turn.
    waiting.cancel()

    with pytest.raises(asyncio.CancelledError):
        await waiting

    assert await asyncio.wait_for(get_value(), timeout=1) == "success"


@rate_limit(min_interval=0.01)
async def module_level_limited_call():
    return "success"


def test_rate_limit_works_across_separate_event_loops():
    async def burst():
        return await asyncio.gather(*(module_level_limited_call() for _ in range(3)))

    assert asyncio.run(burst()) == ["success"] * 3
    assert asyncio.run(burst()) == ["success"] * 3


def test_rate_limit_rejects_non_async_function():
    with pytest.raises(TypeError, match="async function"):

        @rate_limit(min_interval=0)
        def get_value():
            return "not awaitable"
