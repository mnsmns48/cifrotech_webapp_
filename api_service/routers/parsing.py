import asyncio
import uuid

from fastapi import APIRouter, Depends

from api_service.crud import add_parsing_event
from api_service.schemas import ParsingRequest, StartParsing, ParsingLogEvent
from api_users.dependencies.fastapi_users_dep import current_user
from config import redis_session
from engine import db
from parsing.browser import open_page, run_browser

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/give_parsing_id")
async def create_parsing_id(data: ParsingRequest, user = Depends(current_user)):
    parsing_id = str(uuid.uuid4())
    log_event_data = ParsingLogEvent(request_id=parsing_id, user=user.id, vendor=data.vendor_id, parsing_title=data.title,
                               parsing_url=data.url, result=False)
    async with db.session_factory() as pg_session:
        await add_parsing_event(parsing_event_data=log_event_data, pg_session=pg_session)
    return {"parsing_id": parsing_id, "url": data.url}


@parsing_router.post("/start_parsing")
async def main_parsing(data: StartParsing, redis=Depends(redis_session)):
    progress_channel = f"progress:{data.parsing_id}"
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
