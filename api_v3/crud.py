from sqlalchemy import RowMapping, select, func, case, cast, JSON
from sqlalchemy.ext.asyncio import AsyncSession

from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeKey


async def fetch_products_cursor_paginated(
        session: AsyncSession, path_ids: list[int], cursor: int | None, limit: int) -> list[RowMapping]:
    sub_attrs = (
        select(
            AttributeValue.id.label("attr_id"),
            AttributeValue.value.label("attr_value"),
            AttributeValue.alias.label("attr_alias"),
            AttributeKey.id.label("key_id"),
            AttributeKey.key.label("key_name"),
            AttributeKey.alias.label("key_alias"),
            AttributeOriginValue.origin_id.label("origin_id"),
        )
        .join(AttributeOriginValue, AttributeOriginValue.attr_value_id == AttributeValue.id)
        .join(AttributeKey, AttributeKey.id == AttributeValue.attr_key_id)
        .distinct()
        .subquery()
    )

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
            ProductFeaturesGlobal.id.label("feature_id"),

            func.coalesce(
                func.json_agg(
                    func.json_build_object(
                        "id", sub_attrs.c.attr_id,
                        "key", func.json_build_object(
                            "id", sub_attrs.c.key_id,
                            "key", sub_attrs.c.key_name,
                            "alias", sub_attrs.c.key_alias,
                        ),
                        "value", sub_attrs.c.attr_value,
                        "alias", sub_attrs.c.attr_alias,
                    )
                ).filter(sub_attrs.c.attr_id.isnot(None)),
                cast('[]', JSON)
            ).label("attrs")
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .outerjoin(ProductImage, ProductImage.origin_id == ProductOrigin.origin)
        .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
        .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)

        .outerjoin(sub_attrs, sub_attrs.c.origin_id == ProductOrigin.origin)

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
            ProductFeaturesGlobal.title,
            ProductFeaturesGlobal.id
        )
        .order_by(HUbStock.id.desc())
        .limit(limit)
    )

    execute = await session.execute(stmt)
    rows = list(execute.mappings().all())

    return rows
