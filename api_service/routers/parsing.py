import asyncio
from fastapi import APIRouter, Depends
from api_service.schemas import ParsingRequest
from config import redis_session

from parsing.browser import open_page, run_browser

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/start_parsing")
async def go_parsing(data: ParsingRequest, redis=Depends(redis_session)):
    progress_channel = data.progress
    pubsub_obj = redis.pubsub()
    playwright, browser, page = await run_browser()
    await redis.publish(progress_channel, f"Браузер запущен")
    await redis.publish(progress_channel, "data: COUNT=4")
    try:
        await open_page(page=page, url='https://mail.ru')
        await redis.publish(progress_channel, f"mail.ru открыт")
        await open_page(page=page, url='https://ya.ru')
        await redis.publish(progress_channel, f"ya.ru открыт")
        await asyncio.sleep(2)
    finally:
        await redis.publish(progress_channel, "data: END")
        await browser.close()
        await playwright.stop()
        await pubsub_obj.unsubscribe(progress_channel)
        await pubsub_obj.close()
    return {"result": data}
