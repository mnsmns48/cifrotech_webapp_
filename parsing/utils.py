import math
from typing import List

from api_service.schemas import HarvestLineIn


def cost_process(n, reward_ranges):
    for line_from, line_to, is_percent, extra in reward_ranges:
        if line_from <= n < line_to:
            if is_percent:
                addition = n * extra / 100
            else:
                addition = extra
            result = n + addition
            return math.ceil(result / 100) * 100
    return n

def cost_value_update(items: List[HarvestLineIn], ranges: list) -> List[HarvestLineIn]:
    for item in items:
        if item.origin is not None and item.input_price is not None:
            item.output_price = cost_process(item.input_price, ranges)
    return items
