from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ProductTypeWeightRule


class AnalyticService:
    @staticmethod
    async def fetch_all(session: AsyncSession):
        result = await session.execute(select(ProductTypeWeightRule))
        return result.scalars().all()


