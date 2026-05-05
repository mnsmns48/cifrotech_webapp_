from collections import defaultdict
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.price_sync.crud import fetch_leaf_routes, get_vsl_by_origins, get_origins_by_path_ids
from api_service.schemas import PriceSyncRequest, ComparisonResponse, VSLScheme


class PriceSync:
    @staticmethod
    async def start_sync_process(payload: PriceSyncRequest, session: AsyncSession) -> List[ComparisonResponse]:
        leaf_routes = await fetch_leaf_routes(path_ids=[payload.path_id], session=session)
        if payload.origins:
            raw_vsl_list = await get_vsl_by_origins(payload.origins, session)
        else:
            leaf_ids = [leaf.path_id for leaf in leaf_routes]
            origins = await get_origins_by_path_ids(leaf_ids, session)
            raw_vsl_list = await get_vsl_by_origins(origins, session)

        vsl_list = [VSLScheme.model_validate(vsl) for vsl in raw_vsl_list]
        vsl_by_path = defaultdict(list)
        for vsl in vsl_list:
            vsl_by_path[vsl.path_id].append(vsl)

        result: List[ComparisonResponse] = list()
        for leaf in leaf_routes:
            result.append(ComparisonResponse(id=leaf.route[-1].id,
                                             sort_order=leaf.route[-1].sort_order,
                                             label=leaf.route[-1].label,
                                             icon=leaf.route[-1].icon,
                                             parent_id=leaf.route[-1].parent_id,
                                             vsl_list=vsl_by_path.get(leaf.route[-1].id, [])))
        return result
