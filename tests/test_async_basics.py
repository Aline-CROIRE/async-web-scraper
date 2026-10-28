import asyncio
import inspect

import pytest

from src.async_basics import (
    describe_callables,
    greet_async,
    greet_sync,
    main,
    run_concurrently,
    run_sequentially,
    say_hello,
)


@pytest.mark.asyncio
async def test_say_hello(capsys):
    await say_hello()

    captured = capsys.readouterr()
    assert captured.out == "Hello from asyncio!\n"


def test_normal_function_runs_immediately_and_returns_its_value():
    assert not inspect.iscoroutinefunction(greet_sync)
    assert greet_sync("Ada") == "Hello, Ada!"


@pytest.mark.asyncio
async def test_coroutine_function_returns_coroutine_object_that_runs_when_awaited():
    calls = []

    async def record_call():
        calls.append("ran")
        return "done"

    coroutine = record_call()

    assert inspect.iscoroutinefunction(record_call)
    assert inspect.iscoroutine(coroutine)
    assert calls == []  # Calling it did not run the body.

    assert await coroutine == "done"
    assert calls == ["ran"]


@pytest.mark.asyncio
async def test_greet_async_returns_greeting_when_awaited():
    assert await greet_async("Ada") == "Hello, Ada!"


def test_describe_callables_classifies_each_kind():
    assert describe_callables() == {
        "greet_sync is a coroutine function": False,
        "greet_async is a coroutine function": True,
        "greet_sync() returns a coroutine object": False,
        "greet_async() returns a coroutine object": True,
    }


def test_describe_callables_leaves_no_unawaited_coroutine(recwarn):
    describe_callables()

    assert not [w for w in recwarn if "never awaited" in str(w.message)]


def test_asyncio_run_executes_coroutine_from_synchronous_code():
    assert asyncio.run(greet_async("Ada")) == "Hello, Ada!"


@pytest.mark.asyncio
async def test_gather_is_faster_than_sequential_and_keeps_argument_order():
    delays = {"slow": 0.15, "fast": 0.05, "medium": 0.1}

    sequential_results, sequential_time = await run_sequentially(delays)
    concurrent_results, concurrent_time = await run_concurrently(delays)

    assert sequential_results == ["slow", "fast", "medium"]
    assert concurrent_results == ["slow", "fast", "medium"]
    assert sequential_time >= 0.29
    assert concurrent_time < sequential_time - 0.1


def test_main_prints_demonstration(capsys, monkeypatch):
    monkeypatch.setattr(
        "src.async_basics.DEMO_DELAYS", {"page-a": 0.02, "page-b": 0.01}
    )

    asyncio.run(main())

    output = capsys.readouterr().out
    assert "Hello from asyncio!" in output
    assert "greet_async() returns a coroutine object: True" in output
    assert "greet_sync is a coroutine function: False" in output
    assert "sequential:" in output
    assert "gather:" in output
    assert "['page-a', 'page-b']" in output
