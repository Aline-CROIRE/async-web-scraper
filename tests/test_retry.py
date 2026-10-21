import asyncio

import pytest

from src.retry import retry


@pytest.mark.asyncio
async def test_retry_returns_result_when_function_succeeds():
    @retry(max_attempts=3, delay=0)
    async def fetch_data():
        return "success"

    result = await fetch_data()

    assert result == "success"


@pytest.mark.asyncio
async def test_retry_succeeds_after_temporary_failures():
    attempts = 0

    @retry(max_attempts=3, delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise TimeoutError("Temporary timeout")

        return "success"

    result = await fetch_data()

    assert result == "success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_succeeds_after_connection_failure():
    attempts = 0

    @retry(max_attempts=3, delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise ConnectionError("Temporary connection failure")

        return "success"

    result = await fetch_data()

    assert result == "success"
    assert attempts == 2


@pytest.mark.asyncio
async def test_retry_raises_after_maximum_attempts():
    attempts = 0

    @retry(max_attempts=3, delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        raise TimeoutError("Still timing out")

    with pytest.raises(TimeoutError, match="Still timing out"):
        await fetch_data()

    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_does_not_retry_unexpected_exception():
    attempts = 0

    @retry(max_attempts=3, delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        raise ValueError("Invalid data")

    with pytest.raises(ValueError, match="Invalid data"):
        await fetch_data()

    assert attempts == 1


@pytest.mark.asyncio
async def test_retry_filter_can_stop_retries():
    attempts = 0

    @retry(
        max_attempts=3,
        delay=0,
        retry_if=lambda error: "temporary" in str(error),
    )
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        raise TimeoutError("Permanent failure")

    with pytest.raises(TimeoutError, match="Permanent failure"):
        await fetch_data()

    assert attempts == 1


@pytest.mark.asyncio
async def test_retry_waits_without_blocking_event_loop():
    completed = False

    @retry(max_attempts=2, delay=0.05)
    async def fetch_data():
        raise TimeoutError("Temporary timeout")

    async def other_task():
        nonlocal completed
        await asyncio.sleep(0.01)
        completed = True

    results = await asyncio.gather(
        asyncio.create_task(fetch_data(), name="retrying-fetch"),
        asyncio.create_task(other_task(), name="independent-task"),
        return_exceptions=True,
    )

    assert isinstance(results[0], TimeoutError)
    assert results[1] is None
    assert completed is True


@pytest.mark.parametrize("max_attempts", [0, -1])
def test_retry_rejects_invalid_max_attempts(max_attempts):
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        retry(max_attempts=max_attempts)


@pytest.mark.parametrize("delay", [-0.1, -1])
def test_retry_rejects_negative_delay(delay):
    with pytest.raises(ValueError, match="delay cannot be negative"):
        retry(delay=delay)


@pytest.mark.parametrize("exceptions", [(), (1,)])
def test_retry_rejects_invalid_exceptions(exceptions):
    with pytest.raises(
        ValueError,
        match="exceptions must contain exception classes",
    ):
        retry(exceptions=exceptions)
