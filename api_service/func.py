import operator
from typing import Dict, List, Set

from api_service.schemas import ParsingToDiffData, HubToDiffData, ParsingHubDiffOut
from api_service.schemas.hub_schemas import ParsingHubDiffItem
from var_types import PriceDiffStatus


def generate_diff_tabs(parsing_map: Dict[int, List[ParsingToDiffData]],
                       hub_map: Dict[int, List[HubToDiffData]],
                       path_map: Dict[int, str]) -> List[ParsingHubDiffOut]:
    result: List[ParsingHubDiffOut] = list()
    for path_id, label in path_map.items():
        hub_items = hub_map.get(path_id, [])
        items: List[ParsingHubDiffItem] = []

        for h_data in hub_items:
            vsl_id = h_data.vsl_id
            origin = h_data.origin


            parsing_input_price = None
            dt_parsed = None
            parsing_candidates = parsing_map.get(vsl_id, [])
            for p in parsing_candidates:
                if p.origin == origin:
                    parsing_input_price = p.parsing_input_price
                    dt_parsed = p.dt_parsed
                    break

            if parsing_input_price is not None:
                ip = parsing_input_price or 0.0
                hi = h_data.hub_input_price or 0.0
                if ip == hi:
                    status = PriceDiffStatus.equal
                elif hi > ip:
                    status = PriceDiffStatus.hub_higher
                else:
                    status = PriceDiffStatus.parsing_higher
            else:
                status = PriceDiffStatus.only_hub

            item = ParsingHubDiffItem(
                origin=origin,
                title=h_data.title,
                status=status,
                warranty=h_data.warranty,
                optional=None,
                shipment=None,
                parsing_line_title=None,
                parsing_input_price=parsing_input_price,
                parsing_output_price=None,
                dt_parsed=dt_parsed,
                profit_range_id=None,
                hub_input_price=h_data.hub_input_price,
                hub_output_price=h_data.hub_output_price,
                hub_added_at=h_data.hub_added_at,
                hub_updated_at=h_data.hub_updated_at,
            )
            items.append(item)


        items.sort(key=lambda it: it.hub_input_price or 0.0)

        result.append(
            ParsingHubDiffOut(
                path_id=path_id,
                label=label,
                items=items or None
            )
        )

    return result