import asyncio

from api_service.routers.vendor import get_parsing_functions


async def main():
    res = await get_parsing_functions()
    print(res)


if __name__ == "__main__":
    asyncio.run(main())
