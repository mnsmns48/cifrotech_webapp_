from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.crud import update_rule_line_db, add_rule_line_db
from api_service.schemas import ProductTypeWeightRuleCreate, ProductTypeWeightRuleUpdate, \
    ProductTypeValueMapCreateSchema
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

    @staticmethod
    async def fetch_value_map(rule_id: int, session: AsyncSession):
        result = await session.execute(
            select(ProductTypeValueMap)
            .where(ProductTypeValueMap.rule_id == rule_id)
            .options(
                selectinload(ProductTypeValueMap.attr_value)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def create_value_map_line(payload: ProductTypeValueMapCreateSchema, session: AsyncSession):
        stmt = (
            insert(ProductTypeValueMap)
            .values([{"rule_id": payload.rule_id,
                      "attr_value_id": attr_value_id,
                      "multiplier": payload.multiplier}
                     for attr_value_id in payload.attr_value_ids
                     ])
            .returning(ProductTypeValueMap)
        )

        result = await session.execute(stmt)
        await session.commit()
        return result.scalars().all()
