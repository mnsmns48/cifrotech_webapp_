from typing import Optional

from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.s3_helper import get_url_from_s3
from api_service.schemas import AttributeKeyValueSchema, AttributeKey, BrandModel, TypeModel
from api_service.schemas.attribute_schemas import AttributeKeySchema, AttributeValueSchema
from api_service.schemas.features_schemas import FeatureInnerRow, FeatureCategoryScheme, FeatureProductScheme

from api_v3.crud import get_feature_with_type_brand, fetch_base_rows, fetch_pics_map, fetch_origin_value_rows, \
    fetch_attribute_values, fetch_attribute_keys
from api_v3.menu_tree import MenuTree
from api_v3.schemas import HubLevelRouteV3, CategoryItem, AttributeIndex
from cache import CacheManager
from cache.keys.features import feature_key
from cache.settings import cache_ttl


def collect_descendants(tree: dict[int, list[int]], node_id: int) -> set[int]:
    result = {node_id}
    children = tree.get(node_id, [])
    for child in children:
        result.update(collect_descendants(tree, child))
    return result


def build_cursor_response(rows: list[RowMapping], limit: int):
    if not rows:
        return None, False

    last_id = rows[-1]["id"]
    has_more = len(rows) == limit
    next_cursor = last_id if has_more else None

    return next_cursor, has_more


async def build_route(tree: MenuTree, leaf_id: int) -> list[HubLevelRouteV3]:
    levels = await tree.load_levels_cached()
    id_map = {lvl.id: lvl for lvl in levels}

    route: list[HubLevelRouteV3] = list()
    current = id_map.get(leaf_id)

    while current:
        route.append(HubLevelRouteV3(path_id=current.id, label=current.label, slug=current.slug))
        if current.parent_id == 0 or current.parent_id == current.id:
            break

        current = id_map.get(current.parent_id)

    route.reverse()
    return route


def build_images(origin_obj):
    images = origin_obj.images
    pics_keys = [img.key for img in images]
    preview_key = next((img.key for img in images if img.is_preview), None)
    pics = get_url_from_s3(pics_keys, str(origin_obj.origin)) if pics_keys else None
    preview = get_url_from_s3(preview_key, str(origin_obj.origin)) if preview_key else None

    return pics, preview


def build_attrs(origin_obj):
    attrs = list()
    for ov in origin_obj.attribute_values:
        attr_value = ov.attr_value
        attr_key = attr_value.attr_key
        attrs.append(
            AttributeKeyValueSchema(id=attr_value.id,
                                    key=AttributeKey(id=attr_key.id,
                                                     key=attr_key.key,
                                                     alias=attr_key.alias),
                                    value=attr_value.value,
                                    alias=attr_value.alias,
                                    )
        )
    return attrs


def build_pros_cons(feature):
    if not feature.pros_cons:
        return None

    return {"advantage": feature.pros_cons.get("advantage", []),
            "disadvantage": feature.pros_cons.get("disadvantage", [])}


def build_full_specs(feature):
    info = feature.info
    if not info:
        return None

    categories = list()
    for item in info:
        for title, params in item.items():
            rows = [FeatureInnerRow(param=k, value=v) for k, v in params.items()]
            categories.append(FeatureCategoryScheme(title=title, rows=rows))

    return FeatureProductScheme(features_id=feature.id, features=categories)


async def build_feature_data(session: AsyncSession, cache: CacheManager, origin_obj):
    if not origin_obj.features:
        return None, None, None, None, None

    pf_link = origin_obj.features[0]
    feature = await get_feature_with_type_brand(session, pf_link.feature_id)
    if not feature:
        return None, None, None, None, None

    type_obj = TypeModel(id=feature.type.id, type=feature.type.type)
    brand_obj = BrandModel(id=feature.brand.id, brand=feature.brand.brand)

    key = feature_key(feature.id)
    cached = await cache.get(key)

    if cached:
        full_specs_data = cached.get("full_specs")
        full_specs = FeatureProductScheme.model_validate(full_specs_data) if full_specs_data else None
        pros_cons = cached.get("pros_cons")

    else:
        full_specs = build_full_specs(feature)
        pros_cons = build_pros_cons(feature)
        await cache.set(key, {"full_specs": full_specs.model_dump() if full_specs else None,
                              "pros_cons": pros_cons.model_dump() if hasattr(pros_cons, "model_dump") else pros_cons,
                              },
                        ttl=cache_ttl.product_info)
    short_specs_map = await DescBuilder.get_short_specs_bulk(feature_ids=[feature.id], session=session,
                                                             cache=cache)
    short_specs = short_specs_map.get(feature.id)

    return type_obj, brand_obj, full_specs, pros_cons, short_specs


def build_origin_attr_values(origin_value_rows: list[RowMapping], value_map: dict[int, tuple[int, str, Optional[str]]],
                             key_map: dict[int, tuple[str, Optional[str]]]) -> dict[int, dict[str, list[int]]]:
    origin_attr_values: dict[int, dict[str, list[int]]] = dict()

    for row in origin_value_rows:
        origin_id = row["origin_id"]
        val_id = row["attr_value_id"]

        key_id = value_map.get(val_id, (None, None, None))[0]
        if key_id is None:
            continue

        key_str, _ = key_map.get(key_id, (None, None))
        if key_str is None:
            continue

        origin_attr_values.setdefault(origin_id, {}).setdefault(key_str, []).append(val_id)

    return origin_attr_values


def build_attribute_index(value_map: dict[int, tuple[int, str, Optional[str]]],
                          key_map: dict[int, tuple[str, Optional[str]]]) -> AttributeIndex:
    attribute_index_items: dict[int, AttributeKeySchema] = dict()

    for key_id, (key_str, key_alias) in key_map.items():
        values: list[AttributeValueSchema] = list()

        for val_id, (v_key_id, v_value, v_alias) in value_map.items():
            if v_key_id == key_id:
                values.append(AttributeValueSchema(id=val_id, value=v_value, alias=v_alias))

        attribute_index_items[key_id] = AttributeKeySchema(key=key_str,
                                                           alias=key_alias or key_str,
                                                           values=values)

    return AttributeIndex(items=attribute_index_items)


def build_category_items(base_rows: list[RowMapping], pics_map: dict[int, RowMapping],
                         origin_attr_values: dict[int, dict[str, list[int]]]) -> list[CategoryItem]:
    items: list[CategoryItem] = list()

    for row in base_rows:
        origin = row["origin"]
        pics_info = pics_map.get(origin, {})

        raw_pics = pics_info.get("pics", []) or []
        raw_preview = pics_info.get("preview")

        pics = get_url_from_s3(raw_pics, path=str(origin)) if raw_pics else []
        preview = get_url_from_s3(raw_preview, path=str(origin)) if raw_preview else None

        type_model = TypeModel(id=row["ptype_id"], type=row["ptype_title"]) if row["ptype_id"] is not None else None
        brand_model = BrandModel(id=row["pbrand_id"],
                                 brand=row["pbrand_title"]) if row["pbrand_id"] is not None else None

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


async def fetch_category_items(path_ids: set[int], session: AsyncSession) -> tuple[list[CategoryItem], AttributeIndex]:
    base_rows = await fetch_base_rows(path_ids, session)
    if not base_rows:
        return [], AttributeIndex(items={})

    origins = [row["origin"] for row in base_rows]

    pics_map = await fetch_pics_map(session, origins)

    origin_value_rows = await fetch_origin_value_rows(origins, session)

    all_value_ids = {row["attr_value_id"] for row in origin_value_rows}
    value_rows = await fetch_attribute_values(all_value_ids, session)

    value_map = {row["id"]: (row["attr_key_id"], row["value"], row["alias"]) for row in value_rows}

    all_key_ids = {row["attr_key_id"] for row in value_rows}
    key_rows = await fetch_attribute_keys(all_key_ids, session)

    key_map = {row["id"]: (row["key"], row["alias"]) for row in key_rows}

    origin_attr_values = build_origin_attr_values(origin_value_rows, value_map, key_map)
    attribute_index = build_attribute_index(value_map, key_map)
    items = build_category_items(base_rows, pics_map, origin_attr_values)

    return items, attribute_index
