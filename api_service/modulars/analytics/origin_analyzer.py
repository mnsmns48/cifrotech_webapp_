from operator import itemgetter, attrgetter
from statistics import median, mean

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
            if override == OverrideType.include and weight is None:
                weight = 1.0

            if weight is None:
                continue

            multiplier = self.value_multiplier.get(value_id, 1.0)
            total_value += weight * multiplier

        return total_value

    def analyze_model(self, model: ModelForApprove,
                            margin: float = 0.02,
                            min_group_size_for_delta: int = 3,
                            baseline_ratio: float = 1e-8):
        """
        Простая и объяснимая версия analyze_model на основе ratio и threshold.
        Заполняет origin.analyze = AnalyzeItem(...)
        """

        type_id = model.type_.id
        brand_id = model.brand.id

        # helper: безопасный доступ к цене
        def _price(o):
            try:
                return float(getattr(o, "input_price", 0) or 0.0)
            except Exception:
                try:
                    return float(o.get("input_price", 0) or 0.0)
                except Exception:
                    return 0.0

        # 1) value и ratio для каждого origin
        values = {}
        ratios = {}
        for o in model.origins:
            v = float(self.analyze_origin(o, type_id, brand_id) or 0.0)
            p = _price(o) or 1.0
            r = v / p if p > 0 else 0.0
            values[o.origin] = v
            ratios[o.origin] = r

        # 2) определить главный количественный атрибут (если есть) — иначе одна группа
        numeric_keys = set()
        attr_values_by_key = {}
        for origin in model.origins:
            for attr in origin.attrs or []:
                key_id = self.key_by_value.get(attr.id)
                if key_id is None:
                    continue
                val = attr.value
                attr_values_by_key.setdefault(key_id, set()).add(val)
                raw = val or ""
                num_str = "".join(ch for ch in str(raw) if (ch.isdigit() or ch == "."))
                if num_str:
                    try:
                        float(num_str)
                        numeric_keys.add(key_id)
                    except Exception:
                        pass

        # выбрать главный количественный ключ по весу/разнообразию (как в v12.x)
        quantitative_key = None
        if numeric_keys:
            def get_weight(k):
                return self.weight_rules.get((type_id, k), 1.0)

            best = None
            best_score = None
            for k in numeric_keys:
                score = (get_weight(k), len(attr_values_by_key.get(k, ())))
                if best_score is None or score > best_score:
                    best_score = score
                    best = k
            quantitative_key = best

        # 3) группировка: по quantitative_key если есть, иначе одна группа "__all__"
        groups = {}

        def get_attr_value(origin, key_id):
            for attr in origin.attrs or []:
                if self.key_by_value.get(attr.id) == key_id:
                    return attr.value
            return None

        if quantitative_key is None:
            groups["__all__"] = list(model.origins)
        else:
            for o in model.origins:
                qv = get_attr_value(o, quantitative_key)
                if qv is None:
                    groups.setdefault("__none__", []).append(o)
                else:
                    groups.setdefault(str(qv), []).append(o)

        # 4) для каждой группы вычисляем threshold и применяем Δ-разрывы (опционально)
        subgroup_allowed = {}  # group_key -> set(origin_id)
        subgroup_debug = {}

        for gk, origins in groups.items():
            # сортировка по цене
            origins_sorted = sorted(origins, key=lambda x: _price(x))
            prices = [_price(o) for o in origins_sorted]
            ids = [o.origin for o in origins_sorted]
            # Δ-разрыв: если size >= min_group_size_for_delta, ищем резкий скачок
            allowed_ids = set(ids)
            if len(prices) >= min_group_size_for_delta:
                deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
                cutoff = len(prices)
                for i, d in enumerate(deltas):
                    if i > 0:
                        prev_sum = sum(deltas[:i])
                        if d > prev_sum:
                            cutoff = i + 1
                            break
                allowed_ids = set(ids[:cutoff])
            subgroup_allowed[gk] = allowed_ids
            subgroup_debug[gk] = {"prices": prices, "ids": ids, "allowed": sorted(list(allowed_ids))}

        # 5) threshold: для каждой группы threshold = max(best_ratio_in_allowed * (1 - margin), baseline_ratio)
        group_threshold = {}
        for gk, allowed in subgroup_allowed.items():
            if not allowed:
                group_threshold[gk] = baseline_ratio
                continue
            best_ratio = max(ratios.get(o, 0.0) for o in allowed)
            thr = max(best_ratio * (1.0 - margin), baseline_ratio)
            group_threshold[gk] = thr

        # 6) финальные метрики и заполнение AnalyzeItem
        for o in model.origins:
            # определить группу
            if quantitative_key is None:
                gk = "__all__"
            else:
                qv = get_attr_value(o, quantitative_key)
                gk = str(qv) if qv is not None else "__none__"

            v = values.get(o.origin, 0.0)
            p = _price(o)
            r = ratios.get(o.origin, 0.0)
            thr = group_threshold.get(gk, baseline_ratio)
            in_sub = o.origin in subgroup_allowed.get(gk, set())

            # verdict: проходит если в подгруппе и ratio >= threshold
            verdict = bool(in_sub and (r >= thr))

            # price_increase: сколько нужно снизить цену, чтобы ratio >= thr
            if thr <= 0:
                price_increase = 0.0
            else:
                target_price = v / thr if thr > 0 else p
                price_increase = max(0.0, p - target_price)

            # value_increase: сколько нужно увеличить value при текущей цене
            target_value = thr * p
            value_increase = max(0.0, target_value - v)

            # ratio and threshold stored
            origin_ratio = float(r)
            origin_threshold = float(thr)

            o.analyze = AnalyzeItem(
                verdict=verdict,
                ratio=origin_ratio,
                threshold=origin_threshold,
                price_increase=round(price_increase, 2),
                value_increase=round(value_increase, 4),
                value=round(v, 4)
            )

        # 7) диагностика (печать краткой сводки)
        print("=== ratio/threshold diagnostics ===")
        for gk, dbg in subgroup_debug.items():
            print(f"group={gk} prices={dbg['prices']} allowed={dbg['allowed']} threshold={group_threshold.get(gk)}")
        print("=== end diagnostics ===")