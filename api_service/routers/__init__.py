import asyncio

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio.client import PubSub
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from api_service.routers.printer import printer_router
from api_service.routers.vendor import vendor_router
from api_service.routers.vendor_search_line import vendor_search_line_router
from api_users.dependencies.fastapi_users_dep import current_super_user
from api_service.routers.parsing import parsing_router
from config import redis_session
from engine import db

service_router = APIRouter(prefix="/service", dependencies=[Depends(current_super_user)])
service_router.include_router(printer_router)
service_router.include_router(vendor_router)
service_router.include_router(vendor_search_line_router)

service_router.include_router(parsing_router)

progress_router = APIRouter()


@progress_router.get("/progress/{progress_channel_id}")
async def get_progress(request: str, redis=Depends(redis_session),
                       pg_session: AsyncSession = Depends(db.session_dependency)):
    channel = f"progress:{request}"
    active_channels = await redis.pubsub_channels()
    if channel not in active_channels:
        raise HTTPException(status_code=404, detail=f"Я такого канала не знаю")
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    async def event_generator(pubsub_obj: PubSub):
        try:
            while True:
                message = await pubsub_obj.get_message(ignore_subscribe_messages=True, timeout=10.0)
                if message:
                    data = message["data"]
                    yield f"data: {data}\n\n"
                    if data == "END":
                        break
                else:
                    await asyncio.sleep(0.1)
        finally:
            await pubsub_obj.unsubscribe(channel)
            await pubsub_obj.close()

    return StreamingResponse(event_generator(pubsub), media_type="text/event-stream")
