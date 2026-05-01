from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.crud import update_rule_line_db, add_rule_line_db
from api_service.schemas import ProductTypeWeightRuleCreate, ProductTypeWeightRuleUpdate
from models import ProductTypeWeightRule

from sqlalchemy.orm import selectinload

from models.analytics import ProductTypeValueMap


class AnalyticService:
    @staticmethod
    async def fetch_all(session: AsyncSession):
        result = await session.execute(
            select(ProductTypeWeightRule)
            .options(selectinload(ProductTypeWeightRule.product_type),
                     selectinload(ProductTypeWeightRule.attr_key),
                     selectinload(ProductTypeWeightRule.value_maps)
                     .selectinload(ProductTypeValueMap.attr_value))
        )
        return result.scalars().all()

    @staticmethod
    async def add_rule_line(payload: ProductTypeWeightRuleCreate, session: AsyncSession):
        return await add_rule_line_db(payload, session)

    @staticmethod
    async def delete_rule_line(rule_id: int, session: AsyncSession):
        await session.execute(delete(ProductTypeWeightRule).where(ProductTypeWeightRule.id == rule_id))
        await session.commit()
        return {"status": True}

    @staticmethod
    async def update_rule_line(payload: ProductTypeWeightRuleUpdate, session: AsyncSession):
        return await update_rule_line_db(payload, session)

    @staticmethod
    async def toggle_rule_switch(rule_id: int, is_enabled: bool, session: AsyncSession):
        await session.execute(
            update(ProductTypeWeightRule)
            .where(ProductTypeWeightRule.id == rule_id)
            .values(is_enabled=is_enabled)
        )

        await session.commit()

        result = await session.execute(
            select(ProductTypeWeightRule)
            .where(ProductTypeWeightRule.id == rule_id)
            .options(selectinload(ProductTypeWeightRule.product_type),
                     selectinload(ProductTypeWeightRule.attr_key),
                     selectinload(ProductTypeWeightRule.value_maps)
                     .selectinload(ProductTypeValueMap.attr_value))
        )

        return result.scalar_one_or_none()
