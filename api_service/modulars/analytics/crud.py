from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import ProductTypeWeightRuleUpdate, ProductTypeWeightRuleCreate, ProductMarketSettingsSchema, \
    UpdateMarketSettingsRequest
from models import ProductTypeWeightRule, AttributeBrandRule, AttributeValue, ProductTypeValueMap, ProductMarketSettings


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


async def load_weight_rules(session: AsyncSession):
    rows = await session.execute(
        select(
            ProductTypeWeightRule.product_type_id,
            ProductTypeWeightRule.attr_key_id,
            ProductTypeWeightRule.weight
        )
    )
    return rows.all()


async def load_value_maps(session: AsyncSession):
    rows = await session.execute(
        select(
            ProductTypeValueMap.attr_value_id,
            ProductTypeValueMap.multiplier
        )
    )
    return rows.all()


async def load_brand_overrides(session: AsyncSession):
    rows = await session.execute(
        select(
            AttributeBrandRule.product_type_id,
            AttributeBrandRule.brand_id,
            AttributeBrandRule.attr_key_id,
            AttributeBrandRule.rule_type
        )
    )
    return rows.all()


async def load_value_key_map(session: AsyncSession):
    rows = await session.execute(select(AttributeValue.id, AttributeValue.attr_key_id))
    return rows.all()


async def load_market_settings(session: AsyncSession,
                               path_ids: list[int] | set[int] | None) -> list[ProductMarketSettingsSchema]:
    if not path_ids:
        return []

    stmt = select(ProductMarketSettings).where(ProductMarketSettings.path_id.in_(path_ids))
    rows = (await session.execute(stmt)).scalars().all()

    return [ProductMarketSettingsSchema.model_validate(row) for row in rows]


async def get_or_create_market_setting(session: AsyncSession, path_id: int) -> ProductMarketSettings:
    stmt = select(ProductMarketSettings).where(
        ProductMarketSettings.path_id == path_id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    new_item = ProductMarketSettings(path_id=path_id)
    session.add(new_item)
    await session.flush()
    return new_item


async def update_market_setting(payload: UpdateMarketSettingsRequest,
                                session: AsyncSession) -> ProductMarketSettingsSchema:
    item = await get_or_create_market_setting(session, payload.path_id)
    if payload.market_variance_scale is not None:
        item.market_variance_scale = payload.market_variance_scale

    if payload.market_variance_exponent is not None:
        item.market_variance_exponent = payload.market_variance_exponent
    await session.commit()
    await session.refresh(item)
    return ProductMarketSettingsSchema.model_validate(item)
