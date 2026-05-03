import statistics

from api_service.schemas import AnalyzeItem, AttributeKeyValueSchema
from models import ProductFeaturesGlobal


def compute_value(feature: ProductFeaturesGlobal, attrs: dict[int, AttributeKeyValueSchema]) -> float:
    value = 0.0
    for a in attrs.values():
        if a.key.key.lower() in ("ram", "оперативная память"):
            try:
                ram = int(a.value.replace("gb", "").strip())
                value += ram * 0.5
            except:
                pass

    for a in attrs.values():
        if a.key.key.lower() in ("rom", "память", "storage"):
            try:
                rom = a.value.lower().strip()
                if "tb" in rom:
                    rom = int(rom.replace("tb", "")) * 1000
                else:
                    rom = int(rom.replace("gb", ""))
                value += rom * 0.05
            except:
                pass

    for a in attrs.values():
        if a.key.key.lower() in ("sim", "sim_config", "сим-карты"):
            sim_cfg = a.value.lower().strip()
            if sim_cfg in ("sim + esim", "dual", "dual sim", "2 sim"):
                value += 2.0
            elif sim_cfg in ("esim", "1 sim"):
                value += 1.0

    for a in attrs.values():
        if a.key.key.lower() in ("color", "цвет"):
            value += 0.1

    return round(value, 4)


def uniqueness_factor(attrs):
    for a in attrs.values():
        if a.key.key.lower() in ("color", "цвет"):
            if a.value.lower() in ("purple", "фиолетовый"):
                return 1.2
    return 1.0


def compute_dynamic_threshold(group_items: list, attrs: dict) -> float:
    prices = [item["input_price"] for item in group_items]
    base_price = min(prices)

    deltas = [p - base_price for p in prices]
    T1 = statistics.median(deltas)
    if len(prices) > 1:
        T2 = statistics.pstdev(prices)
    else:
        T2 = 0
    avg_price = sum(prices) / len(prices)
    if avg_price > 0:
        relative_sigma = T2 / avg_price
        T3 = relative_sigma * avg_price
    else:
        T3 = 0

    UF = uniqueness_factor(attrs)
    base_threshold = max(T1, T2, T3)
    threshold = base_threshold * UF

    return threshold


def compute_analyze(feature_id: int, origin_id: int, value_current: float, value_base: float, price_current: float,
                    price_base: float, group_items: list, attrs: dict) -> AnalyzeItem:
    value_increase = value_current - value_base
    price_increase = price_current - price_base
    threshold = compute_dynamic_threshold(group_items, attrs)
    if value_increase == 0:
        ratio = float("inf")
    else:
        ratio = price_increase / value_increase
    if value_increase == 0:
        verdict = price_increase <= threshold
    else:
        verdict = ratio <= threshold
    return AnalyzeItem(verdict=verdict, ratio=ratio, threshold=threshold, price_increase=price_increase,
                       value_increase=value_increase, value=value_current)
