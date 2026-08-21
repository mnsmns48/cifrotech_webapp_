from typing import List, Dict, Set

from fastapi import HTTPException
from sqlalchemy import select, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from api_service.s3_helper import get_url_from_s3
from api_service.schemas import HubLevelPath, AttributeKeyValueSchema, AttributeKey, BrandModel, TypeModel
from api_service.schemas.features_schemas import FeatureInnerRow, FeatureCategoryScheme, FeatureProductScheme

from api_v3.crud import get_menu_level, get_feature_with_type_brand
from api_v3.schemas import HubLevelSchemeV3
from cache import CacheManager
from cache.keys.features import feature_key
from cache.keys.hub import MENU_LEVELS
from cache.settings import cache_ttl
from models import HUbMenuLevel


async def load_menu_tree(session: AsyncSession) -> Dict[int, List[int]]:
    stmt = select(HUbMenuLevel.id, HUbMenuLevel.parent_id)
    rows = (await session.execute(stmt)).all()

    tree: Dict[int, List[int]] = {}

    for row in rows:
        node_id = row.id
        parent_id = row.parent_id

        if parent_id not in tree:
            tree[parent_id] = []

        tree[parent_id].append(node_id)

    return tree


def collect_descendants(tree: Dict[int, List[int]], node_id: int, result: Set[int]):
    result.add(node_id)
    if node_id not in tree:
        return
    for child in tree[node_id]:
        collect_descendants(tree, child, result)


async def resolve_menu_levels_to_path_ids(selected_levels: List[int], session: AsyncSession) -> List[int]:
    if not selected_levels:
        return []

    tree = await load_menu_tree(session)

    result: Set[int] = set()

    for level_id in selected_levels:
        collect_descendants(tree, level_id, result)

    return list(result)


def build_cursor_response(rows: list[RowMapping], limit: int):
    if not rows:
        return None, False

    last_id = rows[-1]["id"]
    has_more = len(rows) == limit

    next_cursor = last_id if has_more else None

    return next_cursor, has_more


async def build_route(session, leaf_id: int) -> list[HubLevelPath]:
    route = list()
    current = leaf_id

    while True:
        level = await get_menu_level(session, current)
        if not level:
            break

        route.append(HubLevelPath(path_id=level.id, label=level.label))

        if level.parent_id == 0 or level.parent_id == level.id:
            break

        current = level.parent_id

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
    attrs = []
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
            rows = [FeatureInnerRow(param=k, value=v)
                    for k, v in params.items()]
            categories.append(FeatureCategoryScheme(title=title, rows=rows))

    return FeatureProductScheme(features_id=feature.id, features=categories)


async def build_feature_data(session: AsyncSession, cache: CacheManager, origin_obj):
    if not origin_obj.features:
        return None, None, None, None

    pf_link = origin_obj.features[0]
    feature = await get_feature_with_type_brand(session, pf_link.feature_id)

    if not feature:
        return None, None, None, None

    type_obj = TypeModel(id=feature.type.id, type=feature.type.type)

    brand_obj = BrandModel(id=feature.brand.id, brand=feature.brand.brand)
    key = feature_key(feature.id)
    cached = await cache.get(key)

    if cached:
        full_specs_data = cached.get("full_specs")
        full_specs = (FeatureProductScheme.model_validate(full_specs_data)
                      if full_specs_data else None)
        pros_cons = cached.get("pros_cons")

    else:
        full_specs = build_full_specs(feature)
        pros_cons = build_pros_cons(feature)

        await cache.set(key,
                        {"full_specs": full_specs, "pros_cons": pros_cons},
                        ttl=cache_ttl.product_info)

    return type_obj, brand_obj, full_specs, pros_cons


async def resolve_slug_path_to_level(slug_path: List[str], cache: CacheManager,
                                     session: AsyncSession) -> HubLevelSchemeV3:
    cached = await cache.get(MENU_LEVELS)
    if cached is None:
        levels = await fetch_hub_levels(session)
        raw_levels = [lvl.model_dump() for lvl in levels]
        await cache.set(MENU_LEVELS, raw_levels, ttl=cache_ttl.menu)
        levels_data = raw_levels
    else:
        levels_data = cached

    levels = [HubLevelSchemeV3(**item) for item in levels_data]

    if not slug_path:
        raise HTTPException(status_code=400, detail="Slug path is empty")

    slug_map: Dict[str, List[HubLevelSchemeV3]] = {}
    id_map: Dict[int, HubLevelSchemeV3] = {}

    for lvl in levels:
        slug_map.setdefault(lvl.slug, []).append(lvl)
        id_map[lvl.id] = lvl

    current_level: HubLevelSchemeV3 | None = None

    for index, slug in enumerate(slug_path):
        candidates = slug_map.get(slug)
        if not candidates:
            raise HTTPException(status_code=404, detail=f"Slug '{slug}' not found")

        if index == 0:
            depth0 = [lvl for lvl in candidates if lvl.depth == 0]
            depth2 = [lvl for lvl in candidates if lvl.depth == 2]

            if depth0:
                current_level = depth0[0]
            elif depth2:
                current_level = depth2[0]
            else:
                raise HTTPException(status_code=400, detail=f"Slug '{slug}' cannot be used as first element")
        else:
            next_candidates = [lvl for lvl in candidates if lvl.parent_id == current_level.id]
            if not next_candidates:
                raise HTTPException(status_code=404,
                                    detail=f"Slug '{slug}' does not match parent_id={current_level.id}")
            current_level = next_candidates[0]

    return current_level
