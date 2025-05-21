import asyncio
import os

from api_service.routers.vendor import get_parsing_functions


async def main():
    this_file_name = os.path.basename(__file__).rsplit('.', 1)[0]
    print(this_file_name)


if __name__ == "__main__":
    asyncio.run(main())
