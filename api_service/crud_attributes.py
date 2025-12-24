from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.attributes import AttributeKey


async def fetch_all_attribute_keys(session: AsyncSession):
    execute = await session.execute(select(AttributeKey.key))
    result = list(execute.scalars().all())
    return result
