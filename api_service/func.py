import operator
from collections import defaultdict
from typing import Dict, List, Set, Optional

from api_service.schemas import ParsingToDiffData, HubToDiffData, ParsingHubDiffOut
from api_service.schemas.hub_schemas import ParsingHubDiffItem
from var_types import PriceDiffStatus


def generate_diff_tabs(
    parsing_map: Dict[int, List[ParsingToDiffData]],
    hub_map: Dict[int, List[HubToDiffData]],
    path_map: Dict[int, str]
) -> List[ParsingHubDiffOut]:

    # Шаг 1: Построим индекс для быстрого доступа по (vsl_id, origin)
    indexed_parsing_map: Dict[int, Dict[str, ParsingToDiffData]] = defaultdict(dict)
    for vsl_id, items in parsing_map.items():
        for item in items:
            indexed_parsing_map[vsl_id][item.origin] = item

    # Шаг 2: Основной проход по path_map
    result: List[ParsingHubDiffOut] = []

    for path_id, label in path_map.items():
        hub_items = hub_map.get(path_id, [])
        items: List[ParsingHubDiffItem] = []

        for hub_item in hub_items:
            pars_item: Optional[ParsingToDiffData] = indexed_parsing_map.get(hub_item.vsl_id, {}).get(hub_item.origin)

            parsing_input_price = pars_item.parsing_input_price if pars_item else None
            dt_parsed = pars_item.dt_parsed if pars_item else None

            if parsing_input_price is not None:
                ip = parsing_input_price or 0.0
                hi = hub_item.hub_input_price or 0.0
                if ip == hi:
                    status = PriceDiffStatus.equal
                elif hi > ip:
                    status = PriceDiffStatus.hub_higher
                else:
                    status = PriceDiffStatus.parsing_higher
            else:
                status = PriceDiffStatus.only_hub

            item = ParsingHubDiffItem(
                origin=hub_item.origin,
                title=hub_item.title,
                status=status,
                warranty=hub_item.warranty,
                optional=None,
                shipment=None,
                parsing_line_title=None,
                parsing_input_price=parsing_input_price,
                parsing_output_price=None,
                dt_parsed=dt_parsed,
                profit_range_id=None,
                hub_input_price=hub_item.hub_input_price,
                hub_output_price=hub_item.hub_output_price,
                hub_added_at=hub_item.hub_added_at,
                hub_updated_at=hub_item.hub_updated_at,
            )
            items.append(item)

        result.append(
            ParsingHubDiffOut(
                path_id=path_id,
                label=label,
                items=items
            )
        )

    return result
