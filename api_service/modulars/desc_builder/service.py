from sqlalchemy import select

from models import DescBuilderFormulaLink


class DescBuilder:
    @staticmethod
    async def fetch_formula_link(session):
        stmt = select(DescBuilderFormulaLink.id).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row is not None
