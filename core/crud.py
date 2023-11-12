from typing import Dict, Any

from sqlalchemy import select, Result, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from core.description.description_models import s_main, display, energy, camera, performance
from core.models import StockTable


async def get_directory(session: AsyncSession, parent: int) -> Dict[str, list]:
    destination_folder = bool()
    stmt = (
        select(StockTable).where(StockTable.parent == parent).order_by(StockTable.price)
    )
    result: Result = await session.execute(stmt)
    product = tuple(result.scalars().all())
    for line in product:
        destination_folder = False if line.code < 1000 else True
    output = {'product_list': list(product), 'destination_folder': destination_folder}
    return output


async def get_product(session: AsyncSession, code: int) -> StockTable | None:
    return await session.get(StockTable, code)


async def get_products_in_parent(session: AsyncSession, parent: int) -> tuple[Row | RowMapping | Any, ...]:
    subquery = select(StockTable.code).where(StockTable.parent == parent)
    stmt = select(StockTable).where(StockTable.parent.in_(subquery)).order_by(StockTable.price)
    result: Result = await session.execute(stmt)
    product = tuple(result.scalars().all())
    return product


#
async def get_description(session: AsyncSession, model: str):
    stmt = select(
        s_main.c.title,
        s_main.c.release_date,
        s_main.c.category,
        display.c.d_size,
        display.c.display_type,
        display.c.refresh_rate,
        display.c.resolution,
        energy.c.capacity,
        energy.c.max_charge_power,
        energy.c.fast_charging,
        camera.c.lenses,
        camera.c.megapixels_front,
        performance.c.storage_size,
        performance.c.ram_size,
        performance.c.chipset,
        performance.c.total_score,
        s_main.c.advantage,
        s_main.c.disadvantage) \
        .where(
        (s_main.c.title == model) &
        (s_main.c.title == display.c.title) &
        (s_main.c.title == energy.c.title) &
        (s_main.c.title == camera.c.title) &
        (s_main.c.title == performance.c.title)
    )
    result: Result = await session.execute(stmt)
    desc = result.scalars().all()
    return desc
