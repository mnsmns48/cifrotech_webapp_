import math
from typing import List

from api_service.schemas import ParsingLinesIn, RewardRangeLineSchema


def cost_process(n, reward_ranges: List[RewardRangeLineSchema]):
    if not reward_ranges:
        return n
    for r in reward_ranges:
        if r.line_from <= n < r.line_to:
            addition = n * r.reward / 100 if r.is_percent else r.reward
            result = n + addition
            return math.ceil(result / 100) * 100
    return n


def cost_value_update(items: List[ParsingLinesIn], ranges: List[RewardRangeLineSchema]) -> List[ParsingLinesIn]:
    updated = list()
    for item in items:
        if item.origin is not None and item.input_price is not None:
            updated_item = item.model_copy()
            updated_item.output_price = cost_process(item.input_price, ranges)
            updated.append(updated_item)
        else:
            updated.append(item)
    return updated
