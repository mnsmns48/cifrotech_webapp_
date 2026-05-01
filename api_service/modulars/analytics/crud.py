from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import ProductTypeWeightRuleUpdate, ProductTypeWeightRuleCreate
from models import ProductTypeWeightRule
from models.analytics import ProductTypeValueMap


async def add_rule_line_db(payload: ProductTypeWeightRuleCreate, session: AsyncSession):
    rule = ProductTypeWeightRule(product_type_id=payload.product_type_id,
                                 attr_key_id=payload.attr_key_id,
                                 weight=payload.weight,
                                 description=payload.description,
                                 is_enabled=payload.is_enabled)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)

    result = await session.execute(
        select(ProductTypeWeightRule).options(selectinload(ProductTypeWeightRule.product_type),
                                              selectinload(ProductTypeWeightRule.attr_key),
                                              selectinload(ProductTypeWeightRule.value_maps)
                                              .selectinload(ProductTypeValueMap.attr_value))
        .where(ProductTypeWeightRule.id == rule.id)
        .order_by(ProductTypeWeightRule.id)
    )
    return result.scalar_one()


async def update_rule_line_db(payload: ProductTypeWeightRuleUpdate,
                              session: AsyncSession) -> ProductTypeWeightRule | None:
    result = await session.execute(select(ProductTypeWeightRule)
                                   .where(ProductTypeWeightRule.id == payload.id)
                                   .options(selectinload(ProductTypeWeightRule.value_maps)))
    rule = result.scalar_one_or_none()
    if rule is None:
        return None

    attr_key_changed = rule.attr_key_id != payload.attr_key_id
    if attr_key_changed:
        await session.execute(
            delete(ProductTypeValueMap)
            .where(ProductTypeValueMap.rule_id == rule.id)
        )
    await session.execute(update(ProductTypeWeightRule)
                          .where(ProductTypeWeightRule.id == payload.id).values(product_type_id=payload.product_type_id,
                                                                                attr_key_id=payload.attr_key_id,
                                                                                weight=payload.weight,
                                                                                description=payload.description,
                                                                                is_enabled=payload.is_enabled))
    await session.commit()
    session.expire_all()

    result = await session.execute(select(ProductTypeWeightRule)
                                   .where(ProductTypeWeightRule.id == payload.id)
                                   .options(
        selectinload(ProductTypeWeightRule.product_type),
        selectinload(ProductTypeWeightRule.attr_key),
        selectinload(ProductTypeWeightRule.value_maps)
        .selectinload(ProductTypeValueMap.attr_value),
    )
                                   .order_by(ProductTypeWeightRule.id)
                                   )
    return result.scalar_one_or_none()
