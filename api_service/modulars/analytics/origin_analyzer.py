from collections import defaultdict
from statistics import median

from api_service.modulars.analytics.crud import (
    load_weight_rules,
    load_value_maps,
    load_brand_overrides,
    load_value_key_map
)

from api_service.schemas import AnalyzeItem


class OriginAnalyzer:

    EPSILON = 0.0001
    MAD_SOFTNESS = 5
    MAD_ALPHA = 1.1

    MIN_THRESHOLD = 0.01
    MAX_THRESHOLD = 5.0

    def __init__(self, session):

        self.session = session

        self.weight_rules = {}
        self.value_multiplier = {}
        self.brand_overrides = {}
        self.key_by_value = {}

        self.rules_by_type = {}

    # ============================================================
    # LOAD
    # ============================================================

    async def load(self):

        rows = await load_weight_rules(self.session)

        for type_id, key_id, weight in rows:
            self.weight_rules[(type_id, key_id)] = float(weight)

            self.rules_by_type.setdefault(
                type_id,
                set()
            ).add(key_id)

        rows = await load_value_maps(self.session)

        for value_id, multiplier in rows:
            self.value_multiplier[value_id] = float(multiplier)

        rows = await load_brand_overrides(self.session)

        for type_id, brand_id, key_id, rule_type in rows:
            self.brand_overrides[
                (type_id, brand_id, key_id)
            ] = rule_type

        rows = await load_value_key_map(self.session)

        for value_id, key_id in rows:
            self.key_by_value[value_id] = key_id

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _get_price(origin) -> float:

        price = (
                getattr(origin, "output_price", None)
                or getattr(origin, "input_price", 0.0)
        )

        try:
            return float(price or 0.0)
        except:
            return 0.0

    def _is_attr_enabled(
            self,
            type_id,
            brand_id,
            key_id
    ):

        rule = self.brand_overrides.get(
            (type_id, brand_id, key_id)
        )

        if rule == "disable":
            return False

        return True

    # ============================================================
    # ECONOMIC ATTRS
    # ============================================================

    def build_economic_features(
            self,
            origin,
            type_id,
            brand_id
    ):

        """
        Только attrs которые:
        - имеют weight
        - имеют multiplier

        Цвет сюда НЕ попадет.
        """

        result = defaultdict(list)

        for attr in (origin.attrs or []):

            value_id = attr.id

            key_id = self.key_by_value.get(value_id)

            if key_id is None:
                continue

            weight = self.weight_rules.get((type_id, key_id), 0)
            if weight <= 1:
                continue

            if not self._is_attr_enabled(
                    type_id,
                    brand_id,
                    key_id
            ):
                continue

            result[key_id].append(value_id)

        return dict(result)

    # ============================================================
    # CONFIGURATION SIGNATURE
    # ============================================================

    def build_signature(self, features):
        """
        Signature строится по key_id + value_id.
        Multiplier НЕ используется, потому что он может быть одинаковым
        для разных ROM/SIM.
        """

        parts = []

        for key_id in sorted(features.keys()):
            # сортируем value_id чтобы signature был стабильным
            values = sorted(features[key_id])
            values_str = ",".join(str(v) for v in values)
            parts.append(f"{key_id}:{values_str}")

        return "|".join(parts)

    # ============================================================
    # VALUE
    # ============================================================

    def calculate_value(
            self,
            features,
            type_id
    ):

        """
        Normalized additive model.
        """

        total = 0.0
        total_weight = 0.0

        for key_id, value_ids in features.items():

            weight = self.weight_rules.get(
                (type_id, key_id),
                0.0
            )

            if weight <= 0:
                continue

            best_multiplier = max(
                self.value_multiplier.get(v, 1.0)
                for v in value_ids
            )

            total += (
                    weight
                    * best_multiplier
            )

            total_weight += weight

        if total_weight <= 0:
            return 0.0

        return float(total / total_weight)

    # ============================================================
    # CONFIGURATION GROUPS
    # ============================================================

    def build_configuration_groups(
            self,
            model
    ):

        """
        signature -> {
            origins,
            features,
            value,
            min_price
        }
        """

        type_id = model.type_.id
        brand_id = model.brand.id

        groups = {}

        for origin in model.origins:

            features = self.build_economic_features(
                origin,
                type_id,
                brand_id
            )

            signature = self.build_signature(
                features
            )

            if signature not in groups:
                value = self.calculate_value(
                    features,
                    type_id
                )

                groups[signature] = {
                    "origins": [],
                    "features": features,
                    "value": value,
                    "min_price": None,
                    "baseline_origin": None
                }

            groups[signature]["origins"].append(
                origin
            )
            print(
                "[GROUP] origin=", origin.origin,
                "signature=", signature,
                "features=", features,
            )
        # baseline внутри группы
        for group in groups.values():
            cheapest = min(
                group["origins"],
                key=lambda o: self._get_price(o)
            )

            group["baseline_origin"] = cheapest.origin
            group["min_price"] = self._get_price(
                cheapest
            )

        return groups

    # ============================================================
    # UPGRADE CHAIN
    # ============================================================

    def build_upgrade_chain(
            self,
            groups
    ):

        """
        Анализируем upgrade economics
        между configurations.
        """

        chain = []

        for signature, group in groups.items():
            chain.append({
                "signature": signature,
                "value": group["value"],
                "price": group["min_price"]
            })

        chain.sort(
            key=lambda x: (
                x["price"],
                x["value"]
            )
        )

        return chain

    # ============================================================
    # GROUP ECONOMICS
    # ============================================================

    def calculate_group_ratios(
            self,
            chain
    ):

        """
        Сравнение идет:
        group -> previous cheaper group
        """

        result = {}

        prev = None

        for item in chain:

            signature = item["signature"]

            if prev is None:
                result[signature] = {
                    "ratio": None,
                    "price_increase": 0.0,
                    "value_increase": 0.0
                }

                prev = item
                continue

            price_delta = (
                    (item["price"] - prev["price"])
                    / max(prev["price"], 1.0)
            )

            value_delta = (
                    (item["value"] - prev["value"])
                    / max(prev["value"], 0.0001)
            )

            if value_delta <= 0:

                ratio = 0.0

            elif price_delta <= self.EPSILON:

                ratio = 999.0

            else:

                ratio = (
                        value_delta
                        / price_delta
                )

            result[signature] = {
                "ratio": float(ratio),
                "price_increase": float(price_delta),
                "value_increase": float(value_delta)
            }

            prev = item

        return result

    # ============================================================
    # THRESHOLD
    # ============================================================

    def calculate_threshold(
            self,
            group_metrics
    ):

        valid = []

        for metrics in group_metrics.values():

            ratio = metrics["ratio"]

            if ratio is None:
                continue

            valid.append(ratio)

        if not valid:
            return self.MIN_THRESHOLD

        med = median(valid)

        threshold = med * 0.1

        threshold = max(
            threshold,
            self.MIN_THRESHOLD
        )

        threshold = min(
            threshold,
            self.MAX_THRESHOLD
        )

        return float(threshold)

    # ============================================================
    # MARKET COMPETITION
    # ============================================================

    def analyze_market_inside_group(self, group):
        """
        baseline = cheapest
        MAD = медианное абсолютное отклонение цен

        dynamic_softness = MAD_SOFTNESS * (baseline / 40000) ** MAD_ALPHA
        effective_mad = MAD * dynamic_softness

        dominated = abs_delta > effective_mad
        """

        # --- собираем цены ---
        prices = [
            self._get_price(o)
            for o in group["origins"]
        ]

        if not prices:
            return {}

        # --- baseline ---
        baseline = group["min_price"]

        # --- медиана ---
        med = median(prices)

        # --- отклонения ---
        deviations = [
            abs(p - med)
            for p in prices
        ]

        # --- MAD ---
        mad = median(deviations)

        # --- динамическая мягкость ---
        # MAD_SOFTNESS и MAD_ALPHA берём из класса
        base_softness = getattr(self, "MAD_SOFTNESS", 5.0)
        alpha = getattr(self, "MAD_ALPHA", 0.7)

        # baseline / 40000 — относительная цена в процентах
        dynamic_softness = base_softness * (baseline / 30000) ** alpha

        # --- итоговый MAD ---
        effective_mad = mad * dynamic_softness

        if effective_mad <= 0:
            effective_mad = 0.0001

        result = {}

        for origin in group["origins"]:
            price = self._get_price(origin)
            abs_delta = price - baseline

            dominated = abs_delta > effective_mad

            # tolerance = self.baseline_tolerance(baseline)
            # delta_pct = abs_delta / baseline
            # dominated = delta_pct > tolerance

            result[origin.origin] = {
                "dominated": dominated,
                "market_delta": abs_delta / max(baseline, 1.0),
                "mad": mad,
                "dynamic_softness": dynamic_softness,
                "effective_mad": effective_mad,
                "abs_delta": abs_delta
            }

        return result

    # ============================================================
    # BUILD ANALYZE
    # ============================================================

    def build_analyze_item(
            self,
            origin,
            group_metrics,
            market_metrics,
            threshold,
            group_value
    ):
        oid = origin.origin

        dominated = market_metrics["dominated"]
        market_delta = market_metrics["market_delta"]

        ratio = group_metrics["ratio"]
        price_inc = group_metrics["price_increase"]
        value_inc = group_metrics["value_increase"]

        # --- логика вердикта ---
        # baseline группы
        if dominated:
            verdict = False
            reason = "Цена выбивается из нормального диапазона внутри группы"

        elif ratio is None:
            verdict = True
            reason = "Базовая конфигурация, от которой считаются апгрейды"


        else:
            verdict = True
            reason = "good"

        # --- лог ---
        print(
            "[ANALYZE] "
            f"origin={oid} | "
            f"verdict={verdict} | "
            f"reason={reason} | "
            f"ratio={ratio} | "
            f"threshold={threshold:.4f} | "
            f"price_inc={price_inc:.4f} | "
            f"value_inc={value_inc:.4f} | "
            f"dominated={dominated} | "
            f"market_delta={market_delta:.4f} | "
            f"group_value={group_value:.4f}"
        )

        return AnalyzeItem(
            verdict=bool(verdict),
            reason=reason,
            ratio=float(ratio or 0.0),
            threshold=float(threshold),
            price_increase=float(price_inc),
            value_increase=float(value_inc),
            value=float(group_value),
        )

    # ============================================================
    # MAIN
    # ============================================================

    def analyze_model_origins(
            self,
            model
    ):

        # ------------------------------------------------
        # 1. CONFIGURATION GROUPS
        # ------------------------------------------------

        groups = self.build_configuration_groups(
            model
        )

        # ------------------------------------------------
        # 2. UPGRADE CHAIN
        # ------------------------------------------------

        chain = self.build_upgrade_chain(
            groups
        )

        # ------------------------------------------------
        # 3. GROUP ECONOMICS
        # ------------------------------------------------

        group_metrics = self.calculate_group_ratios(
            chain
        )

        # ------------------------------------------------
        # 4. THRESHOLD
        # ------------------------------------------------

        threshold = self.calculate_threshold(
            group_metrics
        )

        # ------------------------------------------------
        # 5. MARKET ANALYSIS
        # ------------------------------------------------

        for signature, group in groups.items():

            metrics = group_metrics[signature]

            market = self.analyze_market_inside_group(
                group
            )

            for origin in group["origins"]:
                origin.analyze = (
                    self.build_analyze_item(
                        origin=origin,
                        group_metrics=metrics,
                        market_metrics=market[
                            origin.origin
                        ],
                        threshold=threshold,
                        group_value=group["value"]
                    )
                )
