from collections import defaultdict
from typing import List, Dict

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.main import get_parsing_map, \
    get_hub_map, get_recomputed_lines, update_hubstock_prices, fetch_unidentified_origins_db, \
    resolve_comparison_selected_models, approve_origins_for_update_db
from api_service.func import generate_diff_tabs
from api_service.modulars.price_sync.service import PriceSync
from api_service.s3_helper import get_s3_client
from api_service.schemas import PriceSyncPickedPath, PriceSyncRequest, HubLevelPath, VSLScheme, ParsingHubDiffOut, \
    ParsingToDiffData, HubToDiffData, RecalcScheme, RecomputedResult, UnidentifiedOrigins, HubRoutes, \
    ComparableModel, ComparableUnion, UpdateHubApproveItems, ApproveAnalyzedResponse

from engine import db
from models import VendorSearchLine

price_sync_router = APIRouter(tags=['Price Sync'])


@price_sync_router.post("/start_price_sync_process", response_model=List[PriceSyncPickedPath])
async def start_price_sync_process(payload: PriceSyncRequest,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.start_sync_process(payload, session)




# @price_sync_router.post("/fetch_unidentified_origins", response_model=UnidentifiedOrigins)
# async def fetch_unidentified_origins(payload: ComparisonOutScheme,
#                                      session: AsyncSession = Depends(db.scoped_session_dependency)):
#     return await fetch_unidentified_origins_db(payload, session)



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
