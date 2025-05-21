from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_vendor_by_url
from api_service.schemas import ParsingRequest
from config import redis_session
from engine import db

from parsing.browser import run_browser

import importlib

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/start_parsing")
async def go_parsing(data: ParsingRequest,
                     redis=Depends(redis_session),
                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    progress_channel = data.progress
    pubsub_obj = redis.pubsub()
    playwright, browser, page = await run_browser()
    await redis.publish(progress_channel, f"Браузер запущен")
    vendor = await get_vendor_by_url(session=session, url=data.url)
    try:
        module = importlib.import_module(f"parsing.sources.{vendor.function}")
        func = getattr(module, "main_parsing")
        await func(browser, page, progress_channel, redis, data.url)
    finally:
        await redis.publish(progress_channel, "data: END")
        await browser.close()
        await playwright.stop()
        await pubsub_obj.unsubscribe(progress_channel)
        await pubsub_obj.close()
    return {"result": 'ok'}
