from sqlalchemy import RowMapping, select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.s3_helper import get_url_from_s3
from api_service.schemas import BrandModel, TypeModel
from api_v3.schemas import CategoryItem
from models import HUbStock, ProductOrigin, ProductImage, ProductFeaturesLink, ProductFeaturesGlobal, AttributeValue, \
    AttributeOriginValue, AttributeLink, AttributeBrandRule, ProductType, ProductBrand, HUbMenuLevel
from models.attributes import OverrideType, AttributeKey


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

    base_stmt = (select(HUbStock.id.label("hubstock_id"),
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
                        )
    .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
    .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
    .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
    .outerjoin(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
    .outerjoin(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
    .where(
        HUbStock.path_id.in_(path_ids),
        ProductOrigin.is_deleted.is_(False))
    )

    base_rows = await fetch_rows(session, base_stmt)

    origins = [row["origin"] for row in base_rows]
    pics_map: dict[int, RowMapping] = await fetch_pics_map(session, origins)

    q_origin_values = (select(AttributeOriginValue.origin_id,
                              AttributeOriginValue.attr_value_id).where(AttributeOriginValue.origin_id.in_(origins)))
    origin_value_rows = await fetch_rows(session, q_origin_values)

    origin_to_values: dict[int, list[int]] = dict()
    for row in origin_value_rows:
        origin_to_values.setdefault(row["origin_id"], []).append(row["attr_value_id"])

    all_attr_value_ids = {row["attr_value_id"] for row in origin_value_rows}
    if all_attr_value_ids:
        q_values = (
            select(AttributeValue.id,
                   AttributeValue.attr_key_id)
            .where(AttributeValue.id.in_(all_attr_value_ids))
        )
        value_rows = await fetch_rows(session, q_values)
    else:
        value_rows = []

    value_to_key: dict[int, int] = {row["id"]: row["attr_key_id"] for row in value_rows}

    all_attr_key_ids = {row["attr_key_id"] for row in value_rows}
    if all_attr_key_ids:
        q_keys = (
            select(AttributeKey.id,
                   AttributeKey.key)
            .where(AttributeKey.id.in_(all_attr_key_ids))
        )
        key_rows = await fetch_rows(session, q_keys)
    else:
        key_rows = []

    key_id_to_key: dict[int, str] = {
        row["id"]: row["key"] for row in key_rows
    }

    origin_attr_values: dict[int, dict[str, list[int]]] = {}

    for origin_id, value_ids in origin_to_values.items():
        kv: dict[str, list[int]] = {}

        for val_id in value_ids:
            key_id = value_to_key.get(val_id)
            if key_id is None:
                continue

            key_str = key_id_to_key.get(key_id)
            if key_str is None:
                continue

            kv.setdefault(key_str, []).append(val_id)

        origin_attr_values[origin_id] = kv

    items: list[CategoryItem] = list()

    for row in base_rows:
        origin = row["origin"]
        pics_info = pics_map.get(origin, {})

        raw_pics = pics_info.get("pics", []) or []
        raw_preview = pics_info.get("preview")

        pics = get_url_from_s3(raw_pics, path=str(origin)) if raw_pics else []
        preview = get_url_from_s3(raw_preview, path=str(origin)) if raw_preview else None

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
                                  pics=pics,
                                  preview=preview,
                                  updated_at=row["updated_at"],
                                  attr_values=origin_attr_values.get(origin, {})))

    return items


async def fetch_base_attrs(product_type_ids: set[int], session: AsyncSession) -> set[int]:
    if not product_type_ids:
        return set()

    query = (select(AttributeLink.product_type_id, AttributeLink.attr_key_id)
             .where(AttributeLink.product_type_id.in_(product_type_ids)))

    rows = await session.execute(query)
    type_to_attrs: dict[int, set[int]] = {}

    for pt_id, attr_key_id in rows:
        type_to_attrs.setdefault(pt_id, set()).add(attr_key_id)

    if not type_to_attrs:
        return set()

    attr_sets = list(type_to_attrs.values())
    common_attrs = attr_sets[0]

    for attrs in attr_sets[1:]:
        common_attrs &= attrs

    return common_attrs


async def fetch_brand_rules(product_type_ids: set[int],
                            brand_ids: set[int], session: AsyncSession) -> dict[int, dict[str, set[int]]]:
    rules: dict[int, dict[str, set[int]]] = dict()

    if not product_type_ids or not brand_ids:
        return rules

    query = (select(AttributeBrandRule.brand_id,
                    AttributeBrandRule.attr_key_id,
                    AttributeBrandRule.rule_type)
             .where(AttributeBrandRule.product_type_id.in_(product_type_ids),
                    AttributeBrandRule.brand_id.in_(brand_ids)))

    rows = await session.execute(query)

    for brand_id, attr_key_id, rule_type in rows:
        if brand_id not in rules:
            rules[brand_id] = {"include": set(), "exclude": set()}

        if rule_type == OverrideType.include:
            rules[brand_id]["include"].add(attr_key_id)
        else:
            rules[brand_id]["exclude"].add(attr_key_id)

    return rules
