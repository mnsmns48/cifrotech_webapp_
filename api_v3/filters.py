import json
import hashlib
import re
from typing import Any, Dict, List

from api_service.schemas.desc_builder import BlockResponse
from api_v3.schemas import FilterOption, CategoryItem, AttributeIndex
from api_v3.slug import slugify


async def build_sku_filters(attribute_index: AttributeIndex) -> list[FilterOption]:
    sku_filters: list[FilterOption] = list()

    for key_id, key_schema in attribute_index.items.items():
        key_lower = key_schema.key.lower()

        if "color" in key_lower:
            raw_items = [{"label": alias,
                          "slug": slugify(alias),
                          "ids": ids} for alias, ids in group_alias_values_grouped(key_schema.values)]
        else:
            raw_items = [{"id": v.id, "label": v.alias, "slug": slugify(v.alias)} for v in key_schema.values]

        sku_filters.append(make_custom_filter(key=key_schema.key, label=key_schema.alias, raw_items=raw_items))

    return sku_filters


async def build_meta_filters(items: list[CategoryItem]) -> list[FilterOption]:
    brands: set[tuple[int, str]] = set()
    types: set[tuple[int, str]] = set()
    models: set[tuple[int, str]] = set()

    for item in items:
        if item.brand:
            brands.add((item.brand.id, item.brand.brand))

        if item.type:
            types.add((item.type.id, item.type.type))

        if item.feature_id and item.model:
            models.add((item.feature_id, item.model))

    meta_filters: list[FilterOption] = list()

    if brands:
        raw_items = [{"id": bid, "label": bname, "slug": slugify(bname)} for bid, bname in brands]
        meta_filters.append(make_custom_filter(key="brand", label="Бренд", raw_items=raw_items))

    if types:
        raw_items = [{"id": tid, "label": tname, "slug": slugify(tname)} for tid, tname in types]
        meta_filters.append(make_custom_filter(key="product_type", label="Тип товара", raw_items=raw_items))

    if models:
        raw_items = [{"id": fid, "label": fname, "slug": slugify(fname)} for fid, fname in models]
        meta_filters.append(make_custom_filter(key="model", label="Модель", raw_items=raw_items))

    return meta_filters


def build_model_filters(specs_map: Dict[int, List[BlockResponse]]) -> List[FilterOption]:
    groups: dict[str, dict[str, Any]] = dict()

    for blocks in specs_map.values():
        for block in blocks:
            for value_info in block.values.values():
                if not value_info.in_filter or not value_info.alias:
                    continue

                group_key = slugify(value_info.alias)
                group = groups.get(group_key)

                if group is None:
                    group = {"key": group_key, "label": value_info.alias, "values": {}}
                    groups[group_key] = group

                if value_info.processed:
                    value = value_info.processed
                    slug = slugify(value)
                    group["values"].setdefault(slug, value)

    model_filters = list()

    for group in groups.values():
        values = sort_filter_values(group["values"].values())
        model_filters.append(FilterOption(key=group["key"],
                                          label=group["label"],
                                          type="select",
                                          values=[{"label": value, "slug": slugify(value)} for value in values],
                                          active=[],
                                          meta=None))

    return model_filters


def normalize_numeric_value(v: str) -> str:
    return re.sub(r'[^0-9.,-]', '', v).replace(',', '.')


def sort_filter_values(values: list[str]) -> list[str]:
    numeric_values = list()
    string_values = list()

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
    if raw_items and "ids" in raw_items[0]:
        return FilterOption(key=key, label=label, type="select", values=raw_items, active=[], meta=None)

    unique = {(v["id"], v["label"], v["slug"]) for v in raw_items}
    items = [{"id": i, "label": l, "slug": s} for i, l, s in unique]
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
                      sku_filters: list[FilterOption],
                      model_filters: list[FilterOption], meta_filters: list[FilterOption]) -> dict[str, list[Any]]:
    sku_keys = {f.key for f in sku_filters}
    model_keys = {f.key for f in model_filters}
    meta_keys = {f.key for f in meta_filters}

    normalized: dict[str, list[Any]] = dict()

    sku_index = {f.key: f for f in sku_filters}
    model_index = {f.key: f for f in model_filters}
    meta_index = {f.key: f for f in meta_filters}

    for key, raw_values in active_filters.items():
        if not isinstance(raw_values, list):
            raw_values = [raw_values]

        if key in sku_keys:
            f = sku_index[key]

            if f.values and "ids" in f.values[0]:
                collected_ids = list()

                for raw in raw_values:
                    for v in f.values:
                        if v["slug"] == raw:
                            collected_ids.extend(v["ids"])

                if collected_ids:
                    normalized[key] = collected_ids
                continue

            collected_ids = list()

            for raw in raw_values:
                for v in f.values:
                    if v["slug"] == raw:
                        collected_ids.append(v["id"])

            if collected_ids:
                normalized[key] = collected_ids
            continue

        if key in model_keys:
            f = model_index[key]
            collected_labels = list()

            for raw in raw_values:
                for v in f.values:
                    if v.get("slug") == raw:
                        collected_labels.append(v["label"])

            if collected_labels:
                normalized[key] = collected_labels
            continue

        if key in meta_keys:
            f = meta_index[key]
            collected_ids = list()

            for raw in raw_values:
                for v in f.values:
                    if v.get("slug") == raw:
                        collected_ids.append(v["id"])

            if collected_ids:
                normalized[key] = collected_ids
            continue

        if key.endswith("_min") or key.endswith("_max"):
            try:
                normalized[key] = [float(raw_values[0])]
            except ValueError:
                pass

    return normalized


def validate_filters(normalized_filters: dict[str, list[Any]], sku_filters: list[FilterOption],
                     model_filters: list[FilterOption], meta_filters: list[FilterOption]) -> dict[str, list[Any]]:
    sku_allowed: dict[str, set[int]] = dict()

    for f in sku_filters:
        allowed_ids = set()

        for v in f.values:
            if "id" in v:
                allowed_ids.add(v["id"])
            elif "ids" in v:
                allowed_ids.update(v["ids"])

        sku_allowed[f.key] = allowed_ids

    model_allowed = {f.key: {v["label"] for v in f.values} for f in model_filters}
    meta_allowed = {f.key: {v["id"] for v in f.values} for f in meta_filters}

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

        elif key in meta_allowed:
            allowed = meta_allowed[key]
            cleaned = [v for v in values if v in allowed]
            if cleaned:
                validated[key] = cleaned

        elif key.endswith("_min") or key.endswith("_max"):
            try:
                validated[key] = [float(values[0])]
            except ValueError:
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


def match_sku_item(item, filters, sku_keys):
    price = item.output_price or 0
    minv = filters.get("price_min")
    if minv and price < minv[0]:
        return False

    maxv = filters.get("price_max")
    if maxv and price > maxv[0]:
        return False

    attr_values = item.attr_values

    for key in sku_keys:
        vals = filters.get(key)
        if not vals:
            continue

        item_vals = attr_values.get(key)
        if not item_vals:
            return False

        if not set(vals).intersection(item_vals):
            return False

    return True


def match_meta_item(item: CategoryItem, filters: dict[str, list[Any]], meta_keys: set[str]) -> bool:
    if "brand" in meta_keys:
        vals = filters.get("brand")
        if vals:
            if item.brand is None or item.brand.id not in vals:
                return False

    if "product_type" in meta_keys:
        vals = filters.get("product_type")
        if vals:
            if item.type is None or item.type.id not in vals:
                return False

    if "model" in meta_keys:
        vals = filters.get("model")
        if vals:
            if item.feature_id is None or item.feature_id not in vals:
                return False

    return True


def match_model_item(item: CategoryItem, filters: dict[str, list[Any]],
                     model_keys: set[str], model_specs_map: dict[int, dict[str, list[str]]]) -> bool:
    active_model_keys = model_keys.intersection(filters)
    if not active_model_keys:
        return True

    fid = item.feature_id
    if fid is None:
        return False

    specs = model_specs_map.get(fid)
    if not specs:
        return False

    for key in active_model_keys:
        values = filters[key]
        spec_values = specs.get(key)

        if not spec_values:
            return False

        if not any(value in spec_values for value in values):
            return False

    return True


def group_alias_values_grouped(values):
    groups = dict()
    for v in values:
        alias = v.alias or ""
        groups.setdefault(alias, []).append(v.id)

    return [(alias, ids) for alias, ids in groups.items()]
