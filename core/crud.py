from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import StockTable


async def get_directory(session: AsyncSession, parent: int) -> list[StockTable]:
    stmt = select(StockTable) \
        .where(StockTable.parent == parent).order_by(StockTable.price)
    result: Result = await session.execute(stmt)
    product = result.scalars().all()
    return list(product)


async def get_product(session: AsyncSession, code: int) -> StockTable | None:
    return await session.get(StockTable, code)
