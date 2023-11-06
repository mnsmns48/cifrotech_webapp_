from typing import Dict

from sqlalchemy import select, Result
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
    output = {'product': list(product), 'destination_folder': destination_folder}
    return output


async def get_product(session: AsyncSession, code: int) -> StockTable | None:
    return await session.get(StockTable, code)
