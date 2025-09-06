from typing import Dict, List, Set

from api_service.schemas import ParsingToDiffData, HubToDiffData, ParsingHubDiffOut
from api_service.schemas.hub_schemas import ParsingHubDiffItem
from var_types import PriceDiffStatus


def generate_diff_tabs(
        parsing_map: Dict[int, ParsingToDiffData], hub_map: Dict[int, List[HubToDiffData]],
        path_label_map: Dict[int, str], path_ids: List[int]) -> List[ParsingHubDiffOut]:
    result: List[ParsingHubDiffOut] = list()

    for path_id in path_ids:
        label = path_label_map[path_id]
        hub_items = hub_map.get(path_id, [])

        origins_from_parsing: Set[int] = set(parsing_map.keys())
        origins_from_hub: Set[int] = {h.origin for h in hub_items}
        origins_set: Set[int] = origins_from_parsing.union(origins_from_hub)

        items_list: List[ParsingHubDiffItem] = list()

        for origin in origins_set:
            p_data = parsing_map.get(origin)
            hub_for_o = [h for h in hub_items if h.origin == origin]

            if not hub_for_o:
                status = PriceDiffStatus.only_parsing
                items_list.append(
                    ParsingHubDiffItem(
                        origin=origin,
                        title="",
                        warranty=p_data.warranty if p_data else None,
                        optional=p_data.optional if p_data else None,
                        shipment=p_data.shipment if p_data else None,
                        parsing_line_title=p_data.parsing_line_title if p_data else "",
                        parsing_input_price=p_data.parsing_input_price if p_data else None,
                        parsing_output_price=p_data.parsing_output_price if p_data else None,
                        dt_parsed=p_data.dt_parsed,
                        hub_input_price=0.0,
                        hub_output_price=0.0,
                        hub_added_at=None,
                        hub_updated_at=None,
                        status=status,
                        profit_range_id=p_data.profit_range_id if p_data else 0,
                    )
                )
                continue


            for h in hub_for_o:
                if p_data is None:
                    status = PriceDiffStatus.only_hub
                elif (p_data.parsing_input_price or 0.0) == h.hub_input_price:
                    status = PriceDiffStatus.equal
                elif h.hub_input_price > (p_data.parsing_input_price or 0.0):
                    status = PriceDiffStatus.hub_higher
                else:
                    status = PriceDiffStatus.parsing_higher

                items_list.append(
                    ParsingHubDiffItem(
                        origin=origin,
                        title="",
                        warranty=h.warranty,
                        optional=p_data.optional if p_data else None,
                        shipment=p_data.shipment if p_data else None,
                        parsing_line_title=p_data.parsing_line_title if p_data else "",
                        parsing_input_price=p_data.parsing_input_price if p_data else None,
                        parsing_output_price=p_data.parsing_output_price if p_data else None,
                        dt_parsed=p_data.dt_parsed,
                        hub_input_price=h.hub_input_price,
                        hub_output_price=h.hub_output_price or 0.0,
                        hub_added_at=h.hub_added_at,
                        hub_updated_at=h.hub_updated_at,
                        status=status,
                        profit_range_id=p_data.profit_range_id if p_data else 0,
                    )
                )

        result.append(ParsingHubDiffOut(path_id=path_id, label=label, items=items_list))

    return result
