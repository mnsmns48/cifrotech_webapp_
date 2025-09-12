from collections import defaultdict
from typing import Dict, List, Optional

from api_service.schemas import ParsingToDiffData, HubToDiffData, ParsingHubDiffOut
from api_service.schemas.comparison_schemas import ParsingHubDiffItem
from var_types import PriceDiffStatus


def get_diff_status(pars_item: Optional[ParsingToDiffData],
                    hub_price: Optional[float]) -> PriceDiffStatus:
    if pars_item is None or pars_item.parsing_input_price is None:
        return PriceDiffStatus.only_hub
    pi = pars_item.parsing_input_price or 0.0
    hi = hub_price or 0.0
    if pi == hi:
        return PriceDiffStatus.equal
    elif hi > pi:
        return PriceDiffStatus.hub_higher
    else:
        return PriceDiffStatus.parsing_higher


def generate_diff_tabs(parsing_map: Dict[int, List[ParsingToDiffData]],
                       hub_map: Dict[int, List[HubToDiffData]],
                       path_map: Dict[int, str]) -> List[ParsingHubDiffOut]:
    indexed_parsing_map = defaultdict(dict)
    for vsl_id, items in parsing_map.items():
        for item in items:
            indexed_parsing_map[vsl_id][item.origin] = item

    result: List[ParsingHubDiffOut] = list()

    for path_id, label in path_map.items():
        hub_items = hub_map.get(path_id, [])
        items: List[ParsingHubDiffItem] = list()

        for hub_item in hub_items:
            pars_obj: Optional[ParsingToDiffData] = indexed_parsing_map.get(hub_item.vsl_id, {}).get(hub_item.origin)

            item = ParsingHubDiffItem(origin=hub_item.origin,
                                      title=hub_item.title,
                                      url=pars_obj.url if pars_obj is not None else None,
                                      status=get_diff_status(pars_obj, hub_item.hub_input_price),
                                      warranty=hub_item.warranty,
                                      optional=pars_obj.optional if pars_obj is not None else None,
                                      shipment=pars_obj.shipment if pars_obj is not None else None,
                                      parsing_line_title=pars_obj.parsing_line_title if pars_obj is not None else None,
                                      parsing_input_price=pars_obj.parsing_input_price if pars_obj is not None else None,
                                      parsing_output_price=pars_obj.parsing_output_price if pars_obj is not None else None,
                                      dt_parsed=pars_obj.dt_parsed if pars_obj is not None else None,
                                      profit_range_id=pars_obj.profit_range_id if pars_obj is not None else None,
                                      hub_input_price=hub_item.hub_input_price,
                                      hub_output_price=hub_item.hub_output_price,
                                      hub_added_at=hub_item.hub_added_at,
                                      hub_updated_at=hub_item.hub_updated_at,
                                      )
            items.append(item)

        result.append(
            ParsingHubDiffOut(path_id=path_id, label=label, items=items)
        )

    return result
