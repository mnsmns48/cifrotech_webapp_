from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.features import features_hub_level_link_fetch_db, features_hub_level_routes_db, \
    features_set_level_routes_db, features_check_features_path_label_link_db, get_features_by_origin_db, \
    delete_pros_cons_value_db, add_pros_cons_value_db, update_pros_cons_value_db, create_new_info_category_db, \
    delete_info_category_db, update_info_category_db
from api_service.schemas import FeaturesDataSet, PathRoutes, SetFeaturesHubLevelRequest, SetLevelRoutesResponse, \
    OriginsList, OriginHubLevelMap, FeatureResponseScheme, ProsConsItem, ProsConsItemUpdate, FeatureCategory, \
    UpdateFeatureCategoryRequest

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


@features_router.get("/features/get_features_by_feature_id/{feature_id}", response_model=FeatureResponseScheme)
async def get_features_by_origin(feature_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await get_features_by_origin_db(feature_id, session)


@features_router.post("/features/delete_pros_cons_value")
async def delete_pros_cons_value(payload: ProsConsItem,
                                 session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await delete_pros_cons_value_db(payload, session)


@features_router.post("/features/add_pros_cons_value")
async def add_pros_cons_value(payload: ProsConsItem,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await add_pros_cons_value_db(payload, session)


@features_router.post("/features/update_pros_cons_value")
async def update_pros_cons_value(payload: ProsConsItemUpdate,
                                 session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await update_pros_cons_value_db(payload, session)


@features_router.post("/features/create_new_info_category")
async def create_new_info_category(payload: FeatureCategory,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await create_new_info_category_db(payload, session)


@features_router.post("/features/delete_info_category")
async def delete_info_category(payload: FeatureCategory,
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await delete_info_category_db(payload, session)


@features_router.post("/features/Update_info_category")
async def update_info_category(payload: UpdateFeatureCategoryRequest,
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await update_info_category_db(payload, session)
