import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio.client import PubSub
from starlette.responses import StreamingResponse

from api_users.dependencies.fastapi_users_dep import current_user
from config import redis_session

progress_router = APIRouter()

async def generate_progress_id(redis, user):
    if not user:
        raise HTTPException(status_code=403, detail="No access")
    progress = str(uuid.uuid4())
    await redis.setex(progress, 60, "")
    return {"result": progress}


@progress_router.get("/give_progress_line")
async def create_parsing_id(redis=Depends(redis_session), user=Depends(current_user)):
    return await generate_progress_id(redis, user)


@progress_router.get("/progress/{progress}")
async def get_progress(progress: str, redis=Depends(redis_session)):
    pubsub = redis.pubsub()
    await pubsub.subscribe(progress)

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
            await pubsub_obj.unsubscribe(progress)
            await pubsub_obj.close()

    return StreamingResponse(event_generator(pubsub), media_type="text/event-stream")