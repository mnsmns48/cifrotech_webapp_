from typing import List, Dict, Any

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.hub import fetch_final_leaf_ids, fetch_hub_routes_db
from api_service.crud.main import get_all_children_cte, get_lines_by_origins, get_origins_by_path_ids, get_parsing_map, \
    get_hub_map, get_recomputed_lines, update_hubstock_prices, fetch_unidentified_origins_db, \
    resolve_comparison_selected_models, approve_origins_for_update_db
from api_service.func import generate_diff_tabs
from api_service.s3_helper import get_s3_client
from api_service.schemas import ComparisonOutScheme, ComparisonInScheme, HubLevelPath, VSLScheme, ParsingHubDiffOut, \
    ParsingToDiffData, HubToDiffData, RecalcScheme, RecomputedResult, UnidentifiedOrigins, HubRoutes, \
    ComparableModel, ComparableUnion, HubMenuLevelSchema, ResolveFeatureModel, UpdateHubApproveItems, \
    UpdateApproveItemResponse

from engine import db
from models import VendorSearchLine

comparison_router = APIRouter(tags=['Comparison'])


@comparison_router.post("/start_comparison_process", response_model=ComparisonOutScheme)
async def comparison_process(payload: ComparisonInScheme,
                             session: AsyncSession = Depends(db.scoped_session_dependency)):
    path_ids: List[HubLevelPath] = await get_all_children_cte(session=session, parent_id=payload.path_id)

    if payload.origins:
        raw_vsl_list: list[VendorSearchLine] = await get_lines_by_origins(origins=payload.origins, session=session)
    else:
        only_paths = [p.path_id for p in path_ids]
        origins = await get_origins_by_path_ids(only_paths, session)
        raw_vsl_list: list[VendorSearchLine] = await get_lines_by_origins(origins, session)

    vsl_list: list[VSLScheme] = list()
    for vsl in raw_vsl_list:
        vsl_list.append(VSLScheme.model_validate(vsl))

    return ComparisonOutScheme(vsl_list=vsl_list, path_ids=path_ids)


@comparison_router.post(path="/give_me_consent", response_model=List[ParsingHubDiffOut])
async def consent_process(payload: ComparisonOutScheme,
                          session: AsyncSession = Depends(db.scoped_session_dependency)):
    parsing_map: Dict[int, List[ParsingToDiffData]] = await get_parsing_map(session, payload.vsl_list)
    path_ids: List[int] = [p.path_id for p in payload.path_ids]
    hub_map: Dict[int, List[HubToDiffData]] = await get_hub_map(session, path_ids)
    path_map: Dict[int, str] = dict()
    for p in payload.path_ids:
        if p.path_id in hub_map.keys():
            path_map.update({p.path_id: p.label})
    result: List[ParsingHubDiffOut] = generate_diff_tabs(parsing_map, hub_map, path_map)
    return result


@comparison_router.post(path="/give_recomputed_output_prices", response_model=List[RecomputedResult])
async def recompute_prices(payload: RecalcScheme, session: AsyncSession = Depends(db.scoped_session_dependency)):
    if not payload.origins:
        origins = await get_origins_by_path_ids(path_ids=payload.path_ids, session=session)
    else:
        origins = payload.origins
    changed_lines = await get_recomputed_lines(session=session, origins=origins)
    return changed_lines


@comparison_router.patch("/store_new_prices_hubstock_items")
async def store_new_prices_hubstock_items(
        patch_data: List[RecomputedResult], session: AsyncSession = Depends(db.scoped_session_dependency)):
    price_map = dict()
    for group in patch_data:
        for item in group.recomputed_items:
            price_map.update({item.origin:
                                  {'input_price': item.input_parsing_price,
                                   'output_price': item.output_parsing_price}
                              })
    result = await update_hubstock_prices(price_map, session)
    if result:
        await session.commit()
    return patch_data


@comparison_router.post("/fetch_unidentified_origins", response_model=UnidentifiedOrigins)
async def fetch_unidentified_origins(payload: ComparisonOutScheme,
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_unidentified_origins_db(payload, session)


@comparison_router.post("/resolve_models_for_comparison", response_model=List[ComparableUnion])
async def fetch_hub_routes(payload: ComparisonOutScheme,
                           session: AsyncSession = Depends(db.scoped_session_dependency)):
    leaf_path_ids: List = await fetch_final_leaf_ids(path_ids=payload.path_ids, session=session)
    routes: List[HubRoutes] = await fetch_hub_routes_db(leaf_path_ids, session)
    models_in_hub_: List[ComparableModel] = await resolve_comparison_selected_models(leaf_path_ids, session)

    merged: List[ComparableUnion] = list()
    _buffer = dict()

    for item in models_in_hub_:
        _buffer[item.path_id] = item.models

    for route_item in routes:
        pid = route_item.path_id

        if pid in _buffer:
            models = _buffer[pid]
        else:
            models = []

        merged.append(ComparableUnion(path_id=pid, route=route_item.route, models=models))

    return merged


@comparison_router.post("/approve_origins_for_update", response_model=List[UpdateApproveItemResponse])
async def approve_origins_for_update(payload: UpdateHubApproveItems,
                                     s3_client=Depends(get_s3_client),
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await approve_origins_for_update_db(payload, session, s3_client)
