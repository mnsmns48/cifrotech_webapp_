from typing import Tuple, Sequence

from sqlalchemy import select, delete, Row
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Vendor
from models.vendor import Vendor_search_line, Harvest, RewardRangeLine, RewardRange


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
    await session.execute(delete(Harvest))
    await session.commit()


async def get_range_rewards(session: AsyncSession, range_id: int=None) -> Sequence[Row[tuple[int, int, bool, int]]]:
    if range_id is None:
        default_range_query = select(RewardRange.id).where(RewardRange.is_default == True)
        default_range = await session.execute(default_range_query)
        range_id = default_range.scalar()
    if range_id is None:
        return []
    query = select(
        RewardRangeLine.line_from, RewardRangeLine.line_to, RewardRangeLine.is_percent, RewardRangeLine.reward
    ).where(RewardRangeLine.range_id == range_id)
    result = await session.execute(query)
    return result.all()