from typing import Tuple, Sequence

from sqlalchemy import select, delete, Row
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Vendor
from models.vendor import VendorSearchLine, Harvest, RewardRangeLine, RewardRange, HarvestLine


async def get_vendor_by_url(url: str, session: AsyncSession):
    result = await session.execute(select(Vendor)
                                   .join(Vendor.search_lines)
                                   .where(VendorSearchLine.url == url))
    vendor = result.scalars().first()
    return vendor


async def store_harvest(data: dict, session: AsyncSession) -> int:
    stmt = insert(Harvest).values(**data).returning(Harvest.id)
    result = await session.execute(stmt)
    harvest_id = result.scalar_one()
    await session.commit()
    return harvest_id


async def store_harvest_line(data: list, session: AsyncSession):
    stmt = insert(HarvestLine).values(data).on_conflict_do_nothing()
    await session.execute(stmt)
    await session.commit()


async def delete_harvest_strings_by_vsl_id(session: AsyncSession, vsl_id: int):
    harvest_query = select(Harvest).where(Harvest.vendor_search_line_id == vsl_id)
    harvest_result = await session.execute(harvest_query)
    harvest = harvest_result.scalars().first()
    if not harvest:
        return "Запросов парсинга для этого URL нет"
    await session.delete(harvest)
    await session.commit()
    return "Записи для этого запроса удалены"


async def get_range_rewards(session: AsyncSession, range_id: int = None) -> Sequence[Row[tuple[int, int, bool, int]]]:
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
