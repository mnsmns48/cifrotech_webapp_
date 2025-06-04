import math


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


def cost_value_update(items: list[dict], ranges: list) -> list:
    for item in items:
        if item['origin'] and item['input_price']:
            item['output_price'] = cost_process(item['input_price'], ranges)
    return items
