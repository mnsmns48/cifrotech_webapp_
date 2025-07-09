import asyncio
from datetime import datetime

import aiohttp
import boto3
from aioboto3 import Session
from aiohttp import ClientSession
from botocore.exceptions import NoCredentialsError, EndpointConnectionError, ClientError

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
    list_objects("")


async def check_s3_connection():
    print(repr(settings.s3.s3_access_key))
    try:
        session = boto3.session.Session(
            aws_access_key_id=settings.s3.s3_access_key,
            aws_secret_access_key=settings.s3.s3_secret_access_key,
            region_name=settings.s3.region,
        )
        s3 = session.resource('s3', endpoint_url=settings.s3.s3_url)
        bucket = s3.Bucket(settings.s3.bucket_name)
        objects = list(bucket.objects.limit(1))
        print(f"✅ Успешное подключение к S3 bucket: {settings.s3.bucket_name}")
        return True
    except (NoCredentialsError, EndpointConnectionError):
        print("❌ Ошибка авторизации или подключения к S3")
        return False
    except ClientError as e:
        print(f"❌ Ошибка клиента: {e}")
        return False


def list_objects(prefix: str):
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3.s3_url.rstrip("/"),
        aws_access_key_id=settings.s3.s3_access_key.strip(),
        aws_secret_access_key=settings.s3.s3_secret_access_key.strip(),
        region_name=settings.s3.region
    )

    try:
        resp = s3.list_objects_v2(
            Bucket=settings.s3.bucket_name,
            Prefix=prefix
        )
        contents = resp.get("Contents", [])
        keys = [obj["Key"] for obj in contents]
        print("Found keys:", keys)
        return keys

    except ClientError as e:
        code = e.response["Error"].get("Code")
        print(f"❌ list_objects_v2 failed: {code}")
        return []