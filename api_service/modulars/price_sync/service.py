from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.price_sync.crud import fetch_raw_origins_db, fetch_leaf_routes, collect_price_sync_paths
from api_service.schemas import PathIdRequest, PriceSyncPickedPath, HubRoutes, SyncPathWOrigins


class PriceSync:
    @staticmethod
    async def start_sync_process(payload: PathIdRequest, session: AsyncSession) -> List[PriceSyncPickedPath]:
        leaf_routes: List[HubRoutes] = await fetch_leaf_routes(session, [payload.path_id])
        return await collect_price_sync_paths(session, leaf_routes)

    @staticmethod
    async def fetch_raw_origins(payload: List[PriceSyncPickedPath], session: AsyncSession) -> List[SyncPathWOrigins]:
        return await fetch_raw_origins_db(payload, session)
