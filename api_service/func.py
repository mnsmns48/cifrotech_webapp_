from typing import Dict, List, Set

from api_service.schemas import ParsingToDiffData, HubToDiffData, ParsingHubDiffOut
from api_service.schemas.hub_schemas import ParsingHubDiffItem
from var_types import PriceDiffStatus


def generate_diff_tabs(parsing_map: Dict[int, ParsingToDiffData],
                       hub_map: Dict[int, List[HubToDiffData]],
                       path_map: Dict[int, str]) -> List[ParsingHubDiffOut]:
    result: List[ParsingHubDiffOut] = list()
    for path_id, label in path_map.items():
        hub_items = hub_map.get(path_id, [])
        hub_by_origin = {h.origin: h for h in hub_items}
        origins = set(parsing_map.keys()) | set(hub_by_origin.keys())
        items: List[ParsingHubDiffItem] = []
        for origin in origins:
            p = parsing_map.get(origin)
            h = hub_by_origin.get(origin)
            if p and not h:
                status = PriceDiffStatus.only_parsing
            elif h and not p:
                status = PriceDiffStatus.only_hub
            else:
                ip = p.parsing_input_price or 0.0
                hi = h.hub_input_price or 0.0
                if ip == hi:
                    status = PriceDiffStatus.equal
                elif hi > ip:
                    status = PriceDiffStatus.hub_higher
                else:
                    status = PriceDiffStatus.parsing_higher
            title = p.title if p else (h.title if h else "")
            item = ParsingHubDiffItem(origin=origin, title=title, status=status,
                                      parsing_line_title=p.parsing_line_title if p else None,
                                      parsing_input_price=p.parsing_input_price if p else None,
                                      parsing_output_price=p.parsing_output_price if p else None,
                                      dt_parsed=p.dt_parsed if p else None,
                                      profit_range_id=p.profit_range_id if p else None,
                                      hub_input_price=h.hub_input_price if h else None,
                                      hub_output_price=h.hub_output_price if h else None,
                                      hub_added_at=h.hub_added_at if h else None,
                                      hub_updated_at=h.hub_updated_at if h else None,
                                      warranty=p.warranty if p else (h.warranty if h else None),
                                      optional=p.optional if p else None,
                                      shipment=p.shipment if p else None)
            items.append(item)
        result.append(ParsingHubDiffOut(path_id=path_id, label=label, items=items))
    return result
