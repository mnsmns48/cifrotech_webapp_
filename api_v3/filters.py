import json
import hashlib
import re
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import TypeModel, BrandModel, BrandRuleSchema
from api_service.schemas.desc_builder import BlockResponse
from api_v3.schemas import FilterOption, CategoryItem
from api_v3.slug import slugify
from models import AttributeKey, AttributeValue


async def build_sku_filters(product_types: list[TypeModel],
                            model_map: dict[int, str],
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
    type_values = [{"id": t.id, "label": t.type} for t in product_types]
    model_values = [{"id": fid, "label": model} for fid, model in sorted(model_map.items(), key=lambda x: x[1])]
    sku_filters.append(make_custom_filter("brand", "Бренд", brand_values))
    sku_filters.append(make_custom_filter("product_type", "Тип устройства", type_values))
    sku_filters.append(make_custom_filter("model", "Модель", model_values))

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


def normalize_filters(active_filters: dict[str, list[str]],
                      sku_filters: list[FilterOption], model_filters: list[FilterOption]) -> dict[str, list[Any]]:
    sku_keys = {f.key for f in sku_filters}
    model_keys = {f.key for f in model_filters}

    normalized: dict[str, list[Any]] = {}

    for key, raw_values in active_filters.items():
        if not isinstance(raw_values, list):
            raw_values = [raw_values]
        if key in sku_keys:
            cleaned_values = []
            for v in raw_values:
                try:
                    cleaned_values.append(int(v))
                except ValueError:
                    continue

            if cleaned_values:
                normalized[key] = cleaned_values

        elif key in model_keys:
            cleaned_values = [v.strip() for v in raw_values if v.strip()]
            if cleaned_values:
                normalized[key] = cleaned_values

        elif key.endswith("_min") or key.endswith("_max"):
            try:
                normalized[key] = [float(raw_values[0])]
            except ValueError:
                continue

        else:
            continue

    return normalized


def validate_filters(normalized_filters: dict[str, list[Any]],
                     sku_filters: list[FilterOption], model_filters: list[FilterOption]) -> dict[str, list[Any]]:
    sku_allowed: dict[str, set[int]] = dict()
    for f in sku_filters:
        allowed_ids = {v["id"] for v in f.values}
        sku_allowed[f.key] = allowed_ids

    model_allowed: dict[str, set[str]] = dict()
    for f in model_filters:
        allowed_labels = {v["label"] for v in f.values}
        model_allowed[f.key] = allowed_labels

    validated: dict[str, list[Any]] = dict()

    for key, values in normalized_filters.items():
        if key in sku_allowed:
            allowed = sku_allowed[key]
            cleaned = [v for v in values if v in allowed]
            if cleaned:
                validated[key] = cleaned

        elif key in model_allowed:
            allowed = model_allowed[key]
            cleaned = [v for v in values if v in allowed]
            if cleaned:
                validated[key] = cleaned

        elif key.endswith("_min") or key.endswith("_max"):
            try:
                num = float(values[0])
                validated[key] = [num]
            except ValueError:
                continue

        else:
            continue

    return validated


def prepare_model_specs_map(specs_map: dict[int, list[BlockResponse]]) -> dict[int, dict[str, list[str]]]:
    result: dict[int, dict[str, list[str]]] = dict()
    for fid, blocks in specs_map.items():
        model_map: dict[str, list[str]] = dict()

        for block in blocks:
            for _, value_info in block.values.items():
                if not value_info.in_filter:
                    continue

                alias = value_info.alias
                if not alias:
                    continue

                key = slugify(alias)
                processed = value_info.processed

                model_map.setdefault(key, []).append(processed)

        result[fid] = model_map

    return result


def match_sku_item(item: CategoryItem, filters: dict[str, list[Any]], sku_keys: set[str]) -> bool:
    for key, values in filters.items():

        if key == "price_min":
            if (item.output_price or 0) < values[0]:
                return False
            continue

        if key == "price_max":
            if (item.output_price or 0) > values[0]:
                return False
            continue

        if key in sku_keys:

            if key == "brand":
                if item.brand is None or item.brand.id not in values:
                    return False
                continue

            if key == "product_type":
                if item.type is None or item.type.id not in values:
                    return False
                continue

            if hasattr(item, "attr_values"):
                attr_vals = item.attr_values.get(key)
                if not attr_vals:
                    return False

                if not any(v in attr_vals for v in values):
                    return False
                continue
            return False
    return True


def match_model_item(item: CategoryItem,
                     filters: dict[str, list[Any]],
                     model_keys: set[str],
                     model_specs_map: dict[int, dict[str, list[str]]]) -> bool:
    if not any(key in model_keys for key in filters.keys()):
        return True

    fid = item.feature_id
    if fid is None:
        return False

    specs = model_specs_map.get(fid)
    if not specs:
        return False

    for key, values in filters.items():
        if key in model_keys:
            spec_values = specs.get(key)
            if spec_values is None:
                return False

            if not any(v in spec_values for v in values):
                return False

    return True


def filter_products_engine(items: list[CategoryItem], specs_map: dict[int, list[BlockResponse]],
                           validated_filters: dict[str, list[Any]],
                           sku_filters: list[FilterOption],
                           model_filters: list[FilterOption]) -> list[CategoryItem]:
    sku_keys = {f.key for f in sku_filters}
    model_keys = {f.key for f in model_filters}
    model_specs_map = prepare_model_specs_map(specs_map)
    filtered = list()

    for item in items:
        if not match_sku_item(item, validated_filters, sku_keys):
            continue

        if not match_model_item(item, validated_filters, model_keys, model_specs_map):
            continue

        filtered.append(item)

    return filtered
