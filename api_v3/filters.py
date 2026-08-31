import json
import hashlib
import re
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import TypeModel, BrandModel, BrandRuleSchema
from api_service.schemas.desc_builder import BlockResponse
from api_v3.schemas import FilterOption
from api_v3.slug import slugify
from models import AttributeKey, AttributeValue


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


async def build_sku_filters(product_types: list[TypeModel],
                            brands: list[BrandModel],
                            base_attrs: set[int],
                            brand_rules: list[BrandRuleSchema],
                            session: AsyncSession) -> list[FilterOption]:
    rules_map = {r.brand_id: r for r in brand_rules}
    brand_attr_sets: list[set[int]] = list()

    for brand in brands:
        rules = rules_map.get(brand.id)
        include_keys = rules.include if rules else set()
        exclude_keys = rules.exclude if rules else set()
        brand_attrs = (base_attrs - exclude_keys) | include_keys
        brand_attr_sets.append(brand_attrs)

    if not brand_attr_sets:
        return []

    common_attrs = brand_attr_sets[0]
    for s in brand_attr_sets[1:]:
        common_attrs &= s

    if not common_attrs:
        return []

    sku_filters: list[FilterOption] = list()

    q_keys = select(AttributeKey).where(AttributeKey.id.in_(common_attrs))
    keys_rows = (await session.execute(q_keys)).scalars().all()
    keys_map = {k.id: k for k in keys_rows}

    q_values = (select(AttributeValue.id,
                       AttributeValue.alias,
                       AttributeValue.attr_key_id)
                .where(AttributeValue.attr_key_id.in_(common_attrs))
                )

    values_rows = await session.execute(q_values)

    grouped_values: dict[int, dict[str, int]] = dict()

    for row in values_rows:
        alias = row.alias
        attr_key_id = row.attr_key_id

        grouped_values.setdefault(attr_key_id, {})
        grouped_values[attr_key_id].setdefault(alias, row.id)

    for attr_key_id in common_attrs:
        attr_key = keys_map[attr_key_id]
        alias_map = grouped_values.get(attr_key_id, {})

        raw_items = [{"id": id_, "label": alias}
                     for alias, id_ in alias_map.items()]

        sku_filters.append(make_custom_filter(key=attr_key.key,
                                              label=attr_key.alias or attr_key.key,
                                              raw_items=raw_items))

    brand_values = [{"id": b.id, "label": b.brand} for b in brands]
    sku_filters.append(make_custom_filter("brand", "Бренд", brand_values))
    type_values = [{"id": t.id, "label": t.type} for t in product_types]
    sku_filters.append(make_custom_filter("product_type", "Тип устройства", type_values))

    return sku_filters


def build_model_filters(specs_map: Dict[int, List[BlockResponse]]) -> List[FilterOption]:
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"key": None, "label": None, "values": set()})

    for blocks in specs_map.values():
        for block in blocks:
            for value_info in block.values.values():
                if not value_info.in_filter:
                    continue

                if not value_info.alias:
                    continue

                group_label = value_info.alias
                group_key = slugify(group_label)

                g = groups[group_key]
                g["key"] = group_key
                g["label"] = group_label

                if value_info.processed:
                    g["values"].add(value_info.processed)

    model_filters: list[FilterOption] = []

    for group_key, data in groups.items():
        raw_values = list(data["values"])
        sorted_values = sort_filter_values(raw_values)

        model_filters.append(
            FilterOption(
                key=data["key"],
                label=data["label"],
                type="select",
                values=[{"label": v} for v in sorted_values],
                active=[],
                meta=None
            )
        )

    return model_filters


def normalize_numeric_value(v: str) -> str:
    return re.sub(r'[^0-9.,-]', '', v).replace(',', '.')


def sort_filter_values(values: list[str]) -> list[str]:
    numeric_values = []
    string_values = []

    for v in values:
        cleaned = normalize_numeric_value(v)

        try:
            num = float(cleaned)
            numeric_values.append((num, v))
        except ValueError:
            string_values.append(v)

    numeric_values.sort(key=lambda x: x[0])
    string_values.sort(key=lambda x: x.lower())

    return [orig for _, orig in numeric_values] + string_values


def make_custom_filter(key: str, label: str, raw_items: list[dict]) -> FilterOption:
    unique = {(v["id"], v["label"]) for v in raw_items}
    items = [{"id": i, "label": l} for i, l in unique]
    items.sort(key=lambda x: x["label"].lower())

    return FilterOption(key=key, label=label, type="select", values=items, active=[], meta=None)


def compute_filters_hash(slug: str,
                         active_filters: Dict[str, Any],
                         sort_key: str,
                         page: int,
                         limit: int,
                         model_filters: List[Dict[str, Any]],
                         sku_filters: List[Dict[str, Any]]) -> str:
    payload = {"slug": slug, "active_filters": active_filters, "sort": sort_key,
               "page": page, "limit": limit, "model_filters": model_filters,
               "sku_filters": sku_filters}

    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
