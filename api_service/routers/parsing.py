import asyncio
import uuid

from fastapi import APIRouter, Depends

from api_service.schemas import ParsingRequest, StartParsing
from config import redis_session

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/give_parsing_id")
async def create_parsing_id(data: ParsingRequest):
    return {"parsing_id": str(uuid.uuid4()), 'url': data.url}


@parsing_router.post("/start_parsing")
async def main_parsing(data: StartParsing, redis=Depends(redis_session)):
    progress_channel = f"progress:{data.parsing_id}"
    for i in range(1, 150):
        await asyncio.sleep(3)
        await redis.publish(progress_channel, f"WORK {i} DONE")
    return {"result": data}
