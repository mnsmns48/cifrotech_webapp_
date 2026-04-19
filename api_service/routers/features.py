from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.features import product_features_depps_db, features_hub_level_routes_db, \
    features_set_level_routes_db, features_check_features_path_label_link_db, get_features_by_origin_db, \
    delete_pros_cons_value_db, add_pros_cons_value_db, update_pros_cons_value_db, create_new_info_category_db, \
    delete_info_category_db, update_info_category_db, add_new_features_inner_row_db, delete_features_inner_row_db, \
    update_features_inner_row_db, delete_feature_db, types_brands_request_db, add_new_brand_request_db, \
    add_new_type_request_db, create_new_feature_global_db, set_feature_formula_dependency_db, \
    fetch_product_information_db

from api_service.schemas import FeaturesDataSet, PathRoutes, SetFeaturesHubLevelRequest, SetLevelRoutesResponse, \
    OriginsList, OriginHubLevelMap, FeatureResponseScheme, ProsConsItem, ProsConsItemUpdate, FeatureCategory, \
    UpdateFeatureCategoryRequest, InnerRowRequest, UpdateInnerRowRequest, FeatureIds, TypesAndBrands, \
    ProductOriginUpdate, CreateFeaturesGlobal, SetFeaturesFormulaRequest, SetFormulaResponse, FetchProductInfoRequest, \
    ProductResponse

from engine import db

features_router = APIRouter(tags=['Features'])


@features_router.get("/features/product_features_depps", response_model=FeaturesDataSet)
async def product_features_depps_fetch(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await product_features_depps_db(session)


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


@features_router.post("/features/add_new_inner_row")
async def add_new_features_inner_row(payload: InnerRowRequest,
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await add_new_features_inner_row_db(payload, session)


@features_router.post("/features/delete_inner_row")
async def delete_features_inner_row(payload: InnerRowRequest,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await delete_features_inner_row_db(payload, session)


@features_router.post("/features/update_inner_row")
async def update_features_inner_row(payload: UpdateInnerRowRequest,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await update_features_inner_row_db(payload, session)


@features_router.post("/features/delete_features")
async def delete_feature(feature_ids: FeatureIds,
                         session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await delete_feature_db(feature_ids, session)


@features_router.get("/features/types_brands_request", response_model=TypesAndBrands)
async def types_brands_request(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await types_brands_request_db(session)


@features_router.post("/features/add_new_brand")
async def add_new_brand_request(title: ProductOriginUpdate,
                                session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await add_new_brand_request_db(title, session)


@features_router.post("/features/add_new_type")
async def add_new_type_request(title: ProductOriginUpdate,
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await add_new_type_request_db(title, session)


@features_router.post("/features/create_new_feature_global")
async def create_new_feature_global(payload: CreateFeaturesGlobal,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await create_new_feature_global_db(payload, session)


@features_router.post("/features/set_formula_dependency", response_model=SetFormulaResponse)
async def set_feature_formula_dependency(payload: SetFeaturesFormulaRequest,
                                         session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await set_feature_formula_dependency_db(payload, session)


@features_router.post("/features/fetch_product_information", response_model=ProductResponse)
async def fetch_product_information(payload: FetchProductInfoRequest,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_product_information_db(payload, session)
