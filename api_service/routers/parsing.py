import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_vendor_by_url
from api_service.schemas import ParsingRequest
from config import redis_session
from engine import db
import importlib

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/start_parsing")
async def go_parsing(data: ParsingRequest,
                     redis=Depends(redis_session),
                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    progress_channel = data.progress
    pubsub_obj = redis.pubsub()
    vendor = await get_vendor_by_url(session=session, url=data.url)
    try:
        module = importlib.import_module(f"parsing.sources.{vendor.function}")
        func = getattr(module, "parsing_logic")
        fetch_data: dict = await func(progress_channel, redis, data.url, vendor, session)
        if len(fetch_data.get('data')) > 0:
            fetch_data.update({'is_ok': True})
    finally:
        await redis.publish(progress_channel, "data: COUNT=1")
        await asyncio.sleep(0.5)
        await redis.publish(progress_channel, "END")
        await pubsub_obj.unsubscribe(progress_channel)
        await pubsub_obj.close()
    return fetch_data
