import random

from fastapi_cache.decorator import cache
from sqlalchemy import RowMapping, select, func, case, cast, JSON
from sqlalchemy.ext.asyncio import AsyncSession

from config import cache_key_builder
from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeKey


@cache(expire=60, key_builder=cache_key_builder)
async def fetch_products_cursor_paginated(
        session: AsyncSession, path_ids: list[int], cursor: int | None, limit: int) -> list[RowMapping]:
    stmt = (
        select(
            HUbStock.id,
            HUbStock.origin,
            HUbStock.warranty,
            HUbStock.output_price,
            ProductOrigin.title,
            func.array_agg(ProductImage.key).filter(ProductImage.key.isnot(None)).label("pics"),
            func.max(case((ProductImage.is_preview.is_(True), ProductImage.key))).label("preview"),
            func.max(ProductFeaturesGlobal.title).label("model"),
            func.coalesce(
                func.json_agg(
                    func.json_build_object(
                        "id", AttributeValue.id,
                        "key", func.json_build_object(
                            "id", AttributeKey.id,
                            "key", AttributeKey.key,
                            "alias", AttributeKey.alias,
                        ),
                        "value", AttributeValue.value,
                        "alias", AttributeValue.alias
                    )
                ).filter(AttributeValue.id.isnot(None)),
                cast('[]', JSON)
            ).label("attrs")
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .outerjoin(ProductImage, ProductImage.origin_id == ProductOrigin.origin)
        .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
        .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
        .outerjoin(AttributeOriginValue, AttributeOriginValue.origin_id == ProductOrigin.origin)
        .outerjoin(AttributeValue, AttributeValue.id == AttributeOriginValue.attr_value_id)
        .outerjoin(AttributeKey, AttributeKey.id == AttributeValue.attr_key_id)
        .where(
            HUbStock.path_id.in_(path_ids),
            ProductOrigin.is_deleted.is_(False)
        )
    )

    if cursor is not None:
        stmt = stmt.where(HUbStock.id < cursor)

    stmt = (
        stmt.group_by(
            HUbStock.id,
            ProductOrigin.title,
            ProductFeaturesGlobal.title
        )
        .order_by(HUbStock.id.desc())
        .limit(limit)
    )

    execute = await session.execute(stmt)
    rows = list(execute.mappings().all())

    return rows
