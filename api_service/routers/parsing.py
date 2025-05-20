import asyncio
import uuid

from fastapi import APIRouter, Depends

from api_service.crud import add_parsing_event
from api_service.schemas import ParsingRequest
from api_users.dependencies.fastapi_users_dep import current_user
from config import redis_session
from engine import db
from parsing.browser import open_page, run_browser

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/give_parsing_id")
async def create_parsing_id(data: ParsingRequest, user=Depends(current_user)):
    progress = str(uuid.uuid4())
    async with db.session_factory() as pg_session:
        pg_session.add({"progress": progress})
        await pg_session.commit()
    return {"progress": progress}


@parsing_router.post("/start_parsing")
async def go_parsing(data: ParsingRequest, redis=Depends(redis_session)):
    progress_channel = f"progress:{data.request}"
    pubsub_obj = redis.pubsub()
    await redis.publish(progress_channel, "data: COUNT=4")
    playwright, browser, page = await run_browser()
    await redis.publish(progress_channel, f"Браузер запущен")
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
