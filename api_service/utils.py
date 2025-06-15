import asyncio
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession


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
