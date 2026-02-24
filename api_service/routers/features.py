from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.features import features_hub_level_link_fetch_db, features_hub_level_routes_db, \
    features_set_level_routes_db, features_check_features_path_label_link_db
from api_service.schemas import FeaturesDataSet, PathRoutes, SetFeaturesHubLevelRequest, SetLevelRoutesResponse, \
    OriginsList, OriginHubLevelMap

from engine import db

features_router = APIRouter(tags=['Features'])


@features_router.get("/features/features_hub_level_link_fetch", response_model=FeaturesDataSet)
async def features_hub_level_link_fetch(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await features_hub_level_link_fetch_db(session)


@features_router.get("/features/hub_level_routes", response_model=PathRoutes)
async def features_hub_level_routes(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await features_hub_level_routes_db(session)


@features_router.post("/features/set_level_routes", response_model=SetLevelRoutesResponse)
async def features_set_level_routes(payload: SetFeaturesHubLevelRequest,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await features_set_level_routes_db(payload, session)


@features_router.post("/features/check_features_path_label_link", response_model=OriginHubLevelMap)
async def features_check_features_path_label_link(origin_ids: OriginsList,
                                                  session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await features_check_features_path_label_link_db(origin_ids, session)


@features_router.get("/features/get_features/{origin}")
async def get_features_by_origin(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    pass
