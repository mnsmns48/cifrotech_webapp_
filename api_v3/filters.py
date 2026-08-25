import json
import hashlib
from collections import defaultdict
from typing import Any, Dict, Set, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.schemas.desc_builder import BlockResponse
from api_v3.schemas import HubLevelSchemeV3, FilterOption
from api_v3.slug import slugify
from cache import CacheManager
from cache.settings import cache_ttl
from models import ProductFeaturesHubMenuLevelLink, ProductFeaturesGlobal, AttributeLink, AttributeBrandRule, \
    AttributeKey, AttributeValue, AttributeModelOption


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, list):
        normalized = [_normalize_value(v) for v in value]
        return sorted(normalized)

    if isinstance(value, dict):
        return {
            key: _normalize_value(value[key])
            for key in sorted(value.keys())
            if value[key] is not None
        }

    if isinstance(value, str) and value.isdigit():
        return int(value)

    return value


def normalize_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {
        key: value
        for key, value in filters.items()
        if value not in (None, "", [], {})
    }

    normalized = {
        key: _normalize_value(value)
        for key, value in cleaned.items()
    }

    return normalized


def generate_filters_hash(filters: Dict[str, Any]) -> str:
    normalized = normalize_filters(filters)
    json_str = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(json_str.encode("utf-8")).hexdigest()


async def build_sku_filters(product_type_ids: set[int], feature_ids: set[int], brand_ids: set[int],
                            base_attrs: set[int], brand_rules: dict[int, dict[str, set[int]]],
                            session: AsyncSession) -> list[FilterOption]:
    if not product_type_ids or not brand_ids:
        return []

    brand_attr_sets: list[set[int]] = list()

    for brand_id in brand_ids:
        rules = brand_rules.get(brand_id, {"include": set(), "exclude": set()})

        include_keys = rules["include"]
        exclude_keys = rules["exclude"]

        brand_attrs = (base_attrs - exclude_keys) | include_keys
        brand_attr_sets.append(brand_attrs)

    if not brand_attr_sets:
        return []

    common_attrs = brand_attr_sets[0]
    for s in brand_attr_sets[1:]:
        common_attrs &= s

    if not common_attrs:
        return []

    sku_filters: list[FilterOption] = []

    for attr_key_id in common_attrs:
        q_key = select(AttributeKey).where(AttributeKey.id == attr_key_id)
        attr_key = (await session.execute(q_key)).scalar_one()
        q_values = select(AttributeValue.id,
                          AttributeValue.alias).join(
            AttributeModelOption,
            AttributeModelOption.attr_value_id == AttributeValue.id
        ).where(
            AttributeModelOption.model_id.in_(feature_ids),
            AttributeValue.attr_key_id == attr_key_id,
        )

        rows = await session.execute(q_values)

        seen_aliases = dict()
        for row in rows:
            alias = row.alias
            if alias not in seen_aliases:
                seen_aliases[alias] = row.id

        unique_values = [{"id": id_, "label": alias}
                         for alias, id_ in sorted(seen_aliases.items(), key=lambda x: x[0].lower())]

        sku_filters.append(FilterOption(key=attr_key.key,
                                        label=attr_key.alias or attr_key.key,
                                        type="select",
                                        values=unique_values,
                                        active=[],
                                        meta=None))
    return sku_filters


def build_model_filters(specs_map: Dict[int, List[BlockResponse]]) -> List[FilterOption]:
    filter_blocks = []
    for fid, blocks in specs_map.items():
        for block in blocks:
            if block.in_filter:
                filter_blocks.append(block)

    groups = defaultdict(lambda: {"key": None, "label": None, "values": set()})

    for block in filter_blocks:
        group_label = block.title or block.alias or "Характеристика"
        group_key = block.alias or slugify(group_label)

        g = groups[group_key]
        g["key"] = group_key
        g["label"] = group_label

        for v in block.values.values():
            g["values"].add(v)

    model_filters = list()
    for group_key, data in groups.items():
        values = sorted(data["values"])
        model_filters.append(FilterOption(key=data["key"],
                                          label=data["label"],
                                          type="select",
                                          values=[{"label": v} for v in values],
                                          active=[],
                                          meta=None))
    return model_filters
