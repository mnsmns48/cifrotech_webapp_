import asyncio
import re
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.s3_helper import get_s3_client
from config import redis_session
from engine import db


class AppDependencies:
    def __init__(self,
                 redis_deps=Depends(redis_session),
                 session: AsyncSession = Depends(db.scoped_session_dependency),
                 s3_client=Depends(get_s3_client)):
        self.redis = redis_deps
        self.session = session
        self.s3_client = s3_client


async def update_instance_fields(instance, update_data: dict, session: AsyncSession):
    for key, value in update_data.items():
        setattr(instance, key, value)
    await session.commit()
    await session.refresh(instance)


async def event_stream(coroutine_funcs: list):
    total_tasks = len(coroutine_funcs)
    yield f"data: COUNT={total_tasks}\n\n"
    for coro_fn, *args in coroutine_funcs:
        if asyncio.iscoroutinefunction(coro_fn):
            result = await coro_fn(*args)
            yield f"data: {result.get('msg')}\n\n"
    yield "data: END\n\n"


def normalize_origin(raw_number: str | int) -> Optional[int]:
    only_digits = re.compile(r"\D+")
    if isinstance(raw_number, int):
        return raw_number
    parsed = only_digits.sub("", raw_number)
    return int(parsed) if parsed else None
