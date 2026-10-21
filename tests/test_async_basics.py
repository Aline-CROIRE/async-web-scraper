import pytest

from src.async_basics import say_hello


@pytest.mark.asyncio
async def test_say_hello(capsys):
    await say_hello()

    captured = capsys.readouterr()
    assert captured.out == "Hello from asyncio!\n"
