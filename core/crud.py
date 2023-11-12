from typing import Dict, Tuple, Any

from sqlalchemy import select, Result, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
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
