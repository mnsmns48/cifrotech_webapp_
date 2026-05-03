import statistics

from api_service.schemas import AnalyzeItem, AttributeKeyValueSchema
from models import ProductFeaturesGlobal
from models.attributes import OverrideType


def uniqueness_factor(attrs: dict[int, AttributeKeyValueSchema], group_items: list[dict]) -> float:
    if not group_items:
        return 1.0
    total = len(group_items)
    rarity_scores = list()
    for attr in attrs.values():
        count = sum(1 for item in group_items if attr.id in item["attrs_map"])
        rarity = 1 - (count / total)
        rarity_scores.append(rarity)
    avg_rarity = sum(rarity_scores) / len(rarity_scores) if rarity_scores else 0

    return 1.0 + avg_rarity * 0.3


def compute_dynamic_threshold(group_items: list, attrs: dict) -> float:
    prices = [item["input_price"] for item in group_items]
    base_price = min(prices)
    deltas = [p - base_price for p in prices]
    T1 = statistics.median(deltas)
    T2 = statistics.pstdev(prices) if len(prices) > 1 else 0
    avg_price = sum(prices) / len(prices)
    T3 = (T2 / avg_price) * avg_price if avg_price > 0 else 0

    base_threshold = max(T1, T2, T3)

    UF = uniqueness_factor(attrs, group_items)

    return base_threshold * UF


def compute_analyze(value_current: float, value_base: float, price_current: float,
                    price_base: float, group_items: list, attrs: dict) -> AnalyzeItem:
    value_increase = value_current - value_base
    price_increase = price_current - price_base
    threshold = compute_dynamic_threshold(group_items, attrs)
    if value_increase == 0:
        ratio = 999999999999
    else:
        ratio = price_increase / value_increase
    if value_increase == 0:
        verdict = price_increase <= threshold
    else:
        verdict = ratio <= threshold
    return AnalyzeItem(verdict=verdict, ratio=ratio, threshold=threshold, price_increase=price_increase,
                       value_increase=value_increase, value=value_current)


def compute_analyze_map(origin_map: dict[int, dict],
                        features_map: dict[int, ProductFeaturesGlobal],
                        rule_weight_map: dict[int, float],
                        type_key_to_rule: dict[tuple, int],
                        value_multiplier_map: dict[int, float],
                        brand_rule_map: dict[tuple, OverrideType]) -> dict[int, AnalyzeItem]:
    origin_value_map: dict[int, float] = dict()

    for origin_id, data in origin_map.items():
        feature_id = data["feature_id"]
        feature = features_map[feature_id]
        product_type_id = feature.type.id
        brand_id = feature.brand.id
        total_value = 0.0

        for attr_id, attr in data["attrs_map"].items():
            key_id = attr.key.id
            value_id = attr.id
            brand_rule = brand_rule_map.get((product_type_id, brand_id, key_id))
            rule_id = type_key_to_rule.get((product_type_id, key_id))
            base_weight = rule_weight_map.get(rule_id, 0.0)
            multiplier = value_multiplier_map.get(value_id, 1.0)
            if brand_rule == OverrideType.exclude:
                continue
            if brand_rule == OverrideType.include:
                weight = base_weight if base_weight > 0 else 1.0
            else:
                weight = base_weight
            total_value += weight * multiplier

        origin_value_map[origin_id] = total_value

    groups: dict[tuple, list[int]] = dict()

    for origin_id, data in origin_map.items():
        attrs_tuple = tuple(sorted(data["attrs_map"].keys()))
        key = (data["feature_id"], attrs_tuple)
        groups.setdefault(key, []).append(origin_id)

    analyze_map: dict[int, AnalyzeItem] = {}
    for (_feature_id, _attrs_tuple), origin_ids in groups.items():
        base_origin = min(origin_ids, key=lambda oid: origin_map[oid]["input_price"])
        price_base = origin_map[base_origin]["input_price"]
        value_base = origin_value_map[base_origin]
        group_items = [origin_map[oid] for oid in origin_ids]

        for oid in origin_ids:
            analyze_map[oid] = compute_analyze(value_current=origin_value_map[oid],
                                               value_base=value_base,
                                               price_current=origin_map[oid]["input_price"],
                                               price_base=price_base,
                                               group_items=group_items,
                                               attrs=origin_map[oid]["attrs_map"])

    return analyze_map
