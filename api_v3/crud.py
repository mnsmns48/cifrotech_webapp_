from sqlalchemy import RowMapping, select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import BrandModel, TypeModel
from api_v3.schemas import CategoryItem
from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeLink, AttributeBrandRule, ProductType, ProductBrand, HUbMenuLevel
from models.attributes import OverrideType


async def fetch_rows(session: AsyncSession, stmt):
    rows = (await session.execute(stmt)).mappings().all()
    return rows


async def fetch_pics_map(session: AsyncSession, origins: list[int]) -> dict[int, RowMapping]:
    if not origins:
        return {}

    pics_stmt = (select(ProductImage.origin_id,
                        func.array_agg(ProductImage.key)
                        .filter(ProductImage.key.isnot(None))
                        .label("pics"),
                        func.max(case((ProductImage.is_preview.is_(True), ProductImage.key))).label("preview"))
                 .where(ProductImage.origin_id.in_(origins))
                 .group_by(ProductImage.origin_id))
    result = await session.execute(pics_stmt)
    rows = result.mappings().all()

    pics_map = dict()
    for row in rows:
        pics_map[row["origin_id"]] = row

    return pics_map


async def fetch_products_cursor_paginated(session: AsyncSession,
                                          path_ids: list[int],
                                          cursor: int | None,
                                          limit: int) -> list[RowMapping]:
    base_stmt = (select(HUbStock.id,
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
        base_stmt = base_stmt.where(HUbStock.id < cursor)

    base_stmt = base_stmt.order_by(HUbStock.id.desc()).limit(limit)

    base_rows = await fetch_rows(session, base_stmt)

    origins = [row["origin"] for row in base_rows]
    pics_map: dict[int, RowMapping] = await fetch_pics_map(session, origins)

    result = list()
    for row in base_rows:
        origin = row["origin"]
        pics_info = pics_map.get(origin, {})
        result.append({**row, "pics": pics_info.get("pics", []), "preview": pics_info.get("preview")})

    result.sort(key=lambda x: x["output_price"] if x["output_price"] is not None else float("inf"))

    return result


async def get_product_full(session: AsyncSession, origin: int):
    stmt = (
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

    result = await session.execute(stmt)
    product_origin = result.unique().scalar_one_or_none()
    return product_origin


async def get_feature_with_type_brand(session, feature_id: int):
    result = await session.execute(select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == feature_id)
                                   .options(selectinload(ProductFeaturesGlobal.type),
                                            selectinload(ProductFeaturesGlobal.brand)))
    return result.scalar_one_or_none()


async def get_menu_level(session, level_id: int):
    return await session.scalar(select(HUbMenuLevel).where(HUbMenuLevel.id == level_id))


async def fetch_category_items(path_ids: set[int], session: AsyncSession) -> list[CategoryItem]:
    if not path_ids:
        return []

    base_stmt = (
        select(HUbStock.id.label("hubstock_id"),
               HUbStock.origin.label("origin"),
               HUbStock.warranty,
               HUbStock.output_price,
               ProductOrigin.title,
               ProductFeaturesLink.feature_id,
               ProductFeaturesGlobal.title.label("model"),
               ProductFeaturesGlobal.type_id.label("type_id"),
               ProductFeaturesGlobal.brand_id.label("brand_id"),
               ProductType.id.label("ptype_id"),
               ProductType.type.label("ptype_title"),
               ProductBrand.id.label("pbrand_id"),
               ProductBrand.brand.label("pbrand_title"),
               HUbStock.updated_at,
               ).join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
        .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
        .outerjoin(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
        .outerjoin(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
        .where(HUbStock.path_id.in_(path_ids), ProductOrigin.is_deleted.is_(False)))

    base_rows = await fetch_rows(session, base_stmt)

    origins = [row["origin"] for row in base_rows]
    pics_map: dict[int, RowMapping] = await fetch_pics_map(session, origins)

    items: list[CategoryItem] = list()

    for row in base_rows:
        origin = row["origin"]
        pics_info = pics_map.get(origin, {})

        type_model = None
        if row["ptype_id"] is not None:
            type_model = TypeModel(id=row["ptype_id"], type=row["ptype_title"])

        brand_model = None
        if row["pbrand_id"] is not None:
            brand_model = BrandModel(id=row["pbrand_id"], brand=row["pbrand_title"])

        items.append(CategoryItem(hubstock_id=row["hubstock_id"],
                                  origin=origin,
                                  warranty=row["warranty"],
                                  output_price=row["output_price"],
                                  title=row["title"],
                                  model=row["model"],
                                  feature_id=row["feature_id"],
                                  type=type_model,
                                  brand=brand_model,
                                  pics=pics_info.get("pics", []) or [],
                                  preview=pics_info.get("preview"),
                                  updated_at=row["updated_at"]))
    return items


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
