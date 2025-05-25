from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Vendor
from models.vendor import Vendor_search_line, Harvest


async def get_vendor_by_url(url: str, session: AsyncSession):
    result = await session.execute(select(Vendor)
                                   .join(Vendor.search_lines)
                                   .where(Vendor_search_line.url == url))
    vendor = result.scalars().first()
    return vendor


async def save_harvest(data: list, session: AsyncSession):
    stmt = insert(Harvest).values(data).on_conflict_do_nothing()
    await session.execute(stmt)
    await session.commit()


async def truncate_harvest(session: AsyncSession) -> None:
    async with session.begin():
        await session.execute(delete(Harvest))
