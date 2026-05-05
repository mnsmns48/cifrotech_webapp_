from collections import defaultdict
from typing import List, Dict

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.hub import fetch_leaf_routes
from api_service.crud.main import get_all_children_cte, get_vsl_by_origins, get_origins_by_path_ids, get_parsing_map, \
    get_hub_map, get_recomputed_lines, update_hubstock_prices, fetch_unidentified_origins_db, \
    resolve_comparison_selected_models, approve_origins_for_update_db
from api_service.func import generate_diff_tabs
from api_service.s3_helper import get_s3_client
from api_service.schemas import ComparisonResponse, ComparisonSchemeQuery, HubLevelPath, VSLScheme, ParsingHubDiffOut, \
    ParsingToDiffData, HubToDiffData, RecalcScheme, RecomputedResult, UnidentifiedOrigins, HubRoutes, \
    ComparableModel, ComparableUnion, UpdateHubApproveItems, ApproveAnalyzedResponse

from engine import db
from models import VendorSearchLine

comparison_router = APIRouter(tags=['Comparison'])


@comparison_router.post("/start_comparison_process", response_model=List[ComparisonResponse])
async def comparison_process(payload: ComparisonSchemeQuery,
                             session: AsyncSession = Depends(db.scoped_session_dependency)):
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


@comparison_router.post(path="/give_recomputed_output_prices", response_model=List[RecomputedResult])
async def recompute_prices(payload: RecalcScheme, session: AsyncSession = Depends(db.scoped_session_dependency)):
    if not payload.origins:
        origins = await get_origins_by_path_ids(path_ids=payload.path_ids, session=session)
    else:
        origins = payload.origins
    changed_lines = await get_recomputed_lines(session=session, origins=origins)
    return changed_lines


@comparison_router.post("/fetch_unidentified_origins", response_model=UnidentifiedOrigins)
async def fetch_unidentified_origins(payload: ComparisonOutScheme,
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_unidentified_origins_db(payload, session)


@comparison_router.post("/resolve_models_for_comparison", response_model=List[ComparableUnion])
async def resolve_models_for_comparison(payload: ComparisonOutScheme,
                                        session: AsyncSession = Depends(db.scoped_session_dependency)):
    path_ids = [p.path_id for p in payload.path_ids]
    leaf_routes: List[HubRoutes] = await fetch_leaf_routes(path_ids=path_ids, session=session)
    models_in_hub_: List[ComparableModel] = await resolve_comparison_selected_models(path_ids, session)

    merged: List[ComparableUnion] = list()
    _buffer = dict()

    for item in models_in_hub_:
        _buffer[item.path_id] = item.models

    for route_item in leaf_routes:
        pid = route_item.path_id

        if pid in _buffer:
            models = _buffer[pid]
        else:
            models = []

        merged.append(ComparableUnion(path_id=pid, route=route_item.route, models=models))

    return merged

# @comparison_router.post("/approve_origins_for_update", response_model=list[ApproveAnalyzedResponse])
# async def approve_origins_for_update(payload: UpdateHubApproveItems,
#                                      s3_client=Depends(get_s3_client),
#                                      session: AsyncSession = Depends(db.scoped_session_dependency)):
#     return await approve_origins_for_update_db(payload, session, s3_client)
