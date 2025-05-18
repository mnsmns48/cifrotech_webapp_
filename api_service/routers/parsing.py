import uuid

from fastapi import APIRouter, Depends

from api_service.schemas import ParsingRequest
from config import redis_session

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/give_parsing_id")
async def create_parsing_id(data: ParsingRequest):
    return {"parsing_id": str(uuid.uuid4()), 'url': data.url}
