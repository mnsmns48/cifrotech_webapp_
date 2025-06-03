import asyncio
from func import callable_func_


async def main():
    await callable_func_()


if __name__ == "__main__":
    asyncio.run(main())
