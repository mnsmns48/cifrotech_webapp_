from typing import List

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.price_sync.service import PriceSync
from api_service.schemas import PriceSyncPickedPath, PathIdRequest, RawOrigin

from engine import db

price_sync_router = APIRouter(tags=['Price Sync'])


@price_sync_router.post("/start_price_sync_process", response_model=List[PriceSyncPickedPath])
async def start_price_sync_process(payload: PathIdRequest,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.start_sync_process(payload, session)


@price_sync_router.post("/fetch_raw_origins", response_model=List[RawOrigin])
async def fetch_raw_origins(payload: List[PriceSyncPickedPath],
                            session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.fetch_raw_origins(payload, session)

# @comparison_router.post("/resolve_models_for_comparison", response_model=List[ComparableUnion])
# async def resolve_models_for_comparison(payload: ComparisonOutScheme,
#                                         session: AsyncSession = Depends(db.scoped_session_dependency)):
#     path_ids = [p.path_id for p in payload.path_ids]
#     leaf_routes: List[HubRoutes] = await fetch_leaf_routes(path_ids=path_ids, session=session)
#     models_in_hub_: List[ComparableModel] = await resolve_comparison_selected_models(path_ids, session)
#
#     merged: List[ComparableUnion] = list()
#     _buffer = dict()
#
#     for item in models_in_hub_:
#         _buffer[item.path_id] = item.models
#
#     for route_item in leaf_routes:
#         pid = route_item.path_id
#
#         if pid in _buffer:
#             models = _buffer[pid]
#         else:
#             models = []
#
#         merged.append(ComparableUnion(path_id=pid, route=route_item.route, models=models))
#
#     return merged

# @comparison_router.post("/approve_origins_for_update", response_model=list[ApproveAnalyzedResponse])
# async def approve_origins_for_update(payload: UpdateHubApproveItems,
#                                      s3_client=Depends(get_s3_client),
#                                      session: AsyncSession = Depends(db.scoped_session_dependency)):
#     return await approve_origins_for_update_db(payload, session, s3_client)
