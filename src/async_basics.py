import asyncio


async def say_hello():
    """Print a greeting from an asynchronous coroutine."""
    print("Hello from asyncio!")


async def main():
    """Run the coroutine."""
    await say_hello()


if __name__ == "__main__":
    asyncio.run(main())
