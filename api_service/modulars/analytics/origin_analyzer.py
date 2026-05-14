from statistics import median

from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.crud import load_weight_rules, load_value_maps, load_brand_overrides, \
    load_value_key_map
from api_service.schemas import ModelForApprove, AnalyzeItem
from api_service.schemas.product_schemas import OriginWithAttrsPicsAnalyze
from models.attributes import OverrideType


class OriginAnalyzer:

    def __init__(self, session: AsyncSession):
        self.session = session

        self.weight_rules = dict()
        self.value_multiplier = dict()
        self.brand_overrides = dict()
        self.key_by_value = dict()
        self.rules_by_type = dict()

    async def load(self):
        rows = await load_weight_rules(self.session)
        for type_id, key_id, weight in rows:
            self.weight_rules[(type_id, key_id)] = weight
            self.rules_by_type.setdefault(type_id, set()).add(key_id)

        rows = await load_value_maps(self.session)
        for value_id, multiplier in rows:
            self.value_multiplier[value_id] = multiplier

        rows = await load_brand_overrides(self.session)
        for type_id, brand_id, key_id, rule_type in rows:
            self.brand_overrides[(type_id, brand_id, key_id)] = rule_type

        rows = await load_value_key_map(self.session)
        for value_id, key_id in rows:
            self.key_by_value[value_id] = key_id

    def analyze_model(self, model: ModelForApprove):
        values = list()
        for origin in model.origins:
            v = self.analyze_origin(origin, model.type_.id, model.brand.id)
            values.append(v)

        min_value = min(values)
        min_price = min(o.input_price or float("inf") for o in model.origins)

        ratios = list()
        for origin, value in zip(model.origins, values):
            price = origin.input_price or float("inf")

            price_increase = (price - min_price) / min_price if min_price > 0 else 0
            value_increase = (value - min_value) / min_value if min_value > 0 else 0

            if price_increase == 0:
                ratio = 999999.0
            else:
                ratio = value_increase / price_increase

            ratios.append(ratio)

        threshold = median(ratios)

        for origin, value, ratio in zip(model.origins, values, ratios):
            price = origin.input_price or float("inf")

            price_increase = (price - min_price) / min_price if min_price > 0 else 0
            value_increase = (value - min_value) / min_value if min_value > 0 else 0

            # verdict = ratio >= threshold
            verdict = value_increase >= price_increase

            origin.analyze = AnalyzeItem(verdict=verdict,
                                         ratio=round(ratio, 2),
                                         threshold=round(threshold, 2),
                                         price_increase=round(price_increase, 2),
                                         value_increase=round(value_increase, 2),
                                         value=round(value, 2))

    def analyze_origin(self, origin: OriginWithAttrsPicsAnalyze, type_id: int, brand_id: int) -> float:
        total_value = 0.0
        for attr in origin.attrs or []:
            value_id = attr.id
            key_id = self.key_by_value.get(value_id)
            if key_id is None:
                continue

            override = self.brand_overrides.get((type_id, brand_id, key_id))
            if override == OverrideType.exclude:
                continue

            weight = self.weight_rules.get((type_id, key_id))
            if override == OverrideType.include:
                if weight is None:
                    weight = 1.0

            if weight is None:
                continue

            multiplier = self.value_multiplier.get(value_id, 1.0)
            total_value += weight * multiplier

        return total_value

    def debug_print(self, model):
        print("\n================ DEBUG MODEL ================")
        print(f"MODEL: {model.title} (id={model.id})")

        type_id = model.type_.id
        brand_id = model.brand.id

        # Считаем value для каждого origin
        values = []
        for origin in model.origins:
            v = self.analyze_origin(origin, type_id, brand_id)
            values.append(v)

        min_value = min(values)
        min_price = min(o.input_price or float("inf") for o in model.origins)

        print(f"MIN VALUE = {min_value}")
        print(f"MIN PRICE = {min_price}")

        print("\nORIGINS:")
        for origin, value in zip(model.origins, values):
            print("\n--------------------------------------------")
            print(f"ORIGIN {origin.origin}")
            print(f"PRICE = {origin.input_price}")
            print(f"VALUE = {value}")

            # Печатаем атрибуты
            print("ATTRIBUTES:")
            for attr in origin.attrs:
                value_id = attr.id
                key_id = self.key_by_value.get(value_id)
                weight = self.weight_rules.get((type_id, key_id))
                multiplier = self.value_multiplier.get(value_id, 1.0)

                print(f"  value_id={value_id}, key_id={key_id}, "
                      f"weight={weight}, multiplier={multiplier}")

            # Увеличения
            price = origin.input_price or float("inf")
            price_increase = (price - min_price) / min_price if min_price > 0 else 0
            value_increase = (value - min_value) / min_value if min_value > 0 else 0

            # ratio
            if price_increase == 0:
                ratio = 999999.0
            else:
                ratio = value_increase / price_increase

            print(f"price_increase = {price_increase}")
            print(f"value_increase = {value_increase}")
            print(f"ratio = {ratio}")

            # verdict
            verdict = origin.analyze.verdict if origin.analyze else None
            print(f"VERDICT = {verdict}")

        print("============================================\n")
