from collections import defaultdict
from functools import partial
from statistics import median

from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.crud import (load_weight_rules,
                                                 load_value_maps,
                                                 load_brand_overrides,
                                                 load_value_key_map)

from api_service.schemas import AnalyzeItem, ProductMarketSettingsSchema
from config import cache_key_builder


@cache(expire=1000, key_builder=cache_key_builder)
async def load_analyzer_cache(session: AsyncSession):
    return {"rules": await load_weight_rules(session),
            "value_maps": await load_value_maps(session),
            "brand_overrides": await load_brand_overrides(session),
            "value_key_map": await load_value_key_map(session),
            }


class OriginAnalyzer:
    MARKET_VARIANCE_SCALE_DEFAULT: float = 5.0
    MARKET_VARIANCE_EXPONENT_DEFAULT: float = 1.1
    REFERENCE_PRICE: float = 30000
    MIN_RELATIVE_TOLERANCE: float = 0.03
    ABSOLUTE_MIN_PRICE_DELTA: float = 300

    def __init__(self, session: AsyncSession,
                 market_settings_map: dict[int, ProductMarketSettingsSchema]):
        self.session = session
        self.market_settings = market_settings_map
        self.weight_rules = {}
        self.value_multiplier = {}
        self.brand_overrides = {}
        self.key_by_value = {}

    async def load(self):
        cached = await load_analyzer_cache(self.session)
        for row in cached["rules"]:
            self.weight_rules[(row["type_id"], row["key_id"])] = float(row["weight"])
        for row in cached["value_maps"]:
            self.value_multiplier[row["value_id"]] = float(row["multiplier"])
        for row in cached["brand_overrides"]:
            self.brand_overrides[(row["type_id"], row["brand_id"], row["key_id"])] = row["rule_type"]
        for row in cached["value_key_map"]:
            self.key_by_value[row["value_id"]] = row["key_id"]

    @staticmethod
    def _get_price(origin) -> float:
        price = (getattr(origin, "input_price", None) or getattr(origin, "output_price", 0.0))
        try:
            return float(price or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _is_attr_enabled(self, type_id, brand_id, key_id):
        rule = self.brand_overrides.get((type_id, brand_id, key_id))
        return rule != "disable"

    def build_economic_features(self, origin, type_id, brand_id):
        result = defaultdict(list)
        for attr in (origin.attrs or []):
            value_id = attr.id
            key_id = self.key_by_value.get(value_id)
            if key_id is None:
                continue
            if (type_id, key_id) not in self.weight_rules:
                continue
            if value_id not in self.value_multiplier:
                continue
            if not self._is_attr_enabled(type_id, brand_id, key_id):
                continue
            result[key_id].append(value_id)

        return dict(result)

    @staticmethod
    def build_signature(features):
        parts = list()
        for key_id in sorted(features.keys()):
            values = sorted(features[key_id])
            values_str = ",".join(str(v) for v in values)
            parts.append(f"{key_id}:{values_str}")

        return "|".join(parts)

    def calculate_value(self, features, type_id):
        total, total_weight = 0.0, 0.0
        for key_id, value_ids in features.items():
            weight = self.weight_rules.get((type_id, key_id), 0.0)
            if weight <= 0:
                continue
            best_multiplier = max(self.value_multiplier.get(v, 1.0) for v in value_ids)
            total += (weight * best_multiplier)
            total_weight += weight
        if total_weight <= 0:
            return 0.0
        return float(total / total_weight)

    def build_configuration_groups(self, model, path_id):
        groups = dict()
        for origin in model.origins:
            features = self.build_economic_features(origin, model.type_.id, model.brand.id)
            signature = self.build_signature(features)

            if signature not in groups:
                value = self.calculate_value(features=features, type_id=model.type_.id)
                groups[signature] = {"path_id": path_id,
                                     "origins": [],
                                     "features": features,
                                     "value": value,
                                     "baseline_origin": None,
                                     "baseline_price": 0.0}
            groups[signature]["origins"].append(origin)
        for group in groups.values():
            cheapest = min(group["origins"], key=partial(self._get_price))
            group["baseline_origin"] = cheapest.origin
            group["baseline_price"] = self._get_price(cheapest)

        return groups

    def calculate_market_tolerance(self, baseline_price, mad, path_id: int):
        ms = self.market_settings.get(path_id, None)
        if ms:
            scale = ms.market_variance_scale
            exponent = ms.market_variance_exponent
        else:
            scale = self.MARKET_VARIANCE_SCALE_DEFAULT
            exponent = self.MARKET_VARIANCE_EXPONENT_DEFAULT
        dynamic_softness = (scale * (baseline_price / self.REFERENCE_PRICE) ** exponent)
        mad_component = mad * dynamic_softness
        fallback_component = max(baseline_price * self.MIN_RELATIVE_TOLERANCE,
                                 self.ABSOLUTE_MIN_PRICE_DELTA)
        effective_tolerance = max(mad_component, fallback_component)
        return {"dynamic_softness": dynamic_softness,
                "mad_component": mad_component,
                "fallback_component": fallback_component,
                "effective_tolerance": effective_tolerance}

    def analyze_market_inside_group(self, group):
        prices = [self._get_price(origin) for origin in group["origins"]]
        if not prices:
            return {}
        baseline_price = (group["baseline_price"])
        median_price = median(prices)
        deviations = [abs(p - median_price) for p in prices]
        mad = median(deviations)
        tolerance_data = self.calculate_market_tolerance(baseline_price=baseline_price,
                                                         mad=mad,
                                                         path_id=group.get("path_id"))
        effective_tolerance = tolerance_data["effective_tolerance"]
        upper_limit = baseline_price + effective_tolerance

        result = dict()
        for origin in group["origins"]:
            price = self._get_price(origin)
            abs_delta = (price - baseline_price)
            relative_delta = (abs_delta / max(baseline_price, 1.0))
            dominated = price > upper_limit
            result[origin.origin] = {"dominated": dominated,
                                     "price": price,
                                     "baseline_price": baseline_price,
                                     "upper_limit": upper_limit,
                                     "abs_delta": abs_delta,
                                     "relative_delta": relative_delta,
                                     "mad": mad,
                                     **tolerance_data}

        return result

    @staticmethod
    def build_analyze_item(market_metrics, group_value):
        dominated = market_metrics["dominated"]
        if dominated:
            verdict = False
            reason = "Цена аномально высокая для данной конфигурации"
        else:
            verdict = True
            reason = "Цена находится в пределах рынка"

        return AnalyzeItem(verdict=bool(verdict),
                           reason=reason,
                           value=float(group_value),
                           market_price=float(market_metrics["price"]),
                           market_baseline=float(market_metrics["baseline_price"]),
                           market_upper_limit=float(market_metrics["upper_limit"]),
                           market_delta=float(market_metrics["relative_delta"]),
                           market_mad=float(market_metrics["mad"]),
                           market_effective_tolerance=float(market_metrics["effective_tolerance"]))

    def analyze_model(self, model, path_id):
        groups = self.build_configuration_groups(model, path_id)
        for signature, group in groups.items():
            market_metrics = self.analyze_market_inside_group(group)
            for origin in group["origins"]:
                origin.analyze = (self.build_analyze_item(market_metrics=market_metrics[origin.origin],
                                                          group_value=group["value"]))
