from sqlalchemy import RowMapping, select, func, case, cast, JSON
from sqlalchemy.ext.asyncio import AsyncSession

from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeKey


async def fetch_products_cursor_paginated(
        session: AsyncSession,
        path_ids: list[int],
        cursor: int | None,
        limit: int
) -> list[RowMapping]:

    # --- 1. Основная таблица ---
    base = (
        select(
            HUbStock.id,
            HUbStock.origin,
            HUbStock.warranty,
            HUbStock.output_price,
            ProductOrigin.title,
            ProductFeaturesGlobal.id.label("feature_id"),
            ProductFeaturesGlobal.title.label("model"),
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
        .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
        .where(
            HUbStock.path_id.in_(path_ids),
            ProductOrigin.is_deleted.is_(False)
        )
    )

    if cursor is not None:
        base = base.where(HUbStock.id < cursor)

    base = base.order_by(HUbStock.id.desc()).limit(limit)
    base_rows = (await session.execute(base)).mappings().all()

    if not base_rows:
        return []

    origins = [row["origin"] for row in base_rows]

    # --- 2. Картинки ---
    pics_stmt = (
        select(
            ProductImage.origin_id,
            func.array_agg(ProductImage.key)
                .filter(ProductImage.key.isnot(None))
                .label("pics"),
            func.max(
                case((ProductImage.is_preview.is_(True), ProductImage.key))
            ).label("preview"),
        )
        .where(ProductImage.origin_id.in_(origins))
        .group_by(ProductImage.origin_id)
    )
    pics_map = {row["origin_id"]: row for row in (await session.execute(pics_stmt)).mappings().all()}

    # --- 3. Атрибуты ---
    attrs_stmt = (
        select(
            AttributeOriginValue.origin_id,
            func.json_agg(
                func.json_build_object(
                    "id", AttributeValue.id,
                    "key", func.json_build_object(
                        "id", AttributeKey.id,
                        "key", AttributeKey.key,
                        "alias", AttributeKey.alias,
                    ),
                    "value", AttributeValue.value,
                    "alias", AttributeValue.alias,
                )
            ).filter(AttributeValue.id.isnot(None)).label("attrs")
        )
        .join(AttributeValue, AttributeValue.id == AttributeOriginValue.attr_value_id)
        .join(AttributeKey, AttributeKey.id == AttributeValue.attr_key_id)
        .where(AttributeOriginValue.origin_id.in_(origins))
        .group_by(AttributeOriginValue.origin_id)
    )
    attrs_map = {row["origin_id"]: row["attrs"] for row in (await session.execute(attrs_stmt)).mappings().all()}

    # --- 4. Собираем финальный результат ---
    result = []
    for row in base_rows:
        origin = row["origin"]

        pics_info = pics_map.get(origin, {})
        attrs_info = attrs_map.get(origin, [])

        result.append({
            **row,
            "pics": pics_info.get("pics", []),
            "preview": pics_info.get("preview"),
            "attrs": attrs_info,
        })

    return result
