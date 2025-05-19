import asyncio
import uuid

from fastapi import APIRouter, Depends

from api_service.schemas import ParsingRequest, StartParsing
from config import redis_session
from parsing.browser import open_page, run_browser

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/give_parsing_id")
async def create_parsing_id(data: ParsingRequest, redis=Depends(redis_session)):
    parsing_id = str(uuid.uuid4())
    progress_channel = f"progress:{parsing_id}"
    pubsub_obj = redis.pubsub()
    await pubsub_obj.subscribe(progress_channel)
    await redis.publish(progress_channel, f"Start parsing")
    return {"parsing_id": parsing_id, 'url': data.url}


@parsing_router.post("/start_parsing")
async def main_parsing(data: StartParsing, redis=Depends(redis_session)):
    progress_channel = f"progress:{data.parsing_id}"
    pubsub_obj = redis.pubsub()
    await redis.publish(progress_channel, "data: COUNT=5")
    playwright, browser, page = await run_browser()
    await redis.publish(progress_channel, f"Браузер запущен")
    try:
        await open_page(page=page, url='https://mail.ru')
        await redis.publish(progress_channel, f"mail.ru открыт")
        await open_page(page=page, url='https://ya.ru')
        await redis.publish(progress_channel, f"ya.ru открыт")
    finally:
        await redis.publish(progress_channel, "data: END")
        await browser.close()
        await playwright.stop()
        await pubsub_obj.unsubscribe(progress_channel)
        await pubsub_obj.close()
    return {"result": data}
