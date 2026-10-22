import time

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
