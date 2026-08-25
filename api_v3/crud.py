from typing import List, Dict

from sqlalchemy import RowMapping, select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.schemas.desc_builder import BlockResponse
from api_v3.schemas import HubProductSchemeExtV3
from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeLink, AttributeBrandRule
from models.attributes import OverrideType


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


# async def fetch_origins(path_ids: set[int], session: AsyncSession) -> set[int]:
#     q = select(HUbStock.origin).where(HUbStock.path_id.in_(path_ids))
#     rows = await session.execute(q)
#     return {row[0] for row in rows}
#
#
# async def fetch_feature_ids(origin_ids: set[int], session: AsyncSession) -> set[int]:
#     if not origin_ids:
#         return set()
#
#     q = select(ProductFeaturesLink.feature_id).where(ProductFeaturesLink.origin.in_(origin_ids))
#     rows = await session.execute(q)
#     return {row[0] for row in rows}
#
#
# async def fetch_types_brands(feature_ids: set[int], session: AsyncSession) -> tuple[set[int], set[int]]:
#     if not feature_ids:
#         return set(), set()
#
#     q = select(ProductFeaturesGlobal.type_id.label("type_id"),
#                ProductFeaturesGlobal.brand_id.label("brand_id")
#                ).where(ProductFeaturesGlobal.id.in_(feature_ids))
#
#     rows = await session.execute(q)
#
#     product_type_ids = set()
#     brand_ids = set()
#
#     for row in rows:
#         product_type_ids.add(row.type_id)
#         brand_ids.add(row.brand_id)
#
#     return product_type_ids, brand_ids



async def fetch_category_feature_data(
    path_ids: set[int],
    session: AsyncSession
) -> tuple[set[int], set[int], set[int], set[int]]:
    """
    Возвращает origin_ids, feature_ids, product_type_ids, brand_ids
    одним SQL-запросом.
    """

    if not path_ids:
        return set(), set(), set(), set()

    stmt = (
        select(
            HUbStock.origin.label("origin"),
            ProductFeaturesLink.feature_id.label("feature_id"),
            ProductFeaturesGlobal.type_id.label("type_id"),
            ProductFeaturesGlobal.brand_id.label("brand_id"),
        )
        .join(ProductFeaturesLink, ProductFeaturesLink.origin == HUbStock.origin)
        .join(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
        .where(HUbStock.path_id.in_(path_ids))
    )

    rows = (await session.execute(stmt)).mappings().all()

    origin_ids: set[int] = set()
    feature_ids: set[int] = set()
    product_type_ids: set[int] = set()
    brand_ids: set[int] = set()

    for row in rows:
        origin_ids.add(row["origin"])
        feature_ids.add(row["feature_id"])
        product_type_ids.add(row["type_id"])
        brand_ids.add(row["brand_id"])

    return origin_ids, feature_ids, product_type_ids, brand_ids


async def fetch_base_attrs(product_type_ids: set[int], session: AsyncSession) -> set[int]:
    if not product_type_ids:
        return set()

    attr_sets = list()

    for pt_id in product_type_ids:
        q = select(AttributeLink.attr_key_id).where(AttributeLink.product_type_id == pt_id)
        rows = await session.execute(q)
        attr_sets.append({row[0] for row in rows})

    if not attr_sets:
        return set()

    common_attrs = attr_sets[0]

    for attrs in attr_sets[1:]:
        common_attrs &= attrs

    return common_attrs


async def fetch_brand_rules(product_type_ids: set[int], brand_ids: set[int],
                            session: AsyncSession) -> dict[int, dict[str, set[int]]]:
    rules: dict[int, dict[str, set[int]]] = dict()

    if not product_type_ids or not brand_ids:
        return rules

    q = select(AttributeBrandRule.brand_id,
               AttributeBrandRule.attr_key_id,
               AttributeBrandRule.rule_type).where(AttributeBrandRule.product_type_id.in_(product_type_ids),
                                                   AttributeBrandRule.brand_id.in_(brand_ids))
    rows = await session.execute(q)

    for brand_id, attr_key_id, rule_type in rows:
        if brand_id not in rules:
            rules[brand_id] = {"include": set(), "exclude": set()}

        if rule_type == OverrideType.include:
            rules[brand_id]["include"].add(attr_key_id)
        else:
            rules[brand_id]["exclude"].add(attr_key_id)

    return rules


async def fetch_products(origin_ids: set[int], specs_map: Dict[int, List[BlockResponse]], session: AsyncSession):
    if not origin_ids:
        return []

    stmt = (
        select(ProductOrigin)
        .where(ProductOrigin.origin.in_(origin_ids))
        .options(
            selectinload(ProductOrigin.images),
            selectinload(ProductOrigin.features),
        )
    )
    rows = await session.execute(stmt)
    origin_objects = rows.scalars().all()

    origin_to_feature = await DescBuilder.resolve_feature_ids_by_origins(list(origin_ids), session)

    products = []

    for obj in origin_objects:
        fid = origin_to_feature.get(obj.origin)
        short_specs = specs_map.get(fid)

        products.append(
            HubProductSchemeExtV3(
                id=obj.id,
                origin=obj.origin,
                warranty=obj.warranty,
                output_price=obj.output_price,
                title=obj.title,
                pics=obj.pics,
                preview=obj.preview,
                model=obj.model,
                short_specs=short_specs,
            )
        )

    return products
