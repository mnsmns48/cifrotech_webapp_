import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession


async def update_instance_fields(instance, update_data: dict, session: AsyncSession):
    for key, value in update_data.items():
        setattr(instance, key, value)
    await session.commit()
    await session.refresh(instance)


async def event_stream(coroutines: list):
    total_tasks = len(coroutines)
    yield f"data: COUNT={total_tasks}\n\n"
    for coro in coroutines:
        result = await coro()
        yield f"data: {result}\n\n"
    yield "data: END\n\n"


async def coro_1():
    await asyncio.sleep(2)
    return '1!'


async def coro_2():
    await asyncio.sleep(2)
    return '2!'


async def coro_3():
    await asyncio.sleep(2)
    return '3!'


async def coro_4():
    await asyncio.sleep(2)
    return '4!'


async def coro_5():
    await asyncio.sleep(2)
    return '5!'


async def coro_6():
    await asyncio.sleep(2)
    return '6!'
