from sqlalchemy import RowMapping, select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeKey


async def fetch_products_cursor_paginated(session: AsyncSession, path_ids: list[int],
                                          cursor: int | None, limit: int) -> list[RowMapping]:
    base = (select(HUbStock.id,
                   HUbStock.origin,
                   HUbStock.warranty,
                   HUbStock.output_price,
                   ProductOrigin.title,
                   ProductFeaturesGlobal.id.label("feature_id"),
                   ProductFeaturesGlobal.title.label("model"))
            .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
            .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
            .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
            .where(HUbStock.path_id.in_(path_ids), ProductOrigin.is_deleted.is_(False)))

    if cursor is not None:
        base = base.where(HUbStock.id < cursor)

    base = base.order_by(HUbStock.id.desc()).limit(limit)
    base_rows = (await session.execute(base)).mappings().all()

    if not base_rows:
        return []

    origins = [row["origin"] for row in base_rows]

    pics_stmt = (select(ProductImage.origin_id, func.array_agg(ProductImage.key)
                        .filter(ProductImage.key.isnot(None))
                        .label("pics"),
                        func.max(case((ProductImage.is_preview.is_(True), ProductImage.key))).label("preview"),
                        )
                 .where(ProductImage.origin_id.in_(origins))
                 .group_by(ProductImage.origin_id)
                 )
    pics_map = {row["origin_id"]: row for row in (await session.execute(pics_stmt)).mappings().all()}

    result = list()
    for row in base_rows:
        origin = row["origin"]

        pics_info = pics_map.get(origin, {})

        result.append({
            **row, "pics": pics_info.get("pics", []), "preview": pics_info.get("preview")
        })

    result.sort(key=lambda x: x["output_price"] if x["output_price"] is not None else float("inf"))

    return result


async def get_product_full(session, origin: int):
    result = await session.execute(
        select(ProductOrigin)
        .where(ProductOrigin.origin == origin)
        .options(
            selectinload(ProductOrigin.stocks),
            selectinload(ProductOrigin.features)
            .selectinload(ProductFeaturesLink.origin_rel),
            selectinload(ProductOrigin.images),
            selectinload(ProductOrigin.attribute_values)
            .selectinload(AttributeOriginValue.attr_value)
            .selectinload(AttributeValue.attr_key),
        )
    )
    product_origin = result.scalar_one_or_none()
    return product_origin


async def get_feature_with_type_brand(session, feature_id: int):
    result = await session.execute(
        select(ProductFeaturesGlobal)
        .where(ProductFeaturesGlobal.id == feature_id)
        .options(
            selectinload(ProductFeaturesGlobal.type),
            selectinload(ProductFeaturesGlobal.brand),
        )
    )
    return result.scalar_one_or_none()


async def get_menu_level(session, level_id: int):
    from models import HUbMenuLevel
    return await session.scalar(select(HUbMenuLevel).where(HUbMenuLevel.id == level_id))
