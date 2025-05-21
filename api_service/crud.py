from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Vendor
from models.vendor import Vendor_search_line


async def get_vendor_by_url(url: str, session: AsyncSession):
    result = await session.execute(select(Vendor)
                                   .join(Vendor.search_lines)
                                   .where(Vendor_search_line.url == url))
    vendor = result.scalars().first()
    return vendor
