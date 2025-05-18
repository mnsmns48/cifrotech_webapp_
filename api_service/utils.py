import asyncio
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

