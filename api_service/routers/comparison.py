from typing import List, Dict

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_all_children_cte, get_lines_by_origins, get_origins_by_path_ids, get_parsing_map, \
    get_hub_map
from api_service.func import generate_diff_tabs
from api_service.schemas import ComparisonOutScheme, ComparisonInScheme, HubLevelPath, VSLScheme, ParsingHubDiffOut, \
    ParsingToDiffData, HubToDiffData
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


# @comparison_router.post(path="/recompute_output_prices")
# async def recompute_prices(payload: RecalcScheme,
#                            session: AsyncSession = Depends(db.scoped_session_dependency)):
#     if payload.origins:
#         changed_lines = await get_recomputed_lines(origins=payload.origins, session=session)
#     return {"status": payload}
