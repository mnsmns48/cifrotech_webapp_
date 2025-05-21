import asyncio

from playwright.async_api import Browser, Page
from redis.asyncio import Redis


async def main_parsing(browser: Browser,
                       page: Page,
                       progress_channel: str,
                       redis: Redis,
                       url: str):
    pubsub_obj = redis.pubsub()
    await redis.publish(progress_channel, "data: COUNT=2")
    await asyncio.sleep(3)
    await redis.publish(progress_channel, "data: я открылся из функции")
    await asyncio.sleep(1)