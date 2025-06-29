import asyncio
from datetime import datetime

import aiohttp
from aioboto3 import Session
from aiohttp import ClientSession

from bot.crud_bot import show_day_sales
from config import Settings, settings
from engine import db

image_urls = [
    "https://technosuccess.ru/images/thumbnails/2864/3032/detailed/10904/9269292_0_1737749250.webp",
    "https://technosuccess.ru/images/thumbnails/2000/207/detailed/10904/9269292_1_1737749250.webp",
    "https://technosuccess.ru/images/thumbnails/2000/207/detailed/10904/9269292_2_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/95/2000/detailed/10904/9269292_3_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/95/2000/detailed/10904/9269292_4_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/655/2000/detailed/10904/9269292_5_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/927/2000/detailed/10904/9269292_6_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/655/2000/detailed/10904/9269292_7_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/658/2000/detailed/10904/9269292_8_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/927/2000/detailed/10904/9269292_9_1737749251.webp",
    "https://technosuccess.ru/images/thumbnails/658/2000/detailed/10904/9269292_10_1737749251.webp"
]


async def download_image(session, url, save_path):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(save_path, "wb") as file:
                    file.write(await response.read())
    except Exception as e:
        print(f"Error {url}: {e}")


# async def callable_func_(pic_urls: list, session: ClientSession, origin: str):
#     tasks = list()
#     for url in image_urls:
#         tasks.append(download_image(session, url, f"images/{url.rsplit('/', 1)[1]}"))
#     await asyncio.gather(*tasks)


async def callable_func_():
    await check_s3_connection()


async def check_s3_connection():
    session = Session(
        aws_access_key_id=settings.s3.s3_access_key,
        aws_secret_access_key=settings.s3.s3_secret_access_key,
        region_name=settings.s3.region
    )
    async with session.client('s3', endpoint_url=settings.s3.s3_url) as s3_client:
        try:
            response = await s3_client.list_buckets()
            return response
        except Exception as e:
            print("Ошибка подключения к S3:", e)
            raise e
