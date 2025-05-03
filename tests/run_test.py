import asyncio

from tests.func import callable_func


async def main():
    await callable_func()


if __name__ == "__main__":
    asyncio.run(main())
