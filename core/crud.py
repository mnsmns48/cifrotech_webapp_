from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Avail


async def get_directory(session: AsyncSession):
    stmt = select(Avail.type_).group_by('type_')
    result: Result = await session.execute(stmt)
    return result.scalars().all()










async def get_product(session: AsyncSession, code: int) -> Avail | None:
    return await session.get(Avail, code)
